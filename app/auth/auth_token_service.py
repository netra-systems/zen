"""Auth Token Service for JWT token management.

Handles JWT token generation, validation, and claims management.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Secure token-based authentication
3. Value Impact: Enables secure API access and user sessions
4. Revenue Impact: Critical for platform security and user experience
"""

import os
import jwt
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class UserInfo(BaseModel):
    """User information model."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = False

class AuthTokenService:
    """JWT token management service."""
    
    def __init__(self):
        """Initialize token service."""
        self.secret_key = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
        self.algorithm = "HS256"
        self.access_token_expires = timedelta(hours=24)
        
    def generate_jwt(self, user_info: Dict[str, Any]) -> str:
        """Generate JWT token from user information."""
        payload = self._build_token_payload(user_info)
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated JWT for user {user_info.get('id')}")
        return token
        
    def _build_token_payload(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build JWT token payload."""
        now = datetime.utcnow()
        exp = now + self.access_token_expires
        
        return {
            "sub": user_info.get("id"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "iss": "netra-auth-service"
        }
        
    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return claims."""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            return None
            
    def refresh_jwt(self, token: str) -> Optional[str]:
        """Refresh JWT token if valid."""
        claims = self.validate_jwt(token)
        if not claims:
            return None
            
        # Create new token with same user info
        user_info = {
            "id": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name")
        }
        return self.generate_jwt(user_info)
        
    def get_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Get token claims without validation."""
        try:
            # Decode without verification to get claims
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            return payload
        except jwt.JWTError:
            return None
            
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        claims = self.get_token_claims(token)
        if not claims:
            return True
            
        exp = claims.get("exp")
        if not exp:
            return True
            
        return int(time.time()) > exp