"""
WebSocket connection test mocks and shared utilities
Provides mock classes and fixtures for WebSocket connection testing
"""

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
import time
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from netra_backend.app.ws_manager import (

    ConnectionInfo,

    WebSocketManager,

)

class MockWebSocket:

    """Mock WebSocket for testing connection behavior"""
    
    def __init__(self, user_id: str = None):

        self.user_id = user_id or self._generate_user_id()

        self.state = WebSocketState.CONNECTED

        self.sent_messages = []

        self._init_failure_flags()

        self._init_connection_info()
        
    def _generate_user_id(self) -> str:

        """Generate unique user ID"""

        return f"user_{int(time.time() * 1000)}"
        
    def _init_failure_flags(self):

        """Initialize failure simulation flags"""

        self.should_fail_send = False

        self.should_fail_accept = False

        self.should_fail_close = False
        
    def _init_connection_info(self):

        """Initialize connection information"""

        self.close_code = None

        self.close_reason = None

        self.client_host = "127.0.0.1"

        self.client_port = 8000
        
    async def accept(self):

        """Mock WebSocket accept with failure simulation"""

        if self.should_fail_accept:

            raise Exception("Mock accept failure")

        self.state = WebSocketState.CONNECTED
        
    async def send_text(self, data: str):

        """Mock send text with failure and state checking"""

        self._check_send_preconditions()

        self._record_message('text', data)
        
    def _check_send_preconditions(self):

        """Check conditions before sending message"""

        if self.should_fail_send:

            raise WebSocketDisconnect(code=1011, reason="Mock send failure")

        if self.state != WebSocketState.CONNECTED:

            raise WebSocketDisconnect(code=1000, reason="Not connected")
            
    def _record_message(self, msg_type: str, data: str):

        """Record sent message with metadata"""

        self.sent_messages.append({

            'type': msg_type,

            'data': data,

            'timestamp': datetime.now(UTC)

        })
        
    async def send_json(self, data: dict):

        """Mock send JSON message"""

        await self.send_text(json.dumps(data))
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):

        """Mock WebSocket close with failure simulation"""

        if self.should_fail_close:

            raise Exception("Mock close failure")

        self._set_closed_state(code, reason)
        
    def _set_closed_state(self, code: int, reason: str):

        """Set WebSocket to closed state"""

        self.state = WebSocketState.DISCONNECTED

        self.close_code = code

        self.close_reason = reason
        
    async def receive_text(self):

        """Mock receive text message for testing"""

        await asyncio.sleep(0.1)

        return self._generate_ping_message()
        
    def _generate_ping_message(self) -> str:

        """Generate ping message for testing"""

        return '{"type": "ping", "timestamp": ' + str(time.time()) + '}'
        
    def get_sent_messages(self) -> List[Dict[str, Any]]:

        """Get copy of sent messages"""

        return self.sent_messages.copy()
        
    def clear_sent_messages(self):

        """Clear sent message history"""

        self.sent_messages.clear()

class MockConnectionPool:

    """Mock connection pool for testing scalability and resource management"""
    
    def __init__(self, max_connections: int = 100):

        self.max_connections = max_connections

        self.active_connections = 0

        self.total_connections_created = 0

        self.connection_wait_queue = asyncio.Queue()

        self._init_pool_stats()
        
    def _init_pool_stats(self):

        """Initialize connection pool statistics"""

        self.pool_stats = {

            'connections_created': 0,

            'connections_reused': 0,

            'connections_expired': 0,

            'wait_time_total': 0,

            'average_wait_time': 0

        }
        
    async def acquire_connection(self) -> MockWebSocket:

        """Acquire connection from pool with wait tracking"""

        start_time = time.time()

        await self._wait_for_available_slot()

        connection = self._create_new_connection()

        wait_time = time.time() - start_time

        self._update_acquisition_stats(wait_time)

        return connection
        
    async def _wait_for_available_slot(self):

        """Wait for available connection slot"""

        if self.active_connections >= self.max_connections:

            await self.connection_wait_queue.get()
            
    def _create_new_connection(self) -> MockWebSocket:

        """Create and track new connection"""

        connection = MockWebSocket()

        self.active_connections += 1

        self.total_connections_created += 1

        self.pool_stats['connections_created'] += 1

        return connection
        
    def _update_acquisition_stats(self, wait_time: float):

        """Update pool acquisition statistics"""

        self.pool_stats['wait_time_total'] += wait_time

        if self.pool_stats['connections_created'] > 0:

            self.pool_stats['average_wait_time'] = (

                self.pool_stats['wait_time_total'] / 

                self.pool_stats['connections_created']

            )
        
    async def release_connection(self, connection: MockWebSocket):

        """Release connection back to pool"""

        self._decrease_active_count()

        self._notify_waiting_connections()
        
    def _decrease_active_count(self):

        """Decrease active connection count"""

        if self.active_connections > 0:

            self.active_connections -= 1
            
    def _notify_waiting_connections(self):

        """Notify connections waiting for slots"""

        try:

            self.connection_wait_queue.put_nowait(True)

        except asyncio.QueueFull:

            pass
            
    def get_pool_stats(self) -> Dict[str, Any]:

        """Get comprehensive pool statistics"""

        return {

            **self.pool_stats,

            'active_connections': self.active_connections,

            'max_connections': self.max_connections,

            'total_connections_created': self.total_connections_created,

            'utilization_rate': self._calculate_utilization_rate()

        }
        
    def _calculate_utilization_rate(self) -> float:

        """Calculate pool utilization rate"""

        if self.max_connections == 0:

            return 0.0

        return self.active_connections / self.max_connections

class WebSocketTestHelpers:

    """Helper utilities for WebSocket testing"""
    
    @staticmethod

    def create_mock_websockets(count: int, prefix: str = "user") -> Dict[str, MockWebSocket]:

        """Create multiple mock WebSocket connections"""

        return {

            f"{prefix}_{i}": MockWebSocket(f"{prefix}_{i}")

            for i in range(1, count + 1)

        }
        
    @staticmethod

    def reset_ws_manager_singleton():

        """Reset WebSocket manager singleton for clean testing"""

        WebSocketManager._instance = None
        
    @staticmethod

    async def connect_multiple_users(ws_manager: WebSocketManager, 

                                   websockets: Dict[str, MockWebSocket]):

        """Connect multiple WebSocket users to manager"""

        connections = []

        for user_id, websocket in websockets.items():

            conn_info = await ws_manager.connect_user(user_id, websocket)

            connections.append((user_id, websocket, conn_info))

        return connections
        
    @staticmethod

    async def cleanup_connections(ws_manager: WebSocketManager, connections: List):

        """Clean up list of WebSocket connections"""

        for user_id, websocket, _ in connections:

            await ws_manager.disconnect_user(user_id, websocket)
            
    @staticmethod

    def verify_connection_messages(websocket: MockWebSocket, 

                                 expected_message_types: List[str]):

        """Verify WebSocket received expected message types"""

        sent_messages = websocket.get_sent_messages()

        for msg_type in expected_message_types:

            messages_of_type = [

                msg for msg in sent_messages 

                if msg_type in msg['data']

            ]

            assert len(messages_of_type) >= 1, f"Missing {msg_type} messages"