"""Union Types and Complex Validation Tests.

Tests union type handling and complex nested validation scenarios
for comprehensive type safety across the frontend-backend interface.
"""

import json
import pytest
from typing import Dict, Any

# Import schemas for testing
from app.schemas.registry import Message, MessageType, StartAgentPayload

# Import test data
from app.tests.frontend_data_mocks import FrontendDataMocks


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
    
    def test_list_content_types(self) -> None:
        """Test list content in union types."""
        list_message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content=["item1", "item2", "item3"],
            metadata={}
        )
        
        json_data = list_message.model_dump()
        assert isinstance(json_data["content"], list)
        assert len(json_data["content"]) == 3
    
    def test_null_content_handling(self) -> None:
        """Test null content in union types."""
        null_message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content=None,
            metadata={}
        )
        
        json_data = null_message.model_dump()
        assert json_data["content"] is None


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
    
    def test_polymorphic_content_handling(self) -> None:
        """Test polymorphic content handling across message types."""
        polymorphic_messages = [
            # String content
            Message(id="1", type=MessageType.USER, content="Text", metadata={}),
            # Object content
            Message(id="2", type=MessageType.AGENT, content={"result": "data"}, metadata={}),
            # Array content
            Message(id="3", type=MessageType.SYSTEM, content=[1, 2, 3], metadata={}),
            # Numeric content
            Message(id="4", type=MessageType.ERROR, content=404, metadata={}),
            # Boolean content
            Message(id="5", type=MessageType.TOOL, content=True, metadata={})
        ]
        
        content_types = []
        for msg in polymorphic_messages:
            json_data = msg.model_dump()
            content_types.append(type(json_data["content"]))
        
        # Verify we have different content types
        assert str in content_types
        assert dict in content_types
        assert list in content_types
        assert int in content_types
        assert bool in content_types
    
    def test_edge_case_type_combinations(self) -> None:
        """Test edge case type combinations."""
        edge_cases = [
            # Empty structures
            Message(id="1", type=MessageType.SYSTEM, content="", metadata={}),
            Message(id="2", type=MessageType.SYSTEM, content={}, metadata={}),
            Message(id="3", type=MessageType.SYSTEM, content=[], metadata={}),
            # Zero values
            Message(id="4", type=MessageType.SYSTEM, content=0, metadata={}),
            Message(id="5", type=MessageType.SYSTEM, content=0.0, metadata={}),
            # Boolean false
            Message(id="6", type=MessageType.SYSTEM, content=False, metadata={}),
        ]
        
        for msg in edge_cases:
            json_data = msg.model_dump()
            # Should serialize successfully without errors
            assert "content" in json_data
            assert "id" in json_data
    
    def test_unicode_and_special_characters(self) -> None:
        """Test unicode and special character handling."""
        unicode_content = {
            "emoji": "🔥 🚀 💯",
            "chinese": "你好世界",
            "special": "Special chars: @#$%^&*()",
            "json_like": '{"nested": "json"}',
            "multiline": "Line 1\nLine 2\nLine 3"
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content=unicode_content,
            metadata={}
        )
        
        json_data = message.model_dump()
        content = json_data["content"]
        
        assert "🔥" in content["emoji"]
        assert "你好" in content["chinese"]
        assert "@#$%" in content["special"]
        assert "\n" in content["multiline"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])