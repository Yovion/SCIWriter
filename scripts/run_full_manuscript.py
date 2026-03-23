#!/usr/bin/env python3
"""
SCIWriter - Full Manuscript Orchestrator

Runs the complete writing pipeline in order:
  1. run_pipeline.py          (scan + module context + evidence + project files)
  2. resolve_project_brief.py
  3. search_pubmed.py --purpose introduction
  4. write_title.py --execute
  5. build_methods_context.py
  6. write_methods.py --execute
  7. write_results.py         (prompt-only; results_draft.md must already exist)
  8. write_abstract.py --execute
  9. write_introduction.py
 10. search_pubmed.py --purpose discussion
 11. write_discussion.py
 12. assemble_manuscript.py

Usage:
  python3 run_full_manuscript.py --project /path/to/project --user-brief "..."
  python3 run_full_manuscript.py --project /path/to/project --user-brief-file brief.txt
  python3 run_full_manuscript.py --project /path/to/project --user-brief "..." --start-from 5
"""

import sys
import argparse
import subprocess
from pathlib import Path


def run_step(label, cmd, step_num, total):
    """Run one step. Returns True on success, False on failure."""
    print(f"\n{'='*60}")
    print(f"[{step_num}/{total}] RUNNING: {label}")
    print(f"  cmd: {' '.join(str(c) for c in cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            check=True,
            text=True
        )
        print(f"\n✓ SUCCESS: {label}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ FAILED: {label}  (exit code {e.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="SCIWriter full manuscript pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--user-brief", help="Natural language project description (inline)")
    parser.add_argument("--user-brief-file", help="Path to file containing project description")
    parser.add_argument(
        "--start-from", type=int, default=1, metavar="N",
        help="Skip steps before N (useful for resuming after a failure)"
    )
    args = parser.parse_args()

    # Brief is mandatory — exactly one of the two forms must be provided
    if not args.user_brief and not args.user_brief_file:
        parser.error(
            "A project brief is required.\n"
            "  Provide --user-brief \"...\" (inline text)\n"
            "  or     --user-brief-file <path>"
        )
    if args.user_brief and args.user_brief_file:
        parser.error("Provide either --user-brief or --user-brief-file, not both.")

    project = Path(args.project).resolve()
    scripts = Path(__file__).parent
    py = sys.executable

    if not project.exists():
        print(f"✗ Project path not found: {project}")
        sys.exit(1)

    # Build brief forwarding args for resolve_project_brief.py
    if args.user_brief:
        brief_source = f"inline: \"{args.user_brief[:60]}{'...' if len(args.user_brief) > 60 else ''}\""
        brief_args = ["--user-brief", args.user_brief]
    else:
        brief_source = f"file: {args.user_brief_file}"
        brief_args = ["--user-brief-file", args.user_brief_file]

    # ----------------------------------------------------------------
    # Step definitions: (label, [cmd tokens])
    # ----------------------------------------------------------------
    steps = [
        ("run_pipeline (scan + context + evidence)",
         [py, scripts / "run_pipeline.py", "--project", project]),

        ("resolve_project_brief",
         [py, scripts / "resolve_project_brief.py", "--project", project] + brief_args),

        ("search_pubmed --purpose introduction",
         [py, scripts / "search_pubmed.py", "--project", project, "--purpose", "introduction"]),

        ("build_methods_context",
         [py, scripts / "build_methods_context.py", "--project", project]),

        ("write_methods --execute",
         [py, scripts / "write_methods.py", "--project", project, "--execute"]),

        ("write_results --execute",
         [py, scripts / "write_results.py", "--project", project, "--execute"]),

        ("write_abstract --execute",
         [py, scripts / "write_abstract.py", "--project", project, "--execute"]),

        ("write_title --execute",
         [py, scripts / "write_title.py", "--project", project, "--execute"]),

        ("write_introduction",
         [py, scripts / "write_introduction.py", "--project", project]),

        ("search_pubmed --purpose discussion",
         [py, scripts / "search_pubmed.py", "--project", project, "--purpose", "discussion"]),

        ("write_discussion",
         [py, scripts / "write_discussion.py", "--project", project]),

        ("assemble_manuscript",
         [py, scripts / "assemble_manuscript.py", "--project", project]),
    ]

    total = len(steps)
    results = {}  # step_num (1-based) -> (label, success)

    print("=" * 60)
    print("SCIWriter - Full Manuscript Pipeline")
    print("=" * 60)
    print(f"Project : {project}")
    print(f"Brief   : {brief_source}")
    print(f"Steps   : {total}")
    if args.start_from > 1:
        print(f"Resuming from step {args.start_from}")

    for i, (label, cmd) in enumerate(steps, start=1):
        if i < args.start_from:
            results[i] = (label, "skipped")
            continue

        ok = run_step(label, cmd, i, total)
        results[i] = (label, "ok" if ok else "failed")

        if not ok:
            print(f"\n⚠  Pipeline stopped at step {i}: {label}")
            print(f"   Fix the issue and resume with: --start-from {i}")
            break

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)

    for num, (label, status) in results.items():
        icon = {"ok": "✓", "failed": "✗", "skipped": "–"}.get(status, "?")
        print(f"  {icon} [{num:2d}] {label}")

    manuscript = project / "manuscript_v1.md"
    print()
    if manuscript.exists():
        size_kb = manuscript.stat().st_size // 1024
        print(f"✓ manuscript_v1.md generated ({size_kb} KB): {manuscript}")
    else:
        print(f"✗ manuscript_v1.md NOT found: {manuscript}")

    failed = [num for num, (_, s) in results.items() if s == "failed"]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
