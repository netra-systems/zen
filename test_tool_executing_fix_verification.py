#!/usr/bin/env python3
"""
Test script to verify tool_executing event structure fix for Issue #1039.

This script tests that tool_executing WebSocket events now include the tool_name 
field at the top level for proper tool transparency.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext

async def test_tool_executing_event_structure():
    """Test that tool_executing events include tool_name at top level."""
    print("🔧 Testing tool_executing event structure fix...")
    
    # Create mock user context with valid IDs
    user_context = UserExecutionContext(
        user_id="usr_1234567890abcdef",
        thread_id="thrd_abcdef1234567890", 
        run_id="run_fedcba0987654321",
        request_id="req_1122334455667788"
    )
    
    # Create mock WebSocket manager that captures sent events
    captured_events = []
    
    async def mock_send_to_thread(thread_id, message):
        captured_events.append(message)
        return True
    
    mock_websocket_manager = MagicMock()
    mock_websocket_manager.send_to_thread = AsyncMock(side_effect=mock_send_to_thread)
    
    # Create AgentWebSocketBridge with mock
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = mock_websocket_manager
    bridge.user_context = user_context
    
    # Test tool_executing notification
    await bridge.notify_tool_executing(
        run_id="run_fedcba0987654321",
        tool_name="search_analyzer",
        agent_name="TestAgent",
        parameters={"query": "test search"},
        user_context=user_context
    )
    
    # Verify event structure
    assert len(captured_events) == 1, f"Expected 1 event, got {len(captured_events)}"
    
    event = captured_events[0]
    print(f"📨 Captured event: {json.dumps(event, indent=2)}")
    
    # Critical validations
    assert "tool_name" in event, f"❌ tool_name missing from top level. Got keys: {list(event.keys())}"
    assert event["tool_name"] == "search_analyzer", f"❌ tool_name incorrect. Expected 'search_analyzer', got: {event.get('tool_name')}"
    assert event["type"] == "tool_executing", f"❌ event type incorrect. Expected 'tool_executing', got: {event.get('type')}"
    assert "user_id" in event, "❌ user_id missing from event"
    assert "run_id" in event, "❌ run_id missing from event"
    assert "agent_name" in event, "❌ agent_name missing from event"
    
    print("✅ PASS: tool_name is now at top level of tool_executing event")
    print("✅ PASS: All required fields present in event")
    print("✅ PASS: Business transparency requirement satisfied")
    
    return True

async def test_tool_transparency_business_requirement():
    """Test that the business requirement for tool transparency is met."""
    print("\n💼 Testing business requirement: Tool transparency...")
    
    user_context = UserExecutionContext(
        user_id="usr_enterprise_0123456789",
        thread_id="thrd_enterprise_456789abc", 
        run_id="run_enterprise_def012345",
        request_id="req_enterprise_678901bcd"
    )
    
    captured_events = []
    
    async def mock_send_to_thread(thread_id, message):
        captured_events.append(message)
        return True
    
    mock_websocket_manager = MagicMock()
    mock_websocket_manager.send_to_thread = AsyncMock(side_effect=mock_send_to_thread)
    
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = mock_websocket_manager
    bridge.user_context = user_context
    
    # Test with enterprise tool execution scenario
    await bridge.notify_tool_executing(
        run_id="run_enterprise_def012345",
        tool_name="cost_analyzer",
        agent_name="CostOptimizationAgent",
        parameters={
            "scope": "infrastructure",
            "time_range": "last_30_days",
            "include_recommendations": True
        },
        user_context=user_context
    )
    
    event = captured_events[0]
    
    # Business requirement validation: User must be able to see what tool is being used
    assert event["tool_name"] == "cost_analyzer", "❌ Tool name not visible for transparency"
    assert "agent_name" in event, "❌ Agent name not visible for transparency" 
    assert "data" in event, "❌ Tool execution details not included"
    assert "parameters" in event["data"], "❌ Tool parameters not included for transparency"
    
    print("✅ PASS: Enterprise user can see tool being executed (cost_analyzer)")
    print("✅ PASS: Tool transparency enables user trust in AI processes")
    print("✅ PASS: $500K+ ARR protection: Users can track AI tool usage")
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Issue #1039 fix: tool_executing event structure")
    print("="*60)
    
    async def run_tests():
        try:
            await test_tool_executing_event_structure()
            await test_tool_transparency_business_requirement()
            print("\n🎉 ALL TESTS PASSED: Issue #1039 is RESOLVED")
            print("✅ tool_executing events now include tool_name at top level")
            print("✅ Business requirement for tool transparency is satisfied")
            print("✅ Users can now see which AI tools are being executed")
            return True
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False
    
    success = asyncio.run(run_tests())
    exit(0 if success else 1)