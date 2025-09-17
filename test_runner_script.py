#!/usr/bin/env python3
"""
Golden Path Integration Test Runner
Runs integration tests focused on golden path functionality without Docker
"""

import os
import sys
import subprocess
import time

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
            cwd="/c/netra-apex"
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
    os.chdir("/c/netra-apex")

    # Test commands to run
    test_commands = [
        {
            "cmd": "python -m pytest tests/integration/agent_golden_path/ -v --tb=short -x",
            "description": "Agent Golden Path Integration Tests"
        },
        {
            "cmd": "python -m pytest tests/integration/agents/test_issue_1142_golden_path_startup_contamination.py -v --tb=short -x",
            "description": "Issue 1142 Golden Path Startup Contamination Test"
        },
        {
            "cmd": "python -m pytest tests/integration/config_ssot/test_config_golden_path_protection.py -v --tb=short -x",
            "description": "Config SSOT Golden Path Protection Test"
        },
        {
            "cmd": "python -m pytest tests/integration/config_ssot/test_golden_path_auth_failure_reproduction.py -v --tb=short -x",
            "description": "Golden Path Auth Failure Reproduction Test"
        }
    ]

    results = []

    print("GOLDEN PATH INTEGRATION TEST EXECUTION")
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

    # Summary Report
    print(f"\n{'='*60}")
    print("FINAL SUMMARY REPORT")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    for i, result in enumerate(results, 1):
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{i}. {status} - {result['description']}")

        if not result["success"]:
            print(f"   Command: {result['command']}")
            if result['stderr']:
                print(f"   Error: {result['stderr'][:200]}...")

    print(f"\nTest execution completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    return results

if __name__ == "__main__":
    results = main()