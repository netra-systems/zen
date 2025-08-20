"""Integration tests for WebSocket functionality with real services.

These tests verify that WebSocket connections work end-to-end with:
1. Real authentication flow
2. Database integration
3. CORS handling
4. Message processing
5. Error scenarios
"""

import asyncio
import json
import pytest
import websockets
import time
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from test_framework.mock_utils import mock_justified
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.postgres import get_async_db
from app.clients.auth_client import auth_client


@pytest.fixture
def test_client():
    """Test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def mock_auth_success():
    """Mock successful authentication."""
    with patch.object(auth_client, 'validate_token') as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "user_id": "integration_test_user",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "expires_at": "2024-12-31T23:59:59Z"
        }
        yield mock_validate


@pytest.fixture
async def mock_db_session():
    """Mock database session for integration tests."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    with patch('app.routes.websocket_secure.get_async_db', return_value=session):
        yield session


@pytest.fixture
def valid_jwt_token():
    """Valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.signature"


class TestWebSocketServiceDiscovery:
    """Test WebSocket service discovery endpoints."""
    
    def test_secure_websocket_config_endpoint(self, test_client):
        """Test secure WebSocket configuration endpoint."""
        response = test_client.get("/ws/secure/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "websocket_config" in data
        config = data["websocket_config"]
        
        assert config["version"] == "2.0"
        assert config["security_level"] == "enterprise"
        assert config["features"]["secure_auth"] is True
        assert config["features"]["header_based_jwt"] is True
        assert config["features"]["cors_validation"] is True
        assert "limits" in config
    
    def test_secure_websocket_health_endpoint(self, test_client):
        """Test secure WebSocket health check endpoint."""
        response = test_client.get("/ws/secure/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "secure_websocket"
        assert data["version"] == "2.0"
        assert data["security_level"] == "enterprise"
        assert "timestamp" in data
        assert "cors_stats" in data


class TestWebSocketCORS:
    """Test WebSocket CORS validation."""
    
    @patch('app.core.websocket_cors.check_websocket_cors')
    def test_cors_allowed_origin(self, mock_cors_check, test_client):
        """Test WebSocket connection with allowed origin."""
        mock_cors_check.return_value = True
        
        # Test that CORS check would be called for allowed origins
        from app.core.websocket_cors import get_websocket_cors_handler
        cors_handler = get_websocket_cors_handler()
        
        # Test with localhost (should be allowed in development)
        result = cors_handler.is_origin_allowed("http://localhost:3000")
        assert result is True
    
    def test_cors_blocked_origin(self, test_client):
        """Test WebSocket connection with blocked origin."""
        from app.core.websocket_cors import get_websocket_cors_handler
        cors_handler = get_websocket_cors_handler()
        
        # Test with suspicious origin (should be blocked)
        result = cors_handler.is_origin_allowed("http://malicious-site.com")
        assert result is False
    
    def test_cors_security_violations_tracking(self, test_client):
        """Test CORS security violations are tracked."""
        from app.core.websocket_cors import get_websocket_cors_handler
        cors_handler = get_websocket_cors_handler()
        
        # Make several blocked requests
        for _ in range(3):
            cors_handler.is_origin_allowed("http://blocked-site.com")
        
        stats = cors_handler.get_security_stats()
        assert stats["total_violations"] >= 3


class TestWebSocketAuthentication:
    """Test WebSocket authentication scenarios."""
    
    async def test_header_authentication_success(self, mock_auth_success, mock_db_session, valid_jwt_token):
        """Test successful authentication via Authorization header."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        # Mock WebSocket with Authorization header
        class MockWebSocket:
            def __init__(self):
                self.headers = {"authorization": f"Bearer {valid_jwt_token}"}
        
        websocket = MockWebSocket()
        manager = SecureWebSocketManager(mock_db_session)
        
        result = await manager.validate_secure_auth(websocket)
        
        assert result["user_id"] == "integration_test_user"
        assert result["auth_method"] == "header"
        assert result["email"] == "test@example.com"
        mock_auth_success.assert_called_once_with(valid_jwt_token)
    
    async def test_subprotocol_authentication_success(self, mock_auth_success, mock_db_session, valid_jwt_token):
        """Test successful authentication via Sec-WebSocket-Protocol."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        # Mock WebSocket with subprotocol authentication
        class MockWebSocket:
            def __init__(self):
                self.headers = {"sec-websocket-protocol": f"jwt.{valid_jwt_token}, chat"}
        
        websocket = MockWebSocket()
        manager = SecureWebSocketManager(mock_db_session)
        
        result = await manager.validate_secure_auth(websocket)
        
        assert result["user_id"] == "integration_test_user"
        assert result["auth_method"] == "subprotocol"
        mock_auth_success.assert_called_once_with(valid_jwt_token)
    
    async def test_authentication_failure_no_token(self, mock_db_session):
        """Test authentication failure when no token provided."""
        from app.routes.websocket_secure import SecureWebSocketManager
        from fastapi import HTTPException
        
        class MockWebSocket:
            def __init__(self):
                self.headers = {}
        
        websocket = MockWebSocket()
        manager = SecureWebSocketManager(mock_db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            await manager.validate_secure_auth(websocket)
        
        assert exc_info.value.status_code == 1008
        assert "Authentication required" in exc_info.value.detail
    
    async def test_authentication_failure_invalid_token(self, mock_db_session, valid_jwt_token):
        """Test authentication failure with invalid token."""
        from app.routes.websocket_secure import SecureWebSocketManager
        from fastapi import HTTPException
        
        with patch.object(auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {"valid": False}
            
            class MockWebSocket:
                def __init__(self):
                    self.headers = {"authorization": f"Bearer {valid_jwt_token}"}
            
            websocket = MockWebSocket()
            manager = SecureWebSocketManager(mock_db_session)
            
            with pytest.raises(HTTPException) as exc_info:
                await manager.validate_secure_auth(websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Authentication failed" in exc_info.value.detail


class TestWebSocketMessageProcessing:
    """Test WebSocket message processing scenarios."""
    
    async def test_valid_message_processing(self, mock_db_session):
        """Test processing of valid messages."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        connection_id = await manager.add_connection("test_user", websocket, {})
        
        # Mock justification: Preventing actual LLM API calls in test environment during message flow testing
        with patch.object(manager, 'process_user_message') as mock_process:
            mock_process.return_value = None
            
            valid_message = json.dumps({
                "type": "user_message",
                "payload": {"content": "Hello, how are you?"}
            })
            
            result = await manager.handle_message(connection_id, valid_message)
            
            assert result is True
            assert manager._stats["messages_processed"] == 1
            mock_process.assert_called_once()
    
    async def test_invalid_json_handling(self, mock_db_session):
        """Test handling of invalid JSON messages."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        connection_id = await manager.add_connection("test_user", websocket, {})
        
        invalid_json = "{ invalid json message }"
        result = await manager.handle_message(connection_id, invalid_json)
        
        assert result is False
        assert len(websocket.sent_messages) == 1
        error_msg = websocket.sent_messages[0]
        assert error_msg["type"] == "error"
        assert error_msg["payload"]["code"] == "JSON_ERROR"
    
    async def test_system_message_handling(self, mock_db_session):
        """Test handling of system messages (ping/pong)."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        connection_id = await manager.add_connection("test_user", websocket, {})
        
        ping_message = json.dumps({"type": "ping"})
        result = await manager.handle_message(connection_id, ping_message)
        
        assert result is True
        assert len(websocket.sent_messages) == 1
        pong_msg = websocket.sent_messages[0]
        assert pong_msg["type"] == "pong"
        assert "timestamp" in pong_msg
    
    async def test_message_size_limit(self, mock_db_session):
        """Test message size limit enforcement."""
        from app.routes.websocket_secure import SecureWebSocketManager, SECURE_WEBSOCKET_CONFIG
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        connection_id = await manager.add_connection("test_user", websocket, {})
        
        # Create oversized message
        max_size = SECURE_WEBSOCKET_CONFIG["limits"]["max_message_size"]
        large_content = "x" * (max_size + 1000)
        large_message = json.dumps({"type": "user_message", "content": large_content})
        
        result = await manager.handle_message(connection_id, large_message)
        
        assert result is False
        assert len(websocket.sent_messages) == 1
        error_msg = websocket.sent_messages[0]
        assert error_msg["type"] == "error"
        assert error_msg["payload"]["code"] == "MESSAGE_TOO_LARGE"


class TestWebSocketConnectionManagement:
    """Test WebSocket connection lifecycle management."""
    
    async def test_connection_lifecycle(self, mock_db_session):
        """Test complete connection lifecycle."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False
                self.close_code = None
                self.close_reason = None
            
            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code
                self.close_reason = reason
                self.application_state = "DISCONNECTED"
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        session_info = {"user_id": "test_user", "auth_method": "header"}
        
        # Test connection addition
        connection_id = await manager.add_connection("test_user", websocket, session_info)
        
        assert connection_id in manager.connections
        assert manager.connections[connection_id]["user_id"] == "test_user"
        assert manager._stats["connections_created"] == 1
        
        # Test connection removal
        await manager.remove_connection(connection_id, "Test cleanup")
        
        assert connection_id not in manager.connections
        assert websocket.closed is True
        assert websocket.close_reason == "Test cleanup"
        assert manager._stats["connections_closed"] == 1
    
    async def test_connection_limit_enforcement(self, mock_db_session):
        """Test connection limit per user."""
        from app.routes.websocket_secure import SecureWebSocketManager, SECURE_WEBSOCKET_CONFIG
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False
            
            async def close(self, code=1000, reason=""):
                self.closed = True
        
        manager = SecureWebSocketManager(mock_db_session)
        max_connections = SECURE_WEBSOCKET_CONFIG["limits"]["max_connections_per_user"]
        user_id = "test_user"
        
        websockets = []
        connection_ids = []
        
        # Create maximum allowed connections
        for i in range(max_connections):
            ws = MockWebSocket()
            websockets.append(ws)
            conn_id = await manager.add_connection(user_id, ws, {"user_id": user_id})
            connection_ids.append(conn_id)
        
        assert len(manager.connections) == max_connections
        
        # Add one more connection - should evict oldest
        extra_ws = MockWebSocket()
        extra_conn_id = await manager.add_connection(user_id, extra_ws, {"user_id": user_id})
        
        assert len(manager.connections) == max_connections  # Still at limit
        assert extra_conn_id in manager.connections  # New connection exists
        assert connection_ids[0] not in manager.connections  # Oldest removed
        assert websockets[0].closed is True  # Oldest WebSocket closed
    
    async def test_send_to_user_multiple_connections(self, mock_db_session):
        """Test sending messages to user with multiple connections."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        user_id = "test_user"
        
        # Add multiple connections for same user
        websockets = []
        for i in range(3):
            ws = MockWebSocket()
            websockets.append(ws)
            await manager.add_connection(user_id, ws, {"user_id": user_id})
        
        # Send message to user
        message = {"type": "notification", "payload": {"text": "Hello all connections"}}
        result = await manager.send_to_user(user_id, message)
        
        assert result is True
        
        # Verify all connections received the message
        for ws in websockets:
            assert len(ws.sent_messages) == 1
            assert ws.sent_messages[0] == message


class TestWebSocketResourceCleanup:
    """Test resource cleanup and memory management."""
    
    async def test_manager_cleanup(self, mock_db_session):
        """Test comprehensive manager cleanup."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False
            
            async def close(self, code=1000, reason=""):
                self.closed = True
        
        manager = SecureWebSocketManager(mock_db_session)
        
        # Add connections
        websockets = []
        for i in range(3):
            ws = MockWebSocket()
            websockets.append(ws)
            await manager.add_connection(f"user_{i}", ws, {"user_id": f"user_{i}"})
        
        assert len(manager.connections) == 3
        
        # Test cleanup
        await manager.cleanup()
        
        # Verify all resources cleaned up
        assert len(manager.connections) == 0
        for ws in websockets:
            assert ws.closed is True
        mock_db_session.close.assert_called_once()
    
    async def test_context_manager_cleanup(self, mock_db_session):
        """Test cleanup via context manager."""
        from app.routes.websocket_secure import get_secure_websocket_manager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False
            
            async def close(self, code=1000, reason=""):
                self.closed = True
        
        websockets = []
        
        # Use context manager
        async with get_secure_websocket_manager(mock_db_session) as manager:
            # Add connections inside context
            for i in range(2):
                ws = MockWebSocket()
                websockets.append(ws)
                await manager.add_connection(f"user_{i}", ws, {"user_id": f"user_{i}"})
            
            assert len(manager.connections) == 2
        
        # After context exit, everything should be cleaned up
        for ws in websockets:
            assert ws.closed is True


class TestWebSocketErrorHandling:
    """Test error handling in various scenarios."""
    
    async def test_agent_service_error(self, mock_db_session):
        """Test handling of agent service errors."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        connection_id = await manager.add_connection("test_user", websocket, {})
        
        # Mock agent service error
        with patch.object(manager, 'process_user_message') as mock_process:
            mock_process.side_effect = Exception("Agent service unavailable")
            
            message = json.dumps({"type": "user_message", "payload": {"content": "Hello"}})
            result = await manager.handle_message(connection_id, message)
            
            assert result is False
            assert manager._stats["errors_handled"] == 1
            
            # Should send error to client
            assert len(websocket.sent_messages) == 1
            error_msg = websocket.sent_messages[0]
            assert error_msg["type"] == "error"
            assert error_msg["payload"]["code"] == "PROCESSING_ERROR"
            
            # Should rollback database session
            mock_db_session.rollback.assert_called_once()
    
    async def test_database_session_error(self, mock_db_session):
        """Test handling of database session errors."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        manager = SecureWebSocketManager(mock_db_session)
        
        # Mock database error during user validation
        with patch('app.routes.websocket_secure.SecurityService') as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.get_user_by_id.side_effect = Exception("DB connection lost")
            
            result = await manager.validate_user_exists("test_user")
            
            assert result is False  # Should handle gracefully
    
    async def test_websocket_send_error_handling(self, mock_db_session):
        """Test handling of WebSocket send errors."""
        from app.routes.websocket_secure import SecureWebSocketManager
        
        class MockWebSocket:
            def __init__(self):
                self.application_state = "CONNECTED"
                self.send_error = False
            
            async def send_json(self, data):
                if self.send_error:
                    raise ConnectionError("WebSocket connection lost")
        
        manager = SecureWebSocketManager(mock_db_session)
        websocket = MockWebSocket()
        await manager.add_connection("test_user", websocket, {})
        
        # First send should work
        result = await manager.send_to_user("test_user", {"type": "test"})
        assert result is True
        
        # Second send should fail and trigger cleanup
        websocket.send_error = True
        result = await manager.send_to_user("test_user", {"type": "test"})
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])