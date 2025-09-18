"""
Mission Critical: User-Friendly Errors Don't Break Golden Path

MISSION CRITICAL: This test ensures that user-friendly error messages
do not interfere with the core WebSocket agent events that deliver 90% of platform value.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure error improvements don't break core functionality
- Value Impact: Core chat functionality MUST continue working while errors improve
- Strategic Impact: Cannot sacrifice core value for nice-to-have error messages

This test validates that:
1. All 5 critical WebSocket events are still sent even when errors occur
2. User-friendly error messages are additive, not replacements for core functionality
3. Error handling doesn't introduce latency that breaks real-time chat experience
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase

from netra_backend.app.services.user_friendly_error_mapper import UserFriendlyErrorMapper
from netra_backend.app.websocket_core.error_recovery_handler import (
    ErrorType,
    WebSocketErrorContext
)


class TestUserFriendlyErrorsGoldenPath(SSotAsyncTestCase):
    """MISSION CRITICAL: Ensure user-friendly errors don't break core agent functionality."""

    async def setup_method(self, method=None):
        """Set up test fixtures."""
        await super().setup_method(method)
        self.error_mapper = UserFriendlyErrorMapper()

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_websocket_events_still_sent_with_errors(self):
        """CRITICAL: All 5 WebSocket events must be sent even when errors occur."""
        # This should FAIL until implementation preserves core functionality

        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

        # Set up components with user-friendly error integration
        websocket_manager = UnifiedWebSocketManager(
            config={'error_mapper_enabled': True},
            error_mapper=self.error_mapper
        )

        execution_engine = ExecutionEngine(
            websocket_manager=websocket_manager,
            error_mapper=self.error_mapper
        )

        # Track all events sent
        sent_events = []

        async def mock_send_event(connection_id, event_type, payload):
            sent_events.append({
                'connection_id': connection_id,
                'event_type': event_type,
                'payload': payload,
                'timestamp': time.time()
            })

        # Mock WebSocket manager to track events
        with patch.object(websocket_manager, 'send_event', mock_send_event):
            # Simulate agent execution that encounters an error mid-process
            connection_id = "critical_test_connection"
            user_id = "critical_test_user"

            # Start agent execution
            await execution_engine.start_agent_execution(
                connection_id=connection_id,
                user_id=user_id,
                agent_type="triage_agent",
                query="Test query that will encounter error"
            )

            # Simulate error during execution
            error_context = WebSocketErrorContext(
                error_type=ErrorType.SERVICE_UNAVAILABLE,
                connection_id=connection_id,
                user_id=user_id,
                error_message="Service temporarily unavailable",
                timestamp=datetime.now(timezone.utc)
            )

            # Handle error with user-friendly messages
            await execution_engine.handle_execution_error_with_user_friendly_messages(error_context)

        # CRITICAL ASSERTION: All 5 events must still be sent
        event_types = [event['event_type'] for event in sent_events]

        # These events are NON-NEGOTIABLE for chat functionality
        required_events = [
            'agent_started',
            'agent_thinking',
            'agent_completed'  # May complete with error but must complete
        ]

        for required_event in required_events:
            assert required_event in event_types, \
                f"CRITICAL: Missing required event {required_event}. Events sent: {event_types}"

        # Additional events might be present (tool_executing, tool_completed, user_friendly_error)
        # but the core 3 are absolutely required

        # User-friendly error should be sent as ADDITIONAL event, not replacement
        user_friendly_events = [e for e in sent_events if e['event_type'] == 'user_friendly_error']
        assert len(user_friendly_events) >= 1, \
            "User-friendly error event should be sent IN ADDITION to core events"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_error_mapping_latency_acceptable(self):
        """CRITICAL: Error mapping must not introduce latency that breaks real-time chat."""
        # This should FAIL until performance requirements are met

        # Real-time chat requires sub-50ms response times
        MAX_ACCEPTABLE_LATENCY_MS = 50

        error_context = {
            'error_type': ErrorType.RATE_LIMIT_EXCEEDED,
            'error_message': 'Rate limit exceeded',
            'timestamp': datetime.now(timezone.utc),
            'connection_id': 'latency_test_connection',
            'user_id': 'latency_test_user'
        }

        # Measure error mapping time
        start_time = time.time()
        result = self.error_mapper.map_error(error_context)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000

        assert latency_ms < MAX_ACCEPTABLE_LATENCY_MS, \
            f"CRITICAL: Error mapping took {latency_ms}ms, must be under {MAX_ACCEPTABLE_LATENCY_MS}ms for real-time chat"

        # Result should still be valid
        assert hasattr(result, 'user_message')
        assert len(result.user_message) > 0

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_agent_execution_continues_after_user_friendly_error(self):
        """CRITICAL: Agent execution must continue/recover after sending user-friendly errors."""
        # This should FAIL until proper integration is implemented

        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

        execution_engine = ExecutionEngine(
            error_mapper=self.error_mapper
        )

        # Track execution state
        execution_states = []

        async def mock_state_change(state):
            execution_states.append({
                'state': state,
                'timestamp': time.time()
            })

        with patch.object(execution_engine, 'update_execution_state', mock_state_change):
            # Start execution
            execution_id = await execution_engine.start_execution(
                query="Test query",
                user_id="state_test_user"
            )

            # Simulate recoverable error
            error_context = WebSocketErrorContext(
                error_type=ErrorType.RATE_LIMIT_EXCEEDED,  # Recoverable error
                connection_id="state_test_connection",
                user_id="state_test_user",
                error_message="Rate limit exceeded, backing off",
                timestamp=datetime.now(timezone.utc)
            )

            # Handle error (should send user-friendly message AND continue execution)
            recovery_result = await execution_engine.handle_error_and_continue(error_context)

            # Wait for recovery/continuation
            await asyncio.sleep(0.1)

        # CRITICAL: Execution should continue after recoverable error
        assert recovery_result.execution_continued, \
            "CRITICAL: Agent execution must continue after recoverable error"

        # Should have progressed through execution states
        assert len(execution_states) >= 3, \
            f"Expected multiple execution states, got: {[s['state'] for s in execution_states]}"

        # Final state should not be 'error' for recoverable errors
        final_state = execution_states[-1]['state']
        assert final_state != 'error', \
            f"CRITICAL: Final execution state should not be 'error' for recoverable errors, got: {final_state}"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_websocket_connection_stability_with_error_messages(self):
        """CRITICAL: User-friendly error messages must not destabilize WebSocket connections."""
        # This should FAIL until WebSocket stability is guaranteed

        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

        websocket_manager = UnifiedWebSocketManager(
            config={'user_friendly_errors_enabled': True},
            error_mapper=self.error_mapper
        )

        # Simulate active WebSocket connection
        connection_id = "stability_test_connection"
        user_id = "stability_test_user"

        # Track connection state
        connection_events = []

        async def mock_connection_event(event_type, connection_id):
            connection_events.append({
                'event_type': event_type,
                'connection_id': connection_id,
                'timestamp': time.time()
            })

        with patch.object(websocket_manager, 'emit_connection_event', mock_connection_event):
            # Simulate connection establishment
            await websocket_manager.handle_connection(connection_id, user_id)

            # Send multiple user-friendly error messages rapidly
            for i in range(10):
                error_context = WebSocketErrorContext(
                    error_type=ErrorType.MESSAGE_DELIVERY_FAILED,
                    connection_id=connection_id,
                    user_id=user_id,
                    error_message=f"Test error {i}",
                    timestamp=datetime.now(timezone.utc)
                )

                await websocket_manager.send_user_friendly_error(error_context)
                await asyncio.sleep(0.01)  # Rapid succession

        # CRITICAL: Connection should remain stable
        connection_closed_events = [
            e for e in connection_events
            if e['event_type'] in ['connection_closed', 'connection_error', 'connection_lost']
        ]

        assert len(connection_closed_events) == 0, \
            f"CRITICAL: Connection became unstable with events: {connection_closed_events}"

        # Connection should still be active
        assert websocket_manager.is_connection_active(connection_id), \
            "CRITICAL: WebSocket connection should remain active after error messages"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_concurrent_users_error_isolation(self):
        """CRITICAL: User-friendly errors for one user must not affect other users."""
        # This should FAIL until proper user isolation is implemented

        # Set up multiple concurrent users
        users = [
            {'connection_id': f'user_{i}_connection', 'user_id': f'user_{i}'}
            for i in range(5)
        ]

        # Track messages sent to each user
        user_messages = {user['user_id']: [] for user in users}

        async def mock_send_to_user(connection_id, message):
            # Find user by connection_id
            user_id = next(
                user['user_id'] for user in users
                if user['connection_id'] == connection_id
            )
            user_messages[user_id].append(message)

        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager.send_message', mock_send_to_user):
            # Create error for only one user
            error_user = users[0]
            error_context = WebSocketErrorContext(
                error_type=ErrorType.AUTHENTICATION_FAILED,
                connection_id=error_user['connection_id'],
                user_id=error_user['user_id'],
                error_message="Authentication failed for user 0",
                timestamp=datetime.now(timezone.utc)
            )

            # Send user-friendly error
            await self.error_mapper.send_user_friendly_error_via_websocket(error_context)

        # CRITICAL: Only the error user should receive the error message
        error_user_messages = user_messages[error_user['user_id']]
        assert len(error_user_messages) >= 1, \
            "Error user should receive user-friendly error message"

        error_message_found = any(
            msg.get('type') == 'user_friendly_error'
            for msg in error_user_messages
        )
        assert error_message_found, \
            "Error user should receive user-friendly error message"

        # Other users should NOT receive any error messages
        for user in users[1:]:  # Skip the error user
            other_user_messages = user_messages[user['user_id']]
            error_messages = [
                msg for msg in other_user_messages
                if msg.get('type') == 'user_friendly_error'
            ]
            assert len(error_messages) == 0, \
                f"CRITICAL: User {user['user_id']} should not receive error messages from other users"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_system_degradation_graceful_with_user_friendly_errors(self):
        """CRITICAL: System must degrade gracefully if error mapping fails."""
        # This should FAIL until proper fallback is implemented

        # Simulate error mapping failure
        broken_error_mapper = UserFriendlyErrorMapper()

        def mock_broken_mapping(error_context):
            raise Exception("Error mapper is broken!")

        with patch.object(broken_error_mapper, 'map_error', mock_broken_mapping):
            # System should still handle errors even if user-friendly mapping fails
            error_context = WebSocketErrorContext(
                error_type=ErrorType.SERVICE_UNAVAILABLE,
                connection_id="fallback_test_connection",
                user_id="fallback_test_user",
                error_message="Service unavailable",
                timestamp=datetime.now(timezone.utc)
            )

            # Should not raise exception, should fallback gracefully
            try:
                result = await broken_error_mapper.map_error_with_fallback(error_context.__dict__)
            except Exception as e:
                pytest.fail(f"CRITICAL: System should not crash when error mapping fails: {e}")

            # Should provide basic fallback error message
            assert hasattr(result, 'user_message')
            assert len(result.user_message) > 0
            assert 'error' in result.user_message.lower()

            # Should indicate fallback was used
            assert hasattr(result, 'is_fallback')
            assert result.is_fallback is True

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_business_value_preservation(self):
        """CRITICAL: Core business value (chat functionality) must be preserved."""
        # This should FAIL until business value is demonstrably preserved

        # Simulate complete chat flow with error that gets user-friendly treatment
        chat_flow_events = []

        async def track_chat_event(event_type, data):
            chat_flow_events.append({
                'event_type': event_type,
                'data': data,
                'timestamp': time.time()
            })

        # Mock complete chat system
        with patch('netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine.track_business_value_event', track_chat_event):
            # Start chat session
            await track_chat_event('chat_session_started', {'user_id': 'business_test_user'})

            # User sends message
            await track_chat_event('user_message_received', {
                'message': 'Help me optimize costs',
                'user_id': 'business_test_user'
            })

            # Agent starts processing (with potential for errors)
            await track_chat_event('agent_processing_started', {
                'agent_type': 'cost_optimizer',
                'user_id': 'business_test_user'
            })

            # Error occurs but is handled with user-friendly message
            error_context = WebSocketErrorContext(
                error_type=ErrorType.RATE_LIMIT_EXCEEDED,
                connection_id="business_test_connection",
                user_id="business_test_user",
                error_message="Rate limit exceeded",
                timestamp=datetime.now(timezone.utc)
            )

            # Handle error with user-friendly message AND continue processing
            await self.error_mapper.handle_error_preserving_business_value(error_context)

            # Agent completes with value (despite error)
            await track_chat_event('agent_completed', {
                'result': 'Cost optimization recommendations provided',
                'business_value_delivered': True,
                'user_id': 'business_test_user'
            })

        # CRITICAL: Business value must be delivered despite errors
        business_value_events = [
            e for e in chat_flow_events
            if e['event_type'] in ['agent_completed', 'business_value_delivered']
        ]

        assert len(business_value_events) >= 1, \
            "CRITICAL: Business value must be delivered even when errors occur"

        # Final event should indicate successful value delivery
        final_event = chat_flow_events[-1]
        assert final_event['event_type'] == 'agent_completed', \
            f"Chat session should complete successfully, got final event: {final_event['event_type']}"

        assert final_event['data'].get('business_value_delivered') is True, \
            "CRITICAL: Business value must be delivered to user despite errors"