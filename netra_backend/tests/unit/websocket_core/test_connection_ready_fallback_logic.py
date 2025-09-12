"""
Test 5: Connection Ready Fallback Logic Bug

This test reproduces the WebSocket race condition bug identified in the Golden Path analysis:
When is_connection_ready_for_messages() is called with a non-existent connection,
it incorrectly returns True instead of False.

Bug Location: connection_state_machine.py:816
Bug Code: return True  # Should be return False

This bug allows message processing to proceed even when the connection
doesn't exist, leading to race conditions and silent failures.

Business Impact: $500K+ ARR dependency - chat functionality failures
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import ConnectionID
from netra_backend.app.websocket_core.connection_state_machine import (
    is_connection_ready_for_messages,
    get_connection_state_machine
)


class TestConnectionReadyFallbackLogic(SSotBaseTestCase):
    """Test suite to reproduce the connection ready fallback logic bug."""

    def test_connection_ready_non_existent_connection_should_return_false_but_returns_true(self):
        """
         ALERT:  BUG REPRODUCTION: is_connection_ready_for_messages() with non-existent connection
        
        Expected Behavior: Should return False for non-existent connections
        Actual Behavior: Incorrectly returns True (the bug)
        
        This test SHOULD FAIL with current code, proving the bug exists.
        """
        # ARRANGE: Create a connection ID that doesn't exist
        non_existent_connection_id = ConnectionID(str(uuid.uuid4()))
        
        # Verify the connection doesn't exist by checking state machine is None
        machine = get_connection_state_machine(non_existent_connection_id)
        assert machine is None, "Test setup failed: connection should not exist"
        
        # ACT: Check if the non-existent connection is ready for messages
        result = is_connection_ready_for_messages(non_existent_connection_id)
        
        # ASSERT: This should be False but will be True due to the bug
        #  ALERT:  THIS TEST WILL FAIL - proving the bug exists
        assert result is False, (
            "BUG CONFIRMED: is_connection_ready_for_messages() returned True for non-existent connection. "
            "This is the fallback logic bug identified in Golden Path analysis. "
            "Bug location: connection_state_machine.py:816 should return False, not True"
        )
        
        # Record the bug detection metric
        self.record_metric("bug_detected", "connection_ready_fallback_logic")
        self.record_metric("bug_location", "connection_state_machine.py:816")
        self.record_metric("expected_result", False)
        self.record_metric("actual_result", result)

    def test_connection_ready_with_registered_connection_returns_machine_result(self):
        """
        Test that when a connection exists, the function properly delegates to the state machine.
        
        This test should PASS and shows the intended behavior when connections exist.
        """
        # ARRANGE: Create a mock connection ID and state machine
        connection_id = ConnectionID(str(uuid.uuid4()))
        mock_machine = MagicMock()
        mock_machine.can_process_messages.return_value = True
        
        # Mock the state machine getter to return our mock machine
        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get:
            mock_get.return_value = mock_machine
            
            # ACT: Check if the existing connection is ready for messages
            result = is_connection_ready_for_messages(connection_id)
            
            # ASSERT: Should delegate to the state machine's can_process_messages method
            assert result is True
            mock_get.assert_called_once_with(connection_id)
            mock_machine.can_process_messages.assert_called_once()
        
        # Record successful delegation metric
        self.record_metric("delegation_test", "passed")

    def test_connection_ready_with_registered_connection_returns_false_when_not_ready(self):
        """
        Test that when a connection exists but is not ready, the function returns False.
        
        This test should PASS and shows proper delegation behavior.
        """
        # ARRANGE: Create a mock connection ID and state machine that's not ready
        connection_id = ConnectionID(str(uuid.uuid4()))
        mock_machine = MagicMock()
        mock_machine.can_process_messages.return_value = False
        
        # Mock the state machine getter to return our mock machine
        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get:
            mock_get.return_value = mock_machine
            
            # ACT: Check if the not-ready connection is ready for messages
            result = is_connection_ready_for_messages(connection_id)
            
            # ASSERT: Should properly return False from the state machine
            assert result is False
            mock_get.assert_called_once_with(connection_id)
            mock_machine.can_process_messages.assert_called_once()
        
        # Record successful not-ready test
        self.record_metric("not_ready_test", "passed")

    def test_multiple_non_existent_connections_all_return_true_bug(self):
        """
        Test that multiple non-existent connections all incorrectly return True.
        
        This demonstrates the systemic nature of the bug - it affects ALL non-existent connections.
        This test SHOULD FAIL, showing the bug affects multiple scenarios.
        """
        # ARRANGE: Create multiple non-existent connection IDs
        non_existent_connections = [
            ConnectionID(str(uuid.uuid4()))
            for i in range(5)
        ]
        
        # Verify none of these connections exist
        for conn_id in non_existent_connections:
            machine = get_connection_state_machine(conn_id)
            assert machine is None, f"Test setup failed: connection {conn_id} should not exist"
        
        # ACT: Check all non-existent connections
        results = [
            is_connection_ready_for_messages(conn_id)
            for conn_id in non_existent_connections
        ]
        
        # ASSERT: All should be False but will be True due to the bug
        #  ALERT:  THIS TEST WILL FAIL - showing systemic bug impact
        for i, result in enumerate(results):
            assert result is False, (
                f"BUG CONFIRMED: Connection {non_existent_connections[i]} returned True "
                f"instead of False. This systemic bug affects ALL non-existent connections."
            )
        
        # Record systemic bug metrics
        self.record_metric("systemic_bug_test", "failed_as_expected")
        self.record_metric("affected_connections_count", len(non_existent_connections))
        self.record_metric("all_returned_true", all(results))

    def teardown_method(self, method=None):
        """Clean up test state and log bug detection results."""
        super().teardown_method(method)
        
        # Log metrics for bug tracking
        metrics = self.get_all_metrics()
        if "bug_detected" in metrics:
            print(f"\n ALERT:  BUG DETECTION REPORT:")
            print(f"Bug Type: {metrics.get('bug_detected')}")
            print(f"Bug Location: {metrics.get('bug_location')}")
            print(f"Expected Result: {metrics.get('expected_result')}")
            print(f"Actual Result: {metrics.get('actual_result')}")
            print(f"Test Duration: {metrics.get('execution_time'):.3f}s")