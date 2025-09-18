from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
"""
"""
Mission Critical Server Message Validation Tests - POST FIX

This module tests the FIXED MissionCriticalEventValidator's ability to handle'
both flat and ServerMessage format structures.

BUSINESS IMPACT: $500K+ ARR depends on proper WebSocket event validation
to ensure Golden Path chat functionality works correctly.

Issue #892: Validation that MissionCriticalEventValidator now handles
both flat event structures and ServerMessage format with nested payload.
"
"

"""
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any

from tests.mission_critical.test_websocket_agent_events_suite import MissionCriticalEventValidator


class ServerMessageValidationFixedTests(SSotBaseTestCase):
    "Test MissionCriticalEventValidator with both formats after fix."
    
    def setup_method(self, method):
        "Set up test validator."
        super().setup_method(method)

        self.validator = MissionCriticalEventValidator()
        self.test_timestamp = datetime.now(timezone.utc).isoformat()
    
    def test_flat_event_validation_still_works(self):
        "Verify validator still works with flat event format after fix."
        flat_event = {
            type: agent_started,
            "user_id: test-user-123,"
            thread_id: test-thread-456, 
            timestamp: self.test_timestamp"
            timestamp: self.test_timestamp"
        }
        
        self.validator.errors = []
        result = self.validator.validate_event_content_structure(flat_event, agent_started")"
        self.assertTrue(result, fFlat event validation should work, errors: {self.validator.errors})
        self.assertEqual(len(self.validator.errors), 0, No validation errors expected for flat format)"
        self.assertEqual(len(self.validator.errors), 0, No validation errors expected for flat format)"
    
    def test_server_message_format_now_passes(self):
        "Verify that ServerMessage format now passes with fixed validator."
        server_message = {
            type": agent_started,"
            payload: {
                user_id: test-user-123","
                "thread_id: test-thread-456,"
                timestamp: self.test_timestamp,
                status": started,"
                agent_name: supervisor
            },
            sender: "system,"
            timestamp": self.test_timestamp"
        }
        
        self.validator.errors = []
        result = self.validator.validate_event_content_structure(server_message, agent_started)
        self.assertTrue(result, fServerMessage format should pass with fixed validator, errors: {self.validator.errors}")"
        self.assertEqual(len(self.validator.errors), 0, No validation errors expected for ServerMessage format)
    
    def test_tool_executing_server_message_format_passes(self):
        "Test tool_executing event in ServerMessage format passes after fix."
        server_message = {
            type: tool_executing,
            "payload: {"
                tool_name: search_data,
                parameters: {"query: test search},"
                timestamp: self.test_timestamp,
                sub_agent_name": data_helper"
            },
            sender: system, 
            timestamp: self.test_timestamp"
            timestamp: self.test_timestamp"
        }
        
        self.validator.errors = []
        result = self.validator.validate_event_content_structure(server_message, "tool_executing)"
        self.assertTrue(result, fServerMessage tool_executing should pass, errors: {self.validator.errors})
        self.assertEqual(len(self.validator.errors), 0, "No validation errors for tool_executing ServerMessage)"
    
    def test_agent_completed_server_message_format_passes(self):
        Test agent_completed event in ServerMessage format passes after fix."
        Test agent_completed event in ServerMessage format passes after fix."
        server_message = {
            "type: agent_completed,"
            payload: {
                status": success,"
                final_response: Task completed successfully,
                timestamp: self.test_timestamp,"
                timestamp: self.test_timestamp,"
                "execution_time: 45.2,"
                agent_name: supervisor
            },
            sender": system,"
            timestamp: self.test_timestamp
        }
        
        self.validator.errors = []
        result = self.validator.validate_event_content_structure(server_message, agent_completed)"
        result = self.validator.validate_event_content_structure(server_message, agent_completed)"
        self.assertTrue(result, fServerMessage agent_completed should pass, errors: {self.validator.errors}")"
        self.assertEqual(len(self.validator.errors), 0, No validation errors for agent_completed ServerMessage)
    
    def test_agent_thinking_both_formats_work(self):
        ""Test that both flat and ServerMessage formats work for agent_thinking."
        flat_event = {
            type: agent_thinking","
            "reasoning: Analyzing user request,"
            timestamp: self.test_timestamp
        }
        
        server_message = {
            type": agent_thinking, "
            payload: {
                reasoning: Analyzing user request","
                "timestamp: self.test_timestamp,"
                agent_name: supervisor
            },
            sender": system,"
            timestamp: self.test_timestamp
        }
        
        # Test flat format
        self.validator.errors = []
        flat_result = self.validator.validate_event_content_structure(flat_event, agent_thinking)"
        flat_result = self.validator.validate_event_content_structure(flat_event, agent_thinking)"
        self.assertTrue(flat_result, fFlat format should work, errors: {self.validator.errors}")"
        
        # Test ServerMessage format
        self.validator.errors = []
        server_result = self.validator.validate_event_content_structure(server_message, agent_thinking)
        self.assertTrue(server_result, fServerMessage format should work, errors: {self.validator.errors}")"
    
    def test_tool_completed_both_formats_work(self):
        Test that both formats work for tool_completed events."
        Test that both formats work for tool_completed events."
        flat_event = {
            type": tool_completed,"
            tool_name: search_data,
            results": {data: search results},"
            duration: 2.5,"
            duration: 2.5,"
            timestamp": self.test_timestamp"
        }
        
        server_message = {
            type: tool_completed,
            "payload: {"
                tool_name: search_data,
                results: {"data: search results},"
                duration: 2.5,
                timestamp": self.test_timestamp,"
                sub_agent_name: data_helper
            },
            sender: system","
            "timestamp: self.test_timestamp"
        }
        
        # Test flat format
        self.validator.errors = []
        flat_result = self.validator.validate_event_content_structure(flat_event, tool_completed)
        self.assertTrue(flat_result, f"Flat tool_completed should work, errors: {self.validator.errors})"
        
        # Test ServerMessage format
        self.validator.errors = []
        server_result = self.validator.validate_event_content_structure(server_message, tool_completed")"
        self.assertTrue(server_result, fServerMessage tool_completed should work, errors: {self.validator.errors})
    
    def test_missing_fields_detected_in_both_formats(self):
        "Test that missing required fields are properly detected in both formats."
        # Flat format missing fields
        flat_incomplete = {
            type: agent_started,
            "user_id: test-user-123"
            # Missing thread_id and timestamp
        }
        
        # ServerMessage format missing fields
        server_incomplete = {
            type: agent_started,
            payload: {"
            payload: {"
                user_id": test-user-123"
                # Missing thread_id and timestamp
            },
            sender: system
        }
        
        # Test flat format detects missing fields
        self.validator.errors = []
        flat_result = self.validator.validate_event_content_structure(flat_incomplete, agent_started")"
        self.assertFalse(flat_result, Should detect missing fields in flat format)
        self.assertGreater(len(self.validator.errors), 0, Should have errors for missing fields)"
        self.assertGreater(len(self.validator.errors), 0, Should have errors for missing fields)"
        self.assertIn("missing required fields, self.validator.errors[0)"
        self.assertIn(flat format, self.validator.errors[0)
        
        # Test ServerMessage format detects missing fields
        self.validator.errors = []
        server_result = self.validator.validate_event_content_structure(server_incomplete, "agent_started)"
        self.assertFalse(server_result, Should detect missing fields in ServerMessage format)
        self.assertGreater(len(self.validator.errors), 0, Should have errors for missing fields)"
        self.assertGreater(len(self.validator.errors), 0, Should have errors for missing fields)"
        self.assertIn(missing required fields", self.validator.errors[0)"
        self.assertIn(ServerMessage format, self.validator.errors[0)
    
    def test_invalid_payload_structure_handled(self):
        ""Test that invalid payload structures are handled gracefully."
        # ServerMessage with non-dict payload
        invalid_server_message = {
            type: agent_started","
            "payload: invalid_payload,  # Should be dict"
            sender: system,
            "timestamp: self.test_timestamp"
        }
        
        # Should fall back to treating as flat format and fail validation
        self.validator.errors = []
        result = self.validator.validate_event_content_structure(invalid_server_message, agent_started)
        self.assertFalse(result, Should fail validation for invalid payload structure)"
        self.assertFalse(result, Should fail validation for invalid payload structure)"
        self.assertGreater(len(self.validator.errors), 0, Should have validation errors")"


if __name__ == "__main__:"
    unittest.main()
))))
}