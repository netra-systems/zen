"""Null, Array, and Union Type Consistency Tests.

Tests null vs undefined handling, array type consistency, and union type
validation patterns across the frontend-backend interface.
"""

import json
import pytest
from typing import Dict, Any

# Import schemas for testing
from app.schemas.registry import Message, MessageType, StartAgentPayload
from app.schemas.Request import RequestModel

# Import test data
from app.tests.frontend_data_mocks import FrontendDataMocks


class TestNullUndefinedHandling:
    """Test handling of null vs undefined fields."""
    
    def test_explicit_none_handling(self) -> None:
        """Test explicit None value handling."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None
        )
        
        json_data = payload.model_dump()
        assert "thread_id" in json_data
        assert json_data["thread_id"] is None
    
    def test_exclude_none_behavior(self) -> None:
        """Test exclude_none serialization behavior."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None
        )
        
        json_data_with_none = payload.model_dump()
        json_data_no_none = payload.model_dump(exclude_none=True)
        
        assert "thread_id" in json_data_with_none
        assert "thread_id" not in json_data_no_none
    
    def test_optional_field_omission(self) -> None:
        """Test omitted optional fields."""
        minimal_data = FrontendDataMocks.minimal_start_agent_payload()
        
        payload = StartAgentPayload(**minimal_data)
        json_data = payload.model_dump(exclude_none=True)
        
        assert "query" in json_data
        assert "user_id" in json_data
        assert "thread_id" not in json_data
        assert "context" not in json_data
    
    def test_nested_none_handling(self) -> None:
        """Test None handling in nested structures."""
        workloads_data = [{
            "run_id": "run123",
            "query": "test",
            "data_source": {
                "source_table": "logs",
                "filters": None
            },
            "time_range": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z"
            }
        }]
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        json_data = request.model_dump()
        assert json_data["workloads"][0]["data_source"]["filters"] is None
    
    def test_partial_object_with_nulls(self) -> None:
        """Test partial objects with explicit null fields."""
        partial_data = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": None,
            "context": {
                "session_id": "session123",
                "metadata": None
            }
        }
        
        payload = StartAgentPayload(**partial_data)
        json_data = payload.model_dump()
        
        assert json_data["thread_id"] is None
        assert json_data["context"]["metadata"] is None
    
    def test_conditional_null_exclusion(self) -> None:
        """Test conditional null field exclusion."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None,
            context=None
        )
        
        # Include nulls
        with_nulls = payload.model_dump(exclude_none=False)
        assert with_nulls["thread_id"] is None
        assert with_nulls["context"] is None
        
        # Exclude nulls
        without_nulls = payload.model_dump(exclude_none=True)
        assert "thread_id" not in without_nulls
        assert "context" not in without_nulls


class TestArrayTypeConsistency:
    """Test array type handling consistency."""
    
    def test_simple_array_serialization(self) -> None:
        """Test simple array serialization."""
        workloads_data = FrontendDataMocks.workloads_array_data()
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        json_data = request.model_dump()
        assert isinstance(json_data["workloads"], list)
        assert len(json_data["workloads"]) == 3
    
    def test_empty_array_handling(self) -> None:
        """Test empty array handling."""
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=[]
        )
        
        json_data = request.model_dump()
        assert isinstance(json_data["workloads"], list)
        assert len(json_data["workloads"]) == 0
    
    def test_nested_array_structures(self) -> None:
        """Test nested array structures."""
        complex_result = {
            "recommendations": [
                {"action": "scale_up", "tags": ["performance", "cost"]},
                {"action": "optimize", "tags": ["efficiency"]}
            ],
            "metrics_history": [
                [10, 20, 30],  # CPU usage over time
                [5, 15, 25]    # Memory usage over time
            ]
        }
        
        json_str = json.dumps(complex_result)
        parsed = json.loads(json_str)
        
        assert len(parsed["recommendations"]) == 2
        assert len(parsed["metrics_history"][0]) == 3
        assert "performance" in parsed["recommendations"][0]["tags"]
    
    def test_array_of_mixed_types(self) -> None:
        """Test arrays containing mixed types."""
        mixed_metadata = {
            "values": ["string", 42, True, None, {"key": "value"}],
            "nested_arrays": [[1, 2], ["a", "b"], [True, False]]
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Mixed array test",
            metadata=mixed_metadata
        )
        
        json_data = message.model_dump()
        values = json_data["metadata"]["values"]
        
        assert values[0] == "string"
        assert values[1] == 42
        assert values[2] is True
        assert values[3] is None
        assert isinstance(values[4], dict)
    
    def test_array_bounds_and_indexing(self) -> None:
        """Test array bounds and indexing consistency."""
        large_array = [f"item_{i}" for i in range(100)]
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Large array test",
            metadata={"items": large_array}
        )
        
        json_data = message.model_dump()
        items = json_data["metadata"]["items"]
        
        assert len(items) == 100
        assert items[0] == "item_0"
        assert items[99] == "item_99"


class TestUnionTypeHandling:
    """Test union type handling in schemas."""
    
    def test_string_content_message(self) -> None:
        """Test Message with string content."""
        text_message = Message(
            id="msg1",
            type=MessageType.USER,
            content="Simple text",
            metadata={}
        )
        
        json_data = text_message.model_dump()
        assert isinstance(json_data["content"], str)
        assert json_data["content"] == "Simple text"
    
    def test_complex_content_message(self) -> None:
        """Test Message with complex content structure."""
        complex_content = {
            "text": "Complex message",
            "attachments": ["file1.pdf", "file2.xlsx"],
            "formatting": {"bold": True, "color": "blue"}
        }
        
        complex_message = Message(
            id="msg2",
            type=MessageType.AGENT,
            content=complex_content,
            metadata={}
        )
        
        json_data = complex_message.model_dump()
        assert isinstance(json_data["content"], dict)
        assert json_data["content"]["text"] == "Complex message"
        assert len(json_data["content"]["attachments"]) == 2
    
    def test_mixed_content_types_sequence(self) -> None:
        """Test multiple content types in sequence."""
        messages = [
            Message(id="1", type=MessageType.USER, content="Text", metadata={}),
            Message(id="2", type=MessageType.AGENT, content={"data": "object"}, metadata={}),
            Message(id="3", type=MessageType.SYSTEM, content="More text", metadata={})
        ]
        
        for msg in messages:
            json_data = msg.model_dump()
            assert "content" in json_data
            
            content_type = type(json_data["content"])
            assert content_type in [str, dict]
    
    def test_numeric_content_types(self) -> None:
        """Test numeric content in union types."""
        numeric_message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content=42,  # Integer content
            metadata={}
        )
        
        json_data = numeric_message.model_dump()
        assert isinstance(json_data["content"], int)
        assert json_data["content"] == 42
    
    def test_boolean_content_types(self) -> None:
        """Test boolean content in union types."""
        boolean_message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content=True,  # Boolean content
            metadata={}
        )
        
        json_data = boolean_message.model_dump()
        assert isinstance(json_data["content"], bool)
        assert json_data["content"] is True


class TestComplexTypeValidation:
    """Test complex nested type validation scenarios."""
    
    def test_deeply_nested_structure_consistency(self) -> None:
        """Test deeply nested structure type consistency."""
        complex_data = FrontendDataMocks.complex_websocket_payload()
        
        payload = StartAgentPayload(**complex_data["payload"])
        json_data = payload.model_dump()
        
        session_data = json_data["context"]["session"]
        assert session_data["id"] == "session123"
        assert session_data["metadata"]["client"]["name"] == "web"
    
    def test_mixed_type_preservation_in_metadata(self) -> None:
        """Test mixed type preservation in complex objects."""
        mixed_metadata = {
            "string_field": "text",
            "number_field": 42,
            "boolean_field": True,
            "null_field": None,
            "array_field": [1, "two", 3.0],
            "object_field": {"nested": "value"}
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Test",
            metadata=mixed_metadata
        )
        
        json_data = message.model_dump()
        metadata = json_data["metadata"]
        
        assert isinstance(metadata["string_field"], str)
        assert isinstance(metadata["number_field"], int)
        assert isinstance(metadata["boolean_field"], bool)
        assert metadata["null_field"] is None
        assert isinstance(metadata["array_field"], list)
        assert isinstance(metadata["object_field"], dict)
    
    def test_circular_reference_prevention(self) -> None:
        """Test prevention of circular references in serialization."""
        # Create non-circular but deeply nested structure
        deep_structure = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": "deep_value",
                        "array": [1, 2, 3]
                    }
                }
            }
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Deep structure test",
            metadata=deep_structure
        )
        
        json_data = message.model_dump()
        deep_value = json_data["metadata"]["level1"]["level2"]["level3"]["data"]
        assert deep_value == "deep_value"
    
    def test_large_object_serialization(self) -> None:
        """Test serialization of large complex objects."""
        large_data = {
            "arrays": {
                f"array_{i}": [j for j in range(10)]
                for i in range(5)
            },
            "objects": {
                f"obj_{i}": {"id": i, "data": f"value_{i}"}
                for i in range(10)
            },
            "mixed": [i if i % 2 == 0 else f"string_{i}" for i in range(20)]
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Large object test",
            metadata=large_data
        )
        
        json_data = message.model_dump()
        assert len(json_data["metadata"]["arrays"]) == 5
        assert len(json_data["metadata"]["objects"]) == 10
        assert len(json_data["metadata"]["mixed"]) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])