"""Test SSL certificate handling for staging database connections."""

import sys
from pathlib import Path
import ssl
import socket
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder
from google.cloud import secretmanager

def fetch_secret(secret_id: str, project: str = "netra-staging") -> str:
    """Fetch a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project}/secrets/{secret_id}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error fetching secret {secret_id}: {e}")
        raise

def test_ssl_certificate_validation():
    """Test SSL certificate validation for staging database."""
    print("=" * 60)
    print("TESTING SSL CERTIFICATE VALIDATION")
    print("=" * 60)
    
    try:
        # Get staging database configuration
        print("\n1. Fetching staging database configuration...")
        host = fetch_secret("postgres-host-staging")
        port = fetch_secret("postgres-port-staging")
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        
        # Check if this is a Cloud SQL Unix socket (SSL not applicable)
        if "/cloudsql/" in host:
            print("   Connection type: Cloud SQL Unix Socket")
            print("   SSL validation: Not applicable (Unix socket handles encryption)")
            return True
        
        # For TCP connections, test SSL certificate validation
        print("   Connection type: TCP")
        
        # Parse host and port
        if ":" in host:
            host_parts = host.split(":")
            hostname = host_parts[0]
            port_num = int(host_parts[1]) if len(host_parts) > 1 else int(port)
        else:
            hostname = host
            port_num = int(port)
        
        print(f"   Hostname: {hostname}")
        print(f"   Port: {port_num}")
        
        # Test SSL connection
        print("\n2. Testing SSL connection...")
        
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        try:
            with socket.create_connection((hostname, port_num), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    print("   SSL connection: SUCCESS")
                    
                    # Get certificate info
                    cert = ssock.getpeercert()
                    print(f"   Certificate subject: {cert.get('subject', 'N/A')}")
                    print(f"   Certificate issuer: {cert.get('issuer', 'N/A')}")
                    print(f"   Certificate version: {cert.get('version', 'N/A')}")
                    
                    # Check certificate validity
                    not_after = cert.get('notAfter')
                    if not_after:
                        print(f"   Certificate expires: {not_after}")
                    
                    return True
        except ssl.SSLError as e:
            print(f"   SSL connection FAILED: {e}")
            return False
        except socket.error as e:
            print(f"   Network connection FAILED: {e}")
            return False
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ssl_parameter_handling():
    """Test SSL parameter handling in database URLs."""
    print("\n" + "=" * 60)
    print("TESTING SSL PARAMETER HANDLING IN URLs")
    print("=" * 60)
    
    # Test cases for SSL parameter handling
    test_cases = [
        {
            "description": "Cloud SQL URL (should remove SSL parameters)",
            "host": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
            "should_have_ssl": False
        },
        {
            "description": "TCP staging URL (should have SSL parameters)",
            "host": "127.0.0.1",  # Mock TCP host
            "should_have_ssl": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        
        # Build environment configuration
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": test_case['host'],
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "postgres",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "complex_staging_password_123!"
        }
        
        builder = DatabaseURLBuilder(env_vars)
        
        # Get URLs
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        print(f"   Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
        print(f"   Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
        
        # Check SSL parameters
        has_ssl_async = "ssl" in async_url.lower() if async_url else False
        has_ssl_sync = "ssl" in sync_url.lower() if sync_url else False
        
        print(f"   Async URL has SSL: {has_ssl_async}")
        print(f"   Sync URL has SSL: {has_ssl_sync}")
        print(f"   Expected SSL: {test_case['should_have_ssl']}")
        
        if test_case['should_have_ssl']:
            if not (has_ssl_async or has_ssl_sync):
                print("   ERROR: Expected SSL parameters but none found!")
                return False
            print("   SSL parameters present as expected")
        else:
            if has_ssl_async or has_ssl_sync:
                print("   ERROR: Found SSL parameters but none expected!")
                return False
            print("   No SSL parameters as expected")
    
    return True

def test_url_driver_compatibility():
    """Test URL compatibility with different database drivers for SSL."""
    print("\n" + "=" * 60)
    print("TESTING URL DRIVER COMPATIBILITY FOR SSL")
    print("=" * 60)
    
    base_urls = [
        "postgresql://user:pass@localhost:5432/db?sslmode=require",
        "postgresql://user:pass@localhost:5432/db?ssl=require",
        "postgresql://user:pass@/db?host=/cloudsql/project:region:instance&sslmode=require"
    ]
    
    drivers = ['asyncpg', 'psycopg2', 'psycopg', 'base']
    
    for i, base_url in enumerate(base_urls, 1):
        print(f"\n{i}. Testing URL: {DatabaseURLBuilder.mask_url_for_logging(base_url)}")
        
        for driver in drivers:
            # Format URL for driver
            formatted_url = DatabaseURLBuilder.format_url_for_driver(base_url, driver)
            masked_url = DatabaseURLBuilder.mask_url_for_logging(formatted_url)
            
            print(f"   {driver:10}: {masked_url}")
            
            # Validate URL for driver
            is_valid, error_msg = DatabaseURLBuilder.validate_url_for_driver(formatted_url, driver)
            if not is_valid:
                print(f"            VALIDATION ERROR: {error_msg}")
                return False
            else:
                print(f"            Valid")
    
    return True

def test_staging_ssl_configuration():
    """Test staging SSL configuration with real secrets."""
    print("\n" + "=" * 60)
    print("TESTING STAGING SSL CONFIGURATION WITH REAL SECRETS")
    print("=" * 60)
    
    try:
        # Fetch real staging configuration
        print("\n1. Fetching staging database secrets...")
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": fetch_secret("postgres-host-staging"),
            "POSTGRES_PORT": fetch_secret("postgres-port-staging"),
            "POSTGRES_DB": fetch_secret("postgres-db-staging"),
            "POSTGRES_USER": fetch_secret("postgres-user-staging"),
            "POSTGRES_PASSWORD": fetch_secret("postgres-password-staging")
        }
        
        print(f"   Host: {env_vars['POSTGRES_HOST']}")
        print(f"   Port: {env_vars['POSTGRES_PORT']}")
        print(f"   Database: {env_vars['POSTGRES_DB']}")
        print(f"   User: {env_vars['POSTGRES_USER']}")
        
        # Build URLs using DatabaseURLBuilder
        print("\n2. Building database URLs...")
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        print(f"   Configuration valid: {is_valid}")
        if not is_valid:
            print(f"   Error: {error_msg}")
            return False
        
        # Get URLs
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        print(f"   Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
        print(f"   Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
        
        # Test URL normalization
        print("\n3. Testing URL normalization...")
        if async_url:
            normalized_async = DatabaseURLBuilder.normalize_postgres_url(async_url)
            print(f"   Normalized async: {DatabaseURLBuilder.mask_url_for_logging(normalized_async)}")
            
            # Format for different drivers
            for driver in ['asyncpg', 'psycopg2']:
                formatted = DatabaseURLBuilder.format_url_for_driver(normalized_async, driver)
                print(f"   For {driver}: {DatabaseURLBuilder.mask_url_for_logging(formatted)}")
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all SSL certificate and configuration tests."""
    print("DATABASE SSL CERTIFICATE AND CONFIGURATION TESTING")
    print("=" * 80)
    
    tests = [
        ("SSL Certificate Validation", test_ssl_certificate_validation),
        ("SSL Parameter Handling", test_ssl_parameter_handling),
        ("URL Driver Compatibility", test_url_driver_compatibility),
        ("Staging SSL Configuration", test_staging_ssl_configuration)
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
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("SSL TEST SUMMARY")
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