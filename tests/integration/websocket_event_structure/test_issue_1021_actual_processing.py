"""
Test for Issue #1021: Verify actual backend WebSocket event processing produces payload structure
"""

import time
import unittest
from netra_backend.app.websocket_core.websocket_manager import _WebSocketManagerImplementation


class TestIssue1021ActualProcessing(unittest.TestCase):
    """Test actual backend WebSocket event processing for Issue #1021."""

    def setUp(self):
        """Set up test websocket manager."""
        self.manager = _UnifiedWebSocketManagerImplementation()

    def test_tool_executing_event_processing(self):
        """Test that tool_executing events are wrapped in payload structure."""
        # Test data that would come from agent execution
        test_data = {
            "tool_name": "aws_cost_analyzer",
            "parameters": {"region": "us-east-1"},
            "user_id": "test_user_123",
            "thread_id": "thread_456",
            "status": "executing"
        }

        # Process through the actual backend method
        result = self.manager._process_business_event("tool_executing", test_data)

        # Verify structure matches frontend expectations
        self.assertIsNotNone(result, "Event processing should not return None")
        self.assertEqual(result["type"], "tool_executing")
        self.assertIn("payload", result, "Result should have 'payload' field")

        # Verify payload contains expected fields
        payload = result["payload"]
        self.assertEqual(payload["tool_name"], "aws_cost_analyzer")
        self.assertEqual(payload["user_id"], "test_user_123")
        self.assertEqual(payload["thread_id"], "thread_456")
        self.assertIn("timestamp", payload)

        # Verify frontend can access data
        frontend_tool_name = result.get("payload", {}).get("tool_name")
        self.assertEqual(frontend_tool_name, "aws_cost_analyzer",
                        "Frontend should be able to access tool_name via payload.tool_name")

        print(f"✅ FIXED: Backend now emits: {result}")

    def test_tool_completed_event_processing(self):
        """Test that tool_completed events are wrapped in payload structure."""
        test_data = {
            "tool_name": "aws_cost_analyzer",
            "results": {"cost": "$100.50"},
            "duration": 1500,
            "success": True,
            "user_id": "test_user_123",
            "thread_id": "thread_456"
        }

        result = self.manager._process_business_event("tool_completed", test_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "tool_completed")
        self.assertIn("payload", result)

        payload = result["payload"]
        self.assertEqual(payload["tool_name"], "aws_cost_analyzer")
        self.assertEqual(payload["success"], True)
        self.assertEqual(payload["duration"], 1500)

    def test_agent_started_event_processing(self):
        """Test that agent_started events are wrapped in payload structure."""
        test_data = {
            "agent_name": "data_helper",
            "task_description": "Analyzing AWS costs",
            "user_id": "test_user_123",
            "thread_id": "thread_456"
        }

        result = self.manager._process_business_event("agent_started", test_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "agent_started")
        self.assertIn("payload", result)

        payload = result["payload"]
        self.assertEqual(payload["agent_name"], "data_helper")
        self.assertEqual(payload["task_description"], "Analyzing AWS costs")

    def test_agent_thinking_event_processing(self):
        """Test that agent_thinking events are wrapped in payload structure."""
        test_data = {
            "reasoning": "Analyzing cost data...",
            "user_id": "test_user_123",
            "thread_id": "thread_456"
        }

        result = self.manager._process_business_event("agent_thinking", test_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "agent_thinking")
        self.assertIn("payload", result)

        payload = result["payload"]
        self.assertEqual(payload["reasoning"], "Analyzing cost data...")

    def test_agent_completed_event_processing(self):
        """Test that agent_completed events are wrapped in payload structure."""
        test_data = {
            "status": "completed",
            "final_response": "Analysis complete. AWS costs are optimized.",
            "user_id": "test_user_123",
            "thread_id": "thread_456"
        }

        result = self.manager._process_business_event("agent_completed", test_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "agent_completed")
        self.assertIn("payload", result)

        payload = result["payload"]
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["final_response"], "Analysis complete. AWS costs are optimized.")

    def test_generic_event_processing(self):
        """Test that generic events are wrapped in payload structure."""
        test_data = {
            "custom_field": "custom_value",
            "user_id": "test_user_123"
        }

        result = self.manager._process_business_event("custom_event", test_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "custom_event")
        self.assertIn("payload", result)

        payload = result["payload"]
        self.assertEqual(payload["custom_field"], "custom_value")
        self.assertIn("timestamp", payload)

    def test_frontend_compatibility_simulation(self):
        """Simulate frontend processing to verify compatibility."""
        def simulate_frontend_processing(event_data):
            """Simulate how frontend processes events."""
            try:
                # Frontend looks for payload
                payload = event_data.get('payload')
                if not payload:
                    return {"error": "Missing payload field", "success": False}

                tool_name = payload.get('tool_name')
                if not tool_name:
                    return {"error": "Missing tool_name in payload", "success": False}

                return {"success": True, "tool_name": tool_name}
            except Exception as e:
                return {"error": str(e), "success": False}

        # Test with actual backend processing
        test_data = {"tool_name": "aws_cost_analyzer", "user_id": "test_user_123"}
        backend_result = self.manager._process_business_event("tool_executing", test_data)

        frontend_result = simulate_frontend_processing(backend_result)

        # This should now succeed with our fix
        self.assertTrue(frontend_result["success"],
                       f"Frontend processing should succeed. Got: {frontend_result}")
        self.assertEqual(frontend_result["tool_name"], "aws_cost_analyzer")

        print(f"✅ COMPATIBILITY VERIFIED: Frontend can now process backend events")


if __name__ == '__main__':
    unittest.main()