"""Simple Type Safety Tests for Frontend-Backend Communication.

Focused tests that validate core type consistency.
"""

import json
import pytest
from typing import Dict, Any
from datetime import datetime
from pydantic import ValidationError

# Import backend schemas
from app.schemas.websocket_unified import (
    WebSocketMessageType,
    StartAgentPayload,
    UserMessagePayload,
    WebSocketMessage,
    StreamChunk,
    AgentUpdate
)
from app.schemas.Message import Message, MessageType
from app.schemas.Agent import AgentStarted, AgentCompleted
from app.schemas.Tool import ToolStarted, ToolCompleted, ToolStatus


class TestBasicTypeSafety:
    """Test basic type safety between frontend and backend."""
    
    def test_websocket_message_types(self):
        """Test WebSocket message type enum values."""
        # These are the types that frontend sends
        frontend_types = [
            "start_agent",
            "user_message",
            "stop_agent",
            "create_thread",
            "switch_thread",
            "delete_thread",
            "rename_thread",
            "list_threads",
            "ping"
        ]
        
        for msg_type in frontend_types:
            try:
                ws_type = WebSocketMessageType(msg_type)
                assert ws_type.value == msg_type
            except ValueError:
                pytest.fail(f"Frontend message type '{msg_type}' not recognized by backend")
    
    def test_start_agent_payload(self):
        """Test StartAgent payload from frontend."""
        # This is what frontend typically sends
        frontend_payload = {
            "query": "Analyze system performance",
            "user_id": "user123",
            "thread_id": "thread456",
            "context": {
                "session_id": "session789",
                "source": "chat_ui"
            }
        }
        
        # Validate it works with backend schema
        try:
            payload = StartAgentPayload(**frontend_payload)
            assert payload.query == "Analyze system performance"
            assert payload.user_id == "user123"
            assert payload.thread_id == "thread456"
            assert payload.context["session_id"] == "session789"
        except ValidationError as e:
            pytest.fail(f"Frontend StartAgent payload doesn't match backend schema: {e}")
    
    def test_user_message_payload(self):
        """Test UserMessage payload from frontend."""
        frontend_payload = {
            "content": "What are the optimization opportunities?",
            "thread_id": "thread456",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "client_version": "1.0.0"
            }
        }
        
        try:
            payload = UserMessagePayload(**frontend_payload)
            assert payload.content == "What are the optimization opportunities?"
            assert payload.thread_id == "thread456"
        except ValidationError as e:
            pytest.fail(f"Frontend UserMessage payload doesn't match backend schema: {e}")
    
    def test_agent_response_types(self):
        """Test agent response types that go to frontend."""
        # AgentStarted response
        agent_started = AgentStarted(run_id="run123")
        started_json = agent_started.model_dump()
        assert "run_id" in started_json
        assert started_json["run_id"] == "run123"
        
        # AgentCompleted response
        agent_completed = AgentCompleted(
            run_id="run123",
            result={"status": "success", "findings": 5}
        )
        completed_json = agent_completed.model_dump()
        assert completed_json["result"]["findings"] == 5
        
        # AgentUpdate response
        agent_update = AgentUpdate(
            content="Processing data...",
            run_id="run123",
            metadata={"progress": 0.5}
        )
        update_json = agent_update.model_dump()
        assert update_json["content"] == "Processing data..."
    
    def test_tool_status_enum(self):
        """Test tool status enum values."""
        # Frontend expects these status values
        frontend_statuses = ["success", "error", "partial_success", "in_progress", "complete"]
        
        for status in frontend_statuses:
            try:
                tool_status = ToolStatus(status)
                assert tool_status.value == status
            except ValueError:
                pytest.fail(f"Frontend tool status '{status}' not recognized by backend")
    
    def test_message_type_enum(self):
        """Test message type enum values."""
        # Frontend expects these message types
        frontend_types = ["user", "agent", "system", "error", "tool"]
        
        for msg_type in frontend_types:
            try:
                message_type = MessageType(msg_type)
                assert message_type.value == msg_type
            except ValueError:
                pytest.fail(f"Frontend message type '{msg_type}' not recognized by backend")
    
    def test_streaming_chunks(self):
        """Test streaming chunk structure."""
        # What frontend expects to receive
        chunk_data = {
            "content": "Processing your request",
            "index": 0,
            "finished": False,
            "metadata": {"tokens": 4}
        }
        
        try:
            chunk = StreamChunk(**chunk_data)
            assert chunk.content == "Processing your request"
            assert chunk.index == 0
            assert chunk.finished is False
        except ValidationError as e:
            pytest.fail(f"Streaming chunk structure mismatch: {e}")
    
    def test_websocket_envelope(self):
        """Test WebSocket message envelope structure."""
        # Full message as sent by frontend
        message_data = {
            "type": "start_agent",
            "payload": {
                "query": "Test query",
                "user_id": "user123"
            }
        }
        
        try:
            # Validate type
            msg_type = WebSocketMessageType(message_data["type"])
            
            # Validate payload
            payload = StartAgentPayload(**message_data["payload"])
            
            # Create full message
            message = WebSocketMessage(
                type=msg_type,
                payload=payload.model_dump()
            )
            
            # Serialize to JSON (what goes over the wire)
            json_str = message.model_dump_json()
            parsed = json.loads(json_str)
            
            assert parsed["type"] == "start_agent"
            assert parsed["payload"]["query"] == "Test query"
        except (ValueError, ValidationError) as e:
            pytest.fail(f"WebSocket envelope structure mismatch: {e}")
    
    def test_optional_fields(self):
        """Test handling of optional fields."""
        # Minimal payload (only required fields)
        minimal = {
            "query": "Test query",
            "user_id": "user123"
        }
        
        try:
            payload = StartAgentPayload(**minimal)
            assert payload.query == "Test query"
            assert payload.thread_id is None  # Optional field
            assert payload.context is None  # Optional field
        except ValidationError as e:
            pytest.fail(f"Failed to handle optional fields: {e}")
        
        # Full payload (all fields)
        full = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": "thread456",
            "context": {"session": "abc123"}
        }
        
        try:
            payload = StartAgentPayload(**full)
            assert payload.thread_id == "thread456"
            assert payload.context == {"session": "abc123"}
        except ValidationError as e:
            pytest.fail(f"Failed to handle full payload: {e}")
    
    def test_datetime_serialization(self):
        """Test datetime handling between frontend and backend."""
        from datetime import timezone
        
        now = datetime.now(timezone.utc)
        
        # Create a message with datetime
        message = Message(
            id="msg123",
            type=MessageType.USER,
            content="Test message",
            timestamp=now,
            metadata={}
        )
        
        # Serialize to JSON (what frontend receives)
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        
        # Verify datetime is ISO format string
        assert isinstance(parsed["timestamp"], str)
        assert "T" in parsed["timestamp"]  # ISO format
        
        # Verify it can be parsed back
        from datetime import datetime as dt
        dt.fromisoformat(parsed["timestamp"].replace("Z", "+00:00"))
    
    def test_tool_execution_flow(self):
        """Test tool execution type flow."""
        # Tool started (backend to frontend)
        tool_started = ToolStarted(
            tool_name="log_analyzer",
            tool_args={"level": "error", "limit": 100},
            run_id="run123"
        )
        
        started_json = tool_started.model_dump()
        assert started_json["tool_name"] == "log_analyzer"
        assert started_json["tool_args"]["level"] == "error"
        
        # Tool completed (backend to frontend)
        tool_completed = ToolCompleted(
            tool_name="log_analyzer",
            tool_output={"logs": ["error1", "error2"], "count": 2},
            run_id="run123",
            status=ToolStatus.SUCCESS
        )
        
        completed_json = tool_completed.model_dump()
        assert completed_json["status"] == "success"
        assert completed_json["tool_output"]["count"] == 2
    
    def test_error_handling(self):
        """Test error message handling."""
        # Missing required field
        with pytest.raises(ValidationError) as exc_info:
            StartAgentPayload(user_id="user123")  # Missing 'query'
        
        assert "query" in str(exc_info.value).lower()
        
        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            UserMessagePayload(
                content=123,  # Should be string
                thread_id="thread456"
            )
        
        # Invalid enum value
        with pytest.raises(ValueError):
            WebSocketMessageType("invalid_type")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])