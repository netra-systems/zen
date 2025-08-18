"""JWT Token Manager - Comprehensive JWT token operations.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Secure authentication and session management
- Value Impact: Ensures secure user sessions and prevents unauthorized access
- Revenue Impact: Protects platform integrity and customer trust

Architecture Compliance:
- File: ≤300 lines
- Functions: ≤8 lines each
- Strong typing throughout
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

from jose import jwt, JWTError
from pydantic import BaseModel, Field

from app.core.exceptions_auth import AuthenticationError
from app.core.exceptions_base import ValidationError


@dataclass
class TokenClaims:
    """Structured JWT token claims data."""
    user_id: str
    email: str
    environment: str
    iat: int
    exp: int
    jti: str
    pr_number: Optional[str] = None


class JWTTokenManager:
    """JWT token manager for authentication operations."""
    
    def __init__(self):
        """Initialize JWT manager with default configuration."""
        self.algorithm = "HS256"
        self.expiration_hours = 1
        self.config = None
        self.redis_manager = None
    
    def _get_secret_key(self) -> str:
        """Get JWT secret key from config or environment."""
        if self.config and self.config.jwt_secret_key:
            return self.config.jwt_secret_key
        env_secret = os.environ.get('JWT_SECRET_KEY')
        if env_secret:
            return env_secret
        raise AuthenticationError("JWT secret key not configured")
    
    def _create_revocation_key(self, jti: str) -> str:
        """Create Redis revocation key for token JTI."""
        return f"revoked_token:{jti}"
    
    async def generate_jwt(self, user_data: Dict[str, Any], environment: str, 
                          pr_number: Optional[str] = None) -> str:
        """Generate JWT token with user data and environment."""
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(hours=self.expiration_hours)
        jti = str(uuid.uuid4())
        return self._encode_jwt_payload(user_data, environment, now, exp_time, jti, pr_number)
    
    def _encode_jwt_payload(self, user_data: Dict[str, Any], environment: str,
                           now: datetime, exp_time: datetime, jti: str,
                           pr_number: Optional[str]) -> str:
        """Encode JWT payload with claims."""
        payload = self._build_jwt_payload(user_data, environment, now, exp_time, jti, pr_number)
        secret = self._get_secret_key()
        return jwt.encode(payload, secret, algorithm=self.algorithm)
    
    def _build_jwt_payload(self, user_data: Dict[str, Any], environment: str,
                          now: datetime, exp_time: datetime, jti: str,
                          pr_number: Optional[str]) -> Dict[str, Any]:
        """Build JWT payload dictionary."""
        return {
            "user_id": user_data["user_id"], "email": user_data["email"],
            "environment": environment, "pr_number": pr_number,
            "iat": int(now.timestamp()), "exp": int(exp_time.timestamp()), "jti": jti
        }
    
    async def validate_jwt(self, token: str) -> TokenClaims:
        """Validate JWT token and return claims."""
        try:
            payload = self._decode_and_verify_token(token)
            await self._check_token_revocation(payload.get("jti"))
            return self._create_token_claims(payload)
        except JWTError:
            raise AuthenticationError("Invalid JWT token")
    
    def _decode_and_verify_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token signature."""
        secret = self._get_secret_key()
        return jwt.decode(token, secret, algorithms=[self.algorithm])
    
    async def _check_token_revocation(self, jti: Optional[str]):
        """Check if token is revoked in Redis."""
        if jti and await self._check_revocation_in_redis(jti):
            raise AuthenticationError("Token has been revoked")
    
    def _create_token_claims(self, payload: Dict[str, Any]) -> TokenClaims:
        """Create TokenClaims object from JWT payload."""
        return TokenClaims(
            user_id=payload["user_id"], email=payload["email"],
            environment=payload["environment"], iat=payload["iat"],
            exp=payload["exp"], jti=payload["jti"], pr_number=payload.get("pr_number")
        )
    
    async def get_jwt_claims(self, token: str) -> TokenClaims:
        """Extract JWT claims without full validation."""
        try:
            payload = self._decode_token_payload(token)
            return self._create_token_claims(payload)
        except Exception:
            raise ValidationError("Invalid token format")
    
    def _decode_token_payload(self, token: str) -> Dict[str, Any]:
        """Decode token payload without validation."""
        secret = self._get_secret_key()
        return jwt.decode(token, secret, algorithms=[self.algorithm], options={"verify_exp": False})
    
    async def refresh_jwt(self, old_token: str) -> str:
        """Refresh JWT token by generating new one and revoking old."""
        claims = await self.validate_jwt(old_token)
        await self.revoke_jwt(old_token)
        user_data = {"user_id": claims.user_id, "email": claims.email}
        return await self.generate_jwt(user_data, claims.environment, claims.pr_number)
    
    async def revoke_jwt(self, token: str):
        """Revoke JWT token by adding to Redis blacklist."""
        try:
            claims = await self.get_jwt_claims(token)
            await self._store_revocation_in_redis(claims.jti)
        except Exception:
            # Gracefully handle token parsing errors
            pass
    
    async def _store_revocation_in_redis(self, jti: str):
        """Store token revocation in Redis if enabled."""
        if self.redis_manager and self.redis_manager.enabled:
            revocation_key = self._create_revocation_key(jti)
            expiry_seconds = self.expiration_hours * 3600
            await self.redis_manager.set(revocation_key, "revoked", ex=expiry_seconds)
    
    async def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked."""
        if not self.redis_manager or not self.redis_manager.enabled:
            return False
        try:
            claims = await self.get_jwt_claims(token)
            return await self._check_revocation_in_redis(claims.jti)
        except Exception:
            return False
    
    async def _check_revocation_in_redis(self, jti: str) -> bool:
        """Check Redis for token revocation status."""
        if not self.redis_manager or not self.redis_manager.enabled:
            return False
        revocation_key = self._create_revocation_key(jti)
        result = await self.redis_manager.get(revocation_key)
        return result is not None


# Global token manager instance
token_manager = JWTTokenManager()


# Convenience functions
async def generate_jwt(user_data: Dict[str, Any], environment: str, 
                      pr_number: Optional[str] = None) -> str:
    """Generate JWT token using global manager."""
    return await token_manager.generate_jwt(user_data, environment, pr_number)


async def validate_jwt(token: str) -> TokenClaims:
    """Validate JWT token using global manager."""
    return await token_manager.validate_jwt(token)


async def refresh_jwt(old_token: str) -> str:
    """Refresh JWT token using global manager."""
    return await token_manager.refresh_jwt(old_token)


async def revoke_jwt(token: str):
    """Revoke JWT token using global manager."""
    await token_manager.revoke_jwt(token)


async def get_jwt_claims(token: str) -> TokenClaims:
    """Get JWT claims using global manager."""
    return await token_manager.get_jwt_claims(token)


async def is_token_revoked(token: str) -> bool:
    """Check if token is revoked using global manager."""
    return await token_manager.is_token_revoked(token)