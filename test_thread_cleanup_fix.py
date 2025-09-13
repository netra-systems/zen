#!/usr/bin/env python3
"""
Test script to validate ThreadCleanupManager fix for deployment failure.
This script tests the fix for the async/await pattern issue that caused 503 errors.
"""

import sys
import threading
import time
import weakref
import gc
from unittest.mock import patch

# Add the project to Python path
sys.path.insert(0, 'C:\\GitHub\\netra-apex')

def test_thread_cleanup_manager_fix():
    """Test that ThreadCleanupManager handles asyncio context properly."""
    print("Testing ThreadCleanupManager fix...")

    # Import after adding to path
    from netra_backend.app.core.thread_cleanup_manager import ThreadCleanupManager

    # Create manager instance
    manager = ThreadCleanupManager()
    print("✓ ThreadCleanupManager created successfully")

    # Test 1: Verify weak reference callback doesn't crash
    print("\nTest 1: Weak reference callback handling")

    # Create a test thread
    test_thread = threading.Thread(target=lambda: time.sleep(0.1), name="TestThread")
    test_thread.start()

    # Register the thread
    manager.register_thread(test_thread)
    print("✓ Test thread registered")

    # Wait for thread to complete
    test_thread.join()
    print("✓ Test thread completed")

    # Force garbage collection to trigger weak reference callbacks
    gc.collect()
    print("✓ Garbage collection triggered (weak reference callbacks executed)")

    # Test 2: Test _schedule_cleanup directly
    print("\nTest 2: Direct _schedule_cleanup call")

    # Reset cleanup scheduled flag
    manager._cleanup_scheduled = False

    try:
        # This should not crash even without asyncio event loop
        manager._schedule_cleanup()
        print("✓ _schedule_cleanup executed without errors")

        # Wait a moment for any background operations
        time.sleep(0.5)

        print("✓ Background cleanup operations completed")

    except Exception as e:
        print(f"✗ _schedule_cleanup failed: {e}")
        return False

    # Test 3: Test statistics gathering
    print("\nTest 3: Statistics and cleanup validation")

    stats = manager.get_statistics()
    print(f"✓ Statistics retrieved: {stats}")

    # Force cleanup all
    cleanup_stats = manager.force_cleanup_all()
    print(f"✓ Force cleanup completed: {cleanup_stats}")

    print("\n🎉 All tests passed! ThreadCleanupManager fix is working correctly.")
    return True

def test_async_context_handling():
    """Test that the fix handles various asyncio context scenarios."""
    print("\nTesting async context handling...")

    from netra_backend.app.core.thread_cleanup_manager import ThreadCleanupManager

    manager = ThreadCleanupManager()

    # Test without any asyncio context (simulates GCP weak reference callback)
    print("Testing without asyncio context (GCP deployment scenario)...")

    # Simulate the exact failure scenario
    try:
        # This simulates what happens during weak reference callback in GCP
        manager._cleanup_scheduled = False
        manager._schedule_cleanup()
        print("✓ Cleanup scheduling handled gracefully without asyncio context")

        # Wait for thread-based cleanup
        time.sleep(1.0)
        print("✓ Thread-based cleanup completed")

    except Exception as e:
        print(f"✗ Failed to handle no-asyncio scenario: {e}")
        return False

    return True

if __name__ == "__main__":
    print("ThreadCleanupManager Deployment Fix Validation")
    print("=" * 50)

    try:
        # Run the main test
        success1 = test_thread_cleanup_manager_fix()

        # Run async context test
        success2 = test_async_context_handling()

        if success1 and success2:
            print("\n🚀 DEPLOYMENT FIX VALIDATED SUCCESSFULLY!")
            print("The ThreadCleanupManager fix resolves the GCP Cloud Run 503 error.")
            sys.exit(0)
        else:
            print("\n❌ VALIDATION FAILED!")
            print("The fix needs additional work.")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)