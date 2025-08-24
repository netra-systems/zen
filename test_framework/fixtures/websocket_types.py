"""
WebSocket Types Test Fixtures

Provides WebSocket-related fixtures and types for testing.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime


class MockWebSocketState(str, Enum):
    """Mock WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MockMessageType(str, Enum):
    """Mock WebSocket message types."""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    AGENT_RESPONSE = "agent_response"
    USER_INPUT = "user_input"
    SYSTEM_NOTIFICATION = "system_notification"


@dataclass
class MockWebSocketMessage:
    """Mock WebSocket message."""
    type: MockMessageType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "connection_id": self.connection_id
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MockWebSocketMessage':
        """Create from dictionary."""
        return cls(
            type=MockMessageType(data.get("type", "message")),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            user_id=data.get("user_id"),
            connection_id=data.get("connection_id")
        )


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str = None, user_id: str = None):
        self.connection_id = connection_id or f"conn_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.state = MockWebSocketState.DISCONNECTED
        self.connected_at: Optional[float] = None
        self.disconnected_at: Optional[float] = None
        self.last_activity = time.time()
        
        # Message queues
        self.sent_messages: List[MockWebSocketMessage] = []
        self.received_messages: List[MockWebSocketMessage] = []
        self.pending_messages: List[MockWebSocketMessage] = []
        
        # Event handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_handlers: List[Callable] = []
        self.disconnection_handlers: List[Callable] = []
        
        # Statistics
        self.message_count = 0
        self.error_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
    
    async def connect(self) -> bool:
        """Simulate WebSocket connection."""
        try:
            self.state = MockWebSocketState.CONNECTING
            await asyncio.sleep(0.01)  # Simulate connection delay
            
            self.state = MockWebSocketState.CONNECTED
            self.connected_at = time.time()
            self.last_activity = time.time()
            
            # Trigger connection handlers
            for handler in self.connection_handlers:
                try:
                    await handler(self)
                except Exception as e:
                    print(f"Connection handler error: {e}")
            
            return True
            
        except Exception as e:
            self.state = MockWebSocketState.ERROR
            print(f"Connection error: {e}")
            return False
    
    async def disconnect(self, code: int = 1000, reason: str = "Normal closure"):
        """Simulate WebSocket disconnection."""
        if self.state in [MockWebSocketState.DISCONNECTED, MockWebSocketState.ERROR]:
            return
        
        self.state = MockWebSocketState.DISCONNECTING
        await asyncio.sleep(0.01)  # Simulate disconnection delay
        
        self.state = MockWebSocketState.DISCONNECTED
        self.disconnected_at = time.time()
        
        # Trigger disconnection handlers
        for handler in self.disconnection_handlers:
            try:
                await handler(self, code, reason)
            except Exception as e:
                print(f"Disconnection handler error: {e}")
    
    async def send_message(self, message: Union[MockWebSocketMessage, Dict[str, Any], str]):
        """Send a message through the WebSocket."""
        if self.state != MockWebSocketState.CONNECTED:
            raise RuntimeError(f"Cannot send message, connection state: {self.state}")
        
        if isinstance(message, str):
            try:
                data = json.loads(message)
                ws_message = MockWebSocketMessage.from_dict(data)
            except json.JSONDecodeError:
                ws_message = MockWebSocketMessage(
                    type=MockMessageType.MESSAGE,
                    data={"text": message}
                )
        elif isinstance(message, dict):
            ws_message = MockWebSocketMessage.from_dict(message)
        else:
            ws_message = message
        
        ws_message.connection_id = self.connection_id
        ws_message.user_id = ws_message.user_id or self.user_id
        
        self.sent_messages.append(ws_message)
        self.message_count += 1
        self.bytes_sent += len(ws_message.to_json())
        self.last_activity = time.time()
        
        # Process message handlers
        handler = self.message_handlers.get(ws_message.type)
        if handler:
            try:
                await handler(ws_message)
            except Exception as e:
                self.error_count += 1
                print(f"Message handler error: {e}")
    
    async def receive_message(self) -> Optional[MockWebSocketMessage]:
        """Receive a message from the WebSocket."""
        if self.state != MockWebSocketState.CONNECTED:
            return None
        
        if self.received_messages:
            message = self.received_messages.pop(0)
            self.bytes_received += len(message.to_json())
            self.last_activity = time.time()
            return message
        
        # Simulate periodic heartbeat
        await asyncio.sleep(0.01)
        heartbeat = MockWebSocketMessage(
            type=MockMessageType.HEARTBEAT,
            data={"timestamp": time.time()},
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        return heartbeat
    
    def add_received_message(self, message: Union[MockWebSocketMessage, Dict[str, Any]]):
        """Add a message to the received queue."""
        if isinstance(message, dict):
            message = MockWebSocketMessage.from_dict(message)
        
        message.connection_id = self.connection_id
        message.user_id = message.user_id or self.user_id
        self.received_messages.append(message)
    
    def on_message(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
    
    def on_connect(self, handler: Callable):
        """Register a connection handler."""
        self.connection_handlers.append(handler)
    
    def on_disconnect(self, handler: Callable):
        """Register a disconnection handler."""
        self.disconnection_handlers.append(handler)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        uptime = (time.time() - self.connected_at) if self.connected_at else 0
        
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "state": self.state,
            "connected_at": self.connected_at,
            "uptime_seconds": uptime,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "last_activity": self.last_activity
        }


class MockWebSocketManager:
    """Mock WebSocket manager for testing multiple connections."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.user_connections: Dict[str, List[str]] = {}
        self.message_history: List[Dict[str, Any]] = []
        
        # Broadcasting
        self.broadcast_handlers: List[Callable] = []
        self.room_memberships: Dict[str, Set[str]] = {}
        
        # Statistics
        self.total_connections = 0
        self.active_connections = 0
        self.messages_processed = 0
    
    async def add_connection(self, connection: MockWebSocketConnection) -> bool:
        """Add a connection to the manager."""
        try:
            await connection.connect()
            
            self.connections[connection.connection_id] = connection
            self.total_connections += 1
            self.active_connections += 1
            
            # Track user connections
            if connection.user_id:
                if connection.user_id not in self.user_connections:
                    self.user_connections[connection.user_id] = []
                self.user_connections[connection.user_id].append(connection.connection_id)
            
            return True
            
        except Exception as e:
            print(f"Failed to add connection: {e}")
            return False
    
    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection from the manager."""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        await connection.disconnect()
        
        # Clean up tracking
        if connection.user_id and connection.user_id in self.user_connections:
            user_conns = self.user_connections[connection.user_id]
            if connection_id in user_conns:
                user_conns.remove(connection_id)
            if not user_conns:
                del self.user_connections[connection.user_id]
        
        del self.connections[connection_id]
        self.active_connections -= 1
        
        return True
    
    async def broadcast_message(self, message: Union[MockWebSocketMessage, Dict[str, Any]], 
                              exclude_connections: List[str] = None):
        """Broadcast a message to all connections."""
        exclude_connections = exclude_connections or []
        
        for conn_id, connection in self.connections.items():
            if conn_id not in exclude_connections and connection.state == MockWebSocketState.CONNECTED:
                try:
                    await connection.send_message(message)
                except Exception as e:
                    print(f"Broadcast error to {conn_id}: {e}")
        
        # Record broadcast
        if isinstance(message, dict):
            message_data = message
        else:
            message_data = message.to_dict()
        
        self.message_history.append({
            "type": "broadcast",
            "message": message_data,
            "timestamp": time.time(),
            "target_count": len(self.connections) - len(exclude_connections)
        })
    
    async def send_to_user(self, user_id: str, message: Union[MockWebSocketMessage, Dict[str, Any]]):
        """Send a message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return False
        
        success_count = 0
        for conn_id in self.user_connections[user_id]:
            connection = self.connections.get(conn_id)
            if connection and connection.state == MockWebSocketState.CONNECTED:
                try:
                    await connection.send_message(message)
                    success_count += 1
                except Exception as e:
                    print(f"Send to user error ({conn_id}): {e}")
        
        return success_count > 0
    
    def join_room(self, connection_id: str, room: str) -> bool:
        """Add connection to a room."""
        if connection_id not in self.connections:
            return False
        
        if room not in self.room_memberships:
            self.room_memberships[room] = set()
        
        self.room_memberships[room].add(connection_id)
        return True
    
    def leave_room(self, connection_id: str, room: str) -> bool:
        """Remove connection from a room."""
        if room in self.room_memberships and connection_id in self.room_memberships[room]:
            self.room_memberships[room].remove(connection_id)
            if not self.room_memberships[room]:
                del self.room_memberships[room]
            return True
        return False
    
    async def broadcast_to_room(self, room: str, message: Union[MockWebSocketMessage, Dict[str, Any]]):
        """Broadcast message to all connections in a room."""
        if room not in self.room_memberships:
            return
        
        for conn_id in self.room_memberships[room]:
            connection = self.connections.get(conn_id)
            if connection and connection.state == MockWebSocketState.CONNECTED:
                try:
                    await connection.send_message(message)
                except Exception as e:
                    print(f"Room broadcast error to {conn_id}: {e}")
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "unique_users": len(self.user_connections),
            "rooms": len(self.room_memberships),
            "messages_processed": self.messages_processed,
            "message_history_size": len(self.message_history)
        }


# Fixture factory functions

def create_mock_websocket_connection(user_id: str = "test_user") -> MockWebSocketConnection:
    """Create a mock WebSocket connection."""
    return MockWebSocketConnection(user_id=user_id)

def create_mock_websocket_manager() -> MockWebSocketManager:
    """Create a mock WebSocket manager."""
    return MockWebSocketManager()

def create_mock_websocket_message(message_type: MockMessageType = MockMessageType.MESSAGE,
                                 data: Dict[str, Any] = None) -> MockWebSocketMessage:
    """Create a mock WebSocket message."""
    return MockWebSocketMessage(
        type=message_type,
        data=data or {"content": "test message"}
    )

async def setup_mock_websocket_scenario(user_count: int = 3) -> Dict[str, Any]:
    """Set up a complete WebSocket testing scenario."""
    manager = MockWebSocketManager()
    connections = []
    
    for i in range(user_count):
        user_id = f"user_{i+1}"
        connection = MockWebSocketConnection(user_id=user_id)
        await manager.add_connection(connection)
        connections.append(connection)
    
    return {
        "manager": manager,
        "connections": connections,
        "user_ids": [f"user_{i+1}" for i in range(user_count)]
    }

def create_websocket_test_messages() -> List[MockWebSocketMessage]:
    """Create a variety of test WebSocket messages."""
    return [
        MockWebSocketMessage(
            type=MockMessageType.CONNECT,
            data={"user_id": "test_user"}
        ),
        MockWebSocketMessage(
            type=MockMessageType.USER_INPUT,
            data={"content": "Hello, this is a test message"}
        ),
        MockWebSocketMessage(
            type=MockMessageType.AGENT_RESPONSE,
            data={"response": "I understand your message", "agent_id": "test_agent"}
        ),
        MockWebSocketMessage(
            type=MockMessageType.HEARTBEAT,
            data={"timestamp": time.time()}
        ),
        MockWebSocketMessage(
            type=MockMessageType.SYSTEM_NOTIFICATION,
            data={"notification": "System maintenance in 5 minutes"}
        ),
        MockWebSocketMessage(
            type=MockMessageType.DISCONNECT,
            data={"reason": "User logout"}
        )
    ]

def simulate_websocket_conversation(connection: MockWebSocketConnection, 
                                  message_count: int = 5) -> List[MockWebSocketMessage]:
    """Simulate a WebSocket conversation."""
    messages = []
    
    for i in range(message_count):
        if i % 2 == 0:
            # User message
            message = MockWebSocketMessage(
                type=MockMessageType.USER_INPUT,
                data={"content": f"User message {i+1}"}
            )
        else:
            # Agent response
            message = MockWebSocketMessage(
                type=MockMessageType.AGENT_RESPONSE,
                data={"response": f"Agent response to message {i}"}
            )
        
        connection.add_received_message(message)
        messages.append(message)
    
    return messages

# WebSocket test data

def get_websocket_test_data() -> Dict[str, Any]:
    """Get comprehensive WebSocket test data."""
    return {
        "connection_scenarios": [
            {"user_id": "regular_user", "expected_state": "connected"},
            {"user_id": "admin_user", "expected_state": "connected"},
            {"user_id": None, "expected_state": "error"}  # No user ID
        ],
        "message_types": [
            MockMessageType.CONNECT,
            MockMessageType.MESSAGE,
            MockMessageType.HEARTBEAT,
            MockMessageType.AGENT_RESPONSE,
            MockMessageType.DISCONNECT
        ],
        "test_rooms": ["general", "admin", "notifications"],
        "error_scenarios": [
            {"type": "connection_lost", "expected_recovery": True},
            {"type": "invalid_message", "expected_recovery": False},
            {"type": "rate_limit", "expected_recovery": True}
        ]
    }


class BidirectionalTypeTest:
    """Test class for bidirectional WebSocket type validation."""
    
    def __init__(self):
        self.test_cases = []
        self.validation_results = []
    
    def add_test_case(self, name: str, input_data: Any, expected_output: Any):
        """Add a test case for type validation."""
        self.test_cases.append({
            "name": name,
            "input": input_data,
            "expected": expected_output
        })
    
    def validate_message_type(self, message: MockWebSocketMessage) -> bool:
        """Validate message type consistency."""
        try:
            # Check if message type is valid
            if not isinstance(message.type, (str, MockMessageType)):
                return False
            
            # Check if data is serializable
            json.dumps(message.data)
            
            # Check if message can be reconstructed
            reconstructed = MockWebSocketMessage.from_dict(message.to_dict())
            return reconstructed.type == message.type and reconstructed.data == message.data
            
        except Exception:
            return False
    
    def run_bidirectional_test(self) -> Dict[str, Any]:
        """Run bidirectional type validation tests."""
        results = {
            "passed": 0,
            "failed": 0,
            "total": len(self.test_cases),
            "details": []
        }
        
        for test_case in self.test_cases:
            try:
                # Create message from input
                message = MockWebSocketMessage(
                    type=test_case["input"].get("type", MockMessageType.USER_INPUT),
                    data=test_case["input"].get("data", {})
                )
                
                # Validate bidirectional conversion
                is_valid = self.validate_message_type(message)
                
                if is_valid:
                    results["passed"] += 1
                    results["details"].append({
                        "name": test_case["name"],
                        "status": "passed"
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "name": test_case["name"],
                        "status": "failed",
                        "error": "Type validation failed"
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "name": test_case["name"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return results