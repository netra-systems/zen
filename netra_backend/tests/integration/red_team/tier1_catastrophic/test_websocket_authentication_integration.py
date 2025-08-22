"""
RED TEAM TEST 7: WebSocket Authentication Integration

DESIGN TO FAIL: This test is DESIGNED to FAIL initially to validate:
1. WebSocket connections with real JWT tokens from auth service
2. Token expiration during active WebSocket connection
3. WebSocket rejection with invalid tokens

These tests use real services and will expose actual authentication issues.
"""
import pytest
import asyncio
import websockets
import jwt
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import httpx
from typing import Dict, Any

from netra_backend.app.core.config import get_settings
from netra_backend.app.services.user_auth_service import UserAuthService
from netra_backend.app.websocket.ws_manager import WebSocketManager
from netra_backend.app.websocket.ws_auth import WebSocketAuth

# Import absolute paths
from netra_backend.tests.helpers.websocket_test_helpers import (
    create_test_websocket_client,
    generate_test_jwt_token,
    mock_auth_service_response
)


class TestWebSocketAuthenticationIntegration:
    """
    RED TEAM Test Suite: WebSocket Authentication Integration
    
    DESIGNED TO FAIL: These tests expose real WebSocket auth vulnerabilities
    """
    
    @pytest.fixture
    async def settings(self):
        """Get application settings"""
        return get_settings()
    
    @pytest.fixture
    async def auth_service(self, settings):
        """Real auth service instance"""
        return UserAuthService(settings)
    
    @pytest.fixture
    async def ws_manager(self, settings):
        """Real WebSocket manager"""
        manager = WebSocketManager(settings)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def ws_auth(self, settings, auth_service):
        """Real WebSocket authentication handler"""
        return WebSocketAuth(settings, auth_service)
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_real_jwt_fails(self, ws_manager, ws_auth, settings):
        """
        DESIGNED TO FAIL: Test WebSocket connections with real JWT tokens from auth service
        
        This test WILL FAIL because:
        1. JWT secret mismatch between services
        2. Token format incompatibility
        3. Missing required claims in JWT
        4. WebSocket auth not properly integrated with auth service
        """
        # Generate a "real" JWT token (this should match auth service format)
        real_jwt_claims = {
            "sub": "user123",
            "email": "test@example.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "aud": "netra-backend",
            "iss": "netra-auth-service",
            "user_id": "user123",
            "role": "user"
        }
        
        # Use the JWT secret from settings (this may not match auth service)
        jwt_secret = getattr(settings, 'jwt_secret', 'default_secret')
        real_jwt_token = jwt.encode(real_jwt_claims, jwt_secret, algorithm="HS256")
        
        # Try to establish WebSocket connection with real JWT
        websocket_url = f"ws://localhost:8000/ws?token={real_jwt_token}"
        
        # THIS WILL FAIL: WebSocket connection with real JWT
        try:
            async with websockets.connect(websocket_url, timeout=5) as websocket:
                # Send a test message
                test_message = {
                    "type": "test_message",
                    "content": "Hello WebSocket",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (this may timeout)
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                
                # THIS ASSERTION WILL FAIL - WebSocket auth likely broken
                assert response_data.get("status") == "authenticated", \
                    f"Expected successful authentication, got: {response_data}"
                    
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.InvalidStatusCode,
                asyncio.TimeoutError,
                ConnectionRefusedError) as e:
            # THIS SHOULD FAIL - indicating WebSocket auth issues
            pytest.fail(f"WebSocket connection with real JWT failed: {e}")
    
    @pytest.mark.asyncio
    async def test_token_expiration_during_active_websocket_fails(self, ws_manager, ws_auth):
        """
        DESIGNED TO FAIL: Test token expiration during active WebSocket connection
        
        This test WILL FAIL because:
        1. No automatic token refresh mechanism
        2. WebSocket doesn't handle token expiration gracefully
        3. Active connections don't validate token expiration
        """
        # Create a JWT token that expires in 2 seconds
        short_lived_claims = {
            "sub": "user123",
            "email": "test@example.com", 
            "iat": int(time.time()),
            "exp": int(time.time()) + 2,  # Expires in 2 seconds
            "user_id": "user123"
        }
        
        short_lived_token = jwt.encode(short_lived_claims, "test_secret", algorithm="HS256")
        websocket_url = f"ws://localhost:8000/ws?token={short_lived_token}"
        
        try:
            async with websockets.connect(websocket_url, timeout=5) as websocket:
                # Send initial message (should work)
                initial_message = {"type": "test", "content": "before expiration"}
                await websocket.send(json.dumps(initial_message))
                
                # Wait for token to expire
                await asyncio.sleep(3)
                
                # Try to send message after token expiration
                expired_message = {"type": "test", "content": "after expiration"}
                await websocket.send(json.dumps(expired_message))
                
                # THIS SHOULD FAIL: Connection should be closed due to expired token
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    # THIS ASSERTION WILL FAIL - expired tokens should reject messages
                    assert response_data.get("error") == "token_expired", \
                        f"Expected token expiration error, got: {response_data}"
                        
                except asyncio.TimeoutError:
                    # THIS WILL FAIL - WebSocket should actively reject expired tokens
                    pytest.fail("WebSocket accepted message with expired token - no expiration checking")
                    
        except websockets.exceptions.ConnectionClosed:
            # This is the expected behavior, but likely won't happen
            pass
        except (ConnectionRefusedError, OSError) as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_rejection_with_invalid_tokens_fails(self, ws_manager):
        """
        DESIGNED TO FAIL: Test WebSocket rejection with invalid tokens
        
        This test WILL FAIL because:
        1. Invalid tokens may be accepted due to weak validation
        2. Malformed JWTs might not be properly rejected
        3. Missing token validation in WebSocket handler
        """
        invalid_tokens = [
            "invalid.jwt.token",  # Malformed JWT
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",  # Invalid signature
            "",  # Empty token
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",  # Wrong format
            jwt.encode({"exp": int(time.time()) - 3600}, "wrong_secret", algorithm="HS256"),  # Expired with wrong secret
            jwt.encode({"sub": "user"}, "wrong_secret", algorithm="HS256"),  # Missing required claims
        ]
        
        rejection_count = 0
        acceptance_count = 0
        
        for i, invalid_token in enumerate(invalid_tokens):
            websocket_url = f"ws://localhost:8000/ws?token={invalid_token}"
            
            try:
                async with websockets.connect(websocket_url, timeout=3) as websocket:
                    # If connection succeeds, try to send a message
                    test_message = {"type": "test", "content": f"invalid token test {i}"}
                    await websocket.send(json.dumps(test_message))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        # THIS IS BAD: Invalid token was accepted
                        acceptance_count += 1
                    except asyncio.TimeoutError:
                        # Connection open but no response - still bad
                        acceptance_count += 1
                        
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidStatusCode,
                    ConnectionRefusedError,
                    OSError):
                # This is good - invalid token was rejected
                rejection_count += 1
            except Exception as e:
                # Unexpected error
                pytest.fail(f"Unexpected error with invalid token {i}: {e}")
        
        # THIS ASSERTION WILL FAIL - some invalid tokens will be accepted
        assert acceptance_count == 0, \
            f"Invalid tokens were accepted: {acceptance_count} accepted, {rejection_count} rejected"
        
        # All invalid tokens should be rejected
        assert rejection_count == len(invalid_tokens), \
            f"Not all invalid tokens were rejected: {rejection_count}/{len(invalid_tokens)}"
    
    @pytest.mark.asyncio
    async def test_websocket_auth_service_integration_failure(self, ws_auth, auth_service):
        """
        DESIGNED TO FAIL: Test integration between WebSocket auth and auth service
        
        This test WILL FAIL because:
        1. WebSocket auth doesn't properly call auth service
        2. Token validation logic is inconsistent
        3. User context not properly established
        """
        # Create a token that should be validated by auth service
        test_token_claims = {
            "sub": "user123",
            "email": "test@example.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "user_id": "user123",
            "role": "user"
        }
        
        test_token = jwt.encode(test_token_claims, "test_secret", algorithm="HS256")
        
        # Test WebSocket auth validation
        try:
            user_context = await ws_auth.authenticate_websocket(test_token)
            
            # THIS WILL FAIL: WebSocket auth may not properly integrate with auth service
            assert user_context is not None, "WebSocket auth returned None user context"
            assert user_context.user_id == "user123", f"Wrong user ID: {user_context.user_id}"
            assert user_context.email == "test@example.com", f"Wrong email: {user_context.email}"
            
            # Verify auth service was actually called
            # THIS WILL FAIL: Auth service integration likely missing
            with patch.object(auth_service, 'validate_jwt_token') as mock_validate:
                mock_validate.return_value = {"user_id": "user123", "email": "test@example.com"}
                
                # Call auth again to check if service is used
                user_context_2 = await ws_auth.authenticate_websocket(test_token)
                
                # THIS ASSERTION WILL FAIL if auth service isn't called
                assert mock_validate.called, "Auth service validate_jwt_token was not called"
                
        except Exception as e:
            # THIS WILL FAIL - WebSocket auth likely has integration issues
            pytest.fail(f"WebSocket auth service integration failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_auth_race_condition(self, ws_manager):
        """
        DESIGNED TO FAIL: Test concurrent WebSocket authentication race conditions
        
        This test WILL FAIL because:
        1. Race conditions in token validation
        2. Shared state corruption during concurrent auth
        3. Memory leaks from failed auth attempts
        """
        # Create multiple valid tokens for different users
        tokens = []
        for i in range(10):
            claims = {
                "sub": f"user{i}",
                "email": f"user{i}@example.com",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
                "user_id": f"user{i}"
            }
            token = jwt.encode(claims, "test_secret", algorithm="HS256")
            tokens.append(token)
        
        # Attempt concurrent WebSocket connections
        async def connect_websocket(token, user_id):
            try:
                websocket_url = f"ws://localhost:8000/ws?token={token}"
                async with websockets.connect(websocket_url, timeout=5) as websocket:
                    # Send identification message
                    message = {
                        "type": "identify",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send(json.dumps(message))
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    
                    return {
                        "success": True,
                        "user_id": user_id,
                        "response": response_data
                    }
            except Exception as e:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": str(e)
                }
        
        # Start concurrent connections
        tasks = [
            connect_websocket(token, f"user{i}") 
            for i, token in enumerate(tokens)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for race conditions
        successful_connections = [r for r in results if r.get("success", False)]
        failed_connections = [r for r in results if not r.get("success", False)]
        
        # THIS WILL FAIL: Concurrent auth may cause issues
        assert len(successful_connections) == len(tokens), \
            f"Race conditions in concurrent auth: {len(successful_connections)}/{len(tokens)} succeeded"
        
        # Check for user ID mixups (race condition indicator)
        user_ids_in_responses = [
            conn["response"].get("user_id") 
            for conn in successful_connections 
            if "response" in conn
        ]
        
        expected_user_ids = [f"user{i}" for i in range(10)]
        
        # THIS WILL FAIL if race conditions cause user ID mixups
        assert set(user_ids_in_responses) == set(expected_user_ids), \
            f"User ID mixup detected - race condition in auth: expected {expected_user_ids}, got {user_ids_in_responses}"
    
    @pytest.mark.asyncio 
    async def test_websocket_auth_memory_leak_during_failures(self, ws_manager):
        """
        DESIGNED TO FAIL: Test memory leaks during failed WebSocket auth attempts
        
        This test WILL FAIL because:
        1. Failed auth attempts may not clean up properly
        2. Connection objects leaked during auth failures
        3. Token validation caches not properly cleared
        """
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many failed auth attempts
        for i in range(100):
            invalid_token = f"invalid_token_{i}"
            websocket_url = f"ws://localhost:8000/ws?token={invalid_token}"
            
            try:
                # Each attempt should fail and clean up
                async with websockets.connect(websocket_url, timeout=1) as websocket:
                    await websocket.send(json.dumps({"type": "test"}))
                    await asyncio.wait_for(websocket.recv(), timeout=1)
            except:
                # Expected to fail
                pass
        
        # Force garbage collection
        import gc
        gc.collect()
        await asyncio.sleep(1)  # Allow cleanup
        
        # Check memory usage after failed attempts
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # THIS WILL FAIL: Memory should increase due to leaks
        max_acceptable_increase = 10 * 1024 * 1024  # 10MB
        assert memory_increase < max_acceptable_increase, \
            f"Memory leak detected: {memory_increase / 1024 / 1024:.2f}MB increase after 100 failed auth attempts"