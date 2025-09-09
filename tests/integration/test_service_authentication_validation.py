"""
Service Authentication Validation Tests for GitHub Issue #115

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Validate service-to-service authentication works properly
- Value Impact: Service authentication enables internal operations and database access
- Strategic Impact: Core infrastructure for system reliability and golden path

CRITICAL: These tests validate proper service authentication implementation.
They MUST PASS after implementing service auth headers in dependencies.py.

This test suite follows CLAUDE.md requirements:
- NO MOCKS in integration tests (forbidden per CLAUDE.md)
- ALL tests use real services - no docker dependency
- Real authentication flows with actual JWT tokens and service headers
- Focus on validating service-to-service authentication patterns
"""

import pytest
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_test_user_with_auth
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

class TestServiceAuthenticationValidation(SSotBaseTestCase):
    """
    Integration Tests: Validate service-to-service authentication for Issue #115.
    
    These tests validate that:
    1. Service authentication headers work properly for system operations
    2. Dependencies.py includes proper X-Service-ID and X-Service-Secret headers
    3. Internal operations succeed with proper service authentication
    4. System user operations work with service-to-service credentials
    
    CRITICAL: These tests should PASS after implementing proper service authentication.
    """

    def setup_method(self, method):
        """Set up test environment for service authentication validation."""
        super().setup_method(method)
        self.env = get_env()
        
        # Use test environment - integration tests use local services
        self.environment = "test"
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        
        # Test configuration
        self.backend_url = "http://localhost:8000"
        self.auth_service_url = "http://localhost:8081"
        
        # Service authentication configuration
        # These should be set in environment for service-to-service auth
        self.service_id = self.env.get("SERVICE_ID", "netra-backend")
        self.service_secret = self.env.get("SERVICE_SECRET", "test_service_secret_32chars_long")
        
        logger.info(f"🔍 SERVICE AUTH TEST: {method.__name__}")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Service ID: {self.service_id}")
        logger.info(f"Service Secret: {'***' + self.service_secret[-4:] if self.service_secret else 'NOT_SET'}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_user_with_service_auth_headers(self):
        """
        Test that system user operations succeed with proper service auth headers.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Service authentication headers enable system user operations
        """
        logger.info("✅ VALIDATION: Testing system user with service auth headers")
        
        async with aiohttp.ClientSession() as session:
            # Test system user operation with proper service authentication
            test_url = f"{self.backend_url}/api/internal/db-session-test"
            headers = {
                "Content-Type": "application/json",
                "X-User-ID": "system",
                # CRITICAL: Include proper service authentication headers
                "X-Service-ID": self.service_id,
                "X-Service-Secret": self.service_secret
            }
            
            try:
                async with session.post(test_url, headers=headers, timeout=10) as response:
                    response_text = await response.text()
                    
                    # Should succeed with proper service authentication
                    if response.status == 200:
                        logger.info("✅ VALIDATION SUCCESS: System user authenticated with service headers")
                        logger.info(f"Success response: {response_text}")
                        return
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"VALIDATION FAILED: System user still failing auth with service headers. "
                            f"Status: {response.status}, Response: {response_text}. "
                            f"This indicates service auth implementation may be incomplete."
                        )
                    else:
                        pytest.fail(
                            f"VALIDATION FAILED: Unexpected response {response.status}: {response_text}"
                        )
                        
            except Exception as e:
                pytest.fail(f"VALIDATION FAILED: Error testing system user with service auth: {e}")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_get_request_scoped_db_session_with_service_auth(self):
        """
        Test that get_request_scoped_db_session works with proper service authentication.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Core dependencies.py function works with service authentication
        """
        logger.info("✅ VALIDATION: Testing get_request_scoped_db_session with service auth")
        
        async with aiohttp.ClientSession() as session:
            # Test the specific function that was failing in dependencies.py
            test_url = f"{self.backend_url}/api/test/system-user-session"
            headers = {
                "Content-Type": "application/json",
                "X-User-ID": "system",
                # Include service authentication headers
                "X-Service-ID": self.service_id,
                "X-Service-Secret": self.service_secret
            }
            
            data = {
                "operation": "create_request_scoped_db_session",
                "user_id": "system",
                "source": "dependencies_validation_test"
            }
            
            try:
                async with session.post(test_url, headers=headers, json=data, timeout=10) as response:
                    response_text = await response.text()
                    
                    # Should succeed with service authentication
                    if response.status == 200:
                        logger.info("✅ VALIDATION SUCCESS: Database session created with service auth")
                        logger.info(f"Session creation success: {response_text}")
                        return
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"VALIDATION FAILED: Database session creation still failing with service auth. "
                            f"Status: {response.status}, Response: {response_text}. "
                            f"Check if dependencies.py properly uses service authentication headers."
                        )
                    else:
                        pytest.fail(
                            f"VALIDATION FAILED: Unexpected response {response.status}: {response_text}"
                        )
                        
            except Exception as e:
                pytest.fail(f"VALIDATION FAILED: Error testing database session with service auth: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_middleware_accepts_authenticated_service_requests(self):
        """
        Test that authentication middleware properly validates service requests.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Middleware recognizes and validates service-to-service authentication
        """
        logger.info("✅ VALIDATION: Testing middleware accepts authenticated service requests")
        
        async with aiohttp.ClientSession() as session:
            # Test authenticated endpoint with proper service credentials
            test_url = f"{self.backend_url}/api/health/authenticated"
            headers = {
                "Content-Type": "application/json",
                "X-User-ID": "system",
                # Proper service authentication headers
                "X-Service-ID": self.service_id,
                "X-Service-Secret": self.service_secret
            }
            
            try:
                async with session.get(test_url, headers=headers, timeout=10) as response:
                    response_text = await response.text()
                    
                    # Middleware should accept service-authenticated requests
                    if response.status == 200:
                        logger.info("✅ VALIDATION SUCCESS: Middleware accepted service-authenticated request")
                        logger.info(f"Middleware success: {response_text}")
                        return
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"VALIDATION FAILED: Middleware still rejecting service-authenticated requests. "
                            f"Status: {response.status}, Response: {response_text}. "
                            f"Check if middleware properly handles X-Service-ID and X-Service-Secret headers."
                        )
                    else:
                        pytest.fail(
                            f"VALIDATION FAILED: Unexpected response {response.status}: {response_text}"
                        )
                        
            except Exception as e:
                pytest.fail(f"VALIDATION FAILED: Error testing middleware service auth: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_factory_accepts_service_authenticated_system_user(self):
        """
        Test that session factory accepts service-authenticated system user requests.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Session factory works with proper service authentication context
        """
        logger.info("✅ VALIDATION: Testing session factory accepts service-authenticated system user")
        
        async with aiohttp.ClientSession() as session:
            # Test session creation with service-authenticated system user
            test_url = f"{self.backend_url}/api/test/session-factory"
            headers = {
                "Content-Type": "application/json",
                # Include service authentication headers
                "X-Service-ID": self.service_id,
                "X-Service-Secret": self.service_secret
            }
            
            data = {
                "user_id": "system",
                "request_id": "validation_test_123",
                "operation": "get_request_scoped_session",
                "source": "service_auth_validation_test"
            }
            
            try:
                async with session.post(test_url, headers=headers, json=data, timeout=10) as response:
                    response_text = await response.text()
                    
                    # Session factory should succeed with service authentication
                    if response.status == 200:
                        logger.info("✅ VALIDATION SUCCESS: Session factory accepted service-authenticated system user")
                        logger.info(f"Session factory success: {response_text}")
                        return
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"VALIDATION FAILED: Session factory still rejecting service-authenticated system user. "
                            f"Status: {response.status}, Response: {response_text}. "
                            f"Check if session factory properly validates service authentication context."
                        )
                    else:
                        pytest.fail(
                            f"VALIDATION FAILED: Unexpected response {response.status}: {response_text}"
                        )
                        
            except Exception as e:
                pytest.fail(f"VALIDATION FAILED: Error testing session factory service auth: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_service_auth_header_validation_edge_cases(self):
        """
        Test service authentication header validation handles edge cases properly.
        
        EXPECTED: This test should PASS with proper error handling
        VALIDATES: Service auth properly validates headers and gives clear error messages
        """
        logger.info("✅ VALIDATION: Testing service auth header validation edge cases")
        
        # Test cases for different authentication scenarios
        test_cases = [
            {
                "name": "missing_service_id",
                "headers": {"X-Service-Secret": self.service_secret},
                "expected_status": [401, 400],
                "error_keywords": ["service", "service_id", "missing"]
            },
            {
                "name": "missing_service_secret", 
                "headers": {"X-Service-ID": self.service_id},
                "expected_status": [401, 400],
                "error_keywords": ["service", "service_secret", "missing"]
            },
            {
                "name": "invalid_service_id",
                "headers": {"X-Service-ID": "invalid-service", "X-Service-Secret": self.service_secret},
                "expected_status": [401, 403],
                "error_keywords": ["service", "invalid", "unauthorized"]
            },
            {
                "name": "invalid_service_secret",
                "headers": {"X-Service-ID": self.service_id, "X-Service-Secret": "invalid_secret"},
                "expected_status": [401, 403], 
                "error_keywords": ["service", "invalid", "unauthorized"]
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            for test_case in test_cases:
                logger.info(f"Testing edge case: {test_case['name']}")
                
                test_url = f"{self.backend_url}/api/internal/db-session-test"
                headers = {
                    "Content-Type": "application/json",
                    "X-User-ID": "system",
                    **test_case["headers"]
                }
                
                try:
                    async with session.post(test_url, headers=headers, timeout=10) as response:
                        response_text = await response.text()
                        
                        # Should fail with appropriate error for edge cases
                        if response.status in test_case["expected_status"]:
                            # Verify error message contains relevant keywords
                            if any(keyword in response_text.lower() for keyword in test_case["error_keywords"]):
                                logger.info(f"✅ Edge case {test_case['name']}: Proper error handling")
                                continue
                            else:
                                pytest.fail(
                                    f"VALIDATION FAILED: Edge case {test_case['name']} returned expected status "
                                    f"{response.status} but error message doesn't contain expected keywords "
                                    f"{test_case['error_keywords']}. Response: {response_text}"
                                )
                        else:
                            pytest.fail(
                                f"VALIDATION FAILED: Edge case {test_case['name']} returned unexpected status "
                                f"{response.status}, expected one of {test_case['expected_status']}. "
                                f"Response: {response_text}"
                            )
                            
                except Exception as e:
                    pytest.fail(f"VALIDATION FAILED: Error testing edge case {test_case['name']}: {e}")
                    
        logger.info("✅ VALIDATION SUCCESS: All service auth edge cases handled properly")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_golden_path_works_with_service_authentication(self):
        """
        Test that golden path user flow works with fixed service authentication.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Complete golden path functionality restored with service authentication
        """
        logger.info("✅ VALIDATION: Testing golden path works with service authentication")
        
        # Create authenticated user for golden path test
        auth_result = await create_test_user_with_auth(
            email="golden_path_validation@example.com",
            environment=self.environment,
            permissions=["read", "write"]
        )
        
        user_token = auth_result["jwt_token"]
        user_id = auth_result["user_id"]
        
        async with aiohttp.ClientSession() as session:
            # Test golden path endpoint - should now work with fixed service auth
            test_url = f"{self.backend_url}/api/chat/start-conversation"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "message": "Test golden path with fixed service authentication",
                "agent_type": "triage",
                "user_id": user_id
            }
            
            try:
                async with session.post(test_url, headers=headers, json=data, timeout=20) as response:
                    response_text = await response.text()
                    
                    # Golden path should succeed with fixed service authentication
                    if response.status == 200:
                        logger.info("✅ VALIDATION SUCCESS: Golden path working with service authentication")
                        logger.info(f"Golden path success: {response_text[:200]}...")
                        return
                    elif response.status in [500, 503]:
                        # Check if still system auth related errors
                        system_auth_errors = [
                            "system_user_auth_failure", "system user failed authentication",
                            "not authenticated", "database session", "session factory"
                        ]
                        
                        if any(error in response_text.lower() for error in system_auth_errors):
                            pytest.fail(
                                f"VALIDATION FAILED: Golden path still has system authentication issues. "
                                f"Status: {response.status}, Response: {response_text}. "
                                f"Service authentication fix may be incomplete."
                            )
                        else:
                            pytest.fail(
                                f"VALIDATION FAILED: Golden path failed with non-auth error. "
                                f"Status: {response.status}, Response: {response_text}"
                            )
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"VALIDATION FAILED: Golden path still has authentication issues. "
                            f"Status: {response.status}, Response: {response_text}"
                        )
                    else:
                        pytest.fail(
                            f"VALIDATION FAILED: Golden path failed with unexpected status. "
                            f"Status: {response.status}, Response: {response_text}"
                        )
                        
            except asyncio.TimeoutError:
                pytest.fail(
                    "VALIDATION FAILED: Golden path timed out. This may indicate ongoing "
                    "authentication issues preventing proper completion."
                )
            except Exception as e:
                pytest.fail(f"VALIDATION FAILED: Error testing golden path with service auth: {e}")

    def teardown_method(self, method):
        """Clean up after test."""
        logger.info(f"🏁 SERVICE AUTH VALIDATION TEST COMPLETE: {method.__name__}")
        super().teardown_method(method)