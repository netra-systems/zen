#!/usr/bin/env python3
"""
Test integration points for monitoring module fix.
This specifically tests the middleware that was failing.
"""

import sys

def test_middleware_import():
    """Test that the middleware can import monitoring functions."""
    print("🔍 Testing middleware import...")

    try:
        # Test the exact import statement from the middleware
        from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
        print("✅ SUCCESS: Middleware import pattern works")
        return True
    except Exception as e:
        print(f"❌ FAILED: Middleware import failed: {e}")
        return False

def test_middleware_instantiation():
    """Test that the middleware can be instantiated."""
    print("🔍 Testing middleware instantiation...")

    try:
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        middleware = GCPAuthContextMiddleware(None)
        print("✅ SUCCESS: Middleware instantiation works")
        return True
    except Exception as e:
        print(f"❌ FAILED: Middleware instantiation failed: {e}")
        return False

def test_app_factory_import():
    """Test that app factory can import without errors."""
    print("🔍 Testing app factory import...")

    try:
        from netra_backend.app.core.app_factory import create_fastapi_app
        print("✅ SUCCESS: App factory import works")
        return True
    except Exception as e:
        print(f"❌ FAILED: App factory import failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 MIDDLEWARE INTEGRATION TEST")
    print("Testing monitoring module integration points")
    print("=" * 60)

    tests = [
        test_middleware_import,
        test_middleware_instantiation,
        test_app_factory_import
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        return 0
    else:
        print("💥 SOME INTEGRATION TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())