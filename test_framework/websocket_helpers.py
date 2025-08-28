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
    """Unified helper utilities for WebSocket testing with enhanced connection stability"""
    
    @staticmethod
    async def create_test_websocket_connection(
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        """Create a test WebSocket connection with proper authentication and retries"""
        if not WEBSOCKETS_AVAILABLE:
            raise pytest.skip("websockets library not available")
        
        # Extract JWT token from headers for subprotocol authentication
        auth_token = None
        subprotocols = []
        
        if headers and "Authorization" in headers:
            auth_header = headers["Authorization"]
            if auth_header.startswith("Bearer "):
                auth_token = auth_header.replace("Bearer ", "")
                # Use jwt-auth subprotocol for authentication
                subprotocols = ["jwt-auth"]
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Try connection with retries - handle different websockets API versions
                try:
                    # Try newer websockets API (>= 10.0)
                    if subprotocols:
                        connection = await asyncio.wait_for(
                            websockets.connect(
                                url,
                                additional_headers=headers or {},
                                subprotocols=subprotocols
                            ),
                            timeout=timeout
                        )
                    else:
                        connection = await asyncio.wait_for(
                            websockets.connect(
                                url,
                                additional_headers=headers or {}
                            ),
                            timeout=timeout
                        )
                except TypeError:
                    # Fallback to older API (< 10.0)
                    if subprotocols:
                        connection = await asyncio.wait_for(
                            websockets.connect(
                                url,
                                extra_headers=headers or {},
                                subprotocols=subprotocols
                            ),
                            timeout=timeout
                        )
                    else:
                        connection = await asyncio.wait_for(
                            websockets.connect(
                                url,
                                extra_headers=headers or {}
                            ),
                            timeout=timeout
                        )
                
                # Test basic connectivity by sending a ping
                await connection.ping()
                
                return connection
                
            except (websockets.exceptions.ConnectionClosedError, 
                   websockets.exceptions.InvalidStatusCode,
                   asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Wait with exponential backoff
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
            except Exception as e:
                last_error = e
                break
        
        error_msg = f"Failed to create WebSocket connection after {max_retries} attempts: {last_error}"
        raise ConnectionError(error_msg)
    
    @staticmethod
    async def send_test_message(
        websocket,
        message: Dict[str, Any],
        timeout: float = 5.0
    ):
        """Send a test message through WebSocket with connection validation"""
        try:
            # Check if connection is still alive
            if hasattr(websocket, 'closed') and websocket.closed:
                raise RuntimeError("WebSocket connection is closed")
            elif hasattr(websocket, 'state') and websocket.state.name != 'OPEN':
                raise RuntimeError("WebSocket connection is not open")
            
            message_json = json.dumps(message)
            await asyncio.wait_for(
                websocket.send(message_json),
                timeout=timeout
            )
        except websockets.exceptions.ConnectionClosed as e:
            raise RuntimeError(f"WebSocket connection closed while sending message: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to send WebSocket message: {e}")
    
    @staticmethod
    async def receive_test_message(
        websocket,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Receive and parse a test message from WebSocket with proper error handling"""
        try:
            # Check if connection is still alive
            if hasattr(websocket, 'closed') and websocket.closed:
                raise RuntimeError("WebSocket connection is closed")
            elif hasattr(websocket, 'state') and websocket.state.name != 'OPEN':
                raise RuntimeError("WebSocket connection is not open")
            
            message_raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=timeout
            )
            
            # Handle different message types
            try:
                return json.loads(message_raw)
            except json.JSONDecodeError:
                # Handle text messages that aren't JSON
                return {"type": "text", "content": message_raw}
                
        except websockets.exceptions.ConnectionClosed as e:
            raise RuntimeError(f"WebSocket connection closed while receiving message: {e}")
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timeout waiting for WebSocket message (timeout: {timeout}s)")
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
        self._closed = False
        
    async def connect(self, websocket: MockWebSocket, user_id: str):
        """Mock connect method"""
        if not self._closed:
            self.connections[user_id] = websocket
        
    async def disconnect(self, user_id: str):
        """Mock disconnect method"""
        if user_id in self.connections:
            await self.connections[user_id].close()
            del self.connections[user_id]
    
    async def close_all_connections(self):
        """Close all active connections"""
        if self._closed:
            return
        
        for user_id, websocket in list(self.connections.items()):
            try:
                await websocket.close()
            except Exception:
                pass
        
        self.connections.clear()
        self._closed = True
    
    async def cleanup(self):
        """Comprehensive cleanup of manager resources"""
        await self.close_all_connections()
        self.broadcast_messages.clear()
            
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
            """Connect to WebSocket endpoint with enhanced error handling"""
            url = f"{self.base_url}{endpoint}"
            try:
                self.connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url, headers, timeout=10.0, max_retries=3
                )
                yield self.connection
            except Exception as e:
                raise ConnectionError(f"Failed to connect to WebSocket endpoint {endpoint}: {e}")
            
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
        """Start the high-volume test server with better error handling"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        async def handler(websocket, path):
            self.connected_clients.add(websocket)
            try:
                # Send welcome message to confirm connection
                await websocket.send(json.dumps({"type": "connected", "timestamp": time.time()}))
                await websocket.wait_closed()
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.connected_clients.discard(websocket)
                
        try:
            self.server = await websockets.serve(handler, "localhost", self.port)
        except OSError as e:
            if "Address already in use" in str(e):
                # Try a different port
                self.port += 1
                self.server = await websockets.serve(handler, "localhost", self.port)
            else:
                raise
        
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
        """Connect to WebSocket with authentication using proper subprotocol"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # Try newer websockets API first
            try:
                self.websocket = await websockets.connect(
                    self.uri, 
                    additional_headers=headers,
                    subprotocols=["jwt-auth"]
                )
            except TypeError:
                # Fallback to older API
                self.websocket = await websockets.connect(
                    self.uri, 
                    extra_headers=headers,
                    subprotocols=["jwt-auth"]
                )
        except Exception:
            # Fallback to basic connection without subprotocol
            try:
                self.websocket = await websockets.connect(
                    self.uri, 
                    additional_headers=headers
                )
            except TypeError:
                self.websocket = await websockets.connect(
                    self.uri, 
                    extra_headers=headers
                )
        
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
    """High-volume throughput client fixture with enhanced connection stability"""
    if not WEBSOCKETS_AVAILABLE:
        yield AsyncMock()
        return
        
    websocket_uri = "ws://localhost:8765"
    client = HighVolumeThroughputClient(
        websocket_uri, 
        "test-token", 
        "primary-client"
    )
    
    max_retries = 5  # Increased retries for stability
    for attempt in range(max_retries):
        try:
            await client.connect()
            # Test connection is working by sending a ping
            test_message = {"type": "ping", "timestamp": time.time()}
            await client.websocket.send(json.dumps(test_message))
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"Unable to establish minimum WebSocket connections after {max_retries} attempts: {e}")
            # Exponential backoff
            await asyncio.sleep(0.5 * (2 ** attempt))
    
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

async def ensure_websocket_service_ready(base_url: str = "http://localhost:8000", max_wait: float = 30.0) -> bool:
    """Ensure WebSocket service is ready before running tests"""
    import httpx
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            async with httpx.AsyncClient() as client:
                health_response = await client.get(f"{base_url}/ws/health", timeout=2.0)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    if health_data.get("status") == "healthy":
                        return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    
    return False

async def establish_minimum_websocket_connections(connection_count: int = 1, timeout: float = 10.0) -> List:
    """Establish minimum required WebSocket connections for E2E tests"""
    connections = []
    
    # First ensure service is ready
    if not await ensure_websocket_service_ready():
        raise RuntimeError("WebSocket service not ready")
    
    for i in range(connection_count):
        try:
            # Use test endpoint which doesn't require authentication
            url = "ws://localhost:8000/ws/test"
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url, timeout=timeout
            )
            connections.append(connection)
        except Exception as e:
            # Clean up any successful connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
            raise RuntimeError(f"Unable to establish minimum WebSocket connections: {e}")
    
    return connections