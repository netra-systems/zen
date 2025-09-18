#!/usr/bin/env python3
"""
Test import stability and check for circular imports or other issues.
"""

import sys

def test_basic_imports():
    """Test basic imports that might reveal issues."""
    print("🔍 Testing basic imports...")

    imports_to_test = [
        "netra_backend.app.services.monitoring",
        "netra_backend.app.services.monitoring.gcp_error_reporter",
        "netra_backend.app.middleware.gcp_auth_context_middleware",
        "netra_backend.app.core.app_factory",
    ]

    failed = []
    for import_name in imports_to_test:
        try:
            __import__(import_name)
            print(f"✅ {import_name}")
        except Exception as e:
            print(f"❌ {import_name}: {e}")
            failed.append((import_name, str(e)))

    return len(failed) == 0, failed

def test_function_availability():
    """Test that required functions are available."""
    print("\n🔍 Testing function availability...")

    try:
        from netra_backend.app.services.monitoring import set_request_context, clear_request_context

        # Check if functions are callable
        if not callable(set_request_context):
            raise ValueError("set_request_context is not callable")
        if not callable(clear_request_context):
            raise ValueError("clear_request_context is not callable")

        print("✅ Required functions are available and callable")
        return True
    except Exception as e:
        print(f"❌ Function availability test failed: {e}")
        return False

def test_module_exports():
    """Test that module exports are correct."""
    print("\n🔍 Testing module exports...")

    try:
        import netra_backend.app.services.monitoring as monitoring

        expected_exports = ["set_request_context", "clear_request_context", "GCPErrorReporter"]
        missing = []

        for export in expected_exports:
            if not hasattr(monitoring, export):
                missing.append(export)

        if missing:
            print(f"❌ Missing exports: {missing}")
            return False
        else:
            print("✅ All expected exports are available")
            return True

    except Exception as e:
        print(f"❌ Module exports test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 IMPORT STABILITY TEST")
    print("Testing for circular imports and stability issues")
    print("=" * 60)

    basic_success, failed_imports = test_basic_imports()
    function_success = test_function_availability()
    export_success = test_module_exports()

    print("\n" + "=" * 60)
    print("📊 SUMMARY")

    if basic_success and function_success and export_success:
        print("🎉 ALL STABILITY TESTS PASSED!")
        print("✅ No circular import issues detected")
        print("✅ All required functions available")
        print("✅ Module exports are correct")
        return 0
    else:
        print("💥 STABILITY ISSUES DETECTED!")
        if not basic_success:
            print("❌ Basic import failures:")
            for name, error in failed_imports:
                print(f"  - {name}: {error}")
        if not function_success:
            print("❌ Function availability issues")
        if not export_success:
            print("❌ Module export issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())