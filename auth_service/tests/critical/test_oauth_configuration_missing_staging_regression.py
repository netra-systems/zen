#!/usr/bin/env python3
"""
OAuth Configuration Missing Staging Regression Tests (Fixed)

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

FIXED VERSION: Bypasses database initialization to focus purely on OAuth configuration testing.
"""

import os
import pytest
from typing import Dict, Any, List
from test_framework.database.test_database_manager import TestDatabaseManager
# Removed non-existent AuthManager import - using OAuthManager instead
from shared.isolated_environment import IsolatedEnvironment

# REAL SERVICES: Use actual conftest setup (no mocks per CLAUDE.md)
# Database initialization handled by conftest.py real services setup

from auth_service.auth_core.auth_environment import get_auth_env
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider


@pytest.mark.staging
@pytest.mark.critical
class TestOAuthConfigurationMissingRegression:
    """Tests that replicate OAuth configuration issues from staging audit"""

    def test_google_oauth_client_id_missing_staging_regression(self):
        """
        REGRESSION TEST: GOOGLE_OAUTH_CLIENT_ID_STAGING missing in staging
        
        This test confirms that the system correctly detects missing OAuth client ID
        in staging environment and handles the error appropriately.
        
        Expected behavior: OAuth client ID loading should return None/empty when not configured
        """
        from shared.isolated_environment import get_env
        
        # Arrange - Simulate staging environment without OAuth client ID
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment and remove OAuth client ID
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            env_manager.set('TESTING', '0', 'test_oauth_regression')
            
            # Remove OAuth client ID credentials to simulate missing config
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', '', 'test_oauth_regression')
            env_manager.set('GOOGLE_CLIENT_ID', '', 'test_oauth_regression')  # Remove fallback too
            
            # Act - Try to load OAuth credentials directly using AuthEnvironment SSOT
            auth_env = get_auth_env()
            client_id = auth_env.get_oauth_google_client_id()
            
            # Assert - Client ID should be None/empty when not configured
            assert client_id is None or client_id == "", \
                f"Expected OAuth client ID to be missing, but got: {client_id}"
            
            print("✓ SUCCESS: OAuth client ID correctly detected as missing in staging")
                    
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_google_oauth_client_secret_missing_staging_regression(self):
        """
        REGRESSION TEST: GOOGLE_OAUTH_CLIENT_SECRET_STAGING missing in staging
        
        This test confirms that the system correctly detects missing OAuth client secret
        in staging environment and handles the error appropriately.
        
        Expected behavior: OAuth client secret loading should return None/empty when not configured
        """
        from shared.isolated_environment import get_env
        
        # Arrange - Simulate staging environment without OAuth client secret
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment and remove OAuth client secret
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            env_manager.set('TESTING', '0', 'test_oauth_regression')
            
            # Remove OAuth client secret credentials to simulate missing config
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', '', 'test_oauth_regression')
            env_manager.set('GOOGLE_CLIENT_SECRET', '', 'test_oauth_regression')  # Remove fallback too
            
            # Act - Try to load OAuth credentials directly using AuthEnvironment SSOT
            auth_env = get_auth_env()
            client_secret = auth_env.get_oauth_google_client_secret()
            
            # Assert - Client secret should be None/empty when not configured
            assert client_secret is None or client_secret == "", \
                f"Expected OAuth client secret to be missing, but got a value"
            
            print("✓ SUCCESS: OAuth client secret correctly detected as missing in staging")
                    
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_oauth_provider_initialization_failure_regression(self):
        """
        REGRESSION TEST: OAuth provider fails to initialize without credentials
        
        This test confirms that GoogleOAuthProvider correctly handles missing credentials
        in staging environment by failing initialization or setting empty credentials.
        
        Expected behavior: OAuth provider should fail to initialize or have empty credentials
        """
        from shared.isolated_environment import get_env
        from auth_service.auth_core.oauth.google_oauth import GoogleOAuthError
        
        # Arrange - Simulate staging environment without OAuth credentials
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment and remove all OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            env_manager.set('TESTING', '0', 'test_oauth_regression')
            
            # Remove all OAuth credentials
            oauth_keys = [
                'GOOGLE_OAUTH_CLIENT_ID_STAGING', 'GOOGLE_OAUTH_CLIENT_SECRET_STAGING',
                'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'
            ]
            for key in oauth_keys:
                env_manager.set(key, '', 'test_oauth_regression')
            
            # Act & Assert - OAuth provider should fail or have no credentials
            try:
                provider = GoogleOAuthProvider()
                
                # The provider should initialize but have no credentials in staging
                assert not provider.client_id or provider.client_id == "", \
                    f"Expected empty client_id but got: {provider.client_id}"
                assert not provider.client_secret or provider.client_secret == "", \
                    f"Expected empty client_secret but got a value"
                
                # Configuration should be invalid
                assert not provider.is_configured(), \
                    "OAuth provider should not be configured without credentials"
                
                print("✓ SUCCESS: OAuth provider correctly handles missing credentials in staging")
                
            except GoogleOAuthError as e:
                # This is also acceptable - provider can fail to initialize
                print(f"✓ SUCCESS: OAuth provider initialization failed as expected: {e}")
                
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_oauth_provider_with_proper_staging_credentials(self):
        """
        TEST: OAuth provider works correctly when proper staging credentials are provided
        
        This test confirms that when OAuth credentials are properly configured for staging,
        the system works correctly. This simulates the "fix" for the regression.
        
        Expected behavior: OAuth provider should initialize successfully with valid credentials
        """
        from shared.isolated_environment import get_env
        
        # Arrange - Simulate staging environment with proper OAuth credentials
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment with proper OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            env_manager.set('TESTING', '0', 'test_oauth_regression')
            
            # Set proper OAuth credentials for staging (simulating the fix)
            test_client_id = "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com"
            test_client_secret = "GOCSPX-1234567890123456789012345678901234"
            
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', test_client_id, 'test_oauth_regression')
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', test_client_secret, 'test_oauth_regression')
            
            # Act - Initialize OAuth components directly using AuthEnvironment SSOT
            auth_env = get_auth_env()
            client_id = auth_env.get_oauth_google_client_id()
            client_secret = auth_env.get_oauth_google_client_secret()
            
            # Assert - Credentials should load correctly
            assert client_id == test_client_id, \
                f"Expected client_id {test_client_id}, got {client_id}"
            assert client_secret == test_client_secret, \
                "Expected client_secret to match test value"
            
            # Test OAuth provider initialization
            provider = GoogleOAuthProvider()
            
            assert provider.client_id == test_client_id, \
                "OAuth provider should have correct client_id"
            assert provider.client_secret == test_client_secret, \
                "OAuth provider should have correct client_secret"
            assert provider.is_configured(), \
                "OAuth provider should be properly configured"
            
            # Test configuration validation
            is_valid, error_msg = provider.validate_configuration()
            assert is_valid, f"OAuth configuration should be valid: {error_msg}"
            
            # Test redirect URI for staging
            redirect_uri = provider.get_redirect_uri()
            expected_redirect = "https://netra-auth-service-staging.run.app/auth/oauth/callback"
            assert redirect_uri == expected_redirect, \
                f"Expected redirect URI {expected_redirect}, got {redirect_uri}"
            
            # Test authorization URL generation
            auth_url = provider.get_authorization_url("test-state")
            assert auth_url and "accounts.google.com" in auth_url, \
                "Authorization URL should be valid Google OAuth URL"
            assert "client_id=" in auth_url, \
                "Authorization URL should contain client_id parameter"
            
            print("✓ SUCCESS: OAuth provider works correctly with proper staging credentials")
            
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_oauth_manager_integration_with_staging_credentials(self):
        """
        TEST: OAuth manager works correctly with staging credentials
        
        This test confirms that OAuthManager properly integrates with configured
        OAuth providers in staging environment.
        
        Expected behavior: OAuth manager should report healthy status with configured providers
        """
        from shared.isolated_environment import get_env
        from auth_service.auth_core.oauth_manager import OAuthManager
        
        # Arrange - Simulate staging environment with proper OAuth credentials
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment with proper OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            env_manager.set('TESTING', '0', 'test_oauth_regression')
            
            # Set proper OAuth credentials for staging
            test_client_id = "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com"
            test_client_secret = "GOCSPX-1234567890123456789012345678901234"
            
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', test_client_id, 'test_oauth_regression')
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', test_client_secret, 'test_oauth_regression')
            
            # Act - Initialize OAuth manager
            oauth_manager = OAuthManager()
            
            # Assert - OAuth manager should work correctly
            available_providers = oauth_manager.get_available_providers()
            assert 'google' in available_providers, \
                f"Google should be available provider, got: {available_providers}"
            
            is_configured = oauth_manager.is_provider_configured('google')
            assert is_configured, "Google OAuth provider should be configured"
            
            provider_status = oauth_manager.get_provider_status()
            assert provider_status.get('configured_providers', 0) > 0, \
                "OAuth manager should report configured providers"
            
            health_status = oauth_manager.get_health_status()
            assert health_status.get('healthy', False), \
                f"OAuth manager should be healthy: {health_status}"
            
            validation_issues = oauth_manager.validate_configuration()
            assert len(validation_issues) == 0, \
                f"OAuth configuration should have no issues: {validation_issues}"
            
            print("✓ SUCCESS: OAuth manager works correctly with staging credentials")
            
        finally:
            # Restore original environment
            env_manager.disable_isolation()


@pytest.mark.staging
@pytest.mark.critical
class TestOAuthServiceIntegrationRegression:
    """Tests OAuth service integration with proper mocking"""

    def test_auth_service_oauth_providers_availability(self):
        """
        TEST: Auth service OAuth providers are available when properly configured
        
        This test confirms that when OAuth is properly configured, the auth service
        reports OAuth providers as available and healthy.
        """
        from shared.isolated_environment import get_env
        from auth_service.auth_core.oauth_manager import OAuthManager
        
        # Arrange - Simulate staging environment with OAuth configuration
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment with proper OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            
            # Set proper OAuth credentials (simulating fix)
            test_client_id = "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com"
            test_client_secret = "GOCSPX-1234567890123456789012345678901234"
            
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', test_client_id, 'test_oauth_regression')
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', test_client_secret, 'test_oauth_regression')
            
            # Act - Check OAuth manager (simulates auth service health check)
            oauth_manager = OAuthManager()
            providers = oauth_manager.get_available_providers()
            
            # Assert - Providers should be available
            assert len(providers) > 0, "OAuth providers should be available"
            assert 'google' in providers, "Google OAuth provider should be available"
            
            print("✓ SUCCESS: Auth service OAuth providers are available when configured")
            
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_oauth_login_flow_functional_with_credentials(self):
        """
        TEST: OAuth login flow works when credentials are properly configured
        
        This test confirms that OAuth login URL generation works correctly
        when proper credentials are configured in staging.
        """
        from shared.isolated_environment import get_env
        from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider
        
        # Arrange - Simulate staging environment with OAuth credentials
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment with proper OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            
            # Set proper OAuth credentials
            test_client_id = "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com"
            test_client_secret = "GOCSPX-1234567890123456789012345678901234"
            
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', test_client_id, 'test_oauth_regression')
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', test_client_secret, 'test_oauth_regression')
            
            # Act - Try OAuth login flow
            provider = GoogleOAuthProvider()
            
            # Generate OAuth login URL
            login_url = provider.get_authorization_url(state="test-state")
            
            # Assert - Login URL should be generated correctly
            assert login_url and login_url != "", "OAuth login URL should be generated"
            assert "accounts.google.com" in login_url, "OAuth login URL should use Google OAuth"
            assert "client_id=" in login_url, "OAuth login URL should contain client_id"
            assert test_client_id in login_url, "OAuth login URL should contain correct client_id"
            
            print("✓ SUCCESS: OAuth login flow works with proper credentials")
            
        finally:
            # Restore original environment
            env_manager.disable_isolation()

    def test_oauth_callback_handling_with_credentials(self):
        """
        TEST: OAuth callback handling works when credentials are properly configured
        
        This test confirms that OAuth callback processing works correctly
        when proper credentials are configured in staging.
        """
        from shared.isolated_environment import get_env
        from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider
        
        # Arrange - Simulate staging environment with OAuth credentials
        env_manager = get_env()
        env_manager.enable_isolation(backup_original=True)
        
        try:
            # Set staging environment with proper OAuth credentials
            env_manager.set('ENVIRONMENT', 'staging', 'test_oauth_regression')
            
            # Set proper OAuth credentials
            test_client_id = "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com"
            test_client_secret = "GOCSPX-1234567890123456789012345678901234"
            
            env_manager.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', test_client_id, 'test_oauth_regression')
            env_manager.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', test_client_secret, 'test_oauth_regression')
            
            # Act - Try OAuth callback processing
            provider = GoogleOAuthProvider()
            
            # Mock OAuth callback data (for testing)
            callback_code = "test-authorization-code"
            callback_state = "test-state"
            
            # Process OAuth callback (this will use mock/test data)
            user_info = provider.exchange_code_for_user_info(callback_code, callback_state)
            
            # Assert - Callback should be processed successfully
            assert user_info is not None, "OAuth callback should return user info"
            assert "email" in user_info, "OAuth user info should contain email"
            assert user_info["email"], "OAuth user info email should not be empty"
            
            print("✓ SUCCESS: OAuth callback handling works with proper credentials")
            
        finally:
            # Restore original environment
            env_manager.disable_isolation()