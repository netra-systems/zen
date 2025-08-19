"""
JWT Token Handler - Core authentication token management
Maintains 300-line limit with focused single responsibility
"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
import logging

from ..config import AuthConfig

logger = logging.getLogger(__name__)

class JWTHandler:
    """Single Source of Truth for JWT operations"""
    
    def __init__(self):
        self.secret = self._get_jwt_secret()
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_expiry = int(os.getenv("JWT_ACCESS_EXPIRY_MINUTES", "15"))
        self.refresh_expiry = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "7"))
        self.service_expiry = int(os.getenv("JWT_SERVICE_EXPIRY_MINUTES", "5"))
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret with production safety"""
        secret = AuthConfig.get_jwt_secret()
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if not secret:
            if env in ["staging", "production"]:
                raise ValueError("JWT_SECRET must be set in production/staging")
            logger.warning("Using default JWT secret for development")
            return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
        
        if len(secret) < 32 and env in ["staging", "production"]:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        
        return secret
        
    def create_access_token(self, user_id: str, email: str, 
                           permissions: list = None) -> str:
        """Create access token for user authentication"""
        payload = self._build_payload(
            sub=user_id,
            email=email,
            permissions=permissions or [],
            token_type="access",
            exp_minutes=self.access_expiry
        )
        return self._encode_token(payload)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token for token renewal"""
        payload = self._build_payload(
            sub=user_id,
            token_type="refresh",
            exp_minutes=self.refresh_expiry * 24 * 60
        )
        return self._encode_token(payload)
    
    def create_service_token(self, service_id: str, 
                           service_name: str) -> str:
        """Create token for service-to-service auth"""
        payload = self._build_payload(
            sub=service_id,
            service=service_name,
            token_type="service",
            exp_minutes=self.service_expiry
        )
        return self._encode_token(payload)
    
    def validate_token(self, token: str, 
                      token_type: str = "access") -> Optional[Dict]:
        """Validate and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm]
            )
            
            if payload.get("token_type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[tuple]:
        """Generate new access token from refresh token"""
        payload = self.validate_token(refresh_token, "refresh")
        if not payload:
            return None
            
        # Get user details from database (placeholder)
        user_id = payload["sub"]
        # In real implementation, fetch from DB
        email = "user@example.com"
        permissions = []
        
        new_access = self.create_access_token(user_id, email, permissions)
        new_refresh = self.create_refresh_token(user_id)
        
        return new_access, new_refresh
    
    def _build_payload(self, sub: str, token_type: str, 
                      exp_minutes: int, **kwargs) -> Dict:
        """Build JWT payload with standard claims"""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=exp_minutes)
        
        payload = {
            "sub": sub,
            "iat": now,
            "exp": exp,
            "token_type": token_type,
            "iss": "netra-auth-service"
        }
        payload.update(kwargs)
        return payload
    
    def _encode_token(self, payload: Dict) -> str:
        """Encode payload into JWT token"""
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token without full validation"""
        try:
            # Decode without verification for user ID extraction
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            return payload.get("sub")
        except Exception:
            return None