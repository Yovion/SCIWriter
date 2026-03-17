#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path


def infer_module_type(folder_name, files):
    """Infer module type from folder and file names.

    Priority:
    1. Check folder name first (highest priority)
    2. Check file names if folder name is ambiguous
    3. univariate_cox has higher priority than differential_expression
    """
    folder_lower = folder_name.lower()
    files_lower = " ".join(files).lower()

    # Priority 1: Check folder name for univariate_cox keywords
    if any(kw in folder_lower for kw in ["unicox", "cox", "univariate"]):
        return "univariate_cox"

    # Priority 2: Check folder name for differential_expression keywords
    if any(kw in folder_lower for kw in ["deg", "edger", "differential"]):
        return "differential_expression"

    # Priority 3: Check file names for univariate_cox keywords
    if any(kw in files_lower for kw in ["unicox", "cox"]):
        return "univariate_cox"

    # Priority 4: Check file names for differential_expression keywords
    if any(kw in files_lower for kw in ["deg", "edger", "diff"]):
        return "differential_expression"

    return "unknown"


def classify_file(filename):
    """Classify file into categories.

    Priority:
    1. Check file extension first (scripts must be identified first)
    2. Check if filename indicates it's a result file
    3. Default classification by extension
    """
    ext = Path(filename).suffix.lower()
    name = filename.lower()

    # Priority 1: Scripts by extension (highest priority)
    if ext in [".r", ".py", ".sh"]:
        return "scripts"

    # Priority 2: Result files by name pattern (for .txt files with result keywords)
    if ext == ".txt" and any(kw in name for kw in ["unicox", "diffsig", "result"]):
        return "result_tables"

    # Priority 3: Result files by extension
    if ext in [".xls", ".xlsx", ".csv", ".tsv"]:
        return "result_tables"

    # Priority 4: Text inputs
    if ext == ".txt":
        return "text_inputs"

    # Priority 5: Other files
    return "other_files"


def scan_project(project_path):
    """Scan project structure and generate metadata."""
    project_path = Path(project_path)
    project_name = project_path.name

    result = {
        "project_name": project_name,
        "project_path": str(project_path),
        "modules": []
    }

    # Get all first-level directories
    for item in sorted(project_path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            files = [f.name for f in item.iterdir() if f.is_file()]

            module_info = {
                "module_name": item.name,
                "module_type": infer_module_type(item.name, files),
                "files": {
                    "result_tables": [],
                    "scripts": [],
                    "text_inputs": [],
                    "other_files": []
                }
            }

            # Classify each file
            for filename in files:
                category = classify_file(filename)
                module_info["files"][category].append(filename)

            result["modules"].append(module_info)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan project structure and generate project_scan.json")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = args.project

    scan_result = scan_project(project_path)

    # Save to project root
    output_path = Path(project_path) / "project_scan.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scan_result, f, indent=2, ensure_ascii=False)

    print(f"Project scan completed!")
    print(f"Result saved to: {output_path}")
    print(f"\nFound {len(scan_result['modules'])} modules:")
    for module in scan_result["modules"]:
        print(f"  - {module['module_name']} ({module['module_type']})")
