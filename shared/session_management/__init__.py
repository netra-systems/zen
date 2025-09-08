"""Shared Session Management Module

This module provides SSOT session management functionality for the entire Netra platform.
It integrates with the UnifiedIdGenerator session management while providing enhanced
functionality for user session lifecycle management.

Key Components:
- UserSessionManager: SSOT for session lifecycle management
- UserSession: Enhanced session data structure
- SessionMetrics: Session monitoring and metrics
- Convenience functions: Easy-to-use session management functions

Usage:
    from shared.session_management import get_user_session, get_session_manager
    
    # Get or create user session (maintains continuity)
    context = await get_user_session(user_id, thread_id)
    
    # Advanced usage with session manager
    session_manager = get_session_manager()
    context = await session_manager.get_or_create_user_session(user_id, thread_id)
"""

from shared.session_management.user_session_manager import (
    UserSessionManager,
    UserSession,
    SessionMetrics,
    SessionManagerError,
    get_session_manager,
    initialize_session_manager,
    shutdown_session_manager,
    get_user_session,
    get_session_metrics
)

__all__ = [
    'UserSessionManager',
    'UserSession', 
    'SessionMetrics',
    'SessionManagerError',
    'get_session_manager',
    'initialize_session_manager',
    'shutdown_session_manager',
    'get_user_session',
    'get_session_metrics'
]