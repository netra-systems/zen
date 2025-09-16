#!/usr/bin/env python3
"""Test script to benchmark collection timing and reproduce Issue #987"""

import time
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def run_collection_test(test_path, use_fast_collection=False):
    """Run collection test and measure timing."""
    cmd = [sys.executable, "tests/unified_test_runner.py"]

    if use_fast_collection:
        cmd.append("--fast-collection")

    # Add specific test path
    cmd.append(test_path)

    print(f"\nRunning: {' '.join(cmd)}")
    print(f"Fast collection: {use_fast_collection}")

    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        end_time = time.time()

        duration = end_time - start_time
        print(f"Duration: {duration:.2f}s")
        print(f"Return code: {result.returncode}")

        if result.stdout:
            print(f"STDOUT:\n{result.stdout[:500]}...")
        if result.stderr:
            print(f"STDERR:\n{result.stderr[:500]}...")

        return {
            'duration': duration,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        end_time = time.time()
        duration = end_time - start_time
        print(f"TIMEOUT after {duration:.2f}s")
        return {
            'duration': duration,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Timeout expired',
            'success': False
        }
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"ERROR after {duration:.2f}s: {e}")
        return {
            'duration': duration,
            'returncode': -2,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }

def main():
    """Main test execution."""
    print("=== Issue #987 Collection Timing Test ===")

    # Test mission critical suite
    test_path = "tests/mission_critical/test_websocket_agent_events_suite.py"

    print(f"\nTesting collection of: {test_path}")

    # Test without fast collection
    print("\n--- Test 1: Regular Collection ---")
    result1 = run_collection_test(test_path, use_fast_collection=False)

    # Test with fast collection
    print("\n--- Test 2: Fast Collection ---")
    result2 = run_collection_test(test_path, use_fast_collection=True)

    # Analysis
    print("\n=== RESULTS ANALYSIS ===")
    print(f"Regular collection: {result1['duration']:.2f}s (success: {result1['success']})")
    print(f"Fast collection: {result2['duration']:.2f}s (success: {result2['success']})")

    # Check for regression
    baseline_threshold = 10.0  # 10 seconds baseline
    if result1['duration'] > baseline_threshold:
        print(f"⚠️ REGRESSION DETECTED: Regular collection took {result1['duration']:.2f}s > {baseline_threshold}s baseline")

    if result2['duration'] > baseline_threshold:
        print(f"⚠️ REGRESSION DETECTED: Fast collection took {result2['duration']:.2f}s > {baseline_threshold}s baseline")

    # Check for import errors
    for i, result in enumerate([result1, result2], 1):
        if 'infrastructure.vpc_connectivity_fix' in result['stderr']:
            print(f"🔍 IMPORT ERROR DETECTED in test {i}: infrastructure.vpc_connectivity_fix")
        if 'ImportError' in result['stderr']:
            print(f"🔍 IMPORT ERROR DETECTED in test {i}: {result['stderr']}")

if __name__ == "__main__":
    main()