"""Real WebSocket Test Client

Professional WebSocket client for testing real-time connections to the Netra backend.
Supports authentication, message protocols, reconnection, and concurrent connections.

Business Value: Ensures WebSocket reliability for real-time chat features (20% revenue impact).
"""

import asyncio
import json
import time
import uuid
import websockets
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    messages_sent: int = 0
    messages_received: int = 0
    reconnection_count: int = 0
    last_ping_time: Optional[datetime] = None
    last_pong_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class TestMessage:
    """Structured test message"""
    message_type: str
    content: str
    thread_id: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket protocol format"""
        message = {
            "type": self.message_type,
            "payload": {
                "content": self.content,
                "timestamp": (self.timestamp or datetime.now()).isoformat()
            }
        }
        
        if self.thread_id:
            message["payload"]["thread_id"] = self.thread_id
            
        return message


class WebSocketTestClient:
    """Professional WebSocket test client for Netra backend"""
    
    def __init__(self, base_url: str = "ws://localhost:8000", 
                 auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        self.client_id = str(uuid.uuid4())
        self.metrics = ConnectionMetrics()
        self.message_handlers: List[Callable] = []
        self.reconnection_enabled = True
        self.max_reconnection_attempts = 5
        self.reconnection_delay = 2.0
        self._stop_event = asyncio.Event()
        
    def add_message_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add message handler for incoming messages"""
        self.message_handlers.append(handler)
        
    def get_connection_url(self) -> str:
        """Build WebSocket connection URL with authentication"""
        ws_url = f"{self.base_url}/ws"
        if self.auth_token:
            ws_url += f"?token={self.auth_token}"
        return ws_url
        
    async def connect(self) -> bool:
        """Establish WebSocket connection with authentication"""
        if self.state == ConnectionState.CONNECTED:
            return True
            
        self.state = ConnectionState.CONNECTING
        url = self.get_connection_url()
        
        try:
            logger.info(f"[CLIENT {self.client_id[:8]}] Connecting to {url}")
            self.websocket = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.state = ConnectionState.CONNECTED
            self.metrics.connected_at = datetime.now(timezone.utc)
            logger.info(f"[CLIENT {self.client_id[:8]}] Connected successfully")
            
            # Start message listening task
            asyncio.create_task(self._message_listener())
            asyncio.create_task(self._ping_task())
            
            return True
            
        except Exception as e:
            self.state = ConnectionState.FAILED
            error_msg = f"Connection failed: {str(e)}"
            self.metrics.errors.append(error_msg)
            logger.error(f"[CLIENT {self.client_id[:8]}] {error_msg}")
            return False
            
    async def disconnect(self, code: int = 1000, reason: str = "Client disconnect"):
        """Gracefully disconnect from WebSocket"""
        if self.websocket and self.state == ConnectionState.CONNECTED:
            try:
                logger.info(f"[CLIENT {self.client_id[:8]}] Disconnecting: {reason}")
                await self.websocket.close(code=code, reason=reason)
            except Exception as e:
                logger.warning(f"[CLIENT {self.client_id[:8]}] Disconnect error: {e}")
                
        self.state = ConnectionState.DISCONNECTED
        self.metrics.disconnected_at = datetime.now(timezone.utc)
        self._stop_event.set()
        
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send structured message to WebSocket"""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            logger.error(f"[CLIENT {self.client_id[:8]}] Cannot send - not connected")
            return False
            
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            self.metrics.messages_sent += 1
            
            logger.info(f"[CLIENT {self.client_id[:8]}] Sent: {message.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            error_msg = f"Send failed: {str(e)}"
            self.metrics.errors.append(error_msg)
            logger.error(f"[CLIENT {self.client_id[:8]}] {error_msg}")
            return False
            
    async def send_test_message(self, test_message: TestMessage) -> bool:
        """Send structured test message"""
        return await self.send_message(test_message.to_websocket_message())
        
    async def send_chat_message(self, content: str, 
                              thread_id: Optional[str] = None) -> bool:
        """Send chat message with proper protocol"""
        message = {
            "type": "chat_message",
            "payload": {
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "client_id": self.client_id
            }
        }
        
        if thread_id:
            message["payload"]["thread_id"] = thread_id
            
        return await self.send_message(message)
        
    async def send_ping(self) -> bool:
        """Send ping message"""
        ping_message = {
            "type": "ping",
            "payload": {
                "timestamp": datetime.now().isoformat(),
                "client_id": self.client_id
            }
        }
        
        self.metrics.last_ping_time = datetime.now(timezone.utc)
        return await self.send_message(ping_message)
        
    async def _message_listener(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for raw_message in self.websocket:
                try:
                    message = json.loads(raw_message)
                    await self._handle_received_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"[CLIENT {self.client_id[:8]}] JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"[CLIENT {self.client_id[:8]}] Message handling error: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"[CLIENT {self.client_id[:8]}] Connection closed: {e}")
            await self._handle_connection_lost()
        except Exception as e:
            logger.error(f"[CLIENT {self.client_id[:8]}] Message listener error: {e}")
            await self._handle_connection_lost()
            
    async def _handle_received_message(self, message: Dict[str, Any]):
        """Handle received message from server"""
        self.metrics.messages_received += 1
        message_type = message.get("type", "unknown")
        
        logger.info(f"[CLIENT {self.client_id[:8]}] Received: {message_type}")
        
        # Handle pong messages
        if message_type == "pong":
            self.metrics.last_pong_time = datetime.now(timezone.utc)
            
        # Call registered handlers
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"[CLIENT {self.client_id[:8]}] Handler error: {e}")
                
    async def _handle_connection_lost(self):
        """Handle connection loss and attempt reconnection"""
        if self.state == ConnectionState.CONNECTED:
            self.state = ConnectionState.DISCONNECTED
            
        if self.reconnection_enabled:
            await self._attempt_reconnection()
            
    async def _attempt_reconnection(self):
        """Attempt to reconnect with exponential backoff"""
        self.state = ConnectionState.RECONNECTING
        
        for attempt in range(self.max_reconnection_attempts):
            try:
                logger.info(f"[CLIENT {self.client_id[:8]}] Reconnection attempt {attempt + 1}")
                
                await asyncio.sleep(self.reconnection_delay * (2 ** attempt))
                
                if await self.connect():
                    self.metrics.reconnection_count += 1
                    logger.info(f"[CLIENT {self.client_id[:8]}] Reconnected successfully")
                    return
                    
            except Exception as e:
                logger.error(f"[CLIENT {self.client_id[:8]}] Reconnection failed: {e}")
                
        self.state = ConnectionState.FAILED
        logger.error(f"[CLIENT {self.client_id[:8]}] Max reconnection attempts exceeded")
        
    async def _ping_task(self):
        """Periodic ping task"""
        try:
            while self.state == ConnectionState.CONNECTED and not self._stop_event.is_set():
                await asyncio.sleep(30)  # Ping every 30 seconds
                if self.state == ConnectionState.CONNECTED:
                    await self.send_ping()
        except Exception as e:
            logger.error(f"[CLIENT {self.client_id[:8]}] Ping task error: {e}")
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics"""
        uptime = None
        if self.metrics.connected_at:
            if self.metrics.disconnected_at:
                uptime = (self.metrics.disconnected_at - self.metrics.connected_at).total_seconds()
            else:
                uptime = (datetime.now(timezone.utc) - self.metrics.connected_at).total_seconds()
                
        return {
            "client_id": self.client_id,
            "state": self.state.value,
            "uptime_seconds": uptime,
            "messages_sent": self.metrics.messages_sent,
            "messages_received": self.metrics.messages_received,
            "reconnection_count": self.metrics.reconnection_count,
            "error_count": len(self.metrics.errors),
            "last_errors": self.metrics.errors[-5:] if self.metrics.errors else [],
            "ping_latency_ms": self._calculate_ping_latency()
        }
        
    def _calculate_ping_latency(self) -> Optional[float]:
        """Calculate ping latency if available"""
        if (self.metrics.last_ping_time and self.metrics.last_pong_time and
            self.metrics.last_pong_time > self.metrics.last_ping_time):
            delta = self.metrics.last_pong_time - self.metrics.last_ping_time
            return delta.total_seconds() * 1000
        return None
        
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.state == ConnectionState.CONNECTED
        
    def is_healthy(self) -> bool:
        """Check if client is healthy"""
        return self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]


class ConcurrentWebSocketTester:
    """Manages multiple concurrent WebSocket test clients"""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.clients: List[WebSocketTestClient] = []
        self.test_tokens = []
        
    def add_test_token(self, token: str):
        """Add authentication token for testing"""
        self.test_tokens.append(token)
        
    async def create_client(self, auth_token: Optional[str] = None) -> WebSocketTestClient:
        """Create and configure new test client"""
        if not auth_token and self.test_tokens:
            auth_token = self.test_tokens[len(self.clients) % len(self.test_tokens)]
            
        client = WebSocketTestClient(self.base_url, auth_token)
        self.clients.append(client)
        return client
        
    async def connect_all_clients(self) -> Dict[str, bool]:
        """Connect all clients and return results"""
        results = {}
        
        connection_tasks = []
        for client in self.clients:
            task = asyncio.create_task(client.connect())
            connection_tasks.append((client.client_id, task))
            
        for client_id, task in connection_tasks:
            try:
                success = await task
                results[client_id] = success
            except Exception as e:
                logger.error(f"Connection task failed for {client_id}: {e}")
                results[client_id] = False
                
        return results
        
    async def disconnect_all_clients(self):
        """Disconnect all clients gracefully"""
        disconnect_tasks = []
        for client in self.clients:
            if client.is_connected():
                task = asyncio.create_task(client.disconnect())
                disconnect_tasks.append(task)
                
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
    async def broadcast_message(self, message: Dict[str, Any]) -> Dict[str, bool]:
        """Broadcast message to all connected clients"""
        results = {}
        
        send_tasks = []
        for client in self.clients:
            if client.is_connected():
                task = asyncio.create_task(client.send_message(message))
                send_tasks.append((client.client_id, task))
                
        for client_id, task in send_tasks:
            try:
                success = await task
                results[client_id] = success
            except Exception as e:
                logger.error(f"Broadcast failed for {client_id}: {e}")
                results[client_id] = False
                
        return results
        
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """Get metrics from all clients"""
        total_clients = len(self.clients)
        connected_clients = sum(1 for c in self.clients if c.is_connected())
        healthy_clients = sum(1 for c in self.clients if c.is_healthy())
        
        total_sent = sum(c.metrics.messages_sent for c in self.clients)
        total_received = sum(c.metrics.messages_received for c in self.clients)
        total_errors = sum(len(c.metrics.errors) for c in self.clients)
        
        return {
            "total_clients": total_clients,
            "connected_clients": connected_clients,
            "healthy_clients": healthy_clients,
            "connection_rate": connected_clients / total_clients if total_clients > 0 else 0,
            "health_rate": healthy_clients / total_clients if total_clients > 0 else 0,
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
            "total_errors": total_errors,
            "clients": [client.get_metrics() for client in self.clients]
        }


async def example_usage():
    """Example usage of the WebSocket test client"""
    
    # Single client test
    client = WebSocketTestClient("ws://localhost:8000", "test-auth-token")
    
    # Add message handler
    def handle_message(message):
        print(f"Received: {message}")
        
    client.add_message_handler(handle_message)
    
    # Connect and test
    if await client.connect():
        # Send test messages
        await client.send_chat_message("Hello from test client!")
        await asyncio.sleep(1)
        await client.send_ping()
        await asyncio.sleep(2)
        
        # Check metrics
        metrics = client.get_metrics()
        print(f"Client metrics: {metrics}")
        
        await client.disconnect()
        
    # Concurrent client test
    tester = ConcurrentWebSocketTester("ws://localhost:8000")
    tester.add_test_token("test-token-1")
    tester.add_test_token("test-token-2")
    
    # Create multiple clients
    clients = []
    for i in range(3):
        client = await tester.create_client()
        clients.append(client)
        
    # Connect all clients
    results = await tester.connect_all_clients()
    print(f"Connection results: {results}")
    
    # Broadcast test message
    test_message = {
        "type": "test_broadcast",
        "payload": {
            "content": "Broadcast test message",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    broadcast_results = await tester.broadcast_message(test_message)
    print(f"Broadcast results: {broadcast_results}")
    
    await asyncio.sleep(2)
    
    # Get aggregate metrics
    metrics = tester.get_aggregate_metrics()
    print(f"Aggregate metrics: {metrics}")
    
    # Cleanup
    await tester.disconnect_all_clients()


if __name__ == "__main__":
    asyncio.run(example_usage())