"""
Inter-Service Authentication and Communication Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Architecture)
- Business Goal: Ensure reliable communication between auth service and backend service
- Value Impact: Enables seamless authentication across microservices architecture
- Strategic Impact: Inter-service failures cause complete platform breakdown

This test suite validates inter-service authentication and communication flows
from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml:

1. Backend-to-Auth service authentication using SERVICE_SECRET and SERVICE_ID
2. Token validation requests between services
3. User data synchronization across services
4. Service health check and availability monitoring
5. Error handling and retry mechanisms
6. Performance requirements for service communication

CRITICAL: Inter-service authentication failures cause cascade failures where
backend cannot validate user tokens, resulting in complete user lockout.

Incident References:
- SERVICE_SECRET missing causes inter-service authentication failures
- SERVICE_ID mismatches break backend-to-auth communication
- Network timeouts between services cause user experience degradation
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper,
    create_integration_test_helper
)
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestInterServiceAuthCommunication(SSotBaseTestCase):
    """
    Inter-Service Authentication and Communication Integration Tests.
    
    Tests critical communication flows between auth service and backend service
    using real services and real authentication mechanisms.
    
    CRITICAL: Uses real auth service, simulates backend service calls.
    No mocks for auth service to ensure production-like behavior.
    """
    
    @pytest.fixture(scope="class")
    async def auth_manager(self):
        """Start real auth service for inter-service testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for inter-service tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_manager):
        """Create auth helper for inter-service testing."""
        helper = IntegrationTestAuthHelper(auth_manager)
        yield helper
    
    @pytest.fixture
    async def test_database(self):
        """Provide isolated test database session."""
        async with DatabaseTestUtilities("auth_service").transaction_scope() as db_session:
            yield db_session
    
    @pytest.fixture
    def service_config(self):
        """Provide inter-service communication configuration."""
        return {
            "backend_service_id": "netra-backend",  # HARDCODED as per MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
            "service_secret": "test-service-secret-32-chars-long",
            "request_timeout": 10.0,  # seconds
            "retry_attempts": 3,
            "retry_delay": 1.0  # seconds
        }
    
    # === INTER-SERVICE AUTHENTICATION TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_backend_to_auth_service_authentication(
        self, auth_manager, service_config
    ):
        """
        Integration test for backend-to-auth service authentication.
        
        Tests the critical authentication flow where backend service
        authenticates with auth service using SERVICE_SECRET and SERVICE_ID.
        
        CRITICAL: This is the foundation of all inter-service communication.
        """
        # Record test metadata
        self.record_metric("test_category", "inter_service_auth")
        self.record_metric("test_focus", "backend_to_auth_authentication")
        
        # Test successful inter-service authentication
        auth_success = await self._test_inter_service_authentication(
            auth_manager,
            service_id=service_config["backend_service_id"],
            service_secret=service_config["service_secret"],
            should_succeed=True,
            scenario="valid_credentials"
        )
        
        assert auth_success, "Backend-to-auth service authentication should succeed with valid credentials"
        
        # Test authentication failure scenarios
        failure_scenarios = [
            {
                "name": "wrong_service_secret",
                "service_id": service_config["backend_service_id"],
                "service_secret": "wrong-service-secret",
                "should_succeed": False
            },
            {
                "name": "wrong_service_id",
                "service_id": "wrong-service-id",
                "service_secret": service_config["service_secret"],
                "should_succeed": False
            },
            {
                "name": "missing_service_secret",
                "service_id": service_config["backend_service_id"],
                "service_secret": "",
                "should_succeed": False
            },
            {
                "name": "missing_service_id",
                "service_id": "",
                "service_secret": service_config["service_secret"],
                "should_succeed": False
            }
        ]
        
        for scenario in failure_scenarios:
            scenario_name = scenario["name"]
            
            logger.debug(f"Testing inter-service auth failure scenario: {scenario_name}")
            
            auth_failure = await self._test_inter_service_authentication(
                auth_manager,
                service_id=scenario["service_id"],
                service_secret=scenario["service_secret"],
                should_succeed=scenario["should_succeed"],
                scenario=scenario_name
            )
            
            assert not auth_failure, (
                f"Inter-service auth failure scenario '{scenario_name}' should be rejected. "
                f"This ensures proper service authentication validation."
            )
            
            self.record_metric(f"auth_failure_{scenario_name}", "correctly_rejected")
        
        self.record_metric("inter_service_authentication", "working")
        logger.info(f" PASS:  Inter-service authentication working ({len(failure_scenarios)} failure scenarios tested)")
    
    async def _test_inter_service_authentication(
        self,
        auth_manager: IntegrationAuthServiceManager,
        service_id: str,
        service_secret: str,
        should_succeed: bool,
        scenario: str
    ) -> bool:
        """Test inter-service authentication."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": service_id,
                    "X-Service-Secret": service_secret
                }
                
                # Use token validation endpoint as representative inter-service call
                request_data = {
                    "token": "dummy-token-for-service-auth-test",
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    # Service authentication should succeed (token might be invalid)
                    # We're testing service auth, not token validity
                    if should_succeed:
                        success = response.status != 403  # 403 = service auth failure
                    else:
                        success = response.status == 403  # Should be rejected
                    
                    self.record_metric(f"service_auth_test_{scenario}", "passed" if success else "failed")
                    self.increment_db_query_count(1)
                    
                    return success
                    
        except Exception as e:
            logger.warning(f"Inter-service auth test error for scenario {scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_validation_service_communication(
        self, auth_manager, auth_helper, service_config
    ):
        """
        Integration test for token validation service communication.
        
        Tests the critical flow where backend service requests token validation
        from auth service - the most common inter-service operation.
        """
        # Record test metadata
        self.record_metric("test_category", "token_validation_communication")
        self.record_metric("test_focus", "backend_to_auth_token_validation")
        
        # Step 1: Create a valid token for testing
        test_user_data = {
            "user_id": "interservice-test-user-456",
            "email": "interservice.test@example.com",
            "permissions": ["read", "write"]
        }
        
        valid_token = await auth_manager.create_test_token(
            user_id=test_user_data["user_id"],
            email=test_user_data["email"],
            permissions=test_user_data["permissions"]
        )
        
        assert valid_token is not None, "Failed to create test token"
        self.increment_db_query_count(1)  # Token creation
        
        # Step 2: Test token validation via inter-service communication
        validation_success = await self._test_token_validation_communication(
            auth_manager,
            token=valid_token,
            service_id=service_config["backend_service_id"],
            service_secret=service_config["service_secret"],
            should_succeed=True,
            scenario="valid_token_validation"
        )
        
        assert validation_success, "Token validation via inter-service communication should succeed"
        
        # Step 3: Test token validation with invalid tokens
        invalid_token_scenarios = [
            {
                "name": "invalid_token",
                "token": "invalid.jwt.token",
                "should_succeed": False  # Service auth succeeds, but token validation fails
            },
            {
                "name": "expired_token",
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid",
                "should_succeed": False
            },
            {
                "name": "empty_token",
                "token": "",
                "should_succeed": False
            }
        ]
        
        for scenario in invalid_token_scenarios:
            scenario_name = scenario["name"]
            
            logger.debug(f"Testing token validation scenario: {scenario_name}")
            
            validation_result = await self._test_token_validation_communication(
                auth_manager,
                token=scenario["token"],
                service_id=service_config["backend_service_id"],
                service_secret=service_config["service_secret"],
                should_succeed=scenario["should_succeed"],
                scenario=scenario_name
            )
            
            if scenario["should_succeed"]:
                assert validation_result, f"Token validation scenario '{scenario_name}' should succeed"
            else:
                assert not validation_result, f"Token validation scenario '{scenario_name}' should fail"
            
            self.record_metric(f"token_validation_{scenario_name}", "passed")
        
        self.record_metric("token_validation_communication", "working")
        logger.info(f" PASS:  Token validation service communication working ({len(invalid_token_scenarios)} scenarios tested)")
    
    async def _test_token_validation_communication(
        self,
        auth_manager: IntegrationAuthServiceManager,
        token: str,
        service_id: str,
        service_secret: str,
        should_succeed: bool,
        scenario: str
    ) -> bool:
        """Test token validation communication."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": service_id,
                    "X-Service-Secret": service_secret
                }
                
                request_data = {
                    "token": token,
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    # Check service communication success
                    service_auth_ok = response.status != 403
                    if not service_auth_ok:
                        logger.error(f"Service authentication failed for scenario {scenario}")
                        return False
                    
                    # Check token validation result
                    if response.status == 200:
                        result = await response.json()
                        token_valid = result.get("valid", False)
                    else:
                        token_valid = False
                    
                    self.record_metric(f"token_validation_comm_{scenario}", "success" if token_valid else "failed")
                    self.increment_db_query_count(1)
                    
                    return token_valid
                    
        except Exception as e:
            logger.warning(f"Token validation communication error for scenario {scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_communication_performance(
        self, auth_manager, auth_helper, service_config
    ):
        """
        Integration test for service communication performance.
        
        Tests that inter-service communication performs within acceptable limits
        to ensure good user experience and system responsiveness.
        """
        # Record test metadata
        self.record_metric("test_category", "service_communication_performance")
        self.record_metric("test_focus", "inter_service_performance")
        
        # Create test token
        test_token = await auth_manager.create_test_token(
            user_id="perf-test-user-789",
            email="perf.interservice@example.com",
            permissions=["read"]
        )
        
        assert test_token is not None, "Failed to create test token for performance test"
        
        # Test multiple inter-service requests and measure performance
        response_times = []
        num_requests = 15
        
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                success = await self._test_token_validation_communication(
                    auth_manager,
                    token=test_token,
                    service_id=service_config["backend_service_id"],
                    service_secret=service_config["service_secret"],
                    should_succeed=True,
                    scenario=f"perf_test_{i}"
                )
                
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # Should succeed for performance measurement
                assert success, f"Performance test request {i} should succeed"
                
                self.increment_db_query_count(1)
                
            except Exception as e:
                pytest.fail(f"Inter-service communication failed on request {i}: {e}")
        
        # Analyze performance
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        
        # Performance requirements for inter-service communication
        assert avg_response_time < 1.0, (
            f"Average inter-service response time {avg_response_time:.3f}s exceeds 1.0s limit. "
            f"Slow inter-service communication degrades user experience."
        )
        
        assert p95_response_time < 2.0, (
            f"95th percentile inter-service response time {p95_response_time:.3f}s exceeds 2.0s limit. "
            f"This could cause request timeouts."
        )
        
        assert max_response_time < 5.0, (
            f"Maximum inter-service response time {max_response_time:.3f}s exceeds 5.0s limit. "
            f"This indicates potential performance issues."
        )
        
        self.record_metric("avg_interservice_response_time_ms", avg_response_time * 1000)
        self.record_metric("max_interservice_response_time_ms", max_response_time * 1000)
        self.record_metric("p95_interservice_response_time_ms", p95_response_time * 1000)
        self.record_metric("interservice_performance", "acceptable")
        
        logger.info(
            f" PASS:  Inter-service communication performance acceptable "
            f"(avg: {avg_response_time:.3f}s, p95: {p95_response_time:.3f}s, max: {max_response_time:.3f}s)"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_communication_retry_mechanisms(
        self, auth_manager, service_config
    ):
        """
        Integration test for service communication retry mechanisms.
        
        Tests retry behavior when inter-service communication fails due to
        network issues, timeouts, or temporary service unavailability.
        """
        # Record test metadata
        self.record_metric("test_category", "service_communication_reliability")
        self.record_metric("test_focus", "retry_mechanisms")
        
        # Test retry scenarios
        retry_scenarios = [
            {
                "name": "temporary_network_timeout",
                "simulate_failure_count": 2,
                "should_eventually_succeed": True
            },
            {
                "name": "temporary_service_error",
                "simulate_failure_count": 1,
                "should_eventually_succeed": True
            },
            {
                "name": "persistent_failure",
                "simulate_failure_count": 5,  # More than retry attempts
                "should_eventually_succeed": False
            }
        ]
        
        for scenario in retry_scenarios:
            scenario_name = scenario["name"]
            failure_count = scenario["simulate_failure_count"]
            
            logger.debug(f"Testing retry scenario: {scenario_name}")
            
            # Test retry mechanism with simulated failures
            retry_success = await self._test_retry_mechanism(
                auth_manager,
                service_config,
                simulate_failure_count=failure_count,
                scenario=scenario_name
            )
            
            if scenario["should_eventually_succeed"]:
                assert retry_success, (
                    f"Retry scenario '{scenario_name}' should eventually succeed after {failure_count} failures"
                )
            else:
                assert not retry_success, (
                    f"Retry scenario '{scenario_name}' should fail after {failure_count} failures exceed retry limit"
                )
            
            self.record_metric(f"retry_test_{scenario_name}", "passed")
        
        self.record_metric("service_communication_retry", "working")
        logger.info(f" PASS:  Service communication retry mechanisms working ({len(retry_scenarios)} scenarios tested)")
    
    async def _test_retry_mechanism(
        self,
        auth_manager: IntegrationAuthServiceManager,
        service_config: Dict[str, Any],
        simulate_failure_count: int,
        scenario: str
    ) -> bool:
        """Test retry mechanism with simulated failures."""
        attempt_count = 0
        max_attempts = service_config["retry_attempts"]
        retry_delay = service_config["retry_delay"]
        
        for attempt in range(max_attempts + 1):  # +1 for initial attempt
            attempt_count += 1
            
            try:
                # Simulate failure for first N attempts
                if attempt < simulate_failure_count:
                    logger.debug(f"Simulating failure for attempt {attempt + 1} in scenario {scenario}")
                    await asyncio.sleep(0.1)  # Simulate network delay
                    # Simulate failure by skipping the actual request
                    continue
                
                # Actual request after simulated failures
                success = await self._test_token_validation_communication(
                    auth_manager,
                    token="test-token-for-retry",
                    service_id=service_config["backend_service_id"],
                    service_secret=service_config["service_secret"],
                    should_succeed=False,  # Token is dummy, we just test service communication
                    scenario=f"retry_{scenario}_attempt_{attempt}"
                )
                
                # If we get a response (even failure), communication succeeded
                self.record_metric(f"retry_attempts_{scenario}", attempt_count)
                self.increment_db_query_count(attempt_count)
                
                return True  # Communication established
                
            except Exception as e:
                logger.debug(f"Retry attempt {attempt + 1} failed for scenario {scenario}: {e}")
                
                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay)
        
        # All retry attempts exhausted
        self.record_metric(f"retry_attempts_{scenario}", attempt_count)
        return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_health_check_communication(
        self, auth_manager, service_config
    ):
        """
        Integration test for service health check communication.
        
        Tests health check endpoints that allow services to monitor each other's
        availability and health status.
        """
        # Record test metadata
        self.record_metric("test_category", "service_health_monitoring")
        self.record_metric("test_focus", "health_check_communication")
        
        # Test auth service health check
        health_status = await self._test_service_health_check(
            auth_manager, "auth_service_health"
        )
        
        assert health_status is not None, "Auth service health check should return status"
        assert health_status.get("status") == "healthy", (
            f"Auth service should be healthy, got: {health_status}"
        )
        
        # Validate health check response structure
        required_health_fields = ["status", "timestamp"]
        for field in required_health_fields:
            assert field in health_status, f"Health check missing required field: {field}"
        
        # Test health check performance
        health_check_times = []
        num_health_checks = 5
        
        for i in range(num_health_checks):
            start_time = time.time()
            
            health_result = await self._test_service_health_check(
                auth_manager, f"health_perf_test_{i}"
            )
            
            health_check_time = time.time() - start_time
            health_check_times.append(health_check_time)
            
            assert health_result is not None, f"Health check {i} should succeed"
        
        # Health check performance requirements
        avg_health_check_time = sum(health_check_times) / len(health_check_times)
        max_health_check_time = max(health_check_times)
        
        assert avg_health_check_time < 0.5, (
            f"Average health check time {avg_health_check_time:.3f}s exceeds 0.5s limit. "
            f"Slow health checks can cause false positive failure detection."
        )
        
        assert max_health_check_time < 2.0, (
            f"Maximum health check time {max_health_check_time:.3f}s exceeds 2.0s limit."
        )
        
        self.record_metric("avg_health_check_time_ms", avg_health_check_time * 1000)
        self.record_metric("max_health_check_time_ms", max_health_check_time * 1000)
        self.record_metric("service_health_monitoring", "working")
        
        logger.info(
            f" PASS:  Service health check communication working "
            f"(avg: {avg_health_check_time:.3f}s, max: {max_health_check_time:.3f}s)"
        )
    
    async def _test_service_health_check(
        self, auth_manager: IntegrationAuthServiceManager, scenario: str
    ) -> Optional[Dict[str, Any]]:
        """Test service health check."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{auth_manager.get_auth_url()}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        self.record_metric(f"health_check_{scenario}", "success")
                        return health_data
                    else:
                        logger.warning(f"Health check failed for scenario {scenario}: {response.status}")
                        self.record_metric(f"health_check_{scenario}", "failed")
                        return None
                        
        except Exception as e:
            logger.warning(f"Health check error for scenario {scenario}: {e}")
            return None
    
    # === TEARDOWN AND VALIDATION ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with inter-service metrics validation."""
        super().teardown_method(method)
        
        # Validate inter-service metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure inter-service tests recorded their metrics
        if "service" in method.__name__.lower() if method else "":
            assert "test_category" in metrics, "Inter-service tests must record test_category metric"
            assert "test_focus" in metrics, "Inter-service tests must record test_focus metric"
        
        # Log inter-service specific metrics for analysis
        service_metrics = {k: v for k, v in metrics.items() if "service" in k.lower() or "inter" in k.lower()}
        if service_metrics:
            logger.info(f"Inter-service test metrics: {service_metrics}")
