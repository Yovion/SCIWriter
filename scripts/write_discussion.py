#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Try to import LLM client (optional dependency)
try:
    from llm_client import call, call_json, is_available as llm_available
    LLM_AVAILABLE = llm_available()
except ImportError:
    LLM_AVAILABLE = False
    print("ℹ️  llm_client not available, using rule-based approach", file=sys.stderr)


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if file_path.exists():
        print(f"  ✓ {description}: {file_path}")
        return True
    else:
        print(f"  ✗ {description}: {file_path} (NOT FOUND)")
        return False


def check_prerequisites(project_path, prompts_dir):
    """Check if all required files exist."""
    print("\nChecking project files...")
    errors = []

    # Check project-level files
    project_yaml = project_path / "project.yaml"
    storyline = project_path / "storyline.md"
    abstract_draft = project_path / "abstract_draft.md"
    results_draft = project_path / "results_draft.md"
    introduction_draft = project_path / "introduction_draft.md"

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")
    if not check_file_exists(abstract_draft, "abstract_draft.md"):
        errors.append(f"Missing: {abstract_draft}")
    if not check_file_exists(results_draft, "results_draft.md"):
        errors.append(f"Missing: {results_draft}")
    if not check_file_exists(introduction_draft, "introduction_draft.md"):
        errors.append(f"Missing: {introduction_draft}")

    # Check optional files
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

    title_candidates = project_path / "title_candidates.md"
    if title_candidates.exists():
        check_file_exists(title_candidates, "title_candidates.md (optional)")

    # Check prompt template
    print("\nChecking prompt template...")
    discussion_writer = prompts_dir / "discussion_writer.md"

    if not check_file_exists(discussion_writer, "discussion_writer.md"):
        errors.append(f"Missing: {discussion_writer}")

    return errors


def generate_manifest(project_path, prompts_dir):
    """Generate discussion_manifest.json."""
    project_yaml_path = project_path / "project.yaml"

    with open(project_yaml_path, "r", encoding="utf-8") as f:
        project_data = yaml.safe_load(f)

    project_name = project_data.get("project_name", "")
    results_order = project_data.get("results_order", [])
    main_text_modules = project_data.get("main_text_modules", [])
    detected_route = project_data.get("detected_route", "unknown")

    manifest = {
        "project_name": project_name,
        "project_path": str(project_path),
        "detected_route": detected_route,
        "results_order": results_order,
        "main_text_modules": main_text_modules,
        "prompts": {
            "discussion_writer": str(prompts_dir / "discussion_writer.md")
        },
        "input_files": {
            "storyline_path": str(project_path / "storyline.md"),
            "abstract_draft_path": str(project_path / "abstract_draft.md"),
            "results_draft_path": str(project_path / "results_draft.md"),
            "introduction_draft_path": str(project_path / "introduction_draft.md")
        }
    }

    # Add project_brief_resolved_path as top-level field if it exists
    project_brief_path = project_path / "project_brief_resolved.json"
    if project_brief_path.exists():
        manifest["project_brief_resolved_path"] = str(project_brief_path)

    # Add title_candidates_path as top-level field if it exists
    title_candidates_path = project_path / "title_candidates.md"
    if title_candidates_path.exists():
        manifest["title_candidates_path"] = str(title_candidates_path)

    return manifest


# ============================================================================
# NEW: Deep Literature Functions for Discussion (LLM-driven)
# ============================================================================

def filter_reusable_intro_refs(intro_refs_data):
    """
    Filter reusable references from Introduction.

    Args:
        intro_refs_data: Introduction refs_selected.json data

    Returns:
        list: Reusable references
    """
    # Method-related keywords
    method_keywords = [
        'differential expression',
        'Cox regression',
        'survival analysis',
        'prognostic signature',
        'biomarker discovery',
        'transcriptome'
    ]

    reusable = []
    refs = intro_refs_data.get('references', [])

    for ref in refs:
        text = (ref.get('title', '') + " " + ref.get('abstract', '')).lower()
        if any(kw in text for kw in method_keywords):
            ref_copy = ref.copy()
            ref_copy['source'] = 'intro_reused'
            reusable.append(ref_copy)

    return reusable


def search_pubmed_discussion(query, max_results=5, retries=3):
    """
    Search PubMed and return article metadata for Discussion.

    Args:
        query: Search query string
        max_results: Maximum number of results
        retries: Number of retry attempts

    Returns:
        list: List of article dictionaries
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # Step 1: Search for PMIDs
    search_url = base_url + "esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }

    for attempt in range(retries):
        try:
            search_request = urllib.request.Request(
                search_url + "?" + urllib.parse.urlencode(search_params)
            )
            with urllib.request.urlopen(search_request, timeout=30) as response:
                search_data = json.loads(response.read().decode())

            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                return []

            # Step 2: Fetch article details
            time.sleep(0.4)  # Rate limiting

            fetch_url = base_url + "efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml"
            }

            fetch_request = urllib.request.Request(
                fetch_url + "?" + urllib.parse.urlencode(fetch_params)
            )
            with urllib.request.urlopen(fetch_request, timeout=30) as response:
                xml_data = response.read().decode()

            # Parse XML
            root = ET.fromstring(xml_data)
            articles = []

            for article_elem in root.findall(".//PubmedArticle"):
                try:
                    pmid = article_elem.findtext(".//PMID")
                    title = article_elem.findtext(".//ArticleTitle") or ""
                    abstract_elem = article_elem.find(".//Abstract")
                    abstract = ""
                    if abstract_elem is not None:
                        abstract_texts = abstract_elem.findall(".//AbstractText")
                        abstract = " ".join([t.text or "" for t in abstract_texts])

                    journal = article_elem.findtext(".//Journal/Title") or ""
                    year_elem = article_elem.find(".//PubDate/Year")
                    year = year_elem.text if year_elem is not None else ""

                    articles.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "journal": journal,
                        "year": year,
                        "source": "discussion_new"
                    })
                except Exception:
                    continue

            return articles

        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return []

    return []


def supplement_discussion_refs(cancer_type, min_refs=5):
    """
    Supplement Discussion with additional literature search.

    Args:
        cancer_type: Cancer type string
        min_refs: Minimum number of references needed

    Returns:
        list: Additional references
    """
    print("\n  Supplementing Discussion literature...")

    # Priority 1: Method validation
    queries = [
        "differential expression Cox regression survival",
        "DEG prognostic biomarker screening",
        f"{cancer_type} transcriptome prognosis TCGA",
        f"{cancer_type} survival analysis gene signature"
    ]

    all_refs = []
    for query in queries:
        print(f"    Searching: {query}")
        results = search_pubmed_discussion(query, max_results=3)
        all_refs.extend(results)
        time.sleep(0.5)

    # Deduplicate by PMID
    seen = set()
    unique = []
    for ref in all_refs:
        if ref['pmid'] not in seen:
            seen.add(ref['pmid'])
            unique.append(ref)

    # Keep max 10 refs
    return unique[:10]


def assign_refs_to_theme(refs, keywords):
    """Assign references to a theme based on keywords."""
    theme_refs = []
    for ref in refs:
        text = ((ref.get('title') or '') + " " + (ref.get('abstract') or '')).lower()
        if any(kw.lower() in text for kw in keywords):
            theme_refs.append(ref)
    return theme_refs


def extract_key_points_llm_discussion(theme_refs, theme_name, cancer_type, our_findings):
    """
    Extract key points for Discussion theme using LLM (comparative).

    Args:
        theme_refs: List of references for this theme
        theme_name: Theme name
        cancer_type: Cancer type
        our_findings: Summary of our findings

    Returns:
        list: List of key point dictionaries
    """
    if not theme_refs:
        return []

    abstracts_text = "\n\n".join([
        f"[PMID:{ref.get('pmid') or ''}] {ref.get('title') or ''}\n{(ref.get('abstract') or '')[:500]}"
        for ref in theme_refs[:10]
    ])

    prompt = f"""You are summarizing literature for the "{theme_name}" section of a Discussion.

Our study findings:
{our_findings}

Literature abstracts:
{abstracts_text}

Extract 2-4 key points that:
1. Help interpret or contextualize our findings
2. Show consistency or contrast with our results
3. Support our methodological approach
4. Are directly writable into Discussion

Output ONLY a JSON array:
[
  {{
    "point": "Statement that relates our findings to literature",
    "supporting_pmids": ["12345678"]
  }}
]

IMPORTANT: Focus on PATTERNS and METHODS, not individual genes.
Do NOT enumerate gene functions one by one.
"""

    try:
        key_points = call_json(prompt)

        if isinstance(key_points, list):
            for kp in key_points:
                if "point" not in kp or "supporting_pmids" not in kp:
                    print(f"  ⚠️  Invalid key point format for {theme_name}", file=sys.stderr)
                    return []
            return key_points
        else:
            print(f"  ⚠️  Expected list, got {type(key_points)} for {theme_name}", file=sys.stderr)
            return []

    except Exception as e:
        print(f"  ⚠️  Failed to extract key points for {theme_name}: {e}", file=sys.stderr)
        return []


def extract_key_points_rules_discussion(theme_refs, theme_name):
    """
    Extract key points using simple rules (fallback).

    Args:
        theme_refs: List of references for this theme
        theme_name: Theme name

    Returns:
        list: List of key point dictionaries
    """
    key_points = []

    for ref in theme_refs[:2]:
        abstract = ref.get('abstract') or ''
        if abstract:
            first_sentence = abstract.split('.')[0] + '.'
            key_points.append({
                'point': first_sentence,
                'supporting_pmids': [ref.get('pmid') or '']
            })

    return key_points


def generate_lit_summary_discussion(selected_refs, cancer_type, results_summary):
    """
    Generate comparative literature summary for Discussion.

    Args:
        selected_refs: List of selected references
        cancer_type: Cancer type string
        results_summary: Results summary dictionary

    Returns:
        dict: Literature summary with themes and key points
    """
    print("\n" + "=" * 60)
    print("LITERATURE SUMMARY GENERATION (DISCUSSION)")
    print("=" * 60)

    if LLM_AVAILABLE:
        print("✓ Using LLM-driven comparative summarization")
    else:
        print("ℹ️  Using rule-based summarization (LLM not available)")

    # Summarize our findings
    num_genes = results_summary.get('num_significant_genes', 5)
    method = results_summary.get('method', 'DEG-based Cox regression')
    our_findings = f"""- Identified {num_genes} prognostic genes
- Used {method} workflow
- Genes show diverse hazard ratios (risk and protective)"""

    # Fixed theme structure for Discussion
    themes = [
        {
            'theme_id': 'result_interpretation',
            'theme_name': 'Main Findings Interpretation',
            'keywords': ['multi-gene', 'signature', 'prognostic', 'heterogeneity']
        },
        {
            'theme_id': 'result_consistency',
            'theme_name': 'Consistency with Literature',
            'keywords': ['consistent', 'similar', 'align', 'previous', 'reported']
        },
        {
            'theme_id': 'method_validation',
            'theme_name': 'Methodological Support',
            'keywords': ['DEG', 'Cox', 'regression', 'screening', 'workflow', 'approach']
        },
        {
            'theme_id': 'limitations',
            'theme_name': 'Limitations',
            'keywords': ['limitation', 'validation', 'retrospective', 'cohort']
        }
    ]

    # Assign refs to themes and extract key points
    for theme in themes:
        print(f"\n  Processing theme: {theme['theme_name']}")
        theme_refs = assign_refs_to_theme(selected_refs, theme['keywords'])
        print(f"    Found {len(theme_refs)} relevant references")

        if LLM_AVAILABLE:
            theme['key_points'] = extract_key_points_llm_discussion(
                theme_refs,
                theme['theme_name'],
                cancer_type,
                our_findings
            )
        else:
            theme['key_points'] = extract_key_points_rules_discussion(
                theme_refs,
                theme['theme_name']
            )

        print(f"    Extracted {len(theme['key_points'])} key points")

        # Remove keywords from output
        del theme['keywords']

    # Count sources
    reused_count = len([r for r in selected_refs if r.get('source') == 'intro_reused'])
    new_count = len(selected_refs) - reused_count

    return {
        'metadata': {
            'total_refs': len(selected_refs),
            'refs_from_introduction': reused_count,
            'refs_newly_searched': new_count,
            'generated_at': datetime.now().isoformat(),
            'method': 'llm' if LLM_AVAILABLE else 'rules'
        },
        'themes': themes
    }


def format_themes_for_prompt_discussion(themes):
    """Format themes for Discussion LLM prompt."""
    lines = []
    for theme in themes:
        lines.append(f"\n## {theme['theme_name']}")
        for kp in theme.get('key_points', []):
            point = kp.get('point') or ''
            pmids_raw = kp.get('supporting_pmids') or []
            pmids_str = "; ".join([f"PMID:{p}" for p in pmids_raw if p])
            citation = f" [{pmids_str}]" if pmids_str else ""
            if point:
                lines.append(f"- {point}{citation}")
    return "\n".join(lines)


def validate_discussion_quality(discussion_text):
    """
    Validate Discussion text quality.

    Args:
        discussion_text: Generated Discussion text

    Returns:
        tuple: (is_valid, issues_list)
    """
    issues = []

    # Check 1: PMID citations (at least 2)
    import re
    pmid_pattern = r'PMID:\d+'
    pmids = re.findall(pmid_pattern, discussion_text)
    if len(pmids) < 2:
        issues.append(f"Insufficient PMID citations: {len(pmids)} found, need at least 2")

    # Check 2: Paragraph count (should be 4)
    paragraphs = [p.strip() for p in discussion_text.split('\n\n') if p.strip()]
    if len(paragraphs) < 4:
        issues.append(f"Insufficient paragraphs: {len(paragraphs)} found, need 4")

    # Check 3: Word count (at least 600)
    word_count = len(discussion_text.split())
    if word_count < 600:
        issues.append(f"Insufficient word count: {word_count} words, need at least 600")

    is_valid = len(issues) == 0

    return is_valid, issues


def _generate_discussion_direct(cancer_type, results_draft_content, abstract_content,
                                 intro_content, refs_list, retry=False):
    """
    Direct Discussion generation without lit_summary themes.
    Used as fallback when literature summary generation fails.
    """
    if not LLM_AVAILABLE:
        return None

    results_text = (results_draft_content or "")[:3000]
    abstract_text = (abstract_content or "")[:1000]
    intro_text = (intro_content or "")[:1000]

    refs_block = ""
    if refs_list:
        lines = [f"[PMID:{r.get('pmid') or ''}] ({r.get('year') or ''}) {r.get('title') or ''}"
                 for r in refs_list[:20] if r.get('pmid')]
        if lines:
            refs_block = "\n\nAvailable references for citation:\n" + "\n".join(lines)

    prompt = f"""Write a Discussion section for a scientific paper about {cancer_type}.

ABSTRACT:
{abstract_text}

INTRODUCTION (excerpt):
{intro_text}

RESULTS:
{results_text}{refs_block}

Structure:
Paragraph 1: Frame the study approach and overall outcome — do NOT restate exact numbers from Results/Abstract; write like a Discussion opening, not a Results summary
Paragraph 2: Comparison with existing literature — cite PMIDs from the list above; dense citations; emphasize consistency/comparability; avoid strong biological inferences
Paragraph 3: Methodological strengths — explain why DEG → Cox regression is a reasonable screening strategy; cite methodological papers if available
Paragraph 4: Limitations (a) retrospective public-data analysis, (b) no independent cohort validation, (c) no experimental validation, (d) univariate Cox does not account for clinical confounders; conservative conclusion

Requirements:
1. Formal scientific English
2. Insert PMID citations as [PMID:12345678]
3. Exactly 4 paragraphs, 5-7 sentences each, 900-1200 words total
4. Paragraph 2 must have the highest citation density
5. Gene mention rules: at most 2-3 gene names across the whole Discussion; do NOT enumerate gene functions; do NOT write mechanistic interpretations (e.g. "may reflect aggressive metabolism") unless directly supported by cited evidence
6. Do NOT use "novel", "breakthrough", "therapeutic target", "novel mechanism"
7. Conservative language: "may", "suggest", "warrant further investigation", "candidate"
8. Do NOT use template phrases: "is consistent with previous investigations", "provides a framework", "similar studies have shown"
{"9. CRITICAL: write at least 4 PMID citations and at least 900 words" if retry else ""}

Output ONLY the Discussion text (no title, no section header)."""

    try:
        return call(prompt, max_tokens=2500 if retry else 2000)
    except Exception as e:
        print(f"✗ Direct Discussion generation failed: {e}", file=sys.stderr)
        return None


def generate_discussion_text(lit_summary, cancer_type, results_summary, retry=False,
                              results_draft_content=None, refs_list=None):
    """
    Generate Discussion text based on literature summary.

    Args:
        lit_summary: Literature summary dictionary
        cancer_type: Cancer type string
        results_summary: Results summary dictionary
        retry: Whether this is a retry attempt

    Returns:
        str: Generated Discussion text
    """
    if not retry:
        print("\n" + "=" * 60)
        print("DISCUSSION TEXT GENERATION")
        print("=" * 60)

    if not LLM_AVAILABLE:
        print("✗ LLM not available, cannot generate Discussion text")
        print("  Please use the generated prompt manually with Claude")
        return None

    if retry:
        print("\n  ⚠️  Retrying with stricter requirements...")
    else:
        print("✓ Generating Discussion with LLM...")

    themes_text = format_themes_for_prompt_discussion(lit_summary['themes'])

    # Format results — prefer real results_draft content over placeholder summary
    if results_draft_content:
        results_text = results_draft_content[:3000]  # cap to avoid token overflow
    else:
        num_genes = results_summary.get('num_significant_genes', 5)
        method = results_summary.get('method', 'DEG-based Cox regression')
        dataset = results_summary.get('dataset', 'TCGA')
        results_text = f"""- Identified {num_genes} prognostic genes
- Analysis method: {method}
- Dataset: {dataset}"""

    # Build a compact reference list for the LLM to cite from
    refs_block = ""
    if refs_list:
        lines = []
        for r in refs_list[:20]:
            pmid = r.get('pmid') or ''
            title = r.get('title') or ''
            year = r.get('year') or ''
            if pmid:
                lines.append(f"[PMID:{pmid}] ({year}) {title}")
        if lines:
            refs_block = "\n\nAvailable references for citation:\n" + "\n".join(lines)

    # Base prompt
    base_prompt = f"""Write a Discussion section for a scientific paper with the following structure:

Paragraph 1: Summary and interpretation of main findings
Paragraph 2: Comparison with existing literature (consistency and novelty)
Paragraph 3: Methodological strengths and rationale
Paragraph 4: Limitations and future directions

Cancer type: {cancer_type}

Our study results:
{results_text}

Available literature summary:
{themes_text}{refs_block}

Requirements:
1. Use formal scientific writing style
2. Insert PMID citations in format [PMID:12345678] or [PMID:12345678; PMID:23456789]
3. Each paragraph should be 5-7 sentences
4. Total length: 900-1200 words, exactly 4 paragraphs
5. Paragraph 1: frame the study approach and overall outcome — do NOT restate exact numbers from Results/Abstract; do NOT paraphrase the Abstract; write like a Discussion opening
6. Paragraph 2: dense citations (comparison with literature); emphasize consistency/comparability; avoid strong biological inferences beyond what cited papers support
7. Paragraph 3: cite methodological papers; explain why DEG → Cox regression is a reasonable screening strategy
8. Paragraph 4: sparse citations; must include all four limitations: (a) retrospective public-data analysis, (b) no independent cohort validation, (c) no experimental validation, (d) univariate Cox does not account for clinical confounders
9. Gene mention rules: mention at most 2-3 genes by name across the whole Discussion; do NOT enumerate gene functions one by one; do NOT write mechanistic interpretations (e.g. "may reflect aggressive metabolism") unless directly supported by cited evidence; focus on patterns and screening outcomes
10. Do NOT use "novel", "breakthrough", "therapeutic target", "novel mechanism"
11. Use conservative language: "may", "suggest", "warrant further investigation", "candidate"
12. Do NOT use template phrases: "is consistent with previous investigations", "provides a framework", "similar studies have shown"
"""

    # Add stricter requirements for retry
    if retry:
        base_prompt += """

CRITICAL REQUIREMENTS (you failed these in the previous attempt):
- You MUST insert at least 4 PMID citations throughout the text
- You MUST write exactly 4 paragraphs separated by blank lines
- You MUST write at least 900 words (do NOT compress excessively)
- Each paragraph should be substantive (6-8 sentences, not 3-4)
- Use the supporting PMIDs from the literature summary above
- Do NOT write a brief overview - write a full, detailed Discussion
"""

    base_prompt += "\nOutput ONLY the Discussion text (no title, no section header)."

    try:
        discussion_text = call(base_prompt, max_tokens=2500 if retry else 2000)

        if not retry:
            print("✓ Discussion text generated successfully")
        else:
            print("  ✓ Retry generation completed")

        return discussion_text
    except Exception as e:
        print(f"✗ Failed to generate Discussion text: {e}", file=sys.stderr)
        return None


def generate_prompt(project_path, manifest):
    """Generate discussion_prompt.txt."""
    project_name = manifest["project_name"]
    detected_route = manifest["detected_route"]

    # Build file reading order
    file_list = [
        f"1. {project_path}/project.yaml",
        f"2. {manifest['input_files']['storyline_path']}"
    ]

    file_index = 3

    # Add project_brief_resolved.json if it exists
    has_project_brief = "project_brief_resolved_path" in manifest
    if has_project_brief:
        file_list.append(f"{file_index}. {manifest['project_brief_resolved_path']}")
        file_index += 1

    # Add abstract, results, introduction
    file_list.extend([
        f"{file_index}. {manifest['input_files']['abstract_draft_path']}",
        f"{file_index + 1}. {manifest['input_files']['results_draft_path']}",
        f"{file_index + 2}. {manifest['input_files']['introduction_draft_path']}"
    ])
    file_index += 3

    # Add title_candidates.md if it exists
    has_title_candidates = "title_candidates_path" in manifest
    if has_title_candidates:
        file_list.append(f"{file_index}. {manifest['title_candidates_path']}")
        file_index += 1

    # Add prompt template last
    file_list.append(f"{file_index}. {manifest['prompts']['discussion_writer']}")

    prompt = f"""请按以下顺序读取文件：

{chr(10).join(file_list)}

然后写一份 SCI 风格的 Discussion 初稿，要求：
1. 用英文
2. 用 markdown 输出
3. 基于现有 storyline、abstract、results 和 introduction 写作
4. 结构：
   - 第一段：概述主要发现（不要机械重复 Results 或 Abstract 的句式和数字，写成 Discussion 的 opening paragraph）
   - 第二段：结合已有研究解释结果意义（必须明确体现 DEG → Cox regression 的分析路径，不要只写空泛的 "consistent with previous studies"）
   - 第三段：方法路径和结果的潜在价值（具体解释为什么 DEG → survival analysis 是合理的候选预后基因发现策略，不要只说 "future validation"）
   - 第四段：局限性与总结
5. 不要夸张
6. 不要写机制化硬结论
7. 不要写 "novel mechanism"、"breakthrough"、"therapeutic target"、"clinical application" 等高风险表达
8. 避免使用 "novel"、"innovative"、"significant advance" 等词
9. 风格适合生物信息学/转录组生物标志物研究
10. 不要编造文献引用（如需要可用 [ref] 占位）
11. 强调"候选"、"warrant further investigation"、"potential"、"may suggest"
12. 语气保守、客观、正式
13. 第四段必须包含三个具体局限性：
    - retrospective public-data-based analysis
    - lack of independent cohort validation
    - lack of experimental validation
14. 减少模板化表达，避免：
    - "is consistent with previous investigations"
    - "provides a framework"
    - "providing a foundation for future validation studies"
    - 其他空泛的 generic discussion phrases
15. Discussion 长度：4 段，简洁聚焦
16. 基于项目的 detected_route: {detected_route}
"""

    # Add project_brief_resolved.json specific requirements if it exists
    if has_project_brief:
        prompt += """16. 如果 project_brief_resolved.json 中有 avoid_overstatement，Discussion 不得违反这些限制
17. 如果 project_brief_resolved.json 中有 preferred_emphasis，Discussion 应体现这些重点
"""

    # Add title alignment requirement if title exists
    if has_title_candidates:
        next_num = 18 if has_project_brief else 16
        prompt += f"""{next_num}. Discussion 的总结应与 title_candidates.md 中的标题保持一致
"""

    prompt += f"""
保存到：
{project_path}/discussion_draft.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Discussion writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_discussion.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate discussion_manifest.json
  3. Generate discussion_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Discussion Writing Preparation")
    print("=" * 60)
    print(f"Project: {project_path}")
    print(f"Prompts: {prompts_dir}")

    # Check prerequisites
    errors = check_prerequisites(project_path, prompts_dir)

    if errors:
        print("\n" + "=" * 60)
        print("PREREQUISITE CHECK FAILED")
        print("=" * 60)
        print("\nMissing files:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease ensure you have generated:")
        print("  - abstract_draft.md (using write_abstract.py)")
        print("  - results_draft.md (using write_results.py)")
        print("  - introduction_draft.md (using write_introduction.py)")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # NEW: Phase - Literature Reuse and Summary
    refs_selected_path = None
    refs_selected_data = None
    lit_summary_path = None
    lit_summary_data = None

    # PRIORITY 1: Check for shared PubMed search results (from search_pubmed.py --purpose discussion)
    pubmed_results_discussion = project_path / "pubmed_results_discussion.json"
    pubmed_refs_brief_discussion = project_path / "pubmed_refs_brief_discussion.md"

    if pubmed_results_discussion.exists():
        print("\n" + "=" * 60)
        print("USING SHARED PUBMED SEARCH RESULTS")
        print("=" * 60)
        print(f"✓ Found: {pubmed_results_discussion}")
        print(f"✓ Found: {pubmed_refs_brief_discussion}")

        try:
            # Load shared PubMed results
            with open(pubmed_results_discussion, 'r', encoding='utf-8') as f:
                pubmed_data = json.load(f)

            articles = pubmed_data.get('articles', [])
            print(f"✓ Loaded {len(articles)} articles from shared search")

            # Convert to refs format
            reused_refs = []
            for article in articles:
                reused_refs.append({
                    'pmid': article.get('pmid', ''),
                    'title': article.get('title', ''),
                    'abstract': article.get('abstract', ''),
                    'journal': article.get('journal', ''),
                    'year': article.get('year', ''),
                    'doi': article.get('doi', ''),
                    'source': 'shared_search'
                })

            # Build discussion_refs_selected.json
            refs_selected_data = {
                'metadata': {
                    'total_refs': len(reused_refs),
                    'source': 'shared_pubmed_search',
                    'search_date': pubmed_data.get('query_date', datetime.now().isoformat())
                },
                'references': reused_refs
            }

            refs_selected_path = project_path / "discussion_refs_selected.json"
            with open(refs_selected_path, 'w', encoding='utf-8') as f:
                json.dump(refs_selected_data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved: {refs_selected_path}")

        except Exception as e:
            print(f"✗ Failed to load shared PubMed results: {e}")
            print("  Falling back to Introduction reuse...")
            pubmed_results_discussion = None  # Trigger fallback

    # FALLBACK: Try to reuse Introduction references
    _discussion_pubmed_missing = (pubmed_results_discussion is None or
                                   not Path(pubmed_results_discussion).exists())
    if _discussion_pubmed_missing or refs_selected_data is None:
        intro_refs_path = project_path / "introduction_refs_selected.json"
        if intro_refs_path.exists():
            print("\n" + "=" * 60)
            print("LITERATURE REUSE AND SUMMARY (FALLBACK)")
            print("=" * 60)

            try:
                # Load Introduction references
                with open(intro_refs_path, 'r', encoding='utf-8') as f:
                    intro_refs_data = json.load(f)

                # Filter reusable references
                reused_refs = filter_reusable_intro_refs(intro_refs_data)
                print(f"✓ Reused {len(reused_refs)} references from Introduction")

                # Supplement if insufficient
                if len(reused_refs) < 5:
                    print(f"\n  ⚠️  Only {len(reused_refs)} reusable references, supplementing...")
                    cancer_type = "cancer"
                    project_brief_path = project_path / "project_brief_resolved.json"
                    if project_brief_path.exists():
                        with open(project_brief_path, 'r', encoding='utf-8') as f:
                            project_context = json.load(f)
                            cancer_type = project_context.get('disease', {}).get('name', 'cancer')

                    new_refs = supplement_discussion_refs(cancer_type)
                    reused_refs.extend(new_refs)
                    print(f"  ✓ Added {len(new_refs)} supplementary references")
                    print(f"  Total: {len(reused_refs)} references")

                # Build discussion_refs_selected.json
                refs_selected_data = {
                    'metadata': {
                        'total_refs': len(reused_refs),
                        'reused_from_intro': len([r for r in reused_refs if r.get('source') == 'intro_reused']),
                        'newly_searched': len([r for r in reused_refs if r.get('source') == 'discussion_new']),
                        'search_date': datetime.now().isoformat()
                    },
                    'references': reused_refs
                }

                refs_selected_path = project_path / "discussion_refs_selected.json"
                with open(refs_selected_path, 'w', encoding='utf-8') as f:
                    json.dump(refs_selected_data, f, indent=2, ensure_ascii=False)

                print(f"✓ Saved: {refs_selected_path}")

            except Exception as e:
                print(f"✗ Literature processing failed: {e}")
                print("  Continuing without literature summary...")
                refs_selected_data = None

    # Continue with literature summary generation if we have refs
    if refs_selected_data and refs_selected_data.get('references'):
        try:
            # Get cancer type
            cancer_type = "cancer"
            project_brief_path = project_path / "project_brief_resolved.json"
            if project_brief_path.exists():
                with open(project_brief_path, 'r', encoding='utf-8') as f:
                    project_context = json.load(f)
                    cancer_type = project_context.get('disease', {}).get('name', 'cancer')

            # Build results_summary from available data
            results_summary = {
                'num_significant_genes': 5,
                'method': 'DEG-based Cox regression',
                'dataset': 'TCGA'
            }

            # Generate literature summary
            lit_summary_data = generate_lit_summary_discussion(
                refs_selected_data['references'],
                cancer_type,
                results_summary
            )

            lit_summary_path = project_path / "discussion_lit_summary.json"
            with open(lit_summary_path, 'w', encoding='utf-8') as f:
                json.dump(lit_summary_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Literature summary saved to: {lit_summary_path}")
            print(f"  - {len(lit_summary_data['themes'])} themes")
            print(f"  - Method: {lit_summary_data['metadata']['method']}")

        except Exception as e:
            print(f"✗ Literature summary generation failed: {e}")
            print("  Continuing without literature summary...")
            lit_summary_data = None

    # NEW: Phase - Discussion Text Generation
    discussion_draft_path = project_path / "discussion_draft.md"

    if LLM_AVAILABLE:
        try:
            # Get cancer type
            cancer_type = "cancer"
            project_brief_path = project_path / "project_brief_resolved.json"
            if project_brief_path.exists():
                with open(project_brief_path, 'r', encoding='utf-8') as f:
                    project_context = json.load(f)
                    cancer_type = project_context.get('disease', {}).get('name', 'cancer')

            # Read section drafts
            def _read(p):
                return p.read_text(encoding='utf-8') if p.exists() else None

            results_draft_content = _read(project_path / "results_draft.md")
            abstract_draft_content = _read(project_path / "abstract_draft.md")
            intro_draft_content = _read(project_path / "introduction_draft.md")

            results_summary = {
                'num_significant_genes': 5,
                'method': 'DEG-based Cox regression',
                'dataset': 'TCGA'
            }
            refs_list = refs_selected_data.get('references', []) if refs_selected_data else []

            if lit_summary_data:
                discussion_text = generate_discussion_text(
                    lit_summary_data,
                    cancer_type,
                    results_summary,
                    results_draft_content=results_draft_content,
                    refs_list=refs_list
                )
            else:
                # Fallback: direct inline prompt without lit_summary themes
                print("\n" + "=" * 60)
                print("DISCUSSION TEXT GENERATION (direct fallback)")
                print("=" * 60)
                discussion_text = _generate_discussion_direct(
                    cancer_type,
                    results_draft_content,
                    abstract_draft_content,
                    intro_draft_content,
                    refs_list
                )

            if discussion_text:
                is_valid, issues = validate_discussion_quality(discussion_text)
                if not is_valid:
                    print("\n⚠️  Quality check failed:")
                    for issue in issues:
                        print(f"    - {issue}")
                    # Retry once
                    if lit_summary_data:
                        discussion_text = generate_discussion_text(
                            lit_summary_data, cancer_type, results_summary,
                            retry=True,
                            results_draft_content=results_draft_content,
                            refs_list=refs_list
                        )
                    else:
                        discussion_text = _generate_discussion_direct(
                            cancer_type, results_draft_content,
                            abstract_draft_content, intro_draft_content,
                            refs_list, retry=True
                        )
                    if discussion_text:
                        is_valid, issues = validate_discussion_quality(discussion_text)
                        if not is_valid:
                            print("\n⚠️  Quality check still failed after retry — keeping output anyway")
                        else:
                            print("\n✓ Quality check passed after retry")
                else:
                    print("\n✓ Quality check passed")

                with open(discussion_draft_path, 'w', encoding='utf-8') as f:
                    f.write(discussion_text)
                print(f"\n✓ Discussion draft saved to: {discussion_draft_path}")
                print(f"  - Length: {len(discussion_text.split())} words")

        except Exception as e:
            print(f"\n✗ Discussion text generation failed: {e}")
            print("  discussion_prompt.txt is available for manual use")

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)

    manifest = generate_manifest(project_path, prompts_dir)
    manifest_path = project_path / "discussion_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Route: {manifest['detected_route']}")
    print(f"  - Input files: {len(manifest['input_files'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "discussion_prompt.txt"

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n✓ Generated: {prompt_path}")

    # Success summary
    print("\n" + "=" * 60)
    print("PREPARATION COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("\nGenerated files:")
    file_count = 1
    print(f"  {file_count}. {manifest_path}")
    file_count += 1
    print(f"  {file_count}. {prompt_path}")
    file_count += 1

    if refs_selected_path:
        print(f"  {file_count}. {refs_selected_path}")
        file_count += 1

    if lit_summary_path:
        print(f"  {file_count}. {lit_summary_path}")
        file_count += 1

    if discussion_draft_path.exists():
        print(f"  {file_count}. {discussion_draft_path}")
        file_count += 1

    print("\nNext steps:")
    if discussion_draft_path.exists() and LLM_AVAILABLE:
        print(f"  ✓ Discussion draft already generated: {discussion_draft_path}")
        print(f"  1. Review the draft: cat {discussion_draft_path}")
        print(f"  2. Check PMID citations are correctly inserted")
        if lit_summary_path:
            print(f"  3. Review literature summary: cat {lit_summary_path}")
    else:
        print(f"  1. Review the prompt: cat {prompt_path}")
        print(f"  2. Copy the prompt content and send it to Claude Code")
        print(f"  3. Claude will generate: {project_path}/discussion_draft.md")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
