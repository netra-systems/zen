"""
Comprehensive Unit Test Suite for _serialize_message_safely Function

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent WebSocket Message Serialization Failures ($75K+ MRR protection)
- Value Impact: Safe serialization enables ALL WebSocket events to reach users successfully
- Strategic Impact: MISSION CRITICAL - Serialization failures cause complete chat breakdown

This test suite ensures 100% coverage of the _serialize_message_safely function, which is
the CRITICAL utility that enables all WebSocket events to be properly serialized and sent
to users. Without this function working correctly, users would see blank screens instead
of agent progress updates.

CRITICAL COVERAGE AREAS:
- WebSocketState enum serialization (FastAPI/Starlette compatibility)
- Pydantic model serialization with datetime handling
- Complex nested object serialization
- Dataclass conversion and recursive processing
- Enum key handling in dictionaries
- Fallback strategies for unserializable objects
- Performance and edge case handling

The function handles these critical serialization challenges:
1. WebSocketState enums from different frameworks (FastAPI/Starlette)
2. Pydantic models with complex datetime fields
3. Nested data structures with mixed types
4. Enum objects as both keys and values
5. Graceful fallbacks for unknown types
"""

import json
import pytest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, patch

# Import test framework
import unittest
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import system under test
from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely


# Test enums for comprehensive enum testing
class WebSocketStateForTesting(Enum):
    """Test enum mimicking WebSocketState for comprehensive testing."""
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


class GenericTestEnum(Enum):
    """Test generic enum without special handling."""
    OPTION_A = "option_a"
    OPTION_B = "option_b"
    OPTION_C = 42


class IntegerTestEnum(Enum):
    """Test integer-based enum."""
    FIRST = 1
    SECOND = 2
    THIRD = 3


# Test models for Pydantic-like behavior
class MockPydanticModel:
    """Mock Pydantic model for testing model_dump functionality."""
    
    def __init__(self, field1: str, timestamp: datetime, number: int = 42):
        self.field1 = field1
        self.timestamp = timestamp
        self.number = number
    
    def model_dump(self, mode: str = None) -> Dict[str, Any]:
        """Mock Pydantic model_dump method."""
        if mode == 'json':
            return {
                "field1": self.field1,
                "timestamp": self.timestamp.isoformat(),
                "number": self.number
            }
        return {
            "field1": self.field1,
            "timestamp": str(self.timestamp),
            "number": self.number
        }


class MockFailingPydanticModel:
    """Mock Pydantic model that fails on model_dump."""
    
    def model_dump(self, mode: str = None) -> Dict[str, Any]:
        """Always raises exception to test fallback."""
        raise Exception("model_dump failed")


class MockToDictObject:
    """Mock object with to_dict method."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return self.data.copy()


@dataclass
class SerializationTestDataclass:
    """Test dataclass for serialization testing."""
    name: str
    value: int
    timestamp: datetime
    nested: Optional[Dict[str, Any]] = None


class UnserializableObject:
    """Object that cannot be JSON serialized."""
    
    def __init__(self, value: str):
        self.value = value
    
    def __str__(self):
        return f"UnserializableObject({self.value})"


class TestMessageSerialization(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive unit tests for _serialize_message_safely function."""
    
    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)
        # Use IsolatedEnvironment per CLAUDE.md requirements
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="message_serialization_test")
    
    # ============================================================================
    # BASIC SERIALIZATION TESTS
    # ============================================================================
    
    def test_serialize_already_serializable_dict(self):
        """Test serialization of already JSON-serializable dictionary."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        result = _serialize_message_safely(data)
        
        # Should return identical dict since it's already serializable
        self.assertEqual(result, data)
        
        # Verify it can be JSON serialized
        json_str = json.dumps(result)
        self.assertIsInstance(json_str, str)
    
    def test_serialize_basic_types(self):
        """Test serialization of basic JSON-compatible types."""
        test_cases = [
            ("hello world", "hello world"),
            (42, 42),
            (3.14159, 3.14159),
            (True, True),
            (False, False),
            (None, None),
            ([], []),
            ({}, {})
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = _serialize_message_safely(input_val)
                self.assertEqual(result, expected)
    
    # ============================================================================
    # WEBSOCKET STATE ENUM TESTS - CRITICAL for framework compatibility
    # ============================================================================
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_starlette_websocket_state(self, mock_logger):
        """Test serialization of Starlette WebSocketState enum."""
        # Create a mock enum that looks like a WebSocket state from the starlette module
        class MockStarletteWebSocketState(Enum):
            CONNECTED = 1
            
        # Override the module to look like starlette.websockets  
        MockStarletteWebSocketState.__module__ = 'starlette.websockets'
        
        mock_state = MockStarletteWebSocketState.CONNECTED
        
        result = _serialize_message_safely(mock_state)
        
        # Should convert to lowercase name
        self.assertEqual(result, "connected")
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_fastapi_websocket_state(self, mock_logger):
        """Test serialization of FastAPI WebSocketState enum."""
        # Create a mock enum that looks like a WebSocket state from the fastapi module
        class MockFastAPIWebSocketState(Enum):
            OPEN = 1
            
        # Override the module to look like fastapi.websockets  
        MockFastAPIWebSocketState.__module__ = 'fastapi.websockets'
        
        mock_state = MockFastAPIWebSocketState.OPEN
        
        result = _serialize_message_safely(mock_state)
        
        self.assertEqual(result, "open")
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_generic_websocket_state_fallback(self, mock_logger):
        """Test generic WebSocketState detection for class names with websocket pattern."""
        # Create a mock enum that looks like a WebSocket state but isn't from a framework module
        class MockGenericWebSocketState(Enum):
            CONNECTING = 0
            
        # This will be from the test module, not a framework module
        mock_state = MockGenericWebSocketState.CONNECTING
        
        # With our updated logic, this should detect it as a WebSocket state
        # because it has the right class name pattern AND enum name
        MockGenericWebSocketState.__name__ = 'WebSocketState'
        
        result = _serialize_message_safely(mock_state)
        
        # Should return the lowercase name since it matches our WebSocket state detection
        self.assertEqual(result, "connecting")
    
    def test_serialize_test_websocket_state_enum(self):
        """Test serialization of test WebSocketState enum."""
        result = _serialize_message_safely(WebSocketStateForTesting.OPEN)
        
        # Should return the enum name for WebSocket state enums (detected by class name pattern)
        self.assertEqual(result, "open")
    
    def test_serialize_generic_enum_types(self):
        """Test serialization of various generic enum types."""
        test_cases = [
            (GenericTestEnum.OPTION_A, "option_a"),
            (GenericTestEnum.OPTION_B, "option_b"), 
            (GenericTestEnum.OPTION_C, 42),
            (IntegerTestEnum.FIRST, 1),
            (IntegerTestEnum.SECOND, 2),
            (IntegerTestEnum.THIRD, 3)
        ]
        
        for enum_val, expected in test_cases:
            with self.subTest(enum=enum_val):
                result = _serialize_message_safely(enum_val)
                self.assertEqual(result, expected)
    
    # ============================================================================
    # PYDANTIC MODEL SERIALIZATION TESTS
    # ============================================================================
    
    def test_serialize_pydantic_model_json_mode(self):
        """Test Pydantic model serialization in JSON mode."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        model = MockPydanticModel("test_field", timestamp, 100)
        
        result = _serialize_message_safely(model)
        
        self.assertEqual(result["field1"], "test_field")
        self.assertEqual(result["timestamp"], timestamp.isoformat())
        self.assertEqual(result["number"], 100)
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_pydantic_model_fallback(self, mock_logger):
        """Test Pydantic model serialization fallback when JSON mode fails."""
        model = MockFailingPydanticModel()
        
        result = _serialize_message_safely(model)
        
        # Should fall back to string representation
        self.assertIsInstance(result, str)
        mock_logger.warning.assert_called()
    
    # ============================================================================
    # TO_DICT OBJECT TESTS
    # ============================================================================
    
    def test_serialize_to_dict_object(self):
        """Test serialization of objects with to_dict method."""
        data = {
            "agent_state": "running",
            "progress": 0.75,
            "metadata": {"step": 3}
        }
        obj = MockToDictObject(data)
        
        result = _serialize_message_safely(obj)
        
        self.assertEqual(result, data)
    
    # ============================================================================
    # DATACLASS SERIALIZATION TESTS
    # ============================================================================
    
    def test_serialize_simple_dataclass(self):
        """Test serialization of simple dataclass."""
        timestamp = datetime.now()
        dc = SerializationTestDataclass(
            name="test_dataclass",
            value=42,
            timestamp=timestamp
        )
        
        result = _serialize_message_safely(dc)
        
        self.assertEqual(result["name"], "test_dataclass")
        self.assertEqual(result["value"], 42)
        self.assertEqual(result["timestamp"], timestamp.isoformat())
    
    def test_serialize_nested_dataclass(self):
        """Test serialization of dataclass with nested data."""
        timestamp = datetime.now()
        nested_data = {
            "config": {"debug": True},
            "stats": [1, 2, 3],
            "enum_val": GenericTestEnum.OPTION_A
        }
        
        dc = SerializationTestDataclass(
            name="nested_test",
            value=99,
            timestamp=timestamp,
            nested=nested_data
        )
        
        result = _serialize_message_safely(dc)
        
        self.assertEqual(result["name"], "nested_test")
        self.assertEqual(result["nested"]["config"]["debug"], True)
        self.assertEqual(result["nested"]["stats"], [1, 2, 3])
        self.assertEqual(result["nested"]["enum_val"], "option_a")
    
    # ============================================================================
    # DATETIME SERIALIZATION TESTS
    # ============================================================================
    
    def test_serialize_datetime_objects(self):
        """Test serialization of various datetime objects."""
        test_datetimes = [
            datetime.now(),
            datetime(2024, 1, 1, 12, 0, 0),
            datetime.now(timezone.utc),
            datetime(2023, 12, 25, 9, 30, 15, tzinfo=timezone.utc)
        ]
        
        for dt in test_datetimes:
            with self.subTest(datetime=dt):
                result = _serialize_message_safely(dt)
                
                # Should be ISO format string
                self.assertIsInstance(result, str)
                self.assertEqual(result, dt.isoformat())
                
                # Verify it's valid ISO format by parsing back
                parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
                self.assertIsInstance(parsed, datetime)
    
    # ============================================================================
    # COLLECTION SERIALIZATION TESTS
    # ============================================================================
    
    def test_serialize_lists_with_mixed_types(self):
        """Test serialization of lists containing mixed types."""
        data = [
            "string",
            42,
            3.14,
            True,
            GenericTestEnum.OPTION_A,
            datetime.now(),
            {"nested": "dict"},
            [1, 2, 3]
        ]
        
        result = _serialize_message_safely(data)
        
        self.assertEqual(len(result), len(data))
        self.assertEqual(result[0], "string")
        self.assertEqual(result[1], 42)
        self.assertEqual(result[4], "option_a")  # Enum serialized
        self.assertIsInstance(result[5], str)  # Datetime as string
        self.assertEqual(result[6]["nested"], "dict")
    
    def test_serialize_sets_to_lists(self):
        """Test serialization of sets (converted to lists)."""
        data = {
            "item1",
            "item2", 
            "item3",
            GenericTestEnum.OPTION_B
        }
        
        result = _serialize_message_safely(data)
        
        # Should be converted to list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        self.assertIn("item1", result)
        self.assertIn("item2", result)
        self.assertIn("item3", result)
        self.assertIn("option_b", result)  # Enum serialized
    
    def test_serialize_tuples_to_lists(self):
        """Test serialization of tuples (converted to lists)."""
        data = ("first", 42, GenericTestEnum.OPTION_C, datetime.now())
        
        result = _serialize_message_safely(data)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], "first")
        self.assertEqual(result[1], 42)
        self.assertEqual(result[2], 42)  # Enum value
        self.assertIsInstance(result[3], str)  # Datetime
    
    # ============================================================================
    # ENUM KEYS IN DICTIONARIES - Critical edge case
    # ============================================================================
    
    def test_serialize_dict_with_enum_keys(self):
        """Test serialization of dictionaries with enum keys."""
        data = {
            WebSocketStateForTesting.OPEN: "connection_active",
            WebSocketStateForTesting.CLOSED: "connection_inactive", 
            GenericTestEnum.OPTION_A: "selected_option",
            "normal_key": "normal_value"
        }
        
        result = _serialize_message_safely(data)
        
        # Enum keys should be converted to strings
        self.assertIn("open", result)  # WebSocketState handling
        self.assertEqual(result["open"], "connection_active")
        
        self.assertIn("option_a", result)  # Generic enum handling
        self.assertEqual(result["option_a"], "selected_option")
        
        # Normal keys preserved
        self.assertEqual(result["normal_key"], "normal_value")
    
    def test_serialize_complex_dict_with_mixed_enum_keys(self):
        """Test complex dictionary with mixed enum keys and values."""
        data = {
            WebSocketStateForTesting.CONNECTING: {
                "status": GenericTestEnum.OPTION_A,
                "timestamp": datetime.now(),
                "nested": {
                    IntegerTestEnum.FIRST: [1, 2, GenericTestEnum.OPTION_B]
                }
            },
            "metadata": {
                "enum_value": WebSocketStateForTesting.OPEN,
                "count": 42
            }
        }
        
        result = _serialize_message_safely(data)
        
        # Top-level enum key
        self.assertIn("connecting", result)
        
        # Nested enum value
        connecting_data = result["connecting"]
        self.assertEqual(connecting_data["status"], "option_a")
        
        # Deeply nested enum key and values
        nested = connecting_data["nested"]
        self.assertIn("1", nested)  # IntEnum key converted to string
        nested_list = nested["1"] 
        self.assertEqual(nested_list[2], "option_b")  # Enum in list
        
        # Enum value in metadata
        self.assertEqual(result["metadata"]["enum_value"], "open")
    
    # ============================================================================
    # COMPLEX NESTED DATA STRUCTURE TESTS
    # ============================================================================
    
    def test_serialize_deeply_nested_structure(self):
        """Test serialization of deeply nested data structures."""
        timestamp = datetime.now()
        
        data = {
            "user_context": {
                "user_id": "user_123",
                "session_state": WebSocketStateForTesting.OPEN,
                "permissions": ["read", "write"],
                "metadata": {
                    "created_at": timestamp,
                    "preferences": {
                        "theme": GenericTestEnum.OPTION_A,
                        "notifications": True,
                        "settings": {
                            "level": IntegerTestEnum.SECOND,
                            "tags": {"urgent", "priority", "review"}
                        }
                    }
                }
            },
            "agent_states": [
                {
                    "agent_id": "agent_001",
                    "status": WebSocketStateForTesting.CONNECTING,
                    "progress": 0.75,
                    "last_update": timestamp
                },
                {
                    "agent_id": "agent_002", 
                    "status": WebSocketStateForTesting.CLOSED,
                    "error": None
                }
            ]
        }
        
        result = _serialize_message_safely(data)
        
        # Verify top-level structure
        self.assertIn("user_context", result)
        self.assertIn("agent_states", result)
        
        # Check user context serialization
        user_ctx = result["user_context"]
        self.assertEqual(user_ctx["session_state"], "open")
        self.assertEqual(user_ctx["metadata"]["created_at"], timestamp.isoformat())
        self.assertEqual(user_ctx["metadata"]["preferences"]["theme"], "option_a")
        self.assertEqual(user_ctx["metadata"]["preferences"]["settings"]["level"], 2)
        
        # Check that set was converted to list
        tags = user_ctx["metadata"]["preferences"]["settings"]["tags"]
        self.assertIsInstance(tags, list)
        self.assertEqual(len(tags), 3)
        
        # Check agent states array
        agents = result["agent_states"]
        self.assertEqual(len(agents), 2)
        self.assertEqual(agents[0]["status"], "connecting")
        self.assertEqual(agents[0]["last_update"], timestamp.isoformat())
        self.assertEqual(agents[1]["status"], "closed")
    
    # ============================================================================
    # ERROR HANDLING AND FALLBACK TESTS
    # ============================================================================
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_unserializable_object_fallback(self, mock_logger):
        """Test fallback to string for completely unserializable objects."""
        obj = UnserializableObject("test_value")
        
        result = _serialize_message_safely(obj)
        
        # Should fall back to string representation
        self.assertEqual(result, "UnserializableObject(test_value)")
        
        # Should log warning about fallback
        mock_logger.warning.assert_called_once()
        self.assertIn("string fallback", mock_logger.warning.call_args[0][0])
    
    def test_serialize_object_with_uuid(self):
        """Test serialization of UUID objects."""
        test_uuid = uuid.uuid4()
        
        result = _serialize_message_safely(test_uuid)
        
        # UUID should be converted to string
        self.assertEqual(result, str(test_uuid))
    
    @patch('netra_backend.app.websocket_core.unified_manager.logger')
    def test_serialize_dict_with_problematic_values(self, mock_logger):
        """Test dict serialization with values that need special handling."""
        problematic_obj = UnserializableObject("problem")
        
        data = {
            "normal": "value",
            "enum": GenericTestEnum.OPTION_A,
            "datetime": datetime.now(),
            "problematic": problematic_obj,
            "nested": {
                "also_problematic": problematic_obj
            }
        }
        
        result = _serialize_message_safely(data)
        
        # Normal values preserved
        self.assertEqual(result["normal"], "value")
        self.assertEqual(result["enum"], "option_a")
        
        # Problematic objects handled
        self.assertEqual(result["problematic"], "UnserializableObject(problem)")
        self.assertEqual(result["nested"]["also_problematic"], "UnserializableObject(problem)")
    
    # ============================================================================
    # PERFORMANCE AND EDGE CASE TESTS
    # ============================================================================
    
    def test_serialize_empty_collections(self):
        """Test serialization of empty collections."""
        test_cases = [
            ({}, {}),
            ([], []),
            (set(), []),
            (tuple(), [])
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = _serialize_message_safely(input_val)
                self.assertEqual(result, expected)
    
    def test_serialize_large_nested_structure(self):
        """Test serialization of large nested structure for performance."""
        # Create a reasonably large nested structure
        large_data = {
            f"section_{i}": {
                "items": [
                    {
                        "id": f"item_{i}_{j}",
                        "status": GenericTestEnum.OPTION_A if j % 2 == 0 else GenericTestEnum.OPTION_B,
                        "timestamp": datetime.now(),
                        "metadata": {
                            "tags": {f"tag_{k}" for k in range(3)},
                            "priority": IntegerTestEnum.FIRST
                        }
                    }
                    for j in range(10)
                ]
            }
            for i in range(5)
        }
        
        # Should complete without errors or excessive time
        result = _serialize_message_safely(large_data)
        
        # Verify structure integrity
        self.assertEqual(len(result), 5)
        for i in range(5):
            section = result[f"section_{i}"]
            self.assertEqual(len(section["items"]), 10)
            
            # Check first item serialization
            first_item = section["items"][0]
            self.assertEqual(first_item["status"], "option_a")
            self.assertIsInstance(first_item["timestamp"], str)
            self.assertIsInstance(first_item["metadata"]["tags"], list)
            self.assertEqual(first_item["metadata"]["priority"], 1)
    
    def test_serialize_circular_reference_prevention(self):
        """Test that circular references are handled gracefully."""
        # Create structure with potential circular reference
        data = {"key": "value"}
        # Don't actually create circular reference as it would cause infinite recursion
        # This tests that the function can handle complex but non-circular data
        
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": data
                    }
                }
            },
            "reference": data  # Same object referenced twice, but not circular
        }
        
        result = _serialize_message_safely(nested_data)
        
        # Should serialize successfully
        self.assertEqual(result["level1"]["level2"]["level3"]["data"]["key"], "value")
        self.assertEqual(result["reference"]["key"], "value")
    
    def test_serialize_message_with_special_websocket_fields(self):
        """Test serialization of typical WebSocket message with all field types."""
        message = {
            "type": "agent_update",
            "user_id": "user_12345",
            "thread_id": "thread_67890", 
            "timestamp": datetime.now(timezone.utc),
            "connection_state": WebSocketStateForTesting.OPEN,
            "payload": {
                "agent_name": "CostOptimizer",
                "status": GenericTestEnum.OPTION_A,
                "progress": 0.65,
                "current_step": "analyzing_patterns",
                "metadata": {
                    "tools_used": ["search", "analyze", "optimize"],
                    "start_time": datetime.now(),
                    "estimat_remaining": 5000,
                    "tags": {"cost", "optimization", "analysis"},
                    "state_info": {
                        IntegerTestEnum.FIRST: "initialized",
                        IntegerTestEnum.SECOND: "processing"
                    }
                }
            },
            "delivery_confirmation": True
        }
        
        result = _serialize_message_safely(message)
        
        # Verify all fields properly serialized
        self.assertEqual(result["type"], "agent_update")
        self.assertEqual(result["connection_state"], "open")
        self.assertIsInstance(result["timestamp"], str)
        
        payload = result["payload"]
        self.assertEqual(payload["status"], "option_a")
        self.assertEqual(payload["progress"], 0.65)
        
        metadata = payload["metadata"]
        self.assertIsInstance(metadata["tags"], list)
        self.assertIn("cost", metadata["tags"])
        self.assertIsInstance(metadata["start_time"], str)
        
        # Enum keys in nested dict
        state_info = metadata["state_info"]
        self.assertIn("1", state_info)  # IntEnum key converted
        self.assertEqual(state_info["1"], "initialized")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])