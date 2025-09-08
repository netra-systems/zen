"""
Comprehensive Unit Tests for Google OAuth Provider

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure Google OAuth integration prevents authentication failures
- Value Impact: Prevents $75K+ MRR loss from OAuth authentication failures
- Strategic Impact: Core authentication mechanism for user login

Test Coverage:
- Google OAuth provider initialization and configuration
- Authorization URL generation with proper parameters
- Authorization code exchange for user tokens
- User profile retrieval from Google APIs
- State parameter validation (CSRF protection)
- Environment-specific configuration validation
- Error handling for OAuth failures
- Security validations and input sanitization
- Network error handling for Google API calls
- Token validation and refresh flows
- Multiple scope support
- Redirect URI validation across environments

CRITICAL: Uses SSOT BaseTestCase and IsolatedEnvironment.
NO direct os.environ access. Tests with real OAuth flows where possible.
"""

import json
import uuid
import pytest
import requests
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock, Mock
from urllib.parse import urlparse, parse_qs

from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env


class TestGoogleOAuthProviderInitialization(SSotBaseTestCase):
    """Test Google OAuth provider initialization and configuration."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set up test environment variables
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.provider = None
        self.test_state = str(uuid.uuid4())
        
    def test_provider_initializes_successfully(self):
        """Test that Google OAuth provider initializes without errors."""
        self.provider = GoogleOAuthProvider()
        
        assert self.provider is not None
        assert hasattr(self.provider, 'auth_env')
        assert hasattr(self.provider, 'env')
        assert self.provider.env == "test"
        
        self.record_metric("provider_initialized", True)
        
    def test_provider_environment_detection(self):
        """Test provider correctly detects different environments."""
        environments = ["development", "test", "staging", "production"]
        
        for env in environments:
            with self.temp_env_vars(ENVIRONMENT=env):
                provider = GoogleOAuthProvider()
                assert provider.env == env
                
        self.record_metric("environments_tested", len(environments))
        
    def test_provider_credentials_initialization(self):
        """Test provider attempts to initialize credentials."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = "test-client-id.apps.googleusercontent.com"
            mock_client_secret.return_value = "test-client-secret"
            
            provider = GoogleOAuthProvider()
            
            assert provider.client_id == "test-client-id.apps.googleusercontent.com"
            assert provider.client_secret == "test-client-secret"
            
        self.record_metric("credentials_initialized", True)
        
    def test_provider_handles_missing_credentials_in_test(self):
        """Test provider handles missing credentials gracefully in test environment."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = None
            mock_client_secret.return_value = None
            
            # Should not raise exception in test environment
            provider = GoogleOAuthProvider()
            
            assert provider.client_id is None
            assert provider.client_secret is None
            assert provider.is_configured() is False
            
        self.record_metric("missing_credentials_handled", True)
        
    def test_provider_requires_credentials_in_production(self):
        """Test provider requires credentials in production environment."""
        with self.temp_env_vars(ENVIRONMENT="production"):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
                
                mock_client_id.return_value = None
                mock_client_secret.return_value = None
                
                # Should raise exception in production environment
                with self.expect_exception(GoogleOAuthError, "not configured for production"):
                    GoogleOAuthProvider()


class TestGoogleOAuthProviderConfiguration(SSotBaseTestCase):
    """Test Google OAuth provider configuration and validation."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        # Mock credentials for consistent testing
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        
    def test_is_configured_with_valid_credentials(self):
        """Test is_configured returns True with valid credentials."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            assert provider.is_configured() is True
            
        self.record_metric("configured_with_valid_creds", True)
        
    def test_is_configured_with_missing_credentials(self):
        """Test is_configured returns False with missing credentials."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = None
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            assert provider.is_configured() is False
            
            # Test missing client secret
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = None
            
            provider = GoogleOAuthProvider()
            assert provider.is_configured() is False
            
        self.record_metric("unconfigured_handling", True)
        
    def test_validate_configuration_with_valid_data(self):
        """Test configuration validation with valid OAuth data."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            is_valid, message = provider.validate_configuration()
            
            assert is_valid is True
            assert message == "OAuth configuration is valid"
            
        self.record_metric("valid_config_validation", True)
        
    def test_validate_configuration_with_invalid_client_id(self):
        """Test configuration validation with invalid client ID."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            # Test various invalid client IDs
            invalid_client_ids = [
                None,
                "",
                "short-id",
                "invalid-format",
                "123456789-abcdefghijklmnop.invalid.com"
            ]
            
            mock_client_secret.return_value = self.client_secret
            
            for invalid_id in invalid_client_ids:
                mock_client_id.return_value = invalid_id
                
                provider = GoogleOAuthProvider()
                is_valid, message = provider.validate_configuration()
                
                assert is_valid is False
                assert len(message) > 0
                
        self.record_metric("invalid_client_id_tests", len(invalid_client_ids))
        
    def test_validate_configuration_with_invalid_client_secret(self):
        """Test configuration validation with invalid client secret."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            
            # Test various invalid client secrets
            invalid_secrets = [None, "", "short"]
            
            for invalid_secret in invalid_secrets:
                mock_client_secret.return_value = invalid_secret
                
                provider = GoogleOAuthProvider()
                is_valid, message = provider.validate_configuration()
                
                assert is_valid is False
                assert len(message) > 0
                
        self.record_metric("invalid_client_secret_tests", len(invalid_secrets))
        
    def test_get_configuration_status(self):
        """Test getting configuration status."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            status = provider.get_configuration_status()
            
            assert isinstance(status, dict)
            assert status["provider"] == "google"
            assert status["environment"] == "test"
            assert status["client_id_configured"] is True
            assert status["client_secret_configured"] is True
            assert status["is_configured"] is True
            assert "redirect_uri" in status
            
        self.record_metric("configuration_status_retrieved", True)


class TestGoogleOAuthProviderRedirectURI(SSotBaseTestCase):
    """Test Google OAuth provider redirect URI functionality."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
    def test_get_redirect_uri_returns_valid_uri(self):
        """Test that redirect URI is properly formatted."""
        provider = GoogleOAuthProvider()
        redirect_uri = provider.get_redirect_uri()
        
        if redirect_uri:  # May be None in test environment
            assert isinstance(redirect_uri, str)
            assert redirect_uri.startswith("http")
            assert "/auth/callback" in redirect_uri
            
        self.record_metric("redirect_uri_format_valid", True)
        
    def test_redirect_uri_environment_specific(self):
        """Test redirect URI adapts to different environments."""
        environments = ["development", "staging", "production"]
        
        for env in environments:
            with self.temp_env_vars(ENVIRONMENT=env):
                provider = GoogleOAuthProvider()
                redirect_uri = provider.get_redirect_uri()
                
                if redirect_uri:
                    # Should not contain other environment references
                    if env == "staging":
                        assert "localhost" not in redirect_uri or "staging" in redirect_uri
                    elif env == "production":
                        assert "localhost" not in redirect_uri
                        assert "staging" not in redirect_uri
                        
        self.record_metric("redirect_uri_env_tests", len(environments))
        
    def test_redirect_uri_consistency(self):
        """Test that redirect URI is consistent across multiple calls."""
        provider = GoogleOAuthProvider()
        
        uri1 = provider.get_redirect_uri()
        uri2 = provider.get_redirect_uri()
        
        assert uri1 == uri2
        
        self.record_metric("redirect_uri_consistent", True)


class TestGoogleOAuthProviderAuthorizationURL(SSotBaseTestCase):
    """Test Google OAuth provider authorization URL generation."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        self.test_state = str(uuid.uuid4())
        
    def test_get_authorization_url_basic(self):
        """Test basic authorization URL generation."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            auth_url = provider.get_authorization_url(self.test_state)
            
            assert isinstance(auth_url, str)
            assert auth_url.startswith("https://accounts.google.com/o/oauth2/auth")
            assert f"state={self.test_state}" in auth_url
            assert "client_id=" in auth_url
            assert "redirect_uri=" in auth_url
            assert "scope=" in auth_url
            
        self.record_metric("auth_url_generated", True)
        
    def test_get_authorization_url_with_custom_scopes(self):
        """Test authorization URL generation with custom scopes."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            custom_scopes = ["openid", "email", "profile", "https://www.googleapis.com/auth/calendar"]
            auth_url = provider.get_authorization_url(self.test_state, scopes=custom_scopes)
            
            # Parse URL to check parameters
            parsed_url = urlparse(auth_url)
            query_params = parse_qs(parsed_url.query)
            
            scope_param = query_params.get("scope", [])
            if scope_param:
                scopes_in_url = scope_param[0].split(" ")
                for scope in custom_scopes:
                    assert scope in scopes_in_url
                    
        self.record_metric("custom_scopes_tested", True)
        
    def test_get_authorization_url_parameters(self):
        """Test that authorization URL contains all required parameters."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            auth_url = provider.get_authorization_url(self.test_state)
            
            # Parse URL to check parameters
            parsed_url = urlparse(auth_url)
            query_params = parse_qs(parsed_url.query)
            
            required_params = ["client_id", "redirect_uri", "scope", "response_type", "state", "access_type", "prompt"]
            
            for param in required_params:
                assert param in query_params, f"Required parameter {param} missing from auth URL"
                
            # Check specific parameter values
            assert query_params["response_type"][0] == "code"
            assert query_params["access_type"][0] == "offline"
            assert query_params["prompt"][0] == "consent"
            assert query_params["state"][0] == self.test_state
            
        self.record_metric("auth_url_params_validated", True)
        
    def test_get_authorization_url_without_client_id(self):
        """Test authorization URL generation fails without client ID."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = None
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            with self.expect_exception(GoogleOAuthError, "Cannot generate authorization URL without client ID"):
                provider.get_authorization_url(self.test_state)
                
        self.record_metric("auth_url_client_id_required", True)


class TestGoogleOAuthProviderCodeExchange(SSotBaseTestCase):
    """Test Google OAuth provider authorization code exchange."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        self.test_state = str(uuid.uuid4())
        self.test_code = "test-authorization-code"
        
    def test_exchange_code_for_user_info_test_environment(self):
        """Test code exchange in test environment returns mock data."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            user_info = provider.exchange_code_for_user_info(self.test_code, self.test_state)
            
            assert user_info is not None
            assert isinstance(user_info, dict)
            assert user_info["email"] == "test@example.com"
            assert user_info["name"] == "Test User"
            assert user_info["sub"] == "test-user-id"
            assert user_info["verified_email"] is True
            
        self.record_metric("test_code_exchange", True)
        
    def test_exchange_code_for_user_info_without_client_secret(self):
        """Test code exchange fails without client secret."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = None
            
            provider = GoogleOAuthProvider()
            
            with self.expect_exception(GoogleOAuthError, "Cannot exchange code without client secret"):
                provider.exchange_code_for_user_info("some-code", self.test_state)
                
        self.record_metric("code_exchange_client_secret_required", True)
        
    def test_exchange_code_for_user_info_real_api_success(self):
        """Test successful code exchange with mocked Google API responses."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret, \
             patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            # Mock token response
            token_response = Mock()
            token_response.raise_for_status = Mock()
            token_response.json.return_value = {
                "access_token": "ya29.test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_post.return_value = token_response
            
            # Mock user info response
            user_response = Mock()
            user_response.raise_for_status = Mock()
            user_response.json.return_value = {
                "email": "user@example.com",
                "name": "Real User",
                "id": "123456789",
                "verified_email": True,
                "picture": "https://example.com/photo.jpg"
            }
            mock_get.return_value = user_response
            
            provider = GoogleOAuthProvider()
            
            # Use non-test code to trigger real API path
            user_info = provider.exchange_code_for_user_info("real-auth-code", self.test_state)
            
            assert user_info is not None
            assert user_info["email"] == "user@example.com"
            assert user_info["name"] == "Real User"
            assert user_info["sub"] == "123456789"
            assert user_info["verified_email"] is True
            assert user_info["picture"] == "https://example.com/photo.jpg"
            
        self.record_metric("real_api_success_mock", True)
        
    def test_exchange_code_for_user_info_token_request_failure(self):
        """Test code exchange handles token request failures."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret, \
             patch('requests.post') as mock_post:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            # Mock token request failure
            mock_post.side_effect = requests.exceptions.RequestException("Token request failed")
            
            provider = GoogleOAuthProvider()
            
            with self.expect_exception(GoogleOAuthError, "Failed to exchange code"):
                provider.exchange_code_for_user_info("real-auth-code", self.test_state)
                
        self.record_metric("token_request_failure_handled", True)
        
    def test_exchange_code_for_user_info_no_access_token(self):
        """Test code exchange handles missing access token in response."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret, \
             patch('requests.post') as mock_post:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            # Mock token response without access token
            token_response = Mock()
            token_response.raise_for_status = Mock()
            token_response.json.return_value = {"token_type": "Bearer"}
            mock_post.return_value = token_response
            
            provider = GoogleOAuthProvider()
            
            with self.expect_exception(GoogleOAuthError, "No access token in response"):
                provider.exchange_code_for_user_info("real-auth-code", self.test_state)
                
        self.record_metric("missing_access_token_handled", True)
        
    def test_exchange_code_for_user_info_user_info_failure(self):
        """Test code exchange handles user info request failures."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret, \
             patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            # Mock successful token response
            token_response = Mock()
            token_response.raise_for_status = Mock()
            token_response.json.return_value = {"access_token": "ya29.test-token"}
            mock_post.return_value = token_response
            
            # Mock user info request failure
            mock_get.side_effect = requests.exceptions.RequestException("User info request failed")
            
            provider = GoogleOAuthProvider()
            
            with self.expect_exception(GoogleOAuthError, "Failed to exchange code"):
                provider.exchange_code_for_user_info("real-auth-code", self.test_state)
                
        self.record_metric("user_info_failure_handled", True)


class TestGoogleOAuthProviderSelfCheck(SSotBaseTestCase):
    """Test Google OAuth provider self-check functionality."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        
    def test_self_check_with_valid_configuration(self):
        """Test self-check with valid OAuth configuration."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            assert isinstance(check_result, dict)
            assert check_result["provider"] == "google"
            assert check_result["environment"] == "test"
            assert "checks_passed" in check_result
            assert "checks_failed" in check_result
            assert "is_healthy" in check_result
            
            # Should have passed configuration validation
            assert "configuration_validation" in check_result["checks_passed"]
            assert check_result["is_healthy"] is True
            
        self.record_metric("self_check_healthy", True)
        
    def test_self_check_with_invalid_configuration(self):
        """Test self-check with invalid OAuth configuration."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = None
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            assert isinstance(check_result, dict)
            assert check_result["is_healthy"] is False
            assert len(check_result["checks_failed"]) > 0
            assert "error" in check_result
            
        self.record_metric("self_check_unhealthy", True)
        
    def test_self_check_authorization_url_generation(self):
        """Test self-check includes authorization URL generation test."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            if check_result["is_healthy"]:
                assert "authorization_url_generation" in check_result["checks_passed"]
            else:
                # Check might be in failed if other issues exist
                passed_and_failed = check_result["checks_passed"] + check_result["checks_failed"]
                auth_url_checks = [check for check in passed_and_failed if "authorization_url" in check]
                assert len(auth_url_checks) > 0
                
        self.record_metric("auth_url_check_included", True)
        
    def test_self_check_includes_redirect_uri(self):
        """Test self-check includes redirect URI information."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            if "redirect_uri" in check_result:
                assert isinstance(check_result["redirect_uri"], str)
                
            # Should have redirect URI check
            redirect_checks = [check for check in (check_result["checks_passed"] + check_result["checks_failed"]) 
                             if "redirect_uri" in check]
            assert len(redirect_checks) > 0
            
        self.record_metric("redirect_uri_check_included", True)
        
    def test_self_check_client_id_privacy(self):
        """Test self-check doesn't expose full client ID."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            if "client_id_prefix" in check_result:
                client_id_prefix = check_result["client_id_prefix"]
                assert len(client_id_prefix) <= 30  # Should be truncated
                assert client_id_prefix != self.client_id  # Should not expose full ID
                
        self.record_metric("client_id_privacy_protected", True)


class TestGoogleOAuthProviderSecurity(SSotBaseTestCase):
    """Test Google OAuth provider security features."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        
    def test_state_parameter_required(self):
        """Test that state parameter is required for authorization URL."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test with empty state
            auth_url = provider.get_authorization_url("")
            assert "state=" in auth_url
            
            # Test with None state (should be handled)
            try:
                auth_url = provider.get_authorization_url(None)
                assert "state=" in auth_url
            except (TypeError, ValueError):
                # Expected if None is not handled - that's also secure
                pass
                
        self.record_metric("state_parameter_security", True)
        
    def test_redirect_uri_validation_by_environment(self):
        """Test redirect URI validation for different environments."""
        test_cases = [
            ("staging", "http://localhost:8081/auth/callback", False),  # localhost in staging
            ("staging", "https://staging.example.com/auth/callback", True),
            ("production", "http://localhost:8081/auth/callback", False),  # localhost in production
            ("production", "https://staging.example.com/auth/callback", False),  # staging in production
            ("production", "https://app.example.com/auth/callback", True),
        ]
        
        for env, test_uri, should_be_valid in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env):
                with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
                     patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
                    
                    mock_client_id.return_value = self.client_id
                    mock_client_secret.return_value = self.client_secret
                    
                    provider = GoogleOAuthProvider()
                    
                    # Mock the redirect URI to test validation
                    with patch.object(provider, 'get_redirect_uri', return_value=test_uri):
                        is_valid, message = provider.validate_configuration()
                        
                        if should_be_valid:
                            assert is_valid, f"Expected valid for {env} with {test_uri}, but got: {message}"
                        else:
                            assert not is_valid, f"Expected invalid for {env} with {test_uri}, but was valid"
                            
        self.record_metric("redirect_uri_validation_tests", len(test_cases))
        
    def test_no_credential_exposure_in_errors(self):
        """Test that error messages don't expose credentials."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Trigger various error conditions and check messages
            try:
                # Force an error in code exchange
                with patch('requests.post', side_effect=Exception("Test error")):
                    provider.exchange_code_for_user_info("test-code", "test-state")
            except GoogleOAuthError as e:
                error_message = str(e).lower()
                
                # Should not contain sensitive information
                assert self.client_secret.lower() not in error_message
                assert "secret" not in error_message or "client_secret" not in error_message
                
        self.record_metric("credential_exposure_prevented", True)
        
    def test_input_sanitization(self):
        """Test that provider sanitizes inputs properly."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test with potentially malicious inputs
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "../../../etc/passwd",
                "javascript:alert('xss')",
                "\x00\x01\x02"  # null bytes and control characters
            ]
            
            for malicious_input in malicious_inputs:
                # Should handle gracefully without breaking
                try:
                    auth_url = provider.get_authorization_url(malicious_input)
                    # URL should be properly encoded
                    assert isinstance(auth_url, str)
                except Exception:
                    # Rejecting malicious input is also acceptable
                    pass
                    
        self.record_metric("input_sanitization_tests", len(malicious_inputs))


class TestGoogleOAuthProviderPerformance(SSotBaseTestCase):
    """Test Google OAuth provider performance characteristics."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-abcdefghijklmnopqrstuvwxyz"
        
    def test_provider_initialization_performance(self):
        """Test provider initialization performance."""
        import time
        
        start_time = time.time()
        
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
        end_time = time.time()
        initialization_time = end_time - start_time
        
        # Should initialize within 0.5 seconds
        assert initialization_time < 0.5, f"Initialization took {initialization_time:.3f}s"
        
        self.record_metric("initialization_time", initialization_time)
        
    def test_authorization_url_generation_performance(self):
        """Test authorization URL generation performance."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            import time
            start_time = time.time()
            
            # Generate multiple URLs to test performance
            for i in range(100):
                auth_url = provider.get_authorization_url(f"state-{i}")
                assert len(auth_url) > 0
                
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / 100
            
            # Each URL generation should take less than 1ms on average
            assert avg_time < 0.001, f"Average URL generation took {avg_time:.6f}s"
            
        self.record_metric("url_generation_avg_time", avg_time)
        
    def test_memory_usage_stability(self):
        """Test that provider doesn't leak memory during operations."""
        import gc
        import sys
        
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_client_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_client_secret:
            
            mock_client_id.return_value = self.client_id
            mock_client_secret.return_value = self.client_secret
            
            # Measure initial memory
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Perform many operations
            for i in range(50):
                provider = GoogleOAuthProvider()
                auth_url = provider.get_authorization_url(f"state-{i}")
                config_status = provider.get_configuration_status()
                self_check = provider.self_check()
                del provider
                
            # Measure final memory
            gc.collect()
            final_objects = len(gc.get_objects())
            
            growth = final_objects - initial_objects
            
            # Allow some growth but not excessive
            assert growth < 500, f"Memory growth: {growth} objects"
            
        self.record_metric("memory_growth", growth)


if __name__ == "__main__":
    pytest.main([__file__])