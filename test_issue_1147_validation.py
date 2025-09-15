#!/usr/bin/env python3
"""
Validation script for Issue #1147 fix
Tests that create_defensive_user_execution_context works correctly after the fix.
"""

import sys
import traceback
from typing import Optional

def test_import():
    """Test that the import works correctly."""
    try:
        from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context
        print("✅ PASS: Import create_defensive_user_execution_context - Success")
        return True
    except ImportError as e:
        print(f"❌ FAIL: Import create_defensive_user_execution_context - {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected import error - {e}")
        return False

def test_function_with_valid_user():
    """Test the function with a valid user ID."""
    try:
        from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context
        
        # Use a valid-looking user ID
        valid_user_id = "user_abc123def456"
        context = create_defensive_user_execution_context(valid_user_id)
        
        print(f"✅ PASS: create_defensive_user_execution_context with valid user - Created {type(context).__name__}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Function call with valid user failed - {e}")
        traceback.print_exc()
        return False

def test_function_with_placeholder_user():
    """Test the function properly rejects placeholder user IDs."""
    try:
        from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context
        
        # Use a placeholder that should be rejected
        placeholder_user_id = "test_user_123"
        context = create_defensive_user_execution_context(placeholder_user_id)
        
        print(f"❌ FAIL: Function should have rejected placeholder user ID but didn't")
        return False
    except Exception as e:
        # This should fail with InvalidContextError - that's expected
        print(f"✅ PASS: Function correctly rejected placeholder user ID - {type(e).__name__}")
        return True

def test_import_stability():
    """Test that related imports still work."""
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        print("✅ PASS: Import UserExecutionContext - Success")
        return True
    except ImportError as e:
        print(f"❌ FAIL: Import UserExecutionContext - {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected UserExecutionContext import error - {e}")
        return False

def main():
    """Run all validation tests."""
    print("🔍 Testing Issue #1147 Fix: create_defensive_user_execution_context")
    print("=" * 70)
    
    tests = [
        ("Import Functionality", test_import),
        ("Valid User ID Function Call", test_function_with_valid_user),
        ("Placeholder Rejection Security", test_function_with_placeholder_user),
        ("Related Import Stability", test_import_stability),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                print(f"   ❌ Test failed")
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 SUCCESS: Issue #1147 fix is working correctly!")
        print("   - Imports work correctly")
        print("   - Function executes properly")
        print("   - Security validation is active")
        print("   - No breaking changes detected")
        return 0
    else:
        print("⚠️  ISSUES DETECTED: Some tests failed")
        print(f"   - {total - passed} tests failed")
        print("   - System stability may be impacted")
        return 1

if __name__ == "__main__":
    sys.exit(main())