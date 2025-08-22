#!/usr/bin/env python3
"""Debug database test to verify table creation works"""

import asyncio
import os
import sys

# Set environment variables 
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes"

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

async def test_database_setup():
    """Test database initialization and table creation"""
    print("Starting database test...")
    
    from auth_core.database.connection import auth_db
    from auth_core.database.models import Base, AuthSession
    from datetime import datetime, timezone, timedelta
    
    try:
        # Initialize database
        print("Initializing database...")
        await auth_db.initialize()
        print(f"Database initialized: {auth_db._initialized}")
        
        # Check engine
        print(f"Engine: {auth_db.engine}")
        
        # Create tables explicitly
        print("Creating tables...")
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tables created in transaction")
            
            # List tables within the same transaction
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            print(f"Tables found in transaction: {[table[0] for table in tables]}")
        
        # List tables after transaction
        print("Checking tables after transaction...")
        async with auth_db.engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            print(f"Tables found after transaction: {[table[0] for table in tables]}")
        
        # Try creating a session
        print("Creating test session...")
        session = auth_db.async_session_maker()
        
        # Create test AuthSession
        test_session = AuthSession(
            id="test123",
            user_id="user123", 
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        session.add(test_session)
        await session.commit()
        print("Test session created successfully!")
        
        await session.close()
        await auth_db.close()
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Need to import text here
    from sqlalchemy import text
    asyncio.run(test_database_setup())