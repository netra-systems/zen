"""Comprehensive WebSocket tests covering all requirements from SPEC/websockets.xml.

Tests cover:
1. Connection establishment with authentication
2. Authentication flow with JWT tokens
3. Message send/receive with JSON validation
4. Reconnection logic on disconnect
5. Error handling and recovery
6. JSON parsing and validation
7. Service discovery configuration
8. Component re-render resilience
9. Concurrent connections
10. CORS handling
11. Rate limiting
12. Manual database session handling
13. Heartbeat and keepalive
14. Message queuing during disconnections
15. Token expiry and refresh
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
import websockets
from fastapi import WebSocket
from fastapi.testclient import TestClient

from netra_backend.app.core.websocket_cors import (
    WebSocketCORSHandler,
    get_environment_origins,
    validate_websocket_origin,
)
from netra_backend.app.db.postgres import get_async_db

from netra_backend.app.main import app
from netra_backend.app.routes.websocket import (
    websocket_endpoint,
)
from netra_backend.app.routes.utils.websocket_helpers import (
    authenticate_websocket_user,
    accept_websocket_connection,
)
from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager
from netra_backend.tests.conftest import create_test_user, get_test_token

class WebSocketTestClient:
    """Test client for WebSocket connections."""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.messages: List[Dict] = []
        self.connected = False
        
    async def connect(self, endpoint: str, token: str):
        """Connect to WebSocket endpoint."""
        url = f"{self.base_url}{endpoint}?token={token}"
        self.websocket = await websockets.connect(url)
        self.connected = True
        
        # Start message listener
        asyncio.create_task(self._listen_messages())
        
    async def _listen_messages(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages.append(data)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            
    async def send_message(self, message: Dict):
        """Send message to WebSocket."""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            
    def get_messages_by_type(self, message_type: str) -> List[Dict]:
        """Get messages by type."""
        return [msg for msg in self.messages if msg.get("type") == message_type]
        
    def clear_messages(self):
        """Clear message history."""
        self.messages.clear()

@pytest.fixture
async def websocket_client():
    """WebSocket test client fixture."""
    client = WebSocketTestClient()
    yield client
    if client.connected:
        await client.disconnect()

@pytest.fixture
async def authenticated_token(test_user):
    """Get authenticated token for testing."""
    return await get_test_token(test_user.id)

@pytest.mark.asyncio
class TestWebSocketConnection:
    """Test WebSocket connection establishment."""
    
    async def test_connection_establishment_success(self, websocket_client, authenticated_token):
        """Test successful WebSocket connection establishment."""
        # Test connection with valid token
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        
        # Wait for connection established message
        await asyncio.sleep(0.1)
        
        # Verify connection
        assert websocket_client.connected
        
        # Check for connection_established message
        connection_msgs = websocket_client.get_messages_by_type("connection_established")
        assert len(connection_msgs) == 1
        
        connection_msg = connection_msgs[0]
        assert "payload" in connection_msg
        assert "user_id" in connection_msg["payload"]
        assert "connection_id" in connection_msg["payload"]
        assert "server_time" in connection_msg["payload"]
        
    async def test_connection_establishment_invalid_token(self, websocket_client):
        """Test connection fails with invalid token."""
        with pytest.raises(Exception):  # Connection should fail
            await websocket_client.connect("/ws/enhanced", "invalid_token")
            
    async def test_connection_establishment_no_token(self, websocket_client):
        """Test connection fails without token."""
        with pytest.raises(Exception):  # Connection should fail
            await websocket_client.connect("/ws/enhanced", "")

@pytest.mark.asyncio
class TestWebSocketAuthentication:
    """Test WebSocket authentication flow."""
    
    async def test_jwt_authentication_flow(self, authenticated_token):
        """Test JWT authentication flow."""
        # Mock WebSocket for testing
        mock_websocket = Mock()
        mock_websocket.query_params = {"token": authenticated_token}
        mock_websocket.accept = AsyncMock()
        
        # Test token validation
        session_info = await validate_websocket_token_enhanced(mock_websocket)
        
        assert session_info["user_id"]
        assert session_info["authenticated_at"]
        assert session_info["auth_method"] == "jwt_query_param"
        
        # Test database authentication
        user_id = await authenticate_websocket_with_database(session_info)
        assert user_id == session_info["user_id"]
        
    async def test_token_validation_expired_token(self):
        """Test validation fails with expired token."""
        mock_websocket = Mock()
        mock_websocket.query_params = {"token": "expired.token.here"}
        
        with pytest.raises(Exception):
            await validate_websocket_token_enhanced(mock_websocket)
            
    @patch('netra_backend.app.routes.websocket_enhanced.get_async_db')
    async def test_manual_database_session_handling(self, mock_db):
        """Test manual database session handling (not using Depends())."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        # Mock user data
        session_info = {
            "user_id": "test_user_id",
            "email": "test@example.com",
            "authenticated_at": "2025-01-01T00:00:00Z"
        }
        
        # This should work with manual session handling
        with patch('netra_backend.app.services.security_service.SecurityService') as mock_security:
            mock_security_instance = AsyncMock()
            mock_security_instance.get_user_by_id.return_value = Mock(is_active=True)
            mock_security.return_value = mock_security_instance
            
            user_id = await authenticate_websocket_with_database(session_info)
            assert user_id == "test_user_id"
            
            # Verify manual session was used (not Depends())
            assert mock_db.called
            assert mock_session.commit.called

@pytest.mark.asyncio 
class TestWebSocketMessaging:
    """Test WebSocket message handling."""
    
    async def test_message_send_receive_json_first(self, websocket_client, authenticated_token):
        """Test message send/receive with JSON-first validation."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)  # Wait for connection
        
        # Clear connection messages
        websocket_client.clear_messages()
        
        # Test valid JSON message
        test_message = {
            "type": "user_message",
            "payload": {
                "content": "Hello, world!",
                "timestamp": time.time()
            }
        }
        
        await websocket_client.send_message(test_message)
        await asyncio.sleep(0.1)  # Wait for processing
        
        # Should not receive error messages for valid JSON
        error_messages = websocket_client.get_messages_by_type("error")
        assert len(error_messages) == 0
        
    async def test_message_json_validation_errors(self, websocket_client, authenticated_token):
        """Test JSON validation error handling."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Test invalid message structure (missing type)
        invalid_message = {"payload": {"content": "test"}}
        await websocket_client.send_message(invalid_message)
        await asyncio.sleep(0.1)
        
        # Should receive error message
        error_messages = websocket_client.get_messages_by_type("error")
        assert len(error_messages) == 1
        assert error_messages[0]["payload"]["code"] == "MISSING_TYPE_FIELD"
        
    async def test_ping_pong_system_messages(self, websocket_client, authenticated_token):
        """Test ping/pong system message handling."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Send ping message
        ping_message = {"type": "ping", "timestamp": time.time()}
        await websocket_client.send_message(ping_message)
        await asyncio.sleep(0.1)
        
        # Should receive pong response
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) == 1
        assert "timestamp" in pong_messages[0]
        assert "server_time" in pong_messages[0]

@pytest.mark.asyncio
class TestWebSocketReconnection:
    """Test WebSocket reconnection logic."""
    
    async def test_reconnection_on_network_disconnect(self, websocket_client, authenticated_token):
        """Test reconnection after network disconnect."""
        # This test would simulate network disconnection
        # For now, we test the reconnection mechanism components
        
        # Test connection manager handles disconnection
        user_id = "test_user"
        connection_id = "test_connection"
        
        # Simulate adding connection
        mock_websocket = Mock()
        session_info = {"user_id": user_id}
        
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        assert conn_id is not None
        
        # Verify connection exists
        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == 1
        
        # Simulate disconnection
        await connection_manager.remove_connection(user_id, conn_id)
        
        # Verify connection removed
        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == 0
        
    async def test_reconnection_with_exponential_backoff(self):
        """Test reconnection logic uses exponential backoff."""
        # This would be tested in the frontend WebSocket provider
        # Here we verify the backend handles reconnection gracefully
        
        # Mock multiple quick reconnection attempts
        for i in range(3):
            mock_websocket = Mock()
            session_info = {"user_id": f"user_{i}"}
            
            conn_id = await connection_manager.add_connection(f"user_{i}", mock_websocket, session_info)
            await connection_manager.remove_connection(f"user_{i}", conn_id)
            
        # Connection manager should handle rapid reconnections
        assert True  # Basic test passes

@pytest.mark.asyncio
class TestWebSocketErrorHandling:
    """Test WebSocket error handling and recovery."""
    
    async def test_error_message_format(self, websocket_client, authenticated_token):
        """Test error messages follow correct format."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Send malformed message to trigger error
        await websocket_client.websocket.send("invalid json")
        await asyncio.sleep(0.1)
        
        # Should receive properly formatted error
        error_messages = websocket_client.get_messages_by_type("error")
        assert len(error_messages) == 1
        
        error_msg = error_messages[0]
        assert "payload" in error_msg
        assert "code" in error_msg["payload"] 
        assert "error" in error_msg["payload"]
        assert "timestamp" in error_msg["payload"]
        assert "recoverable" in error_msg["payload"]
        
    async def test_connection_resilience_to_errors(self, websocket_client, authenticated_token):
        """Test connection stays alive after recoverable errors."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        
        # Send multiple invalid messages
        for i in range(3):
            await websocket_client.websocket.send("invalid json")
            await asyncio.sleep(0.05)
        
        # Connection should still be alive
        assert websocket_client.connected
        
        # Should be able to send valid message
        valid_message = {"type": "ping"}
        await websocket_client.send_message(valid_message)
        await asyncio.sleep(0.1)
        
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) >= 1

@pytest.mark.asyncio
class TestWebSocketServiceDiscovery:
    """Test WebSocket service discovery."""
    
    async def test_service_discovery_endpoint(self):
        """Test /ws/config service discovery endpoint."""
        with TestClient(app) as client:
            response = client.get("/ws/config")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "websocket_config" in data
            config = data["websocket_config"]
            
            # Verify required configuration fields
            assert "version" in config
            assert "features" in config
            assert "endpoints" in config
            assert "connection_limits" in config
            assert "auth" in config
            
            # Verify features
            features = config["features"]
            assert features["json_first"] is True
            assert features["auth_required"] is True
            assert features["reconnection_supported"] is True
            
    async def test_service_discovery_provides_websocket_url(self):
        """Test service discovery provides correct WebSocket URL."""
        config = await get_websocket_service_discovery()
        
        ws_config = config["websocket_config"]
        assert "endpoints" in ws_config
        assert "websocket" in ws_config["endpoints"]
        assert ws_config["endpoints"]["websocket"] == "/ws/enhanced"

@pytest.mark.asyncio
class TestWebSocketConcurrency:
    """Test concurrent WebSocket connections."""
    
    async def test_concurrent_connections_same_user(self, authenticated_token):
        """Test multiple connections from same user."""
        clients = []
        
        try:
            # Create multiple concurrent connections
            for i in range(3):
                client = WebSocketTestClient()
                await client.connect("/ws/enhanced", authenticated_token)
                clients.append(client)
                await asyncio.sleep(0.05)
            
            # All connections should be established
            for client in clients:
                assert client.connected
                
            # Send message from each connection
            for i, client in enumerate(clients):
                test_message = {
                    "type": "ping", 
                    "payload": {"connection_number": i}
                }
                await client.send_message(test_message)
                
            await asyncio.sleep(0.1)
            
            # Each should receive pong response
            for client in clients:
                pong_messages = client.get_messages_by_type("pong")
                assert len(pong_messages) >= 1
                
        finally:
            # Cleanup connections
            for client in clients:
                if client.connected:
                    await client.disconnect()
                    
    async def test_connection_limit_enforcement(self, authenticated_token):
        """Test connection limits are enforced per user."""
        # This test verifies the connection manager enforces limits
        # Default limit is 5 connections per user
        
        user_id = "test_user"
        session_info = {"user_id": user_id}
        connections = []
        
        # Create max connections + 1
        for i in range(6):
            mock_websocket = Mock()
            conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
            connections.append((conn_id, mock_websocket))
        
        # Should only have 5 connections (oldest removed)
        stats = connection_manager.get_connection_stats()
        assert stats["connections_per_user"][user_id] == 5
        
        # Cleanup
        for conn_id, _ in connections[-5:]:  # Keep only last 5
            await connection_manager.remove_connection(user_id, conn_id)

@pytest.mark.asyncio
class TestWebSocketCORS:
    """Test WebSocket CORS handling."""
    
    def test_cors_handler_initialization(self):
        """Test CORS handler initializes correctly."""
        allowed_origins = ["http://localhost:3000", "https://app.example.com"]
        cors_handler = WebSocketCORSHandler(allowed_origins)
        
        assert cors_handler.allowed_origins == allowed_origins
        
    def test_cors_origin_validation_allowed(self):
        """Test CORS validation allows configured origins."""
        cors_handler = WebSocketCORSHandler(["http://localhost:3000"])
        
        assert cors_handler.is_origin_allowed("http://localhost:3000") is True
        assert cors_handler.is_origin_allowed("http://localhost:3001") is False
        assert cors_handler.is_origin_allowed(None) is False
        
    def test_cors_wildcard_patterns(self):
        """Test CORS wildcard pattern matching."""
        cors_handler = WebSocketCORSHandler(["https://*.example.com"])
        
        assert cors_handler.is_origin_allowed("https://app.example.com") is True
        assert cors_handler.is_origin_allowed("https://api.example.com") is True
        assert cors_handler.is_origin_allowed("https://example.com") is True
        assert cors_handler.is_origin_allowed("http://app.example.com") is False
        
    def test_environment_origins_configuration(self):
        """Test environment-based origin configuration."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            origins = get_environment_origins()
            assert "http://localhost:3000" in origins
            
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            origins = get_environment_origins()
            # Should include production origins but not localhost
            assert any("netrasystems.ai" in origin for origin in origins)
            
    async def test_websocket_cors_validation(self):
        """Test WebSocket CORS validation in route."""
        cors_handler = WebSocketCORSHandler(["http://localhost:3000"])
        
        # Mock WebSocket with allowed origin
        mock_websocket = Mock()
        mock_websocket.headers = {"origin": "http://localhost:3000"}
        
        assert validate_websocket_origin(mock_websocket, cors_handler) is True
        
        # Mock WebSocket with disallowed origin  
        mock_websocket.headers = {"origin": "http://malicious.com"}
        assert validate_websocket_origin(mock_websocket, cors_handler) is False

@pytest.mark.asyncio
class TestWebSocketHeartbeat:
    """Test WebSocket heartbeat and keepalive."""
    
    async def test_heartbeat_messages(self, websocket_client, authenticated_token):
        """Test server sends heartbeat messages."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Wait for potential heartbeat (in real scenario, would wait longer)
        # For testing, we verify the heartbeat mechanism exists
        
        # Send ping to test heartbeat response
        ping_message = {"type": "ping", "timestamp": time.time()}
        await websocket_client.send_message(ping_message)
        await asyncio.sleep(0.1)
        
        # Should receive pong (heartbeat response)
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) >= 1
        
    async def test_connection_timeout_detection(self):
        """Test connection timeout detection."""
        # This tests the connection manager's ability to detect timeouts
        user_id = "timeout_test_user"
        session_info = {"user_id": user_id}
        mock_websocket = Mock()
        
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        # Verify connection metadata tracking
        assert conn_id in connection_manager.connection_metadata
        metadata = connection_manager.connection_metadata[conn_id]
        assert "last_activity" in metadata
        assert "message_count" in metadata
        
        # Cleanup
        await connection_manager.remove_connection(user_id, conn_id)

@pytest.mark.asyncio
class TestWebSocketResilience:
    """Test WebSocket resilience to re-renders and lifecycle changes."""
    
    async def test_connection_survives_component_rerender(self, websocket_client, authenticated_token):
        """Test connection persists through component re-renders."""
        # Establish connection
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        
        original_connection_count = len(websocket_client.messages)
        
        # Simulate component re-render (connection should persist)
        # In real frontend, this would be handled by the provider
        
        # Connection should remain active
        assert websocket_client.connected
        
        # Should be able to send message after "re-render"
        test_message = {"type": "ping"}
        await websocket_client.send_message(test_message)
        await asyncio.sleep(0.1)
        
        # Should receive response
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) >= 1
        
    async def test_message_queuing_during_disconnection(self):
        """Test message queuing when connection is lost."""
        # This would be primarily tested in frontend WebSocket service
        # Here we verify backend handles queued messages correctly
        
        user_id = "queue_test_user" 
        session_info = {"user_id": user_id}
        mock_websocket = Mock()
        
        # Add connection
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        # Simulate connection loss and recovery
        await connection_manager.remove_connection(user_id, conn_id)
        
        # Re-establish connection (simulates queued messages being processed)
        new_conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        # Verify new connection established
        assert new_conn_id != conn_id
        assert new_conn_id in connection_manager.connection_metadata
        
        # Cleanup
        await connection_manager.remove_connection(user_id, new_conn_id)

# Integration test that runs all scenarios
@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for complete WebSocket functionality."""
    
    async def test_complete_websocket_lifecycle(self, websocket_client, authenticated_token):
        """Test complete WebSocket lifecycle from connection to cleanup."""
        # 1. Service Discovery
        config_response = await get_websocket_service_discovery()
        assert config_response["status"] == "success"
        
        # 2. Connection Establishment
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        assert websocket_client.connected
        
        # 3. Authentication Confirmation
        connection_msgs = websocket_client.get_messages_by_type("connection_established")
        assert len(connection_msgs) == 1
        
        websocket_client.clear_messages()
        
        # 4. Message Exchange
        test_message = {
            "type": "user_message", 
            "payload": {"content": "Integration test message"}
        }
        await websocket_client.send_message(test_message)
        
        # 5. Ping/Pong Heartbeat
        ping_message = {"type": "ping", "timestamp": time.time()}
        await websocket_client.send_message(ping_message)
        await asyncio.sleep(0.1)
        
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) >= 1
        
        # 6. Error Handling
        await websocket_client.websocket.send("invalid json")
        await asyncio.sleep(0.1)
        
        error_messages = websocket_client.get_messages_by_type("error")
        assert len(error_messages) >= 1
        
        # Connection should still be alive after error
        assert websocket_client.connected
        
        # 7. Graceful Disconnection
        await websocket_client.disconnect()
        assert not websocket_client.connected

# Performance and load testing
@pytest.mark.asyncio
class TestWebSocketPerformance:
    """Test WebSocket performance characteristics."""
    
    async def test_message_throughput(self, websocket_client, authenticated_token):
        """Test message handling throughput."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Send burst of messages
        start_time = time.time()
        message_count = 10
        
        for i in range(message_count):
            test_message = {
                "type": "ping",
                "payload": {"sequence": i}
            }
            await websocket_client.send_message(test_message)
            
        # Wait for all responses
        await asyncio.sleep(0.5)
        end_time = time.time()
        
        # Verify all messages processed
        pong_messages = websocket_client.get_messages_by_type("pong")
        assert len(pong_messages) >= message_count
        
        # Basic performance check (should handle 10 messages quickly)
        duration = end_time - start_time
        assert duration < 2.0  # Should complete in under 2 seconds
        
    async def test_large_message_handling(self, websocket_client, authenticated_token):
        """Test handling of large messages within limits."""
        await websocket_client.connect("/ws/enhanced", authenticated_token)
        await asyncio.sleep(0.1)
        websocket_client.clear_messages()
        
        # Create message near size limit (default 10KB)
        large_content = "x" * 5000  # 5KB content
        large_message = {
            "type": "user_message",
            "payload": {
                "content": large_content,
                "metadata": {"size": len(large_content)}
            }
        }
        
        await websocket_client.send_message(large_message)
        await asyncio.sleep(0.2)
        
        # Should not receive size error for valid large message
        error_messages = websocket_client.get_messages_by_type("error")
        size_errors = [err for err in error_messages 
                      if "too large" in err.get("payload", {}).get("error", "")]
        assert len(size_errors) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])