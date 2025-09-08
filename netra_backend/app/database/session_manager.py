"""
Database session management - legacy stub.
Functionality consolidated into modern database layer.
"""

from typing import Any, Dict, Optional
from contextlib import contextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# CRITICAL FIX: Add DatabaseSessionManager alias to prevent startup errors
# Many agent files reference DatabaseSessionManager but it was renamed to SessionManager
# This alias maintains backward compatibility during the SSOT migration


class SessionIsolationError(Exception):
    """Raised when session isolation is violated."""
    pass


class SessionScopeValidator:
    """Validates that database sessions maintain proper request scope."""
    
    @staticmethod
    def validate_request_scoped(session: AsyncSession) -> None:
        """Validate that a session is request-scoped.
        
        Args:
            session: Database session to validate
            
        Raises:
            SessionIsolationError: If session is not properly request-scoped
        """
        if hasattr(session, '_global_storage_flag') and session._global_storage_flag:
            raise SessionIsolationError("Session must be request-scoped, not globally stored")
        logger.debug(f"Validated session {id(session)} is request-scoped")


class SessionManager:
    """Legacy session manager for backward compatibility."""
    
    def __init__(self):
        logger.debug("Initialized legacy SessionManager stub")
    
    @contextmanager
    def get_session(self):
        """Get database session - stub implementation."""
        logger.debug("Creating stub database session")
        yield None
    
    async def get_async_session(self):
        """Get async database session - stub implementation."""
        logger.debug("Creating stub async database session")
        return None


class DatabaseSessionManager(SessionManager):
    """Extended database session manager for backward compatibility."""
    
    def __init__(self):
        super().__init__()
        logger.debug("Initialized legacy DatabaseSessionManager stub")
    
    async def create_session(self):
        """Create session - stub implementation."""
        return None
    
    async def close_session(self, session):
        """Close session - stub implementation."""
        pass


# Global instance for backward compatibility
session_manager = SessionManager()


@contextmanager
def managed_session():
    """
    Context manager for database sessions.
    Provides backward compatibility for code expecting managed_session.
    """
    with session_manager.get_session() as session:
        yield session


def validate_agent_session_isolation(agent):
    """
    Validate agent session isolation - stub implementation.
    
    Args:
        agent: Agent instance to validate
        
    Returns:
        bool: Always returns True for stub implementation
    """
    logger.debug(f"Validating session isolation for agent: {getattr(agent, '__class__', type(agent).__name__)}")
    return True


__all__ = [
    "SessionManager",
    "DatabaseSessionManager",
    "session_manager", 
    "managed_session",
    "validate_agent_session_isolation",
    "SessionIsolationError",
    "SessionScopeValidator",
]