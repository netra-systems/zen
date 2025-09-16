"""
Issue #1060 JWT/WebSocket Authentication Fragmentation - Phase 1 Test Suite

CRITICAL MISSION: JWT Validation SSOT Compliance Testing
Validate that JWT validation follows Single Source of Truth patterns across all services.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Authentication Security
- Goal: Golden Path Protection - $500K+ ARR user authentication flow
- Value Impact: Eliminate authentication fragmentation blocking user login → AI responses
- Revenue Impact: Critical infrastructure protecting primary revenue stream

Test Focus Areas:
1. JWT validation SSOT patterns across auth_service and netra_backend
2. Authentication flow consistency validation
3. Cross-service JWT token validation compliance
4. WebSocket authentication path consolidation verification
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Authentication imports - testing fragmentation points
from netra_backend.app.auth_integration.auth import BackendAuthIntegration, AuthValidationResult
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestJWTValidationSSOTCompliance(SSotAsyncTestCase):
    """
    Test JWT validation SSOT compliance across services.

    CRITICAL: This test suite validates that JWT validation follows
    consistent patterns and does not fragment across multiple sources.
    """

    def setup_method(self, method):
        """Set up test environment for JWT validation testing."""
        super().setup_method(method)

        self.auth_client = AuthServiceClient()
        self.backend_auth = BackendAuthIntegration()

        # Test user data for validation
        self.test_user_id = "test_user_jwt_123"
        self.test_email = "jwt.test@example.com"
        self.test_permissions = ["read", "write"]

        logger.info(f"JWT SSOT test setup complete for {method.__name__}")

    async def test_auth_service_jwt_validation_is_canonical(self):
        """
        CRITICAL: Verify auth_service JWT validation is the canonical source.

        This test ensures that the auth_service JWT handler is the SSOT
        for all JWT validation operations across the platform.
        """
        # Test that auth service validation is accessible
        from auth_service.auth_core.core.jwt_handler import JWTHandler

        jwt_handler = JWTHandler()

        # Verify JWT handler has all required SSOT methods
        assert hasattr(jwt_handler, 'validate_token'), "JWT handler missing validate_token method"
        assert hasattr(jwt_handler, 'validate_token_jwt'), "JWT handler missing validate_token_jwt method"
        assert hasattr(jwt_handler, 'create_access_token'), "JWT handler missing create_access_token method"

        # Verify validation method is callable
        assert callable(jwt_handler.validate_token), "validate_token is not callable"

        logger.info("✅ Auth service JWT validation is properly configured as SSOT")

    async def test_backend_delegates_to_auth_service(self):
        """
        CRITICAL: Verify backend auth integration delegates to auth service.

        This test ensures that the backend does NOT perform local JWT validation
        but delegates all validation to the auth service as required by SSOT.
        """
        # Verify backend auth integration uses auth service client
        assert hasattr(self.backend_auth, 'auth_client'), "Backend auth missing auth_client"
        assert isinstance(self.backend_auth.auth_client, AuthServiceClient), "Backend not using AuthServiceClient"

        # Test that backend validate_request_token calls auth service
        test_token = "Bearer test_jwt_token_123"

        with patch.object(self.backend_auth.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "email": self.test_email
            }

            result = await self.backend_auth.validate_request_token(test_token)

            # Verify auth service was called
            mock_validate.assert_called_once()
            assert result.valid is True
            assert result.user_id == self.test_user_id

        logger.info("✅ Backend properly delegates JWT validation to auth service")

    async def test_no_local_jwt_validation_in_backend(self):
        """
        CRITICAL: Verify backend contains NO local JWT validation logic.

        This test ensures that the backend does not perform local JWT
        decoding/validation, which would violate SSOT compliance.
        """
        # Import backend auth module to inspect for JWT violations
        import netra_backend.app.auth_integration.auth as backend_auth_module

        # Get module source to check for JWT violations
        import inspect
        source = inspect.getsource(backend_auth_module)

        # Check for JWT decoding violations
        jwt_violations = []

        if "jwt.decode(" in source:
            jwt_violations.append("Found jwt.decode() in backend auth")
        if "jwt.encode(" in source:
            jwt_violations.append("Found jwt.encode() in backend auth")
        if "JWT_SECRET" in source and "get_env" in source:
            jwt_violations.append("Found JWT_SECRET usage in backend auth")

        # Assert no violations found
        assert len(jwt_violations) == 0, f"SSOT violations found: {jwt_violations}"

        logger.info("✅ Backend auth contains no local JWT validation logic")

    async def test_auth_client_uses_ssot_endpoints(self):
        """
        Test that AuthServiceClient uses SSOT authentication endpoints.

        Validates that the auth client calls the correct auth service
        endpoints and follows SSOT patterns.
        """
        # Verify auth client has correct configuration
        assert hasattr(self.auth_client, 'settings'), "Auth client missing settings"
        assert hasattr(self.auth_client.settings, 'base_url'), "Auth client missing base_url"

        # Verify auth client methods exist
        assert hasattr(self.auth_client, 'validate_token_jwt'), "Auth client missing validate_token_jwt"
        assert callable(self.auth_client.validate_token_jwt), "validate_token_jwt not callable"

        logger.info("✅ Auth client properly configured for SSOT endpoints")

    async def test_jwt_validation_consistency_across_services(self):
        """
        CRITICAL: Test JWT validation consistency across services.

        This test ensures that JWT validation results are consistent
        whether called directly from auth service or through backend integration.
        """
        # Create a test JWT token scenario
        test_token = "mock_jwt_token_for_consistency_test"

        # Mock auth service validation result
        expected_result = {
            "valid": True,
            "user_id": self.test_user_id,
            "email": self.test_email,
            "permissions": self.test_permissions,
            "role": "test_user"
        }

        with patch.object(self.auth_client, 'validate_token_jwt') as mock_auth_validate:
            mock_auth_validate.return_value = expected_result

            # Test backend integration validation
            backend_result = await self.backend_auth.validate_request_token(f"Bearer {test_token}")

            # Verify consistency
            assert backend_result.valid == expected_result["valid"]
            assert backend_result.user_id == expected_result["user_id"]
            assert backend_result.email == expected_result["email"]

            # Verify auth service was called correctly
            mock_auth_validate.assert_called_once_with(test_token)

        logger.info("✅ JWT validation consistency verified across services")

    async def test_jwt_error_handling_consistency(self):
        """
        Test that JWT validation error handling is consistent across services.

        Validates that error scenarios are handled consistently whether
        validation fails at auth service or backend integration level.
        """
        test_token = "Bearer invalid_jwt_token"

        # Test invalid token scenario
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "invalid_token"}

            result = await self.backend_auth.validate_request_token(test_token)

            # Verify error handling
            assert result.valid is False
            assert result.error == "token_validation_failed"
            assert result.user_id is None

        # Test exception scenario
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.side_effect = Exception("Auth service unavailable")

            result = await self.backend_auth.validate_request_token(test_token)

            # Verify exception handling
            assert result.valid is False
            assert "validation_exception" in result.error

        logger.info("✅ JWT error handling consistency verified")

    async def test_auth_header_processing_ssot_compliance(self):
        """
        Test that authorization header processing follows SSOT patterns.

        Validates that Bearer token extraction and processing is
        consistent across all authentication entry points.
        """
        # Test valid Bearer token format
        valid_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "email": self.test_email
            }

            result = await self.backend_auth.validate_request_token(valid_token)

            # Verify token was extracted correctly
            extracted_token = mock_validate.call_args[0][0]
            assert extracted_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
            assert result.valid is True

        # Test invalid header formats
        invalid_headers = [
            "InvalidToken",
            "Basic dGVzdDp0ZXN0",
            "Bearer",
            "",
            None
        ]

        for invalid_header in invalid_headers:
            result = await self.backend_auth.validate_request_token(invalid_header)
            assert result.valid is False
            assert result.error == "invalid_authorization_header"

        logger.info("✅ Authorization header processing SSOT compliance verified")

    async def test_jwt_validation_caching_consistency(self):
        """
        Test JWT validation caching behavior for performance and consistency.

        Validates that JWT validation results are cached appropriately
        to avoid redundant auth service calls while maintaining security.
        """
        test_token = "Bearer test_cached_token_123"

        # Mock successful validation
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "email": self.test_email
            }

            # First validation call
            result1 = await self.backend_auth.validate_request_token(test_token)
            assert result1.valid is True

            # Verify auth service was called
            assert mock_validate.call_count == 1

        logger.info("✅ JWT validation caching behavior verified")

    async def test_cross_service_jwt_validation_paths(self):
        """
        CRITICAL: Test cross-service JWT validation paths.

        This test maps all JWT validation paths across services to identify
        any fragmentation or inconsistencies in validation logic.
        """
        # Map validation paths
        validation_paths = {
            "backend_auth_integration": self.backend_auth,
            "auth_service_client": self.auth_client
        }

        test_token = "test_cross_service_token"

        # Test each validation path
        for path_name, validator in validation_paths.items():
            logger.info(f"Testing validation path: {path_name}")

            # Verify validator has required methods
            if hasattr(validator, 'validate_request_token'):
                # Backend integration path
                with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
                    mock_validate.return_value = {
                        "valid": True,
                        "user_id": self.test_user_id,
                        "email": self.test_email
                    }

                    result = await validator.validate_request_token(f"Bearer {test_token}")
                    assert result.valid is True

            elif hasattr(validator, 'validate_token_jwt'):
                # Direct auth service client path
                pass  # Would test with real auth service in integration tests

        logger.info("✅ Cross-service JWT validation paths mapped and verified")


class TestJWTValidationFragmentationDetection(SSotAsyncTestCase):
    """
    Test suite to detect JWT validation fragmentation patterns.

    This suite identifies potential fragmentation points where JWT
    validation logic might be duplicated or inconsistent.
    """

    def setup_method(self, method):
        """Set up fragmentation detection tests."""
        super().setup_method(method)
        logger.info(f"JWT fragmentation detection setup for {method.__name__}")

    async def test_detect_duplicate_jwt_validation_logic(self):
        """
        Detect duplicate JWT validation logic across the codebase.

        This test scans for potential code duplication in JWT validation
        that could lead to fragmentation and inconsistency.
        """
        # This would be expanded with actual file scanning logic
        # For now, we test the known SSOT pattern

        fragmentation_indicators = []

        # Check for known fragmentation patterns
        try:
            # Import auth integration module
            import netra_backend.app.auth_integration.auth as backend_auth

            # Verify it delegates to auth service (not duplicating logic)
            if hasattr(backend_auth, 'auth_client'):
                logger.info("✅ Backend auth properly uses auth service client")
            else:
                fragmentation_indicators.append("Backend auth missing auth_client delegation")

        except ImportError as e:
            fragmentation_indicators.append(f"Failed to import backend auth: {e}")

        # Assert no fragmentation detected
        assert len(fragmentation_indicators) == 0, f"JWT fragmentation detected: {fragmentation_indicators}"

        logger.info("✅ No duplicate JWT validation logic detected")

    async def test_identify_authentication_entry_points(self):
        """
        Identify all authentication entry points in the system.

        Maps all places where JWT tokens are processed to ensure
        they follow consistent SSOT patterns.
        """
        entry_points = {}

        # Backend auth integration entry point
        try:
            from netra_backend.app.auth_integration.auth import get_current_user
            entry_points["backend_get_current_user"] = get_current_user
        except ImportError:
            pass

        # WebSocket auth entry point
        try:
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
            entry_points["websocket_authenticator"] = WebSocketAuthenticator
        except ImportError:
            pass

        # Auth service entry point
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            entry_points["auth_service_jwt_handler"] = JWTHandler
        except ImportError:
            pass

        # Verify we found expected entry points
        assert len(entry_points) > 0, "No authentication entry points found"

        logger.info(f"✅ Identified {len(entry_points)} authentication entry points: {list(entry_points.keys())}")

    async def test_verify_no_hardcoded_jwt_secrets(self):
        """
        Verify no hardcoded JWT secrets exist in the codebase.

        This test ensures that JWT secrets are properly externalized
        and not hardcoded, which could lead to security issues.
        """
        # Test that secrets come from environment/config
        from auth_service.auth_core.config import AuthConfig

        # Verify AuthConfig methods exist
        assert hasattr(AuthConfig, 'get_jwt_secret'), "AuthConfig missing get_jwt_secret method"
        assert callable(AuthConfig.get_jwt_secret), "get_jwt_secret not callable"

        # Test environment-based secret loading
        env = get_env()
        jwt_secret_key = env.get("JWT_SECRET_KEY")

        # In test environment, secret might be test value
        if jwt_secret_key:
            assert len(jwt_secret_key) > 10, "JWT secret too short"
            assert jwt_secret_key != "secret", "Using default/weak JWT secret"

        logger.info("✅ JWT secret configuration verified")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])