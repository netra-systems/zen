#!/usr/bin/env python3
"""
Test script to validate Analytics Service ClickHouse connection.

This script tests that the analytics service can properly connect to ClickHouse
using the corrected configuration (native protocol on port 9000).
"""
import asyncio
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics_service.analytics_core.database.connection import (
    get_clickhouse_manager,
    get_redis_manager,
    ClickHouseHealthChecker,
    RedisHealthChecker
)
from analytics_service.analytics_core.config import get_config


async def test_clickhouse_connection():
    """Test ClickHouse connection and basic operations."""
    print("=" * 60)
    print("Testing ClickHouse Connection")
    print("=" * 60)
    
    try:
        # Get configuration
        config = get_config()
        print(f"Environment: {config.environment}")
        print(f"ClickHouse Host: {config.clickhouse_host}")
        print(f"ClickHouse Port: {config.clickhouse_port}")
        print(f"ClickHouse Database: {config.clickhouse_database}")
        print()
        
        # Get manager and initialize
        print("Initializing ClickHouse manager...")
        manager = get_clickhouse_manager()
        await manager.initialize()
        print("[U+2713] ClickHouse manager initialized")
        
        # Test health check
        print("\nTesting ClickHouse health check...")
        checker = ClickHouseHealthChecker()
        health = await checker.check_health()
        
        if health["status"] == "healthy":
            print(f"[U+2713] ClickHouse is healthy")
            print(f"  - Latency: {health.get('latency_ms', 'N/A'):.2f}ms")
            print(f"  - Connection pool size: {health.get('pool_size', 'N/A')}")
        else:
            print(f"[U+2717] ClickHouse is unhealthy: {health.get('error', 'Unknown error')}")
            return False
        
        # Test a simple query
        print("\nTesting simple query...")
        async with manager.get_connection() as client:
            result = await asyncio.to_thread(
                lambda: client.execute("SELECT version()")
            )
            print(f"[U+2713] Query successful - ClickHouse version: {result[0][0]}")
        
        # Test table creation
        print("\nTesting table operations...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS analytics.test_events (
            timestamp DateTime,
            event_type String,
            user_id String,
            data String
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, user_id)
        """
        
        await manager.execute_command(create_table_sql)
        print("[U+2713] Test table created/verified")
        
        # Get table info
        table_info = await manager.get_table_info("test_events")
        print(f"[U+2713] Table has {table_info['total_columns']} columns")
        
        return True
        
    except Exception as e:
        print(f"[U+2717] ClickHouse test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_redis_connection():
    """Test Redis connection."""
    print("\n" + "=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)
    
    try:
        # Get configuration
        config = get_config()
        print(f"Redis Host: {config.redis_host}")
        print(f"Redis Port: {config.redis_port}")
        print(f"Redis DB: {config.redis_db}")
        print()
        
        # Get manager and initialize
        print("Initializing Redis manager...")
        manager = get_redis_manager()
        await manager.initialize()
        print("[U+2713] Redis manager initialized")
        
        # Test health check
        print("\nTesting Redis health check...")
        checker = RedisHealthChecker()
        health = await checker.check_health()
        
        if health["status"] == "healthy":
            print(f"[U+2713] Redis is healthy")
            print(f"  - Latency: {health.get('latency_ms', 'N/A'):.2f}ms")
        else:
            print(f"[U+2717] Redis is unhealthy: {health.get('error', 'Unknown error')}")
            return False
        
        # Test basic operations
        print("\nTesting Redis operations...")
        test_key = "analytics:test:key"
        test_value = "test_value"
        
        # Set a value
        await manager.set(test_key, test_value, ttl=60)
        print(f"[U+2713] Set test key: {test_key}")
        
        # Get the value
        retrieved = await manager.get(test_key)
        if retrieved == test_value:
            print(f"[U+2713] Retrieved correct value: {retrieved}")
        else:
            print(f"[U+2717] Retrieved incorrect value: {retrieved}")
            return False
        
        # Clean up
        await manager.delete(test_key)
        print("[U+2713] Cleaned up test key")
        
        return True
        
    except Exception as e:
        print(f"[U+2717] Redis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all connection tests."""
    print("\nAnalytics Service Connection Test")
    print("==================================\n")
    
    # Test ClickHouse
    clickhouse_ok = await test_clickhouse_connection()
    
    # Test Redis
    redis_ok = await test_redis_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if clickhouse_ok and redis_ok:
        print("[U+2713] All connections successful!")
        print("\nThe Analytics Service can now properly connect to:")
        print("  - ClickHouse on native protocol (port 9000)")
        print("  - Redis for caching")
        return 0
    else:
        print("[U+2717] Some connections failed")
        if not clickhouse_ok:
            print("  - ClickHouse connection FAILED")
            print("    Check that CLICKHOUSE_PORT=9000 (not 8123)")
        if not redis_ok:
            print("  - Redis connection FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)