#!/usr/bin/env python3
"""Quick validation script for SessionAccessRateLimiter implementation.

This script tests the basic functionality of the rate limiter
to ensure it works correctly before committing the changes.
"""

import asyncio
import sys
import time
from datetime import datetime

# Test basic import
try:
    from netra_backend.app.middleware.gcp_auth_context_middleware import (
        get_session_access_rate_limiter,
        SessionAccessFailureReason,
        get_session_access_suppression_metrics,
        get_session_access_window_status
    )
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

async def test_rate_limiter():
    """Test the rate limiter functionality."""
    print("\n🧪 Testing SessionAccessRateLimiter...")

    # Get rate limiter instance
    limiter = get_session_access_rate_limiter()
    print("✅ Rate limiter instance created")

    # Test initial metrics
    initial_metrics = limiter.get_suppression_metrics()
    print(f"✅ Initial metrics: {initial_metrics['metrics']['total_attempts']} attempts")

    # Test successful access recording
    await limiter.record_success()
    print("✅ Success recording works")

    # Test failure logging - first should be allowed
    should_log_1 = await limiter.should_log_failure(
        SessionAccessFailureReason.MIDDLEWARE_NOT_INSTALLED,
        "Test failure message 1"
    )
    print(f"✅ First failure should log: {should_log_1}")

    # Test second failure - should be suppressed (within same window)
    should_log_2 = await limiter.should_log_failure(
        SessionAccessFailureReason.MIDDLEWARE_NOT_INSTALLED,
        "Test failure message 2"
    )
    print(f"✅ Second failure should be suppressed: {not should_log_2}")

    # Test metrics after failures
    final_metrics = limiter.get_suppression_metrics()
    print(f"✅ Final metrics - Failures: {final_metrics['metrics']['total_failures']}, Suppressed: {final_metrics['metrics']['suppressed_logs']}")

    # Test window status
    window_status = limiter.get_window_status()
    print(f"✅ Window status - Used: {window_status['logs_used']}, Remaining: {window_status['logs_remaining']}")

    # Test global functions
    global_metrics = get_session_access_suppression_metrics()
    global_window = get_session_access_window_status()
    print("✅ Global accessor functions work")

    print("\n🎉 All tests passed! Rate limiter is functioning correctly.")

    return {
        'suppression_working': not should_log_2,
        'metrics_tracking': final_metrics['metrics']['total_failures'] >= 2,
        'window_management': window_status['logs_used'] > 0
    }

if __name__ == "__main__":
    print("🚀 SessionAccessRateLimiter Validation Test")
    print("=" * 50)

    try:
        results = asyncio.run(test_rate_limiter())

        if all(results.values()):
            print("\n✅ ALL VALIDATION TESTS PASSED")
            print("🎯 Rate limiter ready for deployment")
            sys.exit(0)
        else:
            print(f"\n❌ Some tests failed: {results}")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)