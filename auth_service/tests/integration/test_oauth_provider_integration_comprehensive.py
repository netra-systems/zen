"""
OAuth Provider Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Seamless third-party authentication integration
- Value Impact: Users can authenticate with Google/GitHub without friction
- Strategic Impact: Reduces signup barriers and improves user acquisition

These tests validate:
1. OAuth provider configuration and initialization
2. Real OAuth flow simulation (without actual OAuth calls)
3. Token exchange and user profile retrieval
4. Provider-specific error handling
5. Multi-provider support and switching
6. OAuth state management and security
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from urllib.parse import urlparse, parse_qs

from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider
from auth_service.auth_core.oauth.oauth_config import OAuthConfig
from auth_service.auth_core.oauth.oauth_state_manager import OAuthStateManager
from auth_service.auth_core.database.oauth_repository import OAuthRepository
from auth_service.auth_core.models.oauth_user import OAuthUser
from auth_service.auth_core.models.oauth_token import OAuthToken
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from shared.isolated_environment import get_env


class TestOAuthProviderIntegration(SSotBaseTestCase):
    """
    Comprehensive OAuth provider integration tests.
    
    These tests use realistic mock responses to validate OAuth flows
    without making actual calls to external OAuth providers.
    """

    @pytest.fixture
    def auth_env(self):
        """Get isolated auth environment with OAuth configuration."""
        env = get_env()
        auth_env = AuthEnvironment(env)
        
        # Set OAuth provider configuration
        auth_env.set("GOOGLE_CLIENT_ID", "test-google-client-id-1234567890", source="test")
        auth_env.set("GOOGLE_CLIENT_SECRET", "test-google-client-secret-abcdef", source="test")
        auth_env.set("GITHUB_CLIENT_ID", "test-github-client-id-9876543210", source="test")
        auth_env.set("GITHUB_CLIENT_SECRET", "test-github-client-secret-fedcba", source="test")
        auth_env.set("OAUTH_REDIRECT_BASE_URL", "https://test.netra.com", source="test")
        auth_env.set("OAUTH_STATE_SECRET", "test-oauth-state-secret-32-characters", source="test")
        
        auth_env.load_environment()
        return auth_env

    @pytest.fixture
    def oauth_config(self, auth_env):
        """Create OAuth configuration."""
        return OAuthConfig(auth_env)

    @pytest.fixture
    def oauth_manager(self, oauth_config):
        """Create OAuth manager with providers."""
        manager = OAuthManager(oauth_config)
        
        # Register providers
        google_provider = GoogleOAuthProvider(oauth_config)
        manager.register_provider("google", google_provider)
        
        return manager

    @pytest.fixture
    def oauth_state_manager(self, oauth_config):
        """Create OAuth state manager."""
        return OAuthStateManager(oauth_config)

    @pytest.fixture
    async def oauth_repository(self):
        """Create OAuth repository with database connection."""
        db_helper = DatabaseTestHelper()
        async with db_helper.get_test_session() as session:
            yield OAuthRepository(session)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_provider_configuration_and_initialization(self, oauth_manager, oauth_config):
        """
        Test OAuth providers are properly configured and initialized.
        
        CRITICAL: OAuth providers must be configured with valid credentials.
        """
        # Verify OAuth manager initialization
        assert oauth_manager is not None
        assert len(oauth_manager.registered_providers) >= 1
        assert "google" in oauth_manager.registered_providers
        
        # Verify Google provider configuration
        google_provider = oauth_manager.get_provider("google")
        assert google_provider is not None
        assert google_provider.client_id == oauth_config.google_client_id
        assert google_provider.client_secret == oauth_config.google_client_secret
        assert google_provider.provider_name == "google"
        
        # Verify OAuth configuration
        assert oauth_config.google_client_id.startswith("test-google-client-id")
        assert oauth_config.google_client_secret.startswith("test-google-client-secret")
        assert oauth_config.oauth_redirect_base_url == "https://test.netra.com"
        assert len(oauth_config.oauth_state_secret) >= 32
        
        # Test provider availability check
        provider_status = await oauth_manager.check_provider_availability("google")
        assert provider_status.provider == "google"
        assert provider_status.is_available is True
        assert provider_status.configuration_valid is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_authorization_flow_simulation(self, oauth_manager, oauth_state_manager):
        """
        Test OAuth authorization flow with realistic simulation.
        
        CRITICAL: Authorization flow must generate proper URLs and handle state.
        """
        # Generate OAuth state for the flow
        state_data = {
            "provider": "google",
            "redirect_uri": "/dashboard",
            "user_context": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0 Integration Test"
            }
        }
        
        oauth_state = oauth_state_manager.create_oauth_state(state_data)
        
        assert oauth_state is not None
        assert len(oauth_state.state_token) >= 32
        assert oauth_state.provider == "google"
        assert oauth_state.expires_at > datetime.now(timezone.utc)
        
        # Generate authorization URL
        google_provider = oauth_manager.get_provider("google")
        auth_url = google_provider.get_authorization_url(oauth_state.state_token)
        
        # Verify authorization URL structure
        assert auth_url.startswith("https://accounts.google.com/o/oauth2/auth")
        
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        # Verify required OAuth parameters
        assert "client_id" in query_params
        assert "redirect_uri" in query_params
        assert "response_type" in query_params
        assert "scope" in query_params
        assert "state" in query_params
        
        assert query_params["client_id"][0] == google_provider.client_id
        assert query_params["response_type"][0] == "code"
        assert query_params["state"][0] == oauth_state.state_token
        assert "openid" in query_params["scope"][0]
        assert "email" in query_params["scope"][0]
        
        # Verify state can be validated
        validated_state = oauth_state_manager.validate_oauth_state(oauth_state.state_token)
        assert validated_state is not None
        assert validated_state.provider == "google"
        assert validated_state.redirect_uri == "/dashboard"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_token_exchange_simulation(self, oauth_manager):
        """
        Test OAuth token exchange with mocked provider responses.
        
        CRITICAL: Token exchange must handle provider responses correctly.
        """
        google_provider = oauth_manager.get_provider("google")
        
        # Mock successful token exchange response
        mock_token_response = {
            "access_token": "ya29.a0AfH6SMC_test_access_token_example",
            "refresh_token": "1//04_test_refresh_token_example",
            "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test_id_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "openid email profile"
        }
        
        with patch('httpx.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_post.return_value = mock_response
            
            # Perform token exchange
            authorization_code = "test_authorization_code_12345"
            redirect_uri = "https://test.netra.com/auth/callback"
            
            token_result = await google_provider.exchange_code_for_tokens(
                authorization_code=authorization_code,
                redirect_uri=redirect_uri
            )
            
            # Verify token exchange request
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            assert call_args[0][0] == "https://oauth2.googleapis.com/token"
            assert call_args[1]["data"]["client_id"] == google_provider.client_id
            assert call_args[1]["data"]["client_secret"] == google_provider.client_secret
            assert call_args[1]["data"]["code"] == authorization_code
            assert call_args[1]["data"]["redirect_uri"] == redirect_uri
            assert call_args[1]["data"]["grant_type"] == "authorization_code"
            
            # Verify token result
            assert token_result.access_token == mock_token_response["access_token"]
            assert token_result.refresh_token == mock_token_response["refresh_token"]
            assert token_result.id_token == mock_token_response["id_token"]
            assert token_result.expires_in == mock_token_response["expires_in"]
            assert token_result.token_type == mock_token_response["token_type"]
            assert token_result.provider == "google"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_user_profile_retrieval(self, oauth_manager):
        """
        Test OAuth user profile retrieval with mocked provider API.
        
        CRITICAL: User profile data must be retrieved and parsed correctly.
        """
        google_provider = oauth_manager.get_provider("google")
        
        # Mock user info API response
        mock_user_info = {
            "sub": "1234567890123456789",
            "name": "Integration Test User",
            "given_name": "Integration",
            "family_name": "User", 
            "picture": "https://lh3.googleusercontent.com/a/test_photo",
            "email": "integration.test@gmail.com",
            "email_verified": True,
            "locale": "en"
        }
        
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_info
            mock_get.return_value = mock_response
            
            # Retrieve user info
            access_token = "ya29.a0AfH6SMC_test_access_token"
            user_info = await google_provider.get_user_info(access_token)
            
            # Verify API request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            
            assert "https://www.googleapis.com/oauth2/v2/userinfo" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {access_token}"
            
            # Verify user info parsing
            assert user_info.provider_id == mock_user_info["sub"]
            assert user_info.email == mock_user_info["email"]
            assert user_info.name == mock_user_info["name"]
            assert user_info.first_name == mock_user_info["given_name"]
            assert user_info.last_name == mock_user_info["family_name"]
            assert user_info.picture_url == mock_user_info["picture"]
            assert user_info.email_verified == mock_user_info["email_verified"]
            assert user_info.provider == "google"
            assert user_info.raw_data == mock_user_info

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_error_handling_integration(self, oauth_manager):
        """
        Test OAuth error handling with various provider error scenarios.
        
        CRITICAL: OAuth errors must be handled gracefully without exposing secrets.
        """
        google_provider = oauth_manager.get_provider("google")
        
        # Test token exchange errors
        error_scenarios = [
            {
                "status_code": 400,
                "response": {
                    "error": "invalid_grant",
                    "error_description": "The provided authorization grant is invalid"
                },
                "expected_error": "invalid_grant"
            },
            {
                "status_code": 401, 
                "response": {
                    "error": "invalid_client",
                    "error_description": "The OAuth client was not found"
                },
                "expected_error": "invalid_client"
            },
            {
                "status_code": 500,
                "response": {
                    "error": "server_error", 
                    "error_description": "Internal server error occurred"
                },
                "expected_error": "server_error"
            }
        ]
        
        for scenario in error_scenarios:
            with patch('httpx.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = scenario["status_code"]
                mock_response.json.return_value = scenario["response"]
                mock_response.raise_for_status.side_effect = Exception(f"HTTP {scenario['status_code']}")
                mock_post.return_value = mock_response
                
                # Attempt token exchange that should fail
                with pytest.raises(Exception) as exc_info:
                    await google_provider.exchange_code_for_tokens(
                        authorization_code="invalid_code",
                        redirect_uri="https://test.netra.com/auth/callback"
                    )
                
                error_message = str(exc_info.value)
                
                # Verify error contains expected error code
                assert scenario["expected_error"] in error_message.lower()
                
                # Verify sensitive information is not exposed
                assert google_provider.client_secret not in error_message
                assert "client_secret" not in error_message.lower()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_database_integration(self, oauth_repository):
        """
        Test OAuth data persistence in database.
        
        CRITICAL: OAuth connections must be persisted for user management.
        """
        # Create OAuth user record
        oauth_user_data = {
            "provider": "google",
            "provider_user_id": "1234567890123456789",
            "email": "oauth.integration@gmail.com",
            "name": "OAuth Integration User",
            "email_verified": True,
            "profile_data": {
                "picture": "https://lh3.googleusercontent.com/test",
                "locale": "en",
                "given_name": "OAuth",
                "family_name": "User"
            }
        }
        
        created_oauth_user = await oauth_repository.create_oauth_user(
            provider=oauth_user_data["provider"],
            provider_user_id=oauth_user_data["provider_user_id"],
            email=oauth_user_data["email"],
            name=oauth_user_data["name"],
            email_verified=oauth_user_data["email_verified"],
            profile_data=oauth_user_data["profile_data"]
        )
        
        # Verify OAuth user creation
        assert created_oauth_user is not None
        assert created_oauth_user.id is not None
        assert created_oauth_user.provider == "google"
        assert created_oauth_user.provider_user_id == "1234567890123456789"
        assert created_oauth_user.email == oauth_user_data["email"]
        assert created_oauth_user.name == oauth_user_data["name"]
        assert created_oauth_user.email_verified is True
        assert created_oauth_user.profile_data == oauth_user_data["profile_data"]
        assert created_oauth_user.created_at is not None
        
        # Retrieve OAuth user by provider and ID
        retrieved_user = await oauth_repository.get_oauth_user_by_provider_id(
            provider="google",
            provider_user_id="1234567890123456789"
        )
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_oauth_user.id
        assert retrieved_user.email == oauth_user_data["email"]
        
        # Create OAuth token record
        oauth_token_data = {
            "oauth_user_id": created_oauth_user.id,
            "access_token": "ya29.test_access_token_encrypted",
            "refresh_token": "1//test_refresh_token_encrypted",
            "token_type": "Bearer",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "scope": "openid email profile"
        }
        
        created_token = await oauth_repository.create_oauth_token(
            oauth_user_id=oauth_token_data["oauth_user_id"],
            access_token=oauth_token_data["access_token"],
            refresh_token=oauth_token_data["refresh_token"],
            token_type=oauth_token_data["token_type"],
            expires_at=oauth_token_data["expires_at"],
            scope=oauth_token_data["scope"]
        )
        
        # Verify OAuth token creation
        assert created_token is not None
        assert created_token.oauth_user_id == created_oauth_user.id
        assert created_token.access_token is not None  # May be encrypted
        assert created_token.token_type == "Bearer"
        assert created_token.expires_at == oauth_token_data["expires_at"]
        assert created_token.scope == oauth_token_data["scope"]
        
        # Test token retrieval and validation
        retrieved_token = await oauth_repository.get_active_oauth_token(
            oauth_user_id=created_oauth_user.id
        )
        
        assert retrieved_token is not None
        assert retrieved_token.id == created_token.id
        assert not retrieved_token.is_expired()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_state_management_persistence(self, oauth_state_manager):
        """
        Test OAuth state management with database persistence.
        
        CRITICAL: OAuth states must be persisted to prevent CSRF attacks.
        """
        # Create OAuth state with complex data
        state_data = {
            "provider": "google",
            "redirect_uri": "/dashboard?tab=integrations",
            "user_context": {
                "ip_address": "203.0.113.1",
                "user_agent": "Mozilla/5.0 (Integration Test)",
                "referrer": "https://example.com/signup",
                "utm_source": "integration_test"
            },
            "additional_params": {
                "force_consent": True,
                "hd": "example.com"  # G Suite domain hint
            }
        }
        
        # Create and persist OAuth state
        oauth_state = oauth_state_manager.create_oauth_state(state_data)
        
        assert oauth_state.state_token is not None
        assert len(oauth_state.state_token) >= 32
        assert oauth_state.provider == "google"
        assert oauth_state.redirect_uri == "/dashboard?tab=integrations"
        
        # Verify state persistence
        persisted_state = await oauth_state_manager.get_persisted_state(oauth_state.state_token)
        
        assert persisted_state is not None
        assert persisted_state.provider == state_data["provider"]
        assert persisted_state.redirect_uri == state_data["redirect_uri"]
        assert persisted_state.user_context == state_data["user_context"]
        assert persisted_state.additional_params == state_data["additional_params"]
        
        # Test state expiration
        time.sleep(1)  # Brief delay
        
        # Update state to be expired
        expired_state = await oauth_state_manager.expire_state(oauth_state.state_token)
        assert expired_state.is_expired
        
        # Expired state should not validate
        validation_result = oauth_state_manager.validate_oauth_state(oauth_state.state_token)
        assert not validation_result.is_valid
        assert "expired" in validation_result.error_message.lower()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_provider_oauth_integration(self, oauth_manager, oauth_config):
        """
        Test multiple OAuth providers work independently.
        
        CRITICAL: Multiple OAuth providers must not interfere with each other.
        """
        # Add GitHub provider to manager
        github_provider = GitHubOAuthProvider(oauth_config)  # Would need to implement
        oauth_manager.register_provider("github", github_provider)
        
        # Verify both providers are registered
        assert len(oauth_manager.registered_providers) >= 2
        assert "google" in oauth_manager.registered_providers
        assert "github" in oauth_manager.registered_providers
        
        google_provider = oauth_manager.get_provider("google")
        github_provider = oauth_manager.get_provider("github")
        
        # Verify providers have independent configurations
        assert google_provider.client_id != github_provider.client_id
        assert google_provider.client_secret != github_provider.client_secret
        assert google_provider.provider_name != github_provider.provider_name
        
        # Test independent authorization URLs
        test_state = f"test-state-{uuid.uuid4().hex}"
        
        google_auth_url = google_provider.get_authorization_url(test_state)
        github_auth_url = github_provider.get_authorization_url(test_state)
        
        assert "accounts.google.com" in google_auth_url
        assert "github.com" in github_auth_url
        assert google_auth_url != github_auth_url
        
        # Both should contain the same state parameter
        google_params = parse_qs(urlparse(google_auth_url).query)
        github_params = parse_qs(urlparse(github_auth_url).query)
        
        assert google_params["state"][0] == test_state
        assert github_params["state"][0] == test_state
        
        # Test provider-specific error handling
        for provider_name in ["google", "github"]:
            provider = oauth_manager.get_provider(provider_name)
            
            with pytest.raises(Exception) as exc_info:
                provider.handle_oauth_error("invalid_client", "Client authentication failed")
            
            error_message = str(exc_info.value)
            assert provider_name in error_message.lower() or "client" in error_message.lower()
            assert provider.client_secret not in error_message


# Mock GitHub provider for testing (would be implemented in real system)
class GitHubOAuthProvider:
    """Mock GitHub OAuth provider for multi-provider testing."""
    
    def __init__(self, config):
        self.client_id = config.github_client_id
        self.client_secret = config.github_client_secret
        self.provider_name = "github"
    
    def get_authorization_url(self, state):
        return f"https://github.com/login/oauth/authorize?client_id={self.client_id}&state={state}&scope=user:email"
    
    def handle_oauth_error(self, error_code, error_description):
        raise Exception(f"GitHub OAuth error: {error_code} - {error_description}")