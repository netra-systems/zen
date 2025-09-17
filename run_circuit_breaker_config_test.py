#!/usr/bin/env python3
"""
Simple test runner for circuit breaker configuration validation
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required imports work."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitConfig,
            UnifiedCircuitBreaker,
            UnifiedCircuitBreakerManager,
            get_unified_circuit_breaker_manager
        )
        print("✅ All circuit breaker imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_config_creation():
    """Test basic configuration creation."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig

        config = UnifiedCircuitConfig(name="test_service")
        print(f"✅ Basic config creation successful: {config.name}")
        return True
    except Exception as e:
        print(f"❌ Basic config creation failed: {e}")
        return False

def test_manager_creation():
    """Test manager creation."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import get_unified_circuit_breaker_manager

        manager = get_unified_circuit_breaker_manager()
        print("✅ Manager creation successful")
        return True
    except Exception as e:
        print(f"❌ Manager creation failed: {e}")
        return False

def test_circuit_breaker_creation():
    """Test circuit breaker creation through manager."""
    try:
        from netra_backend.app.core.resilience.unified_circuit_breaker import (
            UnifiedCircuitConfig,
            get_unified_circuit_breaker_manager
        )

        config = UnifiedCircuitConfig(name="test_service", failure_threshold=3)
        manager = get_unified_circuit_breaker_manager()
        breaker = manager.create_circuit_breaker("test_service", config)
        print(f"✅ Circuit breaker creation successful: {breaker.config.name}")
        return True
    except Exception as e:
        print(f"❌ Circuit breaker creation failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🔧 Phase 2: Circuit Breaker Configuration Validation Test")
    print("=" * 60)

    tests = [
        ("Import validation", test_imports),
        ("Basic config creation", test_basic_config_creation),
        ("Manager creation", test_manager_creation),
        ("Circuit breaker creation", test_circuit_breaker_creation)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"Test '{test_name}' failed - stopping execution")
            break

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All validation tests PASSED! Phase 2 implementation is working correctly.")
        return 0
    else:
        print("❌ Some tests FAILED. Phase 2 needs debugging.")
        return 1

if __name__ == "__main__":
    sys.exit(main())