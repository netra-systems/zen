from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Network Constants Validation Script

Validates the new centralized network configuration module.
Business Value: Platform/Internal - Configuration Validation - Ensures consistent network
configuration across all environments and services.

Usage:
    python scripts/validate_network_constants.py
    python scripts/validate_network_constants.py --environment production
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path

try:
    from netra_backend.app.core.network_constants import (
        DatabaseConstants,
        HostConstants,
        NetworkEnvironmentHelper,
        ServiceEndpoints,
        ServicePorts,
        URLConstants,
    )
    print("[OK] Successfully imported network constants module")
except ImportError as e:
    print(f"[ERROR] Failed to import network constants module: {e}")
    sys.exit(1)


def validate_service_ports():
    """Validate service ports are correctly defined."""
    print("\n[PORTS] Validating Service Ports...")
    
    # Check default ports
    assert ServicePorts.POSTGRES_DEFAULT == 5432, "PostgreSQL default port should be 5432"
    assert ServicePorts.REDIS_DEFAULT == 6379, "Redis default port should be 6379"
    assert ServicePorts.CLICKHOUSE_HTTP == 8123, "ClickHouse HTTP port should be 8123"
    assert ServicePorts.CLICKHOUSE_NATIVE == 9000, "ClickHouse native port should be 9000"
    assert ServicePorts.BACKEND_DEFAULT == 8000, "Backend default port should be 8000"
    assert ServicePorts.FRONTEND_DEFAULT == 3000, "Frontend default port should be 3000"
    
    # Test port methods
    postgres_port = ServicePorts.get_postgres_port(is_test=True)
    assert postgres_port == 5433, f"Test PostgreSQL port should be 5433, got {postgres_port}"
    
    redis_port = ServicePorts.get_redis_port(is_test=False)
    assert redis_port == 6379, f"Production Redis port should be 6379, got {redis_port}"
    
    print("[OK] Service ports validation passed")


def validate_host_constants():
    """Validate host constants are correctly defined."""
    print("\n[HOSTS] Validating Host Constants...")
    
    assert HostConstants.LOCALHOST == "localhost", "Localhost should be 'localhost'"
    assert HostConstants.LOCALHOST_IP == "127.0.0.1", "Localhost IP should be '127.0.0.1'"
    assert HostConstants.ANY_HOST == "0.0.0.0", "Any host should be '0.0.0.0'"
    
    # Test helper method
    default_host = HostConstants.get_default_host(use_localhost_ip=True)
    assert default_host == "127.0.0.1", f"Default host with IP should be '127.0.0.1', got {default_host}"
    
    print("[OK] Host constants validation passed")


def validate_database_constants():
    """Validate database constants and URL builders."""
    print("\n[DATABASE] Validating Database Constants...")
    
    # Test PostgreSQL URL builder
    pg_url = DatabaseConstants.build_postgres_url(
        user="test_user",
        password="test_pass", 
        host="localhost",
        port=5432,
        database="test_db",
        async_driver=True
    )
    expected_pg_url = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
    assert pg_url == expected_pg_url, f"PostgreSQL URL mismatch: {pg_url} != {expected_pg_url}"
    
    # Test Redis URL builder
    redis_url = DatabaseConstants.build_redis_url(
        host="localhost",
        port=6379,
        database=1
    )
    expected_redis_url = "redis://localhost:6379/1"
    assert redis_url == expected_redis_url, f"Redis URL mismatch: {redis_url} != {expected_redis_url}"
    
    # Test ClickHouse URL builder
    ch_url = DatabaseConstants.build_clickhouse_url(
        host="localhost",
        port=9000,
        database="default"
    )
    expected_ch_url = "clickhouse://default@localhost:9000/default"
    assert ch_url == expected_ch_url, f"ClickHouse URL mismatch: {ch_url} != {expected_ch_url}"
    
    print("[OK] Database constants validation passed")


def validate_url_constants():
    """Validate URL constants and builders."""
    print("\n[URLS] Validating URL Constants...")
    
    # Test HTTP URL builder
    http_url = URLConstants.build_http_url(
        host="localhost",
        port=8000,
        path="/api/health",
        secure=False
    )
    expected_http_url = "http://localhost:8000/api/health"
    assert http_url == expected_http_url, f"HTTP URL mismatch: {http_url} != {expected_http_url}"
    
    # Test WebSocket URL builder
    ws_url = URLConstants.build_websocket_url(
        host="localhost",
        port=8000,
        path="/ws",
        secure=False
    )
    expected_ws_url = "ws://localhost:8000/ws"
    assert ws_url == expected_ws_url, f"WebSocket URL mismatch: {ws_url} != {expected_ws_url}"
    
    # Test CORS origins
    dev_origins = URLConstants.get_cors_origins("development")
    assert len(dev_origins) >= 2, "Development CORS origins should have at least 2 entries"
    assert any("localhost:3000" in origin for origin in dev_origins), "Development CORS should include frontend"
    
    print("[OK] URL constants validation passed")


def validate_service_endpoints():
    """Validate service endpoint builders."""
    print("\n[ENDPOINTS] Validating Service Endpoints...")
    
    # Test auth service URL builder
    auth_url = ServiceEndpoints.build_auth_service_url(
        host="localhost",
        port=8081
    )
    expected_auth_url = "http://localhost:8081"
    assert auth_url == expected_auth_url, f"Auth service URL mismatch: {auth_url} != {expected_auth_url}"
    
    # Test Google OAuth endpoints
    assert ServiceEndpoints.GOOGLE_TOKEN_URI.startswith("https://oauth2.googleapis.com"), "Google token URI should be valid"
    assert ServiceEndpoints.GOOGLE_AUTH_URI.startswith("https://accounts.google.com"), "Google auth URI should be valid"
    
    print("[OK] Service endpoints validation passed")


def validate_network_environment_helper(environment: str = "development"):
    """Validate network environment helper functionality."""
    print(f"\n[ENVIRONMENT] Validating Network Environment Helper (env: {environment})...")
    
    # Set temporary environment for testing
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = environment
    
    try:
        # Test environment detection
        detected_env = NetworkEnvironmentHelper.get_environment()
        assert detected_env == environment, f"Environment detection failed: {detected_env} != {environment}"
        
        # Test database URLs generation
        db_urls = NetworkEnvironmentHelper.get_database_urls_for_environment()
        assert "postgres" in db_urls, "Database URLs should include postgres"
        assert "redis" in db_urls, "Database URLs should include redis"
        assert "clickhouse" in db_urls, "Database URLs should include clickhouse"
        
        # Test service URLs generation
        service_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
        assert "frontend" in service_urls, "Service URLs should include frontend"
        assert "backend" in service_urls, "Service URLs should include backend"
        assert "auth_service" in service_urls, "Service URLs should include auth_service"
        
        # Validate URL formats based on environment
        if environment == "development":
            assert "localhost" in service_urls["frontend"], "Dev frontend should use localhost"
            assert "localhost" in service_urls["backend"], "Dev backend should use localhost"
        elif environment in ["staging", "production"]:
            assert "https://" in service_urls["frontend"], f"{environment} frontend should use HTTPS"
        
        print(f"[OK] Network environment helper validation passed for {environment}")
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        elif "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate network constants module")
    parser.add_argument(
        "--environment", 
        default="development",
        choices=["development", "staging", "production", "testing"],
        help="Environment to validate (default: development)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print("[TEST] Network Constants Validation Suite")
    print("=" * 50)
    
    try:
        validate_service_ports()
        validate_host_constants()
        validate_database_constants()
        validate_url_constants()
        validate_service_endpoints()
        validate_network_environment_helper(args.environment)
        
        print("\n" + "=" * 50)
        print("[SUCCESS] All validations passed successfully!")
        print(f"[OK] Network constants module is working correctly for {args.environment} environment")
        
        if args.verbose:
            print("\n[SUMMARY] Summary of validated components:")
            print("  [U+2022] Service ports and port selection logic")
            print("  [U+2022] Host constants and helpers")
            print("  [U+2022] Database URL builders (PostgreSQL, Redis, ClickHouse)")
            print("  [U+2022] HTTP and WebSocket URL builders")
            print("  [U+2022] Service endpoint configurations")
            print("  [U+2022] Environment-based configuration logic")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
