"""
Direct JWT Integration Tests - Simple and Reliable SSOT Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure JWT authentication core functionality is working
- Value Impact: Validates the foundation of all authentication without complex dependencies
- Strategic Impact: Core platform reliability - JWT is the foundation of all auth

This test suite validates JWT functionality directly using the JWT handler
without relying on potentially unreliable API endpoints, ensuring the core
authentication mechanism works correctly.

CRITICAL: Tests core JWT operations that all authentication depends on.
"""

import logging
import time
import jwt as pyjwt
from datetime import datetime, timedelta, UTC
from typing import Dict, Any

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestAuthJWTDirectIntegration(SSotBaseTestCase):
    """
    Direct JWT Integration Tests using JWT handler without external dependencies.
    
    Tests core JWT functionality that all authentication depends on,
    ensuring tokens can be created, validated, and managed correctly.
    """
    
    @pytest.fixture
    def jwt_handler(self):
        """Provide JWT handler for direct testing."""
        handler = JWTHandler()
        yield handler
    
    @pytest.fixture
    def test_user_data(self):
        """Provide test user data."""
        return {
            "user_id": "jwt-direct-test-user-001",
            "email": "jwt.direct@example.com",
            "permissions": ["read", "write", "admin"]
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_creation_and_validation_direct(self, jwt_handler, test_user_data):
        """
        BVJ: All Segments - Core JWT authentication validation
        Direct integration test for JWT token creation and validation.
        
        Tests the fundamental JWT operations without external API calls,
        ensuring the core authentication mechanism works correctly.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_direct_integration")
        self.record_metric("test_focus", "creation_and_validation")
        
        user_data = test_user_data
        
        # Step 1: Create access token
        start_time = time.time()
        access_token = jwt_handler.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        token_creation_time = time.time() - start_time
        
        assert access_token is not None, "JWT handler should create access token"
        assert isinstance(access_token, str), "Access token should be string"
        assert len(access_token) > 100, "JWT token should be substantial length"
        
        self.record_metric("token_creation_time_ms", token_creation_time * 1000)
        self.record_metric("access_token_created", True)
        
        # Step 2: Validate token structure
        # Decode without verification to check structure
        unverified_payload = pyjwt.decode(access_token, options={"verify_signature": False})
        
        required_claims = ["sub", "email", "exp", "iat", "permissions", "iss", "aud"]
        for claim in required_claims:
            assert claim in unverified_payload, f"Token missing required claim: {claim}"
        
        assert unverified_payload["sub"] == user_data["user_id"], "Subject should match user ID"
        assert unverified_payload["email"] == user_data["email"], "Email should match"
        assert unverified_payload["permissions"] == user_data["permissions"], "Permissions should match"
        assert unverified_payload["iss"] == "netra-auth-service", "Issuer should be auth service"
        
        self.record_metric("token_structure_valid", True)
        
        # Step 3: Validate token via JWT handler
        start_time = time.time()
        validation_result = jwt_handler.validate_token(access_token, "access")
        token_validation_time = time.time() - start_time
        
        assert validation_result is not None, "JWT validation should return result"
        assert validation_result.get("sub") == user_data["user_id"], "Validated user ID should match"
        assert validation_result.get("email") == user_data["email"], "Validated email should match"
        assert validation_result.get("permissions") == user_data["permissions"], "Validated permissions should match"
        
        self.record_metric("token_validation_time_ms", token_validation_time * 1000)
        self.record_metric("token_validation_success", True)
        
        # Step 4: Test token expiration
        exp_timestamp = validation_result.get("exp")
        current_time = datetime.now(UTC).timestamp()
        time_to_expiry = exp_timestamp - current_time
        
        assert time_to_expiry > 290, f"Token should expire in more than ~5 minutes, got {time_to_expiry:.0f}s"
        assert time_to_expiry < 3600, f"Token should expire in less than 1 hour, got {time_to_expiry:.0f}s"
        
        self.record_metric("token_expiry_reasonable", True)
        self.record_metric("time_to_expiry_seconds", int(time_to_expiry))
        
        logger.info(" PASS:  Direct JWT token creation and validation working correctly")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_refresh_token_cycle_direct(self, jwt_handler, test_user_data):
        """
        BVJ: All Segments - Session continuity via token refresh
        Direct integration test for JWT refresh token cycle.
        
        Tests the token refresh mechanism that ensures users stay logged in
        without having to re-authenticate frequently.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_refresh_direct")
        self.record_metric("test_focus", "refresh_token_cycle")
        
        user_data = test_user_data
        
        # Step 1: Create initial tokens
        access_token = jwt_handler.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        refresh_token = jwt_handler.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        assert access_token is not None, "Should create access token"
        assert refresh_token is not None, "Should create refresh token"
        assert access_token != refresh_token, "Access and refresh tokens should be different"
        
        self.record_metric("initial_tokens_created", True)
        
        # Step 2: Validate both tokens
        access_validation = jwt_handler.validate_token(access_token, "access")
        refresh_validation = jwt_handler.validate_token(refresh_token, "refresh")
        
        assert access_validation is not None, "Access token should be valid"
        assert refresh_validation is not None, "Refresh token should be valid"
        
        assert access_validation.get("token_type") == "access", "Access token should have correct type"
        assert refresh_validation.get("token_type") == "refresh", "Refresh token should have correct type"
        
        self.record_metric("token_types_correct", True)
        
        # Step 3: Use refresh token to generate new access token
        new_access_token, new_refresh_token = jwt_handler.refresh_access_token(refresh_token)
        
        assert new_access_token is not None, "Should generate new access token"
        assert new_refresh_token is not None, "Should generate new refresh token"
        assert new_access_token != access_token, "New access token should be different from original"
        assert new_refresh_token != refresh_token, "New refresh token should be different from original"
        
        # Step 4: Validate new tokens work
        new_access_validation = jwt_handler.validate_token(new_access_token, "access")
        new_refresh_validation = jwt_handler.validate_token(new_refresh_token, "refresh")
        
        assert new_access_validation is not None, "New access token should be valid"
        assert new_refresh_validation is not None, "New refresh token should be valid"
        
        # Verify user data preserved in refresh
        assert new_access_validation.get("sub") == user_data["user_id"], "User ID should be preserved"
        assert new_access_validation.get("email") == user_data["email"], "Email should be preserved"
        assert new_access_validation.get("permissions") == user_data["permissions"], "Permissions should be preserved"
        
        self.record_metric("refresh_cycle_success", True)
        self.record_metric("user_data_preserved", True)
        
        logger.info(" PASS:  Direct JWT refresh token cycle working correctly")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_security_validation_direct(self, jwt_handler):
        """
        BVJ: Enterprise Segment - Security validation for token protection
        Direct integration test for JWT security validation.
        
        Tests that the JWT handler properly rejects malicious or invalid tokens
        to prevent security vulnerabilities.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_security_direct")
        self.record_metric("test_focus", "security_validation")
        
        # Create valid token for comparison
        valid_token = jwt_handler.create_access_token(
            user_id="security-test-user",
            email="security@example.com",
            permissions=["read"]
        )
        
        # Verify valid token works
        valid_result = jwt_handler.validate_token(valid_token, "access")
        assert valid_result is not None, "Valid token should be accepted"
        
        # Test invalid token scenarios
        invalid_scenarios = [
            {
                "name": "empty_token",
                "token": "",
                "description": "Empty token should be rejected"
            },
            {
                "name": "null_token",
                "token": None,
                "description": "Null token should be rejected"
            },
            {
                "name": "malformed_token",
                "token": "not.a.jwt.token.at.all",
                "description": "Malformed token should be rejected"
            },
            {
                "name": "wrong_segments",
                "token": "only.two.segments",
                "description": "Wrong number of segments should be rejected"
            },
            {
                "name": "invalid_base64",
                "token": "invalid!@#.base64!@#.encoding!@#",
                "description": "Invalid base64 encoding should be rejected"
            }
        ]
        
        security_failures = []
        
        for scenario in invalid_scenarios:
            scenario_name = scenario["name"]
            token = scenario["token"]
            description = scenario["description"]
            
            try:
                result = jwt_handler.validate_token(token, "access")
                
                if result is not None:
                    security_failures.append({
                        "scenario": scenario_name,
                        "token": str(token)[:20] + "..." if token else str(token),
                        "description": description,
                        "result": result
                    })
                else:
                    self.record_metric(f"security_scenario_{scenario_name}", "correctly_rejected")
                
            except Exception as e:
                # Exceptions are acceptable for invalid tokens
                self.record_metric(f"security_scenario_{scenario_name}", "correctly_rejected_with_exception")
        
        # Assert no security failures
        assert len(security_failures) == 0, (
            f"SECURITY FAILURE: {len(security_failures)} invalid tokens were not rejected: {security_failures}"
        )
        
        # Test wrong token type scenario
        access_token = jwt_handler.create_access_token("user", "user@example.com", ["read"])
        
        # Try to validate access token as refresh token (should fail)
        wrong_type_result = jwt_handler.validate_token(access_token, "refresh")
        assert wrong_type_result is None, "Wrong token type should be rejected"
        
        self.record_metric("jwt_security_validation", "comprehensive_success")
        self.record_metric("security_scenarios_tested", len(invalid_scenarios))
        
        logger.info(f" PASS:  Direct JWT security validation successful ({len(invalid_scenarios)} scenarios tested)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_multi_user_isolation_direct(self, jwt_handler):
        """
        BVJ: Mid/Enterprise Segments - Multi-user token isolation
        Direct integration test for JWT multi-user isolation.
        
        Tests that tokens for different users maintain proper isolation
        and cannot be confused or mixed up.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_multi_user_direct")
        self.record_metric("test_focus", "user_isolation")
        
        # Create tokens for multiple users
        users_data = [
            {
                "user_id": "isolation-user-001",
                "email": "user1@example.com",
                "permissions": ["read", "write"]
            },
            {
                "user_id": "isolation-user-002", 
                "email": "user2@example.com",
                "permissions": ["read"]
            },
            {
                "user_id": "isolation-user-003",
                "email": "user3@example.com",
                "permissions": ["admin"]
            }
        ]
        
        user_tokens = {}
        
        # Create tokens for all users
        for user_data in users_data:
            access_token = jwt_handler.create_access_token(
                user_id=user_data["user_id"],
                email=user_data["email"],
                permissions=user_data["permissions"]
            )
            
            assert access_token is not None, f"Should create token for user {user_data['user_id']}"
            user_tokens[user_data["user_id"]] = {
                "token": access_token,
                "expected_data": user_data
            }
        
        self.record_metric("multi_user_tokens_created", len(user_tokens))
        
        # Validate each token contains correct user data
        isolation_violations = []
        
        for user_id, token_info in user_tokens.items():
            token = token_info["token"]
            expected_data = token_info["expected_data"]
            
            validation_result = jwt_handler.validate_token(token, "access")
            
            assert validation_result is not None, f"Token should be valid for user {user_id}"
            
            # Check user isolation
            if validation_result.get("sub") != expected_data["user_id"]:
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_sub": expected_data["user_id"],
                    "actual_sub": validation_result.get("sub"),
                    "violation": "user_id_mismatch"
                })
            
            if validation_result.get("email") != expected_data["email"]:
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_email": expected_data["email"],
                    "actual_email": validation_result.get("email"),
                    "violation": "email_mismatch"
                })
            
            if validation_result.get("permissions") != expected_data["permissions"]:
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_permissions": expected_data["permissions"],
                    "actual_permissions": validation_result.get("permissions"),
                    "violation": "permissions_mismatch"
                })
        
        # Verify no isolation violations
        assert len(isolation_violations) == 0, (
            f"USER ISOLATION FAILURE: {len(isolation_violations)} violations detected: {isolation_violations}"
        )
        
        # Verify tokens are unique
        all_tokens = [info["token"] for info in user_tokens.values()]
        unique_tokens = set(all_tokens)
        
        assert len(unique_tokens) == len(all_tokens), (
            f"Token reuse detected: {len(all_tokens)} tokens, {len(unique_tokens)} unique"
        )
        
        self.record_metric("user_isolation_violations", len(isolation_violations))
        self.record_metric("token_uniqueness_verified", True)
        self.record_metric("jwt_multi_user_isolation", "success")
        
        logger.info(f" PASS:  Direct JWT multi-user isolation successful ({len(users_data)} users tested)")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_jwt_performance_direct(self, jwt_handler, test_user_data):
        """
        BVJ: All Segments - JWT performance for user experience
        Direct integration test for JWT performance.
        
        Tests that JWT operations complete within acceptable time limits
        to ensure good user experience and system responsiveness.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_performance_direct")
        self.record_metric("test_focus", "operation_timing")
        
        user_data = test_user_data
        
        # Test token creation performance
        creation_times = []
        num_creations = 10
        
        for i in range(num_creations):
            start_time = time.time()
            
            token = jwt_handler.create_access_token(
                user_id=f"{user_data['user_id']}-{i}",
                email=user_data["email"],
                permissions=user_data["permissions"]
            )
            
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            assert token is not None, f"Token creation {i} should succeed"
        
        # Test token validation performance
        test_token = jwt_handler.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        validation_times = []
        num_validations = 20
        
        for i in range(num_validations):
            start_time = time.time()
            
            result = jwt_handler.validate_token(test_token, "access")
            
            validation_time = time.time() - start_time
            validation_times.append(validation_time)
            
            assert result is not None, f"Token validation {i} should succeed"
        
        # Analyze performance
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        avg_validation_time = sum(validation_times) / len(validation_times)
        max_validation_time = max(validation_times)
        
        # Performance requirements (generous for comprehensive testing)
        assert avg_creation_time < 0.1, (
            f"Average token creation time {avg_creation_time:.3f}s exceeds 0.1s limit"
        )
        
        assert avg_validation_time < 0.1, (
            f"Average token validation time {avg_validation_time:.3f}s exceeds 0.1s limit"
        )
        
        assert max_creation_time < 1.0, (
            f"Maximum token creation time {max_creation_time:.3f}s exceeds 1.0s limit"
        )
        
        assert max_validation_time < 1.0, (
            f"Maximum token validation time {max_validation_time:.3f}s exceeds 1.0s limit"
        )
        
        self.record_metric("avg_creation_time_ms", avg_creation_time * 1000)
        self.record_metric("max_creation_time_ms", max_creation_time * 1000)
        self.record_metric("avg_validation_time_ms", avg_validation_time * 1000)
        self.record_metric("max_validation_time_ms", max_validation_time * 1000)
        self.record_metric("jwt_performance", "acceptable")
        
        logger.info(
            f" PASS:  Direct JWT performance acceptable "
            f"(creation avg: {avg_creation_time:.3f}s, validation avg: {avg_validation_time:.3f}s)"
        )
    
    def teardown_method(self, method=None):
        """Enhanced teardown with JWT-specific metrics validation."""
        super().teardown_method(method)
        
        # Validate JWT test metrics were recorded
        metrics = self.get_all_metrics()
        
        if hasattr(method, '__name__') and method.__name__:
            method_name = method.__name__
            
            # All JWT tests must record these metrics
            required_metrics = ["test_category", "test_focus"]
            for metric in required_metrics:
                assert metric in metrics, f"JWT test {method_name} must record {metric} metric"
            
            # JWT-specific validations
            assert "jwt" in metrics.get("test_category", "").lower(), "JWT tests must have jwt in test_category"
        
        # Log JWT performance and functional metrics
        jwt_metrics = {
            k: v for k, v in metrics.items() 
            if any(keyword in k.lower() for keyword in ["jwt", "token", "time_ms", "performance"])
        }
        
        if jwt_metrics:
            logger.info(f"JWT direct integration test metrics: {jwt_metrics}")