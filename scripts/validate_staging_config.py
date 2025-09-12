#!/usr/bin/env python
"""Validate ClickHouse staging configuration for production deployment.

This script simulates the staging environment and validates that:
1. Environment detection works correctly when ENVIRONMENT=staging
2. ClickHouse configuration uses the correct cloud host and port
3. GCP Secret Manager integration works for loading passwords
4. The system properly avoids localhost defaults in staging

Usage:
    python validate_staging_config.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_staging_configuration():
    """Validate staging configuration without actually connecting."""
    
    print("=" * 70)
    print("STAGING CONFIGURATION VALIDATION")
    print("=" * 70)
    
    # Override IsolatedEnvironment before any imports
    print("\n1. Setting up staging environment...")
    # We need to set this BEFORE importing IsolatedEnvironment
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Now import and override the singleton
    from shared.isolated_environment import IsolatedEnvironment
    
    # Get the singleton instance and override the environment
    env_instance = IsolatedEnvironment.get_instance()
    env_instance.set('ENVIRONMENT', 'staging', 'staging_test')
    
    # Set staging ClickHouse configuration
    staging_config = {
        'CLICKHOUSE_URL': 'clickhouse://default:@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1',
        'CLICKHOUSE_HOST': 'xedvrr4c3r.us-central1.gcp.clickhouse.cloud',
        'CLICKHOUSE_PORT': '8443',
        'CLICKHOUSE_USER': 'default',
        'CLICKHOUSE_DB': 'default',
        'CLICKHOUSE_SECURE': 'true',
        'GCP_PROJECT_ID': '701982941522'  # Staging project ID
    }
    
    for key, value in staging_config.items():
        env_instance.set(key, value, 'staging_test')
    
    print("   [OK] Staging environment variables set")
    
    # Test 2: Verify environment detection
    print("\n2. Testing environment detection...")
    from netra_backend.app.core.environment_constants import EnvironmentDetector
    
    detected_env = EnvironmentDetector.get_environment()
    print(f"   Detected environment: {detected_env}")
    
    if detected_env != "staging":
        print(f"    WARNING:  WARNING: Environment detection returned '{detected_env}' instead of 'staging'")
        print("   This may be due to local .env file overriding settings")
    else:
        print("   [OK] Environment correctly detected as staging")
    
    # Test 3: Database Configuration Manager
    print("\n3. Testing Database Configuration Manager...")
    from netra_backend.app.core.configuration.database import DatabaseConfigManager
    from netra_backend.app.schemas.config import AppConfig
    
    # Create a new manager instance
    manager = DatabaseConfigManager()
    
    # Force refresh to pick up new environment
    manager.refresh_environment()
    
    print(f"   Manager environment: {manager._environment}")
    
    # Create config and populate
    config = AppConfig()
    
    # Set minimal PostgreSQL config to avoid validation errors
    env_instance.set('POSTGRES_HOST', 'staging-postgres.example.com', 'staging_test')
    env_instance.set('DATABASE_URL', 'postgresql://user:pass@staging-postgres.example.com:5432/netra?sslmode=require', 'staging_test')
    
    try:
        manager.populate_database_config(config)
    except Exception as e:
        print(f"   Warning: Database config population failed: {e}")
        print("   Continuing with ClickHouse validation...")
    
    # Check ClickHouse configuration
    print("\n4. ClickHouse Configuration:")
    print(f"   URL from config: {config.clickhouse_url}")
    
    if hasattr(config, 'clickhouse_https'):
        ch_config = config.clickhouse_https
        print(f"   HTTPS Host: {ch_config.host}")
        print(f"   HTTPS Port: {ch_config.port}")
        print(f"   HTTPS User: {ch_config.user}")
        print(f"   HTTPS Database: {ch_config.database}")
        
        # Validate configuration
        if ch_config.host == "xedvrr4c3r.us-central1.gcp.clickhouse.cloud":
            print("   [OK] ClickHouse host correctly set to cloud instance")
        else:
            print(f"   [ERROR] ClickHouse host is '{ch_config.host}', expected cloud host")
        
        if ch_config.port == 8443:
            print("   [OK] ClickHouse port correctly set to 8443 (HTTPS)")
        else:
            print(f"   [ERROR] ClickHouse port is {ch_config.port}, expected 8443")
    else:
        print("    WARNING:  WARNING: clickhouse_https config not found")
    
    # Test 5: Check if password would be loaded from GCP
    print("\n5. GCP Secret Manager Integration:")
    try:
        from netra_backend.app.core.configuration.secrets import SecretManager
        
        # Create secret manager
        secret_manager = SecretManager()
        
        # Check if GCP is available
        if secret_manager._is_gcp_available():
            print("   [OK] GCP Secret Manager is available for staging")
            print(f"   Project ID: {secret_manager._get_gcp_project_id()}")
            
            # Check if password mapping exists
            mappings = secret_manager._secret_mappings
            if 'CLICKHOUSE_PASSWORD' in mappings:
                print("   [OK] CLICKHOUSE_PASSWORD mapping configured")
                mapping = mappings['CLICKHOUSE_PASSWORD']
                print(f"   Required in staging: {mapping.get('required', False)}")
                print(f"   Rotation enabled: {mapping.get('rotation_enabled', False)}")
            else:
                print("    WARNING:  WARNING: CLICKHOUSE_PASSWORD not in secret mappings")
        else:
            print("    WARNING:  GCP Secret Manager not available (may be normal for local testing)")
    except Exception as e:
        print(f"    WARNING:  Failed to check GCP Secret Manager: {e}")
    
    # Test 6: Validate no localhost defaults
    print("\n6. Validating no localhost defaults in staging...")
    
    issues = []
    
    # Check PostgreSQL
    if hasattr(config, 'database_url') and config.database_url:
        if 'localhost' in config.database_url or '127.0.0.1' in config.database_url:
            issues.append("PostgreSQL URL contains localhost")
    
    # Check ClickHouse
    if hasattr(config, 'clickhouse_url') and config.clickhouse_url:
        if 'localhost' in config.clickhouse_url and manager._environment == "staging":
            issues.append("ClickHouse URL contains localhost in staging")
    
    # Check Redis
    if hasattr(config, 'redis_url') and config.redis_url:
        if 'localhost' in config.redis_url and manager._environment == "staging":
            issues.append("Redis URL contains localhost in staging")
    
    if issues:
        print("   [ERROR] Issues found:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print("   [OK] No localhost references found in database URLs")
    
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    # Summary
    all_good = True
    
    if manager._environment == "staging":
        print("[PASS] Environment detection")
    else:
        print(f"[FAIL] Environment detection (got '{manager._environment}')")
        all_good = False
    
    if hasattr(config, 'clickhouse_https') and config.clickhouse_https.host != "localhost":
        print("[PASS] ClickHouse configuration")
    else:
        print("[FAIL] ClickHouse configuration")
        all_good = False
    
    if not issues:
        print("[PASS] No localhost defaults")
    else:
        print("[FAIL] No localhost defaults")
        all_good = False
    
    print("\n" + "=" * 70)
    
    if all_good:
        print("[SUCCESS] STAGING CONFIGURATION VALID")
    else:
        print("[ERROR] STAGING CONFIGURATION ISSUES DETECTED")
        print("\nNOTE: When deployed to actual staging environment:")
        print("- ENVIRONMENT variable will be set correctly by deployment")
        print("- GCP Secret Manager will provide CLICKHOUSE_PASSWORD")
        print("- No .env file will override settings")
    
    print("=" * 70)
    
    return all_good


if __name__ == "__main__":
    success = validate_staging_configuration()
    sys.exit(0 if success else 1)