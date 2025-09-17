#!/usr/bin/env python3
"""
Circuit Breaker Phase 2 Validation Script
Testing the key configuration issues identified in Issue #941 strategy.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports_succeed():
    """Test 1: Verify all required imports work without errors."""
    print("🧪 Test 1: Import validation")

    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitConfig,
            UnifiedCircuitBreaker,
            UnifiedCircuitBreakerManager,
            get_unified_circuit_breaker_manager
        )
        print("✅ UnifiedCircuitBreaker imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_correct_config_creation():
    """Test 2: Verify correct configuration patterns work."""
    print("\n🧪 Test 2: Correct configuration pattern")

    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitConfig,
            get_unified_circuit_breaker_manager
        )

        # CORRECT PATTERN from strategy document
        config = UnifiedCircuitConfig(
            name="test_service",
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,  # ✅ Valid parameter
            timeout_seconds=5.0,  # ✅ Correct parameter name
            expected_exception=ConnectionError  # ✅ Single exception type
        )

        manager = get_unified_circuit_breaker_manager()
        breaker = manager.create_circuit_breaker("test_service", config)

        print(f"✅ Correct pattern works: {config.name}, threshold: {config.failure_threshold}")
        return True
    except Exception as e:
        print(f"❌ Correct config pattern failed: {e}")
        return False

def test_legacy_incorrect_patterns():
    """Test 3: Document the incorrect patterns that should fail."""
    print("\n🧪 Test 3: Legacy incorrect patterns (should fail)")

    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig

        # Test the failing patterns mentioned in strategy document
        failing_tests = []

        # Test 1: success_threshold doesn't exist as expected_exception_types
        try:
            config = UnifiedCircuitConfig(
                name="failing_test",
                failure_threshold=3,
                recovery_timeout=30,
                timeout=5.0,  # ❌ Should be timeout_seconds
                expected_exception_types=["ConnectionError"]  # ❌ Invalid parameter
            )
            failing_tests.append("expected_exception_types parameter accepted (should fail)")
        except (TypeError, ValueError) as e:
            print(f"✅ expected_exception_types correctly rejected: {type(e).__name__}")

        # Test 2: timeout instead of timeout_seconds
        try:
            config = UnifiedCircuitConfig(
                name="failing_test2",
                timeout=5.0  # ❌ Should be timeout_seconds
            )
            failing_tests.append("timeout parameter accepted (should fail)")
        except (TypeError, ValueError) as e:
            print(f"✅ timeout parameter correctly rejected: {type(e).__name__}")

        if failing_tests:
            print(f"❌ These incorrect patterns were NOT rejected: {failing_tests}")
            return False
        else:
            print("✅ All incorrect patterns properly rejected")
            return True

    except Exception as e:
        print(f"❌ Legacy pattern test failed: {e}")
        return False

def test_circuit_breaker_creation():
    """Test 4: Test circuit breaker creation via manager."""
    print("\n🧪 Test 4: Circuit breaker creation")

    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitConfig,
            get_unified_circuit_breaker_manager,
            UnifiedCircuitBreakerState
        )

        config = UnifiedCircuitConfig(
            name="creation_test",
            failure_threshold=2,
            recovery_timeout=15
        )

        manager = get_unified_circuit_breaker_manager()
        breaker = manager.create_circuit_breaker("creation_test", config)

        # Verify breaker properties
        assert breaker.config.name == "creation_test"
        assert breaker.config.failure_threshold == 2
        assert breaker.config.recovery_timeout == 15
        assert breaker.state == UnifiedCircuitBreakerState.CLOSED

        print(f"✅ Circuit breaker created: {breaker.config.name}, state: {breaker.state}")
        return True

    except Exception as e:
        print(f"❌ Circuit breaker creation failed: {e}")
        return False

def test_manager_singleton():
    """Test 5: Verify manager singleton behavior."""
    print("\n🧪 Test 5: Manager singleton")

    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import get_unified_circuit_breaker_manager

        manager1 = get_unified_circuit_breaker_manager()
        manager2 = get_unified_circuit_breaker_manager()

        assert manager1 is manager2, "Manager should be singleton"
        print("✅ Manager singleton behavior verified")
        return True

    except Exception as e:
        print(f"❌ Manager singleton test failed: {e}")
        return False

def test_backward_compatibility():
    """Test 6: Test backward compatibility layer."""
    print("\n🧪 Test 6: Backward compatibility")

    try:
        from netra_backend.app.core.circuit_breaker import (
            get_circuit_breaker,
            CircuitBreaker,
            UnifiedCircuitBreaker
        )

        # Test compatibility alias
        assert CircuitBreaker is UnifiedCircuitBreaker, "CircuitBreaker should alias UnifiedCircuitBreaker"

        # Test get_circuit_breaker with no config
        breaker = get_circuit_breaker("compatibility_test")
        assert breaker is not None

        print("✅ Backward compatibility layer working")
        return True

    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def main():
    """Run all Phase 2 validation tests."""
    print("🔧 Circuit Breaker Phase 2 Configuration Validation")
    print("=" * 60)
    print("Testing the configuration issues identified in Issue #941\n")

    tests = [
        ("Import validation", test_imports_succeed),
        ("Correct config creation", test_correct_config_creation),
        ("Legacy incorrect patterns", test_legacy_incorrect_patterns),
        ("Circuit breaker creation", test_circuit_breaker_creation),
        ("Manager singleton", test_manager_singleton),
        ("Backward compatibility", test_backward_compatibility)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if test_func():
            passed += 1
        else:
            print(f"\n❌ FAILED: {test_name}")
            print("Stopping execution due to failure")
            break

    print("\n" + "=" * 60)
    print(f"📊 Phase 2 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 Phase 2 SUCCESS! Configuration validation is working correctly.")
        print("\nNext Steps:")
        print("- Phase 3: Circuit Breaker Functionality Tests")
        print("- Phase 4: Compatibility Layer Tests")
        print("- Phase 5: Integration Tests")
        return 0
    else:
        print("❌ Phase 2 FAILED! Configuration validation needs fixes.")
        print("\nDebugging needed for configuration API compatibility.")
        return 1

if __name__ == "__main__":
    sys.exit(main())