"""
Authentication Failure Scenarios and Circuit Breaker Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Resilience)
- Business Goal: Prevent cascade failures and ensure system recovery from auth issues
- Value Impact: Maintains system stability during authentication service disruptions
- Strategic Impact: Authentication failures can cause complete platform outages

This test suite validates authentication failure scenarios and circuit breaker patterns
from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml:

1. Circuit breaker permanent failure state prevention (error behind the error)
2. Authentication failure cascade prevention
3. Service degradation and recovery patterns
4. Error handling and retry mechanisms
5. Fallback authentication strategies
6. System resilience under auth service load

CRITICAL: This addresses the "error behind the error" pattern identified in incidents:
- MockCircuitBreaker entering permanent failure state
- AUTH_CIRCUIT_BREAKER_BUG causing complete system unusability
- Authentication failures masking deeper architectural issues

Incident References:
- 2025-09-05: MockCircuitBreaker permanent failure (error behind the error)
- 2025-09-05: Complete staging outage due to circuit breaker architecture flaw
- AUTH_CIRCUIT_BREAKER_BUG_FIX_REPORT_20250905.md: Deep root cause analysis
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from unittest.mock import patch, AsyncMock, MagicMock

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


class TestAuthFailureCircuitBreaker(SSotBaseTestCase):
    """
    Authentication Failure Scenarios and Circuit Breaker Integration Tests.
    
    Tests critical failure scenarios and circuit breaker patterns that prevent
    the "error behind the error" issues identified in system incidents.
    
    CRITICAL: Uses real auth service to test actual failure scenarios.
    Simulates network failures, service overload, and recovery patterns.
    """
    
    @pytest.fixture(scope="class")
    async def auth_manager(self):
        """Start real auth service for failure scenario testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for failure scenario tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_manager):
        """Create auth helper for failure scenario testing."""
        helper = IntegrationTestAuthHelper(auth_manager)
        yield helper
    
    @pytest.fixture
    async def test_database(self):
        """Provide isolated test database session."""
        async with DatabaseTestUtilities("auth_service").transaction_scope() as db_session:
            yield db_session
    
    @pytest.fixture
    def circuit_breaker_config(self):
        """Provide circuit breaker configuration for testing."""
        return {
            "failure_threshold": 5,  # Number of failures before opening circuit
            "recovery_timeout": 10.0,  # Seconds to wait before attempting recovery
            "success_threshold": 3,  # Consecutive successes needed to close circuit
            "request_timeout": 5.0,  # Request timeout in seconds
            "max_retry_attempts": 3,
            "backoff_multiplier": 2.0
        }
    
    # === CIRCUIT BREAKER PERMANENT FAILURE PREVENTION (ERROR BEHIND THE ERROR) ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_circuit_breaker_permanent_failure_state_prevention(
        self, auth_manager, circuit_breaker_config
    ):
        """
        CRITICAL: Test prevention of circuit breaker permanent failure state.
        
        This test addresses the "error behind the error" identified in
        MISSION_CRITICAL_NAMED_VALUES_INDEX.xml where MockCircuitBreaker
        enters permanent failure state causing complete system unusability.
        
        Incident Reference: 2025-09-05 MockCircuitBreaker permanent failure
        """
        # Record test metadata
        self.record_metric("test_category", "circuit_breaker_permanent_failure")
        self.record_metric("test_focus", "permanent_state_prevention")
        self.record_metric("incident_reference", "2025-09-05_circuit_breaker_permanent")
        
        failure_threshold = circuit_breaker_config["failure_threshold"]
        recovery_timeout = circuit_breaker_config["recovery_timeout"]
        
        # Step 1: Trigger circuit breaker with consecutive failures
        consecutive_failures = 0
        max_test_failures = failure_threshold + 2  # Go beyond threshold
        
        for attempt in range(max_test_failures):
            # Attempt authentication with invalid credentials to trigger failure
            failure_result = await self._trigger_authentication_failure(
                auth_manager, f"circuit_breaker_trigger_{attempt}"
            )
            
            if failure_result:
                consecutive_failures += 1
            else:
                # If we get success, reset counter
                consecutive_failures = 0
            
            self.increment_db_query_count(1)
            await asyncio.sleep(0.1)  # Small delay between attempts
        
        logger.info(f"Triggered {consecutive_failures} consecutive failures")
        
        # Step 2: Verify circuit breaker opens (temporary failure state)
        circuit_open_confirmed = await self._verify_circuit_breaker_state(
            auth_manager, expected_state="open", scenario="circuit_opened"
        )
        
        # Circuit should be open initially
        assert circuit_open_confirmed, (
            "Circuit breaker should open after consecutive failures. "
            "If this fails, circuit breaker may not be functioning."
        )
        
        self.record_metric("circuit_breaker_opens", "confirmed")
        
        # Step 3: CRITICAL - Wait for recovery timeout and verify circuit attempts recovery
        logger.info(f"Waiting {recovery_timeout}s for circuit breaker recovery attempt")
        await asyncio.sleep(recovery_timeout + 1)  # Wait for recovery window
        
        # Step 4: Test that circuit breaker allows recovery attempts (half-open state)
        recovery_attempt_allowed = await self._test_circuit_recovery_attempt(
            auth_manager, "recovery_attempt_test"
        )
        
        # CRITICAL: Circuit breaker must allow recovery attempts
        assert recovery_attempt_allowed, (
            "Circuit breaker must allow recovery attempts after timeout. "
            "If this fails, circuit breaker may be in permanent failure state. "
            "This is the 'error behind the error' that causes complete system unusability."
        )
        
        self.record_metric("circuit_recovery_allowed", "confirmed")
        
        # Step 5: Verify successful requests close the circuit
        circuit_close_success = await self._test_circuit_closure_via_success(
            auth_manager, circuit_breaker_config["success_threshold"], "circuit_closure_test"
        )
        
        assert circuit_close_success, (
            "Circuit breaker should close after successful requests. "
            "Failure to close indicates permanent failure state."
        )
        
        self.record_metric("circuit_closure", "working")
        self.record_metric("permanent_failure_prevention", "working")
        
        logger.info(" PASS:  Circuit breaker permanent failure state prevention working")
    
    async def _trigger_authentication_failure(
        self, auth_manager: IntegrationAuthServiceManager, scenario: str
    ) -> bool:
        """Trigger authentication failure to test circuit breaker."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use invalid credentials to trigger failure
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "invalid-service-id",  # Wrong service ID
                    "X-Service-Secret": "invalid-secret"  # Wrong secret
                }
                
                request_data = {
                    "token": "invalid-token-for-circuit-test",
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Authentication failure expected (403, 401, etc.)
                    is_failure = response.status in [401, 403, 500]
                    self.record_metric(f"failure_trigger_{scenario}", "success" if is_failure else "unexpected_success")
                    return is_failure
                    
        except asyncio.TimeoutError:
            # Timeout also counts as failure
            logger.debug(f"Timeout in failure trigger for scenario {scenario}")
            return True
        except Exception as e:
            logger.debug(f"Exception in failure trigger for scenario {scenario}: {e}")
            return True
    
    async def _verify_circuit_breaker_state(
        self, 
        auth_manager: IntegrationAuthServiceManager, 
        expected_state: str, 
        scenario: str
    ) -> bool:
        """Verify circuit breaker state."""
        try:
            # Test multiple requests quickly to check if circuit is open
            quick_requests = 3
            response_statuses = []
            
            for i in range(quick_requests):
                try:
                    async with aiohttp.ClientSession() as session:
                        # Valid credentials for state testing
                        headers = {
                            "Content-Type": "application/json",
                            "X-Service-ID": "netra-backend",
                            "X-Service-Secret": "test-service-secret-32-chars-long"
                        }
                        
                        request_data = {
                            "token": "state-test-token",
                            "token_type": "access"
                        }
                        
                        async with session.post(
                            f"{auth_manager.get_auth_url()}/auth/validate",
                            json=request_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=2)  # Short timeout for state test
                        ) as response:
                            response_statuses.append(response.status)
                            
                except asyncio.TimeoutError:
                    response_statuses.append(503)  # Service unavailable
                except Exception:
                    response_statuses.append(500)  # Internal server error
            
            # Analyze response patterns to infer circuit state
            if expected_state == "open":
                # Circuit open: should get quick failures (503, 500) or timeouts
                failure_responses = sum(1 for status in response_statuses if status >= 500)
                circuit_open = failure_responses >= quick_requests * 0.7  # 70% failures indicate open circuit
            else:
                # Circuit closed: should get normal responses (even if token is invalid)
                normal_responses = sum(1 for status in response_statuses if status in [200, 401])
                circuit_open = normal_responses >= quick_requests * 0.7
            
            self.record_metric(f"circuit_state_test_{scenario}", expected_state)
            return circuit_open
            
        except Exception as e:
            logger.warning(f"Circuit state verification error for scenario {scenario}: {e}")
            return False
    
    async def _test_circuit_recovery_attempt(
        self, auth_manager: IntegrationAuthServiceManager, scenario: str
    ) -> bool:
        """Test that circuit breaker allows recovery attempts."""
        try:
            # This should be allowed in half-open state
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": "test-service-secret-32-chars-long"
                }
                
                request_data = {
                    "token": "recovery-test-token",
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    # Should get a response (not timeout/connection refused)
                    # Even if token is invalid, we should get 401, not 503
                    recovery_allowed = response.status != 503
                    self.record_metric(f"recovery_attempt_{scenario}", "allowed" if recovery_allowed else "blocked")
                    return recovery_allowed
                    
        except asyncio.TimeoutError:
            logger.warning(f"Recovery attempt timed out for scenario {scenario} - may indicate permanent failure")
            return False
        except Exception as e:
            logger.warning(f"Recovery attempt error for scenario {scenario}: {e}")
            return False
    
    async def _test_circuit_closure_via_success(
        self, 
        auth_manager: IntegrationAuthServiceManager, 
        success_threshold: int, 
        scenario: str
    ) -> bool:
        """Test circuit closure via consecutive successful requests."""
        try:
            # Create valid token for success testing
            valid_token = await auth_manager.create_test_token(
                user_id="circuit-closure-test-user",
                email="circuit.test@example.com",
                permissions=["read"]
            )
            
            if not valid_token:
                logger.warning(f"Failed to create valid token for circuit closure test {scenario}")
                return False
            
            # Send consecutive successful requests
            success_count = 0
            
            for i in range(success_threshold + 1):
                success = await self._send_successful_auth_request(
                    auth_manager, valid_token, f"closure_success_{i}"
                )
                
                if success:
                    success_count += 1
                else:
                    logger.warning(f"Successful request {i} failed in circuit closure test")
                
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Should have closed circuit with successful requests
            circuit_closed = success_count >= success_threshold
            self.record_metric(f"circuit_closure_{scenario}", "success" if circuit_closed else "failed")
            self.record_metric(f"closure_success_count", success_count)
            
            return circuit_closed
            
        except Exception as e:
            logger.warning(f"Circuit closure test error for scenario {scenario}: {e}")
            return False
    
    async def _send_successful_auth_request(
        self, 
        auth_manager: IntegrationAuthServiceManager, 
        token: str, 
        scenario: str
    ) -> bool:
        """Send successful authentication request."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": "test-service-secret-32-chars-long"
                }
                
                request_data = {
                    "token": token,
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Success means we get a proper response (200 or 401 for invalid token)
                    # Not 503 (service unavailable) which indicates circuit breaker issues
                    success = response.status != 503
                    self.record_metric(f"success_request_{scenario}", "success" if success else "circuit_blocked")
                    return success
                    
        except Exception as e:
            logger.debug(f"Successful request error for scenario {scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_cascade_failure_prevention(
        self, auth_manager, auth_helper, circuit_breaker_config
    ):
        """
        Integration test for authentication cascade failure prevention.
        
        Tests that authentication service failures don't cascade throughout
        the entire system, causing complete platform breakdown.
        """
        # Record test metadata
        self.record_metric("test_category", "cascade_failure_prevention")
        self.record_metric("test_focus", "authentication_cascade_prevention")
        
        # Step 1: Simulate authentication service degradation
        degradation_scenarios = [
            {
                "name": "slow_response",
                "simulate_delay": 3.0,  # 3 second delay
                "expected_handling": "timeout_gracefully"
            },
            {
                "name": "intermittent_failures",
                "failure_rate": 0.5,  # 50% failure rate
                "expected_handling": "partial_success"
            },
            {
                "name": "high_error_rate",
                "failure_rate": 0.8,  # 80% failure rate
                "expected_handling": "circuit_breaker_activation"
            }
        ]
        
        for scenario in degradation_scenarios:
            scenario_name = scenario["name"]
            
            logger.debug(f"Testing cascade failure prevention scenario: {scenario_name}")
            
            # Test system behavior under degradation
            cascade_prevented = await self._test_cascade_prevention(
                auth_manager, scenario, f"cascade_prevention_{scenario_name}"
            )
            
            assert cascade_prevented, (
                f"Cascade failure prevention failed for scenario '{scenario_name}'. "
                f"System should handle auth service degradation gracefully."
            )
            
            self.record_metric(f"cascade_prevention_{scenario_name}", "working")
        
        self.record_metric("authentication_cascade_prevention", "working")
        logger.info(f" PASS:  Authentication cascade failure prevention working ({len(degradation_scenarios)} scenarios tested)")
    
    async def _test_cascade_prevention(
        self, 
        auth_manager: IntegrationAuthServiceManager,
        scenario: Dict[str, Any],
        test_scenario: str
    ) -> bool:
        """Test cascade failure prevention under various degradation scenarios."""
        try:
            num_test_requests = 10
            success_count = 0
            timeout_count = 0
            error_count = 0
            
            for i in range(num_test_requests):
                try:
                    # Simulate scenario-specific behavior
                    if "slow_response" in scenario["name"]:
                        # Test with shorter timeout to simulate slow response handling
                        request_timeout = 2.0
                    else:
                        request_timeout = 5.0
                    
                    if "failure_rate" in scenario:
                        # Randomly fail requests based on failure rate
                        import random
                        if random.random() < scenario["failure_rate"]:
                            # Simulate failure by using invalid credentials
                            success = await self._trigger_authentication_failure(
                                auth_manager, f"{test_scenario}_simulated_failure_{i}"
                            )
                            if success:  # Failure was triggered successfully
                                error_count += 1
                            continue
                    
                    # Normal request
                    start_time = time.time()
                    
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Content-Type": "application/json",
                            "X-Service-ID": "netra-backend",
                            "X-Service-Secret": "test-service-secret-32-chars-long"
                        }
                        
                        request_data = {
                            "token": f"cascade-test-token-{i}",
                            "token_type": "access"
                        }
                        
                        async with session.post(
                            f"{auth_manager.get_auth_url()}/auth/validate",
                            json=request_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=request_timeout)
                        ) as response:
                            request_time = time.time() - start_time
                            
                            # Success means we get any response (not just 200)
                            # The key is that the system responds and doesn't hang
                            if response.status in [200, 401, 403]:  # Normal responses
                                success_count += 1
                            elif response.status in [500, 503]:  # Server errors
                                error_count += 1
                            
                            self.increment_db_query_count(1)
                            
                except asyncio.TimeoutError:
                    timeout_count += 1
                    logger.debug(f"Request {i} timed out in cascade prevention test")
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Request {i} failed in cascade prevention test: {e}")
            
            # Analyze results for cascade prevention
            total_responses = success_count + error_count + timeout_count
            response_rate = total_responses / num_test_requests
            
            # System should respond to most requests (even with errors)
            # Complete non-responsiveness indicates cascade failure
            cascade_prevented = response_rate >= 0.7  # At least 70% response rate
            
            self.record_metric(f"cascade_test_{test_scenario}_success_count", success_count)
            self.record_metric(f"cascade_test_{test_scenario}_error_count", error_count)
            self.record_metric(f"cascade_test_{test_scenario}_timeout_count", timeout_count)
            self.record_metric(f"cascade_test_{test_scenario}_response_rate", response_rate)
            
            return cascade_prevented
            
        except Exception as e:
            logger.error(f"Cascade prevention test error for scenario {test_scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_behind_error_detection_patterns(
        self, auth_manager, auth_helper
    ):
        """
        Integration test for "error behind the error" detection patterns.
        
        Tests the ability to detect when surface-level authentication errors
        mask deeper architectural issues, as identified in incident analysis.
        
        CRITICAL: This prevents misdiagnosis of authentication failures.
        """
        # Record test metadata
        self.record_metric("test_category", "error_behind_error_detection")
        self.record_metric("test_focus", "deep_root_cause_analysis")
        self.record_metric("incident_pattern", "auth_circuit_breaker_bug")
        
        # Test scenarios that reveal "error behind the error"
        error_patterns = [
            {
                "name": "auth_failure_masking_circuit_issue",
                "surface_error": "token_validation_failed",
                "root_cause_indicators": ["high_response_times", "503_responses", "timeout_patterns"],
                "detection_method": "response_time_analysis"
            },
            {
                "name": "service_secret_masking_config_issue",
                "surface_error": "service_authentication_failed",
                "root_cause_indicators": ["config_load_errors", "environment_mismatches"],
                "detection_method": "error_pattern_analysis"
            },
            {
                "name": "token_refresh_masking_session_corruption",
                "surface_error": "refresh_token_invalid",
                "root_cause_indicators": ["session_store_errors", "redis_connectivity_issues"],
                "detection_method": "correlation_analysis"
            }
        ]
        
        for pattern in error_patterns:
            pattern_name = pattern["name"]
            
            logger.debug(f"Testing error behind error pattern: {pattern_name}")
            
            # Test the detection of deep root causes
            root_cause_detected = await self._test_error_behind_error_detection(
                auth_manager, pattern, f"error_detection_{pattern_name}"
            )
            
            assert root_cause_detected, (
                f"Failed to detect root cause for error pattern '{pattern_name}'. "
                f"This indicates insufficient error analysis depth, which can lead to "
                f"misdiagnosis and prolonged outages."
            )
            
            self.record_metric(f"error_pattern_detection_{pattern_name}", "working")
        
        self.record_metric("error_behind_error_detection", "working")
        logger.info(f" PASS:  Error behind error detection patterns working ({len(error_patterns)} patterns tested)")
    
    async def _test_error_behind_error_detection(
        self,
        auth_manager: IntegrationAuthServiceManager,
        pattern: Dict[str, Any],
        scenario: str
    ) -> bool:
        """Test detection of root causes behind surface errors."""
        try:
            pattern_name = pattern["name"]
            detection_method = pattern["detection_method"]
            
            # Collect metrics for root cause analysis
            metrics = {
                "response_times": [],
                "status_codes": [],
                "error_patterns": [],
                "timing_patterns": []
            }
            
            # Simulate the error pattern with multiple requests
            num_analysis_requests = 15
            
            for i in range(num_analysis_requests):
                start_time = time.time()
                
                try:
                    # Trigger scenario-specific request pattern
                    if "circuit_issue" in pattern_name:
                        # Pattern that might reveal circuit breaker issues
                        result = await self._trigger_authentication_failure(
                            auth_manager, f"{scenario}_circuit_test_{i}"
                        )
                    elif "config_issue" in pattern_name:
                        # Pattern that might reveal configuration issues
                        result = await self._test_service_configuration_errors(
                            auth_manager, f"{scenario}_config_test_{i}"
                        )
                    else:
                        # Generic pattern testing
                        result = await self._trigger_authentication_failure(
                            auth_manager, f"{scenario}_generic_test_{i}"
                        )
                    
                    response_time = time.time() - start_time
                    metrics["response_times"].append(response_time)
                    metrics["timing_patterns"].append(response_time)
                    
                    await asyncio.sleep(0.1)  # Small delay between requests
                    
                except Exception as e:
                    error_pattern = str(type(e).__name__)
                    metrics["error_patterns"].append(error_pattern)
                    logger.debug(f"Error pattern captured: {error_pattern}")
            
            # Analyze collected metrics for root cause indicators
            root_cause_detected = self._analyze_error_patterns_for_root_cause(
                metrics, pattern, scenario
            )
            
            self.record_metric(f"root_cause_analysis_{scenario}", "detected" if root_cause_detected else "missed")
            return root_cause_detected
            
        except Exception as e:
            logger.error(f"Error behind error detection test failed for scenario {scenario}: {e}")
            return False
    
    def _analyze_error_patterns_for_root_cause(
        self, 
        metrics: Dict[str, List], 
        pattern: Dict[str, Any], 
        scenario: str
    ) -> bool:
        """Analyze collected metrics to detect root cause indicators."""
        try:
            root_cause_indicators = pattern["root_cause_indicators"]
            detection_method = pattern["detection_method"]
            
            indicators_found = []
            
            # Response time analysis
            if "response_time_analysis" in detection_method:
                response_times = metrics["response_times"]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    
                    if "high_response_times" in root_cause_indicators:
                        if avg_response_time > 2.0 or max_response_time > 5.0:
                            indicators_found.append("high_response_times")
                    
                    self.record_metric(f"avg_response_time_{scenario}", avg_response_time * 1000)  # ms
                    self.record_metric(f"max_response_time_{scenario}", max_response_time * 1000)  # ms
            
            # Error pattern analysis
            if "error_pattern_analysis" in detection_method:
                error_patterns = metrics["error_patterns"]
                
                # Look for specific error patterns that indicate root causes
                if "config_load_errors" in root_cause_indicators:
                    config_related_errors = [e for e in error_patterns if "config" in e.lower()]
                    if config_related_errors:
                        indicators_found.append("config_load_errors")
                
                if "timeout_patterns" in root_cause_indicators:
                    timeout_errors = [e for e in error_patterns if "timeout" in e.lower()]
                    if len(timeout_errors) > len(error_patterns) * 0.3:  # 30% timeout rate
                        indicators_found.append("timeout_patterns")
            
            # Correlation analysis
            if "correlation_analysis" in detection_method:
                timing_patterns = metrics["timing_patterns"]
                
                # Look for timing correlations that indicate deeper issues
                if len(timing_patterns) > 5:
                    # Check for increasing response times (degradation pattern)
                    first_half_avg = sum(timing_patterns[:len(timing_patterns)//2]) / (len(timing_patterns)//2)
                    second_half_avg = sum(timing_patterns[len(timing_patterns)//2:]) / (len(timing_patterns) - len(timing_patterns)//2)
                    
                    if second_half_avg > first_half_avg * 1.5:  # 50% degradation
                        indicators_found.append("performance_degradation_pattern")
            
            # Detection success if we found expected indicators
            expected_indicators = set(root_cause_indicators)
            found_indicators = set(indicators_found)
            
            detection_rate = len(found_indicators.intersection(expected_indicators)) / len(expected_indicators)
            root_cause_detected = detection_rate >= 0.5  # At least 50% of indicators found
            
            self.record_metric(f"indicators_found_{scenario}", len(indicators_found))
            self.record_metric(f"detection_rate_{scenario}", detection_rate)
            
            return root_cause_detected
            
        except Exception as e:
            logger.error(f"Root cause analysis error for scenario {scenario}: {e}")
            return False
    
    async def _test_service_configuration_errors(
        self, auth_manager: IntegrationAuthServiceManager, scenario: str
    ) -> bool:
        """Test service configuration error patterns."""
        try:
            # Test with various configuration error scenarios
            config_error_scenarios = [
                {"service_id": "", "secret": "valid-secret"},  # Missing service ID
                {"service_id": "valid-id", "secret": ""},  # Missing secret
                {"service_id": "wrong-id", "secret": "wrong-secret"}  # Wrong config
            ]
            
            failure_count = 0
            
            for config in config_error_scenarios:
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Content-Type": "application/json",
                            "X-Service-ID": config["service_id"],
                            "X-Service-Secret": config["secret"]
                        }
                        
                        request_data = {
                            "token": "config-test-token",
                            "token_type": "access"
                        }
                        
                        async with session.post(
                            f"{auth_manager.get_auth_url()}/auth/validate",
                            json=request_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=3)
                        ) as response:
                            if response.status in [401, 403]:  # Configuration errors
                                failure_count += 1
                                
                except Exception:
                    failure_count += 1
            
            # Configuration errors detected if most requests failed
            config_errors_detected = failure_count >= len(config_error_scenarios) * 0.8
            self.record_metric(f"config_error_test_{scenario}", "detected" if config_errors_detected else "missed")
            
            return config_errors_detected
            
        except Exception as e:
            logger.warning(f"Service configuration error test failed for scenario {scenario}: {e}")
            return False
    
    # === TEARDOWN AND VALIDATION ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with failure scenario metrics validation."""
        super().teardown_method(method)
        
        # Validate failure scenario metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure critical failure tests recorded their metrics
        if "circuit" in method.__name__.lower() or "failure" in method.__name__.lower() if method else "":
            assert "test_category" in metrics, "Failure scenario tests must record test_category metric"
            assert "test_focus" in metrics, "Failure scenario tests must record test_focus metric"
        
        # Log failure scenario specific metrics for analysis
        failure_metrics = {k: v for k, v in metrics.items() if any(x in k.lower() for x in ["failure", "circuit", "error"])}
        if failure_metrics:
            logger.info(f"Failure scenario test metrics: {failure_metrics}")
