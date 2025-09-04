"""
Connection-scoped WebSocket Manager with Zero Event Leakage.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: User Isolation & Chat Value Delivery  
- Value Impact: Eliminates ALL cross-user event leakage, enables secure multi-user chat
- Strategic Impact: CRITICAL - Replaces dangerous singleton with isolated connection management

This module implements a connection-scoped WebSocket manager that guarantees zero event
leakage between users. Unlike the singleton pattern, each connection gets its own manager
instance that only handles events for that specific authenticated user.

Key Architecture Changes from Singleton:
1. NO SHARED STATE - Each manager instance is connection-scoped
2. User ID Validation - All events validated against authenticated user
3. Connection Binding - Manager bound to specific user_id + connection_id
4. Automatic Cleanup - Resources cleaned on disconnect
5. Event Filtering - Events for wrong users automatically blocked

Security Features:
- Connection-scoped isolation prevents cross-user data leakage
- Event validation ensures messages only go to intended recipients  
- Audit logging of all event routing decisions for debugging
- Resource cleanup prevents memory leaks from abandoned connections
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection_handler import ConnectionHandler, connection_scope

if TYPE_CHECKING:
    from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter

logger = central_logger.get_logger(__name__)


@dataclass  
class ConnectionScopedManagerStats:
    """Statistics for connection-scoped WebSocket manager."""
    connection_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    events_sent: int = 0
    events_received: int = 0
    events_blocked: int = 0  # Events blocked due to user mismatch
    
    total_agent_events: int = 0
    agent_started_events: int = 0
    agent_thinking_events: int = 0
    tool_executing_events: int = 0
    tool_completed_events: int = 0
    agent_completed_events: int = 0
    
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def record_event_sent(self, event_type: str):
        """Record an event sent."""
        self.events_sent += 1
        self.update_activity()
        
        # Track agent events specifically
        if event_type.startswith('agent_') or event_type.startswith('tool_'):
            self.total_agent_events += 1
            if event_type == 'agent_started':
                self.agent_started_events += 1
            elif event_type == 'agent_thinking':
                self.agent_thinking_events += 1
            elif event_type == 'tool_executing':
                self.tool_executing_events += 1
            elif event_type == 'tool_completed':
                self.tool_completed_events += 1
            elif event_type == 'agent_completed':
                self.agent_completed_events += 1


class ConnectionScopedWebSocketManager:
    """
    Connection-scoped WebSocket manager with enforced user isolation.
    
    This manager is created per-connection and only handles events for the
    authenticated user of that connection. It completely eliminates the 
    singleton pattern that caused cross-user event leakage.
    
    CRITICAL ARCHITECTURE CHANGE:
    - OLD: One global manager serving all users (causes event leakage)
    - NEW: One manager per connection serving only that user (zero leakage)
    
    Each manager instance:
    1. Is bound to a specific user_id and connection_id
    2. Only accepts events intended for that user_id
    3. Automatically blocks events for other users
    4. Cleans up resources when connection closes
    5. Provides detailed audit logging for debugging
    """
    
    # Class-level tracking for global monitoring (not shared state)
    _active_managers: Set[str] = set()
    _total_created: int = 0
    
    def __init__(self, websocket: WebSocket, user_id: str, 
                 connection_id: Optional[str] = None, 
                 thread_id: Optional[str] = None):
        """Initialize connection-scoped manager.
        
        Args:
            websocket: WebSocket connection for this user
            user_id: Authenticated user ID this manager serves
            connection_id: Optional connection ID (generated if not provided)
            thread_id: Optional thread ID for this connection
        """
        self.connection_id = connection_id or f"mgr_{user_id}_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.thread_id = thread_id
        self.websocket = websocket
        
        # Connection handler for this user
        self.handler = ConnectionHandler(websocket, user_id, self.connection_id)
        
        # Stats tracking for this connection only
        self.stats = ConnectionScopedManagerStats(
            connection_id=self.connection_id,
            user_id=user_id
        )
        
        # Event callbacks for this connection
        self.event_callbacks: Dict[str, List[Callable]] = {}
        
        # Resource cleanup tracking
        self._is_initialized = False
        self._is_cleaned = False
        
        # Track globally for monitoring  
        ConnectionScopedWebSocketManager._active_managers.add(self.connection_id)
        ConnectionScopedWebSocketManager._total_created += 1
        
        logger.info(f"🔌 ConnectionScopedWebSocketManager created for user {user_id[:8]}... "
                   f"connection {self.connection_id}")
    
    async def initialize(self, thread_id: Optional[str] = None, 
                        session_id: Optional[str] = None) -> bool:
        """Initialize the connection-scoped manager.
        
        Args:
            thread_id: Optional thread ID for this connection
            session_id: Optional session ID for this connection
            
        Returns:
            bool: True if initialization successful
        """
        if self._is_initialized:
            logger.debug(f"Manager {self.connection_id} already initialized")
            return True
        
        try:
            # Initialize connection handler
            if not await self.handler.authenticate(thread_id=thread_id, session_id=session_id):
                logger.error(f"Failed to authenticate connection handler for {self.connection_id}")
                return False
            
            self.thread_id = thread_id or self.thread_id
            self._is_initialized = True
            
            logger.info(f"✅ ConnectionScopedWebSocketManager initialized for user {self.user_id[:8]}... "
                       f"thread_id: {self.thread_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ConnectionScopedWebSocketManager: {e}")
            return False
    
    async def send_agent_started(self, agent_name: str, run_id: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent started event with strict user validation."""
        return await self._send_agent_event("agent_started", {
            "agent_name": agent_name,
            "run_id": run_id,
            "status": "started",
            "metadata": metadata or {},
            "message": f"{agent_name} has started processing your request"
        })
    
    async def send_agent_thinking(self, agent_name: str, run_id: str, 
                                 thought: str, step: Optional[str] = None) -> bool:
        """Send agent thinking event with strict user validation.""" 
        return await self._send_agent_event("agent_thinking", {
            "agent_name": agent_name,
            "run_id": run_id,
            "thought": thought,
            "step": step,
            "message": f"{agent_name} is thinking: {thought[:100]}..."
        })
    
    async def send_tool_executing(self, tool_name: str, run_id: str,
                                 parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Send tool executing event with strict user validation."""
        return await self._send_agent_event("tool_executing", {
            "tool_name": tool_name,
            "run_id": run_id,
            "parameters": parameters or {},
            "status": "executing",
            "message": f"Executing {tool_name}..."
        })
    
    async def send_tool_completed(self, tool_name: str, run_id: str,
                                 result: Optional[Dict[str, Any]] = None) -> bool:
        """Send tool completed event with strict user validation."""
        return await self._send_agent_event("tool_completed", {
            "tool_name": tool_name, 
            "run_id": run_id,
            "result": result or {},
            "status": "completed",
            "message": f"Completed {tool_name}"
        })
    
    async def send_agent_completed(self, agent_name: str, run_id: str,
                                  result: Optional[Dict[str, Any]] = None,
                                  success: bool = True) -> bool:
        """Send agent completed event with strict user validation."""
        status = "completed" if success else "failed"
        return await self._send_agent_event("agent_completed", {
            "agent_name": agent_name,
            "run_id": run_id, 
            "result": result or {},
            "status": status,
            "success": success,
            "message": f"{agent_name} has {'completed' if success else 'failed'}"
        })
    
    async def send_agent_error(self, agent_name: str, run_id: str, 
                              error: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent error event with strict user validation."""
        return await self._send_agent_event("agent_error", {
            "agent_name": agent_name,
            "run_id": run_id,
            "error": error,
            "details": details or {},
            "status": "error",
            "message": f"{agent_name} encountered an error: {error}"
        })
    
    async def _send_agent_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Send agent event with user validation and audit logging."""
        if not self._is_initialized or self._is_cleaned:
            logger.warning(f"Cannot send {event_type} - manager not initialized or cleaned")
            return False
        
        # Create event with required context
        event = {
            "type": event_type,
            "user_id": self.user_id,
            "connection_id": self.connection_id,
            "thread_id": self.thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        
        try:
            # Send through connection handler (which enforces user validation)
            success = await self.handler.send_event(event)
            
            if success:
                self.stats.record_event_sent(event_type)
                logger.debug(f"✅ Sent {event_type} to user {self.user_id[:8]}... "
                           f"connection {self.connection_id}")
                
                # Trigger callbacks
                await self._trigger_callbacks(event_type, event)
                
            else:
                logger.error(f"❌ Failed to send {event_type} to connection {self.connection_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Exception sending {event_type} to {self.connection_id}: {e}")
            return False
    
    async def handle_incoming_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming message with user validation."""
        if not self._is_initialized:
            return {"type": "error", "message": "Manager not initialized"}
        
        self.stats.events_received += 1
        self.stats.update_activity()
        
        # Delegate to connection handler
        return await self.handler.handle_incoming_message(message)
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """Add callback for specific event type."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
        
        logger.debug(f"Added {event_type} callback to connection {self.connection_id}")
    
    async def _trigger_callbacks(self, event_type: str, event: Dict[str, Any]):
        """Trigger callbacks for event type."""
        callbacks = self.event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {e}")
    
    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy."""
        if self._is_cleaned or not self._is_initialized:
            return False
        
        return (self.websocket.client_state == WebSocketState.CONNECTED and
                not self.handler.context._is_cleaned)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        handler_stats = await self.handler.get_stats() if self.handler else {}
        
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "manager_stats": {
                "created_at": self.stats.created_at.isoformat(),
                "last_activity": self.stats.last_activity.isoformat(),
                "events_sent": self.stats.events_sent,
                "events_received": self.stats.events_received,
                "events_blocked": self.stats.events_blocked,
                "total_agent_events": self.stats.total_agent_events,
                "agent_events_breakdown": {
                    "agent_started": self.stats.agent_started_events,
                    "agent_thinking": self.stats.agent_thinking_events, 
                    "tool_executing": self.stats.tool_executing_events,
                    "tool_completed": self.stats.tool_completed_events,
                    "agent_completed": self.stats.agent_completed_events
                }
            },
            "handler_stats": handler_stats,
            "is_healthy": self.is_connection_healthy(),
            "is_initialized": self._is_initialized,
            "is_cleaned": self._is_cleaned
        }
    
    async def cleanup(self):
        """Clean up all connection resources."""
        if self._is_cleaned:
            return
        
        logger.info(f"🧹 Cleaning up ConnectionScopedWebSocketManager for user {self.user_id} "
                   f"connection {self.connection_id}")
        
        try:
            self._is_cleaned = True
            
            # Clean up handler
            if self.handler:
                await self.handler.cleanup()
                self.handler = None
            
            # Clear callbacks
            self.event_callbacks.clear()
            
            # Remove from global tracking
            ConnectionScopedWebSocketManager._active_managers.discard(self.connection_id)
            
            logger.info(f"✅ ConnectionScopedWebSocketManager cleanup completed for {self.connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error during ConnectionScopedWebSocketManager cleanup: {e}")
    
    @classmethod
    def get_global_stats(cls) -> Dict[str, Any]:
        """Get global manager statistics."""
        return {
            "active_managers": len(cls._active_managers),
            "total_created": cls._total_created,
            "active_connection_ids": list(cls._active_managers)
        }


@asynccontextmanager
async def connection_scoped_manager(websocket: WebSocket, user_id: str,
                                   thread_id: Optional[str] = None,
                                   session_id: Optional[str] = None):
    """
    Context manager for connection-scoped WebSocket management.
    
    This ensures proper resource cleanup even if the connection fails.
    
    Usage:
        async with connection_scoped_manager(websocket, user_id, thread_id) as manager:
            # Connection handling code
            await manager.send_agent_started("DataAnalysisAgent", run_id)
    """
    manager = ConnectionScopedWebSocketManager(websocket, user_id, thread_id=thread_id)
    try:
        if await manager.initialize(thread_id=thread_id, session_id=session_id):
            logger.info(f"✅ Connection-scoped manager ready for user {user_id[:8]}...")
            yield manager
        else:
            logger.error(f"Failed to initialize connection-scoped manager for user {user_id}")
            raise Exception("Manager initialization failed")
    finally:
        await manager.cleanup()


# Legacy compatibility - redirect to connection-scoped approach
def get_websocket_manager():
    """
    DEPRECATED: This function returns the old singleton manager.
    
    For new code, use connection_scoped_manager() context manager instead.
    This ensures proper user isolation and prevents event leakage.
    """
    import warnings
    warnings.warn(
        "get_websocket_manager() is deprecated due to cross-user event leakage. "
        "Use connection_scoped_manager() for proper user isolation.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Import the old manager for backward compatibility
    from netra_backend.app.websocket_core.manager import get_websocket_manager as get_legacy_manager
    return get_legacy_manager()