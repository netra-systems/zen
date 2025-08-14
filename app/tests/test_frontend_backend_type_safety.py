"""Frontend to Backend Type Safety Tests.

Validates that data structures used in frontend match backend expectations
and ensures type consistency across the full stack.
"""

import json
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import ValidationError, BaseModel

# Import backend schemas
from app.schemas.websocket_unified import (
    WebSocketMessageType,
    StartAgentPayload,
    UserMessagePayload,
    CreateThreadPayload,
    SwitchThreadPayload,
    DeleteThreadPayload,
    RenameThreadPayload,
    StopAgentPayload,
    AgentUpdate,
    AgentLog,
    ToolCall,
    ToolResult,
    StreamChunk,
    StreamComplete,
    WebSocketMessage,
    BaseWebSocketPayload,
    ThreadCreated,
    ThreadDeleted,
    ThreadRenamed,
    ThreadList
)
from app.schemas.Request import RequestModel, StartAgentPayload as StartAgentPayloadPydantic
from app.schemas.Message import Message, MessageType
from app.schemas.Agent import AgentStarted, AgentCompleted, AgentErrorMessage
from app.schemas.Tool import ToolStarted, ToolCompleted, ToolStatus


class FrontendDataMocks:
    """Mock data representing typical frontend payloads."""
    
    @staticmethod
    def start_agent_payload() -> Dict[str, Any]:
        """Frontend StartAgent payload structure."""
        return {
            "type": "start_agent",
            "payload": {
                "query": "Analyze system performance",
                "user_id": "user123",
                "thread_id": "thread456",
                "context": {
                    "session_id": "session789",
                    "metadata": {"source": "chat_ui"}
                }
            }
        }
    
    @staticmethod
    def user_message_payload() -> Dict[str, Any]:
        """Frontend UserMessage payload structure."""
        return {
            "type": "user_message",
            "payload": {
                "content": "What are the optimization opportunities?",
                "thread_id": "thread456",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "client_id": "web_client_1"
                }
            }
        }
    
    @staticmethod
    def tool_call_payload() -> Dict[str, Any]:
        """Frontend tool call structure."""
        return {
            "tool_name": "log_fetcher",
            "tool_args": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
                "filters": {"level": "error"}
            },
            "run_id": "run123"
        }
    
    @staticmethod
    def thread_operations() -> List[Dict[str, Any]]:
        """Frontend thread operation payloads."""
        return [
            {
                "type": "create_thread",
                "payload": {
                    "title": "New Analysis Thread",
                    "metadata": {"tags": ["performance", "optimization"]}
                }
            },
            {
                "type": "rename_thread",
                "payload": {
                    "thread_id": "thread456",
                    "new_title": "Performance Analysis Q1 2025"
                }
            },
            {
                "type": "delete_thread",
                "payload": {
                    "thread_id": "thread456"
                }
            },
            {
                "type": "switch_thread",
                "payload": {
                    "thread_id": "thread789"
                }
            }
        ]
    
    @staticmethod
    def websocket_messages() -> List[Dict[str, Any]]:
        """Various WebSocket message formats from frontend."""
        return [
            {
                "type": "ping",
                "payload": {}
            },
            {
                "type": "list_threads",
                "payload": {}
            },
            {
                "type": "stop_agent",
                "payload": {
                    "run_id": "run123"
                }
            }
        ]


class TestFrontendToBackendTypeSafety:
    """Test type safety between frontend and backend."""
    
    def test_start_agent_type_validation(self):
        """Test StartAgent payload type consistency."""
        frontend_data = FrontendDataMocks.start_agent_payload()
        
        # Validate against backend schema
        try:
            payload = StartAgentPayload(**frontend_data["payload"])
            assert payload.query == "Analyze system performance"
            assert payload.user_id == "user123"
            assert payload.thread_id == "thread456"
        except ValidationError as e:
            pytest.fail(f"Frontend StartAgent data doesn't match backend schema: {e}")
    
    def test_user_message_type_validation(self):
        """Test UserMessage payload type consistency."""
        frontend_data = FrontendDataMocks.user_message_payload()
        
        try:
            payload = UserMessagePayload(**frontend_data["payload"])
            assert payload.content == "What are the optimization opportunities?"
            assert payload.thread_id == "thread456"
        except ValidationError as e:
            pytest.fail(f"Frontend UserMessage data doesn't match backend schema: {e}")
    
    def test_websocket_message_envelope(self):
        """Test WebSocket message envelope structure."""
        frontend_data = FrontendDataMocks.start_agent_payload()
        
        try:
            # Validate message type enum
            msg_type = WebSocketMessageType(frontend_data["type"])
            assert msg_type == WebSocketMessageType.START_AGENT
            
            # Validate full message structure
            message = WebSocketMessage(
                type=msg_type,
                payload=frontend_data["payload"]
            )
            assert message.type == WebSocketMessageType.START_AGENT
        except (ValueError, ValidationError) as e:
            pytest.fail(f"WebSocket message structure mismatch: {e}")
    
    def test_thread_operations_type_safety(self):
        """Test thread operation payloads."""
        thread_ops = FrontendDataMocks.thread_operations()
        
        for op in thread_ops:
            msg_type = WebSocketMessageType(op["type"])
            
            if msg_type == WebSocketMessageType.CREATE_THREAD:
                try:
                    payload = CreateThreadPayload(**op["payload"])
                    assert payload.title == "New Analysis Thread"
                except ValidationError as e:
                    pytest.fail(f"CreateThread validation failed: {e}")
            
            elif msg_type == WebSocketMessageType.RENAME_THREAD:
                try:
                    payload = RenameThreadPayload(**op["payload"])
                    assert payload.new_title == "Performance Analysis Q1 2025"
                except ValidationError as e:
                    pytest.fail(f"RenameThread validation failed: {e}")
            
            elif msg_type == WebSocketMessageType.DELETE_THREAD:
                try:
                    payload = DeleteThreadPayload(**op["payload"])
                    assert payload.thread_id == "thread456"
                except ValidationError as e:
                    pytest.fail(f"DeleteThread validation failed: {e}")
            
            elif msg_type == WebSocketMessageType.SWITCH_THREAD:
                try:
                    payload = SwitchThreadPayload(**op["payload"])
                    assert payload.thread_id == "thread789"
                except ValidationError as e:
                    pytest.fail(f"SwitchThread validation failed: {e}")
    
    def test_tool_status_enum_consistency(self):
        """Test tool status enum values match between frontend and backend."""
        frontend_statuses = ["success", "error", "partial_success", "in_progress", "complete"]
        
        for status in frontend_statuses:
            try:
                tool_status = ToolStatus(status)
                assert tool_status.value == status
            except ValueError:
                pytest.fail(f"Tool status '{status}' not recognized by backend enum")
    
    def test_message_type_enum_consistency(self):
        """Test message type enum values."""
        frontend_types = ["user", "agent", "system", "error", "tool"]
        
        for msg_type in frontend_types:
            try:
                message_type = MessageType(msg_type)
                assert message_type.value == msg_type
            except ValueError:
                pytest.fail(f"Message type '{msg_type}' not recognized by backend enum")
    
    def test_agent_lifecycle_payloads(self):
        """Test agent lifecycle message payloads."""
        # Test AgentStarted (using actual schema)
        started_data = {
            "run_id": "run123"
        }
        try:
            started = AgentStarted(**started_data)
            assert started.run_id == "run123"
        except ValidationError as e:
            pytest.fail(f"AgentStarted payload validation failed: {e}")
        
        # Test AgentCompleted
        completed_data = {
            "run_id": "run123",
            "result": {"analysis": "complete", "findings": 5}
        }
        try:
            completed = AgentCompleted(**completed_data)
            assert completed.run_id == "run123"
            assert completed.result["findings"] == 5
        except ValidationError as e:
            pytest.fail(f"AgentCompleted payload validation failed: {e}")
        
        # Test AgentUpdate
        update_data = {
            "content": "Processing data...",
            "run_id": "run123",
            "metadata": {"step": "analysis"}
        }
        try:
            update = AgentUpdate(**update_data)
            assert update.content == "Processing data..."
        except ValidationError as e:
            pytest.fail(f"AgentUpdate payload validation failed: {e}")
    
    def test_stream_chunk_payload(self):
        """Test streaming chunk payload structure."""
        chunk_data = {
            "content": "Processing data...",
            "index": 0,
            "finished": False,
            "metadata": {
                "tokens": 15,
                "model": "gpt-4"
            }
        }
        
        try:
            chunk = StreamChunk(**chunk_data)
            assert chunk.content == "Processing data..."
            assert chunk.index == 0
            assert chunk.finished is False
        except ValidationError as e:
            pytest.fail(f"StreamChunk payload validation failed: {e}")
    
    def test_error_payload_structure(self):
        """Test error payload structure."""
        error_data = {
            "run_id": "run123",
            "message": "WebSocket connection failed"
        }
        
        try:
            error = AgentErrorMessage(**error_data)
            assert error.message == "WebSocket connection failed"
            assert error.run_id == "run123"
        except ValidationError as e:
            pytest.fail(f"Error payload validation failed: {e}")
    
    def test_optional_fields_handling(self):
        """Test handling of optional fields in payloads."""
        # Minimal payload
        minimal = {
            "query": "Test query",
            "user_id": "user123"
        }
        
        try:
            payload = StartAgentPayload(**minimal)
            assert payload.thread_id is None  # Optional field
            assert payload.context is None  # Optional field
        except ValidationError as e:
            pytest.fail(f"Optional fields not handled correctly: {e}")
        
        # Full payload
        full = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": "thread456",
            "context": {"key": "value"}
        }
        
        try:
            payload = StartAgentPayload(**full)
            assert payload.thread_id == "thread456"
            assert payload.context == {"key": "value"}
        except ValidationError as e:
            pytest.fail(f"Full payload validation failed: {e}")
    
    def test_nested_object_validation(self):
        """Test validation of nested objects."""
        request_data = {
            "id": "req123",
            "user_id": "user123",
            "query": "Analyze workload",
            "workloads": [
                {
                    "run_id": "run123",
                    "query": "sub-query",
                    "data_source": {
                        "source_table": "logs",
                        "filters": {"level": "error"}
                    },
                    "time_range": {
                        "start_time": "2025-01-01T00:00:00Z",
                        "end_time": "2025-01-02T00:00:00Z"
                    }
                }
            ]
        }
        
        try:
            request = RequestModel(**request_data)
            assert request.user_id == "user123"
            assert len(request.workloads) == 1
            assert request.workloads[0].data_source.source_table == "logs"
        except ValidationError as e:
            pytest.fail(f"Nested object validation failed: {e}")


class TestBackendToFrontendTypeSafety:
    """Test type safety for backend to frontend communication."""
    
    def test_agent_started_response(self):
        """Test AgentStarted response structure."""
        backend_response = AgentStarted(run_id="run123")
        
        # Serialize to JSON (what frontend receives)
        json_data = backend_response.model_dump()
        
        # Validate structure matches frontend expectations
        assert "run_id" in json_data
        assert isinstance(json_data["run_id"], str)
    
    def test_agent_completed_response(self):
        """Test AgentCompleted response structure."""
        backend_response = AgentCompleted(
            run_id="run123",
            result={"analysis": "complete", "recommendations": ["opt1", "opt2"]}
        )
        
        json_data = backend_response.model_dump()
        
        assert "run_id" in json_data
        assert "result" in json_data
        assert isinstance(json_data["result"]["recommendations"], list)
    
    def test_tool_started_response(self):
        """Test ToolStarted response structure."""
        backend_response = ToolStarted(
            tool_name="log_fetcher",
            tool_args={"start_time": "2025-01-01T00:00:00Z"},
            run_id="run123"
        )
        
        json_data = backend_response.model_dump()
        
        assert json_data["tool_name"] == "log_fetcher"
        assert "tool_args" in json_data
        assert json_data["run_id"] == "run123"
    
    def test_tool_completed_response(self):
        """Test ToolCompleted response structure."""
        backend_response = ToolCompleted(
            tool_name="log_fetcher",
            tool_output={"logs": ["log1", "log2"], "count": 2},
            run_id="run123",
            status=ToolStatus.SUCCESS
        )
        
        json_data = backend_response.model_dump()
        
        assert json_data["status"] == "success"
        assert json_data["tool_output"]["count"] == 2
    
    def test_error_message_response(self):
        """Test error message response structure."""
        backend_response = AgentErrorMessage(
            run_id="run123",
            message="Processing failed due to timeout"
        )
        
        json_data = backend_response.model_dump()
        
        assert json_data["run_id"] == "run123"
        assert json_data["message"] == "Processing failed due to timeout"
    
    def test_websocket_message_serialization(self):
        """Test WebSocket message serialization."""
        message = WebSocketMessage(
            type=WebSocketMessageType.AGENT_STARTED,
            payload={"run_id": "run123"}
        )
        
        # Serialize to JSON string (what goes over WebSocket)
        json_str = message.model_dump_json()
        
        # Parse back to verify structure
        parsed = json.loads(json_str)
        assert parsed["type"] == "agent_started"
        assert parsed["payload"]["run_id"] == "run123"
    
    def test_streaming_response_chunks(self):
        """Test streaming response chunk structure."""
        chunks = [
            StreamChunk(content="Processing", index=0, finished=False),
            StreamChunk(content=" complete", index=1, finished=True)
        ]
        
        for i, chunk in enumerate(chunks):
            json_data = chunk.model_dump()
            assert json_data["index"] == i
            assert json_data["finished"] == (i == 1)


class TestTypeConsistencyValidation:
    """Validate type consistency across the stack."""
    
    def test_datetime_serialization(self):
        """Test datetime serialization consistency."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        # Create a message with datetime
        message = Message(
            id="msg123",
            type=MessageType.USER,
            content="Test message",
            timestamp=now,
            metadata={}
        )
        
        # Serialize and deserialize
        json_data = message.model_dump_json()
        parsed = json.loads(json_data)
        
        # Verify datetime is ISO format string
        assert isinstance(parsed["timestamp"], str)
        assert "T" in parsed["timestamp"]  # ISO format
    
    def test_enum_value_serialization(self):
        """Test enum serialization to string values."""
        status = ToolStatus.SUCCESS
        msg_type = MessageType.AGENT
        
        # Verify enum values serialize to strings
        assert status.value == "success"
        assert msg_type.value == "agent"
        
        # Test in model
        tool = ToolCompleted(
            tool_name="test_tool",
            tool_output={},
            run_id="run123",
            status=status
        )
        
        json_data = tool.model_dump()
        assert json_data["status"] == "success"
    
    def test_null_vs_undefined_handling(self):
        """Test handling of null vs undefined fields."""
        # Test with explicit None
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None
        )
        
        json_data = payload.model_dump()
        assert "thread_id" in json_data
        assert json_data["thread_id"] is None
        
        # Test exclude_none behavior
        json_data_no_none = payload.model_dump(exclude_none=True)
        assert "thread_id" not in json_data_no_none
    
    def test_array_type_consistency(self):
        """Test array type handling."""
        workloads_data = [
            {
                "run_id": f"run{i}",
                "query": f"query{i}",
                "data_source": {
                    "source_table": "logs",
                    "filters": None
                },
                "time_range": {
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-02T00:00:00Z"
                }
            }
            for i in range(3)
        ]
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        json_data = request.model_dump()
        assert isinstance(json_data["workloads"], list)
        assert len(json_data["workloads"]) == 3
    
    def test_deeply_nested_validation(self):
        """Test deeply nested object validation."""
        complex_payload = {
            "type": "start_agent",
            "payload": {
                "query": "Complex analysis",
                "user_id": "user123",
                "context": {
                    "session": {
                        "id": "session123",
                        "metadata": {
                            "client": {
                                "name": "web",
                                "version": "1.0.0"
                            }
                        }
                    }
                }
            }
        }
        
        # Validate type
        msg_type = WebSocketMessageType(complex_payload["type"])
        
        # Validate payload
        payload = StartAgentPayload(**complex_payload["payload"])
        assert payload.context["session"]["metadata"]["client"]["name"] == "web"
    
    def test_union_type_handling(self):
        """Test union type handling in schemas."""
        # Test with different content types for Message
        text_message = Message(
            id="msg1",
            type=MessageType.USER,
            content="Simple text",
            metadata={}
        )
        
        assert isinstance(text_message.content, str)
        
        # Some schemas might support complex content
        complex_content = {
            "text": "Complex message",
            "attachments": ["file1.pdf"]
        }
        
        complex_message = Message(
            id="msg2",
            type=MessageType.AGENT,
            content=complex_content,
            metadata={}
        )
        
        assert isinstance(complex_message.content, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])