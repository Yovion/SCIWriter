#!/usr/bin/env python3
import sys
import json
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


def check_prerequisites(project_path, prompts_dir):
    """Check if all required files exist."""
    print("\nChecking project files...")
    errors = []

    # Check project-level files
    project_yaml = project_path / "project.yaml"
    storyline = project_path / "storyline.md"
    results_draft = project_path / "results_draft.md"
    methods_draft = project_path / "methods_draft.md"

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")
    if not check_file_exists(results_draft, "results_draft.md"):
        errors.append(f"Missing: {results_draft}")
    if not check_file_exists(methods_draft, "methods_draft.md"):
        errors.append(f"Missing: {methods_draft}")

    # Check prompt template
    print("\nChecking prompt template...")
    abstract_writer = prompts_dir / "abstract_writer.md"

    if not check_file_exists(abstract_writer, "abstract_writer.md"):
        errors.append(f"Missing: {abstract_writer}")

    return errors


def generate_manifest(project_path, prompts_dir):
    """Generate abstract_manifest.json."""
    project_yaml_path = project_path / "project.yaml"

    with open(project_yaml_path, "r", encoding="utf-8") as f:
        project_data = yaml.safe_load(f)

    project_name = project_data.get("project_name", "")
    results_order = project_data.get("results_order", [])
    main_text_modules = project_data.get("main_text_modules", [])

    manifest = {
        "project_name": project_name,
        "project_path": str(project_path),
        "results_order": results_order,
        "main_text_modules": main_text_modules,
        "prompts": {
            "abstract_writer": str(prompts_dir / "abstract_writer.md")
        },
        "input_files": {
            "storyline_path": str(project_path / "storyline.md"),
            "methods_draft_path": str(project_path / "methods_draft.md"),
            "results_draft_path": str(project_path / "results_draft.md")
        }
    }

    return manifest


def generate_prompt(project_path, manifest):
    """Generate abstract_prompt.txt."""
    project_name = manifest["project_name"]

    prompt = f"""请按以下顺序读取文件：

1. {project_path}/project.yaml
2. {manifest["input_files"]["storyline_path"]}
3. {manifest["prompts"]["abstract_writer"]}
4. {manifest["input_files"]["methods_draft_path"]}
5. {manifest["input_files"]["results_draft_path"]}

然后写一份 SCI 风格的 Abstract 初稿，要求：
1. 用英文
2. 用 markdown 输出
3. 基于现有 storyline、Methods 和 Results 写作
4. 包含以下部分：
   - Background（简短，1-2句）
   - Methods（简要描述分析流程）
   - Results（总结关键发现）
   - Conclusion（保守结论）
5. 不要编造数值
6. 结论要保守，不要过度推断
7. 不要写机制化和夸张表达
8. 保持适合生物信息学/转录组生物标志物研究的风格
9. 语气正式、克制、像论文 Abstract
10. 保存到：
{project_path}/abstract_draft.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Abstract writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_abstract.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate abstract_manifest.json
  3. Generate abstract_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Abstract Writing Preparation")
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
        print("  - methods_draft.md (using write_methods.py)")
        print("  - results_draft.md (using write_results.py)")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)

    manifest = generate_manifest(project_path, prompts_dir)
    manifest_path = project_path / "abstract_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Input files: {len(manifest['input_files'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "abstract_prompt.txt"

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n✓ Generated: {prompt_path}")

    # Success summary
    print("\n" + "=" * 60)
    print("PREPARATION COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("\nGenerated files:")
    print(f"  1. {manifest_path}")
    print(f"  2. {prompt_path}")

    print("\nNext steps:")
    print(f"  1. Review the prompt: cat {prompt_path}")
    print(f"  2. Copy the prompt content and send it to Claude Code")
    print(f"  3. Claude will generate: {project_path}/abstract_draft.md")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
