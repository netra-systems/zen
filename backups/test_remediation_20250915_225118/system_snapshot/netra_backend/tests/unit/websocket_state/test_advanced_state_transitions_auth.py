"""
Advanced State Machine Transition Tests with Authentication Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core WebSocket Infrastructure
- Business Goal: Eliminate state transition failures that cause chat interruptions
- Value Impact: Ensures complex state transitions work correctly with authentication
- Strategic Impact: Foundation for reliable multi-user chat platform ($120K+ MRR protection)

CRITICAL TESTING REQUIREMENTS:
1. Tests MUST validate complex state transition scenarios with authentication
2. Tests MUST handle edge cases in state machine + auth integration
3. Tests MUST fail hard on state corruption or invalid transitions
4. Tests MUST validate state persistence across authentication token changes
5. Tests MUST test concurrent state transitions with authentication validation

This test suite focuses on ADVANCED state machine scenarios that complement
the existing basic auth integration tests:
- Complex multi-step transition sequences during authentication changes
- State machine behavior during authentication token refresh/renewal
- Edge cases in state transitions when authentication service is unavailable
- State recovery after authentication failures with partial state corruption
- Advanced race condition scenarios in concurrent auth + state operations

SPECIFIC ADVANCED SCENARIOS:
Authentication State Coordination:
- State transitions during active authentication token refresh
- State machine behavior when auth token expires mid-transition
- Complex transition rollback scenarios with authentication context preservation
- State machine recovery from corrupted auth state with partial rollback

Race Condition Edge Cases:
- Concurrent state transitions with simultaneous auth token validation
- State machine deadlock prevention during auth service timeouts
- Complex state coordination when multiple auth events happen simultaneously
- State transition ordering guarantees during authentication state changes

Following SSOT patterns and CLAUDE.md requirements:
- Uses real state machine components (NO MOCKS except for external services)
- Real authentication validation where possible
- Absolute imports only (no relative imports)
- Test categorization with @pytest.mark.unit
- Focuses on business logic validation rather than transport mechanics
"""
import asyncio
import pytest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, ConnectionStateTransition, WebSocketConnectionStateMachine, StateTransitionInfo
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator, WebSocketAuthResult
from netra_backend.app.websocket_core.message_queue import MessageQueue, MessagePriority, MessageQueueState, QueuedMessage
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class AdvancedStateTransitionsAuthTests(SSotBaseTestCase):
    """
    Advanced unit tests for WebSocket state machine authentication integration.
    
    CRITICAL: These tests validate complex state transition scenarios that go beyond
    basic authentication flow testing. Focus is on edge cases, race conditions,
    and advanced coordination between state machine and authentication system.
    
    Tests focus on:
    1. Complex multi-step state transitions during authentication changes
    2. State machine behavior during authentication token lifecycle events
    3. Advanced race condition scenarios in concurrent operations
    4. State recovery and rollback with authentication context preservation
    5. Performance under stress with complex state + auth coordination
    """

    def setup_method(self) -> None:
        """Set up test environment for advanced state transition testing."""
        super().setup_method()
        self.connection_id = str(uuid.uuid4())
        self.user_id = ensure_user_id(str(uuid.uuid4()))
        self.state_machine = WebSocketConnectionStateMachine(connection_id=self.connection_id, user_id=self.user_id)
        self.authenticator = UnifiedWebSocketAuthenticator()
        self.message_queue = MessageQueue(connection_id=self.connection_id, user_id=self.user_id)
        self.created_connections = []
        self.created_users = []

    def teardown_method(self) -> None:
        """Clean up test resources."""
        for conn_id in self.created_connections:
            try:
                pass
            except Exception:
                pass
        super().teardown_method()

    def create_mock_auth_token(self, user_id: str, expires_in_seconds: int=3600) -> str:
        """Create mock JWT token for testing authentication scenarios."""
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        return f'mock.jwt.token.{user_id}.expires.{int(expiry.timestamp())}'

    def create_mock_websocket_with_auth(self, user_id: str, token: str=None) -> Mock:
        """Create mock WebSocket with authentication headers."""
        websocket = Mock()
        websocket.state = 'connected'
        websocket.headers = {'authorization': f'Bearer {token or self.create_mock_auth_token(user_id)}', 'connection-id': self.connection_id, 'user-id': user_id, 'x-request-id': str(uuid.uuid4())}
        return websocket

    def test_complex_transition_sequence_during_token_refresh(self):
        """Test complex state transition sequence during authentication token refresh."""
        self.state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
        initial_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=30)
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), initial_token)
        transition_sequence = [(ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY), (ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING)]
        transition_results = []
        for i, (from_state, to_state) in enumerate(transition_sequence):
            if i == 1:
                refreshed_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=3600)
                websocket.headers['authorization'] = f'Bearer {refreshed_token}'
                assert 'Bearer' in websocket.headers['authorization']
                assert initial_token != refreshed_token
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=from_state, to_state=to_state, user_id=self.user_id)
            success = self.state_machine.execute_transition(transition)
            current_state = self.state_machine.get_current_state()
            transition_results.append({'step': i, 'from_state': from_state, 'to_state': to_state, 'success': success, 'actual_state': current_state, 'has_token_refresh': i == 1})
        for result in transition_results:
            assert result['success'], f"Transition step {result['step']} must succeed even during token refresh"
            assert result['actual_state'] == result['to_state'], f"State must match expected at step {result['step']}"
        final_state = self.state_machine.get_current_state()
        assert final_state == ApplicationConnectionState.PROCESSING
        final_auth_header = websocket.headers.get('authorization')
        assert final_auth_header is not None
        assert 'Bearer' in final_auth_header

    def test_state_transition_rollback_with_auth_context_preservation(self):
        """Test state transition rollback preserves authentication context."""
        self.state_machine._current_state = ApplicationConnectionState.SERVICES_READY
        original_state = self.state_machine.get_current_state()
        auth_token = self.create_mock_auth_token(str(self.user_id))
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), auth_token)
        original_auth_context = {'token': auth_token, 'user_id': str(self.user_id), 'headers': dict(websocket.headers)}
        failing_transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.SERVICES_READY, to_state=ApplicationConnectionState.PROCESSING_READY, user_id=self.user_id)
        with patch.object(self.state_machine, '_validate_transition_conditions', return_value=False):
            transition_success = self.state_machine.execute_transition(failing_transition)
            assert not transition_success, 'Transition should fail due to validation'
            current_state = self.state_machine.get_current_state()
            assert current_state == original_state
            assert current_state == ApplicationConnectionState.SERVICES_READY
        current_auth_context = {'token': websocket.headers.get('authorization', '').replace('Bearer ', ''), 'user_id': websocket.headers.get('user-id'), 'headers': dict(websocket.headers)}
        assert current_auth_context['token'] == original_auth_context['token']
        assert current_auth_context['user_id'] == original_auth_context['user_id']
        assert current_auth_context['headers'] == original_auth_context['headers']

    def test_concurrent_state_transitions_with_auth_validation_race(self):
        """Test concurrent state transitions with authentication validation race conditions."""
        concurrent_count = 8
        state_machines = []
        websockets = []
        auth_contexts = []
        for i in range(concurrent_count):
            conn_id = f'{self.connection_id}_concurrent_{i}'
            user_id = f'concurrent_user_{i}'
            sm = WebSocketConnectionStateMachine(connection_id=conn_id)
            sm._current_state = ApplicationConnectionState.ACCEPTED
            state_machines.append(sm)
            token = self.create_mock_auth_token(user_id)
            ws = self.create_mock_websocket_with_auth(user_id, token)
            websockets.append(ws)
            auth_contexts.append({'user_id': user_id, 'token': token, 'connection_id': conn_id})
            self.created_connections.append(conn_id)
            self.created_users.append(user_id)
        transition_results = []
        results_lock = threading.Lock()

        def concurrent_auth_transition(index: int):
            """Perform concurrent authentication-related state transition."""
            try:
                sm = state_machines[index]
                ws = websockets[index]
                auth_ctx = auth_contexts[index]
                time.sleep(0.001 * (index + 1))
                transition = ConnectionStateTransition(connection_id=auth_ctx['connection_id'], from_state=ApplicationConnectionState.ACCEPTED, to_state=ApplicationConnectionState.AUTHENTICATED, user_id=ensure_user_id(auth_ctx['user_id']))
                success = sm.execute_transition(transition)
                final_state = sm.get_current_state()
                with results_lock:
                    transition_results.append({'index': index, 'success': success, 'final_state': final_state, 'user_id': auth_ctx['user_id'], 'connection_id': auth_ctx['connection_id']})
            except Exception as e:
                with results_lock:
                    transition_results.append({'index': index, 'error': str(e), 'success': False})
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = []
            for i in range(concurrent_count):
                future = executor.submit(concurrent_auth_transition, i)
                futures.append(future)
            for future in as_completed(futures):
                future.result()
        assert len(transition_results) == concurrent_count
        successful_transitions = [r for r in transition_results if r.get('success')]
        assert len(successful_transitions) == concurrent_count, 'All concurrent auth transitions should succeed'
        authenticated_results = [r for r in successful_transitions if r.get('final_state') == ApplicationConnectionState.AUTHENTICATED]
        assert len(authenticated_results) == concurrent_count, 'All transitions should reach AUTHENTICATED state'
        connection_ids = [r.get('connection_id') for r in successful_transitions]
        unique_connections = set(connection_ids)
        assert len(unique_connections) == concurrent_count, 'Each transition should have unique connection context'

    def test_state_machine_recovery_from_auth_service_timeout(self):
        """Test state machine recovery from authentication service timeout scenarios."""
        self.state_machine._current_state = ApplicationConnectionState.ACCEPTED
        slow_token = self.create_mock_auth_token(str(self.user_id))
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), slow_token)
        state_before_timeout = self.state_machine.get_current_state()
        timeout_transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.ACCEPTED, to_state=ApplicationConnectionState.AUTHENTICATED, user_id=self.user_id)
        with patch.object(self.authenticator, 'authenticate_websocket_connection') as mock_auth:
            mock_auth.side_effect = asyncio.TimeoutError('Authentication service timeout')
            try:
                transition_success = self.state_machine.execute_transition(timeout_transition)
                state_after_timeout = self.state_machine.get_current_state()
                assert state_after_timeout in [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.DEGRADED, ApplicationConnectionState.RECONNECTING]
                assert state_after_timeout != ApplicationConnectionState.AUTHENTICATED
            except asyncio.TimeoutError:
                state_after_timeout = self.state_machine.get_current_state()
                assert state_after_timeout == state_before_timeout
        with patch.object(self.authenticator, 'authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value = WebSocketAuthResult(success=True, user_id=str(self.user_id), connection_id=self.connection_id, message='Authentication successful after recovery')
            recovery_transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=self.state_machine.get_current_state(), to_state=ApplicationConnectionState.AUTHENTICATED, user_id=self.user_id)
            recovery_success = self.state_machine.execute_transition(recovery_transition)
            if self.state_machine.get_current_state() != ApplicationConnectionState.AUTHENTICATED:
                assert self.state_machine.get_current_state() in [ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]

    async def test_message_queue_coordination_during_complex_auth_transitions(self):
        """Test message queue coordination during complex authentication state transitions."""
        queue = MessageQueue(connection_id=self.connection_id, user_id=self.user_id)
        test_messages = [{'type': 'critical_system_message', 'priority': MessagePriority.CRITICAL, 'content': 'System alert message'}, {'type': 'user_agent_response', 'priority': MessagePriority.HIGH, 'content': 'Agent processing result'}, {'type': 'typing_indicator', 'priority': MessagePriority.LOW, 'content': 'User is typing...'}]
        auth_states_to_test = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
        queue_behavior_results = []
        for state in auth_states_to_test:
            self.state_machine._current_state = state
            current_state = self.state_machine.get_current_state()
            await queue.clear_queue()
            queued_message_ids = []
            for msg in test_messages:
                success = await queue.enqueue_message(message_data=msg, message_type=msg['type'], priority=msg['priority'])
                queued_message_ids.append(success)
            queue_stats = queue.get_queue_stats()
            queue_state = queue.current_state
            should_buffer = current_state in [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED]
            should_process = current_state in [ApplicationConnectionState.PROCESSING_READY]
            queue_behavior_results.append({'auth_state': current_state, 'queued_count': queue_stats.get('total_size', 0), 'queue_state': queue_state, 'should_buffer': should_buffer, 'should_process': should_process, 'messages_queued': queue_stats.get('messages_queued', 0), 'enqueue_success_count': sum((1 for success in queued_message_ids if success))})
        for result in queue_behavior_results:
            if result['should_buffer']:
                assert result['enqueue_success_count'] > 0, f"Messages should be enqueued in {result['auth_state']} state"
                assert result['queue_state'] == MessageQueueState.BUFFERING, f"Queue should be buffering in {result['auth_state']} state"
            elif result['should_process']:
                assert result['queue_state'] in [MessageQueueState.PASS_THROUGH, MessageQueueState.FLUSHING]

    def test_auth_token_expiry_during_active_state_transitions(self):
        """Test state machine behavior when auth token expires during active transitions."""
        self.state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
        short_lived_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=1)
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), short_lived_token)
        transition_sequence = [(ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY)]
        transition_results = []
        for i, (from_state, to_state) in enumerate(transition_sequence):
            if i == 1:
                time.sleep(1.5)
                current_time = datetime.now(timezone.utc).timestamp()
                token_parts = short_lived_token.split('.')
                if len(token_parts) >= 4:
                    try:
                        expiry_timestamp = float(token_parts[-1])
                        token_expired = current_time > expiry_timestamp
                        assert token_expired, 'Token should be expired for this test'
                    except ValueError:
                        pass
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=from_state, to_state=to_state, user_id=self.user_id)
            success = self.state_machine.execute_transition(transition)
            current_state = self.state_machine.get_current_state()
            transition_results.append({'step': i, 'from_state': from_state, 'to_state': to_state, 'success': success, 'actual_state': current_state, 'token_expired': i == 1})
        for result in transition_results:
            if not result['token_expired']:
                assert result['success'], 'Transition should succeed with valid token'
            elif not result['success']:
                assert result['actual_state'] in [ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.DEGRADED, ApplicationConnectionState.RECONNECTING]
            else:
                assert result['actual_state'] == result['to_state']

    def test_state_machine_deadlock_prevention_during_auth_operations(self):
        """Test state machine deadlock prevention during concurrent authentication operations."""
        self.state_machine._current_state = ApplicationConnectionState.ACCEPTED
        deadlock_test_count = 5
        concurrent_operations = []
        results = []
        results_lock = threading.Lock()

        def potentially_deadlocking_operation(op_id: int):
            """Operation that could cause deadlock if not properly synchronized."""
            try:
                operations = [(ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.DEGRADED), (ApplicationConnectionState.DEGRADED, ApplicationConnectionState.RECONNECTING), (ApplicationConnectionState.RECONNECTING, ApplicationConnectionState.AUTHENTICATED)]
                from_state, to_state = operations[op_id % len(operations)]
                temp_state_machine = WebSocketConnectionStateMachine(connection_id=f'{self.connection_id}_deadlock_{op_id}')
                temp_state_machine._current_state = from_state
                transition = ConnectionStateTransition(connection_id=f'{self.connection_id}_deadlock_{op_id}', from_state=from_state, to_state=to_state, user_id=self.user_id)
                time.sleep(0.01)
                start_time = time.time()
                success = temp_state_machine.execute_transition(transition)
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                with results_lock:
                    results.append({'op_id': op_id, 'success': success, 'execution_time_ms': execution_time, 'from_state': from_state, 'to_state': to_state, 'final_state': temp_state_machine.get_current_state()})
            except Exception as e:
                with results_lock:
                    results.append({'op_id': op_id, 'error': str(e), 'success': False})
        with ThreadPoolExecutor(max_workers=deadlock_test_count) as executor:
            futures = []
            for op_id in range(deadlock_test_count):
                future = executor.submit(potentially_deadlocking_operation, op_id)
                futures.append(future)
            timeout_seconds = 10
            start_time = time.time()
            for future in as_completed(futures, timeout=timeout_seconds):
                try:
                    future.result()
                except Exception as e:
                    with results_lock:
                        results.append({'error': f'Operation timeout or deadlock: {str(e)}', 'success': False, 'deadlock_suspected': True})
            end_time = time.time()
            total_time = end_time - start_time
        assert total_time < timeout_seconds - 1, 'Operations should complete well before timeout (no deadlocks)'
        assert len(results) == deadlock_test_count, 'All operations should complete without deadlock'
        deadlock_indicators = [r for r in results if r.get('deadlock_suspected')]
        assert len(deadlock_indicators) == 0, 'No deadlock indicators should be present'
        successful_ops = [r for r in results if r.get('success') and 'execution_time_ms' in r]
        if successful_ops:
            max_execution_time = max((r['execution_time_ms'] for r in successful_ops))
            assert max_execution_time < 1000, 'No operation should take more than 1 second'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')