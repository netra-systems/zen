"""DateTime and Enum Consistency Tests.

Tests datetime serialization and enum value consistency patterns
across the full stack for frontend-backend communication.
"""

import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

# Import schemas for testing
from app.schemas.registry import Message, MessageType, WebSocketMessageType
from app.schemas.Tool import ToolCompleted, ToolStatus

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
        
        json_str = message.model_dump_json()
        parsed_data = json.loads(json_str)
        
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
    
    def test_datetime_timezone_handling(self) -> None:
        """Test datetime timezone handling consistency."""
        utc_time = datetime.now(timezone.utc)
        
        message = Message(
            id="msg123",
            type=MessageType.USER,
            content="Timezone test",
            timestamp=utc_time,
            metadata={}
        )
        
        json_data = message.model_dump()
        # Should preserve timezone information in ISO format
        timestamp_str = str(json_data["timestamp"])
        assert "T" in timestamp_str
    
    def test_datetime_formatting_consistency(self) -> None:
        """Test consistent datetime formatting across messages."""
        times = [
            datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 6, 15, 14, 30, 45, tzinfo=timezone.utc),
            datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        ]
        
        messages = [
            Message(
                id=f"msg{i}",
                type=MessageType.SYSTEM,
                content=f"Test {i}",
                timestamp=time,
                metadata={}
            )
            for i, time in enumerate(times)
        ]
        
        for msg in messages:
            json_data = msg.model_dump()
            timestamp = json_data["timestamp"]
            assert isinstance(timestamp, str)
            assert "T" in timestamp


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
        
        frontend_data = FrontendDataMocks.start_agent_payload()
        enum_value = WebSocketMessageType(frontend_data["type"])
        assert enum_value.value == "start_agent"
    
    def test_all_tool_status_values(self) -> None:
        """Test all ToolStatus enum values serialize correctly."""
        status_mappings = [
            (ToolStatus.SUCCESS, "success"),
            (ToolStatus.ERROR, "error"),
            (ToolStatus.IN_PROGRESS, "in_progress")
        ]
        
        for enum_val, expected_str in status_mappings:
            assert enum_val.value == expected_str
    
    def test_all_message_type_values(self) -> None:
        """Test all MessageType enum values serialize correctly."""
        type_mappings = [
            (MessageType.USER, "user"),
            (MessageType.AGENT, "agent"),
            (MessageType.SYSTEM, "system"),
            (MessageType.ERROR, "error")
        ]
        
        for enum_val, expected_str in type_mappings:
            assert enum_val.value == expected_str
    
    def test_enum_case_sensitivity(self) -> None:
        """Test enum value case sensitivity."""
        # Test that enum values are case-sensitive
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.SUCCESS.value != "Success"
        assert ToolStatus.SUCCESS.value != "SUCCESS"
    
    def test_enum_in_complex_structure(self) -> None:
        """Test enum serialization in complex nested structures."""
        tool_with_metadata = ToolCompleted(
            tool_name="complex_tool",
            tool_output={
                "results": ["item1", "item2"],
                "metadata": {
                    "execution_time": 2.5,
                    "status_details": "success"
                }
            },
            run_id="run123",
            status=ToolStatus.SUCCESS
        )
        
        json_data = tool_with_metadata.model_dump()
        assert json_data["status"] == "success"
        assert json_data["tool_output"]["metadata"]["status_details"] == "success"


class TestEnumValidation:
    """Test enum validation and error handling."""
    
    def test_invalid_tool_status_handling(self) -> None:
        """Test invalid tool status handling."""
        with pytest.raises(ValueError):
            ToolStatus("invalid_status")
    
    def test_invalid_message_type_handling(self) -> None:
        """Test invalid message type handling."""
        with pytest.raises(ValueError):
            MessageType("invalid_type")
    
    def test_invalid_websocket_message_type(self) -> None:
        """Test invalid WebSocket message type handling."""
        with pytest.raises(ValueError):
            WebSocketMessageType("invalid_websocket_type")
    
    def test_enum_value_normalization(self) -> None:
        """Test that enum values are normalized correctly."""
        # Verify that enum construction is strict
        valid_status = ToolStatus("success")
        assert valid_status == ToolStatus.SUCCESS
        
        valid_type = MessageType("user")
        assert valid_type == MessageType.USER
    
    def test_enum_comparison_consistency(self) -> None:
        """Test enum comparison consistency."""
        status1 = ToolStatus.SUCCESS
        status2 = ToolStatus("success")
        
        assert status1 == status2
        assert status1.value == status2.value
        
        type1 = MessageType.AGENT
        type2 = MessageType("agent")
        
        assert type1 == type2
        assert type1.value == type2.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])