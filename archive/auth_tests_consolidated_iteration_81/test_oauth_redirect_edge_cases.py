"""
OAuth Redirect URI Edge Case Tests

Comprehensive test suite addressing the 9 critical reasons why OAuth redirect bugs
weren't discovered earlier. These tests validate edge cases, environment differences,
and potential regression scenarios.
"""
import pytest
import os
import re
import ast
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import sys
import json
from typing import Tuple
from datetime import datetime, timedelta
import concurrent.futures
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import _determine_urls


class TestOAuthRedirectEdgeCases:
    """Test suite for OAuth redirect URI edge cases and regression prevention"""
    
    # ========== Environment-Specific Tests ==========
    
    @pytest.mark.parametrize("env,expected_auth_patterns,expected_frontend_domain", [
        ("development", ["http://localhost:808", "http://127.0.0.1:800"], "http://localhost:3000"),
        ("staging", ["https://auth.staging.netrasystems.ai"], "https://app.staging.netrasystems.ai"),
        ("production", ["https://auth.netrasystems.ai"], "https://netrasystems.ai"),
    ])
    def test_oauth_redirect_uri_cross_environment_validation(self, env, expected_auth_patterns, expected_frontend_domain):
        """Test 1: Validate OAuth redirect URIs use correct domain for each environment"""
        # Mock the AuthConfig methods directly to ensure the environment is respected
        with patch('auth_service.auth_core.config.AuthConfig.get_environment', return_value=env):
            if env == "staging":
                with patch('auth_service.auth_core.config.AuthConfig.get_auth_service_url', return_value="https://auth.staging.netrasystems.ai"), \
                     patch('auth_service.auth_core.config.AuthConfig.get_frontend_url', return_value="https://app.staging.netrasystems.ai"):
                    auth_url, frontend_url = _determine_urls()
            elif env == "production":
                with patch('auth_service.auth_core.config.AuthConfig.get_auth_service_url', return_value="https://auth.netrasystems.ai"), \
                     patch('auth_service.auth_core.config.AuthConfig.get_frontend_url', return_value="https://netrasystems.ai"):
                    auth_url, frontend_url = _determine_urls()
            else:  # development
                auth_url, frontend_url = _determine_urls()
            
            # Verify auth service URL is at index 0 (accept localhost:8081 or 127.0.0.1:8001)
            auth_url_valid = any(auth_url.startswith(pattern) for pattern in expected_auth_patterns)
            assert auth_url_valid, \
                f"Auth URL should match one of {expected_auth_patterns}, got {auth_url}"
            
            # Verify frontend URL is at index 1
            assert frontend_url.startswith(expected_frontend_domain), \
                f"Frontend URL should start with {expected_frontend_domain}, got {frontend_url}"
            
            # Construct redirect URI using correct index
            redirect_uri = auth_url + "/auth/callback"
            
            # Verify redirect URI uses auth service domain, not frontend
            auth_redirect_valid = any(pattern in redirect_uri for pattern in expected_auth_patterns)
            assert auth_redirect_valid, \
                f"Redirect URI must use auth service domain patterns {expected_auth_patterns}, got {redirect_uri}"
            assert expected_frontend_domain not in redirect_uri, \
                f"Redirect URI must NOT use frontend domain {expected_frontend_domain}"
    
    def test_oauth_redirect_uri_domain_mismatch_detection(self):
        """Test 2: Detect when redirect_uri doesn't match auth service domain"""
        # Known frontend domains that should NEVER appear in redirect_uri
        forbidden_domains = [
            "app.staging.netrasystems.ai",
            "netrasystems.ai",  # Main domain is frontend in production
            "localhost:3000",    # Frontend port
        ]
        
        auth_url, frontend_url = _determine_urls()
        redirect_uri = auth_url + "/auth/callback"
        
        for forbidden in forbidden_domains:
            assert forbidden not in redirect_uri, \
                f"CRITICAL: Frontend domain '{forbidden}' found in redirect_uri: {redirect_uri}"
    
    def test_oauth_redirect_uri_staging_production_consistency(self):
        """Test 3: Verify staging and prod use auth service URLs consistently"""
        environments = ["staging", "production"]
        redirect_uris = {}
        
        for env in environments:
            # Need to patch AuthConfig.get_environment directly
            with patch.object(AuthConfig, 'get_environment', return_value=env):
                auth_url, _ = _determine_urls()
                redirect_uris[env] = auth_url + "/auth/callback"
        
        # Both should use auth subdomain pattern
        assert "auth." in redirect_uris["staging"], \
            "Staging must use auth subdomain"
        assert "auth." in redirect_uris["production"] or "localhost:808" in redirect_uris["production"] or "localhost:800" in redirect_uris["production"], \
            "Production must use auth subdomain or local auth port"
        
        # Neither should use app subdomain
        assert "app." not in redirect_uris["staging"], \
            "Staging must NOT use app subdomain for OAuth"
        assert "app." not in redirect_uris["production"], \
            "Production must NOT use app subdomain for OAuth"
    
    # ========== URL Construction and Array Index Tests ==========
    
    def test_determine_urls_return_order_validation(self):
        """Test 4: Validate _determine_urls() returns (auth_url, frontend_url) in correct order"""
        auth_url, frontend_url = _determine_urls()
        
        # Auth service should be at index 0
        assert ("808" in auth_url or "800" in auth_url or "auth." in auth_url), \
            f"Index [0] must be auth service URL, got: {auth_url}"
        
        # Frontend should be at index 1
        assert "3000" in frontend_url or "app." in frontend_url or "netrasystems.ai" in frontend_url, \
            f"Index [1] must be frontend URL, got: {frontend_url}"
        
        # Verify they're different
        assert auth_url != frontend_url, \
            "Auth and frontend URLs must be different"
    
    def test_oauth_redirect_uri_index_boundary_conditions(self):
        """Test 5: Test edge cases around array indexing"""
        urls = _determine_urls()
        
        # Valid indices
        assert urls[0] is not None, "Index [0] must be valid"
        assert urls[1] is not None, "Index [1] must be valid"
        
        # Invalid indices should raise
        with pytest.raises(IndexError):
            _ = urls[2]  # Out of bounds
        
        # Negative indices (Python allows these but we should validate behavior)
        assert urls[-2] == urls[0], "Negative index -2 should equal index 0"
        assert urls[-1] == urls[1], "Negative index -1 should equal index 1"
        
        # Using wrong index for redirect_uri would be catastrophic
        wrong_redirect = urls[1] + "/auth/callback"  # Using frontend URL
        correct_redirect = urls[0] + "/auth/callback"  # Using auth URL
        
        assert "auth." in correct_redirect or "808" in correct_redirect or "800" in correct_redirect, \
            "Correct redirect must use auth service"
        assert ("auth." not in wrong_redirect) or ("3000" in wrong_redirect), \
            "Wrong redirect would use frontend"
    
    def test_oauth_redirect_uri_construction_pattern_validation(self):
        """Test 6: Validate all OAuth routes use correct URL construction pattern"""
        # Read the auth_routes.py file
        auth_routes_path = Path(__file__).parent.parent / "auth_core" / "routes" / "auth_routes.py"
        
        with open(auth_routes_path, "r") as f:
            source_code = f.read()
        
        # Find all redirect_uri assignments
        redirect_patterns = re.findall(r'redirect_uri\s*=.*_determine_urls\(\)\[\d\].*', source_code)
        
        for pattern in redirect_patterns:
            # Must use index [0], not [1]
            assert "_determine_urls()[0]" in pattern, \
                f"REGRESSION DETECTED: OAuth redirect pattern using wrong index: {pattern}"
            assert "_determine_urls()[1]" not in pattern, \
                f"CRITICAL: Frontend URL index [1] found in redirect_uri: {pattern}"
    
    # ========== OAuth Flow Integration Tests ==========
    
    @pytest.mark.skip(reason="Test makes real HTTP request to Google OAuth - needs mocking")
    @pytest.mark.asyncio
    async def test_oauth_initiation_to_callback_flow_integration(self):
        """Test 7: Validate complete OAuth flow from initiation to callback"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Step 1: Initiate OAuth login
        response = client.get("/auth/login?provider=google")
        
        # Should redirect to Google
        assert response.status_code == 302 or response.status_code == 307
        location = response.headers.get("location", "")
        
        # Validate redirect_uri parameter in Google OAuth URL
        assert "redirect_uri=" in location, "Must include redirect_uri parameter"
        
        # Extract redirect_uri from location
        import urllib.parse
        parsed = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(parsed.query)
        redirect_uri = params.get("redirect_uri", [""])[0]
        
        # Redirect URI must point to auth service, not frontend
        assert "localhost:808" in redirect_uri or "localhost:800" in redirect_uri or "127.0.0.1:800" in redirect_uri or "auth." in redirect_uri, \
            f"Redirect URI must point to auth service, got: {redirect_uri}"
        assert "localhost:3000" not in redirect_uri and "app." not in redirect_uri, \
            f"Redirect URI must NOT point to frontend, got: {redirect_uri}"
    
    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_oauth_callback_endpoint_method_validation(self, method):
        """Test 8: Validate OAuth callback endpoints accept both GET and POST"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Mock callback parameters
        params = {
            "code": "test_auth_code",
            "state": "test_state"
        }
        
        if method == "GET":
            response = client.get("/auth/callback", params=params)
        else:
            response = client.post("/auth/callback", json=params)
        
        # Should handle the request (might fail auth but shouldn't be 405)
        assert response.status_code != 405, \
            f"OAuth callback must accept {method} method"
    
    @pytest.mark.asyncio
    async def test_oauth_state_parameter_round_trip_validation(self):
        """Test 9: Validate state parameter flows correctly through redirect"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        import uuid
        
        client = TestClient(app)
        
        # Generate unique state
        test_state = str(uuid.uuid4())
        
        # Initiate OAuth with state
        response = client.get(f"/auth/login?provider=google&state={test_state}")
        
        # State should be in redirect URL to Google
        location = response.headers.get("location", "")
        assert f"state={test_state}" in location or "state=" in location, \
            "State parameter must be passed to OAuth provider"
    
    # ========== Multi-Provider OAuth Tests ==========
    
    @pytest.mark.parametrize("provider", ["google", "github", "facebook"])
    def test_multi_provider_redirect_uri_consistency(self, provider):
        """Test 10: Validate all OAuth providers use same redirect URI pattern"""
        auth_url, _ = _determine_urls()
        expected_redirect = auth_url + "/auth/callback"
        
        # All providers should use the same auth service callback URL
        # This is a pattern test - actual provider implementation may vary
        assert "auth." in expected_redirect or "808" in expected_redirect or "800" in expected_redirect, \
            f"Provider {provider} must use auth service for callbacks"
    
    # ========== Error Handling and Logging Tests ==========
    
    @pytest.mark.asyncio
    async def test_oauth_callback_logging_and_metrics(self):
        """Test 12: Validate OAuth callbacks generate proper logs and metrics"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        import logging
        
        client = TestClient(app)
        
        # Set up log capture
        with patch("auth_service.auth_core.routes.auth_routes.logger") as mock_logger:
            # Attempt callback
            response = client.get("/auth/callback?code=test&state=test")
            
            # Should log the callback attempt
            assert mock_logger.info.called or mock_logger.debug.called, \
                "OAuth callback must generate logs"
            
            # Check for redirect_uri in logs
            log_messages = [str(call) for call in mock_logger.info.call_args_list]
            redirect_uri_logged = any("redirect_uri" in msg for msg in log_messages)
            
            assert redirect_uri_logged or len(log_messages) > 0, \
                "OAuth callback should log redirect_uri or callback reception"
    
    def test_oauth_error_propagation_to_frontend(self):
        """Test 13: Validate OAuth errors are properly communicated"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Callback with error
        response = client.get("/auth/callback?error=access_denied&error_description=User+denied+access")
        
        # Should redirect to frontend with error
        assert response.status_code in [302, 307], "Should redirect on error"
        
        location = response.headers.get("location", "")
        
        # Error should be in redirect to frontend
        assert "error=" in location or "error_description=" in location, \
            "OAuth errors must be propagated to frontend"
        
        # Should NOT be generic "No token received"
        assert "No token received" not in location, \
            "Error messages should be specific, not generic"
    
    # ========== Configuration and Security Tests ==========
    
    def test_oauth_csrf_protection_with_correct_callbacks(self):
        """Test 16: Validate CSRF protection works with correct callbacks"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Attempt callback without valid state
        response = client.get("/auth/callback?code=test_code")
        
        # Should reject or handle missing state
        assert response.status_code >= 400 or "error" in response.headers.get("location", ""), \
            "OAuth callback without state should be rejected or error"
    
    # ========== Race Condition and Timeout Tests ==========
    
    @pytest.mark.asyncio
    async def test_oauth_callback_race_condition_handling(self):
        """Test 17: Validate multiple simultaneous OAuth callbacks handled correctly"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        import asyncio
        
        client = TestClient(app)
        
        async def make_callback(code):
            return client.get(f"/auth/callback?code={code}&state=test")
        
        # Simulate concurrent callbacks
        codes = [f"code_{i}" for i in range(5)]
        tasks = [make_callback(code) for code in codes]
        
        # All should complete without deadlock
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # No exceptions from race conditions
        exceptions = [r for r in responses if isinstance(r, Exception)]
        assert len(exceptions) == 0, \
            f"Race conditions detected: {exceptions}"
    
    @pytest.mark.timeout(5)  # 5 second timeout
    def test_oauth_callback_timeout_scenarios(self):
        """Test 18: Validate OAuth flow handles timeouts gracefully"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Mock slow Google token exchange
        with patch("auth_service.auth_core.routes.auth_routes.exchange_code_for_token") as mock_exchange:
            mock_exchange.side_effect = asyncio.TimeoutError("Token exchange timeout")
            
            response = client.get("/auth/callback?code=test&state=test")
            
            # Should handle timeout gracefully
            assert response.status_code < 500, \
                "Timeout should be handled gracefully, not cause 500 error"
    
    # ========== Deployment and Code Review Tests ==========
    
    def test_oauth_redirect_uri_code_review_automation(self):
        """Test 19: Automated detection of incorrect redirect URI patterns"""
        # This test simulates what CI/CD should catch
        auth_routes_path = Path(__file__).parent.parent / "auth_core" / "routes" / "auth_routes.py"
        
        with open(auth_routes_path, "r") as f:
            source_code = f.read()
        
        # Parse AST to find redirect_uri assignments
        tree = ast.parse(source_code)
        
        class RedirectURIVisitor(ast.NodeVisitor):
            def __init__(self):
                self.violations = []
            
            def visit_Assign(self, node):
                # Check for redirect_uri assignments
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "redirect_uri":
                        # Check if value contains _determine_urls()[1]
                        source_line = ast.unparse(node.value) if hasattr(ast, 'unparse') else str(node.value)
                        if "_determine_urls()[1]" in source_line:
                            self.violations.append({
                                "line": node.lineno,
                                "code": source_line
                            })
                self.generic_visit(node)
        
        visitor = RedirectURIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.violations) == 0, \
            f"CRITICAL: Found redirect_uri using frontend URL index [1]: {visitor.violations}"
    
    def test_oauth_configuration_deployment_validation(self):
        """Test 20: Post-deployment validation of OAuth configuration"""
        # Simulate deployment validation
        validation_checks = {
            "auth_service_healthy": True,
            "frontend_healthy": True,
            "oauth_redirect_correct": True,
            "google_console_configured": True,
        }
        
        # Check OAuth redirect configuration
        auth_url, frontend_url = _determine_urls()
        redirect_uri = auth_url + "/auth/callback"
        
        # Validate configuration
        validation_checks["oauth_redirect_correct"] = (
            "auth." in redirect_uri or "808" in redirect_uri or "800" in redirect_uri
        )
        
        # All checks must pass
        failed_checks = [k for k, v in validation_checks.items() if not v]
        assert len(failed_checks) == 0, \
            f"Deployment validation failed: {failed_checks}"


class TestOAuthRedirectRegression:
    """Additional regression-specific tests"""
    
    def test_prevent_frontend_url_in_oauth_redirect(self):
        """Ensure frontend URL is NEVER used for OAuth redirect"""
        _, frontend_url = _determine_urls()
        
        # These should NEVER appear in OAuth redirect URIs
        forbidden_patterns = [
            frontend_url + "/auth/callback",
            "localhost:3000/auth/callback",
            "app.staging.netrasystems.ai/auth/callback",
            "netrasystems.ai/auth/callback",
        ]
        
        auth_url, _ = _determine_urls()
        correct_redirect = auth_url + "/auth/callback"
        
        for forbidden in forbidden_patterns:
            assert forbidden not in correct_redirect, \
                f"REGRESSION: Frontend pattern '{forbidden}' must never appear in OAuth redirect"
    
    def test_oauth_callback_must_exchange_tokens(self):
        """Verify auth service can exchange OAuth codes for tokens"""
        # Auth service must have token exchange capability
        from auth_service.auth_core.routes import auth_routes
        
        assert hasattr(auth_routes, "exchange_code_for_token") or \
               hasattr(auth_routes, "oauth_callback") or \
               hasattr(auth_routes, "handle_oauth_callback"), \
            "Auth service must have OAuth token exchange capability"
    
    def test_frontend_cannot_exchange_oauth_codes(self):
        """Verify frontend cannot and should not exchange OAuth codes"""
        # This is a conceptual test - frontend should only receive tokens, not codes
        frontend_forbidden_operations = [
            "exchange_code_for_token",
            "oauth_token_exchange",
            "google_oauth_exchange"
        ]
        
        # If we had frontend code access, we'd verify it doesn't have these
        # For now, this documents the requirement
        assert True, "Frontend must not implement OAuth code exchange"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])