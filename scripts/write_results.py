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

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")

    # Check optional project_brief_resolved.json
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

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

    # Add project_brief_resolved_path if it exists
    project_brief_path = project_path / "project_brief_resolved.json"
    if project_brief_path.exists():
        manifest["project_brief_resolved_path"] = str(project_brief_path)

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

    # Add project_brief_resolved.json if it exists
    file_num = 5
    has_project_brief = "project_brief_resolved_path" in manifest
    if has_project_brief:
        prompt += f"{file_num}. {manifest['project_brief_resolved_path']}\n"
        file_num += 1

    # Add module files
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
5. 语气正式、克制、像论文 Results"""

    # Add project_brief usage requirements
    if has_project_brief:
        prompt += """
6. project_brief_resolved.json 可用于帮助把握疾病背景、主线和避免跑题
7. 但 Results 必须严格以真实结果文件、表格、证据和模块输出为准
8. 不要把 brief 中的意图性描述写成结果事实，不要编造数值、趋势或发现"""

    prompt += f"""
保存到：
{project_path}/results_draft.md
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

    # Build prompt with inline content
    prompt = f"""You are writing a Results section for a scientific paper.

PROJECT CONFIGURATION:
```yaml
{project_yaml_content}
```

STORYLINE:
{storyline_content}
"""

    # Add project_brief_resolved.json if it exists
    if "project_brief_resolved_path" in manifest:
        brief_path = Path(manifest["project_brief_resolved_path"])
        if brief_path.exists():
            with open(brief_path, "r", encoding="utf-8") as f:
                brief_content = f.read()
            prompt += f"\nPROJECT BRIEF:\n{brief_content}\n"

    # Add each module's context and evidence
    for module in manifest["modules"]:
        module_name = module["module_name"]

        # Read module_context.json
        module_context_path = Path(module["module_context_path"])
        if module_context_path.exists():
            with open(module_context_path, "r", encoding="utf-8") as f:
                module_context = json.load(f)
            prompt += f"\n\n---\nMODULE: {module_name}\n"
            prompt += f"Context:\n{json.dumps(module_context, indent=2)}\n"

        # Read evidence.csv (limit to prevent token overflow)
        evidence_path = Path(module["evidence_path"])
        if evidence_path.exists():
            with open(evidence_path, "r", encoding="utf-8") as f:
                evidence_lines = f.readlines()[:50]  # Limit to first 50 lines
            prompt += f"\nEvidence (first 50 lines):\n{''.join(evidence_lines)}\n"

    # Add strict execution requirements
    prompt += """

---

INSTRUCTIONS:
Write a Results section in markdown format.

REQUIREMENTS:
1. Output ONLY the Results text in markdown (no explanations, no meta-commentary)
2. Write in English
3. Organize by results_order modules
4. Use ONLY the provided evidence and data above
5. Do NOT fabricate numbers, trends, or findings
6. Do NOT output <function_calls> or XML tags
7. Do NOT describe your reading process
8. Use formal, scientific writing style
9. Focus on facts from the provided content
10. If project_brief is provided, use it for context only, NOT as results data

Output the Results section now:"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Results writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_results.py --project /path/to/your/project
  python3 write_results.py --project /path/to/your/project --execute

This will:
  1. Check all required files exist
  2. Generate results_manifest.json
  3. Generate results_prompt.txt
  4. (with --execute) Directly generate results_draft.md using LLM
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--execute", action="store_true", help="Execute LLM to generate results_draft.md directly")
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

    # Execute mode: directly generate results_draft.md
    if args.execute:
        print("\n" + "=" * 60)
        print("EXECUTING LLM TO GENERATE RESULTS DRAFT")
        print("=" * 60)

        if not LLM_AVAILABLE:
            print("\n✗ LLM client not available")
            print("  Cannot execute in --execute mode")
            print("  Please use manual mode or check llm_client.py configuration")
            sys.exit(1)

        results_draft_path = project_path / "results_draft.md"

        try:
            # Generate execution-specific prompt with inline content
            print("\n✓ Generating execution prompt with inline content...")
            execute_prompt = generate_execute_prompt(project_path, manifest)
            print(f"  Prompt length: {len(execute_prompt)} chars")

            print("\n✓ Calling LLM...")
            results_text = call(execute_prompt, max_tokens=3000)

            print("✓ LLM response received")

            # Save to results_draft.md
            with open(results_draft_path, "w", encoding="utf-8") as f:
                f.write(results_text)

            print(f"✓ Saved: {results_draft_path}")
            print(f"  - Length: {len(results_text.split())} words")

            # Success summary for execute mode
            print("\n" + "=" * 60)
            print("EXECUTION COMPLETED SUCCESSFULLY")
            print("=" * 60)

            print("\nGenerated files:")
            print(f"  1. {manifest_path}")
            print(f"  2. {prompt_path} (debug artifact)")
            print(f"  3. {results_draft_path}")

            print("\nNext steps:")
            print(f"  1. Review the draft: cat {results_draft_path}")
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
    print(f"  3. Claude will generate: {project_path}/results_draft.md")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
