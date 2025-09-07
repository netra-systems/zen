"""
Auth OAuth Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable seamless OAuth authentication for user onboarding and login
- Value Impact: OAuth reduces friction for users joining the platform, increasing conversion rates
- Strategic Impact: Core authentication mechanism that integrates with external providers while maintaining security

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
External OAuth providers are mocked to isolate auth service behavior and avoid rate limits.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from urllib.parse import urlencode, parse_qs, urlparse

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.oauth_service import OAuthService
from auth_service.services.redis_service import RedisService
from auth_service.services.user_service import UserService
from auth_service.database import get_database


class TestOAuthIntegration(BaseIntegrationTest):
    """Integration tests for OAuth functionality with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services and mocked external OAuth."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.db = get_database()
        self.user_service = UserService(self.auth_config, self.db)
        self.oauth_service = OAuthService(self.auth_config, self.redis_service, self.user_service)
        
        # Test OAuth provider configurations
        self.test_providers = {
            "google": {
                "client_id": "test-google-client-id",
                "client_secret": "test-google-client-secret",
                "redirect_uri": "http://localhost:8081/auth/oauth/google/callback",
                "auth_url": "https://accounts.google.com/o/oauth2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo"
            },
            "github": {
                "client_id": "test-github-client-id", 
                "client_secret": "test-github-client-secret",
                "redirect_uri": "http://localhost:8081/auth/oauth/github/callback",
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "userinfo_url": "https://api.github.com/user"
            }
        }
        
        # Mock external OAuth API responses
        self.mock_oauth_responses = {
            "google": {
                "token_response": {
                    "access_token": "mock-google-access-token",
                    "refresh_token": "mock-google-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600
                },
                "userinfo_response": {
                    "id": "12345678901234567890",
                    "email": "test@gmail.com",
                    "name": "Test User Google",
                    "picture": "https://lh3.googleusercontent.com/test.jpg",
                    "verified_email": True
                }
            },
            "github": {
                "token_response": {
                    "access_token": "mock-github-access-token",
                    "token_type": "bearer",
                    "scope": "read:user user:email"
                },
                "userinfo_response": {
                    "id": 12345678,
                    "login": "testuser",
                    "email": "test@github.com",
                    "name": "Test User GitHub",
                    "avatar_url": "https://github.com/testuser.png"
                }
            }
        }
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean OAuth state data
            oauth_keys = await self.redis_service.keys("oauth:state:*")
            if oauth_keys:
                await self.redis_service.delete(*oauth_keys)
            
            # Clean test user sessions
            session_keys = await self.redis_service.keys("session:test-oauth-*")
            if session_keys:
                await self.redis_service.delete(*session_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_authorization_url_generation(self):
        """
        Test OAuth authorization URL generation for different providers.
        
        BVJ: Users must be able to initiate OAuth flow to authenticate with external providers.
        """
        for provider_name, provider_config in self.test_providers.items():
            # Generate authorization URL
            auth_url, state = await self.oauth_service.generate_auth_url(
                provider=provider_name,
                redirect_uri=provider_config["redirect_uri"]
            )
            
            assert auth_url is not None
            assert state is not None
            assert len(state) >= 32  # State should be sufficiently random
            
            # Parse and validate URL structure
            parsed_url = urlparse(auth_url)
            query_params = parse_qs(parsed_url.query)
            
            assert parsed_url.scheme == "https"
            assert provider_config["client_id"] in query_params.get("client_id", [])
            assert state in query_params.get("state", [])
            assert provider_config["redirect_uri"] in query_params.get("redirect_uri", [])
            assert "code" in query_params.get("response_type", [])
            
            # Verify state is stored in Redis
            state_key = f"oauth:state:{state}"
            stored_state = await self.redis_service.get(state_key)
            assert stored_state is not None
            
            state_data = json.loads(stored_state)
            assert state_data["provider"] == provider_name
            assert state_data["redirect_uri"] == provider_config["redirect_uri"]
            assert "created_at" in state_data
            
            # Verify state expiry (should be 10 minutes)
            ttl = await self.redis_service.ttl(state_key)
            assert 550 <= ttl <= 600  # ~10 minutes with some tolerance
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_callback_flow_google(self):
        """
        Test complete OAuth callback flow with Google (mocked external API).
        
        BVJ: Enables users to authenticate via Google OAuth and access chat features.
        """
        provider = "google"
        
        # Step 1: Generate auth URL and state
        auth_url, state = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        # Mock external OAuth API calls
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock token exchange response
            mock_token_response = AsyncMock()
            mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
            mock_token_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Mock user info response
            mock_userinfo_response = AsyncMock()
            mock_userinfo_response.json.return_value = self.mock_oauth_responses[provider]["userinfo_response"]
            mock_userinfo_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_userinfo_response
            
            # Step 2: Process OAuth callback
            authorization_code = "mock-authorization-code"
            result = await self.oauth_service.process_callback(
                provider=provider,
                code=authorization_code,
                state=state,
                redirect_uri=self.test_providers[provider]["redirect_uri"]
            )
            
            # Verify successful authentication
            assert result is not None
            assert "access_token" in result
            assert "user" in result
            assert "refresh_token" in result
            
            # Verify user data
            user_data = result["user"]
            expected_userinfo = self.mock_oauth_responses[provider]["userinfo_response"]
            assert user_data["email"] == expected_userinfo["email"]
            assert user_data["name"] == expected_userinfo["name"]
            assert user_data["oauth_provider"] == provider
            assert user_data["oauth_id"] == str(expected_userinfo["id"])
            
            # Verify tokens are real JWT tokens
            access_token = result["access_token"]
            assert len(access_token) > 100  # JWT tokens are long
            assert access_token.count('.') == 2  # JWT has 3 parts
            
            # Verify external API calls were made correctly
            assert mock_post.call_count == 1  # Token exchange
            assert mock_get.call_count == 1   # User info fetch
            
            # Verify state was consumed (removed from Redis)
            state_key = f"oauth:state:{state}"
            consumed_state = await self.redis_service.get(state_key)
            assert consumed_state is None  # Should be deleted after use
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_callback_flow_github(self):
        """
        Test complete OAuth callback flow with GitHub (mocked external API).
        
        BVJ: Enables developers to authenticate via GitHub OAuth and access platform features.
        """
        provider = "github"
        
        # Step 1: Generate auth URL and state
        auth_url, state = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        # Mock external OAuth API calls
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock token exchange response (GitHub uses different format)
            mock_token_response = AsyncMock()
            mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
            mock_token_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Mock user info response
            mock_userinfo_response = AsyncMock()
            mock_userinfo_response.json.return_value = self.mock_oauth_responses[provider]["userinfo_response"]
            mock_userinfo_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_userinfo_response
            
            # Step 2: Process OAuth callback
            authorization_code = "mock-github-authorization-code"
            result = await self.oauth_service.process_callback(
                provider=provider,
                code=authorization_code,
                state=state,
                redirect_uri=self.test_providers[provider]["redirect_uri"]
            )
            
            # Verify successful authentication
            assert result is not None
            assert "access_token" in result
            assert "user" in result
            
            # Verify user data
            user_data = result["user"]
            expected_userinfo = self.mock_oauth_responses[provider]["userinfo_response"]
            assert user_data["email"] == expected_userinfo["email"]
            assert user_data["name"] == expected_userinfo["name"]
            assert user_data["oauth_provider"] == provider
            assert user_data["oauth_id"] == str(expected_userinfo["id"])
            
            # Verify GitHub-specific fields
            assert user_data.get("username") == expected_userinfo["login"]
            assert "avatar_url" in user_data
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_state_validation_security(self):
        """
        Test OAuth state validation for security (CSRF protection).
        
        BVJ: Prevents CSRF attacks on OAuth flow, maintaining platform security.
        """
        provider = "google"
        
        # Step 1: Generate legitimate state
        auth_url, legitimate_state = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        # Test Case 1: Invalid/forged state
        forged_state = "forged-state-12345"
        
        with patch('aiohttp.ClientSession.post'):
            with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
                await self.oauth_service.process_callback(
                    provider=provider,
                    code="test-code",
                    state=forged_state,
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
        
        # Test Case 2: Expired state
        # Create state with very short expiry
        expired_state = f"expired-state-{int(time.time())}"
        expired_state_key = f"oauth:state:{expired_state}"
        await self.redis_service.set(
            expired_state_key,
            json.dumps({
                "provider": provider,
                "redirect_uri": self.test_providers[provider]["redirect_uri"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }),
            ex=1  # 1 second expiry
        )
        
        # Wait for expiry
        await asyncio.sleep(2)
        
        with patch('aiohttp.ClientSession.post'):
            with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
                await self.oauth_service.process_callback(
                    provider=provider,
                    code="test-code",
                    state=expired_state,
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
        
        # Test Case 3: State reuse prevention
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock successful OAuth responses
            mock_token_response = AsyncMock()
            mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
            mock_token_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            mock_userinfo_response = AsyncMock()
            mock_userinfo_response.json.return_value = self.mock_oauth_responses[provider]["userinfo_response"]
            mock_userinfo_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_userinfo_response
            
            # First use should succeed
            result1 = await self.oauth_service.process_callback(
                provider=provider,
                code="test-code-1",
                state=legitimate_state,
                redirect_uri=self.test_providers[provider]["redirect_uri"]
            )
            assert result1 is not None
            
            # Second use of same state should fail
            with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
                await self.oauth_service.process_callback(
                    provider=provider,
                    code="test-code-2",
                    state=legitimate_state,  # Reusing same state
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_error_handling_external_api_failures(self):
        """
        Test OAuth error handling when external APIs fail.
        
        BVJ: Ensures graceful degradation when OAuth providers are unavailable.
        """
        provider = "google"
        
        # Generate valid state
        auth_url, state = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        # Test Case 1: Token exchange failure
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_error_response = AsyncMock()
            mock_error_response.status = 400
            mock_error_response.json.return_value = {"error": "invalid_grant"}
            mock_post.return_value.__aenter__.return_value = mock_error_response
            
            with pytest.raises(Exception, match="OAuth token exchange failed"):
                await self.oauth_service.process_callback(
                    provider=provider,
                    code="invalid-code",
                    state=state,
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
        
        # Generate new state for next test
        auth_url2, state2 = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        # Test Case 2: User info fetch failure
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Successful token exchange
            mock_token_response = AsyncMock()
            mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
            mock_token_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Failed user info fetch
            mock_userinfo_error = AsyncMock()
            mock_userinfo_error.status = 403
            mock_userinfo_error.json.return_value = {"error": "insufficient_permissions"}
            mock_get.return_value.__aenter__.return_value = mock_userinfo_error
            
            with pytest.raises(Exception, match="Failed to fetch user information"):
                await self.oauth_service.process_callback(
                    provider=provider,
                    code="valid-code",
                    state=state2,
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_concurrent_authentications(self):
        """
        Test concurrent OAuth authentications for multi-user system.
        
        BVJ: Ensures multiple users can authenticate via OAuth simultaneously.
        """
        provider = "google"
        concurrent_users = 3
        
        async def authenticate_user(user_index: int):
            """Authenticate a single user via OAuth."""
            # Generate unique auth URL and state
            auth_url, state = await self.oauth_service.generate_auth_url(
                provider=provider,
                redirect_uri=self.test_providers[provider]["redirect_uri"]
            )
            
            # Mock unique user data
            unique_userinfo = {
                **self.mock_oauth_responses[provider]["userinfo_response"],
                "id": f"concurrent-user-{user_index}",
                "email": f"concurrent-user-{user_index}@gmail.com",
                "name": f"Concurrent User {user_index}"
            }
            
            with patch('aiohttp.ClientSession.post') as mock_post, \
                 patch('aiohttp.ClientSession.get') as mock_get:
                
                # Mock token exchange
                mock_token_response = AsyncMock()
                mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
                mock_token_response.status = 200
                mock_post.return_value.__aenter__.return_value = mock_token_response
                
                # Mock user info with unique data
                mock_userinfo_response = AsyncMock()
                mock_userinfo_response.json.return_value = unique_userinfo
                mock_userinfo_response.status = 200
                mock_get.return_value.__aenter__.return_value = mock_userinfo_response
                
                # Process OAuth callback
                result = await self.oauth_service.process_callback(
                    provider=provider,
                    code=f"auth-code-{user_index}",
                    state=state,
                    redirect_uri=self.test_providers[provider]["redirect_uri"]
                )
                
                return {
                    "user_index": user_index,
                    "result": result,
                    "state": state,
                    "expected_email": unique_userinfo["email"]
                }
        
        # Execute concurrent OAuth flows
        tasks = [authenticate_user(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        
        # Validate all authentications succeeded
        assert len(results) == concurrent_users
        
        authenticated_emails = []
        authenticated_tokens = []
        
        for auth_result in results:
            result = auth_result["result"]
            assert result is not None
            assert "access_token" in result
            assert "user" in result
            
            # Verify unique user data
            user_data = result["user"]
            assert user_data["email"] == auth_result["expected_email"]
            assert user_data["oauth_provider"] == provider
            
            # Verify unique tokens
            token = result["access_token"]
            assert token not in authenticated_tokens
            authenticated_tokens.append(token)
            
            # Verify unique emails
            email = user_data["email"]
            assert email not in authenticated_emails
            authenticated_emails.append(email)
            
            # Verify state was consumed
            state_key = f"oauth:state:{auth_result['state']}"
            consumed_state = await self.redis_service.get(state_key)
            assert consumed_state is None  # Should be deleted after use
        
        # Verify all users are unique
        assert len(authenticated_emails) == concurrent_users
        assert len(authenticated_tokens) == concurrent_users
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_session_creation_with_redis_persistence(self):
        """
        Test OAuth session creation and persistence in Redis.
        
        BVJ: Ensures authenticated OAuth users maintain session state for continuous platform access.
        """
        provider = "google"
        
        # Generate auth flow
        auth_url, state = await self.oauth_service.generate_auth_url(
            provider=provider,
            redirect_uri=self.test_providers[provider]["redirect_uri"]
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock successful OAuth responses
            mock_token_response = AsyncMock()
            mock_token_response.json.return_value = self.mock_oauth_responses[provider]["token_response"]
            mock_token_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            mock_userinfo_response = AsyncMock()
            mock_userinfo_response.json.return_value = self.mock_oauth_responses[provider]["userinfo_response"]
            mock_userinfo_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_userinfo_response
            
            # Complete OAuth flow
            result = await self.oauth_service.process_callback(
                provider=provider,
                code="test-session-code",
                state=state,
                redirect_uri=self.test_providers[provider]["redirect_uri"]
            )
            
            # Extract user and token information
            user_data = result["user"]
            access_token = result["access_token"]
            
            # Create session in Redis (simulating what the auth service would do)
            session_id = f"oauth-session-{user_data['oauth_id']}-{int(time.time())}"
            session_key = f"session:{session_id}"
            
            session_data = {
                "user_id": user_data["oauth_id"],
                "email": user_data["email"],
                "name": user_data["name"],
                "oauth_provider": provider,
                "access_token": access_token,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_accessed": datetime.now(timezone.utc).isoformat(),
                "oauth_access_token": self.mock_oauth_responses[provider]["token_response"]["access_token"]
            }
            
            await self.redis_service.set(
                session_key,
                json.dumps(session_data),
                ex=3600  # 1 hour session
            )
            
            # Verify session persistence
            stored_session = await self.redis_service.get(session_key)
            assert stored_session is not None
            
            retrieved_session = json.loads(stored_session)
            assert retrieved_session["user_id"] == user_data["oauth_id"]
            assert retrieved_session["email"] == user_data["email"]
            assert retrieved_session["oauth_provider"] == provider
            assert retrieved_session["access_token"] == access_token
            
            # Verify session expiry
            session_ttl = await self.redis_service.ttl(session_key)
            assert 3550 <= session_ttl <= 3600  # Should be close to 1 hour
            
            # Simulate session access update
            retrieved_session["last_accessed"] = datetime.now(timezone.utc).isoformat()
            await self.redis_service.set(
                session_key,
                json.dumps(retrieved_session),
                ex=3600  # Extend session
            )
            
            # Verify session update
            updated_session = await self.redis_service.get(session_key)
            updated_data = json.loads(updated_session)
            assert updated_data["last_accessed"] != session_data["last_accessed"]
            
            # Cleanup
            await self.redis_service.delete(session_key)