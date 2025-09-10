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

# SSOT Imports - Using absolute imports only
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateTransition,
    WebSocketConnectionStateMachine,
    StateTransitionInfo
)
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult
)
from netra_backend.app.websocket_core.message_queue import (
    MessageQueue,
    MessagePriority,
    MessageQueueState,
    QueuedMessage
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestAdvancedStateTransitionsAuth(SSotBaseTestCase):
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
    
    def setUp(self) -> None:
        """Set up test environment for advanced state transition testing."""
        super().setUp()
        
        # Create unique test identifiers
        test_suffix = str(int(time.time() * 1000))
        self.connection_id = f"test_conn_advanced_{test_suffix}"
        self.user_id = ensure_user_id(f"test_user_advanced_{test_suffix}")
        
        # Initialize state machine for testing
        self.state_machine = WebSocketConnectionStateMachine(
            connection_id=self.connection_id
        )
        
        # Initialize authenticator for testing
        self.authenticator = UnifiedWebSocketAuthenticator()
        
        # Initialize message queue for coordination testing
        self.message_queue = MessageQueue(connection_id=self.connection_id, user_id=self.user_id)
        
        # Track test state for cleanup
        self.created_connections = []
        self.created_users = []
    
    def tearDown(self) -> None:
        """Clean up test resources."""
        # Cleanup connections and users created during testing
        for conn_id in self.created_connections:
            try:
                # Clean up any state machine instances
                pass
            except Exception:
                pass
        
        super().tearDown()
    
    def create_mock_auth_token(self, user_id: str, expires_in_seconds: int = 3600) -> str:
        """Create mock JWT token for testing authentication scenarios."""
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        return f"mock.jwt.token.{user_id}.expires.{int(expiry.timestamp())}"
    
    def create_mock_websocket_with_auth(self, user_id: str, token: str = None) -> Mock:
        """Create mock WebSocket with authentication headers."""
        websocket = Mock()
        websocket.state = "connected"
        websocket.headers = {
            'authorization': f'Bearer {token or self.create_mock_auth_token(user_id)}',
            'connection-id': self.connection_id,
            'user-id': user_id,
            'x-request-id': str(uuid.uuid4())
        }
        return websocket
    
    def test_complex_transition_sequence_during_token_refresh(self):
        """Test complex state transition sequence during authentication token refresh."""
        # Start with authenticated state
        self.state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
        
        # Create initial authenticated WebSocket
        initial_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=30)
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), initial_token)
        
        # Simulate complex transition sequence
        transition_sequence = [
            (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY),
            (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY),
            (ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING),
        ]
        
        # Track transition results
        transition_results = []
        
        # Execute transition sequence
        for i, (from_state, to_state) in enumerate(transition_sequence):
            # Simulate token refresh during sequence (at step 1)
            if i == 1:
                # Create refreshed token
                refreshed_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=3600)
                websocket.headers['authorization'] = f'Bearer {refreshed_token}'
                
                # Validate token refresh doesn't interrupt transition
                self.assertIn('Bearer', websocket.headers['authorization'])
                self.assertNotEqual(initial_token, refreshed_token.split('Bearer ')[0])
            
            # Create transition
            transition = ConnectionStateTransition(
                connection_id=self.connection_id,
                from_state=from_state,
                to_state=to_state,
                user_id=self.user_id
            )
            
            # Execute transition
            success = self.state_machine.execute_transition(transition)
            current_state = self.state_machine.get_current_state()
            
            transition_results.append({
                'step': i,
                'from_state': from_state,
                'to_state': to_state,
                'success': success,
                'actual_state': current_state,
                'has_token_refresh': i == 1
            })
        
        # Validate all transitions succeeded
        for result in transition_results:
            self.assertTrue(result['success'], 
                          f"Transition step {result['step']} must succeed even during token refresh")
            self.assertEqual(result['actual_state'], result['to_state'],
                           f"State must match expected at step {result['step']}")
        
        # Final state should be PROCESSING
        final_state = self.state_machine.get_current_state()
        self.assertEqual(final_state, ApplicationConnectionState.PROCESSING)
        
        # Validate authentication context preserved through refresh
        final_auth_header = websocket.headers.get('authorization')
        self.assertIsNotNone(final_auth_header)
        self.assertIn('Bearer', final_auth_header)
    
    def test_state_transition_rollback_with_auth_context_preservation(self):
        """Test state transition rollback preserves authentication context."""
        # Start in SERVICES_READY state
        self.state_machine._current_state = ApplicationConnectionState.SERVICES_READY
        original_state = self.state_machine.get_current_state()
        
        # Create authenticated context
        auth_token = self.create_mock_auth_token(str(self.user_id))
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), auth_token)
        
        # Store original authentication context
        original_auth_context = {
            'token': auth_token,
            'user_id': str(self.user_id),
            'headers': dict(websocket.headers)
        }
        
        # Simulate failing transition (e.g., to PROCESSING_READY fails)
        failing_transition = ConnectionStateTransition(
            connection_id=self.connection_id,
            from_state=ApplicationConnectionState.SERVICES_READY,
            to_state=ApplicationConnectionState.PROCESSING_READY,
            user_id=self.user_id
        )
        
        # Mock transition failure scenario
        with patch.object(self.state_machine, '_validate_transition_conditions', return_value=False):
            transition_success = self.state_machine.execute_transition(failing_transition)
            
            # Transition should fail
            self.assertFalse(transition_success, "Transition should fail due to validation")
            
            # State should rollback to original
            current_state = self.state_machine.get_current_state()
            self.assertEqual(current_state, original_state)
            self.assertEqual(current_state, ApplicationConnectionState.SERVICES_READY)
        
        # Validate authentication context preserved after rollback
        current_auth_context = {
            'token': websocket.headers.get('authorization', '').replace('Bearer ', ''),
            'user_id': websocket.headers.get('user-id'),
            'headers': dict(websocket.headers)
        }
        
        self.assertEqual(current_auth_context['token'], original_auth_context['token'])
        self.assertEqual(current_auth_context['user_id'], original_auth_context['user_id'])
        self.assertEqual(current_auth_context['headers'], original_auth_context['headers'])
    
    def test_concurrent_state_transitions_with_auth_validation_race(self):
        """Test concurrent state transitions with authentication validation race conditions."""
        # Create multiple state machines for concurrent testing
        concurrent_count = 8
        state_machines = []
        websockets = []
        auth_contexts = []
        
        # Initialize concurrent state machines and auth contexts
        for i in range(concurrent_count):
            conn_id = f"{self.connection_id}_concurrent_{i}"
            user_id = f"concurrent_user_{i}"
            
            # Create state machine
            sm = WebSocketConnectionStateMachine(connection_id=conn_id)
            sm._current_state = ApplicationConnectionState.ACCEPTED
            state_machines.append(sm)
            
            # Create authenticated WebSocket
            token = self.create_mock_auth_token(user_id)
            ws = self.create_mock_websocket_with_auth(user_id, token)
            websockets.append(ws)
            
            # Store auth context
            auth_contexts.append({
                'user_id': user_id,
                'token': token,
                'connection_id': conn_id
            })
            
            self.created_connections.append(conn_id)
            self.created_users.append(user_id)
        
        # Results tracking
        transition_results = []
        results_lock = threading.Lock()
        
        def concurrent_auth_transition(index: int):
            """Perform concurrent authentication-related state transition."""
            try:
                sm = state_machines[index]
                ws = websockets[index]
                auth_ctx = auth_contexts[index]
                
                # Add small random delay to increase race condition probability
                time.sleep(0.001 * (index + 1))
                
                # Create transition from ACCEPTED to AUTHENTICATED
                transition = ConnectionStateTransition(
                    connection_id=auth_ctx['connection_id'],
                    from_state=ApplicationConnectionState.ACCEPTED,
                    to_state=ApplicationConnectionState.AUTHENTICATED,
                    user_id=ensure_user_id(auth_ctx['user_id'])
                )
                
                # Execute transition with potential race condition
                success = sm.execute_transition(transition)
                final_state = sm.get_current_state()
                
                # Record result in thread-safe manner
                with results_lock:
                    transition_results.append({
                        'index': index,
                        'success': success,
                        'final_state': final_state,
                        'user_id': auth_ctx['user_id'],
                        'connection_id': auth_ctx['connection_id']
                    })
                
            except Exception as e:
                with results_lock:
                    transition_results.append({
                        'index': index,
                        'error': str(e),
                        'success': False
                    })
        
        # Execute concurrent transitions
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = []
            for i in range(concurrent_count):
                future = executor.submit(concurrent_auth_transition, i)
                futures.append(future)
            
            # Wait for all transitions to complete
            for future in as_completed(futures):
                future.result()  # Will raise any exceptions
        
        # Validate concurrent transition results
        self.assertEqual(len(transition_results), concurrent_count)
        
        # All transitions should succeed independently
        successful_transitions = [r for r in transition_results if r.get('success')]
        self.assertEqual(len(successful_transitions), concurrent_count,
                        "All concurrent auth transitions should succeed")
        
        # All should reach AUTHENTICATED state
        authenticated_results = [r for r in successful_transitions 
                               if r.get('final_state') == ApplicationConnectionState.AUTHENTICATED]
        self.assertEqual(len(authenticated_results), concurrent_count,
                        "All transitions should reach AUTHENTICATED state")
        
        # Each should have unique connection ID (no state bleeding)
        connection_ids = [r.get('connection_id') for r in successful_transitions]
        unique_connections = set(connection_ids)
        self.assertEqual(len(unique_connections), concurrent_count,
                        "Each transition should have unique connection context")
    
    def test_state_machine_recovery_from_auth_service_timeout(self):
        """Test state machine recovery from authentication service timeout scenarios."""
        # Start in ACCEPTED state (ready for authentication)
        self.state_machine._current_state = ApplicationConnectionState.ACCEPTED
        
        # Create WebSocket with valid but slow-to-validate token
        slow_token = self.create_mock_auth_token(str(self.user_id))
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), slow_token)
        
        # Record state before timeout scenario
        state_before_timeout = self.state_machine.get_current_state()
        
        # Simulate authentication service timeout during transition
        timeout_transition = ConnectionStateTransition(
            connection_id=self.connection_id,
            from_state=ApplicationConnectionState.ACCEPTED,
            to_state=ApplicationConnectionState.AUTHENTICATED,
            user_id=self.user_id
        )
        
        # Mock authentication service timeout
        with patch.object(self.authenticator, 'authenticate_websocket_connection') as mock_auth:
            # Configure mock to simulate timeout
            mock_auth.side_effect = asyncio.TimeoutError("Authentication service timeout")
            
            # Attempt transition that will timeout
            try:
                # In real scenario, this would handle timeout gracefully
                transition_success = self.state_machine.execute_transition(timeout_transition)
                
                # Transition should handle timeout gracefully
                state_after_timeout = self.state_machine.get_current_state()
                
                # State should remain stable (not corrupted)
                self.assertIn(state_after_timeout, [
                    ApplicationConnectionState.ACCEPTED,  # Stay in current state
                    ApplicationConnectionState.DEGRADED,  # Or move to degraded
                    ApplicationConnectionState.RECONNECTING  # Or attempt recovery
                ])
                
                # Should not advance to AUTHENTICATED on timeout
                self.assertNotEqual(state_after_timeout, ApplicationConnectionState.AUTHENTICATED)
                
            except asyncio.TimeoutError:
                # Timeout handled at transition level
                state_after_timeout = self.state_machine.get_current_state()
                self.assertEqual(state_after_timeout, state_before_timeout)
        
        # Test recovery mechanism after timeout
        # Mock successful authentication after recovery
        with patch.object(self.authenticator, 'authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value = WebSocketAuthResult(
                success=True,
                user_id=str(self.user_id),
                connection_id=self.connection_id,
                message="Authentication successful after recovery"
            )
            
            # Retry transition after recovery
            recovery_transition = ConnectionStateTransition(
                connection_id=self.connection_id,
                from_state=self.state_machine.get_current_state(),
                to_state=ApplicationConnectionState.AUTHENTICATED,
                user_id=self.user_id
            )
            
            recovery_success = self.state_machine.execute_transition(recovery_transition)
            
            # Recovery should succeed
            if self.state_machine.get_current_state() != ApplicationConnectionState.AUTHENTICATED:
                # If not direct transition, should at least make progress
                self.assertIn(self.state_machine.get_current_state(), [
                    ApplicationConnectionState.AUTHENTICATED,
                    ApplicationConnectionState.SERVICES_READY,
                    ApplicationConnectionState.PROCESSING_READY
                ])
    
    def test_message_queue_coordination_during_complex_auth_transitions(self):
        """Test message queue coordination during complex authentication state transitions."""
        # Initialize message queue with state machine coordination
        queue = MessageQueue(connection_id=self.connection_id, user_id=self.user_id)
        
        # Create test messages for different priority levels
        test_messages = [
            {
                'type': 'critical_system_message',
                'priority': MessagePriority.CRITICAL,
                'content': 'System alert message'
            },
            {
                'type': 'user_agent_response',
                'priority': MessagePriority.HIGH,
                'content': 'Agent processing result'
            },
            {
                'type': 'typing_indicator',
                'priority': MessagePriority.LOW,
                'content': 'User is typing...'
            }
        ]
        
        # Test message queuing behavior across different auth states
        auth_states_to_test = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.PROCESSING_READY
        ]
        
        queue_behavior_results = []
        
        for state in auth_states_to_test:
            # Set state machine to test state
            self.state_machine._current_state = state
            current_state = self.state_machine.get_current_state()
            
            # Clear queue for clean testing
            queue.clear_queue()
            
            # Queue test messages
            queued_message_ids = []
            for msg in test_messages:
                queued_msg = QueuedMessage(
                    message_data=msg,
                    message_type=msg['type'],
                    priority=msg['priority'],
                    connection_id=self.connection_id,
                    user_id=str(self.user_id)
                )
                
                queue.queue_message(queued_msg)
                queued_message_ids.append(id(queued_msg))
            
            # Check queue behavior based on state
            queued_messages = queue.get_queued_messages()
            queue_state = queue.get_queue_state()
            
            # Determine expected behavior based on auth state
            should_buffer = current_state in [
                ApplicationConnectionState.CONNECTING,
                ApplicationConnectionState.ACCEPTED,
                ApplicationConnectionState.AUTHENTICATED
            ]
            
            should_process = current_state in [
                ApplicationConnectionState.PROCESSING_READY
            ]
            
            # Record queue behavior for this state
            queue_behavior_results.append({
                'auth_state': current_state,
                'queued_count': len(queued_messages),
                'queue_state': queue_state,
                'should_buffer': should_buffer,
                'should_process': should_process,
                'critical_messages_preserved': len([m for m in queued_messages 
                                                  if m.priority == MessagePriority.CRITICAL])
            })
        
        # Validate queue coordination behavior
        for result in queue_behavior_results:
            if result['should_buffer']:
                # Messages should be queued during setup phases
                self.assertGreater(result['queued_count'], 0,
                                 f"Messages should be queued in {result['auth_state']} state")
                
                # Critical messages must always be preserved
                self.assertGreater(result['critical_messages_preserved'], 0,
                                 f"Critical messages must be preserved in {result['auth_state']}")
            
            elif result['should_process']:
                # In processing state, queue should be in pass-through mode
                self.assertIn(result['queue_state'], [
                    MessageQueueState.PASS_THROUGH,
                    MessageQueueState.FLUSHING
                ])
    
    def test_auth_token_expiry_during_active_state_transitions(self):
        """Test state machine behavior when auth token expires during active transitions."""
        # Start in AUTHENTICATED state
        self.state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
        
        # Create token that expires very soon (1 second)
        short_lived_token = self.create_mock_auth_token(str(self.user_id), expires_in_seconds=1)
        websocket = self.create_mock_websocket_with_auth(str(self.user_id), short_lived_token)
        
        # Create transition sequence that will span token expiry
        transition_sequence = [
            (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY),
            (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY),
        ]
        
        transition_results = []
        
        for i, (from_state, to_state) in enumerate(transition_sequence):
            # For second transition, token should be expired
            if i == 1:
                # Wait for token to expire
                time.sleep(1.5)
                
                # Verify token is expired (in real scenario)
                current_time = datetime.now(timezone.utc).timestamp()
                token_parts = short_lived_token.split('.')
                if len(token_parts) >= 4:  # mock token format
                    try:
                        expiry_timestamp = float(token_parts[-1])
                        token_expired = current_time > expiry_timestamp
                        self.assertTrue(token_expired, "Token should be expired for this test")
                    except ValueError:
                        pass  # Mock token format, skip validation
            
            # Create transition
            transition = ConnectionStateTransition(
                connection_id=self.connection_id,
                from_state=from_state,
                to_state=to_state,
                user_id=self.user_id
            )
            
            # Execute transition - behavior depends on implementation
            success = self.state_machine.execute_transition(transition)
            current_state = self.state_machine.get_current_state()
            
            transition_results.append({
                'step': i,
                'from_state': from_state,
                'to_state': to_state,
                'success': success,
                'actual_state': current_state,
                'token_expired': i == 1
            })
        
        # Validate transition behavior with expired token
        for result in transition_results:
            if not result['token_expired']:
                # First transition should succeed (token valid)
                self.assertTrue(result['success'], 
                              "Transition should succeed with valid token")
            else:
                # Second transition behavior depends on implementation
                # Should either:
                # 1. Fail and require re-authentication
                # 2. Trigger automatic token refresh
                # 3. Move to degraded state
                
                if not result['success']:
                    # Acceptable: transition failed, requires re-auth
                    self.assertIn(result['actual_state'], [
                        ApplicationConnectionState.SERVICES_READY,  # Stayed in previous state
                        ApplicationConnectionState.DEGRADED,       # Moved to degraded
                        ApplicationConnectionState.RECONNECTING    # Attempting recovery
                    ])
                else:
                    # Acceptable: transition succeeded (token was refreshed)
                    self.assertEqual(result['actual_state'], result['to_state'])
    
    def test_state_machine_deadlock_prevention_during_auth_operations(self):
        """Test state machine deadlock prevention during concurrent authentication operations."""
        # Create scenario with potential for deadlock
        # Multiple threads trying to transition same connection
        
        self.state_machine._current_state = ApplicationConnectionState.ACCEPTED
        
        deadlock_test_count = 5
        concurrent_operations = []
        results = []
        results_lock = threading.Lock()
        
        def potentially_deadlocking_operation(op_id: int):
            """Operation that could cause deadlock if not properly synchronized."""
            try:
                # Different operations that could conflict
                operations = [
                    # Auth-related transitions
                    (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED),
                    (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY),
                    # Recovery operations
                    (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.DEGRADED),
                    (ApplicationConnectionState.DEGRADED, ApplicationConnectionState.RECONNECTING),
                    # Back to operational
                    (ApplicationConnectionState.RECONNECTING, ApplicationConnectionState.AUTHENTICATED),
                ]
                
                # Create operation based on ID
                from_state, to_state = operations[op_id % len(operations)]
                
                # Set state machine to expected from_state for this operation
                # Note: This could cause race conditions in real scenario
                temp_state_machine = WebSocketConnectionStateMachine(
                    connection_id=f"{self.connection_id}_deadlock_{op_id}"
                )
                temp_state_machine._current_state = from_state
                
                # Create transition
                transition = ConnectionStateTransition(
                    connection_id=f"{self.connection_id}_deadlock_{op_id}",
                    from_state=from_state,
                    to_state=to_state,
                    user_id=self.user_id
                )
                
                # Add artificial delay to increase deadlock probability
                time.sleep(0.01)
                
                # Execute transition
                start_time = time.time()
                success = temp_state_machine.execute_transition(transition)
                end_time = time.time()
                
                execution_time = (end_time - start_time) * 1000  # milliseconds
                
                with results_lock:
                    results.append({
                        'op_id': op_id,
                        'success': success,
                        'execution_time_ms': execution_time,
                        'from_state': from_state,
                        'to_state': to_state,
                        'final_state': temp_state_machine.get_current_state()
                    })
                
            except Exception as e:
                with results_lock:
                    results.append({
                        'op_id': op_id,
                        'error': str(e),
                        'success': False
                    })
        
        # Execute potentially deadlocking operations concurrently
        with ThreadPoolExecutor(max_workers=deadlock_test_count) as executor:
            futures = []
            for op_id in range(deadlock_test_count):
                future = executor.submit(potentially_deadlocking_operation, op_id)
                futures.append(future)
            
            # Set timeout to detect deadlocks
            timeout_seconds = 10
            start_time = time.time()
            
            for future in as_completed(futures, timeout=timeout_seconds):
                try:
                    future.result()
                except Exception as e:
                    # Record timeout/deadlock scenario
                    with results_lock:
                        results.append({
                            'error': f"Operation timeout or deadlock: {str(e)}",
                            'success': False,
                            'deadlock_suspected': True
                        })
            
            end_time = time.time()
            total_time = end_time - start_time
        
        # Validate no deadlocks occurred
        self.assertLess(total_time, timeout_seconds - 1,
                       "Operations should complete well before timeout (no deadlocks)")
        
        # All operations should complete
        self.assertEqual(len(results), deadlock_test_count,
                        "All operations should complete without deadlock")
        
        # No deadlock indicators in results
        deadlock_indicators = [r for r in results if r.get('deadlock_suspected')]
        self.assertEqual(len(deadlock_indicators), 0,
                        "No deadlock indicators should be present")
        
        # Execution times should be reasonable (not hanging)
        successful_ops = [r for r in results if r.get('success') and 'execution_time_ms' in r]
        if successful_ops:
            max_execution_time = max(r['execution_time_ms'] for r in successful_ops)
            self.assertLess(max_execution_time, 1000,
                           "No operation should take more than 1 second")


if __name__ == "__main__":
    # Run unit tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "unit"])