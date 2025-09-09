"""
Unit Test Suite for WebSocket Event Type Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure type safety and validation for WebSocket event routing
- Value Impact: Prevents type confusion and routing errors in WebSocket event system
- Strategic Impact: Type safety reduces debugging time and prevents production errors

This test suite validates the strongly typed WebSocket event system, focusing on:
1. StronglyTypedWebSocketEvent validation and construction
2. WebSocketEventType enum validation and constraints
3. Type safety enforcement for event routing
4. Validation error handling and messaging
5. Event priority and metadata validation

CRITICAL VALIDATION AREAS:
- Enum value validation for all WebSocketEventType values
- StronglyTypedWebSocketEvent construction and validation
- Type coercion and validation error handling
- Event priority classification validation
- Metadata validation for routing safety
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
import unittest

# Import system under test - WebSocket types from shared SSOT
from shared.types import (
    WebSocketEventType, WebSocketMessage, WebSocketEventPriority,
    StronglyTypedWebSocketEvent, UserID, ThreadID, RunID, RequestID,
    WebSocketID, ensure_user_id, ensure_thread_id, ensure_request_id
)


class TestWebSocketEventTypeValidation(unittest.TestCase):
    """Test WebSocketEventType enum validation and constraints."""
    
    def test_all_critical_event_types_defined(self):
        """Test that all 5 critical event types are properly defined."""
        # The 5 mission-critical event types for chat value delivery
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for event_name in critical_events:
            with self.subTest(event_name=event_name):
                # Must be able to create from string value
                event_type = WebSocketEventType(event_name)
                self.assertIsInstance(event_type, WebSocketEventType)
                self.assertEqual(event_type.value, event_name)
    
    def test_agent_started_event_type(self):
        """Test agent_started event type validation."""
        event_type = WebSocketEventType.AGENT_STARTED
        
        self.assertEqual(event_type.value, "agent_started")
        self.assertIsInstance(event_type, WebSocketEventType)
        
        # Test creation from string
        from_string = WebSocketEventType("agent_started")
        self.assertEqual(from_string, event_type)
    
    def test_agent_thinking_event_type(self):
        """Test agent_thinking event type validation."""
        event_type = WebSocketEventType.AGENT_THINKING
        
        self.assertEqual(event_type.value, "agent_thinking")
        self.assertIsInstance(event_type, WebSocketEventType)
        
        # Test creation from string
        from_string = WebSocketEventType("agent_thinking")
        self.assertEqual(from_string, event_type)
    
    def test_tool_executing_event_type(self):
        """Test tool_executing event type validation.""" 
        event_type = WebSocketEventType.TOOL_EXECUTING
        
        self.assertEqual(event_type.value, "tool_executing")
        self.assertIsInstance(event_type, WebSocketEventType)
        
        # Test creation from string
        from_string = WebSocketEventType("tool_executing")
        self.assertEqual(from_string, event_type)
    
    def test_tool_completed_event_type(self):
        """Test tool_completed event type validation."""
        event_type = WebSocketEventType.TOOL_COMPLETED
        
        self.assertEqual(event_type.value, "tool_completed")
        self.assertIsInstance(event_type, WebSocketEventType)
        
        # Test creation from string
        from_string = WebSocketEventType("tool_completed")
        self.assertEqual(from_string, event_type)
    
    def test_agent_completed_event_type(self):
        """Test agent_completed event type validation."""
        event_type = WebSocketEventType.AGENT_COMPLETED
        
        self.assertEqual(event_type.value, "agent_completed")
        self.assertIsInstance(event_type, WebSocketEventType)
        
        # Test creation from string
        from_string = WebSocketEventType("agent_completed")
        self.assertEqual(from_string, event_type)
    
    def test_invalid_event_type_raises_error(self):
        """Test that invalid event type strings raise ValueError."""
        invalid_event_types = [
            "invalid_event",
            "agent_unknown",
            "tool_invalid",
            "",
            "AGENT_STARTED",  # Wrong case
            "agent-started",  # Wrong separator
            None
        ]
        
        for invalid_type in invalid_event_types:
            with self.subTest(invalid_type=invalid_type):
                with self.assertRaises((ValueError, TypeError)):
                    WebSocketEventType(invalid_type)
    
    def test_event_type_enumeration_completeness(self):
        """Test that all expected event types are present in enum."""
        expected_event_types = {
            "agent_started",
            "agent_thinking",
            "agent_completed", 
            "tool_executing",
            "tool_completed",
            "error_occurred",
            "status_update"
        }
        
        actual_event_types = {event.value for event in WebSocketEventType}
        
        # All expected types must be present
        for expected in expected_event_types:
            self.assertIn(expected, actual_event_types, 
                         f"Missing expected event type: {expected}")
    
    def test_event_type_case_sensitivity(self):
        """Test that event types are case-sensitive."""
        # Correct case should work
        WebSocketEventType("agent_started")
        
        # Incorrect case should fail
        with self.assertRaises(ValueError):
            WebSocketEventType("AGENT_STARTED")
        
        with self.assertRaises(ValueError):
            WebSocketEventType("Agent_Started")


class TestStronglyTypedWebSocketEventValidation(unittest.TestCase):
    """Test StronglyTypedWebSocketEvent validation and construction."""
    
    def setUp(self):
        """Set up test data with valid strongly typed identifiers."""
        self.user_id = UserID(str(uuid.uuid4()))
        self.thread_id = ThreadID(str(uuid.uuid4()))
        self.request_id = RequestID(str(uuid.uuid4()))
        self.websocket_id = WebSocketID(str(uuid.uuid4()))
    
    def test_strongly_typed_event_creation(self):
        """Test creation of StronglyTypedWebSocketEvent with valid data."""
        event = StronglyTypedWebSocketEvent(
            event_type="agent_started",  # String, not enum
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            websocket_id=self.websocket_id,
            data={"message": "Agent processing started"},
            priority=WebSocketEventPriority.HIGH
        )
        
        self.assertEqual(event.event_type, "agent_started")
        self.assertEqual(event.user_id, self.user_id)
        self.assertEqual(event.thread_id, self.thread_id)
        self.assertEqual(event.request_id, self.request_id)
        self.assertEqual(event.websocket_id, self.websocket_id)
        self.assertEqual(event.priority, WebSocketEventPriority.HIGH)
        self.assertIn("message", event.data)
    
    def test_strongly_typed_event_with_all_critical_types(self):
        """Test StronglyTypedWebSocketEvent with each critical event type."""
        critical_events = [
            ("agent_started", {"status": "started"}),
            ("agent_thinking", {"reasoning": "analyzing data"}),
            ("tool_executing", {"tool": "web_search"}),
            ("tool_completed", {"results": ["result1", "result2"]}),
            ("agent_completed", {"final_answer": "Analysis complete"})
        ]
        
        for event_type, data in critical_events:
            with self.subTest(event_type=event_type):
                event = StronglyTypedWebSocketEvent(
                    event_type=event_type,
                    user_id=self.user_id,
                    thread_id=self.thread_id,
                    request_id=self.request_id,
                    data=data,
                    priority=WebSocketEventPriority.NORMAL
                )
                
                self.assertEqual(event.event_type, event_type)
                self.assertEqual(event.data, data)
                self.assertIsInstance(event.timestamp, datetime)
    
    def test_event_priority_validation(self):
        """Test WebSocketEventPriority validation."""
        valid_priorities = [
            WebSocketEventPriority.LOW,
            WebSocketEventPriority.NORMAL,
            WebSocketEventPriority.HIGH,
            WebSocketEventPriority.CRITICAL
        ]
        
        for priority in valid_priorities:
            with self.subTest(priority=priority):
                event = StronglyTypedWebSocketEvent(
                    event_type="agent_started",
                    user_id=self.user_id,
                    thread_id=self.thread_id,
                    request_id=self.request_id,
                    priority=priority
                )
                
                self.assertEqual(event.priority, priority)
    
    def test_strongly_typed_id_validation(self):
        """Test that strongly typed IDs are properly validated."""
        # Valid IDs should work
        event = StronglyTypedWebSocketEvent(
            event_type="agent_started",
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id
        )
        
        self.assertEqual(event.user_id, self.user_id)
        self.assertEqual(event.thread_id, self.thread_id)
        self.assertEqual(event.request_id, self.request_id)
    
    def test_default_values_validation(self):
        """Test that default values are properly set."""
        event = StronglyTypedWebSocketEvent(
            event_type="agent_started",
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id
        )
        
        # Default values should be set correctly
        self.assertIsInstance(event.data, dict)
        self.assertEqual(event.data, {})
        self.assertIsInstance(event.timestamp, datetime)
        self.assertEqual(event.timestamp.tzinfo, timezone.utc)
        self.assertEqual(event.priority, WebSocketEventPriority.NORMAL)
        self.assertIsNone(event.websocket_id)
    
    def test_timestamp_validation(self):
        """Test timestamp validation and UTC enforcement."""
        custom_timestamp = datetime.now(timezone.utc)
        
        event = StronglyTypedWebSocketEvent(
            event_type="agent_started",
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            timestamp=custom_timestamp
        )
        
        self.assertEqual(event.timestamp, custom_timestamp)
        self.assertEqual(event.timestamp.tzinfo, timezone.utc)


class TestWebSocketEventTypeConstraints(unittest.TestCase):
    """Test constraints and validation rules for WebSocket event types."""
    
    def test_event_type_immutability(self):
        """Test that WebSocketEventType enum values are immutable."""
        # Enum values should not be modifiable
        original_value = WebSocketEventType.AGENT_STARTED.value
        
        # Attempting to modify should not affect the enum
        with self.assertRaises(AttributeError):
            WebSocketEventType.AGENT_STARTED.value = "modified"
        
        # Value should remain unchanged
        self.assertEqual(WebSocketEventType.AGENT_STARTED.value, original_value)
    
    def test_event_type_string_representation(self):
        """Test string representation of WebSocketEventType."""
        event_types_and_strings = [
            (WebSocketEventType.AGENT_STARTED, "agent_started"),
            (WebSocketEventType.AGENT_THINKING, "agent_thinking"),
            (WebSocketEventType.TOOL_EXECUTING, "tool_executing"),
            (WebSocketEventType.TOOL_COMPLETED, "tool_completed"),
            (WebSocketEventType.AGENT_COMPLETED, "agent_completed")
        ]
        
        for event_type, expected_string in event_types_and_strings:
            with self.subTest(event_type=event_type):
                self.assertEqual(str(event_type.value), expected_string)
                self.assertEqual(event_type.value, expected_string)
    
    def test_event_type_equality_validation(self):
        """Test equality comparisons for WebSocketEventType."""
        # Same enum values should be equal
        self.assertEqual(WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_STARTED)
        
        # Different enum values should not be equal
        self.assertNotEqual(WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_COMPLETED)
        
        # Enum should equal string value creation
        self.assertEqual(WebSocketEventType.AGENT_STARTED, WebSocketEventType("agent_started"))
    
    def test_event_type_hashing(self):
        """Test that WebSocketEventType can be used as dictionary keys."""
        event_mapping = {
            WebSocketEventType.AGENT_STARTED: "Agent processing started",
            WebSocketEventType.AGENT_THINKING: "Agent is reasoning",
            WebSocketEventType.TOOL_EXECUTING: "Tool execution in progress", 
            WebSocketEventType.TOOL_COMPLETED: "Tool execution completed",
            WebSocketEventType.AGENT_COMPLETED: "Agent processing completed"
        }
        
        # Should be able to retrieve values using enum keys
        self.assertEqual(event_mapping[WebSocketEventType.AGENT_STARTED], "Agent processing started")
        self.assertEqual(event_mapping[WebSocketEventType.TOOL_EXECUTING], "Tool execution in progress")
        
        # Should have 5 critical events mapped
        self.assertEqual(len(event_mapping), 5)
    
    def test_event_type_iteration(self):
        """Test iteration over WebSocketEventType enum."""
        all_event_types = list(WebSocketEventType)
        
        # Should contain all expected event types
        expected_types = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.AGENT_COMPLETED,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.ERROR_OCCURRED,
            WebSocketEventType.STATUS_UPDATE
        ]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, all_event_types)


class TestWebSocketEventValidationEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for WebSocket event validation."""
    
    def test_none_values_validation(self):
        """Test validation behavior with None values."""
        user_id = UserID(str(uuid.uuid4()))
        thread_id = ThreadID(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # None event_type should raise error
        with self.assertRaises((TypeError, ValueError)):
            StronglyTypedWebSocketEvent(
                event_type=None,
                user_id=user_id,
                thread_id=thread_id,
                request_id=request_id
            )
        
        # None for required IDs should raise error
        with self.assertRaises((TypeError, ValueError)):
            StronglyTypedWebSocketEvent(
                event_type="agent_started",
                user_id=None,
                thread_id=thread_id,
                request_id=request_id
            )
    
    def test_invalid_data_types(self):
        """Test validation with invalid data types for event data."""
        user_id = UserID(str(uuid.uuid4()))
        thread_id = ThreadID(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # Non-dict data should raise validation error
        with self.assertRaises((TypeError, ValueError)):
            StronglyTypedWebSocketEvent(
                event_type="agent_started",
                user_id=user_id,
                thread_id=thread_id,
                request_id=request_id,
                data=None  # None is not allowed for data field
            )


if __name__ == "__main__":
    unittest.main()