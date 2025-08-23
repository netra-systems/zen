"""
WebSocket mock implementations.
Consolidates WebSocket mocks from across the project.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock

from starlette.websockets import WebSocketState, WebSocketDisconnect


class MockWebSocket:
    """Mock WebSocket for testing connection behavior"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or self._generate_user_id()
        self.state = WebSocketState.CONNECTED
        self.sent_messages = []
        self.received_messages = []
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
        self.sent_messages.append({
            "type": "text",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method"""
        if self.should_fail_send:
            raise WebSocketDisconnect(code=1000)
        message = json.dumps(data)
        self.sent_messages.append({
            "type": "json",
            "content": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    async def receive_text(self) -> str:
        """Mock receive_text method"""
        if self.should_fail_receive:
            raise WebSocketDisconnect(code=1000)
        if self.received_messages:
            return self.received_messages.pop(0)
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
        
    def add_received_message(self, message: str):
        """Add a message to the received queue"""
        self.received_messages.append(message)
        
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages"""
        return self.sent_messages.copy()
        
    def clear_messages(self):
        """Clear message history"""
        self.sent_messages.clear()
        self.received_messages.clear()


class MockWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocket] = {}
        self.broadcast_messages = []
        self.connection_events = []
        
    async def connect(self, websocket: MockWebSocket, user_id: str):
        """Mock connect method"""
        self.connections[user_id] = websocket
        self.connection_events.append({
            "type": "connect",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    async def disconnect(self, user_id: str):
        """Mock disconnect method"""
        if user_id in self.connections:
            await self.connections[user_id].close()
            del self.connections[user_id]
            self.connection_events.append({
                "type": "disconnect",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Mock send_message method"""
        if user_id in self.connections:
            await self.connections[user_id].send_json(message)
            
    async def broadcast(self, message: Dict[str, Any]):
        """Mock broadcast method"""
        self.broadcast_messages.append({
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recipient_count": len(self.connections)
        })
        for connection in self.connections.values():
            await connection.send_json(message)
            
    def get_active_connections(self) -> int:
        """Get number of active connections"""
        return len(self.connections)
        
    def get_connection_events(self) -> List[Dict[str, Any]]:
        """Get connection events history"""
        return self.connection_events.copy()
        
    def get_broadcast_history(self) -> List[Dict[str, Any]]:
        """Get broadcast history"""
        return self.broadcast_messages.copy()


class MockWebSocketConnectionManager:
    """Mock WebSocket connection manager with advanced features"""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocket] = {}
        self.rooms: Dict[str, Set[str]] = {}
        self.message_queue: Dict[str, List[Dict[str, Any]]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def add_connection(
        self, 
        connection_id: str, 
        websocket: MockWebSocket,
        metadata: Dict[str, Any] = None
    ):
        """Add connection with metadata"""
        self.connections[connection_id] = websocket
        self.connection_metadata[connection_id] = metadata or {}
        self.message_queue[connection_id] = []
        
    async def remove_connection(self, connection_id: str):
        """Remove connection and clean up"""
        if connection_id in self.connections:
            # Leave all rooms
            for room_id, members in self.rooms.items():
                members.discard(connection_id)
                
            # Clean up
            del self.connections[connection_id]
            del self.connection_metadata[connection_id]
            del self.message_queue[connection_id]
            
    async def join_room(self, connection_id: str, room_id: str):
        """Join a room"""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(connection_id)
        
    async def leave_room(self, connection_id: str, room_id: str):
        """Leave a room"""
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                
    async def send_to_connection(
        self, 
        connection_id: str, 
        message: Dict[str, Any]
    ):
        """Send message to specific connection"""
        if connection_id in self.connections:
            await self.connections[connection_id].send_json(message)
        else:
            # Queue message for when connection is available
            if connection_id not in self.message_queue:
                self.message_queue[connection_id] = []
            self.message_queue[connection_id].append(message)
            
    async def send_to_room(self, room_id: str, message: Dict[str, Any]):
        """Send message to all connections in a room"""
        if room_id in self.rooms:
            for connection_id in self.rooms[room_id]:
                await self.send_to_connection(connection_id, message)
                
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connections"""
        for connection_id in self.connections:
            await self.send_to_connection(connection_id, message)
            
    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of connection IDs in a room"""
        return list(self.rooms.get(room_id, set()))
        
    def get_connection_rooms(self, connection_id: str) -> List[str]:
        """Get list of rooms a connection is in"""
        rooms = []
        for room_id, members in self.rooms.items():
            if connection_id in members:
                rooms.append(room_id)
        return rooms
        
    def get_queued_messages(self, connection_id: str) -> List[Dict[str, Any]]:
        """Get queued messages for a connection"""
        return self.message_queue.get(connection_id, []).copy()


class MockWebSocketBroadcaster:
    """Mock WebSocket broadcaster for testing pub/sub patterns"""
    
    def __init__(self):
        self.subscribers: Dict[str, Set[str]] = {}
        self.published_messages = []
        
    async def subscribe(self, connection_id: str, channel: str):
        """Subscribe connection to a channel"""
        if channel not in self.subscribers:
            self.subscribers[channel] = set()
        self.subscribers[channel].add(connection_id)
        
    async def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe connection from a channel"""
        if channel in self.subscribers:
            self.subscribers[channel].discard(connection_id)
            if not self.subscribers[channel]:
                del self.subscribers[channel]
                
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to a channel"""
        published_msg = {
            "channel": channel,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subscriber_count": len(self.subscribers.get(channel, set()))
        }
        self.published_messages.append(published_msg)
        
    def get_published_messages(self) -> List[Dict[str, Any]]:
        """Get all published messages"""
        return self.published_messages.copy()
        
    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get subscribers for a channel"""
        return list(self.subscribers.get(channel, set()))


class MockHighVolumeWebSocketServer:
    """Mock high-volume WebSocket server for performance testing"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.connected_clients: Set[str] = set()
        self.message_stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connections_made": 0,
            "connections_lost": 0
        }
        self.is_running = False
        
    async def start(self):
        """Start the mock server"""
        self.is_running = True
        
    async def stop(self):
        """Stop the mock server"""
        self.is_running = False
        self.connected_clients.clear()
        
    def add_client(self, client_id: str):
        """Add a client connection"""
        self.connected_clients.add(client_id)
        self.message_stats["connections_made"] += 1
        
    def remove_client(self, client_id: str):
        """Remove a client connection"""
        self.connected_clients.discard(client_id)
        self.message_stats["connections_lost"] += 1
        
    def simulate_message_sent(self):
        """Simulate a message sent"""
        self.message_stats["messages_sent"] += 1
        
    def simulate_message_received(self):
        """Simulate a message received"""
        self.message_stats["messages_received"] += 1
        
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            **self.message_stats,
            "connected_clients": len(self.connected_clients),
            "is_running": self.is_running
        }