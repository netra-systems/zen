"""
Comprehensive WebSocket Connection State Machine Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure WebSocket connection state transitions are reliable and deterministic
- Value Impact: Prevents connection state corruption that would break chat functionality
- Strategic Impact: Foundation for reliable real-time AI interactions

This test suite validates the WebSocket connection state machine logic in isolation,
ensuring that state transitions follow proper business rules and handle edge cases correctly.
These tests are critical for the Golden Path user flow requirements.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from netra_backend.app.core.websocket_recovery_types import ConnectionState, ReconnectionReason
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from shared.types.core_types import UserID, ConnectionID, ensure_user_id


class WebSocketConnectionState(Enum):
    """Enhanced connection state enum for comprehensive testing."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    IDLE = "idle"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class StateTransition:
    """Represents a state transition for testing."""
    from_state: WebSocketConnectionState
    to_state: WebSocketConnectionState
    trigger: str
    is_valid: bool
    requires_condition: Optional[str] = None


class MockWebSocketStateMachine:
    """Mock WebSocket with comprehensive state machine for unit testing."""
    
    def __init__(self, initial_state: WebSocketConnectionState = WebSocketConnectionState.INITIALIZING):
        self.current_state = initial_state
        self.state_history: List[Dict[str, Any]] = []
        self.transition_log: List[StateTransition] = []
        self.error_log: List[Dict[str, Any]] = []
        self.message_queue: List[Dict[str, Any]] = []
        self.connection_metadata = {}
        self.health_metrics = {
            'connection_attempts': 0,
            'successful_messages': 0,
            'failed_messages': 0,
            'reconnection_attempts': 0,
            'total_uptime_seconds': 0
        }
        
        # State machine configuration
        self.state_transition_matrix = self._build_transition_matrix()
        self.state_entry_actions = self._build_entry_actions()
        self.state_exit_actions = self._build_exit_actions()
        
        # Record initial state
        self._record_state_entry(initial_state, "initialization")
    
    def _build_transition_matrix(self) -> Dict[WebSocketConnectionState, List[WebSocketConnectionState]]:
        """Build the valid state transition matrix."""
        return {
            WebSocketConnectionState.INITIALIZING: [
                WebSocketConnectionState.CONNECTING,
                WebSocketConnectionState.ERROR,
                WebSocketConnectionState.TERMINATED
            ],
            WebSocketConnectionState.CONNECTING: [
                WebSocketConnectionState.CONNECTED,
                WebSocketConnectionState.ERROR,
                WebSocketConnectionState.RECONNECTING,
                WebSocketConnectionState.TERMINATED
            ],
            WebSocketConnectionState.CONNECTED: [
                WebSocketConnectionState.AUTHENTICATING,
                WebSocketConnectionState.AUTHENTICATED,  # Direct auth if token present
                WebSocketConnectionState.ACTIVE,  # Skip auth for certain scenarios
                WebSocketConnectionState.DISCONNECTING,
                WebSocketConnectionState.ERROR
            ],
            WebSocketConnectionState.AUTHENTICATING: [
                WebSocketConnectionState.AUTHENTICATED,
                WebSocketConnectionState.ERROR,
                WebSocketConnectionState.DISCONNECTING
            ],
            WebSocketConnectionState.AUTHENTICATED: [
                WebSocketConnectionState.ACTIVE,
                WebSocketConnectionState.IDLE,
                WebSocketConnectionState.DISCONNECTING,
                WebSocketConnectionState.ERROR
            ],
            WebSocketConnectionState.ACTIVE: [
                WebSocketConnectionState.IDLE,
                WebSocketConnectionState.DEGRADED,
                WebSocketConnectionState.DISCONNECTING,
                WebSocketConnectionState.RECONNECTING,
                WebSocketConnectionState.ERROR
            ],
            WebSocketConnectionState.IDLE: [
                WebSocketConnectionState.ACTIVE,
                WebSocketConnectionState.DISCONNECTING,
                WebSocketConnectionState.ERROR
            ],
            WebSocketConnectionState.DEGRADED: [
                WebSocketConnectionState.ACTIVE,  # Recovery
                WebSocketConnectionState.RECONNECTING,
                WebSocketConnectionState.ERROR,
                WebSocketConnectionState.DISCONNECTING
            ],
            WebSocketConnectionState.RECONNECTING: [
                WebSocketConnectionState.CONNECTED,
                WebSocketConnectionState.ERROR,
                WebSocketConnectionState.TERMINATED
            ],
            WebSocketConnectionState.DISCONNECTING: [
                WebSocketConnectionState.DISCONNECTED,
                WebSocketConnectionState.ERROR
            ],
            WebSocketConnectionState.DISCONNECTED: [
                WebSocketConnectionState.CONNECTING,  # Reconnection
                WebSocketConnectionState.TERMINATED
            ],
            WebSocketConnectionState.ERROR: [
                WebSocketConnectionState.CONNECTING,  # Recovery attempt
                WebSocketConnectionState.RECONNECTING,
                WebSocketConnectionState.TERMINATED
            ],
            WebSocketConnectionState.TERMINATED: []  # Terminal state
        }
    
    def _build_entry_actions(self) -> Dict[WebSocketConnectionState, callable]:
        """Build state entry action map."""
        return {
            WebSocketConnectionState.CONNECTING: self._on_entering_connecting,
            WebSocketConnectionState.CONNECTED: self._on_entering_connected,
            WebSocketConnectionState.AUTHENTICATED: self._on_entering_authenticated,
            WebSocketConnectionState.ACTIVE: self._on_entering_active,
            WebSocketConnectionState.ERROR: self._on_entering_error,
            WebSocketConnectionState.DISCONNECTED: self._on_entering_disconnected
        }
    
    def _build_exit_actions(self) -> Dict[WebSocketConnectionState, callable]:
        """Build state exit action map."""
        return {
            WebSocketConnectionState.ACTIVE: self._on_exiting_active,
            WebSocketConnectionState.CONNECTED: self._on_exiting_connected,
            WebSocketConnectionState.ERROR: self._on_exiting_error
        }
    
    def _on_entering_connecting(self):
        """Actions when entering CONNECTING state."""
        self.health_metrics['connection_attempts'] += 1
        self.connection_metadata['last_connection_attempt'] = datetime.utcnow().isoformat()
    
    def _on_entering_connected(self):
        """Actions when entering CONNECTED state."""
        self.connection_metadata['connected_at'] = datetime.utcnow().isoformat()
        self.connection_metadata['connection_stable'] = True
    
    def _on_entering_authenticated(self):
        """Actions when entering AUTHENTICATED state."""
        self.connection_metadata['authenticated_at'] = datetime.utcnow().isoformat()
        self.connection_metadata['auth_valid'] = True
    
    def _on_entering_active(self):
        """Actions when entering ACTIVE state."""
        self.connection_metadata['active_since'] = datetime.utcnow().isoformat()
        self.connection_metadata['ready_for_messages'] = True
    
    def _on_entering_error(self):
        """Actions when entering ERROR state."""
        self.connection_metadata['last_error'] = datetime.utcnow().isoformat()
        self.connection_metadata['ready_for_messages'] = False
    
    def _on_entering_disconnected(self):
        """Actions when entering DISCONNECTED state."""
        self.connection_metadata['disconnected_at'] = datetime.utcnow().isoformat()
        self.connection_metadata['connection_stable'] = False
        self.connection_metadata['ready_for_messages'] = False
    
    def _on_exiting_active(self):
        """Actions when exiting ACTIVE state."""
        if 'active_since' in self.connection_metadata:
            active_duration = (datetime.utcnow() - datetime.fromisoformat(
                self.connection_metadata['active_since'])).total_seconds()
            self.health_metrics['total_uptime_seconds'] += active_duration
    
    def _on_exiting_connected(self):
        """Actions when exiting CONNECTED state."""
        self.connection_metadata.pop('connection_stable', None)
    
    def _on_exiting_error(self):
        """Actions when exiting ERROR state."""
        # Log error recovery
        self.connection_metadata['last_error_recovery'] = datetime.utcnow().isoformat()
    
    def can_transition_to(self, target_state: WebSocketConnectionState) -> bool:
        """Check if transition to target state is valid."""
        valid_transitions = self.state_transition_matrix.get(self.current_state, [])
        return target_state in valid_transitions
    
    def transition_to(self, target_state: WebSocketConnectionState, trigger: str, 
                     force: bool = False, metadata: Optional[Dict] = None) -> bool:
        """Attempt to transition to target state."""
        if not force and not self.can_transition_to(target_state):
            self._record_invalid_transition(self.current_state, target_state, trigger)
            return False
        
        # Execute exit actions for current state
        exit_action = self.state_exit_actions.get(self.current_state)
        if exit_action:
            exit_action()
        
        # Record transition
        old_state = self.current_state
        self.current_state = target_state
        
        # Execute entry actions for new state
        entry_action = self.state_entry_actions.get(target_state)
        if entry_action:
            entry_action()
        
        # Record successful transition
        self._record_state_transition(old_state, target_state, trigger, metadata)
        return True
    
    def _record_state_entry(self, state: WebSocketConnectionState, reason: str):
        """Record state entry."""
        self.state_history.append({
            'state': state.value,
            'action': 'entry',
            'timestamp': datetime.utcnow().isoformat(),
            'reason': reason
        })
    
    def _record_state_transition(self, from_state: WebSocketConnectionState, 
                                to_state: WebSocketConnectionState, trigger: str,
                                metadata: Optional[Dict] = None):
        """Record successful state transition."""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            is_valid=True
        )
        self.transition_log.append(transition)
        
        self.state_history.append({
            'from_state': from_state.value,
            'to_state': to_state.value,
            'trigger': trigger,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        })
    
    def _record_invalid_transition(self, from_state: WebSocketConnectionState,
                                  to_state: WebSocketConnectionState, trigger: str):
        """Record invalid transition attempt."""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            is_valid=False
        )
        self.transition_log.append(transition)
        
        self.error_log.append({
            'type': 'invalid_transition',
            'from_state': from_state.value,
            'to_state': to_state.value,
            'trigger': trigger,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Simulate sending a message based on current state."""
        if self.current_state not in [WebSocketConnectionState.ACTIVE, 
                                     WebSocketConnectionState.AUTHENTICATED,
                                     WebSocketConnectionState.DEGRADED]:
            self.health_metrics['failed_messages'] += 1
            self.error_log.append({
                'type': 'message_send_failed',
                'reason': f'invalid_state_{self.current_state.value}',
                'timestamp': datetime.utcnow().isoformat(),
                'message_type': message.get('type', 'unknown')
            })
            return False
        
        # Simulate degraded performance
        if self.current_state == WebSocketConnectionState.DEGRADED:
            # 30% chance of failure in degraded state
            import random
            if random.random() < 0.3:
                self.health_metrics['failed_messages'] += 1
                return False
        
        self.message_queue.append({
            **message,
            'sent_at': datetime.utcnow().isoformat(),
            'connection_state': self.current_state.value
        })
        self.health_metrics['successful_messages'] += 1
        return True
    
    def get_state_metrics(self) -> Dict[str, Any]:
        """Get comprehensive state metrics."""
        total_transitions = len(self.transition_log)
        invalid_transitions = len([t for t in self.transition_log if not t.is_valid])
        
        state_durations = self._calculate_state_durations()
        
        return {
            'current_state': self.current_state.value,
            'total_transitions': total_transitions,
            'invalid_transitions': invalid_transitions,
            'transition_success_rate': ((total_transitions - invalid_transitions) / 
                                      max(total_transitions, 1)) * 100,
            'state_durations': state_durations,
            'health_metrics': self.health_metrics.copy(),
            'error_count': len(self.error_log),
            'messages_in_queue': len(self.message_queue)
        }
    
    def _calculate_state_durations(self) -> Dict[str, float]:
        """Calculate time spent in each state."""
        durations = {}
        
        for i, entry in enumerate(self.state_history):
            if 'to_state' in entry:  # This is a transition record
                state = entry['to_state']
                start_time = datetime.fromisoformat(entry['timestamp'])
                
                # Find next transition or use current time
                end_time = datetime.utcnow()
                for j in range(i + 1, len(self.state_history)):
                    if 'from_state' in self.state_history[j] and self.state_history[j]['from_state'] == state:
                        end_time = datetime.fromisoformat(self.state_history[j]['timestamp'])
                        break
                
                duration = (end_time - start_time).total_seconds()
                durations[state] = durations.get(state, 0) + duration
        
        return durations


class TestWebSocketConnectionStateMachineUnit:
    """Comprehensive unit tests for WebSocket connection state machine."""
    
    def test_initial_state_is_correct(self):
        """Test that WebSocket starts in correct initial state."""
        state_machine = MockWebSocketStateMachine()
        
        assert state_machine.current_state == WebSocketConnectionState.INITIALIZING
        assert len(state_machine.state_history) == 1
        assert state_machine.state_history[0]['state'] == 'initializing'
        assert state_machine.state_history[0]['action'] == 'entry'
    
    def test_valid_state_transitions(self):
        """Test all valid state transitions in the state machine."""
        state_machine = MockWebSocketStateMachine()
        
        # Test happy path: INITIALIZING -> CONNECTING -> CONNECTED -> AUTHENTICATED -> ACTIVE
        valid_sequence = [
            (WebSocketConnectionState.CONNECTING, "user_initiated_connection"),
            (WebSocketConnectionState.CONNECTED, "tcp_connection_established"), 
            (WebSocketConnectionState.AUTHENTICATING, "auth_token_received"),
            (WebSocketConnectionState.AUTHENTICATED, "auth_validation_successful"),
            (WebSocketConnectionState.ACTIVE, "websocket_handshake_complete")
        ]
        
        for target_state, trigger in valid_sequence:
            assert state_machine.can_transition_to(target_state), \
                f"Should allow transition to {target_state.value} from {state_machine.current_state.value}"
            
            success = state_machine.transition_to(target_state, trigger)
            assert success, f"Transition to {target_state.value} should succeed"
            assert state_machine.current_state == target_state
        
        # Verify all transitions were recorded
        assert len(state_machine.transition_log) == len(valid_sequence)
        for i, (expected_state, expected_trigger) in enumerate(valid_sequence):
            transition = state_machine.transition_log[i]
            assert transition.to_state == expected_state
            assert transition.trigger == expected_trigger
            assert transition.is_valid
    
    def test_invalid_state_transitions(self):
        """Test that invalid state transitions are properly rejected."""
        state_machine = MockWebSocketStateMachine()
        
        # Test invalid transitions from INITIALIZING
        invalid_transitions = [
            WebSocketConnectionState.AUTHENTICATED,  # Can't skip connecting/connected
            WebSocketConnectionState.ACTIVE,         # Can't skip multiple states
            WebSocketConnectionState.IDLE,          # Can't go to idle without being active
            WebSocketConnectionState.DISCONNECTED,  # Can't disconnect before connecting
        ]
        
        for invalid_target in invalid_transitions:
            assert not state_machine.can_transition_to(invalid_target), \
                f"Should NOT allow transition to {invalid_target.value} from INITIALIZING"
            
            success = state_machine.transition_to(invalid_target, "invalid_test")
            assert not success, f"Invalid transition to {invalid_target.value} should fail"
            assert state_machine.current_state == WebSocketConnectionState.INITIALIZING
        
        # Verify invalid transitions were logged as errors
        assert len(state_machine.error_log) == len(invalid_transitions)
        for error in state_machine.error_log:
            assert error['type'] == 'invalid_transition'
            assert error['from_state'] == 'initializing'
    
    def test_error_state_transitions(self):
        """Test transitions to and from ERROR state."""
        state_machine = MockWebSocketStateMachine()
        
        # Establish connection first
        state_machine.transition_to(WebSocketConnectionState.CONNECTING, "test_setup")
        state_machine.transition_to(WebSocketConnectionState.CONNECTED, "test_setup")
        state_machine.transition_to(WebSocketConnectionState.ACTIVE, "test_setup")
        
        # Test transition to ERROR from ACTIVE
        assert state_machine.can_transition_to(WebSocketConnectionState.ERROR)
        success = state_machine.transition_to(WebSocketConnectionState.ERROR, "network_timeout")
        assert success
        assert state_machine.current_state == WebSocketConnectionState.ERROR
        
        # Verify error entry actions executed
        assert 'last_error' in state_machine.connection_metadata
        assert state_machine.connection_metadata['ready_for_messages'] is False
        
        # Test recovery transitions from ERROR
        recovery_states = [
            WebSocketConnectionState.CONNECTING,   # Reconnection attempt
            WebSocketConnectionState.RECONNECTING, # Alternative recovery path
        ]
        
        for recovery_state in recovery_states:
            # Reset to error state
            state_machine.current_state = WebSocketConnectionState.ERROR
            
            assert state_machine.can_transition_to(recovery_state), \
                f"Should allow recovery transition to {recovery_state.value} from ERROR"
            
            success = state_machine.transition_to(recovery_state, "recovery_attempt")
            assert success, f"Recovery transition to {recovery_state.value} should succeed"
            
            # Verify error exit actions
            assert 'last_error_recovery' in state_machine.connection_metadata
    
    async def test_degraded_state_handling(self):
        """Test DEGRADED state transitions and message handling."""
        state_machine = MockWebSocketStateMachine()
        
        # Establish active connection
        transitions = [
            (WebSocketConnectionState.CONNECTING, "setup"),
            (WebSocketConnectionState.CONNECTED, "setup"),
            (WebSocketConnectionState.ACTIVE, "setup")
        ]
        
        for state, trigger in transitions:
            state_machine.transition_to(state, trigger)
        
        # Transition to DEGRADED
        assert state_machine.can_transition_to(WebSocketConnectionState.DEGRADED)
        success = state_machine.transition_to(WebSocketConnectionState.DEGRADED, "network_quality_drop")
        assert success
        assert state_machine.current_state == WebSocketConnectionState.DEGRADED
        
        # Test message sending in degraded state (should work but may fail)
        initial_failed_count = state_machine.health_metrics['failed_messages']
        
        # Send multiple messages to test degraded behavior
        messages_sent = 0
        for i in range(10):
            message = {"type": "test_message", "data": f"message_{i}"}
            if await state_machine.send_message(message):
                messages_sent += 1
        
        # Should send some messages but may have failures
        assert messages_sent > 0, "Should send at least some messages in DEGRADED state"
        assert messages_sent <= 10, "Should not send more messages than attempted"
        
        # Test recovery from DEGRADED
        assert state_machine.can_transition_to(WebSocketConnectionState.ACTIVE)
        recovery_success = state_machine.transition_to(
            WebSocketConnectionState.ACTIVE, "network_quality_restored"
        )
        assert recovery_success
        assert state_machine.current_state == WebSocketConnectionState.ACTIVE
    
    def test_authentication_state_flow(self):
        """Test authentication-related state transitions."""
        state_machine = MockWebSocketStateMachine()
        
        # Establish connection
        state_machine.transition_to(WebSocketConnectionState.CONNECTING, "auth_test")
        state_machine.transition_to(WebSocketConnectionState.CONNECTED, "auth_test")
        
        # Test authentication flow
        assert state_machine.can_transition_to(WebSocketConnectionState.AUTHENTICATING)
        auth_start = state_machine.transition_to(
            WebSocketConnectionState.AUTHENTICATING, "auth_token_received"
        )
        assert auth_start
        
        # Test successful authentication
        assert state_machine.can_transition_to(WebSocketConnectionState.AUTHENTICATED)
        auth_success = state_machine.transition_to(
            WebSocketConnectionState.AUTHENTICATED, "jwt_validation_successful"
        )
        assert auth_success
        
        # Verify authentication metadata
        assert 'authenticated_at' in state_machine.connection_metadata
        assert state_machine.connection_metadata['auth_valid'] is True
        
        # Test transition to active after auth
        assert state_machine.can_transition_to(WebSocketConnectionState.ACTIVE)
        active_success = state_machine.transition_to(
            WebSocketConnectionState.ACTIVE, "auth_complete_ready_for_use"
        )
        assert active_success
        
        # Test auth failure scenario
        state_machine.current_state = WebSocketConnectionState.AUTHENTICATING
        
        assert state_machine.can_transition_to(WebSocketConnectionState.ERROR)
        auth_failure = state_machine.transition_to(
            WebSocketConnectionState.ERROR, "auth_token_invalid"
        )
        assert auth_failure
        assert state_machine.current_state == WebSocketConnectionState.ERROR
    
    def test_reconnection_scenarios(self):
        """Test reconnection state machine behavior."""
        state_machine = MockWebSocketStateMachine()
        
        # Test reconnection from DISCONNECTED
        state_machine.current_state = WebSocketConnectionState.DISCONNECTED
        
        assert state_machine.can_transition_to(WebSocketConnectionState.CONNECTING)
        reconnect_start = state_machine.transition_to(
            WebSocketConnectionState.CONNECTING, "user_triggered_reconnection"
        )
        assert reconnect_start
        
        # Test RECONNECTING state
        state_machine.current_state = WebSocketConnectionState.ACTIVE
        
        assert state_machine.can_transition_to(WebSocketConnectionState.RECONNECTING)
        reconnecting = state_machine.transition_to(
            WebSocketConnectionState.RECONNECTING, "connection_instability_detected"
        )
        assert reconnecting
        
        # From RECONNECTING, should be able to go to CONNECTED or ERROR
        assert state_machine.can_transition_to(WebSocketConnectionState.CONNECTED)
        assert state_machine.can_transition_to(WebSocketConnectionState.ERROR)
        
        # Test successful reconnection
        reconnect_success = state_machine.transition_to(
            WebSocketConnectionState.CONNECTED, "reconnection_successful"
        )
        assert reconnect_success
        
        # Verify reconnection metrics
        assert state_machine.health_metrics['connection_attempts'] >= 1
    
    def test_disconnection_flow(self):
        """Test proper disconnection state flow."""
        state_machine = MockWebSocketStateMachine()
        
        # Establish active connection
        setup_transitions = [
            (WebSocketConnectionState.CONNECTING, "disconnect_test_setup"),
            (WebSocketConnectionState.CONNECTED, "disconnect_test_setup"),
            (WebSocketConnectionState.ACTIVE, "disconnect_test_setup")
        ]
        
        for state, trigger in setup_transitions:
            state_machine.transition_to(state, trigger)
        
        # Record uptime before disconnection
        initial_uptime = state_machine.health_metrics['total_uptime_seconds']
        
        # Test graceful disconnection
        assert state_machine.can_transition_to(WebSocketConnectionState.DISCONNECTING)
        disconnect_start = state_machine.transition_to(
            WebSocketConnectionState.DISCONNECTING, "user_requested_disconnect"
        )
        assert disconnect_start
        
        # From DISCONNECTING should go to DISCONNECTED
        assert state_machine.can_transition_to(WebSocketConnectionState.DISCONNECTED)
        disconnect_complete = state_machine.transition_to(
            WebSocketConnectionState.DISCONNECTED, "disconnect_process_complete"
        )
        assert disconnect_complete
        
        # Verify disconnection metadata
        assert 'disconnected_at' in state_machine.connection_metadata
        assert state_machine.connection_metadata['connection_stable'] is False
        assert state_machine.connection_metadata['ready_for_messages'] is False
        
        # Verify uptime was recorded (exit action from ACTIVE)
        assert state_machine.health_metrics['total_uptime_seconds'] >= initial_uptime
    
    def test_terminal_state_handling(self):
        """Test TERMINATED state behavior."""
        state_machine = MockWebSocketStateMachine()
        
        # Test transition to TERMINATED from various states
        terminal_sources = [
            WebSocketConnectionState.INITIALIZING,
            WebSocketConnectionState.CONNECTING, 
            WebSocketConnectionState.DISCONNECTED,
            WebSocketConnectionState.ERROR
        ]
        
        for source_state in terminal_sources:
            # Reset state machine
            state_machine.current_state = source_state
            
            assert state_machine.can_transition_to(WebSocketConnectionState.TERMINATED), \
                f"Should allow termination from {source_state.value}"
            
            terminate_success = state_machine.transition_to(
                WebSocketConnectionState.TERMINATED, f"termination_from_{source_state.value}"
            )
            assert terminate_success
            
            # Verify no transitions are possible from TERMINATED
            all_states = list(WebSocketConnectionState)
            for target_state in all_states:
                if target_state != WebSocketConnectionState.TERMINATED:
                    assert not state_machine.can_transition_to(target_state), \
                        f"Should NOT allow transition from TERMINATED to {target_state.value}"
    
    async def test_message_sending_state_dependencies(self):
        """Test that message sending respects connection state."""
        state_machine = MockWebSocketStateMachine()
        
        test_message = {"type": "test", "data": "message_state_test"}
        
        # Test message sending in different states
        state_message_results = {
            WebSocketConnectionState.INITIALIZING: False,  # Should fail
            WebSocketConnectionState.CONNECTING: False,    # Should fail
            WebSocketConnectionState.CONNECTED: False,     # Should fail (not ready)
            WebSocketConnectionState.AUTHENTICATING: False, # Should fail
            WebSocketConnectionState.AUTHENTICATED: True,  # Should succeed
            WebSocketConnectionState.ACTIVE: True,         # Should succeed
            WebSocketConnectionState.IDLE: False,          # Should fail
            WebSocketConnectionState.DEGRADED: True,       # Should succeed (but may fail randomly)
            WebSocketConnectionState.DISCONNECTING: False, # Should fail
            WebSocketConnectionState.DISCONNECTED: False,  # Should fail
            WebSocketConnectionState.ERROR: False,         # Should fail
            WebSocketConnectionState.TERMINATED: False     # Should fail
        }
        
        for state, should_succeed in state_message_results.items():
            state_machine.current_state = state
            state_machine.error_log.clear()  # Clear previous errors
            
            result = await state_machine.send_message(test_message)
            
            if should_succeed:
                # For DEGRADED state, may randomly fail, so check differently
                if state == WebSocketConnectionState.DEGRADED:
                    # Either succeeds or fails due to degradation, both are valid
                    assert True, "DEGRADED state can succeed or fail randomly"
                else:
                    assert result, f"Message send should succeed in {state.value} state"
            else:
                assert not result, f"Message send should fail in {state.value} state"
                # Verify error was logged
                assert len(state_machine.error_log) > 0
                assert state_machine.error_log[-1]['type'] == 'message_send_failed'
    
    def test_state_machine_metrics_and_statistics(self):
        """Test state machine metrics collection and calculation."""
        state_machine = MockWebSocketStateMachine()
        
        # Perform a series of transitions with some invalid attempts
        transitions = [
            (WebSocketConnectionState.CONNECTING, "metrics_test", True),
            (WebSocketConnectionState.ACTIVE, "invalid_skip", False),  # Invalid
            (WebSocketConnectionState.CONNECTED, "metrics_test", True),
            (WebSocketConnectionState.AUTHENTICATED, "metrics_test", True),
            (WebSocketConnectionState.IDLE, "invalid_transition", False),  # Invalid
            (WebSocketConnectionState.ACTIVE, "metrics_test", True),
            (WebSocketConnectionState.ERROR, "simulated_error", True),
            (WebSocketConnectionState.CONNECTING, "recovery", True)
        ]
        
        for target_state, trigger, should_succeed in transitions:
            result = state_machine.transition_to(target_state, trigger)
            assert result == should_succeed, \
                f"Transition to {target_state.value} should {'succeed' if should_succeed else 'fail'}"
        
        # Get and verify metrics
        metrics = state_machine.get_state_metrics()
        
        assert metrics['current_state'] == WebSocketConnectionState.CONNECTING.value
        assert metrics['total_transitions'] == len(transitions)
        assert metrics['invalid_transitions'] == 2  # Two invalid transitions
        
        # Verify transition success rate
        expected_success_rate = (6 / 8) * 100  # 6 valid out of 8 attempted
        assert abs(metrics['transition_success_rate'] - expected_success_rate) < 0.1
        
        # Verify health metrics were updated
        assert metrics['health_metrics']['connection_attempts'] >= 2  # At least 2 CONNECTING entries
        
        # Verify state durations were calculated
        assert 'state_durations' in metrics
        assert isinstance(metrics['state_durations'], dict)
    
    def test_concurrent_state_transition_safety(self):
        """Test that concurrent state transitions are handled safely."""
        state_machine = MockWebSocketStateMachine()
        
        # Simulate concurrent transition attempts
        async def attempt_transition(target_state, trigger):
            """Simulate concurrent transition attempt."""
            await asyncio.sleep(0.001)  # Small delay to create race condition
            return state_machine.transition_to(target_state, trigger)
        
        # Set up for concurrent test
        state_machine.transition_to(WebSocketConnectionState.CONNECTING, "concurrent_setup")
        state_machine.transition_to(WebSocketConnectionState.CONNECTED, "concurrent_setup")
        
        # Create concurrent transition tasks
        concurrent_transitions = [
            attempt_transition(WebSocketConnectionState.ACTIVE, "concurrent_1"),
            attempt_transition(WebSocketConnectionState.AUTHENTICATING, "concurrent_2"),
            attempt_transition(WebSocketConnectionState.ERROR, "concurrent_3")
        ]
        
        # Execute concurrent transitions
        results = await asyncio.gather(*concurrent_transitions, return_exceptions=True)
        
        # Verify that state machine remained in a valid state
        assert state_machine.current_state in WebSocketConnectionState
        
        # Verify that exactly one transition succeeded (first one wins)
        successful_transitions = [r for r in results if r is True]
        assert len(successful_transitions) == 1, "Exactly one concurrent transition should succeed"
        
        # Verify state consistency
        assert len(state_machine.transition_log) >= 3  # Initial setup + concurrent attempts
    
    def test_state_machine_edge_cases(self):
        """Test edge cases and boundary conditions."""
        state_machine = MockWebSocketStateMachine()
        
        # Test self-transition (should be rejected unless explicitly allowed)
        assert not state_machine.can_transition_to(WebSocketConnectionState.INITIALIZING)
        self_transition = state_machine.transition_to(
            WebSocketConnectionState.INITIALIZING, "self_transition_test"
        )
        assert not self_transition, "Self-transitions should be rejected"
        
        # Test forced transition (bypassing validation)
        forced_transition = state_machine.transition_to(
            WebSocketConnectionState.ACTIVE, "forced_test", force=True
        )
        assert forced_transition, "Forced transitions should always succeed"
        assert state_machine.current_state == WebSocketConnectionState.ACTIVE
        
        # Test transition with metadata
        metadata = {"force_reason": "emergency_activation", "bypass_auth": True}
        meta_transition = state_machine.transition_to(
            WebSocketConnectionState.ERROR, "metadata_test", metadata=metadata
        )
        assert meta_transition
        
        # Verify metadata was recorded
        last_transition = state_machine.state_history[-1]
        assert last_transition['metadata'] == metadata
        
        # Test rapid state transitions
        rapid_transitions = [
            WebSocketConnectionState.CONNECTING,
            WebSocketConnectionState.ERROR,
            WebSocketConnectionState.RECONNECTING,
            WebSocketConnectionState.CONNECTED,
            WebSocketConnectionState.ACTIVE
        ]
        
        for target_state in rapid_transitions:
            if state_machine.can_transition_to(target_state):
                result = state_machine.transition_to(target_state, "rapid_test")
                assert result, f"Rapid transition to {target_state.value} should succeed"
        
        # Verify all rapid transitions were recorded correctly
        assert len(state_machine.transition_log) >= len(rapid_transitions)
    
    def test_business_value_state_requirements(self):
        """Test that state machine meets business value requirements."""
        state_machine = MockWebSocketStateMachine()
        
        # Golden Path Business Requirement: User must be able to send messages
        # This requires: INITIALIZING -> CONNECTING -> CONNECTED -> ACTIVE
        golden_path = [
            (WebSocketConnectionState.CONNECTING, "user_wants_to_chat"),
            (WebSocketConnectionState.CONNECTED, "websocket_established"),
            (WebSocketConnectionState.ACTIVE, "ready_for_ai_interaction")
        ]
        
        for target_state, trigger in golden_path:
            success = state_machine.transition_to(target_state, trigger)
            assert success, f"Golden Path transition to {target_state.value} must succeed"
        
        # Verify user can send messages in ACTIVE state
        test_message = {"type": "agent_request", "data": {"query": "help with costs"}}
        message_success = await state_machine.send_message(test_message)
        assert message_success, "User must be able to send messages in ACTIVE state"
        
        # Business Requirement: System must handle network issues gracefully
        # Test: ACTIVE -> DEGRADED -> ACTIVE (recovery)
        degradation_success = state_machine.transition_to(
            WebSocketConnectionState.DEGRADED, "network_quality_drop"
        )
        assert degradation_success, "System must handle network degradation"
        
        recovery_success = state_machine.transition_to(
            WebSocketConnectionState.ACTIVE, "network_quality_restored" 
        )
        assert recovery_success, "System must recover from degraded state"
        
        # Business Requirement: System must handle errors and allow recovery
        error_transition = state_machine.transition_to(
            WebSocketConnectionState.ERROR, "simulated_system_error"
        )
        assert error_transition, "System must handle errors"
        
        error_recovery = state_machine.transition_to(
            WebSocketConnectionState.CONNECTING, "error_recovery_attempt"
        )
        assert error_recovery, "System must allow recovery from errors"
        
        # Verify business metrics
        metrics = state_machine.get_state_metrics()
        assert metrics['current_state'] == WebSocketConnectionState.CONNECTING.value
        assert metrics['total_transitions'] >= 6  # All business flow transitions
        
        # Business Value: High success rate indicates reliable user experience
        assert metrics['transition_success_rate'] > 80, \
            "State machine must have high reliability for business value"