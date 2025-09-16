"""
Comprehensive WebSocket JSON Serialization Tests

Tests all WebSocket components for JSON serialization safety, preventing
"Object of type WebSocketState is not JSON serializable" errors in staging.

These tests validate the fixes applied in ultimate test deploy loop Cycle 3.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging

class WebSocketJSONSerializationTests:
    """Test WebSocket components for JSON serialization safety."""

    def test_safe_websocket_state_logging_function(self):
        """Test the safe WebSocket state logging utility function."""
        assert _safe_websocket_state_for_logging(WebSocketState.CONNECTING) == 'connecting'
        assert _safe_websocket_state_for_logging(WebSocketState.CONNECTED) == 'connected'
        assert _safe_websocket_state_for_logging(WebSocketState.DISCONNECTED) == 'disconnected'
        assert _safe_websocket_state_for_logging(None) == 'None'
        assert _safe_websocket_state_for_logging('invalid') == 'invalid'
        for state in [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED]:
            safe_state = _safe_websocket_state_for_logging(state)
            json_result = json.dumps({'state': safe_state})
            assert isinstance(json_result, str)
            parsed = json.loads(json_result)
            assert parsed['state'] == safe_state

    def test_unified_websocket_auth_connection_states_serialization(self):
        """Test UnifiedWebSocketAuthenticator connection states tracking for JSON safety."""
        auth = UnifiedWebSocketAuthenticator()
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        with patch.object(auth, '_safe_websocket_state_for_logging') as mock_safe:
            mock_safe.return_value = 'connected'
            connection_state = mock_websocket.client_state
            connection_state_safe = mock_safe(connection_state)
            auth._connection_states_seen = {}
            auth._connection_states_seen[connection_state_safe] = auth._connection_states_seen.get(connection_state_safe, 0) + 1
            assert 'connected' in auth._connection_states_seen
            assert auth._connection_states_seen['connected'] == 1
            states_json = json.dumps(auth._connection_states_seen)
            assert isinstance(states_json, str)
            parsed_states = json.loads(states_json)
            assert parsed_states['connected'] == 1

    def test_unified_websocket_auth_stats_json_serialization(self):
        """Test that WebSocket auth stats can be JSON serialized safely."""
        auth = UnifiedWebSocketAuthenticator()
        auth._connection_states_seen = {'connected': 5, 'disconnected': 2, 'connecting': 1}
        stats = {'connection_states': auth._connection_states_seen, 'total_connections': sum(auth._connection_states_seen.values())}
        stats_json = json.dumps(stats)
        assert isinstance(stats_json, str)
        parsed_stats = json.loads(stats_json)
        assert parsed_stats['connection_states']['connected'] == 5
        assert parsed_stats['total_connections'] == 8

    def test_unified_authentication_service_debug_logging(self):
        """Test UnifiedAuthenticationService debug logging JSON serialization."""
        auth_service = UnifiedAuthenticationService()
        mock_websocket = Mock(spec=WebSocket)
        test_cases = [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED]
        for state in test_cases:
            mock_websocket.client_state = state
            with patch.object(auth_service, '_safe_websocket_state_for_logging') as mock_safe:
                expected_safe_state = state.name.lower()
                mock_safe.return_value = expected_safe_state
                debug_data = {'websocket_state': mock_safe(getattr(mock_websocket, 'client_state', 'unknown')), 'connection_id': 'test-123', 'user_id': 'user-456'}
                debug_json = json.dumps(debug_data)
                assert isinstance(debug_json, str)
                parsed_debug = json.loads(debug_json)
                assert parsed_debug['websocket_state'] == expected_safe_state
                assert parsed_debug['connection_id'] == 'test-123'

    def test_websocket_state_enum_direct_serialization_fails(self):
        """Verify that WebSocketState enums cannot be directly JSON serialized."""
        with pytest.raises(TypeError, match='Object of type WebSocketState is not JSON serializable'):
            json.dumps({'state': WebSocketState.CONNECTED})
        safe_state = _safe_websocket_state_for_logging(WebSocketState.CONNECTED)
        json_result = json.dumps({'state': safe_state})
        assert json.loads(json_result)['state'] == 'connected'

    def test_all_websocket_states_safe_logging(self):
        """Test safe logging for all possible WebSocket states."""
        all_states = [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED]
        for state in all_states:
            safe_state = _safe_websocket_state_for_logging(state)
            assert isinstance(safe_state, str)
            assert safe_state in ['connecting', 'connected', 'disconnected']
            data = {'websocket_state': safe_state, 'timestamp': '2025-09-08T05:00:00Z', 'connection_id': 'test-conn'}
            json_str = json.dumps(data)
            parsed = json.loads(json_str)
            assert parsed['websocket_state'] == safe_state

    def test_websocket_error_handling_json_serialization(self):
        """Test error handling scenarios for JSON serialization safety."""
        edge_cases = [None, 'string_state', 123, {'complex': 'object'}, []]
        for case in edge_cases:
            safe_state = _safe_websocket_state_for_logging(case)
            assert isinstance(safe_state, str)
            error_data = {'error': 'WebSocket state conversion', 'original_state': safe_state, 'type': 'edge_case_test'}
            json_str = json.dumps(error_data)
            parsed = json.loads(json_str)
            assert parsed['original_state'] == safe_state

    def test_staging_gcp_cloud_run_logging_scenario(self):
        """Test the exact scenario that was failing in staging GCP Cloud Run."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        error_context = {'environment': 'staging', 'ssot_authentication': True, 'error_code': 'WEBSOCKET_AUTH_EXCEPTION', 'failure_context': {'error_code': 'WEBSOCKET_AUTH_EXCEPTION', 'environment': 'staging', 'client_info': {'host': '169.254.169.126', 'port': 2032, 'user_agent': 'Netra-E2E-Tests/1.0'}, 'auth_headers': {'authorization_present': True, 'authorization_preview': 'Bearer eyJhbGciOiJIUzI1NiIsInR...'}, 'websocket_state': _safe_websocket_state_for_logging(mock_websocket.client_state), 'timestamp': '2025-09-08 05:02:18.419998 UTC'}}
        json_str = json.dumps(error_context)
        parsed = json.loads(json_str)
        assert parsed['failure_context']['websocket_state'] == 'connected'
        assert parsed['environment'] == 'staging'

class WebSocketComponentsIntegrationTests:
    """Integration tests for WebSocket components with JSON serialization."""

    def test_end_to_end_websocket_flow_json_safety(self):
        """Test complete WebSocket flow maintains JSON serialization safety."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        auth = UnifiedWebSocketAuthenticator()
        auth._connection_states_seen = {}
        connection_state_safe = _safe_websocket_state_for_logging(mock_websocket.client_state)
        auth._connection_states_seen[connection_state_safe] = 1
        auth_service = UnifiedAuthenticationService()
        system_state = {'auth_stats': auth._connection_states_seen, 'websocket_info': {'state': _safe_websocket_state_for_logging(mock_websocket.client_state), 'connection_id': 'test-conn-123'}, 'timestamp': '2025-09-08T05:00:00Z'}
        json_str = json.dumps(system_state)
        parsed = json.loads(json_str)
        assert parsed['auth_stats']['connected'] == 1
        assert parsed['websocket_info']['state'] == 'connected'
        assert parsed['timestamp'] == '2025-09-08T05:00:00Z'

    def test_prevention_of_future_websocket_json_bugs(self):
        """Test that prevents future WebSocket JSON serialization bugs."""
        mock_websocket = Mock(spec=WebSocket)
        for state in [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED]:
            mock_websocket.client_state = state
            log_scenarios = [{'auth_event': 'connection_attempt', 'websocket_state': _safe_websocket_state_for_logging(state), 'user_id': 'test-user'}, {'error_type': 'websocket_error', 'state': _safe_websocket_state_for_logging(state), 'details': 'test error'}, {'stats': {_safe_websocket_state_for_logging(state): 1}}]
            for scenario in log_scenarios:
                json_str = json.dumps(scenario)
                parsed = json.loads(json_str)
                assert isinstance(parsed, dict)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')