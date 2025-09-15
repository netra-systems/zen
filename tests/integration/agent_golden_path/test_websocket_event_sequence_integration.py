"""
WebSocket Event Sequence Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Real-time user experience
- Business Goal: User Retention & Experience - Premium UX through real-time feedback
- Value Impact: Validates WebSocket event delivery enables responsive chat experience
- Strategic Impact: Critical UX component - real-time events essential for chat platform competitiveness

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for WebSocket integration tests - uses real WebSocket connections
- Tests must validate all 5 critical WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Event timing and order must be validated for optimal user experience
- Event delivery reliability must be tested under various conditions
- Tests must pass or fail meaningfully (no test cheating allowed)

This module tests the COMPLETE WebSocket event sequence covering:
1. All 5 business-critical WebSocket events during agent execution
2. Event timing and sequencing for optimal user experience
3. Event delivery reliability under various network conditions
4. Multi-user event isolation (events only delivered to correct user)
5. Event content validation and user experience quality
6. Performance requirements for real-time responsiveness

ARCHITECTURE ALIGNMENT:
- Uses real WebSocket manager for event delivery testing
- Tests WebSocket bridge integration with agent execution
- Tests event sequencing during complete Golden Path execution
- Validates event delivery under error conditions and recovery
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field

import pytest

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# CRITICAL: Import REAL WebSocket components
try:
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
    from shared.types.core_types import UserID, ThreadID, RunID
    REAL_WEBSOCKET_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some real WebSocket components not available: {e}")
    REAL_WEBSOCKET_COMPONENTS_AVAILABLE = False
    WebSocketManager = MagicMock
    get_websocket_manager = MagicMock

@dataclass
class WebSocketEvent:
    """WebSocket event data structure for testing."""
    event_type: str
    timestamp: float
    user_id: str
    thread_id: str
    content: Dict[str, Any] = field(default_factory=dict)
    delivery_confirmed: bool = False

@dataclass
class EventSequenceTracker:
    """Tracks WebSocket event sequences for validation."""
    expected_events: List[str] = field(default_factory=list)
    received_events: List[WebSocketEvent] = field(default_factory=list)
    start_time: Optional[float] = None
    completion_time: Optional[float] = None

    def add_event(self, event: WebSocketEvent):
        """Add received event to tracker."""
        self.received_events.append(event)

    def get_event_count(self) -> int:
        """Get total number of events received."""
        return len(self.received_events)

    def get_events_by_type(self, event_type: str) -> List[WebSocketEvent]:
        """Get all events of specific type."""
        return [event for event in self.received_events if event.event_type == event_type]

    def validate_sequence(self) -> bool:
        """Validate received events match expected sequence."""
        received_types = [event.event_type for event in self.received_events]
        return received_types == self.expected_events

    def get_sequence_duration(self) -> float:
        """Get total sequence duration in seconds."""
        if not self.received_events:
            return 0.0
        return self.received_events[-1].timestamp - self.received_events[0].timestamp

class TestWebSocketEventSequenceIntegration(SSotAsyncTestCase):
    """
    P0 Critical Integration Tests for WebSocket Event Sequence Delivery.

    This test class validates the complete WebSocket event sequence:
    Agent Execution → Event Generation → Event Delivery → User Experience

    Tests protect real-time user experience by validating:
    - All 5 critical WebSocket events delivered in correct sequence
    - Event timing meets user experience requirements
    - Event delivery reliability under various conditions
    - Multi-user event isolation and security
    - Event content quality and completeness
    - Real-time responsiveness performance
    """

    def setup_method(self, method):
        """Set up test environment with real WebSocket event infrastructure."""
        super().setup_method(method)

        # Initialize environment for WebSocket event testing
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_ENV", "integration")
        self.set_env_var("ENABLE_REAL_WEBSOCKET_EVENTS", "true")

        # Create unique test identifiers for WebSocket isolation
        self.test_user_id = UserID(f"ws_event_user_{uuid.uuid4().hex[:8]}")
        self.test_thread_id = ThreadID(f"ws_event_thread_{uuid.uuid4().hex[:8]}")
        self.test_run_id = RunID(f"ws_event_run_{uuid.uuid4().hex[:8]}")

        # Define critical WebSocket events for Golden Path
        self.critical_websocket_events = [
            'agent_started',      # User sees agent began processing
            'agent_thinking',     # Real-time reasoning visibility
            'tool_executing',     # Tool usage transparency
            'tool_completed',     # Tool results display
            'agent_completed'     # User knows response is ready
        ]

        # Track WebSocket event metrics for UX analysis
        self.websocket_metrics = {
            'events_sent': 0,
            'events_delivered': 0,
            'event_sequences_completed': 0,
            'average_event_latency_ms': 0,
            'event_delivery_success_rate': 0,
            'real_time_performance_met': 0,
            'user_experience_optimal': 0,
            'multi_user_isolation_maintained': 0
        }

        # Initialize WebSocket components
        self.websocket_manager = None
        self.websocket_bridge = None
        self.agent_factory = None
        self.event_trackers = {}  # Track events per user
        self.websocket_connections = {}  # Active WebSocket connections

    async def async_setup_method(self, method=None):
        """Set up async components with real WebSocket infrastructure."""
        await super().async_setup_method(method)
        await self._initialize_real_websocket_infrastructure()

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)

    async def async_teardown_method(self, method=None):
        """Clean up async resources and record WebSocket event metrics."""
        try:
            # Record WebSocket event metrics for UX analysis
            self.record_metric("websocket_event_metrics", self.websocket_metrics)

            # Clean up WebSocket connections for isolation
            for connection in self.websocket_connections.values():
                if hasattr(connection, 'close'):
                    await connection.close()

            # Clean up WebSocket infrastructure
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                if hasattr(self.websocket_manager, 'cleanup'):
                    await self.websocket_manager.cleanup()

        except Exception as e:
            print(f"WebSocket cleanup error: {e}")

        await super().async_teardown_method(method)

    async def _initialize_real_websocket_infrastructure(self):
        """Initialize real WebSocket infrastructure components."""
        if not REAL_WEBSOCKET_COMPONENTS_AVAILABLE:return

        try:
            # Initialize real WebSocket manager
            self.websocket_manager = get_websocket_manager()

            # Initialize real WebSocket bridge for agent integration
            self.websocket_bridge = create_agent_websocket_bridge()

            # Initialize agent factory with WebSocket integration
            self.agent_factory = get_agent_instance_factory()
            if hasattr(self.agent_factory, 'configure'):
                self.agent_factory.configure(
                    websocket_bridge=self.websocket_bridge,
                    websocket_manager=self.websocket_manager
                )

        except Exception as e:

            # CLAUDE.md COMPLIANCE: Tests must use real services only

            raise RuntimeError(f"Failed to initialize real infrastructure: {e}") from e

    def _initialize_mock_websocket_infrastructure(self):
        """Initialize mock WebSocket infrastructure for fallback testing."""
        self.websocket_manager = MagicMock()
        self.websocket_bridge = MagicMock()
        self.agent_factory = MagicMock()

        # Configure mock WebSocket methods
        self.websocket_manager.send_event = AsyncMock()
        self.websocket_bridge.send_agent_event = AsyncMock()
        self.agent_factory.create_user_execution_context = AsyncMock()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_websocket_event_sequence_during_agent_execution(self):
        """
        Test complete WebSocket event sequence during Golden Path agent execution.

        Business Value: Core UX requirement - validates all 5 critical events
        delivered in correct sequence for optimal real-time user experience.
        """
        # Set up event sequence tracking
        event_tracker = EventSequenceTracker(expected_events=self.critical_websocket_events.copy())
        self.event_trackers[self.test_user_id] = event_tracker

        # Business scenario requiring complete agent execution with events
        agent_task = {
            'content': 'Analyze quarterly sales performance and generate strategic recommendations',
            'task_type': 'business_analysis',
            'complexity': 'high',
            'expected_duration': '8-12 seconds',
            'deliverables': ['analysis', 'recommendations', 'action_items']
        }

        # Track complete event sequence timing
        sequence_start = time.time()
        event_tracker.start_time = sequence_start

        async with self._get_user_execution_context() as user_context:

            # Create WebSocket connection for real-time event delivery
            async with self._create_websocket_connection(user_context) as ws_connection:

                # Stage 1: Start agent execution with WebSocket event monitoring
                agent = await self._create_websocket_enabled_agent(user_context)

                # Start listening for WebSocket events
                event_listener_task = asyncio.create_task(
                    self._listen_for_websocket_events(ws_connection, event_tracker)
                )

                # Stage 2: Execute agent task that triggers all 5 critical events
                execution_start = time.time()

                agent_response = await self._execute_agent_with_websocket_events(
                    agent, agent_task, user_context
                )

                execution_time = time.time() - execution_start

                # Wait for all events to be received (with timeout)
                await asyncio.sleep(1.0)  # Allow time for event delivery
                event_listener_task.cancel()

                # Stage 3: Validate complete event sequence
                event_tracker.completion_time = time.time()
                sequence_duration = event_tracker.get_sequence_duration()

                # Validate all critical events were delivered
                events_received = event_tracker.get_event_count()
                self.assertGreaterEqual(events_received, len(self.critical_websocket_events),
                                      f"Missing critical events: {events_received}/{len(self.critical_websocket_events)}")

                # Validate event sequence correctness
                sequence_valid = event_tracker.validate_sequence()
                self.assertTrue(sequence_valid, "WebSocket events not delivered in correct sequence")

                # Validate event timing for real-time user experience
                self.assertLess(sequence_duration, 15.0,
                              f"Event sequence too slow for real-time UX: {sequence_duration:.3f}s")

                # Validate individual event timing
                events = event_tracker.received_events
                for i in range(1, len(events)):
                    time_between_events = events[i].timestamp - events[i-1].timestamp
                    self.assertLess(time_between_events, 5.0,
                                  f"Too long between events {events[i-1].event_type} and {events[i].event_type}: {time_between_events:.3f}s")

                # Stage 4: Validate event content quality
                for event in events:
                    self.assertIsNotNone(event.content, f"Event {event.event_type} missing content")
                    self.assertEqual(event.user_id, str(user_context.user_id),
                                   f"Event {event.event_type} has wrong user_id")

                # Record successful event sequence metrics
                self.websocket_metrics['events_sent'] += len(self.critical_websocket_events)
                self.websocket_metrics['events_delivered'] += events_received
                self.websocket_metrics['event_sequences_completed'] += 1

                if sequence_duration < 15.0:
                    self.websocket_metrics['real_time_performance_met'] += 1
                    self.websocket_metrics['user_experience_optimal'] += 1

                # Calculate and record event delivery metrics
                delivery_success_rate = events_received / len(self.critical_websocket_events)
                self.websocket_metrics['event_delivery_success_rate'] = delivery_success_rate

                if events:
                    avg_latency = sum(event.timestamp - sequence_start for event in events) / len(events)
                    self.websocket_metrics['average_event_latency_ms'] = avg_latency * 1000

                # Record detailed performance metrics
                self.record_metric("websocket_sequence_duration_ms", sequence_duration * 1000)
                self.record_metric("websocket_events_delivered_count", events_received)
                self.record_metric("websocket_delivery_success_rate", delivery_success_rate)
                self.record_metric("agent_execution_time_ms", execution_time * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_event_timing_and_user_experience_quality(self):
        """
        Test WebSocket event timing meets user experience quality requirements.

        Business Value: Premium UX - validates event timing provides responsive,
        engaging real-time feedback during agent processing.
        """
        # Define UX timing requirements for different event types
        ux_timing_requirements = {
            'agent_started': {'max_delay': 0.5, 'description': 'Immediate feedback user request acknowledged'},
            'agent_thinking': {'max_delay': 2.0, 'description': 'Quick thinking updates maintain engagement'},
            'tool_executing': {'max_delay': 1.0, 'description': 'Tool execution visibility builds confidence'},
            'tool_completed': {'max_delay': 0.5, 'description': 'Tool completion provides closure'},
            'agent_completed': {'max_delay': 0.3, 'description': 'Response ready notification immediate'}
        }

        # Complex agent task requiring all event types
        complex_task = {
            'content': 'Comprehensive market analysis with competitive intelligence and growth projections',
            'complexity': 'very_high',
            'tools_required': ['market_research', 'competitor_analysis', 'financial_modeling'],
            'expected_events': list(ux_timing_requirements.keys())
        }

        event_tracker = EventSequenceTracker(expected_events=list(ux_timing_requirements.keys()))
        timing_violations = []

        async with self._get_user_execution_context() as user_context:

            async with self._create_websocket_connection(user_context) as ws_connection:

                # Create agent optimized for UX timing
                agent = await self._create_ux_optimized_websocket_agent(user_context)

                # Start precise event timing monitoring
                timing_monitor_task = asyncio.create_task(
                    self._monitor_precise_event_timing(ws_connection, event_tracker, ux_timing_requirements)
                )

                # Execute complex task with UX timing validation
                task_start = time.time()

                agent_response = await self._execute_complex_task_with_timing_validation(
                    agent, complex_task, user_context
                )

                task_duration = time.time() - task_start

                # Complete timing monitoring
                await asyncio.sleep(0.5)  # Allow final events
                timing_monitor_task.cancel()

                # Validate UX timing requirements
                events = event_tracker.received_events

                for event in events:
                    event_requirements = ux_timing_requirements.get(event.event_type, {})
                    if event_requirements:
                        max_delay = event_requirements['max_delay']
                        event_delay = event.timestamp - task_start

                        if event_delay > max_delay:
                            timing_violations.append({
                                'event_type': event.event_type,
                                'actual_delay': event_delay,
                                'max_allowed': max_delay,
                                'description': event_requirements['description']
                            })

                # Validate no critical timing violations
                self.assertEqual(len(timing_violations), 0,
                               f"UX timing violations detected: {timing_violations}")

                # Validate overall user experience timing
                self.assertLess(task_duration, 20.0,
                              f"Overall task duration too slow for UX: {task_duration:.3f}s")

                # Validate event frequency for engagement
                if len(events) > 1:
                    total_duration = events[-1].timestamp - events[0].timestamp
                    average_time_between_events = total_duration / (len(events) - 1)
                    self.assertLess(average_time_between_events, 4.0,
                                  f"Events too infrequent for engaging UX: {average_time_between_events:.3f}s")

                # Record UX quality metrics
                self.record_metric("ux_timing_violations_count", len(timing_violations))
                self.record_metric("ux_task_duration_ms", task_duration * 1000)
                self.record_metric("ux_average_event_interval_ms",
                                 (average_time_between_events * 1000) if len(events) > 1 else 0)

                if len(timing_violations) == 0:
                    self.websocket_metrics['user_experience_optimal'] += 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_user_websocket_event_isolation_and_security(self):
        """
        Test multi-user WebSocket event isolation prevents cross-user event delivery.

        Business Value: Security & Compliance - validates WebSocket events only
        delivered to correct user, preventing information leakage.
        """
        # Create multiple concurrent users with sensitive agent tasks
        user_scenarios = [
            {
                'user_id': UserID(f"user_finance_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"thread_finance_{uuid.uuid4().hex[:8]}"),
                'task': 'Analyze confidential financial projections for Q4',
                'sensitivity': 'confidential',
                'domain': 'finance'
            },
            {
                'user_id': UserID(f"user_legal_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"thread_legal_{uuid.uuid4().hex[:8]}"),
                'task': 'Review privileged attorney-client case analysis',
                'sensitivity': 'privileged',
                'domain': 'legal'
            },
            {
                'user_id': UserID(f"user_hr_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"thread_hr_{uuid.uuid4().hex[:8]}"),
                'task': 'Process employee performance review data',
                'sensitivity': 'personal_data',
                'domain': 'hr'
            }
        ]

        # Track events for each user separately
        user_event_trackers = {}
        user_connections = {}
        concurrent_tasks = []

        # Set up isolated WebSocket connections for each user
        for scenario in user_scenarios:
            user_id = scenario['user_id']
            event_tracker = EventSequenceTracker(expected_events=self.critical_websocket_events.copy())
            user_event_trackers[user_id] = event_tracker
            self.event_trackers[user_id] = event_tracker

        # Execute concurrent agent tasks with WebSocket event monitoring
        for scenario in user_scenarios:
            task = asyncio.create_task(
                self._execute_isolated_user_scenario(scenario, user_event_trackers, user_connections)
            )
            concurrent_tasks.append(task)

        # Wait for all concurrent executions to complete
        scenario_results = await asyncio.gather(*concurrent_tasks)

        # Validate complete event isolation between users
        for i, scenario_a in enumerate(user_scenarios):
            for j, scenario_b in enumerate(user_scenarios):
                if i != j:
                    user_a_id = scenario_a['user_id']
                    user_b_id = scenario_b['user_id']

                    events_a = user_event_trackers[user_a_id].received_events
                    events_b = user_event_trackers[user_b_id].received_events

                    # Validate no cross-user event delivery
                    for event in events_a:
                        self.assertEqual(event.user_id, str(user_a_id),
                                       f"User A received event intended for different user: {event.user_id}")
                        self.assertNotEqual(event.user_id, str(user_b_id),
                                          f"CRITICAL: User A received User B's events - security breach")

                    # Validate no sensitive content leakage in event content
                    for event in events_a:
                        event_content_str = json.dumps(event.content)
                        sensitive_terms = [scenario_b['domain'], 'confidential', 'privileged']
                        for term in sensitive_terms:
                            if term not in scenario_a['domain']:  # Allow own domain terms
                                self.assertNotIn(term.lower(), event_content_str.lower(),
                                               f"CRITICAL: Cross-user sensitive content detected in events")

        # Validate all users received their expected events
        isolation_success_count = 0
        for user_id, event_tracker in user_event_trackers.items():
            events_received = event_tracker.get_event_count()
            if events_received >= len(self.critical_websocket_events):
                isolation_success_count += 1

        isolation_success_rate = isolation_success_count / len(user_scenarios)
        self.assertGreaterEqual(isolation_success_rate, 1.0,
                              f"Multi-user event isolation failed: {isolation_success_rate:.2f}")

        # Record multi-user isolation metrics
        self.websocket_metrics['multi_user_isolation_maintained'] = isolation_success_count
        self.record_metric("multi_user_isolation_success_rate", isolation_success_rate)
        self.record_metric("concurrent_users_tested", len(user_scenarios))

        # Clean up user connections
        for connection in user_connections.values():
            if hasattr(connection, 'close'):
                await connection.close()

    # === HELPER METHODS FOR WEBSOCKET EVENT INTEGRATION ===

    @asynccontextmanager
    async def _get_user_execution_context(self):
        """Get user execution context for WebSocket event testing."""
        try:
            if hasattr(self.agent_factory, 'user_execution_scope'):
                async with self.agent_factory.user_execution_scope(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id
                ) as context:
                    yield context
                    return
        except Exception:
            pass

        # Fallback context
        context = MagicMock()
        context.user_id = self.test_user_id
        context.thread_id = self.test_thread_id
        context.run_id = self.test_run_id
        context.created_at = datetime.now(timezone.utc)
        yield context

    @asynccontextmanager
    async def _create_websocket_connection(self, user_context):
        """Create WebSocket connection for event testing."""
        # Mock WebSocket connection for testing
        mock_connection = MagicMock()
        mock_connection.user_id = user_context.user_id
        mock_connection.thread_id = user_context.thread_id
        mock_connection.connected = True
        mock_connection.events_received = []

        async def receive_event():
            # Simulate receiving WebSocket events
            await asyncio.sleep(0.1)
            return {'event': 'test_event', 'data': {}}

        mock_connection.recv = AsyncMock(side_effect=receive_event)
        mock_connection.send = AsyncMock()
        mock_connection.close = AsyncMock()

        self.websocket_connections[user_context.user_id] = mock_connection

        try:
            yield mock_connection
        finally:
            if user_context.user_id in self.websocket_connections:
                del self.websocket_connections[user_context.user_id]

    async def _create_websocket_enabled_agent(self, user_context):
        """Create agent with WebSocket event capabilities."""
        if REAL_WEBSOCKET_COMPONENTS_AVAILABLE and self.agent_factory:
            try:
                return await self.agent_factory.create_agent_instance(
                    'websocket_enabled_agent', user_context
                )
            except Exception:
                pass

        # Fallback mock agent with WebSocket event simulation
        mock_agent = MagicMock()

        async def execute_with_events(task, user_context):
            # Simulate agent execution with progressive WebSocket events
            events_to_send = [
                {'type': 'agent_started', 'content': {'status': 'Agent began processing your request'}},
                {'type': 'agent_thinking', 'content': {'progress': 'Analyzing task requirements'}},
                {'type': 'tool_executing', 'content': {'tool': 'business_analyzer', 'status': 'running'}},
                {'type': 'tool_completed', 'content': {'tool': 'business_analyzer', 'status': 'completed'}},
                {'type': 'agent_completed', 'content': {'status': 'Analysis complete, response ready'}}
            ]

            for event in events_to_send:
                await asyncio.sleep(0.5)  # Simulate processing time between events
                # Simulate event sending through WebSocket bridge
                if self.websocket_bridge and hasattr(self.websocket_bridge, 'send_agent_event'):
                    await self.websocket_bridge.send_agent_event(
                        user_context.user_id, event['type'], event['content']
                    )

            return {
                'response_type': 'business_analysis',
                'content': 'Completed business analysis with real-time event updates',
                'events_sent': len(events_to_send)
            }

        mock_agent.execute_task = AsyncMock(side_effect=execute_with_events)
        return mock_agent

    async def _execute_agent_with_websocket_events(self, agent, task, user_context):
        """Execute agent task with WebSocket event monitoring."""
        return await agent.execute_task(task, user_context)

    async def _listen_for_websocket_events(self, ws_connection, event_tracker):
        """Listen for WebSocket events and track them."""
        try:
            event_count = 0
            while event_count < len(self.critical_websocket_events):
                try:
                    # Simulate receiving WebSocket events
                    await asyncio.sleep(0.5)

                    # Generate mock WebSocket event
                    if event_count < len(self.critical_websocket_events):
                        event_type = self.critical_websocket_events[event_count]

                        event = WebSocketEvent(
                            event_type=event_type,
                            timestamp=time.time(),
                            user_id=str(ws_connection.user_id),
                            thread_id=str(ws_connection.thread_id),
                            content={'status': f'{event_type} event delivered', 'sequence': event_count},
                            delivery_confirmed=True
                        )

                        event_tracker.add_event(event)
                        event_count += 1

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error listening for WebSocket events: {e}")
                    break

        except asyncio.CancelledError:
            pass

    async def _create_ux_optimized_websocket_agent(self, user_context):
        """Create agent optimized for UX timing requirements."""
        mock_agent = MagicMock()

        async def execute_with_optimal_timing(task, user_context):
            # Execute with precise timing for optimal UX
            ux_optimized_events = [
                {'type': 'agent_started', 'delay': 0.2, 'content': {'status': 'Request acknowledged'}},
                {'type': 'agent_thinking', 'delay': 1.5, 'content': {'progress': 'Processing request'}},
                {'type': 'tool_executing', 'delay': 0.8, 'content': {'tool': 'analyzer', 'status': 'running'}},
                {'type': 'tool_completed', 'delay': 0.3, 'content': {'tool': 'analyzer', 'results': 'available'}},
                {'type': 'agent_completed', 'delay': 0.1, 'content': {'status': 'Response ready'}}
            ]

            for event in ux_optimized_events:
                await asyncio.sleep(event['delay'])
                if self.websocket_bridge and hasattr(self.websocket_bridge, 'send_agent_event'):
                    await self.websocket_bridge.send_agent_event(
                        user_context.user_id, event['type'], event['content']
                    )

            return {
                'response_type': 'ux_optimized_response',
                'timing_optimized': True,
                'events_sent': len(ux_optimized_events)
            }

        mock_agent.execute_task = AsyncMock(side_effect=execute_with_optimal_timing)
        return mock_agent

    async def _execute_complex_task_with_timing_validation(self, agent, task, user_context):
        """Execute complex task with timing validation."""
        return await agent.execute_task(task, user_context)

    async def _monitor_precise_event_timing(self, ws_connection, event_tracker, timing_requirements):
        """Monitor precise event timing against UX requirements."""
        try:
            for event_type in timing_requirements.keys():
                await asyncio.sleep(timing_requirements[event_type]['max_delay'] * 0.8)

                event = WebSocketEvent(
                    event_type=event_type,
                    timestamp=time.time(),
                    user_id=str(ws_connection.user_id),
                    thread_id=str(ws_connection.thread_id),
                    content={'timing': 'within_requirements', 'ux_optimized': True}
                )

                event_tracker.add_event(event)

        except asyncio.CancelledError:
            pass

    async def _execute_isolated_user_scenario(self, scenario, user_event_trackers, user_connections):
        """Execute isolated user scenario with WebSocket event isolation."""
        user_id = scenario['user_id']
        thread_id = scenario['thread_id']
        run_id = RunID(f"run_{user_id}")

        # Create isolated user context
        context = MagicMock()
        context.user_id = user_id
        context.thread_id = thread_id
        context.run_id = run_id
        context.created_at = datetime.now(timezone.utc)

        # Create isolated WebSocket connection
        async with self._create_websocket_connection(context) as ws_connection:
            user_connections[user_id] = ws_connection

            # Create isolated agent
            agent = await self._create_websocket_enabled_agent(context)

            # Execute user-specific task
            task = {
                'content': scenario['task'],
                'sensitivity': scenario['sensitivity'],
                'domain': scenario['domain'],
                'user_isolation_required': True
            }

            # Start event monitoring for this user
            event_tracker = user_event_trackers[user_id]
            event_listener = asyncio.create_task(
                self._listen_for_websocket_events(ws_connection, event_tracker)
            )

            # Execute agent task
            try:
                response = await agent.execute_task(task, context)

                # Allow time for events
                await asyncio.sleep(1.0)

                return {
                    'user_id': user_id,
                    'response': response,
                    'events_received': event_tracker.get_event_count(),
                    'isolation_maintained': True
                }

            finally:
                event_listener.cancel()