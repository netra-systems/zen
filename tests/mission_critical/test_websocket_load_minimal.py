#!/usr/bin/env python
'''REAL WEBSOCKET LOAD TEST - No Mocks, Real Connections Only

This focused test validates WebSocket and concurrency fixes using REAL WebSocket connections
and REAL services. All MockWebSocketConnection instances have been eliminated per CLAUDE.md.

CRITICAL: Tests the core chat responsiveness requirements:
- 5-10 concurrent users get responses within reasonable timeframes
- All WebSocket events fire correctly under load using REAL connections
- Zero message loss during normal operation
- Connection recovery works within acceptable limits
- Each concurrent user gets the complete event sequence

Business Value: $500K+ ARR - Chat delivers 90% of user value
'''

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
from dataclasses import dataclass, field
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

        # Import real services infrastructure - NO MOCKS ALLOWED
from test_framework.real_services import RealServicesManager, WebSocketTestClient, ServiceUnavailableError
from test_framework.websocket_helpers import WebSocketTestHelpers

        # Import core WebSocket and agent components for integration testing
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


@dataclass
class RealWebSocketLoadMetrics:
    "Metrics for real WebSocket load testing focused on actual system performance.""
    concurrent_users: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    events_sent: int = 0
    events_received: int = 0
    response_times_ms: List[float] = field(default_factory=list)
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    websocket_events: Dict[str, int] = field(default_factory=dict)
    missing_required_events: List[str] = field(default_factory=list)
    message_loss_count: int = 0
    test_duration_ms: float = 0.0
    connection_failures: List[str] = field(default_factory=list)
    event_sequence_failures: List[str] = field(default_factory=list)

    def calculate_stats(self):
        ""Calculate derived statistics - fails fast if no data."
        if not self.response_times_ms:
        raise AssertionError("No response times recorded - WebSocket events not working)

        self.avg_response_time_ms = sum(self.response_times_ms) / len(self.response_times_ms)
        self.max_response_time_ms = max(self.response_times_ms)
        sorted_times = sorted(self.response_times_ms)
        p95_idx = int(len(sorted_times) * 0.95)
        self.p95_response_time_ms = sorted_times[min(p95_idx, len(sorted_times)-1)]


class RealWebSocketConnection:
        ""Real WebSocket connection wrapper for load testing with REAL services."

    def __init__(self, user_id: str, services_manager: RealServicesManager):
        pass
        self.user_id = user_id
        self.services_manager = services_manager
        self.websocket_client: Optional[WebSocketTestClient] = None
        self.connected = False
        self.messages_sent = []
        self.events_received = []
        self.response_times = []
        self.last_send_time = None
        self.connection_url = "formatted_string

    async def connect(self) -> bool:
        ""Connect to real WebSocket service - fails fast if connection fails."
        try:
        self.websocket_client = self.services_manager.create_websocket_client()

        # Connect to chat endpoint with user authentication
        await self.websocket_client.connect( )
        path="formatted_string,
        headers={Authorization": "formatted_string}
        

        self.connected = True
        logger.debug(formatted_string")
        return True

        except Exception as e:
        logger.error("formatted_string)
        self.connected = False
        raise AssertionError(formatted_string")

    async def send_message(self, message: Dict[str, Any] -> None:
        "Send message through REAL WebSocket connection - fails fast on error.""
        if not self.connected or not self.websocket_client:
        raise AssertionError(formatted_string")

        try:
        self.last_send_time = time.time()
        await self.websocket_client.send(message)
        self.messages_sent.append(message)

        except Exception as e:
        logger.error("formatted_string)
        raise AssertionError(formatted_string")

    async def receive_event_with_timeout(self, timeout: float = 5.0) -> Dict[str, Any]:
        "Receive event from REAL WebSocket - fails fast if timeout or error.""
        if not self.connected or not self.websocket_client:
        raise AssertionError(formatted_string")

        try:
        event = await self.websocket_client.receive_json(timeout=timeout)

            # Record response time if we have a send timestamp
        if self.last_send_time:
        response_time = (time.time() - self.last_send_time) * 1000
        self.response_times.append(response_time)

                # Add timestamp and record event
        event['client_received_at'] = time.time()
        self.events_received.append(event)

        return event

        except asyncio.TimeoutError:
        raise AssertionError("formatted_string)
        except Exception as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)

    async def close(self) -> None:
        ""Close REAL WebSocket connection."
        if self.websocket_client:
        await self.websocket_client.close()
        self.websocket_client = None
        self.connected = False


class RealWebSocketLoadTester:
        "Load tester using REAL WebSocket connections and REAL services only.""

        REQUIRED_EVENTS = {
        agent_started",
        "agent_thinking,
        tool_executing",
        "tool_completed,
        agent_completed"
    

    def __init__(self):
        pass
        self.services_manager: Optional[RealServicesManager] = None
        self.connections: List[RealWebSocketConnection] = []
        self.metrics = RealWebSocketLoadMetrics()

    async def setup(self) -> None:
        "Initialize REAL WebSocket load test infrastructure - fails fast if services unavailable.""
        logger.info(Setting up REAL WebSocket load test infrastructure")

        try:
        # Initialize real services manager
        self.services_manager = RealServicesManager()

        # Ensure all required services are available - CRITICAL
        await self.services_manager.ensure_all_services_available()

        # Reset all data to clean state
        await self.services_manager.reset_all_data()

        logger.info("Real services setup complete - ready for load testing)

        except ServiceUnavailableError as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)
        except Exception as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)

    async def teardown(self) -> None:
        ""Clean up REAL service resources."
    # Close all real WebSocket connections
        for conn in self.connections:
        await conn.close()
        self.connections.clear()

        # Close all real service connections
        if self.services_manager:
        await self.services_manager.close_all()

    async def test_real_websocket_event_flow_under_load(self, user_count:
        '''
        Test REAL WebSocket event flow under concurrent load.

        This is the CRITICAL test - validates:
        - Multiple users can establish REAL WebSocket connections simultaneously
        - All required events are emitted via REAL WebSocket connections
        - Response times are reasonable under concurrent load
        - No events are lost through REAL connections
        - Each user gets the complete event sequence: agent_started  ->  agent_thinking  ->  tool_executing  ->  tool_completed  ->  agent_completed

        FAILS FAST if any critical requirement is not met.
        '''
        logger.info("formatted_string)

        test_start = time.time()
        self.metrics = RealWebSocketLoadMetrics(concurrent_users=user_count)

                    # Phase 1: Establish REAL WebSocket connections - CRITICAL
        await self._establish_real_connections(user_count)

                    # Phase 2: Execute concurrent agent flows through REAL connections
        await self._execute_concurrent_agent_flows()

                    # Phase 3: Validate all events received through REAL connections
        self._validate_event_completeness()

                    # Calculate final metrics
        self.metrics.test_duration_ms = (time.time() - test_start) * 1000
        self.metrics.calculate_stats()

        self._log_results()
        return self.metrics

    async def _establish_real_connections(self, user_count: int) -> None:
        ""Establish REAL WebSocket connections - fails fast if any connection fails."
        logger.info("formatted_string)

    # Create and connect all users concurrently
        connection_tasks = []
        for i in range(user_count):
        user_id = formatted_string"
        conn = RealWebSocketConnection(user_id, self.services_manager)
        self.connections.append(conn)
        connection_tasks.append(conn.connect())

        # Execute all connections concurrently - FAIL FAST if any fail
        try:
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)

            # Check for connection failures
        for i, result in enumerate(connection_results):
        if isinstance(result, Exception):
        error_msg = "formatted_string
        self.metrics.connection_failures.append(error_msg)
        self.metrics.failed_connections += 1
        logger.error(formatted_string")
        else:
        self.metrics.successful_connections += 1

                        # FAIL FAST if too many connections failed
        if self.metrics.successful_connections < user_count * 0.8:  # At least 80% must succeed
        raise AssertionError( )
        "formatted_string
        formatted_string"
                        

        logger.info("formatted_string)

        except Exception as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)

    async def _execute_concurrent_agent_flows(self) -> None:
        ""Execute concurrent agent flows through REAL WebSocket connections."
        logger.info("Executing concurrent agent flows through REAL connections)

    # Start all agent flows concurrently
        agent_flow_tasks = []
        for i, conn in enumerate(self.connections):
        if conn.connected:  # Only use successfully connected users
        request_id = formatted_string"
        task = self._execute_single_agent_flow(conn, request_id)
        agent_flow_tasks.append(task)

        # Execute all flows concurrently
        try:
        flow_results = await asyncio.gather(*agent_flow_tasks, return_exceptions=True)

            # Check for flow failures
        for i, result in enumerate(flow_results):
        if isinstance(result, Exception):
        error_msg = "formatted_string
        self.metrics.event_sequence_failures.append(error_msg)
        logger.error(formatted_string")

                    # FAIL FAST if too many flows failed
        successful_flows = len([item for item in []]
        if successful_flows < len(agent_flow_tasks) * 0.8:  # At least 80% must succeed
        raise AssertionError( )
        "formatted_string
        formatted_string"
                    

        logger.info("formatted_string)

        except Exception as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)

    async def _execute_single_agent_flow(self, conn: RealWebSocketConnection, request_id: str) -> None:
        ""Execute a single agent flow and validate complete event sequence."

    # Step 1: Send chat message to trigger agent
        chat_message = {
        "type: chat_message",
        "content: formatted_string",
        "user_id: conn.user_id,
        request_id": request_id,
        "timestamp: time.time()
    

        await conn.send_message(chat_message)

    # Step 2: Receive and validate the complete event sequence
        expected_events = [agent_started", "agent_thinking, tool_executing", "tool_completed, agent_completed"]
        received_events = []

    # Receive all expected events with reasonable timeout
        for expected_event in expected_events:
        try:
        event = await conn.receive_event_with_timeout(timeout=10.0)  # 10 second timeout per event

            # Validate event structure
        if "type not in event:
        raise AssertionError(formatted_string")

        event_type = event["type]
        received_events.append(event_type)

                # Validate event is in expected sequence
        if event_type != expected_event:
        logger.warning(formatted_string")

        logger.debug("formatted_string)

        except Exception as e:
        logger.error(formatted_string")
        raise AssertionError("formatted_string)

                        # Validate we received all required events
        missing_events = set(expected_events) - set(received_events)
        if missing_events:
        raise AssertionError(formatted_string")

        logger.debug("formatted_string)

    def _validate_event_completeness(self) -> None:
        ""Validate all required events were received across all connections."

    Aggregate events from all connections
        all_event_types = set()
        total_events = 0

        for conn in self.connections:
        if conn.connected:
        self.metrics.events_sent += len(conn.messages_sent)
        self.metrics.events_received += len(conn.events_received)
        self.metrics.response_times_ms.extend(conn.response_times)

            # Track event types
        for event in conn.events_received:
        event_type = event.get("type, unknown")
        all_event_types.add(event_type)
        self.metrics.websocket_events[event_type] = \
        self.metrics.websocket_events.get(event_type, 0) + 1
        total_events += 1

                # Check for missing required events across the entire test
        self.metrics.missing_required_events = list(self.REQUIRED_EVENTS - all_event_types)

                # FAIL FAST if critical events are missing
        if self.metrics.missing_required_events:
        raise AssertionError("formatted_string)

                    # FAIL FAST if no events received at all
        if total_events == 0:
        raise AssertionError(CRITICAL: No WebSocket events received - system not working")

                        # Validate minimum event count (each user should get at least 5 events)
        expected_min_events = len(self.connections) * len(self.REQUIRED_EVENTS)
        if total_events < expected_min_events * 0.8:  # Allow 20% tolerance
        raise AssertionError("formatted_string)

        logger.info(formatted_string")

    def _log_results(self) -> None:
        "Log comprehensive test results.""
        logger.info(formatted_string")
        logger.info(f"REAL WEBSOCKET LOAD TEST RESULTS)
        logger.info(formatted_string")
        logger.info("formatted_string)
        logger.info(formatted_string")
        logger.info("formatted_string)
        logger.info(formatted_string")
        logger.info("formatted_string)

        if self.metrics.response_times_ms:
        logger.info(f )
        Response Times:")
        logger.info("formatted_string)
        logger.info(formatted_string")
        logger.info("formatted_string)

        if self.metrics.websocket_events:
        logger.info(f )
        WebSocket Events Received:")
        for event_type, count in self.metrics.websocket_events.items():
        logger.info("formatted_string)

        if self.metrics.missing_required_events:
        logger.error(formatted_string")

        if self.metrics.connection_failures:
        logger.error(f" )
        Connection Failures:)
        for failure in self.metrics.connection_failures:
        logger.error(formatted_string")

        if self.metrics.event_sequence_failures:
        logger.error(f" )
        Event Sequence Failures:)
        for failure in self.metrics.event_sequence_failures:
        logger.error(formatted_string")

        logger.info("formatted_string)
        logger.info(formatted_string")


    async def test_real_websocket_load():
        '''
        CRITICAL TEST: Real WebSocket load test with REAL connections only.

        Validates core chat responsiveness requirements:
        PASS:  8 concurrent users can establish REAL WebSocket connections
        PASS:  All required WebSocket events are fired through REAL connections
        PASS:  Response times are reasonable under concurrent load
        PASS:  No event loss occurs through REAL connections
        PASS:  Each user receives complete event sequence

        FAILS FAST if any critical requirement is not met.
        '''
        pass
        tester = RealWebSocketLoadTester()

        try:
        await tester.setup()

                                                # Run the REAL load test
        metrics = await tester.test_real_websocket_event_flow_under_load(user_count=8)

                                                # Validate CRITICAL acceptance criteria - FAIL FAST
        assert metrics.successful_connections >= 6, \
        "formatted_string

        assert metrics.avg_response_time_ms <= 5000, \
        formatted_string"

        assert metrics.p95_response_time_ms <= 10000, \
        "formatted_string

        assert not metrics.missing_required_events, \
        formatted_string"

        assert metrics.events_received > 0, \
        "CRITICAL: No events received during test - WebSocket system not working

                                                # Validate minimum event throughput (each user should get 5 events)
        expected_min_events = metrics.successful_connections * 5
        assert metrics.events_received >= expected_min_events * 0.8, \
        formatted_string"

        logger.info(" PASS:  REAL WebSocket load test PASSED)

        await asyncio.sleep(0)
        return metrics

        except Exception as e:
        logger.error(formatted_string")
        raise
        finally:
        await tester.teardown()


    async def test_real_websocket_concurrent_stress():
        '''
        Test REAL WebSocket system under higher concurrent stress.

        Validates:
        - System handles 10 concurrent users through REAL connections
        - Performance degrades gracefully under load
        - No complete system failures occur
        - Critical events still flow under stress
        '''
        pass
        tester = RealWebSocketLoadTester()

        try:
        await tester.setup()

                                                                    # Higher load stress test
        user_count = 10
        metrics = await tester.test_real_websocket_event_flow_under_load(user_count=user_count)

                                                                    # More lenient criteria under stress, but still FAIL FAST for critical issues
        assert metrics.successful_connections >= user_count * 0.7, \
        "formatted_string

        assert metrics.avg_response_time_ms <= 10000, \
        formatted_string"

                                                                    # At least some events must be received
        assert metrics.events_received > 0, \
        "CRITICAL: No events received under stress - complete system failure

                                                                    # All event types must be present (even under stress)
        assert not metrics.missing_required_events, \
        formatted_string"

        logger.info(" PASS:  REAL WebSocket concurrent stress test PASSED)

        await asyncio.sleep(0)
        return metrics

        except Exception as e:
        logger.error(formatted_string")
        raise
        finally:
        await tester.teardown()


        if __name__ == "__main__:
    async def run_all_tests():
        ""Run all REAL WebSocket load tests."
        logger.info("=*80)
        logger.info(STARTING REAL WEBSOCKET LOAD TEST SUITE (NO MOCKS)")
        logger.info("=*80)

        try:
        # Test 1: Core REAL load test
        logger.info( )
        [1/2] Running REAL WebSocket load test...")
        metrics1 = await test_real_websocket_load()

        # Test 2: REAL stress test
        logger.info(" )
        [2/2] Running REAL WebSocket concurrent stress test...)
        metrics2 = await test_real_websocket_concurrent_stress()

        logger.info( )
        " + "=*80)
        logger.info( PASS:  ALL REAL WEBSOCKET LOAD TESTS PASSED")
        logger.info("=*80)

        await asyncio.sleep(0)
        return True

        except Exception as e:
        logger.error(formatted_string")
        logger.info("="*80)
        return False

            # Run the tests
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
        pass
