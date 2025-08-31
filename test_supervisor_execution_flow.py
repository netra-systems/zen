#!/usr/bin/env python
"""
Test actual supervisor execution flow to verify WebSocket events.
"""

import asyncio
import sys
import os
import uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState
from unittest.mock import AsyncMock


class EventCaptureWebSocketManager:
    """WebSocket manager that captures events for testing."""
    
    def __init__(self):
        self.events = []
        self.connections = {}
    
    async def send_to_thread(self, thread_id: str, message_data: dict) -> bool:
        """Capture event instead of sending."""
        event = {
            'thread_id': thread_id,
            'message': message_data,
            'timestamp': asyncio.get_event_loop().time()
        }
        self.events.append(event)
        
        event_type = message_data.get('type', 'unknown')
        print(f"🎯 WebSocket Event: {event_type} -> {thread_id}")
        
        if 'payload' in message_data:
            payload = message_data['payload']
            if isinstance(payload, dict):
                if 'agent_name' in payload:
                    print(f"   Agent: {payload['agent_name']}")
                if 'thought' in payload:
                    print(f"   Thought: {payload['thought'][:50]}...")
                if 'tool_name' in payload:
                    print(f"   Tool: {payload['tool_name']}")
        
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock connection."""
        self.connections[thread_id] = {'user_id': user_id, 'connected': True}
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock disconnection."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
    
    def get_event_types(self) -> list:
        """Get all captured event types."""
        return [event['message'].get('type', 'unknown') for event in self.events]


async def test_supervisor_execution_flow():
    """Test actual supervisor execution to see if WebSocket events are sent."""
    
    print("🔍 Testing Supervisor Execution Flow with WebSocket Events...")
    print("=" * 70)
    
    # Create event capturing WebSocket manager
    ws_manager = EventCaptureWebSocketManager()
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Create tool dispatcher
    tool_dispatcher = ToolDispatcher()
    
    # Create mock LLM manager
    llm_manager = AsyncMock()
    llm_manager.generate = AsyncMock(return_value={
        "content": "Test response from supervisor",
        "reasoning": "Processing the user request step by step"
    })
    
    try:
        # Create supervisor
        print("1. Creating SupervisorAgent with event capture...")
        supervisor = SupervisorAgent(
            db_session=mock_db,
            llm_manager=llm_manager,
            websocket_manager=ws_manager,
            tool_dispatcher=tool_dispatcher
        )
        print("✅ SupervisorAgent created")
        
        # Create test state
        print("\n2. Creating test execution state...")
        test_thread_id = "test_thread_123"
        test_run_id = "run_456"
        test_user_id = "user_789"
        
        state = DeepAgentState()
        state.user_request = "What is the system status?"
        state.chat_thread_id = test_thread_id
        state.run_id = test_run_id
        state.user_id = test_user_id
        
        print(f"✅ State created - Thread: {test_thread_id}, Run: {test_run_id}")
        
        # Clear any setup events
        ws_manager.events.clear()
        print(f"\n3. Executing supervisor with event monitoring...")
        
        # Execute supervisor - this should trigger WebSocket events
        try:
            await supervisor.execute(state, test_run_id, stream_updates=True)
            print("✅ Supervisor execution completed")
        except Exception as e:
            print(f"⚠️  Supervisor execution had error: {e} (this may be expected in test)")
        
        # Check captured events
        print(f"\n4. Analyzing captured WebSocket events...")
        print(f"   Total events captured: {len(ws_manager.events)}")
        
        event_types = ws_manager.get_event_types()
        event_counts = {}
        for event_type in event_types:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        print(f"   Event types: {list(event_counts.keys())}")
        
        # Check for critical events
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        print(f"\n5. Checking for critical WebSocket events...")
        missing_events = []
        found_events = []
        
        for event in critical_events:
            if event in event_counts:
                found_events.append(event)
                print(f"   ✅ {event}: {event_counts[event]} events")
            else:
                missing_events.append(event)
                print(f"   ❌ {event}: NOT SENT")
        
        # Detailed event analysis
        print(f"\n6. Detailed Event Analysis:")
        for i, event in enumerate(ws_manager.events[:10]):  # Show first 10 events
            event_type = event['message'].get('type', 'unknown')
            thread = event['thread_id']
            print(f"   [{i+1}] {event_type} -> {thread}")
        
        if len(ws_manager.events) > 10:
            print(f"   ... and {len(ws_manager.events) - 10} more events")
        
        # Summary
        print(f"\n" + "=" * 70)
        print(f"🏁 EXECUTION FLOW ANALYSIS SUMMARY:")
        print(f"=" * 70)
        
        if ws_manager.events:
            print(f"✅ WebSocket Manager: RECEIVING EVENTS")
            print(f"   Total events: {len(ws_manager.events)}")
            print(f"   Event types: {len(event_counts)} unique types")
        else:
            print(f"❌ WebSocket Manager: NO EVENTS RECEIVED")
            print(f"   This indicates WebSocket integration may not be working")
        
        if found_events:
            print(f"✅ Critical Events Found: {len(found_events)}/{len(critical_events)}")
            print(f"   Found: {found_events}")
        
        if missing_events:
            print(f"⚠️  Missing Critical Events: {len(missing_events)}")
            print(f"   Missing: {missing_events}")
        
        # Determine success
        if len(found_events) >= 3:  # At least 3 critical events
            print(f"\n🎉 SUCCESS: Supervisor WebSocket integration is working!")
            print(f"   Critical events are being sent during execution")
            return True
        elif ws_manager.events:
            print(f"\n⚠️  PARTIAL: Some events sent, but missing critical ones")
            print(f"   WebSocket integration partially working")
            return False
        else:
            print(f"\n❌ FAILURE: No WebSocket events detected")
            print(f"   WebSocket integration not working")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during execution flow test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("🧪 Supervisor Execution Flow WebSocket Test")
    print("=" * 70)
    
    success = await test_supervisor_execution_flow()
    
    if success:
        print("\n✅ SUCCESS: WebSocket events are being sent during supervisor execution")
        sys.exit(0)
    else:
        print("\n❌ ISSUES: WebSocket events may not be working properly")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())