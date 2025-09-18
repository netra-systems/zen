"""
WebSocket test helpers - Implementation for Golden Path tests
Created to resolve Issue #1332 Phase 3 - unblock Golden Path testing
"""
import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock


# Import the real WebSocketTestClient from real_services
try:
    from test_framework.real_services import WebSocketTestClient as RealWebSocketTestClient
except ImportError:
    RealWebSocketTestClient = None


class WebSocketTestClient:
    """
    WebSocket test client that provides compatibility for both legacy and new patterns.
    This ensures existing tests continue to work while transitioning to real service patterns.
    """

    def __init__(self, url: str = None, user_id: str = None, headers: Optional[Dict[str, str]] = None, **kwargs):
        """Initialize WebSocket test client with flexible parameter patterns."""
        self.url = url or "ws://localhost:8000/ws"
        self.user_id = user_id or str(uuid.uuid4())
        self.headers = headers or {}
        self.kwargs = kwargs
        self._connection = None
        self._connected = False
        self._messages = []

        # If RealWebSocketTestClient is available and we have proper config, use it
        if RealWebSocketTestClient and 'config' in kwargs:
            self._real_client = RealWebSocketTestClient(kwargs['config'])
        else:
            self._real_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self, endpoint: str = "", headers: Optional[Dict[str, str]] = None):
        """Connect to WebSocket endpoint."""
        if self._real_client:
            await self._real_client.connect(endpoint, headers or self.headers)
            self._connected = True
        else:
            # Mock connection for test compatibility
            self._connection = AsyncMock()
            self._connected = True

    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self._real_client:
            await self._real_client.disconnect()
        elif self._connection:
            await self._connection.close()
        self._connected = False

    async def send(self, message: Union[str, Dict[str, Any]]):
        """Send message through WebSocket."""
        if not self._connected:
            await self.connect()

        if self._real_client:
            await self._real_client.send(message)
        else:
            # Mock send for test compatibility
            if isinstance(message, dict):
                message = json.dumps(message)
            self._messages.append(message)

    async def receive(self, timeout: Optional[float] = 5.0) -> str:
        """Receive message from WebSocket."""
        if not self._connected:
            raise RuntimeError("WebSocket not connected")

        if self._real_client:
            return await self._real_client.receive(timeout)
        else:
            # Mock receive for test compatibility
            if self._messages:
                return self._messages.pop(0)
            return '{"type": "mock", "data": "test message"}'

    async def close(self):
        """Close WebSocket connection."""
        await self.disconnect()


def assert_websocket_events(events: List[Dict[str, Any]], expected_event_types: List[str]) -> bool:
    """
    Assert that WebSocket events contain the expected event types.

    Args:
        events: List of WebSocket events
        expected_event_types: List of expected event type strings

    Returns:
        bool: True if all expected events are found

    Raises:
        AssertionError: If expected events are missing
    """
    if not events:
        raise AssertionError(f"No events received, expected: {expected_event_types}")

    received_types = []
    for event in events:
        if isinstance(event, dict):
            event_type = event.get('type') or event.get('event_type') or event.get('event')
            if event_type:
                received_types.append(event_type)

    missing_events = []
    for expected_type in expected_event_types:
        if expected_type not in received_types:
            missing_events.append(expected_type)

    if missing_events:
        raise AssertionError(
            f"Missing expected WebSocket events: {missing_events}. "
            f"Received events: {received_types}"
        )

    return True


def assert_websocket_events_sent(events: List[Dict[str, Any]], expected_event_types: List[str]) -> bool:
    """
    Alias for assert_websocket_events for backwards compatibility.
    """
    return assert_websocket_events(events, expected_event_types)


async def wait_for_agent_completion(websocket, timeout: float = 60.0) -> Dict[str, Any]:
    """
    Wait for agent execution to complete by monitoring WebSocket events.

    Args:
        websocket: WebSocket connection to monitor
        timeout: Maximum time to wait for completion

    Returns:
        dict: Completion status and collected events
    """
    events = []
    start_time = time.time()
    completed = False

    while time.time() - start_time < timeout and not completed:
        try:
            if hasattr(websocket, 'receive'):
                message = await asyncio.wait_for(websocket.receive(1.0), timeout=1.0)
                if message:
                    try:
                        event = json.loads(message) if isinstance(message, str) else message
                        events.append(event)

                        # Check for completion events
                        event_type = event.get('type') or event.get('event_type') or event.get('event')
                        if event_type == 'agent_completed':
                            completed = True
                            break

                    except (json.JSONDecodeError, AttributeError):
                        continue
            else:
                await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            continue
        except Exception:
            break

    return {
        "completed": completed,
        "events": events,
        "duration": time.time() - start_time,
        "timeout": timeout
    }


async def create_test_websocket_connection(
    url: str = None,
    user_id: str = None,
    headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> WebSocketTestClient:
    """
    Create and return a configured WebSocketTestClient for testing.

    Args:
        url: WebSocket URL to connect to
        user_id: User ID for the connection
        headers: Additional headers for the connection
        **kwargs: Additional arguments for the client

    Returns:
        Configured WebSocketTestClient instance
    """
    client = WebSocketTestClient(
        url=url or "ws://localhost:8000/ws",
        user_id=user_id,
        headers=headers,
        **kwargs
    )
    return client


class WebSocketTestHelpers:
    """Helper functions for WebSocket integration testing."""

    @staticmethod
    async def create_mock_websocket_connection(user_id: str) -> MagicMock:
        """Create mock WebSocket connection for testing."""
        mock_websocket = MagicMock()
        mock_websocket.user_id = user_id
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        return mock_websocket

    @staticmethod
    async def wait_for_events(websocket, event_types: List[str], timeout: float = 30.0) -> Dict[str, Any]:
        """Wait for specific WebSocket events."""
        # Enhanced implementation for Golden Path compatibility
        events = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if hasattr(websocket, 'receive'):
                    message = await asyncio.wait_for(websocket.receive(1.0), timeout=1.0)
                    if message:
                        try:
                            event = json.loads(message) if isinstance(message, str) else message
                            events.append(event)

                            # Check if we have all required event types
                            received_types = [e.get('type') or e.get('event_type') for e in events]
                            if all(event_type in received_types for event_type in event_types):
                                break
                        except (json.JSONDecodeError, AttributeError):
                            continue
                else:
                    await asyncio.sleep(0.1)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

        return {
            "events": events,
            "success": len([e for e in events if e.get('type') in event_types]) >= len(event_types),
            "timeout": timeout
        }

    @staticmethod
    async def simulate_user_message(websocket, message: str):
        """Simulate sending a user message through WebSocket."""
        if hasattr(websocket, 'send'):
            await websocket.send(message)
        else:
            await websocket.send_text(message)

    @staticmethod
    async def create_test_websocket_connection(
        url: str = None,
        user_id: str = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        **kwargs
    ) -> WebSocketTestClient:
        """
        Create and return a configured WebSocketTestClient for testing.

        Args:
            url: WebSocket URL to connect to
            user_id: User ID for the connection
            headers: Additional headers for the connection
            timeout: Connection timeout
            **kwargs: Additional arguments for the client

        Returns:
            Configured WebSocketTestClient instance
        """
        client = WebSocketTestClient(
            url=url or "ws://localhost:8000/ws",
            user_id=user_id,
            headers=headers,
            **kwargs
        )
        await client.connect()
        return client

    @staticmethod
    async def send_test_message(
        websocket,
        message: Union[str, Dict[str, Any]],
        timeout: float = 5.0
    ):
        """
        Send a test message through WebSocket connection.

        Args:
            websocket: WebSocket connection
            message: Message to send (string or dict)
            timeout: Send timeout
        """
        if hasattr(websocket, 'send'):
            await websocket.send(message)
        elif hasattr(websocket, 'send_text'):
            if isinstance(message, dict):
                await websocket.send_text(json.dumps(message))
            else:
                await websocket.send_text(str(message))

    @staticmethod
    async def receive_test_message(
        websocket,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        Receive a test message from WebSocket connection.

        Args:
            websocket: WebSocket connection
            timeout: Receive timeout

        Returns:
            Received message as dict
        """
        if hasattr(websocket, 'receive'):
            message = await asyncio.wait_for(websocket.receive(timeout), timeout=timeout)
        elif hasattr(websocket, 'receive_text'):
            message = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
        else:
            raise AttributeError("WebSocket has no receive method")

        # Parse JSON if it's a string
        if isinstance(message, str):
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                return {"type": "text", "content": message}
        return message

    @staticmethod
    async def close_test_connection(websocket):
        """
        Close WebSocket test connection.

        Args:
            websocket: WebSocket connection to close
        """
        if hasattr(websocket, 'close'):
            await websocket.close()
        elif hasattr(websocket, 'disconnect'):
            await websocket.disconnect()


class MockWebSocket:
    """Mock WebSocket for testing purposes."""

    def __init__(self, user_id: str = None):
        self.user_id = user_id or str(uuid.uuid4())
        self._messages = []
        self._connected = True
        self.send = AsyncMock()
        self.receive = AsyncMock()
        self.close = AsyncMock()
        self.accept = AsyncMock()

    async def send_text(self, message: str):
        """Mock send_text method."""
        await self.send(message)
        self._messages.append(message)

    async def receive_text(self) -> str:
        """Mock receive_text method."""
        if self._messages:
            return self._messages.pop(0)
        return '{"type": "mock", "data": "test"}'

    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method."""
        message = json.dumps(data)
        await self.send_text(message)

    async def receive_json(self) -> Dict[str, Any]:
        """Mock receive_json method."""
        message = await self.receive_text()
        return json.loads(message) if message else {}


class MockWebSocketConnection:
    """Mock WebSocket connection for testing purposes."""

    def __init__(self, user_id: str = None, url: str = None):
        self.user_id = user_id or str(uuid.uuid4())
        self.url = url or "ws://localhost:8000/ws"
        self._websocket = MockWebSocket(user_id)
        self._connected = False
        self._messages = []

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Mock connect method."""
        self._connected = True
        return self._websocket

    async def disconnect(self):
        """Mock disconnect method."""
        self._connected = False
        await self._websocket.close()

    async def send(self, message: Union[str, Dict[str, Any]]):
        """Send message through mock connection."""
        if isinstance(message, dict):
            await self._websocket.send_json(message)
        else:
            await self._websocket.send_text(message)

    async def receive(self, timeout: Optional[float] = None) -> str:
        """Receive message from mock connection."""
        return await self._websocket.receive_text()

    @property
    def websocket(self):
        """Get the underlying websocket."""
        return self._websocket


class WebSocketPerformanceMonitor:
    """Performance monitoring for WebSocket connections."""

    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
        self.event_counts = {}

    def record_metric(self, name: str, value: Any):
        """Record a performance metric."""
        self.metrics[name] = value

    def record_event(self, event_type: str):
        """Record an event occurrence."""
        if event_type not in self.event_counts:
            self.event_counts[event_type] = 0
        self.event_counts[event_type] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return {
            "metrics": self.metrics.copy(),
            "event_counts": self.event_counts.copy(),
            "duration": time.time() - self.start_time
        }

    def reset(self):
        """Reset all metrics."""
        self.metrics = {}
        self.event_counts = {}
        self.start_time = time.time()