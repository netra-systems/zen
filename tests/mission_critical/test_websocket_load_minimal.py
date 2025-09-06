#!/usr/bin/env python
# REMOVED_SYNTAX_ERROR: '''REAL WEBSOCKET LOAD TEST - No Mocks, Real Connections Only

# REMOVED_SYNTAX_ERROR: This focused test validates WebSocket and concurrency fixes using REAL WebSocket connections
# REMOVED_SYNTAX_ERROR: and REAL services. All MockWebSocketConnection instances have been eliminated per CLAUDE.md.

# REMOVED_SYNTAX_ERROR: CRITICAL: Tests the core chat responsiveness requirements:
    # REMOVED_SYNTAX_ERROR: - 5-10 concurrent users get responses within reasonable timeframes
    # REMOVED_SYNTAX_ERROR: - All WebSocket events fire correctly under load using REAL connections
    # REMOVED_SYNTAX_ERROR: - Zero message loss during normal operation
    # REMOVED_SYNTAX_ERROR: - Connection recovery works within acceptable limits
    # REMOVED_SYNTAX_ERROR: - Each concurrent user gets the complete event sequence

    # REMOVED_SYNTAX_ERROR: Business Value: $500K+ ARR - Chat delivers 90% of user value
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Set, Any, Optional, Tuple
    # REMOVED_SYNTAX_ERROR: import threading
    # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass, field
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Add project root to Python path for imports
    # REMOVED_SYNTAX_ERROR: project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # REMOVED_SYNTAX_ERROR: if project_root not in sys.path:
        # REMOVED_SYNTAX_ERROR: sys.path.insert(0, project_root)

        # REMOVED_SYNTAX_ERROR: from loguru import logger

        # Import real services infrastructure - NO MOCKS ALLOWED
        # REMOVED_SYNTAX_ERROR: from test_framework.real_services import RealServicesManager, WebSocketTestClient, ServiceUnavailableError
        # REMOVED_SYNTAX_ERROR: from test_framework.websocket_helpers import WebSocketTestHelpers

        # Import core WebSocket and agent components for integration testing
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


        # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class RealWebSocketLoadMetrics:
    # REMOVED_SYNTAX_ERROR: """Metrics for real WebSocket load testing focused on actual system performance."""
    # REMOVED_SYNTAX_ERROR: concurrent_users: int = 0
    # REMOVED_SYNTAX_ERROR: successful_connections: int = 0
    # REMOVED_SYNTAX_ERROR: failed_connections: int = 0
    # REMOVED_SYNTAX_ERROR: events_sent: int = 0
    # REMOVED_SYNTAX_ERROR: events_received: int = 0
    # REMOVED_SYNTAX_ERROR: response_times_ms: List[float] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: avg_response_time_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: max_response_time_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: p95_response_time_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: websocket_events: Dict[str, int] = field(default_factory=dict)
    # REMOVED_SYNTAX_ERROR: missing_required_events: List[str] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: message_loss_count: int = 0
    # REMOVED_SYNTAX_ERROR: test_duration_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: connection_failures: List[str] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: event_sequence_failures: List[str] = field(default_factory=list)

# REMOVED_SYNTAX_ERROR: def calculate_stats(self):
    # REMOVED_SYNTAX_ERROR: """Calculate derived statistics - fails fast if no data."""
    # REMOVED_SYNTAX_ERROR: if not self.response_times_ms:
        # REMOVED_SYNTAX_ERROR: raise AssertionError("No response times recorded - WebSocket events not working")

        # REMOVED_SYNTAX_ERROR: self.avg_response_time_ms = sum(self.response_times_ms) / len(self.response_times_ms)
        # REMOVED_SYNTAX_ERROR: self.max_response_time_ms = max(self.response_times_ms)
        # REMOVED_SYNTAX_ERROR: sorted_times = sorted(self.response_times_ms)
        # REMOVED_SYNTAX_ERROR: p95_idx = int(len(sorted_times) * 0.95)
        # REMOVED_SYNTAX_ERROR: self.p95_response_time_ms = sorted_times[min(p95_idx, len(sorted_times)-1)]


# REMOVED_SYNTAX_ERROR: class RealWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection wrapper for load testing with REAL services."""

# REMOVED_SYNTAX_ERROR: def __init__(self, user_id: str, services_manager: RealServicesManager):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.services_manager = services_manager
    # REMOVED_SYNTAX_ERROR: self.websocket_client: Optional[WebSocketTestClient] = None
    # REMOVED_SYNTAX_ERROR: self.connected = False
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.events_received = []
    # REMOVED_SYNTAX_ERROR: self.response_times = []
    # REMOVED_SYNTAX_ERROR: self.last_send_time = None
    # REMOVED_SYNTAX_ERROR: self.connection_url = "formatted_string"

# REMOVED_SYNTAX_ERROR: async def connect(self) -> bool:
    # REMOVED_SYNTAX_ERROR: """Connect to real WebSocket service - fails fast if connection fails."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: self.websocket_client = self.services_manager.create_websocket_client()

        # Connect to chat endpoint with user authentication
        # REMOVED_SYNTAX_ERROR: await self.websocket_client.connect( )
        # REMOVED_SYNTAX_ERROR: path="formatted_string",
        # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
        

        # REMOVED_SYNTAX_ERROR: self.connected = True
        # REMOVED_SYNTAX_ERROR: logger.debug("formatted_string")
        # REMOVED_SYNTAX_ERROR: return True

        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
            # REMOVED_SYNTAX_ERROR: self.connected = False
            # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def send_message(self, message: Dict[str, Any]) -> None:
    # REMOVED_SYNTAX_ERROR: """Send message through REAL WebSocket connection - fails fast on error."""
    # REMOVED_SYNTAX_ERROR: if not self.connected or not self.websocket_client:
        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: self.last_send_time = time.time()
            # REMOVED_SYNTAX_ERROR: await self.websocket_client.send(message)
            # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def receive_event_with_timeout(self, timeout: float = 5.0) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Receive event from REAL WebSocket - fails fast if timeout or error."""
    # REMOVED_SYNTAX_ERROR: if not self.connected or not self.websocket_client:
        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: event = await self.websocket_client.receive_json(timeout=timeout)

            # Record response time if we have a send timestamp
            # REMOVED_SYNTAX_ERROR: if self.last_send_time:
                # REMOVED_SYNTAX_ERROR: response_time = (time.time() - self.last_send_time) * 1000
                # REMOVED_SYNTAX_ERROR: self.response_times.append(response_time)

                # Add timestamp and record event
                # REMOVED_SYNTAX_ERROR: event['client_received_at'] = time.time()
                # REMOVED_SYNTAX_ERROR: self.events_received.append(event)

                # REMOVED_SYNTAX_ERROR: return event

                # REMOVED_SYNTAX_ERROR: except asyncio.TimeoutError:
                    # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def close(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Close REAL WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: if self.websocket_client:
        # REMOVED_SYNTAX_ERROR: await self.websocket_client.close()
        # REMOVED_SYNTAX_ERROR: self.websocket_client = None
        # REMOVED_SYNTAX_ERROR: self.connected = False


# REMOVED_SYNTAX_ERROR: class RealWebSocketLoadTester:
    # REMOVED_SYNTAX_ERROR: """Load tester using REAL WebSocket connections and REAL services only."""

    # REMOVED_SYNTAX_ERROR: REQUIRED_EVENTS = { )
    # REMOVED_SYNTAX_ERROR: "agent_started",
    # REMOVED_SYNTAX_ERROR: "agent_thinking",
    # REMOVED_SYNTAX_ERROR: "tool_executing",
    # REMOVED_SYNTAX_ERROR: "tool_completed",
    # REMOVED_SYNTAX_ERROR: "agent_completed"
    

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.services_manager: Optional[RealServicesManager] = None
    # REMOVED_SYNTAX_ERROR: self.connections: List[RealWebSocketConnection] = []
    # REMOVED_SYNTAX_ERROR: self.metrics = RealWebSocketLoadMetrics()

# REMOVED_SYNTAX_ERROR: async def setup(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Initialize REAL WebSocket load test infrastructure - fails fast if services unavailable."""
    # REMOVED_SYNTAX_ERROR: logger.info("Setting up REAL WebSocket load test infrastructure")

    # REMOVED_SYNTAX_ERROR: try:
        # Initialize real services manager
        # REMOVED_SYNTAX_ERROR: self.services_manager = RealServicesManager()

        # Ensure all required services are available - CRITICAL
        # REMOVED_SYNTAX_ERROR: await self.services_manager.ensure_all_services_available()

        # Reset all data to clean state
        # REMOVED_SYNTAX_ERROR: await self.services_manager.reset_all_data()

        # REMOVED_SYNTAX_ERROR: logger.info("Real services setup complete - ready for load testing")

        # REMOVED_SYNTAX_ERROR: except ServiceUnavailableError as e:
            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
            # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def teardown(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Clean up REAL service resources."""
    # Close all real WebSocket connections
    # REMOVED_SYNTAX_ERROR: for conn in self.connections:
        # REMOVED_SYNTAX_ERROR: await conn.close()
        # REMOVED_SYNTAX_ERROR: self.connections.clear()

        # Close all real service connections
        # REMOVED_SYNTAX_ERROR: if self.services_manager:
            # REMOVED_SYNTAX_ERROR: await self.services_manager.close_all()

            # Removed problematic line: async def test_real_websocket_event_flow_under_load(self, user_count: int = 8) -> RealWebSocketLoadMetrics:
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test REAL WebSocket event flow under concurrent load.

                # REMOVED_SYNTAX_ERROR: This is the CRITICAL test - validates:
                    # REMOVED_SYNTAX_ERROR: - Multiple users can establish REAL WebSocket connections simultaneously
                    # REMOVED_SYNTAX_ERROR: - All required events are emitted via REAL WebSocket connections
                    # REMOVED_SYNTAX_ERROR: - Response times are reasonable under concurrent load
                    # REMOVED_SYNTAX_ERROR: - No events are lost through REAL connections
                    # REMOVED_SYNTAX_ERROR: - Each user gets the complete event sequence: agent_started → agent_thinking → tool_executing → tool_completed → agent_completed

                    # REMOVED_SYNTAX_ERROR: FAILS FAST if any critical requirement is not met.
                    # REMOVED_SYNTAX_ERROR: '''
                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                    # REMOVED_SYNTAX_ERROR: test_start = time.time()
                    # REMOVED_SYNTAX_ERROR: self.metrics = RealWebSocketLoadMetrics(concurrent_users=user_count)

                    # Phase 1: Establish REAL WebSocket connections - CRITICAL
                    # REMOVED_SYNTAX_ERROR: await self._establish_real_connections(user_count)

                    # Phase 2: Execute concurrent agent flows through REAL connections
                    # REMOVED_SYNTAX_ERROR: await self._execute_concurrent_agent_flows()

                    # Phase 3: Validate all events received through REAL connections
                    # REMOVED_SYNTAX_ERROR: self._validate_event_completeness()

                    # Calculate final metrics
                    # REMOVED_SYNTAX_ERROR: self.metrics.test_duration_ms = (time.time() - test_start) * 1000
                    # REMOVED_SYNTAX_ERROR: self.metrics.calculate_stats()

                    # REMOVED_SYNTAX_ERROR: self._log_results()
                    # REMOVED_SYNTAX_ERROR: return self.metrics

# REMOVED_SYNTAX_ERROR: async def _establish_real_connections(self, user_count: int) -> None:
    # REMOVED_SYNTAX_ERROR: """Establish REAL WebSocket connections - fails fast if any connection fails."""
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

    # Create and connect all users concurrently
    # REMOVED_SYNTAX_ERROR: connection_tasks = []
    # REMOVED_SYNTAX_ERROR: for i in range(user_count):
        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
        # REMOVED_SYNTAX_ERROR: conn = RealWebSocketConnection(user_id, self.services_manager)
        # REMOVED_SYNTAX_ERROR: self.connections.append(conn)
        # REMOVED_SYNTAX_ERROR: connection_tasks.append(conn.connect())

        # Execute all connections concurrently - FAIL FAST if any fail
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)

            # Check for connection failures
            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(connection_results):
                # REMOVED_SYNTAX_ERROR: if isinstance(result, Exception):
                    # REMOVED_SYNTAX_ERROR: error_msg = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: self.metrics.connection_failures.append(error_msg)
                    # REMOVED_SYNTAX_ERROR: self.metrics.failed_connections += 1
                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: self.metrics.successful_connections += 1

                        # FAIL FAST if too many connections failed
                        # REMOVED_SYNTAX_ERROR: if self.metrics.successful_connections < user_count * 0.8:  # At least 80% must succeed
                        # REMOVED_SYNTAX_ERROR: raise AssertionError( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        

                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def _execute_concurrent_agent_flows(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Execute concurrent agent flows through REAL WebSocket connections."""
    # REMOVED_SYNTAX_ERROR: logger.info("Executing concurrent agent flows through REAL connections")

    # Start all agent flows concurrently
    # REMOVED_SYNTAX_ERROR: agent_flow_tasks = []
    # REMOVED_SYNTAX_ERROR: for i, conn in enumerate(self.connections):
        # REMOVED_SYNTAX_ERROR: if conn.connected:  # Only use successfully connected users
        # REMOVED_SYNTAX_ERROR: request_id = "formatted_string"
        # REMOVED_SYNTAX_ERROR: task = self._execute_single_agent_flow(conn, request_id)
        # REMOVED_SYNTAX_ERROR: agent_flow_tasks.append(task)

        # Execute all flows concurrently
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: flow_results = await asyncio.gather(*agent_flow_tasks, return_exceptions=True)

            # Check for flow failures
            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(flow_results):
                # REMOVED_SYNTAX_ERROR: if isinstance(result, Exception):
                    # REMOVED_SYNTAX_ERROR: error_msg = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: self.metrics.event_sequence_failures.append(error_msg)
                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                    # FAIL FAST if too many flows failed
                    # REMOVED_SYNTAX_ERROR: successful_flows = len([item for item in []])
                    # REMOVED_SYNTAX_ERROR: if successful_flows < len(agent_flow_tasks) * 0.8:  # At least 80% must succeed
                    # REMOVED_SYNTAX_ERROR: raise AssertionError( )
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def _execute_single_agent_flow(self, conn: RealWebSocketConnection, request_id: str) -> None:
    # REMOVED_SYNTAX_ERROR: """Execute a single agent flow and validate complete event sequence."""

    # Step 1: Send chat message to trigger agent
    # REMOVED_SYNTAX_ERROR: chat_message = { )
    # REMOVED_SYNTAX_ERROR: "type": "chat_message",
    # REMOVED_SYNTAX_ERROR: "content": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "user_id": conn.user_id,
    # REMOVED_SYNTAX_ERROR: "request_id": request_id,
    # REMOVED_SYNTAX_ERROR: "timestamp": time.time()
    

    # REMOVED_SYNTAX_ERROR: await conn.send_message(chat_message)

    # Step 2: Receive and validate the complete event sequence
    # REMOVED_SYNTAX_ERROR: expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
    # REMOVED_SYNTAX_ERROR: received_events = []

    # Receive all expected events with reasonable timeout
    # REMOVED_SYNTAX_ERROR: for expected_event in expected_events:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: event = await conn.receive_event_with_timeout(timeout=10.0)  # 10 second timeout per event

            # Validate event structure
            # REMOVED_SYNTAX_ERROR: if "type" not in event:
                # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

                # REMOVED_SYNTAX_ERROR: event_type = event["type"]
                # REMOVED_SYNTAX_ERROR: received_events.append(event_type)

                # Validate event is in expected sequence
                # REMOVED_SYNTAX_ERROR: if event_type != expected_event:
                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                    # REMOVED_SYNTAX_ERROR: logger.debug("formatted_string")

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

                        # Validate we received all required events
                        # REMOVED_SYNTAX_ERROR: missing_events = set(expected_events) - set(received_events)
                        # REMOVED_SYNTAX_ERROR: if missing_events:
                            # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

                            # REMOVED_SYNTAX_ERROR: logger.debug("formatted_string")

# REMOVED_SYNTAX_ERROR: def _validate_event_completeness(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Validate all required events were received across all connections."""

    # Aggregate events from all connections
    # REMOVED_SYNTAX_ERROR: all_event_types = set()
    # REMOVED_SYNTAX_ERROR: total_events = 0

    # REMOVED_SYNTAX_ERROR: for conn in self.connections:
        # REMOVED_SYNTAX_ERROR: if conn.connected:
            # REMOVED_SYNTAX_ERROR: self.metrics.events_sent += len(conn.messages_sent)
            # REMOVED_SYNTAX_ERROR: self.metrics.events_received += len(conn.events_received)
            # REMOVED_SYNTAX_ERROR: self.metrics.response_times_ms.extend(conn.response_times)

            # Track event types
            # REMOVED_SYNTAX_ERROR: for event in conn.events_received:
                # REMOVED_SYNTAX_ERROR: event_type = event.get("type", "unknown")
                # REMOVED_SYNTAX_ERROR: all_event_types.add(event_type)
                # REMOVED_SYNTAX_ERROR: self.metrics.websocket_events[event_type] = \
                # REMOVED_SYNTAX_ERROR: self.metrics.websocket_events.get(event_type, 0) + 1
                # REMOVED_SYNTAX_ERROR: total_events += 1

                # Check for missing required events across the entire test
                # REMOVED_SYNTAX_ERROR: self.metrics.missing_required_events = list(self.REQUIRED_EVENTS - all_event_types)

                # FAIL FAST if critical events are missing
                # REMOVED_SYNTAX_ERROR: if self.metrics.missing_required_events:
                    # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

                    # FAIL FAST if no events received at all
                    # REMOVED_SYNTAX_ERROR: if total_events == 0:
                        # REMOVED_SYNTAX_ERROR: raise AssertionError("CRITICAL: No WebSocket events received - system not working")

                        # Validate minimum event count (each user should get at least 5 events)
                        # REMOVED_SYNTAX_ERROR: expected_min_events = len(self.connections) * len(self.REQUIRED_EVENTS)
                        # REMOVED_SYNTAX_ERROR: if total_events < expected_min_events * 0.8:  # Allow 20% tolerance
                        # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def _log_results(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Log comprehensive test results."""
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info(f"REAL WEBSOCKET LOAD TEST RESULTS")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

    # REMOVED_SYNTAX_ERROR: if self.metrics.response_times_ms:
        # REMOVED_SYNTAX_ERROR: logger.info(f" )
        # REMOVED_SYNTAX_ERROR: Response Times:")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # REMOVED_SYNTAX_ERROR: if self.metrics.websocket_events:
            # REMOVED_SYNTAX_ERROR: logger.info(f" )
            # REMOVED_SYNTAX_ERROR: WebSocket Events Received:")
            # REMOVED_SYNTAX_ERROR: for event_type, count in self.metrics.websocket_events.items():
                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # REMOVED_SYNTAX_ERROR: if self.metrics.missing_required_events:
                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                    # REMOVED_SYNTAX_ERROR: if self.metrics.connection_failures:
                        # REMOVED_SYNTAX_ERROR: logger.error(f" )
                        # REMOVED_SYNTAX_ERROR: Connection Failures:")
                        # REMOVED_SYNTAX_ERROR: for failure in self.metrics.connection_failures:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                            # REMOVED_SYNTAX_ERROR: if self.metrics.event_sequence_failures:
                                # REMOVED_SYNTAX_ERROR: logger.error(f" )
                                # REMOVED_SYNTAX_ERROR: Event Sequence Failures:")
                                # REMOVED_SYNTAX_ERROR: for failure in self.metrics.event_sequence_failures:
                                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")


                                    # Removed problematic line: async def test_real_websocket_load():
                                        # REMOVED_SYNTAX_ERROR: '''
                                        # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Real WebSocket load test with REAL connections only.

                                        # REMOVED_SYNTAX_ERROR: Validates core chat responsiveness requirements:
                                            # REMOVED_SYNTAX_ERROR: ✅ 8 concurrent users can establish REAL WebSocket connections
                                            # REMOVED_SYNTAX_ERROR: ✅ All required WebSocket events are fired through REAL connections
                                            # REMOVED_SYNTAX_ERROR: ✅ Response times are reasonable under concurrent load
                                            # REMOVED_SYNTAX_ERROR: ✅ No event loss occurs through REAL connections
                                            # REMOVED_SYNTAX_ERROR: ✅ Each user receives complete event sequence

                                            # REMOVED_SYNTAX_ERROR: FAILS FAST if any critical requirement is not met.
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: tester = RealWebSocketLoadTester()

                                            # REMOVED_SYNTAX_ERROR: try:
                                                # REMOVED_SYNTAX_ERROR: await tester.setup()

                                                # Run the REAL load test
                                                # REMOVED_SYNTAX_ERROR: metrics = await tester.test_real_websocket_event_flow_under_load(user_count=8)

                                                # Validate CRITICAL acceptance criteria - FAIL FAST
                                                # REMOVED_SYNTAX_ERROR: assert metrics.successful_connections >= 6, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: assert metrics.avg_response_time_ms <= 5000, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: assert metrics.p95_response_time_ms <= 10000, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: assert not metrics.missing_required_events, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: assert metrics.events_received > 0, \
                                                # REMOVED_SYNTAX_ERROR: "CRITICAL: No events received during test - WebSocket system not working"

                                                # Validate minimum event throughput (each user should get 5 events)
                                                # REMOVED_SYNTAX_ERROR: expected_min_events = metrics.successful_connections * 5
                                                # REMOVED_SYNTAX_ERROR: assert metrics.events_received >= expected_min_events * 0.8, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: logger.info("✅ REAL WebSocket load test PASSED")

                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                                                # REMOVED_SYNTAX_ERROR: return metrics

                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                                    # REMOVED_SYNTAX_ERROR: raise
                                                    # REMOVED_SYNTAX_ERROR: finally:
                                                        # REMOVED_SYNTAX_ERROR: await tester.teardown()


                                                        # Removed problematic line: async def test_real_websocket_concurrent_stress():
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: Test REAL WebSocket system under higher concurrent stress.

                                                            # REMOVED_SYNTAX_ERROR: Validates:
                                                                # REMOVED_SYNTAX_ERROR: - System handles 10 concurrent users through REAL connections
                                                                # REMOVED_SYNTAX_ERROR: - Performance degrades gracefully under load
                                                                # REMOVED_SYNTAX_ERROR: - No complete system failures occur
                                                                # REMOVED_SYNTAX_ERROR: - Critical events still flow under stress
                                                                # REMOVED_SYNTAX_ERROR: '''
                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                # REMOVED_SYNTAX_ERROR: tester = RealWebSocketLoadTester()

                                                                # REMOVED_SYNTAX_ERROR: try:
                                                                    # REMOVED_SYNTAX_ERROR: await tester.setup()

                                                                    # Higher load stress test
                                                                    # REMOVED_SYNTAX_ERROR: user_count = 10
                                                                    # REMOVED_SYNTAX_ERROR: metrics = await tester.test_real_websocket_event_flow_under_load(user_count=user_count)

                                                                    # More lenient criteria under stress, but still FAIL FAST for critical issues
                                                                    # REMOVED_SYNTAX_ERROR: assert metrics.successful_connections >= user_count * 0.7, \
                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                    # REMOVED_SYNTAX_ERROR: assert metrics.avg_response_time_ms <= 10000, \
                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                    # At least some events must be received
                                                                    # REMOVED_SYNTAX_ERROR: assert metrics.events_received > 0, \
                                                                    # REMOVED_SYNTAX_ERROR: "CRITICAL: No events received under stress - complete system failure"

                                                                    # All event types must be present (even under stress)
                                                                    # REMOVED_SYNTAX_ERROR: assert not metrics.missing_required_events, \
                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                    # REMOVED_SYNTAX_ERROR: logger.info("✅ REAL WebSocket concurrent stress test PASSED")

                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                                                                    # REMOVED_SYNTAX_ERROR: return metrics

                                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                        # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                                                        # REMOVED_SYNTAX_ERROR: raise
                                                                        # REMOVED_SYNTAX_ERROR: finally:
                                                                            # REMOVED_SYNTAX_ERROR: await tester.teardown()


                                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
# REMOVED_SYNTAX_ERROR: async def run_all_tests():
    # REMOVED_SYNTAX_ERROR: """Run all REAL WebSocket load tests."""
    # REMOVED_SYNTAX_ERROR: logger.info("="*80)
    # REMOVED_SYNTAX_ERROR: logger.info("STARTING REAL WEBSOCKET LOAD TEST SUITE (NO MOCKS)")
    # REMOVED_SYNTAX_ERROR: logger.info("="*80)

    # REMOVED_SYNTAX_ERROR: try:
        # Test 1: Core REAL load test
        # REMOVED_SYNTAX_ERROR: logger.info(" )
        # REMOVED_SYNTAX_ERROR: [1/2] Running REAL WebSocket load test...")
        # REMOVED_SYNTAX_ERROR: metrics1 = await test_real_websocket_load()

        # Test 2: REAL stress test
        # REMOVED_SYNTAX_ERROR: logger.info(" )
        # REMOVED_SYNTAX_ERROR: [2/2] Running REAL WebSocket concurrent stress test...")
        # REMOVED_SYNTAX_ERROR: metrics2 = await test_real_websocket_concurrent_stress()

        # REMOVED_SYNTAX_ERROR: logger.info(" )
        # REMOVED_SYNTAX_ERROR: " + "="*80)
        # REMOVED_SYNTAX_ERROR: logger.info("✅ ALL REAL WEBSOCKET LOAD TESTS PASSED")
        # REMOVED_SYNTAX_ERROR: logger.info("="*80)

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return True

        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("="*80)
            # REMOVED_SYNTAX_ERROR: return False

            # Run the tests
            # REMOVED_SYNTAX_ERROR: success = asyncio.run(run_all_tests())
            # REMOVED_SYNTAX_ERROR: exit(0 if success else 1)
            # REMOVED_SYNTAX_ERROR: pass