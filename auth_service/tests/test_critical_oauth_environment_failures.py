"""Critical OAuth Environment Variable Failures - Failing Tests
Tests that replicate missing OAuth environment variables found in staging logs.

CRITICAL OAUTH ENVIRONMENT ISSUES TO REPLICATE:
1. Missing OAUTH_HMAC_SECRET environment variable causing OAuth flow failures
2. Missing or invalid GOOGLE_CLIENT_ID causing OAuth initialization failures
3. Missing GOOGLE_CLIENT_SECRET causing OAuth token exchange failures  
4. Invalid OAuth redirect URI configuration causing authentication errors

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: OAuth authentication reliability for user onboarding
- Value Impact: Prevents complete authentication system failures in staging/production
- Strategic Impact: Ensures user authentication works for all customer segments
"""

import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.secret_loader import AuthSecretLoader
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


@env("staging")
@env_requires(services=["auth_service"], features=["oauth_configured"])
class TestCriticalOAuthEnvironmentFailures:
    """Test suite for OAuth environment variable failures found in staging."""
    
    def test_missing_oauth_hmac_secret_environment_variable(self):
        """FAILING TEST: Replicates missing OAUTH_HMAC_SECRET causing OAuth flow failures.
        
        This is a critical error where OAUTH_HMAC_SECRET is not set in staging,
        causing OAuth state validation to fail and preventing user authentication.
        """
        # Environment missing OAUTH_HMAC_SECRET
        missing_hmac_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLIENT_ID': 'test-client-id.googleusercontent.com',
            'GOOGLE_CLIENT_SECRET': 'test-client-secret',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long',
            'SERVICE_SECRET': 'test-service-secret-32-chars-long',
            'SERVICE_ID': 'test-service-id',
            'AUTH_FAST_TEST_MODE': 'false'
            # OAUTH_HMAC_SECRET is deliberately missing
        }
        
        with patch.dict(os.environ, missing_hmac_env, clear=True):
            # Remove OAUTH_HMAC_SECRET if it exists
            if 'OAUTH_HMAC_SECRET' in os.environ:
                del os.environ['OAUTH_HMAC_SECRET']
            
            # Try to get OAuth configuration - this should fail for staging
            try:
                # OAuth HMAC secret is required for secure state validation
                oauth_hmac_secret = os.getenv('OAUTH_HMAC_SECRET')
                
                if not oauth_hmac_secret and AuthConfig.get_environment() == 'staging':
                    # This should be detected as a critical configuration error
                    pytest.fail("Missing OAUTH_HMAC_SECRET not detected in staging environment")
                
                # If we get an empty secret in staging, that's a problem
                if AuthConfig.get_environment() == 'staging' and not oauth_hmac_secret:
                    pytest.fail(f"OAUTH_HMAC_SECRET is empty in staging: '{oauth_hmac_secret}'")
                
                logger.error(f"OAuth HMAC secret missing error not detected: '{oauth_hmac_secret}'")
                
            except Exception as e:
                # If an exception is raised, that might be the expected behavior
                if "OAUTH_HMAC_SECRET" in str(e):
                    logger.info(f"OAUTH_HMAC_SECRET correctly detected as missing: {e}")
                else:
                    # Re-raise if it's not related to the missing secret
                    raise
    
    def test_missing_google_client_id_environment_variable(self):
        """FAILING TEST: Tests missing GOOGLE_CLIENT_ID causing OAuth initialization failures.
        
        Without GOOGLE_CLIENT_ID, the OAuth flow cannot be initialized, preventing
        all Google-based authentication.
        """
        missing_client_id_env = {
            'ENVIRONMENT': 'staging',
            # GOOGLE_CLIENT_ID is deliberately missing
            'GOOGLE_CLIENT_SECRET': 'test-client-secret',
            'OAUTH_HMAC_SECRET': 'test-oauth-hmac-secret-32-chars',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, missing_client_id_env, clear=True):
            # Remove GOOGLE_CLIENT_ID if it exists
            if 'GOOGLE_CLIENT_ID' in os.environ:
                del os.environ['GOOGLE_CLIENT_ID']
            
            try:
                client_id = AuthConfig.get_google_client_id()
                
                # In staging, empty client ID should be detected as an error
                if AuthConfig.get_environment() == 'staging' and not client_id:
                    pytest.fail("Missing GOOGLE_CLIENT_ID not detected in staging environment")
                
                # Should not return placeholder values
                if client_id in ['', 'test-client-id', 'GOOGLE_CLIENT_ID']:
                    pytest.fail(f"Invalid GOOGLE_CLIENT_ID placeholder returned: '{client_id}'")
                
                logger.error(f"Google Client ID missing error not detected: '{client_id}'")
                
            except ValueError as e:
                # Expected behavior - should raise ValueError for missing required config
                if "GOOGLE_CLIENT_ID" in str(e) or "client" in str(e).lower():
                    logger.info(f"GOOGLE_CLIENT_ID correctly detected as missing: {e}")
                else:
                    pytest.fail(f"Unexpected error for missing GOOGLE_CLIENT_ID: {e}")
    
    def test_missing_google_client_secret_environment_variable(self):
        """FAILING TEST: Tests missing GOOGLE_CLIENT_SECRET causing OAuth token exchange failures.
        
        Without GOOGLE_CLIENT_SECRET, OAuth authorization codes cannot be exchanged
        for access tokens, breaking the authentication flow.
        """
        missing_client_secret_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLIENT_ID': 'test-client-id.googleusercontent.com',
            # GOOGLE_CLIENT_SECRET is deliberately missing
            'OAUTH_HMAC_SECRET': 'test-oauth-hmac-secret-32-chars',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, missing_client_secret_env, clear=True):
            # Remove GOOGLE_CLIENT_SECRET if it exists
            if 'GOOGLE_CLIENT_SECRET' in os.environ:
                del os.environ['GOOGLE_CLIENT_SECRET']
            
            try:
                client_secret = AuthConfig.get_google_client_secret()
                
                # In staging, empty client secret should be detected as an error
                if AuthConfig.get_environment() == 'staging' and not client_secret:
                    pytest.fail("Missing GOOGLE_CLIENT_SECRET not detected in staging environment")
                
                # Should not return placeholder values
                if client_secret in ['', 'test-secret', 'GOOGLE_CLIENT_SECRET']:
                    pytest.fail(f"Invalid GOOGLE_CLIENT_SECRET placeholder returned: '{client_secret}'")
                
                logger.error(f"Google Client Secret missing error not detected: '{client_secret}'")
                
            except ValueError as e:
                # Expected behavior - should raise ValueError for missing required config
                if "GOOGLE_CLIENT_SECRET" in str(e) or "secret" in str(e).lower():
                    logger.info(f"GOOGLE_CLIENT_SECRET correctly detected as missing: {e}")
                else:
                    pytest.fail(f"Unexpected error for missing GOOGLE_CLIENT_SECRET: {e}")
    
    def test_oauth_environment_variables_validation_in_staging(self):
        """FAILING TEST: Tests comprehensive OAuth environment validation in staging.
        
        All OAuth-related environment variables should be validated together
        to ensure a complete OAuth configuration.
        """
        # Test various incomplete OAuth configurations
        incomplete_oauth_configs = [
            {
                'name': 'All OAuth vars missing',
                'env': {'ENVIRONMENT': 'staging', 'AUTH_FAST_TEST_MODE': 'false'}
            },
            {
                'name': 'Only client ID',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLIENT_ID': 'test-client-id.googleusercontent.com',
                    'AUTH_FAST_TEST_MODE': 'false'
                }
            },
            {
                'name': 'Missing HMAC secret',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLIENT_ID': 'test-client-id.googleusercontent.com',
                    'GOOGLE_CLIENT_SECRET': 'test-client-secret',
                    'AUTH_FAST_TEST_MODE': 'false'
                    # OAUTH_HMAC_SECRET missing
                }
            },
            {
                'name': 'Empty values',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLIENT_ID': '',
                    'GOOGLE_CLIENT_SECRET': '',
                    'OAUTH_HMAC_SECRET': '',
                    'AUTH_FAST_TEST_MODE': 'false'
                }
            }
        ]
        
        for config in incomplete_oauth_configs:
            with patch.dict(os.environ, config['env'], clear=True):
                logger.info(f"Testing OAuth config: {config['name']}")
                
                # Try to get all OAuth configuration values
                errors = []
                
                try:
                    client_id = AuthConfig.get_google_client_id()
                    if not client_id:
                        errors.append(f"Empty GOOGLE_CLIENT_ID: '{client_id}'")
                except Exception as e:
                    errors.append(f"GOOGLE_CLIENT_ID error: {e}")
                
                try:
                    client_secret = AuthConfig.get_google_client_secret()
                    if not client_secret:
                        errors.append(f"Empty GOOGLE_CLIENT_SECRET: '{client_secret}'")
                except Exception as e:
                    errors.append(f"GOOGLE_CLIENT_SECRET error: {e}")
                
                try:
                    oauth_hmac_secret = os.getenv('OAUTH_HMAC_SECRET')
                    if not oauth_hmac_secret:
                        errors.append(f"Empty OAUTH_HMAC_SECRET: '{oauth_hmac_secret}'")
                except Exception as e:
                    errors.append(f"OAUTH_HMAC_SECRET error: {e}")
                
                # In staging, incomplete OAuth config should be detected
                if AuthConfig.get_environment() == 'staging' and errors:
                    logger.error(f"OAuth validation errors for {config['name']}: {errors}")
                    
                    # If we have errors but no exception was raised, validation is insufficient
                    if len(errors) > 0:
                        pytest.fail(f"Incomplete OAuth config '{config['name']}' not properly validated: {errors}")


@env("staging")
class TestOAuthEnvironmentVariableFormatValidation:
    """Test OAuth environment variable format validation."""
    
    def test_google_client_id_format_validation(self):
        """FAILING TEST: Tests Google Client ID format validation failures.
        
        Invalid Client ID formats should be detected to prevent OAuth errors.
        """
        # Test various invalid Client ID formats
        invalid_client_ids = [
            'invalid-client-id',              # Missing .googleusercontent.com
            'test',                           # Too short
            'client-id.apps.google.com',      # Wrong Google domain
            'client-id.example.com',          # Wrong domain
            'client-id@googleusercontent.com', # @ instead of .
            '123',                            # Only numbers
            'client-id.googleusercontent.co',  # Missing 'm'
            '',                               # Empty
            'client-id..googleusercontent.com', # Double dots
            'client-id.googleusercontent.com.malicious.com', # Domain hijacking attempt
        ]
        
        for invalid_client_id in invalid_client_ids:
            test_env = {
                'ENVIRONMENT': 'staging',
                'GOOGLE_CLIENT_ID': invalid_client_id,
                'GOOGLE_CLIENT_SECRET': 'valid-client-secret',
                'OAUTH_HMAC_SECRET': 'valid-oauth-hmac-secret-32-chars',
                'AUTH_FAST_TEST_MODE': 'false'
            }
            
            with patch.dict(os.environ, test_env):
                try:
                    client_id = AuthConfig.get_google_client_id()
                    
                    # If we get back the invalid ID without validation, that's a problem
                    if client_id == invalid_client_id and invalid_client_id != '':
                        pytest.fail(f"Invalid GOOGLE_CLIENT_ID format not detected: '{invalid_client_id}'")
                    
                    # Empty client ID should be detected
                    if not client_id and AuthConfig.get_environment() == 'staging':
                        pytest.fail(f"Empty GOOGLE_CLIENT_ID not detected: '{invalid_client_id}' -> '{client_id}'")
                    
                    logger.warning(f"Client ID format test: '{invalid_client_id}' -> '{client_id}'")
                    
                except ValueError as e:
                    # Expected for invalid formats
                    logger.info(f"Correctly rejected invalid Client ID '{invalid_client_id}': {e}")
    
    def test_oauth_hmac_secret_length_validation(self):
        """FAILING TEST: Tests OAUTH_HMAC_SECRET length validation failures.
        
        HMAC secrets should be long enough to be secure.
        """
        # Test various HMAC secret lengths that might be too short
        weak_hmac_secrets = [
            'short',                    # Too short
            '12345678',                 # 8 chars - too short
            'a' * 16,                   # 16 chars - might be too short
            'weak-secret',              # Predictable
            '1234567890123456',         # Only numbers
            'abcdefghijklmnop',         # Only letters
            '',                         # Empty
            'test',                     # Development value
            'hmac-secret',              # Generic name
        ]
        
        for weak_secret in weak_hmac_secrets:
            test_env = {
                'ENVIRONMENT': 'staging',
                'GOOGLE_CLIENT_ID': 'valid-client-id.googleusercontent.com',
                'GOOGLE_CLIENT_SECRET': 'valid-client-secret',
                'OAUTH_HMAC_SECRET': weak_secret,
                'AUTH_FAST_TEST_MODE': 'false'
            }
            
            with patch.dict(os.environ, test_env):
                oauth_hmac_secret = os.getenv('OAUTH_HMAC_SECRET')
                
                # Check if weak secrets are being used without validation
                if oauth_hmac_secret == weak_secret:
                    # In staging, weak secrets should be detected
                    if len(weak_secret) < 32:  # Minimum secure length
                        pytest.fail(f"Weak OAUTH_HMAC_SECRET not detected: '{weak_secret}' (length: {len(weak_secret)})")
                    
                    # Predictable secrets should be detected
                    if weak_secret in ['test', 'hmac-secret', 'weak-secret']:
                        pytest.fail(f"Predictable OAUTH_HMAC_SECRET not detected: '{weak_secret}'")
                
                logger.warning(f"HMAC secret test: '{weak_secret}' (length: {len(weak_secret)})")
    
    def test_oauth_redirect_uri_configuration_validation(self):
        """FAILING TEST: Tests OAuth redirect URI configuration validation.
        
        Invalid redirect URIs can cause OAuth flow failures.
        """
        # Test environment with potentially problematic redirect URI configuration
        redirect_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLIENT_ID': 'valid-client-id.googleusercontent.com',
            'GOOGLE_CLIENT_SECRET': 'valid-client-secret',
            'OAUTH_HMAC_SECRET': 'valid-oauth-hmac-secret-32-chars-long',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, redirect_env):
            # Test redirect URI construction
            auth_service_url = AuthConfig.get_auth_service_url()
            
            # In staging, should use HTTPS URLs
            if not auth_service_url.startswith('https://'):
                pytest.fail(f"Staging auth service URL should use HTTPS: {auth_service_url}")
            
            # Should not use localhost in staging
            if 'localhost' in auth_service_url and AuthConfig.get_environment() == 'staging':
                pytest.fail(f"Staging auth service URL should not use localhost: {auth_service_url}")
            
            # Construct redirect URI (this is typically done in OAuth routes)
            redirect_uri = f"{auth_service_url}/auth/google/callback"
            
            # Validate redirect URI format
            if not redirect_uri.startswith('https://'):
                pytest.fail(f"OAuth redirect URI should use HTTPS in staging: {redirect_uri}")
            
            # Should not contain dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', '\n', '\r', '\t']
            for char in dangerous_chars:
                if char in redirect_uri:
                    pytest.fail(f"OAuth redirect URI contains dangerous character '{char}': {redirect_uri}")
            
            logger.info(f"OAuth redirect URI validation test: {redirect_uri}")


@env("staging")
class TestOAuthSecretLoaderIntegration:
    """Test OAuth secret loading integration failures."""
    
    def test_auth_secret_loader_oauth_integration(self):
        """FAILING TEST: Tests AuthSecretLoader integration with OAuth environment variables.
        
        The secret loader should properly handle missing OAuth secrets.
        """
        oauth_secrets_env = {
            'ENVIRONMENT': 'staging',
            'AUTH_FAST_TEST_MODE': 'false'
            # All OAuth secrets missing
        }
        
        with patch.dict(os.environ, oauth_secrets_env, clear=True):
            # Test each secret loader method
            oauth_methods = [
                ('get_google_client_id', 'GOOGLE_CLIENT_ID'),
                ('get_google_client_secret', 'GOOGLE_CLIENT_SECRET'),
                ('get_jwt_secret', 'JWT_SECRET_KEY'),
            ]
            
            for method_name, env_var in oauth_methods:
                if hasattr(AuthSecretLoader, method_name):
                    try:
                        method = getattr(AuthSecretLoader, method_name)
                        result = method()
                        
                        # In staging, empty results should be detected
                        if not result and AuthConfig.get_environment() == 'staging':
                            pytest.fail(f"AuthSecretLoader.{method_name}() returned empty value in staging")
                        
                        # Should not return placeholder values
                        if result in ['test', 'placeholder', env_var.lower()]:
                            pytest.fail(f"AuthSecretLoader.{method_name}() returned placeholder: '{result}'")
                        
                        logger.warning(f"Secret loader {method_name}: '{result}'")
                        
                    except ValueError as e:
                        # Expected for missing secrets in staging
                        if env_var in str(e) or method_name.split('_')[-1] in str(e).lower():
                            logger.info(f"AuthSecretLoader correctly detected missing {env_var}: {e}")
                        else:
                            pytest.fail(f"Unexpected error from AuthSecretLoader.{method_name}(): {e}")
                    except Exception as e:
                        logger.error(f"Unexpected exception from AuthSecretLoader.{method_name}(): {e}")
                        raise


# Mark all tests as staging-specific OAuth integration tests
pytestmark = [pytest.mark.integration, pytest.mark.staging, pytest.mark.oauth]