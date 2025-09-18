#!/usr/bin/env python3
"""
Import validation test for infrastructure resilience components.
Tests that all new modules can be imported without circular dependencies.
"""

import sys
import traceback

def test_import(module_name, description):
    """Test import of a module and report result."""
    try:
        __import__(module_name)
        print(f"✅ {description}: Import successful")
        return True
    except Exception as e:
        print(f"❌ {description}: Import failed - {e}")
        print(f"   Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all import validation tests."""
    print("🔍 Infrastructure Resilience Import Validation Test")
    print("=" * 60)

    success_count = 0
    total_tests = 0

    # Test infrastructure resilience components
    tests = [
        ("netra_backend.app.services.infrastructure_resilience", "InfrastructureResilienceManager"),
        ("netra_backend.app.resilience.circuit_breaker", "CircuitBreaker"),
        ("netra_backend.app.core.database_timeout_config", "DatabaseTimeoutConfig"),
    ]

    for module_name, description in tests:
        total_tests += 1
        if test_import(module_name, description):
            success_count += 1

    # Test specific classes can be imported
    print("\n🔍 Testing specific class imports:")
    try:
        from netra_backend.app.services.infrastructure_resilience import InfrastructureResilienceManager
        print("✅ InfrastructureResilienceManager class: Import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ InfrastructureResilienceManager class: Import failed - {e}")
    total_tests += 1

    try:
        from netra_backend.app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerState
        print("✅ CircuitBreaker classes: Import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ CircuitBreaker classes: Import failed - {e}")
    total_tests += 1

    print("\n" + "=" * 60)
    print(f"📊 Import Validation Results: {success_count}/{total_tests} successful")

    if success_count == total_tests:
        print("🎉 All imports successful - No circular dependencies detected")
        return 0
    else:
        print("⚠️  Some imports failed - Please review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())