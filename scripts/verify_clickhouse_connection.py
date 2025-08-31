#!/usr/bin/env python3
"""
Verify ClickHouse connection is using real service, not mock.
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Unicode output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.db.clickhouse import get_clickhouse_client, use_mock_clickhouse
from netra_backend.app.core.configuration import get_configuration


async def verify_clickhouse():
    """Verify ClickHouse connection and configuration."""
    print("=" * 60)
    print("ClickHouse Connection Verification")
    print("=" * 60)
    
    # Check environment
    env = get_env()
    environment = env.get("ENVIRONMENT", "development")
    print(f"Environment: {environment}")
    
    # Check if mock is being used
    mock_enabled = use_mock_clickhouse()
    print(f"Mock ClickHouse enabled: {mock_enabled}")
    
    # Get configuration
    config = get_configuration()
    clickhouse_mode = getattr(config, 'clickhouse_mode', 'unknown')
    print(f"ClickHouse mode: {clickhouse_mode}")
    
    # Check environment variables
    clickhouse_host = env.get("CLICKHOUSE_HOST", "not set")
    clickhouse_port = env.get("CLICKHOUSE_PORT", "not set")
    clickhouse_enabled = env.get("CLICKHOUSE_ENABLED", "not set")
    dev_mode_disable = env.get("DEV_MODE_DISABLE_CLICKHOUSE", "not set")
    
    print(f"\nEnvironment Variables:")
    print(f"  CLICKHOUSE_HOST: {clickhouse_host}")
    print(f"  CLICKHOUSE_PORT: {clickhouse_port}")
    print(f"  CLICKHOUSE_ENABLED: {clickhouse_enabled}")
    print(f"  DEV_MODE_DISABLE_CLICKHOUSE: {dev_mode_disable}")
    
    # Try to connect
    print("\nAttempting connection...")
    try:
        async with get_clickhouse_client() as client:
            client_type = type(client).__name__
            print(f"Client type: {client_type}")
            
            if "Mock" in client_type:
                print("[WARNING] Using MOCK ClickHouse client!")
                print("   This means analytics data is NOT being stored.")
                return False
            else:
                print("[OK] Using REAL ClickHouse client")
                
                # Try a simple query
                try:
                    result = await client.execute("SELECT 1")
                    print(f"[OK] Query successful: {result}")
                    
                    # Check if we can query the analytics table
                    try:
                        result = await client.execute("SHOW TABLES")
                        print(f"[OK] Tables available: {len(result)} tables")
                        for table in result[:5]:  # Show first 5 tables
                            print(f"   - {table}")
                    except Exception as e:
                        print(f"[WARNING] Could not list tables: {e}")
                    
                    return True
                except Exception as e:
                    print(f"[WARNING] Query failed: {e}")
                    return False
                    
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


def main():
    """Main entry point."""
    success = asyncio.run(verify_clickhouse())
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] ClickHouse is properly configured and using REAL service")
    else:
        print("[FAILURE] ClickHouse is NOT properly configured or using MOCK")
        print("\nTo fix this:")
        print("1. Ensure ClickHouse service is running in Docker Compose")
        print("2. Set DEV_MODE_DISABLE_CLICKHOUSE=false")
        print("3. Set CLICKHOUSE_ENABLED=true")
        print("4. Ensure CLICKHOUSE_HOST and CLICKHOUSE_PORT are set correctly")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()