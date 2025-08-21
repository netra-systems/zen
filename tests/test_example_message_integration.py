#!/usr/bin/env python3
"""
Test script to verify the example message integration works end-to-end.
"""

import asyncio
import json
from datetime import datetime

async def test_example_message_flow():
    """Test the example message flow end-to-end."""
    
    print("🚀 Testing Example Message Flow Integration...")
    
    # Test message payload
    test_message = {
        "type": "example_message",
        "payload": {
            "content": "I want to optimize my AI costs while maintaining quality. We're currently spending $2000/month on GPT-4 calls.",
            "example_message_id": "test-123",
            "user_id": "test-user",
            "timestamp": int(datetime.now().timestamp()),
            "example_message_metadata": {
                "title": "Cost Optimization Test",
                "category": "cost-optimization",
                "complexity": "intermediate", 
                "businessValue": "conversion",
                "estimatedTime": "2-3 minutes"
            }
        }
    }
    
    try:
        # Import the message handler
        from app.services.message_handlers import MessageHandlerService
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.services.thread_service import ThreadService
        from app.llm.llm_manager import LLMManager
        from app.agents.tool_dispatcher import ToolDispatcher
        from app.ws_manager import manager
        
        print("✅ Imported required modules successfully")
        
        # Create mock database session
        class MockDBSession:
            pass
        
        # Create components
        llm_manager = LLMManager()
        tool_dispatcher = ToolDispatcher(MockDBSession())
        supervisor = SupervisorAgent(MockDBSession(), llm_manager, manager, tool_dispatcher)
        thread_service = ThreadService()
        message_handler = MessageHandlerService(supervisor, thread_service)
        
        print("✅ Created message handler components successfully")
        
        # Test the new example message handler
        user_id = test_message["payload"]["user_id"]
        payload = test_message["payload"]
        
        print(f"📨 Testing example message handler for user: {user_id}")
        
        # This should now work with our integration
        await message_handler.handle_example_message(user_id, payload, None)
        
        print("✅ Example message handler executed successfully!")
        print("🎉 Example message flow integration is working!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 This indicates missing dependencies or circular imports")
        
    except AttributeError as e:
        print(f"❌ Attribute error: {e}")
        print("🔧 This indicates the integration point is not properly connected")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("🔧 This indicates a deeper issue in the integration")
        import traceback
        traceback.print_exc()

async def test_handler_imports():
    """Test that the example message handler can be imported."""
    print("\n🧪 Testing Handler Imports...")
    
    try:
        from app.handlers.example_message_handler import handle_example_message, get_example_message_handler
        print("✅ Successfully imported example message handler")
        
        # Test creating a handler instance
        handler = get_example_message_handler()
        print(f"✅ Successfully created handler instance: {type(handler)}")
        
        # Test that the ExampleMessageProcessor can be imported
        from app.agents.example_message_processor import get_example_message_supervisor
        supervisor = get_example_message_supervisor()
        print(f"✅ Successfully created example message supervisor: {type(supervisor)}")
        
    except Exception as e:
        print(f"❌ Handler import error: {e}")
        import traceback
        traceback.print_exc()

async def test_websocket_message_routing():
    """Test that WebSocket messages can be routed to example message handler."""
    print("\n🌐 Testing WebSocket Message Routing...")
    
    try:
        from app.services.agent_service_core import AgentService
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.llm.llm_manager import LLMManager
        from app.agents.tool_dispatcher import ToolDispatcher
        from app.ws_manager import manager
        
        # Create components
        class MockDBSession:
            pass
        
        llm_manager = LLLManager()
        tool_dispatcher = ToolDispatcher(MockDBSession())
        supervisor = SupervisorAgent(MockDBSession(), llm_manager, manager, tool_dispatcher)
        agent_service = AgentService(supervisor)
        
        # Test message routing
        test_websocket_message = json.dumps({
            "type": "example_message",
            "payload": {
                "content": "Test optimization request",
                "example_message_id": "ws-test-123",
                "user_id": "websocket-test-user",
                "timestamp": int(datetime.now().timestamp()),
                "example_message_metadata": {
                    "title": "WebSocket Test",
                    "category": "cost-optimization",
                    "complexity": "basic", 
                    "businessValue": "conversion",
                    "estimatedTime": "1-2 minutes"
                }
            }
        })
        
        print("📨 Testing WebSocket message routing...")
        
        # This should route to our new example message handler
        await agent_service.handle_websocket_message("websocket-test-user", test_websocket_message, None)
        
        print("✅ WebSocket message routing successful!")
        
    except Exception as e:
        print(f"❌ WebSocket routing error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("🔬 Example Message Integration Test Suite")
    print("=" * 50)
    
    await test_handler_imports()
    await test_example_message_flow()
    await test_websocket_message_routing()
    
    print("\n" + "=" * 50)
    print("✨ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main())