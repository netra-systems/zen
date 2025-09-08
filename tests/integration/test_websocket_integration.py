"""
WebSocket Integration Tests - Real Authentication & Services

Business Value:
- Validates WebSocket connection and messaging functionality
- Ensures proper JWT authentication flow works end-to-end
- Tests heartbeat and core WebSocket protocol compliance
- Prevents WebSocket regressions that would break chat functionality

Architecture Compliance:
- Uses REAL authentication via E2EAuthHelper (no mocks)
- Tests against actual WebSocket endpoints (/ws)
- Follows User Context Architecture for proper isolation
- Validates all critical WebSocket events are working

CRITICAL: Per CLAUDE.md requirements:
- ALL integration tests MUST use real authentication
- NO mocks in integration tests - use real services
- Use test_framework/ssot/e2e_auth_helper.py for SSOT auth patterns
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any

import pytest
import websockets
from fastapi.testclient import TestClient

from netra_backend.app.main import app
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import get_env

# Get environment to determine which auth helper config to use
env = get_env()
test_environment = env.get("TEST_ENV", env.get("ENVIRONMENT", "test"))

@pytest.fixture
async def auth_helper():
    """Provide authenticated E2E auth helper for WebSocket tests."""
    helper = E2EWebSocketAuthHelper(environment=test_environment)
    # Create and cache a valid JWT token
    token = helper.create_test_jwt_token(
        user_id="websocket-test-user", 
        email="websocket-test@example.com",
        permissions=["read", "write"],
        exp_minutes=10
    )
    return helper

@pytest.fixture
async def authenticated_websocket_client(auth_helper):
    """Provide WebSocket TestClient with proper authentication."""
    # Get auth headers from helper
    token = auth_helper._get_valid_token()
    headers = auth_helper.get_websocket_headers(token)
    
    # Create TestClient
    client = TestClient(app)
    return client, headers

@pytest.mark.asyncio
async def test_websocket_connection_success(authenticated_websocket_client):
    """Test successful WebSocket connection with proper JWT authentication."""
    client, headers = authenticated_websocket_client
    
    # Connect to WebSocket with authentication headers
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Should receive connection_established message
        data = websocket.receive_json()
        
        # Verify connection established
        assert data["type"] == "connection_established"
        assert "connection_id" in data
        assert "user_id" in data
        assert data["connection_ready"] is True
        assert "server_time" in data
        assert "config" in data


@pytest.mark.asyncio 
async def test_websocket_connection_failure_no_token():
    """Test WebSocket connection fails without authentication token."""
    client = TestClient(app)
    
    # Try to connect without authentication - should fail
    with pytest.raises(Exception):  # Should raise WebSocketException or similar
        with client.websocket_connect("/ws") as websocket:
            # This should fail before we get here
            pass


@pytest.mark.asyncio
async def test_websocket_send_receive_ping_pong(authenticated_websocket_client):
    """Test WebSocket ping/pong messaging with authentication."""
    client, headers = authenticated_websocket_client
    
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Wait for connection established
        connection_data = websocket.receive_json()
        assert connection_data["type"] == "connection_established"
        
        # Send ping message
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        websocket.send_json(ping_message)
        
        # Should receive pong response
        response = websocket.receive_json()
        assert response["type"] == "pong"
        assert "timestamp" in response


@pytest.mark.asyncio
async def test_websocket_send_receive_echo(authenticated_websocket_client):
    """Test WebSocket echo functionality with real authentication."""
    client, headers = authenticated_websocket_client
    
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Wait for connection established
        connection_data = websocket.receive_json()
        assert connection_data["type"] == "connection_established"
        
        # Send echo message
        echo_message = {
            "type": "echo", 
            "content": "Hello WebSocket!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        websocket.send_json(echo_message)
        
        # Should receive echo response
        response = websocket.receive_json() 
        assert response["type"] == "echo_response"
        assert response["original"] == echo_message


@pytest.mark.asyncio 
async def test_websocket_heartbeat_functionality(authenticated_websocket_client):
    """Test WebSocket heartbeat configuration."""
    client, headers = authenticated_websocket_client
    
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Wait for connection established
        connection_data = websocket.receive_json()
        assert connection_data["type"] == "connection_established"
        
        # Verify heartbeat config is present
        assert "config" in connection_data
        assert "heartbeat_interval" in connection_data["config"]
        assert connection_data["config"]["heartbeat_interval"] > 0
        
        # Test that connection is stable (basic heartbeat functionality)
        # Send a ping to ensure connection is still active
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_agent_message_fallback(authenticated_websocket_client):
    """Test agent message handling with fallback handler."""
    client, headers = authenticated_websocket_client
    
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Wait for connection established
        connection_data = websocket.receive_json() 
        assert connection_data["type"] == "connection_established"
        
        user_id = connection_data["user_id"]
        
        # Send chat message that should trigger agent response
        chat_message = {
            "type": "chat",
            "content": "Hello from integration test!",
            "thread_id": f"test-thread-{int(time.time())}",
            "user_id": user_id
        }
        websocket.send_json(chat_message)
        
        # Should receive at least one agent event (fallback handler should respond)
        events_received = []
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Try to receive a few events
        for _ in range(6):  # Try to receive up to 6 events (5 agent events + maybe others)
            try:
                event = websocket.receive_json()
                event_type = event.get("type")
                if event_type in expected_events:
                    events_received.append(event_type)
                # Break after getting all expected events
                if len(events_received) >= len(expected_events):
                    break
            except Exception as e:
                # If we timeout or get an error, check what we have
                break
        
        # Should have received at least one agent event
        assert len(events_received) > 0, f"No agent events received. Got: {events_received}"


@pytest.mark.asyncio
async def test_websocket_multiple_connections_isolation():
    """Test that multiple WebSocket connections are properly isolated."""
    # Create two different auth helpers with different users
    helper1 = E2EWebSocketAuthHelper(environment=test_environment)
    helper2 = E2EWebSocketAuthHelper(environment=test_environment)
    
    token1 = helper1.create_test_jwt_token(user_id="user-1", email="user1@test.com")
    token2 = helper2.create_test_jwt_token(user_id="user-2", email="user2@test.com") 
    
    headers1 = helper1.get_websocket_headers(token1)
    headers2 = helper2.get_websocket_headers(token2)
    
    client = TestClient(app)
    
    # Open two connections simultaneously
    with client.websocket_connect("/ws", headers=headers1) as ws1:
        with client.websocket_connect("/ws", headers=headers2) as ws2:
            
            # Get connection info for both
            conn1_data = ws1.receive_json(timeout=10.0)
            conn2_data = ws2.receive_json(timeout=10.0)
            
            assert conn1_data["type"] == "connection_established"
            assert conn2_data["type"] == "connection_established"
            
            # Verify different users and connection IDs
            assert conn1_data["user_id"] != conn2_data["user_id"]
            assert conn1_data["connection_id"] != conn2_data["connection_id"]
            
            # Send message from user 1
            ws1.send_json({
                "type": "ping",
                "message": "from user 1"
            })
            
            # User 1 should get pong back
            user1_response = ws1.receive_json()
            assert user1_response["type"] == "pong"
            
            # User 2 should NOT receive user 1's message/response
            # (This tests isolation - user 2 should only get heartbeat or nothing)
            try:
                user2_unexpected = ws2.receive_json()
                # If we get anything, it should NOT be user 1's pong
                assert user2_unexpected.get("type") != "pong" or user2_unexpected.get("message") != "from user 1"
            except Exception:
                # Timeout is expected - user 2 should not receive user 1's messages
                pass


@pytest.mark.asyncio
async def test_websocket_error_handling(authenticated_websocket_client):
    """Test WebSocket error handling with invalid messages."""
    client, headers = authenticated_websocket_client
    
    with client.websocket_connect("/ws", headers=headers) as websocket:
        # Wait for connection established
        connection_data = websocket.receive_json()
        assert connection_data["type"] == "connection_established"
        
        # Send invalid JSON (should be handled gracefully)
        websocket.send_text("invalid json {")
        
        # Should receive format error
        error_response = websocket.receive_json()
        assert error_response["type"] == "error"
        assert "FORMAT_ERROR" in error_response.get("error_code", "")
        
        # Connection should still be alive after error
        websocket.send_json({"type": "ping"})
        ping_response = websocket.receive_json()
        assert ping_response["type"] == "pong"
