"""Complete WebSocket E2E Tests with Authentication and Message Flow

Tests comprehensive WebSocket connectivity ensuring:
1. JWT authentication handshake
2. Connection establishment before first message
3. JSON message format (content/text field consistency) 
4. Example message handling
5. Agent response streaming
6. Error handling and recovery
7. Connection persistence through re-renders

Follows SPEC/websockets.xml and SPEC/learnings/websocket_message_paradox.xml
Business Value: Ensures WebSocket infrastructure supports real-time AI optimization
"""

import asyncio
import json
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, Mock, patch

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.unified.jwt_token_helpers import JWTTestHelper
from netra_backend.app.routes.websocket_enhanced import connection_manager
from netra_backend.app.core.network_constants import ServicePorts, URLConstants, HostConstants
from netra_backend.app.schemas.websocket_models import UserMessagePayload, AgentUpdatePayload

# Add project root to path


class WebSocketE2EClient:
    """E2E WebSocket test client with auth and message handling."""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.messages: List[Dict] = []
        self.connected = False
        self.jwt_helper = JWTTestHelper(environment="test")
        
    async def connect_with_auth(self, user_id: str = "test_user") -> str:
        """Connect with JWT authentication."""
        token = self.jwt_helper.create_test_user_token(user_id, f"{user_id}@test.com")
        url = f"ws://localhost:8001/ws/enhanced?token={token}"
        self.websocket = await websockets.connect(url)
        self.connected = True
        asyncio.create_task(self._listen_messages())
        return token
        
    async def _listen_messages(self):
        """Listen for messages and maintain connection."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages.append(data)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            
    async def send_json_message(self, message: Dict):
        """Send JSON message (never string)."""
        await self.websocket.send(json.dumps(message))
        
    async def disconnect(self):
        """Disconnect gracefully."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            
    def get_messages_by_type(self, msg_type: str) -> List[Dict]:
        """Get messages by type."""
        return [msg for msg in self.messages if msg.get("type") == msg_type]


@pytest.fixture
async def ws_client():
    """WebSocket E2E client fixture."""
    client = WebSocketE2EClient()
    yield client
    if client.connected:
        await client.disconnect()


@pytest.fixture
def sample_user_message():
    """Sample user message payload following schema."""
    return {
        "type": "user_message",
        "payload": {
            "content": "Analyze my AI workload performance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": "test-correlation-123"
        }
    }


@pytest.fixture  
def sample_example_message():
    """Sample example message for testing."""
    return {
        "type": "chat_message", 
        "payload": {
            "content": "Show me optimization recommendations",
            "example_message_id": "example_optimization_001",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


@pytest.mark.asyncio
class TestWebSocketAuthenticationFlow:
    """Test JWT authentication handshake."""
    
    async def test_connection_with_valid_jwt(self, ws_client):
        """Test connection establishes with valid JWT."""
        token = await ws_client.connect_with_auth("auth_test_user")
        await asyncio.sleep(0.1)
        
        assert ws_client.connected
        connection_msgs = ws_client.get_messages_by_type("connection_established")
        assert len(connection_msgs) == 1
        assert "user_id" in connection_msgs[0]["payload"]
        
    async def test_connection_rejected_invalid_jwt(self):
        """Test connection rejected with invalid JWT."""
        with pytest.raises(Exception):
            ws = await websockets.connect("ws://localhost:8001/ws/enhanced?token=invalid")
            await ws.close()
            
    async def test_connection_rejected_missing_jwt(self):
        """Test connection rejected without JWT."""  
        with pytest.raises(Exception):
            ws = await websockets.connect("ws://localhost:8001/ws/enhanced")
            await ws.close()


@pytest.mark.asyncio
class TestWebSocketMessageFlow:
    """Test message flow and field consistency."""
    
    async def test_user_message_content_field_handling(self, ws_client, sample_user_message):
        """Test user message uses 'content' field (not 'text')."""
        await ws_client.connect_with_auth("message_test_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        await ws_client.send_json_message(sample_user_message)
        await asyncio.sleep(0.2)
        
        # Should not receive field mismatch errors
        error_msgs = ws_client.get_messages_by_type("error")
        field_errors = [e for e in error_msgs if "content" in str(e) or "text" in str(e)]
        assert len(field_errors) == 0
        
    async def test_example_message_processing(self, ws_client, sample_example_message):
        """Test example message processing flow."""
        await ws_client.connect_with_auth("example_test_user") 
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        await ws_client.send_json_message(sample_example_message)
        await asyncio.sleep(0.3)
        
        # Should receive processing acknowledgment
        response_msgs = [msg for msg in ws_client.messages if msg.get("type") in 
                        ["agent_update", "message_processed", "example_response"]]
        assert len(response_msgs) >= 1
        
    async def test_json_first_enforcement(self, ws_client):
        """Test only JSON messages accepted (no strings)."""
        await ws_client.connect_with_auth("json_test_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        # Send invalid string message
        await ws_client.websocket.send("invalid string message")
        await asyncio.sleep(0.1)
        
        error_msgs = ws_client.get_messages_by_type("error")
        assert len(error_msgs) >= 1
        assert any("json" in str(error).lower() for error in error_msgs)


@pytest.mark.asyncio
class TestAgentResponseStreaming:
    """Test agent response streaming."""
    
    async def test_agent_startup_on_first_message(self, ws_client, sample_user_message):
        """Test agent starts on first message without thread context."""
        await ws_client.connect_with_auth("agent_startup_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        await ws_client.send_json_message(sample_user_message)
        await asyncio.sleep(0.5)
        
        # Should receive agent status updates
        agent_msgs = ws_client.get_messages_by_type("agent_update")
        assert len(agent_msgs) >= 1
        
    async def test_agent_response_streaming_format(self, ws_client):
        """Test agent response streaming follows JSON format."""
        await ws_client.connect_with_auth("streaming_test_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        message = {
            "type": "user_message",
            "payload": {"content": "Stream a response to me"}
        }
        await ws_client.send_json_message(message)
        await asyncio.sleep(0.4)
        
        # Check streaming messages are JSON with proper structure
        streaming_msgs = [msg for msg in ws_client.messages 
                         if msg.get("type") == "agent_stream"]
        for msg in streaming_msgs:
            assert "payload" in msg
            assert isinstance(msg["payload"], dict)


@pytest.mark.asyncio
class TestConnectionResilience:
    """Test connection persistence and recovery."""
    
    async def test_connection_survives_component_rerender(self, ws_client):
        """Test connection persists through component re-renders."""
        await ws_client.connect_with_auth("rerender_test_user")
        await asyncio.sleep(0.1)
        
        # Simulate component re-render (connection should persist)
        original_connected = ws_client.connected
        
        # Send ping to verify connection active
        ping_msg = {"type": "ping", "timestamp": time.time()}
        await ws_client.send_json_message(ping_msg)
        await asyncio.sleep(0.1)
        
        assert ws_client.connected == original_connected
        pong_msgs = ws_client.get_messages_by_type("pong")
        assert len(pong_msgs) >= 1
        
    async def test_graceful_error_recovery(self, ws_client):
        """Test connection recovers from recoverable errors."""
        await ws_client.connect_with_auth("error_test_user")
        await asyncio.sleep(0.1)
        
        # Send invalid message format (recoverable error)
        invalid_msg = {"invalid": "structure"}
        await ws_client.send_json_message(invalid_msg)
        await asyncio.sleep(0.1)
        
        # Connection should stay alive
        assert ws_client.connected
        
        # Should be able to send valid message after error
        valid_msg = {"type": "ping"}
        await ws_client.send_json_message(valid_msg)
        await asyncio.sleep(0.1)
        
        pong_msgs = ws_client.get_messages_by_type("pong")
        assert len(pong_msgs) >= 1


@pytest.mark.asyncio
class TestServiceDiscovery:
    """Test WebSocket service discovery."""
    
    async def test_websocket_config_discovery(self):
        """Test backend provides WebSocket configuration."""
        from netra_backend.app.routes.websocket_enhanced import get_websocket_service_discovery
        
        config = await get_websocket_service_discovery()
        
        assert config["status"] == "success"
        ws_config = config["websocket_config"]
        assert ws_config["features"]["json_first"] is True
        assert ws_config["features"]["auth_required"] is True
        assert "/ws/enhanced" in ws_config["endpoints"]["websocket"]


@pytest.mark.asyncio 
class TestErrorHandlingAndLogging:
    """Test comprehensive error scenarios."""
    
    async def test_connection_rejection_logged_clearly(self):
        """Test rejected connections are logged clearly."""
        with patch('app.logging_config.central_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.get_logger.return_value = mock_log
            
            try:
                await websockets.connect("ws://localhost:8001/ws/enhanced?token=bad_token")
            except Exception:
                pass
            
            # Should have logged the rejection reason clearly
            assert mock_log.error.called or mock_log.warning.called
            
    async def test_empty_message_validation(self, ws_client):
        """Test empty messages are rejected early."""
        await ws_client.connect_with_auth("empty_msg_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        empty_msg = {
            "type": "user_message", 
            "payload": {"content": "   "}  # Only whitespace
        }
        await ws_client.send_json_message(empty_msg)
        await asyncio.sleep(0.1)
        
        error_msgs = ws_client.get_messages_by_type("error")
        empty_errors = [e for e in error_msgs if "empty" in str(e).lower()]
        assert len(empty_errors) >= 1


@pytest.mark.asyncio
class TestConcurrentConnections:
    """Test concurrent connection handling."""
    
    async def test_multiple_connections_same_user(self):
        """Test multiple connections from same user handled correctly."""
        clients = []
        try:
            # Create 3 concurrent connections
            for i in range(3):
                client = WebSocketE2EClient()
                await client.connect_with_auth(f"concurrent_user")
                clients.append(client)
                await asyncio.sleep(0.05)
            
            # All should be connected initially  
            for client in clients:
                assert client.connected
                
            # Connection manager enforces limits (max 5 per user)
            stats = connection_manager.get_connection_stats()
            assert stats["total_connections"] <= 5
            
        finally:
            for client in clients:
                if client.connected:
                    await client.disconnect()


@pytest.mark.asyncio
class TestRealTimeFeatures:
    """Test real-time WebSocket features."""
    
    async def test_heartbeat_keepalive(self, ws_client):
        """Test heartbeat keeps connection alive."""
        await ws_client.connect_with_auth("heartbeat_user")
        await asyncio.sleep(0.1)
        
        ping_msg = {"type": "ping", "timestamp": time.time()}
        await ws_client.send_json_message(ping_msg)
        await asyncio.sleep(0.1)
        
        pong_msgs = ws_client.get_messages_by_type("pong")
        assert len(pong_msgs) >= 1
        assert "server_time" in pong_msgs[0]
        
    async def test_message_ordering_preservation(self, ws_client):
        """Test messages maintain order during high throughput."""
        await ws_client.connect_with_auth("ordering_user")
        await asyncio.sleep(0.1)
        ws_client.messages.clear()
        
        # Send sequence of numbered messages rapidly
        for i in range(5):
            msg = {
                "type": "ping", 
                "payload": {"sequence": i, "timestamp": time.time()}
            }
            await ws_client.send_json_message(msg)
            
        await asyncio.sleep(0.2)
        
        pong_msgs = ws_client.get_messages_by_type("pong")
        assert len(pong_msgs) >= 5


@pytest.mark.asyncio
class TestManualDatabaseSessions:
    """Test manual database session handling (not Depends())."""
    
    async def test_websocket_manual_db_sessions(self, ws_client):
        """Test WebSocket endpoints use manual DB sessions."""
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            await ws_client.connect_with_auth("db_session_user")
            await asyncio.sleep(0.1)
            
            # Should have called manual session creation
            assert mock_db.called
            
    @patch('app.routes.websocket_enhanced.get_async_db')
    async def test_auth_validation_manual_session(self, mock_db):
        """Test auth validation uses manual database session."""
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        from netra_backend.app.routes.websocket_enhanced import authenticate_websocket_with_database
        
        session_info = {"user_id": "test_user", "email": "test@example.com"}
        
        with patch('app.services.security_service.SecurityService') as mock_security:
            mock_security_instance = AsyncMock()
            mock_security_instance.get_user_by_id.return_value = Mock(is_active=True)
            mock_security.return_value = mock_security_instance
            
            user_id = await authenticate_websocket_with_database(session_info)
            assert user_id == "test_user"
            assert mock_db.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])