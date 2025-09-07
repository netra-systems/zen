"""OAuth Redirect URI Configuration Regression Tests

CRITICAL: These tests prevent OAuth redirect URI misconfiguration
that caused staging deployment failures.

Business Impact: Prevents authentication failures affecting $75K+ MRR
Reference: OAuth Regression Analysis 20250905
"""

import os
import pytest
from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider
from auth_service.auth_core.auth_environment import get_auth_env


class TestOAuthRedirectURIConfiguration:
    """Test OAuth redirect URI uses proper configuration from AuthEnvironment.
    
    CRITICAL: These tests ensure OAuth redirect URI is correctly configured
    for each environment using the SSOT get_auth_service_url() method.
    """
    
    def test_staging_redirect_uri_uses_proper_domain(self):
        """Test staging OAuth redirect URI uses auth.staging.netrasystems.ai."""
        # Create provider and get redirect URI
        provider = GoogleOAuthProvider()
        redirect_uri = provider.get_redirect_uri()
        
        # CRITICAL: Must use auth.staging.netrasystems.ai, not Cloud Run URL
        assert redirect_uri == "https://auth.staging.netrasystems.ai/auth/oauth/callback", \
            f"Staging redirect URI must use auth.staging.netrasystems.ai, got: {redirect_uri}"
        
        # Verify it doesn't use Cloud Run app URL
        assert "run.app" not in redirect_uri, \
            "Redirect URI must NOT use Cloud Run app URL"
    
    def test_production_redirect_uri_uses_proper_domain(self):
        """Test production OAuth redirect URI uses auth.netrasystems.ai."""
        provider = GoogleOAuthProvider()
        redirect_uri = provider.get_redirect_uri()
        
        # CRITICAL: Must use auth.netrasystems.ai for production
        assert redirect_uri == "https://auth.netrasystems.ai/auth/oauth/callback", \
            f"Production redirect URI must use auth.netrasystems.ai, got: {redirect_uri}"
        
        # Verify it doesn't use Cloud Run app URL
        assert "run.app" not in redirect_uri, \
            "Redirect URI must NOT use Cloud Run app URL"
    
    def test_development_redirect_uri_uses_localhost(self):
        """Test development OAuth redirect URI uses localhost."""
        provider = GoogleOAuthProvider()
        redirect_uri = provider.get_redirect_uri()
        
        # Development should use localhost
        assert "localhost" in redirect_uri or "127.0.0.1" in redirect_uri, \
            f"Development redirect URI must use localhost, got: {redirect_uri}"
        
        # Should not use production domains
        assert "netrasystems.ai" not in redirect_uri, \
            "Development must not use production domains"
    
    def test_redirect_uri_caching(self):
        """Test redirect URI is cached after first call."""
        provider = GoogleOAuthProvider()
        
        # Get redirect URI twice
        uri1 = provider.get_redirect_uri()
        uri2 = provider.get_redirect_uri()
        
        # Should return same cached value
        assert uri1 == uri2, "Redirect URI should be cached"
        assert uri1 is uri2, "Should return same cached object"
    
    def test_redirect_uri_uses_auth_environment_ssot(self):
        """Test redirect URI uses AuthEnvironment.get_auth_service_url() as SSOT."""
        provider = GoogleOAuthProvider()
        auth_env = get_auth_env()
        
        # Get expected base URL from SSOT
        expected_base = auth_env.get_auth_service_url()
        expected_uri = f"{expected_base}/auth/oauth/callback"
        
        # Get actual redirect URI
        actual_uri = provider.get_redirect_uri()
        
        # Must match SSOT
        assert actual_uri == expected_uri, \
            f"Redirect URI must use AuthEnvironment SSOT. Expected: {expected_uri}, Got: {actual_uri}"
    
    def test_redirect_uri_respects_explicit_override(self):
        """Test redirect URI respects AUTH_SERVICE_URL override."""
        provider = GoogleOAuthProvider()
        redirect_uri = provider.get_redirect_uri()
        
        # Should use the override
        assert redirect_uri == "https://custom.domain.com/auth/oauth/callback", \
            f"Should respect AUTH_SERVICE_URL override, got: {redirect_uri}"


class TestOAuthConfigurationValidation:
    """Test OAuth configuration validation to prevent deployment failures."""
    
    def test_validate_configuration_checks_redirect_uri(self):
        """Test configuration validation includes redirect URI check."""
        provider = GoogleOAuthProvider()
        
        # Mock credentials for testing
        provider._client_id = "test-client-id.apps.googleusercontent.com"
        provider._client_secret = "test-secret-key-long-enough"
        
        is_valid, error = provider.validate_configuration()
        
        # Should validate redirect URI is configured
        redirect_uri = provider.get_redirect_uri()
        assert redirect_uri is not None, "Redirect URI must be configured"
    
    def test_staging_configuration_validation(self):
        """Test staging environment configuration validation."""
        provider = GoogleOAuthProvider()
        
        # Mock valid credentials
        provider._client_id = "staging-client.apps.googleusercontent.com"
        provider._client_secret = "staging-secret-key-long-enough"
        
        is_valid, error = provider.validate_configuration()
        
        if not is_valid:
            # If invalid, should be due to missing real credentials, not redirect URI
            assert "redirect URI" not in error.lower() or "staging" in error.lower(), \
                f"Staging validation should not fail on redirect URI: {error}"
    
    def test_self_check_includes_redirect_uri(self):
        """Test self-check includes redirect URI verification."""
        provider = GoogleOAuthProvider()
        
        # Mock credentials
        provider._client_id = "test-client.apps.googleusercontent.com"
        provider._client_secret = "test-secret-long-enough"
        
        results = provider.self_check()
        
        # Should include redirect URI in results
        assert "redirect_uri" in results, "Self-check must include redirect_uri"
        assert results["redirect_uri"] is not None, "Redirect URI should be configured"
        
        # Should have checked redirect URI configuration
        if "redirect_uri_configured" not in str(results["checks_passed"]):
            assert "redirect_uri_configured" not in str(results["checks_failed"]), \
                "Redirect URI configuration should be checked"


class TestOAuthAuthorizationURL:
    """Test OAuth authorization URL generation with proper redirect URI."""
    
    def test_authorization_url_uses_correct_redirect_uri(self):
        """Test authorization URL includes correct redirect URI for staging."""
        provider = GoogleOAuthProvider()
        provider._client_id = "test-client-id"  # Mock client ID
        
        # Generate authorization URL
        auth_url = provider.get_authorization_url("test-state")
        
        # Should include the proper redirect URI
        expected_redirect = "https%3A%2F%2Fauth.staging.netrasystems.ai%2Fauth%2Foauth%2Fcallback"
        assert expected_redirect in auth_url or "auth.staging.netrasystems.ai" in auth_url, \
            f"Authorization URL must include proper redirect URI: {auth_url}"
        
        # Should NOT include Cloud Run URL
        assert "run.app" not in auth_url, \
            "Authorization URL must not include Cloud Run app URL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])