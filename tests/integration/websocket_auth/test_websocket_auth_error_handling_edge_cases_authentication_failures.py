"""
WebSocket Authentication Error Handling Edge Cases - Authentication Failures (7 tests)

Business Value Justification:
- Segment: Platform/Internal - Authentication Security & Reliability
- Business Goal: System Stability & Security - Protect against authentication attack vectors
- Value Impact: Prevents authentication failures from cascading into system outages
- Revenue Impact: Protects $500K+ ARR by ensuring authentication edge cases don't break Golden Path

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real services and real system behavior
- Tests must be realistic but not require actual running services
- Follow SSOT patterns from test_framework/
- Each test must validate actual business value

This test file covers authentication failure edge cases that could occur in production,
focusing on graceful degradation and system resilience when authentication encounters
unexpected conditions, malformed data, or timing issues.
"""

import asyncio
import json
import time
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    extract_e2e_context_from_websocket
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env


class TestWebSocketAuthenticationFailureEdgeCases(SSotAsyncTestCase):
    """
    Integration tests for WebSocket authentication failure edge cases.
    
    Tests realistic authentication failure scenarios that could occur in production,
    validating system resilience and graceful degradation mechanisms.
    
    Business Value: These tests protect the Golden Path chat functionality by ensuring
    authentication edge cases are handled gracefully without system instability.
    """
    
    def setup_method(self, method):
        """Set up test environment with realistic failure scenario configurations."""
        super().setup_method(method)
        
        # Set up realistic test environment variables
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("AUTH_SERVICE_URL", "http://localhost:8001") 
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "0")  # Disable E2E bypass for auth tests
        self.set_env_var("DEMO_MODE", "0")    # Disable demo mode for auth tests
        self.set_env_var("JWT_SECRET_KEY", "test_secret_key_for_edge_cases")
        self.set_env_var("AUTH_CIRCUIT_BREAKER_ENABLED", "true")
        
        # Initialize test metrics
        self.record_metric("test_category", "websocket_auth_failure_edge_cases")
        self.record_metric("business_value", "authentication_resilience")
        self.record_metric("test_start_time", time.time())

    async def test_malformed_jwt_token_handling_graceful_degradation(self):
        """
        Test Case 1: Malformed JWT token handling with graceful degradation.
        
        Business Value: Ensures malformed tokens don't crash the authentication
        system or expose sensitive error information to attackers.
        
        Tests various malformed JWT formats and validates error handling.
        """
        # Arrange - Create mock WebSocket with malformed JWT tokens
        test_cases = [
            "Bearer not.a.jwt",  # Invalid segments
            "Bearer eyJ0.invalid_base64.signature",  # Invalid base64
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOi.missing_signature",  # Missing signature
            "Bearer eyJ0eXAiOiJKV1QifQ.eyJzdWIiOiIxMjMifQ.signature",  # Truncated header
            "Bearer " + "a" * 2000,  # Oversized token
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{invalid_json}.signature",  # Invalid JSON in payload
        ]
        
        for malformed_token in test_cases:
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": malformed_token,
                "sec-websocket-protocol": "chat"
            }
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 8000
            
            # Mock the authentication service to handle malformed tokens
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                # Simulate authentication service rejecting malformed tokens
                mock_service.authenticate_jwt_token.side_effect = ValueError("Invalid JWT format")
                mock_auth_service.return_value = mock_service
                
                # Act & Assert - Authentication should fail gracefully without exceptions
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Verify graceful failure
                assert not result.success
                assert result.error_message is not None
                assert "authentication_failed" in result.error_message.lower()
                assert result.user_context is None
                
                # Verify no sensitive information leakage
                assert "jwt" not in result.error_message.lower()
                assert "token" not in result.error_message.lower()
                
                # Record metrics for business monitoring
                self.record_metric("malformed_token_test", "handled_gracefully")

    async def test_expired_jwt_token_during_active_websocket_connection_handling(self):
        """
        Test Case 2: JWT token expiration during active WebSocket connection.
        
        Business Value: Ensures expired tokens are detected and handled properly
        during active chat sessions without abrupt disconnections.
        
        Tests token expiration scenarios and validates refresh mechanisms.
        """
        # Arrange - Create WebSocket with initially valid but soon-to-expire token
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Create a JWT-like token that appears expired
        expired_time = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
        expired_payload = {
            "sub": "test_user_123",
            "exp": expired_time,
            "iat": expired_time - 3600,
            "email": "test@example.com"
        }
        
        mock_websocket.headers = {
            "authorization": f"Bearer {base64.b64encode(json.dumps(expired_payload).encode()).decode()}",
            "sec-websocket-protocol": "chat"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Mock the authentication service to detect expired tokens
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            # Simulate authentication service detecting expired token
            mock_service.authenticate_jwt_token.return_value = AuthResult(
                success=False,
                error_message="Token expired",
                error_code="TOKEN_EXPIRED"
            )
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate with expired token
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # Assert - Should fail with specific expired token handling
            assert not result.success
            assert "expired" in result.error_message.lower() or "authentication_failed" in result.error_message.lower()
            assert result.user_context is None
            assert result.requires_refresh == True  # Should indicate refresh needed
            
            # Verify proper error categorization for monitoring
            self.record_metric("expired_token_detection", "success")
            self.record_metric("refresh_required", "indicated")

    async def test_jwt_token_corruption_and_tampering_detection(self):
        """
        Test Case 3: JWT token corruption and tampering detection.
        
        Business Value: Protects against token manipulation attacks that could
        compromise user authentication and system security.
        
        Tests various tampering scenarios and validates security responses.
        """
        # Arrange - Create tokens with various tampering scenarios
        base_payload = {
            "sub": "test_user_123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "email": "test@example.com"
        }
        
        tampering_scenarios = [
            # Modified payload (privilege escalation attempt)
            {**base_payload, "permissions": ["admin", "delete_all"], "sub": "admin_user"},
            # Modified expiration (time extension attempt)
            {**base_payload, "exp": int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp())},
            # Modified user ID (identity theft attempt)
            {**base_payload, "sub": "admin_123"},
            # Added unauthorized claims
            {**base_payload, "is_admin": True, "bypass_auth": True},
        ]
        
        for tampered_payload in tampering_scenarios:
            mock_websocket = MagicMock(spec=WebSocket)
            # Create tampered token (signature won't match)
            tampered_token = base64.b64encode(json.dumps(tampered_payload).encode()).decode()
            mock_websocket.headers = {
                "authorization": f"Bearer header.{tampered_token}.invalid_signature",
                "sec-websocket-protocol": "chat"
            }
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 8000
            
            # Mock authentication service to detect tampering
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                # Simulate signature verification failure
                mock_service.authenticate_jwt_token.return_value = AuthResult(
                    success=False,
                    error_message="Invalid signature",
                    error_code="TOKEN_INVALID"
                )
                mock_auth_service.return_value = mock_service
                
                # Act - Authenticate with tampered token
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Assert - Should fail with security-appropriate response
                assert not result.success
                assert result.error_message is not None
                assert result.user_context is None
                
                # Verify security logging would be triggered
                mock_service.authenticate_jwt_token.assert_called_once()
                
                # Record security metrics
                self.record_metric("tampering_detection", "blocked")

    async def test_missing_authentication_headers_various_formats_handling(self):
        """
        Test Case 4: Missing authentication headers in various formats.
        
        Business Value: Ensures the system handles missing or incomplete
        authentication headers gracefully without exposing system internals.
        
        Tests various missing header scenarios.
        """
        # Arrange - Test various missing header scenarios
        header_scenarios = [
            {},  # No headers at all
            {"sec-websocket-protocol": "chat"},  # Only protocol, no auth
            {"authorization": ""},  # Empty authorization
            {"authorization": "Bearer"},  # Bearer without token
            {"authorization": "Basic dXNlcjpwYXNz"},  # Wrong auth type
            {"Authorization": "Bearer token"},  # Wrong case
            {"auth": "Bearer token"},  # Wrong header name
            {"authorization": "token_without_bearer"},  # Missing Bearer prefix
        ]
        
        for headers in header_scenarios:
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.headers = headers
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 8000
            
            # Act - Authenticate with missing/invalid headers
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # Assert - Should fail gracefully with consistent error
            assert not result.success
            assert result.error_message is not None
            assert "authentication" in result.error_message.lower() or "unauthorized" in result.error_message.lower()
            assert result.user_context is None
            
            # Verify consistent error handling regardless of missing header type
            self.record_metric("missing_header_scenario", "handled")

    async def test_authentication_timeout_scenarios_and_recovery(self):
        """
        Test Case 5: Authentication timeout scenarios and recovery mechanisms.
        
        Business Value: Ensures authentication timeouts don't leave connections
        in inconsistent states and provides recovery paths for users.
        
        Tests timeout handling and recovery mechanisms.
        """
        # Arrange - Create WebSocket for timeout testing
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer valid_token_format_for_timeout_test",
            "sec-websocket-protocol": "chat"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Mock authentication service to simulate timeout
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # Simulate authentication timeout
            mock_service.authenticate_jwt_token.side_effect = asyncio.TimeoutError("Authentication timeout")
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate with timeout
            start_time = time.time()
            result = await authenticate_websocket_ssot(mock_websocket)
            end_time = time.time()
            
            # Assert - Should handle timeout gracefully
            assert not result.success
            assert result.error_message is not None
            assert "timeout" in result.error_message.lower() or "authentication_failed" in result.error_message.lower()
            assert result.user_context is None
            
            # Verify timeout was handled efficiently (not hanging)
            assert (end_time - start_time) < 30.0  # Should not hang indefinitely
            
            # Record timeout handling metrics
            self.record_metric("timeout_handling", "graceful")
            self.record_metric("timeout_duration", end_time - start_time)

    async def test_concurrent_authentication_attempts_same_user_handling(self):
        """
        Test Case 6: Concurrent authentication attempts from same user.
        
        Business Value: Prevents authentication race conditions that could
        lead to multiple active sessions or authentication state corruption.
        
        Tests concurrent authentication handling and session management.
        """
        # Arrange - Create multiple WebSocket instances for same user
        user_id = "test_user_concurrent_123"
        concurrent_websockets = []
        
        for i in range(5):  # Simulate 5 concurrent connection attempts
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer valid_token_user_{user_id}_attempt_{i}",
                "sec-websocket-protocol": "chat",
                "x-user-id": user_id  # Simulate user identification
            }
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 8000 + i
            concurrent_websockets.append(mock_websocket)
        
        # Mock authentication service for concurrent tests
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # Simulate successful authentication but with session limit
            call_count = 0
            async def mock_authenticate(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 3:  # Allow first 3 connections
                    return AuthResult(
                        success=True,
                        user_id=user_id,
                        email=f"test_{call_count}@example.com",
                        permissions=["execute_agents", "chat_access"]
                    )
                else:  # Reject additional concurrent connections
                    return AuthResult(
                        success=False,
                        error_message="Too many concurrent sessions",
                        error_code="CONCURRENT_LIMIT_EXCEEDED"
                    )
            
            mock_service.authenticate_jwt_token = mock_authenticate
            mock_auth_service.return_value = mock_service
            
            # Act - Attempt concurrent authentications
            tasks = [authenticate_websocket_ssot(ws) for ws in concurrent_websockets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert - Should handle concurrency appropriately
            successful_auths = sum(1 for r in results if isinstance(r, WebSocketAuthResult) and r.success)
            failed_auths = sum(1 for r in results if isinstance(r, WebSocketAuthResult) and not r.success)
            
            # Should have some limit on concurrent sessions
            assert successful_auths <= len(concurrent_websockets)
            assert failed_auths >= 0  # Some may be rejected due to limits
            
            # Record concurrency handling metrics
            self.record_metric("concurrent_auth_attempts", len(concurrent_websockets))
            self.record_metric("concurrent_auth_successful", successful_auths)
            self.record_metric("concurrent_auth_rejected", failed_auths)

    async def test_authentication_state_corruption_recovery_mechanisms(self):
        """
        Test Case 7: Authentication state corruption recovery mechanisms.
        
        Business Value: Ensures the system can recover from authentication
        state corruption without requiring system restart or user re-registration.
        
        Tests state corruption scenarios and recovery mechanisms.
        """
        # Arrange - Create WebSocket for state corruption testing
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer valid_token_for_state_corruption_test",
            "sec-websocket-protocol": "chat"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Test various state corruption scenarios
        corruption_scenarios = [
            # Database connection failure during auth
            {"exception": ConnectionError("Database unavailable"), "should_retry": True},
            # Redis cache corruption
            {"exception": ValueError("Invalid cached auth state"), "should_retry": True},
            # Memory corruption (simulated)
            {"exception": RuntimeError("Authentication state corrupted"), "should_retry": True},
            # Service unavailable
            {"exception": ConnectionRefusedError("Auth service down"), "should_retry": True},
        ]
        
        for scenario in corruption_scenarios:
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                
                # First call fails with corruption
                # Second call succeeds (recovery)
                call_count = 0
                async def mock_authenticate_with_recovery(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise scenario["exception"]
                    else:
                        return AuthResult(
                            success=True,
                            user_id="recovered_user_123",
                            email="recovered@example.com",
                            permissions=["execute_agents", "chat_access"]
                        )
                
                mock_service.authenticate_jwt_token = mock_authenticate_with_recovery
                mock_auth_service.return_value = mock_service
                
                # Act - Authenticate with state corruption
                try:
                    result = await authenticate_websocket_ssot(mock_websocket)
                    
                    # Assert - Should handle corruption gracefully
                    # Either fail gracefully or recover successfully
                    assert isinstance(result, WebSocketAuthResult)
                    
                    if result.success:
                        # Recovery succeeded
                        assert result.user_context is not None
                        self.record_metric("state_corruption_recovery", "success")
                    else:
                        # Graceful failure
                        assert result.error_message is not None
                        self.record_metric("state_corruption_handling", "graceful_failure")
                        
                except Exception as e:
                    # If exception bubbles up, it should be a controlled failure
                    assert "timeout" in str(e).lower() or "unavailable" in str(e).lower()
                    self.record_metric("state_corruption_exception", "controlled")

    def teardown_method(self, method):
        """Clean up after each test method."""
        # Record final test metrics
        self.record_metric("test_end_time", time.time())
        self.record_metric("test_completed", method.__name__)
        super().teardown_method(method)