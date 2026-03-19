#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
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

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")
    if not check_file_exists(abstract_draft, "abstract_draft.md"):
        errors.append(f"Missing: {abstract_draft}")
    if not check_file_exists(results_draft, "results_draft.md"):
        errors.append(f"Missing: {results_draft}")

    # Check optional files
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

    title_candidates = project_path / "title_candidates.md"
    if title_candidates.exists():
        check_file_exists(title_candidates, "title_candidates.md (optional)")

    # Check prompt template
    print("\nChecking prompt template...")
    introduction_writer = prompts_dir / "introduction_writer.md"

    if not check_file_exists(introduction_writer, "introduction_writer.md"):
        errors.append(f"Missing: {introduction_writer}")

    return errors


def calculate_relevance_score(article, disease, study_focus):
    """Calculate relevance score for an article."""
    score = 0.0
    title_lower = article.get('title', '').lower()
    abstract_lower = article.get('abstract', '').lower() if article.get('abstract') else ''

    # Disease relevance (weight 0.3)
    if disease.lower() in title_lower:
        score += 0.3
    elif disease.lower() in abstract_lower:
        score += 0.15

    # Method keywords (weight 0.3)
    method_keywords = [
        'differential expression', 'differentially expressed',
        'cox regression', 'survival analysis',
        'prognostic', 'prognosis', 'biomarker',
        'transcriptome', 'gene expression'
    ]
    matched_methods = sum(1 for kw in method_keywords if kw in abstract_lower)
    score += min(matched_methods * 0.05, 0.3)

    # Recency (weight 0.2)
    try:
        year = int(article.get('year', 0))
        if year >= 2023:
            score += 0.2
        elif year >= 2020:
            score += 0.15
        elif year >= 2018:
            score += 0.1
    except:
        pass

    # Study focus alignment (weight 0.2)
    if study_focus and study_focus.lower() in abstract_lower:
        score += 0.2

    return min(score, 1.0)


def assign_tags(article, disease, study_focus):
    """Assign tags to an article based on content."""
    tags = []
    title_lower = article.get('title', '').lower()
    abstract_lower = article.get('abstract', '').lower() if article.get('abstract') else ''

    # Disease background
    if disease.lower() in title_lower or disease.lower() in abstract_lower:
        tags.append('disease_background')

    # Prognostic biomarker
    biomarker_keywords = ['prognostic', 'prognosis', 'biomarker', 'survival', 'predictor']
    if any(kw in title_lower or kw in abstract_lower for kw in biomarker_keywords):
        tags.append('prognostic_biomarker')

    # Transcriptome
    transcriptome_keywords = ['transcriptome', 'gene expression', 'rna-seq',
                              'differential expression', 'differentially expressed']
    if any(kw in title_lower or kw in abstract_lower for kw in transcriptome_keywords):
        tags.append('transcriptome')

    # Survival analysis
    survival_keywords = ['cox regression', 'survival analysis', 'kaplan-meier',
                        'hazard ratio', 'overall survival']
    if any(kw in title_lower or kw in abstract_lower for kw in survival_keywords):
        tags.append('survival_analysis')

    # Research gap support (cautious)
    gap_keywords = ['systematic screening', 'comprehensive analysis',
                   'integrative approach', 'systematic identification']
    if any(kw in abstract_lower for kw in gap_keywords):
        tags.append('research_gap_support')

    return tags


def generate_selection_reason(article, tags, score):
    """Generate a human-readable selection reason."""
    title = article.get('title', '')
    reasons = []

    if 'disease_background' in tags:
        reasons.append('disease relevance')
    if 'prognostic_biomarker' in tags:
        reasons.append('prognostic biomarker focus')
    if 'transcriptome' in tags:
        reasons.append('transcriptome methods')
    if 'survival_analysis' in tags:
        reasons.append('survival analysis')

    if score >= 0.8:
        prefix = 'Highly relevant'
    elif score >= 0.6:
        prefix = 'Relevant'
    else:
        prefix = 'Moderately relevant'

    return f"{prefix}: {', '.join(reasons)}" if reasons else f"{prefix} article"


def select_references(pubmed_results_path, project_brief_path):
    """Select relevant references from PubMed results."""
    # Load PubMed results
    with open(pubmed_results_path, 'r', encoding='utf-8') as f:
        pubmed_data = json.load(f)

    # Load project context
    project_context = {}
    if project_brief_path.exists():
        with open(project_brief_path, 'r', encoding='utf-8') as f:
            project_context = json.load(f)

    disease = project_context.get('disease', {}).get('name', 'cancer')
    study_focus = project_context.get('study_focus', {}).get('main_theme', '')

    articles = pubmed_data.get('articles', [])

    # Score and tag each article
    scored_articles = []
    for article in articles:
        score = calculate_relevance_score(article, disease, study_focus)
        tags = assign_tags(article, disease, study_focus)
        reason = generate_selection_reason(article, tags, score)

        scored_articles.append({
            'article': article,
            'score': score,
            'tags': tags,
            'reason': reason
        })

    # Sort by score and select top articles
    scored_articles.sort(key=lambda x: x['score'], reverse=True)
    top_n = min(10, len(scored_articles))
    selected = scored_articles[:top_n]

    # Build output
    result = {
        'selection_date': datetime.now().strftime('%Y-%m-%d'),
        'source_file': str(pubmed_results_path),
        'total_available': len(articles),
        'total_selected': len(selected),
        'selection_criteria': {
            'disease_relevance': True,
            'biomarker_focus': True,
            'transcriptome_methods': True,
            'survival_analysis': True,
            'recency_weight': 'prefer_recent_5_years'
        },
        'selected_refs': [
            {
                'pmid': s['article'].get('pmid', ''),
                'title': s['article'].get('title', ''),
                'journal': s['article'].get('journal', ''),
                'year': s['article'].get('year', ''),
                'doi': s['article'].get('doi', ''),
                'abstract': s['article'].get('abstract', ''),
                'selection_reason': s['reason'],
                'relevance_score': round(s['score'], 2),
                'tags': s['tags']
            }
            for s in selected
        ]
    }

    return result


def generate_claims_map(project_context, selected_refs):
    """Generate claims mapping based on selected references."""
    disease = project_context.get('disease', {}).get('name', 'cancer')
    study_focus = project_context.get('study_focus', {}).get('main_theme', 'biomarker screening')
    project_name = project_context.get('project_name', '')
    detected_route = project_context.get('detected_route', 'unknown')

    claims = []

    # Claim 1: Disease background
    disease_bg_refs = [r for r in selected_refs if 'disease_background' in r['tags']]
    claims.append({
        'claim_id': 'intro_bg_01',
        'claim_type': 'disease_background',
        'claim_requirement': f'Establish clinical significance of {disease}, including morbidity/mortality burden',
        'paragraph_position': 1,
        'supporting_pmids': [r['pmid'] for r in disease_bg_refs[:2]],
        'support_type': 'direct',
        'rationale': f'Papers explicitly discuss {disease} clinical burden',
        'confidence': 'high' if len(disease_bg_refs) >= 2 else 'medium'
    })

    # Claim 2: Research status (prognostic biomarker)
    biomarker_refs = [r for r in selected_refs if 'prognostic_biomarker' in r['tags']]
    claims.append({
        'claim_id': 'intro_bg_02',
        'claim_type': 'research_status',
        'claim_requirement': f'Describe existing transcriptomic/biomarker research in {disease}, focusing on prognostic approaches',
        'paragraph_position': 2,
        'supporting_pmids': [r['pmid'] for r in biomarker_refs[:3]],
        'support_type': 'direct',
        'rationale': 'Papers demonstrate prognostic biomarker identification using transcriptome/Cox regression',
        'confidence': 'high' if len(biomarker_refs) >= 2 else 'medium'
    })

    # Claim 3: Research gap (cautious - only if sufficient evidence)
    gap_refs = [r for r in selected_refs if 'research_gap_support' in r['tags']]
    if len(gap_refs) >= 2:
        claims.append({
            'claim_id': 'intro_gap_01',
            'claim_type': 'research_gap',
            'claim_requirement': 'If supported by literature, mention that systematic DEG-based prognostic screening remains valuable. If insufficient support, weaken or omit this claim.',
            'paragraph_position': 2,
            'supporting_pmids': [r['pmid'] for r in gap_refs[:2]],
            'support_type': 'indirect',
            'rationale': 'Papers show value of systematic screening but don\'t explicitly state a gap. Use cautious language.',
            'confidence': 'medium'
        })

    # Claim 4: Study objective (self-description)
    claims.append({
        'claim_id': 'intro_method_01',
        'claim_type': 'study_objective',
        'claim_requirement': 'State study objective: identify prognostic biomarkers via DEG analysis + Cox regression',
        'paragraph_position': 3,
        'supporting_pmids': [],
        'support_type': 'self_description',
        'rationale': 'Describes our own study design, no external citation needed',
        'confidence': 'n/a'
    })

    # Build result
    result = {
        'map_date': datetime.now().strftime('%Y-%m-%d'),
        'project_name': project_name,
        'disease': disease,
        'study_type': detected_route,
        'claims': claims,
        'coverage_summary': {
            'total_claims': len(claims),
            'claims_with_literature_support': len([c for c in claims if c['supporting_pmids']]),
            'claims_self_description': len([c for c in claims if c['support_type'] == 'self_description']),
            'unique_pmids_used': len(set(pmid for c in claims for pmid in c['supporting_pmids']))
        }
    }

    return result


# ============================================================================
# NEW: Deep Literature Summary Functions (LLM-driven)
# ============================================================================

def assign_refs_to_theme(refs, keywords):
    """
    Assign references to a theme based on keywords.

    Args:
        refs: List of references
        keywords: List of keyword strings

    Returns:
        list: References matching the theme
    """
    theme_refs = []
    for ref in refs:
        text = (ref.get('title', '') + " " + ref.get('abstract', '')).lower()
        if any(kw.lower() in text for kw in keywords):
            theme_refs.append(ref)
    return theme_refs


def extract_key_points_llm(theme_refs, theme_name, cancer_type):
    """
    Extract key points from theme references using LLM.

    Args:
        theme_refs: List of references for this theme
        theme_name: Theme name
        cancer_type: Cancer type

    Returns:
        list: List of key point dictionaries
    """
    if not theme_refs:
        return []

    # Build abstracts text (max 10 refs)
    abstracts_text = "\n\n".join([
        f"[PMID:{ref['pmid']}] {ref['title']}\n{ref.get('abstract', 'No abstract')[:500]}"
        for ref in theme_refs[:10]
    ])

    prompt = f"""You are summarizing scientific literature for the "{theme_name}" section of a research paper about {cancer_type}.

Given the following paper abstracts, extract 2-4 key points that:
1. Are directly writable into an Introduction section
2. Represent important facts or consensus findings
3. Are supported by the provided papers

Abstracts:
{abstracts_text}

Output ONLY a JSON array (no markdown, no explanation):
[
  {{
    "point": "Clear, one-sentence statement suitable for Introduction",
    "supporting_pmids": ["12345678", "23456789"]
  }}
]

Requirements:
- Each point should be a complete, factual statement
- Use formal scientific language
- Include 1-3 PMIDs per point
- Output 2-4 points maximum
"""

    try:
        key_points = call_json(prompt)

        # Validate format
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


def extract_key_points_rules(theme_refs, theme_name):
    """
    Extract key points using simple rules (fallback when LLM not available).

    Args:
        theme_refs: List of references for this theme
        theme_name: Theme name

    Returns:
        list: List of key point dictionaries
    """
    key_points = []

    for ref in theme_refs[:3]:
        abstract = ref.get('abstract', '')
        if abstract:
            # Extract first sentence as key point
            first_sentence = abstract.split('.')[0] + '.'
            key_points.append({
                'point': first_sentence,
                'supporting_pmids': [ref['pmid']]
            })

    return key_points


def generate_lit_summary(selected_refs, cancer_type):
    """
    Generate thematic literature summary.

    Args:
        selected_refs: List of selected references
        cancer_type: Cancer type string

    Returns:
        dict: Literature summary with themes and key points
    """
    print("\n" + "=" * 60)
    print("LITERATURE SUMMARY GENERATION")
    print("=" * 60)

    if LLM_AVAILABLE:
        print("✓ Using LLM-driven deep summarization")
    else:
        print("ℹ️  Using rule-based summarization (LLM not available)")

    # Fixed theme structure for Introduction
    themes = [
        {
            'theme_id': 'disease_burden',
            'theme_name': 'Disease Burden and Clinical Challenge',
            'keywords': ['mortality', 'incidence', 'survival', 'burden', 'challenge', 'epidemiology']
        },
        {
            'theme_id': 'existing_biomarkers',
            'theme_name': 'Current Prognostic Biomarkers',
            'keywords': ['biomarker', 'TNM', 'staging', 'molecular', 'EGFR', 'ALK', 'prognostic']
        },
        {
            'theme_id': 'transcriptome_approaches',
            'theme_name': 'Transcriptome-Based Studies',
            'keywords': ['transcriptome', 'RNA-seq', 'gene expression', 'differential expression', 'Cox']
        },
        {
            'theme_id': 'research_gap',
            'theme_name': 'Research Gap',
            'keywords': ['gap', 'need', 'lacking', 'limited', 'challenge', 'systematic']
        }
    ]

    # Assign refs to themes and extract key points
    for theme in themes:
        print(f"\n  Processing theme: {theme['theme_name']}")
        theme_refs = assign_refs_to_theme(selected_refs, theme['keywords'])
        print(f"    Found {len(theme_refs)} relevant references")

        if LLM_AVAILABLE:
            theme['key_points'] = extract_key_points_llm(
                theme_refs,
                theme['theme_name'],
                cancer_type
            )
        else:
            theme['key_points'] = extract_key_points_rules(
                theme_refs,
                theme['theme_name']
            )

        print(f"    Extracted {len(theme['key_points'])} key points")

        # Remove keywords from output
        del theme['keywords']

    return {
        'metadata': {
            'total_refs': len(selected_refs),
            'generated_at': datetime.now().isoformat(),
            'cancer_type': cancer_type,
            'method': 'llm' if LLM_AVAILABLE else 'rules'
        },
        'themes': themes
    }


def format_themes_for_prompt(themes):
    """Format themes for LLM prompt."""
    lines = []
    for theme in themes:
        lines.append(f"\n## {theme['theme_name']}")
        for kp in theme['key_points']:
            pmids_str = "; ".join([f"PMID:{p}" for p in kp['supporting_pmids']])
            lines.append(f"- {kp['point']} [{pmids_str}]")
    return "\n".join(lines)


def validate_introduction_quality(intro_text):
    """
    Validate Introduction text quality.

    Args:
        intro_text: Generated Introduction text

    Returns:
        tuple: (is_valid, issues_list)
    """
    issues = []

    # Check 1: PMID citations (at least 3)
    import re
    pmid_pattern = r'PMID:\d+'
    pmids = re.findall(pmid_pattern, intro_text)
    if len(pmids) < 3:
        issues.append(f"Insufficient PMID citations: {len(pmids)} found, need at least 3")

    # Check 2: Paragraph count (should be 4)
    paragraphs = [p.strip() for p in intro_text.split('\n\n') if p.strip()]
    if len(paragraphs) < 4:
        issues.append(f"Insufficient paragraphs: {len(paragraphs)} found, need 4")

    # Check 3: Word count (at least 700)
    word_count = len(intro_text.split())
    if word_count < 700:
        issues.append(f"Insufficient word count: {word_count} words, need at least 700")

    is_valid = len(issues) == 0

    return is_valid, issues


def generate_introduction_text(lit_summary, cancer_type, study_objective, retry=False):
    """
    Generate Introduction text based on literature summary.

    Args:
        lit_summary: Literature summary dictionary
        cancer_type: Cancer type string
        study_objective: Study objective string
        retry: Whether this is a retry attempt

    Returns:
        str: Generated Introduction text
    """
    if not retry:
        print("\n" + "=" * 60)
        print("INTRODUCTION TEXT GENERATION")
        print("=" * 60)

    if not LLM_AVAILABLE:
        print("✗ LLM not available, cannot generate Introduction text")
        print("  Please use the generated prompt manually with Claude")
        return None

    if retry:
        print("\n  ⚠️  Retrying with stricter requirements...")
    else:
        print("✓ Generating Introduction with LLM...")

    themes_text = format_themes_for_prompt(lit_summary['themes'])

    # Base prompt
    base_prompt = f"""Write an Introduction section for a scientific paper with the following structure:

Paragraph 1: Disease burden and clinical challenge
Paragraph 2: Current prognostic biomarkers and their limitations
Paragraph 3: Transcriptome-based approaches for biomarker discovery
Paragraph 4: Research gap and study objectives

Cancer type: {cancer_type}
Study objective: {study_objective}

Available literature summary:
{themes_text}

Requirements:
1. Use formal scientific writing style
2. Insert PMID citations in format [PMID:12345678] or [PMID:12345678; PMID:23456789]
3. Each paragraph should be 4-6 sentences
4. Total length: 800-1000 words
5. End with a clear statement of study objectives
6. Use the key points from the literature summary
7. Ensure logical flow between paragraphs
8. Do NOT use words like "novel", "innovative", "breakthrough"
9. Use conservative language: "may", "suggest", "potential"
10. Focus on "screening", "identification", "association" rather than "mechanism"
"""

    # Add stricter requirements for retry
    if retry:
        base_prompt += """

CRITICAL REQUIREMENTS (you failed these in the previous attempt):
- You MUST insert at least 5 PMID citations throughout the text
- You MUST write exactly 4 paragraphs separated by blank lines
- You MUST write at least 800 words (do NOT compress or summarize excessively)
- Each paragraph should be substantive (5-7 sentences, not 2-3)
- Use the supporting PMIDs from the literature summary above
- Do NOT write a brief overview - write a full, detailed Introduction
"""

    base_prompt += "\nOutput ONLY the Introduction text (no title, no section header)."

    try:
        intro_text = call(base_prompt, max_tokens=2500 if retry else 2000)

        if not retry:
            print("✓ Introduction text generated successfully")
        else:
            print("  ✓ Retry generation completed")

        return intro_text
    except Exception as e:
        print(f"✗ Failed to generate Introduction text: {e}", file=sys.stderr)
        return None


def generate_manifest(project_path, prompts_dir, literature_mode='project_only',
                     refs_selected_path=None, refs_selected_count=0,
                     claims_map_path=None, claims_count=0):
    """Generate introduction_manifest.json."""
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
        "literature_mode": literature_mode,
        "results_order": results_order,
        "main_text_modules": main_text_modules,
        "prompts": {
            "introduction_writer": str(prompts_dir / "introduction_writer.md")
        },
        "input_files": {
            "storyline_path": str(project_path / "storyline.md"),
            "abstract_draft_path": str(project_path / "abstract_draft.md"),
            "results_draft_path": str(project_path / "results_draft.md")
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

    # Add PubMed results paths as top-level fields if they exist
    pubmed_results_path = project_path / "pubmed_results.json"
    if pubmed_results_path.exists():
        manifest["pubmed_results_path"] = str(pubmed_results_path)

    pubmed_refs_brief_path = project_path / "pubmed_refs_brief.md"
    if pubmed_refs_brief_path.exists():
        manifest["pubmed_refs_brief_path"] = str(pubmed_refs_brief_path)

    # Add literature workflow outputs if they exist
    if refs_selected_path:
        manifest["refs_selected_path"] = str(refs_selected_path)
        manifest["refs_selected_count"] = refs_selected_count

    if claims_map_path:
        manifest["claims_map_path"] = str(claims_map_path)
        manifest["claims_count"] = claims_count

    # Add workflow status
    manifest["workflow_status"] = {
        "pubmed_available": pubmed_results_path.exists(),
        "refs_selection_completed": refs_selected_path is not None,
        "claims_mapping_completed": claims_map_path is not None,
        "ready_for_writing": True
    }

    return manifest


def generate_prompt(project_path, manifest):
    """Generate introduction_prompt.txt."""
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

    # Add abstract and results
    file_list.extend([
        f"{file_index}. {manifest['input_files']['abstract_draft_path']}",
        f"{file_index + 1}. {manifest['input_files']['results_draft_path']}"
    ])
    file_index += 2

    # Add title_candidates.md if it exists
    has_title_candidates = "title_candidates_path" in manifest
    if has_title_candidates:
        file_list.append(f"{file_index}. {manifest['title_candidates_path']}")
        file_index += 1

    # Add literature workflow outputs if they exist
    has_refs_selected = "refs_selected_path" in manifest
    if has_refs_selected:
        file_list.append(f"{file_index}. {manifest['refs_selected_path']}")
        file_index += 1

    has_claims_map = "claims_map_path" in manifest
    if has_claims_map:
        file_list.append(f"{file_index}. {manifest['claims_map_path']}")
        file_index += 1

    # Add prompt template last
    file_list.append(f"{file_index}. {manifest['prompts']['introduction_writer']}")

    prompt = f"""请按以下顺序读取文件：

{chr(10).join(file_list)}

然后写一份 SCI 风格的 Introduction 初稿，要求：
1. 用英文
2. 用 markdown 输出
3. 基于现有 storyline、abstract 和 results 写作
4. 结构：
   - 疾病背景（1-2 段）：疾病的临床重要性、当前挑战
   - 研究现状与不足（1-2 段）：现有生物标志物研究、方法局限性、研究空白
   - 本研究目标（1 段）：本研究方法、预期解决的问题
5. 不要夸张
6. 不要写机制化结论
7. 不要写 "novel mechanism"、"breakthrough"、"revolutionary"、"paradigm shift" 等高风险表达
8. 避免使用 "novel"、"innovative" 等词
9. 风格适合生物信息学/转录组生物标志物研究
10. 不要编造文献引用（如需要可用 [ref] 占位）
11. 强调"筛选"、"识别"、"关联"而非"机制发现"
12. 语气保守、客观、正式
13. 引言长度：3-4 段，简洁聚焦
14. 基于项目的 detected_route: {detected_route}
"""

    # Add project_brief_resolved.json specific requirements if it exists
    if has_project_brief:
        prompt += """15. 如果 project_brief_resolved.json 中提供了 disease.name，则引言应明确讨论该疾病
16. 如果 project_brief_resolved.json 中提供了 study_focus.main_theme，则引言应围绕该研究主题展开
17. 如果 manual_notes.avoid_overstatement 中有内容，引言不得违反这些限制
18. 如果 manual_notes.preferred_emphasis 中有内容，引言应体现这些重点
"""

    # Add title alignment requirement if title exists
    if has_title_candidates:
        prompt += """19. 引言的研究目标应与 title_candidates.md 中的标题保持一致
"""

    # Add literature-grounded writing requirements if in pubmed_grounded mode
    literature_mode = manifest.get('literature_mode', 'project_only')
    has_refs_selected = "refs_selected_path" in manifest
    has_claims_map = "claims_map_path" in manifest

    if literature_mode == 'pubmed_grounded' and has_refs_selected and has_claims_map:
        next_num = 20 if has_title_candidates else 19
        prompt += f"""{next_num}. **重要：基于筛选文献和 claims 绑定写作**
   - introduction_refs_selected.json 中包含了筛选后的高相关度文献
   - introduction_claims_map.json 中定义了关键背景陈述与文献的绑定关系
   - 引言的每个关键背景句应尽量对应 claims_map 中的 claim_requirement
   - 对于有 supporting_pmids 的 claim，必须使用 [PMID:xxxxxxxx] 占位符引用
   - 不要编造 PMID、作者、年份、期刊、DOI
   - 不要轻易写具体基因名，除非 selected_refs 中有明确支持
   - 如果某个背景点缺乏文献支撑（supporting_pmids 为空），应弱化表述或省略
   - 优先使用 selected_refs 中 relevance_score 高的文献
   - 对于 confidence 为 medium 或 low 的 claim，使用更谨慎的表述

{next_num + 1}. **引用占位符规则**
   - 使用 [PMID:xxxxxxxx] 作为引用占位符
   - 例如：[PMID:40792153] 或 [PMID:40792153; PMID:40239580]
   - 每个 PMID 必须来自 introduction_refs_selected.json
   - 不要使用 [Ref1], [Ref2] 等序号占位符
   - 在引言末尾附上参考文献列表：

     ## References (Placeholder)
     - PMID:40792153 - Title of the paper
     - PMID:40239580 - Title of another paper
"""

    prompt += f"""
保存到：
{project_path}/introduction_draft.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Introduction writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_introduction.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate introduction_manifest.json
  3. Generate introduction_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Introduction Writing Preparation")
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
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Detect literature mode
    pubmed_results_path = project_path / "pubmed_results.json"
    pubmed_available = pubmed_results_path.exists()

    literature_mode = "pubmed_grounded" if pubmed_available else "project_only"

    print("\n" + "=" * 60)
    print(f"LITERATURE MODE: {literature_mode.upper()}")
    print("=" * 60)

    if literature_mode == "pubmed_grounded":
        print(f"✓ PubMed results detected: {pubmed_results_path}")
    else:
        print("ℹ No PubMed results found, using project-only mode")

    # Phase: Literature selection (if available)
    refs_selected_path = None
    refs_selected_count = 0
    refs_selected_data = None

    if pubmed_available:
        print("\n" + "=" * 60)
        print("LITERATURE SELECTION")
        print("=" * 60)

        try:
            project_brief_path = project_path / "project_brief_resolved.json"
            refs_selected_data = select_references(pubmed_results_path, project_brief_path)

            refs_selected_path = project_path / "introduction_refs_selected.json"
            with open(refs_selected_path, 'w', encoding='utf-8') as f:
                json.dump(refs_selected_data, f, indent=2, ensure_ascii=False)

            refs_selected_count = refs_selected_data['total_selected']
            print(f"✓ Selected {refs_selected_count} references from {refs_selected_data['total_available']}")
            print(f"✓ Saved to: {refs_selected_path}")
        except Exception as e:
            print(f"✗ Literature selection failed: {e}")
            print("  Continuing with project-only mode...")
            literature_mode = "project_only"

    # Phase: Claims mapping (if refs selected)
    claims_map_path = None
    claims_count = 0

    if refs_selected_data:
        print("\n" + "=" * 60)
        print("CLAIMS MAPPING")
        print("=" * 60)

        try:
            # Load project context
            project_context = {}
            project_brief_path = project_path / "project_brief_resolved.json"
            if project_brief_path.exists():
                with open(project_brief_path, 'r', encoding='utf-8') as f:
                    project_context = json.load(f)

            # Load project.yaml for detected_route
            project_yaml_path = project_path / "project.yaml"
            with open(project_yaml_path, 'r', encoding='utf-8') as f:
                project_data = yaml.safe_load(f)
                project_context['project_name'] = project_data.get('project_name', '')
                project_context['detected_route'] = project_data.get('detected_route', 'unknown')

            claims_map_data = generate_claims_map(
                project_context,
                refs_selected_data['selected_refs']
            )

            claims_map_path = project_path / "introduction_claims_map.json"
            with open(claims_map_path, 'w', encoding='utf-8') as f:
                json.dump(claims_map_data, f, indent=2, ensure_ascii=False)

            claims_count = len(claims_map_data['claims'])
            print(f"✓ Generated {claims_count} claims")
            print(f"✓ Claims with literature support: {claims_map_data['coverage_summary']['claims_with_literature_support']}")
            print(f"✓ Unique PMIDs used: {claims_map_data['coverage_summary']['unique_pmids_used']}")
            print(f"✓ Saved to: {claims_map_path}")
        except Exception as e:
            print(f"✗ Claims mapping failed: {e}")
            print("  Continuing without claims mapping...")

    # NEW: Phase: Literature Summary (if refs selected and LLM available)
    lit_summary_path = None
    lit_summary_data = None

    if refs_selected_data:
        try:
            # Get cancer type from project context
            cancer_type = "cancer"
            project_brief_path = project_path / "project_brief_resolved.json"
            if project_brief_path.exists():
                with open(project_brief_path, 'r', encoding='utf-8') as f:
                    project_context = json.load(f)
                    cancer_type = project_context.get('disease', {}).get('name', 'cancer')

            # Generate literature summary
            lit_summary_data = generate_lit_summary(
                refs_selected_data['selected_refs'],
                cancer_type
            )

            lit_summary_path = project_path / "introduction_lit_summary.json"
            with open(lit_summary_path, 'w', encoding='utf-8') as f:
                json.dump(lit_summary_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Literature summary saved to: {lit_summary_path}")
            print(f"  - {len(lit_summary_data['themes'])} themes")
            print(f"  - Method: {lit_summary_data['metadata']['method']}")

        except Exception as e:
            print(f"\n✗ Literature summary generation failed: {e}")
            print("  Continuing without literature summary...")

    # NEW: Phase: Introduction Text Generation (if LLM available and lit_summary exists)
    intro_draft_path = project_path / "introduction_draft.md"

    if lit_summary_data and LLM_AVAILABLE:
        try:
            # Get study objective
            study_objective = "identify prognostic biomarkers via DEG analysis and Cox regression"
            project_brief_path = project_path / "project_brief_resolved.json"
            if project_brief_path.exists():
                with open(project_brief_path, 'r', encoding='utf-8') as f:
                    project_context = json.load(f)
                    study_focus = project_context.get('study_focus', {})
                    if study_focus:
                        study_objective = study_focus.get('main_theme', study_objective)

            # Generate Introduction text
            intro_text = generate_introduction_text(
                lit_summary_data,
                cancer_type,
                study_objective
            )

            if intro_text:
                # Validate quality
                is_valid, issues = validate_introduction_quality(intro_text)

                if not is_valid:
                    print("\n⚠️  Quality check failed:")
                    for issue in issues:
                        print(f"    - {issue}")

                    # Automatic retry once
                    intro_text = generate_introduction_text(
                        lit_summary_data,
                        cancer_type,
                        study_objective,
                        retry=True
                    )

                    if intro_text:
                        # Re-validate after retry
                        is_valid, issues = validate_introduction_quality(intro_text)
                        if not is_valid:
                            print("\n⚠️  Quality check still failed after retry:")
                            for issue in issues:
                                print(f"    - {issue}")
                            print("  Keeping current output anyway...")
                        else:
                            print("\n✓ Quality check passed after retry")
                else:
                    print("\n✓ Quality check passed")

                # Save to file
                with open(intro_draft_path, 'w', encoding='utf-8') as f:
                    f.write(intro_text)

                print(f"\n✓ Introduction draft saved to: {intro_draft_path}")
                print(f"  - Length: {len(intro_text.split())} words")

        except Exception as e:
            print(f"\n✗ Introduction text generation failed: {e}")
            print("  Falling back to prompt generation...")
            lit_summary_data = None  # Force prompt generation

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING MANIFEST AND PROMPT")
    print("=" * 60)

    manifest = generate_manifest(
        project_path,
        prompts_dir,
        literature_mode=literature_mode,
        refs_selected_path=refs_selected_path,
        refs_selected_count=refs_selected_count,
        claims_map_path=claims_map_path,
        claims_count=claims_count
    )
    manifest_path = project_path / "introduction_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Route: {manifest['detected_route']}")
    print(f"  - Literature mode: {manifest['literature_mode']}")
    print(f"  - Input files: {len(manifest['input_files'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "introduction_prompt.txt"

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

    if claims_map_path:
        print(f"  {file_count}. {claims_map_path}")
        file_count += 1

    if lit_summary_path:
        print(f"  {file_count}. {lit_summary_path}")
        file_count += 1

    if intro_draft_path.exists():
        print(f"  {file_count}. {intro_draft_path}")
        file_count += 1

    print("\nNext steps:")
    if intro_draft_path.exists() and LLM_AVAILABLE:
        print(f"  ✓ Introduction draft already generated: {intro_draft_path}")
        print(f"  1. Review the draft: cat {intro_draft_path}")
        print(f"  2. Check PMID citations are correctly inserted")
        if lit_summary_path:
            print(f"  3. Review literature summary: cat {lit_summary_path}")
    else:
        print(f"  1. Review the prompt: cat {prompt_path}")
        print(f"  2. Copy the prompt content and send it to Claude Code")
        print(f"  3. Claude will generate: {project_path}/introduction_draft.md")

    if literature_mode == "pubmed_grounded":
        print("\n📚 Literature-grounded mode active:")
        print(f"  - {refs_selected_count} references selected")
        print(f"  - {claims_count} claims mapped")
        print("  - Introduction will be based on real literature")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()

