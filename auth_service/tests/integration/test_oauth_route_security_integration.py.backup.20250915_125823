"""
Test OAuth Route Security Integration - BATCH 4 Authentication Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure OAuth HTTP endpoints prevent authentication bypass attacks
- Value Impact: Users experience secure OAuth flows without security vulnerabilities
- Strategic Impact: OAuth route security critical for platform trust and enterprise compliance

Focus: OAuth endpoint security, route validation, callback handling, error responses
"""

import pytest
import json
import secrets
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from urllib.parse import urlencode, parse_qs

from auth_service.main import app
from auth_service.auth_core.oauth_manager import OAuthManager
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env


class TestOAuthRouteSecurityIntegration(BaseIntegrationTest):
    """Test OAuth route security integration and endpoint protection"""

    def setup_method(self):
        """Set up test environment"""
        self.client = TestClient(app)
        self.oauth_manager = OAuthManager()

    @pytest.mark.integration
    def test_oauth_login_endpoint_security(self):
        """Test OAuth login endpoint security and parameter validation"""
        # Test GET /auth/login with provider parameter
        
        # Valid provider request
        response = self.client.get("/auth/login?provider=google")
        
        # Should either redirect to OAuth (302) or return error (400/503)
        assert response.status_code in [302, 400, 503], f"Expected redirect or error, got {response.status_code}"
        
        if response.status_code == 302:
            # OAuth is configured - should redirect to Google
            redirect_location = response.headers.get("location", "")
            assert redirect_location.startswith("https://accounts.google.com/oauth2/auth")
            
            # Parse redirect URL parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(redirect_location)
            params = parse_qs(parsed.query)
            
            # Security validations
            assert "client_id" in params
            assert "redirect_uri" in params
            assert "response_type" in params
            assert "scope" in params
            assert "state" in params
            
            # State should be present for CSRF protection
            state_value = params["state"][0]
            assert len(state_value) >= 20  # Sufficient entropy
            
            # Response type should be 'code' (authorization code flow)
            assert params["response_type"][0] == "code"
            
            # Redirect URI should be legitimate
            redirect_uri = params["redirect_uri"][0]
            assert redirect_uri.startswith(("http://localhost:", "https://"))
            
        elif response.status_code == 503:
            # OAuth not configured - acceptable in test environment
            error_data = response.json()
            assert "detail" in error_data
            assert "not configured" in error_data["detail"].lower()
        
        # Test invalid provider
        invalid_response = self.client.get("/auth/login?provider=invalid-provider")
        assert invalid_response.status_code == 400
        invalid_data = invalid_response.json()
        assert "Unsupported OAuth provider" in invalid_data["detail"]
        
        # Test missing provider parameter
        missing_provider_response = self.client.get("/auth/login")
        assert missing_provider_response.status_code == 400
        missing_data = missing_provider_response.json()
        assert "Provider parameter is required" in missing_data["detail"]
        
        # Test XSS/injection attempts in provider parameter
        malicious_providers = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
        ]
        
        for malicious_provider in malicious_providers:
            malicious_response = self.client.get(f"/auth/login?provider={malicious_provider}")
            assert malicious_response.status_code == 400
            # Should not reflect malicious content in response
            response_text = malicious_response.text.lower()
            assert "<script>" not in response_text
            assert "drop table" not in response_text
            assert "javascript:" not in response_text

    @pytest.mark.integration
    def test_oauth_callback_endpoint_security(self):
        """Test OAuth callback endpoint security and parameter validation"""
        # Test valid callback parameters
        valid_code = "valid-auth-code-12345"
        valid_state = secrets.token_urlsafe(32)
        
        callback_response = self.client.get(f"/auth/callback?code={valid_code}&state={valid_state}")
        
        # Should either redirect (302) or return error (400/500)
        assert callback_response.status_code in [302, 400, 401, 500, 503]
        
        if callback_response.status_code == 302:
            # Successfully processed OAuth callback
            redirect_location = callback_response.headers.get("location", "")
            
            # Should redirect to frontend
            frontend_urls = [
                "http://localhost:3000",
                "https://app.netrasystems.ai",
                "https://app.staging.netrasystems.ai"
            ]
            
            redirect_valid = any(redirect_location.startswith(url) for url in frontend_urls)
            assert redirect_valid, f"Invalid redirect URL: {redirect_location}"
            
            # Should include auth parameters or error info
            assert "?" in redirect_location  # Should have query parameters
        
        # Test missing required parameters
        missing_code_response = self.client.get(f"/auth/callback?state={valid_state}")
        assert missing_code_response.status_code == 400
        missing_code_data = missing_code_response.json()
        assert "Missing authorization code" in missing_code_data["detail"]
        
        missing_state_response = self.client.get(f"/auth/callback?code={valid_code}")
        assert missing_state_response.status_code == 400
        missing_state_data = missing_state_response.json()
        assert "Missing authorization code or state" in missing_state_data["detail"]
        
        # Test OAuth error handling
        error_response = self.client.get("/auth/callback?error=access_denied&error_description=User%20denied%20access")
        assert error_response.status_code == 302  # Should redirect to frontend with error
        
        error_redirect = error_response.headers.get("location", "")
        assert "/auth/error?" in error_redirect
        assert "error=access_denied" in error_redirect
        
        # Test injection attacks in callback parameters
        injection_attacks = [
            ("code", "'; DROP TABLE oauth_codes; --"),
            ("state", "<script>alert('xss')</script>"),
            ("error", "javascript:alert('xss')"),
            ("error_description", "<img src=x onerror=alert('xss')>"),
        ]
        
        for param_name, malicious_value in injection_attacks:
            malicious_params = {"code": valid_code, "state": valid_state}
            malicious_params[param_name] = malicious_value
            
            param_string = urlencode(malicious_params)
            injection_response = self.client.get(f"/auth/callback?{param_string}")
            
            # Should handle malicious input safely
            assert injection_response.status_code in [302, 400, 401, 500]
            
            # Response should not reflect malicious content
            response_text = injection_response.text.lower()
            assert "<script>" not in response_text
            assert "drop table" not in response_text
            assert "javascript:" not in response_text
            assert "onerror=" not in response_text

    @pytest.mark.integration
    def test_oauth_providers_endpoint_security(self):
        """Test OAuth providers endpoint security and information disclosure"""
        # Test providers endpoint
        providers_response = self.client.get("/oauth/providers")
        assert providers_response.status_code == 200
        
        providers_data = providers_response.json()
        assert isinstance(providers_data, dict)
        assert "providers" in providers_data
        assert "status" in providers_data
        assert "provider_details" in providers_data
        
        # Validate provider information doesn't leak secrets
        provider_details = providers_data["provider_details"]
        
        for provider_name, details in provider_details.items():
            assert isinstance(details, dict)
            
            # Should not contain sensitive information
            for key, value in details.items():
                if isinstance(value, str):
                    # Check for secret leakage
                    assert "client_secret" not in value
                    assert not (key.lower() == "client_secret" and len(value) > 10)
                    assert not (len(value) > 50 and value.count('.') >= 2)  # Not a JWT token
            
            # Configuration status should be safe
            if "config_status" in details:
                config_status = details["config_status"]
                if isinstance(config_status, dict):
                    for config_key, config_value in config_status.items():
                        if isinstance(config_value, str) and len(config_value) > 20:
                            # Long strings might be secrets - should be masked
                            if "secret" in config_key.lower():
                                assert "***" in config_value or config_value == "hidden" or len(config_value) <= 20
        
        # Test that available providers are reasonable
        providers_list = providers_data["providers"]
        assert isinstance(providers_list, list)
        
        # Should include Google
        assert "google" in providers_list
        
        # Should not include obviously invalid providers
        invalid_providers = ["', DROP TABLE users; --", "<script>", "../../../../etc/passwd"]
        for invalid in invalid_providers:
            assert invalid not in providers_list

    @pytest.mark.integration
    def test_oauth_config_endpoint_security(self):
        """Test OAuth configuration endpoint security and environment handling"""
        # Test auth config endpoint
        config_response = self.client.get("/auth/config")
        assert config_response.status_code == 200
        
        config_data = config_response.json()
        assert isinstance(config_data, dict)
        
        # Required configuration fields
        required_fields = ["oauth_enabled", "development_mode", "endpoints"]
        for field in required_fields:
            assert field in config_data
        
        # OAuth configuration security
        if "google_client_id" in config_data:
            client_id = config_data["google_client_id"]
            if client_id:  # If present, validate format
                assert isinstance(client_id, str)
                assert len(client_id) > 10
                # Should not be a secret or token
                assert not client_id.startswith("ghs_")  # GitHub token
                assert not client_id.startswith("sk-")   # OpenAI token
        
        # Endpoint configuration security
        endpoints = config_data["endpoints"]
        assert isinstance(endpoints, dict)
        
        for endpoint_name, endpoint_url in endpoints.items():
            if endpoint_url:  # Skip None values
                assert isinstance(endpoint_url, str)
                assert endpoint_url.startswith(("http://", "https://"))
                
                # Development endpoints may use localhost
                if "localhost" in endpoint_url:
                    env = get_env().get("ENVIRONMENT", "development")
                    assert env.lower() in ["development", "test"], f"Localhost should only be used in dev/test, not {env}"
                
                # Production endpoints should use HTTPS
                if "netrasystems.ai" in endpoint_url:
                    assert endpoint_url.startswith("https://"), f"Production URLs should use HTTPS: {endpoint_url}"
        
        # OAuth redirect URI configuration
        if "oauth_redirect_uri" in config_data:
            oauth_redirect = config_data["oauth_redirect_uri"]
            assert isinstance(oauth_redirect, str)
            assert oauth_redirect.startswith(("http://", "https://"))
        
        # Development mode should be boolean
        dev_mode = config_data["development_mode"]
        assert isinstance(dev_mode, bool)
        
        # OAuth enabled should be boolean
        oauth_enabled = config_data["oauth_enabled"]
        assert isinstance(oauth_enabled, bool)

    @pytest.mark.integration
    def test_oauth_route_rate_limiting_security(self):
        """Test OAuth route rate limiting and abuse prevention"""
        # Test rapid requests to OAuth login endpoint
        rapid_responses = []
        
        for i in range(20):  # Make 20 rapid requests
            response = self.client.get("/auth/login?provider=google")
            rapid_responses.append(response.status_code)
        
        # All should get some response (no crashes)
        assert all(status in [302, 400, 503, 429] for status in rapid_responses)
        
        # If rate limiting is implemented, some should be 429 (Too Many Requests)
        rate_limited_count = sum(1 for status in rapid_responses if status == 429)
        
        # Either no rate limiting (all same status) or some rate limiting (some 429s)
        if rate_limited_count > 0:
            assert rate_limited_count < len(rapid_responses)  # Not all should be rate limited
        
        # Test rapid requests to callback endpoint (more likely to be rate limited)
        callback_responses = []
        test_code = "test-code-12345"
        test_state = secrets.token_urlsafe(32)
        
        for i in range(10):  # Make 10 rapid callback requests
            response = self.client.get(f"/auth/callback?code={test_code}-{i}&state={test_state}")
            callback_responses.append(response.status_code)
        
        # All should get some response
        assert all(status in [302, 400, 401, 429, 500, 503] for status in callback_responses)
        
        # Test rapid requests to providers endpoint (should be less restricted)
        provider_responses = []
        
        for i in range(15):
            response = self.client.get("/oauth/providers")
            provider_responses.append(response.status_code)
        
        # Providers endpoint should generally allow rapid requests (read-only)
        success_count = sum(1 for status in provider_responses if status == 200)
        assert success_count >= len(provider_responses) * 0.8  # At least 80% should succeed

    @pytest.mark.integration
    def test_oauth_route_cors_security(self):
        """Test OAuth route CORS security and origin validation"""
        # Test CORS preflight for OAuth endpoints
        cors_origins = [
            "http://localhost:3000",  # Development
            "https://app.netrasystems.ai",  # Production
            "https://app.staging.netrasystems.ai",  # Staging
            "https://evil.com",  # Malicious
            "http://evil.com:3000",  # Malicious with port
        ]
        
        for origin in cors_origins:
            # Test CORS preflight request
            preflight_response = self.client.options(
                "/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            # Should get some response
            assert preflight_response.status_code in [200, 204, 404, 405]
            
            # Check CORS headers if present
            cors_origin = preflight_response.headers.get("Access-Control-Allow-Origin")
            
            if cors_origin:
                # Should not allow malicious origins
                if "evil.com" in origin:
                    assert cors_origin != origin, f"Should not allow malicious origin: {origin}"
                
                # Should allow legitimate origins
                if "localhost" in origin or "netrasystems.ai" in origin:
                    # May or may not allow based on CORS configuration
                    pass  # Both allowing and denying are valid security choices
        
        # Test actual requests with different origins
        for origin in cors_origins[:3]:  # Test legitimate origins only
            response = self.client.get(
                "/auth/config",
                headers={"Origin": origin}
            )
            
            assert response.status_code == 200
            
            # Check if CORS headers are set appropriately
            cors_origin = response.headers.get("Access-Control-Allow-Origin")
            if cors_origin:
                # Should be either the requested origin (if allowed) or "*" or not set
                assert cors_origin in [origin, "*"] or cors_origin.startswith("http")

    @pytest.mark.e2e
    def test_complete_oauth_route_security_flow(self):
        """E2E test of complete OAuth route security flow"""
        # Test complete OAuth route security: Config -> Login -> Callback -> Validation
        
        # 1. Configuration Endpoint Security
        config_response = self.client.get("/auth/config")
        assert config_response.status_code == 200
        config_data = config_response.json()
        
        # Validate configuration security
        assert "google_client_id" in config_data
        assert "oauth_enabled" in config_data
        assert "endpoints" in config_data
        
        oauth_enabled = config_data["oauth_enabled"]
        endpoints = config_data["endpoints"]
        
        # 2. Providers Endpoint Security
        providers_response = self.client.get("/oauth/providers")
        assert providers_response.status_code == 200
        providers_data = providers_response.json()
        
        assert "google" in providers_data["providers"]
        
        # Validate no secrets leaked
        for provider, details in providers_data["provider_details"].items():
            if isinstance(details, dict):
                for key, value in details.items():
                    if isinstance(value, str) and len(value) > 20:
                        if "secret" in key.lower():
                            assert "***" in value or value == "hidden" or len(value) <= 20
        
        # 3. Login Endpoint Security Flow
        if oauth_enabled:
            # Test OAuth login initiation
            login_response = self.client.get("/auth/login?provider=google")
            
            if login_response.status_code == 302:
                # OAuth is configured and working
                redirect_url = login_response.headers.get("location", "")
                assert redirect_url.startswith("https://accounts.google.com/oauth2/auth")
                
                # Parse state parameter for callback testing
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                oauth_state = params.get("state", [""])[0]
                
                # 4. Callback Endpoint Security Flow
                if oauth_state:
                    # Test valid callback format
                    test_code = "test-authorization-code-12345"
                    callback_response = self.client.get(f"/auth/callback?code={test_code}&state={oauth_state}")
                    
                    # Should handle callback (may fail at token exchange, but route should work)
                    assert callback_response.status_code in [302, 401, 500]
                    
                    if callback_response.status_code == 302:
                        # Successful callback processing
                        callback_redirect = callback_response.headers.get("location", "")
                        assert callback_redirect.startswith(("http://localhost:3000", "https://app."))
                    
                    # Test callback error handling
                    error_callback_response = self.client.get(
                        "/auth/callback?error=access_denied&error_description=User%20denied%20access&state=" + oauth_state
                    )
                    assert error_callback_response.status_code == 302
                    
                    error_redirect = error_callback_response.headers.get("location", "")
                    assert "/auth/error?" in error_redirect
                    assert "error=access_denied" in error_redirect
            
            elif login_response.status_code == 503:
                # OAuth not configured - test error handling
                error_data = login_response.json()
                assert "not configured" in error_data["detail"].lower()
        
        # 5. Security Attack Prevention Testing
        # Test various injection attacks across all endpoints
        injection_payloads = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "%00malicious",
            "\x00malicious"
        ]
        
        security_test_endpoints = [
            "/auth/login?provider={}",
            "/auth/callback?code={}&state=valid",
            "/auth/callback?code=valid&state={}",
        ]
        
        for endpoint_template in security_test_endpoints:
            for payload in injection_payloads:
                malicious_endpoint = endpoint_template.format(payload)
                
                security_response = self.client.get(malicious_endpoint)
                
                # Should not crash (return valid HTTP status)
                assert 200 <= security_response.status_code < 600
                
                # Should not reflect malicious content
                response_text = security_response.text.lower()
                assert "<script>" not in response_text
                assert "drop table" not in response_text
                assert "javascript:" not in response_text
                assert "../../../" not in response_text
        
        # 6. Rate Limiting and Performance Security
        # Test rapid successive requests don't cause issues
        performance_endpoints = [
            "/auth/config",
            "/oauth/providers",
            "/auth/login?provider=google",
        ]
        
        for endpoint in performance_endpoints:
            start_time = time.time()
            responses = []
            
            for _ in range(50):
                response = self.client.get(endpoint)
                responses.append(response.status_code)
            
            end_time = time.time()
            
            # Should handle load without crashes
            assert all(200 <= status < 600 for status in responses)
            
            # Should respond reasonably quickly (under 5 seconds for 50 requests)
            assert end_time - start_time < 5.0
            
            # Should not all be errors (some should succeed)
            success_count = sum(1 for status in responses if status < 400)
            assert success_count >= len(responses) * 0.5  # At least 50% should succeed
        
        # 7. Information Disclosure Prevention
        # Test that error responses don't leak sensitive information
        error_test_requests = [
            ("/auth/login?provider=nonexistent", "provider"),
            ("/auth/callback", "parameters"),  
            ("/auth/callback?code=invalid", "state"),
            ("/oauth/providers", None),  # Should not error
        ]
        
        for endpoint, expected_error_type in error_test_requests:
            error_response = self.client.get(endpoint)
            
            if expected_error_type:  # Expecting an error
                assert error_response.status_code >= 400
                
                if error_response.headers.get("content-type", "").startswith("application/json"):
                    error_data = error_response.json()
                    if "detail" in error_data:
                        error_message = error_data["detail"]
                        
                        # Should not leak sensitive information
                        sensitive_terms = ["client_secret", "jwt_secret", "database", "password"]
                        for term in sensitive_terms:
                            assert term not in error_message.lower()
                        
                        # Should provide helpful but safe error information
                        assert len(error_message) > 5  # Should have some content
                        assert len(error_message) < 200  # Should not be overly verbose
            
            else:  # Should not error
                assert error_response.status_code < 400
        
        import time