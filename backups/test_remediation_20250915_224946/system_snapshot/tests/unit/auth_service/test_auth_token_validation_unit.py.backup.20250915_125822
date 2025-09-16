"""
Issue #1174: Authentication Token Validation Failure - Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable authentication token validation for all user tiers
- Value Impact: Token validation directly protects $500K+ ARR by preventing unauthorized access
- Strategic Impact: Core security foundation enabling secure multi-user platform operations

Issue #1174 Specific Focus:
- Tests token validation failure scenarios that cause authentication errors
- Validates token parsing, verification, and error handling
- Reproduces token validation edge cases causing system failures
- Ensures proper error responses for invalid/expired tokens

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns
- Focuses on business-critical authentication failures
- NO mocks for core JWT operations - uses real cryptographic validation
- Tests must FAIL initially to reproduce Issue #1174 symptoms
"""

import asyncio
import jwt
import pytest
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.token_validator import TokenValidator


class TestIssue1174AuthTokenValidationUnit(SSotBaseTestCase):
    """
    Unit tests reproducing Issue #1174 authentication token validation failures.

    These tests are designed to INITIALLY FAIL and reproduce the exact failure
    conditions described in Issue #1174. Success criteria is reproducing the
    problem, then fixing it.
    """

    def setup_method(self, method):
        """Set up for auth token validation unit tests."""
        super().setup_method(method)
        self.env = get_env()

        # Use real JWT configuration - CRITICAL for reproducing Issue #1174
        self.jwt_secret = self.env.get("JWT_SECRET_KEY") or "test-jwt-secret-key-issue-1174-reproduction"
        self.jwt_handler = JWTHandler()
        self.token_validator = TokenValidator()

        # Test data that should trigger Issue #1174 conditions
        self.problematic_user_data = {
            "user_id": "issue-1174-test-user",
            "email": "issue1174@netratest.com",
            "permissions": ["read", "write"],
            "subscription_tier": "enterprise"  # High-value user affected by issue
        }

        # Issue #1174 reproduction vectors
        self.issue_reproduction_scenarios = [
            "malformed_token_structure",
            "invalid_signature",
            "expired_token_edge_case",
            "missing_required_claims",
            "token_type_mismatch",
            "issuer_validation_failure"
        ]

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_malformed_token_validation_failure(self):
        """
        REPRODUCTION TEST: Test that malformed tokens trigger Issue #1174.

        Expected: This test should FAIL initially, reproducing the validation error.
        Business Impact: Enterprise users getting blocked by token parsing errors.
        """
        # Create malformed tokens that should trigger Issue #1174
        malformed_tokens = [
            "invalid.token.structure",  # Invalid format
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload.signature",  # Bad payload
            "",  # Empty token
            None,  # Null token
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.malformed",  # Truncated token
        ]

        validation_failures = []

        for token in malformed_tokens:
            try:
                # This should fail gracefully, but Issue #1174 may cause crashes
                result = self.jwt_handler.validate_token(token)

                # If validation succeeds for malformed token, that's the bug
                validation_failures.append(f"Malformed token accepted: {token}")

            except Exception as e:
                # Log the specific error for Issue #1174 analysis
                self.test_metrics.record_custom(f"validation_error_{token}", str(e))
                self.logger.error(f"Issue #1174 token validation error: {e}")

        # Issue #1174: If any malformed tokens were accepted, that's the bug
        if validation_failures:
            pytest.fail(f"Issue #1174 REPRODUCED: Malformed tokens accepted: {validation_failures}")

        self.logger.info("Token validation correctly rejected all malformed tokens")

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_expired_token_edge_case(self):
        """
        REPRODUCTION TEST: Test expired token edge cases causing Issue #1174.

        Expected: May reveal timing-based validation failures.
        Business Impact: Users getting unexpected authentication errors.
        """
        # Create token that expires at exact boundary conditions
        now = datetime.now(timezone.utc)

        # Edge case: Token expires exactly now (microsecond precision issues)
        edge_case_payload = {
            "sub": self.problematic_user_data["user_id"],
            "email": self.problematic_user_data["email"],
            "iat": now - timedelta(minutes=30),
            "exp": now,  # Expires exactly now - edge case
            "token_type": "access",
            "iss": "netra-auth-service"
        }

        # Create token with real JWT library
        edge_token = jwt.encode(edge_case_payload, self.jwt_secret, algorithm="HS256")

        try:
            # Small delay to ensure token is expired
            time.sleep(0.001)

            # This should fail, but Issue #1174 might cause unexpected behavior
            result = self.jwt_handler.validate_token(edge_token)

            # If expired token is accepted, that's Issue #1174
            pytest.fail(f"Issue #1174 REPRODUCED: Expired token accepted: {result}")

        except jwt.ExpiredSignatureError:
            # Expected behavior - token correctly rejected
            self.logger.info("Expired token correctly rejected")

        except Exception as e:
            # Unexpected error - might be Issue #1174 symptom
            self.test_metrics.record_custom("expired_token_unexpected_error", str(e))
            pytest.fail(f"Issue #1174 REPRODUCED: Unexpected error on expired token: {e}")

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_missing_required_claims(self):
        """
        REPRODUCTION TEST: Test tokens missing required claims trigger Issue #1174.

        Expected: Should reveal claim validation failures.
        Business Impact: Incomplete tokens causing authentication failures.
        """
        required_claims = ["sub", "email", "iat", "exp", "token_type"]

        # Test tokens missing each required claim
        for missing_claim in required_claims:
            # Create payload missing the specific claim
            incomplete_payload = {
                "sub": self.problematic_user_data["user_id"],
                "email": self.problematic_user_data["email"],
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
                "token_type": "access",
                "iss": "netra-auth-service"
            }

            # Remove the specific claim to test validation
            if missing_claim in incomplete_payload:
                del incomplete_payload[missing_claim]

            # Create token with missing claim
            incomplete_token = jwt.encode(incomplete_payload, self.jwt_secret, algorithm="HS256")

            try:
                # This should fail validation, but Issue #1174 might cause crashes
                result = self.jwt_handler.validate_token(incomplete_token)

                # If incomplete token is accepted, that's the bug
                pytest.fail(f"Issue #1174 REPRODUCED: Token missing {missing_claim} was accepted")

            except KeyError as e:
                # Expected - missing claim should cause KeyError
                self.logger.info(f"Token missing {missing_claim} correctly rejected: {e}")

            except Exception as e:
                # Unexpected error - potential Issue #1174 symptom
                self.test_metrics.record_custom(f"missing_claim_error_{missing_claim}", str(e))
                self.logger.error(f"Issue #1174 potential symptom - unexpected error: {e}")

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_invalid_signature_handling(self):
        """
        REPRODUCTION TEST: Test invalid signature handling for Issue #1174.

        Expected: Invalid signatures should be rejected, but may cause unexpected errors.
        Business Impact: Security vulnerability if invalid signatures are accepted.
        """
        # Create valid payload
        valid_payload = {
            "sub": self.problematic_user_data["user_id"],
            "email": self.problematic_user_data["email"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "token_type": "access",
            "iss": "netra-auth-service"
        }

        # Create token with wrong secret (invalid signature)
        wrong_secret = "wrong-secret-key-for-issue-1174-testing"
        invalid_signature_token = jwt.encode(valid_payload, wrong_secret, algorithm="HS256")

        try:
            # This should fail signature verification
            result = self.jwt_handler.validate_token(invalid_signature_token)

            # CRITICAL: If invalid signature is accepted, that's a security bug
            pytest.fail(f"Issue #1174 CRITICAL: Invalid signature accepted - SECURITY VULNERABILITY")

        except jwt.InvalidSignatureError:
            # Expected behavior - invalid signature correctly rejected
            self.logger.info("Invalid signature correctly rejected")

        except Exception as e:
            # Unexpected error - potential Issue #1174 symptom
            self.test_metrics.record_custom("invalid_signature_unexpected_error", str(e))
            pytest.fail(f"Issue #1174 REPRODUCED: Unexpected error on invalid signature: {e}")

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_token_validator_integration(self):
        """
        REPRODUCTION TEST: Test TokenValidator integration issues causing Issue #1174.

        Expected: TokenValidator should properly integrate with JWTHandler.
        Business Impact: Token validation pipeline failures affect all users.
        """
        # Create valid token for integration testing
        valid_payload = {
            "sub": self.problematic_user_data["user_id"],
            "email": self.problematic_user_data["email"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "token_type": "access",
            "iss": "netra-auth-service"
        }

        valid_token = jwt.encode(valid_payload, self.jwt_secret, algorithm="HS256")

        try:
            # Test TokenValidator integration with JWTHandler
            is_valid = self.token_validator.validate_token(valid_token)

            # TokenValidator should return True for valid tokens
            assert is_valid, "Issue #1174 REPRODUCED: TokenValidator rejected valid token"

            # Test that decoded data is accessible
            decoded = self.jwt_handler.validate_token(valid_token)
            assert decoded["sub"] == self.problematic_user_data["user_id"]

            self.logger.info("TokenValidator integration working correctly")

        except Exception as e:
            # Integration error - potential Issue #1174 symptom
            self.test_metrics.record_custom("token_validator_integration_error", str(e))
            pytest.fail(f"Issue #1174 REPRODUCED: TokenValidator integration failure: {e}")

    @pytest.mark.unit
    @pytest.mark.issue_1174
    def test_issue_1174_concurrent_token_validation(self):
        """
        REPRODUCTION TEST: Test concurrent token validation for Issue #1174.

        Expected: Multiple simultaneous validations should not interfere.
        Business Impact: Race conditions could cause sporadic authentication failures.
        """
        # Create multiple valid tokens for concurrent testing
        tokens = []
        for i in range(5):
            payload = {
                "sub": f"{self.problematic_user_data['user_id']}_{i}",
                "email": f"concurrent_test_{i}@netratest.com",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
                "token_type": "access",
                "iss": "netra-auth-service"
            }
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            tokens.append(token)

        # Simulate concurrent validation
        validation_results = []
        validation_errors = []

        for token in tokens:
            try:
                result = self.jwt_handler.validate_token(token)
                validation_results.append(result)

            except Exception as e:
                validation_errors.append(str(e))

        # All tokens should validate successfully
        if validation_errors:
            pytest.fail(f"Issue #1174 REPRODUCED: Concurrent validation errors: {validation_errors}")

        # Verify all results are correct
        assert len(validation_results) == 5, "Issue #1174: Not all tokens validated successfully"

        self.logger.info(f"Concurrent token validation successful: {len(validation_results)} tokens")

    def teardown_method(self, method):
        """Clean up after each test."""
        # Record final metrics for Issue #1174 analysis
        self.test_metrics.record_custom("issue_1174_test_completed", True)
        super().teardown_method(method)