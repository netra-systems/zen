#!/usr/bin/env python
"""
Quick test to verify supervisor WebSocket integration.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState
from unittest.mock import AsyncMock


async def test_supervisor_websocket_integration():
    """Test if supervisor is properly integrated with WebSocket notifications."""
    
    print("🔍 Testing Supervisor WebSocket Integration...")
    print("=" * 60)
    
    # Create mock database session
    mock_db = AsyncMock()
    
    # Create WebSocket manager
    websocket_manager = WebSocketManager()
    
    # Create tool dispatcher
    tool_dispatcher = ToolDispatcher()
    
    # Create LLM manager mock
    llm_manager = AsyncMock()
    
    try:
        # Create supervisor
        print("1. Creating SupervisorAgent...")
        supervisor = SupervisorAgent(
            db_session=mock_db,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        print("✅ SupervisorAgent created successfully")
        
        # Check WebSocket manager integration
        print("\n2. Checking WebSocket Manager Integration...")
        assert supervisor.websocket_manager == websocket_manager, "WebSocket manager not set"
        print("✅ WebSocket manager is set on supervisor")
        
        # Check registry WebSocket integration
        print("\n3. Checking Registry WebSocket Integration...")
        assert supervisor.registry.websocket_manager == websocket_manager, "Registry doesn't have WebSocket manager"
        print("✅ Registry has WebSocket manager")
        
        # Check tool dispatcher enhancement
        print("\n4. Checking Tool Dispatcher Enhancement...")
        if hasattr(tool_dispatcher, '_websocket_enhanced'):
            enhancement_status = tool_dispatcher._websocket_enhanced
            print(f"✅ Tool dispatcher WebSocket enhancement: {enhancement_status}")
        else:
            print("❌ Tool dispatcher WebSocket enhancement status unknown")
        
        # Check ExecutionEngine WebSocket integration
        print("\n5. Checking ExecutionEngine WebSocket Integration...")
        if hasattr(supervisor, 'engine'):
            engine = supervisor.engine
            if hasattr(engine, 'websocket_manager'):
                print("✅ ExecutionEngine has WebSocket manager")
                if hasattr(engine, 'websocket_notifier'):
                    print("✅ ExecutionEngine has WebSocket notifier")
                else:
                    print("❌ ExecutionEngine missing WebSocket notifier")
            else:
                print("❌ ExecutionEngine missing WebSocket manager")
        else:
            print("❌ Supervisor missing ExecutionEngine")
        
        # Test WebSocket notification methods
        print("\n6. Testing WebSocket Notification Methods...")
        if hasattr(supervisor, 'engine') and hasattr(supervisor.engine, 'websocket_notifier'):
            notifier = supervisor.engine.websocket_notifier
            notification_methods = [
                'send_agent_started',
                'send_agent_thinking', 
                'send_tool_executing',
                'send_tool_completed',
                'send_agent_completed'
            ]
            
            missing_methods = []
            for method_name in notification_methods:
                if hasattr(notifier, method_name):
                    print(f"✅ {method_name} method available")
                else:
                    missing_methods.append(method_name)
                    print(f"❌ {method_name} method missing")
            
            if missing_methods:
                print(f"\n❌ Missing critical notification methods: {missing_methods}")
            else:
                print(f"\n✅ All critical notification methods available")
        else:
            print("❌ Cannot test notification methods - no WebSocket notifier")
        
        # Check supervisor execution path
        print("\n7. Checking Supervisor Execution Path...")
        state = DeepAgentState()
        state.user_request = "test request"
        state.chat_thread_id = "test_thread"
        state.run_id = "test_run"
        
        # Check if supervisor uses the WebSocket-enhanced engine
        if hasattr(supervisor, 'engine'):
            print("✅ Supervisor has ExecutionEngine for WebSocket events")
        else:
            print("❌ Supervisor missing ExecutionEngine - events may not be sent")
        
        print("\n" + "=" * 60)
        print("🏁 INTEGRATION TEST SUMMARY:")
        print("=" * 60)
        
        # Final assessment
        critical_components = [
            (hasattr(supervisor, 'websocket_manager'), "SupervisorAgent has WebSocket manager"),
            (hasattr(supervisor, 'registry'), "SupervisorAgent has registry"),
            (supervisor.registry.websocket_manager is not None, "Registry has WebSocket manager"),
            (hasattr(supervisor, 'engine'), "SupervisorAgent has ExecutionEngine"),
        ]
        
        if hasattr(supervisor, 'engine'):
            critical_components.extend([
                (hasattr(supervisor.engine, 'websocket_manager'), "ExecutionEngine has WebSocket manager"),
                (hasattr(supervisor.engine, 'websocket_notifier'), "ExecutionEngine has WebSocket notifier"),
            ])
        
        passed = sum(1 for check, _ in critical_components if check)
        total = len(critical_components)
        
        print(f"\nCritical Components: {passed}/{total} ✅")
        for check, description in critical_components:
            status = "✅" if check else "❌"
            print(f"  {status} {description}")
        
        if passed == total:
            print("\n🎉 SUPERVISOR WEBSOCKET INTEGRATION: FULLY CONFIGURED")
            print("   All WebSocket events should be sent during agent execution")
            return True
        else:
            print(f"\n⚠️  SUPERVISOR WEBSOCKET INTEGRATION: PARTIAL ({passed}/{total})")
            print("   Some WebSocket events may not be sent")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("🧪 Quick Supervisor WebSocket Integration Test")
    print("=" * 60)
    
    success = await test_supervisor_websocket_integration()
    
    if success:
        print("\n✅ SUCCESS: WebSocket integration is properly configured")
        sys.exit(0)
    else:
        print("\n❌ ISSUES: WebSocket integration needs fixes")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())