#!/usr/bin/env python
"""
Demo script to test running multiple isolated test instances simultaneously
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_isolation import TestIsolationManager


def run_isolated_test(instance_id: int):
    """Run an isolated test instance"""
    print(f"\n[Instance {instance_id}] Starting isolated test run...")
    
    # Create isolation manager with unique test ID
    manager = TestIsolationManager(test_id=f"demo_{instance_id}")
    manager.setup_environment()
    manager.apply_environment()
    manager.register_cleanup()
    
    # Show configuration
    print(f"[Instance {instance_id}] Test ID: {manager.test_id}")
    print(f"[Instance {instance_id}] Backend Port: {manager.ports.get('backend', 'N/A')}")
    print(f"[Instance {instance_id}] Frontend Port: {manager.ports.get('frontend', 'N/A')}")
    print(f"[Instance {instance_id}] Redis DB: {manager.get_redis_db_index()}")
    print(f"[Instance {instance_id}] Reports Dir: {manager.directories.get('reports', 'N/A')}")
    
    # Run a quick test
    cmd = [
        sys.executable,
        "test_runner.py",
        "--mode", "quick",
        "--backend-only",  # Just run backend for speed
        "--no-report",  # Skip report generation
        "--keep-reports"  # Keep isolated reports for inspection
    ]
    
    print(f"[Instance {instance_id}] Running tests...")
    start_time = time.time()
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ.copy()
    )
    
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"[Instance {instance_id}] ✅ Tests PASSED in {duration:.2f}s")
    else:
        print(f"[Instance {instance_id}] ❌ Tests FAILED with code {result.returncode} in {duration:.2f}s")
    
    # Show where reports are stored
    print(f"[Instance {instance_id}] Reports saved at: {manager.base_dir}")
    
    return result.returncode


def main():
    print("=" * 80)
    print("TEST ISOLATION DEMONSTRATION")
    print("Running multiple test instances simultaneously")
    print("=" * 80)
    
    # Number of concurrent test instances
    num_instances = 3
    
    # Create and start threads for each instance
    threads = []
    results = [None] * num_instances
    
    def run_instance(idx):
        results[idx] = run_isolated_test(idx + 1)
    
    print(f"\nStarting {num_instances} isolated test instances...")
    print("-" * 80)
    
    for i in range(num_instances):
        thread = threading.Thread(target=run_instance, args=(i,))
        threads.append(thread)
        thread.start()
        time.sleep(0.5)  # Small delay to stagger starts
    
    # Wait for all threads to complete
    print("\nWaiting for all instances to complete...")
    for thread in threads:
        thread.join()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASSED" if result == 0 else f"❌ FAILED (code {result})"
        print(f"Instance {i}: {status}")
    
    all_passed = all(r == 0 for r in results if r is not None)
    print("\n" + ("✅ All instances completed successfully!" if all_passed else "❌ Some instances failed"))
    print("=" * 80)


if __name__ == "__main__":
    main()