#!/usr/bin/env python3
"""
Simple test to verify example message processing works.
"""

import asyncio
import json
from datetime import datetime

async def test_example_message_processing():
    """Test processing an example message directly."""
    
    print("Testing Example Message Processing...")
    
    # Test message payload that matches the expected format
    test_payload = {
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
    
    try:
        # Test the deferred import approach we implemented
        from app.services.message_handlers import MessageHandlerService
        from app.services.thread_service import ThreadService
        
        print("SUCCESS: Imported message handler components")
        
        # Create a mock supervisor (since we don't need the full supervisor for this test)
        class MockSupervisor:
            pass
            
        # Create services
        thread_service = ThreadService()
        message_handler = MessageHandlerService(MockSupervisor(), thread_service)
        
        print("SUCCESS: Created message handler service")
        
        # Test that the method exists and can be called
        user_id = test_payload["user_id"]
        
        print(f"Testing example message handler for user: {user_id}")
        
        # This will test our new integration point
        await message_handler.handle_example_message(user_id, test_payload, None)
        
        print("SUCCESS: Example message handler executed without errors!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

async def test_websocket_message_structure():
    """Test that WebSocket messages are structured correctly."""
    
    print("\nTesting WebSocket Message Structure...")
    
    # Example WebSocket message that should be routed to example message handler
    websocket_message = {
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
    }
    
    try:
        from app.services.agent_service_core import AgentService
        print("SUCCESS: Can import AgentService")
        
        # Test message parsing
        message_str = json.dumps(websocket_message)
        print(f"SUCCESS: Can serialize WebSocket message: {len(message_str)} chars")
        
        # Test that the routing logic exists
        import inspect
        source = inspect.getsource(AgentService._handle_standard_message_types)
        if 'example_message' in source:
            print("SUCCESS: WebSocket message routing includes example_message")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_example_message_processing())
    asyncio.run(test_websocket_message_structure())