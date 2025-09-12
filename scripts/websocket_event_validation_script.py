#!/usr/bin/env python3
"""Quick validation script for WebSocket agent events integration.

This script validates that all 5 critical WebSocket events are properly implemented:
1. agent_started
2. agent_thinking  
3. tool_executing
4. tool_completed
5. agent_completed

Run this script to verify the integration is working correctly.
"""

import asyncio
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock


class WebSocketEventValidator:
    """Validates WebSocket event emission in the agent execution pipeline."""
    
    def __init__(self):
        self.captured_events: List[Dict[str, Any]] = []
        self.required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed", 
            "agent_completed"
        }
        
    async def mock_send_event(self, event_type: str, data: Dict[str, Any]):
        """Mock WebSocket event sending that captures events."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.captured_events.append(event)
        print(f"[U+1F4E1] Event: {event_type} - {data.get('agent_name', data.get('tool_name', 'unknown'))}")
        return True
        
    def get_captured_event_types(self) -> set:
        """Get set of captured event types."""
        return {event["type"] for event in self.captured_events}
        
    def validate_all_events_captured(self) -> bool:
        """Validate all required events were captured."""
        captured = self.get_captured_event_types()
        missing = self.required_events - captured
        
        if missing:
            print(f" FAIL:  Missing events: {missing}")
            print(f"   Captured: {captured}")
            return False
        else:
            print(f" PASS:  All required events captured: {captured}")
            return True
    
    def print_event_summary(self):
        """Print summary of captured events."""
        print(f"\n CHART:  Event Summary:")
        print(f"   Total events captured: {len(self.captured_events)}")
        print(f"   Unique event types: {len(self.get_captured_event_types())}")
        print(f"   Required events: {len(self.required_events)}")
        
        for event_type in sorted(self.get_captured_event_types()):
            count = sum(1 for e in self.captured_events if e["type"] == event_type)
            print(f"   - {event_type}: {count}")


async def test_websocket_integration():
    """Test WebSocket integration with mock components."""
    print("[U+1F680] Starting WebSocket Event Validation Test")
    print("=" * 60)
    
    validator = WebSocketEventValidator()
    
    try:
        # Import the required modules
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
        
        print(" PASS:  Successfully imported core modules")
        
        # Create test user context
        user_context = UserExecutionContext(
            user_id="validation_test_user",
            run_id="validation_test_run",
            thread_id="validation_test_thread"
        )
        print(f" PASS:  Created user context: {user_context.user_id}")
        
        # Create WebSocket bridge with mock manager
        bridge = AgentWebSocketBridge(user_context)
        
        # Mock the websocket manager to capture events
        mock_manager = AsyncMock()
        mock_manager.send_event = validator.mock_send_event
        bridge._websocket_manager = mock_manager
        
        print(" PASS:  Created WebSocket bridge with event capture")
        
        # Test individual WebSocket bridge methods
        print("\n CYCLE:  Testing individual WebSocket bridge methods...")
        
        # Test agent_started
        await bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name="TestAgent"
        )
        
        # Test agent_thinking
        await bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name="TestAgent", 
            reasoning="Testing reasoning display"
        )
        
        # Test tool_executing (via tool dispatcher)
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=bridge
        )
        
        # Register a simple test tool
        class SimpleTestTool:
            name = "validation_tool"
            
            async def arun(self, input_text: str = "test") -> str:
                await asyncio.sleep(0.01)  # Simulate brief work
                return f"Processed: {input_text}"
        
        test_tool = SimpleTestTool()
        dispatcher.register_tool(test_tool)
        
        print(f" PASS:  Created tool dispatcher with test tool: {test_tool.name}")
        
        # Execute tool (should trigger tool_executing and tool_completed)
        result = await dispatcher.execute_tool(
            "validation_tool",
            {"input_text": "WebSocket validation test"}
        )
        
        print(f" PASS:  Tool execution result: {result.success}")
        
        # Test agent_completed
        await bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name="TestAgent",
            result={"success": True, "message": "Validation complete"}
        )
        
        print("\n" + "=" * 60)
        print(" TARGET:  VALIDATION RESULTS")
        print("=" * 60)
        
        # Validate results
        validator.print_event_summary()
        
        success = validator.validate_all_events_captured()
        
        if success:
            print("\n CELEBRATION:  SUCCESS: All critical WebSocket events are properly implemented!")
            print("   The agent execution pipeline should now provide complete user visibility.")
            return True
        else:
            print("\n FAIL:  FAILURE: Missing critical WebSocket events!")
            print("   Users may experience 'stuck agent' behavior due to missing events.")
            return False
            
    except ImportError as e:
        print(f" FAIL:  Import Error: {e}")
        print("   Ensure all required modules are available")
        return False
    except Exception as e:
        print(f" FAIL:  Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    print("WebSocket Agent Events Validation Script")
    print("Testing the 5 critical events for substantive chat interactions")
    print()
    
    success = await test_websocket_integration()
    
    if success:
        print("\n PASS:  Validation passed - WebSocket events are properly integrated")
        sys.exit(0)
    else:
        print("\n FAIL:  Validation failed - WebSocket event integration needs fixes")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())