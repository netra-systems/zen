#!/usr/bin/env python3
"""
Unit Test Runner for Golden Path
Runs unit tests with focus on golden path functionality
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {cmd}")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent)
        )

        duration = time.time() - start_time

        print(f"EXIT CODE: {result.returncode}")
        print(f"DURATION: {duration:.2f}s")

        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"ERROR: {e}")
        return False, "", str(e)

def main():
    """Main test execution function"""
    os.chdir(Path(__file__).parent)

    # Run unit tests with pytest
    test_commands = [
        {
            "cmd": "python -m pytest tests/unit/ -v --tb=short -x --no-header",
            "description": "Unit Tests - Fast Fail Mode"
        }
    ]

    results = []

    print("UNIT TEST EXECUTION - GOLDEN PATH FOCUS")
    print("="*60)
    print(f"Working Directory: {os.getcwd()}")
    print(f"Python Version: {sys.version}")
    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for test_config in test_commands:
        success, stdout, stderr = run_command(test_config["cmd"], test_config["description"])
        results.append({
            "description": test_config["description"],
            "command": test_config["cmd"],
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        })

        # If tests failed, extract failure details
        if not success:
            print("\n" + "="*60)
            print("FAILURE DETAILS ANALYSIS")
            print("="*60)

            # Parse test output for failures
            lines = stdout.split('\n') + stderr.split('\n')
            for i, line in enumerate(lines):
                if 'FAILED' in line or 'ERROR' in line or 'ImportError' in line or 'ModuleNotFoundError' in line:
                    print(f"  {line}")
                    # Print context around error
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        if j != i and lines[j].strip():
                            print(f"    {lines[j]}")

    # Summary Report
    print(f"\n{'='*60}")
    print("FINAL SUMMARY REPORT")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    print(f"Total Test Runs: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    for i, result in enumerate(results, 1):
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{i}. {status} - {result['description']}")

        if not result["success"]:
            print(f"   Command: {result['command']}")
            if result['stderr']:
                print(f"   Error Preview: {result['stderr'][:500]}...")

    print(f"\nTest execution completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Return exit code based on results
    return 0 if all(r["success"] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())