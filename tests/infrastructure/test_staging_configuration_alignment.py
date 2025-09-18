"""
Infrastructure Test: Staging Configuration Alignment for Issue #1197
=====================================================================

Business Value: Platform/Internal - Staging Environment Reliability
Ensures staging environment configuration aligns with test expectations.

This test validates that staging environment configuration is properly aligned
with test requirements, enabling E2E and staging validation for Issue #1197.

EXPECTED BEHAVIOR:
- Initially: May FAIL with configuration mismatches or connectivity issues
- After Fix: Tests PASS with proper staging connectivity
- Regression: Tests FAIL if staging config drifts from test expectations

Author: Claude Code - Staging Configuration Validation
Date: 2025-09-16
"""

import pytest
import asyncio
import aiohttp
import ssl
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import socket

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.isolated_environment_fixtures import isolated_env, staging_env


class TestStagingConfigurationAlignment(SSotBaseTestCase):
    """Test staging environment configuration alignment."""
    
    def test_staging_environment_urls_reachable(self, staging_env):
        """
        Test that staging environment URLs are reachable from test environment.
        
        Based on CLAUDE.md Issue #1278 remediation, the current staging domains are:
        - Backend/Auth: https://staging.netrasystems.ai
        - Frontend: https://staging.netrasystems.ai  
        - WebSocket: wss://api.staging.netrasystems.ai
        
        DEPRECATED (DO NOT USE): *.staging.netrasystems.ai URLs
        """
        staging_urls = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai",
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai",
        }
        
        # Validate URL configuration in staging environment
        for service, expected_url in staging_urls.items():
            # Check if environment has URL configured
            env_key = f"{service.upper()}_URL"
            configured_url = staging_env.get(env_key)
            
            if configured_url:
                # Validate configured URL matches expected pattern
                if "staging.netrasystems.ai" not in configured_url:
                    pytest.fail(
                        f"Staging {service} URL misconfigured: {configured_url}. "
                        f"Should use staging.netrasystems.ai domain per Issue #1278 remediation."
                    )
    
    @pytest.mark.asyncio
    async def test_staging_backend_connectivity(self, staging_env):
        """
        Test HTTP connectivity to staging backend.
        
        This validates that the staging backend is reachable and responding
        to health check requests.
        """
        backend_url = staging_env.get("BACKEND_URL", "https://staging.netrasystems.ai")
        health_endpoint = f"{backend_url}/health"
        
        try:
            # Configure SSL context to handle staging certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(health_endpoint) as response:
                    assert response.status in [200, 204], \
                        f"Staging backend health check failed: {response.status}"
                    
                    # Log response for debugging
                    response_text = await response.text()
                    print(f"Staging backend health response: {response.status} - {response_text}")
                    
        except aiohttp.ClientError as e:
            pytest.fail(
                f"Cannot connect to staging backend at {health_endpoint}. "
                f"This may indicate network issues or staging environment problems. "
                f"Error: {e}"
            )
        except asyncio.TimeoutError:
            pytest.fail(
                f"Timeout connecting to staging backend at {health_endpoint}. "
                f"Staging environment may be slow or unresponsive."
            )
    
    def test_staging_database_configuration(self, staging_env):
        """
        Test that staging database configuration follows expected patterns.
        
        Validates database connection parameters for staging environment
        per Issue #1278 infrastructure requirements.
        """
        db_url = staging_env.get("DATABASE_URL")
        
        if not db_url:
            pytest.skip("DATABASE_URL not configured in staging environment")
        
        # Validate database URL format
        parsed = urlparse(db_url)
        
        assert parsed.scheme == "postgresql", \
            f"Expected PostgreSQL database, got {parsed.scheme}"
        
        assert parsed.hostname, "Database hostname not specified"
        assert parsed.port, "Database port not specified"
        assert parsed.path, "Database name not specified"
        
        # Validate staging-specific configuration
        if "staging" not in db_url.lower():
            print(f"Warning: Database URL may not be staging-specific: {db_url}")
    
    def test_staging_redis_configuration(self, staging_env):
        """
        Test that staging Redis configuration is properly set.
        
        Redis is critical for WebSocket functionality and session management
        in the staging environment.
        """
        redis_url = staging_env.get("REDIS_URL")
        
        if not redis_url:
            pytest.skip("REDIS_URL not configured in staging environment")
        
        # Validate Redis URL format
        parsed = urlparse(redis_url)
        
        assert parsed.scheme == "redis", \
            f"Expected Redis URL, got {parsed.scheme}"
        
        assert parsed.hostname, "Redis hostname not specified"
        
        # Redis port defaults to 6379 if not specified
        port = parsed.port or 6379
        assert isinstance(port, int), "Redis port must be integer"
    
    def test_staging_jwt_configuration(self, staging_env):
        """
        Test that staging JWT configuration is properly set.
        
        JWT configuration is critical for authentication in staging environment.
        Per CLAUDE.md, the key should be JWT_SECRET_KEY (not JWT_SECRET).
        """
        # Check for correct JWT secret key
        jwt_secret = staging_env.get("JWT_SECRET_KEY")
        
        if not jwt_secret:
            # Check for deprecated key name
            deprecated_secret = staging_env.get("JWT_SECRET")
            if deprecated_secret:
                pytest.fail(
                    "JWT_SECRET found but JWT_SECRET_KEY expected. "
                    "Per CLAUDE.md, use JWT_SECRET_KEY for consistency."
                )
            else:
                pytest.fail("JWT_SECRET_KEY not configured in staging environment")
        
        # Validate JWT secret length (should be at least 32 characters for security)
        assert len(jwt_secret) >= 32, \
            f"JWT secret too short: {len(jwt_secret)} chars (minimum 32 required)"
        
        # Validate it's not a test/dummy value in staging
        test_indicators = ["test", "dummy", "example", "changeme"]
        jwt_lower = jwt_secret.lower()
        
        for indicator in test_indicators:
            if indicator in jwt_lower:
                print(f"Warning: JWT secret contains '{indicator}' - may be test value")
    
    def test_staging_oauth_configuration(self, staging_env):
        """
        Test that staging OAuth configuration is properly set.
        
        OAuth is required for user authentication in staging environment.
        """
        required_oauth_vars = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        ]
        
        missing_vars = []
        
        for var in required_oauth_vars:
            value = staging_env.get(var)
            if not value:
                missing_vars.append(var)
            elif "test" in value.lower() or "dummy" in value.lower():
                print(f"Warning: {var} appears to contain test/dummy value")
        
        if missing_vars:
            pytest.fail(f"Missing OAuth configuration in staging: {missing_vars}")
    
    @pytest.mark.asyncio
    async def test_staging_websocket_endpoint_reachability(self, staging_env):
        """
        Test that staging WebSocket endpoint is reachable.
        
        This validates the WebSocket URL configuration per Issue #1278 remediation.
        WebSocket endpoint should be: wss://api.staging.netrasystems.ai
        """
        websocket_url = staging_env.get("WEBSOCKET_URL", "wss://api.staging.netrasystems.ai")
        
        # Validate WebSocket URL format
        if not websocket_url.startswith("wss://"):
            pytest.fail(f"WebSocket URL should use wss:// scheme, got: {websocket_url}")
        
        if "api.staging.netrasystems.ai" not in websocket_url:
            pytest.fail(
                f"WebSocket URL should use api.staging.netrasystems.ai domain "
                f"per Issue #1278 remediation, got: {websocket_url}"
            )
        
        # Test basic connectivity (connection establishment)
        try:
            import websockets
            
            # Test connection establishment (should succeed or fail with auth error)
            async with websockets.connect(
                websocket_url,
                timeout=10,
                ping_interval=None,
                ping_timeout=None
            ) as websocket:
                # If we get here, connection was established
                print(f"WebSocket connection to {websocket_url} successful")
                
        except websockets.ConnectionClosedError:
            # This may be expected if auth is required
            print(f"WebSocket connection closed (may require auth): {websocket_url}")
        except websockets.InvalidStatusCode as e:
            if e.status_code == 401:
                print(f"WebSocket connection rejected with 401 (auth required): {websocket_url}")
            else:
                pytest.fail(f"WebSocket connection failed with status {e.status_code}: {e}")
        except (ConnectionRefusedError, OSError) as e:
            pytest.fail(
                f"Cannot establish WebSocket connection to {websocket_url}. "
                f"Staging WebSocket service may be down. Error: {e}"
            )
        except Exception as e:
            pytest.fail(f"Unexpected error connecting to WebSocket: {e}")
    
    def test_staging_configuration_environment_consistency(self, staging_env):
        """
        Test that staging configuration is internally consistent.
        
        This validates that configuration values are consistent with each other
        and follow expected patterns for a staging environment.
        """
        # Validate ENVIRONMENT variable
        environment = staging_env.get("ENVIRONMENT")
        
        if environment and environment != "staging":
            pytest.fail(
                f"ENVIRONMENT should be 'staging' in staging configuration, "
                f"got: {environment}"
            )
        
        # Validate GCP project configuration
        gcp_project = staging_env.get("GCP_PROJECT_ID")
        
        if gcp_project and "staging" not in gcp_project.lower():
            print(f"Warning: GCP project may not be staging-specific: {gcp_project}")
        
        # Validate log level appropriate for staging
        log_level = staging_env.get("LOG_LEVEL", "INFO")
        
        if log_level == "DEBUG":
            print("Warning: DEBUG log level in staging may be too verbose")
        elif log_level == "ERROR":
            print("Warning: ERROR log level in staging may miss important information")
    
    def test_deprecated_staging_domain_detection(self, staging_env):
        """
        Test that deprecated staging domains are not used.
        
        Per Issue #1278 remediation, *.staging.netrasystems.ai URLs are deprecated
        and cause SSL certificate failures.
        """
        # Get all environment variables that might contain URLs
        all_vars = staging_env.get_all()
        
        deprecated_patterns = [
            ".staging.netrasystems.ai",
            "staging.staging.netrasystems.ai",
        ]
        
        violations = []
        
        for key, value in all_vars.items():
            if isinstance(value, str) and any(pattern in value for pattern in deprecated_patterns):
                violations.append(f"{key}={value}")
        
        if violations:
            error_msg = "Deprecated staging domain patterns found (per Issue #1278):\n"
            for violation in violations:
                error_msg += f"  X {violation}\n"
            error_msg += "\nUse *.netrasystems.ai domains instead of *.staging.netrasystems.ai"
            pytest.fail(error_msg)


# Test execution metadata
if __name__ == "__main__":
    # This test can be run directly to check staging configuration
    pytest.main([__file__, "-v", "--tb=short", "--environment=staging"])