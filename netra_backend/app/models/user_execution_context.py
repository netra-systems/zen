"""
UserExecutionContext: Critical Context Validation for User Operations

This module provides the UserExecutionContext class for ensuring proper context
validation and preventing data leakage between users. This class enforces strict
validation rules to fail fast when invalid or placeholder values are provided.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) 
- Business Goal: Prevent data leakage and ensure proper request isolation
- Value Impact: Guarantees user data security and request traceability
- Revenue Impact: Prevents security breaches that could damage trust and revenue

Key Security Features:
- Fails fast on placeholder values like "None" or "registry"
- Ensures all context fields are properly populated
- Prevents cross-user data contamination
- Enables proper request tracking and debugging
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserExecutionContext:
    """
    Critical context validation class for user operations.
    
    This class ensures that all user execution contexts have valid, non-placeholder
    values to prevent data leakage between users and enable proper request isolation.
    
    The validation is designed to fail fast and provide clear error messages when
    invalid context is provided, preventing silent failures that could lead to
    security vulnerabilities.
    
    Attributes:
        user_id (str): Unique identifier for the user making the request.
                      Must not be None, empty, or the string "None".
        thread_id (str): Unique identifier for the conversation thread.
                        Must not be None or empty.
        run_id (str): Unique identifier for the current execution run.
                     Must not be None, empty, or the placeholder "registry".
        request_id (str): Unique identifier for the specific request.
                         Must not be None or empty.
        websocket_client_id (Optional[str]): Unique identifier for the specific WebSocket client.
                                               Optional, used for targeted event emission.
    
    Raises:
        ValueError: If any field contains invalid or placeholder values.
        
    Example:
        >>> context = UserExecutionContext(
        ...     user_id="user_123",
        ...     thread_id="thread_456", 
        ...     run_id="run_789",
        ...     request_id="req_012",
        ...     websocket_client_id="conn_345"
        ... )
        
        >>> # This will raise ValueError
        >>> invalid_context = UserExecutionContext(
        ...     user_id="None",  # Invalid placeholder
        ...     thread_id="thread_456",
        ...     run_id="registry",  # Invalid placeholder
        ...     request_id="req_012"
        ... )
    """
    user_id: str
    thread_id: str
    run_id: str
    request_id: str
    websocket_client_id: Optional[str] = None
    
    def __post_init__(self) -> None:
        """
        Validate all context fields to ensure they contain valid values.
        
        This validation is critical for preventing data leakage and ensuring
        proper request isolation. It fails fast with clear error messages
        to help developers identify context validation issues immediately.
        
        Raises:
            ValueError: If any field contains invalid or placeholder values.
        """
        # Validate user_id
        if self.user_id is None:
            raise ValueError("UserExecutionContext.user_id cannot be None - this prevents proper user isolation")
        
        if self.user_id == "":
            raise ValueError("UserExecutionContext.user_id cannot be empty - this prevents proper user isolation")
            
        if self.user_id == "None":
            raise ValueError("UserExecutionContext.user_id cannot be the string 'None' - this is a placeholder value that indicates improper context initialization")
        
        # Validate thread_id
        if self.thread_id is None:
            raise ValueError("UserExecutionContext.thread_id cannot be None - this prevents proper conversation tracking")
            
        if self.thread_id == "":
            raise ValueError("UserExecutionContext.thread_id cannot be empty - this prevents proper conversation tracking")
        
        # Validate run_id
        if self.run_id is None:
            raise ValueError("UserExecutionContext.run_id cannot be None - this prevents proper execution tracking")
            
        if self.run_id == "":
            raise ValueError("UserExecutionContext.run_id cannot be empty - this prevents proper execution tracking")
            
        if self.run_id == "registry":
            raise ValueError("UserExecutionContext.run_id cannot be 'registry' - this is a placeholder value that indicates improper context initialization")
        
        # Validate request_id
        if self.request_id is None:
            raise ValueError("UserExecutionContext.request_id cannot be None - this prevents proper request tracking")
            
        if self.request_id == "":
            raise ValueError("UserExecutionContext.request_id cannot be empty - this prevents proper request tracking")
    
    def to_dict(self) -> dict:
        """
        Convert the context to a dictionary representation.
        
        Returns:
            dict: Dictionary containing all context fields.
        """
        return {
            "user_id": self.user_id,
            "thread_id": self.thread_id, 
            "run_id": self.run_id,
            "request_id": self.request_id,
            "websocket_client_id": self.websocket_client_id
        }
    
    def __str__(self) -> str:
        """
        String representation for debugging and logging.
        
        Note: user_id is truncated for security in logs.
        
        Returns:
            str: Human-readable string representation.
        """
        # Truncate user_id for security in logs
        safe_user_id = f"{self.user_id[:8]}..." if len(self.user_id) > 8 else self.user_id
        return f"UserExecutionContext(user_id={safe_user_id}, thread_id={self.thread_id}, run_id={self.run_id}, request_id={self.request_id})"
    
    def __repr__(self) -> str:
        """
        Detailed representation for debugging.
        
        Returns:
            str: Detailed string representation.
        """
        return f"UserExecutionContext(user_id='{self.user_id}', thread_id='{self.thread_id}', run_id='{self.run_id}', request_id='{self.request_id}', websocket_connection_id='{self.websocket_connection_id}')"


__all__ = ["UserExecutionContext"]