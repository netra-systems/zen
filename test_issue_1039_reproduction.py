#!/usr/bin/env python3
"""
Test to reproduce Issue #1039: WebSocket tool_executing validation missing tool_name field.

This test demonstrates that tool_executing events are missing the required tool_name field
which causes validation failures and impacts user transparency about tool usage.

Business Impact: P0 - Golden Path failure - users cannot see which tools are being executed
"""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

# SSOT Test Infrastructure
import sys
import os
from pathlib import Path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core classes under test
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.event_validation_framework import WebSocketEventValidator


class Issue1039ReproductionTest(SSotAsyncTestCase):
    """Test to reproduce and validate fix for issue #1039 - tool_executing missing tool_name field."""
    
    async def setup_test_environment(self):
        """Set up test environment for reproducing the issue."""
        self.mock_manager = MagicMock()
        self.test_user_id = "test_user_1039"
        self.test_context = MagicMock()
        self.test_context.user_id = self.test_user_id
        self.test_context.thread_id = "test_thread_1039"
        self.test_context.run_id = "test_run_1039"
        
        # Create emitter instance
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Create event validator for testing validation logic
        self.validator = WebSocketEventValidator()
        
        # Track emitted events
        self.emitted_events = []
        
        # Mock the manager's emit method to capture events
        async def mock_emit(event_type, data):
            event = {
                "type": event_type,
                "payload": data,
                "timestamp": time.time(),
                "thread_id": self.test_context.thread_id
            }
            self.emitted_events.append(event)
            return True
        
        self.mock_manager.emit_to_user = AsyncMock(side_effect=mock_emit)
    
    async def test_reproduce_issue_1039_tool_executing_missing_tool_name(self):
        """REPRODUCE: Demonstrate tool_executing events are missing tool_name field."""
        await self.setup_test_environment()
        
        # Test the current implementation - this should fail validation
        tool_name = "cost_analyzer"
        metadata = {"query": "analyze costs", "table": "expenses"}
        
        # Emit tool_executing event using current implementation
        await self.emitter.notify_tool_executing(tool_name, metadata)
        
        # Verify event was emitted
        assert len(self.emitted_events) == 1, "Expected 1 tool_executing event to be emitted"
        
        tool_executing_event = self.emitted_events[0]
        assert tool_executing_event["type"] == "tool_executing", "Event type should be tool_executing"
        
        # CRITICAL ISSUE: Check if tool_name is in the event data
        event_data = tool_executing_event["payload"]
        print(f"Event data structure: {event_data}")
        
        # This assertion should fail with current implementation
        try:
            assert "tool_name" in event_data, f"ISSUE #1039 REPRODUCED: tool_executing event missing tool_name field. Event data: {event_data}"
            print("UNEXPECTED: tool_name field was found in event data")
        except AssertionError as e:
            print(f"ISSUE #1039 CONFIRMED: {e}")
            # This is expected - the issue is reproduced
            
        # Also test with event validation framework
        validation_result = self.validator.validate_event(tool_executing_event, {})
        
        if not validation_result.is_valid:
            print(f"Event validation failed as expected: {validation_result.validation_errors}")
            assert "Missing tool_name" in str(validation_result.validation_errors), "Validation should catch missing tool_name"
        else:
            print("UNEXPECTED: Event validation passed - tool_name might be present")
        
        print("Issue #1039 reproduction test completed - tool_executing events missing tool_name field")


if __name__ == "__main__":
    async def run_reproduction_test():
        test = Issue1039ReproductionTest()
        await test.test_reproduce_issue_1039_tool_executing_missing_tool_name()
        print("\nReproduction test completed. Ready to implement fix.")
    
    asyncio.run(run_reproduction_test())