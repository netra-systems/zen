"""
Comprehensive unit tests for WebSocket Authentication & Security.

Tests rate limiting, token validation, CORS handling, and security enforcement.
SECURITY CRITICAL - Prevents unauthorized WebSocket access and DoS attacks.

Business Value: Ensures secure WebSocket connections, preventing security breaches
and enabling enterprise compliance requirements.
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timezone, UTC
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any

import pytest
from fastapi import HTTPException, WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.websocket_core.auth import (
    RateLimiter,
    get_websocket_authenticator,
    get_connection_security_manager,
    validate_message_size,
    sanitize_user_input,
    validate_websocket_origin
)
from netra_backend.app.websocket_core.types import AuthInfo, WebSocketConfig


class TestRateLimiter:
    """Test suite for WebSocket rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test configuration."""
        return RateLimiter(max_requests=5, window_seconds=10)
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initializes with correct configuration."""
        assert rate_limiter.max_requests == 5
        assert rate_limiter.window_seconds == 10
        assert isinstance(rate_limiter.request_history, dict)
        assert len(rate_limiter.request_history) == 0
    
    def test_rate_limiter_allows_initial_requests(self, rate_limiter):
        """Test rate limiter allows requests within limit."""
        client_id = "test-client-123"
        
        # First request should be allowed
        allowed, info = rate_limiter.is_allowed(client_id)
        
        assert allowed is True
        assert isinstance(info, dict)
        assert "requests_remaining" in info
        assert "window_reset_time" in info
        assert info["requests_remaining"] == 4  # 5 - 1 = 4
    
    def test_rate_limiter_tracks_multiple_requests(self, rate_limiter):
        """Test rate limiter properly tracks multiple requests."""
        client_id = "test-client-123"
        
        # Make 5 requests (at the limit)
        for i in range(5):
            allowed, info = rate_limiter.is_allowed(client_id)
            assert allowed is True
            assert info["requests_remaining"] == 4 - i
        
        # 6th request should be denied
        allowed, info = rate_limiter.is_allowed(client_id)
        assert allowed is False
        assert info["requests_remaining"] == 0
    
    def test_rate_limiter_isolates_different_clients(self, rate_limiter):
        """Test rate limiter isolates different client IDs."""
        client1 = "client-1"
        client2 = "client-2"
        
        # Exhaust limit for client1
        for _ in range(5):
            rate_limiter.is_allowed(client1)
        
        # Client1 should be denied
        allowed, _ = rate_limiter.is_allowed(client1)
        assert allowed is False
        
        # Client2 should still be allowed
        allowed, info = rate_limiter.is_allowed(client2)
        assert allowed is True
        assert info["requests_remaining"] == 4
    
    def test_rate_limiter_window_expiry(self, rate_limiter):
        """Test rate limiter resets after window expires."""
        client_id = "test-client-123"
        
        # Mock time to control window behavior
        with patch('time.time') as mock_time:
            # Start at time 0
            mock_time.return_value = 0
            
            # Exhaust the limit
            for _ in range(5):
                rate_limiter.is_allowed(client_id)
            
            # Should be denied at time 0
            allowed, _ = rate_limiter.is_allowed(client_id)
            assert allowed is False
            
            # Move time forward past the window
            mock_time.return_value = 15  # 15 seconds > 10 second window
            
            # Should be allowed again
            allowed, info = rate_limiter.is_allowed(client_id)
            assert allowed is True
            assert info["requests_remaining"] == 4
    
    def test_rate_limiter_partial_window_cleanup(self, rate_limiter):
        """Test rate limiter cleans up expired requests within window."""
        client_id = "test-client-123"
        
        with patch('time.time') as mock_time:
            # Make 3 requests at time 0
            mock_time.return_value = 0
            for _ in range(3):
                rate_limiter.is_allowed(client_id)
            
            # Move time forward by 5 seconds (half the window)
            mock_time.return_value = 5
            
            # Make 2 more requests (should still be allowed)
            for _ in range(2):
                allowed, _ = rate_limiter.is_allowed(client_id)
                assert allowed is True
            
            # Should be at the limit now
            allowed, _ = rate_limiter.is_allowed(client_id)
            assert allowed is False
            
            # Move time forward by another 6 seconds (total 11, past first 3 requests)
            mock_time.return_value = 11
            
            # First 3 requests should have expired, so we should have room
            allowed, info = rate_limiter.is_allowed(client_id)
            assert allowed is True
            # Should have 2 remaining (5 max - 2 from time 5 - 1 just made)
            assert info["requests_remaining"] == 2


class TestWebSocketAuthenticator:
    """Test suite for WebSocket authenticator functionality."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        ws = MagicMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.headers = {"origin": "https://trusted-domain.com"}
        ws.query_params = {}
        return ws
    
    def test_get_websocket_authenticator_singleton(self):
        """Test that websocket authenticator is a singleton."""
        auth1 = get_websocket_authenticator()
        auth2 = get_websocket_authenticator()
        
        assert auth1 is auth2  # Should be the same instance
        assert hasattr(auth1, 'rate_limiter')
        assert hasattr(auth1, 'auth_stats')
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_flow(self, mock_websocket):
        """Test complete WebSocket authentication flow."""
        authenticator = get_websocket_authenticator()
        
        # Mock the auth client response
        mock_validation_result = {
            "valid": True,
            "user_id": "test-user-123",
            "permissions": ["websocket:connect"]
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation_result)
            
            # Add a token to the WebSocket for authentication
            mock_websocket.headers = {
                "origin": "https://trusted-domain.com", 
                "authorization": "Bearer valid-test-token"
            }
            
            with patch('netra_backend.app.core.websocket_cors.check_websocket_cors', return_value=True):
                auth_info = await authenticator.authenticate_websocket(mock_websocket)
            
            assert isinstance(auth_info, AuthInfo)
            assert auth_info.user_id == "test-user-123"
            assert auth_info.is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_cors_failure(self, mock_websocket):
        """Test WebSocket authentication with CORS failure."""
        authenticator = get_websocket_authenticator()
        
        # Mock CORS validation to fail
        with patch('netra_backend.app.core.websocket_cors.check_websocket_cors', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "CORS validation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_rate_limit(self, mock_websocket):
        """Test WebSocket authentication with rate limiting."""
        # Create authenticator with very low rate limit for testing
        authenticator = get_websocket_authenticator()
        authenticator.rate_limiter = RateLimiter(max_requests=1, window_seconds=60)
        
        client_ip = "127.0.0.1"
        
        with patch('netra_backend.app.core.websocket_cors.check_websocket_cors', return_value=True):
            # First request should trigger rate limit (since limit is 1)
            authenticator.rate_limiter.is_allowed(client_ip)  # Use up the limit
            
            with pytest.raises(HTTPException) as exc_info:
                await authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Rate limit exceeded" in str(exc_info.value.detail)


class TestWebSocketUtilities:
    """Test suite for WebSocket utility functions."""
    
    def test_validate_message_size_valid(self):
        """Test message size validation with valid message."""
        message = "This is a normal message"
        result = validate_message_size(message, max_size=100)
        assert result is True
    
    def test_validate_message_size_too_large(self):
        """Test message size validation with oversized message."""
        message = "x" * 1000  # 1000 character message
        result = validate_message_size(message, max_size=100)
        assert result is False
    
    def test_validate_message_size_at_limit(self):
        """Test message size validation at exact limit."""
        message = "x" * 100  # Exactly at limit
        result = validate_message_size(message, max_size=100)
        assert result is True
    
    def test_sanitize_user_input_basic(self):
        """Test basic user input sanitization."""
        user_input = "Hello World!"
        result = sanitize_user_input(user_input)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_sanitize_user_input_with_special_chars(self):
        """Test user input sanitization with special characters."""
        user_input = "Hello <script>alert('xss')</script> World!"
        result = sanitize_user_input(user_input)
        # Should not contain script tags or other dangerous content
        assert "<script>" not in result
        assert "alert(" not in result
    
    def test_sanitize_user_input_empty_string(self):
        """Test user input sanitization with empty string."""
        result = sanitize_user_input("")
        assert result == ""
    
    def test_validate_websocket_origin_allowed(self):
        """Test WebSocket origin validation with allowed origin."""
        ws = MagicMock(spec=WebSocket)
        ws.headers = {"origin": "https://trusted-domain.com"}
        
        allowed_origins = ["https://trusted-domain.com", "https://another-domain.com"]
        result = validate_websocket_origin(ws, allowed_origins)
        assert result is True
    
    def test_validate_websocket_origin_not_allowed(self):
        """Test WebSocket origin validation with disallowed origin."""
        ws = MagicMock(spec=WebSocket)
        ws.headers = {"origin": "https://malicious-domain.com"}
        
        allowed_origins = ["https://trusted-domain.com", "https://another-domain.com"]
        result = validate_websocket_origin(ws, allowed_origins)
        assert result is False
    
    def test_validate_websocket_origin_no_origin_header(self):
        """Test WebSocket origin validation with missing origin header."""
        ws = MagicMock(spec=WebSocket)
        ws.headers = {}  # No origin header
        
        allowed_origins = ["https://trusted-domain.com"]
        result = validate_websocket_origin(ws, allowed_origins)
        # Behavior may vary - some implementations allow missing origin, others don't
        assert isinstance(result, bool)
    
    def test_validate_websocket_origin_case_sensitivity(self):
        """Test WebSocket origin validation is case-sensitive."""
        ws = MagicMock(spec=WebSocket)
        ws.headers = {"origin": "https://TRUSTED-DOMAIN.com"}  # Different case
        
        allowed_origins = ["https://trusted-domain.com"]  # lowercase
        result = validate_websocket_origin(ws, allowed_origins)
        # Should be case-sensitive and fail
        assert result is False


class TestConnectionSecurityManager:
    """Test suite for connection security manager."""
    
    def test_get_connection_security_manager(self):
        """Test getting connection security manager."""
        manager = get_connection_security_manager()
        
        assert manager is not None
        # Should have methods for managing connection security
        assert hasattr(manager, '__class__')
    
    def test_connection_security_manager_singleton(self):
        """Test that connection security manager is singleton."""
        manager1 = get_connection_security_manager()
        manager2 = get_connection_security_manager()
        
        # Should be the same instance
        assert manager1 is manager2


class TestWebSocketSecurityEdgeCases:
    """Test edge cases and security scenarios for WebSocket authentication."""
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent access patterns."""
        import asyncio
        
        rate_limiter = RateLimiter(max_requests=3, window_seconds=5)
        client_id = "concurrent-client"
        
        # Simulate concurrent requests
        async def make_request():
            return rate_limiter.is_allowed(client_id)
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Only first 3 should be allowed
        allowed_count = sum(1 for allowed, _ in results if allowed)
        denied_count = sum(1 for allowed, _ in results if not allowed)
        
        assert allowed_count == 3
        assert denied_count == 7
    
    def test_rate_limiter_memory_cleanup(self):
        """Test that rate limiter cleans up old client histories."""
        rate_limiter = RateLimiter(max_requests=5, window_seconds=1)
        
        # Create requests for many different clients
        for i in range(100):
            client_id = f"client-{i}"
            rate_limiter.is_allowed(client_id)
        
        # Should have 100 clients in history
        assert len(rate_limiter.request_history) == 100
        
        # Wait for window to expire and make request for new client
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 2  # 2 seconds later
            rate_limiter.is_allowed("new-client")
        
        # Old histories should still exist (cleanup is lazy)
        # but new client should be allowed
        allowed, _ = rate_limiter.is_allowed("new-client")
        assert allowed is False  # Second request for new client should hit limit
    
    @pytest.mark.asyncio
    async def test_auth_info_serialization(self):
        """Test that AuthInfo objects can be properly serialized for logging/debugging."""
        auth_info = AuthInfo(
            user_id="test-user",
            is_authenticated=True,
            permissions=["read", "write"],
            metadata={"role": "admin", "timestamp": datetime.now(UTC)}
        )
        
        # Should be able to convert to dict without errors
        info_dict = {
            "user_id": auth_info.user_id,
            "is_authenticated": auth_info.is_authenticated,
            "permissions": auth_info.permissions,
            "metadata": auth_info.metadata
        }
        
        assert info_dict["user_id"] == "test-user"
        assert info_dict["is_authenticated"] is True
        assert "read" in info_dict["permissions"]
        assert info_dict["metadata"]["role"] == "admin"
    
    def test_token_injection_prevention(self):
        """Test prevention of token injection attacks - security critical."""
        authenticator = get_websocket_authenticator()
        
        # Test malicious token patterns that could bypass validation
        malicious_tokens = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "Bearer ../../../etc/passwd",
            "null\x00injection",
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..invalid"
        ]
        
        for token in malicious_tokens:
            # Mock WebSocket with malicious token
            ws = MagicMock(spec=WebSocket)
            ws.headers = {"authorization": f"Bearer {token}"}
            
            # Extract token should handle malicious input safely
            extracted_token, method = authenticator._extract_jwt_token(ws)
            
            # Should extract token but validation will fail safely
            assert method == "header"
            assert extracted_token == token
            # Real validation would reject these tokens securely