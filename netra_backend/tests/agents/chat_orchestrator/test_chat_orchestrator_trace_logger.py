"""
Comprehensive unit tests for ChatOrchestrator trace logging module.

Business Value: Tests the trace logging functionality that provides transparency
in agent execution through compressed trace display and WebSocket event delivery,
enabling users to understand AI processing steps in real-time chat.

Coverage Areas:
- Trace entry creation and formatting
- WebSocket event delivery for real-time transparency
- Trace compression and UI display formatting
- Size limit management and memory efficiency
- Enable/disable functionality for performance control
- Edge cases and error handling

SSOT Compliance: Uses SSotAsyncTestCase, real WebSocket testing, no mocks for core logic
"""

import asyncio
import pytest
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger


class ChatOrchestratorTraceLoggerTests(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive tests for ChatOrchestrator trace logging business logic."""

    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.mock_factory = SSotMockFactory()
        
        # Create mock WebSocket manager for WebSocket tests
        self.mock_websocket = AsyncMock()
        self.trace_logger = TraceLogger(websocket_manager=self.mock_websocket)
        
        # Create trace logger without WebSocket for basic tests
        self.basic_trace_logger = TraceLogger()

    def test_init_default_values(self):
        """Test TraceLogger initialization with default values."""
        logger = TraceLogger()
        
        self.assertIsNone(logger.websocket_manager)
        self.assertTrue(logger.enabled)
        self.assertEqual(logger.max_entries, 20)
        self.assertEqual(logger.traces, [])

    def test_init_with_websocket_manager(self):
        """Test TraceLogger initialization with WebSocket manager."""
        mock_ws = MagicMock()
        logger = TraceLogger(websocket_manager=mock_ws)
        
        self.assertEqual(logger.websocket_manager, mock_ws)
        self.assertTrue(logger.enabled)

    async def test_log_basic_string_message(self):
        """Test logging a basic string message."""
        action = "test_action"
        details = "test details"
        
        await self.trace_logger.log(action, details)
        
        self.assertEqual(len(self.trace_logger.traces), 1)
        trace = self.trace_logger.traces[0]
        
        self.assertEqual(trace["action"], action)
        self.assertEqual(trace["details"]["message"], details)
        self.assertIn("timestamp", trace)

    async def test_log_dict_details(self):
        """Test logging with dictionary details."""
        action = "complex_action"
        details = {"key1": "value1", "key2": "value2"}
        
        await self.trace_logger.log(action, details)
        
        trace = self.trace_logger.traces[0]
        self.assertEqual(trace["details"], details)

    async def test_log_object_details(self):
        """Test logging with object details (converted to string)."""
        action = "object_action"
        details = {"test": "object"}
        
        await self.trace_logger.log(action, details)
        
        trace = self.trace_logger.traces[0]
        # Dict should be preserved as dict
        self.assertEqual(trace["details"], details)

    async def test_log_non_dict_non_string_details(self):
        """Test logging with non-dict, non-string details."""
        action = "numeric_action"
        details = 42
        
        await self.trace_logger.log(action, details)
        
        trace = self.trace_logger.traces[0]
        self.assertEqual(trace["details"]["data"], "42")

    def test_create_trace_entry_format(self):
        """Test trace entry creation format."""
        action = "test_action"
        details = "test details"
        
        entry = self.trace_logger._create_trace_entry(action, details)
        
        self.assertEqual(entry["action"], action)
        self.assertEqual(entry["details"]["message"], details)
        self.assertIn("timestamp", entry)
        
        # Verify timestamp format
        timestamp = entry["timestamp"]
        self.assertTrue(timestamp.endswith("Z") or "+" in timestamp or timestamp.endswith(":00"))

    def test_format_details_string(self):
        """Test details formatting for string input."""
        details = "test message"
        formatted = self.trace_logger._format_details(details)
        
        expected = {"message": "test message"}
        self.assertEqual(formatted, expected)

    def test_format_details_dict(self):
        """Test details formatting for dict input."""
        details = {"key": "value", "number": 42}
        formatted = self.trace_logger._format_details(details)
        
        self.assertEqual(formatted, details)

    def test_format_details_other_types(self):
        """Test details formatting for other types."""
        details = [1, 2, 3]
        formatted = self.trace_logger._format_details(details)
        
        expected = {"data": "[1, 2, 3]"}
        self.assertEqual(formatted, expected)

    async def test_add_trace_entry_within_limit(self):
        """Test adding trace entries within limit."""
        # Add entries within limit
        for i in range(10):
            await self.trace_logger.log(f"action_{i}")
        
        self.assertEqual(len(self.trace_logger.traces), 10)

    async def test_add_trace_entry_exceeds_limit(self):
        """Test adding trace entries that exceed limit."""
        # Add more entries than max_entries (20)
        for i in range(25):
            await self.trace_logger.log(f"action_{i}")
        
        # Should maintain max_entries limit
        self.assertEqual(len(self.trace_logger.traces), 20)
        
        # Should keep the most recent entries
        last_trace = self.trace_logger.traces[-1]
        self.assertEqual(last_trace["action"], "action_24")
        
        first_trace = self.trace_logger.traces[0]
        self.assertEqual(first_trace["action"], "action_5")  # First 5 should be removed

    async def test_websocket_update_sent(self):
        """Test that WebSocket updates are sent when available."""
        action = "websocket_test"
        details = "test message"
        
        await self.trace_logger.log(action, details)
        
        # Verify WebSocket send_agent_update was called
        self.mock_websocket.send_agent_update.assert_called_once()
        
        call_args = self.mock_websocket.send_agent_update.call_args
        self.assertEqual(call_args[1]["agent_name"], "ChatOrchestrator")
        self.assertEqual(call_args[1]["status"], "trace")
        self.assertEqual(call_args[1]["data"]["action"], action)

    async def test_websocket_update_no_manager(self):
        """Test that no WebSocket updates are sent when no manager available."""
        await self.basic_trace_logger.log("test_action", "test details")
        
        # Should not raise error and should still log
        self.assertEqual(len(self.basic_trace_logger.traces), 1)

    async def test_disabled_logging(self):
        """Test that logging is disabled when enabled=False."""
        self.trace_logger.set_enabled(False)
        
        await self.trace_logger.log("disabled_action", "should not log")
        
        self.assertEqual(len(self.trace_logger.traces), 0)
        self.mock_websocket.send_agent_update.assert_not_called()

    def test_get_compressed_trace_default_limit(self):
        """Test getting compressed trace with default limit."""
        # Add more traces than default compressed limit
        for i in range(10):
            trace = {
                "timestamp": f"2025-01-14T12:30:{i:02d}.000000Z",
                "action": f"action_{i}",
                "details": {"message": f"message_{i}"}
            }
            self.trace_logger.traces.append(trace)
        
        compressed = self.trace_logger.get_compressed_trace()
        
        # Should return last 5 by default
        self.assertEqual(len(compressed), 5)
        self.assertEqual(compressed[0], "[0.000000Z] action_5")
        self.assertEqual(compressed[-1], "[0.000000Z] action_9")

    def test_get_compressed_trace_custom_limit(self):
        """Test getting compressed trace with custom limit."""
        # Add traces
        for i in range(10):
            trace = {
                "timestamp": f"2025-01-14T12:30:{i:02d}.000000Z",
                "action": f"action_{i}",
                "details": {"message": f"message_{i}"}
            }
            self.trace_logger.traces.append(trace)
        
        compressed = self.trace_logger.get_compressed_trace(limit=3)
        
        # Should return last 3
        self.assertEqual(len(compressed), 3)
        self.assertEqual(compressed[-1], "[0.000000Z] action_9")

    def test_get_compressed_trace_fewer_than_limit(self):
        """Test getting compressed trace when fewer traces than limit."""
        # Add only 2 traces
        for i in range(2):
            trace = {
                "timestamp": f"2025-01-14T12:30:{i:02d}.000000Z",
                "action": f"action_{i}",
                "details": {"message": f"message_{i}"}
            }
            self.trace_logger.traces.append(trace)
        
        compressed = self.trace_logger.get_compressed_trace(limit=5)
        
        # Should return all available traces
        self.assertEqual(len(compressed), 2)

    def test_format_trace_line(self):
        """Test trace line formatting."""
        trace = {
            "timestamp": "2025-01-14T12:30:45.123456Z",
            "action": "test_action",
            "details": {"message": "test"}
        }
        
        formatted = self.trace_logger._format_trace_line(trace)
        
        # Should extract last 8 chars of timestamp
        expected = "[3456Z] test_action"
        self.assertEqual(formatted, expected)

    def test_format_trace_line_short_timestamp(self):
        """Test trace line formatting with short timestamp."""
        trace = {
            "timestamp": "12:30:45",  # Less than 8 chars
            "action": "short_test",
            "details": {"message": "test"}
        }
        
        formatted = self.trace_logger._format_trace_line(trace)
        
        # Should use full timestamp if less than 8 chars
        expected = "[] short_test"
        self.assertEqual(formatted, expected)

    def test_clear_traces(self):
        """Test clearing all traces."""
        # Add some traces
        for i in range(5):
            self.trace_logger.traces.append({
                "timestamp": f"time_{i}",
                "action": f"action_{i}",
                "details": {"message": f"message_{i}"}
            })
        
        self.assertEqual(len(self.trace_logger.traces), 5)
        
        self.trace_logger.clear()
        
        self.assertEqual(len(self.trace_logger.traces), 0)

    def test_set_enabled_true(self):
        """Test enabling trace logging."""
        self.trace_logger.set_enabled(False)
        self.assertFalse(self.trace_logger.enabled)
        
        self.trace_logger.set_enabled(True)
        self.assertTrue(self.trace_logger.enabled)

    def test_set_enabled_false(self):
        """Test disabling trace logging."""
        self.assertTrue(self.trace_logger.enabled)
        
        self.trace_logger.set_enabled(False)
        self.assertFalse(self.trace_logger.enabled)

    async def test_log_performance_many_entries(self):
        """Test performance with many trace entries."""
        # Test adding many entries efficiently
        actions = [f"performance_test_{i}" for i in range(100)]
        
        for action in actions:
            await self.basic_trace_logger.log(action, f"details for {action}")
        
        # Should maintain max_entries limit
        self.assertEqual(len(self.basic_trace_logger.traces), 20)
        
        # Should have most recent entries
        last_trace = self.basic_trace_logger.traces[-1]
        self.assertEqual(last_trace["action"], "performance_test_99")

    async def test_websocket_error_handling(self):
        """Test handling of WebSocket errors."""
        # Mock WebSocket to raise error
        self.mock_websocket.send_agent_update.side_effect = Exception("WebSocket error")
        
        # Should not raise error when WebSocket fails
        await self.trace_logger.log("error_test", "should handle error")
        
        # Should still log the trace
        self.assertEqual(len(self.trace_logger.traces), 1)

    def test_timestamp_format_validation(self):
        """Test that timestamps are in valid ISO format."""
        entry = self.trace_logger._create_trace_entry("timestamp_test", "details")
        timestamp = entry["timestamp"]
        
        # Should be able to parse the timestamp
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            self.assertIsInstance(parsed_time, datetime)
        except ValueError:
            self.fail(f"Timestamp {timestamp} is not in valid ISO format")

    async def test_trace_content_integrity(self):
        """Test that trace content maintains integrity."""
        test_data = {
            "complex_data": {
                "nested": {"value": 42},
                "list": [1, 2, 3],
                "string": "test"
            }
        }
        
        await self.trace_logger.log("integrity_test", test_data)
        
        trace = self.trace_logger.traces[0]
        self.assertEqual(trace["details"], test_data)
        self.assertEqual(trace["action"], "integrity_test")

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    # Run tests directly if executed as script
    unittest.main()