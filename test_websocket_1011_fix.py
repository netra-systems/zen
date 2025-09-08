#!/usr/bin/env python3
"""
Test script to validate WebSocket 1011 error fix.

This script tests that:
1. WebSocket manager creation works with proper UserExecutionContext
2. No more "user_context must be a UserExecutionContext instance" errors
3. Factory pattern properly validates SSOT UserExecutionContext types
"""

import sys
import uuid
import asyncio
from contextlib import asynccontextmanager

def test_websocket_manager_creation():
    """Test that WebSocket manager creation works with SSOT UserExecutionContext."""
    print("Testing WebSocket manager creation with SSOT UserExecutionContext...")
    
    try:
        # Import the SSOT UserExecutionContext (services version)
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        # Create a valid UserExecutionContext
        ctx = UserExecutionContext(
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=str(uuid.uuid4())
        )
        
        print(f"[OK] Created UserExecutionContext: {ctx.user_id}")
        
        # Test WebSocket manager creation
        manager = create_websocket_manager(ctx)
        
        print(f"[OK] WebSocket manager created successfully: {type(manager).__name__}")
        print(f"   Manager ID: {id(manager)}")
        print(f"   User Context: {manager.user_context.user_id}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] WebSocket manager creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wrong_userexecutioncontext_type():
    """Test that using wrong UserExecutionContext type fails appropriately."""
    print("\nTesting rejection of wrong UserExecutionContext type...")
    
    try:
        # Import the wrong UserExecutionContext (models version)
        from netra_backend.app.services.user_execution_context import UserExecutionContext as WrongUEC
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        # Create context with wrong type (this should fail)
        wrong_ctx = WrongUEC(
            user_id="user_test",
            thread_id="thread_test",
            run_id="run_test",
            request_id="req_test"
        )
        
        # This should raise "user_context must be a UserExecutionContext instance"
        manager = create_websocket_manager(wrong_ctx)
        
        print("[FAIL] Wrong UserExecutionContext type was accepted - this is a bug!")
        return False
        
    except ValueError as e:
        if "user_context must be a UserExecutionContext instance" in str(e):
            print(f"[OK] Correctly rejected wrong UserExecutionContext type: {e}")
            return True
        else:
            print(f"[FAIL] Unexpected ValueError: {e}")
            return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies_imports():
    """Test that dependencies.py uses correct UserExecutionContext import."""
    print("\nTesting dependencies.py imports...")
    
    try:
        # Check that dependencies imports the correct UserExecutionContext
        from netra_backend.app.dependencies import UserExecutionContext
        
        # Verify it's the services version (SSOT)
        if UserExecutionContext.__module__ == "netra_backend.app.services.user_execution_context":
            print("[OK] dependencies.py imports correct SSOT UserExecutionContext")
            return True
        else:
            print(f"[FAIL] dependencies.py imports wrong UserExecutionContext from: {UserExecutionContext.__module__}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Failed to test dependencies imports: {e}")
        return False

def main():
    """Run all WebSocket 1011 error fix validation tests."""
    print("=" * 60)
    print("WEBSOCKET 1011 ERROR FIX VALIDATION")
    print("=" * 60)
    
    tests = [
        ("WebSocket Manager Creation", test_websocket_manager_creation),
        ("Wrong UserExecutionContext Rejection", test_wrong_userexecutioncontext_type),
        ("Dependencies Import Validation", test_dependencies_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results:
        status = "[PASS]" if passed_test else "[FAIL]"
        print(f"{status}: {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED - WebSocket 1011 errors should be resolved!")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} tests failed - WebSocket 1011 errors may persist")
        return 1

if __name__ == "__main__":
    sys.exit(main())