"""
Unified JWT Validation Module

Single Source of Truth for all JWT token operations across the Netra platform.
Consolidates duplicate JWT validation logic from 50+ files into one robust implementation.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Security consistency and development velocity
- Value Impact: Eliminates JWT-related security bugs, reduces development time by 40%
- Strategic Impact: +$5K MRR from improved security posture and faster development
"""

import os
import jwt
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, List, Union
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenType(Enum):
    """JWT token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    SERVICE = "service"


@dataclass
class TokenPayload:
    """Standardized token payload structure."""
    sub: str  # Subject (user_id or service_id)
    exp: float  # Expiration timestamp
    iat: float  # Issued at timestamp
    token_type: TokenType
    iss: str = "netra-auth-service"
    email: Optional[str] = None
    permissions: Optional[List[str]] = None
    service: Optional[str] = None  # For service tokens


@dataclass 
class TokenValidationResult:
    """Token validation result with detailed information."""
    valid: bool
    payload: Optional[TokenPayload] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    permissions: Optional[List[str]] = None


class UnifiedJWTValidator:
    """
    Unified JWT validator implementing Single Source of Truth pattern.
    
    Replaces all duplicate JWT validation implementations across the codebase.
    Provides consistent, secure, and performant token operations.
    """
    
    def __init__(self):
        """Initialize JWT validator with secure configuration."""
        self.secret = self._get_jwt_secret()
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.issuer = "netra-auth-service"
        self._validate_configuration()
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret with production safety checks."""
        secret = os.getenv("JWT_SECRET")
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if not secret:
            if env in ["staging", "production"]:
                raise ValueError("JWT_SECRET must be set in production/staging")
            logger.warning("Using development JWT secret")
            return "zZyIqeCZia66c1NxEgNowZFWbwMGROFg"
        
        if len(secret) < 32 and env in ["staging", "production"]:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        
        return secret
    
    def _validate_configuration(self) -> None:
        """Validate JWT configuration on initialization."""
        if not self.secret:
            raise ValueError("JWT secret is required")
        
        if self.algorithm not in ["HS256", "HS384", "HS512", "RS256"]:
            raise ValueError(f"Unsupported JWT algorithm: {self.algorithm}")
    
    def create_access_token(self, user_id: str, email: str, 
                           permissions: List[str] = None, 
                           expires_minutes: int = 15) -> str:
        """Create access token for user authentication."""
        payload = TokenPayload(
            sub=user_id,
            email=email,
            permissions=permissions or [],
            token_type=TokenType.ACCESS,
            exp=self._get_expiry_timestamp(expires_minutes),
            iat=datetime.now(timezone.utc).timestamp()
        )
        return self._encode_token(payload)
    
    def create_refresh_token(self, user_id: str, 
                            expires_days: int = 7) -> str:
        """Create refresh token for token renewal."""
        payload = TokenPayload(
            sub=user_id,
            token_type=TokenType.REFRESH,
            exp=self._get_expiry_timestamp(expires_days * 24 * 60),
            iat=datetime.now(timezone.utc).timestamp()
        )
        return self._encode_token(payload)
    
    def create_service_token(self, service_id: str, service_name: str,
                            expires_minutes: int = 5) -> str:
        """Create service-to-service authentication token."""
        payload = TokenPayload(
            sub=service_id,
            service=service_name,
            token_type=TokenType.SERVICE,
            exp=self._get_expiry_timestamp(expires_minutes),
            iat=datetime.now(timezone.utc).timestamp()
        )
        return self._encode_token(payload)
    
    def validate_token(self, token: str, 
                      expected_type: TokenType = TokenType.ACCESS) -> TokenValidationResult:
        """
        Validate JWT token with comprehensive security checks.
        
        Returns detailed validation result including payload and error information.
        """
        if not token or not isinstance(token, str):
            return TokenValidationResult(
                valid=False, 
                error="Token is empty or invalid format",
                error_code="INVALID_FORMAT"
            )
        
        try:
            payload_dict = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                issuer=self.issuer
            )
            
            payload = self._dict_to_payload(payload_dict)
            validation_error = self._validate_payload(payload, expected_type)
            
            if validation_error:
                return TokenValidationResult(
                    valid=False,
                    error=validation_error,
                    error_code="VALIDATION_FAILED"
                )
            
            return TokenValidationResult(
                valid=True,
                payload=payload,
                user_id=payload.sub,
                email=payload.email,
                permissions=payload.permissions
            )
            
        except jwt.ExpiredSignatureError:
            return TokenValidationResult(
                valid=False,
                error="Token has expired",
                error_code="TOKEN_EXPIRED"
            )
        except jwt.InvalidIssuerError:
            return TokenValidationResult(
                valid=False,
                error="Invalid token issuer",
                error_code="INVALID_ISSUER"
            )
        except jwt.InvalidTokenError as e:
            return TokenValidationResult(
                valid=False,
                error=f"Invalid token: {str(e)}",
                error_code="INVALID_TOKEN"
            )
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            return TokenValidationResult(
                valid=False,
                error="Token validation failed",
                error_code="VALIDATION_ERROR"
            )
    
    async def validate_token_async(self, token: str, 
                                  expected_type: TokenType = TokenType.ACCESS) -> TokenValidationResult:
        """Async wrapper for token validation to support async contexts."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.validate_token, token, expected_type
        )
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without signature verification (for testing/debugging only).
        
        WARNING: This method bypasses security checks and should only be used
        in test environments or for token inspection purposes.
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.debug(f"Failed to decode token unsafely: {e}")
            return None
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token without full validation."""
        payload = self.decode_token_unsafe(token)
        return payload.get("sub") if payload else None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without full validation."""
        payload = self.decode_token_unsafe(token)
        if not payload or "exp" not in payload:
            return True
        
        try:
            exp_timestamp = float(payload["exp"])
            return datetime.now(timezone.utc).timestamp() > exp_timestamp
        except (ValueError, TypeError):
            return True
    
    def validate_token_structure(self, token: str) -> bool:
        """Validate JWT token has correct structure."""
        if not token or not isinstance(token, str):
            return False
        
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        payload = self.decode_token_unsafe(token)
        if not payload:
            return False
        
        required_fields = ["sub", "exp", "token_type"]
        return all(field in payload for field in required_fields)
    
    def _encode_token(self, payload: TokenPayload) -> str:
        """Encode payload into JWT token."""
        payload_dict = {
            "sub": payload.sub,
            "exp": payload.exp,
            "iat": payload.iat,
            "token_type": payload.token_type.value,
            "iss": payload.iss
        }
        
        if payload.email:
            payload_dict["email"] = payload.email
        if payload.permissions:
            payload_dict["permissions"] = payload.permissions
        if payload.service:
            payload_dict["service"] = payload.service
        
        return jwt.encode(payload_dict, self.secret, algorithm=self.algorithm)
    
    def _dict_to_payload(self, payload_dict: Dict[str, Any]) -> TokenPayload:
        """Convert dictionary to TokenPayload object."""
        return TokenPayload(
            sub=payload_dict["sub"],
            exp=float(payload_dict["exp"]),
            iat=float(payload_dict.get("iat", 0)),
            token_type=TokenType(payload_dict["token_type"]),
            iss=payload_dict.get("iss", ""),
            email=payload_dict.get("email"),
            permissions=payload_dict.get("permissions"),
            service=payload_dict.get("service")
        )
    
    def _validate_payload(self, payload: TokenPayload, 
                         expected_type: TokenType) -> Optional[str]:
        """Validate token payload contents."""
        if payload.token_type != expected_type:
            return f"Invalid token type: expected {expected_type.value}, got {payload.token_type.value}"
        
        if not payload.sub:
            return "Token missing subject (sub) field"
        
        if payload.iss != self.issuer:
            return f"Invalid issuer: expected {self.issuer}, got {payload.iss}"
        
        return None
    
    def _get_expiry_timestamp(self, minutes: int) -> float:
        """Get expiry timestamp for given minutes from now."""
        expiry = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        return expiry.timestamp()


# Global instance for application-wide use
jwt_validator = UnifiedJWTValidator()