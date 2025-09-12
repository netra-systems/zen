#!/usr/bin/env python
"""Test script to verify ClickHouse staging configuration fix.

This test verifies that:
1. StagingConfig can be instantiated without ClickHouse env vars
2. Validation correctly identifies missing ClickHouse after instantiation  
3. Validation passes when ClickHouse is properly configured
"""

import os
import sys
from pathlib import Path

# Fix Windows Unicode output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment


def test_staging_config_instantiation():
    """Test that StagingConfig can be instantiated without immediate validation."""
    print("\n=== Test 1: StagingConfig Instantiation ===")
    
    # Setup clean environment
    env = IsolatedEnvironment()
    env.set("ENVIRONMENT", "staging")
    env.set("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters-long")
    env.set("FERNET_KEY", "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
    env.set("SERVICE_SECRET", "test-service-secret-at-least-32-characters")
    env.set("DATABASE_URL", "postgresql://user:pass@staging-db:5432/netra_staging")
    
    # Do NOT set ClickHouse variables
    
    try:
        from netra_backend.app.schemas.config import StagingConfig
        
        # This should NOT raise an error anymore
        config = StagingConfig()
        print("[U+2713] StagingConfig instantiated successfully without ClickHouse env vars")
        
        # But validation should fail
        try:
            config.validate_mandatory_services()
            print("[U+2717] Validation should have failed for missing ClickHouse")
            return False
        except ValueError as e:
            if "ClickHouse configuration is MANDATORY" in str(e):
                print(f"[U+2713] Validation correctly identified missing ClickHouse: {e}")
            else:
                print(f"[U+2717] Unexpected validation error: {e}")
                return False
                
    except Exception as e:
        print(f"[U+2717] Failed to instantiate StagingConfig: {e}")
        return False
    
    return True


def test_staging_config_with_clickhouse():
    """Test that StagingConfig validation passes with ClickHouse configured."""
    print("\n=== Test 2: StagingConfig with ClickHouse ===")
    
    # Setup environment with ClickHouse - use non-localhost values for staging
    env = IsolatedEnvironment()
    env.set("ENVIRONMENT", "staging")
    env.set("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters-long")
    env.set("FERNET_KEY", "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
    env.set("SERVICE_SECRET", "test-service-secret-at-least-32-characters")
    env.set("DATABASE_URL", "postgresql://user:pass@staging-db:5432/netra_staging?sslmode=require")
    env.set("POSTGRES_HOST", "staging-db")
    env.set("POSTGRES_USER", "netra_app")
    env.set("POSTGRES_PASSWORD", "staging-password")
    env.set("POSTGRES_DB", "netra_staging")
    env.set("REDIS_HOST", "staging-redis")
    env.set("CLICKHOUSE_HOST", "staging-clickhouse")
    env.set("CLICKHOUSE_USER", "default")
    env.set("CLICKHOUSE_PASSWORD", "staging-password")
    env.set("CLICKHOUSE_DB", "netra_analytics")
    
    try:
        from netra_backend.app.schemas.config import StagingConfig
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        # Create config
        config = StagingConfig()
        print("[U+2713] StagingConfig instantiated")
        
        # Populate ClickHouse configuration
        db_manager = DatabaseConfigManager()
        db_manager.populate_database_config(config)
        print("[U+2713] Database configuration populated")
        
        # Now validation should pass
        try:
            config.validate_mandatory_services()
            print("[U+2713] Validation passed with ClickHouse configured")
        except ValueError as e:
            print(f"[U+2717] Validation failed unexpectedly: {e}")
            return False
            
    except Exception as e:
        print(f"[U+2717] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_full_configuration_flow():
    """Test the complete configuration loading flow."""
    print("\n=== Test 3: Full Configuration Flow ===")
    
    # Setup staging environment
    env = IsolatedEnvironment()
    env.set("ENVIRONMENT", "staging")
    env.set("JWT_SECRET_KEY", "staging-jwt-secret-key-at-least-32-characters")
    env.set("FERNET_KEY", "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
    env.set("SERVICE_SECRET", "staging-service-secret-at-least-32-chars")
    env.set("GCP_PROJECT_ID", "netra-staging")
    env.set("DATABASE_URL", "postgresql://user:pass@/netra_staging?host=/cloudsql/project:region:instance")
    env.set("POSTGRES_HOST", "/cloudsql/project:region:instance")
    env.set("POSTGRES_USER", "netra_app")
    env.set("POSTGRES_PASSWORD", "staging-db-password")
    env.set("POSTGRES_DB", "netra_staging")
    env.set("REDIS_HOST", "10.0.0.5")
    env.set("REDIS_PORT", "6379")
    env.set("CLICKHOUSE_HOST", "10.0.0.10")
    env.set("CLICKHOUSE_PORT", "8443")
    env.set("CLICKHOUSE_USER", "default")
    env.set("CLICKHOUSE_PASSWORD", "ch-staging-password")
    env.set("CLICKHOUSE_DB", "netra_analytics")
    env.set("CLICKHOUSE_SECURE", "true")
    
    try:
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        # Use the actual configuration manager
        config_manager = UnifiedConfigManager()
        config = config_manager.get_config()
        
        print(f"[U+2713] Configuration loaded for environment: {config.environment}")
        print(f"[U+2713] ClickHouse host: {config.clickhouse_native.host if hasattr(config, 'clickhouse_native') else 'Not set'}")
        print(f"[U+2713] Redis host: {config.redis.host if hasattr(config, 'redis') else 'Not set'}")
        print(f"[U+2713] Database URL configured: {'Yes' if config.database_url else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"[U+2717] Configuration flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("ClickHouse Staging Configuration Fix Tests")
    print("=" * 60)
    
    tests = [
        test_staging_config_instantiation,
        test_staging_config_with_clickhouse,
        test_full_configuration_flow
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n[U+2717] Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[U+2713] All {total} tests passed!")
        return 0
    else:
        print(f"[U+2717] {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())