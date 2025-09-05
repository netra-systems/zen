"""Comprehensive test of DatabaseURLBuilder functionality and edge cases."""

import sys
from pathlib import Path
import traceback
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder

def test_cloud_sql_configuration():
    """Test Cloud SQL (Unix socket) configuration."""
    print("=" * 60)
    print("TESTING CLOUD SQL CONFIGURATION")
    print("=" * 60)
    
    # Mock staging environment variables
    env_vars = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "postgres", 
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "test_password_123"
    }
    
    builder = DatabaseURLBuilder(env_vars)
    
    # Test validation
    print("\n1. Validating configuration...")
    is_valid, error_msg = builder.validate()
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error_msg}")
        return False
    
    # Test Cloud SQL detection
    print("\n2. Testing Cloud SQL detection...")
    print(f"   Is Cloud SQL: {builder.cloud_sql.is_cloud_sql}")
    print(f"   Has TCP config: {builder.tcp.has_config}")
    
    # Test URL generation
    print("\n3. Testing URL generation...")
    async_url = builder.staging.auto_url
    sync_url = builder.staging.auto_sync_url
    print(f"   Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
    print(f"   Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
    
    # Test environment URL selection
    print("\n4. Testing environment-specific URL selection...")
    env_async = builder.get_url_for_environment(sync=False)
    env_sync = builder.get_url_for_environment(sync=True)
    print(f"   Environment async: {DatabaseURLBuilder.mask_url_for_logging(env_async)}")
    print(f"   Environment sync: {DatabaseURLBuilder.mask_url_for_logging(env_sync)}")
    
    # Test debug info
    print("\n5. Debug information...")
    debug_info = builder.debug_info()
    for key, value in debug_info.items():
        if key != 'available_urls':
            print(f"   {key}: {value}")
    print("   Available URLs:")
    for url_type, available in debug_info['available_urls'].items():
        print(f"     {url_type}: {available}")
    
    return True

def test_tcp_configuration():
    """Test TCP configuration (for development/testing)."""
    print("\n" + "=" * 60)
    print("TESTING TCP CONFIGURATION")
    print("=" * 60)
    
    # Mock development environment variables
    env_vars = {
        "ENVIRONMENT": "development",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "netra_dev", 
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres"
    }
    
    builder = DatabaseURLBuilder(env_vars)
    
    # Test validation
    print("\n1. Validating configuration...")
    is_valid, error_msg = builder.validate()
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error_msg}")
    
    # Test TCP detection
    print("\n2. Testing TCP detection...")
    print(f"   Is Cloud SQL: {builder.cloud_sql.is_cloud_sql}")
    print(f"   Has TCP config: {builder.tcp.has_config}")
    
    # Test URL generation
    print("\n3. Testing URL generation...")
    async_url = builder.tcp.async_url
    sync_url = builder.tcp.sync_url
    async_ssl_url = builder.tcp.async_url_with_ssl
    sync_ssl_url = builder.tcp.sync_url_with_ssl
    
    print(f"   TCP Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
    print(f"   TCP Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
    print(f"   TCP Async SSL URL: {DatabaseURLBuilder.mask_url_for_logging(async_ssl_url)}")
    print(f"   TCP Sync SSL URL: {DatabaseURLBuilder.mask_url_for_logging(sync_ssl_url)}")
    
    return True

def test_driver_url_formatting():
    """Test URL formatting for different database drivers."""
    print("\n" + "=" * 60)
    print("TESTING DRIVER URL FORMATTING")
    print("=" * 60)
    
    base_url = "postgresql://postgres:password@localhost:5432/testdb"
    
    print(f"\n1. Base URL: {base_url}")
    
    # Test different driver formats
    drivers = ['asyncpg', 'psycopg2', 'psycopg', 'base']
    for driver in drivers:
        formatted_url = DatabaseURLBuilder.format_url_for_driver(base_url, driver)
        masked_url = DatabaseURLBuilder.mask_url_for_logging(formatted_url)
        print(f"   {driver}: {masked_url}")
        
        # Test validation
        is_valid, error_msg = DatabaseURLBuilder.validate_url_for_driver(formatted_url, driver)
        print(f"     Valid: {is_valid}" + (f" - {error_msg}" if not is_valid else ""))
    
    return True

def test_ssl_parameter_handling():
    """Test SSL parameter handling for different scenarios."""
    print("\n" + "=" * 60)
    print("TESTING SSL PARAMETER HANDLING")
    print("=" * 60)
    
    # Test cases for SSL parameter handling
    test_cases = [
        {
            "description": "Cloud SQL URL with SSL (should remove SSL)",
            "url": "postgresql://user:pass@/db?host=/cloudsql/project:region:instance&sslmode=require"
        },
        {
            "description": "TCP URL with sslmode for asyncpg conversion",
            "url": "postgresql://user:pass@localhost:5432/db?sslmode=require"
        },
        {
            "description": "TCP URL with ssl for psycopg2 conversion", 
            "url": "postgresql://user:pass@localhost:5432/db?ssl=require"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        original_url = test_case['url']
        print(f"   Original: {DatabaseURLBuilder.mask_url_for_logging(original_url)}")
        
        # Test normalization
        normalized = DatabaseURLBuilder.normalize_postgres_url(original_url)
        print(f"   Normalized: {DatabaseURLBuilder.mask_url_for_logging(normalized)}")
        
        # Test formatting for different drivers
        for driver in ['asyncpg', 'psycopg2']:
            formatted = DatabaseURLBuilder.format_url_for_driver(normalized, driver)
            print(f"   For {driver}: {DatabaseURLBuilder.mask_url_for_logging(formatted)}")
    
    return True

def test_validation_edge_cases():
    """Test validation logic for various edge cases."""
    print("\n" + "=" * 60)
    print("TESTING VALIDATION EDGE CASES")
    print("=" * 60)
    
    # Test cases for validation
    test_cases = [
        {
            "description": "Missing required staging variables",
            "env_vars": {"ENVIRONMENT": "staging"},
            "should_be_valid": False
        },
        {
            "description": "Invalid Cloud SQL format",
            "env_vars": {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "/cloudsql/invalid-format",
                "POSTGRES_USER": "postgres",
                "POSTGRES_DB": "postgres",
                "POSTGRES_PASSWORD": "password"
            },
            "should_be_valid": False
        },
        {
            "description": "Valid Cloud SQL configuration",
            "env_vars": {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "/cloudsql/project:region:instance",
                "POSTGRES_USER": "postgres",
                "POSTGRES_DB": "postgres", 
                "POSTGRES_PASSWORD": "password"
            },
            "should_be_valid": True
        },
        {
            "description": "Localhost in staging (should fail)",
            "env_vars": {
                "ENVIRONMENT": "staging", 
                "POSTGRES_HOST": "localhost",
                "POSTGRES_USER": "postgres",
                "POSTGRES_DB": "postgres",
                "POSTGRES_PASSWORD": "password"
            },
            "should_be_valid": False
        },
        {
            "description": "Development password in staging (should fail)",
            "env_vars": {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "/cloudsql/project:region:instance",
                "POSTGRES_USER": "postgres",
                "POSTGRES_DB": "postgres",
                "POSTGRES_PASSWORD": "password"  # Too simple for staging
            },
            "should_be_valid": False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        builder = DatabaseURLBuilder(test_case['env_vars'])
        is_valid, error_msg = builder.validate()
        expected = test_case['should_be_valid']
        
        print(f"   Expected valid: {expected}")
        print(f"   Actually valid: {is_valid}")
        if not is_valid:
            print(f"   Error: {error_msg}")
        
        if is_valid != expected:
            print(f"   VALIDATION MISMATCH!")
            return False
        else:
            print(f"   Validation correct")
    
    return True

def test_connection_pooling_urls():
    """Test URL generation for connection pooling scenarios."""
    print("\n" + "=" * 60)
    print("TESTING CONNECTION POOLING URL SCENARIOS")
    print("=" * 60)
    
    # Test production-like environment
    production_env = {
        "ENVIRONMENT": "production",
        "POSTGRES_HOST": "/cloudsql/prod-project:us-central1:prod-instance",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "netra_production",
        "POSTGRES_USER": "netra_prod_user",
        "POSTGRES_PASSWORD": "complex_secure_password_123!@#"
    }
    
    builder = DatabaseURLBuilder(production_env)
    
    print("\n1. Production environment URLs...")
    print(f"   Environment: {builder.environment}")
    print(f"   Async URL: {DatabaseURLBuilder.mask_url_for_logging(builder.production.auto_url)}")
    print(f"   Sync URL: {DatabaseURLBuilder.mask_url_for_logging(builder.production.auto_sync_url)}")
    
    # Test different URL access patterns
    print("\n2. Different access patterns...")
    urls_to_test = [
        ("Direct Cloud SQL async", builder.cloud_sql.async_url),
        ("Direct Cloud SQL sync", builder.cloud_sql.sync_url),
        ("Environment auto async", builder.get_url_for_environment(sync=False)),
        ("Environment auto sync", builder.get_url_for_environment(sync=True))
    ]
    
    for description, url in urls_to_test:
        if url:
            masked = DatabaseURLBuilder.mask_url_for_logging(url)
            print(f"   {description}: {masked}")
            
            # Test URL normalization
            normalized = DatabaseURLBuilder.normalize_postgres_url(url)
            if normalized != url:
                print(f"     Normalized: {DatabaseURLBuilder.mask_url_for_logging(normalized)}")
        else:
            print(f"   {description}: NOT AVAILABLE")
    
    return True

def main():
    """Run all database URL builder tests."""
    print("DATABASE URL BUILDER COMPREHENSIVE TESTING")
    print("=" * 80)
    
    tests = [
        ("Cloud SQL Configuration", test_cloud_sql_configuration),
        ("TCP Configuration", test_tcp_configuration),
        ("Driver URL Formatting", test_driver_url_formatting),
        ("SSL Parameter Handling", test_ssl_parameter_handling),
        ("Validation Edge Cases", test_validation_edge_cases),
        ("Connection Pooling URLs", test_connection_pooling_urls)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result, None))
            status = "PASSED" if result else "FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n{test_name}: FAILED WITH EXCEPTION")
            print(f"Exception: {e}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status}: {test_name}")
        if error:
            print(f"    Error: {error}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    overall_success = failed == 0
    print(f"\nOverall Result: {'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)