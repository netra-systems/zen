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
        self._jwt_handler = JWTHandler(auth_config)
    
    async def create_access_token(self, user_id: str, email: str, permissions: list = None) -> str:
        """Create an access token."""
        return await self._jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            permissions=permissions or []
        )
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token."""
        return await self._jwt_handler.validate_token(token)


__all__ = ["JWTService"]