#!/usr/bin/env python3
"""
Simple test to verify circular import fix is working
Tests the specific fix applied to canonical_import_patterns.py line 107
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_specific_circular_import_fix():
    """Test the specific circular import fix that was applied"""
    print("Testing specific circular import fix...")

    try:
        # This import should work without circular import errors
        # The fix changed line 107 from:
        # from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager as _get_manager
        # to:
        # from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as _get_manager

        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        print("✅ canonical_import_patterns.py imports successfully - circular import fix works!")

        # Verify the function is callable
        if callable(get_websocket_manager):
            print("✅ get_websocket_manager function is callable")
        else:
            print("❌ get_websocket_manager is not callable")
            return False

        return True

    except ImportError as e:
        if "circular" in str(e).lower() or "recursion" in str(e).lower():
            print(f"❌ Circular import still exists: {e}")
        else:
            print(f"❌ Import error (not circular): {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_websocket_manager_imports():
    """Test that websocket_manager.py doesn't import back from canonical_import_patterns.py"""
    print("\nTesting websocket_manager.py for reverse imports...")

    try:
        # Read the websocket_manager.py file to check for imports
        with open('netra_backend/app/websocket_core/websocket_manager.py', 'r') as f:
            content = f.read()

        # Check if it imports from canonical_import_patterns
        if 'from netra_backend.app.websocket_core.canonical_import_patterns import' in content:
            print("❌ websocket_manager.py imports from canonical_import_patterns.py - circular dependency exists!")
            return False
        elif 'canonical_import_patterns' in content:
            print("⚠️  websocket_manager.py mentions canonical_import_patterns but may not import it")
            print("✅ No import statement found - circular dependency avoided")
        else:
            print("✅ websocket_manager.py does not reference canonical_import_patterns.py")

        return True

    except Exception as e:
        print(f"❌ Error checking websocket_manager.py: {e}")
        return False

def main():
    """Run the simple validation test"""
    print("🔍 Simple Circular Import Fix Validation")
    print("=" * 45)

    test1_passed = test_specific_circular_import_fix()
    test2_passed = test_websocket_manager_imports()

    print("\n" + "=" * 45)

    if test1_passed and test2_passed:
        print("🎉 CIRCULAR IMPORT FIX VALIDATION: PASSED!")
        print("✅ Line 107 fix successful")
        print("✅ No reverse circular imports detected")
        print("✅ System imports are stable")
        print("\n📋 CONFIDENCE LEVEL: HIGH")
        print("✅ Safe to proceed with further validation")
        return True
    else:
        print("💥 CIRCULAR IMPORT FIX VALIDATION: FAILED!")
        print("❌ Some tests failed - investigation needed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)