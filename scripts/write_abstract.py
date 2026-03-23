#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
from pathlib import Path

# Try to import LLM client (optional dependency)
try:
    from llm_client import call, is_available as llm_available
    LLM_AVAILABLE = llm_available()
except ImportError:
    LLM_AVAILABLE = False


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

    # Check optional project_brief_resolved.json
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

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

    # Add project_brief_resolved_path if it exists
    project_brief_path = project_path / "project_brief_resolved.json"
    if project_brief_path.exists():
        manifest["project_brief_resolved_path"] = str(project_brief_path)

    return manifest


def generate_prompt(project_path, manifest):
    """Generate abstract_prompt.txt."""
    project_name = manifest["project_name"]

    # Build file reading order
    file_list = [
        f"1. {project_path}/project.yaml",
        f"2. {manifest['input_files']['storyline_path']}",
        f"3. {manifest['prompts']['abstract_writer']}"
    ]
    file_index = 4

    # Add project_brief_resolved.json if it exists
    has_project_brief = "project_brief_resolved_path" in manifest
    if has_project_brief:
        file_list.append(f"{file_index}. {manifest['project_brief_resolved_path']}")
        file_index += 1

    file_list.append(f"{file_index}. {manifest['input_files']['methods_draft_path']}")
    file_index += 1
    file_list.append(f"{file_index}. {manifest['input_files']['results_draft_path']}")

    prompt = f"""请按以下顺序读取文件：

{chr(10).join(file_list)}

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
9. 语气正式、克制、像论文 Abstract"""

    # Add project_brief_resolved.json specific requirements if it exists
    if has_project_brief:
        prompt += """
10. 如果 project_brief_resolved.json 中提供了 disease.name、study_focus.main_theme 或 preferred_emphasis，应优先参考这些信息
11. 如果 project_brief_resolved.json 中有 avoid_overstatement，摘要结论不得违反这些限制
12. 但摘要的 Results 和 Conclusion 必须严格以真实结果文件为准，不要编造"""
        prompt += f"""
13. 保存到：
{project_path}/abstract_draft.md
"""
    else:
        prompt += f"""
10. 保存到：
{project_path}/abstract_draft.md
"""

    return prompt


def generate_execute_prompt(project_path, manifest):
    """Generate execution-specific prompt with inline content."""
    project_path = Path(project_path)

    # Read project.yaml
    project_yaml_path = project_path / "project.yaml"
    with open(project_yaml_path, "r", encoding="utf-8") as f:
        project_yaml_content = f.read()

    # Read storyline.md
    storyline_path = project_path / "storyline.md"
    with open(storyline_path, "r", encoding="utf-8") as f:
        storyline_content = f.read()

    # Read methods_draft.md
    methods_draft_path = Path(manifest["input_files"]["methods_draft_path"])
    with open(methods_draft_path, "r", encoding="utf-8") as f:
        methods_content = f.read()

    # Read results_draft.md
    results_draft_path = Path(manifest["input_files"]["results_draft_path"])
    with open(results_draft_path, "r", encoding="utf-8") as f:
        results_content = f.read()

    # Build prompt with inline content
    prompt = f"""You are writing an Abstract section for a scientific paper.

PROJECT CONFIGURATION:
```yaml
{project_yaml_content}
```

STORYLINE:
{storyline_content}

METHODS DRAFT:
{methods_content}

RESULTS DRAFT:
{results_content}
"""

    # Add project_brief_resolved.json if it exists
    if "project_brief_resolved_path" in manifest:
        brief_path = Path(manifest["project_brief_resolved_path"])
        if brief_path.exists():
            with open(brief_path, "r", encoding="utf-8") as f:
                brief_content = f.read()
            prompt += f"\nPROJECT BRIEF:\n{brief_content}\n"

    # Add strict execution requirements
    prompt += """

---

INSTRUCTIONS:
Write an Abstract section in markdown format.

REQUIREMENTS:
1. Output ONLY the Abstract text in markdown (no explanations, no meta-commentary)
2. Write in English
3. Structure: Background (1-2 sentences) → Methods (brief) → Results (key findings) → Conclusion (conservative)
4. Use ONLY information from the Methods and Results drafts above
5. Do NOT fabricate numbers, trends, or findings not present in Results
6. Do NOT output <function_calls> or XML tags
7. Do NOT describe your reading process
8. Use formal, scientific writing style
9. Keep conclusions conservative - no overstatements
10. Do NOT use words like "novel", "breakthrough", "revolutionary"
11. If project_brief is provided, use it for context only, NOT as results data
12. Total length: 200-300 words

Output the Abstract section now:"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Abstract writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_abstract.py --project /path/to/your/project
  python3 write_abstract.py --project /path/to/your/project --execute

This will:
  1. Check all required files exist
  2. Generate abstract_manifest.json
  3. Generate abstract_prompt.txt
  4. (with --execute) Directly generate abstract_draft.md using LLM
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--execute", action="store_true", help="Execute LLM to generate abstract_draft.md directly")
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

    # Execute mode: directly generate abstract_draft.md
    if args.execute:
        print("\n" + "=" * 60)
        print("EXECUTING LLM TO GENERATE ABSTRACT DRAFT")
        print("=" * 60)

        if not LLM_AVAILABLE:
            print("\n✗ LLM client not available")
            print("  Cannot execute in --execute mode")
            print("  Please use manual mode or check llm_client.py configuration")
            sys.exit(1)

        abstract_draft_path = project_path / "abstract_draft.md"

        try:
            # Generate execution-specific prompt with inline content
            print("\n✓ Generating execution prompt with inline content...")
            execute_prompt = generate_execute_prompt(project_path, manifest)
            print(f"  Prompt length: {len(execute_prompt)} chars")

            print("\n✓ Calling LLM...")
            abstract_text = call(execute_prompt, max_tokens=1500)

            print("✓ LLM response received")

            # Save to abstract_draft.md
            with open(abstract_draft_path, "w", encoding="utf-8") as f:
                f.write(abstract_text)

            print(f"✓ Saved: {abstract_draft_path}")
            print(f"  - Length: {len(abstract_text.split())} words")

            # Success summary for execute mode
            print("\n" + "=" * 60)
            print("EXECUTION COMPLETED SUCCESSFULLY")
            print("=" * 60)

            print("\nGenerated files:")
            print(f"  1. {manifest_path}")
            print(f"  2. {prompt_path} (debug artifact)")
            print(f"  3. {abstract_draft_path}")

            print("\nNext steps:")
            print(f"  1. Review the draft: cat {abstract_draft_path}")
            print(f"  2. Proceed to next writing step")

        except Exception as e:
            print(f"\n✗ LLM execution failed: {e}")
            print("  Prompt file is still available for manual use")
            sys.exit(1)

        return

    # Success summary (non-execute mode)
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
