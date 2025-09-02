#!/usr/bin/env python3
"""
Test script to verify WebSocket handler registration in user isolation context.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_handler_registration():
    """Test WebSocket handler registration."""
    print("Testing WebSocket handler registration...")
    print("=" * 60)
    
    # Import WebSocket core modules
    from netra_backend.app.websocket_core import (
        get_message_router,
        get_router_handler_count,
        list_registered_handlers,
        MessageType
    )
    
    # Get the message router
    router = get_message_router()
    
    # Check handler count
    handler_count = get_router_handler_count()
    print(f"Handler count: {handler_count}")
    
    # List all registered handlers
    handlers = list_registered_handlers()
    print(f"Registered handlers: {handlers}")
    
    # Check if base handlers are registered
    expected_handlers = [
        'HeartbeatHandler',
        'UserMessageHandler', 
        'JsonRpcHandler',
        'ErrorHandler'
    ]
    
    print("\nExpected base handlers:")
    for expected in expected_handlers:
        if expected in handlers:
            print(f"  [OK] {expected} - REGISTERED")
        else:
            print(f"  [MISSING] {expected} - MISSING")
    
    # Test handler capabilities
    print("\nHandler capabilities:")
    for handler in router.handlers:
        handler_name = handler.__class__.__name__
        supported_types = getattr(handler, 'supported_types', [])
        print(f"  {handler_name}:")
        for msg_type in supported_types:
            print(f"    - {msg_type}")
    
    # Test message routing
    print("\nTesting message routing:")
    test_messages = [
        {"type": "ping"},
        {"type": "user_message", "content": "test"},
        {"type": "error_message"},
        {"type": "chat", "content": "test chat"}
    ]
    
    for msg in test_messages:
        msg_type = msg.get("type")
        # Try to find a handler
        handler_found = False
        for handler in router.handlers:
            if hasattr(handler, 'can_handle'):
                try:
                    # Normalize message type
                    from netra_backend.app.websocket_core.types import normalize_message_type
                    normalized = normalize_message_type(msg_type)
                    if handler.can_handle(normalized):
                        handler_found = True
                        print(f"  {msg_type} -> {handler.__class__.__name__}")
                        break
                except:
                    pass
        
        if not handler_found:
            print(f"  {msg_type} -> NO HANDLER FOUND")
    
    # Test with app startup
    print("\n" + "=" * 60)
    print("Testing with FastAPI app initialization...")
    
    from fastapi import FastAPI
    from netra_backend.app.core.lifespan_manager import lifespan
    
    # Create app with lifespan
    app = FastAPI(lifespan=lifespan)
    
    # Initialize app state
    app.state.startup_complete = False
    app.state.startup_in_progress = False
    
    # Check handler count after app creation
    handler_count_after = get_router_handler_count()
    print(f"Handler count after app creation: {handler_count_after}")
    
    # Final verdict
    print("\n" + "=" * 60)
    print("FINAL VERDICT:")
    if handler_count >= len(expected_handlers):
        print("[SUCCESS] Base handlers are registered successfully!")
        if handler_count > len(expected_handlers):
            print(f"   Additional handlers: {handler_count - len(expected_handlers)}")
    else:
        print(f"[WARNING] Only {handler_count} handlers registered, expected at least {len(expected_handlers)}")
        print("   This indicates the WebSocket message router initialization issue")
    
    return handler_count >= len(expected_handlers)

if __name__ == "__main__":
    result = asyncio.run(test_handler_registration())
    sys.exit(0 if result else 1)