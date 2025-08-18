#!/usr/bin/env python
"""Test ClickHouse local connection with unified configuration."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment to use local ClickHouse
os.environ["CLICKHOUSE_MODE"] = "local"
os.environ["ENVIRONMENT"] = "development"

async def test_clickhouse_connection():
    """Test ClickHouse connection using local configuration."""
    print("Testing ClickHouse connection with unified configuration...")
    print(f"CLICKHOUSE_MODE: {os.environ.get('CLICKHOUSE_MODE')}")
    print(f"CLICKHOUSE_HOST: {os.environ.get('CLICKHOUSE_HOST')}")
    print(f"CLICKHOUSE_PORT: {os.environ.get('CLICKHOUSE_HTTP_PORT')}")
    print(f"CLICKHOUSE_USER: {os.environ.get('CLICKHOUSE_USER')}")
    print(f"CLICKHOUSE_DB: {os.environ.get('CLICKHOUSE_DB')}")
    
    try:
        from app.db.clickhouse import get_clickhouse_client, get_clickhouse_config
        
        # Test configuration loading
        config = get_clickhouse_config()
        print(f"\nLoaded config:")
        print(f"  Host: {config.host}")
        print(f"  Port: {config.port}")
        print(f"  User: {config.user}")
        print(f"  Database: {config.database}")
        
        # Test connection
        print("\nTesting connection...")
        async with get_clickhouse_client() as client:
            # Simple query to test connection
            result = await client.execute("SELECT 1 as test")
            print(f"[OK] Connection successful! Result: {result}")
            
            # Test creating a table
            await client.execute("""
                CREATE TABLE IF NOT EXISTS test_local (
                    id UInt32,
                    name String,
                    created DateTime
                ) ENGINE = MergeTree()
                ORDER BY id
            """)
            print("[OK] Table creation successful!")
            
            # Test inserting data
            await client.execute("""
                INSERT INTO test_local (id, name, created) VALUES
                (1, 'test1', now()),
                (2, 'test2', now())
            """)
            print("[OK] Data insertion successful!")
            
            # Test querying data
            result = await client.execute("SELECT * FROM test_local")
            print(f"[OK] Query successful! Rows: {len(result)}")
            
            # Clean up
            await client.execute("DROP TABLE IF EXISTS test_local")
            print("[OK] Cleanup successful!")
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_clickhouse_connection())
    sys.exit(0 if success else 1)