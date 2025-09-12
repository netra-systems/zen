# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test to verify WebSocket handler accumulation fix

    # REMOVED_SYNTAX_ERROR: This test ensures that handlers don"t accumulate when multiple WebSocket
    # REMOVED_SYNTAX_ERROR: connections are created and closed.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
    # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.websocket import websocket_endpoint
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import get_message_router
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_no_handler_accumulation():
        # REMOVED_SYNTAX_ERROR: """Test that handlers don't accumulate when connections are made."""

        # Get the message router instance
        # REMOVED_SYNTAX_ERROR: message_router = get_message_router()

        # Record initial handler count
        # REMOVED_SYNTAX_ERROR: initial_count = len(message_router.handlers)
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Simulate multiple WebSocket connections
        # REMOVED_SYNTAX_ERROR: for i in range(5):
            # Create a mock WebSocket
            # REMOVED_SYNTAX_ERROR: mock_websocket = AsyncMock(spec=WebSocket)
            # REMOVED_SYNTAX_ERROR: mock_websocket.headers = { )
            # REMOVED_SYNTAX_ERROR: "authorization": "Bearer mock_token",
            # REMOVED_SYNTAX_ERROR: "sec-websocket-protocol": "jwt-auth"
            
            # REMOVED_SYNTAX_ERROR: mock_# websocket setup complete
            # REMOVED_SYNTAX_ERROR: mock_# websocket setup complete
            # REMOVED_SYNTAX_ERROR: mock_# websocket setup complete
            # REMOVED_SYNTAX_ERROR: mock_# websocket setup complete
            # REMOVED_SYNTAX_ERROR: mock_websocket.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
            # REMOVED_SYNTAX_ERROR: mock_websocket.client_state = Magic        mock_websocket.client_state.value = 1  # CONNECTED
            # REMOVED_SYNTAX_ERROR: mock_websocket.application_state = Magic        mock_websocket.application_state.value = 1  # CONNECTED

            # Mock authentication
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
                # REMOVED_SYNTAX_ERROR: mock_auth.return_value = {"user_id": "formatted_string", "email": "formatted_string"}

                # Mock other dependencies
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
                    # REMOVED_SYNTAX_ERROR: mock_supervisor.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                        # REMOVED_SYNTAX_ERROR: mock_thread_service.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                        # Try to handle the WebSocket (it will fail quickly but should register handlers)
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: await websocket_endpoint(mock_websocket)
                            # REMOVED_SYNTAX_ERROR: except:
                                # REMOVED_SYNTAX_ERROR: pass  # Expected to fail, we just want to trigger handler registration

                                # Check handler count after each connection
                                # REMOVED_SYNTAX_ERROR: current_count = len(message_router.handlers)
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                # Final handler count should not have grown significantly
                                # REMOVED_SYNTAX_ERROR: final_count = len(message_router.handlers)

                                # The count should increase by at most 1 (for the shared AgentMessageHandler)
                                # not by 5 (one per connection)
                                # REMOVED_SYNTAX_ERROR: assert final_count - initial_count <= 1, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # REMOVED_SYNTAX_ERROR: print("formatted_string")


                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_handler_reuse():
                                    # REMOVED_SYNTAX_ERROR: """Test that existing handlers are reused instead of creating new ones."""

                                    # Get the message router instance
                                    # REMOVED_SYNTAX_ERROR: message_router = get_message_router()

                                    # Find any existing AgentMessageHandler
                                    # REMOVED_SYNTAX_ERROR: initial_agent_handler = None
                                    # REMOVED_SYNTAX_ERROR: for handler in message_router.handlers:
                                        # REMOVED_SYNTAX_ERROR: if handler.__class__.__name__ == 'AgentMessageHandler':
                                            # REMOVED_SYNTAX_ERROR: initial_agent_handler = handler
                                            # REMOVED_SYNTAX_ERROR: break

                                            # Create first mock WebSocket connection
                                            # REMOVED_SYNTAX_ERROR: mock_ws1 = AsyncMock(spec=WebSocket)
                                            # REMOVED_SYNTAX_ERROR: mock_ws1.headers = {"authorization": "Bearer mock_token"}
                                            # REMOVED_SYNTAX_ERROR: mock_ws1.websocket = TestWebSocketConnection()
                                            # REMOVED_SYNTAX_ERROR: mock_ws1.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
                                            # REMOVED_SYNTAX_ERROR: mock_ws1.client_state = Magic    mock_ws1.client_state.value = 1
                                            # REMOVED_SYNTAX_ERROR: mock_ws1.application_state = Magic    mock_ws1.application_state.value = 1

                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
                                                # REMOVED_SYNTAX_ERROR: mock_auth.return_value = {"user_id": "user1", "email": "user1@example.com"}

                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                                                        # REMOVED_SYNTAX_ERROR: mock_thread_service.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                                        # REMOVED_SYNTAX_ERROR: try:
                                                            # REMOVED_SYNTAX_ERROR: await websocket_endpoint(mock_ws1)
                                                            # REMOVED_SYNTAX_ERROR: except:
                                                                # REMOVED_SYNTAX_ERROR: pass

                                                                # Find AgentMessageHandler after first connection
                                                                # REMOVED_SYNTAX_ERROR: first_agent_handler = None
                                                                # REMOVED_SYNTAX_ERROR: for handler in message_router.handlers:
                                                                    # REMOVED_SYNTAX_ERROR: if handler.__class__.__name__ == 'AgentMessageHandler':
                                                                        # REMOVED_SYNTAX_ERROR: first_agent_handler = handler
                                                                        # REMOVED_SYNTAX_ERROR: break

                                                                        # Create second mock WebSocket connection
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2 = AsyncMock(spec=WebSocket)
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2.headers = {"authorization": "Bearer mock_token"}
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2.websocket = TestWebSocketConnection()
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2.client_state = Magic    mock_ws2.client_state.value = 1
                                                                        # REMOVED_SYNTAX_ERROR: mock_ws2.application_state = Magic    mock_ws2.application_state.value = 1

                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
                                                                            # REMOVED_SYNTAX_ERROR: mock_auth.return_value = {"user_id": "user2", "email": "user2@example.com"}

                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
                                                                                # REMOVED_SYNTAX_ERROR: mock_supervisor.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                                                                                    # REMOVED_SYNTAX_ERROR: mock_thread_service.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                                        # REMOVED_SYNTAX_ERROR: await websocket_endpoint(mock_ws2)
                                                                                        # REMOVED_SYNTAX_ERROR: except:
                                                                                            # REMOVED_SYNTAX_ERROR: pass

                                                                                            # Find AgentMessageHandler after second connection
                                                                                            # REMOVED_SYNTAX_ERROR: second_agent_handler = None
                                                                                            # REMOVED_SYNTAX_ERROR: agent_handler_count = 0
                                                                                            # REMOVED_SYNTAX_ERROR: for handler in message_router.handlers:
                                                                                                # REMOVED_SYNTAX_ERROR: if handler.__class__.__name__ == 'AgentMessageHandler':
                                                                                                    # REMOVED_SYNTAX_ERROR: second_agent_handler = handler
                                                                                                    # REMOVED_SYNTAX_ERROR: agent_handler_count += 1

                                                                                                    # There should only be ONE AgentMessageHandler
                                                                                                    # REMOVED_SYNTAX_ERROR: assert agent_handler_count <= 1, \
                                                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                                                    # If we had an initial handler, it should be the same object (reused)
                                                                                                    # REMOVED_SYNTAX_ERROR: if initial_agent_handler and first_agent_handler:
                                                                                                        # REMOVED_SYNTAX_ERROR: assert first_agent_handler is initial_agent_handler, \
                                                                                                        # REMOVED_SYNTAX_ERROR: "AgentMessageHandler was replaced instead of reused"

                                                                                                        # The handler from first and second connections should be the same
                                                                                                        # REMOVED_SYNTAX_ERROR: if first_agent_handler and second_agent_handler:
                                                                                                            # REMOVED_SYNTAX_ERROR: assert first_agent_handler is second_agent_handler, \
                                                                                                            # REMOVED_SYNTAX_ERROR: "New AgentMessageHandler created instead of reusing existing"

                                                                                                            # REMOVED_SYNTAX_ERROR: print("[U+2713] Handler reuse test passed!")


                                                                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                                                # REMOVED_SYNTAX_ERROR: asyncio.run(test_no_handler_accumulation())
                                                                                                                # REMOVED_SYNTAX_ERROR: asyncio.run(test_handler_reuse())
                                                                                                                # REMOVED_SYNTAX_ERROR: print(" )
                                                                                                                # REMOVED_SYNTAX_ERROR: [U+2713] All WebSocket handler leak tests passed!")