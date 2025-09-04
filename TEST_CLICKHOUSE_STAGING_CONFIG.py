#!/usr/bin/env python3
"""
Test script to verify ClickHouse staging configuration works correctly.

This script simulates staging environment and verifies the configuration
is loaded properly.
"""

import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_staging_config():
    """Test ClickHouse configuration in staging environment."""
    
    print("=" * 80)
    print("TESTING CLICKHOUSE STAGING CONFIGURATION")
    print("=" * 80)
    
    # Set up staging environment
    print("\n1. Setting up staging environment variables...")
    os.environ["ENVIRONMENT"] = "staging"
    
    # ClickHouse configuration
    os.environ["CLICKHOUSE_URL"] = "clickhouse://default:test123@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1"
    os.environ["CLICKHOUSE_HOST"] = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    os.environ["CLICKHOUSE_PORT"] = "8443"
    os.environ["CLICKHOUSE_USER"] = "default"
    os.environ["CLICKHOUSE_PASSWORD"] = "test123"  # Add password
    os.environ["CLICKHOUSE_DB"] = "default"
    os.environ["CLICKHOUSE_SECURE"] = "true"
    
    # PostgreSQL configuration (required for staging)
    os.environ["POSTGRES_HOST"] = "test-postgres"
    os.environ["POSTGRES_USER"] = "postgres"
    os.environ["POSTGRES_PASSWORD"] = "postgres"
    os.environ["POSTGRES_DB"] = "netra_staging"
    os.environ["POSTGRES_PORT"] = "5432"
    
    # Redis configuration (required for staging)
    os.environ["REDIS_HOST"] = "test-redis"
    os.environ["REDIS_PORT"] = "6379"
    
    print("   Environment: staging")
    print("   CLICKHOUSE_URL: clickhouse://default:***@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1")
    
    # Import after environment setup
    from netra_backend.app.logging_config import central_logger as logger
    from netra_backend.app.core.configuration import get_configuration
    from netra_backend.app.db.clickhouse import get_clickhouse_config, _extract_clickhouse_config
    
    print("\n2. Loading configuration...")
    try:
        # Get unified config
        config = get_configuration()
        print(f"   ✓ Loaded {config.__class__.__name__}")
        print(f"   ✓ Environment: {config.environment}")
        print(f"   ✓ ClickHouse mode: {getattr(config, 'clickhouse_mode', 'not set')}")
        
    except Exception as e:
        print(f"   ✗ Failed to load configuration: {e}")
        return False
    
    print("\n3. Extracting ClickHouse configuration...")
    try:
        # Extract ClickHouse config
        ch_config = _extract_clickhouse_config(config)
        print(f"   ✓ Config type: {ch_config.__class__.__name__}")
        print(f"   ✓ Host: {ch_config.host}")
        print(f"   ✓ Port: {ch_config.port}")
        print(f"   ✓ User: {ch_config.user}")
        print(f"   ✓ Database: {ch_config.database}")
        print(f"   ✓ Secure: {ch_config.secure}")
        
        # Verify it's not localhost
        if ch_config.host == "localhost" or ch_config.host == "127.0.0.1":
            print(f"   ✗ ERROR: Host is still localhost!")
            return False
        
        # Verify it's using ClickHouse Cloud
        if "clickhouse.cloud" not in ch_config.host:
            print(f"   ✗ WARNING: Host doesn't appear to be ClickHouse Cloud")
        
        # Verify port is correct
        if ch_config.port != 8443:
            print(f"   ✗ ERROR: Port should be 8443 for ClickHouse Cloud, got {ch_config.port}")
            return False
        
        # Verify secure is enabled
        if not ch_config.secure:
            print(f"   ✗ ERROR: Secure should be True for ClickHouse Cloud")
            return False
        
        print("\n   ✅ Configuration looks correct for staging!")
        
    except Exception as e:
        print(f"   ✗ Failed to extract ClickHouse config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n4. Testing get_clickhouse_config() function...")
    try:
        # Test the main function
        ch_config2 = get_clickhouse_config()
        print(f"   ✓ Got config: {ch_config2.__class__.__name__}")
        print(f"   ✓ Host matches: {ch_config2.host == ch_config.host}")
        print(f"   ✓ Port matches: {ch_config2.port == ch_config.port}")
        
    except Exception as e:
        print(f"   ✗ Failed to get ClickHouse config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ STAGING CONFIGURATION TEST PASSED!")
    print("=" * 80)
    return True


def test_missing_config():
    """Test what happens when configuration is missing."""
    
    print("\n" + "=" * 80)
    print("TESTING MISSING CONFIGURATION HANDLING")
    print("=" * 80)
    
    # Clear environment
    print("\n1. Clearing environment variables...")
    os.environ["ENVIRONMENT"] = "staging"
    os.environ.pop("CLICKHOUSE_URL", None)
    os.environ.pop("CLICKHOUSE_HOST", None)
    os.environ.pop("CLICKHOUSE_PASSWORD", None)
    
    # Import after environment setup
    from netra_backend.app.core.configuration import get_configuration
    from netra_backend.app.db.clickhouse import _extract_clickhouse_config
    
    print("\n2. Attempting to load configuration...")
    try:
        config = get_configuration()
        ch_config = _extract_clickhouse_config(config)
        print(f"   ✗ Should have raised an error but got: {ch_config}")
        return False
        
    except ConnectionError as e:
        print(f"   ✓ Correctly raised ConnectionError: {e}")
        return True
        
    except Exception as e:
        print(f"   ? Raised unexpected error: {e}")
        return False


def test_development_unchanged():
    """Test that development configuration still works."""
    
    print("\n" + "=" * 80)
    print("TESTING DEVELOPMENT CONFIGURATION (UNCHANGED)")
    print("=" * 80)
    
    # Set up development environment
    print("\n1. Setting up development environment...")
    os.environ["ENVIRONMENT"] = "development"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["CLICKHOUSE_PORT"] = "8124"
    os.environ["CLICKHOUSE_USER"] = "netra"
    os.environ["CLICKHOUSE_PASSWORD"] = "netra123"
    os.environ["CLICKHOUSE_DB"] = "netra_analytics"
    
    # Import after environment setup
    from netra_backend.app.core.configuration import get_configuration
    from netra_backend.app.db.clickhouse import _extract_clickhouse_config
    
    print("\n2. Loading development configuration...")
    try:
        config = get_configuration()
        ch_config = _extract_clickhouse_config(config)
        
        print(f"   ✓ Config type: {ch_config.__class__.__name__}")
        print(f"   ✓ Host: {ch_config.host}")
        print(f"   ✓ Port: {ch_config.port}")
        print(f"   ✓ User: {ch_config.user}")
        
        # Should be localhost for dev
        if ch_config.host != "localhost":
            print(f"   ✗ ERROR: Development should use localhost!")
            return False
        
        print("\n   ✅ Development configuration still works!")
        return True
        
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False


if __name__ == "__main__":
    results = []
    
    # Test 1: Staging configuration works
    results.append(("Staging Config", test_staging_config()))
    
    # Test 2: Missing config is handled
    results.append(("Missing Config", test_missing_config()))
    
    # Test 3: Development still works
    results.append(("Development Config", test_development_unchanged()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! The fix works correctly.")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
    
    sys.exit(0 if all_passed else 1)