#!/usr/bin/env python3
"""
Test Thread ID Consistency Fix - Validation Script

This script validates that the SSOT thread ID consistency fix works correctly,
preventing the WebSocket Factory resource leak bug.

Run: python test_thread_id_consistency_fix.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from shared.id_generation.unified_id_generator import UnifiedIdGenerator

def test_thread_id_consistency():
    """Test that thread_id contains run_id for proper cleanup matching."""
    print("Testing Thread ID Consistency Fix...")
    
    # Generate IDs using the fixed method
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
        user_id="test-user", 
        operation="websocket_factory"
    )
    
    print(f"Generated IDs:")
    print(f"  thread_id: {thread_id}")
    print(f"  run_id: {run_id}")
    print(f"  request_id: {request_id}")
    
    # CRITICAL TEST: thread_id must contain run_id for cleanup to work
    if run_id in thread_id:
        print("PASS: thread_id contains run_id - cleanup will work correctly")
        return True
    else:
        print("FAIL: thread_id does NOT contain run_id - cleanup will fail")
        print(f"Expected thread_id to contain: '{run_id}'")
        print(f"Actual thread_id: '{thread_id}'")
        return False

def test_multiple_generations():
    """Test multiple ID generations to ensure consistency is maintained."""
    print("\nTesting Multiple ID Generations...")
    
    all_passed = True
    for i in range(5):
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
            user_id=f"test-user-{i}", 
            operation="websocket_factory"
        )
        
        if run_id in thread_id:
            print(f"  Generation {i+1}: PASS")
        else:
            print(f"  Generation {i+1}: FAIL")
            print(f"    thread_id: {thread_id}")
            print(f"    run_id: {run_id}")
            all_passed = False
    
    return all_passed

def validate_old_vs_new_pattern():
    """Show the difference between old broken pattern and new fixed pattern."""
    print("\nPattern Comparison (demonstrating the fix):")
    
    # Simulate the OLD BROKEN pattern (for comparison)
    import time
    import secrets
    base_timestamp = int(time.time() * 1000)
    counter_base = 1
    
    old_thread_id = f"thread_websocket_factory_{base_timestamp}_{counter_base}_{secrets.token_hex(4)}"
    old_run_id = f"run_websocket_factory_{base_timestamp}_{counter_base + 1}_{secrets.token_hex(4)}"
    
    print(f"OLD BROKEN Pattern:")
    print(f"  thread_id: {old_thread_id}")
    print(f"  run_id: {old_run_id}")
    print(f"  run_id in thread_id: {old_run_id in old_thread_id} (BROKEN)")
    
    # Show the NEW FIXED pattern
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
        user_id="demo-user", 
        operation="websocket_factory"
    )
    
    print(f"\nNEW FIXED Pattern:")
    print(f"  thread_id: {thread_id}")
    print(f"  run_id: {run_id}")
    print(f"  run_id in thread_id: {run_id in thread_id} (FIXED)")
    
    return True

def main():
    """Run all validation tests."""
    print("="*60)
    print("WEBSOCKET FACTORY THREAD ID CONSISTENCY FIX VALIDATION")
    print("="*60)
    
    tests = [
        test_thread_id_consistency,
        test_multiple_generations, 
        validate_old_vs_new_pattern
    ]
    
    all_passed = True
    for test in tests:
        try:
            result = test()
            all_passed = all_passed and result
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            all_passed = False
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED - Thread ID consistency fix is working!")
        print("This should resolve the WebSocket Factory resource leak bug.")
    else:
        print("SOME TESTS FAILED - Fix needs additional work.")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())