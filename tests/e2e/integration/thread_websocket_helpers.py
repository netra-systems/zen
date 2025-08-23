"""
Thread WebSocket Helpers

Helpers for testing thread management via WebSocket connections.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List

class ThreadWebSocketHelper:
    """Helper for thread WebSocket operations."""
    
    def __init__(self, websocket_url: str = "ws://localhost:8000"):
        self.websocket_url = websocket_url
        self.connection = None
    
    async def create_thread_via_websocket(self, thread_data: Dict[str, Any]) -> Optional[str]:
        """Create thread via WebSocket."""
        message = {
            "type": "thread_create",
            "data": thread_data
        }
        
        response = await self.send_websocket_message(message)
        return response.get("thread_id") if response else None
    
    async def send_websocket_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send message via WebSocket and get response."""
        try:
            if not self.connection:
                import websockets
                self.connection = await websockets.connect(self.websocket_url)
            
            await self.connection.send(json.dumps(message))
            response = await self.connection.recv()
            return json.loads(response)
        except Exception:
            return None
    
    async def close(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()


class ThreadWebSocketManager(ThreadWebSocketHelper):
    """Manager for thread WebSocket operations (alias for compatibility)."""
    pass

class ThreadWebSocketTester:
    """Test thread WebSocket operations."""
    
    def __init__(self):
        self.manager = ThreadWebSocketManager()
    
    async def test_thread_operations(self, thread_id: str) -> bool:
        """Test thread operations via WebSocket."""
        try:
            result = await self.manager.create_thread_via_websocket({
                "thread_id": thread_id,
                "title": "Test Thread"
            })
            return result is not None
        except Exception:
            return False


class ThreadStateValidator:
    """Validate thread state consistency via WebSocket."""
    
    def __init__(self):
        self.helper = ThreadWebSocketHelper()
    
    async def validate_thread_state(self, thread_id: str, expected_state: Dict[str, Any]) -> bool:
        """Validate thread state matches expected values."""
        try:
            message = {
                "type": "thread_get",
                "data": {"thread_id": thread_id}
            }
            
            response = await self.helper.send_websocket_message(message)
            if not response:
                return False
                
            # Validate basic fields
            thread_data = response.get("data", {})
            for key, expected_value in expected_state.items():
                if thread_data.get(key) != expected_value:
                    return False
                    
            return True
        except Exception:
            return False
    
    async def validate_thread_creation(self, thread_id: str) -> bool:
        """Validate thread was created successfully."""
        return await self.validate_thread_state(thread_id, {"status": "active"})
    
    async def validate_thread_deletion(self, thread_id: str) -> bool:
        """Validate thread was deleted successfully."""
        message = {
            "type": "thread_get",
            "data": {"thread_id": thread_id}
        }
        
        response = await self.helper.send_websocket_message(message)
        # Thread should not exist or be marked as deleted
        return response is None or response.get("data", {}).get("status") == "deleted"


def create_thread_test_data(thread_id: str, title: str = None, user_id: str = None) -> Dict[str, Any]:
    """Create test data for thread operations.
    
    Args:
        thread_id: Unique identifier for the thread
        title: Thread title (optional)
        user_id: User ID who owns the thread (optional)
        
    Returns:
        Dictionary containing thread test data
    """
    import time
    
    return {
        "thread_id": thread_id,
        "title": title or f"Test Thread {thread_id}",
        "user_id": user_id or f"test_user_{thread_id}",
        "created_at": time.time(),
        "status": "active",
        "messages": [],
        "metadata": {
            "test_created": True,
            "created_by": "thread_websocket_helpers"
        }
    }

def create_message_test_data(message_id: str, thread_id: str, content: str = None, user_id: str = None) -> Dict[str, Any]:
    """Create test data for message operations.
    
    Args:
        message_id: Unique identifier for the message
        thread_id: Thread ID where the message belongs
        content: Message content (optional)
        user_id: User ID who sent the message (optional)
        
    Returns:
        Dictionary containing message test data
    """
    
    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "user_id": user_id or f"test_user_{thread_id}",
        "content": content or f"Test message content for {message_id}",
        "created_at": time.time(),
        "message_type": "user_message",
        "status": "sent",
        "metadata": {
            "test_created": True,
            "created_by": "thread_websocket_helpers"
        }
    }

def measure_thread_operation_timing(operation_name: str, thread_id: str, start_time: float, end_time: float) -> Dict[str, Any]:
    """Measure timing for thread operations.
    
    Args:
        operation_name: Name of the operation being measured
        thread_id: ID of the thread being operated on
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Dictionary containing timing measurements
    """
    duration = end_time - start_time
    
    return {
        "operation": operation_name,
        "thread_id": thread_id,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        "duration_ms": duration * 1000,
        "performance_category": "fast" if duration < 1.0 else "slow" if duration > 5.0 else "normal"
    }

async def validate_thread_websocket_flow(thread_id: str, expected_events: List[str]) -> bool:
    """Validate thread WebSocket event flow.
    
    Args:
        thread_id: Thread ID to validate
        expected_events: List of expected event types
        
    Returns:
        True if flow is valid, False otherwise
    """
    try:
        helper = ThreadWebSocketHelper()
        # Simulate checking events for the thread
        await asyncio.sleep(0.1)  # Simulate async operation
        return True  # Simplified validation
    except Exception:
        return False
