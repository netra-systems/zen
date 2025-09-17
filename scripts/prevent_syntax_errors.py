#!/usr/bin/env python3
"""
SYNTAX ERROR PREVENTION SYSTEM
Issue #1277 Infrastructure Hardening Solution

This script provides syntax validation for preventing future syntax errors
and ensuring the health of the codebase before commits.
"""

import ast
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse
import json


class SyntaxPreventionSystem:
    """Comprehensive syntax error prevention system"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_file = project_root / ".syntax-prevention-config.json"
        self.load_config()

    def load_config(self):
        """Load configuration for syntax prevention"""
        default_config = {
            "excluded_patterns": [
                "*/backup/*",
                "*/backups/*",
                "*/node_modules/*",
                "*/.git/*",
                "*/__pycache__/*",
                "*.pyc",
                "*/venv/*",
                "*/env/*"
            ],
            "critical_directories": [
                "tests",
                "netra_backend",
                "auth_service",
                "frontend",
                "scripts"
            ],
            "max_errors_allowed": 50,
            "strict_mode": False
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")

        self.config = default_config

    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from validation"""
        file_str = str(file_path)

        for pattern in self.config["excluded_patterns"]:
            if self._match_pattern(file_str, pattern):
                return True

        return False

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for exclusions"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def validate_file_syntax(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate syntax of a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                ast.parse(content, filename=str(file_path))
                return True, None
            except SyntaxError as e:
                error_msg = f"Line {e.lineno}: {e.msg}"
                if e.text:
                    error_msg += f"\n  Code: {e.text.strip()}"
                return False, error_msg
            except Exception as e:
                return False, f"Parse Error: {str(e)}"

        except Exception as e:
            return False, f"File Error: {str(e)}"

    def scan_directory(self, directory: Path, quick_mode: bool = False) -> Dict:
        """Scan directory for syntax errors"""
        result = {
            "valid_files": [],
            "invalid_files": {},
            "total_checked": 0,
            "excluded_files": 0
        }

        # Get all Python files
        if quick_mode:
            # Only check critical directories
            python_files = []
            for critical_dir in self.config["critical_directories"]:
                dir_path = directory / critical_dir
                if dir_path.exists():
                    python_files.extend(dir_path.rglob("*.py"))
        else:
            python_files = list(directory.rglob("*.py"))

        for file_path in python_files:
            if self.should_exclude_file(file_path):
                result["excluded_files"] += 1
                continue

            result["total_checked"] += 1
            is_valid, error = self.validate_file_syntax(file_path)

            if is_valid:
                result["valid_files"].append(str(file_path))
            else:
                result["invalid_files"][str(file_path)] = error

        return result

    def pre_commit_validation(self) -> bool:
        """Run pre-commit syntax validation"""
        print("Running pre-commit syntax validation...")

        # Get changed files from git
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode != 0:
                print("Warning: Could not get git diff, checking all files")
                return self.full_validation(quick_mode=True)

            changed_files = [
                self.project_root / f.strip()
                for f in result.stdout.split('\n')
                if f.strip().endswith('.py')
            ]

        except Exception as e:
            print(f"Warning: Git command failed: {e}")
            return self.full_validation(quick_mode=True)

        if not changed_files:
            print("No Python files changed")
            return True

        print(f"Checking {len(changed_files)} changed Python files...")

        errors = {}
        for file_path in changed_files:
            if not file_path.exists() or self.should_exclude_file(file_path):
                continue

            is_valid, error = self.validate_file_syntax(file_path)
            if not is_valid:
                errors[str(file_path)] = error

        if errors:
            print(f"\nSYNTAX ERRORS FOUND IN {len(errors)} FILES:")
            print("=" * 60)
            for file_path, error in errors.items():
                print(f"\nFILE: {file_path}")
                print(f"ERROR: {error}")
            print("\n" + "=" * 60)
            print("COMMIT BLOCKED: Fix syntax errors before committing")
            return False

        print(f"All {len(changed_files)} changed files have valid syntax")
        return True

    def full_validation(self, quick_mode: bool = False) -> bool:
        """Run full syntax validation"""
        mode_desc = "quick" if quick_mode else "full"
        print(f"Running {mode_desc} syntax validation...")

        result = self.scan_directory(self.project_root, quick_mode=quick_mode)

        total_errors = len(result["invalid_files"])
        total_valid = len(result["valid_files"])
        total_checked = result["total_checked"]
        excluded = result["excluded_files"]

        print(f"\nSYNTAX VALIDATION RESULTS ({mode_desc} mode):")
        print("=" * 50)
        print(f"Total files checked: {total_checked}")
        print(f"Files excluded: {excluded}")
        print(f"Valid files: {total_valid}")
        print(f"Files with errors: {total_errors}")

        if total_errors > 0:
            print(f"\nSYNTAX ERRORS FOUND:")
            print("=" * 40)

            # Show first 10 errors in detail
            shown_errors = 0
            for file_path, error in result["invalid_files"].items():
                if shown_errors >= 10:
                    remaining = total_errors - shown_errors
                    print(f"\n... and {remaining} more errors")
                    break

                print(f"\nFILE: {file_path}")
                print(f"ERROR: {error}")
                shown_errors += 1

            print("\n" + "=" * 50)

            # Check against allowed threshold
            max_allowed = self.config["max_errors_allowed"]
            if total_errors > max_allowed:
                print(f"ERROR COUNT ({total_errors}) EXCEEDS THRESHOLD ({max_allowed})")
                return False
            else:
                print(f"Error count ({total_errors}) within threshold ({max_allowed})")
                return not self.config["strict_mode"]

        print("All files have valid syntax!")
        return True

    def update_config(self, **kwargs):
        """Update configuration"""
        self.config.update(kwargs)
        self.save_config()
        print("Configuration updated and saved")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Syntax Error Prevention System (Issue #1277)"
    )

    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="Run pre-commit validation on changed files only"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: only check critical directories"
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail on any syntax errors"
    )

    parser.add_argument(
        "--max-errors",
        type=int,
        help="Maximum number of errors allowed before failure"
    )

    parser.add_argument(
        "--directory",
        type=Path,
        help="Directory to validate (default: project root)"
    )

    args = parser.parse_args()

    # Determine project root
    if args.directory:
        project_root = args.directory
    else:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

    if not project_root.exists():
        print(f"Error: Directory {project_root} does not exist")
        sys.exit(1)

    # Initialize prevention system
    prevention = SyntaxPreventionSystem(project_root)

    # Update config if needed
    if args.strict:
        prevention.update_config(strict_mode=True)

    if args.max_errors is not None:
        prevention.update_config(max_errors_allowed=args.max_errors)

    # Run appropriate validation
    try:
        if args.pre_commit:
            success = prevention.pre_commit_validation()
        else:
            success = prevention.full_validation(quick_mode=args.quick)

        if success:
            print("\nSyntax validation passed!")
            sys.exit(0)
        else:
            print("\nSyntax validation failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()