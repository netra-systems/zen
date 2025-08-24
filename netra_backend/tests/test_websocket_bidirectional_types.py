# WebSocket type tests using available fixtures
from test_framework.fixtures.websocket_types import (
    MockWebSocketConnection,
    MockWebSocketManager,
    MockWebSocketMessage,
    MockMessageType,
    create_mock_websocket_connection,
    setup_mock_websocket_scenario
)
import pytest
import asyncio


class TestWebSocketBidirectionalTypes:
    """Test WebSocket bidirectional type handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_message_types(self):
        """Test WebSocket message type handling."""
        connection = create_mock_websocket_connection("test_user")
        await connection.connect()
        
        # Test different message types
        message_types = [
            MockMessageType.USER_INPUT,
            MockMessageType.AGENT_RESPONSE,
            MockMessageType.SYSTEM_NOTIFICATION,
            MockMessageType.HEARTBEAT
        ]
        
        for msg_type in message_types:
            message = MockWebSocketMessage(
                type=msg_type,
                data={"test": f"data for {msg_type}"}
            )
            
            await connection.send_message(message)
            assert len(connection.sent_messages) > 0
            assert connection.sent_messages[-1].type == msg_type
        
        await connection.disconnect()
    
    @pytest.mark.asyncio
    async def test_bidirectional_communication(self):
        """Test bidirectional WebSocket communication."""
        scenario = await setup_mock_websocket_scenario(user_count=2)
        manager = scenario["manager"]
        connections = scenario["connections"]
        
        # Send from first to second user
        user_message = MockWebSocketMessage(
            type=MockMessageType.USER_INPUT,
            data={"content": "Hello from user 1"}
        )
        
        await connections[0].send_message(user_message)
        
        # Simulate response
        response_message = MockWebSocketMessage(
            type=MockMessageType.AGENT_RESPONSE,
            data={"content": "Response to user 1"}
        )
        
        await connections[1].send_message(response_message)
        
        # Verify bidirectional flow
        assert len(connections[0].sent_messages) == 1
        assert len(connections[1].sent_messages) == 1
        assert connections[0].sent_messages[0].type == MockMessageType.USER_INPUT
        assert connections[1].sent_messages[0].type == MockMessageType.AGENT_RESPONSE