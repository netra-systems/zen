"""
SSOT Re-export of DatabaseSessionManager.
Maintains backward compatibility while following Single Source of Truth principles.
"""

# SSOT import from the actual implementation
from netra_backend.app.database.session_manager import (
    DatabaseSessionManager,
    SessionManager,
    session_manager,
    managed_session,
    validate_agent_session_isolation,
    SessionIsolationError,
    SessionScopeValidator,
)

# Re-export for backward compatibility
__all__ = [
    "DatabaseSessionManager",
    "SessionManager", 
    "session_manager",
    "managed_session",
    "validate_agent_session_isolation",
    "SessionIsolationError",
    "SessionScopeValidator",
]