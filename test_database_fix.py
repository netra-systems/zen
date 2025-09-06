#!/usr/bin/env python3
import os
import sys
import asyncio

# Add project to path
sys.path.insert(0, os.path.abspath('.'))

async def test_db():
    try:
        # Set test environment
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/netra_test'
        
        from netra_backend.app.db.database_manager import get_database_manager
        
        manager = get_database_manager()
        await manager.initialize()
        
        health = await manager.health_check()
        print(f"Database health: {health}")
        
        await manager.close_all()
        print("Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db())
    sys.exit(0 if success else 1)
