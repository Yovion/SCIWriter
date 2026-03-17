#!/usr/bin/env python3
import sys
import argparse
import subprocess
from pathlib import Path


def check_prerequisites(project_path, scripts_dir):
    """Check if project path and required scripts exist."""
    errors = []

    # Check project path
    if not project_path.exists():
        errors.append(f"Project path does not exist: {project_path}")
    elif not project_path.is_dir():
        errors.append(f"Project path is not a directory: {project_path}")

    # Check required scripts
    required_scripts = [
        "scan_project.py",
        "build_module_context.py",
        "build_evidence.py",
        "build_project_files.py"
    ]

    for script in required_scripts:
        script_path = scripts_dir / script
        if not script_path.exists():
            errors.append(f"Required script not found: {script_path}")

    return errors


def run_script(script_path, project_path, step_num, total_steps):
    """Run a single script and handle errors."""
    script_name = script_path.name
    print(f"\n[{step_num}/{total_steps}] Running {script_name}...")
    print(f"Command: python3 {script_path} --project {project_path}")
    print("-" * 60)

    try:
        result = subprocess.run(
            ["python3", str(script_path), "--project", str(project_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        print(f"✓ {script_name} completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ {script_name} failed with exit code {e.returncode}")
        print("\nSTDOUT:")
        print(e.stdout)
        print("\nSTDERR:")
        print(e.stderr)
        return False


def collect_generated_files(project_path):
    """Collect paths of generated files."""
    files = {
        "project_level": [],
        "module_level": {}
    }

    # Project-level files
    project_scan = project_path / "project_scan.json"
    project_yaml = project_path / "project.yaml"
    storyline = project_path / "storyline.md"

    if project_scan.exists():
        files["project_level"].append(project_scan)
    if project_yaml.exists():
        files["project_level"].append(project_yaml)
    if storyline.exists():
        files["project_level"].append(storyline)

    # Module-level files
    for item in project_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            module_files = []

            module_context = item / "module_context.json"
            evidence = item / "evidence.csv"

            if module_context.exists():
                module_files.append(module_context)
            if evidence.exists():
                module_files.append(evidence)

            if module_files:
                files["module_level"][item.name] = module_files

    return files


def print_summary(files):
    """Print summary of generated files."""
    print("\n" + "=" * 60)
    print("GENERATED FILES")
    print("=" * 60)

    print("\nProject-level files:")
    for f in files["project_level"]:
        print(f"  ✓ {f}")

    if files["module_level"]:
        print("\nModule-level files:")
        for module_name, module_files in sorted(files["module_level"].items()):
            print(f"  {module_name}/")
            for f in module_files:
                print(f"    ✓ {f.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Run the complete SCIWriter pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 run_pipeline.py --project /path/to/your/project

This will execute all pipeline steps in order:
  1. scan_project.py
  2. build_module_context.py
  3. build_evidence.py
  4. build_project_files.py
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    scripts_dir = Path(__file__).parent

    print("=" * 60)
    print("SCIWriter Pipeline")
    print("=" * 60)
    print(f"Project: {project_path}")
    print(f"Scripts: {scripts_dir}")

    # Check prerequisites
    print("\nChecking prerequisites...")
    errors = check_prerequisites(project_path, scripts_dir)
    if errors:
        print("\n✗ Prerequisites check failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("✓ All prerequisites satisfied")

    # Define pipeline steps
    steps = [
        ("scan_project.py", "Scan project structure"),
        ("build_module_context.py", "Build module contexts"),
        ("build_evidence.py", "Build evidence files"),
        ("build_project_files.py", "Build project-level files")
    ]

    # Run pipeline
    print("\n" + "=" * 60)
    print("RUNNING PIPELINE")
    print("=" * 60)

    for i, (script_name, description) in enumerate(steps, 1):
        script_path = scripts_dir / script_name
        success = run_script(script_path, project_path, i, len(steps))

        if not success:
            print("\n" + "=" * 60)
            print("PIPELINE FAILED")
            print("=" * 60)
            print(f"Failed at step {i}/{len(steps)}: {script_name}")
            sys.exit(1)

    # Collect and display generated files
    files = collect_generated_files(project_path)
    print_summary(files)

    # Success
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nAll files generated in: {project_path}")


if __name__ == "__main__":
    main()
