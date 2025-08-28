#!/usr/bin/env python3
"""
OAuth Configuration Missing Staging Regression Tests

Tests to replicate OAuth configuration issues found in GCP staging audit:
- Missing GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
- OAuth authentication functionality broken in staging
- Service initialization failing due to missing OAuth credentials

Business Value: Prevents user authentication failures costing $75K+ MRR
Critical for user login and Google OAuth integration.

Root Cause from Staging Audit:
- GOOGLE_OAUTH_CLIENT_ID_STAGING and GOOGLE_OAUTH_CLIENT_SECRET_STAGING not configured
- Auth service fails to initialize OAuth providers without proper credentials
- Users cannot login via Google OAuth in staging environment

These tests will FAIL initially to confirm the issues exist, then PASS after fixes.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

from auth_service.auth_core.secret_loader import SecretLoader
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider


@pytest.mark.staging
@pytest.mark.critical
class TestOAuthConfigurationMissingRegression:
    """Tests that replicate OAuth configuration issues from staging audit"""

    def test_google_oauth_client_id_missing_staging_regression(self):
        """
        REGRESSION TEST: GOOGLE_OAUTH_CLIENT_ID_STAGING missing in staging
        
        This test should FAIL initially to confirm staging OAuth config is missing.
        Root cause: GOOGLE_OAUTH_CLIENT_ID_STAGING not set in staging environment.
        
        Expected failure: OAuth client ID not available in staging
        """
        # Arrange - Simulate staging environment without OAuth client ID
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            # Remove OAuth client ID if it exists
            staging_env = dict(os.environ)
            staging_env.pop('GOOGLE_OAUTH_CLIENT_ID_STAGING', None)
            staging_env.pop('GOOGLE_CLIENT_ID', None)  # Remove fallback too
            
            with patch.dict(os.environ, staging_env, clear=True):
                # Act & Assert - OAuth initialization should fail
                try:
                    secret_loader = SecretLoader()
                    client_id = secret_loader.load_google_oauth_client_id()
                    
                    # This should FAIL - client ID should not be available
                    if client_id is None or client_id == "":
                        pytest.fail("OAuth client ID missing in staging as expected (this confirms the bug)")
                    else:
                        # If we get here, the test passes (bug is fixed)
                        assert len(client_id) > 20, "OAuth client ID should be valid length"
                        assert client_id.endswith('.apps.googleusercontent.com'), "Invalid OAuth client ID format"
                        
                except (KeyError, ValueError, AttributeError) as e:
                    # Expected failure - confirms the staging issue exists
                    pytest.fail(f"OAuth client ID configuration missing in staging: {e}")

    def test_google_oauth_client_secret_missing_staging_regression(self):
        """
        REGRESSION TEST: GOOGLE_OAUTH_CLIENT_SECRET_STAGING missing in staging
        
        This test should FAIL initially to confirm staging OAuth secret is missing.
        Root cause: GOOGLE_OAUTH_CLIENT_SECRET_STAGING not set in staging environment.
        
        Expected failure: OAuth client secret not available in staging
        """
        # Arrange - Simulate staging environment without OAuth client secret
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            # Remove OAuth client secret if it exists
            staging_env = dict(os.environ)
            staging_env.pop('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', None)
            staging_env.pop('GOOGLE_CLIENT_SECRET', None)  # Remove fallback too
            
            with patch.dict(os.environ, staging_env, clear=True):
                # Act & Assert - OAuth secret loading should fail
                try:
                    secret_loader = SecretLoader()
                    client_secret = secret_loader.load_google_oauth_client_secret()
                    
                    # This should FAIL - client secret should not be available
                    if client_secret is None or client_secret == "":
                        pytest.fail("OAuth client secret missing in staging as expected (this confirms the bug)")
                    else:
                        # If we get here, the test passes (bug is fixed)
                        assert len(client_secret) > 10, "OAuth client secret should be valid length"
                        
                except (KeyError, ValueError, AttributeError) as e:
                    # Expected failure - confirms the staging issue exists
                    pytest.fail(f"OAuth client secret configuration missing in staging: {e}")

    def test_oauth_provider_initialization_failure_regression(self):
        """
        REGRESSION TEST: OAuth provider fails to initialize without credentials
        
        This test should FAIL initially to confirm OAuth provider initialization issues.
        Root cause: GoogleOAuthProvider cannot initialize without client credentials.
        
        Expected failure: OAuth provider initialization throws error
        """
        # Arrange - Mock missing OAuth credentials
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            # Remove all OAuth credentials
            clean_env = {k: v for k, v in os.environ.items() 
                        if not k.startswith('GOOGLE_OAUTH_CLIENT') and not k.startswith('GOOGLE_CLIENT')}
            
            with patch.dict(os.environ, clean_env, clear=True):
                # Act & Assert - OAuth provider initialization should fail
                try:
                    provider = GoogleOAuthProvider()
                    
                    # This should FAIL - provider should not initialize without credentials
                    assert provider.client_id is not None, "OAuth provider should not initialize without client ID"
                    assert provider.client_secret is not None, "OAuth provider should not initialize without client secret"
                    
                except (ValueError, KeyError, AttributeError, TypeError) as e:
                    # Expected failure - confirms OAuth provider cannot initialize
                    pytest.fail(f"OAuth provider initialization fails without credentials: {e}")

    def test_oauth_redirect_uri_configuration_missing_regression(self):
        """
        REGRESSION TEST: OAuth redirect URI not configured for staging
        
        This test should FAIL initially if redirect URI configuration is missing.
        Root cause: OAuth redirect URI not set for staging environment.
        
        Expected failure: OAuth redirect URI missing or incorrect for staging
        """
        # Arrange - Check OAuth redirect URI configuration
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test-client-id',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test-client-secret'
        }, clear=False):
            
            # Act & Assert - Check redirect URI configuration
            try:
                provider = GoogleOAuthProvider()
                redirect_uri = provider.get_redirect_uri()
                
                # This should FAIL if redirect URI is not configured for staging
                if redirect_uri is None:
                    pytest.fail("OAuth redirect URI missing for staging")
                
                # Validate redirect URI format for staging
                expected_staging_domain = "netra-auth-service"  # Expected staging service name
                if expected_staging_domain not in redirect_uri:
                    pytest.fail(f"OAuth redirect URI incorrect for staging: {redirect_uri}")
                    
                if not redirect_uri.startswith('https://'):
                    pytest.fail(f"OAuth redirect URI should use HTTPS in staging: {redirect_uri}")
                    
            except AttributeError:
                # Expected failure - get_redirect_uri method doesn't exist
                pytest.fail("OAuth provider missing redirect URI configuration method")

    def test_oauth_environment_specific_configuration_regression(self):
        """
        REGRESSION TEST: OAuth configuration not environment-aware
        
        This test should FAIL initially if OAuth config doesn't adapt to environment.
        Root cause: OAuth configuration hardcoded instead of environment-specific.
        
        Expected failure: Same OAuth config used across all environments
        """
        # Arrange - Test different environments
        environments_to_test = [
            {
                'env': 'staging',
                'expected_client_id_key': 'GOOGLE_OAUTH_CLIENT_ID_STAGING',
                'expected_secret_key': 'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'
            },
            {
                'env': 'production', 
                'expected_client_id_key': 'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
                'expected_secret_key': 'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION'
            },
            {
                'env': 'development',
                'expected_client_id_key': 'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 
                'expected_secret_key': 'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT'
            }
        ]
        
        # Act & Assert - Test environment-specific configuration
        configuration_failures = []
        
        for env_config in environments_to_test:
            env_name = env_config['env']
            expected_client_id_key = env_config['expected_client_id_key']
            expected_secret_key = env_config['expected_secret_key']
            
            with patch.dict(os.environ, {
                'ENVIRONMENT': env_name,
                expected_client_id_key: f'client-id-{env_name}',
                expected_secret_key: f'client-secret-{env_name}'
            }, clear=False):
                
                try:
                    secret_loader = SecretLoader()
                    
                    # Check if loader uses environment-specific keys
                    client_id = secret_loader.load_google_oauth_client_id()
                    client_secret = secret_loader.load_google_oauth_client_secret()
                    
                    # This should FAIL if not environment-specific
                    if client_id != f'client-id-{env_name}':
                        configuration_failures.append(
                            f"Environment {env_name}: wrong client ID (got {client_id}, expected client-id-{env_name})")
                    
                    if client_secret != f'client-secret-{env_name}':
                        configuration_failures.append(
                            f"Environment {env_name}: wrong client secret")
                            
                except (KeyError, ValueError, AttributeError) as e:
                    configuration_failures.append(f"Environment {env_name}: {e}")
        
        # This should FAIL if configuration is not environment-aware
        if configuration_failures:
            pytest.fail(f"OAuth configuration not environment-specific: {configuration_failures}")


@pytest.mark.staging
@pytest.mark.critical
class TestOAuthServiceIntegrationRegression:
    """Tests OAuth service integration failures due to missing configuration"""

    def test_auth_service_oauth_providers_empty_regression(self):
        """
        REGRESSION TEST: Auth service OAuth providers list empty in staging
        
        This test should FAIL initially if OAuth providers are not initialized.
        Root cause: Auth service health check shows empty OAuth providers.
        
        Expected failure: OAuth providers list is empty
        """
        # Arrange - Simulate auth service initialization without OAuth config
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            # Remove OAuth configuration
            clean_env = {k: v for k, v in os.environ.items() 
                        if not k.startswith('GOOGLE_OAUTH_CLIENT')}
            
            with patch.dict(os.environ, clean_env, clear=True):
                # Act - Try to get OAuth providers from auth service
                try:
                    # This simulates the auth service health check
                    from auth_service.auth_core.oauth_manager import OAuthManager
                    
                    oauth_manager = OAuthManager()
                    providers = oauth_manager.get_available_providers()
                    
                    # This should FAIL - providers should be empty due to missing config
                    if not providers or len(providers) == 0:
                        pytest.fail("OAuth providers empty in staging (confirms the bug exists)")
                    else:
                        # If providers exist, check if they're properly configured
                        assert 'google' in providers, "Google OAuth provider should be available"
                        
                except (AttributeError, ImportError, ValueError) as e:
                    # Expected failure - OAuth manager or providers not available
                    pytest.fail(f"OAuth service integration broken: {e}")

    def test_oauth_login_flow_broken_regression(self):
        """
        REGRESSION TEST: OAuth login flow fails due to missing configuration
        
        This test should FAIL initially if OAuth login cannot be initiated.
        Root cause: Login flow cannot start without proper OAuth credentials.
        
        Expected failure: OAuth login URL generation fails
        """
        # Arrange - Mock OAuth login attempt without credentials
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            # Remove OAuth credentials
            clean_env = {k: v for k, v in os.environ.items() 
                        if not k.startswith('GOOGLE_OAUTH_CLIENT') and not k.startswith('GOOGLE_CLIENT')}
            
            with patch.dict(os.environ, clean_env, clear=True):
                # Act & Assert - OAuth login should fail
                try:
                    provider = GoogleOAuthProvider()
                    
                    # Try to generate OAuth login URL
                    login_url = provider.get_authorization_url(state="test-state")
                    
                    # This should FAIL - login URL should not be generated without credentials
                    if not login_url or login_url == "":
                        pytest.fail("OAuth login URL generation fails (confirms the bug)")
                    else:
                        # If URL is generated, it should be valid
                        assert "accounts.google.com" in login_url, "Invalid OAuth login URL"
                        assert "client_id=" in login_url, "OAuth login URL missing client_id"
                        
                except (ValueError, AttributeError, TypeError) as e:
                    # Expected failure - OAuth login cannot be initiated
                    pytest.fail(f"OAuth login flow broken without configuration: {e}")

    def test_oauth_callback_handling_failure_regression(self):
        """
        REGRESSION TEST: OAuth callback handling fails without proper configuration
        
        This test should FAIL initially if callback processing is broken.
        Root cause: OAuth callback cannot be processed without client secret.
        
        Expected failure: OAuth callback processing throws error
        """
        # Arrange - Mock OAuth callback without proper configuration
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test-client-id'
            # Intentionally missing GOOGLE_OAUTH_CLIENT_SECRET_STAGING
        }, clear=False):
            
            # Act & Assert - OAuth callback should fail
            try:
                provider = GoogleOAuthProvider()
                
                # Mock OAuth callback data
                callback_code = "test-authorization-code"
                callback_state = "test-state"
                
                # Try to process OAuth callback
                user_info = provider.exchange_code_for_user_info(callback_code, callback_state)
                
                # This should FAIL - callback processing should fail without client secret
                if user_info is None:
                    pytest.fail("OAuth callback processing fails (confirms the bug)")
                else:
                    # If processing succeeds, user info should be valid
                    assert "email" in user_info, "OAuth user info should contain email"
                    
            except (ValueError, AttributeError, KeyError) as e:
                # Expected failure - OAuth callback cannot be processed
                pytest.fail(f"OAuth callback handling broken without full configuration: {e}")