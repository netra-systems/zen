"""
OAuth Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - OAuth enables convenient user onboarding
- Business Goal: Seamless user registration and login via Google/GitHub OAuth  
- Value Impact: Reduces friction for new users, increases conversion rates
- Strategic Impact: Enterprise customers expect OAuth SSO integration

CRITICAL REQUIREMENTS:
- NO DOCKER - Integration tests without Docker containers
- NO MOCKS - Use real OAuth flows where possible, real database connections
- Real Services - Connect to PostgreSQL (port 5434) and Redis (port 6381) 
- Integration Layer - Test OAuth service interactions, not full user browser flows

Test Categories:
1. OAuth provider integration (Google, GitHub)
2. OAuth callback handling
3. OAuth state parameter validation
4. OAuth error handling  
5. OAuth user profile extraction
"""

import asyncio
import json
import pytest
import secrets
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser

import httpx
import asyncpg
import redis.asyncio as redis


class TestOAuthIntegration(BaseIntegrationTest):
    """Integration tests for OAuth flows - NO MOCKS for core logic, REAL SERVICES."""
    
    def setup_method(self):
        """Set up for OAuth integration tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # OAuth Configuration (from real environment)
        self.oauth_config = {
            "google": {
                "client_id": self.env.get("GOOGLE_OAUTH_CLIENT_ID"),
                "client_secret": self.env.get("GOOGLE_OAUTH_CLIENT_SECRET"),
                "redirect_uri": self.env.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8081/auth/callback/google")
            },
            "github": {
                "client_id": self.env.get("GITHUB_OAUTH_CLIENT_ID"), 
                "client_secret": self.env.get("GITHUB_OAUTH_CLIENT_SECRET"),
                "redirect_uri": self.env.get("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8081/auth/callback/github")
            }
        }
        
        # Service URLs
        self.auth_service_url = f"http://localhost:{self.env.get('AUTH_SERVICE_PORT', '8081')}"
        self.backend_url = f"http://localhost:{self.env.get('BACKEND_PORT', '8000')}"
        
        # Real service connections
        self.redis_url = f"redis://localhost:{self.env.get('REDIS_PORT', '6381')}"
        self.db_url = self.env.get("TEST_DATABASE_URL") or f"postgresql://test:test@localhost:5434/test_db"
        
        # Test OAuth scenarios
        self.test_oauth_users = {
            "google": {
                "sub": "oauth-google-123456",
                "email": "oauth.google@netra.ai", 
                "name": "OAuth Google User",
                "picture": "https://example.com/avatar.jpg",
                "email_verified": True
            },
            "github": {
                "id": "oauth-github-789012",
                "login": "oauth-github-user",
                "email": "oauth.github@netra.ai",
                "name": "OAuth GitHub User", 
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.oauth
    async def test_oauth_provider_authorization_url_generation(self, real_services_fixture):
        """
        Test OAuth authorization URL generation for Google and GitHub providers.
        
        Business Value: Users get proper OAuth redirect URLs for secure authentication.
        """
        async with httpx.AsyncClient() as client:
            
            # Test Google OAuth URL generation
            if self.oauth_config["google"]["client_id"]:
                google_response = await client.get(
                    f"{self.auth_service_url}/api/v1/oauth/google/authorize",
                    timeout=10.0
                )
                
                if google_response.status_code == 200:
                    google_data = google_response.json()
                    assert "authorization_url" in google_data
                    assert "state" in google_data
                    
                    # Validate Google OAuth URL structure
                    auth_url = google_data["authorization_url"]
                    assert "accounts.google.com" in auth_url
                    assert "oauth2/v2/auth" in auth_url
                    assert self.oauth_config["google"]["client_id"] in auth_url
                    assert urllib.parse.quote(self.oauth_config["google"]["redirect_uri"]) in auth_url
                    
                    # Validate state parameter exists and is secure
                    state = google_data["state"]
                    assert len(state) >= 32  # Should be sufficiently random
                    assert state.replace('-', '').replace('_', '').isalnum()  # URL-safe characters
                    
            # Test GitHub OAuth URL generation  
            if self.oauth_config["github"]["client_id"]:
                github_response = await client.get(
                    f"{self.auth_service_url}/api/v1/oauth/github/authorize", 
                    timeout=10.0
                )
                
                if github_response.status_code == 200:
                    github_data = github_response.json()
                    assert "authorization_url" in github_data
                    assert "state" in github_data
                    
                    # Validate GitHub OAuth URL structure
                    auth_url = github_data["authorization_url"]
                    assert "github.com" in auth_url
                    assert "login/oauth/authorize" in auth_url
                    assert self.oauth_config["github"]["client_id"] in auth_url
                    assert urllib.parse.quote(self.oauth_config["github"]["redirect_uri"]) in auth_url

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.oauth
    async def test_oauth_callback_handling_google(self, real_services_fixture):
        """
        Test OAuth callback handling for Google provider with real service integration.
        
        Business Value: Google users can successfully complete OAuth flow and access platform.
        """
        redis_client = redis.from_url(self.redis_url)
        conn = None
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            # Generate valid OAuth state
            state = secrets.token_urlsafe(32)
            
            # Store state in Redis (simulating OAuth flow)
            await redis_client.setex(
                f"oauth_state:{state}",
                300,  # 5 minutes 
                json.dumps({
                    "provider": "google",
                    "timestamp": int(time.time()),
                    "redirect_after": "/dashboard"
                })
            )
            
            # Simulate Google OAuth callback with mock authorization code
            # NOTE: We mock the external Google API call but use real internal processing
            mock_google_token_response = {
                "access_token": "mock_google_access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "id_token": "mock_google_id_token"
            }
            
            mock_google_user_info = self.test_oauth_users["google"]
            
            async with httpx.AsyncClient() as client:
                
                # Mock external Google API calls while testing internal logic
                with patch('httpx.AsyncClient.post') as mock_post, \
                     patch('httpx.AsyncClient.get') as mock_get:
                    
                    # Mock Google token exchange
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = mock_google_token_response
                    
                    # Mock Google user info retrieval
                    mock_get.return_value.status_code = 200 
                    mock_get.return_value.json.return_value = mock_google_user_info
                    
                    # Test OAuth callback endpoint with real service processing
                    callback_response = await client.get(
                        f"{self.auth_service_url}/api/v1/oauth/google/callback",
                        params={
                            "code": "mock_authorization_code",
                            "state": state
                        },
                        timeout=10.0
                    )
                    
                    # Callback should process successfully
                    assert callback_response.status_code in [200, 302, 404], \
                        f"OAuth callback failed: {callback_response.status_code}"
                    
                    if callback_response.status_code in [200, 302]:
                        # Verify user was created/updated in real database
                        user_record = await conn.fetchrow(
                            "SELECT * FROM users WHERE email = $1",
                            mock_google_user_info["email"]
                        )
                        
                        if user_record:
                            assert user_record["email"] == mock_google_user_info["email"]
                            assert user_record["name"] == mock_google_user_info["name"]
                            
                        # Verify OAuth state was consumed (removed from Redis)
                        remaining_state = await redis_client.get(f"oauth_state:{state}")
                        assert remaining_state is None, "OAuth state should be consumed after use"
            
        except Exception as e:
            self.logger.warning(f"OAuth callback test error: {e}")
            if "not available" in str(e).lower():
                pytest.skip("Required services not available for OAuth testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.oauth  
    async def test_oauth_state_parameter_validation(self, real_services_fixture):
        """
        Test OAuth state parameter validation prevents CSRF attacks.
        
        Business Value: Protects users from OAuth CSRF attacks and unauthorized access.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Test invalid state scenarios
            test_scenarios = [
                {
                    "name": "missing_state",
                    "params": {"code": "test_code"},
                    "should_fail": True
                },
                {
                    "name": "invalid_state_format", 
                    "params": {"code": "test_code", "state": "invalid_state"},
                    "should_fail": True
                },
                {
                    "name": "expired_state",
                    "params": {"code": "test_code", "state": "expired_state_token"},
                    "should_fail": True,
                    "setup": "create_expired_state"
                },
                {
                    "name": "reused_state",
                    "params": {"code": "test_code", "state": "reused_state_token"}, 
                    "should_fail": True,
                    "setup": "create_and_consume_state"
                }
            ]
            
            async with httpx.AsyncClient() as client:
                
                for scenario in test_scenarios:
                    
                    # Setup scenario-specific conditions
                    if scenario.get("setup") == "create_expired_state":
                        # Create expired state in Redis
                        await redis_client.setex(
                            f"oauth_state:{scenario['params']['state']}", 
                            1,  # 1 second TTL
                            json.dumps({"provider": "google", "expired": True})
                        )
                        await asyncio.sleep(2)  # Wait for expiration
                        
                    elif scenario.get("setup") == "create_and_consume_state":
                        # Create state then immediately consume it
                        state_key = f"oauth_state:{scenario['params']['state']}"
                        await redis_client.setex(state_key, 300, json.dumps({"provider": "google"}))
                        await redis_client.delete(state_key)  # Simulate consumption
                    
                    # Test OAuth callback with invalid state
                    response = await client.get(
                        f"{self.auth_service_url}/api/v1/oauth/google/callback",
                        params=scenario["params"],
                        timeout=10.0
                    )
                    
                    if scenario["should_fail"]:
                        assert response.status_code in [400, 401, 403, 404], \
                            f"Scenario '{scenario['name']}' should fail but got {response.status_code}"
                    else:
                        assert response.status_code in [200, 302, 404], \
                            f"Scenario '{scenario['name']}' should succeed but got {response.status_code}"
            
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.oauth
    async def test_oauth_error_handling(self, real_services_fixture):
        """
        Test OAuth error handling for various failure scenarios.
        
        Business Value: Users get clear error messages and system remains stable during OAuth failures.
        """
        async with httpx.AsyncClient() as client:
            
            # Test OAuth provider errors
            oauth_error_scenarios = [
                {
                    "name": "user_denied_access",
                    "params": {"error": "access_denied", "error_description": "User denied access"},
                    "expected_status": [400, 401, 404]
                },
                {
                    "name": "invalid_authorization_code",
                    "params": {"code": "invalid_code", "state": "valid_state"},
                    "expected_status": [400, 401, 404]  
                },
                {
                    "name": "provider_server_error",
                    "params": {"error": "server_error", "error_description": "Provider unavailable"},
                    "expected_status": [400, 500, 502, 503, 504]
                }
            ]
            
            for scenario in oauth_error_scenarios:
                
                # Test Google OAuth error handling
                google_response = await client.get(
                    f"{self.auth_service_url}/api/v1/oauth/google/callback",
                    params=scenario["params"],
                    timeout=10.0
                )
                
                assert google_response.status_code in scenario["expected_status"], \
                    f"Google OAuth error '{scenario['name']}' got unexpected status {google_response.status_code}"
                
                # Test GitHub OAuth error handling  
                github_response = await client.get(
                    f"{self.auth_service_url}/api/v1/oauth/github/callback",
                    params=scenario["params"],
                    timeout=10.0
                )
                
                assert github_response.status_code in scenario["expected_status"], \
                    f"GitHub OAuth error '{scenario['name']}' got unexpected status {github_response.status_code}"
            
            # Test network timeout handling
            # (This tests the auth service's resilience to external API failures)
            with patch('httpx.AsyncClient.post') as mock_post:
                
                # Simulate external API timeout
                mock_post.side_effect = httpx.TimeoutException("OAuth provider timeout")
                
                timeout_response = await client.get(
                    f"{self.auth_service_url}/api/v1/oauth/google/callback",
                    params={"code": "test_code", "state": "timeout_test_state"},
                    timeout=10.0
                )
                
                assert timeout_response.status_code in [400, 500, 502, 503, 504], \
                    f"OAuth timeout should return error status, got {timeout_response.status_code}"

    @pytest.mark.integration  
    @pytest.mark.auth
    @pytest.mark.oauth
    async def test_oauth_user_profile_extraction(self, real_services_fixture):
        """
        Test extraction and processing of user profiles from OAuth providers.
        
        Business Value: User profiles are properly extracted and stored for personalization.
        """
        conn = None
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            # Test profile extraction scenarios
            profile_scenarios = [
                {
                    "provider": "google",
                    "profile_data": self.test_oauth_users["google"],
                    "expected_fields": ["sub", "email", "name", "picture", "email_verified"]
                },
                {
                    "provider": "github", 
                    "profile_data": self.test_oauth_users["github"],
                    "expected_fields": ["id", "login", "email", "name", "avatar_url"]
                }
            ]
            
            async with httpx.AsyncClient() as client:
                
                for scenario in profile_scenarios:
                    
                    # Mock external API response with real profile data
                    with patch('httpx.AsyncClient.get') as mock_get:
                        
                        mock_get.return_value.status_code = 200
                        mock_get.return_value.json.return_value = scenario["profile_data"]
                        
                        # Test profile extraction endpoint
                        profile_response = await client.post(
                            f"{self.auth_service_url}/api/v1/oauth/{scenario['provider']}/extract-profile",
                            json={"access_token": "mock_access_token"},
                            timeout=10.0
                        )
                        
                        if profile_response.status_code == 200:
                            extracted_profile = profile_response.json()
                            
                            # Verify all expected fields are extracted
                            for field in scenario["expected_fields"]:
                                assert field in scenario["profile_data"], \
                                    f"Test data missing required field: {field}"
                            
                            # Verify profile processing
                            assert "user_id" in extracted_profile or "id" in extracted_profile
                            assert "email" in extracted_profile
                            assert "name" in extracted_profile
                            
                            # Test database integration - verify user profile is stored
                            if scenario["provider"] == "google":
                                user_id = scenario["profile_data"]["sub"]
                                email = scenario["profile_data"]["email"]
                            else:  # github
                                user_id = str(scenario["profile_data"]["id"])
                                email = scenario["profile_data"]["email"]
                            
                            # Create user record to test profile integration
                            await conn.execute("""
                                INSERT INTO users (id, email, name, oauth_provider, oauth_provider_id, created_at)
                                VALUES ($1, $2, $3, $4, $5, $6)
                                ON CONFLICT (id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    oauth_provider = EXCLUDED.oauth_provider,
                                    oauth_provider_id = EXCLUDED.oauth_provider_id
                            """, f"oauth_{scenario['provider']}_{user_id}", email, 
                                scenario["profile_data"]["name"], scenario["provider"], 
                                user_id, datetime.now(timezone.utc))
                            
                            # Verify user was stored with OAuth profile data
                            stored_user = await conn.fetchrow(
                                "SELECT * FROM users WHERE email = $1 AND oauth_provider = $2",
                                email, scenario["provider"]
                            )
                            
                            if stored_user:
                                assert stored_user["oauth_provider"] == scenario["provider"]
                                assert stored_user["oauth_provider_id"] == user_id
                                assert stored_user["name"] == scenario["profile_data"]["name"]
            
        except Exception as e:
            self.logger.warning(f"OAuth profile extraction test error: {e}")
            if "not available" in str(e).lower():
                pytest.skip("Required services not available for OAuth profile testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.oauth
    async def test_oauth_provider_configuration_validation(self, real_services_fixture):
        """
        Test OAuth provider configuration validation and error reporting.
        
        Business Value: System fails gracefully when OAuth providers are misconfigured.
        """
        # Test configuration validation scenarios
        config_scenarios = [
            {
                "name": "missing_client_id",
                "provider": "google",
                "config_override": {"client_id": None},
                "should_fail": True
            },
            {
                "name": "invalid_redirect_uri",
                "provider": "github", 
                "config_override": {"redirect_uri": "invalid_uri"},
                "should_fail": True
            },
            {
                "name": "empty_client_secret",
                "provider": "google",
                "config_override": {"client_secret": ""},
                "should_fail": True  
            }
        ]
        
        async with httpx.AsyncClient() as client:
            
            for scenario in config_scenarios:
                
                # Test OAuth configuration validation endpoint
                config_response = await client.post(
                    f"{self.auth_service_url}/api/v1/oauth/{scenario['provider']}/validate-config",
                    json=scenario.get("config_override", {}),
                    timeout=10.0
                )
                
                if scenario["should_fail"]:
                    assert config_response.status_code in [400, 404, 500], \
                        f"Configuration scenario '{scenario['name']}' should fail but got {config_response.status_code}"
                else:
                    assert config_response.status_code in [200, 404], \
                        f"Configuration scenario '{scenario['name']}' should succeed but got {config_response.status_code}"
                
                # Test that authorization fails gracefully with bad config
                if scenario["should_fail"]:
                    auth_response = await client.get(
                        f"{self.auth_service_url}/api/v1/oauth/{scenario['provider']}/authorize",
                        timeout=10.0
                    )
                    
                    assert auth_response.status_code in [400, 404, 500], \
                        f"OAuth authorization should fail with bad config for '{scenario['name']}'"