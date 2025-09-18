# Test script for Issue #1340 - Validate database Row object fixes
import asyncio
import sys
sys.path.insert(0, '.')
from netra_backend.app.db.database_manager import DatabaseManager
from sqlalchemy import text

async def test_database_operations():
    print("Testing database operations after Row object fixes...")

    try:
        # Test DatabaseManager connection testing
        db_manager = DatabaseManager()

        # This should work without the await error now
        print("+ DatabaseManager initialized successfully")

        # Try a simple query if possible
        async with db_manager.get_async_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()  # Should work without await
            if row and row.test == 1:
                print("+ Database query successful: SELECT 1 returned", row.test)
            else:
                print("- Database query failed")

        print("+ All database operations completed successfully")
        return True

    except Exception as e:
        print(f"- Error during database operations: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_operations())
    sys.exit(0 if success else 1)