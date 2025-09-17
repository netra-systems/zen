"""
Issue #1021 Fix Validation Test

This test validates that the WebSocket payload wrapper fix is working correctly
by actually calling the WebSocket manager and checking the message structure.
"""

import json
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager


class TestIssue1021FixValidation(SSotAsyncTestCase):
    """Test that Issue #1021 payload wrapper fix is working."""

    async def setUp(self):
        """Set up test fixtures."""
        await super().setUp()
        self.manager = UnifiedWebSocketManager()
        self.user_id = "test_user_fix_validation"
        self.sent_messages = []

    def create_mock_websocket(self):
        """Create a mock WebSocket that captures sent messages."""
        def capture_send(data):
            """Capture sent messages for analysis."""
            try:
                message = json.loads(data)
                self.sent_messages.append(message)
                print(f"📤 CAPTURED: {json.dumps(message, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON DECODE ERROR: {e}")
                print(f"   Raw data: {data}")

        return type('MockWebSocket', (), {
            'send': capture_send,
            'closed': False
        })()

    async def test_payload_wrapper_implementation(self):
        """Test that WebSocket events are now wrapped in payload structure."""

        print("\n🧪 Testing Issue #1021 Fix: Payload Wrapper Implementation")
        print("=" * 70)

        # Set up mock WebSocket connection
        mock_websocket = self.create_mock_websocket()
        self.manager.connections[self.user_id] = mock_websocket

        # Test data for tool_executing event
        test_data = {
            "tool_name": "aws_cost_analyzer",
            "parameters": {"region": "us-east-1"},
            "execution_id": "exec_123",
            "estimated_time": 3000
        }

        # Emit the critical event
        await self.manager.emit_critical_event(self.user_id, "tool_executing", test_data)

        # Validate that message was sent
        self.assertGreater(len(self.sent_messages), 0, "No messages were sent")

        # Get the latest message
        message = self.sent_messages[-1]

        print(f"\n📊 MESSAGE ANALYSIS:")
        print(f"   Type: {message.get('type')}")
        print(f"   Has 'payload': {'payload' in message}")
        print(f"   Has 'data': {'data' in message}")

        # CRITICAL VALIDATION: Message must have 'payload' field
        self.assertIn('payload', message,
                     "Message must have 'payload' field for frontend compatibility")

        # CRITICAL VALIDATION: payload must contain business data
        payload = message['payload']
        self.assertIn('tool_name', payload,
                     "Payload must contain 'tool_name' for frontend access")

        self.assertEqual(payload['tool_name'], 'aws_cost_analyzer',
                        "Tool name must be accessible via payload.tool_name")

        # CRITICAL VALIDATION: Frontend access pattern must work
        try:
            frontend_tool_name = message['payload']['tool_name']
            self.assertEqual(frontend_tool_name, 'aws_cost_analyzer',
                           "Frontend must be able to access payload.tool_name")
            print(f"   ✅ Frontend access successful: payload.tool_name = {frontend_tool_name}")
        except KeyError:
            self.fail("Frontend cannot access payload.tool_name - fix incomplete")

        # VALIDATION: Message should have proper structure
        expected_root_fields = ['type', 'timestamp', 'critical', 'payload']
        for field in expected_root_fields:
            self.assertIn(field, message, f"Message must have '{field}' at root level")

        print(f"   ✅ PAYLOAD WRAPPER FIX VALIDATED!")

    async def test_multiple_event_types_have_payload(self):
        """Test that all event types now use payload wrapper."""

        print("\n🧪 Testing Multiple Event Types with Payload Wrapper")
        print("=" * 70)

        # Set up mock WebSocket connection
        mock_websocket = self.create_mock_websocket()
        self.manager.connections[self.user_id] = mock_websocket

        # Test different event types
        test_events = [
            ("agent_started", {"agent_name": "supervisor", "task": "analysis"}),
            ("agent_thinking", {"thought": "analyzing data", "step": 1}),
            ("tool_executing", {"tool_name": "DataAnalyzer", "status": "running"}),
            ("tool_completed", {"tool_name": "DataAnalyzer", "result": "success"}),
            ("agent_completed", {"agent_name": "supervisor", "final_response": "done"})
        ]

        initial_message_count = len(self.sent_messages)

        for event_type, data in test_events:
            await self.manager.emit_critical_event(self.user_id, event_type, data)

        # Validate that all events were sent
        new_message_count = len(self.sent_messages) - initial_message_count
        self.assertEqual(new_message_count, len(test_events),
                        f"Expected {len(test_events)} messages, got {new_message_count}")

        # Validate that all messages have payload wrapper
        for i, (event_type, expected_data) in enumerate(test_events):
            message = self.sent_messages[initial_message_count + i]

            with self.subTest(event_type=event_type):
                self.assertIn('payload', message,
                             f"{event_type} event must have payload wrapper")

                self.assertEqual(message.get('type'), event_type,
                               f"Message type must be {event_type}")

                # Validate that business data is in payload
                payload = message['payload']
                for key, value in expected_data.items():
                    self.assertIn(key, payload,
                                 f"{event_type} payload must contain {key}")
                    self.assertEqual(payload[key], value,
                                   f"{event_type} payload.{key} must equal {value}")

        print(f"   ✅ All {len(test_events)} event types use payload wrapper!")

    async def test_frontend_compatibility_simulation(self):
        """Simulate frontend processing to ensure compatibility."""

        print("\n🧪 Testing Frontend Compatibility Simulation")
        print("=" * 70)

        # Set up mock WebSocket connection
        mock_websocket = self.create_mock_websocket()
        self.manager.connections[self.user_id] = mock_websocket

        # Send a tool_executing event
        test_data = {
            "tool_name": "data_analyzer",
            "parameters": {"query": "customer metrics"},
            "execution_id": "exec_456"
        }

        await self.manager.emit_critical_event(self.user_id, "tool_executing", test_data)

        # Get the message
        self.assertGreater(len(self.sent_messages), 0)
        message = self.sent_messages[-1]

        # Simulate frontend processing (based on websocketHandlers.ts patterns)
        def simulate_frontend_processing(event):
            """Simulate frontend WebSocket event processing."""
            try:
                # Frontend expects: const payload = event.payload;
                payload = event['payload']

                # Frontend expects: const toolName = payload.tool_name || 'unknown-tool';
                tool_name = payload.get('tool_name', 'unknown-tool')

                # Frontend expects: const timestamp = payload.timestamp || Date.now();
                timestamp = payload.get('timestamp', 'no-timestamp')

                return {
                    "success": True,
                    "tool_name": tool_name,
                    "timestamp": timestamp,
                    "error": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "tool_name": "unknown-tool",
                    "timestamp": "no-timestamp",
                    "error": str(e)
                }

        # Run the simulation
        result = simulate_frontend_processing(message)

        print(f"   Frontend Processing Result: {json.dumps(result, indent=4)}")

        # Validate frontend processing success
        self.assertTrue(result['success'],
                       f"Frontend processing failed: {result.get('error')}")

        self.assertEqual(result['tool_name'], 'data_analyzer',
                        "Frontend must successfully extract tool name")

        self.assertNotEqual(result['tool_name'], 'unknown-tool',
                           "Frontend should not fall back to 'unknown-tool'")

        print(f"   ✅ Frontend compatibility confirmed!")
        print(f"   ✅ Issue #1021 structural mismatch RESOLVED!")

if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-v']))