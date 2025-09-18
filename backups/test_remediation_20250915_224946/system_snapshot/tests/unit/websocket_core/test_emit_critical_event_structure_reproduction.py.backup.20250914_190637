"""
Unit Test: emit_critical_event Structure Issue Reproduction - Issue #1021

PURPOSE: Direct reproduction of unified_manager.py:1493-1499 structure issue
ROOT CAUSE: emit_critical_event creates generic wrapper that buries business fields in 'data'

EXPECTED FAILURE: These tests MUST FAIL to confirm the issue exists
BUSINESS VALUE: $500K+ ARR - WebSocket events must have business fields at top level
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
import json

from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestEmitCriticalEventStructureReproduction(SSotAsyncTestCase):
    """Direct test of emit_critical_event structure issue"""
    
    def setup_method(self, method):
        """Set up test environment"""
        super().setup_method(method)
        self.manager = UnifiedWebSocketManager()
        self.test_user_id = "test_user_123"
        
        # Mock active connection
        self.manager._connections = {
            self.test_user_id: {
                'websocket': AsyncMock(),
                'last_heartbeat': datetime.now(timezone.utc),
                'status': 'active'
            }
        }
    
    async def test_emit_critical_event_buries_business_fields_in_data_wrapper(self):
        """
        REPRODUCES ISSUE #1021: emit_critical_event buries business fields in 'data' wrapper
        EXPECTED FAILURE: Business fields should be at top level but they get wrapped
        
        Root cause: unified_manager.py:1493-1499 creates generic message structure:
        {
            "type": event_type,
            "data": data,  <-- PROBLEM: business fields buried here
            "timestamp": ...,
            "critical": True
        }
        """
        # Business data that frontend needs at top level
        business_data = {
            "tool_name": "DataAnalyzer",
            "execution_id": "exec_123", 
            "parameters": {"query": "customer metrics"},
            "estimated_time": 3000
        }
        
        captured_message = None
        
        async def capture_send_to_user(user_id, message):
            nonlocal captured_message
            captured_message = message
        
        with patch.object(self.manager, 'send_to_user', side_effect=capture_send_to_user), \
             patch.object(self.manager, 'is_connection_active', return_value=True):
            
            # Call the problematic method
            await self.manager.emit_critical_event(
                self.test_user_id,
                "tool_executing", 
                business_data
            )
        
        # Verify message was sent
        self.assertIsNotNone(captured_message, "No message was captured")
        
        print(f"CAPTURED MESSAGE STRUCTURE: {captured_message}")
        
        # FAILING ASSERTIONS: Business fields should be at top level
        # These assertions WILL FAIL because of the generic wrapper at lines 1493-1499
        self.assertIn("tool_name", captured_message,
                     "tool_name should be at top level, not buried in 'data' wrapper")
        self.assertIn("execution_id", captured_message,
                     "execution_id should be at top level, not buried in 'data' wrapper")
        self.assertIn("parameters", captured_message,
                     "parameters should be at top level, not buried in 'data' wrapper")
        
        # These should pass - system fields should be at top level  
        self.assertEqual(captured_message.get("type"), "tool_executing")
        self.assertIn("timestamp", captured_message)
        self.assertIn("critical", captured_message)
        
        # The PROBLEM: business fields are buried in 'data'
        if "data" in captured_message:
            self.fail(f"Business fields should NOT be wrapped in 'data'. Found: {captured_message['data']}")
    
    async def test_all_event_types_have_same_generic_wrapper_problem(self):
        """
        Test that all event types suffer from same generic wrapper issue
        EXPECTED FAILURE: All business event types get wrapped the same incorrect way
        """
        test_cases = [
            ("agent_started", {
                "agent_type": "SupervisorAgent",
                "run_id": "run_456",
                "user_message": "Analyze customer data"
            }),
            ("agent_thinking", {
                "thinking_content": "I need to gather customer metrics...",
                "step_number": 1,
                "confidence": 0.85
            }),
            ("tool_executing", {
                "tool_name": "CustomerMetrics", 
                "parameters": {"timeframe": "30d"},
                "execution_id": "exec_789"
            }),
            ("tool_completed", {
                "tool_name": "CustomerMetrics",
                "result": {"growth_rate": 12.5},
                "execution_time_ms": 2500,
                "status": "success"
            }),
            ("agent_completed", {
                "response": "Customer metrics show 12.5% growth",
                "run_id": "run_456", 
                "tools_used": ["CustomerMetrics"],
                "total_time_ms": 8500
            })
        ]
        
        captured_messages = []
        
        async def capture_messages(user_id, message):
            captured_messages.append(message)
        
        with patch.object(self.manager, 'send_to_user', side_effect=capture_messages), \
             patch.object(self.manager, 'is_connection_active', return_value=True):
            
            for event_type, event_data in test_cases:
                await self.manager.emit_critical_event(
                    self.test_user_id,
                    event_type,
                    event_data
                )
        
        # Validate all messages have same structural problem
        self.assertEqual(len(captured_messages), 5, "Should have captured 5 messages")
        
        for i, (expected_type, expected_data) in enumerate(test_cases):
            message = captured_messages[i]
            
            print(f"\nEVENT TYPE: {expected_type}")
            print(f"MESSAGE STRUCTURE: {message}")
            
            # System fields should be at top level
            self.assertEqual(message.get("type"), expected_type)
            self.assertIn("timestamp", message)
            self.assertIn("critical", message)
            
            # FAILING ASSERTIONS: Business fields should be at top level
            for business_field in expected_data.keys():
                self.assertIn(business_field, message,
                             f"{business_field} should be at top level in {expected_type} event")
            
            # This should fail - business data should NOT be wrapped
            if "data" in message and isinstance(message["data"], dict):
                for business_field in expected_data.keys():
                    if business_field in message["data"]:
                        self.fail(f"Business field '{business_field}' should not be buried in 'data' wrapper for {expected_type}")
    
    async def test_frontend_cannot_access_wrapped_business_fields(self):
        """
        Test demonstrating frontend access problem with current structure
        EXPECTED FAILURE: Simulates frontend code that breaks with wrapped structure
        """
        business_data = {
            "tool_name": "DataProcessor",
            "progress": 75,
            "eta_seconds": 30,
            "current_stage": "analyzing"
        }
        
        captured_message = None
        
        async def capture_message(user_id, message):
            nonlocal captured_message
            captured_message = message
        
        with patch.object(self.manager, 'send_to_user', side_effect=capture_message), \
             patch.object(self.manager, 'is_connection_active', return_value=True):
            
            await self.manager.emit_critical_event(
                self.test_user_id,
                "tool_executing",
                business_data
            )
        
        # Simulate frontend JavaScript code accessing the message
        # Frontend expects: message.tool_name, message.progress, etc.
        
        try:
            # This is how frontend code tries to access business fields
            frontend_tool_name = captured_message["tool_name"]
            frontend_progress = captured_message["progress"]
            frontend_eta = captured_message["eta_seconds"]
            frontend_stage = captured_message["current_stage"]
            
            # These assertions should pass but will FAIL due to wrapping
            self.assertEqual(frontend_tool_name, "DataProcessor")
            self.assertEqual(frontend_progress, 75)
            self.assertEqual(frontend_eta, 30)
            self.assertEqual(frontend_stage, "analyzing")
            
        except KeyError as e:
            # If we get here, it confirms the fields are wrapped and inaccessible
            self.fail(f"Frontend cannot access business field: {e}. Message structure: {captured_message}")
    
    async def test_correct_structure_should_flatten_business_fields(self):
        """
        Test showing what the CORRECT structure should look like
        This test documents the expected behavior after the fix
        """
        # This is what the structure SHOULD be after fixing the issue
        expected_correct_structure = {
            "type": "tool_executing",
            "tool_name": "DataAnalyzer",  # Business fields at top level
            "execution_id": "exec_123",
            "parameters": {"query": "customer metrics"},
            "estimated_time": 3000,
            "timestamp": "2025-09-14T...",  # System fields also at top level
            "critical": True
        }
        
        # For now, this test documents what we want
        # After fixing unified_manager.py:1493-1499, the emit_critical_event
        # should produce this flattened structure instead of the wrapped one
        
        self.assertTrue(True, "This test documents the desired structure")
        
        # The fix should change unified_manager.py:1493-1499 from:
        # message = {
        #     "type": event_type,
        #     "data": data,          # WRONG: buries business fields
        #     "timestamp": ...,
        #     "critical": True
        # }
        #
        # To something like:
        # message = {
        #     "type": event_type,
        #     **data,                # CORRECT: flattens business fields to top level
        #     "timestamp": ...,
        #     "critical": True  
        # }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])