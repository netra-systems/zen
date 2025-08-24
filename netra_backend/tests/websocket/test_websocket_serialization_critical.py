"""Critical WebSocket Serialization Tests

Comprehensive test suite for WebSocket message serialization issues,
particularly datetime serialization and message type validation.
Maximum 300 lines, functions ≤8 lines each.
"""

import sys
from pathlib import Path

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.schemas.registry import (
    DeepAgentState,
    Message,
    MessageType,
    Thread,
    User,
    WebSocketMessage,
    WebSocketMessageType,
)
from netra_backend.app.schemas.websocket_message_types import (
    AgentCompletedMessage,
    AgentStartedMessage,
    BroadcastResult,
    ConnectionInfo,
    StartAgentMessage,
    UserMessage,
)
from netra_backend.app.services.state_persistence import DateTimeEncoder
from netra_backend.app.websocket_core.manager import WebSocketManager  # BroadcastManager functionality is in WebSocketManager
from netra_backend.app.websocket_core.utils import validate_message_structure as MessageValidator

class TestWebSocketSerializationCritical:
    """Critical serialization tests for production issues"""

    @pytest.fixture
    def datetime_encoder(self):
        """DateTimeEncoder instance"""
        return DateTimeEncoder()

    @pytest.fixture
    def message_validator(self):
        """MessageValidator instance"""
        return MessageValidator()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection"""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_datetime_serialization_error_exact_reproduction(self):
        """Reproduce exact datetime serialization error from production"""
        problematic_data = {
            "timestamp": datetime.now(),
            "nested": {"created_at": datetime.now()}
        }
        
        with pytest.raises(TypeError) as exc_info:
            json.dumps(problematic_data)
        assert "Object of type datetime is not JSON serializable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_datetime_encoder_fix_comprehensive(self, datetime_encoder):
        """Test DateTimeEncoder fixes all datetime serialization issues"""
        test_data = {
            "direct_datetime": datetime.now(),
            "nested": {"deep_datetime": datetime.now()},
            "list_with_datetime": [datetime.now(), "string", 123]
        }
        
        serialized = json.dumps(test_data, cls=DateTimeEncoder)
        deserialized = json.loads(serialized)
        
        assert isinstance(deserialized["direct_datetime"], str)
        assert isinstance(deserialized["nested"]["deep_datetime"], str)

    @pytest.mark.asyncio
    async def test_invalid_thread_created_message_type(self):
        """Test invalid 'thread_created' message type validation failure"""
        invalid_message = {
            "type": "thread_created",  # Invalid type!
            "payload": {"thread_id": str(uuid.uuid4())}
        }
        
        with pytest.raises(ValueError):
            WebSocketMessageType(invalid_message["type"])

    @pytest.mark.asyncio
    async def test_all_websocket_message_types_serialization(self, datetime_encoder):
        """Test serialization of ALL WebSocket message types"""
        test_messages = self._create_all_message_types()
        
        for msg_type, message_data in test_messages.items():
            serialized = json.dumps(message_data, cls=DateTimeEncoder)
            deserialized = json.loads(serialized)
            assert deserialized["type"] == msg_type

    def _create_all_message_types(self) -> Dict[str, Dict[str, Any]]:
        """Create test data for all message types"""
        base_timestamp = datetime.now()
        return {
            "start_agent": {"type": "start_agent", "payload": {"agent_type": "supervisor"}},
            "user_message": {"type": "user_message", "payload": {"text": "test"}},
            "agent_started": {"type": "agent_started", "payload": {"run_id": str(uuid.uuid4())}},
            "agent_completed": {"type": "agent_completed", "payload": {"timestamp": base_timestamp}}
        }

    @pytest.mark.asyncio
    async def test_complex_nested_object_serialization(self, datetime_encoder):
        """Test complex nested structures with datetime serialization"""
        complex_payload = {
            "agent_state": {
                "timestamps": [datetime.now(), datetime.now() + timedelta(hours=1)],
                "metadata": {"created": datetime.now(), "nested": {"deep": datetime.now()}}
            }
        }
        
        message = {"type": "agent_update", "payload": complex_payload}
        serialized = json.dumps(message, cls=DateTimeEncoder)
        assert json.loads(serialized)

    @pytest.mark.asyncio
    async def test_broadcast_with_datetime_recovery(self, mock_websocket):
        """Test broadcast error recovery with datetime serialization"""
        manager = BroadcastManager(Mock())
        message_with_datetime = {
            "type": "agent_log",
            "payload": {"timestamp": datetime.now(), "message": "test"}
        }
        
        with patch('json.dumps') as mock_dumps:
            mock_dumps.side_effect = [
                TypeError("datetime not serializable"),
                json.dumps(message_with_datetime, default=str)
            ]
            
            result = await manager._send_to_connection(
                Mock(websocket=mock_websocket), message_with_datetime
            )
            assert mock_dumps.call_count >= 1

    @pytest.mark.asyncio
    async def test_binary_data_handling(self):
        """Test binary data in WebSocket messages"""
        binary_payload = {
            "type": "tool_result",
            "payload": {
                "data": b"binary_data".hex(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        validated = WebSocketMessage(**binary_payload)
        serialized = json.dumps(validated.model_dump(), cls=DateTimeEncoder)
        assert json.loads(serialized)

    @pytest.mark.asyncio
    async def test_large_message_validation(self, message_validator):
        """Test large message size validation"""
        large_payload = {
            "type": "agent_update",
            "payload": {"data": "x" * (1024 * 1024 + 1)}  # > 1MB
        }
        
        result = message_validator.validate_message(large_payload)
        assert hasattr(result, 'error_type')
        assert result.error_type == "validation_error"

    @pytest.mark.asyncio
    async def test_connection_state_transitions_serialization(self):
        """Test connection state changes with datetime fields"""
        connection_info = ConnectionInfo(
            user_id="test_user",
            connection_id="test_conn",
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            last_message_time=datetime.now(),
            rate_limit_window_start=datetime.now()
        )
        
        serialized = json.dumps(connection_info.model_dump(), cls=DateTimeEncoder)
        assert json.loads(serialized)

    @pytest.mark.asyncio
    async def test_concurrent_datetime_serialization(self):
        """Test concurrent serialization doesn't cause conflicts"""
        async def serialize_message(i: int):
            data = {"type": "agent_log", "payload": {"timestamp": datetime.now(), "id": i}}
            return json.dumps(data, cls=DateTimeEncoder)
        
        tasks = [serialize_message(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_message_type_enum_validation_comprehensive(self):
        """Test all message type enum values validate correctly"""
        valid_types = [t.value for t in WebSocketMessageType]
        
        for msg_type in valid_types:
            message = {"type": msg_type, "payload": {}}
            validated = WebSocketMessage(**message)
            assert validated.type == msg_type

    @pytest.mark.asyncio
    async def test_broadcast_result_serialization(self):
        """Test BroadcastResult with datetime metadata"""
        result = BroadcastResult(
            successful=5,
            failed=1,
            total_connections=6,
            message_type="agent_update"
        )
        
        serialized = json.dumps(result.model_dump())
        assert json.loads(serialized)

    @pytest.mark.asyncio
    async def test_message_validation_security_patterns(self, message_validator):
        """Test security validation in message content"""
        malicious_message = {
            "type": "user_message",
            "payload": {"text": "<script>alert('xss')</script>"}
        }
        
        result = message_validator.validate_message(malicious_message)
        assert hasattr(result, 'error_type')
        assert result.error_type == "security_error"

    @pytest.mark.asyncio
    async def test_datetime_in_all_payload_positions(self, datetime_encoder):
        """Test datetime serialization in various payload positions"""
        payload_variations = [
            {"timestamp": datetime.now()},
            {"metadata": {"created": datetime.now()}},
            {"items": [{"when": datetime.now()}]},
            {"deep": {"nested": {"time": datetime.now()}}}
        ]
        
        for payload in payload_variations:
            message = {"type": "agent_update", "payload": payload}
            serialized = json.dumps(message, cls=DateTimeEncoder)
            assert json.loads(serialized)

    @pytest.mark.asyncio
    async def test_serialization_edge_cases(self):
        """Test edge cases in serialization"""
        edge_cases = [
            {"type": "ping", "payload": {}},
            {"type": "pong", "payload": {}},
            {"type": "error", "payload": {"error": "", "details": {}}},
            {"type": "stream_complete", "payload": {"final": True}}
        ]
        
        for case in edge_cases:
            validated = WebSocketMessage(**case)
            serialized = json.dumps(validated.model_dump(), cls=DateTimeEncoder)
            assert json.loads(serialized)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])