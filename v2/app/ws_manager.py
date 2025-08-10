from app.logging_config import central_logger
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from typing import List, Dict, Any, Optional, Set
import time
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

logger = central_logger.get_logger(__name__)

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    last_pong: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    connection_id: str = field(default_factory=lambda: f"conn_{int(time.time() * 1000)}")

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
            self._stats = {
                "total_connections": 0,
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_errors": 0,
                "connection_failures": 0
            }
            self._initialized = True

    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        # Initialize user's connection list if needed
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        # Check connection limit
        if len(self.active_connections[user_id]) >= self.MAX_CONNECTIONS_PER_USER:
            # Close oldest connection to make room
            oldest_conn = self.active_connections[user_id][0]
            logger.warning(f"User {user_id} exceeded connection limit, closing oldest connection {oldest_conn.connection_id}")
            await self.disconnect(user_id, oldest_conn.websocket, code=1008, reason="Connection limit exceeded")
        
        conn_info = ConnectionInfo(websocket=websocket, user_id=user_id)
        
        # Add connection to tracking structures
        self.active_connections[user_id].append(conn_info)
        self.connection_registry[conn_info.connection_id] = conn_info
        
        # Update statistics
        self._stats["total_connections"] += 1
        
        # Start heartbeat task for this connection
        self.heartbeat_tasks[conn_info.connection_id] = asyncio.create_task(
            self._heartbeat_loop(conn_info)
        )
        
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
        if user_id not in self.active_connections:
            return
        
        # Find and remove the connection info
        conn_info = None
        for conn in self.active_connections[user_id]:
            if conn.websocket == websocket:
                conn_info = conn
                break
        
        if conn_info:
            # Cancel heartbeat task
            if conn_info.connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[conn_info.connection_id].cancel()
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
            duration = (datetime.utcnow() - conn_info.connected_at).total_seconds()
            logger.info(
                f"WebSocket disconnected for user {user_id} "
                f"(ID: {conn_info.connection_id}, Duration: {duration:.1f}s, "
                f"Messages: {conn_info.message_count}, Errors: {conn_info.error_count})"
            )

    async def send_message(self, user_id: str, message: Dict[str, Any], retry: bool = True) -> bool:
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
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = time.time()
        
        connections_to_remove = []
        successful_sends = 0
        
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
            await self.disconnect(user_id, conn_info.websocket, code=1001, reason="Connection lost")
        
        return successful_sends > 0
    
    async def _send_to_connection(self, conn_info: ConnectionInfo, message: Dict[str, Any], retry: bool = True) -> bool:
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
        time_since_ping = (datetime.utcnow() - conn_info.last_ping).total_seconds()
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
                conn_info.last_ping = datetime.utcnow()
                
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
            # Ensure connection is cleaned up
            if conn_info.connection_id in self.connection_registry:
                await self.disconnect(conn_info.user_id, conn_info.websocket)
    
    async def handle_pong(self, user_id: str, websocket: WebSocket):
        """Handle pong response from client."""
        for conn_info in self.active_connections.get(user_id, []):
            if conn_info.websocket == websocket:
                conn_info.last_pong = datetime.utcnow()
                break

    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System"):
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

    async def broadcast(self, message: Dict[str, Any]) -> Dict[str, int]:
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
        
        for user_id, connections in list(self.active_connections.items()):
            for conn_info in connections[:]:  # Use slice copy to avoid modification during iteration
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
            await self.disconnect(user_id, conn_info.websocket, code=1001, reason="Connection lost during broadcast")
        
        if failed_sends > 0:
            logger.warning(f"Broadcast completed: {successful_sends} successful, {failed_sends} failed")
        
        return {"successful": successful_sends, "failed": failed_sends}

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