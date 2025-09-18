"""
Test WebSocket Connection State Transitions for Issue #1061

These tests validate that the WebSocket connection lifecycle properly transitions through
all required states: CONNECTING -> ACCEPTED -> AUTHENTICATED -> SERVICES_READY -> PROCESSING_READY

This addresses Issue #1061: WebSocket connection lifecycle error where ACCEPT state is never
properly sent, causing 100% of WebSocket connections to fail on production.

Business Value Justification:
- Segment: Platform/Critical
- Business Goal: Restore Golden Path functionality (users login → get AI responses)
- Value Impact: Prevents 100% WebSocket connection failures in production
- Revenue Impact: Critical for $500K+ ARR dependency on chat functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.websocket_core.connection_state_machine import (
    ConnectionStateMachine,
    ConnectionStateMachineRegistry,
    ApplicationConnectionState,
    get_connection_state_registry
)
from shared.types.core_types import UserID, ConnectionID
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketStateTransitions(SSotAsyncTestCase):
    """Test proper WebSocket connection state transitions to fix Issue #1061."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.connection_id = "test_connection_123"
        self.user_id = "test_user_456"
        self.registry = ConnectionStateMachineRegistry()
        
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Alternative setup method for pytest compatibility."""
        self.connection_id = "test_connection_123"
        self.user_id = "test_user_456"
        self.registry = ConnectionStateMachineRegistry()
        
    def test_connection_state_machine_initialization(self):
        """Test that connection state machine can be properly initialized."""
        # Create state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Verify initial state
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.CONNECTING)
        self.assertEqual(state_machine.connection_id, self.connection_id)
        self.assertEqual(state_machine.user_id, self.user_id)
        
    def test_accepted_state_transition(self):
        """Test transition to ACCEPTED state after WebSocket transport is ready."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Transition to ACCEPTED state (this is what Issue #1061 was missing)
        success = state_machine.transition_to(
            ApplicationConnectionState.ACCEPTED,
            reason="WebSocket transport accepted",
            metadata={"connection_id": self.connection_id, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        # Verify transition succeeded
        self.assertTrue(success)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.ACCEPTED)
        
    def test_full_state_transition_sequence(self):
        """Test the complete state transition sequence that fixes Issue #1061."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Step 1: CONNECTING -> ACCEPTED (WebSocket transport ready)
        success1 = state_machine.transition_to(
            ApplicationConnectionState.ACCEPTED,
            reason="WebSocket transport accepted",
            metadata={"connection_id": self.connection_id}
        )
        self.assertTrue(success1)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.ACCEPTED)
        
        # Step 2: ACCEPTED -> AUTHENTICATED (User authentication complete)
        success2 = state_machine.transition_to(
            ApplicationConnectionState.AUTHENTICATED,
            reason="User authentication completed",
            metadata={"connection_id": self.connection_id, "user_id": self.user_id}
        )
        self.assertTrue(success2)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.AUTHENTICATED)
        
        # Step 3: AUTHENTICATED -> SERVICES_READY (Services initialized)
        success3 = state_machine.transition_to(
            ApplicationConnectionState.SERVICES_READY,
            reason="WebSocket manager and agent handlers initialized",
            metadata={"connection_id": self.connection_id}
        )
        self.assertTrue(success3)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.SERVICES_READY)
        
        # Step 4: SERVICES_READY -> PROCESSING_READY (Fully operational)
        success4 = state_machine.transition_to(
            ApplicationConnectionState.PROCESSING_READY,
            reason="Connection fully operational for message processing",
            metadata={"connection_id": self.connection_id, "golden_path_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]}
        )
        self.assertTrue(success4)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.PROCESSING_READY)
        
    def test_message_processing_readiness_validation(self):
        """Test that can_process_messages() works correctly with proper state transitions."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Initially should not be ready for messages
        self.assertFalse(state_machine.can_process_messages())
        
        # Should not be ready in ACCEPTED state
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED)
        self.assertFalse(state_machine.can_process_messages())
        
        # Should not be ready in AUTHENTICATED state
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        self.assertFalse(state_machine.can_process_messages())
        
        # Should not be ready in SERVICES_READY state
        state_machine.transition_to(ApplicationConnectionState.SERVICES_READY)
        self.assertFalse(state_machine.can_process_messages())
        
        # Should be ready in PROCESSING_READY state (this is the fix for Issue #1061)
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        self.assertTrue(state_machine.can_process_messages())
        
    def test_invalid_state_transitions_are_rejected(self):
        """Test that invalid state transitions are properly rejected."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Try to jump directly to PROCESSING_READY (should fail)
        success = state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        self.assertFalse(success)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.CONNECTING)
        
        # Try to skip ACCEPTED state and go directly to AUTHENTICATED (should fail)
        success = state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        self.assertFalse(success)
        self.assertEqual(state_machine.current_state, ApplicationConnectionState.CONNECTING)
        
    def test_state_transition_history_tracking(self):
        """Test that state transitions are properly tracked for debugging."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Perform a transition
        state_machine.transition_to(
            ApplicationConnectionState.ACCEPTED,
            reason="Test transition",
            metadata={"test": "value"}
        )
        
        # Verify transition was recorded
        self.assertTrue(len(state_machine._state_history) > 0)
        last_transition = state_machine._state_history[-1]
        self.assertEqual(last_transition.from_state, ApplicationConnectionState.CONNECTING)
        self.assertEqual(last_transition.to_state, ApplicationConnectionState.ACCEPTED)
        self.assertEqual(last_transition.reason, "Test transition")
        self.assertEqual(last_transition.metadata["test"], "value")
        
    def test_registry_get_connection_by_id(self):
        """Test that registry can retrieve connection state machines by ID."""
        # Register a connection
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Retrieve by ID
        retrieved = self.registry.get_connection_state_machine(self.connection_id)
        
        # Verify same instance
        self.assertIs(state_machine, retrieved)
        
    def test_duplicate_connection_registration_handling(self):
        """Test that duplicate connection registrations are handled properly."""
        # Register a connection
        state_machine1 = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Try to register the same connection again
        state_machine2 = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Should return the same instance to prevent state corruption
        self.assertIs(state_machine1, state_machine2)
        
    def test_degraded_mode_message_processing(self):
        """Test message processing capability in degraded mode."""
        # Create and register state machine
        state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        
        # Transition to DEGRADED state after some setup
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED)
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        state_machine.transition_to(ApplicationConnectionState.DEGRADED)
        
        # Should still be able to process messages in degraded mode
        # But only if minimum setup phases are completed (ACCEPTED + AUTHENTICATED)
        self.assertTrue(state_machine.can_process_messages())


class TestWebSocketStateTransitionIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket state transitions with the actual validation function."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.connection_id = "integration_test_123"
        self.user_id = "integration_user_456"
        
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Alternative setup method for pytest compatibility."""
        self.connection_id = "integration_test_123"
        self.user_id = "integration_user_456"
        
    @patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine')
    def test_is_websocket_connected_and_ready_with_proper_state(self, mock_get_state_machine):
        """Test that is_websocket_connected_and_ready works with proper state transitions."""
        from netra_backend.app.websocket_core.utils import is_websocket_connected_and_ready
        from fastapi import WebSocket
        from starlette.websockets import WebSocketState
        
        # Create mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.receive = Mock()
        mock_websocket.send = Mock()
        
        # Create state machine with proper state
        registry = ConnectionStateMachineRegistry()
        state_machine = registry.register_connection(self.connection_id, self.user_id)
        
        # Simulate proper state transitions (the fix for Issue #1061)
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED)
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        state_machine.transition_to(ApplicationConnectionState.SERVICES_READY)
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        
        # Mock the state machine retrieval
        mock_get_state_machine.return_value = state_machine
        
        # Test that connection is ready when state machine is in PROCESSING_READY state
        result = is_websocket_connected_and_ready(mock_websocket, self.connection_id)
        
        # Should return True with proper state transitions
        self.assertTrue(result)
        
    @patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine')
    def test_is_websocket_connected_and_ready_with_incomplete_state(self, mock_get_state_machine):
        """Test that connections not in PROCESSING_READY state are considered not ready."""
        from netra_backend.app.websocket_core.utils import is_websocket_connected_and_ready
        from fastapi import WebSocket
        from starlette.websockets import WebSocketState
        
        # Create mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.receive = Mock()
        mock_websocket.send = Mock()
        
        # Create state machine but don't complete all transitions (simulates Issue #1061)
        registry = ConnectionStateMachineRegistry()
        state_machine = registry.register_connection(self.connection_id, self.user_id)
        
        # Only transition to AUTHENTICATED (missing ACCEPT state - this was the bug)
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        
        # Mock the state machine retrieval
        mock_get_state_machine.return_value = state_machine
        
        # Test that connection is NOT ready when state transitions are incomplete
        result = is_websocket_connected_and_ready(mock_websocket, self.connection_id)
        
        # Should return False because state machine is not in PROCESSING_READY state
        self.assertFalse(result)


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])