"""Test that verifies the fix for 'user' and 'agent' message types."""

import asyncio
import pytest
from unittest.mock import AsyncMock
from fastapi import WebSocket

from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.types import MessageType


class TestUserAgentMessageTypes:
    """Test suite to verify the fix for 'user' and 'agent' message types."""
    
    @pytest.mark.asyncio
    async def test_user_message_type_routing(self):
        """Test that 'user' message type is properly routed."""
        # Setup
        router = MessageRouter()
        user_id = "7c5e1032-ed21-4aea-b12a-aeddf3622bec"
        
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Create a message with 'user' type (the problematic type from the error)
        raw_message = {
            "type": "user",
            "payload": {"content": "Hello from user"},
            "id": "msg_123"
        }
        
        # Act - This should now work with the fix
        result = await router.route_message(user_id, mock_websocket, raw_message)
        
        # Assert - The router should handle 'user' type correctly
        assert result == True, "Router should handle 'user' message type"
        
        # Check routing stats to verify it was routed
        stats = router.get_stats()
        assert stats["messages_routed"] > 0, "Message should be counted as routed"
    
    @pytest.mark.asyncio
    async def test_agent_message_type_routing(self):
        """Test that 'agent' message type is properly routed."""
        # Setup
        router = MessageRouter()
        user_id = "7c5e1032-ed21-4aea-b12a-aeddf3622bec"
        
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Create a message with 'agent' type (another problematic type)
        raw_message = {
            "type": "agent",
            "payload": {
                "action": "start",
                "agent_type": "supervisor",
                "message": "Process this request"
            },
            "id": "msg_456"
        }
        
        # Act - This should now work with the fix
        result = await router.route_message(user_id, mock_websocket, raw_message)
        
        # Assert - The router should handle 'agent' type correctly
        assert result == True, "Router should handle 'agent' message type"
        
        # Check routing stats
        stats = router.get_stats()
        assert stats["messages_routed"] > 0, "Message should be counted as routed"
    
    @pytest.mark.asyncio
    async def test_legacy_type_mapping_verification(self):
        """Verify that the LEGACY_MESSAGE_TYPE_MAP contains the fix."""
        from netra_backend.app.websocket_core.types import LEGACY_MESSAGE_TYPE_MAP
        
        # Assert that the problematic types are now in the map
        assert "user" in LEGACY_MESSAGE_TYPE_MAP, "'user' should be in legacy map"
        assert "agent" in LEGACY_MESSAGE_TYPE_MAP, "'agent' should be in legacy map"
        
        # Verify they map to correct MessageType values
        assert LEGACY_MESSAGE_TYPE_MAP["user"] == MessageType.USER_MESSAGE
        assert LEGACY_MESSAGE_TYPE_MAP["agent"] == MessageType.AGENT_REQUEST
    
    @pytest.mark.asyncio
    async def test_message_type_not_detected_as_unknown(self):
        """Test that 'user' and 'agent' are not detected as unknown types."""
        router = MessageRouter()
        
        # Test internal method that checks for unknown types
        is_user_unknown = router._is_unknown_message_type("user")
        is_agent_unknown = router._is_unknown_message_type("agent")
        
        # Assert - These should NOT be unknown anymore
        assert is_user_unknown == False, "'user' should not be unknown"
        assert is_agent_unknown == False, "'agent' should not be unknown"
    
    @pytest.mark.asyncio
    async def test_full_websocket_simulation(self):
        """Simulate the actual websocket endpoint flow with fixed message types."""
        from netra_backend.app.websocket_core import get_message_router
        
        # Get the actual message router instance (singleton)
        router = get_message_router()
        
        user_id = "7c5e1032-ed21-4aea-b12a-aeddf3622bec"
        connection_id = f"conn_{user_id}_405ad7f8"
        
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Test both problematic message types
        test_messages = [
            {
                "type": "user",
                "payload": {"content": "User message test"},
                "id": "msg_user"
            },
            {
                "type": "agent",
                "payload": {
                    "action": "execute",
                    "agent_type": "supervisor",
                    "task": "analyze"
                },
                "id": "msg_agent"
            }
        ]
        
        for message_data in test_messages:
            # This simulates what websocket.py does at line 506
            success = await router.route_message(user_id, mock_websocket, message_data)
            
            # Assert - Should not fail anymore
            assert isinstance(success, bool), f"route_message should return bool for {message_data['type']}"
            assert success == True, f"Message type '{message_data['type']}' should be routed successfully"
            
            # Verify no error was logged (by checking the message was handled)
            print(f"✓ Successfully routed message type: {message_data['type']}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])