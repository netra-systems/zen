"""
Test OAuth Provider Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable frictionless user onboarding through OAuth social login
- Value Impact: OAuth reduces signup friction by 60-80%, increasing user acquisition
  and conversion rates. Users can access AI optimization services immediately without
  complex registration flows, directly impacting customer acquisition cost (CAC)
- Strategic Impact: Core user acquisition and retention - OAuth is critical for reducing
  time-to-value and improving user experience, which directly affects MRR growth

This test suite validates that OAuth providers deliver reliable social authentication,
enabling rapid user onboarding and access to platform AI services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# Auth service imports
from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError


class TestOAuthProviderBusinessValue(BaseIntegrationTest):
    """Test OAuth provider business logic delivering user onboarding value."""
    
    @pytest.mark.unit
    def test_oauth_manager_provides_business_ready_providers(self, isolated_env):
        """Test that OAuthManager provides production-ready OAuth providers."""
        # Business Context: OAuth manager must provide reliable providers for user onboarding
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "123456789.apps.googleusercontent.com", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION", "valid-google-client-secret-for-oauth-flow", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "123456789.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "valid-google-client-secret-for-oauth-flow"
            
            oauth_manager = OAuthManager()
            
            # Should have Google provider available for business operations
            available_providers = oauth_manager.get_available_providers()
            assert "google" in available_providers, "Google OAuth required for user onboarding"
            
            # Google provider should be properly configured for business use
            google_provider = oauth_manager.get_provider("google")
            assert google_provider is not None, "Google provider must be available for user acquisition"
            
            # Provider should be configured and ready for business operations
            assert oauth_manager.is_provider_configured("google") is True, "Google OAuth must be configured for production"
    
    @pytest.mark.unit
    def test_google_oauth_provider_supports_business_authentication_flow(self, isolated_env):
        """Test that Google OAuth provider supports complete business authentication workflow."""
        # Business Context: OAuth flow must work end-to-end for user conversion
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("AUTH_SERVICE_URL", "https://auth.netrasystems.ai", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "business-client-id.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "business-oauth-secret-key"
            
            google_provider = GoogleOAuthProvider()
            
            # Provider should have proper business credentials
            assert google_provider.client_id == "business-client-id.apps.googleusercontent.com"
            assert google_provider.client_secret == "business-oauth-secret-key"
            
            # Should generate proper redirect URI for business domain
            redirect_uri = google_provider.get_redirect_uri()
            assert redirect_uri == "https://auth.netrasystems.ai/auth/callback"
            assert "/auth/callback" in redirect_uri, "Redirect URI must use standard path"
            
            # Should be configured for business operations
            assert google_provider.is_configured() is True
    
    @pytest.mark.unit
    def test_oauth_authorization_url_enables_user_acquisition(self, isolated_env):
        """Test that OAuth authorization URL generation supports user acquisition flows."""
        # Business Context: Authorization URL must direct users through proper OAuth flow
        isolated_env.set("ENVIRONMENT", "staging", "test")
        isolated_env.set("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "staging-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "staging-oauth-secret"
            
            google_provider = GoogleOAuthProvider()
            
            # Generate authorization URL for user onboarding flow
            state_token = "secure-state-token-123"
            auth_url = google_provider.get_authorization_url(state_token)
            
            # URL should direct to Google OAuth for user authentication
            assert auth_url is not None, "Authorization URL required for user onboarding"
            assert "accounts.google.com" in auth_url, "Must use Google OAuth service"
            assert "oauth2/v2/auth" in auth_url, "Must use proper OAuth endpoint"
            
            # URL should contain required OAuth parameters for business flow
            assert "client_id=staging-client.apps.googleusercontent.com" in auth_url
            assert f"state={state_token}" in auth_url, "State token required for security"
            assert "scope=" in auth_url, "Scopes required for user data access"
            
            # Should include essential scopes for business operations
            assert "email" in auth_url, "Email scope required for user identification"
            assert "profile" in auth_url, "Profile scope required for user experience"
            assert "openid" in auth_url, "OpenID required for secure authentication"
    
    @pytest.mark.unit
    def test_oauth_provider_handles_business_environment_configurations(self, isolated_env):
        """Test that OAuth provider adapts to different business environments."""
        # Business Context: Different environments need different OAuth configurations
        
        # Test staging environment configuration
        isolated_env.set("ENVIRONMENT", "staging", "test")
        isolated_env.set("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "staging-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "staging-secret"
            
            staging_provider = GoogleOAuthProvider()
            staging_redirect = staging_provider.get_redirect_uri()
            
            assert "staging.netrasystems.ai" in staging_redirect
            
        # Test production environment configuration
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("AUTH_SERVICE_URL", "https://auth.netrasystems.ai", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "prod-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "prod-secret"
            
            prod_provider = GoogleOAuthProvider()
            prod_redirect = prod_provider.get_redirect_uri()
            
            assert "auth.netrasystems.ai" in prod_redirect
            assert "staging" not in prod_redirect
    
    @pytest.mark.unit
    def test_oauth_configuration_validation_protects_business_operations(self, isolated_env):
        """Test that OAuth validation prevents configuration failures that impact business."""
        # Business Context: Misconfigured OAuth can cause complete user onboarding failure
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        # Test missing client ID in production (should fail fast)
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = ""  # Missing client ID
            mock_loader.get_google_client_secret.return_value = "valid-secret"
            
            with pytest.raises(GoogleOAuthError) as exc_info:
                GoogleOAuthProvider()
            
            assert "client ID not configured" in str(exc_info.value)
            assert "production" in str(exc_info.value)
        
        # Test missing client secret in production (should fail fast)
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "valid-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = ""  # Missing secret
            
            with pytest.raises(GoogleOAuthError) as exc_info:
                GoogleOAuthProvider()
            
            assert "client secret not configured" in str(exc_info.value)
            assert "production" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_oauth_provider_graceful_degradation_in_development(self, isolated_env):
        """Test that OAuth provider degrades gracefully in development environments."""
        # Business Context: Development should work without OAuth for developer productivity
        isolated_env.set("ENVIRONMENT", "development", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = ""  # Missing in development
            mock_loader.get_google_client_secret.return_value = ""  # Missing in development
            
            # Should not raise exception in development
            google_provider = GoogleOAuthProvider()
            
            # Should indicate unconfigured state
            assert google_provider.is_configured() is False
            assert google_provider.client_id == ""
            assert google_provider.client_secret == ""
    
    @pytest.mark.unit
    def test_oauth_provider_self_check_validates_business_readiness(self, isolated_env):
        """Test that OAuth provider self-check validates business readiness."""
        # Business Context: Self-check prevents silent OAuth failures that impact user acquisition
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "prod-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "prod-oauth-secret"
            
            google_provider = GoogleOAuthProvider()
            
            # Self-check should validate OAuth readiness
            self_check = google_provider.self_check()
            
            assert self_check is not None, "Self-check required for business validation"
            assert self_check.get("is_healthy") is True, "OAuth must be healthy for user acquisition"
            assert self_check.get("client_id_configured") is True, "Client ID required for OAuth"
            assert self_check.get("client_secret_configured") is True, "Client secret required for OAuth"
            
            # Should validate redirect URI configuration
            assert self_check.get("redirect_uri_configured") is True, "Redirect URI required for OAuth flow"
    
    @pytest.mark.unit
    def test_oauth_token_exchange_supports_user_authentication_business_flow(self, isolated_env):
        """Test that OAuth token exchange supports complete user authentication flow."""
        # Business Context: Token exchange converts OAuth code to user tokens for platform access
        isolated_env.set("ENVIRONMENT", "staging", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "staging-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "staging-secret"
            
            google_provider = GoogleOAuthProvider()
            
            # Mock successful token exchange response
            mock_token_response = {
                "access_token": "google-access-token-for-api-calls",
                "token_type": "Bearer",
                "expires_in": 3600,
                "id_token": "google-id-token-with-user-info"
            }
            
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_response
                mock_post.return_value = mock_response
                
                # Exchange OAuth code for tokens
                oauth_code = "oauth-authorization-code-from-google"
                token_data = google_provider.exchange_code_for_token(oauth_code)
                
                # Should return token data for user authentication
                assert token_data is not None, "Token data required for user authentication"
                assert token_data.get("access_token") is not None, "Access token required for API calls"
                assert token_data.get("id_token") is not None, "ID token required for user identification"
                
                # Should have called Google token endpoint
                assert mock_post.called, "Must call Google OAuth token endpoint"
                call_args = mock_post.call_args
                assert "oauth2/v4/token" in call_args[1]["url"] or "token" in call_args[1]["url"]
    
    @pytest.mark.unit
    def test_oauth_user_info_retrieval_enables_user_profile_creation(self, isolated_env):
        """Test that OAuth user info retrieval enables user profile creation for business."""
        # Business Context: User info from OAuth enables personalized user experience
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "prod-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "prod-secret"
            
            google_provider = GoogleOAuthProvider()
            
            # Mock user info response from Google
            mock_user_info = {
                "id": "google-user-id-12345",
                "email": "user@businessclient.com",
                "name": "Business User",
                "picture": "https://lh3.googleusercontent.com/photo.jpg",
                "given_name": "Business",
                "family_name": "User",
                "locale": "en"
            }
            
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_user_info
                mock_get.return_value = mock_response
                
                # Get user info with access token
                access_token = "google-access-token-for-user-api"
                user_info = google_provider.get_user_info(access_token)
                
                # Should return complete user information for business operations
                assert user_info is not None, "User info required for profile creation"
                assert user_info.get("email") == "user@businessclient.com", "Email required for user identification"
                assert user_info.get("name") == "Business User", "Name required for personalization"
                assert user_info.get("id") == "google-user-id-12345", "Google ID required for account linking"
                
                # Should include optional profile enhancement data
                assert user_info.get("picture") is not None, "Profile picture enhances user experience"
                assert user_info.get("given_name") == "Business", "First name enables personalization"
                
                # Should have called Google userinfo endpoint
                assert mock_get.called, "Must call Google userinfo API"
                call_args = mock_get.call_args
                assert "userinfo" in call_args[0][0], "Must use Google userinfo endpoint"
    
    @pytest.mark.unit
    def test_oauth_error_handling_protects_business_continuity(self, isolated_env):
        """Test that OAuth error handling prevents business disruption from auth failures."""
        # Business Context: OAuth failures should not crash the service or lose users
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "prod-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "prod-secret"
            
            google_provider = GoogleOAuthProvider()
            
            # Test network failure during token exchange
            with patch('requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.RequestException("Network error")
                
                # Should handle network errors gracefully
                oauth_code = "valid-oauth-code"
                token_data = google_provider.exchange_code_for_token(oauth_code)
                
                # Should return None or error indication instead of crashing
                assert token_data is None or token_data.get("error") is not None
            
            # Test invalid token response
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.json.return_value = {"error": "invalid_grant"}
                mock_post.return_value = mock_response
                
                # Should handle OAuth errors gracefully
                token_data = google_provider.exchange_code_for_token("invalid-code")
                assert token_data is None or token_data.get("error") is not None
            
            # Test user info API failure
            with patch('requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.Timeout("API timeout")
                
                # Should handle API timeouts gracefully
                access_token = "valid-access-token"
                user_info = google_provider.get_user_info(access_token)
                assert user_info is None or user_info.get("error") is not None
    
    @pytest.mark.unit
    def test_oauth_manager_status_monitoring_supports_business_operations(self, isolated_env):
        """Test that OAuth manager provides status monitoring for business health checks."""
        # Business Context: OAuth status monitoring enables proactive issue detection
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        with patch('auth_service.auth_core.oauth.google_oauth.AuthSecretLoader') as mock_loader:
            mock_loader.get_google_client_id.return_value = "prod-client.apps.googleusercontent.com"
            mock_loader.get_google_client_secret.return_value = "prod-secret"
            
            oauth_manager = OAuthManager()
            
            # Should provide provider status for monitoring
            google_status = oauth_manager.get_provider_status("google")
            
            assert google_status is not None, "Provider status required for monitoring"
            assert google_status.get("configured") is True, "Configuration status required"
            assert google_status.get("provider_name") == "google", "Provider identification required"
            
            # Should indicate health status for business operations
            assert google_status.get("healthy") is not None, "Health status required for monitoring"