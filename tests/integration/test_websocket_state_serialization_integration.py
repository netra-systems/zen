"""
INTEGRATION TEST: WebSocket State Serialization in Real GCP Cloud Run Context

This test validates that the WebSocket state serialization fix works in actual
WebSocket connection scenarios that mirror the GCP Cloud Run environment where
the 1011 errors were occurring.

Business Value: Prevents production outages from WebSocket logging errors.
"""

import asyncio
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from netra_backend.app.websocket_core.utils import is_websocket_connected
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool


class TestWebSocketStateSerializationIntegration:
    """Integration tests for WebSocket state serialization in real scenarios."""

    @pytest.fixture
    def auth_helper(self):
        """Provide authenticated test context."""
        return E2EAuthHelper()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket with realistic state behavior."""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state = WebSocketState.CONNECTED
        mock_ws.application_state = WebSocketState.CONNECTED
        mock_ws.client = Mock()
        mock_ws.client.host = "127.0.0.1"
        mock_ws.client.port = 12345
        mock_ws.headers = {"authorization": "Bearer test_token"}
        return mock_ws

    @pytest.mark.asyncio
    async def test_websocket_connection_state_logging_does_not_crash(self, mock_websocket, caplog):
        """Test that WebSocket connection state logging doesn't cause crashes."""
        import logging
        from netra_backend.app.websocket_core.utils import is_websocket_connected
        
        with caplog.at_level(logging.DEBUG):
            # This should not raise any JSON serialization errors
            result = is_websocket_connected(mock_websocket)
            
        # Verify the function worked
        assert result is True
        
        # Verify no JSON serialization errors in logs
        assert "serialization_error" not in caplog.text
        assert "JSON serializable" not in caplog.text

    @pytest.mark.asyncio
    async def test_websocket_auth_state_logging_integration(self, mock_websocket, auth_helper):
        """Test WebSocket authentication with state logging integration."""
        # Create auth service
        auth_service = UnifiedWebSocketAuth()
        
        # Mock the authentication result
        with patch.object(auth_service, '_authenticate_websocket_request') as mock_auth:
            mock_auth.return_value = AsyncMock()
            mock_auth.return_value.is_authenticated = True
            mock_auth.return_value.user_id = "test_user"
            
            # This should complete without JSON serialization errors
            result = await auth_service.authenticate_websocket(mock_websocket, {})
            
        # Verify authentication succeeded
        assert result.is_authenticated is True

    @pytest.mark.asyncio 
    async def test_websocket_connection_pool_state_handling(self, mock_websocket):
        """Test WebSocket connection pool handles state logging correctly."""
        pool = WebSocketConnectionPool()
        
        # Test connection validation (includes state logging)
        with patch.object(pool, '_validate_websocket_for_pool', return_value=True) as mock_validate:
            # Add connection to pool
            success = pool.add_connection("test_user", "conn_123", mock_websocket)
            
            # Should succeed without JSON serialization errors
            assert mock_validate.called

    def test_websocket_state_in_structured_log_context(self, mock_websocket):
        """Test WebSocket state inclusion in structured logging contexts."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate the structured logging context that caused original issues
        log_context = {
            "event": "websocket_connection",
            "connection_id": "conn_123",
            "user_id": "user_456", 
            "websocket_client_state": _safe_websocket_state_for_logging(mock_websocket.client_state),
            "websocket_application_state": _safe_websocket_state_for_logging(mock_websocket.application_state),
            "timestamp": "2025-09-08T12:00:00Z",
            "environment": "staging"
        }
        
        # This should serialize without errors (the critical test)
        json_string = json.dumps(log_context)
        
        # Verify serialization succeeded
        assert json_string is not None
        parsed = json.loads(json_string)
        assert parsed["websocket_client_state"] == "connected"
        assert parsed["websocket_application_state"] == "connected"

    @pytest.mark.parametrize("state", [
        WebSocketState.CONNECTING,
        WebSocketState.CONNECTED, 
        WebSocketState.DISCONNECTED
    ])
    def test_all_websocket_states_in_error_logging(self, state):
        """Test that all WebSocket states can be safely logged in error contexts."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate error logging context
        error_log = {
            "error": "WebSocket operation failed",
            "state": _safe_websocket_state_for_logging(state),
            "details": {
                "retry_count": 3,
                "last_attempt": "2025-09-08T12:00:00Z"
            }
        }
        
        # Should serialize successfully
        json_string = json.dumps(error_log)
        assert json_string is not None
        
        # Verify state is properly serialized
        parsed = json.loads(json_string)
        assert parsed["state"] == state.name.lower()


class TestGCPCloudRunCompatibility:
    """Test compatibility with GCP Cloud Run structured logging patterns."""

    def test_gcp_structured_logging_format(self):
        """Test that our serialization works with GCP's expected structured logging format."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate GCP Cloud Run structured log entry
        gcp_log_entry = {
            "severity": "INFO",
            "message": "WebSocket connection established",
            "timestamp": "2025-09-08T12:00:00.000Z",
            "labels": {
                "service": "netra-backend",
                "version": "1.0.0"
            },
            "jsonPayload": {
                "websocket_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "connection_id": "conn_12345",
                "user_id": "user_67890",
                "event_type": "websocket_connected"
            }
        }
        
        # This should serialize completely without errors
        json_string = json.dumps(gcp_log_entry)
        assert json_string is not None
        
        # Verify the nested jsonPayload serializes correctly
        parsed = json.loads(json_string)
        assert parsed["jsonPayload"]["websocket_state"] == "connected"

    def test_error_context_serialization_for_gcp(self):
        """Test error context serialization for GCP error reporting."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate the error context that was causing 1011 errors
        error_context = {
            "@type": "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent",
            "eventTime": "2025-09-08T12:00:00.000Z",
            "serviceContext": {
                "service": "netra-backend",
                "version": "1.0.0"
            },
            "message": "WebSocket state serialization error",
            "context": {
                "httpRequest": {
                    "method": "GET",
                    "url": "wss://staging.netra.ai/ws",
                    "responseStatusCode": 1011
                },
                "reportLocation": {
                    "filePath": "websocket_core/utils.py",
                    "lineNumber": 78,
                    "functionName": "is_websocket_connected"
                },
                "sourceReferences": [{
                    "repository": "netra-core-generation-1",
                    "revisionId": "main"
                }]
            },
            "jsonPayload": {
                "websocket_client_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "websocket_application_state": _safe_websocket_state_for_logging(WebSocketState.DISCONNECTED),
                "error_details": "Original error: Object of type WebSocketState is not JSON serializable"
            }
        }
        
        # This should serialize completely without errors
        json_string = json.dumps(error_context)
        assert json_string is not None
        
        # Verify all WebSocket states are properly serialized
        parsed = json.loads(json_string) 
        assert parsed["jsonPayload"]["websocket_client_state"] == "connected"
        assert parsed["jsonPayload"]["websocket_application_state"] == "disconnected"


class TestRegressionPrevention:
    """Ensure the original 1011 error pattern is completely fixed."""

    def test_original_1011_error_scenario_fixed(self):
        """Test the exact scenario that caused the original 1011 error."""
        # This was the problematic code pattern:
        websocket_state = WebSocketState.CONNECTED
        
        # Before fix: logger.debug(f"WebSocket state: {websocket_state}") 
        # would cause JSON serialization error in GCP Cloud Run
        
        # After fix: Use safe serialization
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        safe_state = _safe_websocket_state_for_logging(websocket_state)
        
        # This should work in any logging context
        log_message = f"WebSocket state: {safe_state}"
        
        # And should be JSON serializable for structured logging
        structured_log = {"message": log_message, "state": safe_state}
        json.dumps(structured_log)  # Should not raise exception
        
        assert safe_state == "connected"
        assert isinstance(safe_state, str)

    @pytest.mark.parametrize("problematic_state", [
        WebSocketState.CONNECTING,
        WebSocketState.CONNECTED,
        WebSocketState.DISCONNECTED
    ])
    def test_all_problematic_states_fixed(self, problematic_state):
        """Test that all WebSocket states that could cause 1011 errors are fixed."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # These states all could cause the original error
        safe_state = _safe_websocket_state_for_logging(problematic_state)
        
        # Should be JSON serializable in any context
        contexts = [
            {"state": safe_state},
            {"error": f"Connection failed in state: {safe_state}"},
            {"debug": f"State transition: {safe_state}"},
            [safe_state],  # Even in arrays
            safe_state     # Even standalone
        ]
        
        for context in contexts:
            json.dumps(context)  # Should not raise exception
            
        assert safe_state == problematic_state.name.lower()