from app.logging_config import central_logger
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from typing import List, Dict, Any, Optional, Set, Union
import time
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import threading
from collections import defaultdict
from pydantic import ValidationError
from app.schemas.websocket_types import WebSocketMessageOut, WebSocketRequest, MessageTypeLiteral

logger = central_logger.get_logger(__name__)

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_pong: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    connection_id: str = field(default_factory=lambda: f"conn_{int(time.time() * 1000)}")
    last_message_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rate_limit_count: int = 0
    rate_limit_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class RateLimiter:
    """Rate limiter for WebSocket connections."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_rate_limited(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is rate limited."""
        now = datetime.now(timezone.utc)
        
        # Reset counter if window has passed
        if (now - conn_info.rate_limit_window_start).total_seconds() >= self.window_seconds:
            conn_info.rate_limit_count = 0
            conn_info.rate_limit_window_start = now
        
        # Check if limit exceeded
        if conn_info.rate_limit_count >= self.max_requests:
            return True
        
        # Increment counter
        conn_info.rate_limit_count += 1
        conn_info.last_message_time = now
        return False

class WebSocketManager:
    """Enhanced WebSocket manager with improved connection lifecycle and error handling."""
    _instance = None
    _lock = threading.Lock()
    
    # Configuration constants
    HEARTBEAT_INTERVAL = 30  # seconds
    HEARTBEAT_TIMEOUT = 60  # seconds
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds
    MAX_CONNECTIONS_PER_USER = 5  # Prevent memory exhaustion attacks
    RATE_LIMIT_REQUESTS = 60  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WebSocketManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.active_connections: Dict[str, List[ConnectionInfo]] = {}
            self.connection_registry: Dict[str, ConnectionInfo] = {}
            self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
            self._connection_lock = asyncio.Lock()
            self._rate_limiter = RateLimiter(self.RATE_LIMIT_REQUESTS, self.RATE_LIMIT_WINDOW)
            self._stats = {
                "total_connections": 0,
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_errors": 0,
                "connection_failures": 0,
                "rate_limited_requests": 0
            }
            self._initialized = True

    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        async with self._connection_lock:
            # Initialize user's connection list if needed
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            # Check connection limit
            if len(self.active_connections[user_id]) >= self.MAX_CONNECTIONS_PER_USER:
                # Close oldest connection to make room
                oldest_conn = self.active_connections[user_id][0]
                logger.warning(f"User {user_id} exceeded connection limit, closing oldest connection {oldest_conn.connection_id}")
                await self._disconnect_internal(user_id, oldest_conn.websocket, code=1008, reason="Connection limit exceeded")
            
            conn_info = ConnectionInfo(websocket=websocket, user_id=user_id)
            
            # Add connection to tracking structures
            self.active_connections[user_id].append(conn_info)
            self.connection_registry[conn_info.connection_id] = conn_info
            
            # Update statistics
            self._stats["total_connections"] += 1
            
            # Start heartbeat task for this connection with proper cleanup
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(conn_info)
            )
            self.heartbeat_tasks[conn_info.connection_id] = heartbeat_task
            
            logger.info(f"WebSocket connected for user {user_id} (ID: {conn_info.connection_id})")
            
            # Send initial connection success message
            await self._send_system_message(conn_info, {
                "type": "connection_established",
                "connection_id": conn_info.connection_id,
                "timestamp": time.time()
            })
            
            return conn_info

    async def disconnect(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Properly disconnect and clean up a WebSocket connection."""
        async with self._connection_lock:
            await self._disconnect_internal(user_id, websocket, code, reason)
    
    async def _disconnect_internal(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Internal disconnect method - requires lock to be held."""
        if user_id not in self.active_connections:
            return
        
        # Find and remove the connection info
        conn_info = None
        for conn in self.active_connections[user_id]:
            if conn.websocket == websocket:
                conn_info = conn
                break
        
        if conn_info:
            # Cancel and cleanup heartbeat task properly
            if conn_info.connection_id in self.heartbeat_tasks:
                task = self.heartbeat_tasks[conn_info.connection_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.debug(f"Error cleaning up heartbeat task: {e}")
                del self.heartbeat_tasks[conn_info.connection_id]
            
            # Remove from tracking structures
            self.active_connections[user_id].remove(conn_info)
            if conn_info.connection_id in self.connection_registry:
                del self.connection_registry[conn_info.connection_id]
            
            # Clean up empty user lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            # Close connection if still open
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close(code=code, reason=reason)
                except Exception as e:
                    logger.debug(f"Error closing WebSocket: {e}")
            
            # Log disconnection with statistics
            duration = (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
            logger.info(
                f"WebSocket disconnected for user {user_id} "
                f"(ID: {conn_info.connection_id}, Duration: {duration:.1f}s, "
                f"Messages: {conn_info.message_count}, Errors: {conn_info.error_count})"
            )

    def validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate incoming WebSocket message."""
        try:
            # Basic structure validation
            if not isinstance(message, dict):
                logger.warning(f"Message is not a dictionary: {type(message)}")
                return False
            
            # Required fields
            if "type" not in message:
                logger.warning("Message missing 'type' field")
                return False
            
            # Validate message type
            message_type = message.get("type")
            valid_types = [
                "start_agent", "user_message", "get_thread_history", "stop_agent",
                "create_thread", "switch_thread", "delete_thread", "list_threads",
                "agent_completed", "agent_stopped", "thread_history", "error",
                "agent_update", "tool_started", "tool_completed", "subagent_started",
                "subagent_completed", "ping", "pong", "connection_established"
            ]
            
            if message_type not in valid_types:
                logger.warning(f"Invalid message type: {message_type}")
                return False
            
            # Validate payload if present
            payload = message.get("payload", {})
            if payload is not None and not isinstance(payload, dict):
                logger.warning(f"Payload must be a dictionary, got: {type(payload)}")
                return False
            
            # Size validation (prevent large payloads)
            message_str = json.dumps(message)
            if len(message_str) > 1024 * 1024:  # 1MB limit
                logger.warning(f"Message too large: {len(message_str)} bytes")
                return False
            
            # Input sanitization for text fields
            if "payload" in message and isinstance(message["payload"], dict):
                payload = message["payload"]
                if "text" in payload:
                    text = payload["text"]
                    if isinstance(text, str):
                        # Remove potential script injections
                        if "<script" in text.lower() or "javascript:" in text.lower():
                            logger.warning("Potential script injection detected in message")
                            return False
                        # Limit text length
                        if len(text) > 10000:  # 10KB limit for text
                            logger.warning(f"Text too long: {len(text)} characters")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating message: {e}")
            return False
    
    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content."""
        try:
            # Create a copy to avoid modifying original
            sanitized = message.copy()
            
            # Sanitize payload if present
            if "payload" in sanitized and isinstance(sanitized["payload"], dict):
                payload = sanitized["payload"].copy()
                
                # Sanitize text content
                if "text" in payload and isinstance(payload["text"], str):
                    text = payload["text"]
                    # Basic HTML entity encoding for safety (& must be first to avoid double encoding)
                    text = text.replace("&", "&amp;")
                    text = text.replace("<", "&lt;").replace(">", "&gt;")
                    text = text.replace('"', "&quot;").replace("'", "&#x27;")
                    payload["text"] = text
                
                sanitized["payload"] = payload
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing message: {e}")
            return message
    
    async def send_message(self, user_id: str, message: Union[WebSocketMessageOut, Dict[str, Any]], retry: bool = True) -> bool:
        """Send a message to all connections for a user with retry logic.
        
        Returns:
            bool: True if message was sent to at least one connection.
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return False
        
        # Validate message structure
        if not isinstance(message, dict):
            logger.error(f"Invalid message type: {type(message)}")
            return False
        
        # Validate and sanitize message
        if not self.validate_message(message):
            logger.error(f"Message validation failed for user {user_id}")
            return False
        
        message = self.sanitize_message(message)
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = time.time()
        
        connections_to_remove = []
        successful_sends = 0
        
        # Use lock to prevent race conditions during iteration
        async with self._connection_lock:
            for conn_info in self.active_connections[user_id].copy():
                success = await self._send_to_connection(conn_info, message, retry)
                if success:
                    successful_sends += 1
                    conn_info.message_count += 1
                    self._stats["total_messages_sent"] += 1
                elif not self._is_connection_alive(conn_info):
                    connections_to_remove.append(conn_info)
        
        # Remove dead connections
        for conn_info in connections_to_remove:
            await self._disconnect_internal(user_id, conn_info.websocket, code=1001, reason="Connection lost")
        
        return successful_sends > 0
    
    async def _send_to_connection(self, conn_info: ConnectionInfo, message: Union[WebSocketMessageOut, Dict[str, Any]], retry: bool = True) -> bool:
        """Send a message to a specific connection with retry logic."""
        attempts = self.MAX_RETRY_ATTEMPTS if retry else 1
        
        for attempt in range(attempts):
            try:
                if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                    await conn_info.websocket.send_json(message)
                    return True
                else:
                    logger.debug(f"Connection {conn_info.connection_id} not in CONNECTED state")
                    return False
                    
            except (RuntimeError, ConnectionError) as e:
                if "Cannot call" in str(e) or "close" in str(e).lower():
                    logger.debug(f"Connection {conn_info.connection_id} closed: {e}")
                    return False
                    
                conn_info.error_count += 1
                self._stats["total_errors"] += 1
                
                if attempt < attempts - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    logger.warning(f"Retrying send to {conn_info.connection_id} (attempt {attempt + 2}/{attempts})")
                else:
                    logger.error(f"Failed to send message to {conn_info.connection_id} after {attempts} attempts: {e}")
                    return False
                    
            except Exception as e:
                conn_info.error_count += 1
                self._stats["total_errors"] += 1
                logger.error(f"Unexpected error sending to {conn_info.connection_id}: {e}", exc_info=True)
                return False
        
        return False
    
    async def _send_system_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]):
        """Send a system message to a specific connection."""
        message["system"] = True
        await self._send_to_connection(conn_info, message, retry=False)
    
    def _is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still alive based on heartbeat."""
        if conn_info.websocket.client_state != WebSocketState.CONNECTED:
            return False
        
        # Check heartbeat timeout
        time_since_ping = (datetime.now(timezone.utc) - conn_info.last_ping).total_seconds()
        if time_since_ping > self.HEARTBEAT_TIMEOUT:
            logger.warning(f"Connection {conn_info.connection_id} heartbeat timeout")
            return False
        
        return True
    
    async def _heartbeat_loop(self, conn_info: ConnectionInfo):
        """Heartbeat loop for a specific connection."""
        try:
            while conn_info.websocket.client_state == WebSocketState.CONNECTED:
                # Send ping
                await self._send_system_message(conn_info, {
                    "type": "ping",
                    "timestamp": time.time()
                })
                conn_info.last_ping = datetime.now(timezone.utc)
                
                # Wait for next heartbeat interval
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # Check if connection is still alive
                if not self._is_connection_alive(conn_info):
                    logger.warning(f"Connection {conn_info.connection_id} failed heartbeat check")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for {conn_info.connection_id}")
        except Exception as e:
            logger.error(f"Heartbeat error for {conn_info.connection_id}: {e}")
        finally:
            # Ensure connection is cleaned up - avoid recursive disconnect
            pass
    
    async def handle_message(self, user_id: str, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with rate limiting and validation."""
        # Find connection info
        conn_info = None
        for conn in self.active_connections.get(user_id, []):
            if conn.websocket == websocket:
                conn_info = conn
                break
        
        if not conn_info:
            logger.warning(f"Connection not found for user {user_id}")
            return False
        
        # Check rate limiting
        if self._rate_limiter.is_rate_limited(conn_info):
            self._stats["rate_limited_requests"] += 1
            await self._send_system_message(conn_info, {
                "type": "error",
                "payload": {
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "max_requests": self.RATE_LIMIT_REQUESTS,
                        "window_seconds": self.RATE_LIMIT_WINDOW
                    }
                },
                "timestamp": time.time()
            })
            return False
        
        # Validate message
        if not self.validate_message(message):
            await self._send_system_message(conn_info, {
                "type": "error",
                "payload": {
                    "error": "Invalid message format",
                    "code": "INVALID_MESSAGE"
                },
                "timestamp": time.time()
            })
            return False
        
        # Update statistics
        self._stats["total_messages_received"] += 1
        
        return True
    
    async def handle_pong(self, user_id: str, websocket: WebSocket):
        """Handle pong response from client."""
        for conn_info in self.active_connections.get(user_id, []):
            if conn_info.websocket == websocket:
                conn_info.last_pong = datetime.now(timezone.utc)
                break

    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """Send an error message to a specific user"""
        await self.send_message(
            user_id,
            {
                "type": "error",
                "payload": {"error": error_message, "sub_agent_name": sub_agent_name},
                "displayed_to_user": True
            }
        )
    
    async def send_agent_log(self, user_id: str, log_level: str, message: str, sub_agent_name: str = None):
        """Send agent log messages for real-time monitoring"""
        await self.send_message(
            user_id,
            {
                "type": "agent_log",
                "payload": {
                    "level": log_level,
                    "message": message,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )
    
    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], sub_agent_name: str = None):
        """Send tool call updates"""
        await self.send_message(
            user_id,
            {
                "type": "tool_call",
                "payload": {
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )
    
    async def send_tool_result(self, user_id: str, tool_name: str, result: Any, sub_agent_name: str = None):
        """Send tool result updates"""
        await self.send_message(
            user_id,
            {
                "type": "tool_result",
                "payload": {
                    "tool_name": tool_name,
                    "result": result,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )

    async def broadcast(self, message: Union[WebSocketMessageOut, Dict[str, Any]]) -> Dict[str, int]:
        """Broadcast a message to all connected users.
        
        Returns:
            Dict with counts of successful and failed sends
        """
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = time.time()
        
        # Use lock to prevent race conditions during broadcast
        async with self._connection_lock:
            # Create snapshot of connections to avoid modification during iteration
            connections_snapshot = []
            for user_id, connections in self.active_connections.items():
                for conn_info in connections:
                    connections_snapshot.append((user_id, conn_info))
        
        # Send to all connections outside of lock to avoid blocking
        for user_id, conn_info in connections_snapshot:
            try:
                if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                    await conn_info.websocket.send_json(message)
                    successful_sends += 1
                    conn_info.message_count += 1
                    self._stats["total_messages_sent"] += 1
                else:
                    # Connection is not in CONNECTED state
                    connections_to_remove.append((user_id, conn_info))
                    failed_sends += 1
            except (RuntimeError, ConnectionError) as e:
                logger.debug(f"Connection error during broadcast to {user_id} ({conn_info.connection_id}): {e}")
                connections_to_remove.append((user_id, conn_info))
                failed_sends += 1
            except Exception as e:
                logger.error(f"Unexpected error broadcasting to {user_id} ({conn_info.connection_id}): {e}")
                conn_info.error_count += 1
                self._stats["total_errors"] += 1
                failed_sends += 1
        
        # Clean up dead connections
        for user_id, conn_info in connections_to_remove:
            await self._disconnect_internal(user_id, conn_info.websocket, code=1001, reason="Connection lost during broadcast")
        
        if failed_sends > 0:
            logger.warning(f"Broadcast completed: {successful_sends} successful, {failed_sends} failed")
        
        return {"successful": successful_sends, "failed": failed_sends}
    
    async def send_rate_limit_error(self, user_id: str) -> bool:
        """Send rate limit error to user."""
        return await self.send_message(
            user_id,
            {
                "type": "error",
                "payload": {
                    "error": "Rate limit exceeded. Please slow down your requests.",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "max_requests": self.RATE_LIMIT_REQUESTS,
                        "window_seconds": self.RATE_LIMIT_WINDOW
                    }
                }
            }
        )

    async def shutdown(self):
        """Gracefully shutdown all connections."""
        logger.info("Starting WebSocket manager shutdown...")
        
        # Cancel all heartbeat tasks
        tasks_to_cancel = []
        for task_id, task in self.heartbeat_tasks.items():
            if not task.done():
                task.cancel()
                tasks_to_cancel.append(task)
        
        # Wait for tasks to cancel
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        
        # Close all connections
        for user_id, connections in list(self.active_connections.items()):
            for conn_info in connections:
                try:
                    await conn_info.websocket.close(code=1001, reason="Server shutdown")
                except Exception as e:
                    logger.debug(f"Error closing connection during shutdown: {e}")
        
        # Clear all tracking structures
        self.active_connections.clear()
        self.connection_registry.clear()
        self.heartbeat_tasks.clear()
        
        logger.info(f"WebSocket manager shutdown complete. Stats: {self._stats}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        active_count = sum(len(conns) for conns in self.active_connections.values())
        return {
            **self._stats,
            "active_connections": active_count,
            "active_users": len(self.active_connections),
            "rate_limit_settings": {
                "max_requests": self.RATE_LIMIT_REQUESTS,
                "window_seconds": self.RATE_LIMIT_WINDOW
            },
            "connections_by_user": {
                user_id: len(conns) 
                for user_id, conns in self.active_connections.items()
            }
        }
    
    def get_connection_info(self, user_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about a user's connections."""
        if user_id not in self.active_connections:
            return []
        
        return [
            {
                "connection_id": conn.connection_id,
                "connected_at": conn.connected_at.isoformat(),
                "last_ping": conn.last_ping.isoformat(),
                "last_pong": conn.last_pong.isoformat() if conn.last_pong else None,
                "message_count": conn.message_count,
                "error_count": conn.error_count,
                "is_alive": self._is_connection_alive(conn)
            }
            for conn in self.active_connections[user_id]
        ]

manager = WebSocketManager()
ws_manager = manager  # Alias for compatibility