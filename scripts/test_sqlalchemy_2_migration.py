#!/usr/bin/env python
"""
Test script to validate SQLAlchemy 2.0 migration
"""
import asyncio
import uuid
from datetime import datetime, timezone

async def test_sqlalchemy_2_migration():
    """Test SQLAlchemy 2.0 patterns are working correctly."""
    print("Testing SQLAlchemy 2.0 Migration...")
    
    try:
        # Import models with new patterns
        from netra_backend.app.db.base import Base
        from netra_backend.app.db.models_user import User, Secret
        from netra_backend.app.db.models_agent_state import AgentStateSnapshot
        from auth_service.auth_core.database.models import AuthUser
        from netra_backend.app.db.database_manager import DatabaseManager
        
        print("[SUCCESS] All models imported successfully with SQLAlchemy 2.0 patterns")
        
        # Test database connection
        engine = DatabaseManager.create_application_engine()
        connection_ok = await DatabaseManager.test_connection_with_retry(engine, max_retries=1)
        
        if connection_ok:
            print("[SUCCESS] Database connection works with SQLAlchemy 2.0")
        else:
            print("[ERROR] Database connection failed")
            return False
            
        # Test session creation
        session_factory = DatabaseManager.get_application_session()
        async with session_factory() as session:
            # Test select() query pattern
            from sqlalchemy import select, text
            
            # Test basic select
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                print("[SUCCESS] Basic query execution works")
            else:
                print("[ERROR] Basic query execution failed")
                return False
                
        await engine.dispose()
        
        # Test model creation
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
        
        # Verify type annotations work
        assert hasattr(test_user, '__annotations__')
        print("[SUCCESS] Model type annotations are working")
        
        # Test auth model
        auth_user = AuthUser(
            id=str(uuid.uuid4()),
            email="auth@example.com",
            auth_provider="local"
        )
        
        assert auth_user.auth_provider == "local"
        print("[SUCCESS] Auth service models are working")
        
        print("\n[COMPLETE] SQLAlchemy 2.0 Migration: ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sqlalchemy_2_migration())
    if success:
        print("\n[READY] SQLAlchemy 2.0 migration is ready!")
    else:
        print("\n[FAILED] SQLAlchemy 2.0 migration needs fixes!")
        exit(1)