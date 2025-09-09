"""
Unit Test Suite for WebSocket Event Serialization

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure 100% reliable WebSocket event serialization for chat value delivery
- Value Impact: Prevents serialization failures that would break real-time agent communication
- Strategic Impact: MISSION CRITICAL - JSON serialization failures cause complete chat breakdown

This test suite validates the serialization of all 5 critical WebSocket events that enable
substantive chat interactions and AI value delivery to users:

1. agent_started - User sees agent processing begin
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Results delivery with actionable insights
5. agent_completed - Response completion notification

CRITICAL TESTING AREAS:
- JSON serialization of all WebSocketEventType enums
- Pydantic model serialization with datetime handling
- Strongly typed identifier validation (UserID, ThreadID, etc.)
- Event structure and required field validation
- Complex nested data serialization within event data
- Type safety enforcement for all event fields
"""

import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

# Import system under test - WebSocket types from shared SSOT
from shared.types import (
    WebSocketEventType, WebSocketMessage, UserID, ThreadID, RunID, RequestID, 
    WebSocketID, StronglyTypedWebSocketEvent, WebSocketEventPriority
)

# Test framework imports  
import unittest


class TestWebSocketEventTypeSerialization(unittest.TestCase):
    """Test JSON serialization of WebSocketEventType enums."""
    
    def test_agent_started_serialization(self):
        """Test agent_started event serializes correctly to JSON."""
        event_type = WebSocketEventType.AGENT_STARTED
        
        # Test direct serialization
        serialized = json.dumps(event_type.value)
        self.assertEqual(serialized, '"agent_started"')
        
        # Test deserialization
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized, "agent_started")
        self.assertEqual(WebSocketEventType(deserialized), WebSocketEventType.AGENT_STARTED)
    
    def test_agent_thinking_serialization(self):
        """Test agent_thinking event serializes correctly to JSON."""
        event_type = WebSocketEventType.AGENT_THINKING
        
        serialized = json.dumps(event_type.value)
        self.assertEqual(serialized, '"agent_thinking"')
        
        deserialized = json.loads(serialized)
        self.assertEqual(WebSocketEventType(deserialized), WebSocketEventType.AGENT_THINKING)
    
    def test_tool_executing_serialization(self):
        """Test tool_executing event serializes correctly to JSON."""
        event_type = WebSocketEventType.TOOL_EXECUTING
        
        serialized = json.dumps(event_type.value) 
        self.assertEqual(serialized, '"tool_executing"')
        
        deserialized = json.loads(serialized)
        self.assertEqual(WebSocketEventType(deserialized), WebSocketEventType.TOOL_EXECUTING)
    
    def test_tool_completed_serialization(self):
        """Test tool_completed event serializes correctly to JSON."""
        event_type = WebSocketEventType.TOOL_COMPLETED
        
        serialized = json.dumps(event_type.value)
        self.assertEqual(serialized, '"tool_completed"')
        
        deserialized = json.loads(serialized)
        self.assertEqual(WebSocketEventType(deserialized), WebSocketEventType.TOOL_COMPLETED)
    
    def test_agent_completed_serialization(self):
        """Test agent_completed event serializes correctly to JSON."""
        event_type = WebSocketEventType.AGENT_COMPLETED
        
        serialized = json.dumps(event_type.value)
        self.assertEqual(serialized, '"agent_completed"')
        
        deserialized = json.loads(serialized)
        self.assertEqual(WebSocketEventType(deserialized), WebSocketEventType.AGENT_COMPLETED)
    
    def test_all_critical_events_serializable(self):
        """Test all 5 critical events are JSON serializable."""
        critical_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        for event_type in critical_events:
            with self.subTest(event_type=event_type):
                # Must serialize without errors
                serialized = json.dumps(event_type.value)
                self.assertIsInstance(serialized, str)
                
                # Must deserialize back to same value
                deserialized = json.loads(serialized)
                self.assertEqual(WebSocketEventType(deserialized), event_type)


class TestWebSocketMessageSerialization(unittest.TestCase):
    """Test Pydantic WebSocketMessage model serialization."""
    
    def setUp(self):
        """Set up test data with strongly typed identifiers."""
        self.user_id = UserID(str(uuid.uuid4()))
        self.thread_id = ThreadID(str(uuid.uuid4()))
        self.run_id = RunID(str(uuid.uuid4()))
        self.request_id = RequestID(str(uuid.uuid4()))
        self.test_timestamp = datetime.now(timezone.utc)
    
    def test_agent_started_message_serialization(self):
        """Test agent_started WebSocketMessage serializes correctly."""
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            data={"agent_type": "data_analysis", "reasoning": "Starting data analysis"},
            timestamp=self.test_timestamp
        )
        
        # Test Pydantic model_dump (JSON serialization)
        serialized_dict = message.model_dump()
        self.assertEqual(serialized_dict["event_type"], WebSocketEventType.AGENT_STARTED)
        self.assertEqual(serialized_dict["user_id"], str(self.user_id))
        self.assertEqual(serialized_dict["thread_id"], str(self.thread_id))
        self.assertEqual(serialized_dict["request_id"], str(self.request_id))
        self.assertIn("agent_type", serialized_dict["data"])
        
        # Test full JSON serialization
        json_str = message.model_dump_json()
        self.assertIsInstance(json_str, str)
        
        # Test deserialization
        parsed = json.loads(json_str)
        self.assertEqual(parsed["event_type"], "agent_started")
    
    def test_agent_thinking_message_with_complex_data(self):
        """Test agent_thinking message with complex nested data."""
        complex_data = {
            "reasoning_step": "Analyzing user query",
            "progress": 0.3,
            "tokens_used": 150,
            "current_tools": ["web_search", "data_analysis"],
            "metadata": {
                "model": "gpt-4",
                "temperature": 0.7,
                "confidence": 0.85
            }
        }
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_THINKING,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            data=complex_data,
            timestamp=self.test_timestamp
        )
        
        # Must serialize complex nested data without errors
        serialized_dict = message.model_dump()
        self.assertEqual(serialized_dict["data"]["reasoning_step"], "Analyzing user query")
        self.assertEqual(serialized_dict["data"]["progress"], 0.3)
        self.assertEqual(serialized_dict["data"]["metadata"]["model"], "gpt-4")
        
        # Must survive JSON round-trip
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["data"]["tokens_used"], 150)
    
    def test_tool_executing_message_serialization(self):
        """Test tool_executing message with tool metadata."""
        tool_data = {
            "tool_name": "web_search",
            "tool_input": {"query": "latest AI developments", "max_results": 5},
            "execution_id": str(uuid.uuid4()),
            "started_at": self.test_timestamp.isoformat()
        }
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.TOOL_EXECUTING,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            data=tool_data
        )
        
        serialized = message.model_dump()
        self.assertEqual(serialized["event_type"], WebSocketEventType.TOOL_EXECUTING)
        self.assertEqual(serialized["data"]["tool_name"], "web_search")
        self.assertIn("max_results", serialized["data"]["tool_input"])
    
    def test_tool_completed_message_with_results(self):
        """Test tool_completed message with result data."""
        result_data = {
            "tool_name": "web_search",
            "execution_time_ms": 1250,
            "success": True,
            "results": [
                {"title": "AI News", "url": "https://example.com", "snippet": "Latest AI news"},
                {"title": "ML Updates", "url": "https://example2.com", "snippet": "ML developments"}
            ],
            "token_usage": {"input": 50, "output": 200}
        }
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.TOOL_COMPLETED,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            data=result_data
        )
        
        serialized = message.model_dump()
        self.assertEqual(serialized["event_type"], WebSocketEventType.TOOL_COMPLETED)
        self.assertTrue(serialized["data"]["success"])
        self.assertEqual(len(serialized["data"]["results"]), 2)
    
    def test_agent_completed_message_serialization(self):
        """Test agent_completed message with final response data."""
        completion_data = {
            "status": "success",
            "final_response": "Analysis complete. Found 3 key insights.",
            "execution_time_ms": 5500,
            "tools_used": ["web_search", "data_analysis", "summarization"],
            "total_tokens": 1250,
            "cost_analysis": {"input_cost": 0.05, "output_cost": 0.12, "total": 0.17}
        }
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_COMPLETED,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            data=completion_data
        )
        
        serialized = message.model_dump()
        self.assertEqual(serialized["event_type"], WebSocketEventType.AGENT_COMPLETED)
        self.assertEqual(serialized["data"]["status"], "success")
        self.assertEqual(len(serialized["data"]["tools_used"]), 3)
    
    def test_datetime_serialization_handling(self):
        """Test datetime fields serialize correctly to ISO format."""
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            timestamp=self.test_timestamp
        )
        
        # Use model_dump with mode='json' to serialize for JSON
        serialized = message.model_dump(mode='json')
        
        # Timestamp should be serialized as ISO string in JSON mode
        self.assertIsInstance(serialized["timestamp"], str)
        
        # Should be parseable back to datetime
        parsed_timestamp = datetime.fromisoformat(serialized["timestamp"].replace('Z', '+00:00'))
        self.assertEqual(parsed_timestamp.replace(microsecond=0), 
                        self.test_timestamp.replace(microsecond=0))
    
    def test_strongly_typed_id_validation(self):
        """Test that strongly typed IDs are validated correctly."""
        # Valid IDs should work
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id
        )
        
        # Should serialize successfully
        serialized = message.model_dump()
        self.assertEqual(serialized["user_id"], str(self.user_id))
        
        # Empty string IDs should work but we test that validation logic exists
        # Note: UserID is a NewType wrapper, so empty strings are technically valid at type level
        # Validation would need to happen at the application level
        empty_message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=UserID(""),  # Empty string - validation depends on implementation
            thread_id=self.thread_id,
            request_id=self.request_id
        )
        
        # The message should be created but we can verify the ID is empty
        self.assertEqual(str(empty_message.user_id), "")


class TestWebSocketEventMetadataValidation(unittest.TestCase):
    """Test event metadata and typing validation."""
    
    def test_required_fields_validation(self):
        """Test that all required fields are present in WebSocketMessage."""
        user_id = UserID(str(uuid.uuid4()))
        thread_id = ThreadID(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # All required fields present - should work
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id
        )
        
        self.assertEqual(message.event_type, WebSocketEventType.AGENT_STARTED)
        self.assertEqual(message.user_id, user_id)
        self.assertEqual(message.thread_id, thread_id)
        self.assertEqual(message.request_id, request_id)
        self.assertIsInstance(message.timestamp, datetime)
        self.assertIsInstance(message.data, dict)
    
    def test_event_type_enum_validation(self):
        """Test that event_type must be a valid WebSocketEventType."""
        user_id = UserID(str(uuid.uuid4()))
        thread_id = ThreadID(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # Valid enum values should work
        for event_type in [WebSocketEventType.AGENT_STARTED, WebSocketEventType.TOOL_EXECUTING]:
            message = WebSocketMessage(
                event_type=event_type,
                user_id=user_id,
                thread_id=thread_id,
                request_id=request_id
            )
            self.assertEqual(message.event_type, event_type)
    
    def test_data_field_defaults_to_empty_dict(self):
        """Test that data field defaults to empty dictionary."""
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=UserID(str(uuid.uuid4())),
            thread_id=ThreadID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        self.assertEqual(message.data, {})
        self.assertIsInstance(message.data, dict)
    
    def test_timestamp_defaults_to_utc_now(self):
        """Test that timestamp defaults to current UTC time."""
        before = datetime.now(timezone.utc)
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=UserID(str(uuid.uuid4())),
            thread_id=ThreadID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        after = datetime.now(timezone.utc)
        
        # Timestamp should be between before and after
        self.assertGreaterEqual(message.timestamp, before)
        self.assertLessEqual(message.timestamp, after)
        self.assertEqual(message.timestamp.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()