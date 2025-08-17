"""JWT token generation and management service.

Secure JWT token creation and validation with proper error handling.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import os
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Strongly typed data structures for security
class UserInfo:
    """Google OAuth user information structure."""
    def __init__(self, id: str, email: str, name: str, picture: Optional[str] = None):
        self.id = id
        self.email = email
        self.name = name
        self.picture = picture
    
    def get(self, key: str) -> Optional[str]:
        """Get attribute value."""
        return getattr(self, key, None)


class AuthTokenService:
    """JWT token generation and management service."""
    
    def __init__(self):
        """Initialize token service."""
        self.jwt_secret = self._get_secure_jwt_secret()
        self.token_expiry = 3600  # 1 hour
        
    def _validate_jwt_secret_exists(self, secret: Optional[str]) -> None:
        """Validate JWT secret exists."""
        if not secret:
            raise HTTPException(
                status_code=500, 
                detail="JWT_SECRET_KEY environment variable must be set"
            )
    
    def _validate_jwt_secret_length(self, secret: str) -> None:
        """Validate JWT secret meets minimum length requirement."""
        if len(secret) < 32:
            raise HTTPException(
                status_code=500,
                detail="JWT_SECRET_KEY must be at least 32 characters long"
            )
    
    def _get_secure_jwt_secret(self) -> str:
        """Get JWT secret with security validation."""
        secret = os.getenv("JWT_SECRET_KEY")
        self._validate_jwt_secret_exists(secret)
        self._validate_jwt_secret_length(secret)
        return secret
        
    def generate_jwt(self, user_info: UserInfo) -> str:
        """Generate JWT token with user claims."""
        now = datetime.now(timezone.utc)
        payload = self._build_jwt_payload(user_info, now)
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _build_jwt_payload(self, user_info: UserInfo, now: datetime) -> Dict[str, Any]:
        """Build JWT payload with standard claims."""
        return {
            "sub": user_info.get("id"), "email": user_info.get("email"),
            "name": user_info.get("name"), "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.token_expiry)).timestamp()),
            "iss": "netra-auth-service", "aud": "netra-api"
        }
    
    def _handle_jwt_expired(self) -> None:
        """Handle expired JWT token."""
        logger.warning("JWT token expired")
    
    def _handle_jwt_invalid(self, error: jwt.InvalidTokenError) -> None:
        """Handle invalid JWT token."""
        logger.error(f"JWT validation failed: {error}")

    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return claims."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            self._handle_jwt_expired()
            return None
        except jwt.InvalidTokenError as e:
            self._handle_jwt_invalid(e)
            return None