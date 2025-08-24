"""
Unified WebSocket test utilities and helpers.
Consolidates WebSocket testing functionality from across the project.

This module provides:
- WebSocket connection helpers  
- Mock WebSocket implementations
- WebSocket test utilities
- WebSocket performance testing tools
"""

import asyncio
import json
import time
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True  
except ImportError:
    HTTPX_AVAILABLE = False

# =============================================================================
# WEBSOCKET CONNECTION UTILITIES
# =============================================================================

class WebSocketTestHelpers:
    """Unified helper utilities for WebSocket testing"""
    
    @staticmethod
    async def create_test_websocket_connection(
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 5.0
    ):
        """Create a test WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            raise pytest.skip("websockets library not available")
            
        try:
            connection = await asyncio.wait_for(
                websockets.connect(url, extra_headers=headers or {}),
                timeout=timeout
            )
            return connection
        except Exception as e:
            raise ConnectionError(f"Failed to create WebSocket connection: {e}")
    
    @staticmethod
    async def send_test_message(
        websocket,
        message: Dict[str, Any],
        timeout: float = 5.0
    ):
        """Send a test message through WebSocket"""
        try:
            message_json = json.dumps(message)
            await asyncio.wait_for(
                websocket.send(message_json),
                timeout=timeout
            )
        except Exception as e:
            raise RuntimeError(f"Failed to send WebSocket message: {e}")
    
    @staticmethod
    async def receive_test_message(
        websocket,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Receive and parse a test message from WebSocket"""
        try:
            message_raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=timeout
            )
            return json.loads(message_raw)
        except Exception as e:
            raise RuntimeError(f"Failed to receive WebSocket message: {e}")
    
    @staticmethod
    async def close_test_connection(websocket):
        """Close WebSocket test connection safely"""
        try:
            if hasattr(websocket, 'close'):
                await websocket.close()
        except Exception:
            pass  # Ignore cleanup errors

# =============================================================================
# MOCK WEBSOCKET IMPLEMENTATIONS
# =============================================================================

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
        self.should_fail_receive = False
        self.should_disconnect = False
        
    def _init_connection_info(self):
        """Initialize connection information"""
        self.client_info = {
            "host": "127.0.0.1",
            "port": 8000,
            "user_agent": "test-client"
        }
        
    async def send_text(self, message: str):
        """Mock send_text method"""
        if self.should_fail_send:
            raise WebSocketDisconnect(code=1000)
        self.sent_messages.append(message)
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method"""
        message = json.dumps(data)
        await self.send_text(message)
        
    async def receive_text(self) -> str:
        """Mock receive_text method"""
        if self.should_fail_receive:
            raise WebSocketDisconnect(code=1000)
        return '{"type": "test", "data": "mock_message"}'
        
    async def receive_json(self) -> Dict[str, Any]:
        """Mock receive_json method"""
        text = await self.receive_text()
        return json.loads(text)
        
    async def close(self, code: int = 1000):
        """Mock close method"""
        self.state = WebSocketState.DISCONNECTED
        
    def simulate_disconnect(self):
        """Simulate connection disconnect"""
        self.should_disconnect = True
        self.state = WebSocketState.DISCONNECTED

class MockWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocket] = {}
        self.broadcast_messages = []
        
    async def connect(self, websocket: MockWebSocket, user_id: str):
        """Mock connect method"""
        self.connections[user_id] = websocket
        
    async def disconnect(self, user_id: str):
        """Mock disconnect method"""
        if user_id in self.connections:
            await self.connections[user_id].close()
            del self.connections[user_id]
            
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Mock send_message method"""
        if user_id in self.connections:
            await self.connections[user_id].send_json(message)
            
    async def broadcast(self, message: Dict[str, Any]):
        """Mock broadcast method"""
        self.broadcast_messages.append(message)
        for connection in self.connections.values():
            await connection.send_json(message)
            
    def get_active_connections(self) -> int:
        """Get number of active connections"""
        return len(self.connections)

# =============================================================================
# WEBSOCKET TEST FIXTURES
# =============================================================================

@pytest.fixture
async def mock_websocket():
    """Create a mock WebSocket for testing"""
    yield MockWebSocket()

@pytest.fixture  
async def mock_websocket_manager():
    """Create a mock WebSocket manager for testing"""
    yield MockWebSocketManager()

@pytest.fixture
async def websocket_test_client():
    """Create WebSocket test client with authentication"""
    class WebSocketTestClient:
        def __init__(self, base_url: str = "ws://localhost:8000"):
            self.base_url = base_url
            self.connection = None
            
        async def connect(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
            """Connect to WebSocket endpoint"""
            url = f"{self.base_url}{endpoint}"
            self.connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url, headers
            )
            yield self.connection
            
        async def send_message(self, message: Dict[str, Any]):
            """Send message through connection"""
            if not self.connection:
                raise RuntimeError("Not connected to WebSocket")
            await WebSocketTestHelpers.send_test_message(self.connection, message)
            
        async def receive_message(self) -> Dict[str, Any]:
            """Receive message from connection"""
            if not self.connection:
                raise RuntimeError("Not connected to WebSocket")
            yield await WebSocketTestHelpers.receive_test_message(self.connection)
            
        async def close(self):
            """Close WebSocket connection"""
            if self.connection:
                await WebSocketTestHelpers.close_test_connection(self.connection)
                self.connection = None
    
    yield WebSocketTestClient()

# =============================================================================
# PERFORMANCE TESTING UTILITIES
# =============================================================================

class WebSocketPerformanceMonitor:
    """Monitor WebSocket performance in tests"""
    
    def __init__(self):
        self.metrics = {}
        self.message_counts = {}
        
    def start_monitoring(self, test_name: str):
        """Start monitoring for a test"""
        self.metrics[test_name] = {
            "start_time": time.time(),
            "messages_sent": 0,
            "messages_received": 0,
            "errors": []
        }
        
    def record_message_sent(self, test_name: str):
        """Record a message sent"""
        if test_name in self.metrics:
            self.metrics[test_name]["messages_sent"] += 1
            
    def record_message_received(self, test_name: str):
        """Record a message received"""
        if test_name in self.metrics:
            self.metrics[test_name]["messages_received"] += 1
            
    def record_error(self, test_name: str, error: str):
        """Record an error"""
        if test_name in self.metrics:
            self.metrics[test_name]["errors"].append(error)
            
    def stop_monitoring(self, test_name: str):
        """Stop monitoring and return metrics"""
        if test_name in self.metrics:
            self.metrics[test_name]["end_time"] = time.time()
            self.metrics[test_name]["duration"] = (
                self.metrics[test_name]["end_time"] - 
                self.metrics[test_name]["start_time"]
            )
            return self.metrics[test_name]
        return None

@pytest.fixture
def websocket_performance_monitor():
    """WebSocket performance monitoring fixture"""
    return WebSocketPerformanceMonitor()

# =============================================================================
# HIGH-VOLUME TESTING UTILITIES  
# =============================================================================

class HighVolumeWebSocketServer:
    """Mock high-volume WebSocket server for performance testing"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.server = None
        self.connected_clients = set()
        
    async def start(self):
        """Start the high-volume test server"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        async def handler(websocket, path):
            self.connected_clients.add(websocket)
            try:
                await websocket.wait_closed()
            finally:
                self.connected_clients.discard(websocket)
                
        self.server = await websockets.serve(handler, "localhost", self.port)
        
    async def stop(self):
        """Stop the test server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

class HighVolumeThroughputClient:
    """High-volume throughput client for performance testing"""
    
    def __init__(self, uri: str, token: str, client_id: str):
        self.uri = uri
        self.token = token
        self.client_id = client_id
        self.websocket = None
        self.message_count = 0
        
    async def connect(self):
        """Connect to WebSocket with authentication"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        self.websocket = await websockets.connect(self.uri, extra_headers=headers)
        
    async def send_bulk_messages(self, count: int, message_template: Dict[str, Any]):
        """Send bulk messages for throughput testing"""
        if not self.websocket:
            raise RuntimeError("Not connected")
            
        for i in range(count):
            message = {**message_template, "sequence": i, "client_id": self.client_id}
            await self.websocket.send(json.dumps(message))
            self.message_count += 1
            
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

@pytest.fixture
async def high_volume_server():
    """High-volume WebSocket server fixture"""
    if not WEBSOCKETS_AVAILABLE:
        yield None
        return
        
    server = HighVolumeWebSocketServer()
    await server.start()
    await asyncio.sleep(1.0)  # Allow server startup time
    yield server
    await server.stop()

@pytest.fixture
async def throughput_client(common_test_user, high_volume_server):
    """High-volume throughput client fixture"""
    if not WEBSOCKETS_AVAILABLE:
        yield AsyncMock()
        return
        
    websocket_uri = "ws://localhost:8765"
    client = HighVolumeThroughputClient(
        websocket_uri, 
        "test-token", 
        "primary-client"
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await client.connect()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1.0)
    
    yield client
    
    try:
        await client.disconnect()
    except Exception:
        pass  # Ignore cleanup errors

# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_websocket_message(message: Dict[str, Any], required_fields: List[str]):
    """Validate WebSocket message structure"""
    for field in required_fields:
        if field not in message:
            raise AssertionError(f"Required field '{field}' missing from message")
    return True

def assert_websocket_response_time(duration: float, max_duration: float = 1.0):
    """Assert WebSocket response time is within limits"""
    if duration > max_duration:
        raise AssertionError(f"WebSocket response took {duration:.3f}s (max: {max_duration}s)")
    return True