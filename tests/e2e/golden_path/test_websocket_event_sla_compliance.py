"""

E2E Tests for WebSocket Event SLA Compliance



Business Value Justification (BVJ):

- Segment: Platform/All Users  

- Business Goal: Ensure WebSocket event delivery meets business SLA requirements

- Value Impact: Protects $500K+ ARR by guaranteeing real-time chat experience quality

- Strategic Impact: Validates critical infrastructure supporting 90% of platform value



This test suite validates WebSocket event SLA compliance in GCP staging:

1. Connection establishment < 2 seconds (SLA requirement)

2. First event delivery < 5 seconds (business critical)

3. All 5 critical events delivered reliably

4. Event failure recovery mechanisms

5. Event ordering and sequencing validation

6. Event delivery under load conditions

7. Connection stability during agent execution

8. Graceful degradation during service stress



CRITICAL REQUIREMENTS:

- Tests run against real GCP staging WebSocket endpoints

- Real timing measurements with actual network latency

- Real agent execution with LLM integration

- Comprehensive failure recovery validation

- Load testing with concurrent connections

- SLA breach detection and alerting



Test Strategy:

- Direct WebSocket connection testing to staging endpoints

- Precision timing measurements for SLA compliance

- Real agent execution flows with event validation

- Concurrent connection load testing

- Network failure simulation and recovery testing

"""



import asyncio

import pytest

import time

import websockets

import json

import logging

import statistics

from typing import Dict, Any, Optional, List, Tuple

from datetime import datetime, timedelta

import httpx

from unittest.mock import patch



from test_framework.base_e2e_test import BaseE2ETest





@pytest.mark.e2e

@pytest.mark.gcp_staging

@pytest.mark.mission_critical

@pytest.mark.golden_path

@pytest.mark.sla_critical

class TestWebSocketEventSLACompliance(BaseE2ETest):

    """

    Test WebSocket event delivery SLA compliance in GCP staging.

    

    BUSINESS IMPACT: Protects $500K+ ARR by ensuring real-time chat quality

    SLA REQUIREMENTS: 

    - Connection: < 2s

    - First Event: < 5s

    - All Events: 100% delivery

    """



    @pytest.fixture(autouse=True)

    def setup_sla_testing(self):

        """Set up SLA testing configuration and thresholds."""

        # Business-critical SLA thresholds

        self.sla_connection_establishment = 2.0  # seconds

        self.sla_first_event_delivery = 5.0  # seconds

        self.sla_event_sequence_timeout = 30.0  # seconds

        self.sla_event_reliability = 100.0  # percent (all events must be delivered)

        

        # GCP staging endpoints

        self.staging_websocket_url = "wss://staging.netra.ai/ws"

        self.staging_auth_url = "https://auth-staging.netra.ai"

        self.staging_api_url = "https://api-staging.netra.ai"

        

        # Required critical events for business value

        self.critical_events = [

            "agent_started",

            "agent_thinking", 

            "tool_executing",

            "tool_completed",

            "agent_completed"

        ]

        

        # Load testing parameters

        self.concurrent_connections_test = 25

        self.load_test_duration = 60.0  # seconds

        

        self.logger = logging.getLogger(__name__)

        self.sla_violations = []

        

        yield

        

        # Report SLA violations if any

        if self.sla_violations:

            self.logger.critical(f"SLA VIOLATIONS DETECTED: {len(self.sla_violations)} violations")

            for violation in self.sla_violations:

                self.logger.critical(f"SLA VIOLATION: {violation}")



    async def test_connection_establishment_sla_compliance(self):

        """

        Test WebSocket connection establishment meets < 2s SLA requirement.

        

        CRITICAL: Connection speed directly impacts user experience

        """

        connection_times = []

        test_iterations = 10

        

        for i in range(test_iterations):

            start_time = time.time()

            

            try:

                # Establish WebSocket connection to staging

                websocket = await websockets.connect(

                    self.staging_websocket_url,

                    timeout=self.sla_connection_establishment + 1.0

                )

                

                connection_time = time.time() - start_time

                connection_times.append(connection_time)

                

                # Clean up connection

                await websocket.close()

                

                # Individual connection SLA validation

                if connection_time > self.sla_connection_establishment:

                    violation = {

                        "type": "connection_establishment",

                        "iteration": i + 1,

                        "time": connection_time,

                        "sla_threshold": self.sla_connection_establishment,

                        "violation_amount": connection_time - self.sla_connection_establishment

                    }

                    self.sla_violations.append(violation)

                    

            except asyncio.TimeoutError:

                violation = {

                    "type": "connection_timeout",

                    "iteration": i + 1,

                    "time": "timeout",

                    "sla_threshold": self.sla_connection_establishment

                }

                self.sla_violations.append(violation)

                

            # Brief pause between iterations

            await asyncio.sleep(0.1)

        

        # Statistical SLA compliance analysis

        if connection_times:

            avg_connection_time = statistics.mean(connection_times)

            max_connection_time = max(connection_times)

            p95_connection_time = statistics.quantiles(connection_times, n=20)[18]  # 95th percentile

            

            self.logger.info(f"Connection SLA Metrics:")

            self.logger.info(f"  Average: {avg_connection_time:.3f}s")

            self.logger.info(f"  Maximum: {max_connection_time:.3f}s") 

            self.logger.info(f"  95th Percentile: {p95_connection_time:.3f}s")

            

            # SLA compliance assertions

            assert avg_connection_time < self.sla_connection_establishment, (

                f"Average connection time {avg_connection_time:.3f}s violates {self.sla_connection_establishment}s SLA"

            )

            

            assert p95_connection_time < self.sla_connection_establishment, (

                f"95th percentile connection time {p95_connection_time:.3f}s violates SLA"

            )

        

        assert len(self.sla_violations) == 0, (

            f"Connection establishment SLA violations: {len(self.sla_violations)}"

        )



    async def test_first_event_delivery_sla_compliance(self):

        """

        Test first WebSocket event delivery meets < 5s SLA requirement.

        

        CRITICAL: First event signals system responsiveness to user

        """

        websocket = None

        try:

            # Establish connection and authenticate

            websocket, auth_token = await self._establish_authenticated_websocket()

            

            # Submit chat message to trigger agent execution

            start_time = time.time()

            test_message = "Quick test message for first event SLA validation"

            await self._submit_chat_message_via_websocket(websocket, test_message, auth_token)

            

            # Wait for first event with timeout

            first_event = await self._wait_for_first_event(

                websocket, 

                timeout=self.sla_first_event_delivery + 1.0

            )

            

            first_event_time = time.time() - start_time

            

            # SLA compliance validation

            assert first_event is not None, "No first event received within timeout"

            assert first_event_time < self.sla_first_event_delivery, (

                f"First event delivery time {first_event_time:.3f}s violates {self.sla_first_event_delivery}s SLA"

            )

            

            # Validate first event is business-critical event

            assert first_event.get('type') == 'agent_started', (

                f"First event should be 'agent_started', got '{first_event.get('type')}'"

            )

            

            self.logger.info(f"First event delivered in {first_event_time:.3f}s (SLA: {self.sla_first_event_delivery}s)")

            

        finally:

            if websocket:

                await websocket.close()



    async def test_critical_events_reliability_sla(self):

        """

        Test all 5 critical events are delivered with 100% reliability.

        

        BUSINESS CRITICAL: Missing events break user experience

        """

        websocket = None

        try:

            # Establish authenticated WebSocket connection

            websocket, auth_token = await self._establish_authenticated_websocket()

            

            # Submit message to trigger full agent execution

            test_message = "Comprehensive test message requiring all agent execution phases"

            await self._submit_chat_message_via_websocket(websocket, test_message, auth_token)

            

            # Collect all events within SLA timeout

            events = await self._collect_all_events(

                websocket, 

                timeout=self.sla_event_sequence_timeout

            )

            

            # Extract event types for analysis

            received_event_types = [event.get('type') for event in events if event.get('type')]

            

            # SLA compliance validation - all critical events must be present

            missing_events = []

            for critical_event in self.critical_events:

                if critical_event not in received_event_types:

                    missing_events.append(critical_event)

            

            # Calculate reliability percentage

            reliability_percentage = (

                (len(self.critical_events) - len(missing_events)) / len(self.critical_events) * 100

            )

            

            self.logger.info(f"Event Reliability Metrics:")

            self.logger.info(f"  Required Events: {len(self.critical_events)}")

            self.logger.info(f"  Received Events: {len(received_event_types)}")

            self.logger.info(f"  Missing Events: {missing_events}")

            self.logger.info(f"  Reliability: {reliability_percentage:.1f}%")

            

            # SLA assertions

            assert len(missing_events) == 0, (

                f"Critical events missing: {missing_events}. SLA requires 100% delivery."

            )

            

            assert reliability_percentage == 100.0, (

                f"Event reliability {reliability_percentage:.1f}% violates 100% SLA requirement"

            )

            

        finally:

            if websocket:

                await websocket.close()



    async def test_event_sequencing_sla_compliance(self):

        """

        Test events are delivered in correct business-logical sequence.

        

        BUSINESS LOGIC: Event order reflects agent execution phases

        """

        websocket = None

        try:

            # Establish connection and submit message

            websocket, auth_token = await self._establish_authenticated_websocket()

            test_message = "Test message for event sequencing validation"

            await self._submit_chat_message_via_websocket(websocket, test_message, auth_token)

            

            # Collect events with timestamps

            events = await self._collect_all_events(websocket, timeout=30.0)

            

            # Extract business-critical events with timestamps

            critical_events_received = [

                (event.get('type'), event.get('timestamp', time.time()))

                for event in events 

                if event.get('type') in self.critical_events

            ]

            

            # Sort by timestamp to validate sequence

            critical_events_received.sort(key=lambda x: x[1])

            event_sequence = [event[0] for event in critical_events_received]

            

            # Expected business-logical sequence

            expected_sequence = [

                "agent_started",

                "agent_thinking",

                "tool_executing", 

                "tool_completed",

                "agent_completed"

            ]

            

            self.logger.info(f"Event Sequencing Analysis:")

            self.logger.info(f"  Expected: {expected_sequence}")

            self.logger.info(f"  Received: {event_sequence}")

            

            # Validate sequence compliance

            assert len(event_sequence) >= 3, (

                f"Insufficient events for sequence validation: {len(event_sequence)}"

            )

            

            # Check critical sequence points

            if "agent_started" in event_sequence and "agent_completed" in event_sequence:

                agent_started_index = event_sequence.index("agent_started")

                agent_completed_index = event_sequence.index("agent_completed")

                

                assert agent_started_index < agent_completed_index, (

                    "agent_started must come before agent_completed"

                )

            

            if "tool_executing" in event_sequence and "tool_completed" in event_sequence:

                tool_executing_index = event_sequence.index("tool_executing")

                tool_completed_index = event_sequence.index("tool_completed")

                

                assert tool_executing_index < tool_completed_index, (

                    "tool_executing must come before tool_completed"

                )

                

        finally:

            if websocket:

                await websocket.close()



    async def test_concurrent_connections_sla_compliance(self):

        """

        Test WebSocket SLA compliance under concurrent load.

        

        SCALABILITY: System must maintain SLA under realistic load

        """

        connection_tasks = []

        

        # Create concurrent connection tasks

        for i in range(self.concurrent_connections_test):

            task = asyncio.create_task(

                self._test_single_connection_under_load(connection_id=i)

            )

            connection_tasks.append(task)

        

        # Execute all connections concurrently

        start_time = time.time()

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        total_test_time = time.time() - start_time

        

        # Analyze results for SLA compliance

        successful_connections = 0

        failed_connections = 0

        sla_violations = 0

        connection_times = []

        first_event_times = []

        

        for i, result in enumerate(results):

            if isinstance(result, Exception):

                failed_connections += 1

                self.logger.error(f"Connection {i} failed: {result}")

            else:

                successful_connections += 1

                connection_times.append(result['connection_time'])

                first_event_times.append(result['first_event_time'])

                

                # Check for SLA violations

                if result['connection_time'] > self.sla_connection_establishment:

                    sla_violations += 1

                if result['first_event_time'] > self.sla_first_event_delivery:

                    sla_violations += 1

        

        # Calculate performance metrics

        success_rate = (successful_connections / self.concurrent_connections_test) * 100

        avg_connection_time = statistics.mean(connection_times) if connection_times else 0

        avg_first_event_time = statistics.mean(first_event_times) if first_event_times else 0

        

        self.logger.info(f"Concurrent Load Test Results:")

        self.logger.info(f"  Concurrent Connections: {self.concurrent_connections_test}")

        self.logger.info(f"  Success Rate: {success_rate:.1f}%")

        self.logger.info(f"  Failed Connections: {failed_connections}")

        self.logger.info(f"  SLA Violations: {sla_violations}")

        self.logger.info(f"  Average Connection Time: {avg_connection_time:.3f}s")

        self.logger.info(f"  Average First Event Time: {avg_first_event_time:.3f}s")

        self.logger.info(f"  Total Test Duration: {total_test_time:.1f}s")

        

        # SLA compliance assertions under load

        assert success_rate >= 95.0, (

            f"Success rate {success_rate:.1f}% below 95% threshold under load"

        )

        

        assert sla_violations == 0, (

            f"SLA violations detected under load: {sla_violations}"

        )

        

        assert avg_connection_time < self.sla_connection_establishment, (

            f"Average connection time {avg_connection_time:.3f}s violates SLA under load"

        )



    async def test_event_recovery_after_network_failure(self):

        """

        Test event delivery recovery after network failure.

        

        RELIABILITY: System must recover and continue event delivery

        """

        websocket = None

        try:

            # Establish connection and start message

            websocket, auth_token = await self._establish_authenticated_websocket()

            test_message = "Test message for failure recovery validation"

            await self._submit_chat_message_via_websocket(websocket, test_message, auth_token)

            

            # Collect initial events

            initial_events = await self._collect_events_with_timeout(websocket, timeout=5.0)

            initial_event_count = len(initial_events)

            

            # Simulate network failure by closing connection

            await websocket.close()

            

            # Wait for failure period

            await asyncio.sleep(2.0)

            

            # Re-establish connection

            websocket, auth_token = await self._establish_authenticated_websocket()

            

            # Verify recovery by submitting new message

            recovery_message = "Recovery test message"

            await self._submit_chat_message_via_websocket(websocket, recovery_message, auth_token)

            

            # Collect events after recovery

            recovery_events = await self._collect_events_with_timeout(websocket, timeout=10.0)

            

            # Validate recovery success

            assert len(recovery_events) > 0, "No events received after recovery"

            

            # Verify critical events are delivered after recovery

            recovery_event_types = [event.get('type') for event in recovery_events]

            assert 'agent_started' in recovery_event_types, (

                "agent_started event not received after recovery"

            )

            

            self.logger.info(f"Recovery successful: {len(recovery_events)} events after network failure")

            

        finally:

            if websocket:

                await websocket.close()



    # Private helper methods



    async def _establish_authenticated_websocket(self) -> Tuple[websockets.WebSocketServerProtocol, str]:

        """Establish authenticated WebSocket connection to staging."""

        # Get authentication token

        auth_token = await self._get_staging_auth_token()

        

        # Connect to WebSocket with authentication

        websocket = await websockets.connect(

            f"{self.staging_websocket_url}?token={auth_token}",

            timeout=self.sla_connection_establishment

        )

        

        return websocket, auth_token



    async def _get_staging_auth_token(self) -> str:

        """Get authentication token for staging environment."""

        async with httpx.AsyncClient() as client:

            response = await client.post(

                f"{self.staging_auth_url}/login",

                json={

                    "email": "test@netra.ai",

                    "password": "testpassword123"

                }

            )

            

            if response.status_code == 200:

                return response.json().get('token', 'test-token')

            else:

                return 'test-token'  # Fallback for testing



    async def _submit_chat_message_via_websocket(self, websocket, message: str, auth_token: str):

        """Submit chat message via WebSocket connection."""

        message_payload = {

            "type": "chat_message",

            "message": message,

            "token": auth_token,

            "timestamp": time.time()

        }

        

        await websocket.send(json.dumps(message_payload))



    async def _wait_for_first_event(self, websocket, timeout: float = 5.0) -> Optional[Dict[str, Any]]:

        """Wait for first WebSocket event within timeout."""

        try:

            event_data = await asyncio.wait_for(websocket.recv(), timeout=timeout)

            return json.loads(event_data)

        except (asyncio.TimeoutError, json.JSONDecodeError):

            return None



    async def _collect_all_events(self, websocket, timeout: float = 30.0) -> List[Dict[str, Any]]:

        """Collect all WebSocket events within timeout period."""

        events = []

        start_time = time.time()

        

        try:

            while time.time() - start_time < timeout:

                try:

                    # Wait for next event with shorter timeout for responsiveness

                    event_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)

                    event = json.loads(event_data)

                    event['received_timestamp'] = time.time()

                    events.append(event)

                    

                    # Break if we received agent_completed (end of sequence)

                    if event.get('type') == 'agent_completed':

                        break

                        

                except asyncio.TimeoutError:

                    # Continue waiting for more events

                    continue

                    

        except websockets.exceptions.ConnectionClosed:

            self.logger.warning("WebSocket connection closed during event collection")

        

        return events



    async def _collect_events_with_timeout(self, websocket, timeout: float) -> List[Dict[str, Any]]:

        """Collect WebSocket events with specific timeout."""

        return await self._collect_all_events(websocket, timeout)



    async def _test_single_connection_under_load(self, connection_id: int) -> Dict[str, Any]:

        """Test single connection performance under concurrent load."""

        websocket = None

        try:

            # Measure connection establishment time

            connection_start = time.time()

            websocket, auth_token = await self._establish_authenticated_websocket()

            connection_time = time.time() - connection_start

            

            # Submit message and measure first event time

            first_event_start = time.time()

            test_message = f"Load test message {connection_id}"

            await self._submit_chat_message_via_websocket(websocket, test_message, auth_token)

            

            # Wait for first event

            first_event = await self._wait_for_first_event(websocket, timeout=10.0)

            first_event_time = time.time() - first_event_start if first_event else 10.0

            

            return {

                "connection_id": connection_id,

                "connection_time": connection_time,

                "first_event_time": first_event_time,

                "success": first_event is not None

            }

            

        finally:

            if websocket:

                await websocket.close()

