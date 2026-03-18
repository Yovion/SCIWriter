#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
from pathlib import Path


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


def resolve_field(cli_value, yaml_value, field_name, source_tracking):
    """Resolve field value with priority: CLI > YAML > default."""
    if cli_value is not None:
        source_tracking[field_name] = "CLI"
        return cli_value
    elif yaml_value is not None:
        source_tracking[field_name] = "YAML"
        return yaml_value
    else:
        source_tracking[field_name] = "default"
        return None


def resolve_list_field(cli_values, yaml_values, field_name, source_tracking):
    """Resolve list field with priority: CLI > YAML > default."""
    if cli_values:
        source_tracking[field_name] = "CLI"
        return cli_values
    elif yaml_values:
        source_tracking[field_name] = "YAML"
        return yaml_values
    else:
        source_tracking[field_name] = "default"
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Resolve project brief from CLI args and YAML file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 resolve_project_brief.py --project /path/to/project \\
    --disease "Lung Cancer" \\
    --abbr "LC" \\
    --main-theme "prognostic biomarker identification" \\
    --bio-focus "transcriptomics" \\
    --notes "Focus on survival outcomes" \\
    --notes "Avoid mechanistic claims" \\
    --avoid "novel mechanism" \\
    --emphasis "data-driven approach"

Priority: CLI > project_brief.yaml > default
        """
    )

    parser.add_argument("--project", required=True, help="Project directory path")
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
    print("SCIWriter - Project Brief Resolver")
    print("=" * 60)
    print(f"Project: {project_path}\n")

    # Load YAML if exists
    yaml_data = load_project_brief_yaml(project_path)

    # Extract YAML values
    yaml_disease = yaml_data.get("disease", {})
    yaml_study_focus = yaml_data.get("study_focus", {})
    yaml_manual_notes = yaml_data.get("manual_notes", {})

    # Track source of each field
    source_tracking = {}

    # Resolve each field
    disease_name = resolve_field(
        args.disease,
        yaml_disease.get("name"),
        "disease.name",
        source_tracking
    )

    disease_abbr = resolve_field(
        args.abbr,
        yaml_disease.get("abbreviation"),
        "disease.abbreviation",
        source_tracking
    )

    main_theme = resolve_field(
        args.main_theme,
        yaml_study_focus.get("main_theme"),
        "study_focus.main_theme",
        source_tracking
    )

    bio_focus = resolve_field(
        args.bio_focus,
        yaml_study_focus.get("biological_focus"),
        "study_focus.biological_focus",
        source_tracking
    )

    # Resolve list fields
    important_background = resolve_list_field(
        args.notes,
        yaml_manual_notes.get("important_background"),
        "manual_notes.important_background",
        source_tracking
    )

    avoid_overstatement = resolve_list_field(
        args.avoid,
        yaml_manual_notes.get("avoid_overstatement"),
        "manual_notes.avoid_overstatement",
        source_tracking
    )

    preferred_emphasis = resolve_list_field(
        args.emphasis,
        yaml_manual_notes.get("preferred_emphasis"),
        "manual_notes.preferred_emphasis",
        source_tracking
    )

    # Read project name from project.yaml if exists
    project_yaml_path = project_path / "project.yaml"
    project_name = "unknown"
    if project_yaml_path.exists():
        with open(project_yaml_path, "r", encoding="utf-8") as f:
            project_data = yaml.safe_load(f)
            project_name = project_data.get("project_name", "unknown")

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
            "order": ["CLI", "YAML", "default"],
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

        print(f"  {field:40s} [{source:7s}]{value_preview}")

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
