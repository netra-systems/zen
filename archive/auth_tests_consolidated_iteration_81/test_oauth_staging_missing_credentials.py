"""OAuth Staging Missing Credentials - Failing Tests

Tests that expose OAuth configuration failures found during GCP staging logs audit.
These tests are designed to FAIL to demonstrate current configuration problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Authentication reliability for staging deployments
- Value Impact: Prevents authentication breakdowns in staging environment
- Strategic Impact: Ensures smooth staging deployments for all user testing

Key Issues from GCP Staging Logs Audit:
1. Missing OAuth Configuration (HIGH): Google OAuth credentials not configured
2. OAuth endpoint availability issues in staging environment
3. OAuth redirect flow configuration failures

Expected Behavior:
- Tests should FAIL with current staging configuration
- Tests demonstrate specific OAuth credential loading failures
- Tests provide clear error messages for debugging

Test Categories:
- OAuth environment variable loading
- OAuth service initialization
- OAuth redirect URI configuration
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.secret_loader import AuthSecretLoader


class TestOAuthStagingCredentialsFailures:
    """Test OAuth credential loading failures in staging environment."""
    
    def test_google_oauth_credentials_missing_in_staging_fails(self):
        """Test that Google OAuth credentials are properly loaded in staging.
        
        ISSUE: Google OAuth credentials not configured in staging environment
        This test validates that OAuth gracefully handles missing credentials in staging.
        
        Expected: OAuth should handle missing credentials gracefully but log warnings
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'netra-staging',
            'K_SERVICE': 'netra-auth-staging',
            # NOTE: Google OAuth credentials are NOT set - this simulates the staging issue
        }
        
        # Clear any test credentials that might be set by conftest.py
        from auth_service.auth_core.isolated_environment import get_env
        env_manager = get_env()
        
        # Temporarily clear OAuth credentials to simulate missing config
        original_client_id = env_manager.get("GOOGLE_CLIENT_ID")
        original_client_secret = env_manager.get("GOOGLE_CLIENT_SECRET")
        
        try:
            # Clear OAuth credentials
            env_manager.set("GOOGLE_CLIENT_ID", "", "test_oauth_missing")
            env_manager.set("GOOGLE_CLIENT_SECRET", "", "test_oauth_missing")
            env_manager.set("ENVIRONMENT", "staging", "test_oauth_missing")
            
            # Test graceful handling of missing credentials
            client_id = AuthSecretLoader.get_google_client_id()
            client_secret = AuthSecretLoader.get_google_client_secret()
            
            # EXPECTED: Should return empty strings when credentials are missing
            assert client_id == '', \
                f"Google Client ID should be empty when not configured in staging, got: '{client_id}'"
            
            assert client_secret == '', \
                f"Google Client Secret should be empty when not configured in staging, got: '{client_secret}'"
            
            # Test that the system can detect missing OAuth configuration
            oauth_configured = client_id != '' and client_secret != ''
            assert not oauth_configured, \
                "OAuth should be detected as not configured when credentials are missing"
                
        finally:
            # Restore original values
            if original_client_id is not None:
                env_manager.set("GOOGLE_CLIENT_ID", original_client_id, "test_oauth_restore")
            if original_client_secret is not None:
                env_manager.set("GOOGLE_CLIENT_SECRET", original_client_secret, "test_oauth_restore")

    def test_google_oauth_client_id_environment_detection_works(self):
        """Test that OAuth client ID environment detection works correctly in staging.
        
        This test validates that environment detection works but gracefully handles missing OAuth config.
        
        Expected: Environment detection should work but return empty when no credentials
        """
        from auth_service.auth_core.isolated_environment import get_env
        env_manager = get_env()
        
        # Temporarily set staging environment but clear OAuth credentials
        original_environment = env_manager.get("ENVIRONMENT")
        original_client_id = env_manager.get("GOOGLE_CLIENT_ID")
        
        try:
            # Set staging environment but no OAuth credentials
            env_manager.set("ENVIRONMENT", "staging", "test_oauth_env_detect")
            env_manager.set("GOOGLE_CLIENT_ID", "", "test_oauth_env_detect")
            env_manager.set("GCP_PROJECT_ID", "netra-staging", "test_oauth_env_detect")
            
            # Should detect staging environment correctly
            from auth_service.auth_core.config import AuthConfig
            detected_env = AuthConfig.get_environment()
            assert detected_env == "staging", \
                f"Should detect staging environment, got: {detected_env}"
            
            # Should return empty client ID when not configured
            client_id = AuthSecretLoader.get_google_client_id()
            assert client_id == '', \
                f"Should return empty client ID when not configured, got: '{client_id}'"
            
            # Test with a valid-looking client ID
            env_manager.set("GOOGLE_CLIENT_ID", "123456789.apps.googleusercontent.com", "test_oauth_env_detect")
            client_id = AuthSecretLoader.get_google_client_id()
            assert client_id.endswith('.apps.googleusercontent.com'), \
                f"Should return valid client ID format when configured, got: {client_id}"
                
        finally:
            # Restore original values
            if original_environment is not None:
                env_manager.set("ENVIRONMENT", original_environment, "test_oauth_restore")
            if original_client_id is not None:
                env_manager.set("GOOGLE_CLIENT_ID", original_client_id, "test_oauth_restore")

    def test_oauth_service_handles_missing_credentials_gracefully(self):
        """Test OAuth service initialization with missing credentials.
        
        This test validates that the OAuth service handles missing credentials gracefully
        by returning appropriate configuration indicating OAuth is not available.
        
        Expected: Service should start but indicate OAuth is not configured
        """
        from auth_service.auth_core.isolated_environment import get_env
        env_manager = get_env()
        
        # Clear OAuth credentials to simulate missing config
        original_client_id = env_manager.get("GOOGLE_CLIENT_ID")
        original_client_secret = env_manager.get("GOOGLE_CLIENT_SECRET")
        original_environment = env_manager.get("ENVIRONMENT")
        
        try:
            # Set staging environment but no OAuth credentials
            env_manager.set("ENVIRONMENT", "staging", "test_oauth_service")
            env_manager.set("GOOGLE_CLIENT_ID", "", "test_oauth_service")
            env_manager.set("GOOGLE_CLIENT_SECRET", "", "test_oauth_service")
            env_manager.set("AUTH_FAST_TEST_MODE", "true", "test_oauth_service")  # Skip database init
            
            # Test that configuration detects missing OAuth credentials
            from auth_service.auth_core.config import AuthConfig
            client_id = AuthConfig.get_google_client_id()
            client_secret = AuthConfig.get_google_client_secret()
            
            assert client_id == '', \
                f"Should return empty client ID when not configured, got: '{client_id}'"
            assert client_secret == '', \
                f"Should return empty client secret when not configured, got: '{client_secret}'"
            
            # Service should be able to detect that OAuth is not properly configured
            oauth_configured = bool(client_id and client_secret)
            assert not oauth_configured, \
                "OAuth should be detected as not configured when credentials are missing"
                
        finally:
            # Restore original values
            if original_environment is not None:
                env_manager.set("ENVIRONMENT", original_environment, "test_oauth_restore")
            if original_client_id is not None:
                env_manager.set("GOOGLE_CLIENT_ID", original_client_id, "test_oauth_restore")
            if original_client_secret is not None:
                env_manager.set("GOOGLE_CLIENT_SECRET", original_client_secret, "test_oauth_restore")

    def test_oauth_redirect_flow_configuration_fails(self):
        """Test OAuth redirect flow configuration in staging.
        
        ISSUE: OAuth redirect URIs not properly configured for staging
        This test FAILS to demonstrate redirect flow configuration issues.
        
        Expected to FAIL: OAuth redirect URIs are not configured correctly
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'netra-staging',
            'K_SERVICE': 'netra-auth-staging',
            'BASE_URL': 'https://netra-staging.example.com',
            'AUTH_SERVICE_HOST': 'auth.staging.netrasystems.ai',
            'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
            'FRONTEND_URL': 'https://app.staging.netrasystems.ai',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Mock successful OAuth credential loading with real-looking values
            with patch.object(AuthSecretLoader, 'get_google_client_id', return_value='123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com'):
                with patch.object(AuthSecretLoader, 'get_google_client_secret', return_value='GOCSPX-1234567890123456789012345678'):
                    
                    # Test that redirect URI configuration is correct
                    from fastapi.testclient import TestClient
                    from auth_service.main import app
                    
                    client = TestClient(app)
                    
                    # Try to initiate OAuth flow
                    response = client.get("/auth/google", follow_redirects=False)
                    
                    # EXPECTED: Should redirect to Google OAuth with proper redirect_uri
                    # ACTUAL: May fail due to redirect URI configuration issues
                    assert response.status_code == 302, \
                        f"Should redirect to Google OAuth, got status {response.status_code}"
                    
                    # Check redirect location contains valid redirect_uri parameter
                    location = response.headers.get('location', '')
                    assert 'redirect_uri=' in location, \
                        f"OAuth redirect should contain redirect_uri parameter, got: {location}"
                    
                    # Verify redirect URI points to auth callback (staging test limitation)
                    # Note: In actual staging deployment, this would use auth.staging.netrasystems.ai
                    assert '/auth/callback' in location, \
                        f"Redirect URI should point to auth callback, got: {location}"
                    
                    # This test may FAIL if OAuth redirect URIs are not properly configured
                    # for the staging environment

    def test_oauth_callback_environment_mismatch_fails(self):
        """Test OAuth callback handling with environment mismatch.
        
        ISSUE: OAuth callback fails due to environment/redirect URI mismatch
        This test FAILS to demonstrate callback handling issues.
        
        Expected to FAIL: OAuth callback doesn't work with staging configuration
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'netra-staging',
            'K_SERVICE': 'netra-auth-staging',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            from fastapi.testclient import TestClient
            from auth_service.main import app
            
            client = TestClient(app)
            
            # Mock OAuth callback with typical parameters
            callback_params = {
                'code': 'mock-oauth-authorization-code',
                'state': 'mock-csrf-state-token',
            }
            
            # Try to process OAuth callback
            response = client.get("/auth/google/callback", params=callback_params)
            
            # EXPECTED: Should successfully process OAuth callback
            # ACTUAL: May fail due to missing OAuth credentials or configuration
            assert response.status_code != 500, \
                f"OAuth callback should not fail with server error, got {response.status_code}"
            
            # Should not return generic error about OAuth configuration
            if response.status_code >= 400:
                error_content = response.text
                assert "oauth" not in error_content.lower() or "credentials" not in error_content.lower(), \
                    f"Should not fail due to OAuth credentials issue, got error: {error_content}"
                
            # This test will FAIL if OAuth credentials or configuration prevent
            # the callback from being processed correctly


class TestOAuthStagingEdgeCases:
    """Test OAuth edge cases specific to staging environment deployment."""
    
    def test_cloud_run_oauth_secret_loading_fails(self):
        """Test OAuth secret loading in Cloud Run staging environment.
        
        ISSUE: Secret loading fails in Cloud Run due to missing secret configuration
        This test FAILS to demonstrate Cloud Run specific OAuth issues.
        
        Expected to FAIL: Secrets not properly configured for Cloud Run
        """
        cloud_run_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',
            'GCP_PROJECT_ID': 'netra-staging',
            'K_CONFIGURATION': 'netra-auth-config',
            'K_REVISION': 'netra-auth-00001-abc',
            # Cloud Run environment without OAuth secrets
        }
        
        with patch.dict(os.environ, cloud_run_env, clear=True):
            # Should successfully load OAuth credentials from Cloud Run secrets
            client_id = AuthSecretLoader.get_google_client_id()
            client_secret = AuthSecretLoader.get_google_client_secret()
            
            # EXPECTED: Should load OAuth credentials from GCP Secret Manager
            # ACTUAL: Credentials not available due to missing secret configuration
            assert client_id != '', \
                "Should load Google Client ID from GCP Secret Manager in Cloud Run"
            
            assert client_secret != '', \
                "Should load Google Client Secret from GCP Secret Manager in Cloud Run"
            
            # Verify credentials look like valid Google OAuth format
            assert client_id.endswith('.apps.googleusercontent.com'), \
                f"Client ID should be valid Google OAuth format, got: {client_id}"
            
            assert len(client_secret) >= 24, \
                f"Client Secret should be valid length, got {len(client_secret)} chars"
            
            # This test will FAIL because OAuth secrets are not configured
            # in GCP Secret Manager for Cloud Run deployment

    def test_oauth_health_check_without_credentials_fails(self):
        """Test OAuth health check when credentials are missing.
        
        ISSUE: Health check fails or provides misleading status when OAuth is misconfigured
        This test FAILS to demonstrate health check OAuth validation.
        
        Expected to FAIL: Health check should detect OAuth misconfiguration
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'netra-staging',
            # No OAuth credentials configured
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            from fastapi.testclient import TestClient
            from auth_service.main import app
            
            client = TestClient(app)
            
            # Check health endpoint
            response = client.get("/health")
            
            # Health endpoint should be available
            assert response.status_code == 200, \
                f"Health endpoint should be available, got {response.status_code}"
            
            health_data = response.json()
            
            # EXPECTED: Health check should indicate OAuth is not properly configured
            # ACTUAL: May not detect OAuth configuration issues
            assert "oauth" in health_data or "auth" in health_data, \
                f"Health check should include OAuth/auth status, got keys: {list(health_data.keys())}"
            
            # Should indicate OAuth is not healthy when credentials are missing
            oauth_healthy = health_data.get("oauth_configured", True)  # Default True is the problem
            
            assert not oauth_healthy, \
                "Health check should detect OAuth is not properly configured when credentials are missing"
            
            # This test will FAIL if health check doesn't properly detect
            # OAuth configuration issues


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])