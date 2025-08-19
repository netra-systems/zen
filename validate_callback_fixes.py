"""Validation script for callback failure fixes.

Tests the callback failure propagation without full app dependencies.
"""

import asyncio
import sys
import os

# Add the websocket directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'websocket'))

from reconnection_types import CallbackType, CallbackCriticality
from reconnection_exceptions import CriticalCallbackFailure, CallbackCircuitBreakerOpen, StateNotificationFailure
from callback_failure_manager import CallbackFailureManager


async def test_critical_callback_failure():
    """Test critical callback failure propagation."""
    print("Testing critical callback failure propagation...")
    
    manager = CallbackFailureManager("test-conn")
    
    async def failing_callback():
        raise Exception("Critical state failure")
    
    try:
        await manager.execute_callback_safely(
            CallbackType.STATE_CHANGE, 
            failing_callback
        )
        print("FAIL: Expected StateNotificationFailure to be raised")
        return False
    except StateNotificationFailure as e:
        print(f"SUCCESS: Critical callback failure propagated: {e}")
        return True
    except Exception as e:
        print(f"FAIL: Unexpected exception: {e}")
        return False


async def test_important_callback_graceful_degradation():
    """Test important callback graceful degradation."""
    print("Testing important callback graceful degradation...")
    
    manager = CallbackFailureManager("test-conn")
    
    async def failing_callback():
        raise Exception("Important connect failure")
    
    try:
        await manager.execute_callback_safely(
            CallbackType.CONNECT, 
            failing_callback
        )
        print("SUCCESS: Important callback failure handled gracefully")
        
        # Check that failure was recorded
        if len(manager.failure_history) == 1:
            failure = manager.failure_history[0]
            if failure.criticality == CallbackCriticality.IMPORTANT:
                print("SUCCESS: Important failure properly recorded")
                return True
            else:
                print(f"FAIL: Wrong criticality recorded: {failure.criticality}")
                return False
        else:
            print(f"FAIL: Expected 1 failure, got {len(manager.failure_history)}")
            return False
    except Exception as e:
        print(f"FAIL: Important callback should not raise: {e}")
        return False


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("Testing circuit breaker functionality...")
    
    manager = CallbackFailureManager("test-conn")
    
    # Set low threshold for testing
    manager.circuit_breakers[CallbackType.CONNECT].failure_threshold = 2
    
    # Set connect as non-critical to avoid exceptions
    manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
    
    async def failing_callback():
        raise Exception("Always fails")
    
    # First two failures should work
    try:
        await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
        await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
        print("SUCCESS: First two failures handled")
    except Exception as e:
        print(f"FAIL: Unexpected failure in first attempts: {e}")
        return False
    
    # Check circuit breaker is open
    breaker = manager.circuit_breakers[CallbackType.CONNECT]
    if breaker.is_open:
        print("SUCCESS: Circuit breaker opened after threshold reached")
    else:
        print("FAIL: Circuit breaker should be open")
        return False
    
    # Third attempt should trigger circuit breaker exception
    try:
        await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
        print("FAIL: Expected CallbackCircuitBreakerOpen exception")
        return False
    except CallbackCircuitBreakerOpen:
        print("SUCCESS: Circuit breaker exception raised correctly")
        return True
    except Exception as e:
        print(f"FAIL: Unexpected exception: {e}")
        return False


async def test_non_critical_callback():
    """Test non-critical callback handling."""
    print("Testing non-critical callback handling...")
    
    manager = CallbackFailureManager("test-conn")
    
    async def failing_callback():
        raise Exception("Non-critical disconnect failure")
    
    try:
        await manager.execute_callback_safely(
            CallbackType.DISCONNECT, 
            failing_callback
        )
        print("✅ SUCCESS: Non-critical callback failure handled gracefully")
        
        # Check failure was recorded with correct criticality
        if len(manager.failure_history) == 1:
            failure = manager.failure_history[0]
            if failure.criticality == CallbackCriticality.NON_CRITICAL:
                print("✅ SUCCESS: Non-critical failure properly recorded")
                return True
            else:
                print(f"❌ FAIL: Wrong criticality: {failure.criticality}")
                return False
        else:
            print(f"❌ FAIL: Expected 1 failure, got {len(manager.failure_history)}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Non-critical callback should not raise: {e}")
        return False


def test_criticality_configuration():
    """Test callback criticality configuration."""
    print("Testing callback criticality configuration...")
    
    manager = CallbackFailureManager("test-conn")
    
    # Test default mapping
    expected_defaults = {
        CallbackType.STATE_CHANGE: CallbackCriticality.CRITICAL,
        CallbackType.CONNECT: CallbackCriticality.IMPORTANT,
        CallbackType.DISCONNECT: CallbackCriticality.NON_CRITICAL
    }
    
    for callback_type, expected_criticality in expected_defaults.items():
        if manager.criticality_map[callback_type] != expected_criticality:
            print(f"❌ FAIL: Wrong default criticality for {callback_type}")
            return False
    
    print("✅ SUCCESS: Default criticality mapping correct")
    
    # Test updating criticality
    manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.CRITICAL)
    if manager.criticality_map[CallbackType.CONNECT] == CallbackCriticality.CRITICAL:
        print("✅ SUCCESS: Criticality update works correctly")
        return True
    else:
        print("❌ FAIL: Criticality update failed")
        return False


def test_metrics():
    """Test failure metrics collection."""
    print("Testing failure metrics collection...")
    
    manager = CallbackFailureManager("test-conn")
    
    # Add test data
    manager.circuit_breakers[CallbackType.CONNECT].failure_count = 2
    manager.circuit_breakers[CallbackType.STATE_CHANGE].failure_count = 1
    
    # Add failure history (simulating past failures)
    from reconnection_types import CallbackFailure
    from datetime import datetime, timezone
    
    failure1 = CallbackFailure(
        callback_type=CallbackType.CONNECT,
        timestamp=datetime.now(timezone.utc),
        error_message="Test error",
        criticality=CallbackCriticality.IMPORTANT
    )
    failure2 = CallbackFailure(
        callback_type=CallbackType.STATE_CHANGE,
        timestamp=datetime.now(timezone.utc),
        error_message="Critical error",
        criticality=CallbackCriticality.CRITICAL
    )
    
    manager.failure_history = [failure1, failure2]
    
    metrics = manager.get_failure_metrics()
    
    # Validate metrics
    if metrics['total_failures'] != 2:
        print(f"❌ FAIL: Expected 2 total failures, got {metrics['total_failures']}")
        return False
    
    if metrics['critical_failures'] != 1:
        print(f"❌ FAIL: Expected 1 critical failure, got {metrics['critical_failures']}")
        return False
    
    # Check circuit breaker metrics
    cb_metrics = metrics['circuit_breakers']
    if cb_metrics[CallbackType.CONNECT.value]['failure_count'] != 2:
        print("❌ FAIL: Wrong connect failure count in metrics")
        return False
    
    if cb_metrics[CallbackType.STATE_CHANGE.value]['failure_count'] != 1:
        print("❌ FAIL: Wrong state change failure count in metrics")
        return False
    
    print("✅ SUCCESS: Metrics collection works correctly")
    return True


async def run_all_tests():
    """Run all validation tests."""
    print("=== WebSocket Callback Failure Validation ===\n")
    
    tests = [
        ("Critical Callback Failure", test_critical_callback_failure()),
        ("Important Callback Degradation", test_important_callback_graceful_degradation()),
        ("Circuit Breaker", test_circuit_breaker()),
        ("Non-Critical Callback", test_non_critical_callback()),
        ("Criticality Configuration", test_criticality_configuration()),
        ("Metrics Collection", test_metrics())
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAIL: Test {test_name} threw exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== VALIDATION SUMMARY ===")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! Callback failure fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)