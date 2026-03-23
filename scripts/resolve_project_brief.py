#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
from pathlib import Path
from collections import Counter


def load_project_brief_yaml(project_path):
    """Load project_brief.yaml if it exists."""
    yaml_path = project_path / "project_brief.yaml"

    if yaml_path.exists():
        print(f"✓ Found project_brief.yaml: {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        print(f"ℹ No project_brief.yaml found (optional)")
        return {}


def auto_infer_from_files(project_path):
    """Automatically infer project information from existing files."""
    inference = {
        "disease_name": {"value": None, "source": None},
        "disease_abbr": {"value": None, "source": None},
        "main_theme": {"value": None, "source": None},
        "bio_focus": {"value": None, "source": None},
        "disease_candidates": [],
        "theme_candidates": [],
        "method_candidates": [],
        "bio_focus_candidates": [],
        "modules": [],
        "high_freq_terms": []
    }

    print("\n" + "=" * 60)
    print("AUTO-INFERENCE FROM PROJECT FILES")
    print("=" * 60)

    # 1. Read project.yaml
    project_yaml_path = project_path / "project.yaml"
    if project_yaml_path.exists():
        print(f"✓ Found project.yaml")
        with open(project_yaml_path, "r", encoding="utf-8") as f:
            project_data = yaml.safe_load(f)
            inference["project_name"] = project_data.get("project_name", "unknown")
            inference["detected_route"] = project_data.get("detected_route", "")

            # Extract disease info from project.yaml (if exists)
            disease_info = project_data.get("disease", {})
            if disease_info:
                disease_name_yaml = disease_info.get("name")
                disease_abbr_yaml = disease_info.get("abbreviation")

                if disease_name_yaml and not inference["disease_name"]["value"]:
                    inference["disease_name"]["value"] = disease_name_yaml
                    inference["disease_name"]["source"] = "AUTO_PROJECT_YAML"
                    inference["disease_candidates"].append(disease_name_yaml)
                    print(f"  → Extracted disease.name from project.yaml: {disease_name_yaml}")

                if disease_abbr_yaml and not inference["disease_abbr"]["value"]:
                    inference["disease_abbr"]["value"] = disease_abbr_yaml
                    inference["disease_abbr"]["source"] = "AUTO_PROJECT_YAML"
                    print(f"  → Extracted disease.abbreviation from project.yaml: {disease_abbr_yaml}")
            else:
                print(f"  ℹ project.yaml does not contain 'disease' field (this is normal)")

            # Extract biological focus from project.yaml (if exists)
            study_focus_info = project_data.get("study_focus", {})
            if study_focus_info:
                bio_focus_yaml = study_focus_info.get("biological_focus")
                if bio_focus_yaml and not inference["bio_focus"]["value"]:
                    inference["bio_focus"]["value"] = bio_focus_yaml
                    inference["bio_focus"]["source"] = "AUTO_PROJECT_YAML"
                    inference["bio_focus_candidates"].append(bio_focus_yaml)
                    print(f"  → Extracted study_focus.biological_focus from project.yaml: {bio_focus_yaml}")
            else:
                print(f"  ℹ project.yaml does not contain 'study_focus' field (this is normal)")

    # 2. Read storyline.md
    storyline_path = project_path / "storyline.md"
    if storyline_path.exists():
        print(f"✓ Found storyline.md")
        with open(storyline_path, "r", encoding="utf-8") as f:
            storyline_text = f.read()

            # Extract disease name from storyline
            import re
            # Look for patterns like "laryngeal cancer", "lung cancer", etc.
            disease_pattern = r'\b(\w+\s+(?:cancer|carcinoma|tumor|disease))\b'
            disease_matches = re.findall(disease_pattern, storyline_text.lower())
            if disease_matches:
                # Take the most frequent one
                disease_counter = Counter(disease_matches)
                most_common_disease = disease_counter.most_common(1)[0][0]
                inference["disease_name"]["value"] = most_common_disease
                inference["disease_name"]["source"] = "AUTO_STORYLINE_MD"
                inference["disease_candidates"].append(most_common_disease)

            # Extract theme
            if "prognostic" in storyline_text.lower() and "biomarker" in storyline_text.lower():
                inference["theme_candidates"].append("prognostic biomarker screening")
                if not inference["main_theme"]["value"]:
                    inference["main_theme"]["value"] = "prognostic biomarker screening"
                    inference["main_theme"]["source"] = "AUTO_STORYLINE_MD"
            if "survival" in storyline_text.lower():
                inference["theme_candidates"].append("survival analysis")
            if "differential" in storyline_text.lower():
                inference["method_candidates"].append("differential expression")

            # Extract biological focus
            if "transcriptom" in storyline_text.lower():
                inference["bio_focus_candidates"].append("transcriptomics")
                if not inference["bio_focus"]["value"]:
                    inference["bio_focus"]["value"] = "transcriptomics"
                    inference["bio_focus"]["source"] = "AUTO_STORYLINE_MD"
            if "genom" in storyline_text.lower():
                inference["bio_focus_candidates"].append("genomics")

    # 3. Read project_scan.json
    project_scan_path = project_path / "project_scan.json"
    if project_scan_path.exists():
        print(f"✓ Found project_scan.json")
        with open(project_scan_path, "r", encoding="utf-8") as f:
            scan_data = json.load(f)
            modules = scan_data.get("modules", [])
            for module in modules:
                module_name = module.get("module_name", "")
                module_type = module.get("module_type", "")
                inference["modules"].append({
                    "name": module_name,
                    "type": module_type
                })

                # Infer methods from module types
                if "differential" in module_type.lower() or "deg" in module_name.lower():
                    inference["method_candidates"].append("DEG")
                if "cox" in module_type.lower() or "cox" in module_name.lower():
                    inference["method_candidates"].append("Cox regression")
                if "unicox" in module_name.lower():
                    inference["method_candidates"].append("univariate Cox")
                if "rna" in module_type.lower() or "expression" in module_type.lower():
                    if "transcriptomics" not in inference["bio_focus_candidates"]:
                        inference["bio_focus_candidates"].append("transcriptomics")

    # 4. Read results_draft.md
    results_draft_path = project_path / "results_draft.md"
    if results_draft_path.exists():
        print(f"✓ Found results_draft.md")
        with open(results_draft_path, "r", encoding="utf-8") as f:
            results_text = f.read()

            # Extract disease name
            import re
            disease_pattern = r'\b(\w+\s+(?:cancer|carcinoma|tumor))\b'
            disease_matches = re.findall(disease_pattern, results_text.lower())
            if disease_matches:
                disease_counter = Counter(disease_matches)
                most_common = disease_counter.most_common(1)[0][0]
                inference["disease_candidates"].append(most_common)
                if not inference["disease_name"]["value"]:
                    inference["disease_name"]["value"] = most_common
                    inference["disease_name"]["source"] = "AUTO_RESULTS_DRAFT"

            # Abbreviation extraction from results_draft.md is intentionally skipped:
            # frequency-based uppercase matching produces too many false positives
            # (e.g., method acronyms like DHPS mistaken for disease abbreviations).

    # 5. Read abstract_draft.md
    abstract_draft_path = project_path / "abstract_draft.md"
    if abstract_draft_path.exists():
        print(f"✓ Found abstract_draft.md")
        with open(abstract_draft_path, "r", encoding="utf-8") as f:
            abstract_text = f.read()

            # Extract disease name
            import re
            disease_pattern = r'\b(\w+\s+(?:cancer|carcinoma|tumor))\b'
            disease_matches = re.findall(disease_pattern, abstract_text.lower())
            if disease_matches:
                disease_counter = Counter(disease_matches)
                most_common = disease_counter.most_common(1)[0][0]
                inference["disease_candidates"].append(most_common)
                if not inference["disease_name"]["value"]:
                    inference["disease_name"]["value"] = most_common
                    inference["disease_name"]["source"] = "AUTO_ABSTRACT_DRAFT"

            # Extract abbreviation
            abbr_pattern = r'\b([A-Z]{2,6})\b'
            abbr_matches = re.findall(abbr_pattern, abstract_text)
            exclude_abbrs = {"DEG", "GO", "KEGG", "RNA", "DNA", "PCR", "OS", "PFS", "HR", "CI"}
            abbr_candidates = [a for a in abbr_matches if a not in exclude_abbrs]
            if abbr_candidates:
                abbr_counter = Counter(abbr_candidates)
                most_common_abbr = abbr_counter.most_common(1)[0][0]
                if not inference["disease_abbr"]["value"]:
                    inference["disease_abbr"]["value"] = most_common_abbr
                    inference["disease_abbr"]["source"] = "AUTO_ABSTRACT_DRAFT"

    # 6. Read title_candidates.md
    title_candidates_path = project_path / "title_candidates.md"
    if title_candidates_path.exists():
        print(f"✓ Found title_candidates.md")
        with open(title_candidates_path, "r", encoding="utf-8") as f:
            title_text = f.read()

            # Extract disease name from title
            import re
            disease_pattern = r'\b(\w+\s+(?:cancer|carcinoma|tumor))\b'
            disease_matches = re.findall(disease_pattern, title_text.lower())
            if disease_matches:
                disease_counter = Counter(disease_matches)
                most_common = disease_counter.most_common(1)[0][0]
                inference["disease_candidates"].append(most_common)

    print(f"\nInferred information:")
    print(f"  Disease name: {inference['disease_name']['value']} (from {inference['disease_name']['source']})")
    print(f"  Disease abbr: {inference['disease_abbr']['value']} (from {inference['disease_abbr']['source']})")
    print(f"  Main theme: {inference['main_theme']['value']} (from {inference['main_theme']['source']})")
    print(f"  Bio focus: {inference['bio_focus']['value']} (from {inference['bio_focus']['source']})")
    print(f"  Modules found: {len(inference['modules'])}")
    print(f"  Disease candidates: {len(set(inference['disease_candidates']))}")
    print(f"  Theme candidates: {len(inference['theme_candidates'])}")
    print(f"  Method candidates: {len(set(inference['method_candidates']))}")

    return inference


def load_user_brief(args, project_path):
    """Load user brief from --user-brief, --user-brief-file, or brief_notes.md."""
    user_brief_text = None
    source = None

    # Priority 1: --user-brief
    if args.user_brief:
        user_brief_text = args.user_brief
        source = "USER_BRIEF"
        print(f"✓ Using --user-brief (direct input)")

    # Priority 2: --user-brief-file
    elif args.user_brief_file:
        brief_file_path = Path(args.user_brief_file)
        if brief_file_path.exists():
            with open(brief_file_path, "r", encoding="utf-8") as f:
                user_brief_text = f.read()
            source = "USER_BRIEF_FILE"
            print(f"✓ Using --user-brief-file: {brief_file_path}")
        else:
            print(f"⚠ Warning: --user-brief-file not found: {brief_file_path}")

    # Priority 3: brief_notes.md (auto-detect)
    elif (project_path / "brief_notes.md").exists():
        brief_notes_path = project_path / "brief_notes.md"
        with open(brief_notes_path, "r", encoding="utf-8") as f:
            user_brief_text = f.read()
        source = "BRIEF_NOTES_MD"
        print(f"✓ Auto-detected brief_notes.md: {brief_notes_path}")
    else:
        print(f"ℹ No user brief provided (optional)")

    return user_brief_text, source


def parse_user_brief_fallback(user_brief_text):
    """Fallback rule-based parser when LLM is not available.

    Returns:
        dict: Parsed data with conservative extraction
    """
    import re

    result = {
        "disease": {"name": None, "abbreviation": None},
        "study_focus": {"main_theme": None, "biological_focus": None},
        "manual_notes": {
            "avoid_overstatement": [],
            "important_background": [],
            "preferred_emphasis": []
        }
    }

    if not user_brief_text:
        return result

    text_lower = user_brief_text.lower()

    # ------------------------------------------------------------------
    # 1. disease.name patterns
    # ------------------------------------------------------------------
    # Patterns: 这个项目是X / 这是一个X项目 / 针对X / 这个项目针对X
    disease_patterns = [
        r'针对([^，,。;]+?癌)',
        r'针对([^，,。;]+?瘤)',
        r'针对([^，,。;]+?炎)',
        r'针对([^，,。;]+?病)',
        r'这个项目是([^，,。;]+)',
        r'这是一个([^，,。;]+项目)',
        r'这个项目针对([^，,。;]+)',
    ]
    for pattern in disease_patterns:
        match = re.search(pattern, user_brief_text)
        if match:
            raw = match.group(1).strip()
            # Clean up trailing modifiers
            raw = re.sub(r'[的是针对所在]*(?:项目|研究|分析)?$', '', raw).strip()
            if raw and len(raw) >= 2:
                result["disease"]["name"] = raw
                break

    # ------------------------------------------------------------------
    # 2. main_theme patterns
    # ------------------------------------------------------------------
    theme_patterns = [
        (r'主线是([^，,。;]+)', None),
        (r'研究主线是([^，,。;]+)', None),
        (r'目标是([^，,。;]+)', None),
        (r'主要目标是([^，,。;]+)', None),
        (r'研究目标是([^，,。;]+)', None),
        (r'主题是([^，,。;]+)', None),
        (r'主要主题是([^，,。;]+)', None),
        (r'main theme is ([^,\.;]+)', None),
        (r'theme is ([^,\.;]+)', None),
        (r'主题是([^,。;]+)', None),
    ]
    for pattern, _ in theme_patterns:
        match = re.search(pattern, text_lower)
        if match:
            raw = match.group(1).strip()
            # Normalize known method-heavy strings to natural theme expressions
            theme_map = {
                'deg+unicox 预后筛选': 'prognostic biomarker screening',
                'deg+unicox预后筛选': 'prognostic biomarker screening',
                'deg + unicox': 'prognostic biomarker screening',
                'deg unicox': 'prognostic biomarker screening',
                'deg': 'differentially expressed genes analysis',
                'differential expression': 'differentially expressed genes analysis',
                'survival analysis': 'survival analysis',
                'cox': 'Cox regression analysis',
                'unicox': 'univariate Cox analysis',
                'km': 'Kaplan-Meier survival analysis',
                'wgcna': 'weighted gene co-expression network analysis',
                'immune infiltration': 'immune infiltration analysis',
                'immune microenvironment': 'tumor immune microenvironment analysis',
                'mutation': 'somatic mutation analysis',
                'methylation': 'DNA methylation analysis',
            }
            normalized = theme_map.get(raw.lower(), raw)
            if normalized and len(normalized) >= 3:
                result["study_focus"]["main_theme"] = normalized
                break
            elif raw and len(raw) >= 3:
                result["study_focus"]["main_theme"] = raw
                break

    # ------------------------------------------------------------------
    # 3. biological_focus patterns
    # ------------------------------------------------------------------
    bio_focus_patterns = [
        r'生物学重心是([^，,。;]+)',
        r'生物学重点是([^，,。;]+)',
        r'重心是([^，,。;]+)',
        r'主要聚焦([^，,。;]+)',
        r'聚焦([^，,。;]+)',
        r'focus on ([^,\.;]+)',
        r'biological focus is ([^,\.;]+)',
    ]
    for pattern in bio_focus_patterns:
        match = re.search(pattern, text_lower)
        if match:
            raw = match.group(1).strip()
            if raw and len(raw) >= 3:
                result["study_focus"]["biological_focus"] = raw
                break

    # ------------------------------------------------------------------
    # 4. important_background patterns
    # ------------------------------------------------------------------
    background_patterns = [
        r'背景上要强调([^，,。;]+)',
        r'背景强调([^，,。;]+)',
        r'需要强调([^，,。;]+)',
        r'要突出([^，,。;]+)',
        r'重要背景是([^，,。;]+)',
        r'背景包括([^，,。;]+)',
    ]
    for pattern in background_patterns:
        matches = re.findall(pattern, user_brief_text)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 2:
                result["manual_notes"]["important_background"].append(cleaned)

    # ------------------------------------------------------------------
    # 5. avoid_overstatement patterns (保留已有)
    # ------------------------------------------------------------------
    avoid_patterns = [
        r"don't\s+(?:write|say|mention|emphasize)\s+([^,\.;]+)",
        r"avoid\s+([^,\.;]+)",
        r"not\s+([^,\.;]+)",
        r"不要([^,。;]+)",
    ]
    for pattern in avoid_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 2:
                result["manual_notes"]["avoid_overstatement"].append(cleaned)

    # ------------------------------------------------------------------
    # 6. preferred_emphasis patterns (保留已有)
    # ------------------------------------------------------------------
    emphasis_patterns = [
        r"emphasize\s+([^,\.;]+)",
        r"highlight\s+([^,\.;]+)",
        r"focus on\s+([^,\.;]+)",
        r"强调([^,。;]+)",
    ]
    for pattern in emphasis_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 2:
                result["manual_notes"]["preferred_emphasis"].append(cleaned)

    # ------------------------------------------------------------------
    # Deduplicate
    # ------------------------------------------------------------------
    result["manual_notes"]["avoid_overstatement"] = list(set(result["manual_notes"]["avoid_overstatement"]))
    result["manual_notes"]["preferred_emphasis"] = list(set(result["manual_notes"]["preferred_emphasis"]))
    result["manual_notes"]["important_background"] = list(set(result["manual_notes"]["important_background"]))

    return result


def parse_with_llm(inference, user_brief_text, user_brief_source):
    """Use LLM to parse inference + user brief into structured fields.

    Returns:
        parsed_data: dict with parsed fields (or None if failed)
        user_brief_source: the original user_brief_source (USER_BRIEF, USER_BRIEF_FILE, or BRIEF_NOTES_MD)
        auto_sources: dict mapping each field to its auto-inferred source
    """
    try:
        # Import llm_client
        import sys
        from pathlib import Path
        scripts_dir = Path(__file__).parent
        sys.path.insert(0, str(scripts_dir))
        from llm_client import call_json, is_available

        # Check if LLM is available
        if not is_available():
            print("\n" + "=" * 60)
            print("LLM NOT AVAILABLE - USING FALLBACK RULE-BASED PARSER")
            print("=" * 60)
            print("⚠ LLM is not available (API key not set)")
            print("  Using conservative rule-based parsing for user_brief")

            # Use fallback parser
            if user_brief_text:
                fallback_result = parse_user_brief_fallback(user_brief_text)
                print(f"✓ Fallback parsing completed")
                print(f"  Extracted main_theme: {fallback_result['study_focus']['main_theme']}")
                print(f"  Extracted avoid_overstatement: {len(fallback_result['manual_notes']['avoid_overstatement'])} items")
                print(f"  Extracted preferred_emphasis: {len(fallback_result['manual_notes']['preferred_emphasis'])} items")

                # Track auto sources
                auto_sources = {}
                if inference["disease_name"]["value"]:
                    auto_sources["disease.name"] = inference["disease_name"]["source"]
                if inference["disease_abbr"]["value"]:
                    auto_sources["disease.abbreviation"] = inference["disease_abbr"]["source"]
                if inference["main_theme"]["value"]:
                    auto_sources["study_focus.main_theme"] = inference["main_theme"]["source"]
                if inference["bio_focus"]["value"]:
                    auto_sources["study_focus.biological_focus"] = inference["bio_focus"]["source"]

                return fallback_result, user_brief_source, auto_sources
            else:
                return None, user_brief_source, {}

        # Track which auto-inferred fields are being used
        auto_sources = {}
        if inference["disease_name"]["value"]:
            auto_sources["disease.name"] = inference["disease_name"]["source"]
        if inference["disease_abbr"]["value"]:
            auto_sources["disease.abbreviation"] = inference["disease_abbr"]["source"]
        if inference["main_theme"]["value"]:
            auto_sources["study_focus.main_theme"] = inference["main_theme"]["source"]
        if inference["bio_focus"]["value"]:
            auto_sources["study_focus.biological_focus"] = inference["bio_focus"]["source"]

        # Build inference payload
        inference_payload = {
            "modules": inference["modules"],
            "disease_candidates": list(set(inference["disease_candidates"]))[:5],
            "theme_candidates": list(set(inference["theme_candidates"]))[:3],
            "method_candidates": list(set(inference["method_candidates"]))[:5],
            "bio_focus_candidates": list(set(inference["bio_focus_candidates"]))[:3],
            "auto_inferred": {
                "disease_name": inference["disease_name"]["value"],
                "disease_abbr": inference["disease_abbr"]["value"],
                "main_theme": inference["main_theme"]["value"],
                "bio_focus": inference["bio_focus"]["value"]
            }
        }

        # Build prompt
        prompt = f"""You are a scientific writing assistant. Your task is to extract structured project information from the provided data.

## Auto-inferred data (extracted from project files):
{json.dumps(inference_payload, indent=2, ensure_ascii=False)}

## User Brief (natural language):
{user_brief_text if user_brief_text else "(No user brief provided)"}

## Your Task:
Based on the above information, generate a structured JSON output with the following schema:

{{
  "disease": {{
    "name": "string or null",
    "abbreviation": "string or null"
  }},
  "study_focus": {{
    "main_theme": "string or null",
    "biological_focus": "string or null"
  }},
  "manual_notes": {{
    "avoid_overstatement": ["list of strings"],
    "important_background": ["list of strings"],
    "preferred_emphasis": ["list of strings"]
  }}
}}

## Rules:
1. **Do NOT make up information**. If uncertain, leave the field as null or empty list.
2. **Do NOT treat auxiliary analyses as main theme**. For example, if user says "don't write nitrogen metabolism as main theme", then main_theme should NOT be "nitrogen metabolism".
3. **Prefer user brief over auto-inferred**. If user brief provides explicit info, use that over auto-inferred.
4. **Be conservative with abbreviations**. If disease abbreviation is uncertain, leave it null.
5. **Extract avoid_overstatement from user brief**. Look for phrases like "don't", "avoid", "not", "不要".
6. **Extract preferred_emphasis from user brief**. Look for phrases like "emphasize", "focus on", "highlight", "强调".
7. **Deduplicate and remove empty values** from all lists.
8. **Main theme should reflect the core research goal**, not just a method name. For example, "prognostic biomarker screening" is better than "DEG analysis".

Now generate the JSON output:"""

        print("\n" + "=" * 60)
        print("CALLING LLM FOR STRUCTURED PARSING")
        print("=" * 60)

        result = call_json(prompt)

        if result:
            print("✓ LLM parsing successful")
            return result, user_brief_source, auto_sources
        else:
            print("⚠ LLM parsing failed, using fallback")
            return None, user_brief_source, auto_sources

    except Exception as e:
        print(f"⚠ LLM parsing error: {e}")
        print("  Using fallback rule-based parser")

        # Build auto_sources even on error
        auto_sources = {}
        if inference["disease_name"]["value"]:
            auto_sources["disease.name"] = inference["disease_name"]["source"]
        if inference["disease_abbr"]["value"]:
            auto_sources["disease.abbreviation"] = inference["disease_abbr"]["source"]
        if inference["main_theme"]["value"]:
            auto_sources["study_focus.main_theme"] = inference["main_theme"]["source"]
        if inference["bio_focus"]["value"]:
            auto_sources["study_focus.biological_focus"] = inference["bio_focus"]["source"]

        # Try fallback parser if user_brief_text exists
        if user_brief_text:
            fallback_result = parse_user_brief_fallback(user_brief_text)
            return fallback_result, user_brief_source, auto_sources
        else:
            return None, user_brief_source, auto_sources


def resolve_field_with_priority(cli_value, yaml_value, llm_value, inferred_value,
                                  field_name, source_tracking, user_brief_source=None, inferred_source=None):
    """Resolve field with priority: CLI > user_brief (LLM) > YAML > auto-infer > default.

    Args:
        user_brief_source: USER_BRIEF, USER_BRIEF_FILE, or BRIEF_NOTES_MD
        inferred_source: AUTO_PROJECT_YAML, AUTO_STORYLINE_MD, AUTO_PROJECT_SCAN_JSON, etc.
    """
    if cli_value is not None:
        source_tracking[field_name] = "CLI"
        return cli_value
    elif llm_value is not None:
        # Use the specific user brief source if available
        source_tracking[field_name] = user_brief_source or "LLM_PARSED"
        return llm_value
    elif yaml_value is not None:
        source_tracking[field_name] = "PROJECT_BRIEF_YAML"
        return yaml_value
    elif inferred_value is not None:
        # Preserve specific AUTO source (e.g., AUTO_PROJECT_YAML, AUTO_STORYLINE_MD)
        source_tracking[field_name] = inferred_source if inferred_source else "AUTO_INFERRED"
        return inferred_value
    else:
        source_tracking[field_name] = "DEFAULT"
        return None


def resolve_list_field_with_priority(cli_values, yaml_values, llm_values, field_name, source_tracking, user_brief_source=None):
    """Resolve list field with priority: CLI > user_brief (LLM) > YAML > default."""
    if cli_values:
        source_tracking[field_name] = "CLI"
        return cli_values
    elif llm_values:
        source_tracking[field_name] = user_brief_source or "LLM_PARSED"
        return llm_values
    elif yaml_values:
        source_tracking[field_name] = "PROJECT_BRIEF_YAML"
        return yaml_values
    else:
        source_tracking[field_name] = "DEFAULT"
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Resolve project brief with auto-inference and natural language support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:

1. Auto-inference only:
  python3 resolve_project_brief.py --project /path/to/project

2. With natural language brief:
  python3 resolve_project_brief.py --project /path/to/project \\
    --user-brief "This project is laryngeal cancer prognosis, main theme is DEG+uniCox, don't write nitrogen metabolism as main theme, emphasize prognostic screening."

3. With brief file:
  python3 resolve_project_brief.py --project /path/to/project \\
    --user-brief-file /path/to/brief_description.txt

4. Legacy CLI args (still supported):
  python3 resolve_project_brief.py --project /path/to/project \\
    --disease "Lung Cancer" \\
    --abbr "LC" \\
    --main-theme "prognostic biomarker identification"

Priority: CLI > user_brief > user_brief_file > brief_notes.md > project_brief.yaml > auto-infer > default
        """
    )

    parser.add_argument("--project", required=True, help="Project directory path")

    # New parameters for natural language input
    parser.add_argument("--user-brief", help="Natural language project description (direct input)")
    parser.add_argument("--user-brief-file", help="Path to file containing natural language project description")

    # Legacy parameters (still supported)
    parser.add_argument("--disease", help="Disease name")
    parser.add_argument("--abbr", help="Disease abbreviation")
    parser.add_argument("--main-theme", help="Main research theme")
    parser.add_argument("--bio-focus", help="Biological focus area")
    parser.add_argument("--notes", action="append", help="Important background notes (can be repeated)")
    parser.add_argument("--avoid", action="append", help="Things to avoid (can be repeated)")
    parser.add_argument("--emphasis", action="append", help="Preferred emphasis (can be repeated)")

    args = parser.parse_args()

    project_path = Path(args.project).resolve()

    print("=" * 60)
    print("SCIWriter - Project Brief Resolver (Enhanced)")
    print("=" * 60)
    print(f"Project: {project_path}\n")

    # Step 1: Auto-infer from project files
    inference = auto_infer_from_files(project_path)

    # Step 2: Load user brief (if provided)
    user_brief_text, user_brief_source = load_user_brief(args, project_path)

    # Step 3: Parse with LLM (if user brief or inference available)
    llm_parsed = None
    auto_sources = {}
    if user_brief_text or inference["modules"]:
        llm_parsed, user_brief_source, auto_sources = parse_with_llm(inference, user_brief_text, user_brief_source)

    # Step 4: Load YAML if exists
    print("\n" + "=" * 60)
    print("LOADING YAML CONFIGURATION")
    print("=" * 60)
    yaml_data = load_project_brief_yaml(project_path)

    # Extract YAML values
    yaml_disease = yaml_data.get("disease", {})
    yaml_study_focus = yaml_data.get("study_focus", {})
    yaml_manual_notes = yaml_data.get("manual_notes", {})

    # Extract LLM parsed values
    llm_disease = llm_parsed.get("disease", {}) if llm_parsed else {}
    llm_study_focus = llm_parsed.get("study_focus", {}) if llm_parsed else {}
    llm_manual_notes = llm_parsed.get("manual_notes", {}) if llm_parsed else {}

    # Track source of each field
    source_tracking = {}

    print("\n" + "=" * 60)
    print("RESOLVING FIELDS WITH PRIORITY")
    print("=" * 60)

    # Resolve each field with new priority
    # Note: Use inference["..."]["source"] directly to preserve specific AUTO sources
    # even when parse_with_llm is not called (e.g., no user_brief and no modules)
    disease_name = resolve_field_with_priority(
        args.disease,
        yaml_disease.get("name"),
        llm_disease.get("name"),
        inference["disease_name"]["value"],
        "disease.name",
        source_tracking,
        user_brief_source,
        inference["disease_name"]["source"]
    )

    disease_abbr = resolve_field_with_priority(
        args.abbr,
        yaml_disease.get("abbreviation"),
        llm_disease.get("abbreviation"),
        inference["disease_abbr"]["value"],
        "disease.abbreviation",
        source_tracking,
        user_brief_source,
        inference["disease_abbr"]["source"]
    )

    main_theme = resolve_field_with_priority(
        args.main_theme,
        yaml_study_focus.get("main_theme"),
        llm_study_focus.get("main_theme"),
        inference["main_theme"]["value"],
        "study_focus.main_theme",
        source_tracking,
        user_brief_source,
        inference["main_theme"]["source"]
    )

    bio_focus = resolve_field_with_priority(
        args.bio_focus,
        yaml_study_focus.get("biological_focus"),
        llm_study_focus.get("biological_focus"),
        inference["bio_focus"]["value"],
        "study_focus.biological_focus",
        source_tracking,
        user_brief_source,
        inference["bio_focus"]["source"]
    )

    # Resolve list fields
    important_background = resolve_list_field_with_priority(
        args.notes,
        yaml_manual_notes.get("important_background"),
        llm_manual_notes.get("important_background", []),
        "manual_notes.important_background",
        source_tracking,
        user_brief_source
    )

    avoid_overstatement = resolve_list_field_with_priority(
        args.avoid,
        yaml_manual_notes.get("avoid_overstatement"),
        llm_manual_notes.get("avoid_overstatement", []),
        "manual_notes.avoid_overstatement",
        source_tracking,
        user_brief_source
    )

    preferred_emphasis = resolve_list_field_with_priority(
        args.emphasis,
        yaml_manual_notes.get("preferred_emphasis"),
        llm_manual_notes.get("preferred_emphasis", []),
        "manual_notes.preferred_emphasis",
        source_tracking,
        user_brief_source
    )

    # Deduplicate and clean lists
    important_background = list(filter(None, set(important_background)))
    avoid_overstatement = list(filter(None, set(avoid_overstatement)))
    preferred_emphasis = list(filter(None, set(preferred_emphasis)))

    # ------------------------------------------------------------------
    # Dirty-data guards
    # ------------------------------------------------------------------
    # Guard 1: reject disease.name that contains non-disease words
    _NON_DISEASE_WORDS = {"项目", "转录组", "预后", "筛选", "分析", "研究", "方法"}
    if disease_name and any(w in disease_name for w in _NON_DISEASE_WORDS):
        print(f"⚠ Rejected dirty disease.name (contains non-disease words): {disease_name!r}")
        disease_name = None
        source_tracking["disease.name"] = "REJECTED_DIRTY"

    # Guard 2: normalize main_theme that looks like a raw method string
    _METHOD_STRING_PATTERN = None
    if main_theme:
        import re as _re
        _method_tokens = {"deg", "unicox", "multicox", "cox", "km", "wgcna", "gsea", "ssgsea", "lasso"}
        _theme_lower = main_theme.lower()
        # If the theme is short and composed mostly of method tokens / "+" separators, normalize it
        _tokens = set(_re.split(r'[\s+\-/]+', _theme_lower))
        if _tokens and _tokens.issubset(_method_tokens | {""}):
            print(f"⚠ Normalizing raw method-string main_theme: {main_theme!r} → 'prognostic biomarker screening'")
            main_theme = "prognostic biomarker screening"
            source_tracking["study_focus.main_theme"] = "NORMALIZED_FROM_METHOD_STRING"

    # Read project name from project.yaml if exists
    project_yaml_path = project_path / "project.yaml"
    project_name = inference.get("project_name", "unknown")

    # Build resolved output
    resolved = {
        "project_name": project_name,
        "project_path": str(project_path),
        "disease": {
            "name": disease_name,
            "abbreviation": disease_abbr
        },
        "study_focus": {
            "main_theme": main_theme,
            "biological_focus": bio_focus
        },
        "manual_notes": {
            "important_background": important_background,
            "avoid_overstatement": avoid_overstatement,
            "preferred_emphasis": preferred_emphasis
        },
        "source_priority": {
            "order": ["CLI", "USER_BRIEF", "USER_BRIEF_FILE", "BRIEF_NOTES_MD", "PROJECT_BRIEF_YAML", "AUTO_INFERRED", "DEFAULT"],
            "field_sources": source_tracking
        }
    }

    # Save output
    output_path = project_path / "project_brief_resolved.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("FIELD RESOLUTION SUMMARY")
    print("=" * 60)

    print("\nField sources:")
    for field, source in sorted(source_tracking.items()):
        value_preview = ""
        if "disease.name" in field:
            value_preview = f" = {disease_name}"
        elif "disease.abbreviation" in field:
            value_preview = f" = {disease_abbr}"
        elif "main_theme" in field:
            value_preview = f" = {main_theme}"
        elif "biological_focus" in field:
            value_preview = f" = {bio_focus}"
        elif "important_background" in field:
            value_preview = f" = {len(important_background)} items"
        elif "avoid_overstatement" in field:
            value_preview = f" = {len(avoid_overstatement)} items"
        elif "preferred_emphasis" in field:
            value_preview = f" = {len(preferred_emphasis)} items"

        print(f"  {field:40s} [{source:20s}]{value_preview}")

    print("\n" + "=" * 60)
    print("OUTPUT GENERATED")
    print("=" * 60)
    print(f"\n✓ Generated: {output_path}")

    print("\nResolved values:")
    print(f"  Disease: {disease_name or '(not set)'}")
    print(f"  Abbreviation: {disease_abbr or '(not set)'}")
    print(f"  Main theme: {main_theme or '(not set)'}")
    print(f"  Biological focus: {bio_focus or '(not set)'}")
    print(f"  Background notes: {len(important_background)} items")
    print(f"  Avoid statements: {len(avoid_overstatement)} items")
    print(f"  Emphasis points: {len(preferred_emphasis)} items")

    print("\nNext steps:")
    print(f"  1. Review: cat {output_path}")
    print("  2. Use this resolved brief in downstream writing tasks")


if __name__ == "__main__":
    main()
