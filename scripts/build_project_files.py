#!/usr/bin/env python3
import json
import argparse
import yaml
from pathlib import Path


def detect_route(modules):
    """Detect analysis route based on module types."""
    module_types = [m["module_type"] for m in modules]

    has_deg = "differential_expression" in module_types
    has_cox = "univariate_cox" in module_types

    if has_deg and has_cox:
        return "prognostic_biomarker_pipeline"
    elif has_deg:
        return "differential_expression_analysis"
    elif has_cox:
        return "survival_analysis"
    else:
        return "unknown"


def generate_storyline(project_name, modules, route):
    """Generate storyline.md content."""
    storyline = f"# Project Storyline: {project_name}\n\n"
    storyline += "## Analysis Overview\n\n"

    if route == "prognostic_biomarker_pipeline":
        storyline += (
            "This study aims to identify prognostic biomarkers through a systematic screening approach. "
            "We first identified differentially expressed genes to establish a candidate gene pool. "
            "Subsequently, we evaluated the prognostic significance of these genes using univariate Cox regression analysis. "
            "This pipeline enables the discovery of genes associated with patient survival outcomes.\n\n"
        )
    elif route == "differential_expression_analysis":
        storyline += (
            "This study focuses on identifying differentially expressed genes between conditions. "
            "The analysis provides insights into transcriptional changes and potential functional alterations.\n\n"
        )
    elif route == "survival_analysis":
        storyline += (
            "This study evaluates the prognostic significance of genes using survival analysis. "
            "Univariate Cox regression was employed to identify genes associated with patient outcomes.\n\n"
        )
    else:
        storyline += "This study performs systematic analysis on the provided dataset.\n\n"

    storyline += "## Module Summary\n\n"

    for module in modules:
        module_name = module["module_name"]
        module_type = module["module_type"]
        goal = module.get("goal", "unknown analysis")

        storyline += f"### {module_name}\n"
        storyline += f"- **Type**: {module_type}\n"
        storyline += f"- **Goal**: {goal}\n"

        # Add evidence summary if available
        if "evidence" in module and module["evidence"]:
            storyline += f"- **Key findings**:\n"
            for item, value in module["evidence"].items():
                if item != "representative_genes":
                    storyline += f"  - {item}: {value}\n"

        storyline += "\n"

    storyline += "## Expected Results\n\n"
    storyline += (
        "The results section will present findings from each analysis module in sequential order, "
        "demonstrating the logical flow from initial screening to final biomarker identification.\n"
    )

    return storyline


def build_project_files(project_scan_path):
    """Build project.yaml and storyline.md."""
    project_scan_path = Path(project_scan_path)

    # Read project scan
    with open(project_scan_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    project_path = Path(project_data["project_path"])
    project_name = project_data["project_name"]
    modules_raw = project_data["modules"]

    print(f"Building project files for: {project_name}\n")

    # Collect module information
    modules = []
    for module_raw in modules_raw:
        module_name = module_raw["module_name"]
        module_type = module_raw["module_type"]
        module_dir = project_path / module_name

        module_info = {
            "module_name": module_name,
            "module_type": module_type
        }

        # Read module context
        context_path = module_dir / "module_context.json"
        if context_path.exists():
            with open(context_path, "r", encoding="utf-8") as f:
                context = json.load(f)
                module_info["goal"] = context.get("goal", "")

        # Read evidence
        evidence_path = module_dir / "evidence.csv"
        if evidence_path.exists():
            import pandas as pd
            evidence_df = pd.read_csv(evidence_path)
            evidence_dict = dict(zip(evidence_df["item"], evidence_df["value"]))
            module_info["evidence"] = evidence_dict

        modules.append(module_info)

    # Detect route
    route = detect_route(modules)

    # Build project.yaml
    module_names = [m["module_name"] for m in modules]

    project_yaml = {
        "project_name": project_name,
        "project_path": str(project_path),
        "module_count": len(modules),
        "modules": module_names,
        "results_order": module_names,
        "main_text_modules": module_names,
        "detected_route": route
    }

    # Save project.yaml
    yaml_path = project_path / "project.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(project_yaml, f, default_flow_style=False, allow_unicode=True)

    print(f"✓ project.yaml")
    print(f"  Route: {route}")
    print(f"  Modules: {', '.join(module_names)}")
    print()

    # Generate storyline.md
    storyline_content = generate_storyline(project_name, modules, route)

    storyline_path = project_path / "storyline.md"
    with open(storyline_path, "w", encoding="utf-8") as f:
        f.write(storyline_content)

    print(f"✓ storyline.md")
    print(f"  Generated storyline for {route}")
    print()

    print("Project files generated successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build project.yaml and storyline.md")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_scan_path = Path(args.project) / "project_scan.json"
    build_project_files(project_scan_path)
