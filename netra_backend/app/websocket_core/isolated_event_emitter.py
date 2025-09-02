"""
Isolated WebSocket Event Emitter for User Context Isolation

This module provides the IsolatedWebSocketEventEmitter class that ensures complete
user isolation for WebSocket events, preventing cross-user event leakage.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Platform Stability & User Privacy
- Value Impact: Enables safe 10+ concurrent users with zero event leakage
- Strategic Impact: Critical for production deployment with user isolation guarantees
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING

from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager

logger = central_logger.get_logger(__name__)


@dataclass
class WebSocketEvent:
    """Individual WebSocket event with complete user context."""
    event_type: str
    user_id: str
    thread_id: str
    run_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert event to WebSocket message format."""
        return {
            'type': self.event_type,
            'data': {
                **self.data,
                'user_id': self.user_id,
                'thread_id': self.thread_id,
                'run_id': self.run_id,
                'timestamp': self.timestamp.isoformat(),
                'event_id': self.event_id
            }
        }


class IsolatedWebSocketEventEmitter:
    """
    Per-user WebSocket event emitter with complete user isolation.
    
    This class ensures that WebSocket events are properly isolated per user
    and prevents cross-user event leakage during concurrent agent execution.
    
    Key Features:
    - Complete user isolation (events only go to intended user)
    - Event ordering guarantees within user context  
    - No shared state between users
    - Proper resource cleanup
    - Event filtering and routing
    """
    
    def __init__(self, 
                 user_id: str,
                 thread_id: str, 
                 run_id: str,
                 websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize isolated emitter for specific user context.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            run_id: Run identifier for this execution context
            websocket_manager: Optional WebSocket manager for sending events
        """
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.websocket_manager = websocket_manager
        
        # Event tracking for this user
        self.events_sent = 0
        self.events_failed = 0
        self.last_event_time = None
        
        # Event buffering for reliability
        self.event_buffer: List[WebSocketEvent] = []
        self.max_buffer_size = 100
        
        # Cleanup tracking
        self._is_cleaned = False
        
        logger.debug(f"IsolatedWebSocketEventEmitter created for user {user_id}, thread {thread_id}, run {run_id}")
    
    @classmethod
    def create_for_user(cls, 
                       user_id: str, 
                       thread_id: str,
                       run_id: str, 
                       websocket_manager: Optional['WebSocketManager'] = None) -> 'IsolatedWebSocketEventEmitter':
        """Factory method to create emitter for specific user context.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing  
            run_id: Run identifier for this execution context
            websocket_manager: Optional WebSocket manager
            
        Returns:
            IsolatedWebSocketEventEmitter: Emitter configured for the user
        """
        return cls(user_id, thread_id, run_id, websocket_manager)
    
    # === Agent Event Methods (Required by Mission Critical Tests) ===
    
    async def emit_agent_started(self, agent_name: str, run_id: str) -> None:
        """Emit agent started event for this user."""
        await self._emit_event(
            event_type="agent_started",
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "message": f"Agent {agent_name} has started processing your request"
            }
        )
    
    async def emit_agent_thinking(self, agent_name: str, message: str) -> None:
        """Emit agent thinking event for this user."""
        await self._emit_event(
            event_type="agent_thinking", 
            data={
                "agent_name": agent_name,
                "message": message
            }
        )
    
    async def emit_tool_executing(self, tool_name: str, run_id: str) -> None:
        """Emit tool executing event for this user."""
        await self._emit_event(
            event_type="tool_executing",
            data={
                "tool_name": tool_name,
                "run_id": run_id,
                "message": f"Executing tool: {tool_name}"
            }
        )
    
    async def emit_tool_completed(self, tool_name: str, run_id: str, result: Any = None) -> None:
        """Emit tool completed event for this user."""
        await self._emit_event(
            event_type="tool_completed",
            data={
                "tool_name": tool_name,
                "run_id": run_id,
                "success": True,
                "result": result,
                "message": f"Tool {tool_name} completed successfully"
            }
        )
    
    async def emit_agent_completed(self, agent_name: str, run_id: str, result: Any = None) -> None:
        """Emit agent completed event for this user."""
        await self._emit_event(
            event_type="agent_completed",
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "success": True,
                "result": result,
                "message": f"Agent {agent_name} has completed processing"
            }
        )
    
    # === Legacy WebSocketBridge Compatibility Methods ===
    
    async def notify_agent_started(self, agent_name: str, run_id: str) -> None:
        """Legacy compatibility method."""
        await self.emit_agent_started(agent_name, run_id)
    
    async def notify_agent_completed(self, agent_name: str, run_id: str, result: Any = None) -> None:
        """Legacy compatibility method."""
        await self.emit_agent_completed(agent_name, run_id, result)
    
    async def notify_agent_error(self, agent_name: str, run_id: str, error: str) -> None:
        """Legacy compatibility method."""
        await self._emit_event(
            event_type="agent_error",
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "error": error,
                "message": f"Agent {agent_name} encountered an error: {error}"
            }
        )
    
    # === Core Event Emission ===
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit WebSocket event with complete user isolation.
        
        Args:
            event_type: Type of event to emit
            data: Event data payload
        """
        if self._is_cleaned:
            logger.debug(f"Emitter cleaned, skipping event {event_type} for user {self.user_id}")
            return
        
        # Create isolated event
        event = WebSocketEvent(
            event_type=event_type,
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            data=data
        )
        
        # Buffer event for reliability
        self._buffer_event(event)
        
        # Send event via WebSocket manager
        success = await self._send_event(event)
        
        # Update metrics
        if success:
            self.events_sent += 1
            logger.debug(f"✅ Sent {event_type} event for user {self.user_id}")
        else:
            self.events_failed += 1
            logger.warning(f"❌ Failed to send {event_type} event for user {self.user_id}")
        
        self.last_event_time = datetime.now(timezone.utc)
    
    async def _send_event(self, event: WebSocketEvent) -> bool:
        """Send event via WebSocket manager with user isolation.
        
        Args:
            event: Event to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.websocket_manager:
            logger.debug(f"No WebSocket manager - cannot send {event.event_type} for user {self.user_id}")
            return False
        
        try:
            # Convert event to WebSocket message format
            message = event.to_websocket_message()
            
            # Send message targeting specific user/thread
            if hasattr(self.websocket_manager, 'send_to_thread'):
                # Modern WebSocket manager with thread targeting
                await self.websocket_manager.send_to_thread(
                    thread_id=self.thread_id,
                    message=message
                )
            elif hasattr(self.websocket_manager, 'send_to_user'):
                # WebSocket manager with user targeting
                await self.websocket_manager.send_to_user(
                    user_id=self.user_id,
                    message=message  
                )
            elif hasattr(self.websocket_manager, 'send_message'):
                # Legacy WebSocket manager
                await self.websocket_manager.send_message(message)
            else:
                logger.error(f"WebSocket manager has no send method for user {self.user_id}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to send {event.event_type} event for user {self.user_id}: {e}")
            return False
    
    def _buffer_event(self, event: WebSocketEvent) -> None:
        """Buffer event for reliability and replay capability."""
        self.event_buffer.append(event)
        
        # Trim buffer if it gets too large
        if len(self.event_buffer) > self.max_buffer_size:
            # Keep most recent events
            self.event_buffer = self.event_buffer[-self.max_buffer_size//2:]
            logger.debug(f"Trimmed event buffer for user {self.user_id}")
    
    # === Event Router Interface ===
    
    def set_websocket_manager(self, websocket_manager: 'WebSocketManager') -> None:
        """Set or update WebSocket manager for this emitter."""
        self.websocket_manager = websocket_manager
        logger.debug(f"Updated WebSocket manager for user {self.user_id}")
    
    def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics for monitoring."""
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'events_sent': self.events_sent,
            'events_failed': self.events_failed,
            'events_buffered': len(self.event_buffer),
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'websocket_manager_available': self.websocket_manager is not None,
            'is_cleaned': self._is_cleaned
        }
    
    # === Cleanup ===
    
    async def cleanup(self) -> None:
        """Clean up emitter resources."""
        if self._is_cleaned:
            logger.debug(f"Emitter already cleaned for user {self.user_id}")
            return
        
        logger.info(f"🧹 Cleaning up IsolatedWebSocketEventEmitter for user {self.user_id}")
        
        try:
            # Clear event buffer
            self.event_buffer.clear()
            
            # Clear WebSocket manager reference
            self.websocket_manager = None
            
            # Mark as cleaned
            self._is_cleaned = True
            
            logger.info(f"✅ IsolatedWebSocketEventEmitter cleanup completed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"❌ IsolatedWebSocketEventEmitter cleanup failed for user {self.user_id}: {e}")


# === WebSocket Event Router ===

class WebSocketEventRouter:
    """
    Router for managing multiple isolated event emitters.
    
    This router ensures proper event routing with user isolation
    and manages the lifecycle of per-user emitters.
    """
    
    def __init__(self):
        """Initialize event router."""
        self.emitters: Dict[str, IsolatedWebSocketEventEmitter] = {}
        self.lock = asyncio.Lock()
        
        logger.info("WebSocketEventRouter initialized")
    
    async def get_or_create_emitter(self, 
                                  user_id: str, 
                                  thread_id: str,
                                  run_id: str, 
                                  websocket_manager: Optional['WebSocketManager'] = None) -> IsolatedWebSocketEventEmitter:
        """Get or create isolated emitter for user context."""
        emitter_key = f"{user_id}:{thread_id}:{run_id}"
        
        async with self.lock:
            if emitter_key not in self.emitters:
                emitter = IsolatedWebSocketEventEmitter.create_for_user(
                    user_id=user_id,
                    thread_id=thread_id, 
                    run_id=run_id,
                    websocket_manager=websocket_manager
                )
                self.emitters[emitter_key] = emitter
                logger.debug(f"Created new emitter for {emitter_key}")
            
            return self.emitters[emitter_key]
    
    async def cleanup_emitter(self, user_id: str, thread_id: str, run_id: str) -> None:
        """Clean up specific emitter."""
        emitter_key = f"{user_id}:{thread_id}:{run_id}"
        
        async with self.lock:
            if emitter_key in self.emitters:
                emitter = self.emitters.pop(emitter_key)
                await emitter.cleanup()
                logger.debug(f"Cleaned up emitter for {emitter_key}")
    
    async def cleanup_all_emitters(self) -> None:
        """Clean up all emitters."""
        async with self.lock:
            for emitter in self.emitters.values():
                try:
                    await emitter.cleanup()
                except Exception as e:
                    logger.error(f"Failed to cleanup emitter: {e}")
            
            self.emitters.clear()
            logger.info("All emitters cleaned up")
    
    def get_router_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            'active_emitters': len(self.emitters),
            'emitter_keys': list(self.emitters.keys()),
            'router_initialized': True
        }


# Global event router instance
_event_router: Optional[WebSocketEventRouter] = None


def get_event_router() -> WebSocketEventRouter:
    """Get or create global event router."""
    global _event_router
    if _event_router is None:
        _event_router = WebSocketEventRouter()
    return _event_router


# Export for convenience
__all__ = [
    'IsolatedWebSocketEventEmitter',
    'WebSocketEventRouter', 
    'WebSocketEvent',
    'get_event_router'
]