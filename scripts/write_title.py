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

    # Check prompt template
    print("\nChecking prompt template...")
    title_writer = prompts_dir / "title_writer.md"

    if not check_file_exists(title_writer, "title_writer.md"):
        errors.append(f"Missing: {title_writer}")

    return errors


def generate_manifest(project_path, prompts_dir):
    """Generate title_manifest.json."""
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
        "results_order": results_order,
        "main_text_modules": main_text_modules,
        "prompts": {
            "title_writer": str(prompts_dir / "title_writer.md")
        },
        "input_files": {
            "storyline_path": str(project_path / "storyline.md"),
            "abstract_draft_path": str(project_path / "abstract_draft.md"),
            "results_draft_path": str(project_path / "results_draft.md")
        }
    }

    return manifest


def generate_prompt(project_path, manifest):
    """Generate title_prompt.txt."""
    project_name = manifest["project_name"]
    detected_route = manifest["detected_route"]

    prompt = f"""请按以下顺序读取文件：

1. {project_path}/project.yaml
2. {manifest["input_files"]["storyline_path"]}
3. {manifest["prompts"]["title_writer"]}
4. {manifest["input_files"]["abstract_draft_path"]}
5. {manifest["input_files"]["results_draft_path"]}

然后生成 3 个 SCI 风格的英文标题候选，要求：
1. 用英文
2. 用 markdown 输出
3. 每个标题单独编号（Title 1, Title 2, Title 3）
4. 标题应反映研究对象、分析路线和研究目标
5. 不要夸张
6. 不要写机制化结论
7. 不要写 "novel mechanism"、"new therapeutic target" 等高风险表达
8. 避免使用 "novel"、"innovative"、"breakthrough" 等词
9. 风格适合生物信息学/转录组生物标志物研究
10. 标题长度适中（10-20 个单词）
11. 基于项目的 detected_route: {detected_route}
12. 保存到：
{project_path}/title_candidates.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare title generation inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_title.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate title_manifest.json
  3. Generate title_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Title Generation Preparation")
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
        print("  - abstract_draft.md")
        print("  - results_draft.md")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)

    manifest = generate_manifest(project_path, prompts_dir)
    manifest_path = project_path / "title_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Route: {manifest['detected_route']}")
    print(f"  - Input files: {len(manifest['input_files'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "title_prompt.txt"

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
    print(f"  3. Claude will generate: {project_path}/title_candidates.md")
    print(f"  4. Review the 3 title candidates and select the best one")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
