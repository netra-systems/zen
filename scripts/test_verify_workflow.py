#!/usr/bin/env python3
"""
Test script for verify_workflow_status.py

Demonstrates usage patterns and validates the script functionality.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[int, str]:
    """Run command and return exit code and output."""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=Path(__file__).parent.parent
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def test_help_command() -> bool:
    """Test help command functionality."""
    print("Testing help command...")
    exit_code, output = run_command([
        sys.executable, "scripts/verify_workflow_status.py", "--help"
    ])
    
    success = exit_code == 0 and "Verify GitHub workflow status" in output
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    return success


def test_missing_parameters() -> bool:
    """Test error handling for missing parameters."""
    print("Testing missing parameters...")
    exit_code, output = run_command([
        sys.executable, "scripts/verify_workflow_status.py", "--repo", "test/repo"
    ])
    
    success = exit_code == 1 and "Either --run-id or --workflow-name must be specified" in output
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    return success


def test_missing_token() -> bool:
    """Test error handling for missing GitHub token."""
    print("Testing missing token...")
    # Ensure GITHUB_TOKEN is not set for this test
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/verify_workflow_status.py", 
            "--repo", "test/repo", "--workflow-name", "test"
        ], capture_output=True, text=True, env=env, cwd=Path(__file__).parent.parent)
        
        exit_code = result.returncode
        output = result.stdout + result.stderr
    except Exception as e:
        exit_code, output = 1, str(e)
    
    success = exit_code == 1 and "GitHub token required" in output
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    return success


def main() -> int:
    """Run all tests."""
    print("Running verify_workflow_status.py validation tests...")
    print("=" * 50)
    
    tests = [
        test_help_command,
        test_missing_parameters,
        test_missing_token,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("All tests passed! The script is working correctly.")
        return 0
    else:
        print("Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())