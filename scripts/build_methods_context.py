#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path


def infer_method(module_type):
    """Infer method description from module type."""
    methods = {
        "differential_expression": "differential expression analysis",
        "univariate_cox": "univariate Cox regression analysis",
    }
    return methods.get(module_type, "unknown analysis method")


def infer_software_candidates(module_type, scripts):
    """Infer software candidates from module type and script names."""
    candidates = []

    if module_type == "differential_expression":
        for script in scripts:
            script_lower = script.lower()
            if "edger" in script_lower:
                candidates.append("edgeR")
            elif "deseq" in script_lower:
                candidates.append("DESeq2")
            elif "limma" in script_lower:
                candidates.append("limma")

    elif module_type == "univariate_cox":
        for script in scripts:
            script_lower = script.lower()
            if "cox" in script_lower or "unicox" in script_lower:
                candidates.append("survival package (Cox regression)")

    return candidates


def check_code_matches_results(module_type, scripts):
    """Check if code naming matches module type."""
    if not scripts:
        return False

    for script in scripts:
        script_lower = script.lower()

        if module_type == "differential_expression":
            if any(kw in script_lower for kw in ["edger", "deseq", "limma", "deg", "diff"]):
                return True

        elif module_type == "univariate_cox":
            if any(kw in script_lower for kw in ["cox", "unicox", "survival"]):
                return True

    return False


def determine_source_mode(scripts, result_tables):
    """Determine method source mode."""
    if scripts and result_tables:
        return "code_driven"
    elif result_tables:
        return "result_driven"
    else:
        return "structure_driven"


def determine_confidence(source_mode, code_matches_results):
    """Determine confidence level."""
    if source_mode == "code_driven" and code_matches_results:
        return "high"
    elif source_mode == "result_driven":
        return "medium"
    else:
        return "low"


def build_methods_context(project_scan_path):
    """Build methods_context.json for each module."""
    project_scan_path = Path(project_scan_path)

    # Read project scan
    with open(project_scan_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    project_path = Path(project_data["project_path"])
    modules = project_data["modules"]

    print(f"Building methods contexts for {len(modules)} modules...\n")

    for module in modules:
        module_name = module["module_name"]
        module_type = module["module_type"]
        module_dir = project_path / module_name

        # Read module context
        context_path = module_dir / "module_context.json"
        if not context_path.exists():
            print(f"⚠ {module_name}: module_context.json not found, skipping")
            continue

        with open(context_path, "r", encoding="utf-8") as f:
            module_context = json.load(f)

        # Get available sources
        scripts = module_context.get("scripts", [])
        result_tables = module_context.get("key_result_tables", [])
        text_inputs = module_context.get("text_inputs", [])

        # Determine source mode
        source_mode = determine_source_mode(scripts, result_tables)

        # Infer software candidates
        software_candidates = infer_software_candidates(module_type, scripts)

        # Check code-result match
        code_matches_results = check_code_matches_results(module_type, scripts)

        # Determine confidence
        confidence = determine_confidence(source_mode, code_matches_results)

        # Build methods context
        methods_context = {
            "module_name": module_name,
            "module_type": module_type,
            "inferred_method": infer_method(module_type),
            "method_source_mode": source_mode,
            "available_sources": {
                "scripts": scripts,
                "result_tables": result_tables,
                "text_inputs": text_inputs
            },
            "software_candidates": software_candidates,
            "parameter_candidates": [],
            "code_matches_results": code_matches_results,
            "confidence": confidence
        }

        # Save to module directory
        output_path = module_dir / "methods_context.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(methods_context, f, indent=2, ensure_ascii=False)

        print(f"✓ {module_name}/methods_context.json")
        print(f"  Method: {methods_context['inferred_method']}")
        print(f"  Source mode: {source_mode}")
        print(f"  Software: {', '.join(software_candidates) if software_candidates else 'unknown'}")
        print(f"  Confidence: {confidence}")
        print()

    print("Methods contexts generated successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Build methods_context.json for each module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 build_methods_context.py --project /path/to/your/project

This will generate methods_context.json in each module directory.
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    project_scan_path = project_path / "project_scan.json"

    print("=" * 60)
    print("SCIWriter - Methods Context Builder")
    print("=" * 60)
    print(f"Project: {project_path}")

    # Check if project_scan.json exists
    if not project_scan_path.exists():
        print(f"\n✗ Error: {project_scan_path} not found")
        print("\nPlease run scan_project.py first:")
        print(f"  python3 scan_project.py --project {project_path}")
        sys.exit(1)

    print(f"Project scan: {project_scan_path}")
    print()

    # Build methods contexts
    build_methods_context(project_scan_path)


if __name__ == "__main__":
    main()
