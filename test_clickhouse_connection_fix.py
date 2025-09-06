#!/usr/bin/env python
"""
Test script to verify ClickHouse connection fix.
Tests the connection manager's ability to handle missing/stopped ClickHouse service.
"""

import asyncio
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from netra_backend.app.core.clickhouse_connection_manager import (
    ClickHouseConnectionManager,
    get_clickhouse_connection_manager
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def test_connection_manager():
    """Test ClickHouse connection manager with improved error handling."""
    
    print("=" * 80)
    print("CLICKHOUSE CONNECTION FIX VERIFICATION TEST")
    print("=" * 80)
    
    manager = get_clickhouse_connection_manager()
    
    print("\n1. Testing connection manager initialization...")
    try:
        success = await manager.initialize()
        if success:
            print("[OK] Connection manager initialized successfully!")
        else:
            print("[FAIL] Connection manager initialization failed (but handled gracefully)")
    except Exception as e:
        print(f"[FAIL] Connection manager initialization raised exception: {e}")
        
    print("\n2. Testing dependency validation...")
    try:
        validation = await manager.validate_service_dependencies()
        print(f"   - ClickHouse Available: {validation.get('clickhouse_available', False)}")
        print(f"   - Docker Service Healthy: {validation.get('docker_service_healthy', False)}")
        print(f"   - Connection Successful: {validation.get('connection_successful', False)}")
        print(f"   - Query Execution: {validation.get('query_execution', False)}")
        print(f"   - Overall Health: {validation.get('overall_health', False)}")
        
        if validation.get('errors'):
            print(f"   - Errors: {validation['errors']}")
    except Exception as e:
        print(f"❌ Dependency validation failed: {e}")
    
    print("\n3. Testing connection metrics...")
    metrics = manager.get_connection_metrics()
    print(f"   - Connection State: {metrics.get('connection_state', 'unknown')}")
    print(f"   - Connection Attempts: {metrics.get('connection_attempts', 0)}")
    print(f"   - Successful Connections: {metrics.get('successful_connections', 0)}")
    print(f"   - Failed Connections: {metrics.get('failed_connections', 0)}")
    print(f"   - Circuit Breaker State: {metrics.get('circuit_breaker_state', 'unknown')}")
    
    print("\n4. Testing direct connection (with bypass flag)...")
    try:
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        
        async with get_clickhouse_client(bypass_manager=True) as client:
            result = await client.execute("SELECT version()")
            if result:
                print(f"[OK] Direct connection successful! ClickHouse version: {result[0].get('version()', 'unknown')}")
            else:
                print("[FAIL] Direct connection returned empty result")
    except Exception as e:
        print(f"[FAIL] Direct connection failed: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    # Cleanup
    await manager.shutdown()


async def test_configuration():
    """Test ClickHouse configuration loading."""
    print("\n5. Testing configuration loading...")
    try:
        from netra_backend.app.db.clickhouse import get_clickhouse_config
        config = get_clickhouse_config()
        
        if config:
            print(f"[OK] Configuration loaded:")
            print(f"   - Host: {getattr(config, 'host', 'NOT SET')}")
            print(f"   - Port: {getattr(config, 'port', 'NOT SET')}")
            print(f"   - Database: {getattr(config, 'database', 'NOT SET')}")
            print(f"   - User: {getattr(config, 'user', 'NOT SET')}")
            print(f"   - Password: {'***' if getattr(config, 'password', None) else 'NOT SET'}")
        else:
            print("[FAIL] Configuration is None")
    except Exception as e:
        print(f"[FAIL] Configuration loading failed: {e}")


async def main():
    """Run all tests."""
    await test_connection_manager()
    await test_configuration()


if __name__ == "__main__":
    print("Starting ClickHouse connection fix verification...")
    asyncio.run(main())