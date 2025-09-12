from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""Test ClickHouse staging configuration and connectivity.

env = get_env()
This script validates:
1. Environment detection is working correctly in staging
2. ClickHouse password is loaded from GCP Secret Manager
3. ClickHouse connection parameters are correct
4. Connection to ClickHouse Cloud succeeds with authentication
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_staging_clickhouse():
    """Test ClickHouse configuration and connectivity in staging."""
    
    # Set staging environment
    env.set('ENVIRONMENT', 'staging', "test")
    env.set('CLICKHOUSE_URL', 'clickhouse://default:@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1', "test")
    env.set('CLICKHOUSE_HOST', 'xedvrr4c3r.us-central1.gcp.clickhouse.cloud', "test")
    env.set('CLICKHOUSE_PORT', '8443', "test")
    env.set('CLICKHOUSE_USER', 'default', "test")
    env.set('CLICKHOUSE_DB', 'default', "test")
    env.set('CLICKHOUSE_SECURE', 'true', "test")
    
    # Set GCP project ID for staging
    env.set('GCP_PROJECT_ID', '701982941522', "test")  # Staging project ID
    
    print("=" * 60)
    print("Testing ClickHouse Staging Configuration")
    print("=" * 60)
    
    # Test 1: Environment Detection
    print("\n1. Testing Environment Detection:")
    from netra_backend.app.core.environment_constants import EnvironmentDetector
    env = EnvironmentDetector.get_environment()
    print(f"   Detected environment: {env}")
    assert env == "staging", f"Expected 'staging', got '{env}'"
    print("   [U+2713] Environment detection correct")
    
    # Test 2: Database Configuration Manager
    print("\n2. Testing Database Configuration Manager:")
    from netra_backend.app.core.configuration.database import DatabaseConfigManager
    from netra_backend.app.schemas.config import AppConfig
    
    manager = DatabaseConfigManager()
    print(f"   Manager environment: {manager._environment}")
    assert manager._environment == "staging", f"Expected 'staging', got '{manager._environment}'"
    
    config = AppConfig()
    manager.populate_database_config(config)
    
    print(f"   ClickHouse URL: {config.clickhouse_url}")
    print(f"   ClickHouse Host: {getattr(config.clickhouse_https, 'host', 'Not set')}")
    print(f"   ClickHouse Port: {getattr(config.clickhouse_https, 'port', 'Not set')}")
    
    # Test 3: Secret Manager Integration
    print("\n3. Testing Secret Manager Integration:")
    try:
        from netra_backend.app.core.configuration.secrets import SecretManager
        secret_manager = SecretManager()
        
        # Try to load secrets
        secrets = secret_manager.load_all_secrets()
        
        if 'CLICKHOUSE_PASSWORD' in secrets:
            print("   [U+2713] CLICKHOUSE_PASSWORD loaded from GCP Secret Manager")
            print(f"   Password length: {len(secrets['CLICKHOUSE_PASSWORD'])} characters")
        else:
            print("    WARNING:  CLICKHOUSE_PASSWORD not found in GCP secrets")
            print("   Available secrets:", list(secrets.keys()))
    except Exception as e:
        print(f"    WARNING:  Failed to load from GCP Secret Manager: {e}")
    
    # Test 4: ClickHouse Connection
    print("\n4. Testing ClickHouse Connection:")
    try:
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            # Try a simple query
            result = await client.execute("SELECT 1 as test")
            print(f"   [U+2713] Connection successful! Query result: {result}")
            
            # Try to get database version
            version_result = await client.execute("SELECT version()")
            print(f"   ClickHouse version: {version_result}")
            
    except Exception as e:
        print(f"   [U+2717] Connection failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_staging_clickhouse())