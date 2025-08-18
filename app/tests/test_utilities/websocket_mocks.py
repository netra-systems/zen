"""
Comprehensive WebSocket Mock Utilities Framework
Consolidates WebSocket testing patterns from 30+ test files into reusable components.
Maximum 300 lines, functions ≤8 lines, fully type-safe.

Business Value Justification (BVJ):
1. Segment: Growth & Enterprise  
2. Business Goal: Reduce test development time by 60%
3. Value Impact: Accelerates feature delivery, improves test reliability
4. Revenue Impact: Enables faster iteration on WebSocket features

Module consolidates patterns for:
- Connection lifecycle management
- Message handling simulation  
- Authentication flow mocks
- Rate limiting simulation
- Error and disconnection scenarios
- Broadcast message patterns
"""

import asyncio
import time
import json
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
from enum import Enum

from app.schemas.websocket_message_types import (
    WebSocketMessageUnion, ClientMessageUnion, ServerMessageUnion,
    WebSocketConnectionState, ConnectionInfo, WebSocketStats
)
from app.schemas.registry import WebSocketMessage, WebSocketMessageType


class MockWebSocketState(str, Enum):
    """Mock WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MockWebSocket:
    """Enhanced mock WebSocket with comprehensive testing features."""
    
    def __init__(self, user_id: str = None, connection_id: str = None):
        self.user_id = user_id or f"user_{int(time.time() * 1000)}"
        self.connection_id = connection_id or f"conn_{int(time.time() * 1000)}"
        self.state = MockWebSocketState.CONNECTED
        self.sent_messages: List[Dict[str, Any]] = []
        self._init_failure_simulation()
        self._init_auth_state()
    
    def _init_failure_simulation(self):
        """Initialize failure simulation flags (≤8 lines)."""
        self.should_fail_send = False
        self.should_fail_accept = False
        self.should_fail_close = False
        self.should_timeout = False
        self.timeout_delay = 2.0
        self.failure_probability = 0.0
    
    def _init_auth_state(self):
        """Initialize authentication state (≤8 lines)."""
        self.is_authenticated = True
        self.auth_token = f"token_{self.user_id}"
        self.permissions = ["read", "write"]
        self.rate_limit_count = 0
        self.rate_limit_max = 100
        self.rate_limit_window_start = datetime.now(UTC)
    
    async def accept(self):
        """Mock WebSocket accept with failure simulation (≤8 lines)."""
        if self.should_fail_accept:
            raise ConnectionError("Mock accept failure")
        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay)
        self.state = MockWebSocketState.CONNECTED
    
    async def send_text(self, data: str):
        """Mock send text with comprehensive error handling (≤8 lines)."""
        await self._check_send_preconditions()
        self._record_message("text", data)
        await self._simulate_network_delay()
    
    async def send_json(self, data: Dict[str, Any]):
        """Mock send JSON with type validation (≤8 lines)."""
        await self._check_send_preconditions()
        json_data = json.dumps(data)
        self._record_message("json", json_data)
        await self._simulate_network_delay()
    
    async def _check_send_preconditions(self):
        """Check conditions before sending message (≤8 lines)."""
        if self.should_fail_send or self._should_random_fail():
            raise ConnectionError("Mock send failure")
        if self.state != MockWebSocketState.CONNECTED:
            raise ConnectionError("Not connected")
        self._check_rate_limit()
    
    def _should_random_fail(self) -> bool:
        """Simulate random failures based on probability (≤8 lines)."""
        import random
        return random.random() < self.failure_probability
    
    def _check_rate_limit(self):
        """Check and update rate limiting (≤8 lines)."""
        now = datetime.now(UTC)
        if (now - self.rate_limit_window_start).seconds > 60:
            self.rate_limit_count = 0
            self.rate_limit_window_start = now
        if self.rate_limit_count >= self.rate_limit_max:
            raise ConnectionError("Rate limit exceeded")
        self.rate_limit_count += 1
    
    def _record_message(self, msg_type: str, data: str):
        """Record sent message with metadata (≤8 lines)."""
        self.sent_messages.append({
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now(UTC),
            "user_id": self.user_id,
            "connection_id": self.connection_id
        })
    
    async def _simulate_network_delay(self):
        """Simulate realistic network delays (≤8 lines)."""
        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay)
        else:
            await asyncio.sleep(0.001)  # Minimal delay for realism
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock WebSocket close with failure simulation (≤8 lines)."""
        if self.should_fail_close:
            raise ConnectionError("Mock close failure")
        self.state = MockWebSocketState.DISCONNECTED
        self.close_code = code
        self.close_reason = reason


class WebSocketBuilder:
    """Fluent builder for creating configured mock WebSockets."""
    
    def __init__(self):
        self._websocket = MockWebSocket()
    
    def with_user_id(self, user_id: str) -> 'WebSocketBuilder':
        """Set user ID for the WebSocket (≤8 lines)."""
        self._websocket.user_id = user_id
        return self
    
    def with_authentication(self, token: str = None, permissions: List[str] = None) -> 'WebSocketBuilder':
        """Configure authentication settings (≤8 lines)."""
        self._websocket.auth_token = token or f"token_{self._websocket.user_id}"
        self._websocket.permissions = permissions or ["read", "write"]
        self._websocket.is_authenticated = True
        return self
    
    def with_rate_limiting(self, max_requests: int = 100, window_seconds: int = 60) -> 'WebSocketBuilder':
        """Configure rate limiting parameters (≤8 lines)."""
        self._websocket.rate_limit_max = max_requests
        self._websocket.rate_limit_count = 0
        self._websocket.rate_limit_window_start = datetime.now(UTC)
        return self
    
    def with_failure_simulation(self, send_fail: bool = False, probability: float = 0.0) -> 'WebSocketBuilder':
        """Configure failure simulation (≤8 lines)."""
        self._websocket.should_fail_send = send_fail
        self._websocket.failure_probability = probability
        self._websocket.should_timeout = False
        return self
    
    def with_timeout_simulation(self, delay: float = 2.0) -> 'WebSocketBuilder':
        """Configure timeout simulation (≤8 lines)."""
        self._websocket.should_timeout = True
        self._websocket.timeout_delay = delay
        return self
    
    def build(self) -> MockWebSocket:
        """Build the configured MockWebSocket (≤8 lines)."""
        return self._websocket


class MessageSimulator:
    """Simulates complex WebSocket message patterns."""
    
    def __init__(self):
        self.message_history: List[WebSocketMessage] = []
        self.handlers: Dict[str, Callable] = {}
        
    async def simulate_bidirectional_flow(self, websocket: MockWebSocket, messages: List[Dict]) -> List[Dict]:
        """Simulate bidirectional message exchange (≤8 lines)."""
        results = []
        for msg in messages:
            await websocket.send_json(msg)
            response = await self._generate_response(msg)
            results.append(response)
        return results
    
    async def _generate_response(self, message: Dict) -> Dict:
        """Generate mock response to message (≤8 lines)."""
        msg_type = message.get("type", "unknown")
        handler = self.handlers.get(msg_type, self._default_handler)
        return await handler(message)
    
    async def _default_handler(self, message: Dict) -> Dict:
        """Default message handler (≤8 lines)."""
        return {
            "type": "response",
            "payload": {"status": "received", "original_type": message.get("type")},
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register custom message handler (≤8 lines)."""
        self.handlers[message_type] = handler
    
    async def simulate_broadcast(self, websockets: List[MockWebSocket], message: Dict) -> Dict:
        """Simulate broadcast to multiple connections (≤8 lines)."""
        successful = 0
        failed = 0
        for ws in websockets:
            try:
                await ws.send_json(message)
                successful += 1
            except Exception:
                failed += 1
        return {"successful": successful, "failed": failed, "total": len(websockets)}


@asynccontextmanager
async def websocket_test_context(user_count: int = 1) -> AsyncGenerator[Dict[str, MockWebSocket], None]:
    """Async context manager for WebSocket test isolation (≤8 lines)."""
    websockets = {
        f"user_{i}": WebSocketBuilder().with_user_id(f"user_{i}").build()
        for i in range(1, user_count + 1)
    }
    try:
        yield websockets
    finally:
        await _cleanup_websockets(websockets)


async def _cleanup_websockets(websockets: Dict[str, MockWebSocket]):
    """Cleanup WebSocket connections (≤8 lines)."""
    cleanup_tasks = [
        ws.close() for ws in websockets.values()
        if ws.state == MockWebSocketState.CONNECTED
    ]
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


# Convenience functions for common patterns
def create_mock_websocket(user_id: str = None, **kwargs) -> MockWebSocket:
    """Create basic mock WebSocket with optional configuration (≤8 lines)."""
    builder = WebSocketBuilder()
    if user_id:
        builder = builder.with_user_id(user_id)
    if kwargs.get("auth"):
        builder = builder.with_authentication()
    if kwargs.get("rate_limit"):
        builder = builder.with_rate_limiting()
    return builder.build()


def create_mock_websockets(count: int, prefix: str = "user") -> Dict[str, MockWebSocket]:
    """Create multiple mock WebSocket connections (≤8 lines)."""
    return {
        f"{prefix}_{i}": create_mock_websocket(f"{prefix}_{i}")
        for i in range(1, count + 1)
    }


async def simulate_connection_lifecycle(websocket: MockWebSocket) -> Dict[str, Any]:
    """Simulate complete connection lifecycle (≤8 lines)."""
    await websocket.accept()
    test_message = {"type": "ping", "payload": {}}
    await websocket.send_json(test_message)
    await websocket.close()
    return {
        "connected": websocket.state == MockWebSocketState.DISCONNECTED,
        "messages_sent": len(websocket.sent_messages),
        "final_state": websocket.state
    }