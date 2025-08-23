"""Agent Startup WebSocket Manager - Supporting Module

WebSocket connection management utilities for agent startup E2E tests.
Handles connection lifecycle, message sending, and response validation.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Ensure reliable WebSocket communication during agent startup
- Value Impact: Validates real-time agent communication flows
- Revenue Impact: Protects user experience through reliable agent interactions

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Focused on WebSocket connection management
- Mock connections for testing reliability
"""

from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
from tests.e2e.agent_startup_user_manager import TestUser
from typing import Any, Callable, Dict, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class MockWebSocketConnection:

    """Mock WebSocket connection for testing."""
    

    def __init__(self, user_id: str):

        self.user_id = user_id

        self.connected = True

        self.message_count = 0
        

    async def send_json(self, data: Dict[str, Any]) -> None:

        """Mock send JSON message."""

        logger.debug(f"Mock sending to {self.user_id}: {data}")

        self.message_count += 1
        

    async def receive_json(self) -> Dict[str, Any]:

        """Mock receive JSON message."""

        await asyncio.sleep(0.1)  # Simulate network delay

        response = {

            "type": "agent_response", 

            "data": f"Mock agent response for {self.user_id}",

            "message_id": self.message_count

        }

        return response
        

    async def close(self) -> None:

        """Mock close connection."""

        self.connected = False

        logger.debug(f"Closed connection for {self.user_id}")
        

    def is_connected(self) -> bool:

        """Check if connection is active."""

        return self.connected


class WebSocketManager:

    """Manages WebSocket connections for E2E tests."""
    

    def __init__(self, websocket_url: str):

        self.websocket_url = websocket_url

        self.active_connections: Dict[str, MockWebSocketConnection] = {}

        self.message_handlers: Dict[str, Callable] = {}

        self.connection_metrics: Dict[str, int] = {}
        

    async def connect_user(self, user: TestUser) -> str:

        """Connect user via WebSocket and return connection ID."""

        connection_id = f"conn_{user.user_id}"

        ws_client = await self._create_websocket_connection(user)

        self.active_connections[connection_id] = ws_client

        self._initialize_connection_metrics(connection_id)

        return connection_id
        

    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:

        """Send message through WebSocket connection."""

        if connection_id not in self.active_connections:

            return False

        connection = self.active_connections[connection_id]

        await connection.send_json(message)

        self._update_message_metrics(connection_id, "sent")

        return True
        

    async def wait_for_response(self, connection_id: str, timeout: int = 10) -> Optional[Dict]:

        """Wait for WebSocket response with timeout."""

        if connection_id not in self.active_connections:

            return None

        response = await self._receive_message_with_timeout(connection_id, timeout)

        if response:

            self._update_message_metrics(connection_id, "received")

        return response
        

    async def disconnect_user(self, connection_id: str) -> None:

        """Disconnect specific user connection."""

        if connection_id in self.active_connections:

            connection = self.active_connections[connection_id]

            await connection.close()

            del self.active_connections[connection_id]
            

    async def disconnect_all(self) -> None:

        """Disconnect all active WebSocket connections."""

        disconnect_tasks = [

            self._disconnect_connection(conn)

            for conn in self.active_connections.values()

        ]

        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self.active_connections.clear()

        self.connection_metrics.clear()
        

    def get_connection_count(self) -> int:

        """Get count of active connections."""

        return len(self.active_connections)
        

    def get_connection_metrics(self) -> Dict[str, Dict[str, int]]:

        """Get metrics for all connections."""

        return {

            conn_id: {

                "messages_sent": self.connection_metrics.get(f"{conn_id}_sent", 0),

                "messages_received": self.connection_metrics.get(f"{conn_id}_received", 0),

                "is_connected": conn.is_connected()

            }

            for conn_id, conn in self.active_connections.items()

        }
        

    async def _create_websocket_connection(self, user: TestUser) -> MockWebSocketConnection:

        """Create WebSocket connection for user."""

        return MockWebSocketConnection(user.user_id)
        

    async def _receive_message_with_timeout(self, connection_id: str, timeout: int) -> Optional[Dict]:

        """Receive message with timeout handling."""

        try:

            return await asyncio.wait_for(

                self._receive_message(connection_id), timeout=timeout

            )

        except asyncio.TimeoutError:

            logger.warning(f"Timeout waiting for message on {connection_id}")

            return None
            

    async def _receive_message(self, connection_id: str) -> Dict[str, Any]:

        """Receive message from WebSocket connection."""

        connection = self.active_connections[connection_id]

        return await connection.receive_json()
        

    async def _disconnect_connection(self, connection: MockWebSocketConnection) -> None:

        """Disconnect individual WebSocket connection."""

        await connection.close()
        

    def _initialize_connection_metrics(self, connection_id: str) -> None:

        """Initialize metrics for new connection."""

        self.connection_metrics[f"{connection_id}_sent"] = 0

        self.connection_metrics[f"{connection_id}_received"] = 0
        

    def _update_message_metrics(self, connection_id: str, direction: str) -> None:

        """Update message metrics for connection."""

        metric_key = f"{connection_id}_{direction}"

        self.connection_metrics[metric_key] = (

            self.connection_metrics.get(metric_key, 0) + 1

        )
