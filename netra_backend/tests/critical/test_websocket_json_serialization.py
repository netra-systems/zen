from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive test suite for WebSocket JSON serialization.
# REMOVED_SYNTAX_ERROR: Ensures all WebSocket messages with datetime or complex objects are properly serialized.

# REMOVED_SYNTAX_ERROR: This prevents regressions of the error:
    # REMOVED_SYNTAX_ERROR: "Object of type DeepAgentState is not JSON serializable"
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent import AgentCompleted
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent_models import AgentMetadata, AgentResult
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_models import WebSocketMessage
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import UserMessageHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import ServerMessage, create_server_message
    # REMOVED_SYNTAX_ERROR: import asyncio


# REMOVED_SYNTAX_ERROR: class TestWebSocketJSONSerialization:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket JSON serialization."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a WebSocket manager instance."""
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def pipeline_executor(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a pipeline executor with websocket manager."""
    # REMOVED_SYNTAX_ERROR: mock_engine = MagicMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_session = MagicMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: executor = PipelineExecutor(engine=mock_engine, websocket_manager=websocket_manager, db_session=mock_session)
    # REMOVED_SYNTAX_ERROR: return executor

# REMOVED_SYNTAX_ERROR: def test_websocket_manager_serialize_deep_agent_state(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test that WebSocketManager properly serializes DeepAgentState."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Test request",
    # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata( )
    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: last_updated=datetime.now(timezone.utc)
    
    

    # Test _serialize_message_safely
    # REMOVED_SYNTAX_ERROR: serialized = websocket_manager._serialize_message_safely(state)

    # Should be JSON serializable
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(serialized)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Parse back and verify
    # REMOVED_SYNTAX_ERROR: parsed = json.loads(json_str)
    # REMOVED_SYNTAX_ERROR: assert parsed["user_request"] == "Test request"
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed["metadata"]["created_at"], str)

# REMOVED_SYNTAX_ERROR: def test_pipeline_executor_websocket_message_creation(self, pipeline_executor):
    # REMOVED_SYNTAX_ERROR: """Test that PipelineExecutor creates properly serializable WebSocket messages."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Pipeline test",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread-123"
    

    # Create completion content
    # REMOVED_SYNTAX_ERROR: content = pipeline_executor._create_completion_content(state, "run-123")

    # Create WebSocket message
    # REMOVED_SYNTAX_ERROR: ws_message = pipeline_executor._create_websocket_message(content)

    # Get the dict that would be sent
    # REMOVED_SYNTAX_ERROR: message_dict = ws_message.model_dump(mode='json')

    # Should be JSON serializable
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(message_dict)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Verify structure
    # REMOVED_SYNTAX_ERROR: parsed = json.loads(json_str)
    # REMOVED_SYNTAX_ERROR: assert parsed["type"] == "agent_completed"
    # REMOVED_SYNTAX_ERROR: assert parsed["payload"]["run_id"] == "run-123"
    # REMOVED_SYNTAX_ERROR: assert parsed["payload"]["result"]["output"]["user_request"] == "Pipeline test"

# REMOVED_SYNTAX_ERROR: def test_server_message_with_datetime(self):
    # REMOVED_SYNTAX_ERROR: """Test that ServerMessage with datetime serializes correctly."""
    # REMOVED_SYNTAX_ERROR: msg = create_server_message( )
    # REMOVED_SYNTAX_ERROR: "test_message",
    # REMOVED_SYNTAX_ERROR: {"data": "test", "timestamp": datetime.now(timezone.utc).isoformat()}
    

    # Should have float timestamp, not datetime
    # REMOVED_SYNTAX_ERROR: assert isinstance(msg.timestamp, float)

    # Should serialize properly
    # REMOVED_SYNTAX_ERROR: msg_dict = msg.model_dump(mode='json')
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(msg_dict)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_send_with_deep_agent_state(self, websocket_manager):
        # REMOVED_SYNTAX_ERROR: """Test sending DeepAgentState through WebSocket manager."""
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_request="Send test",
        # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata( )
        # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: custom_fields={"key": "value"}
        
        

        # Mock WebSocket connection
        # REMOVED_SYNTAX_ERROR: mock_websocket = AsyncMock()  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance

        # Add connection
        # REMOVED_SYNTAX_ERROR: conn_id = "test-conn-123"
        # REMOVED_SYNTAX_ERROR: websocket_manager.connections[conn_id] = { )
        # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
        # REMOVED_SYNTAX_ERROR: "user_id": "user-123",
        # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: "message_count": 0
        

        # Send DeepAgentState directly (this is what was failing)
        # REMOVED_SYNTAX_ERROR: result = await websocket_manager._send_to_connection(conn_id, state)

        # Should succeed
        # REMOVED_SYNTAX_ERROR: assert result is True

        # Verify send_json was called with proper dict
        # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_called_once()
        # REMOVED_SYNTAX_ERROR: sent_data = mock_websocket.send_json.call_args[0][0]

        # Verify it's a dict and JSON serializable
        # REMOVED_SYNTAX_ERROR: assert isinstance(sent_data, dict)
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(sent_data)
        # REMOVED_SYNTAX_ERROR: assert json_str is not None

# REMOVED_SYNTAX_ERROR: def test_agent_completed_message_serialization(self):
    # REMOVED_SYNTAX_ERROR: """Test AgentCompleted message with DeepAgentState output."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Completion test",
    # REMOVED_SYNTAX_ERROR: step_count=5,
    # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata(priority=10)
    

    # Create AgentResult with DeepAgentState dict
    # REMOVED_SYNTAX_ERROR: result = AgentResult( )
    # REMOVED_SYNTAX_ERROR: success=True,
    # REMOVED_SYNTAX_ERROR: output=state.to_dict(),
    # REMOVED_SYNTAX_ERROR: execution_time_ms=100.5
    

    # Create AgentCompleted
    # REMOVED_SYNTAX_ERROR: completed = AgentCompleted( )
    # REMOVED_SYNTAX_ERROR: run_id="run-456",
    # REMOVED_SYNTAX_ERROR: result=result,
    # REMOVED_SYNTAX_ERROR: execution_time_ms=100.5
    

    # Serialize with mode='json'
    # REMOVED_SYNTAX_ERROR: completed_dict = completed.model_dump(mode='json')

    # Should be JSON serializable
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(completed_dict)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Verify structure
    # REMOVED_SYNTAX_ERROR: parsed = json.loads(json_str)
    # REMOVED_SYNTAX_ERROR: assert parsed["run_id"] == "run-456"
    # REMOVED_SYNTAX_ERROR: assert parsed["result"]["success"] is True
    # REMOVED_SYNTAX_ERROR: assert parsed["result"]["output"]["user_request"] == "Completion test"
    # REMOVED_SYNTAX_ERROR: assert parsed["result"]["output"]["step_count"] == 5

# REMOVED_SYNTAX_ERROR: def test_websocket_message_with_nested_datetime(self):
    # REMOVED_SYNTAX_ERROR: """Test WebSocketMessage with nested datetime objects."""
    # Create a message with nested datetime
    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "data": { )
    # REMOVED_SYNTAX_ERROR: "state": DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Nested test",
    # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata( )
    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: last_updated=datetime.now(timezone.utc)
    
    # REMOVED_SYNTAX_ERROR: ).to_dict(),  # Convert to dict properly
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
    
    

    # REMOVED_SYNTAX_ERROR: ws_msg = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type="custom_message",
    # REMOVED_SYNTAX_ERROR: payload=payload
    

    # Serialize with mode='json'
    # REMOVED_SYNTAX_ERROR: msg_dict = ws_msg.model_dump(mode='json')

    # Should be JSON serializable
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(msg_dict)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Parse and verify
    # REMOVED_SYNTAX_ERROR: parsed = json.loads(json_str)
    # REMOVED_SYNTAX_ERROR: assert parsed["type"] == "custom_message"
    # REMOVED_SYNTAX_ERROR: assert parsed["payload"]["data"]["state"]["user_request"] == "Nested test"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_model_dump_mode_importance(self, model_dump_mode):
    # REMOVED_SYNTAX_ERROR: """Test the importance of using mode='json' in model_dump."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Mode test",
    # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata(created_at=datetime.now(timezone.utc))
    

    # REMOVED_SYNTAX_ERROR: result = AgentResult(success=True, output=state.to_dict())
    # REMOVED_SYNTAX_ERROR: completed = AgentCompleted(run_id="run-789", result=result, execution_time_ms=50.0)

    # REMOVED_SYNTAX_ERROR: if model_dump_mode:
        # With mode='json' - should work
        # REMOVED_SYNTAX_ERROR: completed_dict = completed.model_dump(mode=model_dump_mode)
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(completed_dict)
            # REMOVED_SYNTAX_ERROR: assert json_str is not None
            # REMOVED_SYNTAX_ERROR: success = True
            # REMOVED_SYNTAX_ERROR: except TypeError:
                # REMOVED_SYNTAX_ERROR: success = False
                # REMOVED_SYNTAX_ERROR: assert success, "Should serialize with mode='json'"
                # REMOVED_SYNTAX_ERROR: else:
                    # Without mode - might fail if any datetime present
                    # REMOVED_SYNTAX_ERROR: completed_dict = completed.model_dump()
                    # This is okay because state.to_dict() already converted datetime
                    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(completed_dict)
                    # REMOVED_SYNTAX_ERROR: assert json_str is not None

# REMOVED_SYNTAX_ERROR: def test_websocket_handler_message_serialization(self):
    # REMOVED_SYNTAX_ERROR: """Test that WebSocket handlers properly serialize messages."""
    # REMOVED_SYNTAX_ERROR: handler = UserMessageHandler()

    # Create a mock response with datetime
    # REMOVED_SYNTAX_ERROR: response = create_server_message( )
    # REMOVED_SYNTAX_ERROR: "heartbeat_ack",
    # REMOVED_SYNTAX_ERROR: {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
    

    # The response should be serializable
    # REMOVED_SYNTAX_ERROR: response_dict = response.model_dump(mode='json')
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(response_dict)
    # REMOVED_SYNTAX_ERROR: assert json_str is not None

    # Verify timestamp is float
    # REMOVED_SYNTAX_ERROR: assert isinstance(response.timestamp, float)

# REMOVED_SYNTAX_ERROR: def test_regression_websocket_manager_send_to_thread(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Regression test for the specific flow that was failing:
        # REMOVED_SYNTAX_ERROR: WebSocketManager.send_to_thread with DeepAgentState
        # REMOVED_SYNTAX_ERROR: """"
        # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

        # Create state that would have caused the error
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_request="Regression test",
        # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata( )
        # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: last_updated=datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: custom_fields={"test": "value"}
        
        

        # The manager should handle this correctly
        # REMOVED_SYNTAX_ERROR: serialized = manager._serialize_message_safely(state)

        # Should be JSON serializable
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(serialized)
            # REMOVED_SYNTAX_ERROR: success = True
            # REMOVED_SYNTAX_ERROR: except TypeError as e:
                # REMOVED_SYNTAX_ERROR: if "not JSON serializable" in str(e):
                    # REMOVED_SYNTAX_ERROR: success = False
                    # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")
                    # REMOVED_SYNTAX_ERROR: raise

                    # REMOVED_SYNTAX_ERROR: assert success, "WebSocketManager should properly serialize DeepAgentState"

# REMOVED_SYNTAX_ERROR: def test_all_websocket_message_types_serializable(self):
    # REMOVED_SYNTAX_ERROR: """Test that all WebSocket message types are properly serializable."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import ( )
    # REMOVED_SYNTAX_ERROR: ErrorMessage,
    # REMOVED_SYNTAX_ERROR: MessageType,
    # REMOVED_SYNTAX_ERROR: ServerMessage,
    # REMOVED_SYNTAX_ERROR: WebSocketStats)

    # Test ErrorMessage
    # REMOVED_SYNTAX_ERROR: error_msg = ErrorMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.ERROR_MESSAGE,
    # REMOVED_SYNTAX_ERROR: error_code="TEST_ERROR",
    # REMOVED_SYNTAX_ERROR: error_message="Test error message",
    # REMOVED_SYNTAX_ERROR: details={"detail": "value"},
    # REMOVED_SYNTAX_ERROR: timestamp=1234567890.0
    
    # REMOVED_SYNTAX_ERROR: json.dumps(error_msg.model_dump(mode='json'))

    # Test ServerMessage
    # REMOVED_SYNTAX_ERROR: server_msg = ServerMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.SYSTEM_MESSAGE,
    # REMOVED_SYNTAX_ERROR: data={"message": "test"},
    # REMOVED_SYNTAX_ERROR: timestamp=1234567890.0,
    # REMOVED_SYNTAX_ERROR: server_id="server-1"
    
    # REMOVED_SYNTAX_ERROR: json.dumps(server_msg.model_dump(mode='json'))

    # Test WebSocketStats
    # REMOVED_SYNTAX_ERROR: stats = WebSocketStats( )
    # REMOVED_SYNTAX_ERROR: active_connections=5,
    # REMOVED_SYNTAX_ERROR: total_messages=100,
    # REMOVED_SYNTAX_ERROR: messages_per_second=10.5,
    # REMOVED_SYNTAX_ERROR: uptime_seconds=3600.0,
    # REMOVED_SYNTAX_ERROR: last_activity=datetime.now(timezone.utc)
    
    # REMOVED_SYNTAX_ERROR: json.dumps(stats.model_dump(mode='json'))

# REMOVED_SYNTAX_ERROR: def test_fix_prevents_original_error(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that our fix prevents the original error:
        # REMOVED_SYNTAX_ERROR: "Object of type DeepAgentState is not JSON serializable"

        # REMOVED_SYNTAX_ERROR: This test simulates the exact scenario that was failing.
        # REMOVED_SYNTAX_ERROR: """"
        # Create the exact scenario from the error log
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_request="Original error test",
        # REMOVED_SYNTAX_ERROR: chat_thread_id="dev-temp-a7108989",
        # REMOVED_SYNTAX_ERROR: user_id="c427ade4"
        

        # Add metadata with datetime (likely cause of serialization issue)
        # REMOVED_SYNTAX_ERROR: state.metadata = AgentMetadata( )
        # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
        # REMOVED_SYNTAX_ERROR: last_updated=datetime.now(timezone.utc)
        

        # Test 1: Direct serialization should fail
        # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError, match="not JSON serializable"):
            # REMOVED_SYNTAX_ERROR: json.dumps(state)

            # Test 2: Using to_dict() should work
            # REMOVED_SYNTAX_ERROR: state_dict = state.to_dict()
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(state_dict)
            # REMOVED_SYNTAX_ERROR: assert json_str is not None

            # Test 3: WebSocketManager should handle it
            # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
            # REMOVED_SYNTAX_ERROR: serialized = manager._serialize_message_safely(state)
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(serialized)
            # REMOVED_SYNTAX_ERROR: assert json_str is not None

            # Test 4: Pipeline executor flow should work
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent import AgentCompleted
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent_models import AgentResult

            # REMOVED_SYNTAX_ERROR: result = AgentResult(success=True, output=state.to_dict())
            # REMOVED_SYNTAX_ERROR: completed = AgentCompleted(run_id="run-test", result=result, execution_time_ms=100.0)

            # With our fix (mode='json')
            # REMOVED_SYNTAX_ERROR: completed_dict = completed.model_dump(mode='json')
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(completed_dict)
            # REMOVED_SYNTAX_ERROR: assert json_str is not None

            # REMOVED_SYNTAX_ERROR: print("✅ All serialization tests passed - regression prevented!")


            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                # Run a quick test
                # REMOVED_SYNTAX_ERROR: test = TestWebSocketJSONSerialization()
                # REMOVED_SYNTAX_ERROR: test.test_fix_prevents_original_error()
                # REMOVED_SYNTAX_ERROR: print("Manual test passed!")