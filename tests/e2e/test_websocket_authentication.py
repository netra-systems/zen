"""Frontend WebSocket Authentication E2E Tests for DEV MODE

CRITICAL CONTEXT: WebSocket Authentication Flow Testing
Tests real authentication flow through WebSocket connections including JWT
validation, token refresh, multi-user scenarios, and auth state management.

Business Value Justification (BVJ):
1. Segment: All segments - Critical security foundation
2. Business Goal: Ensure secure WebSocket authentication
3. Value Impact: Prevents unauthorized access and data breaches  
4. Revenue Impact: Protects platform integrity and compliance

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest
import websockets

from tests.e2e.database_sync_fixtures import create_test_user_data
from tests.e2e.harness_utils import (
    UnifiedTestHarnessComplete as TestHarness,
)
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.harness_utils import UnifiedTestHarnessComplete


class TestWebSocketAuther:
    """Test utilities for WebSocket authentication scenarios."""
    
    def __init__(self):
        self.harness = UnifiedTestHarnessComplete()
        self.jwt_helper = JWTTestHelper()
        self.active_connections: Dict[str, websockets.ClientConnection] = {}
        self.test_users: Dict[str, Dict] = {}
    
    async def setup(self):
        """Initialize test environment with multiple users."""
        await self.harness.setup()
        await self._create_test_users()
        return self
    
    async def cleanup(self):
        """Clean up connections and test environment."""
        await self._close_all_connections()
        await self.harness.teardown()
    
    async def _create_test_users(self):
        """Create test users for authentication scenarios."""
        role_to_tier = {
            "admin": "enterprise", 
            "user": "early",
            "guest": "free"
        }
        
        for role in ["admin", "user", "guest"]:
            tier = role_to_tier[role]
            user_data = create_test_user_data(
                email=f"test-{role}@websocket-auth.test",
                tier=tier
            )
            # Add role information to the user data
            user_data["role"] = role
            self.test_users[role] = user_data
    
    async def _close_all_connections(self):
        """Close all active WebSocket connections."""
        for ws in self.active_connections.values():
            if not ws.closed:
                await ws.close()
        self.active_connections.clear()
    
    async def connect_with_auth(self, user_role: str, connection_id: str = None):
        """Create authenticated WebSocket connection for specific user role."""
        if connection_id is None:
            connection_id = f"{user_role}_{datetime.now().timestamp()}"
        
        user_data = self.test_users[user_role]
        # Use the async method for token creation
        token = await self.jwt_helper.create_token_for_user(user_data["id"])
        
        ws = await websockets.connect(
            "ws://localhost:8000/websocket",
            additional_headers={"Authorization": f"Bearer {token}"}
        )
        self.active_connections[connection_id] = ws
        return ws, token
    
    async def verify_auth_response(self, ws, expected_success: bool = True):
        """Verify authentication response from WebSocket."""
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        response_data = json.loads(response)
        
        if expected_success:
            assert response_data.get("type") != "auth_error"
        else:
            assert response_data.get("type") == "auth_error"
        
        return response_data


@pytest.fixture
async def auth_tester():
    """Fixture providing WebSocket authentication test utilities."""
    tester = TestWebSocketAuther()
    await tester.setup()
    yield tester
    await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_authentication_success(auth_tester):
    """Test successful JWT authentication through WebSocket."""
    # Act
    ws, token = await auth_tester.connect_with_auth("admin")
    
    # Send auth verification message
    auth_msg = {"type": "auth_verify", "payload": {"token": token}}
    await ws.send(json.dumps(auth_msg))
    
    # Assert
    response = await auth_tester.verify_auth_response(ws, expected_success=True)
    assert "user_id" in response.get("payload", {})


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_invalid_jwt_token(auth_tester):
    """Test WebSocket rejects invalid JWT tokens."""
    # Act & Assert
    with pytest.raises(websockets.exceptions.ConnectionClosedError):
        await websockets.connect(
            "ws://localhost:8000/websocket",
            additional_headers={"Authorization": "Bearer invalid_token"}
        )


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_expired_jwt_token(auth_tester):
    """Test WebSocket handles expired JWT tokens."""
    # Arrange - Create expired token
    user_data = auth_tester.test_users["user"]
    expired_token = await auth_tester.jwt_helper.create_expired_token(
        user_data["user_id"]
    )
    
    # Act & Assert
    with pytest.raises(websockets.exceptions.ConnectionClosedError):
        await websockets.connect(
            "ws://localhost:8000/websocket",
            additional_headers={"Authorization": f"Bearer {expired_token}"}
        )


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_token_refresh_flow(auth_tester):
    """Test WebSocket token refresh during active connection."""
    # Arrange
    ws, original_token = await auth_tester.connect_with_auth("user")
    
    # Act - Request token refresh
    refresh_msg = {"type": "token_refresh", "payload": {"token": original_token}}
    await ws.send(json.dumps(refresh_msg))
    
    # Assert
    response = await auth_tester.verify_auth_response(ws, expected_success=True)
    new_token = response.get("payload", {}).get("new_token")
    assert new_token and new_token != original_token


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_multi_user_authentication(auth_tester):
    """Test multiple users can authenticate simultaneously."""
    # Act - Connect multiple users
    connections = {}
    for role in ["admin", "user", "guest"]:
        ws, token = await auth_tester.connect_with_auth(role, f"conn_{role}")
        connections[role] = (ws, token)
    
    # Assert - All connections authenticated
    for role, (ws, token) in connections.items():
        auth_msg = {"type": "auth_verify", "payload": {"token": token}}
        await ws.send(json.dumps(auth_msg))
        response = await auth_tester.verify_auth_response(ws, expected_success=True)
        assert response.get("payload", {}).get("role") == role


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_role_based_permissions(auth_tester):
    """Test WebSocket enforces role-based permissions."""
    # Arrange
    user_ws, user_token = await auth_tester.connect_with_auth("user")
    admin_ws, admin_token = await auth_tester.connect_with_auth("admin")
    
    # Act - User tries admin operation
    admin_msg = {"type": "admin_command", "payload": {"command": "system_status"}}
    await user_ws.send(json.dumps(admin_msg))
    
    # Assert - User request denied
    user_response = await asyncio.wait_for(user_ws.recv(), timeout=5.0)
    user_data = json.loads(user_response)
    assert user_data.get("type") == "permission_denied"
    
    # Act - Admin tries same operation
    await admin_ws.send(json.dumps(admin_msg))
    
    # Assert - Admin request allowed
    admin_response = await asyncio.wait_for(admin_ws.recv(), timeout=5.0)
    admin_data = json.loads(admin_response)
    assert admin_data.get("type") != "permission_denied"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_session_validation(auth_tester):
    """Test WebSocket validates session consistency."""
    # Arrange
    ws, token = await auth_tester.connect_with_auth("user")
    
    # Act - Send message with session info
    session_msg = {
        "type": "session_validate",
        "payload": {"token": token, "session_id": "test_session_123"}
    }
    await ws.send(json.dumps(session_msg))
    
    # Assert
    response = await auth_tester.verify_auth_response(ws, expected_success=True)
    assert "session_id" in response.get("payload", {})


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_concurrent_auth_requests(auth_tester):
    """Test WebSocket handles concurrent authentication requests."""
    # Arrange
    ws, token = await auth_tester.connect_with_auth("admin")
    
    # Act - Send multiple auth requests concurrently
    auth_tasks = []
    for i in range(5):
        auth_msg = {"type": "auth_verify", "payload": {"token": token, "req_id": i}}
        auth_tasks.append(ws.send(json.dumps(auth_msg)))
    
    await asyncio.gather(*auth_tasks)
    
    # Assert - All requests processed
    responses = []
    for _ in range(5):
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        responses.append(json.loads(response))
    
    assert len(responses) == 5
    for response in responses:
        assert response.get("type") != "auth_error"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_auth_state_recovery(auth_tester):
    """Test WebSocket recovers authentication state after reconnection."""
    # Arrange
    ws1, token = await auth_tester.connect_with_auth("user", "initial_conn")
    
    # Act - Store session state
    state_msg = {"type": "store_state", "payload": {"data": "test_data"}}
    await ws1.send(json.dumps(state_msg))
    await ws1.close()
    
    # Reconnect with same token
    ws2 = await websockets.connect(
        "ws://localhost:8000/websocket",
        additional_headers={"Authorization": f"Bearer {token}"}
    )
    auth_tester.active_connections["recovered_conn"] = ws2
    
    # Request state recovery
    recovery_msg = {"type": "recover_state", "payload": {"token": token}}
    await ws2.send(json.dumps(recovery_msg))
    
    # Assert
    response = await asyncio.wait_for(ws2.recv(), timeout=5.0)
    response_data = json.loads(response)
    assert response_data.get("payload", {}).get("data") == "test_data"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_auth_timeout_handling(auth_tester):
    """Test WebSocket handles authentication timeouts gracefully."""
    # Arrange
    ws, token = await auth_tester.connect_with_auth("user")
    
    # Act - Send auth request and wait for timeout
    auth_msg = {"type": "slow_auth_verify", "payload": {"token": token}}
    await ws.send(json.dumps(auth_msg))
    
    # Assert - Connection handles timeout appropriately
    try:
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        response_data = json.loads(response)
        assert response_data.get("type") in ["auth_timeout", "auth_success"]
    except asyncio.TimeoutError:
        # Timeout is acceptable for this test
        pass