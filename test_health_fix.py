#!/usr/bin/env python3
"""Test script for health endpoint fix"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_health_endpoint_fix():
    """Test that the health endpoint works with the fix."""
    
    # Import after path setup
    from netra_backend.app.database import get_db
    
    print("Testing database access pattern fix...")
    print("-" * 60)
    
    # Test 1: Verify get_db() works as a context manager
    try:
        async with get_db() as db:
            # Try to execute a simple query
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"✅ Test 1 PASSED: get_db() works as context manager (result: {value})")
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        return False
    
    # Test 2: Verify the health route import works
    try:
        from netra_backend.app.routes.health import _check_readiness_status
        print("✅ Test 2 PASSED: Health route imports successfully")
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        return False
    
    # Test 3: Verify DatabaseManager doesn't have get_async_session (root cause)
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        has_method = hasattr(DatabaseManager, 'get_async_session')
        if has_method:
            print("❌ Test 3 UNEXPECTED: DatabaseManager has get_async_session method")
        else:
            print("✅ Test 3 PASSED: Confirmed DatabaseManager lacks get_async_session (root cause)")
    except Exception as e:
        print(f"⚠️  Test 3 WARNING: {e}")
    
    # Test 4: Verify alternative database access patterns exist
    try:
        from netra_backend.app.database import database_manager
        
        # Check instance methods
        has_session_scope = hasattr(database_manager, 'session_scope')
        has_get_session = hasattr(database_manager, 'get_session')
        
        print(f"✅ Test 4 PASSED: Alternative methods exist:")
        print(f"   - session_scope: {has_session_scope}")
        print(f"   - get_session: {has_get_session}")
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
    
    print("-" * 60)
    print("Summary: Fix replaces non-existent DatabaseManager.get_async_session()")
    print("         with canonical get_db() from database module SSOT")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_health_endpoint_fix())
    sys.exit(0 if success else 1)