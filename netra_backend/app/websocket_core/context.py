"""
WebSocket Context for Protocol-Specific Patterns

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Code Quality  
- Value Impact: Eliminates mock object anti-patterns in WebSocket handling
- Strategic Impact: Creates clean, maintainable WebSocket architecture

This module provides WebSocketContext - an honest WebSocket context class
that doesn't pretend to be something it's not (unlike mock Request objects).

Key Features:
- Honest about being WebSocket-specific (no mock objects)
- Tracks connection lifecycle and activity
- Provides connection state validation
- Supports user isolation and thread routing
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class WebSocketContext:
    """Context for WebSocket connections - honest about what it is.
    
    This class represents the context for a WebSocket connection without
    pretending to be an HTTP request. It contains all the information needed
    for WebSocket-specific operations while maintaining clean architecture.
    
    CRITICAL: This replaces the anti-pattern of creating mock Request objects
    for WebSocket connections. Mock objects violate clean architecture and
    create maintenance burden.
    
    Attributes:
        connection_id: Unique identifier for this WebSocket connection
        websocket: The actual WebSocket connection object
        user_id: User associated with this connection
        thread_id: Thread/conversation identifier for routing
        run_id: Current run/session identifier
        connected_at: When the connection was established
        last_activity: Last time this connection had activity
    """
    connection_id: str
    websocket: WebSocket
    user_id: str
    thread_id: str
    run_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post-initialization validation and logging."""
        # Validate required fields
        if not self.connection_id:
            raise ValueError("connection_id is required for WebSocketContext")
        if not self.user_id:
            raise ValueError("user_id is required for WebSocketContext")
        if not self.thread_id:
            raise ValueError("thread_id is required for WebSocketContext")
        if not self.run_id:
            raise ValueError("run_id is required for WebSocketContext")
        if not self.websocket:
            raise ValueError("websocket is required for WebSocketContext")
        
        # Log context creation
        logger.debug(
            f"Created WebSocketContext: connection_id={self.connection_id}, "
            f"user_id={self.user_id}, thread_id={self.thread_id}, "
            f"run_id={self.run_id}"
        )
    
    @property
    def is_active(self) -> bool:
        """Check if the WebSocket connection is still active.
        
        Returns:
            bool: True if connection is active and can receive messages
            
        Note:
            This checks the actual WebSocket state, not just a flag.
            Useful for determining if we can send messages to this connection.
        """
        try:
            return (
                self.websocket is not None and 
                self.websocket.client_state == WebSocketState.CONNECTED
            )
        except Exception as e:
            logger.warning(f"Error checking WebSocket state for {self.connection_id}: {e}")
            return False
    
    def update_activity(self) -> None:
        """Update the last activity timestamp.
        
        Should be called whenever this connection processes a message
        or performs any activity. Useful for connection lifecycle management.
        """
        self.last_activity = datetime.utcnow()
        logger.debug(f"Updated activity timestamp for connection {self.connection_id}")
    
    def get_connection_info(self) -> dict:
        """Get connection information for logging/debugging.
        
        Returns:
            dict: Connection information excluding sensitive data
        """
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active,
            "client_state": (
                self.websocket.client_state.name 
                if self.websocket and hasattr(self.websocket.client_state, 'name')
                else "UNKNOWN"
            )
        }
    
    @classmethod
    def create_for_user(
        cls,
        websocket: WebSocket,
        user_id: str,
        thread_id: str,
        run_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> "WebSocketContext":
        """Factory method to create WebSocketContext for a user.
        
        Args:
            websocket: The WebSocket connection object
            user_id: User identifier
            thread_id: Thread/conversation identifier
            run_id: Optional run identifier (auto-generated if not provided)
            connection_id: Optional connection ID (auto-generated if not provided)
            
        Returns:
            WebSocketContext: Configured context for the user connection
        """
        if not run_id:
            run_id = str(uuid.uuid4())
        
        if not connection_id:
            # Create connection ID with user and timestamp for uniqueness
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            connection_id = f"ws_{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        context = cls(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        logger.info(f"Created WebSocketContext for user {user_id}, connection {connection_id}")
        return context
    
    def validate_for_message_processing(self) -> bool:
        """Validate that this context is ready for message processing.
        
        Returns:
            bool: True if context can be used for processing messages
            
        Raises:
            ValueError: If validation fails with details about the issue
        """
        try:
            # Check connection is active
            if not self.is_active:
                raise ValueError(f"WebSocket connection {self.connection_id} is not active")
            
            # Check required identifiers are present
            if not self.user_id or not self.thread_id or not self.run_id:
                raise ValueError(f"Missing required identifiers in context {self.connection_id}")
            
            # Check connection age (warn if very old)
            age = (datetime.utcnow() - self.connected_at).total_seconds()
            if age > 86400:  # 24 hours
                logger.warning(f"WebSocket connection {self.connection_id} is very old: {age}s")
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocketContext validation failed for {self.connection_id}: {e}")
            raise ValueError(f"WebSocket context validation failed: {e}")
    
    def to_isolation_key(self) -> str:
        """Generate a unique key for user isolation.
        
        Returns:
            str: Unique key for isolating this user's data and operations
        """
        return f"ws_{self.user_id}_{self.thread_id}_{self.run_id}"


@dataclass
class WebSocketRequestContext:
    """Request-oriented WebSocket context for testing and flexible usage.
    
    This class provides a more flexible WebSocket context that doesn't require
    an actual WebSocket connection, making it suitable for testing scenarios
    and contexts where we need WebSocket-like behavior without the connection.
    
    Key differences from WebSocketContext:
    - Optional WebSocket connection (for testing)
    - Allows arbitrary attribute storage
    - More flexible for testing scenarios
    - Compatible with existing test patterns
    
    Attributes:
        user_id: User associated with this context
        thread_id: Thread/conversation identifier
        run_id: Current run/session identifier  
        connection_info: Optional connection information
        created_at: When the context was created
        last_activity: Last time this context had activity
    """
    user_id: str
    thread_id: str
    run_id: str
    connection_info: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    _attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and logging."""
        # Validate required fields
        if not self.user_id:
            raise ValueError("user_id is required for WebSocketRequestContext")
        if not self.thread_id:
            raise ValueError("thread_id is required for WebSocketRequestContext")
        if not self.run_id:
            raise ValueError("run_id is required for WebSocketRequestContext")
        
        # Log context creation
        logger.debug(
            f"Created WebSocketRequestContext: user_id={self.user_id}, "
            f"thread_id={self.thread_id}, run_id={self.run_id}"
        )
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting arbitrary attributes for testing flexibility."""
        if name.startswith('_') or name in {
            'user_id', 'thread_id', 'run_id', 'connection_info', 
            'created_at', 'last_activity'
        }:
            # Use normal attribute setting for defined fields
            super().__setattr__(name, value)
        else:
            # Store other attributes in the _attributes dict
            if not hasattr(self, '_attributes'):
                super().__setattr__('_attributes', {})
            self._attributes[name] = value
    
    def __getattr__(self, name: str) -> Any:
        """Allow getting arbitrary attributes for testing flexibility."""
        if hasattr(self, '_attributes') and name in self._attributes:
            return self._attributes[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    @classmethod
    def create_for_user(
        cls,
        user_id: str,
        thread_id: str,
        connection_info: Optional[Any] = None,
        run_id: Optional[str] = None
    ) -> "WebSocketRequestContext":
        """Factory method to create WebSocketRequestContext for a user.
        
        Args:
            user_id: User identifier
            thread_id: Thread/conversation identifier  
            connection_info: Optional connection information
            run_id: Optional run identifier (auto-generated if not provided)
            
        Returns:
            WebSocketRequestContext: Configured context for the user
        """
        if not run_id:
            run_id = str(uuid.uuid4())
        
        context = cls(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            connection_info=connection_info
        )
        
        logger.info(f"Created WebSocketRequestContext for user {user_id}, run {run_id}")
        return context
    
    def update_activity(self) -> None:
        """Update the last activity timestamp.
        
        Should be called whenever this context processes a message
        or performs any activity. Useful for context lifecycle management.
        """
        self.last_activity = datetime.utcnow()
        logger.debug(f"Updated activity timestamp for context {self.run_id}")
    
    def get_context_info(self) -> dict:
        """Get context information for logging/debugging.
        
        Returns:
            dict: Context information excluding sensitive data
        """
        return {
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "has_connection_info": self.connection_info is not None,
            "additional_attributes": list(self._attributes.keys()) if hasattr(self, '_attributes') else []
        }
    
    def to_isolation_key(self) -> str:
        """Generate a unique key for user isolation.
        
        Returns:
            str: Unique key for isolating this user's data and operations
        """
        return f"wsreq_{self.user_id}_{self.thread_id}_{self.run_id}"