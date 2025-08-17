"""WebSocket Client-to-Server Message Type Safety Tests.

Tests for client-to-server WebSocket message type consistency.
"""

import pytest
from pydantic import ValidationError

from app.schemas.registry import (
    WebSocketMessageType,
    StartAgentPayload,
    UserMessagePayload,
    CreateThreadPayload,
    SwitchThreadPayload,
    DeleteThreadPayload,
    StopAgentPayload,
    ClientToServerMessage
)
from app.schemas.websocket_payloads import (
    RenameThreadPayload,
    ListThreadsPayload,
    ThreadHistoryPayload
)
from .test_websocket_type_safety_factory import WebSocketMessageFactory, WebSocketTestDataFactory


class TestClientToServerMessageTypes:
    """Test client-to-server message type safety."""
    
    def test_start_agent_message_validation(self):
        """Test START_AGENT message type validation."""
        message = WebSocketMessageFactory.create_client_message(
            "start_agent",
            {
                "query": "Analyze performance metrics",
                "user_id": "user123",
                "thread_id": "thread456",
                "context": {"session": "abc123"}
            }
        )
        
        # Validate message type
        msg_type = WebSocketMessageType(message["type"])
        assert msg_type == WebSocketMessageType.START_AGENT
        
        # Validate payload
        payload = StartAgentPayload(**message["payload"])
        assert payload.query == "Analyze performance metrics"
        assert payload.user_id == "user123"
        
        # Validate full message
        full_msg = ClientToServerMessage(
            type=msg_type,
            payload=payload
        )
        assert full_msg.type == WebSocketMessageType.START_AGENT
    
    def test_user_message_validation(self):
        """Test USER_MESSAGE message type validation."""
        message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": "What are the key insights?",
                "thread_id": "thread456",
                "metadata": {"source": "chat_input"}
            }
        )
        
        msg_type = WebSocketMessageType(message["type"])
        assert msg_type == WebSocketMessageType.USER_MESSAGE
        
        payload = UserMessagePayload(**message["payload"])
        assert payload.content == "What are the key insights?"
        assert payload.thread_id == "thread456"
    
    def test_thread_operations_validation(self):
        """Test thread operation message validation."""
        test_cases = WebSocketTestDataFactory.get_thread_operation_test_cases()
        
        for op_type, payload_class_name, payload_data in test_cases:
            message = WebSocketMessageFactory.create_client_message(op_type, payload_data)
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            assert msg_type.value == op_type
            
            # Validate payload using dynamic import
            payload_class = self._get_payload_class(payload_class_name)
            payload = payload_class(**message["payload"])
            assert payload is not None
    
    def test_control_messages_validation(self):
        """Test control message validation (ping, stop_agent)."""
        # Test PING
        ping_msg = WebSocketMessageFactory.create_control_message("ping")
        msg_type = WebSocketMessageType(ping_msg["type"])
        assert msg_type == WebSocketMessageType.PING
        
        # Test STOP_AGENT
        stop_msg = WebSocketMessageFactory.create_control_message(
            "stop_agent",
            run_id="run123"
        )
        msg_type = WebSocketMessageType(stop_msg["type"])
        payload = StopAgentPayload(**stop_msg["payload"])
        assert payload.run_id == "run123"
    
    def test_get_thread_history_validation(self):
        """Test GET_THREAD_HISTORY message validation."""
        message = WebSocketMessageFactory.create_client_message(
            "get_thread_history",
            {
                "thread_id": "thread456",
                "limit": 50,
                "offset": 0
            }
        )
        
        msg_type = WebSocketMessageType(message["type"])
        assert msg_type == WebSocketMessageType.GET_THREAD_HISTORY
        
        payload = ThreadHistoryPayload(**message["payload"])
        assert payload.thread_id == "thread456"
        assert payload.limit == 50
        assert payload.offset == 0
    
    def test_required_fields_validation(self):
        """Test validation of required fields."""
        # Missing required field 'query' in START_AGENT
        with pytest.raises(ValidationError):
            StartAgentPayload(user_id="user123")
        
        # Missing required field 'content' in USER_MESSAGE
        with pytest.raises(ValidationError):
            UserMessagePayload(thread_id="thread123")
        
        # Missing required field 'run_id' in STOP_AGENT
        with pytest.raises(ValidationError):
            StopAgentPayload()
    
    def test_optional_fields_validation(self):
        """Test validation of optional fields."""
        # START_AGENT with minimal required fields
        payload = StartAgentPayload(
            query="Test query",
            user_id="user123"
        )
        assert payload.query == "Test query"
        assert payload.thread_id is None  # Optional field
        
        # USER_MESSAGE with optional metadata
        payload = UserMessagePayload(
            content="Test message",
            thread_id="thread123",
            metadata={"source": "test"}
        )
        assert payload.metadata == {"source": "test"}
    
    def test_field_type_validation(self):
        """Test validation of field types."""
        # Invalid type for 'limit' in ThreadHistoryPayload
        with pytest.raises(ValidationError):
            ThreadHistoryPayload(
                thread_id="thread123",
                limit="not_an_int",  # Should be int
                offset=0
            )
        
        # Invalid type for 'offset' in ThreadHistoryPayload
        with pytest.raises(ValidationError):
            ThreadHistoryPayload(
                thread_id="thread123",
                limit=50,
                offset="not_an_int"  # Should be int
            )
    
    def test_extra_fields_validation(self):
        """Test handling of extra fields (should be forbidden)."""
        with pytest.raises(ValidationError):
            StartAgentPayload(
                query="Test",
                user_id="user123",
                extra_field="should_fail"  # Extra field should be rejected
            )
        
        with pytest.raises(ValidationError):
            UserMessagePayload(
                content="Test message",
                thread_id="thread123",
                unexpected_field="should_fail"  # Extra field should be rejected
            )
    
    def test_message_serialization_deserialization(self):
        """Test message serialization and deserialization."""
        # Create a START_AGENT message
        original_message = ClientToServerMessage(
            type=WebSocketMessageType.START_AGENT,
            payload=StartAgentPayload(
                query="Test query",
                user_id="user123",
                thread_id="thread456"
            )
        )
        
        # Serialize to JSON
        json_data = original_message.model_dump_json()
        
        # Deserialize from JSON
        import json
        parsed_data = json.loads(json_data)
        
        # Verify serialized data
        assert parsed_data["type"] == "start_agent"
        assert parsed_data["payload"]["query"] == "Test query"
        assert parsed_data["payload"]["user_id"] == "user123"
    
    def test_thread_operation_edge_cases(self):
        """Test edge cases in thread operations."""
        # CREATE_THREAD with empty title
        payload = CreateThreadPayload(title="")
        assert payload.title == ""
        
        # SWITCH_THREAD with very long thread_id
        long_thread_id = "thread_" + "x" * 1000
        payload = SwitchThreadPayload(thread_id=long_thread_id)
        assert payload.thread_id == long_thread_id
        
        # DELETE_THREAD with special characters in thread_id
        special_thread_id = "thread-123_test@domain.com"
        payload = DeleteThreadPayload(thread_id=special_thread_id)
        assert payload.thread_id == special_thread_id
    
    def _get_payload_class(self, class_name: str):
        """Get payload class by name."""
        from app.schemas.registry import (
            CreateThreadPayload,
            SwitchThreadPayload,
            DeleteThreadPayload,
        )
        from app.schemas.websocket_payloads import (
            RenameThreadPayload,
            ListThreadsPayload,
        )
        
        class_map = {
            "CreateThreadPayload": CreateThreadPayload,
            "SwitchThreadPayload": SwitchThreadPayload,
            "DeleteThreadPayload": DeleteThreadPayload,
            "RenameThreadPayload": RenameThreadPayload,
            "ListThreadsPayload": ListThreadsPayload,
        }
        
        return class_map[class_name]


class TestClientMessageBatchValidation:
    """Test batch validation of client messages."""
    
    def test_batch_client_message_validation(self):
        """Test validation of multiple client messages."""
        test_cases = WebSocketTestDataFactory.get_client_message_test_cases()
        
        for test_case in test_cases:
            message = WebSocketMessageFactory.create_client_message(
                test_case["type"],
                test_case["payload"]
            )
            
            # Validate message type
            msg_type = WebSocketMessageType(message["type"])
            assert isinstance(msg_type, WebSocketMessageType)
            
            # Validate that payload is properly structured
            assert "payload" in message
            assert isinstance(message["payload"], dict)
    
    def test_invalid_message_types(self):
        """Test handling of invalid message types."""
        invalid_types = [
            "invalid_type",
            "INVALID_TYPE",
            "start_invalid",
            "unknown_message",
            "",
            None
        ]
        
        for invalid_type in invalid_types:
            if invalid_type is None:
                continue
            
            with pytest.raises(ValueError):
                WebSocketMessageType(invalid_type)
    
    def test_message_type_string_conversion(self):
        """Test message type string conversion."""
        # Test all valid client message types
        valid_types = [
            "start_agent",
            "user_message",
            "create_thread",
            "switch_thread",
            "delete_thread",
            "stop_agent",
            "ping",
            "get_thread_history"
        ]
        
        for type_str in valid_types:
            msg_type = WebSocketMessageType(type_str)
            assert msg_type.value == type_str
            assert str(msg_type.value) == type_str
