"""Frontend to Backend Type Safety Tests.

Validates that frontend payloads match backend schema expectations
ensuring type consistency in the request flow.
"""

import pytest
from typing import Dict, Any
from pydantic import ValidationError

# Import backend schemas
from app.schemas.registry import (
    WebSocketMessageType,
    StartAgentPayload,
    UserMessagePayload,
    CreateThreadPayload,
    DeleteThreadPayload,
    SwitchThreadPayload,
    StopAgentPayload,
    WebSocketMessage
)
from app.schemas.Request import RequestModel
from app.schemas.Tool import ToolStatus
from app.schemas.registry import MessageType

# Import test data
from app.tests.frontend_data_mocks import FrontendDataMocks, EnumValueMocks


class TestFrontendPayloadValidation:
    """Test frontend payloads against backend schemas."""
    
    def test_start_agent_payload_validation(self) -> None:
        """Test StartAgent payload type consistency."""
        frontend_data = FrontendDataMocks.start_agent_payload()
        payload_data = frontend_data["payload"]
        
        payload = StartAgentPayload(**payload_data)
        assert payload.query == "Analyze system performance"
        assert payload.user_id == "user123"
        assert payload.thread_id == "thread456"
    
    def test_start_agent_validation_failure(self) -> None:
        """Test StartAgent validation with invalid data."""
        invalid_data = {"user_id": "user123"}  # Missing required query
        
        with pytest.raises(ValidationError):
            StartAgentPayload(**invalid_data)
    
    def test_user_message_payload_validation(self) -> None:
        """Test UserMessage payload type consistency."""
        frontend_data = FrontendDataMocks.user_message_payload()
        payload_data = frontend_data["payload"]
        
        payload = UserMessagePayload(**payload_data)
        assert payload.content == "What are the optimization opportunities?"
        assert payload.thread_id == "thread456"
    
    def test_user_message_validation_failure(self) -> None:
        """Test UserMessage validation with missing fields."""
        invalid_data = {"thread_id": "thread456"}  # Missing content
        
        with pytest.raises(ValidationError):
            UserMessagePayload(**invalid_data)


class TestWebSocketMessageValidation:
    """Test WebSocket message envelope validation."""
    
    def test_websocket_message_envelope_structure(self) -> None:
        """Test WebSocket message envelope structure."""
        frontend_data = FrontendDataMocks.start_agent_payload()
        
        msg_type = WebSocketMessageType(frontend_data["type"])
        assert msg_type == WebSocketMessageType.START_AGENT
        
        message = WebSocketMessage(
            type=msg_type,
            payload=frontend_data["payload"]
        )
        assert message.type == WebSocketMessageType.START_AGENT
    
    def test_invalid_message_type(self) -> None:
        """Test invalid WebSocket message type."""
        with pytest.raises(ValueError):
            WebSocketMessageType("invalid_type")
    
    def test_ping_message_validation(self) -> None:
        """Test ping message validation."""
        ping_data = FrontendDataMocks.ping_message()
        
        msg_type = WebSocketMessageType(ping_data["type"])
        message = WebSocketMessage(type=msg_type, payload=ping_data["payload"])
        assert message.type == WebSocketMessageType.PING
    
    def test_stop_agent_message_validation(self) -> None:
        """Test stop agent message validation."""
        stop_data = FrontendDataMocks.stop_agent_message()
        
        msg_type = WebSocketMessageType(stop_data["type"])
        payload = StopAgentPayload(**stop_data["payload"])
        assert payload.run_id == "run123"


class TestThreadOperationValidation:
    """Test thread operation payload validation."""
    
    def test_create_thread_validation(self) -> None:
        """Test CreateThread payload validation."""
        op_data = FrontendDataMocks.create_thread_operation()
        
        msg_type = WebSocketMessageType(op_data["type"])
        payload = CreateThreadPayload(**op_data["payload"])
        assert payload.title == "New Analysis Thread"
        assert msg_type == WebSocketMessageType.CREATE_THREAD
    
    def test_delete_thread_validation(self) -> None:
        """Test DeleteThread payload validation."""
        op_data = FrontendDataMocks.delete_thread_operation()
        
        msg_type = WebSocketMessageType(op_data["type"])
        payload = DeleteThreadPayload(**op_data["payload"])
        assert payload.thread_id == "thread456"
        assert msg_type == WebSocketMessageType.DELETE_THREAD
    
    def test_switch_thread_validation(self) -> None:
        """Test SwitchThread payload validation."""
        op_data = FrontendDataMocks.switch_thread_operation()
        
        msg_type = WebSocketMessageType(op_data["type"])
        payload = SwitchThreadPayload(**op_data["payload"])
        assert payload.thread_id == "thread789"
        assert msg_type == WebSocketMessageType.SWITCH_THREAD
    
    def test_all_thread_operations(self) -> None:
        """Test all thread operations in sequence."""
        operations = FrontendDataMocks.thread_operations()
        
        for op in operations:
            msg_type = WebSocketMessageType(op["type"])
            assert msg_type is not None


class TestEnumConsistencyValidation:
    """Test enum value consistency between frontend and backend."""
    
    def test_tool_status_enum_consistency(self) -> None:
        """Test tool status enum values match frontend expectations."""
        frontend_statuses = EnumValueMocks.tool_statuses()
        
        for status in frontend_statuses:
            tool_status = ToolStatus(status)
            assert tool_status.value == status
    
    def test_invalid_tool_status(self) -> None:
        """Test invalid tool status handling."""
        with pytest.raises(ValueError):
            ToolStatus("invalid_status")
    
    def test_message_type_enum_consistency(self) -> None:
        """Test message type enum values consistency."""
        frontend_types = EnumValueMocks.message_types()
        
        for msg_type in frontend_types:
            message_type = MessageType(msg_type)
            assert message_type.value == msg_type
    
    def test_invalid_message_type(self) -> None:
        """Test invalid message type handling."""
        with pytest.raises(ValueError):
            MessageType("invalid_type")


class TestOptionalFieldHandling:
    """Test handling of optional fields in payloads."""
    
    def test_minimal_start_agent_payload(self) -> None:
        """Test minimal StartAgent payload with optional fields."""
        minimal_data = FrontendDataMocks.minimal_start_agent_payload()
        
        payload = StartAgentPayload(**minimal_data)
        assert payload.thread_id is None
        assert payload.context is None
        assert payload.query == "Test query"
        assert payload.user_id == "user123"
    
    def test_full_start_agent_payload(self) -> None:
        """Test full StartAgent payload with all fields."""
        full_data = FrontendDataMocks.full_start_agent_payload()
        
        payload = StartAgentPayload(**full_data)
        assert payload.thread_id == "thread456"
        assert payload.context == {"key": "value"}
        assert payload.query == "Test query"
        assert payload.user_id == "user123"
    
    def test_partial_payload_validation(self) -> None:
        """Test partial payload with some optional fields."""
        partial_data = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": "thread456"
            # context is omitted
        }
        
        payload = StartAgentPayload(**partial_data)
        assert payload.context is None
        assert payload.thread_id == "thread456"


class TestNestedObjectValidation:
    """Test validation of nested object structures."""
    
    def test_nested_request_validation(self) -> None:
        """Test validation of nested request objects."""
        request_data = FrontendDataMocks.nested_request_data()
        
        request = RequestModel(**request_data)
        assert request.user_id == "user123"
        assert len(request.workloads) == 1
        assert request.workloads[0].data_source.source_table == "logs"
    
    def test_nested_validation_failure(self) -> None:
        """Test nested validation with invalid structure."""
        invalid_data = {
            "user_id": "user123",
            "query": "Test",
            "workloads": [
                {
                    "run_id": "run123",
                    # Missing required query field
                    "data_source": {"source_table": "logs"}
                }
            ]
        }
        
        with pytest.raises(ValidationError):
            RequestModel(**invalid_data)
    
    def test_deeply_nested_validation(self) -> None:
        """Test deeply nested object validation."""
        complex_data = FrontendDataMocks.complex_websocket_payload()
        
        msg_type = WebSocketMessageType(complex_data["type"])
        payload = StartAgentPayload(**complex_data["payload"])
        
        client_name = payload.context["session"]["metadata"]["client"]["name"]
        assert client_name == "web"
    
    def test_array_workload_validation(self) -> None:
        """Test array of workloads validation."""
        workloads_data = FrontendDataMocks.workloads_array_data()
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        assert len(request.workloads) == 3
        assert all(w.data_source.source_table == "logs" for w in request.workloads)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])