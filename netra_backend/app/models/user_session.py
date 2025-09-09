"""User Session Model - Compatibility Wrapper for SSOT UserSession

This module provides backward compatibility for test imports that expect
netra_backend.app.models.user_session, redirecting to the canonical UserSession model
defined in shared.session_management.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test infrastructure stability  
- Value Impact: Enable seamless imports without breaking existing test code
- Strategic Impact: Prevents cascade test failures and maintains SSOT compliance
"""

# Import UserSession from canonical SSOT location
from shared.session_management.user_session_manager import (
    UserSession,
    SessionManagerError,
    UserSessionManager,
    get_session_manager
)

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# Additional compatibility exports for tests
@dataclass
class SessionState:
    """Compatibility class for session state tracking in tests."""
    is_active: bool = True
    connection_count: int = 0
    last_ping: Optional[datetime] = None
    
    def mark_active(self):
        """Mark session as active."""
        self.is_active = True
        self.last_ping = datetime.now()
    
    def mark_inactive(self):
        """Mark session as inactive."""
        self.is_active = False


@dataclass
class SessionMetadata:
    """Compatibility class for session metadata in tests."""
    client_info: Dict[str, str] = None
    connection_type: str = "websocket"
    session_tags: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.client_info is None:
            self.client_info = {}
        if self.session_tags is None:
            self.session_tags = {}


# Re-export for backward compatibility
__all__ = [
    "UserSession", 
    "SessionManagerError", 
    "UserSessionManager",
    "get_session_manager",
    "SessionState",
    "SessionMetadata"
]