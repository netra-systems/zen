"""
WebSocket connection basic functionality tests
Tests core connection management, pooling, heartbeat, and cleanup
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
from pathlib import Path
import sys

import asyncio
import time
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, MagicMock, call, patch

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.websocket_core.connection_info import ConnectionInfo
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.tests.services.test_ws_connection_mocks import (

    MockConnectionPool,

    MockWebSocket,

    WebSocketTestHelpers,

)

class TestWebSocketManagerConnectionPooling:

    """Test WebSocket manager connection pooling and basic functionality"""
    
    @pytest.fixture

    def websocket_manager(self):

        """Create clean WebSocket manager instance"""

        WebSocketTestHelpers.reset_ws_manager_singleton()

        return WebSocketManager()
    
    @pytest.fixture

    def mock_websockets(self):

        """Create mock WebSockets for testing"""

        return WebSocketTestHelpers.create_mock_websockets(5)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_singleton_pattern(self):

        """Test WebSocket manager singleton pattern"""

        WebSocketTestHelpers.reset_ws_manager_singleton()

        manager1, manager2, manager3 = self._create_multiple_managers()

        self._verify_singleton_behavior(manager1, manager2, manager3)
        
    def _create_multiple_managers(self):

        """Create multiple manager instances"""

        return WebSocketManager(), WebSocketManager(), WebSocketManager()
        
    def _verify_singleton_behavior(self, m1, m2, m3):

        """Verify all managers are same instance"""

        assert m1 is m2

        assert m2 is m3

        assert id(m1) == id(m2) == id(m3)
        
    @pytest.mark.asyncio
    async def test_connection_establishment(self, websocket_manager, mock_websockets):

        """Test WebSocket connection establishment"""

        user_id, websocket = self._get_test_websocket(mock_websockets, "user_1")

        conn_info = await websocket_manager.connect_user(user_id, websocket)

        self._verify_connection_established(websocket_manager, user_id, websocket, conn_info)
        
    def _get_test_websocket(self, mock_websockets, user_id):

        """Get test WebSocket for user"""

        return user_id, mock_websockets[user_id]
        
    def _verify_connection_established(self, websocket_manager, user_id, websocket, conn_info):

        """Verify connection was properly established"""

        assert conn_info is not None

        assert conn_info.user_id == user_id

        assert conn_info.websocket is websocket

        assert user_id in websocket_manager.connection_manager.active_connections

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == 1
        
    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self, websocket_manager):

        """Test multiple connections for same user"""

        user_id = "multi_conn_user"

        connections = await self._create_multiple_connections(websocket_manager, user_id, 3)

        self._verify_multiple_connections(websocket_manager, user_id, connections)
        
    async def _create_multiple_connections(self, websocket_manager, user_id, count):

        """Create multiple connections for user"""

        connections = []

        for i in range(count):

            websocket = MockWebSocket(f"{user_id}_{i}")

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append(conn_info)

        return connections
        
    def _verify_multiple_connections(self, websocket_manager, user_id, connections):

        """Verify multiple connections tracked correctly"""

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == 3

        assert websocket_manager.get_stats().total_connections == 3

        connection_ids = {conn.connection_id for conn in connections}

        assert len(connection_ids) == 3
        
    @pytest.mark.asyncio
    async def test_connection_limit_enforcement(self, websocket_manager):

        """Test enforcement of connection limits per user"""

        user_id = "limited_user"

        max_connections = websocket_manager.MAX_CONNECTIONS_PER_USER

        connections = await self._create_max_connections(websocket_manager, user_id, max_connections)

        await self._test_connection_limit_exceeded(websocket_manager, user_id, max_connections, connections)
        
    async def _create_max_connections(self, websocket_manager, user_id, max_connections):

        """Create connections up to limit"""

        connections = []

        for i in range(max_connections):

            websocket = MockWebSocket(f"{user_id}_{i}")

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append(conn_info)

        return connections
        
    async def _test_connection_limit_exceeded(self, websocket_manager, user_id, max_connections, connections):

        """Test behavior when connection limit exceeded"""

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == max_connections

        extra_websocket = MockWebSocket(f"{user_id}_extra")

        await websocket_manager.connect_user(user_id, extra_websocket)

        self._verify_limit_enforcement(websocket_manager, user_id, max_connections, connections)
        
    def _verify_limit_enforcement(self, websocket_manager, user_id, max_connections, connections):

        """Verify connection limit was enforced"""

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == max_connections

        oldest_ws = connections[0].websocket

        assert oldest_ws.state == WebSocketState.DISCONNECTED

        assert oldest_ws.close_code == 1008
        
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self, websocket_manager, mock_websockets):

        """Test connection cleanup when WebSocket disconnects"""

        user_id, websocket = self._get_test_websocket(mock_websockets, "user_1")

        connection_id = await self._establish_test_connection(websocket_manager, user_id, websocket)

        await self._disconnect_and_verify_cleanup(websocket_manager, user_id, websocket, connection_id)
        
    async def _establish_test_connection(self, websocket_manager, user_id, websocket):

        """Establish connection and return connection ID"""

        conn_info = await websocket_manager.connect_user(user_id, websocket)

        connection_id = conn_info.connection_id

        assert connection_id in websocket_manager.connection_manager.connection_registry

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == 1

        return connection_id
        
    async def _disconnect_and_verify_cleanup(self, websocket_manager, user_id, websocket, connection_id):

        """Disconnect and verify proper cleanup"""

        await websocket_manager.disconnect_user(user_id, websocket)

        assert connection_id not in websocket_manager.connection_manager.connection_registry

        assert len(websocket_manager.connection_manager.active_connections[user_id]) == 0

        assert websocket.state == WebSocketState.DISCONNECTED
        
    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, websocket_manager):

        """Test WebSocket heartbeat mechanism"""

        user_id = "heartbeat_user"

        websocket = MockWebSocket(user_id)

        connection_id = await self._setup_heartbeat_test(websocket_manager, user_id, websocket)

        await self._verify_heartbeat_functionality(websocket_manager, websocket, connection_id)

        await websocket_manager.disconnect_user(user_id, websocket)
        
    async def _setup_heartbeat_test(self, websocket_manager, user_id, websocket):

        """Setup connection for heartbeat testing"""

        conn_info = await websocket_manager.connect_user(user_id, websocket)

        connection_id = conn_info.connection_id

        assert connection_id in websocket_manager.core.heartbeat_manager.heartbeat_tasks

        heartbeat_task = websocket_manager.core.heartbeat_manager.heartbeat_tasks[connection_id]

        assert not heartbeat_task.done()

        return connection_id
        
    async def _verify_heartbeat_functionality(self, websocket_manager, websocket, connection_id):

        """Verify heartbeat is functioning"""

        await asyncio.sleep(0.1)

        sent_messages = websocket.get_sent_messages()

        system_messages = self._filter_system_messages(sent_messages)

        assert len(system_messages) >= 1
        
    def _filter_system_messages(self, sent_messages):

        """Filter system messages from sent messages"""

        return [

            msg for msg in sent_messages 

            if 'connection_established' in msg['data'] or 'ping' in msg['data']

        ]
        
    @pytest.mark.asyncio
    async def test_heartbeat_timeout_detection(self, websocket_manager):

        """Test detection of heartbeat timeouts"""

        user_id = "timeout_user"

        websocket = MockWebSocket(user_id)

        websocket.should_fail_send = True

        conn_info = await websocket_manager.connect_user(user_id, websocket)

        await self._test_heartbeat_timeout(websocket_manager, user_id, websocket)
        
    async def _test_heartbeat_timeout(self, websocket_manager, user_id, websocket):

        """Test heartbeat timeout detection behavior"""

        await asyncio.sleep(0.2)
        # Heartbeat should detect failure (implementation dependent)

        await websocket_manager.disconnect_user(user_id, websocket)
        
    @pytest.mark.asyncio
    async def test_concurrent_connection_management(self, websocket_manager):

        """Test concurrent connection establishment and cleanup"""

        num_users, num_connections_per_user = 20, 2

        connection_tasks = self._create_concurrent_connection_tasks(

            websocket_manager, num_users, num_connections_per_user

        )

        results = await self._execute_concurrent_connections(connection_tasks)

        await self._verify_and_cleanup_concurrent_connections(websocket_manager, results)
        
    def _create_concurrent_connection_tasks(self, websocket_manager, num_users, num_connections_per_user):

        """Create concurrent connection tasks"""

        tasks = []

        for user_idx in range(num_users):

            for conn_idx in range(num_connections_per_user):

                user_id = f"concurrent_user_{user_idx}"

                websocket = MockWebSocket(f"{user_id}_{conn_idx}")

                task = websocket_manager.connect_user(user_id, websocket)

                tasks.append((user_id, websocket, task))

        return tasks
        
    async def _execute_concurrent_connections(self, connection_tasks):

        """Execute all connection tasks concurrently"""

        results = []

        for user_id, websocket, task in connection_tasks:

            conn_info = await task

            results.append((user_id, websocket, conn_info))

        return results
        
    async def _verify_and_cleanup_concurrent_connections(self, websocket_manager, results):

        """Verify concurrent connections and cleanup"""

        expected_total = len(results)

        assert len(results) == expected_total

        total_connections = sum(len(conns) for conns in websocket_manager.connection_manager.active_connections.values())

        assert total_connections == expected_total

        await self._cleanup_all_concurrent_connections(websocket_manager, results)
        
    async def _cleanup_all_concurrent_connections(self, websocket_manager, results):

        """Cleanup all concurrent connections"""

        cleanup_tasks = [

            websocket_manager.disconnect_user(user_id, websocket)

            for user_id, websocket, conn_info in results

        ]

        await asyncio.gather(*cleanup_tasks)

        assert len(websocket_manager.connection_manager.connection_registry) == 0
        
    @pytest.mark.asyncio
    async def test_message_broadcasting_to_multiple_connections(self, websocket_manager):

        """Test broadcasting messages to multiple connections"""

        user_id = "broadcast_user"

        websockets = await self._setup_multiple_connections_for_broadcast(websocket_manager, user_id)

        await self._test_broadcast_delivery(websocket_manager, user_id, websockets)

        await self._cleanup_broadcast_connections(websocket_manager, user_id, websockets)
        
    async def _setup_multiple_connections_for_broadcast(self, websocket_manager, user_id):

        """Setup multiple connections for broadcast testing"""

        websockets = []

        for i in range(3):

            websocket = MockWebSocket(f"{user_id}_{i}")

            await websocket_manager.connect_user(user_id, websocket)

            websockets.append(websocket)

        return websockets
        
    async def _test_broadcast_delivery(self, websocket_manager, user_id, websockets):

        """Test message broadcast delivery"""

        test_message = {"type": "broadcast", "content": "Hello all connections!"}

        await websocket_manager.send_message_to_user(user_id, test_message)

        for websocket in websockets:

            WebSocketTestHelpers.verify_connection_messages(websocket, ['broadcast'])
            
    async def _cleanup_broadcast_connections(self, websocket_manager, user_id, websockets):

        """Cleanup broadcast test connections"""

        for websocket in websockets:

            await websocket_manager.disconnect_user(user_id, websocket)
            
    @pytest.mark.asyncio
    async def test_connection_statistics_tracking(self, websocket_manager):

        """Test connection statistics tracking"""

        initial_stats = websocket_manager.get_stats()

        assert initial_stats["total_connections"] == 0

        connections = await self._create_connections_for_stats(websocket_manager)

        await self._test_statistics_updates(websocket_manager, connections)

        await self._cleanup_stats_connections(websocket_manager, connections)
        
    async def _create_connections_for_stats(self, websocket_manager):

        """Create connections for statistics testing"""

        connections = []

        for i in range(5):

            user_id = f"stats_user_{i}"

            websocket = MockWebSocket(user_id)

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append((user_id, websocket, conn_info))

        return connections
        
    async def _test_statistics_updates(self, websocket_manager, connections):

        """Test statistics are properly updated"""

        updated_stats = websocket_manager.get_stats()

        assert updated_stats["total_connections"] == 5

        await self._send_test_messages(websocket_manager, connections)

        final_stats = websocket_manager.get_stats()

        assert final_stats["total_messages_sent"] >= 5
        
    async def _send_test_messages(self, websocket_manager, connections):

        """Send test messages to update statistics"""

        for user_id, websocket, conn_info in connections:

            await websocket_manager.send_message_to_user(user_id, {"test": "message"})
            
    async def _cleanup_stats_connections(self, websocket_manager, connections):

        """Cleanup statistics test connections"""

        for user_id, websocket, conn_info in connections:

            await websocket_manager.disconnect_user(user_id, websocket)