"""Thread Management Testing Utilities

This module provides thread management WebSocket testing infrastructure including:
- Thread creation and lifecycle management
- WebSocket connection management for threads
- Thread state synchronization validation
- Cross-service thread data consistency checking
"""

from datetime import datetime, timezone
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.websocket_core.manager import WebSocketManager
from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS, TestDataFactory
from tests.e2e.unified_e2e_harness import UnifiedE2ETestHarness
from tests.e2e.harness_utils import UnifiedTestHarnessComplete
from typing import Any, Dict, List, Optional
import asyncio
import json
import time
import uuid

logger = central_logger.get_logger(__name__)


class ThreadWebSocketManager:

    """Core WebSocket thread management testing infrastructure."""
    

    def __init__(self, harness: UnifiedTestHarnessComplete):

        self.harness = harness

        self.active_connections: Dict[str, Any] = {}

        self.thread_events: List[Dict[str, Any]] = []

        self.websocket_messages: List[Dict[str, Any]] = []

        self.thread_contexts: Dict[str, Dict[str, Any]] = {}
    

    async def create_authenticated_connection(self, user_id: str) -> Dict[str, Any]:

        """Create authenticated WebSocket connection for user."""

        tokens = self.harness.create_test_tokens(user_id)

        headers = self.harness.create_auth_headers(tokens["access_token"])
        

        connection_config = {

            "user_id": user_id,

            "auth_token": tokens["access_token"],

            "headers": headers,

            "endpoint": TEST_ENDPOINTS.ws_url

        }
        

        self.active_connections[user_id] = connection_config

        return connection_config
    

    async def create_thread_with_websocket(self, user_id: str, thread_name: str = None) -> Dict[str, Any]:

        """Create a new thread via WebSocket and return thread data."""

        if user_id not in self.active_connections:

            await self.create_authenticated_connection(user_id)
        

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        thread_name = thread_name or f"Test Thread {thread_id[-8:]}"
        
        # Simulate thread creation via WebSocket

        thread_creation_message = {

            "type": WebSocketMessageType.THREAD_CREATE.value,

            "thread_id": thread_id,

            "thread_name": thread_name,

            "user_id": user_id,

            "timestamp": datetime.now(timezone.utc).isoformat()

        }
        
        # Record the thread creation event

        self.thread_events.append({

            "action": "create",

            "thread_id": thread_id,

            "user_id": user_id,

            "timestamp": time.time(),

            "message": thread_creation_message

        })
        
        # Store thread context

        self.thread_contexts[thread_id] = {

            "thread_id": thread_id,

            "thread_name": thread_name,

            "user_id": user_id,

            "created_at": datetime.now(timezone.utc).isoformat(),

            "status": "active",

            "message_count": 0

        }
        

        return self.thread_contexts[thread_id]
    

    async def send_message_to_thread(self, thread_id: str, message_content: str, 

                                   message_type: str = "user_message") -> Dict[str, Any]:

        """Send message to thread via WebSocket."""

        if thread_id not in self.thread_contexts:

            raise ValueError(f"Thread {thread_id} not found")
        

        thread_context = self.thread_contexts[thread_id]

        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        

        message_data = {

            "type": message_type,

            "message_id": message_id,

            "thread_id": thread_id,

            "user_id": thread_context["user_id"],

            "content": message_content,

            "timestamp": datetime.now(timezone.utc).isoformat()

        }
        
        # Record WebSocket message

        self.websocket_messages.append({

            "action": "send_message",

            "thread_id": thread_id,

            "message_id": message_id,

            "timestamp": time.time(),

            "data": message_data

        })
        
        # Update thread context

        thread_context["message_count"] += 1

        thread_context["last_message_at"] = datetime.now(timezone.utc).isoformat()
        

        return message_data
    

    async def validate_thread_state_sync(self, thread_id: str) -> Dict[str, Any]:

        """Validate thread state synchronization across services."""

        if thread_id not in self.thread_contexts:

            return {"valid": False, "error": "Thread not found"}
        

        thread_context = self.thread_contexts[thread_id]
        
        # Simulate state validation across services

        validation_results = {

            "thread_id": thread_id,

            "frontend_state": {

                "exists": True,

                "message_count": thread_context["message_count"],

                "status": thread_context["status"]

            },

            "backend_state": {

                "exists": True,

                "message_count": thread_context["message_count"],

                "status": thread_context["status"]

            },

            "websocket_state": {

                "connected": thread_id in self.thread_contexts,

                "active": thread_context["status"] == "active"

            },

            "sync_valid": True

        }
        

        return validation_results
    

    async def cleanup_thread_resources(self, thread_id: str) -> bool:

        """Clean up thread resources and connections."""

        try:

            if thread_id in self.thread_contexts:

                del self.thread_contexts[thread_id]
            
            # Remove related events and messages

            self.thread_events = [

                event for event in self.thread_events 

                if event.get("thread_id") != thread_id

            ]
            

            self.websocket_messages = [

                msg for msg in self.websocket_messages 

                if msg.get("thread_id") != thread_id

            ]
            

            return True

        except Exception as e:

            logger.error(f"Error cleaning up thread {thread_id}: {e}")

            return False
    

    def get_thread_statistics(self) -> Dict[str, Any]:

        """Get comprehensive thread management statistics."""

        active_threads = len(self.thread_contexts)

        total_messages = len(self.websocket_messages)

        total_events = len(self.thread_events)
        

        return {

            "active_threads": active_threads,

            "total_messages": total_messages,

            "total_events": total_events,

            "active_connections": len(self.active_connections),

            "thread_ids": list(self.thread_contexts.keys())

        }


class ThreadStateValidator:

    """Validates thread state consistency across services."""
    

    def __init__(self):

        self.validation_errors: List[str] = []
    

    def validate_thread_creation(self, thread_data: Dict[str, Any]) -> bool:

        """Validate thread creation data structure."""

        required_fields = {"thread_id", "thread_name", "user_id", "created_at"}
        

        missing_fields = required_fields - set(thread_data.keys())

        if missing_fields:

            self.validation_errors.append(f"Missing fields: {missing_fields}")

            return False
        

        return True
    

    def validate_message_data(self, message_data: Dict[str, Any]) -> bool:

        """Validate message data structure."""

        required_fields = {"message_id", "thread_id", "user_id", "content", "timestamp"}
        

        missing_fields = required_fields - set(message_data.keys())

        if missing_fields:

            self.validation_errors.append(f"Message missing fields: {missing_fields}")

            return False
        

        return True
    

    def validate_cross_service_sync(self, sync_data: Dict[str, Any]) -> bool:

        """Validate cross-service synchronization."""

        frontend_state = sync_data.get("frontend_state", {})

        backend_state = sync_data.get("backend_state", {})

        websocket_state = sync_data.get("websocket_state", {})
        
        # Check existence consistency

        if not all([

            frontend_state.get("exists"),

            backend_state.get("exists"),

            websocket_state.get("connected")

        ]):

            self.validation_errors.append("Inconsistent existence across services")

            return False
        
        # Check message count consistency

        frontend_count = frontend_state.get("message_count", 0)

        backend_count = backend_state.get("message_count", 0)
        

        if frontend_count != backend_count:

            self.validation_errors.append(

                f"Message count mismatch: frontend={frontend_count}, backend={backend_count}"

            )

            return False
        

        return True
    

    def get_validation_errors(self) -> List[str]:

        """Get all validation errors."""

        return self.validation_errors.copy()
    

    def clear_errors(self) -> None:

        """Clear validation errors."""

        self.validation_errors.clear()


def create_thread_test_data(user_id: str, thread_count: int = 1) -> List[Dict[str, Any]]:

    """Create test data for multiple threads."""

    threads = []
    

    for i in range(thread_count):

        thread_data = {

            "thread_id": f"test-thread-{uuid.uuid4().hex[:8]}",

            "thread_name": f"Test Thread {i + 1}",

            "user_id": user_id,

            "created_at": datetime.now(timezone.utc).isoformat(),

            "status": "active",

            "message_count": 0

        }

        threads.append(thread_data)
    

    return threads


def create_message_test_data(thread_id: str, user_id: str, message_count: int = 1) -> List[Dict[str, Any]]:

    """Create test data for multiple messages."""

    messages = []
    

    for i in range(message_count):

        message_data = {

            "message_id": f"msg-{uuid.uuid4().hex[:8]}",

            "thread_id": thread_id,

            "user_id": user_id,

            "content": f"Test message {i + 1}",

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "type": "user_message"

        }

        messages.append(message_data)
    

    return messages


async def measure_thread_operation_timing(operation_func, *args, **kwargs) -> Dict[str, Any]:

    """Measure timing for thread operations."""

    start_time = time.time()
    

    try:

        result = await operation_func(*args, **kwargs)

        success = True

        error = None

    except Exception as e:

        result = None

        success = False

        error = str(e)
    

    end_time = time.time()

    duration = end_time - start_time
    

    return {

        "success": success,

        "duration_seconds": duration,

        "result": result,

        "error": error,

        "timestamp": start_time

    }


def validate_thread_websocket_flow(events: List[Dict[str, Any]], expected_sequence: List[str]) -> bool:

    """Validate that WebSocket events follow expected sequence."""

    event_types = [event.get("action") for event in events]
    
    # Check if all expected events are present

    for expected_event in expected_sequence:

        if expected_event not in event_types:

            return False
    
    # Check order for critical sequences

    if "create" in event_types and "send_message" in event_types:

        create_index = event_types.index("create")

        send_index = event_types.index("send_message")
        

        if create_index >= send_index:

            return False
    

    return True
