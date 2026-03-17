#!/usr/bin/env python3
import json
import argparse
from pathlib import Path


def infer_goal(module_type):
    """Infer module goal from module type."""
    goals = {
        "differential_expression": "identify differentially expressed genes",
        "univariate_cox": "identify prognosis-related genes using univariate Cox regression",
    }
    return goals.get(module_type, "unknown analysis goal")


def prioritize_result_tables(module_type, result_tables):
    """Prioritize key result tables based on module type.

    Rules:
    - differential_expression: diffSig.xls first
    - univariate_cox: uniCox.txt or cox-related files first, diffSig.xls second
    """
    if not result_tables:
        return []

    key_files = []

    if module_type == "differential_expression":
        # Priority 1: diffSig.xls
        for f in result_tables:
            if "diffsig" in f.lower():
                key_files.append(f)
        # Priority 2: remaining files
        for f in result_tables:
            if f not in key_files:
                key_files.append(f)

    elif module_type == "univariate_cox":
        # Priority 1: uniCox.txt or cox-related result files
        for f in result_tables:
            f_lower = f.lower()
            if any(kw in f_lower for kw in ["unicox", "cox"]):
                key_files.append(f)

        # Priority 2: diffSig.xls (auxiliary result)
        for f in result_tables:
            if "diffsig" in f.lower() and f not in key_files:
                key_files.append(f)

        # Priority 3: remaining files
        for f in result_tables:
            if f not in key_files:
                key_files.append(f)

    else:
        # Default: keep original order
        key_files = result_tables

    return key_files


def build_module_context(project_scan_path):
    """Build module_context.json for each module."""
    project_scan_path = Path(project_scan_path)

    # Read project scan
    with open(project_scan_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    project_path = Path(project_data["project_path"])
    modules = project_data["modules"]

    print(f"Building module contexts for {len(modules)} modules...\n")

    for idx, module in enumerate(modules, start=1):
        module_name = module["module_name"]
        module_type = module["module_type"]
        files = module["files"]

        # Build module context
        module_context = {
            "module_id": f"module_{idx:02d}",
            "module_name": module_name,
            "module_type": module_type,
            "goal": infer_goal(module_type),
            "key_result_tables": prioritize_result_tables(
                module_type, files["result_tables"]
            ),
            "scripts": files["scripts"],
            "text_inputs": files["text_inputs"],
            "other_files": files["other_files"],
        }

        # Save to module directory
        module_dir = project_path / module_name
        output_path = module_dir / "module_context.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(module_context, f, indent=2, ensure_ascii=False)

        print(f"✓ {module_name}/module_context.json")
        print(f"  Type: {module_type}")
        print(f"  Goal: {module_context['goal']}")
        print(f"  Key results: {', '.join(module_context['key_result_tables'])}")
        print()

    print(f"All module contexts generated successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build module_context.json for each module")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_scan_path = Path(args.project) / "project_scan.json"
    build_module_context(project_scan_path)
