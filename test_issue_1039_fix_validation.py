#!/usr/bin/env python3
"""
Test to validate the fix for Issue #1039: WebSocket tool_executing validation missing tool_name field.

This test confirms that tool_executing events now include the required tool_name field
at the top level of the event structure for frontend and validation compatibility.
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


class Issue1039FixValidationTest(SSotAsyncTestCase):
    """Test to validate the fix for issue #1039 - tool_executing now has tool_name field."""
    
    async def setup_test_environment(self):
        """Set up test environment for validating the fix."""
        self.mock_manager = MagicMock()
        self.test_user_id = "test_user_1039_fix"
        self.test_context = MagicMock()
        self.test_context.user_id = self.test_user_id
        self.test_context.thread_id = "test_thread_1039_fix"
        self.test_context.run_id = "test_run_1039_fix"
        
        # Create emitter instance
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Track emitted events
        self.emitted_events = []
        
        # Mock the manager's emit_critical_event method to capture final event structure
        async def mock_emit_critical_event(user_id, event_type, data):
            final_event = {
                "type": event_type,
                "user_id": user_id,
                "timestamp": time.time(),
                **data  # This should include tool_name at top level after fix
            }
            self.emitted_events.append(final_event)
            return True
        
        self.mock_manager.emit_critical_event = AsyncMock(side_effect=mock_emit_critical_event)
        self.mock_manager.is_connection_active = MagicMock(return_value=True)
    
    async def test_fix_validation_tool_executing_has_tool_name_at_top_level(self):
        """VALIDATION: Confirm tool_executing events now have tool_name at top level."""
        await self.setup_test_environment()
        
        # Test the fixed implementation
        tool_name = "cost_analyzer_fixed"
        metadata = {"query": "analyze costs", "table": "expenses"}
        
        # Emit tool_executing event using fixed implementation
        await self.emitter.notify_tool_executing(tool_name, metadata)
        
        # Verify event was emitted
        assert len(self.emitted_events) == 1, "Expected 1 tool_executing event to be emitted"
        
        tool_executing_event = self.emitted_events[0]
        assert tool_executing_event["type"] == "tool_executing", "Event type should be tool_executing"
        
        # CRITICAL VALIDATION: Check if tool_name is at the top level (should pass after fix)
        print(f"Final event structure: {tool_executing_event}")
        
        assert "tool_name" in tool_executing_event, f"ISSUE #1039 FIX FAILED: tool_executing event still missing tool_name field at top level. Event: {tool_executing_event}"
        assert tool_executing_event["tool_name"] == tool_name, f"tool_name value incorrect. Expected '{tool_name}', got: {tool_executing_event.get('tool_name')}"
        
        # Verify other expected fields are still present
        assert "metadata" in tool_executing_event, "metadata field should still be present"
        assert "status" in tool_executing_event, "status field should still be present"
        assert "timestamp" in tool_executing_event, "timestamp field should still be present"
        
        print("SUCCESS: Issue #1039 fix validated - tool_executing events now have tool_name at top level")
    
    async def test_fix_validation_other_events_not_affected(self):
        """VALIDATION: Confirm the fix doesn't break other event types."""
        await self.setup_test_environment()
        
        # Test that other events (like agent_thinking) are not affected by the fix
        await self.emitter.notify_agent_thinking(agent_name="test_agent", reasoning="thinking process")
        
        # Verify event was emitted
        assert len(self.emitted_events) == 1, "Expected 1 agent_thinking event to be emitted"
        
        thinking_event = self.emitted_events[0]
        assert thinking_event["type"] == "agent_thinking", "Event type should be agent_thinking"
        
        # Should have reasoning field and not be affected by tool_name promotion logic
        assert "reasoning" in thinking_event, "agent_thinking events should still have reasoning field"
        
        print("SUCCESS: Other event types not affected by Issue #1039 fix")
    
    async def test_fix_validation_frontend_compatibility(self):
        """VALIDATION: Confirm the fix makes events compatible with frontend expectations."""
        await self.setup_test_environment()
        
        # Test with the exact fields that frontend expects (based on frontend test)
        tool_name = "search_analyzer"
        metadata = {"args": {"query": "test search"}, "run_id": "test_run_123"}
        
        await self.emitter.notify_tool_executing(tool_name, metadata)
        
        tool_executing_event = self.emitted_events[0]
        
        # Frontend expects these fields at top level according to test_frontend_routing_auth.py
        required_frontend_fields = ["tool_name"]  # args and run_id might come from other sources
        
        for field in required_frontend_fields:
            assert field in tool_executing_event, f"Frontend requires '{field}' field at top level, but it's missing from: {tool_executing_event}"
        
        print("SUCCESS: tool_executing events now compatible with frontend expectations")


if __name__ == "__main__":
    async def run_fix_validation():
        test = Issue1039FixValidationTest()
        
        print("Testing Issue #1039 fix validation...")
        await test.test_fix_validation_tool_executing_has_tool_name_at_top_level()
        await test.test_fix_validation_other_events_not_affected()
        await test.test_fix_validation_frontend_compatibility()
        
        print("\nAll fix validation tests passed! Issue #1039 remediation successful.")
    
    asyncio.run(run_fix_validation())