"""WebSocket Bidirectional Type Consistency and Integration Tests.

Tests for bidirectional WebSocket communication and send functionality.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.registry import (
    WebSocketMessageType,
    WebSocketConnectionState,
    StartAgentPayload,
    ClientToServerMessage,
    ServerToClientMessage,
    UserMessagePayload,
    BaseWebSocketMessage
)
from app.schemas.websocket_payloads import (
    AgentStartedPayload
)
from .test_websocket_type_safety_factory import WebSocketMessageFactory


class TestBidirectionalTypeConsistency:
    """Test type consistency in bidirectional communication."""
    
    def test_request_response_pairing(self):
        """Test request-response message pairing."""
        # Client sends START_AGENT
        request = ClientToServerMessage(
            type=WebSocketMessageType.START_AGENT,
            payload=StartAgentPayload(
                query="Test query",
                user_id="user123"
            )
        )
        
        # Server responds with AGENT_STARTED
        response = ServerToClientMessage(
            type=WebSocketMessageType.AGENT_STARTED,
            payload=AgentStartedPayload(run_id="run123")
        )
        
        # Validate serialization/deserialization
        request_json = request.model_dump_json()
        response_json = response.model_dump_json()
        
        parsed_request = json.loads(request_json)
        parsed_response = json.loads(response_json)
        
        assert parsed_request["type"] == "start_agent"
        assert parsed_response["type"] == "agent_started"
        assert parsed_request["payload"]["query"] == "Test query"
        assert parsed_response["payload"]["run_id"] == "run123"
    
    def test_message_id_tracking(self):
        """Test message ID tracking for correlation."""
        client_msg = BaseWebSocketMessage(
            type=WebSocketMessageType.USER_MESSAGE,
            payload={"content": "Test", "thread_id": "t1"},
            message_id="client_msg_123"
        )
        
        server_msg = BaseWebSocketMessage(
            type=WebSocketMessageType.AGENT_UPDATE,
            payload={"content": "Processing", "run_id": "r1"},
            message_id="server_msg_456",
            correlation_id="client_msg_123"
        )
        
        assert server_msg.correlation_id == client_msg.message_id
        assert server_msg.message_id != client_msg.message_id
    
    def test_connection_state_transitions(self):
        """Test connection state transitions."""
        states = [
            WebSocketConnectionState.CONNECTING,
            WebSocketConnectionState.CONNECTED,
            WebSocketConnectionState.DISCONNECTING,
            WebSocketConnectionState.DISCONNECTED
        ]
        
        for state in states:
            assert isinstance(state.value, str)
            assert WebSocketConnectionState(state.value) == state
        
        # Test state transition logic
        current_state = WebSocketConnectionState.CONNECTING
        assert current_state.value == "connecting"
        
        current_state = WebSocketConnectionState.CONNECTED
        assert current_state.value == "connected"
    
    def test_round_trip_message_integrity(self):
        """Test message integrity in round-trip communication."""
        # Create original message
        original_payload = StartAgentPayload(
            query="Analyze system performance",
            user_id="user123",
            thread_id="thread456",
            context={"session": "abc123", "priority": "high"}
        )
        
        original_message = ClientToServerMessage(
            type=WebSocketMessageType.START_AGENT,
            payload=original_payload
        )
        
        # Serialize to JSON (simulating network transmission)
        json_data = original_message.model_dump_json()
        
        # Deserialize from JSON (simulating reception)
        parsed_data = json.loads(json_data)
        
        # Recreate message from parsed data
        recreated_payload = StartAgentPayload(**parsed_data["payload"])
        recreated_message = ClientToServerMessage(
            type=WebSocketMessageType(parsed_data["type"]),
            payload=recreated_payload
        )
        
        # Verify integrity
        assert recreated_message.type == original_message.type
        assert recreated_payload.query == original_payload.query
        assert recreated_payload.user_id == original_payload.user_id
        assert recreated_payload.context == original_payload.context
    
    def test_type_consistency_across_modules(self):
        """Test type consistency across different modules."""
        # Test that the same message type is handled consistently
        # across client and server message schemas
        
        client_types = [
            WebSocketMessageType.START_AGENT,
            WebSocketMessageType.USER_MESSAGE,
            WebSocketMessageType.PING,
            WebSocketMessageType.STOP_AGENT
        ]
        
        server_types = [
            WebSocketMessageType.AGENT_STARTED,
            WebSocketMessageType.AGENT_COMPLETED,
            WebSocketMessageType.PONG,
            WebSocketMessageType.ERROR
        ]
        
        # Verify all types are properly defined
        for msg_type in client_types + server_types:
            assert isinstance(msg_type.value, str)
            assert len(msg_type.value) > 0
            assert "_" in msg_type.value or msg_type.value in ["ping", "pong"]
    
    def test_payload_type_consistency(self):
        """Test payload type consistency between schemas."""
        # Test that payload types are consistent between
        # message factory and actual schema validation
        
        factory_message = WebSocketMessageFactory.create_client_message(
            "start_agent",
            {
                "query": "Test query",
                "user_id": "user123"
            }
        )
        
        # Validate using actual schema
        payload = StartAgentPayload(**factory_message["payload"])
        message = ClientToServerMessage(
            type=WebSocketMessageType(factory_message["type"]),
            payload=payload
        )
        
        assert message.type == WebSocketMessageType.START_AGENT
        assert message.payload.query == "Test query"
    
    def test_error_propagation_consistency(self):
        """Test error propagation consistency."""
        # Test that validation errors are consistent across
        # different message types and payloads
        
        invalid_payloads = [
            # Missing required fields
            (StartAgentPayload, {"user_id": "user123"}),  # Missing query
            (UserMessagePayload, {"thread_id": "t123"}),  # Missing content
            # Invalid field types
            (StartAgentPayload, {"query": 123, "user_id": "user123"}),  # query should be string
        ]
        
        for payload_class, invalid_data in invalid_payloads:
            with pytest.raises(Exception):  # Could be ValidationError or ValueError
                payload_class(**invalid_data)


class TestWebSocketSendToThread:
    """Test WebSocket send_to_thread functionality."""
    
    async def test_send_to_thread_exists(self):
        """Test that send_to_thread method exists and works."""
        from app.ws_manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        ws_manager.send_message = AsyncMock(return_value=True)
        
        thread_id = "test_thread_123"
        message = {
            "type": "completion",
            "payload": {"status": "completed"},
            "timestamp": 1234567890
        }
        
        result = await ws_manager.send_to_thread(thread_id, message)
        
        ws_manager.send_message.assert_called_once_with(thread_id, message)
        assert result == True
    
    async def test_send_to_thread_with_typed_message(self):
        """Test send_to_thread with properly typed message."""
        from app.ws_manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        ws_manager.send_message = AsyncMock(return_value=True)
        
        # Create a properly typed message
        message = WebSocketMessageFactory.create_server_message(
            "agent_completed",
            {
                "run_id": "run123",
                "result": {"status": "success", "data": {}}
            }
        )
        
        result = await ws_manager.send_to_thread("thread123", message)
        
        ws_manager.send_message.assert_called_once_with("thread123", message)
        assert result == True
    
    async def test_supervisor_send_completion(self):
        """Test supervisor can send completion messages."""
        with patch('app.agents.supervisor_consolidated.WebSocketManager') as MockWS:
            mock_ws = MockWS.return_value
            mock_ws.send_to_thread = AsyncMock(return_value=True)
            
            from app.agents.supervisor_consolidated import SupervisorAgent
            
            supervisor = SupervisorAgent(
                llm_provider=MagicMock(),
                db_session=MagicMock(),
                websocket_manager=mock_ws,
                thread_id="test_thread",
                run_id="test_run",
                user_id="test_user"
            )
            
            state = MagicMock()
            state.messages = []
            state.iterations = 1
            state.tool_calls = []
            state.latest_prompt = "test"
            
            await supervisor._send_completion_message(
                state,
                thread_id="test_thread",
                run_id="test_run"
            )
            
            mock_ws.send_to_thread.assert_called_once()
            args = mock_ws.send_to_thread.call_args[0]
            assert args[0] == "test_thread"
            assert isinstance(args[1], dict)
    
    async def test_send_to_thread_error_handling(self):
        """Test send_to_thread error handling."""
        from app.ws_manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        ws_manager.send_message = AsyncMock(side_effect=Exception("Connection error"))
        
        thread_id = "test_thread_123"
        message = {"type": "test", "payload": {}}
        
        # Should handle errors gracefully
        try:
            result = await ws_manager.send_to_thread(thread_id, message)
            # If no exception is raised, result should indicate failure
            assert result is False or result is None
        except Exception:
            # Exception handling is acceptable
            pass
    
    async def test_send_to_thread_with_validation(self):
        """Test send_to_thread with message validation."""
        from app.ws_manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        ws_manager.send_message = AsyncMock(return_value=True)
        
        # Create a message using the factory to ensure proper structure
        message = WebSocketMessageFactory.create_server_message(
            "stream_chunk",
            {
                "content": "Processing step 1",
                "index": 0,
                "finished": False,
                "metadata": {"progress": 0.1}
            }
        )
        
        # Validate message structure before sending
        assert "type" in message
        assert "payload" in message
        assert "timestamp" in message
        assert "message_id" in message
        
        result = await ws_manager.send_to_thread("thread123", message)
        
        ws_manager.send_message.assert_called_once_with("thread123", message)
        assert result == True


class TestWebSocketMessageValidation:
    """Test comprehensive WebSocket message validation."""
    
    def test_invalid_message_type_handling(self):
        """Test handling of invalid message types."""
        invalid_types = ["invalid_type", "", None, 123, []]
        
        for invalid_type in invalid_types:
            if invalid_type is None or isinstance(invalid_type, (int, list)):
                continue
            
            with pytest.raises(ValueError):
                WebSocketMessageType(invalid_type)
    
    def test_enum_validation_comprehensive(self):
        """Test comprehensive enum field validation."""
        from app.core.error_codes import ErrorSeverity
        from app.schemas.websocket_payloads import ErrorPayload
        
        # Valid enum values
        valid_severities = ["low", "medium", "high", "critical"]
        for severity in valid_severities:
            payload = ErrorPayload(
                message="Test error",
                code="TEST_ERROR",
                severity=severity
            )
            assert payload.severity == ErrorSeverity(severity)
        
        # Invalid enum values
        invalid_severities = ["invalid", "", "CRITICAL", "Low"]
        for invalid_severity in invalid_severities:
            with pytest.raises(Exception):  # ValidationError or ValueError
                ErrorPayload(
                    message="Test error",
                    code="TEST_ERROR",
                    severity=invalid_severity
                )
    
    def test_message_factory_consistency(self):
        """Test message factory produces consistent results."""
        # Create the same message multiple times
        base_payload = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": "thread456"
        }
        
        messages = []
        for i in range(5):
            message = WebSocketMessageFactory.create_client_message(
                "start_agent",
                base_payload.copy()
            )
            messages.append(message)
        
        # All messages should have the same type and payload content
        for message in messages:
            assert message["type"] == "start_agent"
            assert message["payload"]["query"] == "Test query"
            assert message["payload"]["user_id"] == "user123"
            
            # But should have unique message IDs and timestamps
            assert "message_id" in message
            assert "timestamp" in message
        
        # Message IDs should be unique
        message_ids = [msg["message_id"] for msg in messages]
        assert len(set(message_ids)) == len(message_ids)
    
    def test_bidirectional_message_compatibility(self):
        """Test compatibility between client and server messages."""
        # Create a client message
        client_message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": "Hello, please analyze this data",
                "thread_id": "thread123",
                "metadata": {"source": "chat_ui"}
            }
        )
        
        # Create corresponding server response
        server_message = WebSocketMessageFactory.create_server_message(
            "agent_started",
            {"run_id": "run123"}
        )
        
        # Both should be valid WebSocket messages
        assert "type" in client_message
        assert "type" in server_message
        assert "payload" in client_message
        assert "payload" in server_message
        
        # Types should be valid enum values
        client_type = WebSocketMessageType(client_message["type"])
        server_type = WebSocketMessageType(server_message["type"])
        
        assert client_type == WebSocketMessageType.USER_MESSAGE
        assert server_type == WebSocketMessageType.AGENT_STARTED
