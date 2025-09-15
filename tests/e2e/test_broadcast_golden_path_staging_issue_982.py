"""
E2E Staging Test Suite: Golden Path Agent Event Delivery via Broadcast Functions (Issue #982)

This E2E staging test suite validates the complete Golden Path user flow
with real agent event delivery through broadcast function implementations.

Business Value Justification:
- Segment: Platform/Golden Path
- Business Goal: $500K+ ARR Protection through Golden Path reliability
- Value Impact: Ensure end-to-end agent event delivery works in staging
- Strategic Impact: Validate complete user journey with real WebSocket events

Test Strategy: Real staging environment with actual agent workflows
Expected Behavior: Tests should FAIL initially, then PASS after SSOT remediation

Prerequisites:
- GCP Staging environment deployed and accessible
- Real WebSocket connections and agent workflows
- Actual agent event broadcasting functionality

GitHub Issue: https://github.com/netra-systems/netra-apex/issues/982
"""

import pytest
import asyncio
import json
import time
import uuid
import websockets
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlencode
import sys
import os
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Configure logging for E2E tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentEventCapture:
    """Captures agent events during Golden Path execution."""
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    user_id: str
    session_id: str


@dataclass
class GoldenPathTestResult:
    """Results from Golden Path test execution."""
    user_id: str
    session_id: str
    total_events: int
    events_captured: List[AgentEventCapture]
    execution_time: float
    success: bool
    error_messages: List[str]


class StagingWebSocketClient:
    """WebSocket client for staging environment testing."""

    def __init__(self, staging_url: str, auth_token: Optional[str] = None):
        self.staging_url = staging_url
        self.auth_token = auth_token
        self.websocket = None
        self.captured_events: List[AgentEventCapture] = []
        self.connection_active = False
        self.user_id = None
        self.session_id = None

    async def connect(self, user_id: str) -> bool:
        """Connect to staging WebSocket endpoint."""
        try:
            self.user_id = user_id
            self.session_id = str(uuid.uuid4())

            # Build WebSocket URL with authentication
            ws_url = f"{self.staging_url}/ws"
            if self.auth_token:
                ws_url += f"?token={self.auth_token}"

            # Add user context
            ws_url += f"&user_id={user_id}&session_id={self.session_id}"

            logger.info(f"Connecting to staging WebSocket: {ws_url}")

            self.websocket = await websockets.connect(
                ws_url,
                timeout=30,
                ping_interval=20,
                ping_timeout=10
            )

            self.connection_active = True
            logger.info(f"Connected to staging WebSocket for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to staging WebSocket: {e}")
            return False

    async def listen_for_events(self, timeout: float = 60.0) -> List[AgentEventCapture]:
        """Listen for agent events with timeout."""
        if not self.connection_active or not self.websocket:
            return []

        start_time = time.time()
        self.captured_events.clear()

        try:
            while time.time() - start_time < timeout:
                try:
                    # Wait for message with shorter timeout for responsiveness
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=5.0
                    )

                    # Parse and capture event
                    event_data = json.loads(message)
                    event_capture = AgentEventCapture(
                        event_type=event_data.get("type", "unknown"),
                        timestamp=time.time(),
                        data=event_data,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )

                    self.captured_events.append(event_capture)
                    logger.info(f"Captured event: {event_capture.event_type}")

                    # Check for completion events
                    if event_capture.event_type in ["agent_completed", "error", "timeout"]:
                        logger.info(f"Received completion event: {event_capture.event_type}")
                        break

                except asyncio.TimeoutError:
                    # Continue listening, this is normal
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed during event listening")
                    break

        except Exception as e:
            logger.error(f"Error listening for events: {e}")

        return self.captured_events

    async def send_agent_request(self, request_data: Dict[str, Any]) -> bool:
        """Send agent execution request to staging."""
        if not self.connection_active or not self.websocket:
            return False

        try:
            request_message = {
                "type": "agent_request",
                "user_id": self.user_id,
                "session_id": self.session_id,
                "data": request_data
            }

            await self.websocket.send(json.dumps(request_message))
            logger.info(f"Sent agent request for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send agent request: {e}")
            return False

    async def disconnect(self):
        """Disconnect from staging WebSocket."""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info(f"Disconnected from staging WebSocket")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

        self.connection_active = False
        self.websocket = None


@pytest.mark.e2e
class TestGoldenPathBroadcastStaging(SSotAsyncTestCase):
    """E2E staging tests for Golden Path agent event delivery."""

    def setUp(self):
        """Set up staging test environment."""
        super().setUp()

        # Staging environment configuration
        self.staging_base_url = os.getenv("STAGING_BASE_URL", "wss://netra-staging.example.com")
        self.staging_auth_token = os.getenv("STAGING_AUTH_TOKEN")

        # Test configuration
        self.test_timeout = 120.0  # 2 minutes for full Golden Path
        self.expected_agent_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

    async def test_golden_path_agent_event_delivery_consistency(self):
        """
        Test Golden Path agent event delivery consistency across broadcast implementations.

        Expected Behavior: FAIL - Inconsistent event delivery or missing events
        After SSOT remediation: PASS - Consistent complete event delivery
        """
        if not self.staging_auth_token:
            self.skipTest("STAGING_AUTH_TOKEN not available for E2E testing")

        logger.info("=== GOLDEN PATH AGENT EVENT DELIVERY CONSISTENCY TEST ===")

        # Test scenarios for different users
        test_users = [
            {"user_id": "golden_path_test_user_1", "request": "Analyze the current market trends"},
            {"user_id": "golden_path_test_user_2", "request": "Help me optimize my AI workflow"},
            {"user_id": "golden_path_test_user_3", "request": "Provide investment recommendations"}
        ]

        test_results: List[GoldenPathTestResult] = []

        for user_scenario in test_users:
            logger.info(f"Testing Golden Path for user: {user_scenario['user_id']}")

            # Create staging WebSocket client
            client = StagingWebSocketClient(
                staging_url=self.staging_base_url,
                auth_token=self.staging_auth_token
            )

            try:
                # Connect to staging
                connection_success = await client.connect(user_scenario["user_id"])
                self.assertTrue(connection_success, f"Failed to connect to staging for {user_scenario['user_id']}")

                # Send agent request
                start_time = time.time()
                request_data = {
                    "prompt": user_scenario["request"],
                    "agent_type": "supervisor",
                    "priority": "high"
                }

                request_success = await client.send_agent_request(request_data)
                self.assertTrue(request_success, f"Failed to send agent request for {user_scenario['user_id']}")

                # Listen for agent events
                captured_events = await client.listen_for_events(timeout=self.test_timeout)
                execution_time = time.time() - start_time

                # Analyze results
                result = GoldenPathTestResult(
                    user_id=user_scenario["user_id"],
                    session_id=client.session_id,
                    total_events=len(captured_events),
                    events_captured=captured_events,
                    execution_time=execution_time,
                    success=len(captured_events) >= len(self.expected_agent_events),
                    error_messages=[]
                )

                # Check for required events
                captured_event_types = [event.event_type for event in captured_events]
                missing_events = [event_type for event_type in self.expected_agent_events
                                if event_type not in captured_event_types]

                if missing_events:
                    result.error_messages.append(f"Missing required events: {missing_events}")
                    result.success = False

                test_results.append(result)

                logger.info(f"User {user_scenario['user_id']} results:")
                logger.info(f"  - Events captured: {len(captured_events)}")
                logger.info(f"  - Execution time: {execution_time:.2f}s")
                logger.info(f"  - Success: {result.success}")
                if result.error_messages:
                    logger.info(f"  - Errors: {result.error_messages}")

            finally:
                await client.disconnect()

            # Brief pause between users to avoid overwhelming staging
            await asyncio.sleep(2)

        # Analyze consistency across users
        logger.info("=== CONSISTENCY ANALYSIS ===")

        consistency_issues = []
        successful_tests = [result for result in test_results if result.success]
        failed_tests = [result for result in test_results if not result.success]

        logger.info(f"Successful tests: {len(successful_tests)}")
        logger.info(f"Failed tests: {len(failed_tests)}")

        # Check for consistency in successful tests
        if len(successful_tests) >= 2:
            event_counts = [len(result.events_captured) for result in successful_tests]
            if len(set(event_counts)) > 1:
                consistency_issues.append(f"Inconsistent event counts across users: {event_counts}")

            # Check event type consistency
            event_type_sets = [set(event.event_type for event in result.events_captured)
                              for result in successful_tests]

            if len(event_type_sets) >= 2:
                base_set = event_type_sets[0]
                for i, event_set in enumerate(event_type_sets[1:], 1):
                    if event_set != base_set:
                        consistency_issues.append(f"Inconsistent event types between user 0 and user {i}")

        # Check for timing consistency
        if successful_tests:
            execution_times = [result.execution_time for result in successful_tests]
            avg_time = sum(execution_times) / len(execution_times)
            outliers = [time for time in execution_times if abs(time - avg_time) > avg_time * 0.5]

            if outliers:
                consistency_issues.append(f"Execution time outliers detected: {outliers} (avg: {avg_time:.2f})")

        logger.info(f"Consistency issues: {len(consistency_issues)}")
        for issue in consistency_issues:
            logger.info(f"  - {issue}")

        # ASSERTION: Should detect consistency issues initially
        # This test SHOULD FAIL until SSOT remediation is complete

        total_failures = len(failed_tests) + len(consistency_issues)

        if total_failures > 0:
            error_details = []

            # Add failed test details
            for failed_result in failed_tests:
                error_details.append(f"User {failed_result.user_id}: {failed_result.error_messages}")

            # Add consistency issues
            error_details.extend(consistency_issues)

            self.fail(f"GOLDEN PATH BROADCAST VIOLATION: {total_failures} issues detected in staging. "
                     f"Failed tests: {len(failed_tests)}, Consistency issues: {len(consistency_issues)}. "
                     f"Details: {error_details}. "
                     f"Golden Path agent event delivery is inconsistent, blocking $500K+ ARR user experience. "
                     f"SSOT remediation required for reliable broadcast functionality.")
        else:
            logger.info("✓ Golden Path agent event delivery consistency validated")

    async def test_concurrent_user_broadcast_isolation_staging(self):
        """
        Test broadcast event isolation between concurrent users in staging.

        Expected Behavior: FAIL - Cross-user event leakage or isolation failures
        After SSOT remediation: PASS - Perfect user isolation
        """
        if not self.staging_auth_token:
            self.skipTest("STAGING_AUTH_TOKEN not available for E2E testing")

        logger.info("=== CONCURRENT USER BROADCAST ISOLATION TEST ===")

        # Define concurrent user scenarios with distinct, identifiable data
        concurrent_users = [
            {
                "user_id": "isolation_test_alice_999",
                "request": "ALICE_UNIQUE: Analyze cryptocurrency market trends for Alice",
                "identifier": "ALICE_UNIQUE"
            },
            {
                "user_id": "isolation_test_bob_888",
                "request": "BOB_UNIQUE: Create investment portfolio for Bob",
                "identifier": "BOB_UNIQUE"
            },
            {
                "user_id": "isolation_test_charlie_777",
                "request": "CHARLIE_UNIQUE: Generate trading strategy for Charlie",
                "identifier": "CHARLIE_UNIQUE"
            }
        ]

        # Create clients for each user
        clients = []
        for user_data in concurrent_users:
            client = StagingWebSocketClient(
                staging_url=self.staging_base_url,
                auth_token=self.staging_auth_token
            )
            clients.append((client, user_data))

        try:
            # Connect all clients concurrently
            connection_tasks = []
            for client, user_data in clients:
                task = client.connect(user_data["user_id"])
                connection_tasks.append(task)

            connection_results = await asyncio.gather(*connection_tasks)

            # Verify all connections successful
            for i, success in enumerate(connection_results):
                self.assertTrue(success, f"Failed to connect user {concurrent_users[i]['user_id']}")

            logger.info(f"All {len(clients)} users connected concurrently")

            # Send concurrent agent requests
            request_tasks = []
            for client, user_data in clients:
                request_data = {
                    "prompt": user_data["request"],
                    "agent_type": "supervisor",
                    "priority": "high",
                    "user_identifier": user_data["identifier"]
                }
                task = client.send_agent_request(request_data)
                request_tasks.append(task)

            request_results = await asyncio.gather(*request_tasks)

            # Verify all requests sent
            for i, success in enumerate(request_results):
                self.assertTrue(success, f"Failed to send request for user {concurrent_users[i]['user_id']}")

            logger.info("All concurrent agent requests sent")

            # Listen for events concurrently
            listen_tasks = []
            for client, user_data in clients:
                task = client.listen_for_events(timeout=self.test_timeout)
                listen_tasks.append(task)

            all_captured_events = await asyncio.gather(*listen_tasks)

            # Analyze isolation
            logger.info("=== ISOLATION ANALYSIS ===")

            isolation_violations = []

            for i, ((client, user_data), captured_events) in enumerate(zip(clients, all_captured_events)):
                user_id = user_data["user_id"]
                user_identifier = user_data["identifier"]

                logger.info(f"User {user_id} received {len(captured_events)} events")

                # Check for cross-user contamination
                for event in captured_events:
                    event_str = json.dumps(event.data).upper()

                    # Check if this user received events meant for other users
                    for other_user in concurrent_users:
                        if other_user["user_id"] != user_id:
                            other_identifier = other_user["identifier"]

                            if other_identifier in event_str:
                                violation = f"User {user_id} received event containing {other_identifier}"
                                isolation_violations.append(violation)
                                logger.warning(violation)

                # Check if user received their own events
                own_events = [event for event in captured_events
                             if user_identifier in json.dumps(event.data).upper()]

                if not own_events and captured_events:
                    isolation_violations.append(f"User {user_id} did not receive their own events")

                logger.info(f"User {user_id} own events: {len(own_events)}")

            logger.info(f"Isolation violations detected: {len(isolation_violations)}")
            for violation in isolation_violations:
                logger.info(f"  - {violation}")

            # ASSERTION: Should detect isolation violations initially
            if isolation_violations:
                self.fail(f"CONCURRENT USER ISOLATION VIOLATION: {len(isolation_violations)} isolation "
                         f"failures detected in staging environment. Violations: {isolation_violations}. "
                         f"Cross-user event leakage violates security requirements and blocks enterprise deployment. "
                         f"SSOT remediation required for secure user isolation.")
            else:
                logger.info("✓ Concurrent user broadcast isolation validated")

        finally:
            # Cleanup: disconnect all clients
            for client, _ in clients:
                await client.disconnect()

    async def test_broadcast_performance_under_load_staging(self):
        """
        Test broadcast function performance under load in staging.

        Expected Behavior: FAIL - Performance degradation or failures under load
        After SSOT remediation: PASS - Consistent performance
        """
        if not self.staging_auth_token:
            self.skipTest("STAGING_AUTH_TOKEN not available for E2E testing")

        logger.info("=== BROADCAST PERFORMANCE UNDER LOAD TEST ===")

        # Load test configuration
        load_users = [f"load_test_user_{i}" for i in range(5)]  # 5 concurrent users
        load_requests_per_user = 3  # 3 requests each = 15 total concurrent requests

        performance_results = []
        clients = []

        try:
            # Create clients for all users
            for user_id in load_users:
                client = StagingWebSocketClient(
                    staging_url=self.staging_base_url,
                    auth_token=self.staging_auth_token
                )
                clients.append((client, user_id))

            # Connect all clients
            connection_tasks = []
            for client, user_id in clients:
                task = client.connect(user_id)
                connection_tasks.append(task)

            connection_results = await asyncio.gather(*connection_tasks)

            # Verify connections
            for i, success in enumerate(connection_results):
                self.assertTrue(success, f"Failed to connect load test user {load_users[i]}")

            logger.info(f"Connected {len(clients)} users for load testing")

            # Execute load test - multiple requests per user concurrently
            all_tasks = []
            task_metadata = []

            for client, user_id in clients:
                for request_num in range(load_requests_per_user):
                    # Create unique request for tracking
                    request_data = {
                        "prompt": f"Load test request {request_num} for {user_id}",
                        "agent_type": "supervisor",
                        "priority": "normal",
                        "load_test_id": f"{user_id}_req_{request_num}"
                    }

                    # Create task for this request
                    async def execute_request(client_ref, user_id_ref, request_data_ref):
                        start_time = time.time()

                        # Send request
                        success = await client_ref.send_agent_request(request_data_ref)
                        if not success:
                            return {
                                "user_id": user_id_ref,
                                "success": False,
                                "error": "Failed to send request",
                                "duration": 0,
                                "events": []
                            }

                        # Listen for response
                        events = await client_ref.listen_for_events(timeout=60.0)
                        duration = time.time() - start_time

                        return {
                            "user_id": user_id_ref,
                            "success": len(events) > 0,
                            "duration": duration,
                            "events": events,
                            "load_test_id": request_data_ref["load_test_id"]
                        }

                    task = execute_request(client, user_id, request_data)
                    all_tasks.append(task)
                    task_metadata.append({
                        "user_id": user_id,
                        "request_num": request_num,
                        "load_test_id": f"{user_id}_req_{request_num}"
                    })

            logger.info(f"Executing {len(all_tasks)} concurrent requests...")

            # Execute all requests concurrently
            load_start_time = time.time()
            results = await asyncio.gather(*all_tasks)
            total_load_time = time.time() - load_start_time

            logger.info(f"Load test completed in {total_load_time:.2f}s")

            # Analyze performance results
            successful_results = [r for r in results if r["success"]]
            failed_results = [r for r in results if not r["success"]]

            logger.info(f"Successful requests: {len(successful_results)}")
            logger.info(f"Failed requests: {len(failed_results)}")

            if successful_results:
                durations = [r["duration"] for r in successful_results]
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)

                logger.info(f"Average duration: {avg_duration:.2f}s")
                logger.info(f"Max duration: {max_duration:.2f}s")
                logger.info(f"Min duration: {min_duration:.2f}s")

                # Performance thresholds
                performance_issues = []

                if avg_duration > 45.0:  # 45 second average threshold
                    performance_issues.append(f"Average response time too high: {avg_duration:.2f}s")

                if max_duration > 90.0:  # 90 second max threshold
                    performance_issues.append(f"Maximum response time too high: {max_duration:.2f}s")

                if len(failed_results) > 0:
                    performance_issues.append(f"{len(failed_results)} requests failed under load")

                # Check for excessive variation (indicates inconsistent performance)
                duration_variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
                if duration_variance > 100:  # High variance threshold
                    performance_issues.append(f"High performance variance: {duration_variance:.2f}")

                logger.info(f"Performance issues: {len(performance_issues)}")
                for issue in performance_issues:
                    logger.info(f"  - {issue}")

                # ASSERTION: Should detect performance issues initially
                if performance_issues:
                    self.fail(f"BROADCAST PERFORMANCE VIOLATION: {len(performance_issues)} performance "
                             f"issues detected under load. Issues: {performance_issues}. "
                             f"Performance degradation affects user experience and system scalability. "
                             f"SSOT remediation required for consistent broadcast performance.")
                else:
                    logger.info("✓ Broadcast performance under load validated")

            else:
                self.fail("BROADCAST LOAD TEST FAILURE: No successful requests completed. "
                         "Complete system failure under concurrent load indicates serious issues.")

        finally:
            # Cleanup
            for client, _ in clients:
                await client.disconnect()


if __name__ == "__main__":
    import unittest
    unittest.main()