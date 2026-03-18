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
    introduction_draft = project_path / "introduction_draft.md"

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")
    if not check_file_exists(abstract_draft, "abstract_draft.md"):
        errors.append(f"Missing: {abstract_draft}")
    if not check_file_exists(results_draft, "results_draft.md"):
        errors.append(f"Missing: {results_draft}")
    if not check_file_exists(introduction_draft, "introduction_draft.md"):
        errors.append(f"Missing: {introduction_draft}")

    # Check optional files
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

    title_candidates = project_path / "title_candidates.md"
    if title_candidates.exists():
        check_file_exists(title_candidates, "title_candidates.md (optional)")

    # Check prompt template
    print("\nChecking prompt template...")
    discussion_writer = prompts_dir / "discussion_writer.md"

    if not check_file_exists(discussion_writer, "discussion_writer.md"):
        errors.append(f"Missing: {discussion_writer}")

    return errors


def generate_manifest(project_path, prompts_dir):
    """Generate discussion_manifest.json."""
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
            "discussion_writer": str(prompts_dir / "discussion_writer.md")
        },
        "input_files": {
            "storyline_path": str(project_path / "storyline.md"),
            "abstract_draft_path": str(project_path / "abstract_draft.md"),
            "results_draft_path": str(project_path / "results_draft.md"),
            "introduction_draft_path": str(project_path / "introduction_draft.md")
        }
    }

    # Add project_brief_resolved_path as top-level field if it exists
    project_brief_path = project_path / "project_brief_resolved.json"
    if project_brief_path.exists():
        manifest["project_brief_resolved_path"] = str(project_brief_path)

    # Add title_candidates_path as top-level field if it exists
    title_candidates_path = project_path / "title_candidates.md"
    if title_candidates_path.exists():
        manifest["title_candidates_path"] = str(title_candidates_path)

    return manifest


def generate_prompt(project_path, manifest):
    """Generate discussion_prompt.txt."""
    project_name = manifest["project_name"]
    detected_route = manifest["detected_route"]

    # Build file reading order
    file_list = [
        f"1. {project_path}/project.yaml",
        f"2. {manifest['input_files']['storyline_path']}"
    ]

    file_index = 3

    # Add project_brief_resolved.json if it exists
    has_project_brief = "project_brief_resolved_path" in manifest
    if has_project_brief:
        file_list.append(f"{file_index}. {manifest['project_brief_resolved_path']}")
        file_index += 1

    # Add abstract, results, introduction
    file_list.extend([
        f"{file_index}. {manifest['input_files']['abstract_draft_path']}",
        f"{file_index + 1}. {manifest['input_files']['results_draft_path']}",
        f"{file_index + 2}. {manifest['input_files']['introduction_draft_path']}"
    ])
    file_index += 3

    # Add title_candidates.md if it exists
    has_title_candidates = "title_candidates_path" in manifest
    if has_title_candidates:
        file_list.append(f"{file_index}. {manifest['title_candidates_path']}")
        file_index += 1

    # Add prompt template last
    file_list.append(f"{file_index}. {manifest['prompts']['discussion_writer']}")

    prompt = f"""请按以下顺序读取文件：

{chr(10).join(file_list)}

然后写一份 SCI 风格的 Discussion 初稿，要求：
1. 用英文
2. 用 markdown 输出
3. 基于现有 storyline、abstract、results 和 introduction 写作
4. 结构：
   - 第一段：概述主要发现（不要机械重复 Results 或 Abstract 的句式和数字，写成 Discussion 的 opening paragraph）
   - 第二段：结合已有研究解释结果意义（必须明确体现 DEG → Cox regression 的分析路径，不要只写空泛的 "consistent with previous studies"）
   - 第三段：方法路径和结果的潜在价值（具体解释为什么 DEG → survival analysis 是合理的候选预后基因发现策略，不要只说 "future validation"）
   - 第四段：局限性与总结
5. 不要夸张
6. 不要写机制化硬结论
7. 不要写 "novel mechanism"、"breakthrough"、"therapeutic target"、"clinical application" 等高风险表达
8. 避免使用 "novel"、"innovative"、"significant advance" 等词
9. 风格适合生物信息学/转录组生物标志物研究
10. 不要编造文献引用（如需要可用 [ref] 占位）
11. 强调"候选"、"warrant further investigation"、"potential"、"may suggest"
12. 语气保守、客观、正式
13. 第四段必须包含三个具体局限性：
    - retrospective public-data-based analysis
    - lack of independent cohort validation
    - lack of experimental validation
14. 减少模板化表达，避免：
    - "is consistent with previous investigations"
    - "provides a framework"
    - "providing a foundation for future validation studies"
    - 其他空泛的 generic discussion phrases
15. Discussion 长度：4 段，简洁聚焦
16. 基于项目的 detected_route: {detected_route}
"""

    # Add project_brief_resolved.json specific requirements if it exists
    if has_project_brief:
        prompt += """16. 如果 project_brief_resolved.json 中有 avoid_overstatement，Discussion 不得违反这些限制
17. 如果 project_brief_resolved.json 中有 preferred_emphasis，Discussion 应体现这些重点
"""

    # Add title alignment requirement if title exists
    if has_title_candidates:
        next_num = 18 if has_project_brief else 16
        prompt += f"""{next_num}. Discussion 的总结应与 title_candidates.md 中的标题保持一致
"""

    prompt += f"""
保存到：
{project_path}/discussion_draft.md
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Discussion writing inputs and generate prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 write_discussion.py --project /path/to/your/project

This will:
  1. Check all required files exist
  2. Generate discussion_manifest.json
  3. Generate discussion_prompt.txt
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent
    prompts_dir = scripts_dir.parent / "prompts"

    print("=" * 60)
    print("SCIWriter - Discussion Writing Preparation")
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
        print("  - abstract_draft.md (using write_abstract.py)")
        print("  - results_draft.md (using write_results.py)")
        print("  - introduction_draft.md (using write_introduction.py)")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Generate manifest
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)

    manifest = generate_manifest(project_path, prompts_dir)
    manifest_path = project_path / "discussion_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated: {manifest_path}")
    print(f"  - Project: {manifest['project_name']}")
    print(f"  - Route: {manifest['detected_route']}")
    print(f"  - Input files: {len(manifest['input_files'])}")

    # Generate prompt
    prompt = generate_prompt(project_path, manifest)
    prompt_path = project_path / "discussion_prompt.txt"

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
    print(f"  3. Claude will generate: {project_path}/discussion_draft.md")

    print("\nOr use this command to view the prompt:")
    print(f"  cat {prompt_path}")


if __name__ == "__main__":
    main()
