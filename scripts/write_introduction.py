#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime


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

    print("\nNext steps:")
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

