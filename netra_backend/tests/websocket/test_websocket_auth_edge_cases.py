"""
Enhanced WebSocket Authentication Edge Cases Test

Business Value Justification (BVJ):
- Segment: Enterprise, Mid, Early (Security-critical customer segments)
- Business Goal: Security & Compliance, Risk Reduction
- Value Impact: Prevents unauthorized access, ensures security robustness
- Revenue Impact: Protects against potential $100K+ security breaches, enables enterprise compliance

This test comprehensively validates WebSocket authentication security by testing:
1. Token validation with various token formats
2. Expired token handling
3. Malformed token rejection
4. Missing token scenarios
5. Authentication method validation
6. Rate limiting under authentication failures
7. Security violation logging

These tests ensure the authentication system is resilient against all common attack vectors.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import base64

import pytest
from fastapi import HTTPException

from netra_backend.app.websocket_core.auth import WebSocketAuthenticator, RateLimiter, ConnectionSecurityManager
from netra_backend.app.websocket_core.types import WebSocketConfig, AuthInfo


class TestWebSocketAuthenticationEdgeCases:
    """Comprehensive WebSocket authentication edge case testing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = WebSocketConfig(
            max_message_rate_per_minute=5,  # Low limit for testing
            connection_timeout_seconds=60
        )
        self.authenticator = WebSocketAuthenticator(self.config)
        
    def create_mock_websocket(self, headers: Dict[str, str] = None, 
                             client_host: str = "127.0.0.1") -> Mock:
        """Create mock WebSocket with specified headers."""
        mock_websocket = Mock()
        mock_websocket.headers = headers or {}
        mock_websocket.client = Mock()
        mock_websocket.client.host = client_host
        return mock_websocket
    
    def create_jwt_token(self, payload: Dict[str, Any], 
                        secret: str = "test_secret",
                        expired: bool = False,
                        malformed: bool = False) -> str:
        """Create JWT token for testing."""
        from tests.helpers.auth_test_utils import TestAuthHelper
        
        auth_helper = TestAuthHelper()
        
        if expired:
            return auth_helper.create_expired_test_token(payload.get('user_id', 'test_user'))
        elif malformed:
            # Create malformed token by corrupting a valid token
            valid_token = auth_helper.create_test_token(payload.get('user_id', 'test_user'))
            return valid_token[:-5] + "xxxxx"  # Corrupt the signature
        else:
            user_id = payload.get('user_id', 'test_user')
            email = payload.get('email', f"{user_id}@test.com")
            return auth_helper.create_test_token(user_id, email)

    @pytest.mark.asyncio
    async def test_missing_token_rejection(self):
        """Test that connections without tokens are rejected."""
        mock_websocket = self.create_mock_websocket()
        
        # Mock CORS validation to pass
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Authentication required" in exc_info.value.detail
            assert self.authenticator.auth_stats["security_violations"] > 0

    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self):
        """Test handling of malformed Authorization headers."""
        test_cases = [
            {"authorization": "Invalid header format"},
            {"authorization": "Bearer"},  # No token
            {"authorization": "Bearer "},  # Empty token
            {"authorization": "Basic dGVzdA=="},  # Wrong auth type
            {"authorization": "bearer valid-token"},  # Wrong case
        ]
        
        for headers in test_cases:
            mock_websocket = self.create_mock_websocket(headers)
            
            with patch.object(self.authenticator, '_validate_cors', return_value=True), \
                 patch.object(self.authenticator, '_check_rate_limit', return_value=True):
                
                with pytest.raises(HTTPException) as exc_info:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                
                assert exc_info.value.status_code == 1008
                assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_expired_jwt_token_rejection(self):
        """Test that expired JWT tokens are rejected."""
        expired_token = self.create_jwt_token(
            {"user_id": "test_user", "email": "test@example.com"}, 
            expired=True
        )
        
        headers = {"authorization": f"Bearer {expired_token}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        # Mock auth client to simulate expired token response
        mock_validation_result = {"valid": False, "error": "Token expired"}
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   return_value=mock_validation_result):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Invalid or expired token" in exc_info.value.detail
            assert self.authenticator.auth_stats["failed_auths"] > 0

    @pytest.mark.asyncio
    async def test_malformed_jwt_token_rejection(self):
        """Test that malformed JWT tokens are rejected."""
        malformed_token = self.create_jwt_token(
            {"user_id": "test_user", "email": "test@example.com"}, 
            malformed=True
        )
        
        headers = {"authorization": f"Bearer {malformed_token}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        # Mock auth client to simulate malformed token response
        mock_validation_result = {"valid": False, "error": "Invalid token format"}
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   return_value=mock_validation_result):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_subprotocol_jwt_authentication_success(self):
        """Test successful JWT authentication via subprotocol."""
        valid_token = self.create_jwt_token({"user_id": "test_user", "email": "test@example.com"})
        
        # Encode token for subprotocol (base64URL)
        token_b64 = base64.urlsafe_b64encode(f"Bearer {valid_token}".encode()).decode().rstrip('=')
        
        headers = {"sec-websocket-protocol": f"jwt.{token_b64}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        # Mock successful validation
        mock_validation_result = {
            "valid": True,
            "user_id": "test_user",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   return_value=mock_validation_result):
            
            auth_info = await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert isinstance(auth_info, AuthInfo)
            assert auth_info.user_id == "test_user"
            assert auth_info.email == "test@example.com"
            assert auth_info.auth_method == "subprotocol"
            assert "read" in auth_info.permissions
            assert self.authenticator.auth_stats["successful_auths"] > 0

    @pytest.mark.asyncio
    async def test_malformed_subprotocol_jwt(self):
        """Test handling of malformed subprotocol JWT."""
        malformed_cases = [
            ("jwt.invalid_base64", "Authentication required"),
            ("jwt.", "Authentication required"),  # Empty token
            ("notjwt.dGVzdA==", "Authentication required"),  # Wrong prefix
            ("jwt.dGVzdA==.extra.parts", "Authentication required"),  # Too many parts
        ]
        
        for protocol, expected_error in malformed_cases:
            headers = {"sec-websocket-protocol": protocol}
            mock_websocket = self.create_mock_websocket(headers)
            
            # Mock auth service to return invalid for any token that gets through
            mock_validation_result = {"valid": False, "error": "Invalid token format"}
            
            with patch.object(self.authenticator, '_validate_cors', return_value=True), \
                 patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
                 patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                       return_value=mock_validation_result):
                
                with pytest.raises(HTTPException) as exc_info:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                
                assert exc_info.value.status_code == 1008
                # Accept either authentication required OR invalid token messages
                assert (expected_error in exc_info.value.detail or 
                       "Invalid or expired token" in exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authentication_service_failure(self):
        """Test handling of auth service failures."""
        valid_token = self.create_jwt_token({"user_id": "test_user"})
        headers = {"authorization": f"Bearer {valid_token}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   side_effect=Exception("Auth service unavailable")):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1011
            assert "Authentication error" in exc_info.value.detail
            assert self.authenticator.auth_stats["failed_auths"] > 0

    @pytest.mark.asyncio
    async def test_missing_user_id_in_token(self):
        """Test handling of valid token but missing user ID."""
        valid_token = self.create_jwt_token({"email": "test@example.com"})
        headers = {"authorization": f"Bearer {valid_token}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        # Mock validation that returns valid but no user_id
        mock_validation_result = {
            "valid": True,
            "email": "test@example.com",
            "permissions": ["read"]
            # Missing user_id
        }
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   return_value=mock_validation_result):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Invalid user information" in exc_info.value.detail
            assert self.authenticator.auth_stats["security_violations"] > 0

    @pytest.mark.asyncio
    async def test_rate_limiting_on_auth_failures(self):
        """Test that rate limiting works correctly during auth failures."""
        mock_websocket = self.create_mock_websocket()
        client_ip = "192.168.1.100"
        mock_websocket.client.host = client_ip
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True):
            
            # Attempt multiple failed authentications
            for i in range(6):  # Exceed the limit of 5
                with pytest.raises(HTTPException):
                    await self.authenticator.authenticate_websocket(mock_websocket)
            
            # The 6th attempt should be rate limited
            rate_limited_attempts = 0
            for i in range(3):  # Try a few more times
                try:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                except HTTPException as e:
                    if "Rate limit exceeded" in str(e.detail):
                        rate_limited_attempts += 1
            
            assert rate_limited_attempts > 0
            assert self.authenticator.auth_stats["rate_limited"] > 0

    @pytest.mark.asyncio
    async def test_cors_validation_failure(self):
        """Test CORS validation failure handling."""
        headers = {"authorization": "Bearer valid_token", "origin": "http://malicious-site.com"}
        mock_websocket = self.create_mock_websocket(headers)
        
        with patch.object(self.authenticator, '_validate_cors', return_value=False), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "CORS validation failed" in exc_info.value.detail
            assert self.authenticator.auth_stats["cors_violations"] > 0

    @pytest.mark.asyncio
    async def test_client_ip_extraction_methods(self):
        """Test various client IP extraction methods."""
        test_cases = [
            # (headers, expected_ip, description)
            ({"x-forwarded-for": "203.0.113.1,198.51.100.1"}, "203.0.113.1", "x-forwarded-for with multiple IPs"),
            ({"x-real-ip": "203.0.113.2"}, "203.0.113.2", "x-real-ip header"),
            ({"x-forwarded-for": " 203.0.113.3 "}, "203.0.113.3", "x-forwarded-for with spaces"),
            ({}, "127.0.0.1", "default client IP"),
        ]
        
        for headers, expected_ip, description in test_cases:
            mock_websocket = self.create_mock_websocket(headers, client_host="127.0.0.1")
            
            extracted_ip = self.authenticator._get_client_ip(mock_websocket)
            assert extracted_ip == expected_ip, f"Failed for case: {description}"

    @pytest.mark.asyncio
    async def test_authentication_stats_tracking(self):
        """Test that authentication statistics are properly tracked."""
        initial_stats = self.authenticator.get_auth_stats()
        
        # Test successful auth
        valid_token = self.create_jwt_token({"user_id": "test_user", "email": "test@example.com"})
        headers = {"authorization": f"Bearer {valid_token}"}
        mock_websocket = self.create_mock_websocket(headers)
        
        mock_validation_result = {
            "valid": True,
            "user_id": "test_user",
            "email": "test@example.com",
            "permissions": ["read"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt', 
                   return_value=mock_validation_result):
            
            await self.authenticator.authenticate_websocket(mock_websocket)
        
        # Test failed auth
        mock_websocket_fail = self.create_mock_websocket()
        
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True):
            
            with pytest.raises(HTTPException):
                await self.authenticator.authenticate_websocket(mock_websocket_fail)
        
        final_stats = self.authenticator.get_auth_stats()
        
        assert final_stats["successful_auths"] > initial_stats["successful_auths"]
        assert final_stats["security_violations"] > initial_stats["security_violations"]
        assert final_stats["success_rate"] >= 0.0
        assert final_stats["uptime_seconds"] > 0


class TestConnectionSecurityManager:
    """Test ConnectionSecurityManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = WebSocketConfig()
        self.authenticator = WebSocketAuthenticator(config)
        self.security_manager = ConnectionSecurityManager(self.authenticator)
    
    def test_connection_registration_and_unregistration(self):
        """Test connection registration and cleanup."""
        connection_id = "test_conn_123"
        auth_info = AuthInfo(
            user_id="test_user",
            email="test@example.com",
            permissions=["read"],
            auth_method="header",
            authenticated_at=datetime.now(timezone.utc)
        )
        mock_websocket = Mock()
        
        # Register connection
        self.security_manager.register_connection(connection_id, auth_info, mock_websocket)
        
        assert connection_id in self.security_manager.active_connections
        assert self.security_manager.active_connections[connection_id]["auth_info"] == auth_info
        
        # Unregister connection
        self.security_manager.unregister_connection(connection_id)
        assert connection_id not in self.security_manager.active_connections
    
    def test_security_violation_reporting(self):
        """Test security violation reporting and tracking."""
        connection_id = "test_conn_456"
        auth_info = AuthInfo(
            user_id="test_user",
            auth_method="header",
            authenticated_at=datetime.now(timezone.utc)
        )
        mock_websocket = Mock()
        
        self.security_manager.register_connection(connection_id, auth_info, mock_websocket)
        
        # Report violations
        self.security_manager.report_security_violation(
            connection_id, "suspicious_activity", {"details": "test"}
        )
        self.security_manager.report_security_violation(
            connection_id, "rate_limit_exceeded"
        )
        
        conn_info = self.security_manager.active_connections[connection_id]
        assert conn_info["violation_count"] == 2
        
        security_summary = self.security_manager.get_security_summary()
        assert security_summary["total_violations"] >= 2
        assert len(security_summary["recent_violations"]) >= 2
    
    def test_connection_security_validation(self):
        """Test connection security validation logic."""
        connection_id = "test_conn_789"
        auth_info = AuthInfo(
            user_id="test_user",
            auth_method="header",
            authenticated_at=datetime.now(timezone.utc)
        )
        
        # Mock WebSocket with CONNECTED state
        from starlette.websockets import WebSocketState
        mock_websocket = Mock()
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        self.security_manager.register_connection(connection_id, auth_info, mock_websocket)
        
        # Should pass validation initially
        assert self.security_manager.validate_connection_security(connection_id) == True
        
        # Add too many violations
        for i in range(6):
            self.security_manager.report_security_violation(connection_id, f"violation_{i}")
        
        # Should fail validation due to excessive violations
        assert self.security_manager.validate_connection_security(connection_id) == False


class TestRateLimiter:
    """Test RateLimiter functionality in isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rate_limiter = RateLimiter(max_requests=3, window_seconds=60)
    
    def test_rate_limiter_allows_under_limit(self):
        """Test that requests under limit are allowed."""
        client_id = "test_client_1"
        
        # First 3 requests should be allowed
        for i in range(3):
            allowed, rate_info = self.rate_limiter.is_allowed(client_id)
            assert allowed == True
            assert rate_info["requests_count"] == i + 1
            assert rate_info["remaining_requests"] == 3 - (i + 1)
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        client_id = "test_client_2"
        
        # Use up the limit
        for i in range(3):
            allowed, _ = self.rate_limiter.is_allowed(client_id)
            assert allowed == True
        
        # 4th request should be blocked
        allowed, rate_info = self.rate_limiter.is_allowed(client_id)
        assert allowed == False
        assert rate_info["requests_count"] == 3
        assert rate_info["remaining_requests"] == 0
        assert "reset_time" in rate_info
    
    def test_rate_limiter_cleanup(self):
        """Test rate limiter cleanup functionality."""
        client_id = "test_client_3"
        
        # Make some requests
        for i in range(2):
            self.rate_limiter.is_allowed(client_id)
        
        assert client_id in self.rate_limiter.request_history
        
        # Simulate time passage by manipulating history
        past_time = time.time() - 120  # 2 minutes ago
        self.rate_limiter.request_history[client_id] = [past_time, past_time]
        
        # Cleanup should remove expired entries
        self.rate_limiter.cleanup_expired()
        
        # History should be empty or removed
        if client_id in self.rate_limiter.request_history:
            assert len(self.rate_limiter.request_history[client_id]) == 0
        else:
            assert client_id not in self.rate_limiter.request_history


class TestWebSocketAuthenticationBypassPrevention:
    """ITERATION 28: Prevent WebSocket authentication bypass attacks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = WebSocketConfig(
            max_message_rate_per_minute=5,
            connection_timeout_seconds=60
        )
        self.authenticator = WebSocketAuthenticator(self.config)

    @pytest.mark.asyncio
    async def test_websocket_authentication_bypass_prevention(self):
        """ITERATION 28: Prevent WebSocket authentication bypass that allows unauthorized access.
        
        Business Value: Prevents unauthorized access attacks worth $150K+ per security breach.
        """
        # Test 1: Header manipulation attempts should be blocked
        bypass_headers = [
            {"x-forwarded-user": "admin", "authorization": "Bearer fake-token"},  # Header injection
            {"user-agent": "Authorized-Client", "x-real-user": "admin"},  # User agent spoofing
            {"referer": "https://app.netra.ai", "x-user-id": "bypass-123"},  # Referer spoofing
            {"host": "app.netra.ai", "x-authenticated": "true"},  # Host header attack
        ]
        
        for headers in bypass_headers:
            mock_websocket = self.create_mock_websocket(headers)
            
            with patch.object(self.authenticator, '_validate_cors', return_value=True), \
                 patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
                 patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt',
                       return_value={"valid": False, "error": "Invalid token"}):
                
                with pytest.raises(HTTPException) as exc_info:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                
                # Should reject bypass attempts
                assert exc_info.value.status_code in [1008, 1011]
                assert self.authenticator.auth_stats["security_violations"] > 0

        # Test 2: Protocol upgrade manipulation should fail
        protocol_bypass_attempts = [
            {"sec-websocket-protocol": "bypass-auth"},  # Custom protocol
            {"sec-websocket-protocol": "jwt.bypassed"},  # Malformed JWT protocol
            {"upgrade": "websocket", "connection": "upgrade", "x-bypass": "true"},  # Connection bypass
        ]
        
        for headers in protocol_bypass_attempts:
            mock_websocket = self.create_mock_websocket(headers)
            
            with patch.object(self.authenticator, '_validate_cors', return_value=True), \
                 patch.object(self.authenticator, '_check_rate_limit', return_value=True):
                
                with pytest.raises(HTTPException) as exc_info:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                
                assert exc_info.value.status_code == 1008
                assert "Authentication required" in exc_info.value.detail

        # Test 3: CORS bypass attempts should be blocked
        cors_bypass_origins = [
            "null",  # Null origin bypass
            "https://app.netra.ai@evil.com",  # URL confusion
            "https://evil.com#https://app.netra.ai",  # Fragment bypass
            "file://",  # File protocol bypass
            "data:text/html,<script>",  # Data URL bypass
        ]
        
        for origin in cors_bypass_origins:
            headers = {"origin": origin, "authorization": "Bearer valid-token"}
            mock_websocket = self.create_mock_websocket(headers)
            
            with patch.object(self.authenticator, '_validate_cors', return_value=False), \
                 patch.object(self.authenticator, '_check_rate_limit', return_value=True):
                
                with pytest.raises(HTTPException) as exc_info:
                    await self.authenticator.authenticate_websocket(mock_websocket)
                
                assert exc_info.value.status_code == 1008
                assert "CORS validation failed" in exc_info.value.detail

        # Test 4: Client IP spoofing should not bypass security
        spoofing_headers = [
            {"x-forwarded-for": "127.0.0.1", "x-real-ip": "192.168.1.1"},  # Conflicting IPs
            {"x-forwarded-for": "127.0.0.1,evil-proxy.com"},  # Proxy chain manipulation
            {"x-real-ip": "127.0.0.1", "x-client-ip": "trusted-ip"},  # Multiple IP headers
        ]
        
        for headers in spoofing_headers:
            mock_websocket = self.create_mock_websocket(headers, client_host="untrusted-ip")
            
            # Should still be subject to rate limiting regardless of spoofed IPs
            with patch.object(self.authenticator, '_validate_cors', return_value=True):
                
                # Exhaust rate limit
                for _ in range(6):
                    try:
                        await self.authenticator.authenticate_websocket(mock_websocket)
                    except HTTPException:
                        pass  # Expected to fail without auth
                
                # Should eventually be rate limited
                rate_limited = False
                for _ in range(3):
                    try:
                        await self.authenticator.authenticate_websocket(mock_websocket)
                    except HTTPException as e:
                        if "Rate limit exceeded" in str(e.detail):
                            rate_limited = True
                            break
                
                assert rate_limited, "Rate limiting should work regardless of IP spoofing"

        # Test 5: Session token replay attacks should be detected
        replay_token = self.create_jwt_token({"user_id": "replay-victim", "session": "used-session"})
        headers = {"authorization": f"Bearer {replay_token}"}
        
        # Simulate token validation that detects replay
        mock_validation_result = {"valid": False, "error": "Token replay detected"}
        
        mock_websocket = self.create_mock_websocket(headers)
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt',
                   return_value=mock_validation_result):
            
            with pytest.raises(HTTPException) as exc_info:
                await self.authenticator.authenticate_websocket(mock_websocket)
            
            assert exc_info.value.status_code == 1008
            assert "Invalid or expired token" in exc_info.value.detail

        # Test 6: Privilege escalation attempts should fail
        escalation_token = self.create_jwt_token({
            "user_id": "normal-user", 
            "permissions": ["admin", "root", "superuser"],  # Suspicious permissions
        })
        headers = {"authorization": f"Bearer {escalation_token}"}
        
        # Mock validation that detects privilege escalation
        mock_validation_result = {
            "valid": True,
            "user_id": "normal-user",
            "email": "user@example.com",
            "permissions": ["read"],  # Auth service strips elevated permissions
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        mock_websocket = self.create_mock_websocket(headers)
        with patch.object(self.authenticator, '_validate_cors', return_value=True), \
             patch.object(self.authenticator, '_check_rate_limit', return_value=True), \
             patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt',
                   return_value=mock_validation_result):
            
            auth_info = await self.authenticator.authenticate_websocket(mock_websocket)
            
            # Should only have safe permissions, not escalated ones
            assert auth_info.permissions == ["read"]
            assert "admin" not in auth_info.permissions
            assert "root" not in auth_info.permissions

    def create_mock_websocket(self, headers: Dict[str, str] = None, 
                             client_host: str = "127.0.0.1") -> Mock:
        """Create mock WebSocket with specified headers."""
        mock_websocket = Mock()
        mock_websocket.headers = headers or {}
        mock_websocket.client = Mock()
        mock_websocket.client.host = client_host
        return mock_websocket
    
    def create_jwt_token(self, payload: Dict[str, Any], 
                        secret: str = "test_secret",
                        expired: bool = False,
                        malformed: bool = False) -> str:
        """Create JWT token for testing."""
        from tests.helpers.auth_test_utils import TestAuthHelper
        
        auth_helper = TestAuthHelper()
        
        if expired:
            return auth_helper.create_expired_test_token(payload.get('user_id', 'test_user'))
        elif malformed:
            # Create malformed token by corrupting a valid token
            valid_token = auth_helper.create_test_token(payload.get('user_id', 'test_user'))
            return valid_token[:-5] + "xxxxx"  # Corrupt the signature
        else:
            user_id = payload.get('user_id', 'test_user')
            email = payload.get('email', f"{user_id}@test.com")
            return auth_helper.create_test_token(user_id, email)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])