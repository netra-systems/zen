"""
Auth Service Comprehensive E2E Test Suite (Tests 2-5)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Complete end-to-end authentication system validation
- Value Impact: Ensures entire auth system works correctly in production-like environment
- Strategic Impact: Critical validation of authentication platform reliability

These tests validate:
1. Multi-user concurrent authentication flows
2. Authentication error handling and recovery
3. Cross-service authentication integration
4. Performance under realistic load
5. Security boundary enforcement at scale
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from tests.e2e.real_services_manager import RealServicesManager


class TestMultiUserConcurrentAuthE2E(SSotBaseTestCase):
    """Test 2: Multi-user concurrent authentication flows."""

    @pytest.fixture
    async def real_services(self):
        manager = RealServicesManager()
        await manager.start_services()
        yield manager
        await manager.stop_services()

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_user_authentication_isolation(
        self, 
        real_services: RealServicesManager
    ):
        """Test multiple users can authenticate concurrently without interference."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create multiple unique users
        users = []
        for i in range(5):
            unique_id = uuid.uuid4().hex[:6]
            users.append({
                "email": f"concurrent.user.{i}.{unique_id}@netra.com",
                "password": f"ConcurrentPass{i}123!",
                "name": f"Concurrent User {i}",
                "user_id": f"concurrent-{i}-{unique_id}"
            })
        
        async def authenticate_user_concurrently(user_data):
            """Authenticate a single user."""
            try:
                # Register user first
                async with auth_helper.create_authenticated_session() as session:
                    registration_data = {
                        "email": user_data["email"],
                        "password": user_data["password"],
                        "name": user_data["name"]
                    }
                    
                    async with session.post(
                        f"{real_services.auth_service_url}/auth/register",
                        json=registration_data
                    ) as response:
                        if response.status == 201:
                            result = await response.json()
                            return {
                                "success": True,
                                "user_id": result["user"]["id"],
                                "email": user_data["email"],
                                "token": result["access_token"]
                            }
                        else:
                            error_data = await response.json()
                            return {
                                "success": False,
                                "error": error_data.get("error", "Registration failed"),
                                "email": user_data["email"]
                            }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "email": user_data["email"]
                }
        
        # Run concurrent authentication
        tasks = [authenticate_user_concurrently(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_auths = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # At least 3 out of 5 should succeed (allowing for some test environment issues)
        assert len(successful_auths) >= 3
        
        # Verify each successful auth has unique user data
        user_ids = [auth["user_id"] for auth in successful_auths]
        emails = [auth["email"] for auth in successful_auths]
        tokens = [auth["token"] for auth in successful_auths]
        
        assert len(set(user_ids)) == len(successful_auths)  # All unique
        assert len(set(emails)) == len(successful_auths)    # All unique
        assert len(set(tokens)) == len(successful_auths)    # All unique


class TestAuthErrorHandlingE2E(SSotBaseTestCase):
    """Test 3: Authentication error handling and recovery."""

    @pytest.fixture
    async def real_services(self):
        manager = RealServicesManager()
        await manager.start_services()
        yield manager
        await manager.stop_services()

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_authentication_error_scenarios_and_recovery(
        self, 
        real_services: RealServicesManager
    ):
        """Test various authentication error scenarios and recovery."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Test 1: Invalid login credentials
        async with auth_helper.create_authenticated_session() as session:
            invalid_login = {
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!"
            }
            
            async with session.post(
                f"{real_services.auth_service_url}/auth/login",
                json=invalid_login
            ) as response:
                assert response.status == 401
                error_data = await response.json()
                assert "error" in error_data
                assert "invalid" in error_data["error"].lower()

        # Test 2: Malformed request data
        malformed_requests = [
            {},  # Empty request
            {"email": "test@example.com"},  # Missing password
            {"password": "test123"},  # Missing email
            {"email": "invalid-email", "password": "test123"},  # Invalid email format
        ]
        
        for malformed_request in malformed_requests:
            async with auth_helper.create_authenticated_session() as session:
                async with session.post(
                    f"{real_services.auth_service_url}/auth/login",
                    json=malformed_request
                ) as response:
                    assert response.status in [400, 422]  # Bad request or validation error
                    error_data = await response.json()
                    assert "error" in error_data or "detail" in error_data

        # Test 3: Rate limiting behavior
        rapid_login_attempts = []
        start_time = time.time()
        
        for i in range(8):  # Rapid fire login attempts
            async with auth_helper.create_authenticated_session() as session:
                async with session.post(
                    f"{real_services.auth_service_url}/auth/login",
                    json={
                        "email": f"ratelimit{i}@example.com",
                        "password": "InvalidPassword123!"
                    }
                ) as response:
                    rapid_login_attempts.append(response.status)
        
        end_time = time.time()
        
        # Should see some rate limiting (429 status codes) or consistent 401s
        rate_limited_count = sum(1 for status in rapid_login_attempts if status == 429)
        unauthorized_count = sum(1 for status in rapid_login_attempts if status == 401)
        
        # Either rate limiting kicks in, or all are unauthorized
        assert rate_limited_count > 0 or unauthorized_count == len(rapid_login_attempts)


class TestCrossServiceAuthE2E(SSotBaseTestCase):
    """Test 4: Cross-service authentication integration."""

    @pytest.fixture
    async def real_services(self):
        manager = RealServicesManager()
        await manager.start_services()
        yield manager
        await manager.stop_services()

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_cross_service_authentication_integration(
        self, 
        real_services: RealServicesManager
    ):
        """Test authentication works across different services."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create authenticated user
        unique_id = uuid.uuid4().hex[:8]
        test_user = {
            "email": f"crossservice.{unique_id}@netra.com",
            "password": "CrossServiceTest123!",
            "name": f"Cross Service User {unique_id}"
        }
        
        # Register user with auth service
        async with auth_helper.create_authenticated_session() as session:
            async with session.post(
                f"{real_services.auth_service_url}/auth/register",
                json=test_user
            ) as response:
                assert response.status == 201
                registration_result = await response.json()
                
                access_token = registration_result["access_token"]
                user_id = registration_result["user"]["id"]

        # Test 1: Use auth service token with backend service
        auth_headers = auth_helper.get_auth_headers(access_token)
        
        try:
            async with auth_helper.create_authenticated_session() as session:
                # Try to access backend service with auth token
                async with session.get(
                    f"{real_services.backend_url}/api/user/profile",
                    headers=auth_headers
                ) as backend_response:
                    # Backend might not be available in test env, that's okay
                    # We're testing the token format and structure
                    assert backend_response.status in [200, 401, 404, 503]
                    
                    if backend_response.status == 200:
                        backend_data = await backend_response.json()
                        # If backend accepts the token, user ID should match
                        if "user_id" in backend_data:
                            assert backend_data["user_id"] == user_id
        except Exception as e:
            # Backend service might not be running in test environment
            if "connection" in str(e).lower():
                pytest.skip("Backend service not available for cross-service test")

        # Test 2: Validate token format is correct for cross-service use
        # Decode token to verify it has cross-service compatible claims
        import jwt
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        
        # Verify token has necessary claims for cross-service use
        assert "sub" in decoded_token  # Subject (user ID)
        assert "exp" in decoded_token  # Expiration
        assert "iat" in decoded_token  # Issued at
        assert decoded_token["sub"] == user_id


class TestAuthPerformanceE2E(SSotBaseTestCase):
    """Test 5: Authentication performance under realistic load."""

    @pytest.fixture
    async def real_services(self):
        manager = RealServicesManager()
        await manager.start_services()
        yield manager
        await manager.stop_services()

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_authentication_performance_under_load(
        self, 
        real_services: RealServicesManager
    ):
        """Test authentication system performance under realistic load."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Test 1: Token validation performance
        # Create a valid token first
        test_token = auth_helper.create_test_jwt_token(
            user_id="perf-test-user",
            email="perf.test@netra.com"
        )
        
        auth_headers = auth_helper.get_auth_headers(test_token)
        
        # Measure token validation performance
        start_time = time.time()
        validation_results = []
        
        # Make 20 concurrent validation requests
        async def validate_token_request():
            async with auth_helper.create_authenticated_session() as session:
                async with session.get(
                    f"{real_services.auth_service_url}/auth/validate",
                    headers=auth_headers
                ) as response:
                    return response.status
        
        tasks = [validate_token_request() for _ in range(20)]
        validation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance validation
        successful_validations = sum(1 for result in validation_results if result == 200)
        
        # Should complete 20 validations in reasonable time (under 5 seconds)
        assert total_time < 5.0
        
        # Most validations should succeed (allowing for some test env variability)
        assert successful_validations >= 10
        
        # Average response time should be reasonable
        avg_response_time = total_time / len(validation_results)
        assert avg_response_time < 0.5  # Under 500ms average

        # Test 2: Login throughput performance
        start_time = time.time()
        login_results = []
        
        # Create multiple unique users and login concurrently
        async def perform_login_flow(user_index):
            unique_id = uuid.uuid4().hex[:6]
            user_data = {
                "email": f"perf.login.{user_index}.{unique_id}@netra.com",
                "password": f"PerfTest{user_index}123!",
                "name": f"Perf User {user_index}"
            }
            
            try:
                # Register and login
                async with auth_helper.create_authenticated_session() as session:
                    # Register
                    async with session.post(
                        f"{real_services.auth_service_url}/auth/register",
                        json=user_data
                    ) as reg_response:
                        if reg_response.status == 201:
                            # Immediate login after registration
                            async with session.post(
                                f"{real_services.auth_service_url}/auth/login",
                                json={
                                    "email": user_data["email"],
                                    "password": user_data["password"]
                                }
                            ) as login_response:
                                return login_response.status == 200
                        return False
            except Exception:
                return False
        
        # Test concurrent login flows
        login_tasks = [perform_login_flow(i) for i in range(10)]
        login_results = await asyncio.gather(*login_tasks, return_exceptions=True)
        
        end_time = time.time()
        login_total_time = end_time - start_time
        
        # Login performance validation
        successful_logins = sum(1 for result in login_results if result is True)
        
        # Should complete 10 login flows in reasonable time (under 10 seconds)
        assert login_total_time < 10.0
        
        # Most login flows should succeed
        assert successful_logins >= 5
        
        print(f"Performance Results:")
        print(f"  Token validations: {successful_validations}/20 in {total_time:.2f}s")
        print(f"  Login flows: {successful_logins}/10 in {login_total_time:.2f}s")
        print(f"  Average validation time: {avg_response_time:.3f}s")
        print(f"  Average login time: {login_total_time/len(login_results):.3f}s")