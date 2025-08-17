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
        self._jwt_secret: Optional[str] = None
        self.token_expiry = 3600  # 1 hour
        
    
    def _validate_jwt_secret_length(self, secret: str) -> None:
        """Validate JWT secret meets minimum length requirement."""
        if len(secret) < 32:
            raise HTTPException(
                status_code=500,
                detail="JWT_SECRET_KEY must be at least 32 characters long"
            )
    
    def _get_secure_jwt_secret(self) -> str:
        """Get JWT secret with security validation."""
        if self._jwt_secret is None:
            self._jwt_secret = self._load_jwt_secret()
        return self._jwt_secret
    
    def _load_jwt_secret(self) -> str:
        """Load JWT secret with environment-aware defaults."""
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            secret = self._get_default_secret()
        self._validate_jwt_secret_length(secret)
        return secret
    
    def _get_default_secret(self) -> str:
        """Get default secret for testing environments."""
        if self._is_test_environment():
            return "test_jwt_secret_key_for_testing_environment_12345678"
        raise HTTPException(
            status_code=500, 
            detail="JWT_SECRET_KEY environment variable must be set"
        )
    
    def _is_test_environment(self) -> bool:
        """Check if running in test environment."""
        test_indicators = ["pytest", "test", "testing"]
        env = os.getenv("ENVIRONMENT", "").lower()
        return any(indicator in env for indicator in test_indicators)
        
    def generate_jwt(self, user_info: UserInfo) -> str:
        """Generate JWT token with user claims."""
        now = datetime.now(timezone.utc)
        payload = self._build_jwt_payload(user_info, now)
        jwt_secret = self._get_secure_jwt_secret()
        return jwt.encode(payload, jwt_secret, algorithm="HS256")
    
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
            jwt_secret = self._get_secure_jwt_secret()
            return jwt.decode(token, jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            self._handle_jwt_expired()
            return None
        except jwt.InvalidTokenError as e:
            self._handle_jwt_invalid(e)
            return None