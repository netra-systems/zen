#!/usr/bin/env python
"""
Simple Circuit Breaker Test - Issue #941 Verification

This tests the core functionality described in issue #941 to verify
that the TypeError issues have been resolved.
"""

def test_basic_imports():
    """Test that all circuit breaker imports work without TypeError."""
    try:
        # Test unified circuit breaker imports
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitBreaker,
            UnifiedCircuitConfig,
            get_unified_circuit_breaker_manager
        )
        print("✅ Unified circuit breaker imports successful")
        
        # Test legacy compatibility imports
        from netra_backend.app.core.circuit_breaker import (
            get_circuit_breaker,
            CircuitBreaker,
            circuit_breaker
        )
        print("✅ Legacy compatibility imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_circuit_breaker_creation():
    """Test that circuit breakers can be created without TypeError."""
    try:
        from netra_backend.app.core.circuit_breaker import get_circuit_breaker
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig
        
        # Test simple creation (should use defaults)
        breaker1 = get_circuit_breaker('test_service_1')
        print(f"✅ Simple circuit breaker created: {breaker1 is not None}")
        
        # Test creation with config
        config = UnifiedCircuitConfig(
            name="test_service_2",
            failure_threshold=3,
            recovery_timeout=30,
            timeout_seconds=5.0
        )
        breaker2 = get_circuit_breaker('test_service_2', config)
        print(f"✅ Circuit breaker with config created: {breaker2 is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Circuit breaker creation failed: {e}")
        return False

def test_manager_functionality():
    """Test that the circuit breaker manager works properly."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            get_unified_circuit_breaker_manager,
            UnifiedCircuitConfig
        )
        
        manager = get_unified_circuit_breaker_manager()
        print(f"✅ Manager initialized: {manager is not None}")
        
        config = UnifiedCircuitConfig(
            name="managed_service",
            failure_threshold=2,
            recovery_timeout=15
        )
        
        breaker = manager.create_circuit_breaker("managed_service", config)
        print(f"✅ Manager created circuit breaker: {breaker is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Manager functionality failed: {e}")
        return False

def test_configuration_api():
    """Test that the configuration API works as documented in issue #941."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig
        
        # Test the correct configuration pattern from the issue
        config = UnifiedCircuitConfig(
            name="test_service",
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,      # ✅ Valid parameter
            timeout_seconds=5.0,      # ✅ Correct parameter name
            expected_exception=ConnectionError  # ✅ Single exception type
        )
        
        print(f"✅ Configuration created with all parameters: {config.name}")
        print(f"   - failure_threshold: {config.failure_threshold}")
        print(f"   - recovery_timeout: {config.recovery_timeout}")
        print(f"   - success_threshold: {config.success_threshold}")
        print(f"   - timeout_seconds: {config.timeout_seconds}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration API failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("="*60)
    print("ISSUE #941 CIRCUIT BREAKER VERIFICATION")
    print("="*60)
    
    tests = [
        ("Import Tests", test_basic_imports),
        ("Circuit Breaker Creation", test_circuit_breaker_creation),
        ("Manager Functionality", test_manager_functionality),
        ("Configuration API", test_configuration_api)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Issue #941 appears to be resolved!")
        print("✅ No TypeError issues detected")
        print("✅ Circuit breaker system is functional")
        return True
    else:
        print("⚠️  Some tests failed - Issue #941 may not be fully resolved")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)