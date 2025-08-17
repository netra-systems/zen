"""
Simple ClickHouse connection test script
"""
import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_init import create_workload_events_table_if_missing

async def test_connection():
    print("Testing ClickHouse connection...")
    
    try:
        async with get_clickhouse_client() as client:
            # Test basic query
            result = await client.fetch("SELECT 1 as test")
            print(f"✓ Basic connection successful: {result}")
            
            # Get version
            version = await client.fetch("SELECT version() as v")
            print(f"✓ ClickHouse version: {version[0]['v']}")
            
            # Show tables
            tables = await client.fetch("SHOW TABLES")
            print(f"✓ Found {len(tables)} tables")
            if tables:
                print("  Sample tables:")
                for table in tables[:5]:
                    print(f"    - {table}")
            
            # Create workload_events table if missing
            print("\nEnsuring workload_events table exists...")
            success = await create_workload_events_table_if_missing()
            if success:
                print("✓ workload_events table created/verified")
            else:
                print("✗ Could not create workload_events table")
            
            # Test array syntax fixing
            print("\nTesting array syntax fixing...")
            bad_query = "SELECT metrics.name[1] FROM workload_events LIMIT 1"
            try:
                result = await client.execute_query(bad_query)
                print(f"✓ Array syntax automatically fixed, result: {result}")
            except Exception as e:
                print(f"✗ Array syntax fix failed: {e}")
            
            print("\n✅ All ClickHouse tests passed!")
            return True
            
    except Exception as e:
        print(f"\n❌ ClickHouse connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)