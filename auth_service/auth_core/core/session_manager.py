"""
Session Manager - Legacy compatibility wrapper for session operations

This module provides the SessionManager class that was referenced by tests.
It serves as a compatibility layer for the existing SessionService.

Note: This is a minimal implementation to support test imports.
For production use, prefer auth_service.services.session_service.SessionService
"""

import logging
from typing import Dict, Any, Optional
from auth_service.auth_core.core.jwt_handler import JWTHandler

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Legacy SessionManager class for backward compatibility.

    This class provides the interface expected by existing tests while
    maintaining SSOT principles by delegating to JWTHandler for token operations.
    """

    def __init__(self):
        """Initialize the session manager with JWT handler."""
        self._jwt_handler = JWTHandler()

    def create_session(self, user_data: Dict[str, Any]) -> str:
        """
        Create a session token from user data.

        Args:
            user_data: Dictionary containing user information

        Returns:
            JWT token string representing the session
        """
        try:
            # Use JWT handler to create token - maintains SSOT
            # JWTHandler uses create_access_token method
            token = self._jwt_handler.create_access_token(
                user_id=user_data.get("user_id"),
                email=user_data.get("email"),
                permissions=user_data.get("permissions", [])
            )
            return token
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token.

        Args:
            token: JWT token to validate

        Returns:
            User data if valid, None otherwise
        """
        try:
            # Use JWT handler validate_token method - maintains SSOT
            return self._jwt_handler.validate_token(token)
        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            return None

    async def invalidate_session(self, token: str) -> bool:
        """
        Invalidate a session token.

        Note: JWT tokens are stateless, so this is a no-op
        for this implementation. Real session invalidation would
        require a blacklist or database tracking.

        Args:
            token: JWT token to invalidate

        Returns:
            True (always succeeds for compatibility)
        """
        logger.info(f"Session invalidation requested for token (JWT tokens are stateless)")
        return True


__all__ = ["SessionManager"]