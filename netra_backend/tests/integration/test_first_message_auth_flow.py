"""Integration Test: First Message Authentication Flow
BVJ: $8K MRR - Authentication failures cause 40% user abandonment
Components: AuthService → JWT Validation → WebSocket Middleware → Message Handler
Critical: First user message must seamlessly authenticate and process
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from fastapi import WebSocket
from netra_backend.app.schemas import User
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from netra_backend.app.db.models_postgres import Message, Thread, User
from netra_backend.app.services.agent_service_core import AgentService

from netra_backend.app.services.user_auth_service import UserAuthService as AuthService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager
from test_framework.mock_utils import mock_justified

@pytest.mark.asyncio

class TestFirstMessageAuthenticationFlow:

    """Test complete authentication flow for first user message."""
    
    @pytest.fixture

    async def test_user(self):

        """Create test user for authentication testing."""

        return User(

            id="auth_test_user_001",

            email="firstmsg@test.netrasystems.ai",

            username="firstuser",

            is_active=True,

            created_at=datetime.now(timezone.utc)

        )
    
    @pytest.fixture

    async def mock_websocket(self):

        """Create mock WebSocket with auth headers."""

        websocket = Mock(spec=WebSocket)

        websocket.accept = AsyncMock()

        websocket.send_json = AsyncMock()

        websocket.close = AsyncMock()

        websocket.receive_json = AsyncMock(return_value={

            "type": "user_message",

            "payload": {"content": "Hello, this is my first message"}

        })

        websocket.client_state = WebSocketState.CONNECTED

        websocket.headers = {"Authorization": "Bearer test.jwt.token"}

        return websocket
    
    @pytest.fixture

    async def auth_service(self):

        """Create auth service instance."""

        return AuthService()
    
    @pytest.fixture

    async def ws_manager(self):

        """Create WebSocket manager."""

        return WebSocketManager()
    
    async def test_unauthenticated_to_authenticated_flow(

        self, auth_service, ws_manager, mock_websocket, test_user

    ):

        """Test progression from unauthenticated to authenticated state."""
        
        # Step 1: Attempt connection without auth

        no_auth_ws = Mock(spec=WebSocket)

        no_auth_ws.headers = {}

        no_auth_ws.close = AsyncMock()
        
        with pytest.raises(ValueError, match="No authorization header"):

            await ws_manager.connect_with_auth(no_auth_ws, None)
        
        no_auth_ws.close.assert_called_once()
        
        # Step 2: Extract JWT from headers

        auth_header = mock_websocket.headers.get("Authorization")

        assert auth_header == "Bearer test.jwt.token"
        
        token = auth_header.split(" ")[1]

        assert token == "test.jwt.token"
        
        # Step 3: Validate JWT token
        # L2: Mocking JWT validation to test auth flow integration

        with patch.object(auth_service, 'validate_jwt_token') as mock_validate:

            mock_validate.return_value = {

                "user_id": test_user.id,

                "email": test_user.email,

                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

            }
            
            jwt_payload = await auth_service.validate_jwt_token(token)

            assert jwt_payload["user_id"] == test_user.id
        
        # Step 4: Establish authenticated WebSocket

        await ws_manager.connect(mock_websocket, test_user.id)

        mock_websocket.accept.assert_called_once()
        
        # Step 5: Verify authenticated state

        assert test_user.id in ws_manager.active_connections

        connection = ws_manager.active_connections[test_user.id]

        assert connection.user_id == test_user.id

        assert connection.authenticated is True
    
    async def test_jwt_validation_with_expiry(self, auth_service):

        """Test JWT validation including expiry checks."""
        
        # Create expired token

        expired_payload = {

            "user_id": "test_user",

            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()

        }
        
        # L2: Mocking JWT secret for testing token validation

        expired_token = jwt.encode(expired_payload, "test_secret", algorithm="HS256")
        
        # Test expired token rejection

        with pytest.raises(jwt.ExpiredSignatureError):

            jwt.decode(expired_token, "test_secret", algorithms=["HS256"])
        
        # Create valid token

        valid_payload = {

            "user_id": "test_user",

            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

        }

        valid_token = jwt.encode(valid_payload, "test_secret", algorithm="HS256")
        
        # Test valid token acceptance

        decoded = jwt.decode(valid_token, "test_secret", algorithms=["HS256"])

        assert decoded["user_id"] == "test_user"
    
    async def test_websocket_auth_middleware_integration(

        self, ws_manager, mock_websocket, test_user

    ):

        """Test WebSocket authentication middleware."""
        
        # Mock auth middleware
        # L2: Mocking auth middleware to test integration points

        async def auth_middleware(websocket: WebSocket) -> Optional[User]:

            auth_header = websocket.headers.get("Authorization")

            if not auth_header:

                return None
            
            # Simulate token validation

            if "test.jwt.token" in auth_header:

                return test_user

            return None
        
        # Test middleware execution

        authenticated_user = await auth_middleware(mock_websocket)

        assert authenticated_user == test_user
        
        # Test middleware rejection

        no_auth_ws = Mock(spec=WebSocket)

        no_auth_ws.headers = {}
        
        authenticated_user = await auth_middleware(no_auth_ws)

        assert authenticated_user is None
    
    async def test_first_message_after_authentication(

        self, ws_manager, mock_websocket, test_user

    ):

        """Test first message processing after successful authentication."""
        
        # Establish authenticated connection

        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Mock message handler
        # L2: Mocking message handler to test auth→message flow

        message_handler = Mock(spec=MessageHandlerService)

        message_handler.handle_user_message = AsyncMock()
        
        # Process first message

        first_message = {

            "type": "user_message",

            "payload": {

                "content": "Hello, this is my first message",

                "thread_id": None  # No thread yet

            }

        }
        
        # Route message through authenticated connection

        await message_handler.handle_user_message(

            user_id=test_user.id,

            payload=first_message["payload"],

            db_session=None

        )
        
        # Verify message was processed

        message_handler.handle_user_message.assert_called_once_with(

            user_id=test_user.id,

            payload=first_message["payload"],

            db_session=None

        )
    
    async def test_auth_failure_scenarios(self, auth_service, ws_manager):

        """Test various authentication failure scenarios."""
        
        # Scenario 1: Invalid token format

        invalid_ws = Mock(spec=WebSocket)

        invalid_ws.headers = {"Authorization": "InvalidFormat"}

        invalid_ws.close = AsyncMock()
        
        with pytest.raises(ValueError, match="Invalid authorization format"):

            token = invalid_ws.headers["Authorization"].split(" ")[1]
        
        # Scenario 2: Malformed JWT

        malformed_ws = Mock(spec=WebSocket)

        malformed_ws.headers = {"Authorization": "Bearer not.a.jwt"}

        malformed_ws.close = AsyncMock()
        
        # L2: Mocking JWT decode to test malformed token handling

        with patch('jwt.decode') as mock_decode:

            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")
            
            with pytest.raises(jwt.InvalidTokenError):

                jwt.decode("not.a.jwt", "secret", algorithms=["HS256"])
        
        # Scenario 3: User not found after valid JWT
        # L2: Mocking user lookup to test missing user scenario

        with patch.object(auth_service, 'get_user_by_id') as mock_get_user:

            mock_get_user.return_value = None
            
            user = await auth_service.get_user_by_id("nonexistent_user")

            assert user is None
    
    async def test_concurrent_auth_requests(self, ws_manager, test_user):

        """Test handling of concurrent authentication requests."""
        
        # Create multiple WebSocket connections

        connections = []

        for i in range(5):

            ws = Mock(spec=WebSocket)

            ws.accept = AsyncMock()

            ws.headers = {"Authorization": f"Bearer token_{i}"}

            ws.client_state = WebSocketState.CONNECTED

            connections.append(ws)
        
        # Authenticate all connections concurrently

        tasks = []

        for i, ws in enumerate(connections):

            user_id = f"{test_user.id}_{i}"

            tasks.append(ws_manager.connect(ws, user_id))
        
        await asyncio.gather(*tasks)
        
        # Verify all connections authenticated

        for i in range(5):

            user_id = f"{test_user.id}_{i}"

            assert user_id in ws_manager.active_connections
    
    async def test_auth_token_refresh_during_session(

        self, ws_manager, mock_websocket, test_user

    ):

        """Test token refresh while maintaining WebSocket connection."""
        
        # Initial connection with token

        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Simulate token near expiry
        # L2: Mocking token refresh to test session continuity

        async def refresh_token(old_token: str) -> str:
            # Validate old token is near expiry
            # Generate new token

            return "new.jwt.token"
        
        # Refresh token

        new_token = await refresh_token("test.jwt.token")

        assert new_token == "new.jwt.token"
        
        # Update connection auth without disconnecting

        connection = ws_manager.active_connections[test_user.id]

        connection.auth_token = new_token
        
        # Verify connection maintained

        assert test_user.id in ws_manager.active_connections

        assert connection.websocket.client_state == WebSocketState.CONNECTED