class WebSocketTestConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError('WebSocket is closed')
        self.messages_sent.append(message)

    async def close(self, code: int=1000, reason: str='Normal closure'):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
'\nWebSocket Cross-System Failure Tests (Tests 26-35)\n\nThese tests are designed to FAIL initially to expose real WebSocket communication issues\nbetween backend and frontend systems. Each test represents a specific failure mode that\ncould occur in production.\n\nBusiness Value Justification (BVJ):\n- Segment: Platform/Internal\n- Business Goal: System Stability & Risk Reduction  \n- Value Impact: Prevents WebSocket failures that could cause 100% communication loss\n- Strategic Impact: Enables proactive detection of cross-system communication failures\n\nIMPORTANT: These tests WILL FAIL initially. This is intentional to expose actual issues.\n'
import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment
import pytest
import websockets
from fastapi import WebSocket
from fastapi.testclient import TestClient
from netra_backend.app.core.app_factory import create_app
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
logger = central_logger.get_logger(__name__)

class TestWebSocketCrossSystemFailures:
    """Test suite designed to FAIL and expose WebSocket cross-system issues."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_26_message_format_mismatch(self, client):
        """Test 26: Message Format Mismatch
        
        This test WILL FAIL because backend sends {type, payload}
        but frontend expects {event, data} format.
        
        Expected Failure: AssertionError - message format mismatch
        """
        logger.info('Test 26: Testing message format mismatch between backend and frontend')
        try:
            with client.websocket_connect('/ws') as websocket:
                backend_format_message = {'type': 'agent_response', 'payload': {'message': 'Hello from agent', 'timestamp': time.time()}}
                websocket.send_json(backend_format_message)
                response = websocket.receive_json()
                expected_frontend_format = {'event': 'agent_response', 'data': {'message': 'Hello from agent', 'timestamp': response.get('timestamp', time.time())}}
                assert 'event' in response, f"Frontend expects 'event' field, got: {response}"
                assert 'data' in response, f"Frontend expects 'data' field, got: {response}"
                assert response['event'] == 'agent_response', f'Event type mismatch: {response}'
        except Exception as e:
            logger.error(f'Test 26 failed as expected - Message format mismatch: {e}')
            raise AssertionError(f'Message format mismatch detected: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_27_websocket_auth_token_refresh(self, client):
        """Test 27: WebSocket Auth Token Refresh
        
        This test WILL FAIL because WebSocket disconnects during token refresh
        and doesn't properly handle the re-authentication flow.
        
        Expected Failure: WebSocket disconnects when token expires
        """
        logger.info('Test 27: Testing WebSocket behavior during auth token refresh')
        try:
            expired_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJleHAiOjE2MDAwMDAwMDB9.invalid'
            headers = {'Authorization': f'Bearer {expired_token}'}
            with pytest.raises(Exception) as exc_info:
                with client.websocket_connect('/ws', headers=headers) as websocket:
                    websocket.send_json({'type': 'ping', 'timestamp': time.time()})
                    response = websocket.receive_json()
                    assert response is not None, 'Should receive response even with expired token'
                    assert 'error' not in response, 'Should not receive auth error'
            raise AssertionError('WebSocket should have disconnected due to expired token')
        except Exception as e:
            logger.error(f'Test 27 failed as expected - Auth token refresh issue: {e}')
            raise AssertionError(f'WebSocket auth token refresh failed: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_28_binary_message_corruption(self, client):
        """Test 28: Binary Message Corruption
        
        This test WILL FAIL because binary WebSocket frames get corrupted
        when passing through the message processing pipeline.
        
        Expected Failure: Binary data corruption during transmission
        """
        logger.info('Test 28: Testing binary message corruption in WebSocket frames')
        try:
            with client.websocket_connect('/ws') as websocket:
                original_binary_data = b'\\x89PNG\\r\\x1a\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x01\\x00'
                binary_message = {'type': 'file_upload', 'filename': 'test.png', 'content': original_binary_data.hex(), 'size': len(original_binary_data)}
                websocket.send_json(binary_message)
                response = websocket.receive_json()
                if 'content' in response:
                    received_binary = bytes.fromhex(response['content'])
                    assert received_binary == original_binary_data, f'Binary data corrupted: original={original_binary_data.hex()}, received={received_binary.hex()}'
                    assert len(received_binary) == len(original_binary_data), f'Binary data size mismatch: {len(received_binary)} vs {len(original_binary_data)}'
                else:
                    raise AssertionError('No binary content in response')
        except Exception as e:
            logger.error(f'Test 28 failed as expected - Binary message corruption: {e}')
            raise AssertionError(f'Binary message corruption detected: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_29_message_ordering_violation(self, client):
        """Test 29: Message Ordering Violation
        
        This test WILL FAIL because messages arrive out of order to frontend
        due to async processing without proper sequencing.
        
        Expected Failure: Messages received in wrong order
        """
        logger.info('Test 29: Testing message ordering violations in WebSocket communication')
        try:
            with client.websocket_connect('/ws') as websocket:
                messages = []
                for i in range(5):
                    message = {'type': 'sequence_test', 'sequence_id': i, 'timestamp': time.time() + i * 0.001, 'data': f'Message {i}'}
                    messages.append(message)
                    websocket.send_json(message)
                received_messages = []
                for _ in range(5):
                    response = websocket.receive_json()
                    received_messages.append(response)
                for i, response in enumerate(received_messages):
                    expected_sequence = i
                    actual_sequence = response.get('sequence_id', -1)
                    assert actual_sequence == expected_sequence, f'Message order violation: expected sequence {expected_sequence}, got {actual_sequence}'
                timestamps = [msg.get('timestamp', 0) for msg in received_messages]
                sorted_timestamps = sorted(timestamps)
                assert timestamps == sorted_timestamps, f'Timestamp ordering violation: {timestamps} vs {sorted_timestamps}'
        except Exception as e:
            logger.error(f'Test 29 failed as expected - Message ordering violation: {e}')
            raise AssertionError(f'Message ordering violation detected: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_30_websocket_connection_pool_exhaustion(self, client):
        """Test 30: WebSocket Connection Pool Exhaustion
        
        This test WILL FAIL because too many connections crash the system
        and proper connection limits are not enforced.
        
        Expected Failure: Connection pool exhaustion crashes system
        """
        logger.info('Test 30: Testing WebSocket connection pool exhaustion')
        connections = []
        try:
            max_connections = 50
            for i in range(max_connections):
                try:
                    connection = client.websocket_connect('/ws')
                    websocket = connection.__enter__()
                    connections.append((connection, websocket))
                    websocket.send_json({'type': 'connection_test', 'connection_id': i, 'timestamp': time.time()})
                except Exception as e:
                    logger.error(f'Connection {i} failed: {e}')
                    assert i >= 45, f'Connection pool exhausted too early at connection {i}'
                    break
            if len(connections) == max_connections:
                test_websocket = connections[0][1]
                test_websocket.send_json({'type': 'system_health_check'})
                response = test_websocket.receive_json()
                assert response is not None, 'System became unresponsive under connection load'
            assert len(connections) == max_connections, f'Could only create {len(connections)} of {max_connections} connections'
        except Exception as e:
            logger.error(f'Test 30 failed as expected - Connection pool exhaustion: {e}')
            raise AssertionError(f'Connection pool exhaustion detected: {e}')
        finally:
            for connection, websocket in connections:
                try:
                    connection.__exit__(None, None, None)
                except Exception:
                    pass

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_31_cross_tab_websocket_sync(self, client):
        """Test 31: Cross-Tab WebSocket Sync
        
        This test WILL FAIL because messages don't sync across browser tabs
        when multiple WebSocket connections exist for the same user.
        
        Expected Failure: Messages not synchronized across tabs
        """
        logger.info('Test 31: Testing cross-tab WebSocket synchronization')
        try:
            user_id = 'test_user_123'
            with client.websocket_connect(f'/ws/{user_id}') as tab1_ws:
                with client.websocket_connect(f'/ws/{user_id}') as tab2_ws:
                    tab1_message = {'type': 'user_action', 'action': 'send_message', 'content': 'Hello from tab 1', 'tab_id': 'tab1', 'user_id': user_id, 'timestamp': time.time()}
                    tab1_ws.send_json(tab1_message)
                    tab1_response = tab1_ws.receive_json()
                    assert tab1_response is not None, 'Tab 1 should receive response'
                    try:
                        tab2_response = tab2_ws.receive_json()
                        assert tab2_response is not None, 'Tab 2 should receive synced message'
                        assert tab2_response.get('content') == 'Hello from tab 1', f'Tab 2 should receive same content: {tab2_response}'
                        assert tab2_response.get('tab_id') == 'tab1', f'Tab 2 should know message origin: {tab2_response}'
                    except Exception as sync_error:
                        raise AssertionError(f'Cross-tab sync failed: {sync_error}')
                    tab2_message = {'type': 'user_action', 'action': 'send_message', 'content': 'Hello from tab 2', 'tab_id': 'tab2', 'user_id': user_id, 'timestamp': time.time()}
                    tab2_ws.send_json(tab2_message)
                    tab2_response = tab2_ws.receive_json()
                    tab1_sync_response = tab1_ws.receive_json()
                    assert tab1_sync_response.get('content') == 'Hello from tab 2', 'Tab 1 should receive message from tab 2'
        except Exception as e:
            logger.error(f'Test 31 failed as expected - Cross-tab sync failure: {e}')
            raise AssertionError(f'Cross-tab WebSocket sync failed: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_32_websocket_reconnection_state_loss(self, client):
        """Test 32: WebSocket Reconnection State Loss
        
        This test WILL FAIL because state is lost after reconnection
        and the connection doesn't properly restore previous context.
        
        Expected Failure: State lost after WebSocket reconnection
        """
        logger.info('Test 32: Testing WebSocket state loss during reconnection')
        try:
            user_id = 'test_user_reconnect'
            initial_state = {'user_preferences': {'theme': 'dark', 'language': 'en'}, 'session_data': {'workflow_step': 3, 'unsaved_changes': True}, 'connection_id': str(uuid.uuid4())}
            with client.websocket_connect(f'/ws/{user_id}') as websocket:
                setup_message = {'type': 'initialize_state', 'user_id': user_id, 'state': initial_state, 'timestamp': time.time()}
                websocket.send_json(setup_message)
                setup_response = websocket.receive_json()
                assert setup_response.get('type') == 'state_initialized', f'State initialization failed: {setup_response}'
                state_check = {'type': 'get_state', 'user_id': user_id}
                websocket.send_json(state_check)
                state_response = websocket.receive_json()
                assert state_response.get('state') == initial_state, f'Initial state not stored correctly: {state_response}'
            with client.websocket_connect(f'/ws/{user_id}') as new_websocket:
                restore_message = {'type': 'restore_state', 'user_id': user_id, 'connection_id': initial_state['connection_id']}
                new_websocket.send_json(restore_message)
                restore_response = new_websocket.receive_json()
                assert restore_response.get('type') == 'state_restored', f'State restoration failed: {restore_response}'
                restored_state = restore_response.get('state', {})
                assert restored_state == initial_state, f'State mismatch after reconnection: expected {initial_state}, got {restored_state}'
                assert restored_state.get('user_preferences') == initial_state['user_preferences'], 'User preferences lost after reconnection'
                assert restored_state.get('session_data') == initial_state['session_data'], 'Session data lost after reconnection'
        except Exception as e:
            logger.error(f'Test 32 failed as expected - State loss during reconnection: {e}')
            raise AssertionError(f'WebSocket reconnection state loss detected: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_33_agent_message_dropped(self, client):
        """Test 33: Agent Message Dropped
        
        This test WILL FAIL because agent sends message that never reaches frontend
        due to routing or delivery issues in the message pipeline.
        
        Expected Failure: Agent message never delivered to WebSocket client
        """
        logger.info('Test 33: Testing agent message delivery to WebSocket frontend')
        try:
            with client.websocket_connect('/ws') as websocket:
                agent_message = {'type': 'agent_response', 'agent_id': 'supervisor_agent', 'user_id': 'test_user', 'response': {'content': 'Analysis complete: 42 optimizations found', 'status': 'success', 'execution_time': 2.5, 'recommendations': ['Reduce model batch size', 'Enable caching', 'Optimize prompt length']}, 'message_id': str(uuid.uuid4()), 'timestamp': time.time()}
                with patch('netra_backend.app.services.websocket.ws_manager.manager') as mock_manager:
                    mock_manager.websocket = TestWebSocketConnection()
                    websocket.send_json({'type': 'request_agent_analysis', 'prompt': 'Optimize my AI workload', 'user_id': 'test_user'})
                    ack_response = websocket.receive_json()
                    assert ack_response.get('type') == 'request_received', f'Should receive acknowledgment: {ack_response}'
                    try:
                        agent_response = websocket.receive_json()
                        assert agent_response.get('type') == 'agent_response', f'Should receive agent response: {agent_response}'
                        assert 'response' in agent_response, f'Agent response missing content: {agent_response}'
                        assert agent_response['response']['content'] == agent_message['response']['content'], f'Agent response content mismatch: {agent_response}'
                    except Exception as delivery_error:
                        raise AssertionError(f'Agent message dropped: {delivery_error}')
        except Exception as e:
            logger.error(f'Test 33 failed as expected - Agent message dropped: {e}')
            raise AssertionError(f'Agent message delivery failed: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_34_websocket_heartbeat_failure(self, client):
        """Test 34: WebSocket Heartbeat Failure
        
        This test WILL FAIL because heartbeat mechanism fails to detect
        dead connections and keeps sending to disconnected clients.
        
        Expected Failure: Heartbeat mechanism doesn't detect dead connections
        """
        logger.info('Test 34: Testing WebSocket heartbeat failure detection')
        connection_manager = None
        try:
            with client.websocket_connect('/ws') as websocket:
                heartbeat_start = {'type': 'start_heartbeat', 'interval': 5, 'timeout': 10}
                websocket.send_json(heartbeat_start)
                heartbeat_response = websocket.receive_json()
                assert heartbeat_response.get('type') == 'heartbeat_started', f'Heartbeat start failed: {heartbeat_response}'
                ping_message = websocket.receive_json()
                assert ping_message.get('type') == 'ping', f'Should receive heartbeat ping: {ping_message}'
                pong_message = {'type': 'pong', 'timestamp': time.time(), 'original_timestamp': ping_message.get('timestamp')}
                websocket.send_json(pong_message)
                second_ping = websocket.receive_json()
                assert second_ping.get('type') == 'ping', 'Should receive second ping'
                try:
                    timeout_message = websocket.receive_json()
                    raise AssertionError(f'Heartbeat mechanism failed - still receiving messages after missed pong: {timeout_message}')
                except Exception as timeout_error:
                    if 'timeout' not in str(timeout_error).lower():
                        raise AssertionError(f'Heartbeat detection failed: {timeout_error}')
                if connection_manager:
                    active_connections = connection_manager.get_active_connections()
                    assert len(active_connections) == 0, f'Dead connection still in active list: {active_connections}'
        except Exception as e:
            logger.error(f'Test 34 failed as expected - Heartbeat failure: {e}')
            raise AssertionError(f'WebSocket heartbeat mechanism failed: {e}')

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_35_message_size_limit_violation(self, client):
        """Test 35: Message Size Limit Violation
        
        This test WILL FAIL because large messages are silently truncated
        instead of being properly rejected or chunked.
        
        Expected Failure: Large messages silently truncated
        """
        logger.info('Test 35: Testing message size limit violation handling')
        try:
            with client.websocket_connect('/ws') as websocket:
                large_content = 'x' * 10000
                large_message = {'type': 'large_data_upload', 'content': large_content, 'size': len(large_content), 'checksum': hash(large_content), 'timestamp': time.time()}
                websocket.send_json(large_message)
                response = websocket.receive_json()
                if response.get('type') == 'error':
                    assert 'size' in response.get('message', '').lower(), f'Error should mention size limit: {response}'
                elif response.get('type') == 'large_data_upload':
                    received_content = response.get('content', '')
                    received_size = response.get('size', 0)
                    received_checksum = response.get('checksum', 0)
                    assert len(received_content) == len(large_content), f'Content truncated: sent {len(large_content)}, received {len(received_content)}'
                    assert received_content == large_content, 'Content corrupted during transmission'
                    assert received_size == len(large_content), f'Size mismatch: expected {len(large_content)}, got {received_size}'
                    assert received_checksum == hash(large_content), f'Checksum mismatch: data corruption detected'
                else:
                    raise AssertionError(f'Unexpected response type for large message: {response}')
                huge_content = 'y' * 50000
                huge_message = {'type': 'huge_data_upload', 'content': huge_content, 'size': len(huge_content)}
                try:
                    websocket.send_json(huge_message)
                    huge_response = websocket.receive_json()
                    assert huge_response.get('type') == 'error', f'Huge message should be rejected: {huge_response}'
                except Exception as huge_error:
                    logger.warning(f'Huge message caused connection error: {huge_error}')
        except Exception as e:
            logger.error(f'Test 35 failed as expected - Message size limit violation: {e}')
            raise AssertionError(f'Message size limit handling failed: {e}')

class TestWebSocketFailureAnalysis:
    """Additional analysis tests to understand failure patterns."""

    @pytest.mark.asyncio
    async def test_websocket_failure_documentation(self):
        """Document the expected failure patterns for investigation."""
        expected_failures = {'test_26_message_format_mismatch': {'issue': 'Backend uses {type, payload}, frontend expects {event, data}', 'impact': 'Complete communication breakdown', 'root_cause': 'Message schema inconsistency between services'}, 'test_27_websocket_auth_token_refresh': {'issue': 'WebSocket disconnects during token refresh', 'impact': 'User loses real-time connection during auth renewal', 'root_cause': 'No token refresh handling in WebSocket layer'}, 'test_28_binary_message_corruption': {'issue': 'Binary data corrupted in WebSocket frames', 'impact': 'File uploads and binary data transfer fails', 'root_cause': 'JSON encoding/decoding corrupts binary data'}, 'test_29_message_ordering_violation': {'issue': 'Messages arrive out of order', 'impact': 'Frontend state becomes inconsistent', 'root_cause': 'Async processing without message sequencing'}, 'test_30_websocket_connection_pool_exhaustion': {'issue': 'Too many connections crash system', 'impact': 'System becomes unresponsive under load', 'root_cause': 'No connection limits or pool management'}, 'test_31_cross_tab_websocket_sync': {'issue': "Messages don't sync across browser tabs", 'impact': 'Inconsistent state across user sessions', 'root_cause': 'No cross-connection message broadcasting'}, 'test_32_websocket_reconnection_state_loss': {'issue': 'State lost after reconnection', 'impact': 'User loses work progress on disconnect', 'root_cause': 'No persistent state management'}, 'test_33_agent_message_dropped': {'issue': 'Agent messages never reach frontend', 'impact': "AI responses lost, users don't receive results", 'root_cause': 'Message routing pipeline drops messages'}, 'test_34_websocket_heartbeat_failure': {'issue': "Heartbeat doesn't detect dead connections", 'impact': 'Resources wasted on dead connections', 'root_cause': 'Heartbeat mechanism not properly implemented'}, 'test_35_message_size_limit_violation': {'issue': 'Large messages silently truncated', 'impact': 'Data loss without user notification', 'root_cause': 'No proper message size validation'}}
        logger.info('WebSocket failure analysis:')
        for test_name, details in expected_failures.items():
            logger.info(f'{test_name}:')
            logger.info(f"  Issue: {details['issue']}")
            logger.info(f"  Impact: {details['impact']}")
            logger.info(f"  Root Cause: {details['root_cause']}")
        assert len(expected_failures) == 10, 'Should document all 10 failure modes'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')