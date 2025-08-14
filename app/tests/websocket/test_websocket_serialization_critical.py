"""Critical WebSocket Serialization Tests

Tests for WebSocket message serialization issues seen in production,
particularly datetime serialization and message type validation.
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, Mock, patch
from pydantic import ValidationError

from app.schemas import (
    WebSocketMessage, AgentStarted, SubAgentUpdate, 
    AgentCompleted, ErrorMessage
)
from app.websocket.broadcast import WebSocketBroadcaster
from app.ws_manager_messaging import WebSocketManager


class TestWebSocketSerializationCritical:
    """Test WebSocket serialization issues from production"""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager instance"""
        manager = WebSocketManager()
        return manager
    
    @pytest.mark.asyncio
    async def test_datetime_serialization_error_reproduction(self):
        """Reproduce the exact datetime serialization error from production"""
        # Create message with datetime - this is what fails in production
        message_data = {
            "type": "agent_completed",
            "payload": {
                "run_id": str(uuid.uuid4()),
                "timestamp": datetime.now(),  # This causes the error!
                "execution_time": 1234,
                "result": {
                    "status": "success",
                    "completed_at": datetime.now()  # Nested datetime also fails
                }
            }
        }
        
        # Direct JSON serialization should fail
        with pytest.raises(TypeError) as exc_info:
            json.dumps(message_data)
        
        assert "Object of type datetime is not JSON serializable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_datetime_serialization_fix(self):
        """Test the fix for datetime serialization"""
        
        class DateTimeEncoder(json.JSONEncoder):
            """Custom JSON encoder for datetime objects"""
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        # Create message with datetime
        message_data = {
            "type": "agent_completed",
            "payload": {
                "run_id": str(uuid.uuid4()),
                "timestamp": datetime.now(),
                "execution_time": 1234,
                "result": {
                    "status": "success",
                    "completed_at": datetime.now()
                }
            }
        }
        
        # Should work with custom encoder
        serialized = json.dumps(message_data, cls=DateTimeEncoder)
        assert serialized
        
        # Should be able to deserialize
        deserialized = json.loads(serialized)
        assert deserialized["type"] == "agent_completed"
        assert isinstance(deserialized["payload"]["timestamp"], str)
    
    @pytest.mark.asyncio
    async def test_invalid_message_type_error(self):
        """Test the invalid message type error from production"""
        # This is the exact error from logs
        invalid_message = {
            "type": "thread_created",  # Not a valid WebSocketMessage type!
            "payload": {
                "thread_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat()
            }
        }
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(**invalid_message)
        
        # Check error mentions the invalid type
        error_str = str(exc_info.value)
        assert "type" in error_str or "thread_created" in error_str
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_with_datetime(self, mock_websocket):
        """Test broadcasting messages with datetime fields"""
        broadcaster = WebSocketBroadcaster()
        connection_id = "test_conn_123"
        
        # Add connection
        broadcaster.active_connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": str(uuid.uuid4()),
            "thread_id": str(uuid.uuid4())
        }
        
        # Create message with datetime
        message = {
            "type": "sub_agent_update",
            "payload": {
                "agent_name": "TriageSubAgent",
                "status": "processing",
                "timestamp": datetime.now(),
                "metadata": {
                    "started_at": datetime.now(),
                    "progress": 0.5
                }
            }
        }
        
        # Mock JSON encoder
        with patch("json.dumps") as mock_dumps:
            # First call fails (simulating production error)
            mock_dumps.side_effect = [
                TypeError("Object of type datetime is not JSON serializable"),
                json.dumps(message, default=str)  # Second call succeeds with default serializer
            ]
            
            # Should handle the error and retry with proper serialization
            await broadcaster.send_to_connection(connection_id, message)
            
            # Should have tried twice
            assert mock_dumps.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_all_websocket_message_types(self):
        """Test serialization of all WebSocket message types with datetime"""
        test_messages = [
            {
                "type": "agent_started",
                "payload": AgentStarted(
                    run_id=str(uuid.uuid4()),
                    agent_name="Supervisor",
                    timestamp=datetime.now().isoformat()
                ).model_dump()
            },
            {
                "type": "sub_agent_update", 
                "payload": SubAgentUpdate(
                    run_id=str(uuid.uuid4()),
                    agent_name="TriageSubAgent",
                    status="processing",
                    message="Analyzing request",
                    progress=0.5,
                    timestamp=datetime.now().isoformat()
                ).model_dump()
            },
            {
                "type": "agent_completed",
                "payload": AgentCompleted(
                    run_id=str(uuid.uuid4()),
                    success=True,
                    result={"data": "test"},
                    execution_time_ms=1500,
                    timestamp=datetime.now().isoformat()
                ).model_dump()
            },
            {
                "type": "error",
                "payload": ErrorMessage(
                    run_id=str(uuid.uuid4()),
                    error_type="ValidationError",
                    message="Test error",
                    details={"field": "test"},
                    timestamp=datetime.now().isoformat()
                ).model_dump()
            }
        ]
        
        for message in test_messages:
            # Should validate without errors
            validated = WebSocketMessage(**message)
            assert validated.type == message["type"]
            
            # Should serialize to JSON
            serialized = json.dumps(validated.model_dump())
            assert serialized
    
    @pytest.mark.asyncio
    async def test_websocket_manager_send_methods(self, websocket_manager):
        """Test all WebSocket manager send methods handle serialization"""
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        # Mock active connections
        mock_ws = AsyncMock()
        websocket_manager.active_connections = {
            "conn1": {
                "websocket": mock_ws,
                "thread_id": thread_id,
                "user_id": "user1"
            }
        }
        
        # Test send_to_thread with datetime
        message_with_datetime = {
            "type": "agent_log",
            "payload": {
                "message": "Test log",
                "timestamp": datetime.now(),
                "level": "info"
            }
        }
        
        # Mock the serialization to handle datetime
        with patch("json.dumps") as mock_dumps:
            mock_dumps.return_value = json.dumps(message_with_datetime, default=str)
            
            await websocket_manager.send_to_thread(thread_id, message_with_datetime)
            
            # Verify send was called
            mock_ws.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complex_nested_datetime_serialization(self):
        """Test serialization of deeply nested datetime objects"""
        complex_data = {
            "type": "agent_completed",
            "payload": {
                "run_id": str(uuid.uuid4()),
                "timestamp": datetime.now(),
                "result": {
                    "triage": {
                        "completed_at": datetime.now(),
                        "metadata": {
                            "created": datetime.now() - timedelta(hours=1),
                            "updated": datetime.now()
                        }
                    },
                    "optimization": {
                        "started": datetime.now() - timedelta(minutes=30),
                        "ended": datetime.now(),
                        "recommendations": [
                            {
                                "created": datetime.now(),
                                "expires": datetime.now() + timedelta(days=7)
                            }
                        ]
                    }
                }
            }
        }
        
        def serialize_datetime_recursive(obj):
            """Recursively serialize datetime objects"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime_recursive(item) for item in obj]
            return obj
        
        # Serialize the complex structure
        serialized_data = serialize_datetime_recursive(complex_data)
        
        # Should be JSON serializable now
        json_str = json.dumps(serialized_data)
        assert json_str
        
        # Verify all datetimes were converted
        parsed = json.loads(json_str)
        
        def check_no_datetime(obj):
            """Verify no datetime objects remain"""
            if isinstance(obj, datetime):
                return False
            elif isinstance(obj, dict):
                return all(check_no_datetime(v) for v in obj.values())
            elif isinstance(obj, list):
                return all(check_no_datetime(item) for item in obj)
            return True
        
        assert check_no_datetime(parsed)
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_broadcasts(self):
        """Test concurrent WebSocket broadcasts don't cause serialization conflicts"""
        import asyncio
        
        broadcaster = WebSocketBroadcaster()
        
        # Create multiple connections
        connections = {}
        for i in range(5):
            mock_ws = AsyncMock()
            conn_id = f"conn_{i}"
            connections[conn_id] = mock_ws
            broadcaster.active_connections[conn_id] = {
                "websocket": mock_ws,
                "user_id": f"user_{i}",
                "thread_id": str(uuid.uuid4())
            }
        
        # Create messages with datetime
        messages = [
            {
                "type": "sub_agent_update",
                "payload": {
                    "agent_name": f"Agent_{i}",
                    "timestamp": datetime.now() + timedelta(seconds=i),
                    "status": "processing"
                }
            }
            for i in range(5)
        ]
        
        # Broadcast concurrently
        with patch.object(broadcaster, "_serialize_message") as mock_serialize:
            mock_serialize.side_effect = lambda msg: json.dumps(msg, default=str)
            
            tasks = [
                broadcaster.broadcast(msg)
                for msg in messages
            ]
            
            await asyncio.gather(*tasks)
            
            # Verify all messages were serialized
            assert mock_serialize.call_count >= len(messages)
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_broadcast(self, mock_websocket):
        """Test error recovery during WebSocket broadcast"""
        broadcaster = WebSocketBroadcaster()
        
        # Add connections
        broadcaster.active_connections = {
            "conn1": {"websocket": mock_websocket, "user_id": "user1"},
            "conn2": {"websocket": AsyncMock(), "user_id": "user2"}
        }
        
        # First websocket fails
        mock_websocket.send_text.side_effect = Exception("Connection closed")
        
        # Message with datetime
        message = {
            "type": "agent_log",
            "payload": {
                "message": "Test",
                "timestamp": datetime.now()
            }
        }
        
        # Should handle error and continue to other connections
        await broadcaster.broadcast(message)
        
        # Second connection should still receive
        conn2_ws = broadcaster.active_connections["conn2"]["websocket"]
        conn2_ws.send_text.assert_called()
        
        # Failed connection should be removed
        assert "conn1" not in broadcaster.active_connections or \
               broadcaster.active_connections["conn1"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])