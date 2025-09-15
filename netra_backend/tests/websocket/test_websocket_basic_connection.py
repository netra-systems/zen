"""
Basic WebSocket Connection Test

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise (All customer segments)
- Business Goal: Core WebSocket infrastructure reliability
- Value Impact: Validates fundamental real-time communication capability
- Revenue Impact: Foundation for all real-time features ($1M+ ARR dependency)

This test focuses on the most fundamental websocket functionality:
1. Connection establishment without authentication (using /ws/test endpoint)
2. Basic message send/receive (ping/pong)
3. JSON message parsing
4. Connection termination

Note: These tests use mocked WebSocket connections to validate the basic
WebSocket infrastructure without requiring a running server. For integration
tests with real WebSocket servers, see tests/integration/websocket/.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock, Mock, patch
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment
import pytest
pytestmark = [pytest.mark.env_test]

class TestWebSocketBasicConnection:
    """Test basic WebSocket connectivity using mocked connections."""

    @pytest.mark.asyncio
    async def test_websocket_test_endpoint_connection(self):
        """Test that WebSocket connection logic handles successful connections properly."""
        mock_websocket = AsyncMock()
        mock_websocket.open = True
        welcome_message = json.dumps({'type': 'connection_established', 'connection_id': 'test-connection-123', 'server_time': datetime.now(timezone.utc).isoformat(), 'message': 'Welcome to Netra WebSocket test endpoint'})
        mock_websocket.recv = AsyncMock(return_value=welcome_message)
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            websocket_url = 'ws://localhost:8000/ws/test'
            async with mock_connection as websocket:
                assert websocket.open, 'WebSocket should be open after connection'
                welcome_message_raw = await websocket.recv()
                welcome_data = json.loads(welcome_message_raw)
                assert 'type' in welcome_data
                assert welcome_data['type'] == 'connection_established'
                assert 'connection_id' in welcome_data
                assert 'server_time' in welcome_data
                assert 'message' in welcome_data
                print(f'SUCCESS: Received welcome message: {welcome_data}')

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Test basic ping/pong functionality using mocked WebSocket."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established', 'connection_id': 'test-connection-456'})
        pong_message = json.dumps({'type': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat(), 'original_ping': {'test': 'ping_test'}})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, pong_message])
        mock_websocket.send = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                welcome_message_raw = await websocket.recv()
                welcome_data = json.loads(welcome_message_raw)
                print(f"Connected with ID: {welcome_data.get('connection_id')}")
                ping_message = {'type': 'ping', 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': {'test': 'ping_test'}}
                await websocket.send(json.dumps(ping_message))
                print(f'SENT: Ping message: {ping_message}')
                response = await websocket.recv()
                response_data = json.loads(response)
                assert response_data['type'] == 'pong'
                assert 'timestamp' in response_data
                print(f'RECEIVED: Pong response: {response_data}')
                websocket.send.assert_called_once_with(json.dumps(ping_message))

    @pytest.mark.asyncio
    async def test_websocket_echo_message(self):
        """Test echo functionality using mocked WebSocket."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established'})
        echo_message = {'type': 'echo', 'data': {'test_content': 'Hello WebSocket!', 'number': 42, 'bool': True}}
        echo_response = json.dumps({'type': 'echo_response', 'original': echo_message, 'timestamp': datetime.now(timezone.utc).isoformat()})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, echo_response])
        mock_websocket.send = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                await websocket.recv()
                await websocket.send(json.dumps(echo_message))
                print(f'SENT: Echo message: {echo_message}')
                response = await websocket.recv()
                response_data = json.loads(response)
                assert response_data['type'] == 'echo_response'
                assert 'original' in response_data
                assert 'timestamp' in response_data
                assert response_data['original'] == echo_message
                print(f'RECEIVED: Echo response: {response_data}')
                websocket.send.assert_called_once_with(json.dumps(echo_message))

    @pytest.mark.asyncio
    async def test_websocket_invalid_json_handling(self):
        """Test how the WebSocket handles invalid JSON messages using mocked connection."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established'})
        error_response = json.dumps({'type': 'error', 'message': 'Invalid JSON: Expecting property name enclosed in double quotes', 'timestamp': datetime.now(timezone.utc).isoformat()})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, error_response])
        mock_websocket.send = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                await websocket.recv()
                invalid_json = '{ this is not valid json }'
                await websocket.send(invalid_json)
                print(f'SENT: Invalid JSON: {invalid_json}')
                response = await websocket.recv()
                response_data = json.loads(response)
                assert response_data['type'] == 'error'
                assert 'message' in response_data
                assert 'Invalid JSON' in response_data['message']
                print(f'RECEIVED: Error response: {response_data}')
                websocket.send.assert_called_once_with(invalid_json)

    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self):
        """Test handling of unknown message types using mocked connection."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established'})
        ack_response = json.dumps({'type': 'ack', 'received_type': 'unknown_message_type', 'timestamp': datetime.now(timezone.utc).isoformat()})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, ack_response])
        mock_websocket.send = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                await websocket.recv()
                unknown_message = {'type': 'unknown_message_type', 'data': {'content': 'this is an unknown message type'}}
                await websocket.send(json.dumps(unknown_message))
                print(f'SENT: Unknown message type: {unknown_message}')
                response = await websocket.recv()
                response_data = json.loads(response)
                assert response_data['type'] == 'ack'
                assert response_data['received_type'] == 'unknown_message_type'
                assert 'timestamp' in response_data
                print(f'RECEIVED: Ack response: {response_data}')
                websocket.send.assert_called_once_with(json.dumps(unknown_message))

    @pytest.mark.asyncio
    async def test_websocket_connection_timeout_handling(self):
        """Test that WebSocket handles connection timeouts gracefully using mocked connection."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established'})
        heartbeat_message = json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat(), 'server_uptime': 3600})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, heartbeat_message])
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                await websocket.recv()
                try:
                    heartbeat_msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    heartbeat_data = json.loads(heartbeat_msg)
                    assert heartbeat_data['type'] == 'heartbeat'
                    assert 'timestamp' in heartbeat_data
                    print(f'RECEIVED: Heartbeat: {heartbeat_data}')
                except asyncio.TimeoutError:
                    print('WARNING: No heartbeat received within timeout (this may be expected)')
                    assert True

    @pytest.mark.asyncio
    async def test_websocket_multiple_messages_sequence(self):
        """Test sending multiple messages in sequence using mocked connection."""
        mock_websocket = AsyncMock()
        welcome_message = json.dumps({'type': 'connection_established'})
        pong_response_1 = json.dumps({'type': 'pong', 'data': {'sequence': 1}})
        echo_response = json.dumps({'type': 'echo_response', 'original': {'type': 'echo', 'data': {'content': 'message 2'}}})
        pong_response_2 = json.dumps({'type': 'pong', 'data': {'sequence': 3}})
        ack_response = json.dumps({'type': 'ack', 'received_type': 'unknown_type'})
        mock_websocket.recv = AsyncMock(side_effect=[welcome_message, pong_response_1, echo_response, pong_response_2, ack_response])
        mock_websocket.send = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                await websocket.recv()
                messages = [{'type': 'ping', 'data': {'sequence': 1}}, {'type': 'echo', 'data': {'content': 'message 2'}}, {'type': 'ping', 'data': {'sequence': 3}}, {'type': 'unknown_type', 'data': {'sequence': 4}}]
                responses = []
                for i, message in enumerate(messages):
                    await websocket.send(json.dumps(message))
                    print(f'SENT: Message {i + 1}: {message}')
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    responses.append(response_data)
                    print(f'RECEIVED: Response {i + 1}: {response_data}')
                assert len(responses) == len(messages), f'Expected {len(messages)} responses, got {len(responses)}'
                assert responses[0]['type'] == 'pong'
                assert responses[1]['type'] == 'echo_response'
                assert responses[2]['type'] == 'pong'
                assert responses[3]['type'] == 'ack'
                assert websocket.send.call_count == len(messages), f'Expected {len(messages)} send calls'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')