#!/usr/bin/env python3
"""
Python3-compatible unit test launcher for Claude Code environment.

This script provides immediate workaround for Issue #1176 test execution restrictions
by using explicit python3 commands instead of sys.executable.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def main():
    """Execute unit tests using python3 command for Claude Code compatibility."""
    print("=" * 60)
    print("PYTHON3-COMPATIBLE UNIT TEST EXECUTION")
    print("=" * 60)
    print(f"Started: {datetime.now()}")

    # Change to project directory
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    # Add project root to Python path
    sys.path.insert(0, str(project_root))

    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")

    try:
        # Use explicit python3 command for Claude Code compatibility
        cmd = [
            "python3",
            str(project_root / "tests" / "unified_test_runner.py"),
            "--category", "unit",
            "--fast-fail",
            "--execution-mode", "fast_feedback"
        ]

        print(f"Executing command: {' '.join(cmd)}")
        print("-" * 60)

        # Execute with real-time output
        result = subprocess.run(
            cmd,
            cwd=project_root,
            timeout=300  # 5 minute timeout
        )

        print("-" * 60)
        print(f"Test execution completed with return code: {result.returncode}")
        print(f"Finished: {datetime.now()}")

        return result.returncode

    except subprocess.TimeoutExpired:
        print("ERROR: Test execution timed out after 5 minutes")
        return -1
    except FileNotFoundError as e:
        print(f"ERROR: python3 command not found: {e}")
        print("Fallback: Trying with sys.executable...")

        # Fallback to sys.executable
        try:
            cmd = [
                sys.executable,
                str(project_root / "tests" / "unified_test_runner.py"),
                "--category", "unit",
                "--fast-fail",
                "--execution-mode", "fast_feedback"
            ]

            print(f"Fallback command: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=project_root, timeout=300)
            return result.returncode

        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            return -2

    except Exception as e:
        print(f"ERROR: Unexpected error during test execution: {e}")
        return -1

if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)