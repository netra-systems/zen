"""
Mission Critical Server Message Validation Tests

This module tests the MissionCriticalEventValidator's ability to handle 
ServerMessage format structures where event data is nested in payload.

BUSINESS IMPACT: $500K+ ARR depends on proper WebSocket event validation
to ensure Golden Path chat functionality works correctly.

Issue #892: MissionCriticalEventValidator expects flat event structures
but actual ServerMessage format has nested payload structure.
"""

import json
import unittest
from datetime import datetime, timezone
from typing import Dict, Any

from tests.mission_critical.test_websocket_agent_events_suite import MissionCriticalEventValidator


class TestServerMessageValidation(unittest.TestCase):
    """Test MissionCriticalEventValidator with ServerMessage format."""
    
    def setUp(self):
        """Set up test validator."""
        self.validator = MissionCriticalEventValidator()
        self.test_timestamp = datetime.now(timezone.utc).isoformat()
    
    def test_flat_event_validation_works(self):
        """Verify validator works with current flat event format."""
        # This should pass with current implementation
        flat_event = {
            "type": "agent_started",
            "user_id": "test-user-123",
            "thread_id": "test-thread-456", 
            "timestamp": self.test_timestamp
        }
        
        result = self.validator.validate_event_content_structure(flat_event, "agent_started")
        self.assertTrue(result, "Flat event validation should work")
        self.assertEqual(len(self.validator.errors), 0, "No validation errors expected")
    
    def test_server_message_format_fails_current_validation(self):
        """Demonstrate that ServerMessage format fails with current validator."""
        # This is the actual ServerMessage format being sent
        server_message = {
            "type": "agent_started",
            "payload": {
                "user_id": "test-user-123",
                "thread_id": "test-thread-456",
                "timestamp": self.test_timestamp,
                "status": "started",
                "agent_name": "supervisor"
            },
            "sender": "system",
            "timestamp": self.test_timestamp
        }
        
        # Clear any previous errors
        self.validator.errors = []
        
        # This should fail with current implementation because it looks for 
        # user_id, thread_id directly in the event dict, not in payload
        result = self.validator.validate_event_content_structure(server_message, "agent_started")
        self.assertFalse(result, "ServerMessage format should fail with current validator")
        self.assertGreater(len(self.validator.errors), 0, "Should have validation errors")
        
        # Verify the specific error mentions missing required fields
        error_message = str(self.validator.errors)
        self.assertIn("missing required fields", error_message)
        self.assertIn("user_id", error_message)
        self.assertIn("thread_id", error_message)
    
    def test_tool_executing_server_message_format_fails(self):
        """Test tool_executing event in ServerMessage format fails current validation."""
        server_message = {
            "type": "tool_executing",
            "payload": {
                "tool_name": "search_data",
                "parameters": {"query": "test search"},
                "timestamp": self.test_timestamp,
                "sub_agent_name": "data_helper"
            },
            "sender": "system", 
            "timestamp": self.test_timestamp
        }
        
        # Clear any previous errors
        self.validator.errors = []
        
        result = self.validator.validate_event_content_structure(server_message, "tool_executing")
        self.assertFalse(result, "ServerMessage tool_executing should fail with current validator")
        self.assertGreater(len(self.validator.errors), 0, "Should have validation errors for tool_executing")
    
    def test_agent_completed_server_message_format_fails(self):
        """Test agent_completed event in ServerMessage format fails current validation."""
        server_message = {
            "type": "agent_completed",
            "payload": {
                "status": "success",
                "final_response": "Task completed successfully",
                "timestamp": self.test_timestamp,
                "execution_time": 45.2,
                "agent_name": "supervisor"
            },
            "sender": "system",
            "timestamp": self.test_timestamp
        }
        
        # Clear any previous errors
        self.validator.errors = []
        
        result = self.validator.validate_event_content_structure(server_message, "agent_completed")
        self.assertFalse(result, "ServerMessage agent_completed should fail with current validator")
        self.assertGreater(len(self.validator.errors), 0, "Should have validation errors for agent_completed")
    
    def test_mixed_format_handling(self):
        """Test that validator can handle both formats after fix."""
        # This test now passes after implementing the fix
        flat_event = {
            "type": "agent_thinking",
            "reasoning": "Analyzing user request",
            "timestamp": self.test_timestamp
        }
        
        server_message = {
            "type": "agent_thinking", 
            "payload": {
                "reasoning": "Analyzing user request",
                "timestamp": self.test_timestamp,
                "agent_name": "supervisor"
            },
            "sender": "system",
            "timestamp": self.test_timestamp
        }
        
        # Clear errors
        self.validator.errors = []
        
        # Both should work after fix implementation
        flat_result = self.validator.validate_event_content_structure(flat_event, "agent_thinking")
        self.assertTrue(flat_result, "Flat format should work")
        
        # Clear errors for server message test
        self.validator.errors = []
        
        # This now passes with the fix implemented
        server_result = self.validator.validate_event_content_structure(server_message, "agent_thinking")
        self.assertTrue(server_result, f"ServerMessage format should now work with fixed validator, errors: {self.validator.errors}")
    
    def test_validation_report_contains_server_message_errors(self):
        """Test that validation report properly shows ServerMessage format errors."""
        server_messages = [
            {
                "type": "agent_started",
                "payload": {"user_id": "test-user", "status": "started"},
                "sender": "system",
                "timestamp": self.test_timestamp
            },
            {
                "type": "tool_executing", 
                "payload": {"tool_name": "search", "parameters": {}},
                "sender": "system",
                "timestamp": self.test_timestamp
            }
        ]
        
        # Clear errors
        self.validator.errors = []
        
        for msg in server_messages:
            event_type = msg["type"]
            self.validator.validate_event_content_structure(msg, event_type)
        
        report = self.validator.generate_report()
        self.assertIn("missing required fields", report)
        self.assertIn("agent_started", report)
        self.assertIn("tool_executing", report)


if __name__ == "__main__":
    unittest.main()