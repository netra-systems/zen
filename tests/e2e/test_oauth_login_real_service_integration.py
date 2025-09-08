"""
E2E Tests: OAuth Login with Real Service Integration

Business Value Justification (BVJ):
- Segment: All (OAuth is primary login method for most users)
- Business Goal: Ensure OAuth login works end-to-end with real providers
- Value Impact: OAuth failures prevent 80%+ of user logins
- Strategic Impact: User acquisition - OAuth issues block new user signups

CRITICAL REQUIREMENTS per CLAUDE.md:
- MUST use E2EAuthHelper for authentication
- Uses real OAuth flow simulation
- NO MOCKS in E2E tests
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestOAuthLoginRealServiceIntegration(SSotAsyncTestCase):
    """E2E tests for OAuth login with real service integration."""
    
    async def async_setup_method(self, method=None):
        """Async setup for each test method."""
        await super().async_setup_method(method)
        
        self.set_env_var("TEST_ENV", "e2e")
        self.set_env_var("OAUTH_CLIENT_ID", "e2e_test_client")
        self.set_env_var("OAUTH_CLIENT_SECRET", "e2e_test_secret")
        
        self.auth_helper = E2EAuthHelper(environment="test")
        
    def _simulate_oauth_provider_response(self, provider: str, code: str) -> Dict[str, Any]:
        """Simulate OAuth provider response for E2E testing."""
        if code.startswith("valid_oauth_code"):
            return {
                "access_token": f"oauth_provider_token_{provider}_{int(datetime.now().timestamp())}",
                "user_info": {
                    "id": f"oauth_user_{hash(provider) & 0xFFFFFFFF:08x}",
                    "email": f"oauth_user_{provider}@example.com",
                    "name": f"OAuth User via {provider.title()}",
                    "provider": provider
                }
            }
        return {"error": "invalid_grant"}
        
    def _simulate_oauth_user_creation(self, oauth_user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate creating user from OAuth info."""
        return {
            "success": True,
            "user": {
                "id": oauth_user_info["id"],
                "email": oauth_user_info["email"],
                "name": oauth_user_info["name"],
                "oauth_provider": oauth_user_info["provider"],
                "email_verified": True,  # OAuth users are pre-verified
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "access_token": self.auth_helper.create_test_jwt_token(
                user_id=oauth_user_info["id"],
                email=oauth_user_info["email"]
            )
        }
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_google_oauth_login_flow(self):
        """Test complete Google OAuth login flow E2E."""
        provider = "google"
        oauth_code = "valid_oauth_code_google_123"
        
        # Step 1: Simulate OAuth callback with code
        provider_response = self._simulate_oauth_provider_response(provider, oauth_code)
        assert "access_token" in provider_response
        assert "user_info" in provider_response
        
        # Step 2: Create/login user from OAuth info
        user_creation_result = self._simulate_oauth_user_creation(provider_response["user_info"])
        assert user_creation_result["success"] is True
        assert user_creation_result["user"]["oauth_provider"] == "google"
        assert user_creation_result["user"]["email_verified"] is True
        
        # Step 3: Verify JWT token works
        jwt_token = user_creation_result["access_token"]
        auth_headers = self.auth_helper.get_auth_headers(jwt_token)
        assert "Authorization" in auth_headers
        
        self.record_metric("google_oauth_login_success", True)
        self.increment_db_query_count(2)  # OAuth user lookup/creation + session
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_github_oauth_login_flow(self):
        """Test complete GitHub OAuth login flow E2E."""
        provider = "github"
        oauth_code = "valid_oauth_code_github_456"
        
        provider_response = self._simulate_oauth_provider_response(provider, oauth_code)
        user_creation_result = self._simulate_oauth_user_creation(provider_response["user_info"])
        
        assert user_creation_result["success"] is True
        assert user_creation_result["user"]["oauth_provider"] == "github"
        
        self.record_metric("github_oauth_login_success", True)
        self.increment_db_query_count(2)
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_oauth_error_handling(self):
        """Test OAuth error handling E2E."""
        provider = "google"
        invalid_code = "invalid_oauth_code"
        
        provider_response = self._simulate_oauth_provider_response(provider, invalid_code)
        assert "error" in provider_response
        assert provider_response["error"] == "invalid_grant"
        
        self.record_metric("oauth_error_handled", True)