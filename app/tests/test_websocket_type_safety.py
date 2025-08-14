"""WebSocket Message Type Safety Tests.

Specific tests for WebSocket message type consistency between frontend and backend.
"""

import json
import pytest
from typing import Dict, Any, List
from datetime import datetime
from pydantic import ValidationError

from app.schemas.websocket_unified import (
    WebSocketMessageType,
    WebSocketConnectionState,
    ErrorSeverity
)
from app.schemas.Agent import AgentStarted, AgentCompleted, AgentErrorMessage, SubAgentUpdate
from app.schemas.Tool import ToolStarted, ToolCompleted


class WebSocketMessageFactory:
    """Factory for creating test WebSocket messages."""
    
    @staticmethod
    def create_client_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a client-to-server message."""
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"msg_{msg_type}_{datetime.now().timestamp()}"
        }
    
    @staticmethod
    def create_server_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a server-to-client message."""
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"srv_{msg_type}_{datetime.now().timestamp()}"
        }


class TestClientToServerMessages:
    """Test client-to-server message type safety."""
    
    def test_start_agent_message(self):
        """Test START_AGENT message type."""
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
        
        # Validate full message
        full_msg = ClientToServerMessage(
            type=msg_type,
            payload=payload
        )
        assert full_msg.type == WebSocketMessageType.START_AGENT
    
    def test_user_message(self):
        """Test USER_MESSAGE message type."""
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
    
    def test_thread_operations(self):
        """Test thread operation messages."""
        operations = [
            ("create_thread", CreateThreadPayload, {"title": "New Thread"}),
            ("switch_thread", SwitchThreadPayload, {"thread_id": "thread789"}),
            ("delete_thread", DeleteThreadPayload, {"thread_id": "thread456"}),
            ("rename_thread", RenameThreadPayload, {
                "thread_id": "thread456",
                "new_title": "Updated Thread Title"
            }),
            ("list_threads", ListThreadsPayload, {}),
        ]
        
        for op_type, payload_class, payload_data in operations:
            message = WebSocketMessageFactory.create_client_message(op_type, payload_data)
            
            msg_type = WebSocketMessageType(message["type"])
            assert msg_type.value == op_type
            
            payload = payload_class(**message["payload"])
            assert payload is not None
    
    def test_control_messages(self):
        """Test control messages (ping, stop_agent)."""
        # Test PING
        ping_msg = WebSocketMessageFactory.create_client_message("ping", {})
        msg_type = WebSocketMessageType(ping_msg["type"])
        assert msg_type == WebSocketMessageType.PING
        
        # Test STOP_AGENT
        stop_msg = WebSocketMessageFactory.create_client_message(
            "stop_agent",
            {"run_id": "run123"}
        )
        msg_type = WebSocketMessageType(stop_msg["type"])
        payload = StopAgentPayload(**stop_msg["payload"])
        assert payload.run_id == "run123"
    
    def test_get_thread_history(self):
        """Test GET_THREAD_HISTORY message."""
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


class TestServerToClientMessages:
    """Test server-to-client message type safety."""
    
    def test_agent_lifecycle_messages(self):
        """Test agent lifecycle messages."""
        lifecycle_messages = [
            ("agent_started", AgentStartedPayload, {"run_id": "run123"}),
            ("agent_completed", AgentCompletedPayload, {
                "run_id": "run123",
                "result": {"status": "success", "data": {}}
            }),
            ("agent_stopped", AgentStoppedPayload, {
                "run_id": "run123",
                "reason": "User requested stop"
            }),
            ("agent_error", AgentErrorPayload, {
                "run_id": "run123",
                "message": "Processing failed",
                "code": "PROCESSING_ERROR"
            }),
        ]
        
        for msg_type_str, payload_class, payload_data in lifecycle_messages:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            msg_type = WebSocketMessageType(message["type"])
            assert msg_type.value == msg_type_str
            
            payload = payload_class(**message["payload"])
            assert payload.run_id == "run123"
    
    def test_tool_messages(self):
        """Test tool-related messages."""
        tool_messages = [
            ("tool_started", ToolStartedPayload, {
                "tool_name": "log_analyzer",
                "tool_args": {"level": "error"},
                "run_id": "run123"
            }),
            ("tool_completed", ToolCompletedPayload, {
                "tool_name": "log_analyzer",
                "tool_output": {"logs": [], "count": 0},
                "run_id": "run123",
                "status": "success"
            }),
            ("tool_call", ToolCallPayload, {
                "tool_name": "cost_analyzer",
                "tool_args": {"period": "monthly"},
                "run_id": "run123"
            }),
            ("tool_result", ToolResultPayload, {
                "tool_name": "cost_analyzer",
                "result": {"total_cost": 1500.00},
                "run_id": "run123"
            }),
        ]
        
        for msg_type_str, payload_class, payload_data in tool_messages:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            msg_type = WebSocketMessageType(message["type"])
            payload = payload_class(**message["payload"])
            assert payload.tool_name in ["log_analyzer", "cost_analyzer"]
    
    def test_subagent_messages(self):
        """Test subagent messages."""
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
        
        subagent_completed = WebSocketMessageFactory.create_server_message(
            "subagent_completed",
            {
                "subagent_id": "sub123",
                "result": {"analysis": "complete"},
                "parent_run_id": "run123"
            }
        )
        
        payload = SubAgentCompletedPayload(**subagent_completed["payload"])
        assert payload.subagent_id == "sub123"
    
    def test_thread_response_messages(self):
        """Test thread response messages."""
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
                    {"id": "t1", "title": "Thread 1"},
                    {"id": "t2", "title": "Thread 2"}
                ]
            }),
        ]
        
        for msg_type_str, payload_class, payload_data in thread_messages:
            message = WebSocketMessageFactory.create_server_message(
                msg_type_str, payload_data
            )
            
            msg_type = WebSocketMessageType(message["type"])
            payload = payload_class(**message["payload"])
            assert payload is not None
    
    def test_streaming_messages(self):
        """Test streaming messages."""
        # Stream chunk
        chunk_msg = WebSocketMessageFactory.create_server_message(
            "stream_chunk",
            {
                "content": "Processing data",
                "index": 0,
                "finished": False,
                "metadata": {"tokens": 3}
            }
        )
        
        chunk_payload = StreamChunkPayload(**chunk_msg["payload"])
        assert chunk_payload.content == "Processing data"
        assert chunk_payload.finished is False
        
        # Stream complete
        complete_msg = WebSocketMessageFactory.create_server_message(
            "stream_complete",
            {
                "total_chunks": 10,
                "total_tokens": 150,
                "metadata": {"model": "gpt-4"}
            }
        )
        
        complete_payload = StreamCompletePayload(**complete_msg["payload"])
        assert complete_payload.total_chunks == 10
    
    def test_error_message(self):
        """Test error message."""
        error_msg = WebSocketMessageFactory.create_server_message(
            "error",
            {
                "message": "Authentication failed",
                "code": "AUTH_FAILED",
                "severity": "high",
                "details": {"reason": "Invalid token"}
            }
        )
        
        msg_type = WebSocketMessageType(error_msg["type"])
        assert msg_type == WebSocketMessageType.ERROR
        
        payload = ErrorPayload(**error_msg["payload"])
        assert payload.message == "Authentication failed"
        assert payload.severity == ErrorSeverity.HIGH
    
    def test_connection_established(self):
        """Test connection established message."""
        conn_msg = WebSocketMessageFactory.create_server_message(
            "connection_established",
            {
                "connection_id": "conn123",
                "session_id": "session456",
                "server_version": "1.0.0"
            }
        )
        
        payload = ConnectionEstablishedPayload(**conn_msg["payload"])
        assert payload.connection_id == "conn123"


class TestMessageValidation:
    """Test message validation and error handling."""
    
    def test_invalid_message_type(self):
        """Test handling of invalid message types."""
        with pytest.raises(ValueError):
            WebSocketMessageType("invalid_type")
    
    def test_missing_required_fields(self):
        """Test validation of missing required fields."""
        # Missing required field 'query'
        with pytest.raises(ValidationError):
            StartAgentPayload(user_id="user123")
        
        # Missing required field 'run_id'
        with pytest.raises(ValidationError):
            AgentStartedPayload()
    
    def test_invalid_field_types(self):
        """Test validation of invalid field types."""
        # Invalid type for 'limit' (should be int)
        with pytest.raises(ValidationError):
            ThreadHistoryPayload(
                thread_id="thread123",
                limit="not_an_int",
                offset=0
            )
    
    def test_enum_validation(self):
        """Test enum field validation."""
        # Invalid error severity
        with pytest.raises(ValidationError):
            ErrorPayload(
                message="Error",
                code="ERROR",
                severity="invalid_severity"
            )
    
    def test_extra_fields_handling(self):
        """Test handling of extra fields (should be forbidden)."""
        with pytest.raises(ValidationError):
            StartAgentPayload(
                query="Test",
                user_id="user123",
                extra_field="should_fail"
            )


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


class TestWebSocketSendToThread:
    """Test WebSocket send_to_thread functionality."""
    
    @pytest.mark.asyncio
    async def test_send_to_thread_exists(self):
        """Test that send_to_thread method exists and works."""
        from app.ws_manager import WebSocketManager
        from unittest.mock import AsyncMock
        
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
    
    @pytest.mark.asyncio
    async def test_supervisor_send_completion(self):
        """Test supervisor can send completion messages."""
        from unittest.mock import AsyncMock, MagicMock, patch
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])