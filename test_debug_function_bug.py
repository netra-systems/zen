"""Debug script to understand why the function bug isn't triggering"""

import asyncio
from unittest.mock import Mock, AsyncMock
from netra_backend.app.websocket_core.handlers import MessageRouter

# Create a simple test
def debug_function_bug():
    print("=== DEBUGGING FUNCTION BUG ===")
    
    router = MessageRouter()
    
    # Create the problematic function from websocket_ssot.py
    async def agent_handler(user_id: str, websocket, message):
        print(f"Function handler called with: {user_id}, {message}")
        return True
    
    print(f"Function handler type: {type(agent_handler)}")
    print(f"Has can_handle: {hasattr(agent_handler, 'can_handle')}")
    print(f"Has handle_message: {hasattr(agent_handler, 'handle_message')}")
    
    # Add the function to router
    router.add_handler(agent_handler)
    print(f"Custom handlers count: {len(router.custom_handlers)}")
    print(f"Custom handlers: {router.custom_handlers}")
    
    # Try to call can_handle directly
    try:
        result = agent_handler.can_handle("test")
        print(f"can_handle result: {result}")
    except AttributeError as e:
        print(f"Direct can_handle call failed: {e}")
    
    # Try _find_handler
    try:
        from netra_backend.app.websocket_core.types import MessageType
        handler = router._find_handler(MessageType.AGENT_REQUEST)
        print(f"_find_handler result: {handler}")
    except AttributeError as e:
        print(f"_find_handler failed: {e}")
    
    # Try route_message
    mock_websocket = Mock()
    mock_websocket.send_json = AsyncMock()
    mock_websocket.application_state = Mock()
    mock_websocket.application_state._mock_name = "test"
    
    sample_message = {
        "type": "agent_request",
        "payload": {"message": "test"},
        "user_id": "test_user"
    }
    
    try:
        result = asyncio.run(router.route_message("test_user", mock_websocket, sample_message))
        print(f"route_message result: {result}")
    except AttributeError as e:
        print(f"route_message failed: {e}")
    except Exception as e:
        print(f"route_message other error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    debug_function_bug()