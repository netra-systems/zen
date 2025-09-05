"""
Mock Auth Service for Testing

This module provides mock implementations of auth service components
for testing purposes without requiring real dependencies.
"""
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from auth_service.auth_core.models.auth_models import User


class MockSessionManager:
    """Mock implementation of session manager for testing."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the mock session manager."""
        self._initialized = True
    
    async def create_session(self, user: User) -> str:
        """Create a mock session for the user."""
        if not self._initialized:
            await self.initialize()
        
        session_token = f"mock_session_{user.id}_{int(datetime.now(UTC).timestamp())}"
        self._sessions[session_token] = {
            "user_id": user.id,
            "user_email": user.email,
            "created_at": datetime.now(UTC),
            "active": True
        }
        return session_token
    
    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session by token."""
        return self._sessions.get(session_token)
    
    async def validate_session(self, session_token: str) -> bool:
        """Validate if session is active."""
        session = self._sessions.get(session_token)
        return session is not None and session.get("active", False)
    
    async def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session."""
        if session_token in self._sessions:
            self._sessions[session_token]["active"] = False
            return True
        return False
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (mock implementation)."""
        # In a real implementation, this would check timestamps
        pass


class MockAuthService:
    """Mock Auth Service for testing."""
    
    SessionManager = MockSessionManager
    
    def __init__(self):
        self.session_manager = MockSessionManager()
        self._mocked_methods = {}
    
    def mock_method(self, method_name: str, return_value: Any = None, side_effect: Any = None):
        """Mock a specific method on the auth service."""
        mock = AsyncMock() if asyncio.iscoroutinefunction(getattr(self, method_name, None)) else MagicMock()
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        
        setattr(self, method_name, mock)
        self._mocked_methods[method_name] = mock
        return mock
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Mock user authentication."""
        # Simple mock: accept any non-empty credentials
        if email and password:
            return User(id=f"user_{email.split('@')[0]}", email=email)
        return None
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[tuple]:
        """Mock token refresh."""
        if refresh_token and refresh_token.startswith("valid_"):
            new_access = f"access_{int(datetime.now(UTC).timestamp())}"
            new_refresh = f"refresh_{int(datetime.now(UTC).timestamp())}"
            return (new_access, new_refresh)
        return None