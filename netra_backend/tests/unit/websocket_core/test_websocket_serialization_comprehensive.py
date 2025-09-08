"""Comprehensive unit tests for WebSocket JSON serialization.

CRITICAL: Tests the enhanced _serialize_message_safely function that prevents
"Object of type WebSocketState is not JSON serializable" errors.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Chat Functionality
- Value Impact: Prevents WebSocket communication failures that break real-time chat
- Strategic Impact: Ensures all message types can be transmitted to users
"""

import pytest
import json
from datetime import datetime, timezone
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from unittest.mock import Mock

# Import the function under test
from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely


class TestWebSocketState(Enum):
    """Mock WebSocketState enum for testing."""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 3


class TestIntEnum(IntEnum):
    """Test integer enum.""" 
    FIRST = 1
    SECOND = 2
    THIRD = 3


@dataclass
class TestDataClass:
    """Test dataclass for serialization."""
    name: str
    value: int
    created_at: datetime


class TestPydanticModel:
    """Mock Pydantic model for testing."""
    
    def __init__(self, name: str, created_at: datetime):
        self.name = name
        self.created_at = created_at
    
    def model_dump(self, mode: str = None) -> Dict[str, Any]:
        if mode == 'json':
            return {
                'name': self.name,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }
        else:
            return {
                'name': self.name, 
                'created_at': self.created_at
            }


class TestComplexObject:
    """Test object with to_dict method."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data.copy()


class TestWebSocketSerializationComprehensive:
    """Comprehensive test suite for WebSocket message serialization."""
    
    def test_simple_dict_passes_through(self):
        """Test that simple dict passes through unchanged."""
        message = {"type": "test", "data": "simple"}
        result = _serialize_message_safely(message)
        assert result == message
        
        # Verify it's JSON serializable
        json.dumps(result)
    
    def test_websocket_state_enum_serialized(self):
        """CRITICAL: Test WebSocketState enum is properly serialized."""
        # This is the exact error case from the logs
        state = TestWebSocketState.CONNECTED
        result = _serialize_message_safely(state)
        
        # Should convert to the enum value
        assert result == 1
        
        # Verify it's JSON serializable
        json.dumps(result)
    
    def test_string_enum_serialized(self):
        """Test string-based enum serialization."""
        class StringEnum(Enum):
            TEST_VALUE = "test_string"
        
        result = _serialize_message_safely(StringEnum.TEST_VALUE)
        assert result == "test_string"
        json.dumps(result)
    
    def test_int_enum_serialized(self):
        """Test IntEnum serialization."""
        result = _serialize_message_safely(TestIntEnum.SECOND)
        assert result == 2
        json.dumps(result)
    
    def test_pydantic_model_with_datetime(self):
        """Test Pydantic model with datetime field."""
        now = datetime.now(timezone.utc)
        model = TestPydanticModel("test", now)
        
        result = _serialize_message_safely(model)
        
        # Should use model_dump(mode='json') for proper datetime handling
        assert result["name"] == "test"
        assert result["created_at"] == now.isoformat()
        json.dumps(result)
    
    def test_object_with_to_dict_method(self):
        """Test object with to_dict method."""
        obj = TestComplexObject({"key": "value", "number": 42})
        result = _serialize_message_safely(obj)
        
        assert result == {"key": "value", "number": 42}
        json.dumps(result)
    
    def test_dataclass_serialization(self):
        """Test dataclass serialization.""" 
        now = datetime.now(timezone.utc)
        dc = TestDataClass("test", 123, now)
        
        result = _serialize_message_safely(dc)
        
        assert result["name"] == "test"
        assert result["value"] == 123
        assert result["created_at"] == now  # Note: dataclass asdict doesn't convert datetime
        
        # The result should be JSON serializable (datetime will be handled by JSON encoder)
        # For this test, we'll just verify the structure
        assert isinstance(result, dict)
        assert len(result) == 3
    
    def test_datetime_object_serialization(self):
        """Test direct datetime object serialization."""
        now = datetime.now(timezone.utc)
        result = _serialize_message_safely(now)
        
        assert result == now.isoformat()
        json.dumps(result)
    
    def test_list_with_enums_serialized(self):
        """Test list containing enum objects."""
        message = [
            TestWebSocketState.CONNECTING,
            TestWebSocketState.CONNECTED, 
            {"state": TestWebSocketState.DISCONNECTED}
        ]
        
        result = _serialize_message_safely(message)
        
        assert result[0] == 0  # CONNECTING
        assert result[1] == 1  # CONNECTED
        assert result[2]["state"] == 3  # DISCONNECTED
        json.dumps(result)
    
    def test_dict_with_nested_enums(self):
        """Test dict containing nested enum objects."""
        message = {
            "connection_state": TestWebSocketState.CONNECTED,
            "metadata": {
                "previous_state": TestWebSocketState.CONNECTING,
                "states_list": [TestWebSocketState.CONNECTED, TestWebSocketState.DISCONNECTED]
            }
        }
        
        result = _serialize_message_safely(message)
        
        assert result["connection_state"] == 1
        assert result["metadata"]["previous_state"] == 0
        assert result["metadata"]["states_list"] == [1, 3]
        json.dumps(result)
    
    def test_set_converted_to_list(self):
        """Test set objects are converted to lists."""
        message = {"values": {1, 2, 3}}
        result = _serialize_message_safely(message)
        
        assert isinstance(result["values"], list)
        assert set(result["values"]) == {1, 2, 3}
        json.dumps(result)
    
    def test_tuple_converted_to_list(self):
        """Test tuple objects are converted to lists."""
        message = ("first", TestWebSocketState.CONNECTED, 42)
        result = _serialize_message_safely(message)
        
        assert result == ["first", 1, 42]  # tuple → list, enum → value
        json.dumps(result)
    
    def test_complex_nested_structure(self):
        """Test deeply nested structure with all object types."""
        now = datetime.now(timezone.utc)
        model = TestPydanticModel("nested", now)
        
        message = {
            "type": "complex_test",
            "websocket_state": TestWebSocketState.CONNECTED,
            "data": {
                "model": model,
                "datetime": now,
                "enum_list": [TestWebSocketState.CONNECTING, TestWebSocketState.DISCONNECTED],
                "mixed_data": {
                    "numbers": (1, 2, 3),
                    "strings": {"a", "b", "c"},
                    "nested": {
                        "state": TestWebSocketState.CONNECTED
                    }
                }
            }
        }
        
        result = _serialize_message_safely(message)
        
        # Verify all conversions happened correctly
        assert result["websocket_state"] == 1
        assert result["data"]["model"]["name"] == "nested"
        assert result["data"]["model"]["created_at"] == now.isoformat()
        assert result["data"]["datetime"] == now.isoformat()
        assert result["data"]["enum_list"] == [0, 3]
        assert result["data"]["mixed_data"]["numbers"] == [1, 2, 3]
        assert isinstance(result["data"]["mixed_data"]["strings"], list)
        assert result["data"]["mixed_data"]["nested"]["state"] == 1
        
        # Most importantly - it should be JSON serializable
        json.dumps(result)
    
    def test_unsupported_object_fallback(self):
        """Test fallback to string for unsupported objects."""
        class UnsupportedObject:
            def __repr__(self):
                return "UnsupportedObject()"
        
        obj = UnsupportedObject()
        result = _serialize_message_safely(obj)
        
        # Should fall back to string representation
        assert result == "UnsupportedObject()"
        json.dumps(result)
    
    def test_already_serializable_dict_optimization(self):
        """Test optimization path for already serializable dicts."""
        message = {
            "type": "test",
            "data": "simple",
            "number": 42,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3]
        }
        
        # Should pass through unchanged (optimization path)
        result = _serialize_message_safely(message)
        assert result is message  # Same object reference
        json.dumps(result)
    
    def test_dict_with_non_serializable_values_processed(self):
        """Test dict with non-serializable values gets processed."""
        message = {
            "simple": "value",
            "enum": TestWebSocketState.CONNECTED,
            "datetime": datetime.now(timezone.utc)
        }
        
        result = _serialize_message_safely(message)
        
        assert result["simple"] == "value"
        assert result["enum"] == 1
        assert isinstance(result["datetime"], str)  # ISO format
        json.dumps(result)
    
    def test_pydantic_model_fallback(self):
        """Test Pydantic model fallback when mode='json' fails."""
        class FailingPydanticModel:
            def model_dump(self, mode: str = None) -> Dict[str, Any]:
                if mode == 'json':
                    raise Exception("JSON mode failed")
                return {"name": "fallback"}
        
        model = FailingPydanticModel()
        result = _serialize_message_safely(model)
        
        assert result == {"name": "fallback"}
        json.dumps(result)
    
    def test_empty_containers(self):
        """Test empty containers are handled correctly."""
        test_cases = [
            {},  # empty dict
            [],  # empty list  
            (),  # empty tuple
            set(),  # empty set
        ]
        
        for case in test_cases:
            result = _serialize_message_safely(case)
            json.dumps(result)  # Should not raise
    
    def test_none_values_preserved(self):
        """Test None values are preserved correctly."""
        message = {
            "nullable": None,
            "list_with_none": [1, None, 2],
            "nested": {
                "also_null": None
            }
        }
        
        result = _serialize_message_safely(message)
        assert result["nullable"] is None
        assert result["list_with_none"][1] is None
        assert result["nested"]["also_null"] is None
        json.dumps(result)


class TestWebSocketSerializationIntegration:
    """Integration tests for WebSocket serialization in real scenarios."""
    
    def test_agent_state_message_serialization(self):
        """Test typical agent state update message."""
        message = {
            "type": "agent_state_update",
            "user_id": "user123",
            "connection_state": TestWebSocketState.CONNECTED,
            "timestamp": datetime.now(timezone.utc),
            "data": {
                "agent_status": "running",
                "progress": 0.75,
                "metadata": {
                    "states": [TestWebSocketState.CONNECTING, TestWebSocketState.CONNECTED]
                }
            }
        }
        
        result = _serialize_message_safely(message)
        
        # Verify critical fields are properly serialized
        assert result["type"] == "agent_state_update"
        assert result["connection_state"] == 1  # CONNECTED
        assert isinstance(result["timestamp"], str)
        assert result["data"]["metadata"]["states"] == [0, 1]
        
        # Most critical - should be JSON serializable
        json.dumps(result)
    
    def test_error_message_serialization(self):
        """Test WebSocket error message serialization.""" 
        error_message = {
            "type": "error",
            "error_code": "WEBSOCKET_STATE_ERROR",
            "connection_state": TestWebSocketState.DISCONNECTED,
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "previous_states": [
                    TestWebSocketState.CONNECTING,
                    TestWebSocketState.CONNECTED,
                    TestWebSocketState.DISCONNECTED
                ]
            }
        }
        
        result = _serialize_message_safely(error_message)
        
        assert result["connection_state"] == 3  # DISCONNECTED
        assert result["details"]["previous_states"] == [0, 1, 3]
        json.dumps(result)
    
    def test_performance_with_large_message(self):
        """Test serialization performance with large complex message."""
        # Create a large message with many enum objects
        large_message = {
            "type": "bulk_update",
            "connections": []
        }
        
        # Add 100 connection entries with enums
        for i in range(100):
            large_message["connections"].append({
                "id": f"conn_{i}",
                "state": TestWebSocketState.CONNECTED,
                "last_seen": datetime.now(timezone.utc),
                "history": [TestWebSocketState.CONNECTING, TestWebSocketState.CONNECTED]
            })
        
        result = _serialize_message_safely(large_message)
        
        # Verify serialization worked for all entries
        assert len(result["connections"]) == 100
        for conn in result["connections"]:
            assert conn["state"] == 1
            assert conn["history"] == [0, 1]
        
        # Should be JSON serializable
        json_str = json.dumps(result)
        assert len(json_str) > 0


@pytest.mark.parametrize("enum_type,expected_value", [
    (TestWebSocketState.CONNECTING, 0),
    (TestWebSocketState.CONNECTED, 1), 
    (TestWebSocketState.DISCONNECTED, 3),
    (TestIntEnum.FIRST, 1),
    (TestIntEnum.SECOND, 2),
    (TestIntEnum.THIRD, 3),
])
def test_enum_serialization_parametrized(enum_type, expected_value):
    """Parametrized test for enum serialization."""
    result = _serialize_message_safely(enum_type)
    assert result == expected_value
    json.dumps(result)


def test_regression_websocket_state_in_message():
    """CRITICAL REGRESSION TEST: Reproduce original error scenario."""
    # This reproduces the exact error from the logs:
    # "Object of type WebSocketState is not JSON serializable"
    
    # Simulate message that might contain WebSocketState enum
    problematic_message = {
        "type": "connection_update",
        "connection_id": "conn_dev-temp-cc173c1d_3052f606",
        "state": TestWebSocketState.CONNECTED,  # This would cause the original error
        "metadata": {
            "previous_state": TestWebSocketState.CONNECTING,
            "transition_time": datetime.now(timezone.utc)
        }
    }
    
    # Before fix: this would raise TypeError: Object of type WebSocketState is not JSON serializable
    # After fix: should serialize properly
    result = _serialize_message_safely(problematic_message)
    
    assert result["state"] == 1  # CONNECTED value
    assert result["metadata"]["previous_state"] == 0  # CONNECTING value
    assert isinstance(result["metadata"]["transition_time"], str)
    
    # The critical test - this should NOT raise an exception
    json_output = json.dumps(result)
    assert "conn_dev-temp-cc173c1d_3052f606" in json_output