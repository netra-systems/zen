#!/usr/bin/env python3
"""
Performance regression check for Issue #803 fix.
Ensure the fix doesn't cause any performance degradation.
"""

import time
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


def test_performance_regression():
    """Test that the fix doesn't cause performance regression."""
    print("Issue #803 Performance Regression Check")
    print("=" * 45)

    # Test parameters
    num_iterations = 1000
    test_user = "performance_test_user"
    test_operation = "perf_test"

    # Warm up
    for _ in range(10):
        UnifiedIdGenerator.generate_user_context_ids(test_user, test_operation)

    # Performance test
    start_time = time.time()
    for i in range(num_iterations):
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
            f"{test_user}_{i}", f"{test_operation}_{i}"
        )
    end_time = time.time()

    total_time = end_time - start_time
    avg_time_per_call = (total_time / num_iterations) * 1000  # Convert to ms

    print(f"Generated {num_iterations} ID sets in {total_time:.4f} seconds")
    print(f"Average time per call: {avg_time_per_call:.4f} ms")

    # Performance expectations (very generous limits)
    max_acceptable_avg_ms = 1.0  # 1ms per call is very generous

    if avg_time_per_call <= max_acceptable_avg_ms:
        print(f"SUCCESS: Performance is acceptable (< {max_acceptable_avg_ms} ms per call)")
        return True
    else:
        print(f"WARNING: Performance may be degraded (> {max_acceptable_avg_ms} ms per call)")
        return False


if __name__ == "__main__":
    success = test_performance_regression()
    exit(0 if success else 1)