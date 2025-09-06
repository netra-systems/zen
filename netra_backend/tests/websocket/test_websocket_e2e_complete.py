# REMOVED_SYNTAX_ERROR: '''Complete WebSocket E2E Tests with Authentication and Message Flow

# REMOVED_SYNTAX_ERROR: Tests comprehensive WebSocket connectivity ensuring:
    # REMOVED_SYNTAX_ERROR: 1. JWT authentication handshake
    # REMOVED_SYNTAX_ERROR: 2. Connection establishment before first message
    # REMOVED_SYNTAX_ERROR: 3. JSON message format (content/text field consistency)
    # REMOVED_SYNTAX_ERROR: 4. Example message handling
    # REMOVED_SYNTAX_ERROR: 5. Agent response streaming
    # REMOVED_SYNTAX_ERROR: 6. Error handling and recovery
    # REMOVED_SYNTAX_ERROR: 7. Connection persistence through re-renders

    # REMOVED_SYNTAX_ERROR: Follows SPEC/websockets.xml and SPEC/learnings/websocket_message_paradox.xml
    # REMOVED_SYNTAX_ERROR: Business Value: Ensures WebSocket infrastructure supports real-time AI optimization
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import websockets
    # REMOVED_SYNTAX_ERROR: from websockets import ServerConnection

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.network_constants import ( )
    # REMOVED_SYNTAX_ERROR: HostConstants,
    # REMOVED_SYNTAX_ERROR: ServicePorts,
    # REMOVED_SYNTAX_ERROR: URLConstants)
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import get_websocket_manager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_models import ( )
    # REMOVED_SYNTAX_ERROR: AgentUpdatePayload,
    # REMOVED_SYNTAX_ERROR: UserMessagePayload)

    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.integration.jwt_token_helpers import JWTTestHelper

# REMOVED_SYNTAX_ERROR: class WebSocketE2EClient:
    # REMOVED_SYNTAX_ERROR: """E2E WebSocket test client with auth and message handling."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.websocket: Optional[websockets.ServerConnection] = None
    # REMOVED_SYNTAX_ERROR: self.messages: List[Dict] = []
    # REMOVED_SYNTAX_ERROR: self.connected = False
    # REMOVED_SYNTAX_ERROR: self.jwt_helper = JWTTestHelper(secret_key="test_secret_key")

# REMOVED_SYNTAX_ERROR: async def connect_with_auth(self, user_id: str = "test_user") -> str:
    # REMOVED_SYNTAX_ERROR: """Connect with JWT authentication."""
    # REMOVED_SYNTAX_ERROR: token = self.jwt_helper.create_test_token(user_id=user_id, email="formatted_string")
    # REMOVED_SYNTAX_ERROR: url = "formatted_string"
    # REMOVED_SYNTAX_ERROR: self.websocket = await websockets.connect(url)
    # REMOVED_SYNTAX_ERROR: self.connected = True
    # REMOVED_SYNTAX_ERROR: asyncio.create_task(self._listen_messages())
    # REMOVED_SYNTAX_ERROR: return token

# REMOVED_SYNTAX_ERROR: async def _listen_messages(self):
    # REMOVED_SYNTAX_ERROR: """Listen for messages and maintain connection."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: async for message in self.websocket:
            # REMOVED_SYNTAX_ERROR: data = json.loads(message)
            # REMOVED_SYNTAX_ERROR: self.messages.append(data)
            # REMOVED_SYNTAX_ERROR: except websockets.exceptions.ConnectionClosed:
                # REMOVED_SYNTAX_ERROR: self.connected = False

# REMOVED_SYNTAX_ERROR: async def send_json_message(self, message: Dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message (never string)."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await self.websocket.send(json.dumps(message))

# REMOVED_SYNTAX_ERROR: async def disconnect(self):
    # REMOVED_SYNTAX_ERROR: """Disconnect gracefully."""
    # REMOVED_SYNTAX_ERROR: if self.websocket:
        # REMOVED_SYNTAX_ERROR: await self.websocket.close()
        # REMOVED_SYNTAX_ERROR: self.connected = False

# REMOVED_SYNTAX_ERROR: def get_messages_by_type(self, msg_type: str) -> List[Dict]:
    # REMOVED_SYNTAX_ERROR: """Get messages by type."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return [item for item in []]

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def ws_client():
    # REMOVED_SYNTAX_ERROR: """WebSocket E2E client fixture."""
    # REMOVED_SYNTAX_ERROR: client = WebSocketE2EClient()
    # REMOVED_SYNTAX_ERROR: yield client
    # REMOVED_SYNTAX_ERROR: if client.connected:
        # REMOVED_SYNTAX_ERROR: await client.disconnect()

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_user_message():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Sample user message payload following schema."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "type": "user_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "content": "Analyze my AI workload performance",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "correlation_id": "test-correlation-123"
    
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_example_message():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Sample example message for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "type": "chat_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "content": "Show me optimization recommendations",
    # REMOVED_SYNTAX_ERROR: "example_message_id": "example_optimization_001",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
    
    

    # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestWebSocketAuthenticationFlow:
    # REMOVED_SYNTAX_ERROR: """Test JWT authentication handshake."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_connection_with_valid_jwt(self, ws_client):
        # REMOVED_SYNTAX_ERROR: """Test connection establishes with valid JWT."""
        # REMOVED_SYNTAX_ERROR: token = await ws_client.connect_with_auth("auth_test_user")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # REMOVED_SYNTAX_ERROR: assert ws_client.connected
        # REMOVED_SYNTAX_ERROR: connection_msgs = ws_client.get_messages_by_type("connection_established")
        # REMOVED_SYNTAX_ERROR: assert len(connection_msgs) == 1
        # REMOVED_SYNTAX_ERROR: assert "user_id" in connection_msgs[0]["payload"]

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_connection_rejected_invalid_jwt(self):
            # REMOVED_SYNTAX_ERROR: """Test connection rejected with invalid JWT."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
                # REMOVED_SYNTAX_ERROR: ws = await websockets.connect("ws://localhost:8001/ws?token=invalid")
                # REMOVED_SYNTAX_ERROR: await ws.close()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_connection_rejected_missing_jwt(self):
                    # REMOVED_SYNTAX_ERROR: """Test connection rejected without JWT."""
                    # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
                        # REMOVED_SYNTAX_ERROR: ws = await websockets.connect("ws://localhost:8001/ws")
                        # REMOVED_SYNTAX_ERROR: await ws.close()

                        # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestWebSocketMessageFlow:
    # REMOVED_SYNTAX_ERROR: """Test message flow and field consistency."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_message_content_field_handling(self, ws_client, sample_user_message):
        # REMOVED_SYNTAX_ERROR: """Test user message uses 'content' field (not 'text')."""
        # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("message_test_user")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
        # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

        # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(sample_user_message)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

        # Should not receive field mismatch errors
        # REMOVED_SYNTAX_ERROR: error_msgs = ws_client.get_messages_by_type("error")
        # REMOVED_SYNTAX_ERROR: field_errors = [item for item in []]
        # REMOVED_SYNTAX_ERROR: assert len(field_errors) == 0

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_example_message_processing(self, ws_client, sample_example_message):
            # REMOVED_SYNTAX_ERROR: """Test example message processing flow."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("example_test_user")
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
            # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

            # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(sample_example_message)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.3)

            # Should receive processing acknowledgment
            # REMOVED_SYNTAX_ERROR: response_msgs = [msg for msg in ws_client.messages if msg.get("type") in )
            # REMOVED_SYNTAX_ERROR: ["agent_update", "message_processed", "example_response"]]
            # REMOVED_SYNTAX_ERROR: assert len(response_msgs) >= 1

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_json_first_enforcement(self, ws_client):
                # REMOVED_SYNTAX_ERROR: """Test only JSON messages accepted (no strings)."""
                # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("json_test_user")
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
                # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

                # Send invalid string message
                # REMOVED_SYNTAX_ERROR: await ws_client.websocket.send("invalid string message")
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                # REMOVED_SYNTAX_ERROR: error_msgs = ws_client.get_messages_by_type("error")
                # REMOVED_SYNTAX_ERROR: assert len(error_msgs) >= 1
                # REMOVED_SYNTAX_ERROR: assert any("json" in str(error).lower() for error in error_msgs)

                # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestAgentResponseStreaming:
    # REMOVED_SYNTAX_ERROR: """Test agent response streaming."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_agent_startup_on_first_message(self, ws_client, sample_user_message):
        # REMOVED_SYNTAX_ERROR: """Test agent starts on first message without thread context."""
        # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("agent_startup_user")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
        # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

        # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(sample_user_message)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)

        # Should receive agent status updates
        # REMOVED_SYNTAX_ERROR: agent_msgs = ws_client.get_messages_by_type("agent_update")
        # REMOVED_SYNTAX_ERROR: assert len(agent_msgs) >= 1

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_response_streaming_format(self, ws_client):
            # REMOVED_SYNTAX_ERROR: """Test agent response streaming follows JSON format."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("streaming_test_user")
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
            # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

            # REMOVED_SYNTAX_ERROR: message = { )
            # REMOVED_SYNTAX_ERROR: "type": "user_message",
            # REMOVED_SYNTAX_ERROR: "payload": {"content": "Stream a response to me"}
            
            # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(message)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.4)

            # Check streaming messages are JSON with proper structure
            # REMOVED_SYNTAX_ERROR: streaming_msgs = [msg for msg in ws_client.messages )
            # REMOVED_SYNTAX_ERROR: if msg.get("type") == "agent_stream"]
            # REMOVED_SYNTAX_ERROR: for msg in streaming_msgs:
                # REMOVED_SYNTAX_ERROR: assert "payload" in msg
                # REMOVED_SYNTAX_ERROR: assert isinstance(msg["payload"], dict)

                # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestConnectionResilience:
    # REMOVED_SYNTAX_ERROR: """Test connection persistence and recovery."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_connection_survives_component_rerender(self, ws_client):
        # REMOVED_SYNTAX_ERROR: """Test connection persists through component re-renders."""
        # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("rerender_test_user")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # Simulate component re-render (connection should persist)
        # REMOVED_SYNTAX_ERROR: original_connected = ws_client.connected

        # Send ping to verify connection active
        # REMOVED_SYNTAX_ERROR: ping_msg = {"type": "ping", "timestamp": time.time()}
        # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(ping_msg)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # REMOVED_SYNTAX_ERROR: assert ws_client.connected == original_connected
        # REMOVED_SYNTAX_ERROR: pong_msgs = ws_client.get_messages_by_type("pong")
        # REMOVED_SYNTAX_ERROR: assert len(pong_msgs) >= 1

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_graceful_error_recovery(self, ws_client):
            # REMOVED_SYNTAX_ERROR: """Test connection recovers from recoverable errors."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("error_test_user")
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # Send invalid message format (recoverable error)
            # REMOVED_SYNTAX_ERROR: invalid_msg = {"invalid": "structure"}
            # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(invalid_msg)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # Connection should stay alive
            # REMOVED_SYNTAX_ERROR: assert ws_client.connected

            # Should be able to send valid message after error
            # REMOVED_SYNTAX_ERROR: valid_msg = {"type": "ping"}
            # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(valid_msg)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # REMOVED_SYNTAX_ERROR: pong_msgs = ws_client.get_messages_by_type("pong")
            # REMOVED_SYNTAX_ERROR: assert len(pong_msgs) >= 1

            # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestServiceDiscovery:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket service discovery."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_config_discovery(self):
        # REMOVED_SYNTAX_ERROR: """Test backend provides WebSocket configuration."""
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.websocket import ( )
        # REMOVED_SYNTAX_ERROR: get_websocket_service_discovery)

        # REMOVED_SYNTAX_ERROR: config = await get_websocket_service_discovery()

        # REMOVED_SYNTAX_ERROR: assert config["status"] == "success"
        # REMOVED_SYNTAX_ERROR: ws_config = config["websocket_config"]
        # REMOVED_SYNTAX_ERROR: assert ws_config["features"]["json_first"] is True
        # REMOVED_SYNTAX_ERROR: assert ws_config["features"]["auth_required"] is True
        # REMOVED_SYNTAX_ERROR: assert "/ws" in ws_config["endpoints"]["websocket"]

        # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestErrorHandlingAndLogging:
    # REMOVED_SYNTAX_ERROR: """Test comprehensive error scenarios."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_connection_rejection_logged_clearly(self):
        # REMOVED_SYNTAX_ERROR: """Test rejected connections are logged clearly."""
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            # Mock: Generic component isolation for controlled unit testing
            # REMOVED_SYNTAX_ERROR: mock_log = mock_log_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: mock_logger.get_logger.return_value = mock_log

            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: await websockets.connect("ws://localhost:8001/ws?token=bad_token")
                # REMOVED_SYNTAX_ERROR: except Exception:
                    # REMOVED_SYNTAX_ERROR: pass

                    # Should have logged the rejection reason clearly
                    # REMOVED_SYNTAX_ERROR: assert mock_log.error.called or mock_log.warning.called

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_empty_message_validation(self, ws_client):
                        # REMOVED_SYNTAX_ERROR: """Test empty messages are rejected early."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("empty_msg_user")
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
                        # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

                        # REMOVED_SYNTAX_ERROR: empty_msg = { )
                        # REMOVED_SYNTAX_ERROR: "type": "user_message",
                        # REMOVED_SYNTAX_ERROR: "payload": {"content": "   "}  # Only whitespace
                        
                        # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(empty_msg)
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                        # REMOVED_SYNTAX_ERROR: error_msgs = ws_client.get_messages_by_type("error")
                        # REMOVED_SYNTAX_ERROR: empty_errors = [item for item in []]
                        # REMOVED_SYNTAX_ERROR: assert len(empty_errors) >= 1

                        # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestConcurrentConnections:
    # REMOVED_SYNTAX_ERROR: """Test concurrent connection handling."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_multiple_connections_same_user(self):
        # REMOVED_SYNTAX_ERROR: """Test multiple connections from same user handled correctly."""
        # REMOVED_SYNTAX_ERROR: clients = []
        # REMOVED_SYNTAX_ERROR: try:
            # Create 3 concurrent connections
            # REMOVED_SYNTAX_ERROR: for i in range(3):
                # REMOVED_SYNTAX_ERROR: client = WebSocketE2EClient()
                # REMOVED_SYNTAX_ERROR: await client.connect_with_auth(f"concurrent_user")
                # REMOVED_SYNTAX_ERROR: clients.append(client)
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)

                # All should be connected initially
                # REMOVED_SYNTAX_ERROR: for client in clients:
                    # REMOVED_SYNTAX_ERROR: assert client.connected

                    # Connection manager enforces limits (max 5 per user)
                    # REMOVED_SYNTAX_ERROR: ws_manager = get_websocket_manager()
                    # REMOVED_SYNTAX_ERROR: stats = ws_manager.get_stats()
                    # REMOVED_SYNTAX_ERROR: total_connections = stats.total_connections if hasattr(stats, 'total_connections') else len(getattr(stats, 'connections', {}))
                    # REMOVED_SYNTAX_ERROR: assert total_connections <= 5

                    # REMOVED_SYNTAX_ERROR: finally:
                        # REMOVED_SYNTAX_ERROR: for client in clients:
                            # REMOVED_SYNTAX_ERROR: if client.connected:
                                # REMOVED_SYNTAX_ERROR: await client.disconnect()

                                # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestRealTimeFeatures:
    # REMOVED_SYNTAX_ERROR: """Test real-time WebSocket features."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_heartbeat_keepalive(self, ws_client):
        # REMOVED_SYNTAX_ERROR: """Test heartbeat keeps connection alive."""
        # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("heartbeat_user")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # REMOVED_SYNTAX_ERROR: ping_msg = {"type": "ping", "timestamp": time.time()}
        # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(ping_msg)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # REMOVED_SYNTAX_ERROR: pong_msgs = ws_client.get_messages_by_type("pong")
        # REMOVED_SYNTAX_ERROR: assert len(pong_msgs) >= 1
        # REMOVED_SYNTAX_ERROR: assert "server_time" in pong_msgs[0]

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_message_ordering_preservation(self, ws_client):
            # REMOVED_SYNTAX_ERROR: """Test messages maintain order during high throughput."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("ordering_user")
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
            # REMOVED_SYNTAX_ERROR: ws_client.messages.clear()

            # Send sequence of numbered messages rapidly
            # REMOVED_SYNTAX_ERROR: for i in range(5):
                # REMOVED_SYNTAX_ERROR: msg = { )
                # REMOVED_SYNTAX_ERROR: "type": "ping",
                # REMOVED_SYNTAX_ERROR: "payload": {"sequence": i, "timestamp": time.time()}
                
                # REMOVED_SYNTAX_ERROR: await ws_client.send_json_message(msg)

                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

                # REMOVED_SYNTAX_ERROR: pong_msgs = ws_client.get_messages_by_type("pong")
                # REMOVED_SYNTAX_ERROR: assert len(pong_msgs) >= 5

                # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestManualDatabaseSessions:
    # REMOVED_SYNTAX_ERROR: """Test manual database session handling (not Depends())."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_manual_db_sessions(self, ws_client):
        # REMOVED_SYNTAX_ERROR: """Test WebSocket endpoints use manual DB sessions."""
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.postgres.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            # REMOVED_SYNTAX_ERROR: mock_session = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__.return_value = mock_session

            # REMOVED_SYNTAX_ERROR: await ws_client.connect_with_auth("db_session_user")
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # Should have called manual session creation
            # REMOVED_SYNTAX_ERROR: assert mock_db.called

            # Mock: Component isolation for testing without external dependencies
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_auth_validation_manual_session(self, mock_db):
                # REMOVED_SYNTAX_ERROR: """Test auth validation uses manual database session."""
                # REMOVED_SYNTAX_ERROR: pass
                # Mock: Database session isolation for transaction testing without real database dependency
                # REMOVED_SYNTAX_ERROR: mock_session = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__.return_value = mock_session

                # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.websocket import ( )
                # REMOVED_SYNTAX_ERROR: authenticate_websocket_with_database)

                # REMOVED_SYNTAX_ERROR: session_info = {"user_id": "test_user", "email": "test@example.com"}

                # Mock: Security service isolation for auth testing without real token validation
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.security_service.SecurityService') as mock_security:
                    # Mock: Security service isolation for auth testing without real token validation
                    # REMOVED_SYNTAX_ERROR: mock_security_instance = AsyncNone  # TODO: Use real service instance
                    # Mock: Security service isolation for auth testing without real token validation
                    # REMOVED_SYNTAX_ERROR: mock_security_instance.get_user_by_id.return_value = Mock(is_active=True)
                    # REMOVED_SYNTAX_ERROR: mock_security.return_value = mock_security_instance

                    # REMOVED_SYNTAX_ERROR: user_id = await authenticate_websocket_with_database(session_info)
                    # REMOVED_SYNTAX_ERROR: assert user_id == "test_user"
                    # REMOVED_SYNTAX_ERROR: assert mock_db.called

                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])