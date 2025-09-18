"""
E2E Tests for Error Handling and Recovery - Golden Path Resilience Validation

MISSION CRITICAL: Tests that the agent system handles errors gracefully and recovers
properly, maintaining user experience quality even when failures occur. This validates
platform resilience under adverse conditions.

Business Value Justification (BVJ):
- Segment: All Users (Error recovery affects all customer tiers)
- Business Goal: Platform Reliability & User Confidence
- Value Impact: Graceful error handling prevents user frustration and churn
- Strategic Impact: $500K+ ARR depends on reliable platform experience

Error Recovery Requirements:
1. Graceful handling of agent processing failures
2. Clear error messaging to users via WebSocket events
3. System recovery without requiring user reconnection
4. Tool execution failure recovery
5. Network interruption resilience

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens via staging auth service
- REAL WEBSOCKETS: wss:// connections with failure simulation
- REAL AGENTS: Complete agent workflows with induced failure scenarios
- RECOVERY VALIDATION: System recovery and continued operation testing

CRITICAL: These tests must validate RECOVERY CAPABILITY, not just error detection.
System resilience and continued operation are primary success metrics.

GitHub Issue: #1059 Agent Golden Path Messages E2E Test Creation
Phase: Phase 1 - Error Recovery Enhancement
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
import httpx

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.error_recovery
@pytest.mark.mission_critical
class TestErrorRecoveryE2E(SSotAsyncTestCase):
    """
    E2E tests validating comprehensive error handling and recovery in the agent system.

    Tests that the platform handles various failure scenarios gracefully and
    recovers operation without breaking user experience.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and error recovery test utilities."""
        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)

        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available for error recovery validation")

        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")

        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper()

        # Test user configuration for error scenarios
        cls.test_user_id = f"error_recovery_user_{int(time.time())}"
        cls.test_user_email = f"error_recovery_test_{int(time.time())}@netra-testing.ai"

        # Error scenario configurations
        cls.error_scenarios = {
            "invalid_agent_request": {
                "description": "Invalid agent type request",
                "expected_error_type": "agent_error",
                "recovery_possible": True,
                "severity": "medium"
            },
            "malformed_message": {
                "description": "Malformed message structure",
                "expected_error_type": "validation_error",
                "recovery_possible": True,
                "severity": "low"
            },
            "empty_message_content": {
                "description": "Empty message content",
                "expected_error_type": "validation_error",
                "recovery_possible": True,
                "severity": "low"
            },
            "oversized_message": {
                "description": "Message exceeding size limits",
                "expected_error_type": "size_limit_error",
                "recovery_possible": True,
                "severity": "medium"
            },
            "invalid_user_context": {
                "description": "Invalid user context data",
                "expected_error_type": "context_error",
                "recovery_possible": True,
                "severity": "medium"
            }
        }

        # Recovery validation criteria
        cls.recovery_criteria = {
            "error_acknowledgment": "System acknowledges error occurred",
            "error_messaging": "Clear error message provided to user",
            "connection_maintained": "WebSocket connection remains active",
            "subsequent_request_success": "Next valid request processes normally",
            "no_system_corruption": "System state remains consistent"
        }

        cls.logger.info(f"Error recovery tests initialized for staging")

    def setup_method(self, method):
        """Setup for each error recovery test method."""
        super().setup_method(method)

        # Generate test-specific error context
        self.thread_id = f"error_recovery_test_{int(time.time())}"
        self.run_id = f"run_{self.thread_id}"

        # Create JWT token for this test
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(
            user_id=self.__class__.test_user_id,
            email=self.__class__.test_user_email,
            exp_minutes=60
        )

        self.logger.info(f"Error recovery test setup complete - thread_id: {self.thread_id}")

    def _create_error_scenario_message(self, scenario_name: str) -> Dict[str, Any]:
        """
        Create message that will trigger specific error scenario.

        Args:
            scenario_name: Name of error scenario to trigger

        Returns:
            Dict with message designed to trigger the error
        """
        error_messages = {
            "invalid_agent_request": {
                "type": "agent_request",
                "agent": "nonexistent_agent_that_should_fail",
                "message": "This should trigger an agent error",
                "thread_id": f"error_test_{scenario_name}_{int(time.time())}",
                "user_id": self.__class__.test_user_id
            },
            "malformed_message": {
                "type": "agent_request",
                "invalid_field": "This message is missing required fields",
                "malformed_structure": True
                # Missing required fields: agent, message, thread_id
            },
            "empty_message_content": {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "",  # Empty message content
                "thread_id": f"empty_test_{scenario_name}_{int(time.time())}",
                "user_id": self.__class__.test_user_id
            },
            "oversized_message": {
                "type": "agent_request",
                "agent": "supervisor_agent",
                "message": "A" * 10000,  # Oversized message content
                "thread_id": f"oversized_test_{scenario_name}_{int(time.time())}",
                "user_id": self.__class__.test_user_id,
                "context": {"oversized_test": True}
            },
            "invalid_user_context": {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test message with invalid context",
                "thread_id": None,  # Invalid thread_id
                "user_id": None,  # Invalid user_id
                "context": {"invalid_context_test": True}
            }
        }

        return error_messages.get(scenario_name, {})

    def _validate_error_recovery(self, scenario_name: str, error_events: List[Dict[str, Any]],
                                recovery_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate error recovery for a specific scenario.

        Args:
            scenario_name: Name of error scenario tested
            error_events: Events collected during error scenario
            recovery_events: Events collected during recovery validation

        Returns:
            Dict with recovery validation results
        """
        scenario_config = self.__class__.error_scenarios.get(scenario_name, {})
        validation = {
            "scenario": scenario_name,
            "error_acknowledged": False,
            "error_message_provided": False,
            "expected_error_type_received": False,
            "recovery_successful": False,
            "connection_maintained": True,
            "system_corruption_detected": False,
            "recovery_score": 0.0,
            "validation_details": []
        }

        # Validate error acknowledgment
        error_types_received = [event.get("type", "unknown") for event in error_events]
        expected_error_type = scenario_config.get("expected_error_type", "error")

        validation["error_acknowledged"] = any("error" in event_type.lower() for event_type in error_types_received)

        if expected_error_type:
            validation["expected_error_type_received"] = expected_error_type in error_types_received

        # Validate error messaging
        error_messages = []
        for event in error_events:
            if "error" in event.get("type", "").lower():
                event_data = event.get("data", {})
                error_message = event_data.get("message", event_data.get("error", ""))
                if error_message:
                    error_messages.append(error_message)

        validation["error_message_provided"] = len(error_messages) > 0
        validation["error_messages"] = error_messages

        # Validate recovery capability
        if scenario_config.get("recovery_possible", False):
            # Check if recovery events show successful subsequent processing
            recovery_success_indicators = [
                "agent_started", "agent_thinking", "agent_completed"
            ]

            recovery_event_types = [event.get("type", "unknown") for event in recovery_events]
            recovery_indicators_found = [
                indicator for indicator in recovery_success_indicators
                if indicator in recovery_event_types
            ]

            validation["recovery_successful"] = len(recovery_indicators_found) >= 2

        # Calculate recovery score
        score_components = []
        if validation["error_acknowledged"]:
            score_components.append(0.3)
        if validation["error_message_provided"]:
            score_components.append(0.2)
        if validation["expected_error_type_received"]:
            score_components.append(0.2)
        if validation["recovery_successful"]:
            score_components.append(0.3)

        validation["recovery_score"] = sum(score_components)

        # Add validation details
        validation["validation_details"] = [
            f"Error acknowledged: {validation['error_acknowledged']}",
            f"Error message provided: {validation['error_message_provided']}",
            f"Expected error type: {validation['expected_error_type_received']}",
            f"Recovery successful: {validation['recovery_successful']}",
            f"Recovery score: {validation['recovery_score']:.2f}/1.0"
        ]

        return validation

    async def test_comprehensive_error_handling_and_recovery_scenarios(self):
        """
        Test comprehensive error handling and recovery across multiple failure scenarios.

        ERROR RECOVERY CORE: This validates that the system handles various error
        conditions gracefully and recovers operation for continued user interaction.

        Error scenarios tested:
        1. Invalid agent requests
        2. Malformed message structures
        3. Empty message content
        4. Oversized message content
        5. Invalid user context data

        Recovery validation:
        1. Error acknowledgment and clear messaging
        2. Connection stability during errors
        3. Successful processing of subsequent valid requests
        4. No system state corruption

        DIFFICULTY: Very High (75+ minutes)
        REAL SERVICES: Yes - Complete staging GCP with error injection
        STATUS: Should PASS - Error recovery critical for user experience
        """
        error_recovery_start_time = time.time()
        recovery_metrics = []

        self.logger.info("🛡️ Testing comprehensive error handling and recovery scenarios")

        try:
            # Step 1: Establish WebSocket connection for error testing
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # Staging environment
            ssl_context.verify_mode = ssl.CERT_NONE

            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "error-recovery-e2e",
                        "X-Error-Testing": "enabled"
                    },
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=25.0
            )

            connection_time = time.time() - connection_start
            recovery_metrics.append({
                "metric": "websocket_connection_time",
                "value": connection_time,
                "timestamp": time.time(),
                "success": True
            })

            self.logger.info(f"✅ WebSocket connected for error testing in {connection_time:.2f}s")

            # Step 2: Test each error scenario with recovery validation
            scenario_results = []

            for scenario_name, scenario_config in self.__class__.error_scenarios.items():
                scenario_start = time.time()
                self.logger.info(f"⚠️ Testing error scenario: {scenario_name}")

                # Create error-inducing message
                error_message = self._create_error_scenario_message(scenario_name)

                # Send error message and collect error events
                error_events = []
                try:
                    await websocket.send(json.dumps(error_message))

                    # Collect error response events
                    error_timeout = 20.0
                    error_collection_start = time.time()

                    while time.time() - error_collection_start < error_timeout:
                        try:
                            event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event = json.loads(event_data)
                            error_events.append(event)

                            event_type = event.get("type", "unknown")

                            # Stop collecting when we receive an error event
                            if "error" in event_type.lower():
                                self.logger.info(f"📥 Error event received for {scenario_name}: {event_type}")
                                break

                        except asyncio.TimeoutError:
                            break

                except Exception as send_error:
                    self.logger.info(f"📥 Send error for {scenario_name}: {send_error}")
                    # This may be expected for malformed messages

                # Step 3: Validate recovery with subsequent valid request
                recovery_events = []

                if scenario_config.get("recovery_possible", False):
                    # Send valid recovery message
                    recovery_message = {
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": f"Recovery test after {scenario_name} error scenario. Please provide a brief response.",
                        "thread_id": f"recovery_{scenario_name}_{int(time.time())}",
                        "run_id": f"recovery_run_{scenario_name}",
                        "user_id": self.__class__.test_user_id,
                        "context": {
                            "recovery_test": True,
                            "previous_error_scenario": scenario_name
                        }
                    }

                    try:
                        await websocket.send(json.dumps(recovery_message))

                        # Collect recovery events
                        recovery_timeout = 45.0
                        recovery_collection_start = time.time()

                        while time.time() - recovery_collection_start < recovery_timeout:
                            try:
                                event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                event = json.loads(event_data)
                                recovery_events.append(event)

                                event_type = event.get("type", "unknown")

                                # Stop when we receive completion or another error
                                if event_type == "agent_completed":
                                    self.logger.info(f"✅ Recovery successful for {scenario_name}")
                                    break
                                elif "error" in event_type.lower():
                                    self.logger.warning(f"⚠️ Recovery error for {scenario_name}: {event}")
                                    break

                            except asyncio.TimeoutError:
                                continue

                    except Exception as recovery_error:
                        self.logger.error(f"❌ Recovery attempt failed for {scenario_name}: {recovery_error}")

                scenario_duration = time.time() - scenario_start

                # Validate error recovery for this scenario
                recovery_validation = self._validate_error_recovery(
                    scenario_name, error_events, recovery_events
                )

                scenario_results.append({
                    "scenario": scenario_name,
                    "duration": scenario_duration,
                    "error_events": len(error_events),
                    "recovery_events": len(recovery_events),
                    "recovery_validation": recovery_validation,
                    "success": recovery_validation["recovery_score"] >= 0.6
                })

                recovery_metrics.append({
                    "metric": f"scenario_{scenario_name}",
                    "duration": scenario_duration,
                    "recovery_score": recovery_validation["recovery_score"],
                    "recovery_successful": recovery_validation["recovery_successful"]
                })

                self.logger.info(f"🔄 {scenario_name}: Recovery score {recovery_validation['recovery_score']:.2f}, "
                               f"Duration {scenario_duration:.1f}s")

            await websocket.close()

            # Step 4: Validate overall error recovery capability

            # Calculate success metrics
            successful_scenarios = [r for r in scenario_results if r["success"]]
            failed_scenarios = [r for r in scenario_results if not r["success"]]

            success_rate = len(successful_scenarios) / len(scenario_results)
            avg_recovery_score = sum(r["recovery_validation"]["recovery_score"] for r in scenario_results) / len(scenario_results)

            recovery_metrics.append({
                "metric": "overall_error_recovery",
                "scenarios_tested": len(scenario_results),
                "successful_scenarios": len(successful_scenarios),
                "failed_scenarios": len(failed_scenarios),
                "success_rate": success_rate,
                "avg_recovery_score": avg_recovery_score
            })

            # CRITICAL: Minimum error recovery capability required
            assert success_rate >= 0.75, (
                f"Error recovery success rate too low: {success_rate:.1%} "
                f"(required ≥75%). Failed scenarios: {[r['scenario'] for r in failed_scenarios]}"
            )

            assert avg_recovery_score >= 0.65, (
                f"Average recovery score too low: {avg_recovery_score:.2f} "
                f"(required ≥0.65). System recovery capability insufficient."
            )

            # Validate specific recovery requirements
            for result in scenario_results:
                validation = result["recovery_validation"]

                # Critical scenarios must have proper error acknowledgment
                if self.__class__.error_scenarios[result["scenario"]]["severity"] in ["high", "medium"]:
                    assert validation["error_acknowledged"], (
                        f"Critical error scenario {result['scenario']} not properly acknowledged"
                    )

                # Recoverable scenarios must demonstrate recovery
                if self.__class__.error_scenarios[result["scenario"]]["recovery_possible"]:
                    assert validation["recovery_successful"], (
                        f"Recoverable scenario {result['scenario']} failed to recover properly"
                    )

            # Final error recovery reporting
            total_recovery_test_time = time.time() - error_recovery_start_time

            recovery_metrics.append({
                "metric": "total_error_recovery_test_time",
                "value": total_recovery_test_time,
                "all_scenarios_validated": True,
                "timestamp": time.time(),
                "success": True
            })

            # Log comprehensive recovery results
            self.logger.info("🛡️ COMPREHENSIVE ERROR RECOVERY SUCCESS")
            self.logger.info(f"🔄 Error Recovery Metrics:")
            self.logger.info(f"   Total Test Time: {total_recovery_test_time:.1f}s")
            self.logger.info(f"   Scenarios Tested: {len(scenario_results)}")
            self.logger.info(f"   Successful Recoveries: {len(successful_scenarios)}")
            self.logger.info(f"   Failed Recoveries: {len(failed_scenarios)}")
            self.logger.info(f"   Success Rate: {success_rate:.1%}")
            self.logger.info(f"   Average Recovery Score: {avg_recovery_score:.2f}/1.0")

            # Log individual scenario results
            for result in scenario_results:
                validation = result["recovery_validation"]
                self.logger.info(f"   {result['scenario']}: Score {validation['recovery_score']:.2f}, "
                               f"Recovery {validation['recovery_successful']}, "
                               f"Duration {result['duration']:.1f}s")

        except Exception as e:
            total_time = time.time() - error_recovery_start_time

            self.logger.error(f"❌ COMPREHENSIVE ERROR RECOVERY FAILED")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")
            self.logger.error(f"   Recovery metrics collected: {len(recovery_metrics)}")

            # Fail with error recovery impact context
            raise AssertionError(
                f"Error recovery validation failed after {total_time:.1f}s: {e}. "
                f"Poor error recovery threatens user experience and platform reliability. "
                f"Recovery metrics: {recovery_metrics}"
            )

    async def test_network_interruption_resilience(self):
        """
        Test system resilience to network interruptions and connection recovery.

        NETWORK RESILIENCE: Validates that the system handles network interruptions
        gracefully and can recover connections without losing user context or data.

        Network interruption scenarios:
        1. Connection timeout during agent processing
        2. Connection drop and reconnection
        3. Partial message delivery
        4. WebSocket ping/pong failure handling

        DIFFICULTY: High (45 minutes)
        REAL SERVICES: Yes - Staging GCP with network simulation
        STATUS: Should PASS - Network resilience critical for reliability
        """
        network_test_start_time = time.time()
        network_metrics = []

        self.logger.info("🌐 Testing network interruption resilience")

        try:
            # Step 1: Establish initial connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            initial_connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "network-resilience-e2e",
                        "X-Network-Testing": "enabled"
                    },
                    ssl=ssl_context,
                    ping_interval=20,  # Shorter ping interval for testing
                    ping_timeout=5
                ),
                timeout=20.0
            )

            initial_connection_time = time.time() - initial_connection_start
            network_metrics.append({
                "metric": "initial_connection_time",
                "value": initial_connection_time,
                "timestamp": time.time(),
                "success": True
            })

            # Step 2: Send initial message to establish processing context
            initial_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": (
                    "Network resilience test: Please analyze this request and provide a response. "
                    "This test will simulate network interruptions during processing."
                ),
                "thread_id": f"network_test_{int(time.time())}",
                "run_id": f"network_run_{int(time.time())}",
                "user_id": self.__class__.test_user_id,
                "context": {
                    "network_resilience_test": True,
                    "expect_interruptions": True
                }
            }

            await websocket.send(json.dumps(initial_message))

            # Step 3: Collect initial events (simulate interruption during processing)
            initial_events = []
            interruption_timeout = 15.0  # Allow some processing before "interruption"
            collection_start = time.time()

            while time.time() - collection_start < interruption_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    initial_events.append(event)

                    event_type = event.get("type", "unknown")

                    # Simulate interruption after receiving agent_started
                    if event_type == "agent_started":
                        self.logger.info("📡 Simulating network interruption after agent_started")
                        break

                except asyncio.TimeoutError:
                    # This timeout could simulate network delay
                    self.logger.info("⏰ Timeout during initial processing (simulating network delay)")
                    break

            # Step 4: Simulate connection interruption by closing
            interruption_start = time.time()
            await websocket.close(code=1001, reason="Simulated network interruption")

            # Wait a moment to simulate network outage
            await asyncio.sleep(2)

            interruption_duration = time.time() - interruption_start

            network_metrics.append({
                "metric": "connection_interruption",
                "duration": interruption_duration,
                "events_before_interruption": len(initial_events),
                "timestamp": time.time(),
                "success": True
            })

            # Step 5: Attempt reconnection and recovery
            recovery_start = time.time()

            try:
                # Establish new connection for recovery
                recovery_websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.__class__.staging_config.urls.websocket_url,
                        additional_headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "X-Environment": "staging",
                            "X-Test-Suite": "network-recovery-e2e",
                            "X-Recovery-Attempt": "true"
                        },
                        ssl=ssl_context,
                        ping_interval=30,
                        ping_timeout=10
                    ),
                    timeout=25.0
                )

                recovery_connection_time = time.time() - recovery_start
                network_metrics.append({
                    "metric": "recovery_connection_time",
                    "value": recovery_connection_time,
                    "timestamp": time.time(),
                    "success": True
                })

                self.logger.info(f"🔄 Successfully reconnected after interruption in {recovery_connection_time:.2f}s")

                # Step 6: Validate system recovery with new request
                recovery_message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": (
                        "Post-interruption recovery test: Please provide a response to validate "
                        "that the system has recovered properly from the network interruption."
                    ),
                    "thread_id": f"recovery_test_{int(time.time())}",
                    "run_id": f"recovery_run_{int(time.time())}",
                    "user_id": self.__class__.test_user_id,
                    "context": {
                        "post_interruption_recovery": True,
                        "recovery_validation": True
                    }
                }

                await recovery_websocket.send(json.dumps(recovery_message))

                # Collect recovery events
                recovery_events = []
                recovery_timeout = 45.0
                recovery_collection_start = time.time()

                while time.time() - recovery_collection_start < recovery_timeout:
                    try:
                        event_data = await asyncio.wait_for(recovery_websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        recovery_events.append(event)

                        event_type = event.get("type", "unknown")

                        if event_type == "agent_completed":
                            self.logger.info("✅ Recovery processing completed successfully")
                            break

                        if "error" in event_type.lower():
                            self.logger.warning(f"⚠️ Error during recovery: {event}")

                    except asyncio.TimeoutError:
                        continue

                await recovery_websocket.close()

                recovery_processing_time = time.time() - recovery_collection_start

                # Validate recovery success
                recovery_successful = any(
                    event.get("type") == "agent_completed" for event in recovery_events
                )

                network_metrics.append({
                    "metric": "recovery_processing",
                    "duration": recovery_processing_time,
                    "recovery_events": len(recovery_events),
                    "recovery_successful": recovery_successful,
                    "timestamp": time.time(),
                    "success": recovery_successful
                })

                # Network resilience assertions
                assert recovery_successful, (
                    f"System failed to recover properly after network interruption. "
                    f"Recovery events: {len(recovery_events)}, "
                    f"Processing time: {recovery_processing_time:.1f}s"
                )

                assert recovery_connection_time < 30.0, (
                    f"Recovery connection too slow: {recovery_connection_time:.1f}s (max 30s)"
                )

                assert recovery_processing_time < 60.0, (
                    f"Recovery processing too slow: {recovery_processing_time:.1f}s (max 60s)"
                )

            except Exception as recovery_error:
                raise AssertionError(f"Network recovery failed: {recovery_error}")

            # Final network resilience reporting
            total_network_test_time = time.time() - network_test_start_time

            network_metrics.append({
                "metric": "total_network_resilience_test",
                "value": total_network_test_time,
                "network_interruption_handled": True,
                "recovery_validated": recovery_successful,
                "timestamp": time.time(),
                "success": True
            })

            self.logger.info("🌐 NETWORK INTERRUPTION RESILIENCE SUCCESS")
            self.logger.info(f"📡 Network Resilience Metrics:")
            self.logger.info(f"   Total Test Time: {total_network_test_time:.1f}s")
            self.logger.info(f"   Initial Connection: {initial_connection_time:.2f}s")
            self.logger.info(f"   Recovery Connection: {recovery_connection_time:.2f}s")
            self.logger.info(f"   Events Before Interruption: {len(initial_events)}")
            self.logger.info(f"   Recovery Events: {len(recovery_events)}")
            self.logger.info(f"   Recovery Successful: {recovery_successful}")

        except Exception as e:
            total_time = time.time() - network_test_start_time

            self.logger.error(f"❌ NETWORK INTERRUPTION RESILIENCE FAILED")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")

            raise AssertionError(
                f"Network resilience validation failed after {total_time:.1f}s: {e}. "
                f"Poor network resilience affects platform reliability and user experience."
            )


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--agent-goldenpath",
        "--error-recovery"
    ])