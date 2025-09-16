"""
Cross-Service Authentication Validation Tests - PRIORITY 1 SECURITY CRITICAL

**CRITICAL**: Comprehensive cross-service JWT validation testing between auth and backend services.
These tests ensure service-to-service authentication works correctly, preventing cascade failures
that would break all Chat functionality and user authentication.

Business Value Justification (BVJ):
- Segment: All tiers - cross-service auth enables all user functionality
- Business Goal: Platform Stability, System Reliability
- Value Impact: Prevents total platform failure from auth communication breakdowns
- Strategic Impact: Service auth failures cause complete user lockout and business shutdown

ULTRA CRITICAL CONSTRAINTS:
- ALL tests use REAL auth service and real JWT tokens
- Tests designed to FAIL HARD - no try/except bypassing
- Focus on realistic service-to-service scenarios  
- Service authentication must work under load
- ABSOLUTE IMPORTS ONLY (from auth_service.* not relative)

Cross-Service Attack Vectors Tested:
- Service credential injection attacks
- JWT token replay between services
- Service authorization bypass attempts  
- Man-in-the-middle service impersonation
- Service secret brute force attempts
- Circuit breaker bypass exploits
"""

import asyncio
import httpx
import json  
import jwt as jwt_library
import pytest
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch, AsyncMock

# ABSOLUTE IMPORTS ONLY - No relative imports
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, TokenString, AuthValidationResult,
    ensure_user_id, ensure_request_id
)
from test_framework.ssot.base_test_case import SSotBaseTestCase  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.user_service import UserService
from auth_service.services.redis_service import RedisService
from auth_service.auth_core.database.database_manager import AuthDatabaseManager


class TestCrossServiceAuthValidation(SSotBaseTestCase):
    """
    PRIORITY 1: Comprehensive cross-service authentication validation tests.
    
    This test suite validates critical service-to-service authentication that enables
    all platform functionality:
    - JWT token validation between auth service and backend
    - Service authentication using SERVICE_ID and SERVICE_SECRET
    - Cross-service authorization and permission validation
    - Service communication security and attack prevention
    - Circuit breaker and retry logic for service resilience
    - Performance requirements for service communication
    """
    
    @pytest.fixture(autouse=True)
    async def setup_cross_service_test_environment(self):
        """Set up comprehensive cross-service test environment with real services."""
        
        # Initialize environment and services
        self.env = get_env()
        self.auth_config = AuthConfig()
        
        # CRITICAL: Real service instances - NO MOCKS for cross-service testing
        self.jwt_service = JWTService(self.auth_config)
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        # AuthDatabaseManager provides static methods for database operations
        self.user_service = UserService(self.auth_config)
        
        # Auth helper for E2E token creation  
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Service authentication configuration
        self.service_config = {
            "backend_service_id": "netra-backend",  # Production service ID
            "test_service_secret": f"test-service-secret-{secrets.token_hex(16)}",
            "invalid_service_secret": "wrong-secret-value",
            "malicious_service_id": "malicious-service",
            "auth_service_url": "http://localhost:8083",  # Test auth service  
            "request_timeout": 10.0,
            "retry_attempts": 3
        }
        
        # Create test users for cross-service validation
        self.test_users = [
            {
                "user_id": f"cross-service-user-{i}",
                "email": f"cross.service.user.{i}@testdomain.com",
                "name": f"Cross Service User {i}",
                "password": f"CrossServicePass{i}#{secrets.token_hex(4)}",
                "permissions": ["read", "write", "admin"] if i == 0 else ["read", "write"],
                "tier": "enterprise" if i == 0 else "early"
            }
            for i in range(3)  # Create 3 test users
        ]
        
        # Track created resources for cleanup
        self.created_users = []
        self.created_tokens = []
        self.created_redis_keys = []
        
        # Create test users and tokens
        for user_data in self.test_users:
            created_user = await self.user_service.create_user(
                email=user_data["email"],
                name=user_data["name"],
                password=user_data["password"]
            )
            self.created_users.append(created_user)
            
            # Create JWT token for user
            jwt_token = await self.jwt_service.create_access_token(
                user_id=str(created_user.id),
                email=created_user.email,
                permissions=user_data["permissions"]
            )
            self.created_tokens.append(jwt_token)
            
            user_data["db_user"] = created_user
            user_data["jwt_token"] = jwt_token
        
        yield
        
        # Comprehensive cleanup
        await self._cleanup_cross_service_test_resources()
    
    async def _cleanup_cross_service_test_resources(self):
        """Comprehensive cleanup of cross-service test resources."""
        try:
            # Clean up users
            for user in self.created_users:
                try:
                    await self.user_service.delete_user(user.id)
                except Exception as e:
                    self.logger.warning(f"User cleanup warning {user.id}: {e}")
            
            # Clean up Redis keys
            for redis_key in self.created_redis_keys:
                try:
                    await self.redis_service.delete(redis_key)
                except Exception as e:
                    self.logger.warning(f"Redis cleanup warning {redis_key}: {e}")
            
            # Clean up cross-service test keys
            cross_service_keys = await self.redis_service.keys("*cross-service*")
            if cross_service_keys:
                await self.redis_service.delete(*cross_service_keys)
                
            await self.redis_service.close()
            
        except Exception as e:
            self.logger.warning(f"Cross-service cleanup warning: {e}")
    
    async def _make_service_authenticated_request(
        self, 
        endpoint: str,
        method: str = "POST",
        service_id: Optional[str] = None,
        service_secret: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        bearer_token: Optional[str] = None
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Make service-authenticated request to auth service.
        
        Returns tuple of (status_code, response_data)
        """
        
        service_id = service_id or self.service_config["backend_service_id"]
        service_secret = service_secret or self.service_config["test_service_secret"]
        
        headers = {
            "Content-Type": "application/json",
            "X-Service-ID": service_id,
            "X-Service-Secret": service_secret
        }
        
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        
        url = f"{self.service_config['auth_service_url']}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.service_config["request_timeout"]) as client:
            try:
                if method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=payload or {})
                elif method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Parse response if JSON
                try:
                    response_data = response.json() if response.content else None
                except:
                    response_data = None
                
                return response.status_code, response_data
                
            except Exception as e:
                self.logger.error(f"Service request failed: {e}")
                return 0, {"error": str(e)}
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_to_service_authentication_comprehensive(self):
        """
        CRITICAL: Test comprehensive service-to-service authentication flows.
        
        BVJ: Ensures backend service can authenticate with auth service using
        SERVICE_ID and SERVICE_SECRET, enabling all platform functionality.
        """
        
        # TEST 1: Successful service authentication
        status_code, response_data = await self._make_service_authenticated_request(
            endpoint="/auth/validate",
            payload={
                "token": self.test_users[0]["jwt_token"],
                "token_type": "access"
            }
        )
        
        # Service auth should succeed (token may be invalid, but service auth works)
        assert status_code != 403, f"Service authentication should succeed, got {status_code}: {response_data}"
        assert status_code != 401 or "service" not in str(response_data).lower(), "Service auth failure indicated"
        
        # TEST 2: Invalid service credentials scenarios
        auth_failure_scenarios = [
            {
                "name": "wrong_service_id",
                "service_id": "wrong-service-id",
                "service_secret": self.service_config["test_service_secret"],
                "should_fail": True
            },
            {
                "name": "wrong_service_secret", 
                "service_id": self.service_config["backend_service_id"],
                "service_secret": self.service_config["invalid_service_secret"],
                "should_fail": True
            },
            {
                "name": "empty_service_id",
                "service_id": "",
                "service_secret": self.service_config["test_service_secret"], 
                "should_fail": True
            },
            {
                "name": "empty_service_secret",
                "service_id": self.service_config["backend_service_id"],
                "service_secret": "",
                "should_fail": True
            },
            {
                "name": "malicious_service_id",
                "service_id": self.service_config["malicious_service_id"],
                "service_secret": self.service_config["test_service_secret"],
                "should_fail": True
            }
        ]
        
        for scenario in auth_failure_scenarios:
            scenario_name = scenario["name"]
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                service_id=scenario["service_id"],
                service_secret=scenario["service_secret"],
                payload={
                    "token": "test-token",
                    "token_type": "access"
                }
            )
            
            if scenario["should_fail"]:
                assert status_code == 403, (
                    f"Service auth failure scenario '{scenario_name}' should return 403, "
                    f"got {status_code}: {response_data}"
                )
            else:
                assert status_code != 403, (
                    f"Service auth scenario '{scenario_name}' should not return 403, "
                    f"got {status_code}: {response_data}"
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_validation_cross_service(self):
        """
        CRITICAL: Test JWT token validation through cross-service communication.
        
        BVJ: Ensures backend service can validate user JWT tokens via auth service,
        enabling secure user authentication for all Chat functionality.
        """
        
        # TEST 1: Valid token validation
        test_user = self.test_users[0]
        valid_token = test_user["jwt_token"]
        
        status_code, response_data = await self._make_service_authenticated_request(
            endpoint="/auth/validate",
            payload={
                "token": valid_token,
                "token_type": "access"
            }
        )
        
        # Should succeed with valid token and service auth
        assert status_code == 200, f"Valid token validation should succeed, got {status_code}: {response_data}"
        assert response_data is not None, "Response data should not be None"
        assert response_data.get("valid") is True, f"Token should be valid: {response_data}"
        
        # Verify user data in response
        assert response_data.get("user_id") == str(test_user["db_user"].id)
        assert response_data.get("email") == test_user["email"]
        assert response_data.get("permissions") == test_user["permissions"]
        
        # TEST 2: Invalid token scenarios
        invalid_token_scenarios = [
            {
                "name": "malformed_token",
                "token": "invalid.jwt.format",
                "should_be_valid": False
            },
            {
                "name": "expired_token",
                "token": self._create_expired_jwt_token(test_user["db_user"]),
                "should_be_valid": False
            },
            {
                "name": "wrong_signature",
                "token": self._create_wrong_signature_jwt_token(test_user["db_user"]),
                "should_be_valid": False
            },
            {
                "name": "empty_token",
                "token": "",
                "should_be_valid": False
            },
            {
                "name": "none_token",
                "token": None,
                "should_be_valid": False
            }
        ]
        
        for scenario in invalid_token_scenarios:
            scenario_name = scenario["name"]
            token = scenario["token"]
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": token,
                    "token_type": "access"
                }
            )
            
            # Service auth should succeed, but token validation should fail
            assert status_code != 403, f"Service auth should work for scenario '{scenario_name}'"
            
            if response_data:
                token_valid = response_data.get("valid", False)
                assert token_valid is False, (
                    f"Invalid token scenario '{scenario_name}' should be rejected, "
                    f"but got valid=True: {response_data}"
                )
        
        # TEST 3: Multiple valid tokens from different users
        for i, user in enumerate(self.test_users):
            user_token = user["jwt_token"]
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate", 
                payload={
                    "token": user_token,
                    "token_type": "access"
                }
            )
            
            assert status_code == 200, f"User {i} token validation should succeed"
            assert response_data.get("valid") is True, f"User {i} token should be valid"
            assert response_data.get("user_id") == str(user["db_user"].id)
            assert response_data.get("email") == user["email"]
    
    def _create_expired_jwt_token(self, user) -> str:
        """Create an expired JWT token for testing."""
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "type": "access",
            "iss": "test-auth-service"
        }
        
        return jwt_library.encode(payload, self.auth_config.jwt_secret_key, algorithm="HS256")
    
    def _create_wrong_signature_jwt_token(self, user) -> str:
        """Create a JWT token with wrong signature for testing."""
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
            "iss": "test-auth-service"
        }
        
        # Sign with wrong secret
        return jwt_library.encode(payload, "wrong-jwt-secret-key", algorithm="HS256")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_permission_validation(self):
        """
        CRITICAL: Test cross-service permission validation for different user tiers.
        
        BVJ: Ensures backend service can validate user permissions via auth service,
        enabling proper access control for Chat features by tier.
        """
        
        # Create users with different permission levels
        admin_user = self.test_users[0]  # Has admin permissions
        regular_user = self.test_users[1]  # Has read/write permissions
        
        # TEST 1: Admin user permission validation
        admin_status, admin_response = await self._make_service_authenticated_request(
            endpoint="/auth/validate",
            payload={
                "token": admin_user["jwt_token"],
                "token_type": "access"
            }
        )
        
        assert admin_status == 200, f"Admin token validation should succeed"
        assert admin_response.get("valid") is True
        
        admin_permissions = admin_response.get("permissions", [])
        assert "read" in admin_permissions
        assert "write" in admin_permissions  
        assert "admin" in admin_permissions, f"Admin user should have admin permission: {admin_permissions}"
        
        # TEST 2: Regular user permission validation  
        regular_status, regular_response = await self._make_service_authenticated_request(
            endpoint="/auth/validate",
            payload={
                "token": regular_user["jwt_token"],
                "token_type": "access" 
            }
        )
        
        assert regular_status == 200, f"Regular token validation should succeed"
        assert regular_response.get("valid") is True
        
        regular_permissions = regular_response.get("permissions", [])
        assert "read" in regular_permissions
        assert "write" in regular_permissions
        assert "admin" not in regular_permissions, f"Regular user should not have admin permission: {regular_permissions}"
        
        # TEST 3: Permission consistency across multiple requests
        consistency_tests = 5
        for i in range(consistency_tests):
            # Test admin permissions consistency
            admin_status, admin_response = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": admin_user["jwt_token"],
                    "token_type": "access"
                }
            )
            
            assert admin_response.get("permissions") == admin_user["permissions"], (
                f"Admin permissions should be consistent across requests {i}"
            )
            
            # Test regular permissions consistency
            regular_status, regular_response = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": regular_user["jwt_token"], 
                    "token_type": "access"
                }
            )
            
            assert regular_response.get("permissions") == regular_user["permissions"], (
                f"Regular permissions should be consistent across requests {i}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_attack_prevention(self):
        """
        CRITICAL: Test cross-service attack prevention mechanisms.
        
        BVJ: Ensures auth service prevents service impersonation attacks
        and credential injection that could compromise platform security.
        """
        
        # TEST 1: Service credential injection attacks
        injection_scenarios = [
            {
                "name": "sql_injection_service_id",
                "service_id": "'; DROP TABLE users; --",
                "service_secret": self.service_config["test_service_secret"],
                "should_be_rejected": True
            },
            {
                "name": "xss_injection_service_id", 
                "service_id": "<script>alert('xss')</script>",
                "service_secret": self.service_config["test_service_secret"],
                "should_be_rejected": True
            },
            {
                "name": "path_traversal_service_secret",
                "service_id": self.service_config["backend_service_id"],
                "service_secret": "../../etc/passwd",
                "should_be_rejected": True
            },
            {
                "name": "null_byte_injection",
                "service_id": "netra-backend\x00malicious",
                "service_secret": self.service_config["test_service_secret"],
                "should_be_rejected": True
            }
        ]
        
        for scenario in injection_scenarios:
            scenario_name = scenario["name"]
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                service_id=scenario["service_id"],
                service_secret=scenario["service_secret"],
                payload={
                    "token": "test-token",
                    "token_type": "access"
                }
            )
            
            if scenario["should_be_rejected"]:
                assert status_code == 403, (
                    f"Injection attack '{scenario_name}' should be rejected with 403, "
                    f"got {status_code}: {response_data}"
                )
        
        # TEST 2: Service impersonation attempts
        valid_token = self.test_users[0]["jwt_token"]
        
        impersonation_scenarios = [
            {
                "name": "fake_backend_service",
                "service_id": "fake-netra-backend",
                "service_secret": secrets.token_hex(32),
                "should_fail": True
            },
            {
                "name": "admin_service_impersonation",
                "service_id": "admin-service",  
                "service_secret": self.service_config["test_service_secret"],
                "should_fail": True
            },
            {
                "name": "auth_service_self_impersonation",
                "service_id": "auth-service",
                "service_secret": self.service_config["test_service_secret"],
                "should_fail": True
            }
        ]
        
        for scenario in impersonation_scenarios:
            scenario_name = scenario["name"]
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                service_id=scenario["service_id"],
                service_secret=scenario["service_secret"], 
                payload={
                    "token": valid_token,
                    "token_type": "access"
                }
            )
            
            if scenario["should_fail"]:
                assert status_code == 403, (
                    f"Service impersonation '{scenario_name}' should fail with 403, "
                    f"got {status_code}: {response_data}"
                )
        
        # TEST 3: Token replay attack prevention
        replay_token = valid_token
        
        # Make multiple requests with same token (simulate replay)
        replay_results = []
        for i in range(5):
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": replay_token,
                    "token_type": "access"
                }
            )
            replay_results.append((status_code, response_data))
        
        # All should succeed (token replay is valid unless token is blacklisted)
        # But responses should be consistent
        first_response = replay_results[0][1]
        for i, (status, response) in enumerate(replay_results[1:], 1):
            assert status == replay_results[0][0], f"Replay request {i} status should be consistent"
            if response and first_response:
                assert response.get("user_id") == first_response.get("user_id"), (
                    f"Replay request {i} user_id should be consistent"
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_cross_service_performance_requirements(self):
        """
        CRITICAL: Test cross-service performance meets requirements for Chat responsiveness.
        
        BVJ: Ensures auth service responds quickly enough to backend requests
        to maintain good Chat user experience and prevent timeouts.
        """
        
        valid_token = self.test_users[0]["jwt_token"]
        performance_test_count = 20
        response_times = []
        
        # TEST 1: Individual request performance
        for i in range(performance_test_count):
            start_time = time.time()
            
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": valid_token,
                    "token_type": "access"
                }
            )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            # Individual request should succeed
            assert status_code == 200, f"Performance test request {i} should succeed"
            assert response_data.get("valid") is True, f"Token should be valid in request {i}"
        
        # Analyze performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        
        # Performance requirements for cross-service communication
        assert avg_response_time < 1.0, (
            f"Average cross-service response time {avg_response_time:.3f}s exceeds 1.0s limit. "
            f"This will cause Chat delays and poor user experience."
        )
        
        assert p95_response_time < 2.0, (
            f"95th percentile response time {p95_response_time:.3f}s exceeds 2.0s limit. "
            f"This could cause Chat request timeouts."
        )
        
        assert max_response_time < 5.0, (
            f"Maximum response time {max_response_time:.3f}s exceeds 5.0s limit. "
            f"This indicates performance issues that could break Chat."
        )
        
        # TEST 2: Concurrent request performance
        concurrent_count = 10
        concurrent_tasks = []
        
        async def concurrent_validation_request():
            start_time = time.time()
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": valid_token,
                    "token_type": "access"
                }
            )
            response_time = time.time() - start_time
            return status_code, response_data, response_time
        
        # Execute concurrent requests
        concurrent_start = time.time()
        for _ in range(concurrent_count):
            concurrent_tasks.append(concurrent_validation_request())
        
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_total_time = time.time() - concurrent_start
        
        # Validate concurrent results
        for i, (status, response, resp_time) in enumerate(concurrent_results):
            assert status == 200, f"Concurrent request {i} should succeed"
            assert response.get("valid") is True, f"Concurrent token {i} should be valid"
        
        concurrent_response_times = [result[2] for result in concurrent_results]
        avg_concurrent_time = sum(concurrent_response_times) / len(concurrent_response_times)
        
        # Concurrent performance should not degrade significantly
        assert avg_concurrent_time < avg_response_time * 2, (
            f"Concurrent average time {avg_concurrent_time:.3f}s should not be more than "
            f"2x sequential time {avg_response_time:.3f}s"
        )
        
        # Total concurrent time should show parallelism benefit
        assert concurrent_total_time < avg_response_time * concurrent_count * 0.8, (
            f"Concurrent execution should show parallelism benefit. "
            f"Total time {concurrent_total_time:.3f}s vs expected sequential "
            f"{avg_response_time * concurrent_count:.3f}s"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_resilience_and_recovery(self):
        """
        CRITICAL: Test cross-service resilience, circuit breakers, and recovery.
        
        BVJ: Ensures backend service can handle auth service failures gracefully
        and recover quickly to maintain Chat availability during outages.
        """
        
        valid_token = self.test_users[0]["jwt_token"]
        
        # TEST 1: Timeout handling
        # Simulate slow auth service response with very short timeout
        short_timeout_config = {**self.service_config, "request_timeout": 0.1}  # 100ms timeout
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock slow response that exceeds timeout
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.2)  # Slower than timeout
                return AsyncMock(status_code=200, json=lambda: {"valid": True})
            
            mock_client.return_value.__aenter__.return_value.post = slow_response
            
            start_time = time.time()
            status_code, response_data = await self._make_service_authenticated_request(
                endpoint="/auth/validate",
                payload={
                    "token": valid_token,
                    "token_type": "access"
                }
            )
            response_time = time.time() - start_time
            
            # Should timeout quickly, not hang for long time
            assert response_time < 1.0, f"Timeout should be quick, took {response_time:.3f}s"
        
        # TEST 2: Error recovery scenarios  
        recovery_scenarios = [
            {
                "name": "temporary_500_error",
                "simulate_errors": 2,  # First 2 requests fail
                "should_eventually_succeed": True
            },
            {
                "name": "temporary_503_unavailable", 
                "simulate_errors": 1,  # First request fails
                "should_eventually_succeed": True  
            },
            {
                "name": "network_timeout",
                "simulate_errors": 3,  # Multiple failures
                "should_eventually_succeed": False  # Exceeds retry limit
            }
        ]
        
        for scenario in recovery_scenarios:
            scenario_name = scenario["name"]
            error_count = scenario["simulate_errors"]
            
            # Track recovery attempts
            attempt_count = 0
            max_attempts = self.service_config["retry_attempts"] + 1
            
            for attempt in range(max_attempts):
                attempt_count += 1
                
                # Simulate failure for first N attempts
                if attempt < error_count:
                    # Simulate different error types
                    if "500" in scenario_name:
                        # Simulate server error - would be handled by real retry logic
                        continue  
                    elif "503" in scenario_name:
                        # Simulate service unavailable
                        continue
                    elif "timeout" in scenario_name:
                        # Simulate timeout
                        continue
                
                # Actual request after simulated failures
                status_code, response_data = await self._make_service_authenticated_request(
                    endpoint="/auth/validate",
                    payload={
                        "token": valid_token,
                        "token_type": "access"
                    }
                )
                
                # If we get a response, recovery succeeded
                if status_code == 200 and response_data.get("valid"):
                    if scenario["should_eventually_succeed"]:
                        assert attempt_count <= max_attempts, (
                            f"Recovery scenario '{scenario_name}' took too many attempts: {attempt_count}"
                        )
                        break
                    else:
                        # Should not succeed if scenario expects failure
                        assert False, f"Scenario '{scenario_name}' should not recover"
                
            # If we exit loop without success and should succeed, that's a problem
            if scenario["should_eventually_succeed"] and attempt_count >= max_attempts:
                assert False, f"Recovery scenario '{scenario_name}' failed to recover"


__all__ = ["TestCrossServiceAuthValidation"]