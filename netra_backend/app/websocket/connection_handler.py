"""
Connection-scoped WebSocket handler with zero event leakage between users.

Business Value Justification:
- Segment: All (Free → Enterprise) 
- Business Goal: User Isolation & Chat Value Delivery
- Value Impact: Eliminates cross-user event leakage that destroys user trust
- Strategic Impact: CRITICAL - Core chat functionality requires isolated events

This module implements strict per-connection WebSocket event handling to prevent
event leakage between users. Each connection gets its own handler instance that
only processes events intended for that specific user.

Key Security Features:
1. Connection-scoped handlers - No shared state between connections
2. User ID validation on ALL messages - Messages tagged with validated user context
3. Event filtering - Only events for the authenticated user are delivered
4. Automatic cleanup - Resources freed on disconnect
5. Audit logging - All event routing decisions logged for debugging

Architecture:
- Each WebSocket connection gets a unique ConnectionHandler instance
- ConnectionHandler is bound to authenticated user_id and connection_id  
- All events are validated against the bound user_id before delivery
- Handler automatically cleans up on connection close
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UserWebSocketEmitter
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionContext:
    """Per-connection context with strict user isolation."""
    connection_id: str
    user_id: str
    websocket: WebSocket
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Event tracking for this connection only
    events_received: int = 0
    events_sent: int = 0
    events_filtered: int = 0  # Events blocked due to user mismatch
    
    # Connection state
    is_authenticated: bool = False
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _is_cleaned: bool = False
    
    # SECURITY FIX: Event buffering to prevent race conditions
    _event_buffer: List[Dict[str, Any]] = field(default_factory=list)
    _buffer_enabled: bool = True
    _max_buffer_size: int = 50
    
    async def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def add_to_buffer(self, event: Dict[str, Any]) -> bool:
        """Add event to buffer if buffering is enabled.
        
        Returns:
            bool: True if event was buffered, False if buffer is full or disabled
        """
        if not self._buffer_enabled:
            return False
            
        if len(self._event_buffer) >= self._max_buffer_size:
            logger.warning(f"Event buffer full for connection {self.connection_id}, dropping oldest events")
            # Drop oldest events to make room
            self._event_buffer = self._event_buffer[-(self._max_buffer_size//2):]
        
        self._event_buffer.append(event)
        logger.debug(f"Buffered event for connection {self.connection_id}, buffer size: {len(self._event_buffer)}")
        return True
    
    def get_buffered_events(self) -> List[Dict[str, Any]]:
        """Get and clear all buffered events."""
        events = self._event_buffer.copy()
        self._event_buffer.clear()
        self._buffer_enabled = False  # Disable buffering after first flush
        logger.debug(f"Flushed {len(events)} buffered events for connection {self.connection_id}")
        return events
    
    def is_thread_associated(self) -> bool:
        """Check if thread_id has been properly associated."""
        return self.thread_id is not None and self.is_authenticated
    
    async def cleanup(self):
        """Clean up connection resources."""
        if self._is_cleaned:
            return
        
        logger.info(f"🧹 Cleaning up ConnectionContext for user {self.user_id} connection {self.connection_id}")
        # Clear any remaining buffered events
        if self._event_buffer:
            logger.warning(f"Discarding {len(self._event_buffer)} unbuffered events for {self.connection_id}")
            self._event_buffer.clear()
        self._is_cleaned = True


class ConnectionHandler:
    """
    Per-connection WebSocket handler with enforced user isolation.
    
    This handler is created for each WebSocket connection and ensures:
    1. All events are validated against the authenticated user_id
    2. No events leak between different user connections
    3. Automatic resource cleanup on disconnect
    4. Comprehensive audit logging of event routing decisions
    
    CRITICAL: Each instance is bound to ONE user_id and ONE connection.
    Events for different user_ids are automatically rejected.
    """
    
    # Class-level tracking for monitoring (but not shared state)
    _active_handlers: Set[str] = set()
    _total_created: int = 0
    
    def __init__(self, websocket: WebSocket, user_id: str, connection_id: Optional[str] = None):
        """Initialize handler for specific user connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: Authenticated user ID this handler serves
            connection_id: Optional connection ID (generated if not provided)
        """
        self.connection_id = connection_id or f"conn_{user_id}_{uuid.uuid4().hex[:8]}"
        self.context = ConnectionContext(
            connection_id=self.connection_id,
            user_id=user_id,
            websocket=websocket
        )
        
        # Event router for infrastructure
        self.event_router = WebSocketEventRouter()
        
        # Per-connection event emitter (no shared state)
        self.emitter: Optional[UserWebSocketEmitter] = None
        
        # Strict filtering - only events for this user_id
        self.allowed_user_id = user_id
        
        # Track this handler globally for monitoring
        ConnectionHandler._active_handlers.add(self.connection_id)
        ConnectionHandler._total_created += 1
        
        logger.info(f"🔌 ConnectionHandler created for user {user_id[:8]}... "
                   f"connection {self.connection_id}")
    
    async def authenticate(self, thread_id: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """Authenticate and initialize the connection.
        
        Args:
            thread_id: Optional thread ID for this connection
            session_id: Optional session ID for this connection
            
        Returns:
            bool: True if authentication successful
        """
        try:
            self.context.thread_id = thread_id
            self.context.session_id = session_id
            self.context.is_authenticated = True
            
            # Create UserExecutionContext for this specific user
            user_context = UserExecutionContext(
                user_id=self.context.user_id,
                thread_id=thread_id,
                run_id=f"ws_{self.connection_id}",
                request_id=self.connection_id
            )
            
            # Create isolated emitter for this user only
            self.emitter = UserWebSocketEmitter(
                context=user_context, 
                router=self.event_router,
                connection_id=self.connection_id
            )
            
            logger.info(f"✅ ConnectionHandler authenticated for user {self.context.user_id[:8]}... "
                       f"thread_id: {thread_id}")
            
            # SECURITY FIX: Flush any buffered events that arrived before thread association
            buffered_events = self.context.get_buffered_events()
            if buffered_events:
                logger.info(f"🔄 Flushing {len(buffered_events)} buffered events for connection {self.connection_id}")
                for event in buffered_events:
                    try:
                        await self.emitter.send_event(event)
                        self.context.events_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send buffered event: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed for connection {self.connection_id}: {e}")
            return False
    
    async def handle_incoming_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming message from client with strict user validation.
        
        Args:
            message: Message received from client
            
        Returns:
            Optional response message or None
        """
        if not self.context.is_authenticated:
            logger.warning(f"🚫 Rejecting message from unauthenticated connection {self.connection_id}")
            return {"type": "error", "message": "Connection not authenticated"}
        
        await self.context.update_activity()
        self.context.events_received += 1
        
        # CRITICAL: Validate message is for this user
        message_user_id = message.get("user_id")
        if message_user_id and message_user_id != self.allowed_user_id:
            logger.error(f"🚨 SECURITY VIOLATION: Message for user {message_user_id} "
                        f"sent to connection for user {self.allowed_user_id}")
            self.context.events_filtered += 1
            return {"type": "error", "message": "Message user mismatch"}
        
        # Process valid message
        message_type = message.get("type", "unknown")
        logger.debug(f"📨 Processing {message_type} message for user {self.context.user_id[:8]}...")
        
        # Handle thread association
        if message_type == "join_thread" and "thread_id" in message:
            thread_id = message["thread_id"]
            self.context.thread_id = thread_id
            logger.info(f"🔗 Connection {self.connection_id} joined thread {thread_id}")
            
            return {
                "type": "thread_joined", 
                "thread_id": thread_id,
                "connection_id": self.connection_id
            }
        
        return None
    
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to client with strict user validation.
        
        Args:
            event: Event to send to client
            
        Returns:
            bool: True if event sent successfully
        """
        # SECURITY FIX: Handle events before thread association is complete
        if not self.context.is_authenticated:
            # If user is not authenticated but we have a valid user connection, buffer the event
            if (self.context.user_id and 
                event.get("user_id") == self.context.user_id and 
                self.context.add_to_buffer(event)):
                logger.debug(f"📦 Buffered event for connection {self.connection_id} "
                           f"waiting for authentication")
                return True
            else:
                logger.warning(f"🚫 Cannot buffer event for unauthenticated connection {self.connection_id}")
                return False
        
        # Check if emitter is available
        if not self.emitter:
            logger.warning(f"🚫 No emitter available for connection {self.connection_id}")
            return False
        
        # CRITICAL: Validate event is for this user
        event_user_id = event.get("user_id")
        event_thread_id = event.get("thread_id")
        
        # Block events for different users
        if event_user_id and event_user_id != self.allowed_user_id:
            logger.error(f"🚨 BLOCKED: Event for user {event_user_id} blocked from "
                        f"user {self.allowed_user_id} connection {self.connection_id}")
            self.context.events_filtered += 1
            return False
        
        # Block events for different threads (if thread filtering enabled)
        if (self.context.thread_id and event_thread_id and 
            event_thread_id != self.context.thread_id):
            logger.debug(f"🚫 Event for thread {event_thread_id} blocked from "
                        f"connection on thread {self.context.thread_id}")
            self.context.events_filtered += 1
            return False
        
        # Add connection context to event
        event_with_context = {
            **event,
            "connection_id": self.connection_id,
            "user_id": self.allowed_user_id,  # Ensure user_id is set correctly
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Send through WebSocket
            await self.context.websocket.send_json(event_with_context)
            self.context.events_sent += 1
            await self.context.update_activity()
            
            logger.debug(f"✅ Sent {event.get('type', 'unknown')} event to "
                        f"user {self.context.user_id[:8]}... connection {self.connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send event to connection {self.connection_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "connection_id": self.connection_id,
            "user_id": self.context.user_id,
            "thread_id": self.context.thread_id,
            "is_authenticated": self.context.is_authenticated,
            "created_at": self.context.created_at.isoformat(),
            "last_activity": self.context.last_activity.isoformat(),
            "events_received": self.context.events_received,
            "events_sent": self.context.events_sent, 
            "events_filtered": self.context.events_filtered,
            "connection_state": self.context.websocket.client_state.name
        }
    
    async def cleanup(self):
        """Clean up connection resources."""
        logger.info(f"🧹 Cleaning up ConnectionHandler for user {self.context.user_id} "
                   f"connection {self.connection_id}")
        
        try:
            # Clean up emitter
            if self.emitter:
                # UserWebSocketEmitter doesn't have cleanup method, but context does
                if hasattr(self.emitter, 'cleanup'):
                    await self.emitter.cleanup()
                self.emitter = None
            
            # Clean up connection context
            await self.context.cleanup()
            
            # Remove from global tracking
            ConnectionHandler._active_handlers.discard(self.connection_id)
            
            logger.info(f"✅ ConnectionHandler cleanup completed for {self.connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error during ConnectionHandler cleanup: {e}")
    
    @classmethod
    def get_global_stats(cls) -> Dict[str, Any]:
        """Get global handler statistics."""
        return {
            "active_handlers": len(cls._active_handlers),
            "total_created": cls._total_created,
            "active_connection_ids": list(cls._active_handlers)
        }


@asynccontextmanager
async def connection_scope(websocket: WebSocket, user_id: str, 
                          thread_id: Optional[str] = None, 
                          session_id: Optional[str] = None):
    """
    Context manager for connection-scoped WebSocket handling.
    
    This ensures proper resource cleanup even if the connection fails.
    
    Usage:
        async with connection_scope(websocket, user_id) as handler:
            await handler.authenticate(thread_id=thread_id)
            # Connection handling code
    """
    handler = ConnectionHandler(websocket, user_id)
    try:
        if await handler.authenticate(thread_id=thread_id, session_id=session_id):
            yield handler
        else:
            logger.error(f"Failed to authenticate connection for user {user_id}")
            raise Exception("Authentication failed")
    finally:
        await handler.cleanup()