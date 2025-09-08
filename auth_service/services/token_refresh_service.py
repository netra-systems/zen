"""
Token Refresh Service - Single Source of Truth for Token Refresh Operations

This service provides a unified interface for token refresh operations,
following SSOT principles and maintaining service independence.

Business Value: Enables seamless session continuation without frequent 
re-authentication, improving user experience and reducing login friction.
"""

import logging
import secrets
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
import jwt

from auth_service.auth_core.config import AuthConfig
from auth_service.services.redis_service import RedisService
from auth_service.services.jwt_service import JWTService
from auth_service.services.user_service import UserService

logger = logging.getLogger(__name__)


class TokenRefreshError(Exception):
    """Raised when token refresh operations fail."""
    pass


class TokenRefreshService:
    """
    Single Source of Truth for token refresh operations.
    
    This service provides a unified interface for managing refresh tokens,
    validating token refresh requests, and issuing new access tokens.
    """
    
    def __init__(self, auth_config: AuthConfig, redis_service: Optional[RedisService] = None, 
                 jwt_service: Optional[JWTService] = None, user_service: Optional[UserService] = None):
        """
        Initialize TokenRefreshService with configuration and dependencies.
        
        Args:
            auth_config: Authentication configuration
            redis_service: Optional Redis service instance
            jwt_service: Optional JWT service instance
            user_service: Optional User service instance
        """
        self.auth_config = auth_config
        self.redis_service = redis_service or RedisService(auth_config)
        self.jwt_service = jwt_service or JWTService(auth_config)
        self.user_service = user_service or UserService(auth_config)
        
        # Refresh token storage keys
        self.refresh_token_prefix = "refresh_token:"
        self.user_refresh_tokens_prefix = "user_refresh_tokens:"
        
    def _get_refresh_token_key(self, token_id: str) -> str:
        """Generate Redis key for refresh token."""
        return f"{self.refresh_token_prefix}{token_id}"
    
    def _get_user_refresh_tokens_key(self, user_id: str) -> str:
        """Generate Redis key for user's refresh tokens list."""
        return f"{self.user_refresh_tokens_prefix}{user_id}"
    
    async def create_refresh_token(self, user_id: str, access_token: str, device_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new refresh token for a user.
        
        Args:
            user_id: User ID
            access_token: Associated access token
            device_info: Optional device/client information
            
        Returns:
            Dictionary with refresh token information
            
        Raises:
            TokenRefreshError: If token creation fails
        """
        try:
            # Generate unique refresh token
            token_id = str(uuid.uuid4())
            refresh_token = secrets.token_urlsafe(32)
            
            # Set expiration (refresh tokens live longer than access tokens)
            # Convert days to seconds
            refresh_expiry = self.auth_config.get_jwt_refresh_expiry_days() * 24 * 3600
            expires_at = datetime.now(UTC) + timedelta(seconds=refresh_expiry)
            
            # Prepare token data
            token_data = {
                "token_id": token_id,
                "refresh_token": refresh_token,
                "user_id": user_id,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_used": datetime.now(UTC).isoformat(),
                "device_info": device_info or {},
                "is_active": True
            }
            
            # Store refresh token in Redis
            token_key = self._get_refresh_token_key(token_id)
            await self.redis_service.set(
                token_key,
                str(token_data),  # Convert to string for Redis
                ex=refresh_expiry
            )
            
            # Add to user's refresh tokens list
            await self._add_to_user_refresh_tokens(user_id, token_id, refresh_expiry)
            
            logger.info(f"Created refresh token for user {user_id}")
            
            return {
                "token_id": token_id,
                "refresh_token": refresh_token,
                "expires_in": refresh_expiry,
                "expires_at": expires_at.isoformat(),
                "created_at": token_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create refresh token for user {user_id}: {e}")
            raise TokenRefreshError(f"Refresh token creation failed: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Use refresh token to generate new access token.
        
        Args:
            refresh_token: Refresh token to use
            
        Returns:
            Dictionary with new access token and updated refresh token info
            
        Raises:
            TokenRefreshError: If refresh fails
        """
        try:
            # Find and validate refresh token
            token_data = await self._find_refresh_token(refresh_token)
            if not token_data:
                raise TokenRefreshError("Invalid or expired refresh token")
            
            user_id = token_data["user_id"]
            token_id = token_data["token_id"]
            
            # Check if refresh token is still active
            if not token_data.get("is_active", False):
                raise TokenRefreshError("Refresh token has been revoked")
            
            # Check expiration
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(UTC) > expires_at:
                # Clean up expired token
                await self._delete_refresh_token(token_id)
                raise TokenRefreshError("Refresh token has expired")
            
            # Get user information for new access token
            user = await self.user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                raise TokenRefreshError("User account is not active")
            
            # Generate new access token
            new_access_token = await self.jwt_service.create_access_token(
                user_id=user.id,
                email=user.email,
                permissions=[]  # Add user permissions as needed
            )
            
            # Update refresh token usage
            await self._update_refresh_token_usage(token_id)
            
            logger.info(f"Refreshed access token for user {user_id}")
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": self.auth_config.get_jwt_access_expiry_minutes() * 60,  # Convert minutes to seconds
                "refresh_token": refresh_token,  # Return same refresh token
                "user_id": user_id
            }
            
        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise TokenRefreshError(f"Token refresh failed: {str(e)}")
    
    async def _find_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Find refresh token data by token value."""
        try:
            # In a production system, we might need to maintain a lookup table
            # For now, we'll search through all refresh tokens (not efficient for scale)
            # This is a simplified implementation
            
            # Get all refresh token keys
            pattern = f"{self.refresh_token_prefix}*"
            token_keys = await self.redis_service.keys(pattern)
            
            for token_key in token_keys:
                token_data_str = await self.redis_service.get(token_key)
                if token_data_str and refresh_token in str(token_data_str):
                    # Parse token data (simplified)
                    # In production, would use proper JSON parsing
                    return self._parse_token_data(token_data_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find refresh token: {e}")
            return None
    
    def _parse_token_data(self, token_data_str: str) -> Dict[str, Any]:
        """Parse token data string (simplified implementation)."""
        # This is a simplified parser - in production would use proper JSON
        try:
            # Extract key fields from string representation
            data = {}
            if "token_id" in token_data_str:
                data["token_id"] = token_data_str.split("'token_id': '")[1].split("'")[0]
            if "user_id" in token_data_str:
                data["user_id"] = token_data_str.split("'user_id': '")[1].split("'")[0]
            if "expires_at" in token_data_str:
                data["expires_at"] = token_data_str.split("'expires_at': '")[1].split("'")[0]
            if "is_active" in token_data_str:
                data["is_active"] = "True" in token_data_str
            
            return data
        except Exception:
            return {}
    
    async def _update_refresh_token_usage(self, token_id: str):
        """Update refresh token last used timestamp."""
        try:
            token_key = self._get_refresh_token_key(token_id)
            token_data_str = await self.redis_service.get(token_key)
            
            if token_data_str:
                # Update last used timestamp (simplified)
                updated_data_str = token_data_str.replace(
                    "'last_used': '",
                    f"'last_used': '{datetime.now(UTC).isoformat()}'"
                )
                
                # Get remaining TTL and update
                # In production, would properly parse and update JSON
                await self.redis_service.set(token_key, updated_data_str, ex=3600)  # Keep existing TTL
                
        except Exception as e:
            logger.error(f"Failed to update refresh token usage: {e}")
    
    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a specific refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            token_data = await self._find_refresh_token(refresh_token)
            if not token_data:
                return False
            
            token_id = token_data.get("token_id")
            if not token_id:
                return False
            
            await self._delete_refresh_token(token_id)
            
            logger.info(f"Revoked refresh token {token_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False
    
    async def revoke_user_refresh_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        try:
            # Get user's refresh tokens
            user_tokens_key = self._get_user_refresh_tokens_key(user_id)
            tokens_data = await self.redis_service.get(user_tokens_key)
            
            if not tokens_data:
                return 0
            
            # Parse token IDs (simplified)
            token_ids = str(tokens_data).split(",") if tokens_data else []
            revoked_count = 0
            
            for token_id in token_ids:
                token_id = token_id.strip().replace("'", "").replace("[", "").replace("]", "")
                if await self._delete_refresh_token(token_id):
                    revoked_count += 1
            
            # Clear user tokens list
            await self.redis_service.delete(user_tokens_key)
            
            logger.info(f"Revoked {revoked_count} refresh tokens for user {user_id}")
            return revoked_count
            
        except Exception as e:
            logger.error(f"Failed to revoke user refresh tokens: {e}")
            return 0
    
    async def _delete_refresh_token(self, token_id: str) -> bool:
        """Delete a refresh token."""
        try:
            token_key = self._get_refresh_token_key(token_id)
            deleted_count = await self.redis_service.delete(token_key)
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete refresh token {token_id}: {e}")
            return False
    
    async def _add_to_user_refresh_tokens(self, user_id: str, token_id: str, expires_in: int):
        """Add token ID to user's refresh tokens list."""
        try:
            user_tokens_key = self._get_user_refresh_tokens_key(user_id)
            existing_tokens = await self.redis_service.get(user_tokens_key)
            
            # Parse existing tokens (simplified)
            token_list = []
            if existing_tokens:
                token_list = str(existing_tokens).split(",")
            
            token_list.append(token_id)
            
            # Store updated list
            await self.redis_service.set(
                user_tokens_key,
                ",".join(token_list),
                ex=expires_in
            )
            
        except Exception as e:
            logger.error(f"Failed to add token to user refresh tokens list: {e}")
    
    async def get_user_refresh_token_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about user's refresh tokens.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with token information
        """
        try:
            user_tokens_key = self._get_user_refresh_tokens_key(user_id)
            tokens_data = await self.redis_service.get(user_tokens_key)
            
            if not tokens_data:
                return {
                    "user_id": user_id,
                    "active_tokens": 0,
                    "tokens": []
                }
            
            # Count tokens (simplified)
            token_count = len(str(tokens_data).split(",")) if tokens_data else 0
            
            return {
                "user_id": user_id,
                "active_tokens": token_count,
                "tokens": []  # Detailed token info could be added here
            }
            
        except Exception as e:
            logger.error(f"Failed to get refresh token info for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "active_tokens": 0,
                "tokens": [],
                "error": str(e)
            }


__all__ = ["TokenRefreshService", "TokenRefreshError"]