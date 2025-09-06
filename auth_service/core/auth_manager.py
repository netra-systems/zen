"""Mock Auth Manager for testing purposes.

This module provides a mock AuthManager class that can be imported by tests
without requiring the full auth service implementation.
"""

from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock


class AuthManager:
    """Mock Authentication Manager for testing purposes."""
    
    def __init__(self):
        """Initialize the mock auth manager."""
        self.client = AsyncMock()
        self.jwt_handler = AsyncMock()
        self.token_validator = AsyncMock()
        self.is_initialized = False
        self._user_sessions = {}
        
    async def initialize(self):
        """Initialize the auth manager."""
        self.is_initialized = True
        
    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user."""
        # Mock successful authentication
        return {
            "success": True,
            "user_id": f"user_{username}",
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600
        }
        
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a token."""
        # Mock successful validation
        return {
            "valid": True,
            "user_id": "mock_user",
            "expires_at": "2024-12-31T23:59:59Z"
        }
        
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh a token."""
        # Mock successful refresh
        return {
            "success": True,
            "access_token": "new_mock_access_token",
            "expires_in": 3600
        }
        
    async def logout_user(self, user_id: str) -> bool:
        """Log out a user."""
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]
        return True
        
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        return {
            "user_id": user_id,
            "username": f"user_{user_id}",
            "email": f"{user_id}@example.com",
            "roles": ["user"]
        }
        
    async def check_permissions(self, user_id: str, resource: str, action: str) -> bool:
        """Check user permissions."""
        # Mock always allowing access for tests
        return True
        
    async def create_session(self, user_id: str) -> str:
        """Create a user session."""
        session_id = f"session_{user_id}"
        self._user_sessions[user_id] = session_id
        return session_id
        
    async def get_session(self, user_id: str) -> Optional[str]:
        """Get user session."""
        return self._user_sessions.get(user_id)
        
    async def cleanup(self):
        """Clean up auth resources."""
        self._user_sessions.clear()
        self.is_initialized = False
        
    @property 
    def health_check(self):
        """Health check method."""
        return AsyncMock(return_value={"status": "healthy"})