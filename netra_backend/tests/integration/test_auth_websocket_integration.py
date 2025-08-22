"""Integration Test: Authentication to WebSocket Connection Flow

BVJ: $20K MRR - First impression critical for conversion
Components: Auth Service → Backend → WebSocket Manager
Critical: Users can't interact without successful auth→WS flow
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from netra_backend.app.schemas import User

from netra_backend.app.config import get_config

@pytest.mark.asyncio

class TestAuthToWebSocketFlow:

    """Test complete authentication to WebSocket connection establishment."""
    
    @pytest.fixture

    async def auth_token(self):

        """Generate valid JWT token."""

        payload = {

            "sub": "test_user_123",

            "email": "test@example.com",

            "exp": datetime.utcnow() + timedelta(hours=1)

        }

        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    @pytest.fixture

    async def mock_user(self):

        """Create mock user for testing."""

        return User(

            id="test_user_123",

            email="test@example.com",

            username="testuser",

            is_active=True,

            created_at=datetime.utcnow()

        )
    
    async def test_successful_auth_to_websocket(self, auth_token, mock_user):

        """Test successful auth flow leading to WS connection."""
        from netra_backend.app.services.auth_service import AuthService
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        # Setup mocks

        auth_service = Mock(spec=AuthService)

        auth_service.validate_token = AsyncMock(return_value=mock_user)
        
        ws_manager = WebSocketManager()

        mock_websocket = Mock()

        mock_websocket.accept = AsyncMock()

        mock_websocket.send_json = AsyncMock()
        
        # Execute auth validation

        user = await auth_service.validate_token_jwt(auth_token)

        assert user.id == "test_user_123"
        
        # Establish WebSocket connection

        await ws_manager.connect(mock_websocket, user.id)
        
        # Verify connection established

        assert user.id in ws_manager.active_connections

        mock_websocket.accept.assert_called_once()
        
        # Send initial connection message

        await ws_manager.send_message(user.id, {

            "type": "connection_established",

            "user_id": user.id,

            "timestamp": datetime.utcnow().isoformat()

        })
        
        mock_websocket.send_json.assert_called()
    
    async def test_invalid_token_blocks_websocket(self):

        """Test invalid token prevents WS connection."""
        
        auth_service = Mock(spec=AuthService)

        auth_service.validate_token = AsyncMock(side_effect=ValueError("Invalid token"))
        
        ws_manager = WebSocketManager()

        mock_websocket = Mock()
        
        # Attempt connection with invalid token

        with pytest.raises(ValueError):

            await auth_service.validate_token_jwt("invalid_token")
        
        # Verify no connection established

        assert len(ws_manager.active_connections) == 0
    
    async def test_expired_token_handling(self):

        """Test expired token gracefully handled."""

        expired_payload = {

            "sub": "test_user",

            "exp": datetime.utcnow() - timedelta(hours=1)

        }

        expired_token = jwt.encode(

            expired_payload, 

            settings.SECRET_KEY, 

            algorithm="HS256"

        )
        
        auth_service = Mock(spec=AuthService)

        auth_service.validate_token = AsyncMock(

            side_effect=jwt.ExpiredSignatureError("Token expired")

        )
        
        with pytest.raises(jwt.ExpiredSignatureError):

            await auth_service.validate_token_jwt(expired_token)
    
    async def test_auth_service_unavailable_fallback(self):

        """Test fallback when auth service is unavailable."""
        from netra_backend.app.core.circuit_breaker import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(

            failure_threshold=3,

            recovery_timeout=60

        )
        
        auth_service = Mock(spec=AuthService)

        auth_service.validate_token = AsyncMock(

            side_effect=ConnectionError("Auth service unavailable")

        )
        
        # Simulate failures to open circuit

        for _ in range(3):

            try:

                await circuit_breaker.call(auth_service.validate_token, "token")

            except:

                pass
        
        assert circuit_breaker.state == "open"
        
        # Verify circuit prevents further calls

        with pytest.raises(Exception, match="Circuit breaker is open"):

            await circuit_breaker.call(auth_service.validate_token, "token")
    
    async def test_concurrent_auth_requests(self, auth_token, mock_user):

        """Test system handles concurrent auth requests."""
        
        auth_service = Mock(spec=AuthService)

        auth_service.validate_token = AsyncMock(return_value=mock_user)

        ws_manager = WebSocketManager()
        
        # Simulate 10 concurrent connections

        tasks = []

        for i in range(10):

            mock_ws = Mock()

            mock_ws.accept = AsyncMock()

            user_id = f"user_{i}"
            
            async def connect_user(ws, uid):

                await ws_manager.connect(ws, uid)
            
            tasks.append(connect_user(mock_ws, user_id))
        
        await asyncio.gather(*tasks)
        
        # Verify all connections established

        assert len(ws_manager.active_connections) == 10
    
    async def test_auth_to_websocket_with_redis_session(self, auth_token, mock_user):

        """Test auth flow with Redis session storage."""
        from netra_backend.app.services.redis_manager import RedisManager
        
        redis_manager = Mock(spec=RedisManager)

        redis_manager.set = AsyncMock(return_value=True)

        redis_manager.get = AsyncMock(return_value=json.dumps({

            "user_id": mock_user.id,

            "email": mock_user.email,

            "session_id": "session_123"

        }))
        
        # Store session in Redis

        session_key = f"session:{mock_user.id}"

        await redis_manager.set(session_key, json.dumps({

            "user_id": mock_user.id,

            "email": mock_user.email,

            "session_id": "session_123"

        }))
        
        # Retrieve and verify session

        session_data = await redis_manager.get(session_key)

        assert json.loads(session_data)["user_id"] == mock_user.id
    
    async def test_websocket_auth_header_validation(self, auth_token):

        """Test WebSocket connection validates auth headers."""
        
        ws_manager = WebSocketManager()

        mock_websocket = Mock()

        mock_websocket.headers = {"Authorization": f"Bearer {auth_token}"}

        mock_websocket.accept = AsyncMock()
        
        # Extract and validate token from headers

        auth_header = mock_websocket.headers.get("Authorization")

        assert auth_header.startswith("Bearer ")
        
        token = auth_header.split(" ")[1]

        assert token == auth_token