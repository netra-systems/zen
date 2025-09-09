"""User Session Manager - Minimal implementation for integration tests.

This module provides user session management functionality for WebSocket connections.
"""

import logging
from typing import Any, Dict, Optional, Set
from shared.types import UserID

logger = logging.getLogger(__name__)


class UserSessionManager:
    """Minimal user session manager implementation for integration tests."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._user_sessions: Dict[UserID, Set[str]] = {}
        logger.info("UserSessionManager initialized")
    
    async def create_session(self, user_id: UserID, session_data: Dict[str, Any]) -> str:
        """Create a new user session."""
        session_id = f"session_{len(self._sessions)}"
        self._sessions[session_id] = {
            'user_id': user_id,
            'data': session_data,
            'active': True
        }
        
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    async def get_user_sessions(self, user_id: UserID) -> Set[str]:
        """Get all sessions for a user."""
        return self._user_sessions.get(user_id, set())
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data."""
        if session_id in self._sessions:
            self._sessions[session_id]['data'].update(data)
            return True
        return False
    
    async def close_session(self, session_id: str) -> bool:
        """Close a session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session['active'] = False
            user_id = session['user_id']
            if user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)
            return True
        return False
    
    async def is_session_active(self, session_id: str) -> bool:
        """Check if session is active."""
        session = self._sessions.get(session_id)
        return session is not None and session.get('active', False)
    
    def clear_all_sessions(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()
        self._user_sessions.clear()