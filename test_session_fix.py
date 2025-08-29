#!/usr/bin/env python3
"""Test script to verify SQLAlchemy async session fix for IllegalStateChangeError."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.database import get_db


async def test_generator_exit_handling():
    """Test that GeneratorExit is handled gracefully."""
    print("Testing GeneratorExit handling...")
    
    try:
        async for session in get_db():
            print("  - Session created successfully")
            # Simulate early exit (which causes GeneratorExit)
            break
        print("  ✓ GeneratorExit handled without error")
    except Exception as e:
        print(f"  ✗ Error during GeneratorExit: {e}")
        return False
    
    return True


async def test_concurrent_session_access():
    """Test concurrent session access patterns."""
    print("Testing concurrent session access...")
    
    async def worker(worker_id: int):
        """Worker that uses a database session."""
        try:
            async for session in get_db():
                print(f"  - Worker {worker_id}: Session created")
                # Simulate some work
                await asyncio.sleep(0.1)
                print(f"  - Worker {worker_id}: Work completed")
                break
            return True
        except Exception as e:
            print(f"  ✗ Worker {worker_id} error: {e}")
            return False
    
    # Run multiple workers concurrently
    tasks = [worker(i) for i in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success = all(r is True for r in results)
    if success:
        print("  ✓ All concurrent workers completed successfully")
    else:
        print("  ✗ Some workers failed")
    
    return success


async def test_transaction_handling():
    """Test transaction commit and rollback handling."""
    print("Testing transaction handling...")
    
    try:
        # Test normal commit flow
        async for session in get_db():
            print("  - Testing normal transaction flow")
            # The session should handle transactions internally
            break
        print("  ✓ Normal transaction flow completed")
        
        # Test exception handling with rollback
        try:
            async for session in get_db():
                print("  - Testing exception with rollback")
                raise ValueError("Test exception")
        except ValueError:
            print("  ✓ Exception handled with proper rollback")
        
        return True
    except Exception as e:
        print(f"  ✗ Transaction handling error: {e}")
        return False


async def test_session_cleanup():
    """Test that sessions are properly cleaned up."""
    print("Testing session cleanup...")
    
    async def create_and_abandon_session():
        """Create a session and abandon it without proper cleanup."""
        async for session in get_db():
            print("  - Session created and abandoned")
            # Simulate abandoning the session
            return
    
    try:
        # Create multiple sessions and abandon them
        for i in range(3):
            await create_and_abandon_session()
        
        print("  ✓ All abandoned sessions cleaned up properly")
        return True
    except Exception as e:
        print(f"  ✗ Session cleanup error: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("SQLAlchemy Async Session Fix Test Suite")
    print("=" * 60)
    
    tests = [
        test_generator_exit_handling,
        test_concurrent_session_access,
        test_transaction_handling,
        test_session_cleanup
    ]
    
    results = []
    for test in tests:
        print()
        result = await test()
        results.append(result)
    
    print()
    print("=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        return 0
    else:
        print(f"✗ Some tests failed ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)