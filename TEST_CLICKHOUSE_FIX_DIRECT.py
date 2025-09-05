#!/usr/bin/env python3
"""
Direct test of the ClickHouse staging configuration fix.
Tests the _extract_clickhouse_config function directly without full system load.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_extract_config_staging():
    """Test _extract_clickhouse_config with staging config."""
    
    print("=" * 80)
    print("DIRECT TEST: _extract_clickhouse_config for STAGING")
    print("=" * 80)
    
    # Set environment
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["CLICKHOUSE_URL"] = "clickhouse://default:test123@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1"
    os.environ["CLICKHOUSE_PASSWORD"] = "test123"
    
    # Create a mock config object
    class MockStagingConfig:
        environment = "staging"
        clickhouse_mode = "shared"
        
        class clickhouse_https:
            host = None  # Empty - this is the problem we're fixing
            port = None
            user = None
            password = None
            database = None
    
    config = MockStagingConfig()
    
    print(f"\nInput config:")
    print(f"  environment: {config.environment}")
    print(f"  clickhouse_mode: {config.clickhouse_mode}")
    print(f"  clickhouse_https.host: {config.clickhouse_https.host} (empty!)")
    
    # Import and test the function
    from netra_backend.app.db.clickhouse import _extract_clickhouse_config
    
    print("\nCalling _extract_clickhouse_config...")
    try:
        result = _extract_clickhouse_config(config)
        
        print(f"\n✅ SUCCESS! Got config type: {result.__class__.__name__}")
        print(f"  Host: {result.host}")
        print(f"  Port: {result.port}")
        print(f"  User: {result.user}")
        print(f"  Database: {result.database}")
        print(f"  Secure: {result.secure}")
        print(f"  Has password: {bool(result.password)}")
        
        # Verify correctness
        assert result.host == "xedvrr4c3r.us-central1.gcp.clickhouse.cloud", f"Wrong host: {result.host}"
        assert result.port == 8443, f"Wrong port: {result.port}"
        assert result.secure == True, f"Should be secure"
        assert result.user == "default", f"Wrong user: {result.user}"
        assert result.password == "test123", f"Wrong password"
        
        print("\n✅ All assertions passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extract_config_development():
    """Test that development still works."""
    
    print("\n" + "=" * 80)
    print("DIRECT TEST: _extract_clickhouse_config for DEVELOPMENT")
    print("=" * 80)
    
    # Set environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["CLICKHOUSE_USER"] = "netra"
    os.environ["CLICKHOUSE_PASSWORD"] = "netra123"
    os.environ["CLICKHOUSE_DB"] = "netra_analytics"
    
    # Create a mock config object
    class MockDevConfig:
        environment = "development"
        clickhouse_mode = "local"
        
        class clickhouse_http:
            host = "localhost"
            port = 8123
            user = "dev"
            password = "dev"
            database = "dev"
    
    config = MockDevConfig()
    
    print(f"\nInput config:")
    print(f"  environment: {config.environment}")
    print(f"  clickhouse_mode: {config.clickhouse_mode}")
    
    # Import and test the function
    from netra_backend.app.db.clickhouse import _extract_clickhouse_config
    
    print("\nCalling _extract_clickhouse_config...")
    try:
        result = _extract_clickhouse_config(config)
        
        print(f"\n✅ SUCCESS! Got config type: {result.__class__.__name__}")
        print(f"  Host: {result.host}")
        print(f"  Port: {result.port}")
        print(f"  User: {result.user}")
        
        # Development should use localhost
        assert result.host == "localhost", f"Dev should use localhost, got {result.host}"
        assert result.secure == False, f"Dev should not use secure"
        
        print("\n✅ Development config still works!")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


def test_missing_url():
    """Test error handling when URL is missing."""
    
    print("\n" + "=" * 80)
    print("DIRECT TEST: Missing CLICKHOUSE_URL in staging")
    print("=" * 80)
    
    # Clear environment
    os.environ["ENVIRONMENT"] = "staging"
    os.environ.pop("CLICKHOUSE_URL", None)
    os.environ.pop("CLICKHOUSE_HOST", None)
    
    # Create a mock config object
    class MockStagingConfig:
        environment = "staging"
        clickhouse_mode = "shared"
        class clickhouse_https:
            host = None
    
    config = MockStagingConfig()
    
    # Import and test the function
    from netra_backend.app.db.clickhouse import _extract_clickhouse_config
    
    print("\nCalling _extract_clickhouse_config with missing URL...")
    try:
        result = _extract_clickhouse_config(config)
        print(f"❌ Should have raised error, got: {result}")
        return False
        
    except ConnectionError as e:
        print(f"✅ Correctly raised ConnectionError: {str(e)[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Wrong error type: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("TESTING CLICKHOUSE CONFIGURATION FIX")
    print("=" * 80)
    
    results = []
    
    # Test 1: Staging extracts correctly
    results.append(("Staging Extraction", test_extract_config_staging()))
    
    # Test 2: Development still works
    results.append(("Development Extraction", test_extract_config_development()))
    
    # Test 3: Missing URL is handled
    results.append(("Missing URL Handling", test_missing_url()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 THE FIX WORKS! Staging now gets ClickHouse Cloud config correctly.")
        print("\nThe issue was:")
        print("1. No staging-specific handler in _extract_clickhouse_config")
        print("2. It fell back to empty clickhouse_https config")
        print("3. Which defaulted to localhost")
        print("\nThe fix:")
        print("1. Added explicit staging handler")
        print("2. Loads from CLICKHOUSE_URL environment variable")
        print("3. Parses URL to extract host, port, credentials")
        print("4. Returns correct ClickHouse Cloud configuration")
    else:
        print("\n⚠️ Some tests failed. Check the output above.")
    
    sys.exit(0 if all_passed else 1)