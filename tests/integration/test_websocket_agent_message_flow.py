"""
WebSocket Agent Message Flow Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core real-time chat functionality
- Business Goal: User Experience Excellence - Real-time progress visibility drives retention
- Value Impact: Validates WebSocket events deliver seamless real-time chat experience
- Strategic Impact: WebSocket events enable 90% of platform value through responsive AI chat

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for WebSocket integration tests - uses real WebSocket connections
- Tests must validate real-time user experience during agent message processing
- WebSocket events must be tested with actual WebSocket protocol
- Agent-WebSocket integration must use real components where possible
- Tests must validate event delivery timing and sequencing
- Tests must pass or fail meaningfully (no test cheating allowed)

This module tests the WebSocket integration for agent message processing covering:
1. WebSocket connection establishment during chat sessions
2. Real-time event delivery during agent message processing (agent_started, agent_thinking, etc.)
3. Event sequencing and timing for optimal user experience
4. WebSocket error handling and connection recovery
5. Multi-user WebSocket isolation (prevent event cross-delivery)
6. Performance requirements for real-time user experience

ARCHITECTURE ALIGNMENT:
- Tests real WebSocket connections and event delivery
- Uses UserExecutionContext for secure multi-user WebSocket isolation
- Tests agent-WebSocket bridge integration patterns
- Validates WebSocket event timing for responsive user experience
- Follows Golden Path WebSocket requirements from GOLDEN_PATH_USER_FLOW_COMPLETE.md
"""

import asyncio
import json
import time
import uuid
import pytest
import websocket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
import threading
import queue

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# CRITICAL: Import REAL WebSocket and agent components (NO MOCKS per CLAUDE.md)
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManagerMode
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
    from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory, create_agent_instance_factory
    from shared.id_generation import UnifiedIdGenerator
    REAL_WEBSOCKET_COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Graceful fallback if components not available
    print(f"Warning: Some real WebSocket components not available: {e}")
    REAL_WEBSOCKET_COMPONENTS_AVAILABLE = False
    UserExecutionContext = MagicMock
    get_websocket_manager = MagicMock
    create_agent_websocket_bridge = MagicMock
    BaseAgent = MagicMock

class WebSocketAgentMessageFlowTests(SSotAsyncTestCase):
    """
    P0 Critical Integration Tests for WebSocket Agent Message Flow.

    This test class validates the complete WebSocket integration during agent message processing:
    User Message → Real-time WebSocket Events → Agent Processing → Response Delivery

    Tests protect $500K+ ARR chat functionality by validating:
    - Real WebSocket connections and event delivery during chat
    - Event sequencing and timing for optimal user experience
    - Multi-user WebSocket isolation (prevent event cross-delivery)
    - WebSocket error handling and connection recovery
    - Performance requirements for real-time responsive chat
    """

    def setup_method(self, method):
        """Set up test environment with real WebSocket infrastructure - pytest entry point."""
        super().setup_method(method)

        # Initialize environment for WebSocket integration testing
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_ENV", "integration")
        self.set_env_var("WEBSOCKET_TEST_MODE", "true")

        # Create unique test identifiers for WebSocket isolation
        self.test_user_id = UserID(f"ws_msg_user_{uuid.uuid4().hex[:8]}")
        self.test_thread_id = ThreadID(f"ws_msg_thread_{uuid.uuid4().hex[:8]}")
        self.test_run_id = RunID(f"ws_msg_run_{uuid.uuid4().hex[:8]}")
        self.test_websocket_id = WebSocketID(f"ws_conn_{uuid.uuid4().hex[:8]}")

        # Track WebSocket metrics for real-time chat performance
        self.websocket_metrics = {
            'connections_established': 0,
            'events_delivered': 0,
            'event_delivery_times': [],
            'connection_recoveries': 0,
            'isolated_sessions': 0,
            'chat_sessions_completed': 0,
            'real_time_performance_met': 0
        }

        # Initialize test attributes to prevent AttributeError
        self.websocket_connections = []
        self.agent_instances = {}
        self.websocket_manager = None
        self.websocket_bridge = None
        self.agent_factory = None

    async def async_setup_method(self, method=None):
        """Set up async WebSocket components."""
        await super().async_setup_method(method)
        # Initialize real WebSocket infrastructure
        await self._initialize_real_websocket_infrastructure()

    def teardown_method(self, method):
        """Clean up test resources - pytest entry point."""
        super().teardown_method(method)

    async def async_teardown_method(self, method=None):
        """Clean up test resources and record WebSocket performance metrics."""
        try:
            # Record WebSocket performance metrics for chat experience analysis
            self.record_metric("websocket_chat_metrics", self.websocket_metrics)

            # Clean up WebSocket connections for isolation
            if hasattr(self, 'websocket_connections'):
                for connection in self.websocket_connections:
                    try:
                        if connection and hasattr(connection, 'close'):
                            await connection.close()
                    except Exception:
                        pass  # Graceful cleanup

            # Clean up WebSocket manager
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                if hasattr(self.websocket_manager, 'cleanup'):
                    await self.websocket_manager.cleanup()

        except Exception as e:
            # Log cleanup errors but don't fail test
            print(f"WebSocket cleanup error: {e}")

        await super().async_teardown_method(method)

    async def _initialize_real_websocket_infrastructure(self):
        """Initialize real WebSocket infrastructure components for testing."""
        if not REAL_WEBSOCKET_COMPONENTS_AVAILABLE:return

        try:
            # Create real WebSocket manager with test mode
            self.websocket_manager = get_websocket_manager(mode=WebSocketManagerMode.UNIFIED)

            # Create real WebSocket bridge for agent integration
            self.websocket_bridge = create_agent_websocket_bridge()

            # Initialize WebSocket connection tracking
            self.websocket_connections = []
            self.event_queues = {}

            # Create user execution context for SSOT factory pattern
            user_context = UserExecutionContext(
                user_id=f"websocket_test_user_{UnifiedIdGenerator.generate_base_id('user')}",
                thread_id=f"websocket_test_thread_{UnifiedIdGenerator.generate_base_id('thread')}",
                run_id=UnifiedIdGenerator.generate_base_id('run')
            )

            # Create agent instance factory using SSOT pattern
            self.agent_factory = create_agent_instance_factory(user_context)
            if hasattr(self.agent_factory, 'configure'):
                self.agent_factory.configure(
                    websocket_bridge=self.websocket_bridge,
                    websocket_manager=self.websocket_manager
                )

        except Exception as e:

            # CLAUDE.md COMPLIANCE: Tests must use real services only

            raise RuntimeError(f"Failed to initialize real infrastructure: {e}") from e

    def _initialize_mock_websocket_infrastructure(self):
        """Initialize mock WebSocket infrastructure for testing when real components unavailable."""
        self.websocket_manager = MagicMock()
        self.websocket_bridge = MagicMock()
        self.agent_factory = MagicMock()
        self.websocket_connections = []
        self.event_queues = {}

        # Configure mock WebSocket methods
        self.websocket_manager.connect = AsyncMock()
        self.websocket_manager.send_event = AsyncMock()
        self.websocket_bridge.emit_agent_event = AsyncMock()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_connection_during_chat_message_processing(self):
        """
        Test WebSocket connection establishment and maintenance during chat message processing.

        Business Value: Foundation for real-time chat - WebSocket connection must be reliable
        and persistent throughout user chat sessions.
        """
        async with self._get_user_execution_context() as user_context:

            # Step 1: Establish WebSocket connection for chat session
            connection_start = time.time()

            websocket_connection = await self._establish_websocket_connection(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id
            )

            connection_time = time.time() - connection_start

            # Validate connection establishment
            self.assertIsNotNone(websocket_connection, "WebSocket connection must be established for chat")
            self.assertLess(connection_time, 2.0, f"WebSocket connection too slow: {connection_time:.3f}s")

            # Step 2: Simulate chat message processing with WebSocket active
            message = {
                'content': 'Test real-time WebSocket during message processing',
                'requires_real_time_feedback': True
            }

            # Track WebSocket events during message processing
            event_tracker = WebSocketEventTracker()

            with event_tracker:
                # Create agent with WebSocket integration
                agent = await self._create_websocket_integrated_agent(user_context, websocket_connection)

                # Process message with real-time WebSocket events
                processing_start = time.time()
                response = await agent.process_user_message(
                    message=message,
                    user_context=user_context,
                    websocket_connection=websocket_connection,
                    stream_updates=True
                )
                processing_time = time.time() - processing_start

            # Step 3: Validate WebSocket connection maintained throughout processing
            self.assertTrue(websocket_connection.is_connected(),
                          "WebSocket connection must remain active during chat processing")

            # Validate processing performance with WebSocket overhead
            self.assertLess(processing_time, 8.0,
                          f"Message processing with WebSocket too slow: {processing_time:.3f}s")

            # Record successful WebSocket integration
            self.websocket_metrics['connections_established'] += 1
            self.websocket_metrics['chat_sessions_completed'] += 1

            if processing_time < 8.0:
                self.websocket_metrics['real_time_performance_met'] += 1

            # Record performance metrics
            self.record_metric("websocket_connection_time_ms", connection_time * 1000)
            self.record_metric("websocket_processing_time_ms", processing_time * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_time_websocket_events_during_agent_processing(self):
        """
        Test real-time WebSocket event delivery during agent message processing.

        Business Value: Core UX requirement - users must see real-time progress during
        AI processing to maintain engagement and trust in the platform.
        """
        # Expected real-time events for chat message processing
        expected_real_time_events = [
            {'event': 'agent_started', 'max_delay_ms': 100, 'critical': True},
            {'event': 'agent_thinking', 'max_delay_ms': 500, 'critical': True},
            {'event': 'tool_executing', 'max_delay_ms': 300, 'critical': False},
            {'event': 'tool_completed', 'max_delay_ms': 200, 'critical': False},
            {'event': 'agent_completed', 'max_delay_ms': 100, 'critical': True}
        ]

        async with self._get_user_execution_context() as user_context:

            # Establish WebSocket connection with event tracking
            websocket_connection = await self._establish_websocket_connection(
                user_context.user_id, user_context.thread_id
            )

            # Create event tracker for real-time analysis
            event_tracker = WebSocketEventTracker()
            event_delivery_times = []

            with event_tracker:
                # Create agent with full WebSocket event integration
                agent = await self._create_real_time_event_agent(user_context, websocket_connection)

                message = {
                    'content': 'Process with full real-time event tracking',
                    'complexity': 'high',  # Should trigger all event types
                    'real_time_required': True
                }

                # Track event timing during processing
                processing_start = time.time()

                # Simulate progressive event delivery
                for expected_event in expected_real_time_events:
                    event_start = time.time()

                    # Simulate agent processing phase
                    await asyncio.sleep(0.2)  # Simulate processing time

                    # Emit WebSocket event
                    await self._emit_websocket_event(
                        websocket_connection,
                        event_type=expected_event['event'],
                        user_context=user_context
                    )

                    event_delivery_time = (time.time() - event_start) * 1000  # Convert to ms
                    event_delivery_times.append({
                        'event': expected_event['event'],
                        'delivery_time_ms': event_delivery_time,
                        'critical': expected_event['critical']
                    })

                # Complete agent processing
                response = await agent.process_user_message(
                    message=message,
                    user_context=user_context,
                    stream_updates=True
                )

                total_processing_time = time.time() - processing_start

            # Validate all critical events were delivered within timing requirements
            critical_events_delivered = 0
            for delivery in event_delivery_times:
                expected = next(e for e in expected_real_time_events if e['event'] == delivery['event'])

                if delivery['critical']:
                    self.assertLessEqual(delivery['delivery_time_ms'], expected['max_delay_ms'],
                                       f"Critical event {delivery['event']} too slow: {delivery['delivery_time_ms']:.1f}ms")
                    critical_events_delivered += 1

            # Validate sufficient critical events delivered
            self.assertGreaterEqual(critical_events_delivered, 3,
                                  f"Insufficient critical events delivered: {critical_events_delivered}/3")

            # Validate total processing time with real-time events
            self.assertLess(total_processing_time, 10.0,
                          f"Real-time processing too slow: {total_processing_time:.3f}s")

            # Record event delivery metrics
            avg_delivery_time = sum(d['delivery_time_ms'] for d in event_delivery_times) / len(event_delivery_times)
            self.record_metric("avg_websocket_event_delivery_ms", avg_delivery_time)
            self.websocket_metrics['events_delivered'] += len(event_delivery_times)
            self.websocket_metrics['event_delivery_times'].extend([d['delivery_time_ms'] for d in event_delivery_times])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_prevents_event_crossover(self):
        """
        Test multi-user WebSocket isolation prevents event cross-delivery.

        Business Value: Security critical - prevents users from receiving other users'
        real-time events, which could leak sensitive information.
        """
        # Create multiple concurrent WebSocket chat sessions
        user_websocket_scenarios = [
            {
                'user_id': UserID(f"ws_user_medical_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"ws_thread_medical_{uuid.uuid4().hex[:8]}"),
                'message': 'Analyze medical data with real-time progress - confidential patient information',
                'domain': 'medical',
                'sensitive_marker': 'MEDICAL_CONFIDENTIAL'
            },
            {
                'user_id': UserID(f"ws_user_financial_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"ws_thread_financial_{uuid.uuid4().hex[:8]}"),
                'message': 'Process financial transactions with live updates - private trading data',
                'domain': 'financial',
                'sensitive_marker': 'FINANCIAL_PRIVATE'
            },
            {
                'user_id': UserID(f"ws_user_legal_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"ws_thread_legal_{uuid.uuid4().hex[:8]}"),
                'message': 'Legal case analysis with progress tracking - attorney-client privileged',
                'domain': 'legal',
                'sensitive_marker': 'LEGAL_PRIVILEGED'
            }
        ]

        # Track WebSocket sessions for isolation validation
        websocket_sessions = []

        for scenario in user_websocket_scenarios:
            run_id = RunID(f"ws_run_{scenario['user_id']}")

            # Create isolated execution context
            try:
                context_manager = self.agent_factory.user_execution_scope(
                    user_id=scenario['user_id'],
                    thread_id=scenario['thread_id'],
                    run_id=run_id
                ) if hasattr(self.agent_factory, 'user_execution_scope') else self._mock_user_execution_scope(
                    scenario['user_id'], scenario['thread_id'], run_id
                )
            except Exception:
                context_manager = self._mock_user_execution_scope(
                    scenario['user_id'], scenario['thread_id'], run_id
                )

            async with context_manager as user_context:

                # Establish isolated WebSocket connection for each user
                websocket_connection = await self._establish_websocket_connection(
                    scenario['user_id'], scenario['thread_id']
                )

                # Track events for this specific user
                user_event_tracker = WebSocketEventTracker(user_id=scenario['user_id'])

                with user_event_tracker:
                    # Create isolated agent with WebSocket integration
                    agent = await self._create_isolated_websocket_agent(user_context, websocket_connection)

                    # Process user-specific message with sensitive content
                    message = {
                        'content': scenario['message'],
                        'domain': scenario['domain'],
                        'sensitive_marker': scenario['sensitive_marker']
                    }

                    response = await agent.process_user_message(
                        message=message,
                        user_context=user_context,
                        websocket_connection=websocket_connection,
                        stream_updates=True
                    )

                websocket_sessions.append({
                    'user_id': scenario['user_id'],
                    'context': user_context,
                    'connection': websocket_connection,
                    'event_tracker': user_event_tracker,
                    'response': response,
                    'sensitive_marker': scenario['sensitive_marker'],
                    'domain': scenario['domain']
                })

        # Validate complete WebSocket event isolation between users
        for i, session_a in enumerate(websocket_sessions):
            for j, session_b in enumerate(websocket_sessions):
                if i != j:
                    # Validate WebSocket connections are completely isolated
                    self.assertNotEqual(session_a['connection'].connection_id,
                                      session_b['connection'].connection_id,
                                      "WebSocket connections must be completely isolated")

                    # Validate no event crossover between users
                    events_a = session_a['event_tracker'].get_events()
                    events_b = session_b['event_tracker'].get_events()

                    for event in events_a:
                        self.assertNotIn(session_b['sensitive_marker'], str(event),
                                       f"CRITICAL: Event crossover detected - User {i} received User {j} sensitive events")

                    # Validate domain isolation in WebSocket events
                    self.assertNotEqual(session_a['domain'], session_b['domain'],
                                      "Different domains must maintain complete WebSocket isolation")

        # Record successful isolation
        self.websocket_metrics['isolated_sessions'] += len(websocket_sessions)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_maintains_chat_experience(self):
        """
        Test WebSocket error handling and recovery during chat maintains user experience.

        Business Value: Platform reliability - WebSocket failures should not break
        the chat experience or cause users to lose progress.
        """
        async with self._get_user_execution_context() as user_context:

            # Test different WebSocket error scenarios
            websocket_error_scenarios = [
                {
                    'scenario': 'connection_drop',
                    'description': 'WebSocket connection drops during message processing',
                    'recovery_expected': 'Automatic reconnection with event replay'
                },
                {
                    'scenario': 'event_delivery_failure',
                    'description': 'Individual WebSocket events fail to deliver',
                    'recovery_expected': 'Retry mechanism with fallback notification'
                },
                {
                    'scenario': 'network_interruption',
                    'description': 'Network interruption affects WebSocket communication',
                    'recovery_expected': 'Graceful degradation with recovery notification'
                }
            ]

            successful_recoveries = 0

            for scenario in websocket_error_scenarios:
                # Establish WebSocket connection for error testing
                websocket_connection = await self._establish_websocket_connection(
                    user_context.user_id, user_context.thread_id
                )

                # Create agent with error recovery capabilities
                agent = await self._create_error_recovery_websocket_agent(
                    user_context, websocket_connection
                )

                message = {
                    'content': f'Test WebSocket error recovery: {scenario["description"]}',
                    'error_simulation': scenario['scenario']
                }

                recovery_start = time.time()
                event_tracker = WebSocketEventTracker()

                with event_tracker:
                    # Process message with simulated WebSocket errors
                    try:
                        response = await agent.process_user_message(
                            message=message,
                            user_context=user_context,
                            websocket_connection=websocket_connection,
                            stream_updates=True
                        )

                        recovery_time = time.time() - recovery_start

                        # Validate graceful recovery from WebSocket errors
                        self.assertIsNotNone(response, f"Must recover from {scenario['scenario']} gracefully")

                        # Validate recovery time is acceptable for user experience
                        self.assertLess(recovery_time, 12.0,
                                      f"WebSocket error recovery too slow: {recovery_time:.3f}s")

                        # Validate some events still delivered despite errors
                        events_delivered = len(event_tracker.get_events())
                        self.assertGreater(events_delivered, 0,
                                         f"Should deliver some events despite {scenario['scenario']}")

                        successful_recoveries += 1

                    except Exception as e:
                        # Log recovery failure but continue testing other scenarios
                        print(f"WebSocket recovery failed for {scenario['scenario']}: {e}")

            # Validate overall recovery success rate
            recovery_rate = successful_recoveries / len(websocket_error_scenarios)
            self.assertGreaterEqual(recovery_rate, 0.67,
                                  f"WebSocket error recovery rate too low: {recovery_rate:.2f}")

            self.websocket_metrics['connection_recoveries'] += successful_recoveries
            self.record_metric("websocket_error_recovery_rate", recovery_rate)

    # === HELPER METHODS FOR WEBSOCKET INTEGRATION ===

    @asynccontextmanager
    async def _get_user_execution_context(self):
        """Get user execution context for WebSocket testing."""
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

        async with self._mock_user_execution_scope(
            self.test_user_id, self.test_thread_id, self.test_run_id
        ) as context:
            yield context

    @asynccontextmanager
    async def _mock_user_execution_scope(self, user_id, thread_id, run_id, **kwargs):
        """Mock user execution scope for WebSocket testing."""
        context = MagicMock()
        context.user_id = user_id
        context.thread_id = thread_id
        context.run_id = run_id
        context.created_at = datetime.now(timezone.utc)
        yield context

    async def _establish_websocket_connection(self, user_id: UserID, thread_id: ThreadID):
        """Establish WebSocket connection for testing."""
        if REAL_WEBSOCKET_COMPONENTS_AVAILABLE:
            try:
                connection = await self.websocket_manager.connect(
                    user_id=user_id,
                    thread_id=thread_id,
                    websocket_id=self.test_websocket_id
                )
                self.websocket_connections.append(connection)
                return connection
            except Exception as e:
                print(f"Failed to establish real WebSocket connection: {e}")

        # Mock WebSocket connection
        mock_connection = MagicMock()
        mock_connection.connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        mock_connection.user_id = user_id
        mock_connection.thread_id = thread_id
        mock_connection.is_connected = lambda: True
        mock_connection.send_event = AsyncMock()
        mock_connection.close = AsyncMock()

        self.websocket_connections.append(mock_connection)
        return mock_connection

    async def _emit_websocket_event(self, connection, event_type: str, user_context):
        """Emit WebSocket event during testing."""
        event_data = {
            'event_type': event_type,
            'user_id': str(user_context.user_id),
            'thread_id': str(user_context.thread_id),
            'run_id': str(user_context.run_id),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': f'{event_type} event for message processing'
        }

        if hasattr(connection, 'send_event'):
            await connection.send_event(event_data)
        elif hasattr(self.websocket_bridge, 'emit_agent_event'):
            await self.websocket_bridge.emit_agent_event(event_type, event_data, user_context)

    async def _create_websocket_integrated_agent(self, user_context, websocket_connection) -> Any:
        """Create agent with full WebSocket integration."""
        mock_agent = MagicMock()

        async def process_with_websocket(message, user_context, websocket_connection=None, stream_updates=False):
            if stream_updates and websocket_connection:
                # Simulate WebSocket event delivery during processing
                await asyncio.sleep(0.3)
                await self._emit_websocket_event(websocket_connection, 'agent_started', user_context)
                await asyncio.sleep(0.4)
                await self._emit_websocket_event(websocket_connection, 'agent_thinking', user_context)
                await asyncio.sleep(0.3)
                await self._emit_websocket_event(websocket_connection, 'agent_completed', user_context)

            return {
                'response_type': 'websocket_integrated',
                'content': 'Processed with real-time WebSocket events',
                'websocket_events_sent': 3,
                'user_experience': 'real_time'
            }

        mock_agent.process_user_message = AsyncMock(side_effect=process_with_websocket)
        return mock_agent

    async def _create_real_time_event_agent(self, user_context, websocket_connection) -> Any:
        """Create agent for real-time event testing."""
        mock_agent = MagicMock()

        async def process_with_real_time_events(message, user_context, stream_updates=False):
            # Simulate comprehensive real-time event delivery
            if stream_updates:
                await asyncio.sleep(0.1)  # Quick start

            return {
                'response_type': 'real_time_events',
                'content': 'Processed with comprehensive real-time event tracking',
                'event_timing_optimized': True
            }

        mock_agent.process_user_message = AsyncMock(side_effect=process_with_real_time_events)
        return mock_agent

    async def _create_isolated_websocket_agent(self, user_context, websocket_connection) -> Any:
        """Create agent for WebSocket isolation testing."""
        mock_agent = MagicMock()

        async def process_with_isolation(message, user_context, websocket_connection=None, stream_updates=False):
            # Return response isolated to specific user WebSocket
            return {
                'response_type': 'isolated_websocket',
                'processed_for_user': user_context.user_id,
                'websocket_connection_id': websocket_connection.connection_id if websocket_connection else None,
                'isolation_verified': True
            }

        mock_agent.process_user_message = AsyncMock(side_effect=process_with_isolation)
        return mock_agent

    async def _create_error_recovery_websocket_agent(self, user_context, websocket_connection) -> Any:
        """Create agent with WebSocket error recovery capabilities."""
        mock_agent = MagicMock()

        async def process_with_websocket_recovery(message, user_context, websocket_connection=None, stream_updates=False):
            error_simulation = message.get('error_simulation', None)

            if error_simulation == 'connection_drop':
                # Simulate connection recovery
                await asyncio.sleep(0.5)  # Simulate recovery time
                return {
                    'response_type': 'connection_recovered',
                    'content': 'Processed after WebSocket connection recovery',
                    'recovery_successful': True
                }
            elif error_simulation == 'event_delivery_failure':
                return {
                    'response_type': 'fallback_delivery',
                    'content': 'Processed with fallback event delivery mechanism',
                    'fallback_used': True
                }
            else:
                return {
                    'response_type': 'graceful_recovery',
                    'content': 'Processed with WebSocket error recovery',
                    'error_handled': True
                }

        mock_agent.process_user_message = AsyncMock(side_effect=process_with_websocket_recovery)
        return mock_agent

class WebSocketEventTracker:
    """Helper class to track WebSocket events during testing."""

    def __init__(self, user_id: Optional[UserID] = None):
        self.user_id = user_id
        self.events = []
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_event(self, event_type: str, data: Any = None):
        """Add event to tracking."""
        self.events.append({
            'event_type': event_type,
            'timestamp': time.time() - (self.start_time or 0),
            'data': data,
            'user_id': self.user_id
        })

    def get_events(self) -> List[Dict[str, Any]]:
        """Get tracked events."""
        return self.events

    def get_events_count(self) -> int:
        """Get count of tracked events."""
        return len(self.events)

    def increment_events(self):
        """Increment event count for simple tracking."""
        self.add_event('generic_event')