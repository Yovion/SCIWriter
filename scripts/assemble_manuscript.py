#!/usr/bin/env python3
import sys
import yaml
import argparse
from pathlib import Path


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if file_path.exists():
        print(f"  ✓ {description}: {file_path}")
        return True
    else:
        print(f"  ✗ {description}: {file_path} (NOT FOUND)")
        return False


def check_prerequisites(project_path):
    """Check if all required files exist."""
    print("\nChecking required files...")
    errors = []

    # Check required files
    project_yaml = project_path / "project.yaml"
    abstract_draft = project_path / "abstract_draft.md"
    methods_draft = project_path / "methods_draft.md"
    results_draft = project_path / "results_draft.md"

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(abstract_draft, "abstract_draft.md"):
        errors.append(f"Missing: {abstract_draft}")
    if not check_file_exists(methods_draft, "methods_draft.md"):
        errors.append(f"Missing: {methods_draft}")
    if not check_file_exists(results_draft, "results_draft.md"):
        errors.append(f"Missing: {results_draft}")

    # Check optional title file
    title_candidates = project_path / "title_candidates.md"
    if title_candidates.exists():
        check_file_exists(title_candidates, "title_candidates.md (optional)")

    # Check optional Introduction file
    introduction_draft = project_path / "introduction_draft.md"
    if introduction_draft.exists():
        check_file_exists(introduction_draft, "introduction_draft.md (optional)")

    # Check optional Discussion file
    discussion_draft = project_path / "discussion_draft.md"
    if discussion_draft.exists():
        check_file_exists(discussion_draft, "discussion_draft.md (optional)")

    return errors


def read_section_content(file_path, section_title):
    """Read section content and remove duplicate top-level heading if present."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Check if first line is the duplicate heading
    lines = content.split("\n")
    if lines and lines[0].strip() == f"# {section_title}":
        # Remove the first line (duplicate heading)
        content = "\n".join(lines[1:]).strip()

    return content


def read_title_candidate(project_path):
    """Read the first title candidate from title_candidates.md if it exists."""
    title_file = project_path / "title_candidates.md"

    if not title_file.exists():
        return None

    try:
        with open(title_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find the first title (after "## Title 1")
        for i, line in enumerate(lines):
            if line.strip().startswith("## Title 1"):
                # The next non-empty line should be the title
                for j in range(i + 1, len(lines)):
                    title_line = lines[j].strip()
                    if title_line and not title_line.startswith("#"):
                        return title_line

        return None
    except Exception as e:
        print(f"  ⚠ Warning: Could not read title from {title_file}: {e}")
        return None


def assemble_manuscript(project_path):
    """Assemble manuscript from section drafts."""
    # Read project name
    project_yaml_path = project_path / "project.yaml"
    with open(project_yaml_path, "r", encoding="utf-8") as f:
        project_data = yaml.safe_load(f)

    project_name = project_data.get("project_name", "Untitled Project")

    # Read title candidate if available
    title_text = read_title_candidate(project_path)
    title_status = "✓ Title: completed" if title_text else "✗ Title: to be generated"
    has_title = title_text is not None

    # Read section contents
    abstract_content = read_section_content(project_path / "abstract_draft.md", "Abstract")
    methods_content = read_section_content(project_path / "methods_draft.md", "Methods")
    results_content = read_section_content(project_path / "results_draft.md", "Results")

    # Read Introduction if available
    introduction_file = project_path / "introduction_draft.md"
    if introduction_file.exists():
        introduction_content = read_section_content(introduction_file, "Introduction")
        introduction_status = "✓ Introduction: completed"
    else:
        introduction_content = "[To be generated]"
        introduction_status = "✗ Introduction: to be generated"

    # Read Discussion if available
    discussion_file = project_path / "discussion_draft.md"
    if discussion_file.exists():
        discussion_content = read_section_content(discussion_file, "Discussion")
        discussion_status = "✓ Discussion: completed"
    else:
        discussion_content = "[To be generated]"
        discussion_status = "✗ Discussion: to be generated"

    # Prepare title section
    if title_text:
        title_section = title_text
    else:
        title_section = "[To be generated]"

    # Assemble manuscript
    manuscript = f"""<!--
Auto-assembled manuscript V1
Generated by SCIWriter

Status:
- {title_status}
- ✓ Abstract: completed
- {introduction_status}
- ✓ Methods: completed
- ✓ Results: completed
- {discussion_status}

Project: {project_name}
-->

# Title

{title_section}

# Abstract

{abstract_content}

# Introduction

{introduction_content}

# Methods

{methods_content}

# Results

{results_content}

# Discussion

{discussion_content}
"""

    return manuscript, has_title, introduction_file.exists(), discussion_file.exists()


def main():
    parser = argparse.ArgumentParser(
        description="Assemble manuscript from section drafts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 assemble_manuscript.py --project /path/to/your/project

This will generate manuscript_v1.md from existing section drafts.
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()

    print("=" * 60)
    print("SCIWriter - Manuscript Assembler")
    print("=" * 60)
    print(f"Project: {project_path}")

    # Check prerequisites
    errors = check_prerequisites(project_path)

    if errors:
        print("\n" + "=" * 60)
        print("PREREQUISITE CHECK FAILED")
        print("=" * 60)
        print("\nMissing files:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease ensure you have generated all section drafts:")
        print("  - abstract_draft.md")
        print("  - methods_draft.md")
        print("  - results_draft.md")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Assemble manuscript
    print("\n" + "=" * 60)
    print("ASSEMBLING MANUSCRIPT")
    print("=" * 60)

    manuscript, has_title, has_introduction, has_discussion = assemble_manuscript(project_path)
    output_path = project_path / "manuscript_v1.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(manuscript)

    print(f"\n✓ Generated: {output_path}")

    # Success summary
    print("\n" + "=" * 60)
    print("ASSEMBLY COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("\nGenerated file:")
    print(f"  {output_path}")

    # Dynamic status messages
    title_msg = "Title (from title_candidates.md)" if has_title else "Title (placeholder)"
    intro_msg = "Introduction (from introduction_draft.md)" if has_introduction else "Introduction (placeholder)"
    discussion_msg = "Discussion (from discussion_draft.md)" if has_discussion else "Discussion (placeholder)"

    print("\nManuscript structure:")
    print(f"  - {title_msg}")
    print("  - Abstract (from abstract_draft.md)")
    print(f"  - {intro_msg}")
    print("  - Methods (from methods_draft.md)")
    print("  - Results (from results_draft.md)")
    print(f"  - {discussion_msg}")

    print("\nNext steps:")
    print(f"  1. Review the manuscript: cat {output_path}")

    # Dynamic next steps based on what's missing
    missing_sections = []
    if not has_title:
        missing_sections.append("Title")
    if not has_introduction:
        missing_sections.append("Introduction")
    if not has_discussion:
        missing_sections.append("Discussion")

    if missing_sections:
        print(f"  2. Generate missing sections: {', '.join(missing_sections)}")
        print("  3. Refine and polish the manuscript")
    else:
        print("  2. Refine and polish the manuscript")


if __name__ == "__main__":
    main()
