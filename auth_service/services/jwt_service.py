"""
JWT Service - Single Source of Truth for JWT Token Management

This service provides a unified interface for JWT token operations,
following SSOT principles and maintaining service independence.
"""

import logging
from typing import Dict, Any, Optional
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)


class JWTService:
    """
    Single Source of Truth for JWT token management operations.
    
    This service wraps the existing JWTHandler to provide a consistent interface.
    """
    
    def __init__(self, auth_config: AuthConfig):
        """Initialize JWT service with configuration."""
        self.auth_config = auth_config
        self._jwt_handler = JWTHandler()  # JWTHandler gets config from AuthConfig internally
    
    async def create_access_token(self, user_id: str, email: str, permissions: list = None) -> str:
        """Create an access token."""
        return self._jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            permissions=permissions or []
        )
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token."""
        return self._jwt_handler.validate_token(token)
    
    async def create_refresh_token(self, user_id: str, email: str = None, permissions: list = None) -> str:
        """Create a refresh token."""
        return self._jwt_handler.create_refresh_token(user_id, email, permissions)
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[tuple]:
        """Generate new access token from refresh token."""
        return self._jwt_handler.refresh_access_token(refresh_token)
    
    async def validate_refresh_token(self, token: str, user_id: str) -> bool:
        """Validate a refresh token for a specific user."""
        payload = self._jwt_handler.validate_token(token, token_type="refresh")
        if not payload:
            return False
        return payload.get("sub") == user_id


__all__ = ["JWTService"]