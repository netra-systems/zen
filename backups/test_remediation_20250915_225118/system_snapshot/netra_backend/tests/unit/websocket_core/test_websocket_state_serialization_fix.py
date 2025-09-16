"""
Test WebSocket State Serialization Fix

This test verifies that WebSocketState enum objects are properly serialized
when sent via WebSocket connections, preventing the JSON serialization errors.

CRITICAL: This test prevents the regression of WebSocket 1011 errors caused by
"Object of type WebSocketState is not JSON serializable" errors.
"""
import json
import pytest
from unittest.mock import AsyncMock, Mock
from enum import Enum
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
from starlette.websockets import WebSocketState as StarletteWebSocketState
from fastapi.websockets import WebSocketState as FastAPIWebSocketState

class WebSocketStateSerializationTests:
    """Test WebSocket state serialization fixes."""

    def test_serialize_starlette_websocket_state(self):
        """Test serialization of Starlette WebSocketState enum."""
        for state in StarletteWebSocketState:
            result = _serialize_message_safely(state)
            assert isinstance(result, str)
            assert result == state.name.lower()

    def test_serialize_fastapi_websocket_state(self):
        """Test serialization of FastAPI WebSocketState enum."""
        for state in FastAPIWebSocketState:
            result = _serialize_message_safely(state)
            assert isinstance(result, str)
            assert result == state.name.lower()

    def test_serialize_dict_with_websocket_state(self):
        """Test serialization of dict containing WebSocketState."""
        message = {'type': 'connection_status', 'websocket_state': StarletteWebSocketState.CONNECTED, 'timestamp': datetime.utcnow(), 'user_id': 'test_user'}
        result = _serialize_message_safely(message)
        assert result['websocket_state'] == 'connected'
        assert isinstance(result['timestamp'], str)
        assert result['user_id'] == 'test_user'
        assert result['type'] == 'connection_status'
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_nested_dict_with_websocket_state(self):
        """Test serialization of nested dict containing WebSocketState."""
        message = {'type': 'diagnostics', 'connection_info': {'state': StarletteWebSocketState.CONNECTING, 'details': {'client_state': FastAPIWebSocketState.DISCONNECTED}}, 'metadata': {'states': [StarletteWebSocketState.CONNECTED, StarletteWebSocketState.DISCONNECTED]}}
        result = _serialize_message_safely(message)
        assert result['connection_info']['state'] == 'connecting'
        assert result['connection_info']['details']['client_state'] == 'disconnected'
        assert result['metadata']['states'] == ['connected', 'disconnected']
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_list_with_websocket_states(self):
        """Test serialization of list containing WebSocketState enums."""
        states = [StarletteWebSocketState.CONNECTING, FastAPIWebSocketState.CONNECTED, StarletteWebSocketState.DISCONNECTED]
        result = _serialize_message_safely(states)
        assert result == ['connecting', 'connected', 'disconnected']
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_enum_keys_in_dict(self):
        """Test serialization when enum objects are used as dictionary keys."""
        message = {StarletteWebSocketState.CONNECTED: 'active', StarletteWebSocketState.DISCONNECTED: 'inactive', 'normal_key': 'normal_value'}
        result = _serialize_message_safely(message)
        assert 'connected' in result
        assert 'disconnected' in result
        assert result['connected'] == 'active'
        assert result['disconnected'] == 'inactive'
        assert result['normal_key'] == 'normal_value'
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_complex_message_structure(self):
        """Test serialization of complex message structure that could cause the original error."""
        message = {'type': 'websocket_diagnostics', 'connection_diagnostics': {'websocket_state': StarletteWebSocketState.CONNECTED, 'client_state': FastAPIWebSocketState.CONNECTED, 'last_ping': datetime.utcnow(), 'error_count': 0}, 'user_context': {'user_id': 'test_user_123', 'connection_count': 1, 'active_states': [StarletteWebSocketState.CONNECTED, FastAPIWebSocketState.CONNECTED]}, 'raw_websocket_info': {StarletteWebSocketState.CONNECTED: {'count': 1, 'details': {'state': FastAPIWebSocketState.CONNECTED, 'timestamp': datetime.utcnow()}}}}
        result = _serialize_message_safely(message)
        assert result['connection_diagnostics']['websocket_state'] == 'connected'
        assert result['connection_diagnostics']['client_state'] == 'connected'
        assert isinstance(result['connection_diagnostics']['last_ping'], str)
        assert result['user_context']['active_states'] == ['connected', 'connected']
        assert 'connected' in result['raw_websocket_info']
        assert result['raw_websocket_info']['connected']['details']['state'] == 'connected'
        assert isinstance(result['raw_websocket_info']['connected']['details']['timestamp'], str)
        json_str = json.dumps(result)
        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed['type'] == 'websocket_diagnostics'

    def test_fallback_enum_handling(self):
        """Test fallback handling for generic enum objects."""

        class CustomEnum(Enum):
            VALUE1 = 'value1'
            VALUE2 = 'value2'
        result = _serialize_message_safely(CustomEnum.VALUE1)
        assert result == 'value1'
        message = {'custom': CustomEnum.VALUE2}
        result = _serialize_message_safely(message)
        assert result['custom'] == 'value2'
        json_str = json.dumps(result)
        assert json_str is not None

    def test_performance_impact_of_serialization(self):
        """Test that safe serialization doesn't significantly impact performance."""
        import time
        message = {'type': 'performance_test', 'states': [StarletteWebSocketState.CONNECTED] * 100, 'nested': {'data': [{'state': FastAPIWebSocketState.CONNECTED}] * 50}, 'timestamp': datetime.utcnow()}
        start_time = time.time()
        for _ in range(10):
            result = _serialize_message_safely(message)
            json.dumps(result)
        end_time = time.time()
        assert end_time - start_time < 0.1

    def test_regression_prevention(self):
        """Test that prevents the specific regression that was occurring."""
        websocket_state = StarletteWebSocketState.CONNECTED
        try:
            result = _serialize_message_safely(websocket_state)
            json.dumps(result)
            assert True
        except TypeError as e:
            if 'not JSON serializable' in str(e):
                pytest.fail(f'WebSocket serialization fix failed: {e}')
            else:
                raise
        assert result == 'connected'

class WebSocketMessageSendingTests:
    """Test WebSocket message sending patterns that were problematic."""

    @pytest.mark.asyncio
    async def test_websocket_send_with_state_objects(self):
        """Test WebSocket send operation with state objects (simulated)."""
        mock_websocket = AsyncMock()
        message = {'type': 'connection_update', 'state': StarletteWebSocketState.CONNECTED, 'client_state': FastAPIWebSocketState.CONNECTED, 'timestamp': datetime.utcnow()}
        safe_message = _serialize_message_safely(message)
        await mock_websocket.send_json(safe_message)
        mock_websocket.send_json.assert_called_once()
        called_args = mock_websocket.send_json.call_args[0][0]
        assert called_args['state'] == 'connected'
        assert called_args['client_state'] == 'connected'
        assert isinstance(called_args['timestamp'], str)
        json.dumps(called_args)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')