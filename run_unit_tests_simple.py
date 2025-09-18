#!/usr/bin/env python3
"""
Simple script to run unit tests and capture failures.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_unit_tests():
    """Run unit tests using subprocess."""
    print("Starting unit test execution...")

    # Change to project directory
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    # Add project root to Python path
    sys.path.insert(0, str(project_root))

    try:
        # Try to run the unified test runner
        cmd = [
            sys.executable,
            "tests/unified_test_runner.py",
            "--category", "unit",
            "--fast-fail",
            "--execution-mode", "fast_feedback"
        ]

        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        print("=== STDOUT ===")
        print(result.stdout)
        print("\n=== STDERR ===")
        print(result.stderr)
        print(f"\n=== RETURN CODE: {result.returncode} ===")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print("Test execution timed out after 5 minutes")
        return -1, "", "Timeout"
    except Exception as e:
        print(f"Error running tests: {e}")
        return -1, "", str(e)

if __name__ == "__main__":
    return_code, stdout, stderr = run_unit_tests()
    print(f"\nTest execution completed with return code: {return_code}")