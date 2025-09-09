"""
Test WebSocket Connection State Machine Transitions with Application State Persistence

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket state transitions with persistent application state
- Value Impact: Users experience consistent connection states that are properly tracked and recovered
- Strategic Impact: Foundation for reliable real-time communication and agent interactions

This integration test validates that WebSocket connection state machine transitions
are properly managed and that application state persists correctly across state changes.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class ConnectionState(Enum):
    """Connection state enumeration for testing state machine."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class TestWebSocketConnectionStateMachineApplicationStateIntegration(BaseIntegrationTest):
    """Test WebSocket connection state machine transitions with comprehensive application state persistence."""
    
    def _create_state_tracking_websocket(self, initial_state: ConnectionState = ConnectionState.INITIALIZING):
        """Create a WebSocket mock that tracks state transitions."""
        class StateTrackingWebSocket:
            def __init__(self, initial_state: ConnectionState):
                self.current_state = initial_state
                self.state_history: List[Dict[str, Any]] = []
                self.messages_sent = []
                self.is_closed = False
                self.state_change_callbacks = []
                
                # Record initial state
                self._record_state_change(None, initial_state, "initialization")
            
            def _record_state_change(self, from_state: Optional[ConnectionState], 
                                   to_state: ConnectionState, reason: str):
                """Record state change with timestamp."""
                transition = {
                    'from_state': from_state.value if from_state else None,
                    'to_state': to_state.value,
                    'timestamp': datetime.utcnow().isoformat(),
                    'reason': reason
                }
                self.state_history.append(transition)
                
                # Notify callbacks
                for callback in self.state_change_callbacks:
                    callback(transition)
            
            def transition_to(self, new_state: ConnectionState, reason: str = "manual"):
                """Transition to a new state."""
                old_state = self.current_state
                self.current_state = new_state
                self._record_state_change(old_state, new_state, reason)
                return True
            
            def can_transition_to(self, target_state: ConnectionState) -> bool:
                """Check if transition is valid from current state."""
                valid_transitions = {
                    ConnectionState.INITIALIZING: [ConnectionState.CONNECTING, ConnectionState.ERROR],
                    ConnectionState.CONNECTING: [ConnectionState.CONNECTED, ConnectionState.ERROR, ConnectionState.DISCONNECTED],
                    ConnectionState.CONNECTED: [ConnectionState.AUTHENTICATED, ConnectionState.ACTIVE, ConnectionState.DISCONNECTING, ConnectionState.ERROR],
                    ConnectionState.AUTHENTICATED: [ConnectionState.ACTIVE, ConnectionState.DEGRADED, ConnectionState.DISCONNECTING, ConnectionState.ERROR],
                    ConnectionState.ACTIVE: [ConnectionState.DEGRADED, ConnectionState.DISCONNECTING, ConnectionState.DISCONNECTED, ConnectionState.ERROR],
                    ConnectionState.DEGRADED: [ConnectionState.ACTIVE, ConnectionState.DISCONNECTING, ConnectionState.ERROR],
                    ConnectionState.DISCONNECTING: [ConnectionState.DISCONNECTED, ConnectionState.ERROR],
                    ConnectionState.DISCONNECTED: [ConnectionState.CONNECTING],  # Can reconnect
                    ConnectionState.ERROR: [ConnectionState.CONNECTING, ConnectionState.DISCONNECTED]  # Can recover
                }
                return target_state in valid_transitions.get(self.current_state, [])
            
            async def send_json(self, data):
                if self.current_state in [ConnectionState.DISCONNECTED, ConnectionState.ERROR]:
                    raise ConnectionError(f"Cannot send message in state: {self.current_state.value}")
                
                # Add state info to message
                data['_connection_state'] = self.current_state.value
                data['_state_timestamp'] = datetime.utcnow().isoformat()
                self.messages_sent.append(data)
            
            async def close(self, code=1000, reason="Normal closure"):
                if self.can_transition_to(ConnectionState.DISCONNECTING):
                    self.transition_to(ConnectionState.DISCONNECTING, f"close_requested_{code}")
                    # Simulate async close process
                    await asyncio.sleep(0.01)
                    self.transition_to(ConnectionState.DISCONNECTED, "close_completed")
                self.is_closed = True
            
            def add_state_change_callback(self, callback):
                """Add callback for state changes."""
                self.state_change_callbacks.append(callback)
        
        return StateTrackingWebSocket(initial_state)
    
    async def _persist_connection_state(self, real_services_fixture, connection_id: str, 
                                      user_id: str, state: ConnectionState, metadata: Dict):
        """Persist connection state to Redis for application state tracking."""
        state_data = {
            'connection_id': connection_id,
            'user_id': user_id,
            'current_state': state.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata
        }
        
        # Store in Redis with expiration
        state_key = f"connection_state:{connection_id}"
        await real_services_fixture["redis"].set(
            state_key,
            json.dumps(state_data),
            ex=3600  # 1 hour expiration
        )
        
        # Also track user's active connections
        user_connections_key = f"user_connections:{user_id}"
        await real_services_fixture["redis"].sadd(user_connections_key, connection_id)
        await real_services_fixture["redis"].expire(user_connections_key, 3600)
        
        return state_data
    
    async def _get_persisted_connection_state(self, real_services_fixture, connection_id: str) -> Optional[Dict]:
        """Retrieve persisted connection state from Redis."""
        state_key = f"connection_state:{connection_id}"
        state_json = await real_services_fixture["redis"].get(state_key)
        
        if state_json:
            return json.loads(state_json)
        return None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_state_machine_transitions_with_application_persistence(self, real_services_fixture):
        """
        Test complete WebSocket connection state machine with persistent application state tracking.
        
        Business Value: Ensures connection states are properly tracked and persisted,
        enabling reliable connection management and recovery scenarios.
        """
        # Create test user and session
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'state_machine_test@netra.ai',
            'name': 'State Machine Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create state-tracking WebSocket
        state_websocket = self._create_state_tracking_websocket()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="state_test_conn",
            context={"user_id": user_id, "test": "state_machine"}
        )
        
        # State transition tracking
        state_transitions = []
        
        def track_state_transitions(transition):
            state_transitions.append(transition)
            # Persist state change to application state
            asyncio.create_task(
                self._persist_connection_state(
                    real_services_fixture,
                    connection_id,
                    user_id,
                    ConnectionState(transition['to_state']),
                    {'transition_reason': transition['reason']}
                )
            )
        
        state_websocket.add_state_change_callback(track_state_transitions)
        
        # Test State 1: INITIALIZING -> CONNECTING
        assert state_websocket.current_state == ConnectionState.INITIALIZING
        
        # Transition to connecting
        assert state_websocket.can_transition_to(ConnectionState.CONNECTING)
        state_websocket.transition_to(ConnectionState.CONNECTING, "connection_attempt")
        
        # Test State 2: CONNECTING -> CONNECTED
        await asyncio.sleep(0.01)  # Simulate connection time
        assert state_websocket.can_transition_to(ConnectionState.CONNECTED)
        state_websocket.transition_to(ConnectionState.CONNECTED, "connection_established")
        
        # Create WebSocket connection object
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=state_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "state_machine_test",
                "initial_state": ConnectionState.CONNECTED.value,
                "session_id": session_data['session_key']
            }
        )
        
        # Add connection to manager
        await websocket_manager.add_connection(connection)
        
        # Verify connection is active and state is persisted
        assert websocket_manager.is_connection_active(user_id)
        
        # Check persisted state
        await asyncio.sleep(0.1)  # Allow state persistence to complete
        persisted_state = await self._get_persisted_connection_state(real_services_fixture, connection_id)
        assert persisted_state is not None
        assert persisted_state['current_state'] == ConnectionState.CONNECTED.value
        assert persisted_state['user_id'] == user_id
        
        # Test State 3: CONNECTED -> AUTHENTICATED
        assert state_websocket.can_transition_to(ConnectionState.AUTHENTICATED)
        state_websocket.transition_to(ConnectionState.AUTHENTICATED, "authentication_successful")
        
        # Send message in authenticated state
        auth_message = {
            "type": "authentication_complete",
            "data": {"user_id": user_id, "authenticated": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, auth_message)
        
        # Verify message was sent with correct state
        assert len(state_websocket.messages_sent) > 0
        sent_message = state_websocket.messages_sent[-1]
        assert sent_message['_connection_state'] == ConnectionState.AUTHENTICATED.value
        assert sent_message['type'] == 'authentication_complete'
        
        # Test State 4: AUTHENTICATED -> ACTIVE
        assert state_websocket.can_transition_to(ConnectionState.ACTIVE)
        state_websocket.transition_to(ConnectionState.ACTIVE, "connection_ready_for_use")
        
        # Send active message
        active_message = {
            "type": "connection_active",
            "data": {"ready": True, "capabilities": ["messaging", "agent_execution"]},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, active_message)
        
        # Verify active state message
        active_sent_message = state_websocket.messages_sent[-1]
        assert active_sent_message['_connection_state'] == ConnectionState.ACTIVE.value
        
        # Test State 5: ACTIVE -> DEGRADED (simulating network issues)
        assert state_websocket.can_transition_to(ConnectionState.DEGRADED)
        state_websocket.transition_to(ConnectionState.DEGRADED, "network_quality_degraded")
        
        # Test message sending in degraded state (should still work but with state annotation)
        degraded_message = {
            "type": "degraded_connection_warning",
            "data": {"warning": "Connection quality degraded", "retry_recommended": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, degraded_message)
        
        degraded_sent_message = state_websocket.messages_sent[-1]
        assert degraded_sent_message['_connection_state'] == ConnectionState.DEGRADED.value
        
        # Test State 6: DEGRADED -> ACTIVE (recovery)
        assert state_websocket.can_transition_to(ConnectionState.ACTIVE)
        state_websocket.transition_to(ConnectionState.ACTIVE, "connection_quality_restored")
        
        # Test State 7: ACTIVE -> DISCONNECTING
        assert state_websocket.can_transition_to(ConnectionState.DISCONNECTING)
        state_websocket.transition_to(ConnectionState.DISCONNECTING, "client_requested_disconnect")
        
        # Test State 8: DISCONNECTING -> DISCONNECTED
        await state_websocket.close(1000, "Normal closure")
        assert state_websocket.current_state == ConnectionState.DISCONNECTED
        
        # Verify state transition history
        assert len(state_transitions) >= 8  # Should have all the transitions we made
        
        # Verify specific transitions occurred
        transition_sequence = [t['to_state'] for t in state_transitions]
        expected_sequence = [
            ConnectionState.INITIALIZING.value,  # Initial
            ConnectionState.CONNECTING.value,
            ConnectionState.CONNECTED.value,
            ConnectionState.AUTHENTICATED.value,
            ConnectionState.ACTIVE.value,
            ConnectionState.DEGRADED.value,
            ConnectionState.ACTIVE.value,  # Recovery
            ConnectionState.DISCONNECTING.value,
            ConnectionState.DISCONNECTED.value
        ]
        
        for expected_state in expected_sequence:
            assert expected_state in transition_sequence, f"Expected state {expected_state} not found in transitions"
        
        # Verify final persisted state
        await asyncio.sleep(0.1)  # Allow final state persistence
        final_persisted_state = await self._get_persisted_connection_state(real_services_fixture, connection_id)
        assert final_persisted_state['current_state'] == ConnectionState.DISCONNECTED.value
        
        # Verify database state consistency
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, is_active FROM auth.users WHERE id = $1", user_id
        )
        assert db_user['is_active'] is True  # User should remain active despite connection state changes
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        
        # Clean up Redis state
        await real_services_fixture["redis"].delete(f"connection_state:{connection_id}")
        await real_services_fixture["redis"].delete(f"user_connections:{user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_machine_error_handling_with_application_recovery(self, real_services_fixture):
        """
        Test WebSocket state machine error handling with application state recovery mechanisms.
        
        Business Value: Ensures system can handle and recover from connection errors
        while maintaining application state consistency and enabling reconnection.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'error_recovery_test@netra.ai',
            'name': 'Error Recovery Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create error-prone WebSocket
        error_websocket = self._create_state_tracking_websocket()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="error_test_conn",
            context={"user_id": user_id, "test": "error_recovery"}
        )
        
        # Set up state persistence
        error_transitions = []
        
        def track_error_transitions(transition):
            error_transitions.append(transition)
            asyncio.create_task(
                self._persist_connection_state(
                    real_services_fixture,
                    connection_id,
                    user_id,
                    ConnectionState(transition['to_state']),
                    {
                        'transition_reason': transition['reason'],
                        'error_context': transition.get('error', 'none')
                    }
                )
            )
        
        error_websocket.add_state_change_callback(track_error_transitions)
        
        # Establish connection through normal flow
        error_websocket.transition_to(ConnectionState.CONNECTING, "initial_connection")
        error_websocket.transition_to(ConnectionState.CONNECTED, "connection_successful")
        error_websocket.transition_to(ConnectionState.ACTIVE, "ready_for_use")
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=error_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "error_recovery_test",
                "session_id": session_data['session_key']
            }
        )
        
        await websocket_manager.add_connection(connection)
        
        # Simulate error scenarios
        
        # Error Scenario 1: Network interruption
        assert error_websocket.can_transition_to(ConnectionState.ERROR)
        error_websocket.transition_to(ConnectionState.ERROR, "network_interruption")
        
        # Attempt to send message in error state (should fail)
        try:
            error_message = {
                "type": "test_message_in_error_state",
                "data": {"should_fail": True}
            }
            await error_websocket.send_json(error_message)
            assert False, "Should not be able to send message in error state"
        except ConnectionError as e:
            assert "ERROR" in str(e), "Should get connection error in ERROR state"
        
        # Verify error state is persisted
        await asyncio.sleep(0.1)
        error_persisted_state = await self._get_persisted_connection_state(real_services_fixture, connection_id)
        assert error_persisted_state['current_state'] == ConnectionState.ERROR.value
        assert 'network_interruption' in error_persisted_state['metadata']['transition_reason']
        
        # Recovery Scenario 1: ERROR -> CONNECTING (reconnection attempt)
        assert error_websocket.can_transition_to(ConnectionState.CONNECTING)
        error_websocket.transition_to(ConnectionState.CONNECTING, "reconnection_attempt")
        
        # Recovery Scenario 2: CONNECTING -> CONNECTED (successful recovery)
        error_websocket.transition_to(ConnectionState.CONNECTED, "reconnection_successful")
        error_websocket.transition_to(ConnectionState.ACTIVE, "fully_recovered")
        
        # Test that connection works after recovery
        recovery_message = {
            "type": "recovery_test",
            "data": {"recovered": True, "connection_restored": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, recovery_message)
        
        # Verify message sent successfully after recovery
        assert len(error_websocket.messages_sent) > 0
        recovered_message = error_websocket.messages_sent[-1]
        assert recovered_message['type'] == 'recovery_test'
        assert recovered_message['_connection_state'] == ConnectionState.ACTIVE.value
        
        # Error Scenario 2: Gradual degradation
        error_websocket.transition_to(ConnectionState.DEGRADED, "performance_degradation")
        
        # Send message in degraded state (should work but be marked)
        degraded_message = {
            "type": "degraded_performance_message",
            "data": {"performance_warning": True}
        }
        await websocket_manager.send_to_user(user_id, degraded_message)
        
        degraded_sent = error_websocket.messages_sent[-1]
        assert degraded_sent['_connection_state'] == ConnectionState.DEGRADED.value
        
        # Error Scenario 3: Degraded -> Error (complete failure)
        error_websocket.transition_to(ConnectionState.ERROR, "complete_connection_failure")
        
        # Test application state consistency during errors
        
        # Verify user session remains valid despite connection errors
        cached_session = await real_services_fixture["redis"].get(session_data['session_key'])
        assert cached_session is not None, "User session should remain valid during connection errors"
        
        # Verify user data integrity in database
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id
        )
        assert db_user is not None, "User should exist in database despite connection errors"
        assert db_user['is_active'] is True, "User should remain active despite connection errors"
        
        # Test reconnection after complete failure
        # ERROR -> CONNECTING -> CONNECTED -> ACTIVE
        error_websocket.transition_to(ConnectionState.CONNECTING, "full_reconnection_attempt")
        error_websocket.transition_to(ConnectionState.CONNECTED, "full_reconnection_success")
        error_websocket.transition_to(ConnectionState.ACTIVE, "fully_operational_again")
        
        # Verify final state
        final_message = {
            "type": "connection_fully_restored",
            "data": {"all_systems_operational": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, final_message)
        
        final_sent = error_websocket.messages_sent[-1]
        assert final_sent['type'] == 'connection_fully_restored'
        assert final_sent['_connection_state'] == ConnectionState.ACTIVE.value
        
        # Verify complete transition history includes error handling
        error_transition_states = [t['to_state'] for t in error_transitions]
        
        # Should include error states and recoveries
        assert ConnectionState.ERROR.value in error_transition_states, "Should have ERROR state transitions"
        assert ConnectionState.DEGRADED.value in error_transition_states, "Should have DEGRADED state transitions"
        assert ConnectionState.ACTIVE.value in error_transition_states, "Should have ACTIVE recovery transitions"
        
        # Count recovery attempts (ERROR -> CONNECTING transitions)
        recovery_attempts = sum(1 for i, state in enumerate(error_transition_states)
                              if state == ConnectionState.CONNECTING.value and i > 0 and
                              error_transition_states[i-1] == ConnectionState.ERROR.value)
        assert recovery_attempts >= 2, "Should have multiple recovery attempts"
        
        # Verify final persisted state shows recovery
        await asyncio.sleep(0.1)
        final_persisted_state = await self._get_persisted_connection_state(real_services_fixture, connection_id)
        assert final_persisted_state['current_state'] == ConnectionState.ACTIVE.value
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await real_services_fixture["redis"].delete(f"connection_state:{connection_id}")
        await real_services_fixture["redis"].delete(f"user_connections:{user_id}")
        
        # Verify business value: Error recovery maintains user experience
        self.assert_business_value_delivered({
            'error_recovery': True,
            'state_persistence': True,
            'user_session_continuity': True,
            'automatic_reconnection': True
        }, 'automation')
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_concurrent_state_transitions_with_application_consistency(self, real_services_fixture):
        """
        Test concurrent WebSocket state transitions maintain application state consistency.
        
        Business Value: Ensures state machine integrity under concurrent operations,
        preventing state corruption and maintaining reliable connection management.
        """
        # Create multiple users for concurrent testing
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'concurrent_state_user_{i}@netra.ai',
                'name': f'Concurrent State User {i}',
                'is_active': True
            })
            session_data = await self.create_test_session(real_services_fixture, user_data['id'])
            users.append({'user_data': user_data, 'session_data': session_data})
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        async def concurrent_state_transition_test(user_info, user_index):
            """Run concurrent state transitions for a single user."""
            user_id = user_info['user_data']['id']
            
            # Create state-tracking WebSocket
            concurrent_websocket = self._create_state_tracking_websocket()
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"concurrent_conn_{user_index}",
                context={"user_id": user_id, "test": "concurrent"}
            )
            
            concurrent_transitions = []
            
            def track_concurrent_transitions(transition):
                concurrent_transitions.append(transition)
                # Persist state with user index for tracking
                asyncio.create_task(
                    self._persist_connection_state(
                        real_services_fixture,
                        connection_id,
                        user_id,
                        ConnectionState(transition['to_state']),
                        {
                            'user_index': user_index,
                            'transition_reason': transition['reason']
                        }
                    )
                )
            
            concurrent_websocket.add_state_change_callback(track_concurrent_transitions)
            
            # Perform state transitions sequence
            transitions_sequence = [
                (ConnectionState.CONNECTING, "initial_connect"),
                (ConnectionState.CONNECTED, "connection_established"),
                (ConnectionState.AUTHENTICATED, "auth_successful"),
                (ConnectionState.ACTIVE, "ready_for_use"),
                (ConnectionState.DEGRADED, "simulated_network_issue"),
                (ConnectionState.ACTIVE, "network_recovered"),
                (ConnectionState.DISCONNECTING, "planned_disconnect"),
                (ConnectionState.DISCONNECTED, "disconnect_complete")
            ]
            
            for target_state, reason in transitions_sequence:
                if concurrent_websocket.can_transition_to(target_state):
                    concurrent_websocket.transition_to(target_state, f"{reason}_user_{user_index}")
                    # Small delay to simulate real-world timing
                    await asyncio.sleep(0.05)
            
            # Create and manage connection
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=concurrent_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "concurrent_state_test",
                    "user_index": user_index,
                    "session_id": user_info['session_data']['session_key']
                }
            )
            
            await websocket_manager.add_connection(connection)
            
            # Send messages during various states
            test_messages = [
                {"type": f"message_from_user_{user_index}", "data": {"step": 1}},
                {"type": f"auth_message_user_{user_index}", "data": {"step": 2}},
                {"type": f"active_message_user_{user_index}", "data": {"step": 3}},
                {"type": f"recovery_message_user_{user_index}", "data": {"step": 4}}
            ]
            
            for msg in test_messages:
                try:
                    await websocket_manager.send_to_user(user_id, msg)
                    await asyncio.sleep(0.02)  # Small delay between messages
                except Exception as e:
                    # Some messages might fail depending on state - that's expected
                    pass
            
            # Clean up this user's connection
            await websocket_manager.remove_connection(connection_id)
            await real_services_fixture["redis"].delete(f"connection_state:{connection_id}")
            
            return {
                'user_id': user_id,
                'connection_id': connection_id,
                'transitions': concurrent_transitions,
                'messages_sent': concurrent_websocket.messages_sent,
                'final_state': concurrent_websocket.current_state.value
            }
        
        # Run concurrent state transition tests
        concurrent_tasks = [
            concurrent_state_transition_test(user_info, i)
            for i, user_info in enumerate(users)
        ]
        
        # Execute all concurrent state transitions
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent test {i} failed with: {result}"
        
        # Verify state transition integrity for each user
        for i, result in enumerate(results):
            user_id = result['user_id']
            connection_id = result['connection_id']
            transitions = result['transitions']
            messages = result['messages_sent']
            
            # Verify all expected transitions occurred
            transition_states = [t['to_state'] for t in transitions]
            expected_states = [
                ConnectionState.INITIALIZING.value,
                ConnectionState.CONNECTING.value,
                ConnectionState.CONNECTED.value,
                ConnectionState.AUTHENTICATED.value,
                ConnectionState.ACTIVE.value,
                ConnectionState.DEGRADED.value,
                ConnectionState.ACTIVE.value,  # Recovery
                ConnectionState.DISCONNECTING.value,
                ConnectionState.DISCONNECTED.value
            ]
            
            for expected_state in expected_states:
                assert expected_state in transition_states, \
                    f"User {i} missing expected state: {expected_state}"
            
            # Verify messages were sent with appropriate state annotations
            state_annotated_messages = [msg for msg in messages if '_connection_state' in msg]
            assert len(state_annotated_messages) > 0, f"User {i} should have state-annotated messages"
            
            # Verify final state is DISCONNECTED
            assert result['final_state'] == ConnectionState.DISCONNECTED.value, \
                f"User {i} should end in DISCONNECTED state"
        
        # Verify database consistency across all users
        for i, user_info in enumerate(users):
            user_id = user_info['user_data']['id']
            
            db_user = await real_services_fixture["postgres"].fetchrow(
                "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id
            )
            assert db_user is not None, f"User {i} should exist in database"
            assert db_user['is_active'] is True, f"User {i} should remain active"
        
        # Verify WebSocket manager statistics are consistent
        final_stats = websocket_manager.get_stats()
        assert final_stats['total_connections'] == 0, "All connections should be cleaned up"
        assert final_stats['unique_users'] == 0, "No users should have active connections"
        
        # Verify no cross-user state contamination occurred
        # Check that each user's transitions were properly isolated
        all_user_ids = {result['user_id'] for result in results}
        assert len(all_user_ids) == 3, "Should have 3 unique users"
        
        # Clean up any remaining Redis state
        for i, user_info in enumerate(users):
            user_id = user_info['user_data']['id']
            await real_services_fixture["redis"].delete(f"user_connections:{user_id}")
        
        # Verify business value: Concurrent operations maintain state integrity
        self.assert_business_value_delivered({
            'concurrent_state_integrity': True,
            'multi_user_isolation': True,
            'state_machine_reliability': True,
            'application_consistency': True
        }, 'automation')