"""
Unit Test Suite for WebSocket Event Ordering Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure correct event sequence validation for reliable chat interactions
- Value Impact: Prevents event ordering violations that would confuse users about agent progress
- Strategic Impact: Proper event ordering ensures users see logical progression of AI work

This test suite validates the business logic for WebSocket event sequence validation,
ensuring that events follow the correct order for meaningful chat interactions:

CRITICAL EVENT SEQUENCE:
1. agent_started (required first)
2. agent_thinking (optional, multiple allowed)  
3. tool_executing (optional, multiple allowed)
4. tool_completed (must follow tool_executing)
5. agent_completed (required last)

VALIDATION RULES:
- agent_started must be the first event
- tool_completed must be preceded by tool_executing
- agent_completed must be the final event
- Multiple thinking/tool events allowed in sequence
- Invalid sequences must be rejected

This ensures users see logical progression:
"Agent started → Agent thinking → Tool executing → Tool completed → Agent completed"
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import unittest

# Import system under test - WebSocket types and validation logic
from shared.types import (
    WebSocketEventType, WebSocketMessage, WebSocketEventPriority,
    StronglyTypedWebSocketEvent, UserID, ThreadID, RunID, RequestID
)


class WebSocketEventSequenceValidator:
    """Business logic for validating WebSocket event sequences.
    
    This class implements the business rules for proper event ordering
    to ensure users see logical progression of agent work.
    """
    
    def __init__(self):
        self.event_history: List[WebSocketEventType] = []
        self.started = False
        self.completed = False
        self.pending_tools: Dict[str, bool] = {}  # tool_id -> is_executing
    
    def validate_next_event(self, event_type: WebSocketEventType, tool_id: Optional[str] = None) -> bool:
        """Validate if the next event type is allowed given current state."""
        
        # Rule 1: agent_started must be first
        if not self.started and event_type != WebSocketEventType.AGENT_STARTED:
            return False
        
        # Rule 2: No events allowed after agent_completed
        if self.completed:
            return False
        
        # Rule 3: agent_started can only appear once
        if event_type == WebSocketEventType.AGENT_STARTED and self.started:
            return False
        
        # Rule 4: tool_completed must be preceded by tool_executing
        if event_type == WebSocketEventType.TOOL_COMPLETED:
            if tool_id is None or tool_id not in self.pending_tools:
                return False
            if not self.pending_tools[tool_id]:
                return False
        
        # Rule 5: tool_executing requires a valid tool_id
        if event_type == WebSocketEventType.TOOL_EXECUTING and (tool_id is None or not tool_id.strip()):
            return False
        
        return True
    
    def add_event(self, event_type: WebSocketEventType, tool_id: Optional[str] = None) -> bool:
        """Add an event to the sequence if valid."""
        if not self.validate_next_event(event_type, tool_id):
            return False
        
        self.event_history.append(event_type)
        
        # Update state based on event type
        if event_type == WebSocketEventType.AGENT_STARTED:
            self.started = True
        elif event_type == WebSocketEventType.AGENT_COMPLETED:
            self.completed = True
        elif event_type == WebSocketEventType.TOOL_EXECUTING and tool_id:
            self.pending_tools[tool_id] = True
        elif event_type == WebSocketEventType.TOOL_COMPLETED and tool_id:
            self.pending_tools[tool_id] = False
        
        return True
    
    def is_valid_complete_sequence(self) -> bool:
        """Check if current sequence represents a complete valid workflow."""
        return (
            self.started and 
            self.completed and 
            len(self.event_history) >= 2 and  # At least started + completed
            self.event_history[0] == WebSocketEventType.AGENT_STARTED and
            self.event_history[-1] == WebSocketEventType.AGENT_COMPLETED and
            all(not executing for executing in self.pending_tools.values())  # All tools completed
        )


class TestWebSocketEventSequenceValidation(unittest.TestCase):
    """Test the business logic for WebSocket event sequence validation."""
    
    def setUp(self):
        """Set up a fresh validator for each test."""
        self.validator = WebSocketEventSequenceValidator()
    
    def test_agent_started_must_be_first(self):
        """Test that agent_started must be the first event in any sequence."""
        # agent_started should be allowed as first event
        self.assertTrue(self.validator.validate_next_event(WebSocketEventType.AGENT_STARTED))
        
        # Other events should NOT be allowed before agent_started
        invalid_first_events = [
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        for event_type in invalid_first_events:
            with self.subTest(event_type=event_type):
                fresh_validator = WebSocketEventSequenceValidator()
                self.assertFalse(fresh_validator.validate_next_event(event_type))
    
    def test_agent_started_can_only_appear_once(self):
        """Test that agent_started can only appear once in a sequence."""
        # First agent_started should be allowed
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # Second agent_started should be rejected
        self.assertFalse(self.validator.validate_next_event(WebSocketEventType.AGENT_STARTED))
        self.assertFalse(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
    
    def test_valid_minimal_sequence(self):
        """Test the minimal valid sequence: agent_started → agent_completed."""
        # Add agent_started
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # Add agent_completed
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        
        # Should be a valid complete sequence
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_agent_thinking_events_allowed_after_started(self):
        """Test that agent_thinking events are allowed after agent_started."""
        # Start sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # Multiple thinking events should be allowed
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_THINKING))
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_THINKING))
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_THINKING))
        
        # Complete sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_tool_execution_sequence_validation(self):
        """Test that tool_executing must be followed by tool_completed."""
        # Start sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # Tool executing should require tool_id
        self.assertFalse(self.validator.validate_next_event(WebSocketEventType.TOOL_EXECUTING))
        self.assertTrue(self.validator.validate_next_event(WebSocketEventType.TOOL_EXECUTING, "tool_1"))
        
        # Add tool executing
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "tool_1"))
        
        # Tool completed should require the same tool_id
        self.assertFalse(self.validator.validate_next_event(WebSocketEventType.TOOL_COMPLETED))
        self.assertFalse(self.validator.validate_next_event(WebSocketEventType.TOOL_COMPLETED, "wrong_tool"))
        self.assertTrue(self.validator.validate_next_event(WebSocketEventType.TOOL_COMPLETED, "tool_1"))
        
        # Add tool completed
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "tool_1"))
        
        # Complete sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_multiple_tool_sequences(self):
        """Test multiple tool execution sequences."""
        # Start sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # First tool
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "web_search"))
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "web_search"))
        
        # Second tool
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "data_analysis"))
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "data_analysis"))
        
        # Third tool
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "summarization"))
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "summarization"))
        
        # Complete sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_concurrent_tool_execution_validation(self):
        """Test validation of concurrent tool execution."""
        # Start sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # Start multiple tools concurrently
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "tool_1"))
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "tool_2"))
        
        # Complete tools in different order
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "tool_2"))
        self.assertTrue(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "tool_1"))
        
        # Complete sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_no_events_allowed_after_agent_completed(self):
        """Test that no events are allowed after agent_completed."""
        # Complete a valid sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_COMPLETED))
        
        # No further events should be allowed
        invalid_after_completion = [
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        for event_type in invalid_after_completion:
            with self.subTest(event_type=event_type):
                self.assertFalse(self.validator.validate_next_event(event_type))
    
    def test_tool_completed_without_executing_rejected(self):
        """Test that tool_completed without tool_executing is rejected."""
        # Start sequence
        self.assertTrue(self.validator.add_event(WebSocketEventType.AGENT_STARTED))
        
        # tool_completed without tool_executing should be rejected
        self.assertFalse(self.validator.validate_next_event(WebSocketEventType.TOOL_COMPLETED, "tool_1"))
        self.assertFalse(self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "tool_1"))
    
    def test_complex_valid_sequence(self):
        """Test a complex but valid event sequence representing real agent work."""
        sequence_steps = [
            (WebSocketEventType.AGENT_STARTED, None),
            (WebSocketEventType.AGENT_THINKING, None),
            (WebSocketEventType.TOOL_EXECUTING, "web_search"),
            (WebSocketEventType.AGENT_THINKING, None),
            (WebSocketEventType.TOOL_COMPLETED, "web_search"),
            (WebSocketEventType.AGENT_THINKING, None),
            (WebSocketEventType.TOOL_EXECUTING, "data_analysis"),
            (WebSocketEventType.TOOL_COMPLETED, "data_analysis"),
            (WebSocketEventType.AGENT_THINKING, None),
            (WebSocketEventType.AGENT_COMPLETED, None)
        ]
        
        for event_type, tool_id in sequence_steps:
            with self.subTest(event_type=event_type, tool_id=tool_id):
                self.assertTrue(self.validator.add_event(event_type, tool_id))
        
        # Should be a valid complete sequence
        self.assertTrue(self.validator.is_valid_complete_sequence())


class TestEventSequenceStateManagement(unittest.TestCase):
    """Test state machine transitions for event sequence validation."""
    
    def setUp(self):
        """Set up a fresh validator for each test."""
        self.validator = WebSocketEventSequenceValidator()
    
    def test_initial_state(self):
        """Test the initial state of the validator."""
        self.assertFalse(self.validator.started)
        self.assertFalse(self.validator.completed)
        self.assertEqual(len(self.validator.event_history), 0)
        self.assertEqual(len(self.validator.pending_tools), 0)
        self.assertFalse(self.validator.is_valid_complete_sequence())
    
    def test_state_after_agent_started(self):
        """Test state transitions after agent_started event."""
        self.validator.add_event(WebSocketEventType.AGENT_STARTED)
        
        self.assertTrue(self.validator.started)
        self.assertFalse(self.validator.completed)
        self.assertEqual(len(self.validator.event_history), 1)
        self.assertEqual(self.validator.event_history[0], WebSocketEventType.AGENT_STARTED)
        self.assertFalse(self.validator.is_valid_complete_sequence())
    
    def test_state_after_tool_execution(self):
        """Test state management during tool execution."""
        self.validator.add_event(WebSocketEventType.AGENT_STARTED)
        self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "test_tool")
        
        self.assertTrue(self.validator.started)
        self.assertFalse(self.validator.completed)
        self.assertIn("test_tool", self.validator.pending_tools)
        self.assertTrue(self.validator.pending_tools["test_tool"])
        self.assertFalse(self.validator.is_valid_complete_sequence())
    
    def test_state_after_tool_completion(self):
        """Test state management after tool completion."""
        self.validator.add_event(WebSocketEventType.AGENT_STARTED)
        self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "test_tool")
        self.validator.add_event(WebSocketEventType.TOOL_COMPLETED, "test_tool")
        
        self.assertTrue(self.validator.started)
        self.assertFalse(self.validator.completed)
        self.assertIn("test_tool", self.validator.pending_tools)
        self.assertFalse(self.validator.pending_tools["test_tool"])
        self.assertFalse(self.validator.is_valid_complete_sequence())
    
    def test_state_after_agent_completed(self):
        """Test final state after agent_completed event."""
        self.validator.add_event(WebSocketEventType.AGENT_STARTED)
        self.validator.add_event(WebSocketEventType.AGENT_COMPLETED)
        
        self.assertTrue(self.validator.started)
        self.assertTrue(self.validator.completed)
        self.assertEqual(len(self.validator.event_history), 2)
        self.assertTrue(self.validator.is_valid_complete_sequence())
    
    def test_incomplete_sequence_with_pending_tools(self):
        """Test that sequences with pending tools are marked incomplete."""
        self.validator.add_event(WebSocketEventType.AGENT_STARTED)
        self.validator.add_event(WebSocketEventType.TOOL_EXECUTING, "pending_tool")
        self.validator.add_event(WebSocketEventType.AGENT_COMPLETED)
        
        # Should be marked as complete by state but invalid due to pending tool
        self.assertTrue(self.validator.started)
        self.assertTrue(self.validator.completed)
        self.assertFalse(self.validator.is_valid_complete_sequence())


class TestEventSequenceErrorPrevention(unittest.TestCase):
    """Test error prevention in event sequence validation."""
    
    def test_prevents_invalid_sequences(self):
        """Test that all invalid sequences are properly rejected."""
        validator = WebSocketEventSequenceValidator()
        
        # These sequences should all be rejected
        invalid_sequences = [
            # Starting with wrong event
            [(WebSocketEventType.AGENT_THINKING, None)],
            [(WebSocketEventType.TOOL_EXECUTING, "tool_1")],
            [(WebSocketEventType.AGENT_COMPLETED, None)],
            
            # Double agent_started
            [(WebSocketEventType.AGENT_STARTED, None), (WebSocketEventType.AGENT_STARTED, None)],
            
            # Tool completed without executing
            [(WebSocketEventType.AGENT_STARTED, None), (WebSocketEventType.TOOL_COMPLETED, "tool_1")],
            
            # Events after completion
            [
                (WebSocketEventType.AGENT_STARTED, None),
                (WebSocketEventType.AGENT_COMPLETED, None),
                (WebSocketEventType.AGENT_THINKING, None)
            ]
        ]
        
        for sequence in invalid_sequences:
            with self.subTest(sequence=sequence):
                validator = WebSocketEventSequenceValidator()
                success = True
                for event_type, tool_id in sequence:
                    if not validator.add_event(event_type, tool_id):
                        success = False
                        break
                
                # At least one event in the sequence should have been rejected
                self.assertFalse(success, f"Invalid sequence was incorrectly accepted: {sequence}")
    
    def test_tool_id_validation(self):
        """Test validation of tool IDs in tool events."""
        validator = WebSocketEventSequenceValidator()
        validator.add_event(WebSocketEventType.AGENT_STARTED)
        
        # tool_executing without tool_id should fail
        self.assertFalse(validator.add_event(WebSocketEventType.TOOL_EXECUTING, None))
        self.assertFalse(validator.add_event(WebSocketEventType.TOOL_EXECUTING, ""))
        
        # Valid tool_executing should work
        self.assertTrue(validator.add_event(WebSocketEventType.TOOL_EXECUTING, "valid_tool"))
        
        # tool_completed with wrong tool_id should fail
        self.assertFalse(validator.add_event(WebSocketEventType.TOOL_COMPLETED, "wrong_tool"))
        self.assertFalse(validator.add_event(WebSocketEventType.TOOL_COMPLETED, None))
        
        # tool_completed with correct tool_id should work
        self.assertTrue(validator.add_event(WebSocketEventType.TOOL_COMPLETED, "valid_tool"))


if __name__ == "__main__":
    unittest.main()