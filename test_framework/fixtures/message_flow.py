"""
Message Flow Test Fixtures

Shared fixtures for message flow testing.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class MessageFlowTracker:
    """Track message flows during testing."""
    
    def __init__(self):
        """Initialize message flow tracker."""
        self.messages: List[Dict[str, Any]] = []
        self.flows: Dict[str, List[str]] = {}
        self.errors: List[Dict[str, Any]] = []
    
    def track_message(self, message_id: str, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Track a message in the flow."""
        message_data = {
            "id": message_id,
            "type": message_type,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }
        self.messages.append(message_data)
    
    def track_flow(self, flow_id: str, message_id: str):
        """Track a message as part of a flow."""
        if flow_id not in self.flows:
            self.flows[flow_id] = []
        self.flows[flow_id].append(message_id)
    
    def track_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Track an error in the flow."""
        error_data = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now(timezone.utc),
            "context": context or {}
        }
        self.errors.append(error_data)
    
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages by type."""
        return [msg for msg in self.messages if msg["type"] == message_type]
    
    def get_flow_messages(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get messages for a specific flow."""
        message_ids = self.flows.get(flow_id, [])
        return [msg for msg in self.messages if msg["id"] in message_ids]
    
    def clear(self):
        """Clear all tracked data."""
        self.messages.clear()
        self.flows.clear()
        self.errors.clear()


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize mock WebSocket connection."""
        self.user_id = user_id or str(uuid.uuid4())
        self.messages_sent: List[Dict[str, Any]] = []
        self.messages_received: List[Dict[str, Any]] = []
        self.connected = False
        self.closed = False
    
    async def connect(self):
        """Mock connection."""
        self.connected = True
        self.closed = False
    
    async def disconnect(self):
        """Mock disconnection."""
        self.connected = False
        self.closed = True
    
    async def send_json(self, data: Dict[str, Any]):
        """Mock sending JSON data."""
        if not self.connected:
            raise RuntimeError("Connection closed")
        
        self.messages_sent.append({
            "data": data,
            "timestamp": datetime.now(timezone.utc)
        })
    
    async def receive_json(self) -> Dict[str, Any]:
        """Mock receiving JSON data."""
        if not self.connected:
            raise RuntimeError("Connection closed")
        
        if not self.messages_received:
            # Simulate timeout or no message
            await asyncio.sleep(0.1)
            return {"type": "ping", "data": {}}
        
        return self.messages_received.pop(0)["data"]
    
    def add_received_message(self, data: Dict[str, Any]):
        """Add a message to the received queue."""
        self.messages_received.append({
            "data": data,
            "timestamp": datetime.now(timezone.utc)
        })


def create_mock_message_flow_environment():
    """Create a mock message flow environment."""
    return {
        "tracker": MessageFlowTracker(),
        "websocket_manager": MagicMock(),
        "message_router": MagicMock(),
        "agent_service": MagicMock(),
        "user_service": MagicMock()
    }


def create_test_message(
    message_type: str = "user_message", 
    content: str = "Test message",
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a test message."""
    return {
        "id": str(uuid.uuid4()),
        "type": message_type,
        "content": content,
        "thread_id": thread_id or str(uuid.uuid4()),
        "user_id": user_id or str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }


def create_mock_agent_response(
    content: str = "Mock agent response",
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a mock agent response."""
    return {
        "id": str(uuid.uuid4()),
        "type": "agent_response", 
        "content": content,
        "thread_id": thread_id or str(uuid.uuid4()),
        "agent_id": "mock_agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "response_time": 0.5,
            "tokens_used": 150
        }
    }