#!/usr/bin/env python3
"""
Direct execution of golden path tests against staging using subprocess.
This avoids pytest subprocess issues by calling the unified test runner directly.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).parent),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print stdout
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        # Print stderr
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        # Print return code
        print(f"\nReturn code: {result.returncode}")

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
        else:
            print(f"❌ {description} - FAILED")

        return result.returncode == 0, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT (300 seconds)")
        return False, "", "Command timed out"
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, "", str(e)

def main():
    """Main execution function."""
    print("🌟 NETRA APEX GOLDEN PATH E2E TEST EXECUTION AGAINST STAGING")
    print("Using unified test runner with staging environment")

    # Set environment variables
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["STAGING_ENV"] = "true"
    os.environ["TEST_MODE"] = "true"

    # Test commands to run
    commands = [
        {
            "cmd": [
                sys.executable, "tests/unified_test_runner.py",
                "--env", "staging",
                "--no-docker",
                "--fast-fail",
                "--filter", "test_simplified_golden_path_validation",
                "-v"
            ],
            "description": "Simplified Golden Path E2E Test - Component Validation"
        },
        {
            "cmd": [
                sys.executable, "tests/unified_test_runner.py",
                "--env", "staging",
                "--no-docker",
                "--fast-fail",
                "--filter", "test_staging_environment_health_check",
                "-v"
            ],
            "description": "Staging Environment Health Check"
        },
        {
            "cmd": [
                sys.executable, "tests/unified_test_runner.py",
                "--env", "staging",
                "--no-docker",
                "--category", "e2e",
                "--filter", "golden",
                "--fast-fail",
                "-v"
            ],
            "description": "Golden Path E2E Tests (All)"
        }
    ]

    results = []

    # Run each command
    for i, test_cmd in enumerate(commands, 1):
        print(f"\n{'#'*80}")
        print(f"TEST {i}/{len(commands)}")
        print(f"{'#'*80}")

        success, stdout, stderr = run_command(test_cmd["cmd"], test_cmd["description"])

        results.append({
            "description": test_cmd["description"],
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        })

        # Stop on first failure if fast-fail mode
        if not success:
            print(f"\n⚠️  Stopping execution due to failure in: {test_cmd['description']}")
            break

    # Print summary
    print(f"\n{'='*80}")
    print("📋 EXECUTION SUMMARY")
    print(f"{'='*80}")

    successful = 0
    failed = 0

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} - {result['description']}")

        if result["success"]:
            successful += 1
        else:
            failed += 1

    print(f"\nTotal: {len(results)} tests")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    # Print failure details
    if failed > 0:
        print(f"\n{'='*80}")
        print("❌ FAILURE DETAILS")
        print(f"{'='*80}")

        for result in results:
            if not result["success"]:
                print(f"\n🔍 Failed Test: {result['description']}")
                print("-" * 60)
                if result["stderr"]:
                    print("Error Output:")
                    print(result["stderr"])
                if result["stdout"]:
                    print("Standard Output:")
                    print(result["stdout"][-1000:])  # Last 1000 chars

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()