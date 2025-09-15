"""Unit Tests: WebSocket Event Structure Validation - Issue #1021

CRITICAL ISSUE: unified_manager.py incorrectly wraps business event data, causing validation
failures for tool_name, execution_time, and results fields in WebSocket events.

These tests MUST FAIL initially to prove the current bug exists, then pass after remediation.

Purpose: Validate that WebSocket events preserve business data structure during transmission
without incorrect wrapping that hides critical fields from consumers.

Business Value: $500K+ ARR - Ensures WebSocket events contain the business data fields
required for real-time chat functionality that delivers 90% of platform value.
"""

import asyncio
import time
import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManager,
    get_websocket_manager,
    WebSocketManagerMode
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.unit
class WebSocketEventStructureValidationTests:
    """Test suite that reproduces Issue #1021 WebSocket event structure problems."""

    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        # Create test user context
        id_manager = UnifiedIDManager()
        test_user_context = type('MockUserContext', (), {
            'user_id': id_manager.generate_id(IDType.USER, prefix="test"),
            'thread_id': id_manager.generate_id(IDType.THREAD, prefix="test"),
            'request_id': id_manager.generate_id(IDType.REQUEST, prefix="test"),
            'is_test': True
        })()

        manager = get_websocket_manager(
            user_context=test_user_context,
            mode=WebSocketManagerMode.UNIFIED
        )
        return manager

    @pytest.mark.asyncio
    async def test_tool_executing_event_structure_validation(self, websocket_manager):
        """Test tool_executing event contains required business fields at top level.

        FAILS INITIALLY: unified_manager.py wraps data incorrectly, hiding tool_name
        PASSES AFTER FIX: Business data properly preserved at top level

        Root Cause: WebSocket transmission incorrectly nests business fields in 'payload'
        when mission critical tests expect them at the top level for transparency.
        """
        # Simulate real agent tool execution event with business data
        business_event_data = {
            "type": "tool_executing",
            "tool_name": "search_analyzer",
            "tool_args": {"query": "test search"},
            "execution_id": "exec_123",
            "timestamp": time.time(),
            "user_id": "test_user_456"
        }

        # Test that WebSocket manager preserves business structure at top level
        # CRITICAL: This is where the bug manifests - business fields get wrapped incorrectly
        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(business_event_data)

        # CRITICAL VALIDATIONS (currently failing due to unified_manager.py wrapping)
        assert "tool_name" in wrapped_event, f"tool_name missing from wrapped event. Got: {wrapped_event}"
        assert wrapped_event["tool_name"] == "search_analyzer", f"tool_name value incorrect. Expected 'search_analyzer', got: {wrapped_event.get('tool_name')}"
        assert "tool_args" in wrapped_event, f"tool_args missing from wrapped event. Got: {wrapped_event}"
        assert isinstance(wrapped_event["tool_args"], dict), f"tool_args not dict type. Got: {type(wrapped_event.get('tool_args'))}"
        assert "execution_id" in wrapped_event, f"execution_id missing from wrapped event. Got: {wrapped_event}"

        # Ensure event type is preserved
        assert wrapped_event["type"] == "tool_executing", f"Event type incorrect. Expected 'tool_executing', got: {wrapped_event.get('type')}"

    @pytest.mark.asyncio
    async def test_tool_completed_event_structure_validation(self, websocket_manager):
        """Test tool_completed event contains execution results and metrics at top level.

        FAILS INITIALLY: Business data wrapped incorrectly by unified_manager.py
        PASSES AFTER FIX: Results and execution_time properly preserved at top level

        Mission Critical Requirement: tool_completed events must have top-level tool_name,
        results, and execution_time fields for frontend consumption and transparency.
        """
        business_event_data = {
            "type": "tool_completed",
            "tool_name": "search_analyzer",
            "results": {
                "found_items": 5,
                "top_result": "Critical finding"
            },
            "execution_time": 2.34,
            "success": True,
            "execution_id": "exec_123",
            "user_id": "test_user_456"
        }

        # Test WebSocket transmission preserves business data at top level
        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(business_event_data)

        # CRITICAL VALIDATIONS (currently failing due to incorrect wrapping)
        assert "tool_name" in wrapped_event, f"tool_name missing from wrapped event. Got: {wrapped_event}"
        assert wrapped_event["tool_name"] == "search_analyzer", f"tool_name value incorrect"
        assert "results" in wrapped_event, f"results missing from event. Got: {wrapped_event}"
        assert "execution_time" in wrapped_event, f"execution_time missing. Got: {wrapped_event}"
        assert wrapped_event["execution_time"] == 2.34, f"execution_time value incorrect. Expected 2.34, got: {wrapped_event.get('execution_time')}"
        assert isinstance(wrapped_event["results"], dict), f"results not dict type. Got: {type(wrapped_event.get('results'))}"

        # Validate nested results structure is preserved
        assert wrapped_event["results"]["found_items"] == 5, "Nested results data corrupted"
        assert wrapped_event["results"]["top_result"] == "Critical finding", "Nested results data corrupted"

    @pytest.mark.asyncio
    async def test_agent_started_event_structure_validation(self, websocket_manager):
        """Test agent_started contains proper user context and identifiers at top level.

        Mission Critical: agent_started events must have user_id, thread_id, and agent_name
        at the top level for proper routing and user isolation validation.
        """
        business_event_data = {
            "type": "agent_started",
            "user_id": "test_user_123",
            "thread_id": "thread_456",
            "agent_name": "DataHelperAgent",
            "task_description": "Analyze user request",
            "timestamp": time.time()
        }

        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(business_event_data)

        # Validate critical fields preserved at top level
        assert "user_id" in wrapped_event, f"user_id missing from wrapped event. Got: {wrapped_event}"
        assert wrapped_event["user_id"] == "test_user_123", f"user_id value incorrect"
        assert "thread_id" in wrapped_event, f"thread_id missing from wrapped event. Got: {wrapped_event}"
        assert wrapped_event["thread_id"] == "thread_456", f"thread_id value incorrect"
        assert "agent_name" in wrapped_event, f"agent_name missing from wrapped event. Got: {wrapped_event}"
        assert wrapped_event["agent_name"] == "DataHelperAgent", f"agent_name value incorrect"
        assert wrapped_event["type"] == "agent_started", f"event type incorrect"

    @pytest.mark.asyncio
    async def test_agent_completed_event_structure_validation(self, websocket_manager):
        """Test agent_completed event preserves final results at top level.

        Business Critical: agent_completed must have top-level final_response and status
        fields for chat UI to display completion properly.
        """
        business_event_data = {
            "type": "agent_completed",
            "agent_name": "DataHelperAgent",
            "final_response": "Analysis completed successfully with 3 key insights",
            "status": "success",
            "duration_ms": 5420.5,
            "user_id": "test_user_123",
            "timestamp": time.time()
        }

        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(business_event_data)

        # Critical business fields must be at top level
        assert "final_response" in wrapped_event, f"final_response missing. Got: {wrapped_event}"
        assert "status" in wrapped_event, f"status missing. Got: {wrapped_event}"
        assert "duration_ms" in wrapped_event, f"duration_ms missing. Got: {wrapped_event}"
        assert "agent_name" in wrapped_event, f"agent_name missing. Got: {wrapped_event}"

        assert wrapped_event["final_response"] == "Analysis completed successfully with 3 key insights"
        assert wrapped_event["status"] == "success"
        assert wrapped_event["duration_ms"] == 5420.5

    @pytest.mark.asyncio
    async def test_agent_thinking_event_structure_validation(self, websocket_manager):
        """Test agent_thinking event preserves reasoning content at top level.

        Real-time Requirement: agent_thinking must have top-level reasoning/content
        field for live updates to user during agent processing.
        """
        business_event_data = {
            "type": "agent_thinking",
            "reasoning": "I need to analyze the user's request for data patterns...",
            "agent_name": "DataHelperAgent",
            "step_number": 2,
            "user_id": "test_user_123",
            "timestamp": time.time()
        }

        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(business_event_data)

        # Critical thinking content must be at top level for real-time display
        assert "reasoning" in wrapped_event, f"reasoning missing. Got: {wrapped_event}"
        assert "agent_name" in wrapped_event, f"agent_name missing. Got: {wrapped_event}"
        assert "step_number" in wrapped_event, f"step_number missing. Got: {wrapped_event}"

        assert wrapped_event["reasoning"] == "I need to analyze the user's request for data patterns..."
        assert wrapped_event["agent_name"] == "DataHelperAgent"
        assert wrapped_event["step_number"] == 2

    @pytest.mark.asyncio
    async def test_event_wrapping_preserves_all_fields(self, websocket_manager):
        """Test that NO business fields are lost during WebSocket wrapping.

        Comprehensive Test: Complex business event with nested data should have ALL
        original fields preserved at their original locations after serialization.
        """
        complex_business_event = {
            "type": "tool_completed",
            "tool_name": "complex_analyzer",
            "tool_version": "v2.1.0",
            "results": {
                "analysis_complete": True,
                "findings": ["item1", "item2"],
                "metadata": {"confidence": 0.95}
            },
            "execution_time": 5.67,
            "performance_metrics": {
                "memory_usage": "128MB",
                "cpu_time": "3.2s"
            },
            "success": True,
            "correlation_id": "corr_789",
            "user_id": "test_user_123",
            "timestamp": time.time()
        }

        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
        wrapped_event = _serialize_message_safely(complex_business_event)

        # Verify ALL original fields preserved at top level
        for key, value in complex_business_event.items():
            assert key in wrapped_event, f"Field {key} lost during wrapping. Got: {wrapped_event}"
            assert wrapped_event[key] == value, f"Field {key} value changed during wrapping. Expected: {value}, Got: {wrapped_event.get(key)}"

        # Additional validation for nested structures
        assert wrapped_event["results"]["analysis_complete"] == True
        assert wrapped_event["results"]["findings"] == ["item1", "item2"]
        assert wrapped_event["results"]["metadata"]["confidence"] == 0.95
        assert wrapped_event["performance_metrics"]["memory_usage"] == "128MB"

    @pytest.mark.asyncio
    async def test_emit_critical_event_preserves_structure(self, websocket_manager):
        """Test emit_critical_event method preserves business data structure.

        Integration Test: Verify that the high-level emit_critical_event API
        preserves the business event structure all the way through to transmission.
        """
        # Mock a WebSocket connection
        mock_websocket = AsyncMock()
        mock_connection = MagicMock()
        mock_connection.websocket = mock_websocket
        mock_connection.connection_id = "test_conn_123"

        # Add connection to manager
        await websocket_manager.add_connection(mock_connection)
        websocket_manager._user_connections[websocket_manager.user_context.user_id] = {"test_conn_123"}

        # Business event data
        event_data = {
            "tool_name": "test_analyzer",
            "execution_id": "exec_456",
            "parameters": {"query": "test"},
            "timestamp": time.time()
        }

        # Emit critical event
        await websocket_manager.emit_critical_event(
            user_id=websocket_manager.user_context.user_id,
            event_type="tool_executing",
            data=event_data
        )

        # Verify WebSocket was called
        assert mock_websocket.send_json.called, "WebSocket send_json was not called"

        # Extract the actual message sent
        call_args = mock_websocket.send_json.call_args[0][0]

        # CRITICAL: Business fields should be at top level in transmitted message
        # This is where the bug manifests - if fields are wrapped in 'data' or 'payload',
        # the frontend can't access them directly
        assert "tool_name" in call_args, f"tool_name missing from transmitted message: {call_args}"
        assert call_args["tool_name"] == "test_analyzer"
        assert "execution_id" in call_args, f"execution_id missing from transmitted message: {call_args}"
        assert call_args["execution_id"] == "exec_456"
        assert call_args["type"] == "tool_executing"