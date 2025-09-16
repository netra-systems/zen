#!/usr/bin/env python3
"""
Quick validation script for WebSocketManagerFactory remediation.
Tests that SSOT imports work and WebSocketManagerFactory is properly removed.
"""

import sys
import warnings

def test_ssot_imports():
    """Test that SSOT WebSocket manager imports work."""
    print("Testing SSOT imports...")

    try:
        # Test SSOT import
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        print("✅ SSOT get_websocket_manager import successful")

        # Test that function exists and is callable
        if callable(get_websocket_manager):
            print("✅ get_websocket_manager is callable")
        else:
            print("❌ get_websocket_manager is not callable")
            return False

    except ImportError as e:
        print(f"❌ SSOT import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in SSOT import: {e}")
        return False

    return True

def test_factory_removal():
    """Test that WebSocketManagerFactory references are properly removed."""
    print("\nTesting WebSocketManagerFactory removal...")

    try:
        # Test that WebSocketManagerFactory import fails from canonical_imports
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        print("✅ create_websocket_manager import works (compatibility function)")

        # Test that direct WebSocketManagerFactory import fails
        try:
            from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory
            print("❌ WebSocketManagerFactory still importable (should be removed)")
            return False
        except (ImportError, AttributeError):
            print("✅ WebSocketManagerFactory properly removed from canonical_imports")

    except ImportError as e:
        print(f"❌ Canonical imports test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in factory removal test: {e}")
        return False

    return True

def test_compatibility_layer():
    """Test that compatibility layer still works."""
    print("\nTesting compatibility layer...")

    try:
        # Test that compatibility imports still work
        from netra_backend.app.websocket_core.websocket_manager_factory_compat import create_websocket_manager as compat_create
        print("✅ Compatibility layer create_websocket_manager works")

        from netra_backend.app.websocket_core.websocket_manager_factory_compat import get_websocket_manager_factory as compat_factory
        print("✅ Compatibility layer get_websocket_manager_factory works")

    except ImportError as e:
        print(f"❌ Compatibility layer test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in compatibility test: {e}")
        return False

    return True

def main():
    """Run all validation tests."""
    print("WEBSOCKET MANAGER FACTORY REMEDIATION VALIDATION")
    print("=" * 60)

    all_passed = True

    # Capture warnings to check for deprecation warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Run tests
        tests = [
            ("SSOT Imports", test_ssot_imports),
            ("Factory Removal", test_factory_removal),
            ("Compatibility Layer", test_compatibility_layer),
        ]

        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            print("-" * 40)
            if not test_func():
                all_passed = False

        # Check for warnings
        if w:
            print(f"\n⚠️  Captured {len(w)} warnings:")
            for warning in w:
                print(f"   - {warning.message}")

    # Final result
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Remediation successful!")
        print("   - SSOT patterns working")
        print("   - WebSocketManagerFactory properly removed")
        print("   - Compatibility maintained")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())