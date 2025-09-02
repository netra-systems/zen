#!/usr/bin/env python
"""Isolated test for WebSocket bridge lifecycle audit."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set test environment
os.environ['TEST_ENV'] = 'true'
os.environ['WEBSOCKET_BRIDGE_TEST'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'

from tests.mission_critical.test_websocket_bridge_lifecycle_audit_20250902 import (
    TestAgent,
    WebSocketBridgeLifecycleAuditor,
    EventCapture
)

async def test_bridge_setting_isolated():
    """Test that demonstrates bridge setting mechanism in isolation."""
    print("Testing WebSocket bridge setting mechanism...")
    
    # Create auditor and set up test environment
    auditor = WebSocketBridgeLifecycleAuditor()
    execution_engine, registry, bridges = await auditor.setup_test_environment()
    
    # Create and register test agent
    test_agent = TestAgent("IsolatedTestAgent")
    registry.register("IsolatedTestAgent", test_agent)
    
    # Verify agent initially has no bridge
    assert not test_agent.websocket_bridge_set
    print("+ Agent initially has no WebSocket bridge")
    
    # Test direct bridge setting (simulating AgentExecutionCore behavior)
    bridge = list(bridges.values())[0]
    run_id = "test-run-123"
    
    test_agent.set_websocket_bridge(bridge, run_id)
    
    # Verify bridge was set correctly
    assert test_agent.websocket_bridge_set
    assert test_agent.websocket_bridge_instance is not None
    assert test_agent.run_id_received == run_id
    print("+ WebSocket bridge set correctly on agent")
    
    # Test that agent can emit events after bridge is set
    await test_agent.emit_thinking("Test thinking message")
    print("+ Agent can emit events with bridge set")
    
    # Cleanup
    await auditor.cleanup_test_environment()
    print("+ Test completed successfully")

async def test_event_capture():
    """Test the event capture mechanism."""
    print("Testing event capture mechanism...")
    
    capture = EventCapture()
    
    # Test basic event capture
    capture.capture_event("test_event", {"message": "test"})
    events = capture.get_events_by_type("test_event")
    assert len(events) == 1
    assert events[0]['data']['message'] == "test"
    print("+ Basic event capture works")
    
    # Test event sequence validation
    capture.capture_event("event_1", {})
    capture.capture_event("event_2", {})
    capture.capture_event("event_3", {})
    
    assert capture.validate_event_sequence(["test_event", "event_1", "event_2"])
    print("+ Event sequence validation works")
    
    # Test thread safety (basic)
    capture.clear()
    assert len(capture.events) == 0
    print("+ Event capture cleanup works")

async def main():
    """Run all isolated tests."""
    print("Starting WebSocket Bridge Lifecycle Isolated Tests")
    print("=" * 50)
    
    try:
        await test_event_capture()
        print()
        await test_bridge_setting_isolated()
        
        print()
        print("=" * 50)
        print("All isolated tests PASSED!")
        
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())