"""
Comprehensive test suite for WebSocket JSON serialization.
Ensures all WebSocket messages with datetime or complex objects are properly serialized.

This prevents regressions of the error:
"Object of type DeepAgentState is not JSON serializable"
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.schemas.agent import AgentCompleted
from netra_backend.app.schemas.agent_models import AgentMetadata, AgentResult
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.websocket_core.handlers import UserMessageHandler
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core.types import ServerMessage, create_server_message
import asyncio


class TestWebSocketJSONSerialization:
    """Test suite for WebSocket JSON serialization."""
    pass

    @pytest.fixture
    def websocket_manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a WebSocket manager instance."""
    pass
        return WebSocketManager()

    @pytest.fixture
    def pipeline_executor(self, websocket_manager):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a pipeline executor with websocket manager."""
        mock_engine = MagicNone  # TODO: Use real service instance
    pass
        mock_session = MagicNone  # TODO: Use real service instance
        executor = PipelineExecutor(engine=mock_engine, websocket_manager=websocket_manager, db_session=mock_session)
        return executor

    def test_websocket_manager_serialize_deep_agent_state(self, websocket_manager):
        """Test that WebSocketManager properly serializes DeepAgentState."""
        state = DeepAgentState(
            user_request="Test request",
            metadata=AgentMetadata(
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
        )
        
        # Test _serialize_message_safely
        serialized = websocket_manager._serialize_message_safely(state)
        
        # Should be JSON serializable
        json_str = json.dumps(serialized)
        assert json_str is not None
        
        # Parse back and verify
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "Test request"
        assert isinstance(parsed["metadata"]["created_at"], str)

    def test_pipeline_executor_websocket_message_creation(self, pipeline_executor):
        """Test that PipelineExecutor creates properly serializable WebSocket messages."""
    pass
        state = DeepAgentState(
            user_request="Pipeline test",
            chat_thread_id="thread-123"
        )
        
        # Create completion content
        content = pipeline_executor._create_completion_content(state, "run-123")
        
        # Create WebSocket message
        ws_message = pipeline_executor._create_websocket_message(content)
        
        # Get the dict that would be sent
        message_dict = ws_message.model_dump(mode='json')
        
        # Should be JSON serializable
        json_str = json.dumps(message_dict)
        assert json_str is not None
        
        # Verify structure
        parsed = json.loads(json_str)
        assert parsed["type"] == "agent_completed"
        assert parsed["payload"]["run_id"] == "run-123"
        assert parsed["payload"]["result"]["output"]["user_request"] == "Pipeline test"

    def test_server_message_with_datetime(self):
        """Test that ServerMessage with datetime serializes correctly."""
        msg = create_server_message(
            "test_message",
            {"data": "test", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        # Should have float timestamp, not datetime
        assert isinstance(msg.timestamp, float)
        
        # Should serialize properly
        msg_dict = msg.model_dump(mode='json')
        json_str = json.dumps(msg_dict)
        assert json_str is not None

    @pytest.mark.asyncio
    async def test_websocket_send_with_deep_agent_state(self, websocket_manager):
        """Test sending DeepAgentState through WebSocket manager."""
    pass
        state = DeepAgentState(
            user_request="Send test",
            metadata=AgentMetadata(
                created_at=datetime.now(timezone.utc),
                custom_fields={"key": "value"}
            )
        )
        
        # Mock WebSocket connection
        mock_websocket = AsyncNone  # TODO: Use real service instance
        mock_websocket.send_json = AsyncNone  # TODO: Use real service instance
        
        # Add connection
        conn_id = "test-conn-123"
        websocket_manager.connections[conn_id] = {
            "websocket": mock_websocket,
            "user_id": "user-123",
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Send DeepAgentState directly (this is what was failing)
        result = await websocket_manager._send_to_connection(conn_id, state)
        
        # Should succeed
        assert result is True
        
        # Verify send_json was called with proper dict
        mock_websocket.send_json.assert_called_once()
        sent_data = mock_websocket.send_json.call_args[0][0]
        
        # Verify it's a dict and JSON serializable
        assert isinstance(sent_data, dict)
        json_str = json.dumps(sent_data)
        assert json_str is not None

    def test_agent_completed_message_serialization(self):
        """Test AgentCompleted message with DeepAgentState output."""
        state = DeepAgentState(
            user_request="Completion test",
            step_count=5,
            metadata=AgentMetadata(priority=10)
        )
        
        # Create AgentResult with DeepAgentState dict
        result = AgentResult(
            success=True,
            output=state.to_dict(),
            execution_time_ms=100.5
        )
        
        # Create AgentCompleted
        completed = AgentCompleted(
            run_id="run-456",
            result=result,
            execution_time_ms=100.5
        )
        
        # Serialize with mode='json'
        completed_dict = completed.model_dump(mode='json')
        
        # Should be JSON serializable
        json_str = json.dumps(completed_dict)
        assert json_str is not None
        
        # Verify structure
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run-456"
        assert parsed["result"]["success"] is True
        assert parsed["result"]["output"]["user_request"] == "Completion test"
        assert parsed["result"]["output"]["step_count"] == 5

    def test_websocket_message_with_nested_datetime(self):
        """Test WebSocketMessage with nested datetime objects."""
    pass
        # Create a message with nested datetime
        payload = {
            "data": {
                "state": DeepAgentState(
                    user_request="Nested test",
                    metadata=AgentMetadata(
                        created_at=datetime.now(timezone.utc),
                        last_updated=datetime.now(timezone.utc)
                    )
                ).to_dict(),  # Convert to dict properly
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        ws_msg = WebSocketMessage(
            type="custom_message",
            payload=payload
        )
        
        # Serialize with mode='json'
        msg_dict = ws_msg.model_dump(mode='json')
        
        # Should be JSON serializable
        json_str = json.dumps(msg_dict)
        assert json_str is not None
        
        # Parse and verify
        parsed = json.loads(json_str)
        assert parsed["type"] == "custom_message"
        assert parsed["payload"]["data"]["state"]["user_request"] == "Nested test"

    @pytest.mark.parametrize("model_dump_mode", [None, 'json'])
    def test_model_dump_mode_importance(self, model_dump_mode):
        """Test the importance of using mode='json' in model_dump."""
        state = DeepAgentState(
            user_request="Mode test",
            metadata=AgentMetadata(created_at=datetime.now(timezone.utc))
        )
        
        result = AgentResult(success=True, output=state.to_dict())
        completed = AgentCompleted(run_id="run-789", result=result, execution_time_ms=50.0)
        
        if model_dump_mode:
            # With mode='json' - should work
            completed_dict = completed.model_dump(mode=model_dump_mode)
            try:
                json_str = json.dumps(completed_dict)
                assert json_str is not None
                success = True
            except TypeError:
                success = False
            assert success, "Should serialize with mode='json'"
        else:
            # Without mode - might fail if any datetime present
            completed_dict = completed.model_dump()
            # This is okay because state.to_dict() already converted datetime
            json_str = json.dumps(completed_dict)
            assert json_str is not None

    def test_websocket_handler_message_serialization(self):
        """Test that WebSocket handlers properly serialize messages."""
    pass
        handler = UserMessageHandler()
        
        # Create a mock response with datetime
        response = create_server_message(
            "heartbeat_ack",
            {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        # The response should be serializable
        response_dict = response.model_dump(mode='json')
        json_str = json.dumps(response_dict)
        assert json_str is not None
        
        # Verify timestamp is float
        assert isinstance(response.timestamp, float)

    def test_regression_websocket_manager_send_to_thread(self):
        """
        Regression test for the specific flow that was failing:
        WebSocketManager.send_to_thread with DeepAgentState
        """
    pass
        manager = WebSocketManager()
        
        # Create state that would have caused the error
        state = DeepAgentState(
            user_request="Regression test",
            metadata=AgentMetadata(
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                custom_fields={"test": "value"}
            )
        )
        
        # The manager should handle this correctly
        serialized = manager._serialize_message_safely(state)
        
        # Should be JSON serializable
        try:
            json_str = json.dumps(serialized)
            success = True
        except TypeError as e:
            if "not JSON serializable" in str(e):
                success = False
                raise AssertionError(f"Regression detected: {e}")
            raise
        
        assert success, "WebSocketManager should properly serialize DeepAgentState"

    def test_all_websocket_message_types_serializable(self):
        """Test that all WebSocket message types are properly serializable."""
        from netra_backend.app.websocket_core.types import (
            ErrorMessage,
            MessageType,
            ServerMessage,
            WebSocketStats)
        
        # Test ErrorMessage
        error_msg = ErrorMessage(
            type=MessageType.ERROR_MESSAGE,
            error_code="TEST_ERROR",
            error_message="Test error message",
            details={"detail": "value"},
            timestamp=1234567890.0
        )
        json.dumps(error_msg.model_dump(mode='json'))
        
        # Test ServerMessage
        server_msg = ServerMessage(
            type=MessageType.SYSTEM_MESSAGE,
            data={"message": "test"},
            timestamp=1234567890.0,
            server_id="server-1"
        )
        json.dumps(server_msg.model_dump(mode='json'))
        
        # Test WebSocketStats
        stats = WebSocketStats(
            active_connections=5,
            total_messages=100,
            messages_per_second=10.5,
            uptime_seconds=3600.0,
            last_activity=datetime.now(timezone.utc)
        )
        json.dumps(stats.model_dump(mode='json'))

    def test_fix_prevents_original_error(self):
        """
    pass
        Test that our fix prevents the original error:
        "Object of type DeepAgentState is not JSON serializable"
        
        This test simulates the exact scenario that was failing.
        """
        # Create the exact scenario from the error log
        state = DeepAgentState(
            user_request="Original error test",
            chat_thread_id="dev-temp-a7108989",
            user_id="c427ade4"
        )
        
        # Add metadata with datetime (likely cause of serialization issue)
        state.metadata = AgentMetadata(
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        
        # Test 1: Direct serialization should fail
        with pytest.raises(TypeError, match="not JSON serializable"):
            json.dumps(state)
        
        # Test 2: Using to_dict() should work
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        assert json_str is not None
        
        # Test 3: WebSocketManager should handle it
        manager = WebSocketManager()
        serialized = manager._serialize_message_safely(state)
        json_str = json.dumps(serialized)
        assert json_str is not None
        
        # Test 4: Pipeline executor flow should work
        from netra_backend.app.schemas.agent import AgentCompleted
        from netra_backend.app.schemas.agent_models import AgentResult
        
        result = AgentResult(success=True, output=state.to_dict())
        completed = AgentCompleted(run_id="run-test", result=result, execution_time_ms=100.0)
        
        # With our fix (mode='json')
        completed_dict = completed.model_dump(mode='json')
        json_str = json.dumps(completed_dict)
        assert json_str is not None
        
        print("✅ All serialization tests passed - regression prevented!")


if __name__ == "__main__":
    # Run a quick test
    test = TestWebSocketJSONSerialization()
    test.test_fix_prevents_original_error()
    print("Manual test passed!")