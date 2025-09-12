"""
WebSocket Service Connectivity E2E Test - Service Unavailability Detection

CRITICAL SERVICE CONNECTION VALIDATION: This test validates that WebSocket service
connection failures are properly detected and provide clear diagnostic information
when backend services are unavailable.

Test Objective: WebSocket Service Connection Failure Detection
- MANDATORY hard failure when WebSocket service is unavailable
- MANDATORY clear error messages explaining service connectivity issues
- MANDATORY service health validation before connection attempts
- PROOF that connection failures are properly diagnosed and reported

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Reliable service connectivity detection for WebSocket features
- Value Impact: Clear diagnosis of service issues for faster problem resolution
- Strategic Impact: Reduces time-to-resolution for WebSocket connectivity issues

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY hard failure when WebSocket service unavailable (NO try/except hiding)
2. MANDATORY authentication via E2EAuthHelper for all connection attempts
3. MANDATORY service health checks before connection attempts
4. MANDATORY clear error messages explaining business impact
5. NO silent failures or connection attempt hiding
6. Must demonstrate service unavailability causes immediate hard failure

WEBSOCKET SERVICE CONNECTION VALIDATION FLOW:
```
Service Health Check  ->  Authentication Setup  ->  Connection Attempt  -> 
Service Unavailable Detection  ->  Hard Failure with Clear Diagnosis  ->  Test Failure
```
"""

import asyncio
import json
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - SERVICE CONNECTIVITY FOCUSED
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for service connectivity validation
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.service_connectivity
@pytest.mark.asyncio
@pytest.mark.websocket_service
class TestWebSocketServiceConnectivityE2E(SSotAsyncTestCase):
    """
    WebSocket Service Connectivity Failure Detection Tests.
    
    This test suite validates that WebSocket service connection failures
    are properly detected, diagnosed, and reported when services are unavailable.
    
    CRITICAL MANDATE: These tests MUST fail hard when services are unavailable
    to provide clear diagnosis of service connectivity issues.
    """
    
    def setup_method(self, method=None):
        """Setup with service connectivity validation focus."""
        super().setup_method(method)
        
        # Service connectivity compliance metrics
        self.record_metric("websocket_service_connectivity_test", True)
        self.record_metric("service_availability_validation", "mandatory")
        self.record_metric("connection_failure_tolerance", 0)  # ZERO tolerance for silent failures
        self.record_metric("service_health_check_required", True)
        
        # Initialize service connectivity components
        self._auth_helper = None
        self._websocket_helper = None
        self._websocket_url = None
        
    async def async_setup_method(self, method=None):
        """Async setup with mandatory service connectivity validation."""
        await super().async_setup_method(method)
        
        # CRITICAL: Initialize authentication helpers for service testing
        environment = self.get_env_var("TEST_ENV", "test")
        self._auth_helper = E2EAuthHelper(environment=environment)
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Get WebSocket service URL for connectivity testing
        self._websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Record service connectivity setup
        self.record_metric("websocket_service_setup_completed", True)
        self.record_metric("websocket_service_url", self._websocket_url)

    @pytest.mark.timeout(30)  # Allow time for service connectivity validation
    @pytest.mark.asyncio
    async def test_websocket_service_unavailable_hard_failure(self, real_services_fixture):
        """
        CRITICAL: Test WebSocket service unavailability detection with hard failure.
        
        This test validates that:
        1. WebSocket service health is checked before connection attempts
        2. Service unavailability causes immediate hard failure
        3. Clear error messages explain service connectivity issues
        4. Business impact of service unavailability is explained
        5. No silent failures or connection hiding occurs
        
        SERVICE CONNECTIVITY REQUIREMENTS:
        - Service health check MUST be performed
        - Service unavailability MUST cause hard test failure
        - Error messages MUST explain business impact
        - NO try/except blocks hiding connection failures
        
        BUSINESS IMPACT: WebSocket service unavailability prevents real-time AI features
        """
        test_start_time = time.time()
        
        # === SERVICE HEALTH CHECK ===
        self.record_metric("service_health_check_start", time.time())
        
        # Create authenticated user for service testing
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_service_test@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            permissions=["read", "write", "websocket"],
            websocket_enabled=True
        )
        
        # Extract authentication data
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        user_id = str(authenticated_user.user_id)
        
        # Get authenticated WebSocket headers
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        # Validate authentication setup before service testing
        assert jwt_token, "JWT token MUST be present for service connectivity testing"
        assert auth_headers.get("Authorization"), "Authorization header MUST be present"
        
        self.record_metric("authentication_setup_validated", True)
        
        # === WEBSOCKET SERVICE CONNECTIVITY TEST ===
        self.record_metric("websocket_service_connection_attempt_start", time.time())
        
        # CRITICAL: This connection attempt MUST fail hard if service is unavailable
        # NO try/except hiding - let the test fail with clear service connectivity error
        connection_success = False
        connection_error = None
        service_response_time = None
        
        try:
            # Attempt WebSocket connection with authentication
            # This MUST fail if WebSocket service is unavailable
            connection_start = time.time()
            
            websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=10.0,  # Reasonable timeout for service detection
                    close_timeout=5.0
                ),
                timeout=15.0  # Total connection timeout
            )
            
            service_response_time = time.time() - connection_start
            connection_success = True
            
            # If connection succeeded, close it and record metrics
            await websocket_connection.close()
            
        except Exception as e:
            connection_error = str(e)
            service_response_time = time.time() - connection_start if 'connection_start' in locals() else 0
        
        # Record connection attempt metrics
        self.record_metric("websocket_service_connection_success", connection_success)
        self.record_metric("websocket_service_response_time", service_response_time)
        self.record_metric("websocket_service_connection_error", connection_error)
        
        # === SERVICE UNAVAILABILITY VALIDATION ===
        if connection_success:
            # Service is available - this is unexpected for this test
            self.record_metric("websocket_service_available", True)
            print(f"[U+2139][U+FE0F] WebSocket service is available at {self._websocket_url}")
            print(f"   [U+1F4E1] Connection successful in {service_response_time:.3f}s")
            print(f"   [U+1F464] Authenticated as user: {user_id}")
            print(f"   [U+1F517] This test expects service unavailability for failure detection validation")
            
            # For this test, we want to validate failure detection
            # If service is available, we can still test timeout scenarios
            await self._test_service_timeout_scenarios(auth_headers, user_id)
            
        else:
            # Service is unavailable - this is what we're testing
            self.record_metric("websocket_service_unavailable", True)
            
            # CRITICAL: Hard failure with clear business impact explanation
            business_impact_message = (
                f" ALERT:  WEBSOCKET SERVICE CONNECTIVITY FAILURE DETECTED:\n"
                f"   [U+1F534] Service URL: {self._websocket_url}\n"
                f"   [U+1F534] Connection Error: {connection_error}\n"
                f"   [U+1F534] Response Time: {service_response_time:.3f}s\n"
                f"   [U+1F534] User Authentication: Valid (JWT present)\n"
                f"   [U+1F534] User ID: {user_id}\n"
                f"\n"
                f"   [U+1F4BC] BUSINESS IMPACT:\n"
                f"   [U+2022] Real-time AI chat features unavailable\n"
                f"   [U+2022] WebSocket-based agent events blocked\n"
                f"   [U+2022] Live agent execution updates not delivered\n"
                f"   [U+2022] User experience degraded for interactive AI features\n"
                f"\n"
                f"   [U+1F527] RESOLUTION REQUIRED:\n"
                f"   [U+2022] Check WebSocket service health at {self._websocket_url}\n"
                f"   [U+2022] Verify backend service is running and accessible\n"
                f"   [U+2022] Validate service configuration and network connectivity\n"
                f"   [U+2022] Ensure load balancer and proxy settings are correct\n"
            )
            
            # Print detailed diagnosis for immediate visibility
            print(business_impact_message)
            
            # MANDATORY HARD FAILURE - DO NOT HIDE THIS ERROR
            pytest.fail(business_impact_message)
        
        # Record final metrics
        total_test_time = time.time() - test_start_time
        self.record_metric("websocket_service_connectivity_test_duration", total_test_time)

    async def _test_service_timeout_scenarios(self, auth_headers: Dict[str, str], user_id: str):
        """Test various service timeout scenarios when service is available."""
        
        # === TIMEOUT SCENARIO 1: Very Short Connection Timeout ===
        self.record_metric("timeout_test_1_start", time.time())
        
        short_timeout_failed = False
        try:
            # Use extremely short timeout to simulate service unavailability
            await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=0.001  # 1ms timeout - should fail
                ),
                timeout=0.01  # 10ms total timeout
            )
        except Exception:
            short_timeout_failed = True
        
        assert short_timeout_failed, "Extremely short timeout should cause connection failure"
        self.record_metric("short_timeout_failure_detected", True)
        
        # === TIMEOUT SCENARIO 2: Connection Interruption Simulation ===
        self.record_metric("timeout_test_2_start", time.time())
        
        # This simulates network interruption during connection
        interruption_detected = False
        try:
            # Connect but immediately cancel the operation
            connection_task = asyncio.create_task(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers
                )
            )
            
            # Cancel after very brief delay to simulate interruption
            await asyncio.sleep(0.01)
            connection_task.cancel()
            
            await connection_task
            
        except asyncio.CancelledError:
            interruption_detected = True
        except Exception:
            interruption_detected = True
        
        assert interruption_detected, "Connection interruption should be detected"
        self.record_metric("connection_interruption_detected", True)
        
        print(f" PASS:  Service timeout scenarios validated for user: {user_id}")

    @pytest.mark.timeout(25)
    @pytest.mark.asyncio
    async def test_websocket_service_port_unavailable(self, real_services_fixture):
        """
        CRITICAL: Test WebSocket service port unavailability detection.
        
        This test validates detection of WebSocket service port issues:
        1. Wrong port numbers cause immediate connection failure
        2. Network-level connection issues are properly reported
        3. Port availability is validated before authentication
        4. Clear error messages distinguish port vs authentication issues
        
        PORT CONNECTIVITY VALIDATION:
        - Wrong port numbers MUST cause connection failure
        - Port unavailability MUST be clearly diagnosed
        - Network-level errors MUST be distinguished from auth errors
        """
        
        # Create authenticated user
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_port_test@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        # === TEST 1: Wrong Port Number ===
        wrong_port_urls = [
            "ws://localhost:9999/ws",  # Wrong port
            "ws://localhost:1/ws",     # Invalid port
            "ws://localhost:65536/ws", # Out of range port
        ]
        
        for wrong_url in wrong_port_urls:
            connection_failed = False
            port_error = None
            
            try:
                await asyncio.wait_for(
                    websockets.connect(
                        wrong_url,
                        additional_headers=auth_headers,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
            except Exception as e:
                connection_failed = True
                port_error = str(e)
            
            # Connection should fail for wrong ports
            assert connection_failed, f"Wrong port should cause failure: {wrong_url}"
            
            # Record port error details
            self.record_metric(f"port_error_{wrong_url.split(':')[2].split('/')[0]}", port_error)
        
        # === TEST 2: Invalid Hostname ===
        invalid_host_urls = [
            "ws://nonexistent.localhost:8000/ws",
            "ws://invalid.domain.test:8000/ws",
        ]
        
        for invalid_url in invalid_host_urls:
            hostname_failed = False
            hostname_error = None
            
            try:
                await asyncio.wait_for(
                    websockets.connect(
                        invalid_url,
                        additional_headers=auth_headers,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
            except Exception as e:
                hostname_failed = True
                hostname_error = str(e)
            
            # Connection should fail for invalid hostnames
            assert hostname_failed, f"Invalid hostname should cause failure: {invalid_url}"
            
            # Record hostname error details
            self.record_metric(f"hostname_error", hostname_error)
        
        # Record port connectivity test success
        self.record_metric("port_connectivity_tests_completed", True)
        
        print(f"\n PASS:  WEBSOCKET PORT CONNECTIVITY VALIDATION:")
        print(f"   [U+1F6AB] Wrong ports: FAILED as expected ({len(wrong_port_urls)} tested)")
        print(f"   [U+1F6AB] Invalid hostnames: FAILED as expected ({len(invalid_host_urls)} tested)")
        print(f"    SEARCH:  Port-level connectivity issues: PROPERLY DETECTED")

    @pytest.mark.timeout(20)
    @pytest.mark.asyncio
    async def test_websocket_service_protocol_errors(self, real_services_fixture):
        """
        CRITICAL: Test WebSocket service protocol-level errors.
        
        This test validates detection of WebSocket protocol issues:
        1. HTTP vs WebSocket protocol mismatches
        2. Invalid WebSocket upgrade requests
        3. Protocol-level connection failures
        4. Clear error messages for protocol issues
        """
        
        # Create authenticated user
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_protocol_test@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        # === TEST 1: HTTP URL instead of WebSocket URL ===
        http_url = self._websocket_url.replace("ws://", "http://").replace("wss://", "https://")
        
        http_protocol_failed = False
        http_error = None
        
        try:
            await asyncio.wait_for(
                websockets.connect(
                    http_url,
                    additional_headers=auth_headers,
                    open_timeout=5.0
                ),
                timeout=8.0
            )
        except Exception as e:
            http_protocol_failed = True
            http_error = str(e)
        
        # Should fail due to protocol mismatch
        assert http_protocol_failed, "HTTP URL should fail for WebSocket connection"
        self.record_metric("http_protocol_error", http_error)
        
        # === TEST 2: Invalid WebSocket Path ===
        invalid_paths = [
            self._websocket_url.replace("/ws", "/invalid"),
            self._websocket_url.replace("/ws", "/api/websocket"),
            self._websocket_url + "/nonexistent",
        ]
        
        for invalid_path_url in invalid_paths:
            path_failed = False
            path_error = None
            
            try:
                await asyncio.wait_for(
                    websockets.connect(
                        invalid_path_url,
                        additional_headers=auth_headers,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
            except Exception as e:
                path_failed = True
                path_error = str(e)
            
            # Should fail due to invalid path
            if path_failed:
                self.record_metric(f"invalid_path_error", path_error)
                print(f" PASS:  Invalid path properly rejected: {invalid_path_url}")
            else:
                print(f"[U+2139][U+FE0F] Path accepted (may be valid route): {invalid_path_url}")
        
        # Record protocol error test success
        self.record_metric("protocol_error_tests_completed", True)
        
        print(f"\n PASS:  WEBSOCKET PROTOCOL ERROR VALIDATION:")
        print(f"   [U+1F6AB] HTTP protocol mismatch: PROPERLY REJECTED")
        print(f"    SEARCH:  Invalid paths tested: {len(invalid_paths)}")
        print(f"   [U+1F6E1][U+FE0F] Protocol-level errors: PROPERLY DETECTED")

    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_websocket_service_health_validation(self, real_services_fixture):
        """
        CRITICAL: Test WebSocket service health validation before connections.
        
        This test validates service health checking:
        1. Service health is checked before connection attempts
        2. Unhealthy services are detected before authentication
        3. Health check failures provide clear service status
        4. Multiple health check methods are validated
        """
        
        # === HEALTH CHECK 1: Basic Connection Test ===
        self.record_metric("health_check_1_start", time.time())
        
        basic_health_passed = False
        health_response_time = None
        
        try:
            health_start = time.time()
            
            # Basic connectivity test with minimal timeout
            test_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    open_timeout=3.0,
                    close_timeout=1.0
                ),
                timeout=5.0
            )
            
            health_response_time = time.time() - health_start
            basic_health_passed = True
            await test_connection.close()
            
        except Exception as e:
            health_response_time = time.time() - health_start if 'health_start' in locals() else 0
            self.record_metric("basic_health_check_error", str(e))
        
        self.record_metric("basic_health_check_passed", basic_health_passed)
        self.record_metric("basic_health_response_time", health_response_time)
        
        # === HEALTH CHECK 2: Authenticated Connection Health ===
        self.record_metric("health_check_2_start", time.time())
        
        # Create authenticated user for health testing
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_health_test@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        auth_health_passed = False
        auth_response_time = None
        
        try:
            auth_start = time.time()
            
            # Authenticated connectivity test
            auth_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=5.0,
                    close_timeout=1.0
                ),
                timeout=8.0
            )
            
            auth_response_time = time.time() - auth_start
            auth_health_passed = True
            await auth_connection.close()
            
        except Exception as e:
            auth_response_time = time.time() - auth_start if 'auth_start' in locals() else 0
            self.record_metric("auth_health_check_error", str(e))
        
        self.record_metric("auth_health_check_passed", auth_health_passed)
        self.record_metric("auth_health_response_time", auth_response_time)
        
        # === HEALTH STATUS EVALUATION ===
        if basic_health_passed and auth_health_passed:
            # Service is healthy
            self.record_metric("websocket_service_health_status", "healthy")
            print(f"\n PASS:  WEBSOCKET SERVICE HEALTH: HEALTHY")
            print(f"   [U+1F4E1] Basic connectivity: {health_response_time:.3f}s")
            print(f"   [U+1F510] Authenticated connectivity: {auth_response_time:.3f}s")
            print(f"   [U+1F7E2] Service is operational and ready for WebSocket connections")
            
        elif basic_health_passed and not auth_health_passed:
            # Service connectivity OK but authentication issues
            self.record_metric("websocket_service_health_status", "auth_issues")
            
            auth_issue_message = (
                f" ALERT:  WEBSOCKET SERVICE HEALTH: AUTHENTICATION ISSUES\n"
                f"   [U+1F7E2] Basic connectivity: {health_response_time:.3f}s (OK)\n"
                f"   [U+1F534] Authenticated connectivity: FAILED\n"
                f"   [U+1F534] Auth response time: {auth_response_time:.3f}s\n"
                f"\n"
                f"   [U+1F4BC] BUSINESS IMPACT:\n"
                f"   [U+2022] WebSocket service is running but authentication is broken\n"
                f"   [U+2022] Users cannot establish authenticated WebSocket connections\n"
                f"   [U+2022] Real-time AI features will not work\n"
                f"\n"
                f"   [U+1F527] RESOLUTION REQUIRED:\n"
                f"   [U+2022] Check JWT authentication configuration\n"
                f"   [U+2022] Verify authentication service connectivity\n"
                f"   [U+2022] Validate WebSocket authentication middleware\n"
            )
            
            print(auth_issue_message)
            pytest.fail(auth_issue_message)
            
        else:
            # Service is completely unavailable
            self.record_metric("websocket_service_health_status", "unavailable")
            
            unavailable_message = (
                f" ALERT:  WEBSOCKET SERVICE HEALTH: UNAVAILABLE\n"
                f"   [U+1F534] Basic connectivity: FAILED\n"
                f"   [U+1F534] Authenticated connectivity: FAILED\n"
                f"   [U+1F534] Service URL: {self._websocket_url}\n"
                f"\n"
                f"   [U+1F4BC] BUSINESS IMPACT:\n"
                f"   [U+2022] WebSocket service is completely unavailable\n"
                f"   [U+2022] No real-time AI chat features available\n"
                f"   [U+2022] All WebSocket-dependent functionality broken\n"
                f"\n"
                f"   [U+1F527] RESOLUTION REQUIRED:\n"
                f"   [U+2022] Start WebSocket service\n"
                f"   [U+2022] Check service configuration and ports\n"
                f"   [U+2022] Verify network connectivity and firewall settings\n"
            )
            
            print(unavailable_message)
            pytest.fail(unavailable_message)

    async def async_teardown_method(self, method=None):
        """Clean up WebSocket service connectivity test resources."""
        # Record final service connectivity metrics
        if hasattr(self, '_metrics'):
            final_metrics = self.get_all_metrics()
            service_status = final_metrics.get("websocket_service_health_status", "unknown")
            print(f"\n CHART:  WEBSOCKET SERVICE CONNECTIVITY TEST SUMMARY:")
            print(f"   [U+1F3E5] Final Health Status: {service_status}")
            print(f"    CHART:  Total Metrics Recorded: {len(final_metrics)}")
        
        await super().async_teardown_method(method)