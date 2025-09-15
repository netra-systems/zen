"""
Essential WebSocket JSON Serialization Tests

Core tests validating the fixes for "Object of type WebSocketState is not JSON serializable"
errors that were blocking staging deployment in the ultimate test loop.
"""
import json
import pytest
from fastapi.websockets import WebSocketState
from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging

class WebSocketJSONSerializationFixesTests:
    """Essential tests for WebSocket JSON serialization safety."""

    def test_websocket_state_safe_logging_all_states(self):
        """Test safe logging for all WebSocket states."""
        test_cases = [(WebSocketState.CONNECTING, 'connecting'), (WebSocketState.CONNECTED, 'connected'), (WebSocketState.DISCONNECTED, 'disconnected')]
        for state, expected in test_cases:
            safe_state = _safe_websocket_state_for_logging(state)
            assert safe_state == expected
            json_data = json.dumps({'websocket_state': safe_state})
            parsed = json.loads(json_data)
            assert parsed['websocket_state'] == expected

    def test_websocket_state_direct_json_fails(self):
        """Confirm WebSocket enums cannot be directly JSON serialized."""
        with pytest.raises(TypeError, match='Object of type WebSocketState is not JSON serializable'):
            json.dumps({'state': WebSocketState.CONNECTED})

    def test_websocket_state_safe_logging_edge_cases(self):
        """Test safe logging handles edge cases properly."""
        edge_cases = [(None, 'None'), ('string', 'string'), (123, '123'), ([], '[]')]
        for input_val, expected in edge_cases:
            safe_val = _safe_websocket_state_for_logging(input_val)
            assert safe_val == expected
            json_data = json.dumps({'value': safe_val})
            parsed = json.loads(json_data)
            assert parsed['value'] == expected

    def test_staging_error_scenario_fix(self):
        """Test the exact staging error scenario that was fixed."""
        websocket_state = WebSocketState.CONNECTED
        safe_state = _safe_websocket_state_for_logging(websocket_state)
        error_context = {'environment': 'staging', 'error_code': 'WEBSOCKET_AUTH_EXCEPTION', 'failure_context': {'websocket_state': safe_state, 'client_info': {'host': '169.254.169.126', 'port': 2032}, 'timestamp': '2025-09-08 05:02:18.419998 UTC'}}
        json_str = json.dumps(error_context)
        parsed = json.loads(json_str)
        assert parsed['failure_context']['websocket_state'] == 'connected'

    def test_connection_states_dict_json_serialization(self):
        """Test connection states dictionary can be JSON serialized."""
        connection_states = {}
        for state in [WebSocketState.CONNECTED, WebSocketState.DISCONNECTED, WebSocketState.CONNECTING]:
            safe_key = _safe_websocket_state_for_logging(state)
            connection_states[safe_key] = connection_states.get(safe_key, 0) + 1
        json_str = json.dumps(connection_states)
        parsed = json.loads(json_str)
        assert 'connected' in parsed
        assert 'disconnected' in parsed
        assert 'connecting' in parsed
        assert all((isinstance(v, int) for v in parsed.values()))

    def test_websocket_logging_in_error_messages(self):
        """Test WebSocket state logging in error message scenarios."""
        error_scenarios = [{'error': 'connection_failed', 'websocket_state': _safe_websocket_state_for_logging(WebSocketState.CONNECTING), 'retry_count': 3}, {'error': 'authentication_failed', 'websocket_state': _safe_websocket_state_for_logging(WebSocketState.CONNECTED), 'user_id': 'test-user-123'}, {'error': 'unexpected_disconnect', 'websocket_state': _safe_websocket_state_for_logging(WebSocketState.DISCONNECTED), 'duration_seconds': 45.2}]
        for scenario in error_scenarios:
            json_str = json.dumps(scenario)
            parsed = json.loads(json_str)
            assert 'websocket_state' in parsed
            assert isinstance(parsed['websocket_state'], str)

    def test_gcp_cloud_run_structured_logging_compatibility(self):
        """Test compatibility with GCP Cloud Run structured logging."""
        log_entry = {'timestamp': '2025-09-08T05:02:18.419998Z', 'severity': 'ERROR', 'message': 'WebSocket authentication failed', 'jsonPayload': {'websocket_state': _safe_websocket_state_for_logging(WebSocketState.CONNECTED), 'connection_id': 'conn-12345', 'user_id': 'user-67890', 'environment': 'staging', 'error_details': {'code': 'AUTH_FAILED', 'state_info': _safe_websocket_state_for_logging(WebSocketState.CONNECTED)}}}
        json_str = json.dumps(log_entry)
        parsed = json.loads(json_str)
        assert parsed['jsonPayload']['websocket_state'] == 'connected'
        assert parsed['jsonPayload']['error_details']['state_info'] == 'connected'

    def test_prevention_regression_all_websocket_states(self):
        """Regression prevention test for all WebSocket states."""
        all_states = [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED]
        for state in all_states:
            contexts = [{'auth_state': _safe_websocket_state_for_logging(state)}, {'connection_info': {'state': _safe_websocket_state_for_logging(state)}}, {'error_context': {'websocket_state': _safe_websocket_state_for_logging(state)}}, {'stats': {_safe_websocket_state_for_logging(state): 1}}]
            for context in contexts:
                json_str = json.dumps(context)
                parsed = json.loads(json_str)
                assert isinstance(parsed, dict)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')