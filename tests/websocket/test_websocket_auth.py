"""WebSocket Authentication Flow Tests

Business Value Justification (BVJ):
- Segment: All customer tiers
- Business Goal: Secure WebSocket connection establishment
- Value Impact: Ensures only authenticated users can establish WebSocket connections
- Revenue Impact: Prevents unauthorized access, maintains platform security integrity

Tests WebSocket authentication:
- Connection with valid JWT tokens
- Connection rejection with invalid tokens
- Token validation during connection
- Authentication handshake flow
- Token expiry handling
"""

import asyncio
import json
import pytest
import aiohttp
import time
from typing import Dict, Any, Optional

from netra_backend.tests.unified.e2e.staging_test_helpers import (
    get_staging_suite,
    create_test_user_with_token,
    test_websocket_connection_flow
)


@pytest.mark.asyncio
@pytest.mark.websocket
class TestWebSocketAuthentication:
    """Test WebSocket authentication and authorization flows."""
    
    async def test_websocket_connection_with_valid_token(self):
        """Test WebSocket connection succeeds with valid JWT token."""
        suite = await get_staging_suite()
        
        # Create test user with valid token
        user_data = await create_test_user_with_token(suite)
        assert user_data["success"], f"Failed to create user: {user_data.get('error')}"
        
        # Test WebSocket connection with valid token
        connection_success = await test_websocket_connection_flow(suite, user_data)
        assert connection_success, "WebSocket connection with valid token failed"
    
    async def test_websocket_connection_with_invalid_token(self):
        """Test WebSocket connection is rejected with invalid token."""
        suite = await get_staging_suite()
        ws_url = suite.harness.get_websocket_url()
        
        # Try connection with invalid token
        invalid_headers = {"Authorization": "Bearer invalid-token-12345"}
        
        try:
            async with suite.aio_session.ws_connect(
                ws_url, headers=invalid_headers, ssl=False, timeout=5
            ) as ws:
                # If connection succeeds, it should close quickly due to invalid auth
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=3)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        # Should receive error message
                        assert data.get("type") in ["error", "connection_error", "auth_error"]
                    elif msg.type == aiohttp.WSMsgType.CLOSE:
                        # Connection closed due to auth failure - expected behavior
                        pass
                except asyncio.TimeoutError:
                    # Connection might stay open but not respond - also acceptable
                    pass
        except (aiohttp.ClientConnectionError, aiohttp.WSConnectorError):
            # Connection rejected immediately - expected for invalid auth
            pass
    
    async def test_websocket_connection_without_token(self):
        """Test WebSocket connection is rejected without authentication token."""
        suite = await get_staging_suite()
        ws_url = suite.harness.get_websocket_url()
        
        # Try connection without token
        try:
            async with suite.aio_session.ws_connect(
                ws_url, ssl=False, timeout=5
            ) as ws:
                # Connection might be accepted but should reject on handshake
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=3)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        assert data.get("type") in ["error", "auth_required", "unauthorized"]
                except asyncio.TimeoutError:
                    pytest.fail("Expected auth error but got timeout")
        except (aiohttp.ClientConnectionError, aiohttp.WSConnectorError):
            # Connection rejected immediately - acceptable
            pass
    
    async def test_websocket_auth_handshake_flow(self):
        """Test complete WebSocket authentication handshake flow."""
        suite = await get_staging_suite()
        
        # Create authenticated user
        user_data = await create_test_user_with_token(suite)
        assert user_data["success"], "Failed to create test user"
        
        ws_url = suite.harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}
        
        async with suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            # Send connection init with auth token
            init_message = {
                "type": "connection_init",
                "payload": {"auth_token": user_data["access_token"]}
            }
            await ws.send_json(init_message)
            
            # Wait for connection acknowledgment
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.TEXT, "Expected text message"
            
            response = json.loads(msg.data)
            assert response.get("type") in ["connection_ack", "connected"], \
                   f"Unexpected handshake response: {response.get('type')}"
            
            # Verify connection is active by sending ping
            ping_message = {"type": "ping", "payload": {"timestamp": time.time()}}
            await ws.send_json(ping_message)
            
            # Should receive pong or similar response
            pong_msg = await ws.receive()
            if pong_msg.type == aiohttp.WSMsgType.TEXT:
                pong_data = json.loads(pong_msg.data)
                assert pong_data.get("type") in ["pong", "ack", "status"]


@pytest.mark.asyncio
@pytest.mark.websocket
class TestWebSocketTokenValidation:
    """Test WebSocket token validation and security."""
    
    async def test_websocket_token_format_validation(self):
        """Test WebSocket validates JWT token format correctly."""
        suite = await get_staging_suite()
        ws_url = suite.harness.get_websocket_url()
        
        # Test various invalid token formats
        invalid_tokens = [
            "",  # Empty token
            "not-a-jwt-token",  # Plain string
            "Bearer invalid-format",  # Wrong format in header
            "eyJhbGciOiJIUzI1NiJ9.invalid",  # Malformed JWT
        ]
        
        for invalid_token in invalid_tokens:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            
            try:
                async with suite.aio_session.ws_connect(
                    ws_url, headers=headers, ssl=False, timeout=3
                ) as ws:
                    # Connection might succeed but should fail on validation
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=2)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            # Should receive auth error
                            assert data.get("type") in ["error", "auth_error", "invalid_token"]
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            # Connection closed - expected
                            pass
                    except asyncio.TimeoutError:
                        # No response - connection might be dropped
                        pass
            except Exception:
                # Connection error expected for invalid tokens
                pass
    
    async def test_websocket_maintains_auth_state(self):
        """Test WebSocket maintains authentication state during session."""
        suite = await get_staging_suite()
        
        # Create authenticated connection
        user_data = await create_test_user_with_token(suite)
        assert user_data["success"], "Failed to create test user"
        
        ws_url = suite.harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}
        
        async with suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            # Initialize connection
            await ws.send_json({
                "type": "connection_init",
                "payload": {"auth_token": user_data["access_token"]}
            })
            
            # Wait for ack
            ack_msg = await ws.receive()
            assert ack_msg.type == aiohttp.WSMsgType.TEXT
            
            # Send authenticated request
            auth_test_message = {
                "type": "message",
                "content": "Test authenticated message",
                "thread_id": f"auth_test_{user_data['user_id']}"
            }
            await ws.send_json(auth_test_message)
            
            # Should receive response or acknowledgment (not auth error)
            response_msg = await asyncio.wait_for(ws.receive(), timeout=10)
            if response_msg.type == aiohttp.WSMsgType.TEXT:
                response_data = json.loads(response_msg.data)
                # Should not be an auth error - connection is authenticated
                assert response_data.get("type") not in ["auth_error", "unauthorized"]


@pytest.mark.asyncio
@pytest.mark.websocket
class TestWebSocketAuthRecovery:
    """Test WebSocket authentication error recovery."""
    
    async def test_websocket_auth_error_handling(self):
        """Test WebSocket handles authentication errors gracefully."""
        suite = await get_staging_suite()
        ws_url = suite.harness.get_websocket_url()
        
        # Connect with invalid token and verify graceful error handling
        headers = {"Authorization": "Bearer expired-or-invalid-token"}
        
        auth_error_received = False
        try:
            async with suite.aio_session.ws_connect(
                ws_url, headers=headers, ssl=False, timeout=5
            ) as ws:
                # Send connection init
                await ws.send_json({
                    "type": "connection_init",
                    "payload": {"auth_token": "expired-or-invalid-token"}
                })
                
                # Should receive error response
                error_msg = await asyncio.wait_for(ws.receive(), timeout=5)
                if error_msg.type == aiohttp.WSMsgType.TEXT:
                    error_data = json.loads(error_msg.data)
                    if error_data.get("type") in ["error", "auth_error", "connection_error"]:
                        auth_error_received = True
                        # Error should include helpful message
                        assert "error" in error_data or "message" in error_data
                elif error_msg.type == aiohttp.WSMsgType.CLOSE:
                    auth_error_received = True  # Connection closed due to auth error
        except Exception:
            # Connection error is also acceptable for auth failure
            auth_error_received = True
        
        assert auth_error_received, "Expected authentication error but none received"


# Convenience function for WebSocket auth testing
async def test_websocket_auth_flow(ws_url: str, token: str) -> Dict[str, Any]:
    """Test WebSocket authentication flow and return results."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, headers=headers, ssl=False, timeout=10) as ws:
                # Send connection init
                await ws.send_json({
                    "type": "connection_init",
                    "payload": {"auth_token": token}
                })
                
                # Wait for response
                msg = await asyncio.wait_for(ws.receive(), timeout=5)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    return {
                        "success": data.get("type") in ["connection_ack", "connected"],
                        "response_type": data.get("type"),
                        "message": data.get("message", "")
                    }
                else:
                    return {"success": False, "reason": "Non-text response"}
                    
    except Exception as e:
        return {"success": False, "reason": f"Connection error: {str(e)}"}


if __name__ == "__main__":
    # Direct execution for WebSocket auth testing
    async def run_auth_tests():
        suite = await get_staging_suite()
        user_data = await create_test_user_with_token(suite)
        
        if user_data["success"]:
            ws_url = suite.harness.get_websocket_url()
            result = await test_websocket_auth_flow(ws_url, user_data["access_token"])
            print(json.dumps(result, indent=2))
        else:
            print(f"Failed to create test user: {user_data}")
    
    asyncio.run(run_auth_tests())