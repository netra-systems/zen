"""
Test case for WebSocket JWT validation failure scenario.
Reproduces the authentication failure when auth service rejects the JWT token.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_websocket_jwt_validation_failure():
    """
    Test that reproduces WebSocket connection failure when JWT validation fails.
    
    This test simulates:
    1. WebSocket connection request with JWT in Sec-WebSocket-Protocol
    2. Auth service returning 401 Unauthorized
    3. WebSocket connection being rejected with proper error
    """
    from netra_backend.app.main import app
    
    # Mock the auth client to return validation failure
    with patch('netra_backend.app.clients.auth_client.auth_client') as mock_auth_client:
        # Configure auth client to return invalid token response
        mock_validate = AsyncMock(return_value={"valid": False})
        mock_auth_client.validate_token_jwt = mock_validate
        
        # Use TestClient for WebSocket testing
        with TestClient(app) as client:
            # Attempt WebSocket connection with JWT in subprotocol
            invalid_jwt = "Bearer invalid.jwt.token"
            
            try:
                # This should fail with authentication error
                with client.websocket_connect(
                    "/ws",
                    subprotocols=[invalid_jwt],
                    headers={
                        "Origin": "http://localhost:3000"
                    }
                ) as websocket:
                    # Should not reach here - connection should be rejected
                    assert False, "WebSocket connection should have been rejected"
                    
            except WebSocketDisconnect as e:
                # Expected behavior - connection rejected
                assert e.code == 1008  # Policy Violation
                assert "Authentication failed" in str(e.reason) or "Invalid or expired token" in str(e.reason)
                
            except Exception as e:
                # Check if it's the expected authentication error
                assert "Authentication failed" in str(e) or "Invalid or expired token" in str(e)
                
            # Verify auth validation was attempted
            mock_validate.assert_called_once_with(invalid_jwt)

@pytest.mark.asyncio 
async def test_websocket_auth_service_401_response():
    """
    Test WebSocket behavior when auth service returns explicit 401 status.
    
    Simulates the exact scenario from the logs where:
    - Auth service endpoint returns 401 Unauthorized
    - WebSocket connection is properly rejected
    """
    from httpx import Response

    from netra_backend.app.main import app
    
    # Mock httpx client to simulate 401 from auth service
    with patch('netra_backend.app.clients.auth_client_core.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Simulate 401 response from auth service
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid token"}
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        mock_client.post.return_value = mock_response
        
        with TestClient(app) as client:
            jwt_token = "Bearer test.jwt.token"
            
            try:
                with client.websocket_connect(
                    "/ws",
                    subprotocols=[jwt_token],
                    headers={
                        "Origin": "http://localhost:3000",
                        "Host": "localhost:8001"
                    }
                ) as websocket:
                    assert False, "Connection should have been rejected"
                    
            except (WebSocketDisconnect, Exception) as e:
                # Verify proper error handling
                error_msg = str(e)
                assert "401" in error_msg or "Authentication failed" in error_msg or "Invalid" in error_msg
                
            # Verify auth service was called
            mock_client.post.assert_called()
            call_args = mock_client.post.call_args
            assert "/auth/validate" in call_args[0][0]

@pytest.mark.asyncio
async def test_websocket_no_token_provided():
    """
    Test WebSocket rejection when no authentication token is provided.
    """
    from netra_backend.app.main import app
    
    with TestClient(app) as client:
        try:
            # Connect without any auth token
            with client.websocket_connect(
                "/ws",
                headers={
                    "Origin": "http://localhost:3000"
                }
            ) as websocket:
                assert False, "Should reject connection without auth"
                
        except (WebSocketDisconnect, Exception) as e:
            # Should get authentication required error
            assert "Authentication required" in str(e) or "No secure JWT token" in str(e)

@pytest.mark.asyncio
async def test_websocket_auth_token_validation_flow():
    """
    Test complete auth token validation flow matching the logs.
    
    Reproduces:
    - CORS validation success
    - Auth via Sec-WebSocket-Protocol
    - Auth service validation call returning 401
    - Proper error logging and connection rejection
    """
    import logging

    from netra_backend.app.main import app
    
    # Capture logs to verify proper error logging
    with patch('netra_backend.app.routes.websocket_unified.logger') as mock_logger:
        with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:
            # Auth validation returns invalid
            mock_validate.return_value = {"valid": False}
            
            with TestClient(app) as client:
                jwt_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
                
                try:
                    with client.websocket_connect(
                        "/ws", 
                        subprotocols=[jwt_token],
                        headers={
                            "Origin": "http://localhost:3000",
                            "Host": "localhost:8001"
                        }
                    ) as ws:
                        assert False, "Should not connect with invalid token"
                        
                except Exception as e:
                    # Verify the error matches expected
                    assert "Authentication failed" in str(e) or "Invalid" in str(e)
                    
                # Verify logging matches the pattern from the provided logs
                mock_logger.info.assert_any_call("WebSocket auth via Sec-WebSocket-Protocol")
                mock_logger.error.assert_any_call("WebSocket connection denied: Invalid JWT token")

@pytest.mark.asyncio
async def test_websocket_successful_auth_dev_environment():
    """
    Test successful WebSocket connection in development environment.
    Dev environment bypasses auth validation for local development.
    """
    import os

    from netra_backend.app.main import app
    
    # Set development environment
    with patch.dict(os.environ, {"ENVIRONMENT": "development", "DEV_MODE": "true"}):
        with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:
            # In dev mode, auth might be bypassed or always return valid
            mock_validate.return_value = {"valid": True, "user_id": "dev_user", "role": "developer"}
            
            with TestClient(app) as client:
                jwt_token = "Bearer dev.token.here"
                
                try:
                    with client.websocket_connect(
                        "/ws",
                        subprotocols=[jwt_token],
                        headers={
                            "Origin": "http://localhost:3000",
                            "Host": "localhost:8001"
                        }
                    ) as websocket:
                        # Connection should succeed in dev mode
                        # Send a test message
                        websocket.send_json({"type": "ping"})
                        
                        # Should receive some response
                        response = websocket.receive_json()
                        assert response is not None
                        
                        # Clean disconnect
                        websocket.close()
                        
                except Exception as e:
                    pytest.fail(f"Dev environment connection should succeed: {e}")

@pytest.mark.asyncio
async def test_websocket_successful_valid_oauth_token():
    """
    Test successful WebSocket connection with valid OAuth token.
    Simulates production scenario with valid JWT from OAuth provider.
    """
    from datetime import datetime, timedelta

    import jwt

    from netra_backend.app.main import app
    
    # Create a valid JWT token
    secret_key = "test_secret_key"
    payload = {
        "user_id": "oauth_user_123",
        "email": "user@example.com",
        "role": "user",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "iss": "netra-auth-service"
    }
    valid_jwt = jwt.encode(payload, secret_key, algorithm="HS256")
    
    with patch('netra_backend.app.core.auth_client.auth_client.validate_token') as mock_validate:
        # Auth service validates the token successfully
        mock_validate.return_value = {
            "valid": True,
            "user_id": "oauth_user_123",
            "email": "user@example.com",
            "role": "user",
            "exp": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        with TestClient(app) as client:
            auth_header = f"Bearer {valid_jwt}"
            
            try:
                with client.websocket_connect(
                    "/ws",
                    subprotocols=[auth_header],
                    headers={
                        "Origin": "http://localhost:3000",
                        "Host": "localhost:8001"
                    }
                ) as websocket:
                    # Connection should succeed with valid token
                    assert websocket is not None
                    
                    # Send initial message
                    websocket.send_json({
                        "type": "thread_list",
                        "data": {"page": 1}
                    })
                    
                    # Should receive response
                    response = websocket.receive_json()
                    assert response is not None
                    
                    # Verify auth was called with our token
                    mock_validate.assert_called_once_with(auth_header)
                    
                    websocket.close()
                    
            except Exception as e:
                pytest.fail(f"Valid OAuth token should allow connection: {e}")

@pytest.mark.asyncio
async def test_websocket_auth_with_authorization_header():
    """
    Test successful WebSocket connection using Authorization header instead of subprotocol.
    """
    from netra_backend.app.main import app
    
    with patch('netra_backend.app.core.auth_client.auth_client.validate_token') as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "user_id": "header_auth_user",
            "role": "user"
        }
        
        with TestClient(app) as client:
            jwt_token = "Bearer valid.header.token"
            
            try:
                with client.websocket_connect(
                    "/ws",
                    headers={
                        "Authorization": jwt_token,
                        "Origin": "http://localhost:3000",
                        "Host": "localhost:8001"
                    }
                ) as websocket:
                    # Should connect with auth header
                    assert websocket is not None
                    
                    # Test basic communication
                    websocket.send_json({"type": "status"})
                    response = websocket.receive_json()
                    assert response is not None
                    
                    websocket.close()
                    
            except Exception as e:
                pytest.fail(f"Authorization header auth should work: {e}")

@pytest.mark.asyncio
async def test_websocket_token_refresh_during_connection():
    """
    Test WebSocket connection handles token refresh properly.
    Simulates scenario where token is refreshed while connection is active.
    """
    from datetime import datetime, timedelta

    from netra_backend.app.main import app
    
    with patch('netra_backend.app.core.auth_client.auth_client.validate_token') as mock_validate:
        # Initial valid token
        mock_validate.return_value = {
            "valid": True,
            "user_id": "refresh_user",
            "role": "user",
            "exp": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        
        with TestClient(app) as client:
            jwt_token = "Bearer initial.token"
            
            try:
                with client.websocket_connect(
                    "/ws",
                    subprotocols=[jwt_token],
                    headers={
                        "Origin": "http://localhost:3000"
                    }
                ) as websocket:
                    # Initial connection succeeds
                    websocket.send_json({"type": "ping"})
                    response = websocket.receive_json()
                    assert response is not None
                    
                    # Simulate token refresh message
                    websocket.send_json({
                        "type": "auth_refresh",
                        "token": "Bearer refreshed.token"
                    })
                    
                    # Connection should remain active
                    websocket.send_json({"type": "ping"})
                    response = websocket.receive_json()
                    assert response is not None
                    
                    websocket.close()
                    
            except Exception as e:
                pytest.fail(f"Token refresh should be handled gracefully: {e}")

if __name__ == "__main__":
    # Run the tests
    print("Running WebSocket JWT validation failure tests...")
    asyncio.run(test_websocket_jwt_validation_failure())
    asyncio.run(test_websocket_auth_service_401_response())
    asyncio.run(test_websocket_no_token_provided())
    asyncio.run(test_websocket_auth_token_validation_flow())
    
    print("\nRunning WebSocket successful authentication tests...")
    asyncio.run(test_websocket_successful_auth_dev_environment())
    asyncio.run(test_websocket_successful_valid_oauth_token())
    asyncio.run(test_websocket_auth_with_authorization_header())
    asyncio.run(test_websocket_token_refresh_during_connection())
    
    print("\nAll tests completed!")