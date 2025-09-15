"""
Integration tests for WebSocket event delivery structure validation (Issue #1049)

These tests demonstrate the structure mismatch between expected event formats
and actual event delivery through the WebSocket infrastructure.

Business Value: Ensures real-time AI transparency events reach users in
the correct format for optimal chat experience.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator, ValidationResult, WebSocketEventMessage
)
from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge
from shared.types.execution_types import StronglyTypedUserExecutionContext


@pytest.mark.integration
class TestWebSocketEventDeliveryStructure:
    """Integration tests for WebSocket event delivery structure."""

    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return StronglyTypedUserExecutionContext(
            user_id="test-user-123",
            request_id="req-123",
            run_id="run-123",
            thread_id="thread-123",
            websocket_client_id="ws-123"
        )

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager to capture events."""
        manager = Mock()
        manager.send_event = AsyncMock(return_value=True)
        manager.emit_event = AsyncMock(return_value=True)
        manager.is_connection_active = Mock(return_value=True)
        return manager

    @pytest.fixture
    def bridge_factory(self, user_context, mock_websocket_manager):
        """Create WebSocket bridge factory with mocked manager."""
        bridge = StandardWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        return bridge

    async def test_tool_executing_event_delivery_structure(self, bridge_factory, mock_websocket_manager):
        """
        EXPECTED TO FAIL: Test tool_executing event delivery uses flat structure.

        This test validates that tool_executing events are delivered with
        tool_name at the top level of the payload for user transparency.
        """
        # Execute tool_executing notification
        success = await bridge_factory.notify_tool_executing(
            run_id="run-123",
            agent_name="test-agent",
            tool_name="data_analyzer",
            parameters={"query": "optimization analysis"}
        )

        assert success, "Tool executing notification should succeed"

        # Verify WebSocket manager was called
        assert mock_websocket_manager.send_event.called or mock_websocket_manager.emit_event.called, \
            "WebSocket manager should be called"

        # Extract the event that was sent
        if mock_websocket_manager.send_event.called:
            call_args = mock_websocket_manager.send_event.call_args
        elif mock_websocket_manager.emit_event.called:
            call_args = mock_websocket_manager.emit_event.call_args
        else:
            pytest.fail("No WebSocket method was called")

        # Analyze the event structure
        event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('data', {})

        # Validate flat structure - tool_name should be at top level
        assert "tool_name" in event_data, "tool_name should be at top level of event data"
        assert event_data["tool_name"] == "data_analyzer", "tool_name should have correct value"
        assert event_data.get("type") == "tool_executing", "Event type should be tool_executing"

        # Validate this event would pass validator
        validator = UnifiedEventValidator(validation_mode="realtime")

        validation_event = {
            "type": "tool_executing",
            "run_id": "run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "tool_name": event_data.get("tool_name")
            }
        }

        result = validator.validate_event(validation_event, "test-user-123")
        assert result.is_valid, f"Delivered event structure should be valid: {result.error_message}"

    async def test_tool_completed_event_delivery_structure(self, bridge_factory, mock_websocket_manager):
        """
        EXPECTED TO FAIL: Test tool_completed event delivery uses flat structure.

        This test validates that tool_completed events are delivered with
        results at the top level of the payload for user insights.
        """
        # Execute tool_completed notification
        tool_result = {
            "analysis": "Cost optimization potential: 23%",
            "recommendations": ["Switch to GPT-4o", "Implement caching"],
            "confidence": 0.95
        }

        success = await bridge_factory.notify_tool_completed(
            run_id="run-123",
            agent_name="test-agent",
            tool_name="data_analyzer",
            result=tool_result,
            execution_time_ms=1500.0
        )

        assert success, "Tool completed notification should succeed"

        # Verify WebSocket manager was called
        assert mock_websocket_manager.send_event.called or mock_websocket_manager.emit_event.called, \
            "WebSocket manager should be called"

        # Extract the event that was sent
        if mock_websocket_manager.send_event.called:
            call_args = mock_websocket_manager.send_event.call_args
        elif mock_websocket_manager.emit_event.called:
            call_args = mock_websocket_manager.emit_event.call_args
        else:
            pytest.fail("No WebSocket method was called")

        event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('data', {})

        # Validate flat structure - results should be at top level
        assert "result" in event_data or "results" in event_data, \
            "results should be at top level of event data"
        assert "tool_name" in event_data, "tool_name should be at top level"
        assert event_data["tool_name"] == "data_analyzer", "tool_name should have correct value"

        # Validate this event would pass validator
        validator = UnifiedEventValidator(validation_mode="realtime")

        validation_event = {
            "type": "tool_completed",
            "run_id": "run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "results": event_data.get("result", event_data.get("results"))
            }
        }

        result = validator.validate_event(validation_event, "test-user-123")
        assert result.is_valid, f"Delivered event structure should be valid: {result.error_message}"

    async def test_websocket_bridge_event_format_consistency(self, bridge_factory, mock_websocket_manager):
        """
        Test that all events from WebSocket bridge have consistent flat structure.

        This test validates that the bridge factory produces events in a
        consistent format that matches validator expectations.
        """
        # Test multiple event types
        events_to_test = [
            {
                "method": "notify_agent_started",
                "args": ("run-123", "test-agent"),
                "expected_fields": ["agent_name"]
            },
            {
                "method": "notify_agent_thinking",
                "args": ("run-123", "test-agent", {"reasoning": "analyzing data"}),
                "expected_fields": ["agent_name"]
            },
            {
                "method": "notify_tool_executing",
                "args": ("run-123", "test-agent", "data_analyzer", {"query": "test"}),
                "expected_fields": ["tool_name", "agent_name"]
            },
            {
                "method": "notify_agent_completed",
                "args": ("run-123", "test-agent", {"result": "analysis complete"}),
                "expected_fields": ["agent_name"]
            }
        ]

        for event_test in events_to_test:
            # Reset mock
            mock_websocket_manager.reset_mock()

            # Call the method
            method = getattr(bridge_factory, event_test["method"])
            success = await method(*event_test["args"])

            assert success, f"{event_test['method']} should succeed"

            # Verify event structure
            assert mock_websocket_manager.send_event.called or mock_websocket_manager.emit_event.called, \
                f"WebSocket manager should be called for {event_test['method']}"

            # Extract event data
            if mock_websocket_manager.send_event.called:
                call_args = mock_websocket_manager.send_event.call_args
            else:
                call_args = mock_websocket_manager.emit_event.call_args

            event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('data', {})

            # Check expected fields are at top level
            for field in event_test["expected_fields"]:
                assert field in event_data, \
                    f"{field} should be at top level in {event_test['method']} event"

    def test_event_validator_schema_matches_delivery_format(self):
        """
        Test that event validator schema requirements match delivery format.

        This test ensures that the validator's PAYLOAD_SCHEMAS align with
        what the WebSocket bridge actually delivers.
        """
        validator = UnifiedEventValidator(validation_mode="realtime")

        # Check validator schema requirements
        tool_executing_schema = validator.PAYLOAD_SCHEMAS.get("tool_executing", set())
        tool_completed_schema = validator.PAYLOAD_SCHEMAS.get("tool_completed", set())

        assert "tool_name" in tool_executing_schema, \
            "Validator should require tool_name for tool_executing events"
        assert "results" in tool_completed_schema, \
            "Validator should require results for tool_completed events"

        # Test that expected flat structure passes validation
        flat_tool_executing = {
            "type": "tool_executing",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "tool_name": "data_analyzer"  # Flat structure
            }
        }

        result = validator.validate_event(flat_tool_executing, "test-user-123")
        assert result.is_valid, "Flat tool_executing structure should be valid"

        flat_tool_completed = {
            "type": "tool_completed",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "results": {"analysis": "complete"}  # Flat structure
            }
        }

        result = validator.validate_event(flat_tool_completed, "test-user-123")
        assert result.is_valid, "Flat tool_completed structure should be valid"


@pytest.mark.integration
class TestWebSocketEventStructureMismatchDetection:
    """Test detection and handling of structure mismatches."""

    def test_nested_structure_detection(self):
        """
        Test that nested structures are detected and rejected properly.

        This test validates that the validator correctly identifies when
        required fields are nested instead of flat.
        """
        validator = UnifiedEventValidator(validation_mode="realtime")

        # Nested structure that should fail
        nested_event = {
            "type": "tool_executing",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "data": {  # tool_name nested inside data
                    "tool_name": "data_analyzer",
                    "status": "executing"
                }
            }
        }

        result = validator.validate_event(nested_event, "test-user-123")

        # Should fail due to missing tool_name at expected flat level
        assert not result.is_valid, "Nested structure should be invalid"
        assert "tool_name" in (result.error_message or ""), \
            "Error should mention missing tool_name field"

    def test_structure_mismatch_business_impact(self):
        """
        Test that structure mismatches have proper business impact categorization.

        This test validates that structure issues are correctly identified
        as impacting user experience and revenue.
        """
        validator = UnifiedEventValidator(validation_mode="realtime")

        # Event with structure that impacts business value
        bad_structure_event = {
            "type": "tool_completed",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                "tool_name": "data_analyzer",
                # Missing results field - impacts user insights delivery
            }
        }

        result = validator.validate_event(bad_structure_event, "test-user-123")

        assert not result.is_valid, "Bad structure should be invalid"
        assert "results" in (result.error_message or ""), "Should mention missing results"

        # Check business impact messaging
        error_msg = result.error_message or ""
        assert any(keyword in error_msg.lower() for keyword in
                  ["insights", "actionable", "value", "transparency"]), \
            "Error should reference business impact"

    async def test_websocket_manager_format_validation(self):
        """
        Test that WebSocket manager receives events in expected format.

        This test validates the event format at the WebSocket manager level.
        """
        # Mock WebSocket manager to capture exact format
        captured_events = []

        def capture_event(*args, **kwargs):
            captured_events.append((args, kwargs))
            return True

        mock_manager = Mock()
        mock_manager.send_event = Mock(side_effect=capture_event)

        # Create user context
        user_context = StronglyTypedUserExecutionContext(
            user_id="test-user-123",
            request_id="req-123",
            run_id="run-123",
            thread_id="thread-123",
            websocket_client_id="ws-123"
        )

        # Create bridge with mock manager
        bridge = StandardWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_manager

        # Send tool executing event
        await bridge.notify_tool_executing(
            run_id="run-123",
            agent_name="test-agent",
            tool_name="cost_analyzer",
            parameters={"mode": "optimization"}
        )

        # Analyze captured event
        assert len(captured_events) > 0, "Event should be captured"

        args, kwargs = captured_events[0]

        # Check event structure
        if len(args) > 1:
            event_data = args[1]
        else:
            event_data = kwargs.get('data', {})

        # Validate flat structure requirements
        assert isinstance(event_data, dict), "Event data should be dictionary"
        assert "tool_name" in event_data, "tool_name should be in event data"
        assert event_data["tool_name"] == "cost_analyzer", "tool_name should match"

    def test_event_validation_error_context(self):
        """
        Test that validation errors provide clear context about structure issues.

        This test validates that error messages clearly explain structure
        requirements and business impact.
        """
        validator = UnifiedEventValidator(validation_mode="realtime")

        # Create event with structure issue
        problematic_event = {
            "type": "tool_executing",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-09-14T12:00:00Z",
            "payload": {
                # Missing tool_name - structure issue
                "status": "executing",
                "agent": "test-agent"
            }
        }

        result = validator.validate_event(problematic_event, "test-user-123")

        assert not result.is_valid, "Problematic event should be invalid"

        error_msg = result.error_message or ""

        # Check error provides clear guidance
        assert "tool_name" in error_msg, "Error should mention missing field"

        # Check business context is provided
        business_context_keywords = ["transparency", "user", "see", "tool"]
        assert any(keyword in error_msg.lower() for keyword in business_context_keywords), \
            f"Error should provide business context: {error_msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])