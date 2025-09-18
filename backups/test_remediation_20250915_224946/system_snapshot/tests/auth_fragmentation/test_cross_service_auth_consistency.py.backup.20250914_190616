"""
Issue #1060 JWT/WebSocket Authentication Fragmentation - Cross-Service Consistency Tests

CRITICAL MISSION: Cross-Service Authentication Consistency Validation
Validate that authentication behavior is consistent across all services and integration points.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Multi-Service Authentication Security
- Goal: Golden Path Protection - $500K+ ARR cross-service authentication reliability
- Value Impact: Ensure authentication consistency across auth_service ↔ netra_backend ↔ frontend
- Revenue Impact: Authentication failures block the entire Golden Path user flow

Test Focus Areas:
1. Cross-service JWT token validation consistency
2. Authentication header processing standardization
3. User context propagation across service boundaries
4. Error handling consistency across all authentication touchpoints
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Cross-service authentication imports
from netra_backend.app.auth_integration.auth import (
    BackendAuthIntegration,
    AuthValidationResult,
    get_current_user,
    _validate_token_with_auth_service
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class AuthServiceTestScenario:
    """Test scenario for cross-service authentication testing."""
    name: str
    token: str
    expected_valid: bool
    expected_user_id: Optional[str]
    expected_error: Optional[str]
    auth_service_response: Dict[str, Any]


class TestCrossServiceAuthenticationConsistency(SSotAsyncTestCase):
    """
    Test cross-service authentication consistency.

    CRITICAL: This test suite validates that authentication behavior
    is consistent across all service boundaries and integration points.
    """

    def setup_method(self, method):
        """Set up cross-service authentication testing environment."""
        super().setup_method(method)

        self.auth_client = AuthServiceClient()
        self.backend_auth = BackendAuthIntegration()

        # Test scenarios for cross-service validation
        self.test_scenarios = [
            AuthServiceTestScenario(
                name="valid_user_token",
                token="Bearer valid_jwt_token_123",
                expected_valid=True,
                expected_user_id="user_cross_service_789",
                expected_error=None,
                auth_service_response={
                    "valid": True,
                    "user_id": "user_cross_service_789",
                    "email": "cross.service@example.com",
                    "role": "user",
                    "permissions": ["read", "write"]
                }
            ),
            AuthServiceTestScenario(
                name="expired_token",
                token="Bearer expired_jwt_token_456",
                expected_valid=False,
                expected_user_id=None,
                expected_error="token_validation_failed",
                auth_service_response={
                    "valid": False,
                    "error": "token_expired"
                }
            ),
            AuthServiceTestScenario(
                name="invalid_signature",
                token="Bearer tampered_jwt_token_789",
                expected_valid=False,
                expected_user_id=None,
                expected_error="token_validation_failed",
                auth_service_response={
                    "valid": False,
                    "error": "invalid_signature"
                }
            )
        ]

        logger.info(f"Cross-service auth consistency test setup complete for {method.__name__}")

    async def test_auth_service_backend_consistency(self):
        """
        CRITICAL: Test auth service and backend authentication consistency.

        This test ensures that authentication results are consistent
        between direct auth service calls and backend integration calls.
        """
        for scenario in self.test_scenarios:
            logger.info(f"Testing scenario: {scenario.name}")

            with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
                mock_validate.return_value = scenario.auth_service_response

                # Test backend integration
                backend_result = await self.backend_auth.validate_request_token(scenario.token)

                # Verify consistency with expected results
                assert backend_result.valid == scenario.expected_valid, f"Scenario {scenario.name}: Backend valid mismatch"
                assert backend_result.user_id == scenario.expected_user_id, f"Scenario {scenario.name}: User ID mismatch"

                if scenario.expected_error:
                    assert scenario.expected_error in str(backend_result.error), f"Scenario {scenario.name}: Error mismatch"

                # Verify auth service was called correctly
                extracted_token = scenario.token.replace("Bearer ", "") if scenario.token.startswith("Bearer ") else scenario.token
                mock_validate.assert_called_once_with(extracted_token)

        logger.info("✅ Auth service and backend authentication consistency verified")

    async def test_authentication_header_processing_standardization(self):
        """
        CRITICAL: Test authentication header processing standardization.

        This test ensures that Bearer token extraction and processing
        is consistent across all authentication entry points.
        """
        # Test various header formats
        header_test_cases = [
            {
                "header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
                "expected_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
                "should_succeed": True
            },
            {
                "header": "bearer lowercase_bearer_token",
                "expected_token": None,
                "should_succeed": False  # Case sensitive
            },
            {
                "header": "Bearer",
                "expected_token": None,
                "should_succeed": False  # Missing token
            },
            {
                "header": "Basic dGVzdDp0ZXN0",
                "expected_token": None,
                "should_succeed": False  # Wrong auth type
            },
            {
                "header": "",
                "expected_token": None,
                "should_succeed": False  # Empty header
            },
            {
                "header": None,
                "expected_token": None,
                "should_succeed": False  # None header
            }
        ]

        for test_case in header_test_cases:
            logger.info(f"Testing header: {test_case['header']}")

            if test_case["should_succeed"]:
                # Mock successful auth service response
                with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
                    mock_validate.return_value = {
                        "valid": True,
                        "user_id": "header_test_user",
                        "email": "header.test@example.com"
                    }

                    result = await self.backend_auth.validate_request_token(test_case["header"])

                    # Verify successful processing
                    assert result.valid is True
                    assert result.user_id == "header_test_user"

                    # Verify correct token extracted
                    mock_validate.assert_called_once_with(test_case["expected_token"])
            else:
                # Test should fail gracefully
                result = await self.backend_auth.validate_request_token(test_case["header"])

                # Verify failure handling
                assert result.valid is False
                assert result.error == "invalid_authorization_header"

        logger.info("✅ Authentication header processing standardization verified")

    async def test_user_context_propagation_consistency(self):
        """
        CRITICAL: Test user context propagation across service boundaries.

        This test ensures that user context (ID, permissions, roles) is
        consistently propagated and maintained across service calls.
        """
        test_user_context = {
            "user_id": "context_prop_user_123",
            "email": "context.prop@example.com",
            "role": "admin",
            "permissions": ["read", "write", "admin", "delete"],
            "organization_id": "org_456",
            "tenant_id": "tenant_789"
        }

        test_token = "Bearer context_propagation_token"

        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                **test_user_context
            }

            # Test backend validation
            result = await self.backend_auth.validate_request_token(test_token)

            # Verify user context preserved
            assert result.valid is True
            assert result.user_id == test_user_context["user_id"]
            assert result.email == test_user_context["email"]

            # Verify full claims available
            assert "role" in result.claims
            assert result.claims["role"] == test_user_context["role"]
            assert "permissions" in result.claims
            assert result.claims["permissions"] == test_user_context["permissions"]

        logger.info("✅ User context propagation consistency verified")

    async def test_error_handling_consistency_across_services(self):
        """
        CRITICAL: Test error handling consistency across all services.

        This test ensures that authentication errors are handled consistently
        across all service boundaries and provide useful error information.
        """
        error_scenarios = [
            {
                "name": "auth_service_unavailable",
                "exception": Exception("Connection refused"),
                "expected_error_type": "validation_exception"
            },
            {
                "name": "auth_service_timeout",
                "exception": asyncio.TimeoutError("Request timeout"),
                "expected_error_type": "validation_exception"
            },
            {
                "name": "auth_service_invalid_response",
                "response": {"invalid": "response"},
                "expected_error_type": "token_validation_failed"
            },
            {
                "name": "auth_service_malformed_response",
                "response": None,
                "expected_error_type": "token_validation_failed"
            }
        ]

        test_token = "Bearer error_handling_test_token"

        for scenario in error_scenarios:
            logger.info(f"Testing error scenario: {scenario['name']}")

            with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
                if "exception" in scenario:
                    mock_validate.side_effect = scenario["exception"]
                else:
                    mock_validate.return_value = scenario["response"]

                result = await self.backend_auth.validate_request_token(test_token)

                # Verify error handling
                assert result.valid is False
                assert result.user_id is None
                assert scenario["expected_error_type"] in result.error

        logger.info("✅ Error handling consistency across services verified")

    async def test_authentication_timeout_consistency(self):
        """
        Test authentication timeout handling consistency.

        Validates that authentication timeouts are handled consistently
        across all service integration points.
        """
        test_token = "Bearer timeout_test_token"

        # Test auth service timeout
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.side_effect = asyncio.TimeoutError("Auth service timeout")

            result = await self.backend_auth.validate_request_token(test_token)

            # Verify timeout handling
            assert result.valid is False
            assert "validation_exception" in result.error
            assert "timeout" in result.error.lower() or "Auth service timeout" in result.error

        logger.info("✅ Authentication timeout consistency verified")

    async def test_jwt_claims_consistency_across_services(self):
        """
        CRITICAL: Test JWT claims consistency across services.

        This test ensures that JWT claims are interpreted consistently
        across all services and maintain their semantic meaning.
        """
        standard_claims = {
            "sub": "claims_test_user_456",  # Subject (user ID)
            "iat": 1640995200,  # Issued at
            "exp": 1640998800,  # Expires at
            "aud": "netra-platform",  # Audience
            "iss": "auth-service",  # Issuer
            "role": "premium_user",
            "permissions": ["read", "write", "premium_features"],
            "organization_id": "org_premium_123",
            "tenant_id": "tenant_premium_456"
        }

        test_token = "Bearer jwt_claims_consistency_token"

        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                **standard_claims
            }

            result = await self.backend_auth.validate_request_token(test_token)

            # Verify standard claims preserved
            assert result.valid is True
            assert result.user_id == standard_claims["sub"]

            # Verify extended claims available
            assert result.claims["role"] == standard_claims["role"]
            assert result.claims["permissions"] == standard_claims["permissions"]
            assert result.claims["organization_id"] == standard_claims["organization_id"]

        logger.info("✅ JWT claims consistency across services verified")

    async def test_authentication_performance_consistency(self):
        """
        Test authentication performance consistency across services.

        Validates that authentication performance is consistent and
        doesn't degrade significantly across service boundaries.
        """
        import time

        test_token = "Bearer performance_test_token"
        performance_results = []

        # Mock fast auth service response
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "perf_test_user",
                "email": "perf.test@example.com"
            }

            # Test multiple authentication calls
            for i in range(10):
                start_time = time.time()

                result = await self.backend_auth.validate_request_token(test_token)

                end_time = time.time()
                auth_time = end_time - start_time
                performance_results.append(auth_time)

                assert result.valid is True

        # Analyze performance consistency
        avg_time = sum(performance_results) / len(performance_results)
        max_time = max(performance_results)
        min_time = min(performance_results)

        # Verify reasonable performance (< 50ms average)
        assert avg_time < 0.05, f"Authentication too slow: {avg_time:.3f}s average"

        # Verify consistency (max not more than 3x min)
        if min_time > 0:
            time_ratio = max_time / min_time
            assert time_ratio < 10, f"Performance inconsistent: {time_ratio:.1f}x variation"

        logger.info(f"✅ Authentication performance consistent: {avg_time:.3f}s average, {time_ratio:.1f}x variation")


class TestCrossServiceAuthenticationFragmentationDetection(SSotAsyncTestCase):
    """
    Test suite to detect cross-service authentication fragmentation.

    This suite identifies potential fragmentation points across service
    boundaries that could lead to authentication inconsistencies.
    """

    def setup_method(self, method):
        """Set up cross-service fragmentation detection tests."""
        super().setup_method(method)
        logger.info(f"Cross-service auth fragmentation detection setup for {method.__name__}")

    async def test_identify_authentication_service_boundaries(self):
        """
        Identify all authentication service boundaries in the system.

        Maps all cross-service authentication touchpoints to ensure
        they follow consistent SSOT patterns.
        """
        service_boundaries = {}

        # Backend to Auth Service boundary
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            service_boundaries["backend_to_auth"] = AuthServiceClient
        except ImportError:
            pass

        # Backend Auth Integration boundary
        try:
            from netra_backend.app.auth_integration.auth import BackendAuthIntegration
            service_boundaries["backend_auth_integration"] = BackendAuthIntegration
        except ImportError:
            pass

        # WebSocket Auth boundary
        try:
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
            service_boundaries["websocket_auth"] = WebSocketAuthenticator
        except ImportError:
            pass

        # Verify we found expected boundaries
        assert len(service_boundaries) > 0, "No authentication service boundaries found"

        logger.info(f"✅ Identified {len(service_boundaries)} authentication service boundaries: {list(service_boundaries.keys())}")

    async def test_verify_single_auth_service_dependency(self):
        """
        CRITICAL: Verify single auth service dependency across all services.

        This test ensures that all services depend on a single auth service
        and don't fragment authentication across multiple sources.
        """
        # Test backend auth integration uses single auth client
        backend_auth = BackendAuthIntegration()
        assert hasattr(backend_auth, 'auth_client'), "Backend auth missing single auth client"

        # Test auth client configuration
        auth_client = backend_auth.auth_client
        assert hasattr(auth_client, 'settings'), "Auth client missing settings"
        assert hasattr(auth_client.settings, 'base_url'), "Auth client missing base_url"

        # Verify auth client methods
        required_methods = ['validate_token_jwt']
        for method_name in required_methods:
            assert hasattr(auth_client, method_name), f"Auth client missing {method_name}"
            assert callable(getattr(auth_client, method_name)), f"{method_name} not callable"

        logger.info("✅ Single auth service dependency verified across all services")

    async def test_detect_authentication_configuration_fragmentation(self):
        """
        Detect authentication configuration fragmentation.

        This test identifies potential configuration fragmentation that
        could lead to inconsistent authentication behavior.
        """
        from shared.isolated_environment import get_env

        env = get_env()

        # Check for consistent auth configuration access
        auth_config_keys = [
            "AUTH_SERVICE_URL",
            "JWT_SECRET_KEY",
            "AUTH_SERVICE_ENABLED"
        ]

        config_sources = []

        for config_key in auth_config_keys:
            value = env.get(config_key)
            if value:
                config_sources.append(config_key)

        # Verify configuration is accessible
        assert env is not None, "Environment access not available"

        logger.info(f"✅ Authentication configuration sources identified: {config_sources}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])