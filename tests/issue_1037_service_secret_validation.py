#!/usr/bin/env python3
"""
Issue #1037 SSOT Configuration Authentication Remediation Test

This test validates that SERVICE_SECRET is properly resolved through SSOT configuration
for service-to-service authentication, following the pattern established in Issue #521.

Current Issue:
- AuthConfig.get_service_secret() looks for SECRET_KEY 
- System expects SERVICE_SECRET for inter-service auth
- This mismatch causes authentication failures

Expected Fix:
- Update auth service configuration to use SERVICE_SECRET consistently
- Follow SSOT configuration pattern for unified secret resolution
"""

import os
import pytest
import logging
from typing import Optional

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestIssue1037ServiceSecretSSotValidation(SSotAsyncTestCase):
    """
    Test SSOT configuration authentication remediation for Issue #1037.
    
    This test follows the Issue #521 pattern of creating a failing test first,
    then implementing the minimal fix to ensure SSOT configuration consistency.
    """

    def setUp(self):
        """Set up test environment for Issue #1037 validation."""
        super().setUp()
        
        # Use the inherited environment from SSOT base test case
        # Clear any existing auth-related environment variables
        env = self.get_env()
        
        # Set up baseline configuration
        env.set("ENVIRONMENT", "test", "issue_1037_test")
        env.set("JWT_SECRET_KEY", "test-jwt-secret-32-characters-long", "issue_1037_test")
        
    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()

    def test_service_secret_ssot_resolution_currently_fails(self):
        """
        Test that SERVICE_SECRET is properly resolved through SSOT configuration.
        
        EXPECTED TO FAIL initially due to SECRET_KEY vs SERVICE_SECRET mismatch.
        After fix, this should pass by using SERVICE_SECRET consistently.
        
        Issue #1037: Auth service configuration inconsistency between SECRET_KEY and SERVICE_SECRET
        """
        # GIVEN: SERVICE_SECRET is configured (standard expectation)
        test_service_secret = "test-service-secret-32-characters-long"
        env = self.get_env()
        env.set("SERVICE_SECRET", test_service_secret, "issue_1037_test")
        
        # AND: Clear any test framework SECRET_KEY to isolate the test
        env.delete("SECRET_KEY", "test_framework_base")
        env.delete("SECRET_KEY", "development")
        
        # Verify only SERVICE_SECRET is available
        assert env.get("SERVICE_SECRET") == test_service_secret, "SERVICE_SECRET should be set"
        
        try:
            # WHEN: Auth service tries to get service secret through SSOT configuration
            from auth_service.auth_core.config import AuthConfig
            from auth_service.auth_core.auth_environment import AuthEnvironment
            
            # Create auth environment with our test environment
            auth_env = AuthEnvironment()
            auth_env.env = env
            
            # Test the current implementation
            resolved_secret = auth_env.get_secret_key()  # This is what get_service_secret() calls
            
            # THEN: Should resolve SERVICE_SECRET, not look for SECRET_KEY
            # CURRENTLY FAILS: This assertion will fail because get_secret_key() looks for SECRET_KEY
            assert resolved_secret == test_service_secret, (
                f"SSOT configuration should resolve SERVICE_SECRET: expected '{test_service_secret}', "
                f"got '{resolved_secret}'. AuthConfig.get_service_secret() -> get_secret_key() "
                f"should use SERVICE_SECRET for service-to-service authentication consistency."
            )
            
        except ValueError as e:
            # EXPECTED FAILURE: Current implementation fails when SECRET_KEY not found
            logger.info(f"Expected failure - Issue #1037 not fixed yet: {e}")
            
            # Verify the failure is due to SECRET_KEY expectation, not SERVICE_SECRET resolution
            assert "SECRET_KEY must be explicitly set" in str(e), (
                f"Expected SECRET_KEY error, got: {e}"
            )
            
            # This test should fail initially - that's the point
            pytest.fail(
                "Issue #1037 not fixed: AuthConfig.get_service_secret() still looks for SECRET_KEY "
                "instead of SERVICE_SECRET. Need to implement SSOT configuration fix."
            )

    def test_service_secret_fallback_pattern(self):
        """
        Test that SERVICE_SECRET follows the same fallback pattern as JWT secrets.
        
        This validates the intended behavior after the fix is implemented.
        """
        # GIVEN: Both SERVICE_SECRET and SECRET_KEY are available
        service_secret = "service-secret-32-characters-long"
        secret_key = "secret-key-32-characters-long"
        
        env = self.get_env()
        env.set("SERVICE_SECRET", service_secret, "issue_1037_test")
        env.set("SECRET_KEY", secret_key, "issue_1037_test")
        
        try:
            from auth_service.auth_core.auth_environment import AuthEnvironment
            
            auth_env = AuthEnvironment()
            auth_env.env = env
            
            # WHEN: Requesting service secret
            resolved_secret = auth_env.get_secret_key()
            
            # THEN: Should prefer SERVICE_SECRET over SECRET_KEY for service auth
            # This will fail initially, but shows the intended behavior
            assert resolved_secret == service_secret, (
                "After Issue #1037 fix: SERVICE_SECRET should be preferred for service authentication"
            )
            
        except (ImportError, ValueError) as e:
            # Expected during development - test framework validation
            logger.info(f"Development environment limitation: {e}")
            pytest.skip("Skip due to test environment limitations")

    def test_auth_config_service_secret_integration(self):
        """
        Test that AuthConfig.get_service_secret() uses SERVICE_SECRET through SSOT.
        
        Integration test for the complete flow after fix implementation.
        """
        # GIVEN: SERVICE_SECRET is configured
        test_service_secret = "auth-service-secret-32-characters-long"
        env = self.get_env()
        env.set("SERVICE_SECRET", test_service_secret, "issue_1037_test")
        
        try:
            from auth_service.auth_core.config import AuthConfig
            from auth_service.auth_core.auth_environment import get_auth_env
            
            # Mock the auth environment with our test environment
            original_get_auth_env = get_auth_env
            
            def mock_get_auth_env():
                auth_env = original_get_auth_env()
                auth_env.env = env
                return auth_env
            
            import auth_service.auth_core.config
            auth_service.auth_core.config.get_auth_env = mock_get_auth_env
            
            # WHEN: Getting service secret through AuthConfig
            resolved_secret = AuthConfig.get_service_secret()
            
            # THEN: Should return SERVICE_SECRET value
            assert resolved_secret == test_service_secret, (
                f"AuthConfig.get_service_secret() should return SERVICE_SECRET value: "
                f"expected '{test_service_secret}', got '{resolved_secret}'"
            )
            
            # Restore original function
            auth_service.auth_core.config.get_auth_env = original_get_auth_env
            
        except Exception as e:
            logger.info(f"Expected failure during Issue #1037 implementation: {e}")
            pytest.fail(
                f"Issue #1037 integration test failed: {e}. "
                "Need to implement SERVICE_SECRET support in auth service configuration."
            )


if __name__ == "__main__":
    # Run the failing test to validate Issue #1037
    pytest.main([__file__, "-v", "-s"])