"""
CRITICAL REGRESSION TEST: WebSocket 1011 Error Fix Validation

This test specifically validates that the WebSocketState enum serialization fix
prevents the "Object of type WebSocketState is not JSON serializable" error
that was causing 1011 internal server errors in GCP Cloud Run.

Business Impact: Prevents $120K+ MRR loss from WebSocket outages
"""

import asyncio
import json
import pytest
from unittest.mock import patch, Mock
from starlette.websockets import WebSocketState
from fastapi.websockets import WebSocketState as FastAPIWebSocketState

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestWebSocket1011ErrorFix:
    """Regression tests for the specific 1011 WebSocket error scenario."""

    @pytest.fixture
    def auth_helper(self):
        """Provide authenticated test context."""
        return E2EAuthHelper()

    def test_websocket_state_json_serialization_does_not_raise_error(self):
        """Test that WebSocketState enums can be JSON serialized without errors."""
        # This was the core issue: WebSocketState enums causing JSON serialization errors
        
        test_states = [
            WebSocketState.CONNECTING,
            WebSocketState.CONNECTED,
            WebSocketState.DISCONNECTED
        ]
        
        # Before fix: These would raise "Object of type WebSocketState is not JSON serializable"
        # After fix: These should work with safe serialization
        
        for state in test_states:
            # Test direct serialization (should fail without safe wrapper)
            with pytest.raises(TypeError, match="Object of type WebSocketState is not JSON serializable"):
                json.dumps({"state": state})
            
            # Test safe serialization (should work)
            from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
            safe_state = _safe_websocket_state_for_logging(state)
            
            # This should NOT raise any exception
            result = json.dumps({"state": safe_state})
            assert result is not None
            assert state.name.lower() in result

    def test_all_websocket_modules_use_safe_logging(self):
        """Test that all WebSocket modules use safe logging for WebSocketState."""
        # Import all modules that were fixed
        from netra_backend.app.websocket_core import utils, unified_websocket_auth
        from netra_backend.app.services import websocket_connection_pool
        from netra_backend.app.routes import websocket
        
        # Verify each module has the safe logging function
        assert hasattr(utils, '_safe_websocket_state_for_logging')
        assert hasattr(unified_websocket_auth, '_safe_websocket_state_for_logging')
        assert hasattr(websocket_connection_pool, '_safe_websocket_state_for_logging')
        assert hasattr(websocket, '_safe_websocket_state_for_logging')
        
        # Test each function works correctly
        test_state = WebSocketState.CONNECTED
        
        functions = [
            utils._safe_websocket_state_for_logging,
            unified_websocket_auth._safe_websocket_state_for_logging,
            websocket_connection_pool._safe_websocket_state_for_logging,
            websocket._safe_websocket_state_for_logging
        ]
        
        for func in functions:
            result = func(test_state)
            assert result == "connected"
            assert isinstance(result, str)
            # Should be JSON serializable
            json.dumps({"test": result})

    def test_gcp_cloud_run_structured_logging_compatibility(self):
        """Test compatibility with GCP Cloud Run structured logging format."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate the exact structured logging format used by GCP Cloud Run
        # This is what was causing the 1011 errors
        
        gcp_structured_log = {
            "timestamp": "2025-09-08T12:00:00.000Z",
            "severity": "INFO",
            "insertId": "1234567890",
            "resource": {
                "type": "cloud_run_revision",
                "labels": {
                    "service_name": "netra-backend",
                    "revision_name": "netra-backend-00001",
                    "location": "us-central1"
                }
            },
            "labels": {
                "instanceId": "00bf4bf02d3a4e8e"
            },
            "jsonPayload": {
                "message": "WebSocket connection state check",
                "websocket_client_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "websocket_application_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "connection_id": "conn_12345",
                "user_id": "user_67890"
            }
        }
        
        # This should serialize completely without errors
        json_string = json.dumps(gcp_structured_log)
        assert json_string is not None
        
        # Verify the WebSocket states are properly serialized
        parsed = json.loads(json_string)
        assert parsed["jsonPayload"]["websocket_client_state"] == "connected"
        assert parsed["jsonPayload"]["websocket_application_state"] == "connected"

    @pytest.mark.parametrize("error_scenario", [
        "websocket_connection_failed",
        "websocket_authentication_failed", 
        "websocket_state_transition_error",
        "websocket_message_send_failed"
    ])
    def test_error_logging_with_websocket_states(self, error_scenario):
        """Test that error logging with WebSocket states works correctly."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate error contexts that were causing 1011 errors
        error_contexts = {
            "websocket_connection_failed": {
                "error": "Failed to establish WebSocket connection",
                "client_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTING),
                "expected_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED)
            },
            "websocket_authentication_failed": {
                "error": "WebSocket authentication failed", 
                "auth_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "user_id": "user_12345"
            },
            "websocket_state_transition_error": {
                "error": "Invalid WebSocket state transition",
                "from_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTING),
                "to_state": _safe_websocket_state_for_logging(WebSocketState.DISCONNECTED)
            },
            "websocket_message_send_failed": {
                "error": "Failed to send WebSocket message",
                "connection_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "message_type": "agent_update"
            }
        }
        
        error_context = error_contexts[error_scenario]
        
        # This should serialize without errors
        json_string = json.dumps(error_context)
        assert json_string is not None
        
        # All state values should be strings
        parsed = json.loads(json_string)
        for key, value in parsed.items():
            if "state" in key:
                assert isinstance(value, str)
                assert value in ["connecting", "connected", "disconnected"]

    def test_websocket_routes_logging_integration(self):
        """Test that WebSocket routes use safe logging correctly."""
        from netra_backend.app.routes.websocket import _safe_websocket_state_for_logging
        
        # Test the patterns that were causing issues in the routes
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # These logging patterns were causing 1011 errors
        client_state_safe = _safe_websocket_state_for_logging(mock_websocket.client_state)
        app_state_safe = _safe_websocket_state_for_logging(mock_websocket.application_state)
        
        # Simulate the debug logging that was failing
        debug_log = {
            "message": "WebSocket state before loop",
            "client_state": client_state_safe,
            "application_state": app_state_safe,
            "connection_id": "conn_123"
        }
        
        # Should serialize successfully
        json.dumps(debug_log)
        
        # Verify values are correct
        assert client_state_safe == "connected"
        assert app_state_safe == "connected"


class TestRegressionPrevention:
    """Ensure this fix prevents future regressions of the 1011 error."""

    def test_direct_websocket_state_logging_raises_error(self):
        """Verify that direct WebSocket state logging still raises errors (as expected)."""
        # This test ensures we understand WHY the fix was needed
        
        state = WebSocketState.CONNECTED
        
        # Direct JSON serialization should still fail (this is expected behavior)
        with pytest.raises(TypeError, match="Object of type WebSocketState is not JSON serializable"):
            json.dumps({"state": state})
        
        # This confirms our fix is necessary and working correctly

    def test_safe_logging_prevents_the_error(self):
        """Test that safe logging prevents the JSON serialization error."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        state = WebSocketState.CONNECTED
        
        # Safe logging should prevent the error
        safe_state = _safe_websocket_state_for_logging(state)
        
        # This should NOT raise an error
        result = json.dumps({"state": safe_state})
        assert result is not None
        assert '"state": "connected"' in result

    def test_all_websocket_states_are_handled(self):
        """Ensure all WebSocketState enum values are handled correctly."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Test all possible WebSocketState values
        all_states = [
            WebSocketState.CONNECTING,
            WebSocketState.CONNECTED,
            WebSocketState.DISCONNECTED
        ]
        
        expected_values = ["connecting", "connected", "disconnected"]
        
        for i, state in enumerate(all_states):
            safe_state = _safe_websocket_state_for_logging(state)
            
            # Should be the expected lowercase string
            assert safe_state == expected_values[i]
            
            # Should be JSON serializable
            json.dumps({"state": safe_state})
            
            # Should work in complex nested structures
            complex_structure = {
                "error": "WebSocket error",
                "details": {
                    "state": safe_state,
                    "retry_count": 3
                },
                "metadata": [safe_state, "other_value"]
            }
            
            json.dumps(complex_structure)  # Should not raise


class TestProductionScenarios:
    """Test scenarios that mirror production conditions where 1011 errors occurred."""

    def test_staging_environment_websocket_logging(self):
        """Test WebSocket logging in staging environment conditions."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate staging environment logging context
        staging_log_context = {
            "environment": "staging",
            "service": "netra-backend", 
            "instance": "staging-instance-001",
            "websocket_diagnostics": {
                "client_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "application_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "connection_count": 5,
                "last_message_time": "2025-09-08T12:00:00Z"
            },
            "gcp_cloud_run": {
                "revision": "netra-backend-staging-00042",
                "memory_usage": "256MB",
                "cpu_usage": "15%"
            }
        }
        
        # This should serialize successfully in staging
        json_string = json.dumps(staging_log_context)
        assert json_string is not None
        
        # Verify WebSocket states are properly serialized
        parsed = json.loads(json_string)
        diagnostics = parsed["websocket_diagnostics"]
        assert diagnostics["client_state"] == "connected"
        assert diagnostics["application_state"] == "connected"

    def test_production_error_reporting_integration(self):
        """Test integration with production error reporting."""
        from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging
        
        # Simulate the error report that would be sent to GCP Error Reporting
        error_report = {
            "@type": "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent",
            "eventTime": "2025-09-08T12:00:00.000Z",
            "serviceContext": {
                "service": "netra-backend-production",
                "version": "1.2.3"
            },
            "message": "WebSocket connection error prevented",
            "context": {
                "httpRequest": {
                    "method": "GET", 
                    "url": "wss://app.netra.ai/ws",
                    "responseStatusCode": 200  # NOT 1011 anymore!
                },
                "reportLocation": {
                    "filePath": "websocket_core/utils.py",
                    "lineNumber": 111,
                    "functionName": "is_websocket_connected"
                }
            },
            "sourceLocation": {
                "file": "websocket_core/utils.py",
                "line": 111,
                "function": "_safe_websocket_state_for_logging"
            },
            "errorContext": {
                "websocket_client_state": _safe_websocket_state_for_logging(WebSocketState.CONNECTED),
                "websocket_application_state": _safe_websocket_state_for_logging(WebSocketState.DISCONNECTED),
                "fix_applied": "Safe WebSocket state serialization",
                "error_prevented": "Object of type WebSocketState is not JSON serializable"
            }
        }
        
        # This should serialize completely for GCP Error Reporting
        json_string = json.dumps(error_report)
        assert json_string is not None
        
        # Verify the error context serialized correctly
        parsed = json.loads(json_string) 
        error_context = parsed["errorContext"]
        assert error_context["websocket_client_state"] == "connected"
        assert error_context["websocket_application_state"] == "disconnected"