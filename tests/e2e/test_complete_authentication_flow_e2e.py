"""
Test Complete Authentication Flow E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless user onboarding and authentication experience
- Value Impact: Protects user acquisition funnel and reduces signup friction
- Strategic Impact: Core user experience for customer acquisition and retention

CRITICAL COMPLIANCE:
- Uses real authentication services for E2E testing
- Tests complete OAuth and JWT flows
- Validates user registration to first login journey
- Uses E2EAuthHelper for proper authentication patterns
"""

import pytest
import uuid
from datetime import datetime, timezone

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestCompleteAuthenticationFlowE2E(BaseE2ETest):
    """Test complete authentication flow end-to-end."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_oauth_registration_to_authenticated_session_e2e(self):
        """Test complete OAuth registration to authenticated session flow."""
        # Given: New user attempting to register via OAuth
        e2e_auth = E2EAuthHelper()
        
        new_user_data = {
            "email": f"newuser_{uuid.uuid4()}@enterprise.com",
            "name": "Test Enterprise User",
            "oauth_provider": "google"
        }
        
        # When: User completes OAuth registration flow
        auth_result = await e2e_auth.authenticate_oauth_user(
            email=new_user_data["email"],
            name=new_user_data["name"],
            provider=new_user_data["oauth_provider"]
        )
        
        # Then: User should be fully authenticated and able to access platform
        assert auth_result is not None
        assert auth_result["authenticated"] is True
        assert auth_result["user_id"] is not None
        assert auth_result["access_token"] is not None
        
        # Should be able to make authenticated requests immediately
        user_profile = await e2e_auth.get_authenticated_user_profile(
            auth_result["access_token"]
        )
        
        assert user_profile["email"] == new_user_data["email"]
        assert user_profile["subscription_tier"] in ["free", "trial", "enterprise_trial"]
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_user_login_to_dashboard_access_e2e(self):
        """Test user login to dashboard access complete flow."""
        # Given: Existing user attempting to log in
        e2e_auth = E2EAuthHelper()
        
        # Create test user first
        test_user = await e2e_auth.create_test_user(
            email="logintest@company.com",
            subscription_tier="premium"
        )
        
        # When: User logs in and accesses dashboard
        login_result = await e2e_auth.authenticate_existing_user(
            email=test_user["email"],
            password="test-password-123"
        )
        
        # Then: Should be able to access protected dashboard resources
        assert login_result["authenticated"] is True
        
        dashboard_data = await e2e_auth.get_authenticated_dashboard_data(
            login_result["access_token"]
        )
        
        assert dashboard_data is not None
        assert dashboard_data["user_id"] == test_user["user_id"]
        assert "subscription_tier" in dashboard_data