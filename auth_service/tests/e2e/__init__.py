"""
Auth Service E2E Tests

This package contains comprehensive end-to-end tests for the auth service
following TEST_CREATION_GUIDE.md standards and CLAUDE.md requirements.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure auth service delivers complete business value through testing
- Value Impact: Validates authentication system enables all user business flows
- Strategic Impact: Critical foundation for platform reliability and user experience

E2E Test Coverage:
- Complete OAuth login flows (test_complete_oauth_login_flow.py)
- Auth service business flows (test_auth_service_business_flows.py) 
- Cross-service authentication (test_cross_service_authentication.py)

CRITICAL E2E REQUIREMENTS (all tests comply):
✅ Uses REAL Docker services - NO MOCKS allowed
✅ Tests complete business user journeys end-to-end
✅ Uses proper authentication patterns (JWT/OAuth)
✅ Validates timing (no 0-second executions)
✅ Tests business value delivery scenarios
✅ Includes comprehensive error handling
✅ Uses proper pytest markers (@pytest.mark.e2e, @pytest.mark.real_services)

Test Execution:
    python tests/unified_test_runner.py --category e2e --real-services
    python tests/unified_test_runner.py --test-file auth_service/tests/e2e/test_complete_oauth_login_flow.py
"""

__version__ = "1.0.0"
__all__ = [
    "TestCompleteOAuthLoginFlow",
    "TestAuthServiceBusinessFlows", 
    "TestCrossServiceAuthentication"
]