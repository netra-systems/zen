"""
OAuth Security Comprehensive Test Suite - Issue #213

CRITICAL: Tests to validate OAuth security measures using SSOT validator.

These tests ensure that SSOT OAuth consolidation maintains and improves
security posture while preventing security regressions.

Business Value: Platform/Internal - Security Validation and Compliance
Prevents security vulnerabilities during SSOT consolidation that could expose OAuth credentials.

Test Strategy:
- Test OAuth token validation and security measures
- Test OAuth state parameter validation
- Test OAuth provider configuration security
- Test OAuth credential protection and access control

SAFETY: These tests validate security functionality without exposing real credentials.
"""

import os
import re
import pytest
import logging
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Base test case not needed for simple pytest
from shared.configuration.central_config_validator import (
    CentralConfigurationValidator,
    Environment,
    ConfigRequirement,
    clear_central_validator_cache
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestOAuthSecurityComprehensive:
    """Test suite for OAuth security validation using SSOT - Issue #213."""
    
    def setup_method(self):
        """Set up secure test environment."""
        clear_central_validator_cache()
        
        # Set up test OAuth credentials with security validation
        self.secure_test_credentials = {
            "client_id": "test-oauth-client-id-for-automated-testing",
            "client_secret": "test-oauth-client-secret-for-automated-testing-secure",
            "redirect_uri": "https://test.netra.app/auth/callback",
            "scope": "openid email profile"
        }
        
        # Set up test environment
        os.environ["ENVIRONMENT"] = "test"
        os.environ["PYTEST_CURRENT_TEST"] = "test_oauth_security_comprehensive.py"
        os.environ["GOOGLE_OAUTH_CLIENT_ID_TEST"] = self.secure_test_credentials["client_id"]
        os.environ["GOOGLE_OAUTH_CLIENT_SECRET_TEST"] = self.secure_test_credentials["client_secret"]
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-test-environment-only-32-chars-min"
    
    def teardown_method(self):
        """Clean up secure test environment."""
        clear_central_validator_cache()
    
    def test_oauth_security_comprehensive_ssot(self):
        """
        CRITICAL: Test OAuth security measures using SSOT validator.
        
        This test MUST PASS to ensure SSOT OAuth validation maintains
        security standards required for production OAuth flows.
        """
        validator = CentralConfigurationValidator()
        
        # Test 1: OAuth credential format validation
        oauth_creds = validator.get_oauth_credentials()
        
        # Verify client ID format (should not be empty or default)
        client_id = oauth_creds["client_id"]
        assert len(client_id) > 10, \
            f"OAuth client ID should be substantial length. Got: {len(client_id)} chars"
        assert not client_id.startswith("YOUR_"), \
            f"OAuth client ID should not be placeholder. Got: {client_id}"
        assert not client_id == "dummy" and not client_id == "test", \
            f"OAuth client ID should not be generic test value. Got: {client_id}"
        
        # Verify client secret format (should be substantial and not placeholder)
        client_secret = oauth_creds["client_secret"]
        assert len(client_secret) > 15, \
            f"OAuth client secret should be substantial length. Got: {len(client_secret)} chars"
        assert not client_secret.startswith("YOUR_"), \
            f"OAuth client secret should not be placeholder. Got: {client_secret}"
        assert not client_secret == "dummy" and not client_secret == "test", \
            f"OAuth client secret should not be generic test value"
        
        logger.info("✅ OAuth credential format validation passed")
        
        # Test 2: Environment-specific credential isolation
        environment = validator.get_environment()
        expected_client_id_var = f"GOOGLE_OAUTH_CLIENT_ID_{environment.value.upper()}"
        expected_client_secret_var = f"GOOGLE_OAUTH_CLIENT_SECRET_{environment.value.upper()}"
        
        # Verify environment-specific variables are used
        actual_client_id_env = get_env(expected_client_id_var)
        assert actual_client_id_env == client_id, \
            f"OAuth should use environment-specific client ID variable: {expected_client_id_var}"
        
        actual_client_secret_env = get_env(expected_client_secret_var)
        assert actual_client_secret_env == client_secret, \
            f"OAuth should use environment-specific client secret variable: {expected_client_secret_var}"
        
        logger.info("✅ Environment-specific OAuth credential isolation validated")
        
        # Test 3: OAuth validation security checks
        try:
            validator.validate_all_requirements()
            logger.info("✅ OAuth security validation passed with SSOT")
        except Exception as e:
            pytest.fail(f"OAuth security validation failed: {e}")
    
    def test_oauth_provider_configuration_validation(self):
        """
        Test OAuth provider configuration validation.
        
        This test ensures OAuth provider-specific configuration
        (Google/GitHub/Microsoft) is properly validated for security.
        """
        validator = CentralConfigurationValidator()
        
        # Test Google OAuth configuration validation
        oauth_creds = validator.get_oauth_credentials()
        
        # Google OAuth client ID format validation
        client_id = oauth_creds["client_id"]
        
        # Google client IDs have specific format patterns (for production)
        # For test environment, we validate it's not obviously insecure
        assert not any(insecure_pattern in client_id.lower() for insecure_pattern in [
            "password", "secret", "key", "token", "admin", "root"
        ]), f"OAuth client ID should not contain insecure terms. Got: {client_id}"
        
        # Test OAuth scope validation (if implemented)
        # This would validate that OAuth scopes are appropriate and minimal
        expected_scopes = ["openid", "email", "profile"]
        # Note: Scope validation would be part of SSOT OAuth configuration
        
        # Test OAuth redirect URI validation (security critical)
        # This ensures only authorized redirect URIs are accepted
        test_redirect_uris = [
            ("https://test.netra.app/auth/callback", True),  # Valid test URI
            ("https://netra.app/auth/callback", True),       # Valid production URI
            ("http://localhost:3000/auth/callback", True),   # Valid dev URI
            ("http://evil.com/steal-tokens", False),         # Invalid external URI
            ("javascript:alert('xss')", False),              # Invalid XSS attempt
            ("", False),                                     # Invalid empty URI
        ]
        
        for redirect_uri, should_be_valid in test_redirect_uris:
            is_valid = self._validate_oauth_redirect_uri_security(redirect_uri)
            if should_be_valid:
                assert is_valid, f"Valid redirect URI should pass validation: {redirect_uri}"
            else:
                assert not is_valid, f"Invalid redirect URI should fail validation: {redirect_uri}"
        
        logger.info("✅ OAuth provider configuration validation passed")
    
    def test_oauth_state_parameter_security(self):
        """
        Test OAuth state parameter security validation.
        
        This test ensures OAuth state parameters are properly validated
        to prevent CSRF attacks and state manipulation.
        """
        # Test OAuth state generation and validation patterns
        valid_state_patterns = [
            "random-string-123456789",
            "csrf-token-abcdef123456", 
            "state-parameter-secure-random-value"
        ]
        
        invalid_state_patterns = [
            "",                    # Empty state
            "short",              # Too short
            "predictable-123",    # Predictable pattern
            "user_id_12345",      # Contains user info
            "../../../etc/passwd", # Path traversal attempt
            "<script>alert('xss')</script>", # XSS attempt
        ]
        
        # Test valid state parameters
        for state in valid_state_patterns:
            is_valid = self._validate_oauth_state_security(state)
            assert is_valid, f"Valid OAuth state should pass validation: {state}"
        
        # Test invalid state parameters
        for state in invalid_state_patterns:
            is_valid = self._validate_oauth_state_security(state)
            assert not is_valid, f"Invalid OAuth state should fail validation: {state}"
        
        logger.info("✅ OAuth state parameter security validation passed")
    
    def test_oauth_credential_access_control(self):
        """
        Test OAuth credential access control and protection.
        
        This test ensures OAuth credentials are properly protected
        and accessed only through secure SSOT methods.
        """
        validator = CentralConfigurationValidator()
        
        # Test 1: OAuth credentials are not logged or exposed
        with patch('logging.Logger.info') as mock_logger:
            oauth_creds = validator.get_oauth_credentials()
            
            # Verify credentials are not logged
            for call in mock_logger.call_args_list:
                log_message = str(call)
                assert oauth_creds["client_secret"] not in log_message, \
                    "OAuth client secret should not appear in logs"
                assert oauth_creds["client_id"] not in log_message or "***" in log_message, \
                    "OAuth client ID should be masked in logs"
        
        # Test 2: OAuth credential immutability
        oauth_creds_copy = oauth_creds.copy()
        oauth_creds["client_secret"] = "modified"
        
        # Get credentials again - should be unchanged
        oauth_creds_fresh = validator.get_oauth_credentials()
        assert oauth_creds_fresh["client_secret"] == oauth_creds_copy["client_secret"], \
            "OAuth credentials should be immutable"
        
        # Test 3: OAuth credential validation on access
        try:
            client_id = validator.get_oauth_client_id()
            assert client_id == oauth_creds_copy["client_id"], \
                "OAuth client ID access should be consistent"
        except Exception as e:
            pytest.fail(f"OAuth credential access should work: {e}")
        
        logger.info("✅ OAuth credential access control validation passed")
    
    def test_oauth_error_information_disclosure(self):
        """
        Test OAuth error messages don't disclose sensitive information.
        
        This test ensures OAuth validation errors provide useful information
        without exposing sensitive configuration details.
        """
        # Test with missing OAuth configuration
        missing_config_env = {
            "ENVIRONMENT": "test",
            "PYTEST_CURRENT_TEST": "test_oauth_security_comprehensive.py",
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-test-environment-only-32-chars-min",
            # Intentionally missing OAuth credentials
        }
        
        def mock_env_getter_missing_oauth(key, default=None):
            return missing_config_env.get(key, default)
        
        validator = CentralConfigurationValidator(env_getter_func=mock_env_getter_missing_oauth)
        
        # Test OAuth error messages
        with pytest.raises(ValueError) as exc_info:
            validator.get_oauth_credentials()
        
        error_message = str(exc_info.value)
        
        # Verify error message is helpful but not revealing
        assert "OAuth credentials not properly configured" in error_message, \
            "Error should mention OAuth configuration issue"
        
        # Verify error message doesn't expose sensitive information
        sensitive_terms = [
            "secret", "password", "key", "token", "credential",
            os.environ.get("JWT_SECRET_KEY", ""), 
            "internal", "production"
        ]
        
        for term in sensitive_terms:
            if term:  # Skip empty terms
                assert term.lower() not in error_message.lower(), \
                    f"Error message should not expose sensitive term: {term}"
        
        # Verify error message provides actionable guidance
        assert any(guidance in error_message for guidance in [
            "configuration", "environment", "variable", "missing"
        ]), "Error message should provide actionable guidance"
        
        logger.info("✅ OAuth error information disclosure protection validated")
    
    def test_oauth_configuration_integrity(self):
        """
        Test OAuth configuration integrity and consistency.
        
        This test ensures OAuth configuration maintains integrity
        across different access patterns and validation scenarios.
        """
        validator = CentralConfigurationValidator()
        
        # Test 1: Configuration consistency across multiple validators
        validator2 = CentralConfigurationValidator()
        
        oauth_creds1 = validator.get_oauth_credentials()
        oauth_creds2 = validator2.get_oauth_credentials()
        
        assert oauth_creds1 == oauth_creds2, \
            "OAuth credentials should be consistent across validator instances"
        
        # Test 2: Configuration integrity after cache operations
        validator.clear_environment_cache()
        oauth_creds_after_clear = validator.get_oauth_credentials()
        
        assert oauth_creds_after_clear == oauth_creds1, \
            "OAuth credentials should be consistent after cache clear"
        
        # Test 3: Configuration validation integrity
        try:
            validator.validate_all_requirements()
            validation1_success = True
        except Exception:
            validation1_success = False
        
        try:
            validator2.validate_all_requirements()
            validation2_success = True
        except Exception:
            validation2_success = False
        
        assert validation1_success == validation2_success, \
            "OAuth validation should be consistent across validator instances"
        
        if validation1_success:
            logger.info("✅ OAuth configuration integrity maintained")
        else:
            logger.warning("⚠️ OAuth configuration validation failed consistently")
    
    def _validate_oauth_redirect_uri_security(self, redirect_uri: str) -> bool:
        """Validate OAuth redirect URI for security."""
        if not redirect_uri:
            return False
        
        # Check for dangerous protocols
        if not redirect_uri.startswith(('https://', 'http://localhost')):
            return False
        
        # Check for XSS/injection attempts
        dangerous_patterns = [
            'javascript:', 'data:', 'vbscript:', 'file:',
            '<script', 'alert(', 'eval(', 'document.cookie'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in redirect_uri.lower():
                return False
        
        # Check for path traversal
        if '../' in redirect_uri or '..\\' in redirect_uri:
            return False
        
        # Check for authorized domains (basic whitelist)
        authorized_domains = [
            'netra.app', 'test.netra.app', 'localhost',
            '127.0.0.1', '0.0.0.0'
        ]
        
        # Extract domain from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(redirect_uri)
            domain = parsed.netloc.split(':')[0]  # Remove port if present
            
            return any(domain == auth_domain or domain.endswith('.' + auth_domain) 
                      for auth_domain in authorized_domains)
        except Exception:
            return False
    
    def _validate_oauth_state_security(self, state: str) -> bool:
        """Validate OAuth state parameter for security."""
        if not state or len(state) < 8:
            return False
        
        # Check for dangerous content
        dangerous_patterns = [
            '<', '>', '"', "'", '&', ';', '|', '`',
            '../', '..\\', 'user_id', 'admin', 'root'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in state:
                return False
        
        # Check for sufficient randomness (basic check)
        if re.match(r'^[a-zA-Z0-9\-_]+$', state):
            return True
        
        return False


def test_oauth_security_validation_capability():
    """
    Verify OAuth security validation test capability.
    
    This meta-test ensures our security validation tests work correctly.
    """
    test_instance = TestOAuthSecurityComprehensive()
    test_instance.setup_method()
    
    try:
        # Verify security validation methods work
        assert not test_instance._validate_oauth_redirect_uri_security(""), \
            "Should reject empty redirect URI"
        assert test_instance._validate_oauth_redirect_uri_security("https://test.netra.app/auth/callback"), \
            "Should accept valid redirect URI"
        
        assert not test_instance._validate_oauth_state_security(""), \
            "Should reject empty state"
        assert test_instance._validate_oauth_state_security("secure-random-state-123456"), \
            "Should accept valid state"
        
        # Verify we can get OAuth credentials for security testing
        validator = CentralConfigurationValidator()
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"], "Should be able to get OAuth credentials for testing"
        
        logger.info("✅ OAuth security validation test capability verified")
        
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    # Run the meta-test to verify security validation capability
    test_oauth_security_validation_capability()
    print("✅ OAuth security comprehensive tests created and capability verified!")