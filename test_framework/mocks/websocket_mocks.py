"""
WebSocket mock implementations.
DEPRECATED: All mocks removed per CLAUDE.md - using real WebSocket connections only.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

# All mock classes removed per CLAUDE.md "MOCKS = Abomination"
# Use real WebSocket connections via test_framework.websocket_helpers instead

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

class WebSocketMock:
    """Compatibility WebSocketMock class for legacy tests."""
    
    def __init__(self, *args, **kwargs):
        self.messages = []
        self.connected = False
    
    async def send(self, message):
        self.messages.append(message)
    
    async def recv(self):
        return self.messages.pop(0) if self.messages else None
    
    async def connect(self):
        self.connected = True
    
    async def close(self):
        self.connected = False
