"""
Session Model: Single Source of Truth for Session Management

This module provides the Session model for auth session management, extending
the SessionInfo from schemas.auth_types with additional fields required for
comprehensive session lifecycle management.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Provide robust session management for auth infrastructure
- Value Impact: Enable secure, scalable session handling
- Revenue Impact: Support auth system reliability
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from netra_backend.app.schemas.auth_types import SessionInfo


class Session(BaseModel):
    """
    Comprehensive Session model for auth session management.
    
    Extends SessionInfo with additional fields required for:
    - Device tracking
    - Timeout management
    - Session data storage
    - Migration capabilities
    - Recovery scenarios
    """
    # Core session identification
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="Associated user ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Device and network information
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Session configuration
    timeout_seconds: Optional[int] = Field(default=3600, description="Session timeout in seconds")
    
    # Session state and data
    is_valid: bool = Field(default=True, description="Whether session is currently valid")
    is_expired: bool = Field(default=False, description="Whether session has expired")
    
    # Flexible session data storage
    session_data: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary session data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    
    # Migration support
    migrated_from: Optional[str] = Field(default=None, description="Previous session ID if migrated")
    migrated_to: Optional[str] = Field(default=None, description="New session ID if migrated")
    
    def is_session_expired(self) -> bool:
        """Check if session is expired based on timeout or explicit expiry."""
        now = datetime.now(timezone.utc)
        
        # Check explicit expiry
        if self.expires_at and now > self.expires_at:
            return True
            
        # Check timeout-based expiry
        if self.timeout_seconds:
            timeout_threshold = self.last_activity.timestamp() + self.timeout_seconds
            return now.timestamp() > timeout_threshold
            
        return False
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def mark_invalid(self) -> None:
        """Mark session as invalid."""
        self.is_valid = False
        self.is_expired = True
    
    def store_data(self, key: str, value: Any) -> None:
        """Store data in session."""
        self.session_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from session."""
        return self.session_data.get(key, default)

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow"
    )


# Backward compatibility alias
SessionModel = Session

__all__ = ["Session", "SessionModel"]