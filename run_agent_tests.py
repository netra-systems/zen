#!/usr/bin/env python3
"""
Simple test runner for staging agent tests - no docker dependency
"""

import sys
import os
import asyncio
import subprocess
import json
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables for staging
os.environ['ENVIRONMENT'] = 'staging'
os.environ['NO_DOCKER'] = '1'

def run_test(test_file_path):
    """Run a single test file and capture results"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file_path}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # Run the test
        result = subprocess.run(
            [sys.executable, str(test_file_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        duration = time.time() - start_time

        print(f"Return code: {result.returncode}")
        print(f"Duration: {duration:.2f}s")

        if result.stdout:
            print(f"STDOUT:")
            print(result.stdout)

        if result.stderr:
            print(f"STDERR:")
            print(result.stderr)

        return {
            "test_file": test_file_path,
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        print(f"Test timed out after 5 minutes")
        return {
            "test_file": test_file_path,
            "success": False,
            "error": "Test timed out",
            "duration": 300
        }

    except Exception as e:
        print(f"Error running test: {e}")
        return {
            "test_file": test_file_path,
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }

def main():
    """Run all specified agent tests"""

    test_files = [
        "tests/staging/test_staging_agent_execution.py",
        "tests/staging/test_staging_websocket_agent_events.py",
        "tests/e2e/test_agent_websocket_events_comprehensive.py",
        "tests/e2e/integration/test_agent_orchestration_real_llm.py"
    ]

    results = []

    for test_file in test_files:
        test_path = PROJECT_ROOT / test_file
        if test_path.exists():
            result = run_test(test_path)
            results.append(result)
        else:
            print(f"WARNING: Test file not found: {test_file}")
            results.append({
                "test_file": test_file,
                "success": False,
                "error": "File not found",
                "duration": 0
            })

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        test_name = os.path.basename(result["test_file"])
        duration = result.get("duration", 0)
        print(f"{status:4} | {test_name:50} | {duration:6.2f}s")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    main()