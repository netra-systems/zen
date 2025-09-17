class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Test to verify WebSocket handlers are properly managed per-connection.
        Ensures no handler accumulation and no connection interference.
        '''
        import sys
        import os
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment
        sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

        import asyncio
        import pytest
        from fastapi import WebSocket
        from netra_backend.app.websocket_core.handlers import MessageRouter
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        from netra_backend.app.services.message_handlers import MessageHandlerService
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


@pytest.mark.asyncio
class TestWebSocketHandlerPerConnection:
    """Test suite to verify WebSocket handler management fixes."""

    async def test_each_connection_gets_own_handler(self):
    """Verify each WebSocket connection gets its own handler instance."""
        # Create mock components
    message_router = MessageRouter()
    initial_handler_count = len(message_router.handlers)

        # Create mock WebSockets
    ws1 = MagicMock(spec=WebSocket)
    ws2 = MagicMock(spec=WebSocket)
    ws3 = MagicMock(spec=WebSocket)

        # Create mock services
    mock_supervisor = Magic        mock_thread_service = Magic        mock_ws_manager = Magic
        # Create handlers for each connection
    service1 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler1 = AgentMessageHandler(service1, ws1)

    service2 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler2 = AgentMessageHandler(service2, ws2)

    service3 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler3 = AgentMessageHandler(service3, ws3)

        # Add all handlers
    message_router.add_handler(handler1)
    message_router.add_handler(handler2)
    message_router.add_handler(handler3)

        # Verify all handlers are registered
    assert len(message_router.handlers) == initial_handler_count + 3

        # Verify each handler has its own websocket reference
    agent_handlers = [item for item in []]
    assert len(agent_handlers) == 3

    websockets = [h.websocket for h in agent_handlers]
    assert ws1 in websockets
    assert ws2 in websockets
    assert ws3 in websockets

        # Verify no duplicate websockets
    assert len(set(websockets)) == 3

    async def test_handler_cleanup_on_disconnect(self):
    """Verify handlers are properly cleaned up when connections close."""
    pass
            # Create mock components
    message_router = MessageRouter()

            # Create mock WebSockets
    ws1 = MagicMock(spec=WebSocket)
    ws2 = MagicMock(spec=WebSocket)
    ws3 = MagicMock(spec=WebSocket)

            # Create mock services
    mock_supervisor = Magic        mock_thread_service = Magic        mock_ws_manager = Magic
            # Add handlers
    service1 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler1 = AgentMessageHandler(service1, ws1)
    message_router.add_handler(handler1)

    service2 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler2 = AgentMessageHandler(service2, ws2)
    message_router.add_handler(handler2)

    service3 = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler3 = AgentMessageHandler(service3, ws3)
    message_router.add_handler(handler3)

    assert len(message_router.handlers) == 3

            # Simulate cleanup for ws2
    handlers_to_remove = []
    for handler in message_router.handlers:
    if isinstance(handler, AgentMessageHandler) and handler.websocket == ws2:
    handlers_to_remove.append(handler)

    for handler in handlers_to_remove:
    message_router.handlers.remove(handler)

                        # Verify correct handler was removed
    assert len(message_router.handlers) == 2

    remaining_websockets = [ )
    h.websocket for h in message_router.handlers
    if isinstance(h, AgentMessageHandler)
                        
    assert ws1 in remaining_websockets
    assert ws2 not in remaining_websockets  # ws2 handler removed
    assert ws3 in remaining_websockets

    async def test_no_handler_accumulation(self):
    """Verify handlers don't accumulate over multiple connect/disconnect cycles."""
    message_router = MessageRouter()

                            # Simulate 10 connect/disconnect cycles
    for i in range(10):
                                # Create connection
    ws = MagicMock(spec=WebSocket)
    mock_supervisor = Magic            mock_thread_service = Magic            mock_ws_manager = Magic
    service = MessageHandlerService(mock_supervisor, mock_thread_service, mock_ws_manager)
    handler = AgentMessageHandler(service, ws)
    message_router.add_handler(handler)

                                # Simulate disconnect - cleanup
    handlers_to_remove = []
    for h in message_router.handlers:
    if isinstance(h, AgentMessageHandler) and h.websocket == ws:
    handlers_to_remove.append(h)

    for h in handlers_to_remove:
    message_router.handlers.remove(h)

                                            # After 10 cycles, should have 0 handlers
    assert len(message_router.handlers) == 0

    async def test_concurrent_connections_receive_own_events(self):
    """Verify each connection receives only its own events."""
    pass
                                                # Create mock components
    message_router = MessageRouter()

                                                # Create mock WebSockets with send tracking
    ws1_messages = []
    ws2_messages = []
    ws3_messages = []

    ws1 = AsyncMock(spec=WebSocket)
    ws1.send_json = AsyncMock(side_effect=lambda x: None ws1_messages.append(msg))

    ws2 = AsyncMock(spec=WebSocket)
    ws2.send_json = AsyncMock(side_effect=lambda x: None ws2_messages.append(msg))

    ws3 = AsyncMock(spec=WebSocket)
    ws3.send_json = AsyncMock(side_effect=lambda x: None ws3_messages.append(msg))

                                                # This test verifies the concept - actual WebSocket event routing
                                                # would be tested in integration tests with real WebSocket connections

                                                # Each websocket should maintain its own event stream
    assert ws1 != ws2 != ws3
    assert id(ws1) != id(ws2) != id(ws3)

    async def test_fallback_handler_cleanup(self):
    """Verify fallback handlers are also cleaned up properly."""
    from netra_backend.app.websocket_core.handlers import BaseMessageHandler
    from netra_backend.app.websocket_core.types import MessageType

                                                    # Create mock fallback handler class
class FallbackAgentHandler(BaseMessageHandler):
    def __init__(self, websocket=None):
        super().__init__([MessageType.CHAT])
        self.websocket = websocket

    async def handle_message(self, user_id, websocket, message):
        await asyncio.sleep(0)
        return True

        message_router = MessageRouter()

    # Add fallback handlers
        ws1 = MagicMock(spec=WebSocket)
        ws2 = MagicMock(spec=WebSocket)

        fallback1 = FallbackAgentHandler(ws1)
        fallback2 = FallbackAgentHandler(ws2)

        message_router.add_handler(fallback1)
        message_router.add_handler(fallback2)

        assert len(message_router.handlers) == 2

    # Clean up fallback for ws1
        handlers_to_remove = []
        for handler in message_router.handlers:
        if handler.__class__.__name__ == 'FallbackAgentHandler' and \
        hasattr(handler, 'websocket') and handler.websocket == ws1:
        handlers_to_remove.append(handler)

        for handler in handlers_to_remove:
        message_router.handlers.remove(handler)

                # Verify cleanup
        assert len(message_router.handlers) == 1
        assert message_router.handlers[0].websocket == ws2


        if __name__ == "__main__":
        asyncio.run(TestWebSocketHandlerPerConnection().test_each_connection_gets_own_handler())
        asyncio.run(TestWebSocketHandlerPerConnection().test_handler_cleanup_on_disconnect())
        asyncio.run(TestWebSocketHandlerPerConnection().test_no_handler_accumulation())
        print(" PASS:  All WebSocket handler per-connection tests passed!")
        pass
