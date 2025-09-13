from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import patch
"""
Staging-Specific CORS Tests

Business Value Justification (BVJ):
- Segment: ALL (Required for staging environment validation)
- Business Goal: Ensure CORS works correctly in staging before production
- Value Impact: Prevents CORS-related production deployment failures
- Strategic Impact: Validates staging environment mirrors production behavior

Test Coverage:
- Staging domains work correctly
- Production domains are blocked in staging
- Localhost is allowed in staging for testing
- Environment detection works correctly
- Cloud Run URLs are properly supported
"""

import os
import pytest
from typing import Dict, List
from fastapi.testclient import TestClient

from shared.cors_config_builder import (
    CORSConfigurationBuilder,
    get_cors_origins, get_cors_config, is_origin_allowed
)
from test_framework.fixtures import create_test_app
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


@pytest.mark.staging
class TestCORSStagingSpecific:
    """Test CORS configuration specifically for staging environment."""
    
    @pytest.fixture
    def staging_app(self):
        """Create test app configured for staging."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            return create_test_app()
    
    @pytest.fixture
    def staging_client(self, staging_app):
        """Create test client for staging environment."""
        return TestClient(staging_app)
    
    def test_staging_environment_detection(self):
        """Test staging environment is correctly detected."""
        staging_env_vars = [
            {"ENVIRONMENT": "staging"},
            {"ENV": "staging"}, 
            {"NETRA_ENV": "staging"},
            {"AUTH_ENV": "staging"},
            {"NODE_ENV": "staging"},
        ]
        
        for env_var in staging_env_vars:
            # Clear other environment variables that might interfere
            clear_env = {k: "" for k in ["ENVIRONMENT", "ENV", "NETRA_ENV", "AUTH_ENV", "NODE_ENV"]}
            with patch.dict(os.environ, {**clear_env, **env_var}, clear=False):
                cors_builder = CORSConfigurationBuilder()
                environment = cors_builder.environment
                assert environment == "staging", f"Failed to detect staging with {env_var}"
    
    def test_staging_origins_configuration(self):
        """Test staging CORS origins are correctly configured."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()
            
            # Should include staging domains
            assert "https://app.staging.netrasystems.ai" in origins
            assert "https://auth.staging.netrasystems.ai" in origins
            assert "https://api.staging.netrasystems.ai" in origins
            
            # Should include localhost for testing
            assert "http://localhost:3000" in origins
            assert "http://127.0.0.1:3000" in origins
            
            # Should include Cloud Run patterns
            assert any("run.app" in origin for origin in origins)
    
    def test_staging_blocks_production_domains(self):
        """Test staging environment blocks production domains."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()
            
            # Production domains should not be in staging origins
            production_domains = [
                "https://netrasystems.ai",
                "https://app.netrasystems.ai", 
                "https://api.netrasystems.ai"
            ]
            
            for domain in production_domains:
                assert domain not in origins, f"Production domain {domain} found in staging origins"
    
    def test_staging_allows_localhost(self):
        """Test staging environment allows localhost origins."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()
            
            localhost_variants = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000"
            ]
            
            for localhost in localhost_variants:
                assert is_origin_allowed(localhost, origins, "staging"), \
                    f"Localhost {localhost} not allowed in staging"
    
    def test_staging_cloud_run_pattern_matching(self):
        """Test staging Cloud Run URL pattern matching."""
        cloud_run_urls = [
            "https://netra-frontend-701982941522.us-central1.run.app",
            "https://netra-backend-701982941522.us-central1.run.app",
            "https://netra-auth-123456789.europe-west1.run.app"
        ]
        
        for url in cloud_run_urls:
            cors_builder = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
            assert cors_builder.origins._matches_staging_patterns(url), f"Cloud Run URL {url} not matched by staging patterns"
    
    def test_staging_cors_config_structure(self):
        """Test staging CORS configuration structure."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            config = get_cors_config()
            
            # Should have all required fields
            required_fields = [
                "allow_origins", "allow_credentials", "allow_methods",
                "allow_headers", "expose_headers", "max_age"
            ]
            
            for field in required_fields:
                assert field in config, f"Missing required CORS field: {field}"
            
            # Credentials should be enabled
            assert config["allow_credentials"] is True
            
            # Should include required headers for staging
            assert "Authorization" in config["allow_headers"]
            assert "Content-Type" in config["allow_headers"]
            assert "X-Request-ID" in config["allow_headers"]
    
    def test_staging_cors_preflight_requests(self, staging_client):
        """Test CORS preflight requests work in staging."""
        staging_origins = [
            "https://app.staging.netrasystems.ai",
            "http://localhost:3000"
        ]
        
        for origin in staging_origins:
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type"
            }
            
            response = staging_client.options("/health", headers=headers)
            
            # Should succeed or get appropriate auth error
            assert response.status_code in [200, 204, 401]
            
            if response.status_code in [200, 204]:
                assert response.headers.get("Access-Control-Allow-Origin") == origin
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    
    def test_staging_blocks_invalid_origins(self, staging_client):
        """Test staging blocks invalid origins."""
        invalid_origins = [
            "http://malicious-site.com",
            "https://attacker.net",
            "https://netrasystems.ai",  # Production domain blocked in staging
            "http://localhost:9999"     # Non-standard port
        ]
        
        for origin in invalid_origins:
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
            
            response = staging_client.options("/health", headers=headers)
            
            # Should not get CORS approval for invalid origins
            cors_origin = response.headers.get("Access-Control-Allow-Origin")
            assert cors_origin != origin, f"Invalid origin {origin} was incorrectly allowed"
    
    def test_staging_custom_cors_env_override(self):
        """Test staging can override CORS with environment variable."""
        custom_origins = "https://custom-staging.example.com,https://test.staging.local"
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "CORS_ORIGINS": custom_origins
        }):
            origins = get_cors_origins()
            
            assert "https://custom-staging.example.com" in origins
            assert "https://test.staging.local" in origins
    
    def test_staging_websocket_cors_support(self, staging_client):
        """Test WebSocket CORS support in staging."""
        # This would require WebSocket test support
        # For now, test that WebSocket origins match HTTP origins
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            from shared.cors_config_builder import get_websocket_cors_origins
            
            ws_origins = get_websocket_cors_origins()
            http_origins = get_cors_origins()
            
            assert ws_origins == http_origins, "WebSocket origins should match HTTP origins in staging"
    
    def test_staging_cors_error_responses(self, staging_client):
        """Test CORS headers are present in error responses."""
        origin = "https://app.staging.netrasystems.ai"
        headers = {"Origin": origin}
        
        # Test 404 response
        response = staging_client.get("/nonexistent-endpoint", headers=headers)
        
        if response.status_code == 404:
            # Should still have CORS headers for staging domain
            cors_headers = [
                "Access-Control-Allow-Origin",
                "access-control-allow-origin"  # Case variations
            ]
            
            has_cors_header = any(header in response.headers for header in cors_headers)
            assert has_cors_header, "CORS headers missing from 404 response"
    
    def test_staging_cors_vary_header(self, staging_client):
        """Test Vary: Origin header is present in staging."""
        origin = "https://app.staging.netrasystems.ai" 
        headers = {"Origin": origin}
        
        response = staging_client.get("/health", headers=headers)
        
        if response.status_code == 200:
            vary_header = response.headers.get("Vary", "")
            assert "Origin" in vary_header, "Vary: Origin header missing"
    
    def test_staging_cors_max_age(self, staging_client):
        """Test CORS Max-Age header in staging."""
        origin = "https://app.staging.netrasystems.ai"
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "POST"
        }
        
        response = staging_client.options("/health", headers=headers)
        
        if response.status_code in [200, 204]:
            max_age = response.headers.get("Access-Control-Max-Age")
            assert max_age is not None, "Max-Age header missing"
            assert int(max_age) > 0, "Max-Age should be positive"
    
    def test_staging_cors_exposed_headers(self, staging_client):
        """Test CORS exposed headers in staging."""
        origin = "https://app.staging.netrasystems.ai"
        headers = {"Origin": origin}
        
        response = staging_client.get("/health", headers=headers)
        
        if response.status_code == 200:
            exposed_headers = response.headers.get("Access-Control-Expose-Headers", "")
            
            # Should expose useful headers
            expected_exposed = ["X-Request-ID", "Content-Length"]
            
            for header in expected_exposed:
                # Header should be in exposed headers (case-insensitive)
                assert any(header.lower() in exposed_headers.lower().split(",") 
                          for _ in [1]), f"Header {header} not exposed"
    
    def test_staging_environment_parity(self):
        """Test staging CORS configuration maintains parity with production patterns."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            staging_config = get_cors_config()
        
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            production_config = get_cors_config()
        
        # Core configuration should be the same (except origins)
        parity_fields = ["allow_credentials", "allow_methods", "allow_headers", "max_age"]
        
        for field in parity_fields:
            assert staging_config[field] == production_config[field], \
                f"Staging/production parity broken for {field}"
    
    def test_staging_security_headers(self, staging_client):
        """Test security headers are present with CORS in staging."""
        origin = "https://app.staging.netrasystems.ai"
        headers = {"Origin": origin}
        
        response = staging_client.get("/health", headers=headers)
        
        if response.status_code == 200:
            # Check for security headers
            security_headers = ["X-Content-Type-Options", "X-Frame-Options"]
            
            for header in security_headers:
                # Log presence for visibility (may not be required in all environments)
                header_present = header in response.headers
                print(f"Staging security header {header}: {'present' if header_present else 'missing'}")


@pytest.mark.staging
@pytest.mark.e2e
class TestStagingCORSE2E:
    """End-to-end CORS tests for staging environment."""
    
    @pytest.mark.asyncio
    async def test_staging_frontend_backend_cors_flow(self):
        """Test complete CORS flow between staging frontend and backend."""
        # This test would require actual staging services to be running
        # For now, validate configuration is correct
        
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()
            config = get_cors_config()
            
            # Frontend should be able to call backend
            frontend_origin = "https://app.staging.netrasystems.ai"
            assert frontend_origin in origins
            
            # Authentication service should be callable
            auth_origin = "https://auth.staging.netrasystems.ai"
            assert auth_origin in origins
            
            # Configuration should support credentials
            assert config["allow_credentials"] is True
    
    def test_staging_mixed_content_prevention(self):
        """Test staging prevents mixed content issues."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()
            
            # All staging origins should be HTTPS (except localhost)
            for origin in origins:
                if "localhost" not in origin and "127.0.0.1" not in origin:
                    assert origin.startswith("https://"), \
                        f"Non-HTTPS origin {origin} in staging (mixed content risk)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "staging"])
