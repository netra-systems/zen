"""JWT Token Management Service for Authentication Subdomain.

Provides secure JWT token generation, validation, refresh, and revocation
for multi-environment authentication with PR-specific token support.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union

from jose import jwt, JWTError
from pydantic import BaseModel, Field

from app.core.exceptions_auth import AuthenticationError
from app.core.exceptions_base import ValidationError
from app.redis_manager import RedisManager
from app.config import get_config
from app.logging_config import central_logger as logger


class TokenClaims(BaseModel):
    """JWT token claims structure."""
    user_id: str
    email: str
    environment: str
    pr_number: Optional[str] = None
    iat: int = Field(description="Issued at timestamp")
    exp: int = Field(description="Expiration timestamp")
    jti: str = Field(description="JWT ID for revocation tracking")


class JWTTokenManager:
    """JWT token management with Redis-based revocation support."""
    
    def __init__(self):
        """Initialize JWT manager with configuration."""
        self.config = get_config()
        self.algorithm = "HS256"
        self.expiration_hours = 1
        self.redis_manager = RedisManager()
        
    def _get_secret_key(self) -> str:
        """Get JWT secret key from configuration."""
        secret = getattr(self.config, 'jwt_secret_key', None)
        if not secret:
            secret = os.getenv('JWT_SECRET_KEY')
        if not secret:
            raise AuthenticationError("JWT secret key not configured")
        return secret
        
    def _create_revocation_key(self, jti: str) -> str:
        """Create Redis key for token revocation."""
        return f"revoked_token:{jti}"
        
    def _build_jwt_claims(self, user_data: Dict[str, Any], environment: str, 
                          pr_number: Optional[str], now: datetime, jti: str) -> Dict[str, Any]:
        """Build JWT claims dictionary."""
        return {
            "user_id": user_data["user_id"], "email": user_data["email"],
            "environment": environment, "pr_number": pr_number,
            "iat": int(now.timestamp()), "exp": self._calculate_expiration(now),
            "jti": jti
        }
    
    def _calculate_expiration(self, now: datetime) -> int:
        """Calculate JWT expiration timestamp."""
        return int((now + timedelta(hours=self.expiration_hours)).timestamp())
    
    async def generate_jwt(
        self, 
        user_data: Dict[str, Any], 
        environment: str, 
        pr_number: Optional[str] = None
    ) -> str:
        """Generate JWT token with user claims and environment context."""
        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        claims = self._build_jwt_claims(user_data, environment, pr_number, now, jti)
        token = jwt.encode(claims, self._get_secret_key(), algorithm=self.algorithm)
        logger.info(f"JWT generated for user {user_data['user_id']} in env {environment}")
        return token
        
    async def validate_jwt(self, token: str) -> TokenClaims:
        """Validate JWT token and return decoded claims."""
        try:
            payload = jwt.decode(token, self._get_secret_key(), algorithms=[self.algorithm])
        except JWTError as e:
            raise AuthenticationError(f"Invalid JWT token: {str(e)}")
            
        if await self.is_token_revoked(token):
            raise AuthenticationError("Token has been revoked")
            
        return TokenClaims(**payload)
        
    async def refresh_jwt(self, old_token: str) -> str:
        """Refresh expiring JWT token with new expiration time."""
        claims = await self.validate_jwt(old_token)
        await self.revoke_jwt(old_token)
        
        user_data = {"user_id": claims.user_id, "email": claims.email}
        new_token = await self.generate_jwt(user_data, claims.environment, claims.pr_number)
        
        logger.info(f"JWT refreshed for user {claims.user_id}")
        return new_token
        
    async def _store_revocation_in_redis(self, revocation_key: str) -> None:
        """Store revocation key in Redis if enabled."""
        if self.redis_manager.enabled:
            await self.redis_manager.set(revocation_key, "revoked", ex=3600)
    
    def _handle_revocation_error(self, error: Exception, error_type: str) -> None:
        """Handle specific revocation errors with appropriate logging."""
        if isinstance(error, ValidationError):
            logger.error(f"Invalid token format during revocation: {str(error)}")
            # Don't raise for revocation - it should be a graceful operation
        elif isinstance(error, ConnectionError):
            logger.error(f"Redis connection failed during token revocation: {str(error)}")
        else:
            logger.error(f"Unexpected error during token revocation: {str(error)}")
            # Don't raise for revocation - log and continue gracefully
    
    async def revoke_jwt(self, token: str) -> None:
        """Add JWT token to revocation list in Redis."""
        try:
            claims = await self.get_jwt_claims(token)
            revocation_key = self._create_revocation_key(claims.jti)
            await self._store_revocation_in_redis(revocation_key)
            logger.info(f"JWT revoked for user {claims.user_id}")
        except Exception as e:
            self._handle_revocation_error(e, "revocation")
            
    def _decode_token_payload(self, token: str) -> Dict[str, Any]:
        """Decode JWT payload without validation."""
        return jwt.decode(
            token,
            key="", 
            algorithms=[self.algorithm],
            options={"verify_signature": False, "verify_exp": False}
        )
        
    async def get_jwt_claims(self, token: str) -> TokenClaims:
        """Extract claims from JWT without validation (for revocation)."""
        try:
            payload = self._decode_token_payload(token)
            return TokenClaims(**payload)
        except Exception as e:
            raise ValidationError(f"Invalid token format: {str(e)}")
            
    async def _check_revocation_in_redis(self, jti: str) -> bool:
        """Check if token ID is in Redis revocation list."""
        revocation_key = self._create_revocation_key(jti)
        result = await self.redis_manager.get(revocation_key)
        return result is not None
        
    async def is_token_revoked(self, token: str) -> bool:
        """Check if JWT token is in revocation list."""
        if not self.redis_manager.enabled:
            return False
        try:
            claims = await self.get_jwt_claims(token)
            return await self._check_revocation_in_redis(claims.jti)
        except Exception:
            return False


# Global token manager instance
token_manager = JWTTokenManager()


# Convenience functions for external usage
async def generate_jwt(
    user_data: Dict[str, Any], 
    environment: str, 
    pr_number: Optional[str] = None
) -> str:
    """Generate JWT token with user claims."""
    return await token_manager.generate_jwt(user_data, environment, pr_number)


async def validate_jwt(token: str) -> TokenClaims:
    """Validate JWT token and return claims."""
    return await token_manager.validate_jwt(token)


async def refresh_jwt(old_token: str) -> str:
    """Refresh expiring JWT token."""
    return await token_manager.refresh_jwt(old_token)


async def revoke_jwt(token: str) -> None:
    """Revoke JWT token."""
    await token_manager.revoke_jwt(token)


async def get_jwt_claims(token: str) -> TokenClaims:
    """Extract JWT claims without validation."""
    return await token_manager.get_jwt_claims(token)


async def is_token_revoked(token: str) -> bool:
    """Check if token is revoked."""
    return await token_manager.is_token_revoked(token)