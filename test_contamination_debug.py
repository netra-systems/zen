#!/usr/bin/env python3
"""Debug script for contamination prevention issue."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, "/Users/anthony/Desktop/netra-apex")

from unittest.mock import Mock, AsyncMock
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from shared.types.core_types import UserID, ensure_user_id

async def debug_contamination_prevention():
    """Debug the contamination prevention logic."""
    
    # Create mock WebSocket manager
    mock_manager = Mock(spec=WebSocketManagerProtocol)
    mock_manager.send_to_user = AsyncMock()
    mock_manager.get_user_connections = Mock(return_value=[
        {"connection_id": "conn_1", "user_id": "performance_user_123"}
    ])
    
    # Create service
    service = WebSocketBroadcastService(mock_manager)
    
    # Test event with contaminated user_id
    target_user = "secure_user_789"
    contaminated_event = {
        "type": "agent_message",
        "data": {"message": "Response for user"},
        "user_id": "wrong_user_999",  # EVENT DATA: preserved for audit/provenance
        "sender_id": "different_user_888",  # EVENT DATA: preserved for attribution
        "target_user_id": "another_user_777"  # ROUTING FIELD: sanitized for security
    }
    
    print(f"Original event: {contaminated_event}")
    print(f"Target user: {target_user}")
    
    # Call broadcast method
    result = await service.broadcast_to_user(target_user, contaminated_event)
    
    print(f"Result: {result}")
    print(f"Result errors: {result.errors}")
    
    # Get the actual sent event
    if mock_manager.send_to_user.called:
        call_args = mock_manager.send_to_user.call_args
        sent_event = call_args[0][1]  # Second argument is the event
        print(f"Event sent to WebSocket manager: {sent_event}")
        
        # Check what happened to each field
        print(f"Original user_id: {contaminated_event.get('user_id')}")
        print(f"Sent user_id: {sent_event.get('user_id')}")
        print(f"Original sender_id: {contaminated_event.get('sender_id')}")
        print(f"Sent sender_id: {sent_event.get('sender_id')}")
        print(f"Original target_user_id: {contaminated_event.get('target_user_id')}")
        print(f"Sent target_user_id: {sent_event.get('target_user_id')}")
        
        # Check event data preservation (user_id, sender_id should be preserved)
        if (sent_event.get('user_id') == contaminated_event.get('user_id') and
            sent_event.get('sender_id') == contaminated_event.get('sender_id')):
            print("✅ SUCCESS: Event data fields (user_id, sender_id) were preserved")
        else:
            print("❌ FAILURE: Event data fields were modified when they should have been preserved")
            
        # Check routing field sanitization (target_user_id should be fixed to target_user)
        if sent_event.get('target_user_id') == target_user:
            print("✅ SUCCESS: Routing field (target_user_id) was sanitized to target user")
        else:
            print("❌ FAILURE: Routing field was not properly sanitized")
    else:
        print("❌ FAILURE: send_to_user was not called")

if __name__ == "__main__":
    asyncio.run(debug_contamination_prevention())