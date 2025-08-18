"""WebSocket Server-to-Client Message Type Safety Tests.

Tests for server-to-client WebSocket message type consistency.
"""

import pytest
from pydantic import ValidationError

from app.schemas.registry import (
    WebSocketMessageType,
    ServerToClientMessage,
    AgentCompletedPayload
)
from app.schemas.websocket_payloads import (
    AgentStartedPayload,
    AgentErrorPayload,
    ToolStartedPayload,
    ToolCompletedPayload,
    ToolCallPayload,
    ToolResultPayload,
    SubAgentStartedPayload,
    SubAgentCompletedPayload,
    ThreadCreatedPayload,
    ThreadSwitchedPayload,
    ThreadDeletedPayload,
    ThreadRenamedPayload,
    ThreadListPayload,
    StreamChunkPayload,
    StreamCompletePayload,
    ErrorPayload,
    ConnectionEstablishedPayload
)
from app.core.error_codes import ErrorSeverity
from .test_websocket_type_safety_factory import WebSocketMessageFactory, WebSocketTestDataFactory


class TestServerToClientMessageTypes:
    """Test server-to-client message type safety."""
    
    def test_agent_lifecycle_messages_validation(self):
        """Test agent lifecycle message validation."""
        test_cases = WebSocketTestDataFactory.get_agent_lifecycle_test_cases()
        
        for msg_type_str, payload_class_name, payload_data in test_cases:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            assert msg_type.value == msg_type_str
            
            # Validate payload
            payload_class = self._get_payload_class(payload_class_name)
            payload = payload_class(**message["payload"])
            assert payload.run_id == "run123"
    
    def test_agent_started_message(self):
        """Test AGENT_STARTED message validation."""
        message = WebSocketMessageFactory.create_agent_lifecycle_message(
            "agent_started",
            "run123"
        )
        
        payload = AgentStartedPayload(**message["payload"])
        assert payload.run_id == "run123"
        
        # Test with optional fields
        message_with_extras = WebSocketMessageFactory.create_agent_lifecycle_message(
            "agent_started",
            "run123",
            agent_type="supervisor",
            started_at="2024-01-01T00:00:00Z"
        )
        
        payload = AgentStartedPayload(**message_with_extras["payload"])
        assert payload.run_id == "run123"
    
    def test_agent_completed_message(self):
        """Test AGENT_COMPLETED message validation."""
        message = WebSocketMessageFactory.create_agent_lifecycle_message(
            "agent_completed",
            "run123",
            result={"status": "success", "data": {"analysis": "complete"}}
        )
        
        payload = AgentCompletedPayload(**message["payload"])
        assert payload.run_id == "run123"
        assert payload.result["status"] == "success"
    
    def test_agent_error_message(self):
        """Test AGENT_ERROR message validation."""
        message = WebSocketMessageFactory.create_agent_lifecycle_message(
            "agent_error",
            "run123",
            message="Processing failed",
            code="PROCESSING_ERROR"
        )
        
        payload = AgentErrorPayload(**message["payload"])
        assert payload.run_id == "run123"
        assert payload.message == "Processing failed"
        assert payload.code == "PROCESSING_ERROR"
    
    def test_tool_messages_validation(self):
        """Test tool-related message validation."""
        test_cases = WebSocketTestDataFactory.get_tool_message_test_cases()
        
        for msg_type_str, payload_class_name, payload_data in test_cases:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            payload_class = self._get_payload_class(payload_class_name)
            payload = payload_class(**message["payload"])
            
            # All tool messages should have tool_name
            assert hasattr(payload, 'tool_name')
            assert payload.tool_name in ["log_analyzer", "cost_analyzer"]
    
    def test_tool_started_message(self):
        """Test TOOL_STARTED message validation."""
        message = WebSocketMessageFactory.create_tool_message(
            "tool_started",
            "log_analyzer",
            "run123",
            tool_args={"level": "error", "limit": 100}
        )
        
        payload = ToolStartedPayload(**message["payload"])
        assert payload.tool_name == "log_analyzer"
        assert payload.run_id == "run123"
        assert payload.tool_args["level"] == "error"
    
    def test_tool_completed_message(self):
        """Test TOOL_COMPLETED message validation."""
        message = WebSocketMessageFactory.create_tool_message(
            "tool_completed",
            "cost_analyzer",
            "run123",
            tool_output={"total_cost": 1500.00, "breakdown": {}},
            status="success"
        )
        
        payload = ToolCompletedPayload(**message["payload"])
        assert payload.tool_name == "cost_analyzer"
        assert payload.tool_output["total_cost"] == 1500.00
        assert payload.status == "success"
    
    def test_subagent_messages_validation(self):
        """Test subagent message validation."""
        # Test SUBAGENT_STARTED
        subagent_started = WebSocketMessageFactory.create_server_message(
            "subagent_started",
            {
                "subagent_id": "sub123",
                "subagent_type": "data_analyzer",
                "parent_run_id": "run123"
            }
        )
        
        payload = SubAgentStartedPayload(**subagent_started["payload"])
        assert payload.subagent_id == "sub123"
        assert payload.subagent_type == "data_analyzer"
        assert payload.parent_run_id == "run123"
        
        # Test SUBAGENT_COMPLETED
        subagent_completed = WebSocketMessageFactory.create_server_message(
            "subagent_completed",
            {
                "subagent_id": "sub123",
                "result": {"analysis": "complete", "insights": []},
                "parent_run_id": "run123"
            }
        )
        
        payload = SubAgentCompletedPayload(**subagent_completed["payload"])
        assert payload.subagent_id == "sub123"
        assert payload.result["analysis"] == "complete"
    
    def test_thread_response_messages_validation(self):
        """Test thread response message validation."""
        thread_messages = [
            ("thread_created", ThreadCreatedPayload, {
                "thread_id": "new_thread_123",
                "title": "New Analysis Thread"
            }),
            ("thread_switched", ThreadSwitchedPayload, {
                "thread_id": "thread456",
                "previous_thread_id": "thread123"
            }),
            ("thread_deleted", ThreadDeletedPayload, {
                "thread_id": "thread456"
            }),
            ("thread_renamed", ThreadRenamedPayload, {
                "thread_id": "thread456",
                "new_title": "Renamed Thread"
            }),
            ("thread_list", ThreadListPayload, {
                "threads": [
                    {"id": "t1", "title": "Thread 1", "created_at": "2024-01-01T00:00:00Z"},
                    {"id": "t2", "title": "Thread 2", "created_at": "2024-01-01T01:00:00Z"}
                ]
            }),
        ]
        
        for msg_type_str, payload_class, payload_data in thread_messages:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            payload = payload_class(**message["payload"])
            assert payload is not None
    
    def test_streaming_messages_validation(self):
        """Test streaming message validation."""
        # Test STREAM_CHUNK
        chunk_msg = WebSocketMessageFactory.create_streaming_message(
            "stream_chunk",
            content="Processing data chunk 1",
            index=0,
            finished=False,
            metadata={"tokens": 5, "model": "gpt-4"}
        )
        
        chunk_payload = StreamChunkPayload(**chunk_msg["payload"])
        assert chunk_payload.content == "Processing data chunk 1"
        assert chunk_payload.index == 0
        assert chunk_payload.finished is False
        assert chunk_payload.metadata["tokens"] == 5
        
        # Test STREAM_COMPLETE
        complete_msg = WebSocketMessageFactory.create_streaming_message(
            "stream_complete",
            total_chunks=10,
            total_tokens=150,
            metadata={"model": "gpt-4", "duration_ms": 5000}
        )
        
        complete_payload = StreamCompletePayload(**complete_msg["payload"])
        assert complete_payload.total_chunks == 10
        assert complete_payload.total_tokens == 150
        assert complete_payload.metadata["model"] == "gpt-4"
    
    def test_error_message_validation(self):
        """Test error message validation."""
        error_msg = WebSocketMessageFactory.create_error_message(
            "Authentication failed",
            "AUTH_FAILED",
            "high",
            details={"reason": "Invalid token", "retry_after": 300}
        )
        
        msg_type = WebSocketMessageType(error_msg["type"])
        assert msg_type == WebSocketMessageType.ERROR
        
        payload = ErrorPayload(**error_msg["payload"])
        assert payload.message == "Authentication failed"
        assert payload.code == "AUTH_FAILED"
        assert payload.severity == ErrorSeverity.HIGH
        assert payload.details["reason"] == "Invalid token"
    
    def test_connection_established_message(self):
        """Test connection established message validation."""
        conn_msg = WebSocketMessageFactory.create_connection_message(
            "conn123",
            "session456",
            "1.0.0"
        )
        
        payload = ConnectionEstablishedPayload(**conn_msg["payload"])
        assert payload.connection_id == "conn123"
        assert payload.session_id == "session456"
        assert payload.server_version == "1.0.0"
    
    def test_server_message_serialization(self):
        """Test server message serialization."""
        # Create a server message
        server_msg = ServerToClientMessage(
            type=WebSocketMessageType.AGENT_STARTED,
            payload=AgentStartedPayload(run_id="run123")
        )
        
        # Serialize to JSON
        json_data = server_msg.model_dump_json()
        
        # Deserialize from JSON
        import json
        parsed_data = json.loads(json_data)
        
        # Verify serialized data
        assert parsed_data["type"] == "agent_started"
        assert parsed_data["payload"]["run_id"] == "run123"
    
    def test_error_severity_validation(self):
        """Test error severity validation."""
        # Valid severities
        valid_severities = ["low", "medium", "high", "critical"]
        
        for severity in valid_severities:
            error_msg = WebSocketMessageFactory.create_error_message(
                "Test error",
                "TEST_ERROR",
                severity
            )
            
            payload = ErrorPayload(**error_msg["payload"])
            assert payload.severity.value == severity
        
        # Invalid severity should raise validation error
        with pytest.raises(ValidationError):
            ErrorPayload(
                message="Error",
                code="ERROR",
                severity="invalid_severity"
            )
    
    def _get_payload_class(self, class_name: str):
        """Get payload class by name."""
        class_map = {
            "AgentStartedPayload": AgentStartedPayload,
            "AgentCompletedPayload": AgentCompletedPayload,
            "AgentErrorPayload": AgentErrorPayload,
            "ToolStartedPayload": ToolStartedPayload,
            "ToolCompletedPayload": ToolCompletedPayload,
            "ToolCallPayload": ToolCallPayload,
            "ToolResultPayload": ToolResultPayload,
            "SubAgentStartedPayload": SubAgentStartedPayload,
            "SubAgentCompletedPayload": SubAgentCompletedPayload,
            "ThreadCreatedPayload": ThreadCreatedPayload,
            "ThreadSwitchedPayload": ThreadSwitchedPayload,
            "ThreadDeletedPayload": ThreadDeletedPayload,
            "ThreadRenamedPayload": ThreadRenamedPayload,
            "ThreadListPayload": ThreadListPayload,
            "StreamChunkPayload": StreamChunkPayload,
            "StreamCompletePayload": StreamCompletePayload,
            "ErrorPayload": ErrorPayload,
            "ConnectionEstablishedPayload": ConnectionEstablishedPayload,
        }
        
        return class_map[class_name]


class TestServerMessageBatchValidation:
    """Test batch validation of server messages."""
    
    def test_batch_server_message_validation(self):
        """Test validation of multiple server messages."""
        test_cases = WebSocketTestDataFactory.get_server_message_test_cases()
        
        for test_case in test_cases:
            message = WebSocketMessageFactory.create_server_message(
                test_case["type"],
                test_case["payload"]
            )
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            assert isinstance(msg_type, WebSocketMessageType)
            
            # Validate that payload is properly structured
            assert "payload" in message
            assert isinstance(message["payload"], dict)
    
    def test_server_message_timestamp_validation(self):
        """Test server message timestamp validation."""
        # All server messages should have timestamps
        message = WebSocketMessageFactory.create_server_message(
            "agent_started",
            {"run_id": "run123"}
        )
        
        assert "timestamp" in message
        assert "message_id" in message
        assert message["message_id"].startswith("srv_")
    
    def test_message_id_uniqueness(self):
        """Test that message IDs are unique."""
        message_ids = set()
        
        # Generate multiple messages
        for i in range(100):
            message = WebSocketMessageFactory.create_server_message(
                "agent_started",
                {"run_id": f"run{i}"}
            )
            message_id = message["message_id"]
            
            # Ensure no duplicate message IDs
            assert message_id not in message_ids
            message_ids.add(message_id)
