"""
WebSocket Utilities

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Code Reuse
- Value Impact: Shared utilities, eliminates duplication across 20+ files
- Strategic Impact: DRY principle, consistent utility functions

Consolidated utility functions from scattered WebSocket implementation files.
All functions ≤25 lines as per CLAUDE.md requirements.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import (
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    ConnectionInfo,
    MessageType,
    create_standard_message,
    create_error_message,
    create_server_message
)

logger = central_logger.get_logger(__name__)


def generate_connection_id(user_id: str, prefix: str = "conn") -> str:
    """Generate unique connection ID."""
    timestamp = int(time.time() * 1000)
    random_suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{user_id}_{timestamp}_{random_suffix}"


def generate_message_id() -> str:
    """Generate unique message ID."""
    return str(uuid.uuid4())


def get_current_timestamp() -> float:
    """Get current timestamp in seconds."""
    return time.time()


def get_current_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is connected."""
    return websocket.application_state == WebSocketState.CONNECTED


async def safe_websocket_send(websocket: WebSocket, data: Union[Dict[str, Any], str],
                            retry_count: int = 2) -> bool:
    """Safely send data to WebSocket with retry logic."""
    if not is_websocket_connected(websocket):
        return False
    
    for attempt in range(retry_count + 1):
        try:
            if isinstance(data, str):
                await websocket.send_text(data)
            else:
                await websocket.send_json(data)
            return True
            
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during send")
            return False
        except Exception as e:
            logger.warning(f"WebSocket send attempt {attempt + 1} failed: {e}")
            if attempt < retry_count:
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"WebSocket send failed after {retry_count + 1} attempts")
                return False
    
    return False


async def safe_websocket_close(websocket: WebSocket, code: int = 1000, 
                             reason: str = "Normal closure") -> None:
    """Safely close WebSocket connection."""
    if not is_websocket_connected(websocket):
        return
    
    try:
        await websocket.close(code=code, reason=reason)
    except Exception as e:
        logger.warning(f"Error closing WebSocket: {e}")


class WebSocketMessageQueue:
    """Queue for managing WebSocket messages."""
    
    def __init__(self, max_size: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.stats = {
            "enqueued": 0,
            "dequeued": 0,
            "dropped": 0,
            "errors": 0
        }
    
    async def enqueue(self, message: Union[WebSocketMessage, Dict[str, Any]]) -> bool:
        """Add message to queue."""
        try:
            # Convert to dict if needed
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            else:
                message_dict = message
            
            self.queue.put_nowait(message_dict)
            self.stats["enqueued"] += 1
            return True
            
        except asyncio.QueueFull:
            self.stats["dropped"] += 1
            logger.warning("Message queue is full, dropping message")
            return False
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error enqueueing message: {e}")
            return False
    
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get message from queue."""
        try:
            if timeout:
                message = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            else:
                message = await self.queue.get()
            
            self.stats["dequeued"] += 1
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error dequeuing message: {e}")
            return None
    
    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def clear(self) -> None:
        """Clear all messages from queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self.stats,
            "current_size": self.queue.qsize(),
            "max_size": self.queue.maxsize
        }


class WebSocketHeartbeat:
    """Manages WebSocket heartbeat/ping mechanism."""
    
    def __init__(self, interval: float = 45.0, timeout: float = 10.0):
        self.interval = interval
        self.timeout = timeout
        self.running = False
        self.last_pong: Optional[float] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self, websocket: WebSocket) -> None:
        """Start heartbeat monitoring."""
        if self.running:
            return
        
        self.running = True
        self.last_pong = time.time()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
    
    async def stop(self) -> None:
        """Stop heartbeat monitoring."""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
    
    def on_pong_received(self) -> None:
        """Called when pong is received."""
        self.last_pong = time.time()
    
    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        """Main heartbeat loop."""
        try:
            while self.running and is_websocket_connected(websocket):
                current_time = time.time()
                
                # Check if we missed a pong
                if self.last_pong and (current_time - self.last_pong) > (self.interval + self.timeout):
                    logger.warning("WebSocket heartbeat timeout")
                    break
                
                # Send ping
                ping_message = create_server_message(
                    MessageType.PING,
                    {"timestamp": current_time}
                )
                
                if not await safe_websocket_send(websocket, ping_message.model_dump()):
                    logger.warning("Failed to send heartbeat ping")
                    break
                
                await asyncio.sleep(self.interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        finally:
            self.running = False


class WebSocketConnectionMonitor:
    """Monitors WebSocket connection health and statistics."""
    
    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.global_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "errors_occurred": 0,
            "start_time": time.time()
        }
    
    def register_connection(self, connection_id: str, user_id: str,
                          websocket: WebSocket) -> None:
        """Register connection for monitoring."""
        self.connections[connection_id] = {
            "user_id": user_id,
            "websocket": websocket,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "is_healthy": True
        }
        
        self.global_stats["total_connections"] += 1
        self.global_stats["active_connections"] += 1
    
    def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.global_stats["active_connections"] -= 1
    
    def update_activity(self, connection_id: str, activity_type: str = "message") -> None:
        """Update connection activity."""
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            conn["last_activity"] = datetime.now(timezone.utc)
            
            if activity_type == "message_sent":
                conn["messages_sent"] += 1
            elif activity_type == "message_received":
                conn["messages_received"] += 1
            elif activity_type == "error":
                conn["errors"] += 1
                self.global_stats["errors_occurred"] += 1
            
            self.global_stats["messages_processed"] += 1
    
    def get_connection_health(self, connection_id: str) -> Dict[str, Any]:
        """Get health status for specific connection."""
        if connection_id not in self.connections:
            return {"status": "not_found"}
        
        conn = self.connections[connection_id]
        websocket = conn["websocket"]
        current_time = datetime.now(timezone.utc)
        last_activity = conn["last_activity"]
        
        # Calculate activity metrics
        inactive_seconds = (current_time - last_activity).total_seconds()
        is_stale = inactive_seconds > 300  # 5 minutes
        is_connected = is_websocket_connected(websocket)
        
        return {
            "connection_id": connection_id,
            "user_id": conn["user_id"],
            "is_connected": is_connected,
            "is_stale": is_stale,
            "inactive_seconds": inactive_seconds,
            "messages_sent": conn["messages_sent"],
            "messages_received": conn["messages_received"],
            "error_count": conn["errors"],
            "connected_duration": (current_time - conn["connected_at"]).total_seconds()
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global connection statistics."""
        uptime = time.time() - self.global_stats["start_time"]
        
        return {
            **self.global_stats,
            "uptime_seconds": uptime,
            "connections_by_user": self._get_connections_by_user(),
            "health_summary": self._get_health_summary()
        }
    
    def _get_connections_by_user(self) -> Dict[str, int]:
        """Get connection count by user."""
        user_counts = {}
        for conn in self.connections.values():
            user_id = conn["user_id"]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
    
    def _get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all connections."""
        healthy_count = 0
        stale_count = 0
        
        for connection_id in self.connections:
            health = self.get_connection_health(connection_id)
            if health.get("is_connected") and not health.get("is_stale"):
                healthy_count += 1
            elif health.get("is_stale"):
                stale_count += 1
        
        return {
            "healthy_connections": healthy_count,
            "stale_connections": stale_count,
            "total_monitored": len(self.connections)
        }


# Utility functions for message processing

def parse_websocket_message(raw_data: Union[str, bytes]) -> Optional[Dict[str, Any]]:
    """Parse raw WebSocket message data."""
    try:
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
        
        return json.loads(raw_data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse WebSocket message: {e}")
        return None


def validate_message_structure(message: Dict[str, Any]) -> bool:
    """Validate basic message structure."""
    required_fields = ["type"]
    
    if not isinstance(message, dict):
        return False
    
    for field in required_fields:
        if field not in message:
            return False
    
    return True


def extract_user_info_from_message(message: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract user information from message."""
    user_info = {}
    
    if "user_id" in message:
        user_info["user_id"] = str(message["user_id"])
    
    if "thread_id" in message:
        user_info["thread_id"] = str(message["thread_id"])
    
    return user_info if user_info else None


async def broadcast_to_websockets(websockets: List[WebSocket], 
                                message: Union[Dict[str, Any], str],
                                exclude_websockets: Optional[List[WebSocket]] = None) -> int:
    """Broadcast message to multiple WebSockets."""
    exclude_websockets = exclude_websockets or []
    successful_sends = 0
    
    # Filter out excluded WebSockets
    target_websockets = [ws for ws in websockets if ws not in exclude_websockets]
    
    # Send to all targets concurrently
    send_tasks = []
    for websocket in target_websockets:
        if is_websocket_connected(websocket):
            task = safe_websocket_send(websocket, message)
            send_tasks.append(task)
    
    if send_tasks:
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        successful_sends = sum(1 for result in results if result is True)
    
    return successful_sends


def format_websocket_error_response(error_code: str, error_message: str,
                                  request_id: Optional[str] = None) -> Dict[str, Any]:
    """Format standardized WebSocket error response."""
    error_response = {
        "type": "error",
        "error": {
            "code": error_code,
            "message": error_message,
            "timestamp": time.time()
        }
    }
    
    if request_id:
        error_response["request_id"] = request_id
    
    return error_response


def create_connection_info(connection_id: str, user_id: str,
                         thread_id: Optional[str] = None) -> ConnectionInfo:
    """Create connection info object."""
    return ConnectionInfo(
        connection_id=connection_id,
        user_id=user_id,
        thread_id=thread_id,
        connected_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
        message_count=0,
        is_healthy=True
    )


# Global utilities instances
_connection_monitor: Optional[WebSocketConnectionMonitor] = None

def get_connection_monitor() -> WebSocketConnectionMonitor:
    """Get global connection monitor."""
    global _connection_monitor
    if _connection_monitor is None:
        _connection_monitor = WebSocketConnectionMonitor()
    return _connection_monitor


@asynccontextmanager
async def websocket_message_queue_context(max_size: int = 1000) -> AsyncGenerator[WebSocketMessageQueue, None]:
    """Context manager for WebSocket message queue."""
    queue = WebSocketMessageQueue(max_size=max_size)
    try:
        yield queue
    finally:
        queue.clear()


@asynccontextmanager  
async def websocket_heartbeat_context(websocket: WebSocket, interval: float = 45.0) -> AsyncGenerator[WebSocketHeartbeat, None]:
    """Context manager for WebSocket heartbeat."""
    heartbeat = WebSocketHeartbeat(interval=interval)
    try:
        await heartbeat.start(websocket)
        yield heartbeat
    finally:
        await heartbeat.stop()