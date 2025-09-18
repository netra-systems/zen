"""Empty docstring."""
Integration Tests: WebSocket Error Handling & Reconnection Patterns

Business Value Justification (BVJ):
    - Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain real-time communication continuity during network failures
- Value Impact: WebSocket resilience ensures uninterrupted AI chat and real-time updates
- Strategic Impact: Foundation for reliable real-time AI service delivery and user engagement

This test suite validates WebSocket error handling patterns with real services:
    - Connection failure detection and automatic reconnection with PostgreSQL logging
- Message queue persistence during disconnection with Redis buffering
- Graceful connection degradation and recovery patterns
- Concurrent user WebSocket isolation during failures
- Authentication re-establishment after reconnection
- Event replay and state synchronization after connection recovery

CRITICAL: Uses REAL PostgreSQL, Redis, and WebSocket connections - NO MOCKS for integration testing.
Tests validate actual WebSocket behavior, reconnection timing, and message integrity.
"""Empty docstring."""
import asyncio
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
import pytest
import websockets
from websockets import ConnectionClosed, InvalidStatusCode, InvalidHandshake
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class WebSocketState(Enum):
    "WebSocket connection state levels."""
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    RECONNECTING = 'reconnecting'
    FAILED = 'failed'
    AUTHENTICATION_PENDING = 'authentication_pending'

class WebSocketMessage:
    "Represents a WebSocket message with metadata."

    def __init__(self, message_type: str, data: Dict[str, Any], user_id: str=None):
        self.id = str(uuid.uuid4())
        self.type = message_type
        self.data = data
        self.user_id = user_id
        self.timestamp = datetime.now(timezone.utc)
        self.delivery_attempts = 0
        self.delivered = False

    def to_dict(self) -> Dict[str, Any]:
        "Convert message to dictionary for transmission."
        return {'id': self.id, 'type': self.type, 'data': self.data, 'timestamp': self.timestamp.isoformat(), 'user_id': self.user_id}

    def to_json(self) -> str:
        Convert message to JSON string.""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        Create message from JSON string.""
        data = json.loads(json_str)
        msg = cls(data['type'], data['data'], data.get('user_id'))
        msg.id = data['id']
        msg.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+0:0'))
        return msg

class ReconnectingWebSocketClient:
    "WebSocket client with automatic reconnection and message persistence."""

    def __init__(self, url: str, auth_token: str, user_id: str, max_reconnect_attempts: int=5, reconnect_delay: float=1.0):
        self.url = url
        self.auth_token = auth_token
        self.user_id = user_id
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.state = WebSocketState.DISCONNECTED
        self.websocket = None
        self.reconnect_attempts = 0
        self.last_heartbeat = None
        self.connection_id = None
        self.message_queue = []
        self.pending_messages = {}
        self.received_messages = []
        self.message_handlers = {}
        self.connection_attempts = 0
        self.successful_connections = 0
        self.connection_failures = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.reconnection_events = []
        self.on_connected = None
        self.on_disconnected = None
        self.on_message = None
        self.on_reconnect_attempt = None

    async def connect(self) -> bool:
        ""Establish WebSocket connection with authentication.""

        self.connection_attempts += 1
        connect_start = time.time()
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}', 'X-User-ID': self.user_id, 'X-Test-Mode': 'true'}
            self.websocket = await websockets.connect(self.url, additional_headers=headers, ping_interval=20, ping_timeout=10, close_timeout=5)
            self.state = WebSocketState.AUTHENTICATION_PENDING
            self.connection_id = str(uuid.uuid4())
            auth_message = WebSocketMessage('authenticate', {'token': self.auth_token, 'user_id': self.user_id, 'connection_id': self.connection_id}, self.user_id)
            await self.websocket.send(auth_message.to_json())
            auth_response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_response)
            if auth_data.get('type') == 'authentication_success':
                self.state = WebSocketState.CONNECTED
                self.successful_connections += 1
                self.reconnect_attempts = 0
                self.last_heartbeat = time.time()
                connection_duration = time.time() - connect_start
                self.reconnection_events.append({'event': 'connection_established', 'timestamp': datetime.now(timezone.utc), 'duration_ms': connection_duration * 1000, 'attempt': self.connection_attempts, 'connection_id': self.connection_id}
                if self.on_connected:
                    await self.on_connected(self.connection_id)
                asyncio.create_task(self._message_handler())
                asyncio.create_task(self._heartbeat_handler())
                await self._send_queued_messages()
                return True
            else:
                raise Exception(f'Authentication failed: {auth_data}')
        except Exception as e:
            self.connection_failures += 1
            self.state = WebSocketState.FAILED
            connection_duration = time.time() - connect_start
            self.reconnection_events.append({'event': 'connection_failed', 'timestamp': datetime.now(timezone.utc), 'duration_ms': connection_duration * 1000, 'attempt': self.connection_attempts, 'error': str(e)}
            logger.warning(f'WebSocket connection failed: {e}')
            return False

    async def send_message(self, message_type: str, data: Dict[str, Any) -> bool:
        Send message with delivery confirmation and queuing.""
        message = WebSocketMessage(message_type, data, self.user_id)
        if self.state == WebSocketState.CONNECTED and self.websocket:
            try:
                await self.websocket.send(message.to_json())
                self.messages_sent += 1
                self.pending_messages[message.id] = message
                message.delivery_attempts += 1
                return True
            except Exception as e:
                logger.warning(f'Failed to send message: {e}')
                self.message_queue.append(message)
                await self._handle_connection_loss()
                return False
        else:
            self.message_queue.append(message)
            return False

    async def disconnect(self):
        Gracefully disconnect WebSocket.""
        if self.websocket:
            self.state = WebSocketState.DISCONNECTED
            await self.websocket.close()
            self.websocket = None
            if self.on_disconnected:
                await self.on_disconnected('graceful_disconnect')

    async def force_disconnect(self):
        Simulate network failure by forcefully closing connection.""
        if self.websocket:
            self.state = WebSocketState.DISCONNECTED
            self.websocket.transport.close()
            self.websocket = None
            await self._handle_connection_loss()

    async def _message_handler(self):
        "Handle incoming WebSocket messages."""
        try:
            async for raw_message in self.websocket:
                try:
                    message_data = json.loads(raw_message)
                    message = WebSocketMessage.from_json(raw_message)
                    self.messages_received += 1
                    self.received_messages.append(message)
                    self.last_heartbeat = time.time()
                    if message.type == 'delivery_confirmation':
                        message_id = message.data.get('message_id')
                        if message_id in self.pending_messages:
                            self.pending_messages[message_id].delivered = True
                            del self.pending_messages[message_id]
                    elif message.type == 'heartbeat':
                        heartbeat_response = WebSocketMessage('heartbeat_response', {'timestamp': datetime.now(timezone.utc).isoformat()}, self.user_id)
                        await self.websocket.send(heartbeat_response.to_json())
                    else:
                        if self.on_message:
                            await self.on_message(message)
                        if message.type in self.message_handlers:
                            await self.message_handlers[message.type](message)
                except json.JSONDecodeError:
                    logger.warning(f'Received invalid JSON message: {raw_message}')
                except Exception as e:
                    logger.error(f'Error handling message: {e}')
        except ConnectionClosed:
            await self._handle_connection_loss()
        except Exception as e:
            logger.error(f'Message handler error: {e}')
            await self._handle_connection_loss()

    async def _heartbeat_handler(self):
        "Monitor connection health with heartbeats."
        while self.state == WebSocketState.CONNECTED:
            try:
                await asyncio.sleep(30)
                if self.last_heartbeat and time.time() - self.last_heartbeat > 60:
                    logger.warning('Heartbeat timeout - connection appears dead')
                    await self._handle_connection_loss()
                    break
            except Exception as e:
                logger.error(f'Heartbeat handler error: {e}')
                break

    async def _handle_connection_loss(self):
        "Handle connection loss and attempt reconnection."
        if self.state == WebSocketState.RECONNECTING:
            return
        self.state = WebSocketState.DISCONNECTED
        self.reconnection_events.append({'event': 'connection_lost', 'timestamp': datetime.now(timezone.utc), 'reconnect_attempts': self.reconnect_attempts}
        if self.on_disconnected:
            await self.on_disconnected('connection_lost')
        await self._attempt_reconnection()

    async def _attempt_reconnection(self):
        Attempt to reconnect with exponential backoff.""
        self.state = WebSocketState.RECONNECTING
        while self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            if self.on_reconnect_attempt:
                await self.on_reconnect_attempt(self.reconnect_attempts)
            self.reconnection_events.append({'event': 'reconnection_attempt', 'timestamp': datetime.now(timezone.utc), 'attempt': self.reconnect_attempts}
            delay = self.reconnect_delay * 2 ** (self.reconnect_attempts - 1)
            delay = min(delay, 30)
            logger.info(f'Attempting reconnection #{self.reconnect_attempts} after {delay:."1f"}s')""

            await asyncio.sleep(delay)
            if await self.connect():
                logger.info(f'Reconnection successful after {self.reconnect_attempts} attempts')
                return True
        self.state = WebSocketState.FAILED
        self.reconnection_events.append({'event': 'reconnection_failed', 'timestamp': datetime.now(timezone.utc), 'total_attempts': self.reconnect_attempts}
        logger.error('All reconnection attempts failed')
        return False

    async def _send_queued_messages(self):
        Send all queued messages after reconnection.""
        if not self.message_queue:
            return
        queued_count = len(self.message_queue)
        successful_sends = 0
        for message in self.message_queue.copy():
            try:
                await self.websocket.send(message.to_json())
                self.messages_sent += 1
                self.pending_messages[message.id] = message
                message.delivery_attempts += 1
                successful_sends += 1
                self.message_queue.remove(message)
            except Exception as e:
                logger.warning(f'Failed to send queued message: {e}')
                message.delivery_attempts += 1
                if message.delivery_attempts >= 3:
                    self.message_queue.remove(message)
                    logger.error(f'Dropping message after {message.delivery_attempts} attempts')
        logger.info(f'Sent {successful_sends}/{queued_count} queued messages after reconnection')

    def get_connection_stats(self) -> Dict[str, Any]:
        "Get comprehensive connection statistics."""
        return {'current_state': self.state.value, 'connection_attempts': self.connection_attempts, 'successful_connections': self.successful_connections, 'connection_failures': self.connection_failures, 'reconnect_attempts': self.reconnect_attempts, 'messages_sent': self.messages_sent, 'messages_received': self.messages_received, 'queued_messages': len(self.message_queue), 'pending_messages': len(self.pending_messages), 'connection_success_rate': self.successful_connections / max(self.connection_attempts, 1), 'reconnection_events_count': len(self.reconnection_events), 'connection_id': self.connection_id}

class WebSocketErrorHandlingTests(BaseIntegrationTest):
    ""Integration tests for WebSocket error handling and reconnection patterns.""


    def setup_method(self):
        Set up test environment.""
        super().setup_method()
        self.env = get_env()
        self.env.set('TEST_MODE', 'true', source='test')
        self.env.set('USE_REAL_SERVICES', 'true', source='test')
        self.auth_helper = E2EAuthHelper()
        self.websocket_url = 'ws://localhost:8000/ws'

    @pytest.fixture
    async def authenticated_websocket_client(self):
        Create authenticated WebSocket client for testing.""
        user_context = await create_authenticated_user_context(user_email='websocket_test@example.com', user_id='websocket_test_user', environment='test')
        client = ReconnectingWebSocketClient(url=self.websocket_url, auth_token=user_context.agent_context.get('jwt_token'), user_id=str(user_context.user_id), max_reconnect_attempts=3, reconnect_delay=0.5)
        return (client, user_context)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_and_authentication(self, real_services_fixture, authenticated_websocket_client):
        Test WebSocket connection establishment and authentication.""
        client, user_context = authenticated_websocket_client
        postgres = real_services_fixture['postgres']
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS websocket_connections (\n                id SERIAL PRIMARY KEY,\n                user_id TEXT NOT NULL,\n                connection_id TEXT,\n                event_type TEXT NOT NULL,\n                timestamp TIMESTAMP DEFAULT NOW(),\n                duration_ms DECIMAL,\n                success BOOLEAN\n            )\n        ')
        try:
            connection_start = time.time()
            connection_successful = await client.connect()
            connection_duration = time.time() - connection_start
            await postgres.execute(\n                INSERT INTO websocket_connections (user_id, connection_id, event_type, duration_ms, success)\n                VALUES ($1, $2, 'connection_attempt', $3, $4)\n            ", str(user_context.user_id), client.connection_id, connection_duration * 1000, connection_successful)"
            assert connection_successful is True
            assert client.state == WebSocketState.CONNECTED
            assert client.connection_id is not None
            assert client.successful_connections == 1
            test_message_sent = await client.send_message('test_message', {'content': 'Hello WebSocket', 'test_type': 'authentication_test')
            assert test_message_sent is True
            assert client.messages_sent == 1
            await asyncio.sleep(0.1)
            stats = client.get_connection_stats()
            assert stats['current_state'] == 'connected'
            assert stats['connection_success_rate'] == 1.0
            assert stats['messages_sent'] >= 1
            await client.disconnect()
            assert client.state == WebSocketState.DISCONNECTED
            await postgres.execute(\n                INSERT INTO websocket_connections (user_id, connection_id, event_type, success)\n                VALUES ($1, $2, 'graceful_disconnect', true)\n            , str(user_context.user_id), client.connection_id)
        finally:
            await postgres.execute('DROP TABLE IF EXISTS websocket_connections')
        logger.info(' PASS:  WebSocket connection and authentication test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_automatic_reconnection_after_network_failure(self, real_services_fixture, authenticated_websocket_client):
        ""Test automatic reconnection after simulated network failure.""

        client, user_context = authenticated_websocket_client
        redis = real_services_fixture['redis']
        reconnection_events = []

        async def track_reconnection_event(event_type, data=None):
            event = {'event_type': event_type, 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': data or {}}
            reconnection_events.append(event)
            await redis.set_json(f'reconnection_event:{len(reconnection_events)}', event, ex=300)
        client.on_connected = lambda conn_id: track_reconnection_event('connected', {'connection_id': conn_id)
        client.on_disconnected = lambda reason: track_reconnection_event('disconnected', {'reason': reason)
        client.on_reconnect_attempt = lambda attempt: track_reconnection_event('reconnect_attempt', {'attempt': attempt)
        initial_connection = await client.connect()
        assert initial_connection is True
        initial_connection_id = client.connection_id
        initial_stats = client.get_connection_stats()
        pre_disconnect_messages = []
        for i in range(3):
            message_sent = await client.send_message('pre_disconnect_message', {'message_index': i, 'content': f'Message before disconnect {i)')
            assert message_sent is True
            pre_disconnect_messages.append(f'pre_disconnect_message_{i}')
        await client.force_disconnect()
        assert client.state in [WebSocketState.DISCONNECTED, "WebSocketState.RECONNECTING]"
        disconnected_messages = []
        for i in range(2):
            message_queued = await client.send_message('disconnected_message', {'message_index': i, 'content': f'Message while disconnected {i)')
            assert message_queued is False
            disconnected_messages.append(f'disconnected_message_{i}')
        assert len(client.message_queue) >= 2
        reconnection_timeout = 15
        start_wait = time.time()
        while client.state != WebSocketState.CONNECTED and time.time() - start_wait < reconnection_timeout:
            await asyncio.sleep(0.1)
        assert client.state == WebSocketState.CONNECTED
        assert client.connection_id != initial_connection_id
        assert client.successful_connections == 2
        await asyncio.sleep(1.0)
        assert len(client.message_queue) == 0
        assert client.messages_sent >= 5
        assert len(reconnection_events) >= 3
        event_types = [event['event_type'] for event in reconnection_events]
        assert 'disconnected' in event_types
        assert 'reconnect_attempt' in event_types
        assert event_types.count('connected') >= 2
        post_reconnect_message = await client.send_message('post_reconnect_test', {'content': 'Message after reconnection', 'test_validation': True)
        assert post_reconnect_message is True
        final_stats = client.get_connection_stats()
        await redis.set_json('reconnection_test_stats', final_stats, ex=300)
        assert final_stats['connection_success_rate'] >= 0.5
        assert final_stats['reconnect_attempts'] <= client.max_reconnect_attempts
        assert final_stats['messages_sent'] >= 6
        await client.disconnect()
        logger.info(' PASS:  Automatic reconnection after network failure test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_persistence_and_replay_after_reconnection(self, real_services_fixture, authenticated_websocket_client):
        Test message persistence and replay after connection recovery.""
        client, user_context = authenticated_websocket_client
        postgres = real_services_fixture['postgres']
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS websocket_message_log (\n                id SERIAL PRIMARY KEY,\n                user_id TEXT NOT NULL,\n                message_id TEXT NOT NULL,\n                message_type TEXT NOT NULL,\n                message_data JSONB NOT NULL,\n                sent_timestamp TIMESTAMP,\n                delivered_timestamp TIMESTAMP,\n                delivery_attempts INTEGER DEFAULT 0,\n                connection_id TEXT\n            )\n        ')
        try:
            await client.connect()
            original_connection_id = client.connection_id

            async def log_message_to_db(message: WebSocketMessage):
                await postgres.execute('\n                    INSERT INTO websocket_message_log \n                    (user_id, message_id, message_type, message_data, sent_timestamp, connection_id)\n                    VALUES ($1, $2, $3, $4, $5, $6)\n                ', str(user_context.user_id), message.id, message.type, json.dumps(message.data), message.timestamp, client.connection_id)
            critical_messages = [{'type': 'user_action', 'data': {'action': 'start_analysis', 'priority': 'high'}}, {'type': 'ai_request', 'data': {'query': 'Analyze cost optimization', 'session_id': 'test_session'}}, {'type': 'data_update', 'data': {'entity': 'user_preferences', 'changes': {'theme': 'dark'}}}]
            sent_message_ids = []
            for i, msg_data in enumerate(critical_messages):
                message = WebSocketMessage(msg_data['type'], msg_data['data'], str(user_context.user_id))
                await log_message_to_db(message)
                sent_message_ids.append(message.id)
                success = await client.send_message(msg_data['type'), msg_data['data')
                assert success is True
                await postgres.execute('\n                    UPDATE websocket_message_log \n                    SET delivery_attempts = delivery_attempts + 1 \n                    WHERE message_id = $1\n                ', message.id)
            assert client.messages_sent >= len(critical_messages)
            await client.force_disconnect()
            queued_messages = [{'type': 'offline_action', 'data': {'action': 'queue_update', 'priority': 'medium'}}, {'type': 'background_sync', 'data': {'sync_type': 'preferences', 'urgent': False}}]
            queued_message_ids = []
            for msg_data in queued_messages:
                message = WebSocketMessage(msg_data['type'], msg_data['data'], str(user_context.user_id))
                await log_message_to_db(message)
                queued_message_ids.append(message.id)
                await client.send_message(msg_data['type'), msg_data['data')
            assert len(client.message_queue) >= len(queued_messages)
            reconnection_timeout = 10
            start_wait = time.time()
            while client.state != WebSocketState.CONNECTED and time.time() - start_wait < reconnection_timeout:
                await asyncio.sleep(0.1)
            assert client.state == WebSocketState.CONNECTED
            new_connection_id = client.connection_id
            assert new_connection_id != original_connection_id
            await asyncio.sleep(2.0)
            assert len(client.message_queue) == 0
            for message_id in queued_message_ids:
                await postgres.execute('\n                    UPDATE websocket_message_log \n                    SET delivered_timestamp = NOW(), connection_id = $2\n                    WHERE message_id = $1\n                ', message_id, new_connection_id)
            all_message_ids = sent_message_ids + queued_message_ids
            logged_messages = await postgres.fetch('\n                SELECT message_id, message_type, delivery_attempts, delivered_timestamp\n                FROM websocket_message_log \n                WHERE user_id = $1 \n                ORDER BY sent_timestamp\n            ', str(user_context.user_id))
            assert len(logged_messages) >= len(all_message_ids)
            for record in logged_messages:
                assert record['delivery_attempts'] >= 1
            post_reconnect_message = WebSocketMessage('reconnection_test', {'test': 'post_reconnection', 'timestamp': datetime.now(timezone.utc).isoformat()}, str(user_context.user_id))
            await log_message_to_db(post_reconnect_message)
            success = await client.send_message('reconnection_test', post_reconnect_message.data)
            assert success is True
            await postgres.execute('\n                UPDATE websocket_message_log \n                SET delivered_timestamp = NOW(), delivery_attempts = 1 \n                WHERE message_id = $1\n            ', post_reconnect_message.id)
            message_stats = await postgres.fetchrow('\n                SELECT \n                    COUNT(*) as total_messages,\n                    COUNT(CASE WHEN delivered_timestamp IS NOT NULL THEN 1 END) as delivered_messages,\n                    AVG(delivery_attempts) as avg_delivery_attempts,\n                    COUNT(DISTINCT connection_id) as unique_connections\n                FROM websocket_message_log \n                WHERE user_id = $1\n            ', str(user_context.user_id))
            delivery_rate = message_stats['delivered_messages'] / message_stats['total_messages']
            assert delivery_rate >= 0.8
            assert message_stats['unique_connections'] >= 2
            assert message_stats['avg_delivery_attempts'] <= 2
        finally:
            await postgres.execute('DROP TABLE IF EXISTS websocket_message_log')
            await client.disconnect()
        logger.info(' PASS:  Message persistence and replay after reconnection test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_connection_isolation(self, real_services_fixture):
        Test WebSocket connection isolation between concurrent users.""
        redis = real_services_fixture['redis']
        user_count = 4
        websocket_clients = []
        user_contexts = []
        for i in range(user_count):
            user_context = await create_authenticated_user_context(user_email=f'concurrent_ws_test_{i}@example.com', user_id=f'concurrent_ws_user_{i}', environment='test')
            user_contexts.append(user_context)
            client = ReconnectingWebSocketClient(url=self.websocket_url, auth_token=user_context.agent_context.get('jwt_token'), user_id=str(user_context.user_id), max_reconnect_attempts=2, reconnect_delay=0.2)
            websocket_clients.append(client)
        try:
            connection_tasks = [client.connect() for client in websocket_clients]
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            successful_connections = sum((1 for result in connection_results if result is True))
            assert successful_connections >= user_count - 1

            async def send_user_messages(client, user_index, message_count):
                Send messages from specific user.""
                sent_messages = []
                for i in range(message_count):
                    message_data = {'user_index': user_index, 'message_index': i, 'content': f'User {user_index} message {i}', 'timestamp': datetime.now(timezone.utc).isoformat(), 'private_data': f'secret_data_user_{user_index}_{i}'}
                    success = await client.send_message('user_message', message_data)
                    if success:
                        sent_messages.append(message_data)
                    await redis.set_json(f'user_message:{user_index}:{i}', message_data, ex=300)
                    await asyncio.sleep(0.1)
                return sent_messages
            message_tasks = [send_user_messages(client, i, 5) for i, client in enumerate(websocket_clients) if client.state == WebSocketState.CONNECTED]
            user_message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            for user_index, messages in enumerate(user_message_results):
                if isinstance(messages, list):
                    assert len(messages) >= 3
                    for message in messages:
                        assert message['user_index'] == user_index
                        assert f'secret_data_user_{user_index}' in message['private_data']
            victim_client = websocket_clients[0]
            victim_user_index = 0
            await victim_client.force_disconnect()
            await asyncio.sleep(0.5)
            remaining_active_connections = sum((1 for i, client in enumerate(websocket_clients) if i != victim_user_index and client.state == WebSocketState.CONNECTED))
            assert remaining_active_connections >= user_count - 2
            post_failure_tasks = [send_user_messages(client, i, 2) for i, client in enumerate(websocket_clients) if i != victim_user_index and client.state == WebSocketState.CONNECTED]
            if post_failure_tasks:
                post_failure_results = await asyncio.gather(*post_failure_tasks, return_exceptions=True)
                successful_post_failure = sum((1 for result in post_failure_results if isinstance(result, list) and len(result) > 0))
                assert successful_post_failure >= 1
            victim_reconnection = await victim_client.connect()
            if victim_reconnection:
                reconnect_message = await send_user_messages(victim_client, victim_user_index, 1)
                assert len(reconnect_message) >= 1
            isolation_stats = {}
            for i, client in enumerate(websocket_clients):
                stats = client.get_connection_stats()
                isolation_stats[f'user_{i}'] = {'final_state': stats['current_state'], 'messages_sent': stats['messages_sent'], 'connection_success_rate': stats['connection_success_rate'], 'reconnection_events': stats['reconnection_events_count']}
            await redis.set_json('websocket_isolation_test_results', isolation_stats, ex=600)
            total_messages_sent = sum((stats['messages_sent'] for stats in isolation_stats.values()))
            assert total_messages_sent >= user_count * 3
        finally:
            cleanup_tasks = [client.disconnect() for client in websocket_clients]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        logger.info(' PASS:  Concurrent WebSocket connection isolation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_recovery_with_authentication_renewal(self, real_services_fixture, authenticated_websocket_client):
        "Test WebSocket recovery with authentication token renewal."""
        client, user_context = authenticated_websocket_client
        postgres = real_services_fixture['postgres']
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS auth_renewal_log (\n                id SERIAL PRIMARY KEY,\n                user_id TEXT NOT NULL,\n                old_token_hash TEXT,\n                new_token_hash TEXT,\n                renewal_reason TEXT,\n                success BOOLEAN,\n                timestamp TIMESTAMP DEFAULT NOW()\n            )\n        ')
        try:
            initial_connection = await client.connect()
            assert initial_connection is True
            original_token = client.auth_token
            original_token_hash = hash(original_token)
            for i in range(3):
                await client.send_message('pre_renewal_message', {'index': i, 'auth_generation': 'original')
            original_messages_sent = client.messages_sent
            new_user_context = await create_authenticated_user_context(user_email=user_context.agent_context['user_email'], user_id=str(user_context.user_id), environment='test')
            new_token = new_user_context.agent_context.get('jwt_token')
            new_token_hash = hash(new_token)
            await postgres.execute("\n                INSERT INTO auth_renewal_log (user_id, old_token_hash, new_token_hash, renewal_reason)\n                VALUES ($1, $2, $3, 'token_expiration_simulation')\n            , str(user_context.user_id), str(original_token_hash), str(new_token_hash))"
            client.auth_token = new_token
            await client.force_disconnect()
            reconnection_timeout = 10
            start_wait = time.time()
            while client.state != WebSocketState.CONNECTED and time.time() - start_wait < reconnection_timeout:
                await asyncio.sleep(0.1)
            if client.state == WebSocketState.CONNECTED:
                await postgres.execute('\n                    UPDATE auth_renewal_log \n                    SET success = true \n                    WHERE user_id = $1 AND new_token_hash = $2\n                ', str(user_context.user_id), str(new_token_hash))
                post_renewal_messages = []
                for i in range(3):
                    success = await client.send_message('post_renewal_message', {'index': i, 'auth_generation': 'renewed', 'renewal_verified': True)
                    if success:
                        post_renewal_messages.append(i)
                assert len(post_renewal_messages) >= 2
                assert client.messages_sent > original_messages_sent
                stable_connection_test = True
                for i in range(5):
                    test_message = await client.send_message('stability_test', {'test_index': i, 'stability_check': True)
                    if not test_message:
                        stable_connection_test = False
                        break
                    await asyncio.sleep(0.1)
                assert stable_connection_test is True
            else:
                await postgres.execute('\n                    UPDATE auth_renewal_log \n                    SET success = false \n                    WHERE user_id = $1 AND new_token_hash = $2\n                ', str(user_context.user_id), str(new_token_hash))
                assert client.reconnect_attempts > 0
            for renewal_round in range(2):
                another_context = await create_authenticated_user_context(user_email=user_context.agent_context['user_email'], user_id=str(user_context.user_id), environment='test')
                another_token = another_context.agent_context.get('jwt_token')
                another_hash = hash(another_token)
                await postgres.execute('\n                    INSERT INTO auth_renewal_log (user_id, old_token_hash, new_token_hash, renewal_reason)\n                    VALUES ($1, $2, $3, $4)\n                ', str(user_context.user_id), str(new_token_hash), str(another_hash), f'periodic_renewal_round_{renewal_round}')
                client.auth_token = another_token
                new_token_hash = another_hash
                renewal_test = await client.send_message('renewal_test', {'renewal_round': renewal_round, 'token_generation': f'renewal_{renewal_round)')
                await asyncio.sleep(0.2)
            renewal_summary = await postgres.fetchrow('\n                SELECT \n                    COUNT(*) as total_renewals,\n                    COUNT(CASE WHEN success = true THEN 1 END) as successful_renewals,\n                    COUNT(DISTINCT new_token_hash) as unique_tokens\n                FROM auth_renewal_log \n                WHERE user_id = $1\n            ', str(user_context.user_id))
            renewal_success_rate = renewal_summary['successful_renewals'] / renewal_summary['total_renewals']
            assert renewal_summary['total_renewals'] >= 3
            assert renewal_summary['unique_tokens'] >= 3
            final_stats = client.get_connection_stats()
            auth_renewal_results = {'renewal_summary': dict(renewal_summary), 'final_connection_stats': final_stats, 'renewal_success_rate': renewal_success_rate, 'total_messages_with_renewals': final_stats['messages_sent']}
            await postgres.execute(\n                INSERT INTO auth_renewal_log (user_id, renewal_reason, success)\n                VALUES ($1, 'test_completion_summary', true)\n            ", str(user_context.user_id))"
        finally:
            await postgres.execute('DROP TABLE IF EXISTS auth_renewal_log')
            await client.disconnect()
        logger.info(' PASS:  WebSocket error recovery with authentication renewal test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
""""

)))))))))))))))))))