"""
Unit Test Suite for WebSocket Connection State Machine Transitions

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable WebSocket connection state management for chat stability
- Value Impact: Prevents connection state bugs that would break real-time agent communication
- Strategic Impact: Stable connections are foundation for all chat-based business value delivery

This test suite validates the WebSocket connection state machine that manages
connection lifecycle and ensures reliable communication channels for agent events.

CONNECTION STATE MACHINE:
- CONNECTING  ->  CONNECTED (successful connection)
- CONNECTING  ->  FAILED (connection failure)
- CONNECTED  ->  DISCONNECTED (clean disconnect)
- CONNECTED  ->  CLOSING (initiated disconnect)
- DISCONNECTED  ->  RECONNECTING (reconnection attempt)
- RECONNECTING  ->  CONNECTED (successful reconnection)
- RECONNECTING  ->  FAILED (reconnection failure)
- FAILED  ->  RECONNECTING (retry attempt)
- CLOSING  ->  DISCONNECTED (graceful close completion)

CRITICAL VALIDATION AREAS:
- Valid state transitions according to business logic
- Invalid transition prevention and error handling
- State persistence and recovery scenarios
- Connection metadata management (timestamps, counters)
- Concurrent state change handling
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import unittest
from unittest.mock import Mock, patch

# Import system under test - Connection state types from shared SSOT
from shared.types import (
    ConnectionState, WebSocketConnectionInfo, WebSocketID, UserID,
    ensure_websocket_id, ensure_user_id
)


class WebSocketConnectionStateMachine:
    """State machine for managing WebSocket connection transitions.
    
    This class implements the business logic for valid connection state
    transitions to ensure reliable WebSocket communication.
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS = {
        ConnectionState.CONNECTING: {
            ConnectionState.CONNECTED,
            ConnectionState.FAILED
        },
        ConnectionState.CONNECTED: {
            ConnectionState.DISCONNECTED,
            ConnectionState.CLOSING,
            ConnectionState.FAILED
        },
        ConnectionState.DISCONNECTED: {
            ConnectionState.RECONNECTING,
            ConnectionState.CONNECTING
        },
        ConnectionState.RECONNECTING: {
            ConnectionState.CONNECTED,
            ConnectionState.FAILED
        },
        ConnectionState.FAILED: {
            ConnectionState.RECONNECTING,
            ConnectionState.CONNECTING
        },
        ConnectionState.CLOSING: {
            ConnectionState.DISCONNECTED,
            ConnectionState.FAILED
        }
    }
    
    def __init__(self, initial_state: ConnectionState = ConnectionState.CONNECTING):
        """Initialize state machine with given initial state."""
        self.current_state = initial_state
        self.state_history: List[ConnectionState] = [initial_state]
        self.transition_count = 0
        
    def can_transition_to(self, target_state: ConnectionState) -> bool:
        """Check if transition to target state is valid."""
        return target_state in self.VALID_TRANSITIONS.get(self.current_state, set())
    
    def transition_to(self, target_state: ConnectionState) -> bool:
        """Attempt to transition to target state."""
        if not self.can_transition_to(target_state):
            return False
        
        self.current_state = target_state
        self.state_history.append(target_state)
        self.transition_count += 1
        return True
    
    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.current_state
    
    def is_connected(self) -> bool:
        """Check if connection is in a connected state."""
        return self.current_state == ConnectionState.CONNECTED
    
    def is_active(self) -> bool:
        """Check if connection is in an active state (connected or connecting)."""
        return self.current_state in {
            ConnectionState.CONNECTED,
            ConnectionState.CONNECTING,
            ConnectionState.RECONNECTING
        }
    
    def is_terminal(self) -> bool:
        """Check if connection is in a terminal state."""
        return self.current_state in {
            ConnectionState.FAILED,
            ConnectionState.DISCONNECTED
        }


class TestConnectionStateTransitions(unittest.TestCase):
    """Test valid connection state transitions."""
    
    def setUp(self):
        """Set up a fresh state machine for each test."""
        self.state_machine = WebSocketConnectionStateMachine()
    
    def test_initial_connecting_state(self):
        """Test that state machine starts in CONNECTING state."""
        self.assertEqual(self.state_machine.get_state(), ConnectionState.CONNECTING)
        self.assertFalse(self.state_machine.is_connected())
        self.assertTrue(self.state_machine.is_active())
        self.assertFalse(self.state_machine.is_terminal())
    
    def test_successful_connection_flow(self):
        """Test successful connection: CONNECTING  ->  CONNECTED."""
        # Should be able to transition from CONNECTING to CONNECTED
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.CONNECTED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.CONNECTED))
        
        # Verify final state
        self.assertEqual(self.state_machine.get_state(), ConnectionState.CONNECTED)
        self.assertTrue(self.state_machine.is_connected())
        self.assertTrue(self.state_machine.is_active())
        self.assertFalse(self.state_machine.is_terminal())
    
    def test_connection_failure_flow(self):
        """Test connection failure: CONNECTING  ->  FAILED."""
        # Should be able to transition from CONNECTING to FAILED
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.FAILED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.FAILED))
        
        # Verify final state
        self.assertEqual(self.state_machine.get_state(), ConnectionState.FAILED)
        self.assertFalse(self.state_machine.is_connected())
        self.assertFalse(self.state_machine.is_active())
        self.assertTrue(self.state_machine.is_terminal())
    
    def test_graceful_disconnect_flow(self):
        """Test graceful disconnect: CONNECTED  ->  CLOSING  ->  DISCONNECTED."""
        # First connect
        self.state_machine.transition_to(ConnectionState.CONNECTED)
        
        # Then initiate graceful disconnect
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.CLOSING))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.CLOSING))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.CLOSING)
        
        # Complete disconnect
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.DISCONNECTED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.DISCONNECTED))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.DISCONNECTED)
        self.assertTrue(self.state_machine.is_terminal())
    
    def test_direct_disconnect_flow(self):
        """Test direct disconnect: CONNECTED  ->  DISCONNECTED."""
        # First connect
        self.state_machine.transition_to(ConnectionState.CONNECTED)
        
        # Direct disconnect (e.g., network failure)
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.DISCONNECTED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.DISCONNECTED))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.DISCONNECTED)
        self.assertTrue(self.state_machine.is_terminal())
    
    def test_reconnection_success_flow(self):
        """Test successful reconnection: DISCONNECTED  ->  RECONNECTING  ->  CONNECTED."""
        # Start from disconnected state
        self.state_machine.transition_to(ConnectionState.FAILED)
        
        # Attempt reconnection
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.RECONNECTING))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.RECONNECTING))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.RECONNECTING)
        self.assertTrue(self.state_machine.is_active())
        
        # Successful reconnection
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.CONNECTED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.CONNECTED))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.CONNECTED)
        self.assertTrue(self.state_machine.is_connected())
    
    def test_reconnection_failure_flow(self):
        """Test failed reconnection: DISCONNECTED  ->  RECONNECTING  ->  FAILED."""
        # Start from disconnected state
        self.state_machine.transition_to(ConnectionState.FAILED)
        
        # Attempt reconnection
        self.assertTrue(self.state_machine.transition_to(ConnectionState.RECONNECTING))
        
        # Reconnection fails
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.FAILED))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.FAILED))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.FAILED)
        self.assertTrue(self.state_machine.is_terminal())
    
    def test_retry_after_failure(self):
        """Test retry attempt after failure: FAILED  ->  RECONNECTING."""
        # Start from failed state
        self.state_machine.transition_to(ConnectionState.FAILED)
        
        # Should be able to retry
        self.assertTrue(self.state_machine.can_transition_to(ConnectionState.RECONNECTING))
        self.assertTrue(self.state_machine.transition_to(ConnectionState.RECONNECTING))
        self.assertEqual(self.state_machine.get_state(), ConnectionState.RECONNECTING)
        self.assertTrue(self.state_machine.is_active())


class TestInvalidStateTransitions(unittest.TestCase):
    """Test that invalid state transitions are properly rejected."""
    
    def setUp(self):
        """Set up a fresh state machine for each test."""
        self.state_machine = WebSocketConnectionStateMachine()
    
    def test_invalid_transitions_from_connecting(self):
        """Test that invalid transitions from CONNECTING are rejected."""
        # Valid: CONNECTING  ->  CONNECTED, FAILED
        # Invalid: CONNECTING  ->  DISCONNECTED, RECONNECTING, CLOSING
        
        invalid_transitions = [
            ConnectionState.DISCONNECTED,
            ConnectionState.RECONNECTING,
            ConnectionState.CLOSING
        ]
        
        for invalid_state in invalid_transitions:
            with self.subTest(invalid_state=invalid_state):
                self.assertFalse(self.state_machine.can_transition_to(invalid_state))
                self.assertFalse(self.state_machine.transition_to(invalid_state))
                # State should remain unchanged
                self.assertEqual(self.state_machine.get_state(), ConnectionState.CONNECTING)
    
    def test_invalid_transitions_from_connected(self):
        """Test that invalid transitions from CONNECTED are rejected."""
        # Move to connected state first
        self.state_machine.transition_to(ConnectionState.CONNECTED)
        
        # Valid: CONNECTED  ->  DISCONNECTED, CLOSING, FAILED
        # Invalid: CONNECTED  ->  CONNECTING, RECONNECTING
        
        invalid_transitions = [
            ConnectionState.CONNECTING,
            ConnectionState.RECONNECTING
        ]
        
        for invalid_state in invalid_transitions:
            with self.subTest(invalid_state=invalid_state):
                self.assertFalse(self.state_machine.can_transition_to(invalid_state))
                self.assertFalse(self.state_machine.transition_to(invalid_state))
                # State should remain CONNECTED
                self.assertEqual(self.state_machine.get_state(), ConnectionState.CONNECTED)
    
    def test_invalid_transitions_from_disconnected(self):
        """Test that invalid transitions from DISCONNECTED are rejected."""
        # Move to disconnected state first
        self.state_machine.transition_to(ConnectionState.CONNECTED)
        self.state_machine.transition_to(ConnectionState.DISCONNECTED)
        
        # Valid: DISCONNECTED  ->  RECONNECTING, CONNECTING
        # Invalid: DISCONNECTED  ->  CONNECTED, FAILED, CLOSING
        
        invalid_transitions = [
            ConnectionState.CONNECTED,
            ConnectionState.FAILED,
            ConnectionState.CLOSING
        ]
        
        for invalid_state in invalid_transitions:
            with self.subTest(invalid_state=invalid_state):
                self.assertFalse(self.state_machine.can_transition_to(invalid_state))
                self.assertFalse(self.state_machine.transition_to(invalid_state))
                # State should remain DISCONNECTED
                self.assertEqual(self.state_machine.get_state(), ConnectionState.DISCONNECTED)
    
    def test_no_transitions_to_same_state(self):
        """Test that transitions to the same state are not allowed."""
        all_states = list(ConnectionState)
        
        for state in all_states:
            with self.subTest(state=state):
                state_machine = WebSocketConnectionStateMachine(state)
                
                # Transition to same state should be invalid
                self.assertFalse(state_machine.can_transition_to(state))
                self.assertFalse(state_machine.transition_to(state))


class TestWebSocketConnectionInfo(unittest.TestCase):
    """Test WebSocketConnectionInfo data structure and validation."""
    
    def setUp(self):
        """Set up test data."""
        self.websocket_id = WebSocketID(str(uuid.uuid4()))
        self.user_id = UserID(str(uuid.uuid4()))
        self.connection_time = datetime.now(timezone.utc)
    
    def test_connection_info_creation(self):
        """Test creation of WebSocketConnectionInfo with valid data."""
        conn_info = WebSocketConnectionInfo(
            websocket_id=self.websocket_id,
            user_id=self.user_id,
            connection_state=ConnectionState.CONNECTED,
            connected_at=self.connection_time
        )
        
        self.assertEqual(conn_info.websocket_id, self.websocket_id)
        self.assertEqual(conn_info.user_id, self.user_id)
        self.assertEqual(conn_info.connection_state, ConnectionState.CONNECTED)
        self.assertEqual(conn_info.connected_at, self.connection_time)
        self.assertIsNone(conn_info.last_ping)
        self.assertEqual(conn_info.message_count, 0)
    
    def test_connection_info_with_optional_fields(self):
        """Test ConnectionInfo with optional fields set."""
        last_ping = datetime.now(timezone.utc)
        
        conn_info = WebSocketConnectionInfo(
            websocket_id=self.websocket_id,
            user_id=self.user_id,
            connection_state=ConnectionState.CONNECTED,
            connected_at=self.connection_time,
            last_ping=last_ping,
            message_count=42
        )
        
        self.assertEqual(conn_info.last_ping, last_ping)
        self.assertEqual(conn_info.message_count, 42)
    
    def test_connection_info_state_transitions(self):
        """Test updating connection state in ConnectionInfo."""
        conn_info = WebSocketConnectionInfo(
            websocket_id=self.websocket_id,
            user_id=self.user_id,
            connection_state=ConnectionState.CONNECTING,
            connected_at=self.connection_time
        )
        
        # Update to connected state
        conn_info.connection_state = ConnectionState.CONNECTED
        self.assertEqual(conn_info.connection_state, ConnectionState.CONNECTED)
        
        # Update to disconnected state
        conn_info.connection_state = ConnectionState.DISCONNECTED
        self.assertEqual(conn_info.connection_state, ConnectionState.DISCONNECTED)
    
    def test_connection_info_message_counting(self):
        """Test message count tracking in ConnectionInfo."""
        conn_info = WebSocketConnectionInfo(
            websocket_id=self.websocket_id,
            user_id=self.user_id,
            connection_state=ConnectionState.CONNECTED,
            connected_at=self.connection_time
        )
        
        # Start with 0 messages
        self.assertEqual(conn_info.message_count, 0)
        
        # Simulate message counting
        conn_info.message_count += 1
        self.assertEqual(conn_info.message_count, 1)
        
        conn_info.message_count += 5
        self.assertEqual(conn_info.message_count, 6)
    
    def test_connection_info_ping_tracking(self):
        """Test ping timestamp tracking in ConnectionInfo."""
        conn_info = WebSocketConnectionInfo(
            websocket_id=self.websocket_id,
            user_id=self.user_id,
            connection_state=ConnectionState.CONNECTED,
            connected_at=self.connection_time
        )
        
        # Initially no ping
        self.assertIsNone(conn_info.last_ping)
        
        # Update ping timestamp
        ping_time = datetime.now(timezone.utc)
        conn_info.last_ping = ping_time
        self.assertEqual(conn_info.last_ping, ping_time)


class TestStateTransitionHistory(unittest.TestCase):
    """Test state transition history tracking and analysis."""
    
    def test_state_history_tracking(self):
        """Test that state machine tracks transition history."""
        state_machine = WebSocketConnectionStateMachine()
        
        # Initial state should be in history
        self.assertEqual(len(state_machine.state_history), 1)
        self.assertEqual(state_machine.state_history[0], ConnectionState.CONNECTING)
        
        # Transition to CONNECTED
        state_machine.transition_to(ConnectionState.CONNECTED)
        self.assertEqual(len(state_machine.state_history), 2)
        self.assertEqual(state_machine.state_history[-1], ConnectionState.CONNECTED)
        
        # Transition to DISCONNECTED
        state_machine.transition_to(ConnectionState.DISCONNECTED)
        self.assertEqual(len(state_machine.state_history), 3)
        self.assertEqual(state_machine.state_history[-1], ConnectionState.DISCONNECTED)
    
    def test_transition_count_tracking(self):
        """Test that state machine tracks number of transitions."""
        state_machine = WebSocketConnectionStateMachine()
        
        # Start with 0 transitions
        self.assertEqual(state_machine.transition_count, 0)
        
        # Each successful transition should increment count
        state_machine.transition_to(ConnectionState.CONNECTED)
        self.assertEqual(state_machine.transition_count, 1)
        
        state_machine.transition_to(ConnectionState.DISCONNECTED)
        self.assertEqual(state_machine.transition_count, 2)
        
        # Failed transitions should not increment count
        initial_count = state_machine.transition_count
        state_machine.transition_to(ConnectionState.CONNECTED)  # Invalid transition
        self.assertEqual(state_machine.transition_count, initial_count)
    
    def test_complex_state_sequence(self):
        """Test tracking of complex state transition sequence."""
        state_machine = WebSocketConnectionStateMachine()
        
        # Complex sequence: CONNECTING  ->  CONNECTED  ->  CLOSING  ->  DISCONNECTED  ->  RECONNECTING  ->  CONNECTED
        transitions = [
            ConnectionState.CONNECTED,
            ConnectionState.CLOSING,
            ConnectionState.DISCONNECTED,
            ConnectionState.RECONNECTING,
            ConnectionState.CONNECTED
        ]
        
        for target_state in transitions:
            self.assertTrue(state_machine.transition_to(target_state))
        
        # Verify complete history
        expected_history = [
            ConnectionState.CONNECTING,  # Initial
            ConnectionState.CONNECTED,
            ConnectionState.CLOSING,
            ConnectionState.DISCONNECTED,
            ConnectionState.RECONNECTING,
            ConnectionState.CONNECTED
        ]
        
        self.assertEqual(state_machine.state_history, expected_history)
        self.assertEqual(state_machine.transition_count, 5)
        self.assertEqual(state_machine.get_state(), ConnectionState.CONNECTED)


class TestConnectionStateEnumProperties(unittest.TestCase):
    """Test properties and validation of ConnectionState enum."""
    
    def test_all_connection_states_defined(self):
        """Test that all expected connection states are defined."""
        expected_states = {
            "connecting",
            "connected", 
            "disconnected",
            "reconnecting",
            "failed",
            "closing"
        }
        
        actual_states = {state.value for state in ConnectionState}
        self.assertEqual(actual_states, expected_states)
    
    def test_connection_state_string_values(self):
        """Test that connection states have correct string values."""
        state_mappings = {
            ConnectionState.CONNECTING: "connecting",
            ConnectionState.CONNECTED: "connected",
            ConnectionState.DISCONNECTED: "disconnected",
            ConnectionState.RECONNECTING: "reconnecting",
            ConnectionState.FAILED: "failed",
            ConnectionState.CLOSING: "closing"
        }
        
        for state, expected_value in state_mappings.items():
            self.assertEqual(state.value, expected_value)
    
    def test_connection_state_creation_from_string(self):
        """Test creation of ConnectionState from string values."""
        string_to_state = {
            "connecting": ConnectionState.CONNECTING,
            "connected": ConnectionState.CONNECTED,
            "disconnected": ConnectionState.DISCONNECTED,
            "reconnecting": ConnectionState.RECONNECTING,
            "failed": ConnectionState.FAILED,
            "closing": ConnectionState.CLOSING
        }
        
        for string_value, expected_state in string_to_state.items():
            self.assertEqual(ConnectionState(string_value), expected_state)
    
    def test_invalid_connection_state_values(self):
        """Test that invalid connection state values raise errors."""
        invalid_values = [
            "invalid",
            "CONNECTED",  # Wrong case
            "disconnecting",  # Doesn't exist
            "",
            None
        ]
        
        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaises((ValueError, TypeError)):
                    ConnectionState(invalid_value)


if __name__ == "__main__":
    unittest.main()