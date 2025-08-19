"""Simple validation script for callback failure fixes."""

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
        await manager.execute_callback_safely(CallbackType.STATE_CHANGE, failing_callback)
        print("FAIL: Expected StateNotificationFailure to be raised")
        return False
    except StateNotificationFailure:
        print("SUCCESS: Critical callback failure propagated correctly")
        return True
    except Exception as e:
        print(f"FAIL: Unexpected exception: {e}")
        return False


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("Testing circuit breaker functionality...")
    
    manager = CallbackFailureManager("test-conn")
    manager.circuit_breakers[CallbackType.CONNECT].failure_threshold = 2
    manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
    
    async def failing_callback():
        raise Exception("Always fails")
    
    # First two failures should work
    await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
    await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
    
    # Check circuit breaker is open
    if manager.circuit_breakers[CallbackType.CONNECT].is_open:
        print("SUCCESS: Circuit breaker opened after threshold")
    else:
        print("FAIL: Circuit breaker should be open")
        return False
    
    # Third attempt should trigger exception
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


def test_criticality_configuration():
    """Test callback criticality configuration."""
    print("Testing callback criticality configuration...")
    
    manager = CallbackFailureManager("test-conn")
    
    # Test defaults
    expected = {
        CallbackType.STATE_CHANGE: CallbackCriticality.CRITICAL,
        CallbackType.CONNECT: CallbackCriticality.IMPORTANT,
        CallbackType.DISCONNECT: CallbackCriticality.NON_CRITICAL
    }
    
    for cb_type, expected_crit in expected.items():
        if manager.criticality_map[cb_type] != expected_crit:
            print(f"FAIL: Wrong default criticality for {cb_type}")
            return False
    
    # Test updating
    manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.CRITICAL)
    if manager.criticality_map[CallbackType.CONNECT] == CallbackCriticality.CRITICAL:
        print("SUCCESS: Criticality configuration works correctly")
        return True
    else:
        print("FAIL: Criticality update failed")
        return False


async def main():
    """Run all tests."""
    print("=== WebSocket Callback Failure Validation ===\n")
    
    tests = [
        ("Critical Callback Failure", test_critical_callback_failure()),
        ("Circuit Breaker", test_circuit_breaker()),
        ("Criticality Configuration", test_criticality_configuration())
    ]
    
    results = []
    for test_name, test in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutine(test):
                result = await test
            else:
                result = test
            results.append((test_name, result))
        except Exception as e:
            print(f"FAIL: Test {test_name} threw exception: {e}")
            results.append((test_name, False))
    
    print("\n=== VALIDATION SUMMARY ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("All tests passed! Callback failure fixes are working correctly.")
        return True
    else:
        print("Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)