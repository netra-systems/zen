"""
Isolation Violation Detection Verification Tests

This test file verifies that our real WebSocket isolation tests CORRECTLY
detect and fail hard when isolation violations occur.

These are "meta-tests" that intentionally create isolation violations
to verify our security tests are working properly.

CRITICAL: These tests must demonstrate that our isolation detection works.
If these tests pass, it means our security validation is functioning.

Business Value: Ensures our security tests actually detect violations
rather than giving false confidence.

@compliance CLAUDE.md - Tests must fail hard when isolation violated
@compliance Security validation must be reliable and accurate
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from unittest.mock import patch

from test_framework.ssot.real_websocket_test_client import (
    RealWebSocketTestClient,
    WebSocketEvent,
    SecurityError
)
from test_framework.ssot.real_websocket_connection_manager import (
    RealWebSocketConnectionManager,
    IsolationTestType
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

logger = logging.getLogger(__name__)


class TestIsolationViolationDetection:
    """
    Verification Tests: Ensure isolation violation detection works correctly.
    
    These tests intentionally create isolation violations to verify
    that our security validation correctly detects them.
    """
    
    @pytest.mark.asyncio
    async def test_client_detects_user_id_mismatch(self):
        """Verify that RealWebSocketTestClient detects user ID mismatches."""
        # Create client with expected user
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False  # Skip auth for this isolated test
        )
        client.expected_user_id = "user_123"
        
        # Create event with wrong user ID (simulates cross-user leak)
        malicious_event = WebSocketEvent(
            event_type="test_event",
            data={"user_id": "user_456"},  # Different user!
            timestamp=time.time(),
            user_id="user_456"  # This should trigger violation
        )
        
        # Verify client detects the violation
        with pytest.raises(SecurityError) as exc_info:
            client._validate_user_isolation(malicious_event)
        
        assert "USER ISOLATION VIOLATION" in str(exc_info.value)
        assert "user_123" in str(exc_info.value)
        assert "user_456" in str(exc_info.value)
        
        # Verify violation is recorded
        assert len(client.isolation_violations) == 1
        
        logger.info("✅ Client correctly detected user ID mismatch violation")
    
    @pytest.mark.asyncio
    async def test_client_allows_matching_user_id(self):
        """Verify that RealWebSocketTestClient allows events for correct user."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        client.expected_user_id = "user_123"
        
        # Create event with correct user ID
        valid_event = WebSocketEvent(
            event_type="test_event",
            data={"user_id": "user_123"},
            timestamp=time.time(),
            user_id="user_123"  # Matches expected user
        )
        
        # This should NOT raise an exception
        client._validate_user_isolation(valid_event)
        
        # No violations should be recorded
        assert len(client.isolation_violations) == 0
        
        logger.info("✅ Client correctly allowed matching user ID")
    
    @pytest.mark.asyncio
    async def test_assert_no_violations_fails_when_violations_exist(self):
        """Verify that assert_no_isolation_violations() fails when violations exist."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        
        # Manually add a violation to test assertion
        violation = "Test violation for verification"
        client.isolation_violations.append(violation)
        
        # The assertion should fail
        with pytest.raises(AssertionError) as exc_info:
            client.assert_no_isolation_violations()
        
        assert "USER ISOLATION VIOLATIONS DETECTED" in str(exc_info.value)
        assert violation in str(exc_info.value)
        
        logger.info("✅ Client correctly failed assertion when violations exist")
    
    @pytest.mark.asyncio
    async def test_assert_events_received_fails_when_missing(self):
        """Verify that assert_events_received() fails when events are missing."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        
        # Add some events but not all required ones
        client.received_events = [
            WebSocketEvent("agent_started", {}, time.time()),
            WebSocketEvent("agent_thinking", {}, time.time())
            # Missing: agent_completed, tool_executing, tool_completed
        ]
        
        required_events = {
            "agent_started",
            "agent_thinking", 
            "agent_completed",
            "tool_executing",
            "tool_completed"
        }
        
        # The assertion should fail
        with pytest.raises(AssertionError) as exc_info:
            client.assert_events_received(required_events)
        
        assert "Missing expected WebSocket events" in str(exc_info.value)
        assert "agent_completed" in str(exc_info.value)
        
        logger.info("✅ Client correctly failed assertion when events missing")
    
    @pytest.mark.asyncio
    async def test_connection_manager_detects_violations(self):
        """Verify that connection manager detects isolation violations."""
        manager = RealWebSocketConnectionManager(
            backend_url="ws://localhost:8000",
            environment="test"
        )
        
        # Create mock connection profile with violations
        connection_id = "test_conn_123"
        manager.connections[connection_id] = type('MockProfile', (), {
            'connection_id': connection_id,
            'user_id': 'user_123',
            'isolation_violations': ['Test violation 1', 'Test violation 2'],
            'record_violation': lambda self, v: None
        })()
        
        # Add global violations
        manager.global_violations.append("Global test violation")
        
        # Get isolation summary
        summary = manager.get_isolation_summary()
        
        # Verify violations are detected
        assert not summary['test_passed']
        assert summary['global_violations'] == 1
        assert connection_id in summary['connection_violations']
        assert summary['connection_violations'][connection_id]['violations'] == 2
        
        # Verify assertion fails
        with pytest.raises(AssertionError) as exc_info:
            manager.assert_no_violations()
        
        assert "ISOLATION VIOLATIONS DETECTED" in str(exc_info.value)
        
        logger.info("✅ Connection manager correctly detected violations")
    
    @pytest.mark.asyncio
    async def test_security_error_raised_on_critical_violations(self):
        """Verify that SecurityError is raised for critical violations."""
        # This tests that our custom SecurityError works correctly
        
        try:
            raise SecurityError("Critical security violation detected")
        except SecurityError as e:
            assert "Critical security violation detected" in str(e)
            logger.info("✅ SecurityError correctly raised and caught")
        
        # Verify it's a proper exception
        assert issubclass(SecurityError, Exception)
    
    @pytest.mark.asyncio
    async def test_isolation_test_result_indicates_failure(self):
        """Verify that isolation test results correctly indicate failures."""
        from test_framework.ssot.real_websocket_connection_manager import IsolationTestResult
        
        # Create a failed test result
        failed_result = IsolationTestResult(
            test_type=IsolationTestType.EVENT_ISOLATION,
            test_passed=False,
            connections_tested=5,
            total_violations=3,
            violation_details=[
                "User A received User B's data",
                "Cross-user event leak detected", 
                "Authentication boundary crossed"
            ],
            test_duration=15.5,
            events_validated=100
        )
        
        # Verify failure detection
        assert not failed_result.test_passed
        assert failed_result.total_violations == 3
        assert len(failed_result.violation_details) == 3
        assert "User A received User B's data" in failed_result.violation_details
        
        logger.info("✅ IsolationTestResult correctly indicates failure")
    
    @pytest.mark.asyncio
    async def test_websocket_events_isolation_function_detects_violations(self):
        """Verify the isolation testing utility function detects violations."""
        # This test validates that the function correctly detects violations
        # by manually creating clients with existing violations rather than
        # trying to send events (which would require real connections)
        
        from test_framework.ssot.real_websocket_test_client import test_websocket_events_isolation
        
        # Create clients with pre-existing violations (simulates post-test state)
        mock_clients = []
        
        for i in range(2):
            client = RealWebSocketTestClient(
                backend_url="ws://localhost:8000",
                environment="test", 
                auth_required=False
            )
            client.connection_id = f"test_client_{i}"
            client.expected_user_id = f"user_{i}"
            
            # Add violation to second client (simulates cross-user leak detection)
            if i == 1:
                violation = "Test cross-user violation detected in isolation test"
                client.isolation_violations.append(violation)
            
            mock_clients.append(client)
        
        # Mock the wait_for_events and send_event methods since we're not actually connecting
        async def mock_send_event(event_type, data):
            pass  # Mock implementation - no actual sending
        
        async def mock_wait_for_events(event_types, timeout):
            return []  # Mock implementation - no events received
        
        for client in mock_clients:
            client.send_event = mock_send_event
            client.wait_for_events = mock_wait_for_events
        
        # The function should detect existing violations and raise SecurityError
        with pytest.raises(SecurityError) as exc_info:
            await test_websocket_events_isolation(
                clients=mock_clients,
                event_types={"test_event"},
                timeout=1.0
            )
        
        assert "WebSocket isolation test FAILED" in str(exc_info.value)
        
        logger.info("✅ test_websocket_events_isolation correctly detected violations")


class TestIsolationViolationScenarios:
    """
    Test various scenarios where isolation violations might occur
    to ensure our detection is comprehensive.
    """
    
    @pytest.mark.asyncio
    async def test_event_data_contamination_detection(self):
        """Test detection of event data contamination between users."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        client.expected_user_id = "user_alice"
        
        # Event contains data meant for different user
        contaminated_event = WebSocketEvent(
            event_type="message_notification",
            data={
                "user_id": "user_bob",  # Wrong user!
                "message": "Private message for Bob",
                "recipient": "user_bob"
            },
            timestamp=time.time(),
            user_id="user_bob"
        )
        
        # Should detect contamination
        with pytest.raises(SecurityError):
            client._validate_user_isolation(contaminated_event)
        
        logger.info("✅ Event data contamination correctly detected")
    
    @pytest.mark.asyncio
    async def test_empty_user_context_handling(self):
        """Test handling of events with missing user context."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        client.expected_user_id = "user_alice"
        
        # Event with no user context - should be allowed
        neutral_event = WebSocketEvent(
            event_type="system_notification",
            data={"message": "System maintenance scheduled"},
            timestamp=time.time(),
            user_id=None  # No user context
        )
        
        # Should NOT raise exception (system events are OK)
        client._validate_user_isolation(neutral_event)
        
        assert len(client.isolation_violations) == 0
        
        logger.info("✅ Empty user context correctly handled")
    
    @pytest.mark.asyncio 
    async def test_partial_user_id_in_data_only(self):
        """Test detection when user_id is only in event data, not event.user_id."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test",
            auth_required=False
        )
        client.expected_user_id = "user_alice"
        
        # User ID only in data field
        data_violation_event = WebSocketEvent(
            event_type="user_action",
            data={"user_id": "user_charlie"},  # Wrong user in data
            timestamp=time.time(),
            user_id=None  # No user_id at event level
        )
        
        # Should still detect violation
        with pytest.raises(SecurityError):
            client._validate_user_isolation(data_violation_event)
        
        logger.info("✅ User ID in data field violation correctly detected")


if __name__ == "__main__":
    # Run verification tests
    pytest.main([__file__, "-v", "--tb=short"])