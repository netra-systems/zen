"""
Comprehensive WebSocket Authentication Serialization Tests

This test suite validates that all WebSocket authentication response paths
use safe JSON serialization and handle WebSocketState enums correctly.

CRITICAL: Tests the fix for "Object of type WebSocketState is not JSON serializable"
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    get_websocket_authenticator
)
from netra_backend.app.services.unified_authentication_service import AuthResult
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketAuthSerializationFix:
    """Test that WebSocket authentication responses use safe serialization."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket with state information."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        websocket.headers = {"authorization": "Bearer test-token"}
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 8000
        return websocket
    
    @pytest.fixture
    def auth_failure_result(self):
        """Create WebSocket authentication failure result."""
        return WebSocketAuthResult(
            success=False,
            error_message="Token validation failed",
            error_code="WEBSOCKET_AUTH_EXCEPTION"
        )
    
    @pytest.fixture
    def auth_success_result(self):
        """Create WebSocket authentication success result."""
        user_context = UserExecutionContext(
            user_id="usr_a1b2c3d4e5f6",
            websocket_client_id="wsc_9876543210ab",
            thread_id="thr_fedcba0987654321",
            run_id="run_135791113171921"
        )
        
        auth_result = AuthResult(
            success=True,
            user_id="usr_a1b2c3d4e5f6",
            email="user@auth.test",
            permissions=["read", "write"]
        )
        
        return WebSocketAuthResult(
            success=True,
            user_context=user_context,
            auth_result=auth_result
        )

    @pytest.fixture
    def authenticator(self):
        """Create WebSocket authenticator instance."""
        return UnifiedWebSocketAuthenticator()
    
    async def test_auth_error_response_serializes_websocket_state_safely(self, authenticator, mock_websocket, auth_failure_result):
        """
        CRITICAL TEST: Verify authentication error responses handle WebSocketState enums.
        
        This test directly addresses the root cause:
        "Object of type WebSocketState is not JSON serializable"
        """
        # Add WebSocketState to the auth result to simulate real-world scenario
        auth_failure_result.error_message = f"Auth failed with connection state: {mock_websocket.client_state}"
        
        # Call the method that previously failed
        await authenticator.create_auth_error_response(mock_websocket, auth_failure_result)
        
        # Verify send_json was called
        mock_websocket.send_json.assert_called_once()
        
        # Get the message that was sent
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL ASSERTION: Message must be JSON serializable
        json_string = json.dumps(sent_message)
        assert json_string is not None
        
        # Verify message structure
        assert sent_message["type"] == "authentication_error"
        assert sent_message["event"] == "auth_failed"
        assert sent_message["error_code"] == "WEBSOCKET_AUTH_EXCEPTION"
        assert sent_message["ssot_authenticated"] is False
        assert "timestamp" in sent_message
        assert isinstance(sent_message["timestamp"], str)
    
    async def test_auth_success_response_serializes_websocket_state_safely(self, authenticator, mock_websocket, auth_success_result):
        """
        CRITICAL TEST: Verify authentication success responses handle WebSocketState enums.
        """
        # Call the method that could contain WebSocketState enums
        await authenticator.create_auth_success_response(mock_websocket, auth_success_result)
        
        # Verify send_json was called
        mock_websocket.send_json.assert_called_once()
        
        # Get the message that was sent
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL ASSERTION: Message must be JSON serializable
        json_string = json.dumps(sent_message)
        assert json_string is not None
        
        # Verify message structure
        assert sent_message["type"] == "authentication_success"
        assert sent_message["event"] == "auth_success"
        assert sent_message["user_id"] == "usr_a1b2c3d4e5f6"
        assert sent_message["websocket_client_id"] == "wsc_9876543210ab"
        assert sent_message["permissions"] == ["read", "write"]
        assert sent_message["ssot_authenticated"] is True
        assert "timestamp" in sent_message
        assert isinstance(sent_message["timestamp"], str)
    
    async def test_auth_error_with_complex_enum_data(self, authenticator, mock_websocket):
        """Test authentication error with complex data including multiple enums."""
        # Create auth result with complex metadata that might include enums
        auth_failure_result = WebSocketAuthResult(
            success=False,
            error_message="Complex auth failure",
            error_code="WEBSOCKET_AUTH_EXCEPTION"
        )
        
        # Ensure WebSocket is detected as connected for this test
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        await authenticator.create_auth_error_response(mock_websocket, auth_failure_result)
        
        # Verify the response was sent and is JSON serializable
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL: Must not raise JSON serialization error
        json.dumps(sent_message)
        
        # Verify error response structure
        assert sent_message["type"] == "authentication_error"
        assert sent_message["error_code"] == "WEBSOCKET_AUTH_EXCEPTION"
    
    async def test_handle_authentication_failure_full_flow(self, authenticator, mock_websocket, auth_failure_result):
        """Test the complete authentication failure handling flow."""
        # Mock the close method
        mock_websocket.close = AsyncMock()
        
        # Handle authentication failure (this calls create_auth_error_response internally)
        await authenticator.handle_authentication_failure(mock_websocket, auth_failure_result, close_connection=True)
        
        # Verify error response was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL: Response must be JSON serializable
        json.dumps(sent_message)
        
        # Verify connection was closed after error response
        mock_websocket.close.assert_called_once()
        
        # Verify close code is appropriate for auth failure
        close_args = mock_websocket.close.call_args
        assert close_args[1]["code"] == 1008  # Policy violation
    
    async def test_websocket_state_enum_in_error_metadata(self, authenticator, mock_websocket):
        """Test that WebSocketState enums in error metadata are handled safely."""
        # Create a failure result that might contain WebSocket state information
        auth_failure_result = WebSocketAuthResult(
            success=False,
            error_message="Connection state error",
            error_code="INVALID_WEBSOCKET_STATE"
        )
        
        # Simulate the websocket having state information that could leak into responses
        # But keep it CONNECTED so the message is actually sent for testing
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        await authenticator.create_auth_error_response(mock_websocket, auth_failure_result)
        
        # Verify the message was safely serialized
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL: Must not contain raw enum objects
        json_string = json.dumps(sent_message)
        
        # Verify no enum objects leaked into the response
        assert "WebSocketState" not in json_string
        assert sent_message["error_code"] == "INVALID_WEBSOCKET_STATE"
    
    async def test_concurrent_auth_responses_serialization_safety(self, authenticator, mock_websocket, auth_failure_result, auth_success_result):
        """Test that concurrent authentication responses don't cause serialization issues."""
        # Create multiple WebSocket mocks with different states
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket1.client_state = WebSocketState.CONNECTED
        
        websocket2 = Mock()
        websocket2.send_json = AsyncMock()
        websocket2.client_state = WebSocketState.CONNECTING
        
        websocket3 = Mock()
        websocket3.send_json = AsyncMock()
        websocket3.client_state = WebSocketState.DISCONNECTED
        
        # Send concurrent authentication responses
        tasks = [
            authenticator.create_auth_error_response(websocket1, auth_failure_result),
            authenticator.create_auth_success_response(websocket2, auth_success_result),
            authenticator.create_auth_error_response(websocket3, auth_failure_result)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all responses were sent and are JSON serializable
        for ws in [websocket1, websocket2, websocket3]:
            ws.send_json.assert_called_once()
            sent_message = ws.send_json.call_args[0][0]
            # CRITICAL: All concurrent responses must be JSON serializable
            json.dumps(sent_message)
    
    async def test_auth_response_with_disconnected_websocket(self, authenticator, auth_failure_result):
        """Test authentication response handling when WebSocket is disconnected."""
        # Create WebSocket that appears disconnected
        disconnected_websocket = Mock()
        disconnected_websocket.send_json = AsyncMock()
        disconnected_websocket.client_state = WebSocketState.DISCONNECTED
        disconnected_websocket.application_state = WebSocketState.DISCONNECTED
        
        # Should not attempt to send to disconnected WebSocket
        await authenticator.create_auth_error_response(disconnected_websocket, auth_failure_result)
        
        # Verify no send attempt was made to disconnected socket
        disconnected_websocket.send_json.assert_not_called()
    
    def test_get_websocket_authenticator_singleton_safe_serialization(self):
        """Test that the global authenticator instance uses safe serialization."""
        authenticator1 = get_websocket_authenticator()
        authenticator2 = get_websocket_authenticator()
        
        # Verify singleton pattern
        assert authenticator1 is authenticator2
        
        # Verify both instances have access to safe serialization (implicit through import)
        # This ensures the singleton doesn't break serialization safety
        assert hasattr(authenticator1, 'create_auth_error_response')
        assert hasattr(authenticator1, 'create_auth_success_response')


class TestWebSocketAuthSerializationRegression:
    """Regression tests to ensure the serialization fix works in real scenarios."""
    
    async def test_reproduction_of_original_json_serialization_error(self):
        """
        REGRESSION TEST: Reproduce the exact error scenario that was failing.
        
        This test recreates the conditions that caused:
        "Object of type WebSocketState is not JSON serializable"
        """
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Create a WebSocket mock that mimics real WebSocket with state
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        mock_websocket.headers = {"authorization": "Bearer invalid-token"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8080
        
        # Create authentication failure that might include state information
        auth_failure = WebSocketAuthResult(
            success=False,
            error_message="WebSocket authentication error: Token validation failed",
            error_code="WEBSOCKET_AUTH_EXCEPTION"
        )
        
        # This call would previously fail with JSON serialization error
        # Now it should succeed with safe serialization
        await authenticator.create_auth_error_response(mock_websocket, auth_failure)
        
        # Verify the response was successfully sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        # CRITICAL REGRESSION TEST: This must not raise a JSON serialization error
        json_string = json.dumps(sent_message)
        
        # Verify the message structure is correct
        assert sent_message["type"] == "authentication_error"
        assert sent_message["error_code"] == "WEBSOCKET_AUTH_EXCEPTION"
        assert "Object of type WebSocketState" not in json_string
    
    async def test_all_websocket_state_enum_values_serialization(self):
        """Test that all possible WebSocketState enum values are handled safely."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Test all possible WebSocketState values
        test_states = [
            (WebSocketState.CONNECTING, "should not send"),  # Not connected, shouldn't send
            (WebSocketState.CONNECTED, "should send"),       # Connected, should send
            (WebSocketState.DISCONNECTED, "should not send") # Disconnected, shouldn't send
        ]
        
        for state, expectation in test_states:
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.client_state = state
            mock_websocket.application_state = state
            mock_websocket.headers = {}
            mock_websocket.client = None
            
            auth_result = WebSocketAuthResult(
                success=False,
                error_message=f"Auth error with state {state}",
                error_code="WEBSOCKET_AUTH_EXCEPTION"
            )
            
            await authenticator.create_auth_error_response(mock_websocket, auth_result)
            
            # Only CONNECTED state should result in send_json being called
            if state == WebSocketState.CONNECTED:
                mock_websocket.send_json.assert_called_once()
                sent_message = mock_websocket.send_json.call_args[0][0]
                
                # CRITICAL: Message must serialize safely
                json.dumps(sent_message)
                
                # Verify error code is correct
                assert sent_message["error_code"] == "WEBSOCKET_AUTH_EXCEPTION"
            else:
                # Should not send to non-connected sockets
                mock_websocket.send_json.assert_not_called()
    
    async def test_fix_maintains_ssot_compliance(self):
        """Test that the serialization fix maintains SSOT compliance."""
        # Verify the fix doesn't break SSOT principles
        authenticator1 = get_websocket_authenticator()
        authenticator2 = get_websocket_authenticator()
        
        # Should still be singleton (SSOT compliance)
        assert authenticator1 is authenticator2
        
        # Should still use unified auth service (SSOT compliance)
        assert hasattr(authenticator1, '_auth_service')
        assert authenticator1._auth_service is not None
        
        # Should still track statistics (SSOT compliance)
        stats = authenticator1.get_websocket_auth_stats()
        assert "ssot_compliance" in stats
        assert stats["ssot_compliance"]["ssot_compliant"] is True
        
        # NEW: Should use safe serialization (fix compliance)
        # Verify by checking that methods exist and can be called without error
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        auth_result = WebSocketAuthResult(success=False, error_code="TEST")
        
        # This should work without JSON serialization errors (fix verification)
        await authenticator1.create_auth_error_response(mock_websocket, auth_result)
        mock_websocket.send_json.assert_called_once()
        
        # Message should be JSON serializable
        sent_message = mock_websocket.send_json.call_args[0][0]
        json.dumps(sent_message)  # Should not raise exception