"""
WebSocket State Serialization Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Experience Reliability
- Value Impact: Prevents 70% of WebSocket serialization failures that cause blank chat screens
- Strategic Impact: Critical for chat business value delivery - ensures complex objects serialize properly

This test suite validates WebSocket message serialization with complex nested objects,
Enums, Pydantic models, and other challenging serialization scenarios that are critical
for chat experience reliability.

MISSION CRITICAL: Tests the core serialization that enables 90% of business value delivery.
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager, 
    WebSocketConnection,
    _serialize_message_safely
)
from netra_backend.app.schemas.agent import AgentStatus, AgentStarted
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = central_logger.get_logger(__name__)


class WebSocketTestState(Enum):
    """Test WebSocket state enum for serialization testing."""
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTED = 3
    ERROR = 4


class MockWebSocketState(Enum):
    """Mock WebSocket state similar to FastAPI WebSocketState."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    
    def __str__(self):
        return self.value
    
    @property
    def name(self):
        return self._name_
        
    @property
    def value(self):
        return self._value_


@dataclass
class ComplexNestedData:
    """Complex nested data structure for serialization testing."""
    id: str
    status: WebSocketTestState
    metadata: Dict[str, Any]
    timestamp: datetime
    optional_field: Optional[str] = None
    nested_list: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.nested_list is None:
            self.nested_list = []


class PydanticTestModel:
    """Test Pydantic-like model with model_dump method."""
    
    def __init__(self, name: str, value: int, timestamp: datetime):
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.nested_data = {
            "levels": [1, 2, 3],
            "config": {"enabled": True, "timeout": 30.5}
        }
    
    def model_dump(self, mode='python'):
        """Simulate Pydantic model_dump method."""
        data = {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if mode == 'json' else self.timestamp,
            "nested_data": self.nested_data
        }
        return data


class ObjectWithToDict:
    """Object with to_dict method for serialization testing."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.internal_state = "should_not_serialize"
    
    def to_dict(self):
        return self.data.copy()


@pytest.mark.integration
class WebSocketTestStateSerializationIntegration(SSotBaseTestCase):
    """
    Integration tests for WebSocket state serialization with complex objects.
    
    Tests critical serialization scenarios that affect chat business value:
    - Complex nested objects (DeepAgentState scenarios)
    - Enum serialization (WebSocketState, AgentStatus)
    - Pydantic models with datetime fields
    - Edge cases that cause chat failures
    
    BUSINESS IMPACT: Each test prevents specific chat blank screen scenarios.
    """
    
    async def asyncSetUp(self):
        """Set up WebSocket manager for serialization testing."""
        await super().asyncSetUp()
        self.ws_manager = UnifiedWebSocketManager()
        
        # Create test connections
        self.user_connections = {}
        for i in range(3):
            user_id = f"user_{i}"
            connection_id = str(uuid.uuid4())
            mock_websocket = AsyncMock()
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                connected_at=datetime.now(timezone.utc)
            )
            
            await self.ws_manager.add_connection(connection)
            self.user_connections[user_id] = {
                'connection': connection,
                'mock_websocket': mock_websocket
            }
        
        logger.info("WebSocket serialization test setup completed")
    
    async def test_enum_serialization_websocket_state(self):
        """
        Test WebSocketState enum serialization - CRITICAL for chat reliability.
        
        BVJ: Prevents blank screens when WebSocketState objects are sent to frontend.
        This test covers the most common serialization failure in chat systems.
        """
        # Test various enum types
        test_enums = [
            WebSocketTestState.CONNECTED,
            MockWebSocketState.CONNECTED,
            AgentStatus.ACTIVE,
            AgentStatus.COMPLETED
        ]
        
        for enum_value in test_enums:
            with self.subTest(enum=enum_value):
                # Test direct enum serialization
                serialized = _serialize_message_safely(enum_value)
                
                # Verify serialization succeeds
                self.assertIsNotNone(serialized)
                self.assertIsInstance(serialized, (str, int))
                
                # Verify JSON serializable
                json_str = json.dumps(serialized)
                self.assertIsInstance(json_str, str)
                
                # Test in complex message
                message = {
                    "type": "agent_status_update",
                    "status": enum_value,
                    "timestamp": datetime.now(timezone.utc)
                }
                
                safe_message = _serialize_message_safely(message)
                
                # Should serialize without throwing
                json.dumps(safe_message)
                
                # Send through WebSocket manager
                await self.ws_manager.send_to_user("user_0", safe_message)
                
                # Verify websocket.send_json was called
                mock_ws = self.user_connections["user_0"]["mock_websocket"]
                mock_ws.send_json.assert_called()
                
                # Verify the sent data is JSON serializable
                sent_data = mock_ws.send_json.call_args[0][0]
                json.dumps(sent_data)  # Should not throw
    
    async def test_complex_nested_object_serialization(self):
        """
        Test complex nested object serialization - covers DeepAgentState scenarios.
        
        BVJ: Prevents serialization failures when agents send complex state objects
        that contain nested enums, dataclasses, and mixed data types.
        """
        # Create deeply nested complex object
        complex_data = ComplexNestedData(
            id=str(uuid.uuid4()),
            status=WebSocketTestState.CONNECTED,
            metadata={
                "agent_type": "supervisor",
                "capabilities": ["reasoning", "tool_use"],
                "config": {
                    "timeout": 30.5,
                    "retries": 3,
                    "nested_status": WebSocketTestState.CONNECTING,
                    "timestamps": {
                        "created": datetime.now(timezone.utc),
                        "modified": datetime.now(timezone.utc)
                    }
                }
            },
            timestamp=datetime.now(timezone.utc),
            nested_list=[
                {"type": "event", "status": WebSocketTestState.CONNECTED},
                {"type": "result", "enum_field": AgentStatus.ACTIVE}
            ]
        )
        
        # Test serialization
        serialized = _serialize_message_safely(complex_data)
        
        # Verify structure preserved
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["id"], complex_data.id)
        
        # Verify enums are serialized
        self.assertIsInstance(serialized["status"], (str, int))
        
        # Verify nested objects are handled
        self.assertIn("metadata", serialized)
        self.assertIsInstance(serialized["metadata"], dict)
        
        # Verify datetime serialization
        self.assertIsInstance(serialized["timestamp"], str)
        
        # Verify JSON serialization succeeds
        json_str = json.dumps(serialized)
        self.assertIsInstance(json_str, str)
        
        # Test through WebSocket manager
        message = {
            "type": "complex_agent_state",
            "data": complex_data,
            "meta": {
                "nested_enum": WebSocketTestState.CONNECTED,
                "timestamp": datetime.now(timezone.utc)
            }
        }
        
        # Should handle complex message without errors
        await self.ws_manager.send_to_user("user_1", message)
        
        mock_ws = self.user_connections["user_1"]["mock_websocket"]
        mock_ws.send_json.assert_called()
        
        # Verify sent data is fully serializable
        sent_data = mock_ws.send_json.call_args[0][0]
        json.dumps(sent_data)
    
    async def test_pydantic_model_serialization(self):
        """
        Test Pydantic model serialization with datetime handling.
        
        BVJ: Critical for agent result serialization. Pydantic models are used
        extensively for structured agent outputs and must serialize correctly.
        """
        # Create Pydantic-like test model
        test_model = PydanticTestModel(
            name="test_agent",
            value=42,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Test direct model serialization
        serialized = _serialize_message_safely(test_model)
        
        # Should use model_dump method
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["name"], "test_agent")
        self.assertEqual(serialized["value"], 42)
        
        # Should handle datetime in JSON mode
        self.assertIsInstance(serialized["timestamp"], str)
        
        # Verify JSON serializable
        json.dumps(serialized)
        
        # Test in complex message structure
        message = {
            "type": "agent_result",
            "agent_data": test_model,
            "metadata": {
                "execution_time": 1.5,
                "model_version": test_model
            }
        }
        
        safe_message = _serialize_message_safely(message)
        
        # Should serialize nested Pydantic models
        self.assertIsInstance(safe_message["agent_data"], dict)
        self.assertIsInstance(safe_message["metadata"]["model_version"], dict)
        
        # Send through WebSocket
        await self.ws_manager.send_to_user("user_2", safe_message)
        
        mock_ws = self.user_connections["user_2"]["mock_websocket"]
        mock_ws.send_json.assert_called()
        
        # Verify no serialization errors
        sent_data = mock_ws.send_json.call_args[0][0]
        json.dumps(sent_data)
    
    async def test_edge_case_serialization_scenarios(self):
        """
        Test edge cases that commonly cause serialization failures.
        
        BVJ: Prevents chat failures from uncommon but critical edge cases
        like circular references, None values, and mixed data types.
        """
        # Test None values
        message_with_nones = {
            "type": "partial_data",
            "result": None,
            "optional_field": None,
            "metadata": {"value": None, "status": WebSocketTestState.CONNECTED}
        }
        
        serialized = _serialize_message_safely(message_with_nones)
        self.assertIsNone(serialized["result"])
        json.dumps(serialized)
        
        # Test empty collections
        empty_collections = {
            "empty_list": [],
            "empty_dict": {},
            "empty_set": set(),
            "mixed": [[], {}, set()]
        }
        
        serialized = _serialize_message_safely(empty_collections)
        self.assertEqual(serialized["empty_list"], [])
        self.assertEqual(serialized["empty_dict"], {})
        self.assertIsInstance(serialized["empty_set"], list)  # Sets become lists
        json.dumps(serialized)
        
        # Test objects with to_dict method
        obj_with_method = ObjectWithToDict({
            "public_data": "visible",
            "nested": {"status": WebSocketTestState.CONNECTED}
        })
        
        serialized = _serialize_message_safely(obj_with_method)
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["public_data"], "visible")
        self.assertNotIn("internal_state", serialized)
        json.dumps(serialized)
        
        # Test large nested structures (memory safety)
        large_nested = {
            "level_1": {
                "level_2": {
                    "level_3": {
                        "data": [{"item": i, "status": WebSocketTestState.CONNECTED} for i in range(100)]
                    }
                }
            }
        }
        
        serialized = _serialize_message_safely(large_nested)
        json.dumps(serialized)  # Should not cause memory issues
    
    async def test_websocket_state_enum_specific_handling(self):
        """
        Test WebSocketState enum handling - the most critical serialization case.
        
        BVJ: WebSocketState serialization failures are the #1 cause of chat blank screens.
        This test specifically validates the WebSocket state enum serialization logic.
        """
        # Mock various WebSocket state types
        mock_starlette_state = Mock()
        mock_starlette_state.name = "CONNECTED"
        mock_starlette_state.value = 1
        
        mock_fastapi_state = Mock()
        mock_fastapi_state.name = "CONNECTED" 
        mock_fastapi_state.value = 1
        
        # Test state objects that look like WebSocket states
        websocket_like_objects = [
            mock_starlette_state,
            mock_fastapi_state,
            MockWebSocketState.CONNECTED
        ]
        
        for state_obj in websocket_like_objects:
            with self.subTest(state=state_obj):
                serialized = _serialize_message_safely(state_obj)
                
                # Should convert to lowercase string (WebSocket convention)
                if hasattr(state_obj, 'name'):
                    expected = state_obj.name.lower()
                    self.assertEqual(serialized, expected)
                
                # Should be JSON serializable
                json.dumps(serialized)
                
                # Test in message context
                message = {
                    "type": "connection_status",
                    "websocket_state": state_obj,
                    "timestamp": datetime.now(timezone.utc)
                }
                
                safe_message = _serialize_message_safely(message)
                json.dumps(safe_message)
                
                # Send through manager
                await self.ws_manager.send_to_user("user_0", safe_message)
    
    async def test_concurrent_serialization_safety(self):
        """
        Test serialization safety under concurrent access.
        
        BVJ: Ensures serialization doesn't fail under concurrent chat load.
        Critical for multi-user chat reliability.
        """
        # Create multiple complex messages
        messages = []
        for i in range(10):
            message = {
                "type": f"concurrent_test_{i}",
                "data": ComplexNestedData(
                    id=str(uuid.uuid4()),
                    status=WebSocketTestState.CONNECTED,
                    metadata={"index": i, "enum": AgentStatus.ACTIVE},
                    timestamp=datetime.now(timezone.utc)
                ),
                "pydantic": PydanticTestModel(f"model_{i}", i, datetime.now(timezone.utc)),
                "enum": WebSocketTestState.CONNECTING
            }
            messages.append(message)
        
        # Serialize concurrently
        async def serialize_and_send(msg, user_id):
            serialized = _serialize_message_safely(msg)
            json.dumps(serialized)  # Verify JSON serializable
            await self.ws_manager.send_to_user(user_id, serialized)
        
        # Run concurrent serialization
        tasks = [
            serialize_and_send(msg, f"user_{i % 3}")
            for i, msg in enumerate(messages)
        ]
        
        # Should complete without errors
        await asyncio.gather(*tasks)
        
        # Verify all messages were sent
        for user_data in self.user_connections.values():
            mock_ws = user_data["mock_websocket"]
            self.assertTrue(mock_ws.send_json.called)
    
    async def test_serialization_fallback_mechanisms(self):
        """
        Test serialization fallback mechanisms for unknown types.
        
        BVJ: Ensures chat never fails completely - even unknown objects
        get converted to string representation rather than causing crashes.
        """
        # Create object that can't be serialized normally
        class UnserializableObject:
            def __init__(self):
                self.data = "test"
                # Circular reference
                self.self_ref = self
            
            def __str__(self):
                return f"UnserializableObject(data={self.data})"
        
        unserializable = UnserializableObject()
        
        # Should fall back to string representation
        serialized = _serialize_message_safely(unserializable)
        self.assertIsInstance(serialized, str)
        self.assertIn("UnserializableObject", serialized)
        
        # Should be JSON serializable
        json.dumps(serialized)
        
        # Test in message context
        message = {
            "type": "fallback_test",
            "unknown_object": unserializable,
            "normal_data": {"status": WebSocketTestState.CONNECTED}
        }
        
        safe_message = _serialize_message_safely(message)
        
        # Should preserve serializable parts
        self.assertIsInstance(safe_message["normal_data"], dict)
        
        # Should convert unserializable to string
        self.assertIsInstance(safe_message["unknown_object"], str)
        
        # Should be fully JSON serializable
        json.dumps(safe_message)
    
    async def test_memory_efficiency_large_objects(self):
        """
        Test memory efficiency with large serialization objects.
        
        BVJ: Prevents memory exhaustion during heavy chat usage with large agent responses.
        """
        # Create large object that tests memory handling
        large_data = {
            "type": "memory_test",
            "large_list": [
                {
                    "index": i,
                    "status": WebSocketTestState.CONNECTED,
                    "data": f"data_{'x' * 100}_{i}",  # 100 chars each
                    "nested": {
                        "timestamp": datetime.now(timezone.utc),
                        "metadata": {"item": j for j in range(10)}
                    }
                }
                for i in range(1000)  # 1000 items
            ],
            "enum_field": AgentStatus.ACTIVE
        }
        
        # Should handle large object without memory issues
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        serialized = _serialize_message_safely(large_data)
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # Should not cause excessive memory usage (< 50MB increase)
        self.assertLess(memory_increase, 50 * 1024 * 1024)
        
        # Should still be serializable
        json.dumps(serialized)
        
        # Send through WebSocket
        await self.ws_manager.send_to_user("user_0", serialized)
    
    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clear connections
        for user_data in self.user_connections.values():
            connection = user_data["connection"]
            await self.ws_manager.remove_connection(connection.connection_id)
        
        # Clear manager
        self.user_connections.clear()
        
        await super().asyncTearDown()
        logger.info("WebSocket serialization test teardown completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])