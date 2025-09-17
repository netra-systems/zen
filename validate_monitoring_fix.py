#!/usr/bin/env python3
"""
Comprehensive validation script for Issue #1204 monitoring module import fix.
This script validates that the monitoring module exports are working correctly
and that the specific middleware import that was failing now works.
"""

import sys
import traceback
from pathlib import Path

def test_basic_monitoring_imports():
    """Test basic monitoring module imports."""
    print("🔍 Testing basic monitoring module imports...")

    try:
        # Test the specific import that was failing in the middleware
        from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
        print("✅ PASS: Direct import from gcp_error_reporter works")

        # Test that these functions are also available from the module __init__
        from netra_backend.app.services.monitoring import set_request_context, clear_request_context
        print("✅ PASS: Import from monitoring module __init__ works")

        # Test other required exports
        from netra_backend.app.services.monitoring import GCPErrorReporter, get_error_reporter
        print("✅ PASS: GCPErrorReporter and get_error_reporter imports work")

        return True

    except ImportError as e:
        print(f"❌ FAIL: Basic imports failed: {e}")
        traceback.print_exc()
        return False

def test_middleware_specific_import():
    """Test the exact import pattern used in the middleware that was failing."""
    print("\n🔍 Testing middleware-specific import pattern...")

    try:
        # This is the exact import from line 27 of gcp_auth_context_middleware.py
        from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context

        # Verify the functions are callable
        if not callable(set_request_context):
            raise ValueError("set_request_context is not callable")
        if not callable(clear_request_context):
            raise ValueError("clear_request_context is not callable")

        print("✅ PASS: Middleware import pattern works correctly")
        print(f"✅ PASS: set_request_context is callable: {callable(set_request_context)}")
        print(f"✅ PASS: clear_request_context is callable: {callable(clear_request_context)}")

        return True

    except Exception as e:
        print(f"❌ FAIL: Middleware import pattern failed: {e}")
        traceback.print_exc()
        return False

def test_function_execution():
    """Test that the imported functions can actually be executed."""
    print("\n🔍 Testing function execution...")

    try:
        from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context

        # Test calling the functions with minimal parameters
        set_request_context("test-user-123", "test-trace-456")
        print("✅ PASS: set_request_context executes without error")

        clear_request_context()
        print("✅ PASS: clear_request_context executes without error")

        return True

    except Exception as e:
        print(f"❌ FAIL: Function execution failed: {e}")
        traceback.print_exc()
        return False

def test_module_all_exports():
    """Test that all expected exports are available in __all__."""
    print("\n🔍 Testing module __all__ exports...")

    try:
        import netra_backend.app.services.monitoring as monitoring_module

        expected_exports = [
            "GCPErrorService",
            "GCPClientManager",
            "ErrorFormatter",
            "GCPRateLimiter",
            "GCPErrorReporter",
            "get_error_reporter",
            "set_request_context",
            "clear_request_context"
        ]

        actual_all = getattr(monitoring_module, '__all__', [])
        print(f"📋 Module __all__ exports: {actual_all}")

        missing_exports = [exp for exp in expected_exports if exp not in actual_all]
        if missing_exports:
            print(f"❌ FAIL: Missing exports in __all__: {missing_exports}")
            return False

        # Test that all exports are actually importable
        for export_name in expected_exports:
            if hasattr(monitoring_module, export_name):
                print(f"✅ PASS: {export_name} is available")
            else:
                print(f"❌ FAIL: {export_name} is not available as attribute")
                return False

        return True

    except Exception as e:
        print(f"❌ FAIL: Module exports test failed: {e}")
        traceback.print_exc()
        return False

def test_app_startup_simulation():
    """Simulate parts of app startup to check if monitoring imports work in that context."""
    print("\n🔍 Testing app startup simulation...")

    try:
        # Try to import the middleware that was failing
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        print("✅ PASS: GCPAuthContextMiddleware import successful")

        # Try to create an instance
        middleware = GCPAuthContextMiddleware(None)
        print("✅ PASS: GCPAuthContextMiddleware instantiation successful")

        return True

    except Exception as e:
        print(f"❌ FAIL: App startup simulation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main validation routine."""
    print("=" * 70)
    print("🚀 MONITORING MODULE IMPORT FIX VALIDATION")
    print("Issue #1204: Monitoring Module Import Failure")
    print("=" * 70)

    tests = [
        ("Basic Monitoring Imports", test_basic_monitoring_imports),
        ("Middleware Import Pattern", test_middleware_specific_import),
        ("Function Execution", test_function_execution),
        ("Module Exports", test_module_all_exports),
        ("App Startup Simulation", test_app_startup_simulation)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print(f"{'='*50}")

        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            failed += 1
            print(f"❌ {test_name}: FAILED")

    print("\n" + "=" * 70)
    print(f"📊 FINAL RESULTS")
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Issue #1204 fix is working correctly")
        print("✅ Monitoring module imports are stable")
        print("✅ System is ready for deployment")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("❌ Issue #1204 fix needs additional work")
        print("❌ System not ready for deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())