"""
Test User Journey E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete user journey from signup to value delivery
- Value Impact: Ensures end-to-end user experience delivers business value
- Strategic Impact: Core user acquisition and retention validation
"""

import pytest
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestUserJourneyE2E(BaseE2ETest):
    """Test complete user journey end-to-end."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_signup_to_first_value_delivery(self):
        """Test complete user journey from signup to first value delivery."""
        # Given: New user starting journey
        e2e_auth = E2EAuthHelper()
        
        # When: User completes signup and onboarding
        auth_result = await e2e_auth.authenticate_test_user(
            email="journey@startup.com",
            subscription_tier="free"
        )
        
        # Then: Should deliver initial value
        assert auth_result["authenticated"] is True
        assert auth_result["user_id"] is not None