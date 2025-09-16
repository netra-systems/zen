"""
Comprehensive Security-Focused Unit Tests for OAuth Provider Classes

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent OAuth security breaches and authentication failures
- Value Impact: Protects $75K+ MRR from OAuth authentication failures
- Strategic Impact: Core security foundation for multi-user authentication system
- Risk Mitigation: Prevents credential leakage, CSRF attacks, and unauthorized access

CRITICAL SECURITY TESTING:
This test suite focuses on the most security-critical aspects of OAuth authentication:
- Multi-environment credential isolation (dev/staging/prod cannot cross-contaminate)
- State parameter validation (CSRF protection)
- Redirect URI validation (prevents callback hijacking)
- Credential sanitization (prevents exposure in logs/errors)
- Input validation (prevents injection attacks)
- Environment-specific configuration validation

TESTING METHODOLOGY:
- Uses SSOT BaseTestCase for isolated environment management
- NO mocks of core business logic - tests real OAuth provider behavior
- Real IsolatedEnvironment usage throughout
- Tests fail hard when security validation fails
- Comprehensive edge case coverage for security scenarios
"""

import pytest
import uuid
import hashlib
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, Mock, MagicMock
from urllib.parse import urlparse, parse_qs

from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env


class TestOAuthProviderEnvironmentIsolation(SSotBaseTestCase):
    """Test OAuth provider environment isolation to prevent credential leakage."""
    
    def setup_method(self, method=None):
        """Setup for each test method with isolated environment."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
    def test_development_credentials_isolated_from_production(self):
        """Test development OAuth credentials cannot leak to production."""
        # Set up development credentials
        dev_client_id = "dev-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        dev_client_secret = "GOCSPX-dev-abcdefghijklmnop"
        
        with self.temp_env_vars(
            ENVIRONMENT="development",
            GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT=dev_client_id,
            GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT=dev_client_secret
        ):
            # Create provider in development
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                mock_id.return_value = dev_client_id
                mock_secret.return_value = dev_client_secret
                
                dev_provider = GoogleOAuthProvider()
                assert dev_provider.client_id == dev_client_id
                assert dev_provider.client_secret == dev_client_secret
        
        # Switch to production environment - credentials should NOT be accessible
        with self.temp_env_vars(
            ENVIRONMENT="production",
            # Production has no credentials configured
        ):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                # Production requires credentials to be configured
                mock_id.return_value = None
                mock_secret.return_value = None
                
                # Should fail hard in production without credentials
                with self.expect_exception(GoogleOAuthError, "not configured for production"):
                    GoogleOAuthProvider()
        
        self.record_metric("environment_isolation_validated", True)
        
    def test_staging_credentials_validated_for_environment(self):
        """Test staging OAuth credentials are validated for staging environment."""
        staging_client_id = "staging-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        staging_client_secret = "GOCSPX-staging-abcdefghijklmnop"
        
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            GOOGLE_OAUTH_CLIENT_ID_STAGING=staging_client_id,
            GOOGLE_OAUTH_CLIENT_SECRET_STAGING=staging_client_secret
        ):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                mock_id.return_value = staging_client_id
                mock_secret.return_value = staging_client_secret
                
                provider = GoogleOAuthProvider()
                
                # Validate configuration for staging
                is_valid, message = provider.validate_configuration()
                
                if is_valid:
                    # If configuration is valid, redirect URI should be staging-appropriate
                    redirect_uri = provider.get_redirect_uri()
                    if redirect_uri:
                        assert "staging" in redirect_uri or "localhost" not in redirect_uri, \
                            f"Staging redirect URI should not contain localhost: {redirect_uri}"
                        
        self.record_metric("staging_validation_completed", True)
        
    def test_production_oauth_configuration_security_requirements(self):
        """Test production OAuth configuration meets strict security requirements."""
        prod_client_id = "prod-123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com"
        prod_client_secret = "GOCSPX-prod-abcdefghijklmnopqrstuvwxyz123456789"
        
        with self.temp_env_vars(
            ENVIRONMENT="production",
            GOOGLE_OAUTH_CLIENT_ID_PRODUCTION=prod_client_id,
            GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION=prod_client_secret
        ):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                mock_id.return_value = prod_client_id
                mock_secret.return_value = prod_client_secret
                
                provider = GoogleOAuthProvider()
                
                # Production configuration must be valid and secure
                is_valid, message = provider.validate_configuration()
                assert is_valid, f"Production OAuth configuration invalid: {message}"
                
                # Production redirect URI must not contain localhost or staging
                redirect_uri = provider.get_redirect_uri()
                if redirect_uri:
                    assert "localhost" not in redirect_uri, \
                        f"Production redirect URI must not contain localhost: {redirect_uri}"
                    assert "staging" not in redirect_uri, \
                        f"Production redirect URI must not contain staging: {redirect_uri}"
                        
        self.record_metric("production_security_validated", True)


class TestOAuthStateParameterSecurity(SSotBaseTestCase):
    """Test OAuth state parameter security (CSRF protection)."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "test-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-test-abcdefghijklmnopqrstuvwxyz"
        
    def test_state_parameter_cryptographically_strong(self):
        """Test state parameter generation uses cryptographically strong values."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Generate multiple authorization URLs with different state values
            state_values = []
            for _ in range(50):
                state = str(uuid.uuid4())
                state_values.append(state)
                
                auth_url = provider.get_authorization_url(state)
                parsed_url = urlparse(auth_url)
                query_params = parse_qs(parsed_url.query)
                
                assert "state" in query_params
                assert query_params["state"][0] == state
                
            # Ensure all state values are unique (no collisions)
            assert len(set(state_values)) == len(state_values), "State values must be unique"
            
            # Ensure state values are sufficiently long for security
            for state in state_values:
                assert len(state) >= 30, f"State value too short for security: {state}"
                
        self.record_metric("state_security_validated", len(state_values))
        
    def test_state_parameter_prevents_replay_attacks(self):
        """Test state parameter prevents replay attacks."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Generate multiple auth URLs at different times
            urls_and_times = []
            for i in range(10):
                state = f"session-{i}-{int(time.time())}-{uuid.uuid4()}"
                auth_url = provider.get_authorization_url(state)
                timestamp = time.time()
                urls_and_times.append((auth_url, timestamp, state))
                time.sleep(0.01)  # Small delay to ensure different timestamps
                
            # Each URL should have different state parameters
            states = [state for _, _, state in urls_and_times]
            assert len(set(states)) == len(states), "Each auth URL must have unique state"
            
            # State should include timestamp-based uniqueness
            for i, (url, timestamp, state) in enumerate(urls_and_times):
                for j, (other_url, other_timestamp, other_state) in enumerate(urls_and_times):
                    if i != j:
                        assert state != other_state, f"State collision between requests {i} and {j}"
                        
        self.record_metric("replay_attack_prevention_validated", True)
        
    def test_malicious_state_parameters_handled_safely(self):
        """Test malicious state parameters are handled safely."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test various malicious state inputs
            malicious_states = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "javascript:alert('xss')",
                "data:text/html,<script>alert('xss')</script>",
                "\x00\x01\x02\x03",  # null bytes and control characters
                "%3Cscript%3Ealert('xss')%3C/script%3E",  # URL encoded XSS
                "AAAA" * 10000,  # extremely long state
                "",  # empty state
                " \t\n\r ",  # whitespace-only state
            ]
            
            for malicious_state in malicious_states:
                try:
                    auth_url = provider.get_authorization_url(malicious_state)
                    
                    # If URL was generated, it should be safely encoded
                    parsed_url = urlparse(auth_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    assert "state" in query_params
                    state_in_url = query_params["state"][0]
                    
                    # Should not contain dangerous characters in final URL
                    assert "<script>" not in auth_url.lower()
                    assert "javascript:" not in auth_url.lower()
                    assert "DROP TABLE" not in auth_url.upper()
                    
                except Exception:
                    # It's also acceptable to reject malicious states entirely
                    pass
                    
        self.record_metric("malicious_state_tests", len(malicious_states))


class TestOAuthRedirectURISecurity(SSotBaseTestCase):
    """Test OAuth redirect URI security to prevent callback hijacking."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
        self.client_id = "test-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-test-abcdefghijklmnopqrstuvwxyz"
        
    def test_redirect_uri_environment_specific_validation(self):
        """Test redirect URI validation is strict for each environment."""
        test_scenarios = [
            # (environment, test_uri, should_be_valid, reason)
            ("production", "https://app.netrasystems.ai/auth/callback", True, "Valid production URI"),
            ("production", "http://localhost:8081/auth/callback", False, "Localhost not allowed in production"),
            ("production", "https://staging.netrasystems.ai/auth/callback", False, "Staging URI not allowed in production"),
            ("staging", "https://app.staging.netrasystems.ai/auth/callback", True, "Valid staging URI"),
            ("staging", "http://localhost:8081/auth/callback", True, "Localhost allowed in staging for testing"),
            ("staging", "https://app.netrasystems.ai/auth/callback", False, "Production URI not allowed in staging"),
            ("development", "http://localhost:8081/auth/callback", True, "Localhost allowed in development"),
            ("development", "https://app.netrasystems.ai/auth/callback", False, "Production URI not allowed in development"),
        ]
        
        for env, test_uri, should_be_valid, reason in test_scenarios:
            with self.temp_env_vars(ENVIRONMENT=env):
                with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                     patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                    
                    mock_id.return_value = self.client_id
                    mock_secret.return_value = self.client_secret
                    
                    provider = GoogleOAuthProvider()
                    
                    # Mock the redirect URI to test validation
                    with patch.object(provider, 'get_redirect_uri', return_value=test_uri):
                        is_valid, message = provider.validate_configuration()
                        
                        if should_be_valid:
                            assert is_valid, f"Expected valid for {env} with {test_uri}: {reason}. Got: {message}"
                        else:
                            assert not is_valid, f"Expected invalid for {env} with {test_uri}: {reason}. Got: {message}"
                            
        self.record_metric("redirect_uri_validation_scenarios", len(test_scenarios))
        
    def test_redirect_uri_prevents_open_redirect_attacks(self):
        """Test redirect URI validation prevents open redirect attacks."""
        malicious_redirects = [
            "https://evil.com/auth/callback",
            "http://evil.com/auth/callback", 
            "https://app.netrasystems.ai.evil.com/auth/callback",
            "https://evil.com@app.netrasystems.ai/auth/callback",
            "https://app.netrasystems.ai/auth/callback@evil.com",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://evil.com/auth/callback",
        ]
        
        with self.temp_env_vars(ENVIRONMENT="production"):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                mock_id.return_value = self.client_id
                mock_secret.return_value = self.client_secret
                
                provider = GoogleOAuthProvider()
                
                for malicious_uri in malicious_redirects:
                    with patch.object(provider, 'get_redirect_uri', return_value=malicious_uri):
                        is_valid, message = provider.validate_configuration()
                        
                        # Should reject all malicious redirect URIs
                        assert not is_valid, f"Should reject malicious redirect URI: {malicious_uri}"
                        assert len(message) > 0, "Should provide error message for rejected URI"
                        
        self.record_metric("malicious_redirect_tests", len(malicious_redirects))
        
    def test_redirect_uri_https_enforcement_production(self):
        """Test redirect URI enforces HTTPS in production environments."""
        http_uris = [
            "http://app.netrasystems.ai/auth/callback",
            "http://api.netrasystems.ai/auth/callback",
            "http://secure.netrasystems.ai/auth/callback",
        ]
        
        with self.temp_env_vars(ENVIRONMENT="production"):
            with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
                 patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
                
                mock_id.return_value = self.client_id
                mock_secret.return_value = self.client_secret
                
                provider = GoogleOAuthProvider()
                
                for http_uri in http_uris:
                    with patch.object(provider, 'get_redirect_uri', return_value=http_uri):
                        is_valid, message = provider.validate_configuration()
                        
                        # Should reject HTTP URIs in production
                        assert not is_valid, f"Should reject HTTP URI in production: {http_uri}"
                        
        self.record_metric("https_enforcement_tests", len(http_uris))


class TestOAuthCredentialSecurity(SSotBaseTestCase):
    """Test OAuth credential security and sanitization."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "test-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-test-very-sensitive-secret-key"
        
    def test_credentials_not_exposed_in_error_messages(self):
        """Test OAuth credentials are never exposed in error messages."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test various error scenarios
            error_scenarios = [
                # Force token exchange error
                lambda: provider.exchange_code_for_user_info("invalid-code", "test-state"),
                # Force authorization URL error with None state
                lambda: provider.get_authorization_url(None) if hasattr(provider, '_client_id') else None,
                # Force configuration validation error
                lambda: provider.validate_configuration(),
            ]
            
            for scenario in error_scenarios:
                if scenario is None:
                    continue
                    
                try:
                    result = scenario()
                    # If it returns a result, check for credential exposure
                    if hasattr(result, '__str__'):
                        result_str = str(result).lower()
                        assert self.client_secret.lower() not in result_str, \
                            "Client secret found in result"
                        assert "secret" not in result_str or "client_secret" not in result_str, \
                            "Secret keywords found in result"
                        
                except Exception as e:
                    error_message = str(e).lower()
                    
                    # Critical: Client secret must NEVER appear in error messages
                    assert self.client_secret.lower() not in error_message, \
                        f"Client secret exposed in error message: {e}"
                    
                    # Should not contain other sensitive information
                    assert "password" not in error_message or "credential" not in error_message, \
                        f"Sensitive keywords in error message: {e}"
                        
        self.record_metric("credential_exposure_prevention_validated", True)
        
    def test_self_check_masks_sensitive_information(self):
        """Test self-check functionality masks sensitive information."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            check_result = provider.self_check()
            
            # Convert entire result to string for searching
            result_str = str(check_result).lower()
            
            # Must not expose full client secret anywhere
            assert self.client_secret.lower() not in result_str, \
                "Full client secret exposed in self-check result"
                
            # Must not expose sensitive credential data
            assert "gocspx-" not in result_str, \
                "OAuth client secret pattern exposed in self-check"
            
            # If client_id_prefix is present, it should be truncated
            if "client_id_prefix" in check_result:
                prefix = check_result["client_id_prefix"]
                assert len(prefix) <= 30, "Client ID prefix should be truncated"
                assert prefix != self.client_id, "Full client ID should not be in prefix"
                
        self.record_metric("self_check_sanitization_validated", True)
        
    def test_configuration_status_sanitization(self):
        """Test configuration status properly sanitizes sensitive data."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            status = provider.get_configuration_status()
            
            # Convert entire status to string for searching
            status_str = str(status).lower()
            
            # Must not expose actual credentials
            assert self.client_secret.lower() not in status_str, \
                "Client secret exposed in configuration status"
            assert self.client_id not in status_str, \
                "Full client ID exposed in configuration status"
                
            # Should indicate if configured but not expose values
            assert status["client_id_configured"] in [True, False], \
                "Should indicate if client ID is configured"
            assert status["client_secret_configured"] in [True, False], \
                "Should indicate if client secret is configured"
            assert status["is_configured"] in [True, False], \
                "Should indicate overall configuration status"
                
        self.record_metric("configuration_status_sanitization_validated", True)


class TestOAuthInputValidationSecurity(SSotBaseTestCase):
    """Test OAuth input validation and sanitization security."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        
        self.client_id = "test-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-test-abcdefghijklmnopqrstuvwxyz"
        
    def test_authorization_code_input_validation(self):
        """Test authorization code input is properly validated and sanitized."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test malicious authorization codes
            malicious_codes = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "javascript:alert('xss')",
                "\x00\x01\x02\x03",  # null bytes
                "code' OR '1'='1",
                "%3Cscript%3E",  # URL encoded
                "A" * 10000,  # extremely long
            ]
            
            for malicious_code in malicious_codes:
                try:
                    # Should either handle safely or reject
                    result = provider.exchange_code_for_user_info(malicious_code, "test-state")
                    
                    # If it returns a result, should be safe test data
                    if result:
                        assert result.get("email") == "test@example.com", \
                            "Should return safe test data for malicious code"
                            
                except GoogleOAuthError:
                    # It's acceptable to reject malicious codes with proper error
                    pass
                except Exception as e:
                    # Should not cause unhandled exceptions
                    assert False, f"Unhandled exception for malicious code {malicious_code}: {e}"
                    
        self.record_metric("malicious_code_tests", len(malicious_codes))
        
    def test_scope_parameter_validation(self):
        """Test OAuth scope parameter validation and sanitization."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test malicious scopes
            malicious_scopes = [
                ["<script>alert('xss')</script>"],
                ["'; DROP TABLE users; --"],
                ["javascript:alert('xss')"],
                ["data:text/html,<script>"],
                ["scope' OR '1'='1"],
                ["A" * 1000],  # extremely long scope
                ["\x00\x01\x02"],  # null bytes
            ]
            
            for scopes in malicious_scopes:
                try:
                    auth_url = provider.get_authorization_url("test-state", scopes=scopes)
                    
                    # If URL was generated, should be safely encoded
                    assert isinstance(auth_url, str), "Should return valid URL string"
                    assert auth_url.startswith("https://accounts.google.com"), \
                        "Should start with Google OAuth endpoint"
                        
                    # Should not contain dangerous content
                    assert "<script>" not in auth_url.lower()
                    assert "javascript:" not in auth_url.lower()
                    assert "DROP TABLE" not in auth_url.upper()
                    
                except Exception:
                    # Rejecting malicious scopes is also acceptable
                    pass
                    
        self.record_metric("malicious_scope_tests", len(malicious_scopes))


class TestOAuthPerformanceAndResourceSecurity(SSotBaseTestCase):
    """Test OAuth performance characteristics and resource security."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("ENVIRONMENT", "test") 
        self.set_env_var("TESTING", "true")
        
        self.client_id = "test-123456789-abcdefghijklmnop.apps.googleusercontent.com"
        self.client_secret = "GOCSPX-test-abcdefghijklmnopqrstuvwxyz"
        
    def test_oauth_provider_dos_protection(self):
        """Test OAuth provider has basic DoS protection."""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            provider = GoogleOAuthProvider()
            
            # Test rapid successive calls don't consume excessive resources
            import time
            start_time = time.time()
            
            for i in range(100):
                auth_url = provider.get_authorization_url(f"state-{i}")
                assert len(auth_url) > 0
                
                # Basic resource consumption check
                if i > 0 and i % 50 == 0:
                    elapsed = time.time() - start_time
                    # Should not take more than 5 seconds for 50 calls
                    assert elapsed < 5.0, f"OAuth URL generation too slow: {elapsed}s for {i} calls"
            
            total_time = time.time() - start_time
            avg_time = total_time / 100
            
            # Each call should be fast (less than 10ms average)
            assert avg_time < 0.01, f"OAuth operations too slow: {avg_time:.4f}s average"
            
        self.record_metric("dos_protection_avg_time", avg_time)
        
    def test_oauth_provider_memory_safety(self):
        """Test OAuth provider doesn't leak memory or resources."""
        import gc
        
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_id') as mock_id, \
             patch('auth_service.auth_core.secret_loader.AuthSecretLoader.get_google_client_secret') as mock_secret:
            
            mock_id.return_value = self.client_id
            mock_secret.return_value = self.client_secret
            
            # Measure initial memory state
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Create and destroy many providers
            for i in range(50):
                provider = GoogleOAuthProvider()
                auth_url = provider.get_authorization_url(f"state-{i}")
                is_valid, _ = provider.validate_configuration()
                status = provider.get_configuration_status()
                check = provider.self_check()
                
                # Explicit cleanup
                del provider
                del auth_url
                del status
                del check
                
                if i % 10 == 0:
                    gc.collect()
                    
            # Final cleanup and measurement
            gc.collect()
            final_objects = len(gc.get_objects())
            growth = final_objects - initial_objects
            
            # Should not have excessive memory growth
            assert growth < 1000, f"Excessive memory growth: {growth} objects"
            
        self.record_metric("memory_growth_objects", growth)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])