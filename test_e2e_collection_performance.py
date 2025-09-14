#!/usr/bin/env python
"""
Test script for E2E collection performance optimization.
Measures collection time before and after optimization.
"""

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e_collection_optimizer import E2ECollectionOptimizer

def test_collection_performance():
    """Test E2E collection performance"""

    print("=" * 60)
    print("E2E COLLECTION PERFORMANCE TEST")
    print("=" * 60)

    # Test the optimizer
    print("\n1. Testing E2E Collection Optimizer")
    print("-" * 40)

    optimizer = E2ECollectionOptimizer(PROJECT_ROOT)

    # Get statistics
    stats = optimizer.get_statistics()
    print(f"Directory Statistics:")
    print(f"  Total directories: {stats['total_directories']}")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Test files: {stats['test_files']}")
    print(f"  Cache entries: {stats['cache_entries']}")

    # Test collection with different patterns
    test_patterns = ["*", "*agent*", "*auth*", "*websocket*"]

    for pattern in test_patterns:
        print(f"\n2. Testing pattern: '{pattern}'")
        print("-" * 40)

        # First run (cold)
        start_time = time.time()
        test_files = optimizer.collect_tests_optimized(pattern)
        cold_time = time.time() - start_time

        print(f"  Cold run: {len(test_files)} files in {cold_time:.2f}s")

        # Second run (warm/cached)
        start_time = time.time()
        test_files_cached = optimizer.collect_tests_optimized(pattern)
        warm_time = time.time() - start_time

        print(f"  Warm run: {len(test_files_cached)} files in {warm_time:.2f}s")
        if warm_time > 0:
            print(f"  Speedup: {cold_time/warm_time:.1f}x faster")
        else:
            print(f"  Speedup: instant (cached)")

        # Verify consistency
        if len(test_files) == len(test_files_cached):
            print("  Results consistent")
        else:
            print("  Results inconsistent!")

    # Test vs traditional glob
    print(f"\n3. Comparison with Traditional Collection")
    print("-" * 40)

    e2e_dir = PROJECT_ROOT / "tests" / "e2e"
    if e2e_dir.exists():
        # Traditional glob approach
        start_time = time.time()
        traditional_files = list(e2e_dir.rglob("*test*.py"))
        traditional_files = [str(f) for f in traditional_files if f.is_file()]
        traditional_time = time.time() - start_time

        print(f"  Traditional glob: {len(traditional_files)} files in {traditional_time:.2f}s")

        # Optimized approach
        start_time = time.time()
        optimized_files = optimizer.collect_tests_optimized("*")
        optimized_time = time.time() - start_time

        print(f"  Optimized: {len(optimized_files)} files in {optimized_time:.2f}s")

        if traditional_time > 0 and optimized_time > 0:
            speedup = traditional_time / optimized_time
            print(f"  Speedup: {speedup:.1f}x faster")
        else:
            print(f"  Speedup: instant (cached)")

    # Clean up
    optimizer.save_cache()

    print(f"\nE2E Collection Performance Test Complete")
    print("=" * 60)


def test_unified_runner_integration():
    """Test integration with unified test runner"""

    print("\n4. Testing Unified Runner Integration")
    print("-" * 40)

    try:
        from tests.unified_test_runner import UnifiedTestRunner

        runner = UnifiedTestRunner()

        # Test fast path collection with E2E optimization
        start_time = time.time()
        e2e_files = runner._fast_path_collect_tests("*", "e2e")
        integration_time = time.time() - start_time

        print(f"  Unified runner E2E: {len(e2e_files)} files in {integration_time:.2f}s")
        print("  Integration successful")

    except Exception as e:
        print(f"  Integration failed: {e}")


if __name__ == "__main__":
    try:
        test_collection_performance()
        test_unified_runner_integration()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()