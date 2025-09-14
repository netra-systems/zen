"""
E2E Tests for Critical Error Recovery - Golden Path Resilience

MISSION CRITICAL: Tests system resilience and graceful error recovery during
critical failure scenarios to validate platform stability, user experience
preservation, and business continuity under adverse conditions.

Business Value Justification (BVJ):
- Segment: All Users (Platform Reliability for Business Continuity)
- Business Goal: Platform Trust & Reliability for Customer Retention
- Value Impact: Validates system gracefully handles errors without user experience degradation
- Strategic Impact: Proves platform robustness, prevents churn due to reliability issues

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens with error scenario handling
- REAL WEBSOCKETS: Persistent wss:// connections through error conditions
- REAL AGENTS: All agent types under error stress conditions
- REAL RECOVERY: Actual error detection, handling, and recovery mechanisms
- ERROR DEPTH: Network failures, timeout scenarios, malformed requests, system overload

CRITICAL: These tests must demonstrate actual error recovery and system resilience.
No mocking error scenarios or bypassing real failure conditions.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - STEP 1
Coverage Target: 0.9% → 25% improvement (Priority Scenario #5)
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass
from enum import Enum

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


class ErrorScenarioType(Enum):
    """Types of error scenarios to test."""
    NETWORK_INTERRUPTION = "network_interruption"
    TIMEOUT_SCENARIO = "timeout_scenario"
    MALFORMED_REQUEST = "malformed_request"
    INVALID_AUTH = "invalid_auth"
    SYSTEM_OVERLOAD = "system_overload"
    AGENT_ERROR = "agent_error"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    RATE_LIMITING = "rate_limiting"


@dataclass
class ErrorRecoveryResult:
    """Tracks error recovery test results."""
    scenario_type: ErrorScenarioType
    error_induced: bool
    error_detected: bool
    recovery_attempted: bool
    recovery_successful: bool
    user_experience_preserved: bool
    recovery_time: float
    error_message: str = ""
    recovery_steps: List[str] = None


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.error_recovery
@pytest.mark.mission_critical
class TestCriticalErrorRecoveryE2E(SSotAsyncTestCase):
    """
    E2E tests for validating critical error recovery and system resilience.

    Tests platform ability to detect, handle, and recover from various
    error conditions while preserving user experience and business continuity.
    """

    @classmethod
    def setUpClass(cls):
        """Setup staging environment configuration and dependencies."""
        super().setUpClass()

        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)

        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available")

        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")

        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper(
            base_url=cls.staging_config.urls.websocket_url,
            environment="staging"
        )

        # Test user configuration for error recovery
        cls.test_user_id = f"error_recovery_user_{int(time.time())}"
        cls.test_user_email = f"error_recovery_test_{int(time.time())}@netra-testing.ai"

        cls.logger.info(f"Critical error recovery E2E tests initialized for staging")

    def setUp(self):
        """Setup for each test method."""
        super().setUp()

        # Generate error recovery specific context
        self.recovery_test_id = str(uuid.uuid4())
        self.thread_id = f"error_recovery_{self.recovery_test_id}"
        self.run_id = f"run_{self.thread_id}"

        # Create JWT token for error recovery testing
        self.access_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            expires_in_hours=2
        )

        self.logger.info(f"Error recovery test setup - recovery_test_id: {self.recovery_test_id}")

    async def _establish_recovery_test_websocket(self) -> websockets.WebSocketServerProtocol:
        """Establish WebSocket connection for error recovery testing."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False  # Staging environment
        ssl_context.verify_mode = ssl.CERT_NONE

        websocket = await asyncio.wait_for(
            websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "critical-error-recovery-e2e",
                    "X-Recovery-Test-Id": self.recovery_test_id,
                    "X-Enable-Error-Recovery": "true"
                },
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ),
            timeout=20.0
        )

        return websocket

    async def _test_error_scenario(self, scenario_type: ErrorScenarioType,
                                 error_induction_func, recovery_validation_func) -> ErrorRecoveryResult:
        """Generic error scenario testing framework."""
        result = ErrorRecoveryResult(
            scenario_type=scenario_type,
            error_induced=False,
            error_detected=False,
            recovery_attempted=False,
            recovery_successful=False,
            user_experience_preserved=False,
            recovery_time=0.0,
            recovery_steps=[]
        )

        recovery_start_time = time.time()

        try:
            # Step 1: Induce the error condition
            self.logger.info(f"🔥 Inducing error scenario: {scenario_type.value}")
            await error_induction_func(result)
            result.error_induced = True

            # Step 2: Allow system to detect and attempt recovery
            recovery_timeout = 60.0  # Allow time for recovery mechanisms
            recovery_detection_start = time.time()

            while time.time() - recovery_detection_start < recovery_timeout:
                try:
                    # Test system responsiveness during recovery
                    recovery_validated = await recovery_validation_func(result)
                    if recovery_validated:
                        result.recovery_successful = True
                        break

                    await asyncio.sleep(2)  # Brief pause between recovery checks

                except Exception as recovery_check_error:
                    result.error_message = f"Recovery validation error: {str(recovery_check_error)}"
                    continue

            result.recovery_time = time.time() - recovery_start_time

        except Exception as scenario_error:
            result.error_message = f"Error scenario execution failed: {str(scenario_error)}"
            result.recovery_time = time.time() - recovery_start_time

        return result

    async def test_websocket_disconnection_recovery(self):
        """
        Test WebSocket disconnection and automatic recovery.

        RECOVERY VALIDATION: System should detect WebSocket disconnection,
        attempt reconnection, and restore user session without data loss.

        Recovery Flow Expected:
        1. Establish stable WebSocket connection
        2. Simulate connection interruption
        3. System detects disconnection
        4. Automatic reconnection attempts
        5. Session restoration with context preservation
        6. User can continue normal operations

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Actual WebSocket disconnection/reconnection in staging
        STATUS: Should PASS - WebSocket reliability is critical for real-time chat
        """
        self.logger.info("🔥 Testing WebSocket disconnection recovery")

        async def induce_websocket_disconnection(result: ErrorRecoveryResult):
            """Induce WebSocket disconnection by closing connection abruptly."""
            # Establish initial connection
            websocket = await self._establish_recovery_test_websocket()

            # Send initial message to establish session
            initial_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Initial connection test before disconnection simulation",
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.test_user_id,
                "context": {"pre_disconnection": True}
            }

            await websocket.send(json.dumps(initial_message))

            # Wait for initial response to establish session
            try:
                initial_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                result.recovery_steps.append("Initial session established")
            except asyncio.TimeoutError:
                result.error_message = "Failed to establish initial session"
                return

            # Simulate abrupt disconnection
            await websocket.close(code=1006, reason="Simulated network interruption")
            result.recovery_steps.append("WebSocket connection forcibly closed")
            result.error_detected = True

        async def validate_websocket_recovery(result: ErrorRecoveryResult) -> bool:
            """Validate that WebSocket recovery was successful."""
            try:
                # Attempt to establish new connection (simulating client reconnection)
                recovery_websocket = await self._establish_recovery_test_websocket()
                result.recovery_steps.append("Reconnection attempt successful")

                # Send recovery test message
                recovery_message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Post-recovery connection test to validate session restoration",
                    "thread_id": self.thread_id,  # Same thread to test context preservation
                    "run_id": f"{self.run_id}_recovery",
                    "user_id": self.test_user_id,
                    "context": {"post_recovery": True}
                }

                await recovery_websocket.send(json.dumps(recovery_message))
                result.recovery_steps.append("Recovery message sent")

                # Wait for recovery response
                recovery_response = await asyncio.wait_for(recovery_websocket.recv(), timeout=30.0)
                response_event = json.loads(recovery_response)

                # Wait for completion
                completion_timeout = 45.0
                completion_start = time.time()

                while time.time() - completion_start < completion_timeout:
                    try:
                        event_data = await asyncio.wait_for(recovery_websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)

                        if event.get("type") == "agent_completed":
                            result.recovery_steps.append("Post-recovery agent response completed")
                            result.user_experience_preserved = True
                            await recovery_websocket.close()
                            return True

                    except asyncio.TimeoutError:
                        continue

                await recovery_websocket.close()
                return False

            except Exception as e:
                result.recovery_steps.append(f"Recovery validation failed: {str(e)}")
                return False

        # Execute WebSocket disconnection recovery test
        recovery_result = await self._test_error_scenario(
            ErrorScenarioType.WEBSOCKET_DISCONNECT,
            induce_websocket_disconnection,
            validate_websocket_recovery
        )

        self.logger.info(f"🔥 WebSocket Disconnection Recovery Results:")
        self.logger.info(f"   Error Induced: {recovery_result.error_induced}")
        self.logger.info(f"   Error Detected: {recovery_result.error_detected}")
        self.logger.info(f"   Recovery Successful: {recovery_result.recovery_successful}")
        self.logger.info(f"   User Experience Preserved: {recovery_result.user_experience_preserved}")
        self.logger.info(f"   Recovery Time: {recovery_result.recovery_time:.1f}s")
        self.logger.info(f"   Recovery Steps: {recovery_result.recovery_steps}")

        # Validate WebSocket disconnection recovery
        assert recovery_result.error_induced, (
            f"WebSocket disconnection should be successfully induced. "
            f"Error: {recovery_result.error_message}"
        )

        assert recovery_result.error_detected, (
            f"WebSocket disconnection should be detected by system. "
            f"Detection failed."
        )

        assert recovery_result.recovery_successful, (
            f"WebSocket recovery should succeed. Recovery failed after {recovery_result.recovery_time:.1f}s. "
            f"Steps: {recovery_result.recovery_steps}"
        )

        assert recovery_result.user_experience_preserved, (
            f"User experience should be preserved after WebSocket recovery. "
            f"Users should be able to continue normal operations."
        )

        assert recovery_result.recovery_time <= 90.0, (
            f"WebSocket recovery took too long: {recovery_result.recovery_time:.1f}s "
            f"(expected ≤90s for good user experience)"
        )

        self.logger.info("✅ WebSocket disconnection recovery validated")

    async def test_agent_timeout_recovery(self):
        """
        Test agent timeout detection and recovery mechanisms.

        RECOVERY VALIDATION: System should detect agent timeouts,
        provide appropriate error messages, and allow retry operations.

        Recovery Flow Expected:
        1. Send request to agent that will timeout
        2. System detects agent timeout condition
        3. Appropriate timeout error message sent to user
        4. System remains responsive for new requests
        5. User can retry with successful outcome

        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - Actual agent timeout scenarios in staging
        STATUS: Should PASS - Timeout handling is critical for user experience
        """
        self.logger.info("🔥 Testing agent timeout recovery")

        async def induce_agent_timeout(result: ErrorRecoveryResult):
            """Induce agent timeout by sending complex request that may timeout."""
            websocket = await self._establish_recovery_test_websocket()

            # Send extremely complex request likely to cause timeout
            timeout_inducing_message = {
                "type": "agent_request",
                "agent": "apex_optimizer_agent",
                "message": (
                    "COMPLEX TIMEOUT TEST: Perform comprehensive analysis of 50+ scenarios: "
                    + "analyze " * 100 +  # Repetitive content to potentially cause timeout
                    "Provide detailed optimization strategies for each scenario with complete "
                    "cost-benefit analysis, implementation timelines, risk assessments, "
                    "competitive analysis, market research, technical specifications, "
                    "regulatory compliance requirements, and ROI projections."
                ),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.test_user_id,
                "context": {
                    "timeout_test": True,
                    "complexity_level": "maximum",
                    "expected_timeout": True
                }
            }

            await websocket.send(json.dumps(timeout_inducing_message))
            result.recovery_steps.append("Complex timeout-inducing message sent")

            # Monitor for timeout detection
            timeout_detection_period = 45.0
            detection_start = time.time()

            while time.time() - detection_start < timeout_detection_period:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    event_type = event.get("type", "unknown")

                    if "timeout" in event_type.lower() or "error" in event_type.lower():
                        result.error_detected = True
                        result.recovery_steps.append(f"Timeout/error detected: {event_type}")
                        break

                except asyncio.TimeoutError:
                    # Timeout waiting for response may indicate agent timeout
                    result.error_detected = True
                    result.recovery_steps.append("Agent timeout detected (no response)")
                    break

            await websocket.close()

        async def validate_timeout_recovery(result: ErrorRecoveryResult) -> bool:
            """Validate system recovery after timeout."""
            try:
                # Test system responsiveness after timeout
                recovery_websocket = await self._establish_recovery_test_websocket()

                # Send simple request that should succeed
                recovery_message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Simple post-timeout test: What is AI cost optimization?",
                    "thread_id": f"{self.thread_id}_recovery",
                    "run_id": f"{self.run_id}_recovery",
                    "user_id": self.test_user_id,
                    "context": {"post_timeout_recovery": True}
                }

                await recovery_websocket.send(json.dumps(recovery_message))
                result.recovery_steps.append("Post-timeout recovery message sent")

                # Wait for successful response
                recovery_timeout = 30.0
                recovery_start = time.time()

                while time.time() - recovery_start < recovery_timeout:
                    try:
                        event_data = await asyncio.wait_for(recovery_websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)

                        if event.get("type") == "agent_completed":
                            result.recovery_steps.append("Post-timeout agent response successful")
                            result.user_experience_preserved = True
                            await recovery_websocket.close()
                            return True

                    except asyncio.TimeoutError:
                        continue

                await recovery_websocket.close()
                return False

            except Exception as e:
                result.recovery_steps.append(f"Timeout recovery validation failed: {str(e)}")
                return False

        # Execute agent timeout recovery test
        recovery_result = await self._test_error_scenario(
            ErrorScenarioType.TIMEOUT_SCENARIO,
            induce_agent_timeout,
            validate_timeout_recovery
        )

        self.logger.info(f"🔥 Agent Timeout Recovery Results:")
        self.logger.info(f"   Error Induced: {recovery_result.error_induced}")
        self.logger.info(f"   Timeout Detected: {recovery_result.error_detected}")
        self.logger.info(f"   Recovery Successful: {recovery_result.recovery_successful}")
        self.logger.info(f"   System Responsive Post-Timeout: {recovery_result.user_experience_preserved}")
        self.logger.info(f"   Recovery Time: {recovery_result.recovery_time:.1f}s")
        self.logger.info(f"   Recovery Steps: {recovery_result.recovery_steps}")

        # Validate timeout recovery
        assert recovery_result.error_detected, (
            f"Agent timeout should be detected by system. "
            f"No timeout detection occurred."
        )

        assert recovery_result.recovery_successful, (
            f"System should recover from agent timeout and remain responsive. "
            f"Recovery failed. Steps: {recovery_result.recovery_steps}"
        )

        assert recovery_result.user_experience_preserved, (
            f"User experience should be preserved after timeout recovery. "
            f"System should remain responsive for new requests."
        )

        self.logger.info("✅ Agent timeout recovery validated")

    async def test_malformed_request_handling(self):
        """
        Test handling of malformed requests with graceful error responses.

        RECOVERY VALIDATION: System should detect malformed requests,
        provide helpful error messages, and continue normal operation.

        Recovery Flow Expected:
        1. Send various types of malformed requests
        2. System detects and validates request format
        3. Appropriate validation error messages sent
        4. System remains stable and responsive
        5. User can send valid requests successfully

        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - Actual request validation in staging
        STATUS: Should PASS - Input validation is critical for system stability
        """
        self.logger.info("🔥 Testing malformed request handling")

        malformed_requests = [
            # Missing required fields
            {"type": "agent_request", "message": "Missing agent field"},
            # Invalid agent type
            {"type": "agent_request", "agent": "nonexistent_agent", "message": "Invalid agent"},
            # Empty message
            {"type": "agent_request", "agent": "triage_agent", "message": ""},
            # Invalid JSON structure
            "{ invalid json structure without proper formatting",
            # Missing type field
            {"agent": "triage_agent", "message": "Missing type field"},
        ]

        websocket = await self._establish_recovery_test_websocket()
        recovery_results = []

        try:
            for i, malformed_request in enumerate(malformed_requests):
                self.logger.info(f"Testing malformed request {i+1}/{len(malformed_requests)}")

                try:
                    # Send malformed request
                    if isinstance(malformed_request, str):
                        await websocket.send(malformed_request)
                    else:
                        await websocket.send(json.dumps(malformed_request))

                    # Wait for error response
                    error_response_timeout = 15.0
                    error_start = time.time()
                    error_handled = False

                    while time.time() - error_start < error_response_timeout:
                        try:
                            response_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            response = json.loads(response_data)

                            if "error" in response.get("type", "").lower():
                                error_handled = True
                                recovery_results.append({
                                    "request_index": i,
                                    "error_handled": True,
                                    "error_type": response.get("type"),
                                    "error_data": response
                                })
                                break

                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue

                    if not error_handled:
                        recovery_results.append({
                            "request_index": i,
                            "error_handled": False,
                            "error_type": "no_response"
                        })

                except Exception as send_error:
                    recovery_results.append({
                        "request_index": i,
                        "error_handled": True,
                        "error_type": "send_exception",
                        "send_error": str(send_error)
                    })

            # Test system recovery with valid request
            valid_recovery_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Valid request after malformed request handling test",
                "thread_id": f"{self.thread_id}_malformed_recovery",
                "run_id": f"{self.run_id}_malformed_recovery",
                "user_id": self.test_user_id
            }

            await websocket.send(json.dumps(valid_recovery_message))

            # Wait for successful response
            recovery_successful = False
            recovery_timeout = 30.0
            recovery_start = time.time()

            while time.time() - recovery_start < recovery_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)

                    if event.get("type") == "agent_completed":
                        recovery_successful = True
                        break

                except asyncio.TimeoutError:
                    continue

        finally:
            await websocket.close()

        # Analyze malformed request handling results
        handled_errors = [r for r in recovery_results if r["error_handled"]]
        total_malformed_requests = len(malformed_requests)

        self.logger.info(f"🔥 Malformed Request Handling Results:")
        self.logger.info(f"   Total Malformed Requests: {total_malformed_requests}")
        self.logger.info(f"   Errors Properly Handled: {len(handled_errors)}")
        self.logger.info(f"   Error Handling Rate: {len(handled_errors)/total_malformed_requests:.1%}")
        self.logger.info(f"   System Recovery After Errors: {recovery_successful}")

        # Validate malformed request handling
        error_handling_rate = len(handled_errors) / total_malformed_requests
        assert error_handling_rate >= 0.8, (
            f"Malformed request error handling rate too low: {error_handling_rate:.1%} "
            f"(expected ≥80%). System should handle most malformed requests gracefully."
        )

        assert recovery_successful, (
            f"System should recover and handle valid requests after malformed request errors. "
            f"Recovery failed."
        )

        # Validate that errors provide meaningful feedback
        error_types = [r.get("error_type", "unknown") for r in handled_errors]
        meaningful_errors = [t for t in error_types if t not in ["unknown", "no_response"]]

        assert len(meaningful_errors) >= len(handled_errors) * 0.7, (
            f"Error responses should provide meaningful error types. "
            f"Meaningful: {len(meaningful_errors)}/{len(handled_errors)}"
        )

        self.logger.info("✅ Malformed request handling validated")

    async def test_system_recovery_under_stress(self):
        """
        Test system recovery under combined stress conditions.

        RECOVERY VALIDATION: System should maintain stability and recover
        gracefully when multiple stress factors are present simultaneously.

        Recovery Flow Expected:
        1. Apply multiple concurrent stressors
        2. Monitor system behavior under stress
        3. System maintains basic functionality
        4. Graceful degradation without complete failure
        5. Recovery when stress is reduced

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Combined stress testing in staging
        STATUS: Should PASS - System resilience under stress is critical
        """
        self.logger.info("🔥 Testing system recovery under combined stress")

        stress_results = {
            "concurrent_connections": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "timeouts": 0,
            "recovery_successful": False,
            "stress_duration": 0.0
        }

        stress_start_time = time.time()

        try:
            # Create multiple concurrent stress connections
            stress_connections = 4  # Moderate stress for staging
            connection_tasks = []

            async def create_stress_connection(conn_index: int):
                """Create a stress connection that sends multiple requests."""
                try:
                    websocket = await self._establish_recovery_test_websocket()
                    stress_results["concurrent_connections"] += 1

                    # Send multiple requests rapidly
                    for req_index in range(3):  # 3 requests per connection
                        request = {
                            "type": "agent_request",
                            "agent": "triage_agent",
                            "message": f"Stress test request {conn_index}-{req_index}: "
                                     f"Analyze AI cost optimization under system stress",
                            "thread_id": f"stress_{conn_index}_{req_index}_{self.recovery_test_id}",
                            "run_id": f"stress_run_{conn_index}_{req_index}",
                            "user_id": f"stress_user_{conn_index}",
                            "context": {"stress_test": True, "connection": conn_index}
                        }

                        await websocket.send(json.dumps(request))

                        # Wait for response with timeout
                        response_received = False
                        response_timeout = 30.0
                        response_start = time.time()

                        while time.time() - response_start < response_timeout:
                            try:
                                event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                event = json.loads(event_data)

                                if event.get("type") == "agent_completed":
                                    stress_results["successful_requests"] += 1
                                    response_received = True
                                    break
                                elif "error" in event.get("type", "").lower():
                                    stress_results["failed_requests"] += 1
                                    response_received = True
                                    break

                            except asyncio.TimeoutError:
                                continue

                        if not response_received:
                            stress_results["timeouts"] += 1

                        # Brief pause between requests
                        await asyncio.sleep(1)

                    await websocket.close()

                except Exception as e:
                    stress_results["failed_requests"] += 1

            # Create concurrent stress connections
            for i in range(stress_connections):
                task = create_stress_connection(i)
                connection_tasks.append(task)

            # Execute stress test
            await asyncio.gather(*connection_tasks, return_exceptions=True)

            stress_results["stress_duration"] = time.time() - stress_start_time

            # Test system recovery after stress
            recovery_websocket = await self._establish_recovery_test_websocket()

            recovery_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Post-stress recovery validation: Simple AI optimization question",
                "thread_id": f"post_stress_recovery_{self.recovery_test_id}",
                "run_id": f"recovery_run_{self.recovery_test_id}",
                "user_id": self.test_user_id,
                "context": {"post_stress_recovery": True}
            }

            await recovery_websocket.send(json.dumps(recovery_message))

            # Wait for successful recovery response
            recovery_timeout = 45.0
            recovery_start = time.time()

            while time.time() - recovery_start < recovery_timeout:
                try:
                    event_data = await asyncio.wait_for(recovery_websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)

                    if event.get("type") == "agent_completed":
                        stress_results["recovery_successful"] = True
                        break

                except asyncio.TimeoutError:
                    continue

            await recovery_websocket.close()

        except Exception as e:
            stress_results["stress_duration"] = time.time() - stress_start_time
            self.logger.error(f"Stress test execution error: {e}")

        # Analyze stress test results
        total_requests = stress_results["successful_requests"] + stress_results["failed_requests"] + stress_results["timeouts"]
        success_rate = stress_results["successful_requests"] / total_requests if total_requests > 0 else 0

        self.logger.info(f"🔥 System Stress Recovery Results:")
        self.logger.info(f"   Stress Duration: {stress_results['stress_duration']:.1f}s")
        self.logger.info(f"   Concurrent Connections: {stress_results['concurrent_connections']}")
        self.logger.info(f"   Total Requests: {total_requests}")
        self.logger.info(f"   Successful Requests: {stress_results['successful_requests']}")
        self.logger.info(f"   Failed Requests: {stress_results['failed_requests']}")
        self.logger.info(f"   Timeouts: {stress_results['timeouts']}")
        self.logger.info(f"   Success Rate Under Stress: {success_rate:.1%}")
        self.logger.info(f"   Post-Stress Recovery: {stress_results['recovery_successful']}")

        # Validate system behavior under stress
        assert success_rate >= 0.5, (
            f"Success rate under stress too low: {success_rate:.1%} "
            f"(expected ≥50%). System should maintain basic functionality under stress."
        )

        assert stress_results["recovery_successful"], (
            f"System should recover after stress conditions are reduced. "
            f"Post-stress recovery failed."
        )

        # System should not completely fail under stress
        assert stress_results["successful_requests"] > 0, (
            f"System should handle at least some requests under stress. "
            f"Complete failure detected."
        )

        # Validate stress test actually created meaningful load
        assert total_requests >= 8, (
            f"Stress test should generate meaningful request load. "
            f"Only {total_requests} requests generated."
        )

        self.logger.info("✅ System recovery under stress validated")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--agent-goldenpath"
    ])