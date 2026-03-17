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

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")

    # If project.yaml exists, check module files
    if project_yaml.exists():
        with open(project_yaml, "r", encoding="utf-8") as f:
            project_data = yaml.safe_load(f)

        results_order = project_data.get("results_order", [])
        print(f"\nChecking {len(results_order)} modules...")

        for module_name in results_order:
            module_dir = project_path / module_name
            module_context = module_dir / "module_context.json"
            evidence = module_dir / "evidence.csv"

            if not check_file_exists(module_context, f"{module_name}/module_context.json"):
                errors.append(f"Missing: {module_context}")
            if not check_file_exists(evidence, f"{module_name}/evidence.csv"):
                errors.append(f"Missing: {evidence}")

    # Check prompt templates
    print("\nChecking prompt templates...")
    results_writer = prompts_dir / "results_writer.md"
    module_rules = prompts_dir / "module_rules.md"

    if not check_file_exists(results_writer, "results_writer.md"):
        errors.append(f"Missing: {results_writer}")
    if not check_file_exists(module_rules, "module_rules.md"):
        errors.append(f"Missing: {module_rules}")

    return errors


def generate_manifest(project_path, prompts_dir):
    """Generate results_manifest.json."""
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
            "results_writer": str(prompts_dir / "results_writer.md"),
            "module_rules": str(prompts_dir / "module_rules.md")
        },
        "modules": []
    }

    for module_name in results_order:
        module_dir = project_path / module_name
        module_info = {
            "module_name": module_name,
            "module_context_path": str(module_dir / "module_context.json"),
            "evidence_path": str(module_dir / "evidence.csv")
        }
        manifest["modules"].append(module_info)

    return manifest


def generate_prompt(project_path, manifest):
    """Generate results_prompt.txt."""
    project_name = manifest["project_name"]
    results_order = manifest["results_order"]

    prompt = f"""请按以下顺序读取文件：

1. {project_path}/project.yaml
2. {project_path}/storyline.md
3. {manifest["prompts"]["results_writer"]}
4. {manifest["prompts"]["module_rules"]}
"""

    # Add module files
    file_num = 5
    for module in manifest["modules"]:
        module_name = module["module_name"]
        prompt += f"{file_num}. {module['module_context_path']}\n"
        file_num += 1
        prompt += f"{file_num}. {module['evidence_path']}\n"
        file_num += 1

    prompt += f"""
如果有必要，再查看这些原始文件：
"""

    # Add original result files
    for module in manifest["modules"]:
        module_name = module["module_name"]
        module_dir = project_path / module_name

        # Read module_context to get key_result_tables and scripts
        with open(module["module_context_path"], "r", encoding="utf-8") as f:
            context = json.load(f)

        key_result_tables = context.get("key_result_tables", [])
        scripts = context.get("scripts", [])

        for table in key_result_tables:
            if table != "evidence.csv":  # Skip evidence.csv as it's already listed
                prompt += f"- {module_dir}/{table}\n"

        for script in scripts:
            prompt += f"- {module_dir}/{script}\n"

    prompt += f"""
然后写一份 SCI 风格的 Results 初稿，要求：
1. 用英文
2. 用 markdown 输出
3. 按 results_order 顺序分成小节
4. 只使用已有证据，不要编造数值
5. 语气正式、克制、像论文 Results
6. 保存到：
{project_path}/results_draft.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Results writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_results.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate results_manifest.json
  3. Generate results_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Results Writing Preparation")
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
        print("\nPlease run the pipeline first:")
        print("  python3 run_pipeline.py --project <project_path>")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)

    manifest = generate_manifest(project_path, prompts_dir)
    manifest_path = project_path / "results_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Modules: {len(manifest['modules'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "results_prompt.txt"

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
    print(f"  3. Claude will generate: {project_path}/results_draft.md")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
