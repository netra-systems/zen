"""
JWT Token Handler - Core authentication token management
Maintains 450-line limit with focused single responsibility
"""
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.security.oauth_security import JWTSecurityValidator

logger = logging.getLogger(__name__)

class JWTHandler:
    """Single Source of Truth for JWT operations"""
    
    def __init__(self):
        self.secret = self._get_jwt_secret()
        self.algorithm = AuthConfig.get_jwt_algorithm()
        self.access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
        self.refresh_expiry = AuthConfig.get_jwt_refresh_expiry_days()
        self.service_expiry = AuthConfig.get_jwt_service_expiry_minutes()
        self.security_validator = JWTSecurityValidator()
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret with production safety"""
        secret = AuthConfig.get_jwt_secret()
        env = AuthConfig.get_environment()
        
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
        """Validate and decode JWT token with enhanced security"""
        try:
            # First validate token security (algorithm, etc.)
            if not self.security_validator.validate_token_security(token):
                logger.warning("Token failed security validation")
                return None
            
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                # Enhanced security options
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub"]
                }
            )
            
            if payload.get("token_type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}")
                return None
            
            # Additional security checks
            if not self._validate_token_claims(payload):
                logger.warning("Token claims validation failed")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def validate_token_jwt(self, token: str, 
                          token_type: str = "access") -> Optional[Dict]:
        """Alias for validate_token for backwards compatibility with tests"""
        return self.validate_token(token, token_type)
    
    def validate_id_token(self, id_token: str, expected_issuer: str = None) -> Optional[Dict]:
        """Validate OAuth ID token from external providers (Google, etc.)"""
        try:
            # Decode header to check algorithm
            header = jwt.get_unverified_header(id_token)
            algorithm = header.get("alg")
            
            # For external OAuth ID tokens, we typically can't verify signature
            # without the provider's public key. For testing, we'll do basic validation.
            # In production, this would verify against Google's public keys.
            
            # Basic validation without signature verification for now
            payload = jwt.decode(
                id_token,
                options={
                    "verify_signature": False,  # Would need provider's public key
                    "verify_exp": True,
                    "verify_iat": True
                }
            )
            
            # Validate issuer if provided
            if expected_issuer and payload.get("iss") != expected_issuer:
                logger.warning(f"Invalid ID token issuer: {payload.get('iss')}")
                return None
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and exp < time.time():
                logger.warning("ID token is expired")
                return None
            
            # Check if token is too old
            iat = payload.get("iat")
            if iat and (time.time() - iat) > 24 * 60 * 60:  # 24 hours
                logger.warning("ID token issued too long ago")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("ID token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"ID token validation error: {e}")
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
            # Still validate basic security even without signature verification
            if not self.security_validator.validate_token_security(token):
                return None
            
            # Decode without verification for user ID extraction
            payload = jwt.decode(
                token, 
                options={"verify_signature": False, "verify_exp": False}
            )
            return payload.get("sub")
        except Exception:
            return None
    
    def _validate_token_claims(self, payload: Dict) -> bool:
        """Validate additional token claims for security"""
        try:
            # Check required claims
            required_claims = ["sub", "iat", "exp", "iss"]
            for claim in required_claims:
                if claim not in payload:
                    logger.warning(f"Missing required claim: {claim}")
                    return False
            
            # Validate issuer
            if payload.get("iss") != "netra-auth-service":
                logger.warning(f"Invalid issuer: {payload.get('iss')}")
                return False
            
            # Check token age (not too old)
            issued_at = payload.get("iat")
            if isinstance(issued_at, datetime):
                age = datetime.now(timezone.utc) - issued_at
            else:
                age = datetime.now(timezone.utc) - datetime.fromtimestamp(issued_at, timezone.utc)
            
            # Reject tokens older than 24 hours for security
            if age.total_seconds() > 24 * 60 * 60:
                logger.warning("Token too old")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Token claims validation error: {e}")
            return False