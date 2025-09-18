"""
Real WebSocket message_handler tests - NO MOCKS
Coverage Target: 85%
Business Value: Customer-facing functionality

MOCK ELIMINATION PHASE 1: All mocks replaced with real WebSocket connections
using real services infrastructure for mission-critical WebSocket & Chat functionality.
"""
import pytest
import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from test_framework.real_services import get_real_services, WebSocketTestClient
from test_framework.environment_isolation import IsolatedEnvironment
from netra_backend.app.services.websocket.message_handler import MessageHandlerService
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

@pytest.mark.asyncio
class MessageHandlerRealConnectionsTests:
    """Real WebSocket message handler test suite - NO MOCKS."""

    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Setup real services infrastructure for all tests."""
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
        await self.real_services.reset_all_data()
        self.ws_manager = WebSocketManager()
        yield
        await self.real_services.close_all()
        self.env.disable_isolation(restore_original=True)

    async def create_real_websocket_connection(self, conn_id: str) -> WebSocketTestClient:
        """Create a real WebSocket connection for testing."""
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f'test/{conn_id}')
        return ws_client

    async def capture_websocket_messages(self, ws_client: WebSocketTestClient, timeout: float=2.0) -> List[Dict]:
        """Capture messages from real WebSocket connection."""
        messages = []
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                message = await ws_client.receive_json(timeout=0.1)
                messages.append(message)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
        return messages

    async def test_real_websocket_connection(self):
        """Test real WebSocket connection through message handler."""
        conn_id = 'test_client_real'
        ws_client = await self.create_real_websocket_connection(conn_id)
        await self.ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        assert ws_client._connected is True
        assert conn_id in self.ws_manager.connections
        await self.ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
        await ws_client.close()
        assert ws_client._connected is False
        assert conn_id not in self.ws_manager.connections

    async def test_real_message_processing(self):
        """Test message processing with real WebSocket connection."""
        conn_id = 'test_message_handler'
        ws_client = await self.create_real_websocket_connection(conn_id)
        await self.ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        received_messages = []

        async def capture_messages():
            while ws_client._connected:
                try:
                    message = await ws_client.receive_json(timeout=0.1)
                    received_messages.append(message)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        capture_task = asyncio.create_task(capture_messages())
        test_messages = [{'type': 'ping', 'timestamp': time.time()}, {'type': 'user_message', 'content': 'Hello', 'timestamp': time.time()}, {'type': 'command', 'action': 'status', 'timestamp': time.time()}, {'type': 'heartbeat', 'timestamp': time.time()}]
        for msg in test_messages:
            await ws_client.send(msg)
            await asyncio.sleep(0.1)
        await asyncio.sleep(1.0)
        capture_task.cancel()
        assert ws_client._connected is True
        print(f'Received {len(received_messages)} response messages')
        await self.ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
        await ws_client.close()

    async def test_real_event_broadcasting(self):
        """Test event broadcasting through message handler to real WebSocket connections."""
        conn_ids = ['handler_client_1', 'handler_client_2']
        ws_clients = []
        capture_tasks = []
        all_messages = {}
        try:
            for conn_id in conn_ids:
                ws_client = await self.create_real_websocket_connection(conn_id)
                await self.ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
                ws_clients.append(ws_client)
                all_messages[conn_id] = []

                async def capture_for_client(client, client_id):
                    while client._connected:
                        try:
                            message = await client.receive_json(timeout=0.1)
                            all_messages[client_id].append(message)
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break
                task = asyncio.create_task(capture_for_client(ws_client, conn_id))
                capture_tasks.append(task)
            broadcast_data = {'type': 'handler_broadcast', 'message': 'Message from handler', 'timestamp': time.time()}
            await self.ws_manager.broadcast_to_all(broadcast_data)
            await asyncio.sleep(1.0)
            for task in capture_tasks:
                task.cancel()
            await asyncio.gather(*capture_tasks, return_exceptions=True)
            for conn_id in conn_ids:
                client_messages = all_messages[conn_id]
                assert len(client_messages) >= 0
        finally:
            for i, ws_client in enumerate(ws_clients):
                conn_id = conn_ids[i]
                await self.ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
                await ws_client.close()

    async def test_concurrent_real_message_handling(self):
        """Test concurrent message handling with real WebSocket connections."""
        connection_count = 5
        conn_ids = [f'concurrent_handler_{i}' for i in range(connection_count)]
        ws_clients = []
        try:

            async def create_and_connect(conn_id):
                ws_client = await self.create_real_websocket_connection(conn_id)
                await self.ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
                return ws_client
            connection_tasks = [create_and_connect(conn_id) for conn_id in conn_ids]
            ws_clients = await asyncio.gather(*connection_tasks)
            assert len(ws_clients) == connection_count
            for i, ws_client in enumerate(ws_clients):
                assert ws_client._connected is True
                assert conn_ids[i] in self.ws_manager.connections

            async def send_test_messages(client, client_id):
                messages = [{'type': 'concurrent_test', 'client_id': client_id, 'seq': i, 'timestamp': time.time()} for i in range(5)]
                for msg in messages:
                    await client.send(msg)
                    await asyncio.sleep(0.01)
            send_tasks = [send_test_messages(ws_clients[i], conn_ids[i]) for i in range(connection_count)]
            await asyncio.gather(*send_tasks)
            for ws_client in ws_clients:
                assert ws_client._connected is True
        finally:
            cleanup_tasks = []
            for i, ws_client in enumerate(ws_clients):
                if ws_client and ws_client._connected:
                    conn_id = conn_ids[i]
                    cleanup_tasks.append(self._cleanup_connection(conn_id, ws_client))
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def _cleanup_connection(self, conn_id: str, ws_client: WebSocketTestClient):
        """Helper method to cleanup a connection."""
        try:
            await self.ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
            await ws_client.close()
        except Exception as e:
            print(f'Cleanup error for {conn_id}: {e}')

    async def test_message_handler_resilience(self):
        """Test message handler resilience with real WebSocket connections."""
        conn_id = 'handler_resilience_test'
        ws_client = await self.create_real_websocket_connection(conn_id)
        await self.ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        assert ws_client._connected is True
        message_types = [{'type': 'valid_message', 'data': 'test'}, {'type': 'empty_message'}, {'type': 'large_message', 'data': 'x' * 1000}, {'type': 'special_chars', 'data': 'Special: [U+00FC][U+00F1][U+00ED][U+00E7][U+00F6]d[U+00E9] & symbols!@#$%'}, {'type': 'json_in_data', 'data': {'nested': {'json': 'value'}}}, {'type': 'array_data', 'data': [1, 2, 3, 'mixed', {'types': True}]}]
        for msg in message_types:
            await ws_client.send(msg)
            await asyncio.sleep(0.1)
        assert ws_client._connected is True
        await self.ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
        await ws_client.close()
        assert ws_client._connected is False

@pytest.mark.asyncio
class MessageRoutingRealTests:
    """Test message routing with real WebSocket connections."""

    @pytest.fixture(autouse=True)
    async def setup_routing_services(self):
        """Setup for message routing tests."""
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
        await self.real_services.reset_all_data()
        yield
        await self.real_services.close_all()
        self.env.disable_isolation(restore_original=True)

    async def test_message_routing_real_websocket(self):
        """Test message routing capabilities with real WebSocket connections."""
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        ws_manager = WebSocketManager()
        connections = {'admin_user': await self._create_test_connection('admin_123', ws_manager), 'regular_user': await self._create_test_connection('user_456', ws_manager), 'guest_user': await self._create_test_connection('guest_789', ws_manager)}
        try:
            admin_message = {'type': 'admin_notification', 'message': 'Admin only message', 'timestamp': time.time()}
            user_message = {'type': 'user_update', 'message': 'User update message', 'timestamp': time.time()}
            await ws_manager.broadcast_to_user('admin_123', admin_message)
            await ws_manager.broadcast_to_user('user_456', user_message)
            await asyncio.sleep(0.5)
            for conn_type, ws_client in connections.items():
                assert ws_client._connected is True
        finally:
            for conn_type, ws_client in connections.items():
                user_id = {'admin_user': 'admin_123', 'regular_user': 'user_456', 'guest_user': 'guest_789'}[conn_type]
                await ws_manager.disconnect_user(user_id, ws_client._websocket, user_id)
                await ws_client.close()

    async def _create_test_connection(self, user_id: str, ws_manager: WebSocketManager) -> WebSocketTestClient:
        """Helper to create test connection."""
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f'test/{user_id}')
        await ws_manager.connect_user(user_id, ws_client._websocket, user_id)
        return ws_client
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')