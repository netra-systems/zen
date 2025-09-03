"""
WebSocket Exception Classes for Loud Failure Handling

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Experience  
- Value Impact: Eliminates silent failures that cause 15% user abandonment
- Strategic Impact: Makes all WebSocket failures visible and recoverable

These exceptions ensure that WebSocket failures are LOUD and visible,
never silent. They propagate up the stack to ensure proper error handling
and user notification.
"""

from typing import Optional, Dict, Any


class WebSocketError(Exception):
    """Base exception for all WebSocket-related errors."""
    
    def __init__(self, message: str, user_id: Optional[str] = None, 
                 thread_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.user_id = user_id
        self.thread_id = thread_id
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/monitoring."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "context": self.context
        }


class WebSocketBridgeUnavailableError(WebSocketError):
    """Raised when WebSocket bridge is None or unavailable."""
    
    def __init__(self, operation: str, user_id: Optional[str] = None,
                 thread_id: Optional[str] = None):
        message = f"WebSocket bridge unavailable for operation: {operation}"
        super().__init__(message, user_id, thread_id, {"operation": operation})


class WebSocketSendFailureError(WebSocketError):
    """Raised when sending a WebSocket message fails."""
    
    def __init__(self, reason: str, event_type: str, user_id: Optional[str] = None,
                 thread_id: Optional[str] = None):
        message = f"Failed to send WebSocket event '{event_type}': {reason}"
        super().__init__(message, user_id, thread_id, 
                        {"event_type": event_type, "failure_reason": reason})


class WebSocketConnectionLostError(WebSocketError):
    """Raised when WebSocket connection is lost during operation."""
    
    def __init__(self, user_id: str, thread_id: Optional[str] = None,
                 last_event: Optional[str] = None):
        message = f"WebSocket connection lost for user {user_id}"
        super().__init__(message, user_id, thread_id, {"last_event": last_event})


class WebSocketBufferOverflowError(WebSocketError):
    """Raised when message buffer overflows."""
    
    def __init__(self, buffer_size: int, message_size: int, 
                 user_id: Optional[str] = None):
        message = f"Message buffer overflow: message size {message_size} exceeds buffer {buffer_size}"
        super().__init__(message, user_id, context={
            "buffer_size": buffer_size,
            "message_size": message_size
        })


class WebSocketContextValidationError(WebSocketError):
    """Raised when WebSocket context validation fails."""
    
    def __init__(self, validation_error: str, run_id: Optional[str] = None,
                 user_id: Optional[str] = None):
        message = f"WebSocket context validation failed: {validation_error}"
        super().__init__(message, user_id, context={
            "run_id": run_id,
            "validation_error": validation_error
        })


class WebSocketManagerNotInitializedError(WebSocketError):
    """Raised when WebSocket manager is not properly initialized."""
    
    def __init__(self, component: str):
        message = f"WebSocket manager not initialized in {component}"
        super().__init__(message, context={"component": component})


class AgentCommunicationFailureError(WebSocketError):
    """Raised when agent-to-agent communication fails."""
    
    def __init__(self, from_agent: str, to_agent: str, reason: str,
                 user_id: Optional[str] = None):
        message = f"Communication failure from {from_agent} to {to_agent}: {reason}"
        super().__init__(message, user_id, context={
            "from_agent": from_agent,
            "to_agent": to_agent,
            "failure_reason": reason
        })


class WebSocketEventDroppedError(WebSocketError):
    """Raised when a WebSocket event is dropped/lost."""
    
    def __init__(self, event_type: str, reason: str, user_id: Optional[str] = None,
                 thread_id: Optional[str] = None):
        message = f"WebSocket event '{event_type}' dropped: {reason}"
        super().__init__(message, user_id, thread_id, {
            "event_type": event_type,
            "drop_reason": reason
        })