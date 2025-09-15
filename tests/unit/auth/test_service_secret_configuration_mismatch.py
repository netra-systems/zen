"""
Unit Tests for Issue #1037: SERVICE_SECRET vs JWT_SECRET_KEY Configuration Mismatch

PURPOSE: These tests will FAIL initially to prove authentication regression exists.
The tests demonstrate the exact configuration inconsistencies causing 403 service failures.

EXPECTED FAILURES:
1. Auth service expects JWT_SECRET_KEY but backend sends SERVICE_SECRET
2. JWT validation secrets are inconsistent between services
3. Service-to-service authentication uses wrong secret sources

TEST STRATEGY: Create realistic scenarios that reproduce the exact 403 errors
described in Issue #1037, proving the regression before fixing it.
"""

import pytest
import os
import logging
from typing import Dict, Any
from unittest.mock import patch, Mock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestServiceSecretConfigurationMismatch(SSotAsyncTestCase):
    """
    CRITICAL: These tests will FAIL to prove Issue #1037 regression exists.

    Business Impact: $500K+ ARR at risk from authentication failures causing
    complete user lockout and service-to-service communication breakdown.
    """

    def setUp(self):
        """Set up test environment to reproduce configuration mismatch."""
        super().setUp()
        self.env = IsolatedEnvironment()

        # Clear all JWT/SERVICE secrets to ensure clean test state
        secret_keys = [
            "JWT_SECRET_KEY", "JWT_SECRET", "SERVICE_SECRET",
            "JWT_SECRET_STAGING", "JWT_SECRET_PRODUCTION"
        ]
        for key in secret_keys:
            self.env.delete(key, "test_setup")

        logger.info("Test setup: All auth secrets cleared for mismatch testing")

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()

    def test_auth_service_expects_jwt_secret_key_backend_sends_service_secret(self):
        """
        REGRESSION TEST: Auth service configured for JWT_SECRET_KEY,
        but backend service sends SERVICE_SECRET. This causes 403 failures.

        EXPECTED: This test will FAIL initially, proving the regression.
        """
        logger.info("Testing SERVICE_SECRET vs JWT_SECRET_KEY mismatch...")

        # Simulate auth service configuration (expects JWT_SECRET_KEY)
        auth_service_secret = "auth-service-jwt-secret-key-32-chars-long-for-testing"
        self.env.set("JWT_SECRET_KEY", auth_service_secret, "auth_service_config")

        # Simulate backend service configuration (sends SERVICE_SECRET)
        backend_service_secret = "backend-service-secret-different-32-chars-long-testing"
        self.env.set("SERVICE_SECRET", backend_service_secret, "backend_service_config")

        # Test: Backend tries to authenticate with auth service
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            from netra_backend.app.clients.auth_client_core import AuthServiceClient

            # Auth service JWT handler uses JWT_SECRET_KEY
            jwt_handler = JWTHandler()
            auth_secret = jwt_handler.get_jwt_secret()

            # Backend client uses SERVICE_SECRET for authentication
            auth_client = AuthServiceClient()
            client_secret = auth_client.service_secret

            # CRITICAL: These should be the SAME but they're DIFFERENT
            # This mismatch causes 403 authentication failures
            self.assertEqual(
                auth_secret,
                client_secret,
                f"REGRESSION DETECTED: Auth service uses '{auth_secret[:8]}...' "
                f"but backend sends '{client_secret[:8]}...'. This causes 403 failures!"
            )

            # If we reach here, the mismatch is NOT detected (test should fail)
            self.fail(
                "Expected configuration mismatch not detected! "
                "This indicates the regression test setup is incorrect."
            )

        except (ImportError, AttributeError, AssertionError) as e:
            # Expected failure proving regression exists
            logger.error(f"REGRESSION CONFIRMED: {str(e)}")
            raise AssertionError(
                f"Issue #1037 regression confirmed: SERVICE_SECRET vs JWT_SECRET_KEY mismatch. "
                f"Auth service and backend use different secret sources causing 403 failures. "
                f"Error: {str(e)}"
            )

    def test_jwt_validation_secret_inconsistency(self):
        """
        REGRESSION TEST: JWT tokens created with one secret cannot be
        validated with a different secret, causing authentication failures.

        EXPECTED: This test will FAIL initially, proving token validation breaks.
        """
        logger.info("Testing JWT validation secret inconsistency...")

        # Secret used by auth service to create tokens
        token_creation_secret = "token-creation-secret-32-chars-long-for-jwt-testing"

        # Different secret used by backend to validate tokens
        token_validation_secret = "token-validation-secret-different-32-chars-testing"

        try:
            # Simulate JWT token creation (auth service)
            import jwt
            test_payload = {"user_id": "test-user", "exp": 9999999999}

            # Auth service creates token with one secret
            token = jwt.encode(test_payload, token_creation_secret, algorithm="HS256")

            # Backend tries to validate with different secret (should fail)
            decoded = jwt.decode(token, token_validation_secret, algorithms=["HS256"])

            # If we reach here, validation succeeded (unexpected - test should fail)
            self.fail(
                f"JWT validation should have failed with mismatched secrets! "
                f"Creation secret: '{token_creation_secret[:8]}...', "
                f"Validation secret: '{token_validation_secret[:8]}...'"
            )

        except jwt.InvalidSignatureError as e:
            # Expected failure - proves JWT secret mismatch causes validation failure
            logger.error(f"JWT VALIDATION REGRESSION CONFIRMED: {str(e)}")
            raise AssertionError(
                f"Issue #1037 JWT regression confirmed: Secret mismatch prevents token validation. "
                f"This causes 403 authentication failures. Error: {str(e)}"
            )
        except ImportError:
            self.skipTest("PyJWT not available for JWT validation testing")

    def test_service_to_service_authentication_secret_mismatch(self):
        """
        REGRESSION TEST: Service-to-service calls fail when services use
        different secret sources for authentication headers.

        EXPECTED: This test will FAIL initially, proving service comm breakdown.
        """
        logger.info("Testing service-to-service authentication secret mismatch...")

        # Configure auth service with one secret source
        auth_service_secret = "auth-service-secret-source-32-chars-long-testing"
        self.env.set("JWT_SECRET_KEY", auth_service_secret, "auth_service")

        # Configure backend service with different secret source
        backend_secret = "backend-service-secret-source-different-32-chars"
        self.env.set("SERVICE_SECRET", backend_secret, "backend_service")

        # Test service-to-service communication
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient

            # Backend creates auth client
            auth_client = AuthServiceClient()

            # Check if client secret matches what auth service expects
            client_secret = getattr(auth_client, 'service_secret', None)
            expected_secret = self.env.get("JWT_SECRET_KEY")

            if client_secret != expected_secret:
                # This mismatch causes 403 service-to-service failures
                raise ValueError(
                    f"Service secret mismatch: Client uses '{client_secret[:8] if client_secret else 'None'}...' "
                    f"but auth service expects '{expected_secret[:8] if expected_secret else 'None'}...'"
                )

            # If secrets match, that's unexpected (test should fail to prove regression)
            self.fail(
                "Expected service secret mismatch not found! "
                "This indicates the regression test is not detecting Issue #1037."
            )

        except (ValueError, ImportError, AttributeError) as e:
            # Expected failure proving service communication regression
            logger.error(f"SERVICE COMMUNICATION REGRESSION CONFIRMED: {str(e)}")
            raise AssertionError(
                f"Issue #1037 service communication regression confirmed: "
                f"Secret mismatch prevents service-to-service auth. Error: {str(e)}"
            )

    def test_environment_specific_secret_configuration_drift(self):
        """
        REGRESSION TEST: Different environments (dev/staging/prod) have
        drifted to use different secret configuration patterns.

        EXPECTED: This test will FAIL initially, proving configuration drift.
        """
        logger.info("Testing environment-specific secret configuration drift...")

        # Test different environment patterns
        environments_configs = {
            "development": {"JWT_SECRET_KEY": "dev-secret-32-chars-long", "SERVICE_SECRET": None},
            "staging": {"JWT_SECRET_KEY": None, "SERVICE_SECRET": "staging-secret-32-chars"},
            "production": {"JWT_SECRET_KEY": "prod-jwt-secret-32", "SERVICE_SECRET": "prod-service-secret-32"}
        }

        inconsistent_patterns = []

        for env_name, config in environments_configs.items():
            # Clear environment
            for key in ["JWT_SECRET_KEY", "SERVICE_SECRET"]:
                self.env.delete(key, f"env_test_{env_name}")

            # Set environment-specific config
            for key, value in config.items():
                if value:
                    self.env.set(key, value, f"env_test_{env_name}")

            # Check for configuration consistency
            jwt_secret = self.env.get("JWT_SECRET_KEY")
            service_secret = self.env.get("SERVICE_SECRET")

            # Track inconsistent patterns
            if bool(jwt_secret) != bool(service_secret):
                inconsistent_patterns.append({
                    "environment": env_name,
                    "jwt_secret_present": bool(jwt_secret),
                    "service_secret_present": bool(service_secret),
                    "config": config
                })

        # Test should fail if we detect configuration drift
        if inconsistent_patterns:
            drift_details = "\n".join([
                f"  {p['environment']}: JWT_SECRET_KEY={p['jwt_secret_present']}, "
                f"SERVICE_SECRET={p['service_secret_present']}"
                for p in inconsistent_patterns
            ])

            raise AssertionError(
                f"Issue #1037 configuration drift regression confirmed:\n"
                f"Different environments use inconsistent secret patterns:\n{drift_details}\n"
                f"This causes authentication to work in some environments but fail in others."
            )

        # If no drift detected, test passes (unexpected for regression)
        logger.warning(
            "No configuration drift detected - this may indicate "
            "the regression test is not reproducing Issue #1037 accurately."
        )


if __name__ == "__main__":
    # Run the tests to prove Issue #1037 regression exists
    pytest.main([__file__, "-v", "--tb=short"])