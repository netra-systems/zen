"""Type Consistency Validation Tests.

Tests general type consistency patterns across the full stack including
datetime serialization, enum handling, null vs undefined, and union types.
"""

import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

# Import schemas for testing
from app.schemas.registry import Message, MessageType, StartAgentPayload
from app.schemas.Tool import ToolCompleted, ToolStatus
from app.schemas.Request import RequestModel
from app.schemas.registry import WebSocketMessageType

# Import test data
from app.tests.frontend_data_mocks import FrontendDataMocks


class TestDateTimeConsistency:
    """Test datetime serialization consistency across the stack."""
    
    def test_datetime_iso_serialization(self) -> None:
        """Test datetime serialization to ISO format."""
        now = datetime.now(timezone.utc)
        
        message = Message(
            id="msg123",
            type=MessageType.USER,
            content="Test message",
            timestamp=now,
            metadata={}
        )
        
        json_data = message.model_dump_json()
        parsed = json.loads(json_data)
        
        assert isinstance(parsed["timestamp"], str)
        assert "T" in parsed["timestamp"]
    
    def test_datetime_roundtrip_consistency(self) -> None:
        """Test datetime roundtrip serialization consistency."""
        original_time = datetime.now(timezone.utc)
        
        message = Message(
            id="msg123",
            type=MessageType.USER,
            content="Test",
            timestamp=original_time,
            metadata={}
        )
        
        # Serialize and parse back
        json_str = message.model_dump_json()
        parsed_data = json.loads(json_str)
        
        # Verify ISO format structure
        timestamp_str = parsed_data["timestamp"]
        assert "T" in timestamp_str
        assert timestamp_str.endswith("Z") or "+" in timestamp_str
    
    def test_datetime_in_metadata(self) -> None:
        """Test datetime handling in metadata objects."""
        metadata_with_time = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_start": "2025-01-01T10:00:00Z"
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="System message",
            metadata=metadata_with_time
        )
        
        json_data = message.model_dump()
        assert "created_at" in json_data["metadata"]
        assert "T" in json_data["metadata"]["created_at"]


class TestEnumSerialization:
    """Test enum serialization to string values."""
    
    def test_tool_status_enum_serialization(self) -> None:
        """Test ToolStatus enum serialization."""
        status = ToolStatus.SUCCESS
        
        assert status.value == "success"
        
        tool = ToolCompleted(
            tool_name="test_tool",
            tool_output={},
            run_id="run123",
            status=status
        )
        
        json_data = tool.model_dump()
        assert json_data["status"] == "success"
    
    def test_message_type_enum_serialization(self) -> None:
        """Test MessageType enum serialization."""
        msg_type = MessageType.AGENT
        
        assert msg_type.value == "agent"
        
        message = Message(
            id="msg123",
            type=msg_type,
            content="Agent message",
            metadata={}
        )
        
        json_data = message.model_dump()
        assert json_data["type"] == "agent"
    
    def test_websocket_message_type_serialization(self) -> None:
        """Test WebSocketMessageType enum serialization."""
        msg_type = WebSocketMessageType.START_AGENT
        
        assert msg_type.value == "start_agent"
        
        # Test in actual usage context
        frontend_data = FrontendDataMocks.start_agent_payload()
        enum_value = WebSocketMessageType(frontend_data["type"])
        assert enum_value.value == "start_agent"
    
    def test_all_enum_values_serialize_to_strings(self) -> None:
        """Test all enum values serialize to strings."""
        enums_to_test = [
            (ToolStatus.SUCCESS, "success"),
            (ToolStatus.ERROR, "error"),
            (MessageType.USER, "user"),
            (MessageType.AGENT, "agent"),
            (WebSocketMessageType.PING, "ping")
        ]
        
        for enum_val, expected_str in enums_to_test:
            assert enum_val.value == expected_str


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
        
        # Serialize and verify structure preservation
        json_str = json.dumps(complex_result)
        parsed = json.loads(json_str)
        
        assert len(parsed["recommendations"]) == 2
        assert len(parsed["metrics_history"][0]) == 3
        assert "performance" in parsed["recommendations"][0]["tags"]


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
    
    def test_mixed_content_types(self) -> None:
        """Test multiple content types in sequence."""
        messages = [
            Message(id="1", type=MessageType.USER, content="Text", metadata={}),
            Message(id="2", type=MessageType.AGENT, content={"data": "object"}, metadata={}),
            Message(id="3", type=MessageType.SYSTEM, content="More text", metadata={})
        ]
        
        for msg in messages:
            json_data = msg.model_dump()
            assert "content" in json_data
            
            # Content can be string or dict
            content_type = type(json_data["content"])
            assert content_type in [str, dict]


class TestComplexTypeValidation:
    """Test complex nested type validation."""
    
    def test_deeply_nested_structure_consistency(self) -> None:
        """Test deeply nested structure type consistency."""
        complex_data = FrontendDataMocks.complex_websocket_payload()
        
        payload = StartAgentPayload(**complex_data["payload"])
        json_data = payload.model_dump()
        
        # Verify deep nesting preserved
        session_data = json_data["context"]["session"]
        assert session_data["id"] == "session123"
        assert session_data["metadata"]["client"]["name"] == "web"
    
    def test_mixed_type_preservation(self) -> None:
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])