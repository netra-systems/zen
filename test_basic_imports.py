#!/usr/bin/env python3
"""
Basic import test for Issue #1176 Phase 3 validation.
Tests that critical imports work without Docker dependencies.
"""

def test_basic_python():
    """Test basic Python functionality."""
    print("✓ Basic Python works")
    return True

def test_netra_backend_import():
    """Test if netra_backend can be imported."""
    try:
        from netra_backend.app.main import app
        print("✓ Backend main import works")
        return True
    except Exception as e:
        print(f"✗ Backend import failed: {e}")
        return False

def test_auth_service_import():
    """Test if auth_service can be imported."""
    try:
        from auth_service.main import app
        print("✓ Auth service import works")
        return True
    except Exception as e:
        print(f"✗ Auth service import failed: {e}")
        return False

def test_test_framework_import():
    """Test if test framework can be imported."""
    try:
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        print("✓ Test framework import works")
        return True
    except Exception as e:
        print(f"✗ Test framework import failed: {e}")
        return False

def test_unified_test_runner_import():
    """Test if unified test runner can be imported."""
    try:
        import sys
        sys.path.insert(0, 'tests')
        from unified_test_runner import UnifiedTestRunner
        print("✓ Unified test runner import works")
        return True
    except Exception as e:
        print(f"✗ Unified test runner import failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Issue #1176 Phase 3 Validation: Basic Import Tests ===")

    tests = [
        test_basic_python,
        test_netra_backend_import,
        test_auth_service_import,
        test_test_framework_import,
        test_unified_test_runner_import,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")

    print(f"\n=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("✓ All basic imports working - infrastructure is healthy")
        exit(0)
    else:
        print("✗ Some imports failed - infrastructure issues detected")
        exit(1)