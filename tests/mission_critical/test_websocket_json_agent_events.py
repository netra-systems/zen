"""
MISSION CRITICAL: WebSocket JSON Agent Events Test Suite

This test suite verifies that ALL WebSocket events for agent execution serialize correctly 
and work with the unified JSON handler. Any failure here BREAKS chat functionality.

CRITICAL WebSocket Events that MUST work:
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User must know when done

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability (prevents chat UI from appearing broken)
- Value Impact: Ensures 90% of value delivery channel remains functional
- Strategic Impact: WebSocket events are the primary user feedback mechanism
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.registry import WebSocketMessage, AgentStarted, ServerMessage
from netra_backend.app.schemas.websocket_models import (
    BaseWebSocketPayload, AgentUpdatePayload, ToolCall, ToolResult,
    AgentCompleted, StreamChunk, StreamComplete
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.types import get_frontend_message_type


class TestWebSocketJSONAgentEvents:
    """Test WebSocket JSON serialization for all critical agent events."""

    @pytest.fixture
    def websocket_manager(self):
        """Create a test WebSocket manager."""
        manager = WebSocketManager()
        # Mock the send methods to capture serialization
        manager.send_to_thread = AsyncMock()
        manager.broadcast_to_all = AsyncMock()
        return manager

    @pytest.fixture
    def websocket_notifier(self, websocket_manager):
        """Create a WebSocket notifier with mocked manager."""
        return WebSocketNotifier(websocket_manager)

    @pytest.fixture
    def agent_context(self):
        """Create a test agent execution context."""
        return AgentExecutionContext(
            agent_name="test-agent",
            run_id="run-12345", 
            thread_id="thread-67890",
            user_id="user-test",
            metadata={"test": "context"}
        )

    @pytest.fixture
    def complex_agent_state(self):
        """Create a complex DeepAgentState for serialization testing."""
        optimizations = OptimizationsResult(
            optimization_type="cost_optimization",
            recommendations=["Reduce instance sizes", "Use spot instances"],
            cost_savings=1250.75,
            performance_improvement=15.5,
            confidence_score=0.92
        )
        
        action_plan = ActionPlanResult(
            action_plan_summary="Comprehensive optimization plan",
            total_estimated_time="2-3 weeks",
            required_approvals=["Engineering Manager", "Finance"],
            actions=[
                {"id": 1, "action": "Analyze current usage", "priority": "high"},
                {"id": 2, "action": "Implement changes", "priority": "medium"}
            ],
            execution_timeline=[
                {"week": 1, "tasks": ["Analysis", "Planning"]},
                {"week": 2, "tasks": ["Implementation", "Testing"]}
            ]
        )
        
        return DeepAgentState(
            user_request="Optimize our cloud infrastructure costs",
            chat_thread_id="thread-67890",
            user_id="user-test", 
            run_id="run-12345",
            optimizations_result=optimizations,
            action_plan_result=action_plan,
            final_report="Optimization analysis complete with $1,250 potential savings",
            step_count=5,
            messages=[
                {"role": "user", "content": "Please analyze our costs"},
                {"role": "assistant", "content": "I'll analyze your infrastructure costs"}
            ]
        )

    @pytest.mark.asyncio
    async def test_agent_started_json_serialization(self, websocket_notifier, agent_context):
        """Test agent_started event JSON serialization."""
        # Send agent started notification
        await websocket_notifier.send_agent_started(agent_context)
        
        # Verify the message was sent
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
        
        assert thread_id == agent_context.thread_id
        assert isinstance(message_dict, dict)
        
        # Test JSON serialization
        json_str = json.dumps(message_dict)
        assert json_str is not None
        
        # Verify round-trip serialization
        deserialized = json.loads(json_str)
        assert deserialized["type"] == "agent_started"
        assert "payload" in deserialized
        assert deserialized["payload"]["agent_name"] == "test-agent"
        assert deserialized["payload"]["run_id"] == "run-12345"

    @pytest.mark.asyncio
    async def test_agent_thinking_json_serialization(self, websocket_notifier, agent_context):
        """Test agent_thinking event JSON serialization."""
        thinking_text = "I need to analyze the user's request for cost optimization..."
        
        await websocket_notifier.send_agent_thinking(agent_context, thinking_text, step_number=1)
        
        # Verify serialization
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
        
        # Test JSON serialization
        json_str = json.dumps(message_dict)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "agent_thinking"
        assert deserialized["payload"]["thought"] == thinking_text
        assert deserialized["payload"]["agent_name"] == "test-agent"
        assert deserialized["payload"]["step_number"] == 1

    @pytest.mark.asyncio
    async def test_tool_executing_json_serialization(self, websocket_notifier, agent_context):
        """Test tool_executing event JSON serialization."""
        tool_name = "cost_analyzer_tool"
        
        await websocket_notifier.send_tool_executing(agent_context, tool_name)
        
        # Verify serialization
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
        
        # Test JSON serialization
        json_str = json.dumps(message_dict)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "tool_executing"
        assert deserialized["payload"]["tool_name"] == tool_name
        assert deserialized["payload"]["agent_name"] == "test-agent"
        assert "timestamp" in deserialized["payload"]

    @pytest.mark.asyncio
    async def test_tool_completed_json_serialization(self, websocket_notifier, agent_context):
        """Test tool_completed event JSON serialization."""
        tool_name = "cost_analyzer_tool"
        tool_result = {
            "analysis": "Found 3 optimization opportunities",
            "cost_savings": 1250.75,
            "recommendations": ["Use spot instances", "Reduce storage"]
        }
        
        await websocket_notifier.send_tool_completed(agent_context, tool_name, tool_result)
        
        # Verify serialization
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
        
        # Test JSON serialization including complex nested data
        json_str = json.dumps(message_dict)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "tool_completed"
        assert deserialized["payload"]["tool_name"] == tool_name
        assert deserialized["payload"]["result"]["cost_savings"] == 1250.75
        assert len(deserialized["payload"]["result"]["recommendations"]) == 2

    @pytest.mark.asyncio
    async def test_agent_completed_json_serialization(self, websocket_notifier, agent_context):
        """Test agent_completed event JSON serialization."""
        completion_result = {
            "status": "success",
            "summary": "Cost optimization analysis complete",
            "total_savings": 1250.75,
            "recommendations_count": 5
        }
        duration_ms = 12500.0
        
        await websocket_notifier.send_agent_completed(agent_context, completion_result, duration_ms)
        
        # Verify serialization
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
        
        # Test JSON serialization
        json_str = json.dumps(message_dict)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "agent_completed"
        assert deserialized["payload"]["result"]["status"] == "success"
        assert deserialized["payload"]["duration_ms"] == duration_ms
        assert deserialized["payload"]["agent_name"] == "test-agent"
        assert deserialized["payload"]["run_id"] == "run-12345"

    @pytest.mark.asyncio
    async def test_websocket_manager_serialize_message_safely(self, websocket_manager):
        """Test WebSocketManager._serialize_message_safely with various message types."""
        
        # Test 1: Simple dict
        simple_dict = {"type": "test", "message": "hello"}
        result = websocket_manager._serialize_message_safely(simple_dict)
        assert result == simple_dict
        
        # Test 2: WebSocketMessage (Pydantic model)
        websocket_msg = WebSocketMessage(
            type="agent_update",
            payload={"agent_name": "test", "status": "active"}
        )
        result = websocket_manager._serialize_message_safely(websocket_msg)
        assert isinstance(result, dict)
        assert result["type"] == "agent_update"
        
        # Test 3: BaseWebSocketPayload
        base_payload = BaseWebSocketPayload(
            timestamp=datetime.now(timezone.utc)
        )
        result = websocket_manager._serialize_message_safely(base_payload)
        assert isinstance(result, dict)
        assert "timestamp" in result
        
        # Test 4: None handling
        result = websocket_manager._serialize_message_safely(None)
        assert result == {}

    @pytest.mark.asyncio 
    async def test_deep_agent_state_json_serialization(self, websocket_manager, complex_agent_state):
        """Test DeepAgentState serialization in WebSocket context."""
        
        # Test direct serialization
        result = websocket_manager._serialize_message_safely(complex_agent_state)
        
        # Verify it's JSON serializable
        json_str = json.dumps(result)
        deserialized = json.loads(json_str)
        
        # Verify core fields are preserved
        assert deserialized["user_request"] == "Optimize our cloud infrastructure costs"
        assert deserialized["run_id"] == "run-12345"
        assert deserialized["step_count"] == 5
        
        # Verify complex nested objects are serialized
        assert "optimizations_result" in deserialized
        assert deserialized["optimizations_result"]["cost_savings"] == 1250.75
        assert "action_plan_result" in deserialized
        assert len(deserialized["action_plan_result"]["actions"]) == 2

    @pytest.mark.asyncio
    async def test_async_serialization_performance(self, websocket_manager, complex_agent_state):
        """Test async serialization performance and timeout handling."""
        
        start_time = time.time()
        result = await websocket_manager._serialize_message_safely_async(complex_agent_state)
        end_time = time.time()
        
        # Should complete quickly (under 1 second)
        assert (end_time - start_time) < 1.0
        
        # Result should be JSON serializable
        json_str = json.dumps(result)
        assert json_str is not None
        
        # Verify complex data is preserved
        deserialized = json.loads(json_str)
        assert deserialized["optimizations_result"]["cost_savings"] == 1250.75

    @pytest.mark.asyncio
    async def test_websocket_message_type_conversion(self, websocket_manager):
        """Test message type conversion for frontend compatibility."""
        
        # Test backend message types get converted to frontend types
        backend_message = {
            "type": "agent_status_update", 
            "payload": {"status": "processing"}
        }
        
        result = websocket_manager._serialize_message_safely(backend_message)
        
        # Verify type conversion (should use get_frontend_message_type)
        expected_frontend_type = get_frontend_message_type("agent_status_update")
        assert result["type"] == expected_frontend_type

    @pytest.mark.asyncio
    async def test_websocket_send_with_timeout_and_retry(self, websocket_manager):
        """Test WebSocket send with timeout and retry mechanism."""
        
        # Create mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()
        
        # Create mock connection info
        conn_info = {
            "websocket": mock_websocket,
            "message_count": 0,
            "last_activity": datetime.now(timezone.utc)
        }
        
        message_dict = {"type": "test", "payload": {"message": "hello"}}
        conn_id = "test-conn-123"
        
        # Test successful send
        result = await websocket_manager._send_to_connection_with_retry(
            conn_id, mock_websocket, message_dict, conn_info
        )
        
        assert result is True
        mock_websocket.send_json.assert_called_once_with(message_dict, timeout=5.0)
        
        # Verify timeout_used attribute is set on websocket for test compatibility
        assert hasattr(mock_websocket, 'timeout_used')
        assert mock_websocket.timeout_used == 5.0

    @pytest.mark.asyncio
    async def test_websocket_send_timeout_handling(self, websocket_manager):
        """Test WebSocket timeout handling with retries."""
        
        # Create mock WebSocket that times out
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock(side_effect=asyncio.TimeoutError("Send timeout"))
        
        conn_info = {"websocket": mock_websocket, "message_count": 0}
        message_dict = {"type": "test", "payload": {}}
        conn_id = "test-conn-timeout"
        
        # Should retry and eventually fail
        result = await websocket_manager._send_to_connection_with_retry(
            conn_id, mock_websocket, message_dict, conn_info
        )
        
        assert result is False
        # Should attempt 3 times (max_retries=3)
        assert mock_websocket.send_json.call_count == 3
        
        # Verify timeout stats are incremented
        assert websocket_manager.connection_stats["send_timeouts"] > 0
        assert websocket_manager.connection_stats["timeout_failures"] > 0

    @pytest.mark.asyncio
    async def test_all_websocket_event_types_serialize(self, websocket_notifier, agent_context):
        """Test that all critical WebSocket event types can be JSON serialized."""
        
        # List of all critical events that must work
        critical_events = [
            ("agent_started", lambda: websocket_notifier.send_agent_started(agent_context)),
            ("agent_thinking", lambda: websocket_notifier.send_agent_thinking(
                agent_context, "Analyzing request", 1)),
            ("tool_executing", lambda: websocket_notifier.send_tool_executing(
                agent_context, "analysis_tool")),
            ("tool_completed", lambda: websocket_notifier.send_tool_completed(
                agent_context, "analysis_tool", {"result": "success"})),
            ("agent_completed", lambda: websocket_notifier.send_agent_completed(
                agent_context, {"status": "complete"}, 1000.0))
        ]
        
        for event_name, send_func in critical_events:
            # Reset the mock
            websocket_notifier.websocket_manager.send_to_thread.reset_mock()
            
            # Send the event
            await send_func()
            
            # Verify it was sent and is JSON serializable
            assert websocket_notifier.websocket_manager.send_to_thread.called, f"{event_name} was not sent"
            
            thread_id, message_dict = websocket_notifier.websocket_manager.send_to_thread.call_args[0]
            
            # Critical: Must be JSON serializable
            try:
                json_str = json.dumps(message_dict)
                deserialized = json.loads(json_str)
                assert deserialized["type"] == event_name
            except (TypeError, ValueError) as e:
                pytest.fail(f"CRITICAL: {event_name} event is not JSON serializable: {e}")

    @pytest.mark.asyncio
    async def test_websocket_error_recovery_json_serialization(self, websocket_manager):
        """Test that error recovery messages serialize correctly."""
        
        # Test error message with complex error details
        error_details = {
            "error_type": "TimeoutError",
            "stack_trace": ["line 1", "line 2", "line 3"],
            "context": {"user_id": "123", "thread_id": "456"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        error_message = {
            "type": "error",
            "payload": {
                "error_message": "WebSocket connection lost",
                "error_code": "WS_CONNECTION_LOST",
                "error_details": error_details,
                "recovery_action": "reconnect"
            }
        }
        
        # Test serialization
        result = websocket_manager._serialize_message_safely(error_message)
        
        # Must be JSON serializable
        json_str = json.dumps(result)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "error"
        assert "error_details" in deserialized["payload"]
        assert len(deserialized["payload"]["error_details"]["stack_trace"]) == 3

    @pytest.mark.asyncio
    async def test_websocket_concurrent_serialization(self, websocket_manager):
        """Test concurrent serialization doesn't cause issues."""
        
        # Create multiple complex messages
        messages = []
        for i in range(10):
            complex_state = DeepAgentState(
                user_request=f"Request {i}",
                run_id=f"run-{i}",
                step_count=i,
                optimizations_result=OptimizationsResult(
                    optimization_type=f"type_{i}",
                    recommendations=[f"rec_{i}_1", f"rec_{i}_2"],
                    cost_savings=float(i * 100)
                )
            )
            messages.append(complex_state)
        
        # Serialize all concurrently
        tasks = [
            websocket_manager._serialize_message_safely_async(msg) 
            for msg in messages
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed and be JSON serializable
        assert len(results) == 10
        
        for i, result in enumerate(results):
            json_str = json.dumps(result)
            deserialized = json.loads(json_str)
            assert deserialized["user_request"] == f"Request {i}"
            assert deserialized["run_id"] == f"run-{i}"

    def test_websocket_message_size_limits(self, websocket_manager):
        """Test WebSocket message size handling."""
        
        # Create a very large message
        large_content = "x" * 100000  # 100KB of content
        large_message = {
            "type": "large_message",
            "payload": {
                "content": large_content,
                "metadata": {"size": len(large_content)}
            }
        }
        
        # Should still serialize (WebSocket manager handles size limits)
        result = websocket_manager._serialize_message_safely(large_message)
        
        # Should be JSON serializable
        json_str = json.dumps(result)
        assert len(json_str) > 100000
        
        # Verify content is preserved
        deserialized = json.loads(json_str)
        assert len(deserialized["payload"]["content"]) == 100000

    @pytest.mark.asyncio
    async def test_websocket_circuit_breaker_integration(self, websocket_manager):
        """Test WebSocket integration with circuit breaker patterns."""
        
        # Test circuit breaker status message serialization
        circuit_breaker_message = {
            "type": "circuit_breaker_status",
            "payload": {
                "service": "agent_execution", 
                "state": "OPEN",
                "failure_count": 5,
                "last_failure_time": datetime.now(timezone.utc).isoformat(),
                "next_attempt_time": datetime.now(timezone.utc).isoformat(),
                "error_details": {
                    "recent_errors": ["timeout", "connection_error", "serialization_error"]
                }
            }
        }
        
        # Must serialize properly for UI display
        result = websocket_manager._serialize_message_safely(circuit_breaker_message)
        json_str = json.dumps(result)
        deserialized = json.loads(json_str)
        
        assert deserialized["type"] == "circuit_breaker_status"
        assert deserialized["payload"]["state"] == "OPEN"
        assert len(deserialized["payload"]["error_details"]["recent_errors"]) == 3

    @pytest.mark.asyncio
    async def test_websocket_message_ordering_preservation(self, websocket_manager, agent_context):
        """Test that WebSocket message ordering is preserved during serialization."""
        
        # Create sequence of messages that must maintain order
        messages = [
            {"type": "agent_started", "payload": {"agent_name": "test", "sequence": 1}},
            {"type": "agent_thinking", "payload": {"thought": "step 1", "sequence": 2}},
            {"type": "tool_executing", "payload": {"tool": "analyzer", "sequence": 3}},
            {"type": "tool_completed", "payload": {"result": "done", "sequence": 4}}, 
            {"type": "agent_completed", "payload": {"status": "success", "sequence": 5}}
        ]
        
        # Serialize all messages
        serialized_messages = []
        for msg in messages:
            result = websocket_manager._serialize_message_safely(msg)
            json_str = json.dumps(result)
            deserialized = json.loads(json_str)
            serialized_messages.append(deserialized)
        
        # Verify order is preserved
        for i, msg in enumerate(serialized_messages, 1):
            assert msg["payload"]["sequence"] == i
            
    def test_websocket_special_characters_handling(self, websocket_manager):
        """Test WebSocket handling of special characters and unicode."""
        
        # Message with various special characters and unicode
        special_message = {
            "type": "agent_message",
            "payload": {
                "content": "Hello 🌟 Special chars: áéíóú ñ çÇ 中文 русский العربية",
                "emojis": ["😀", "🚀", "💡", "⚡"],
                "symbols": ["@", "#", "$", "%", "&", "*"],
                "quotes": ["'single'", '"double"', "`backtick`"],
                "unicode_points": ["\u2603", "\u2764", "\u1F4A1"]  # ☃ ❤ 💡
            }
        }
        
        # Should serialize without issues
        result = websocket_manager._serialize_message_safely(special_message)
        json_str = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(json_str)
        
        # Verify special characters are preserved
        assert "🌟" in deserialized["payload"]["content"]
        assert len(deserialized["payload"]["emojis"]) == 4
        assert "💡" in deserialized["payload"]["emojis"]