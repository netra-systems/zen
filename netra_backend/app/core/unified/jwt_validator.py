"""
Unified JWT Validation Module - Delegates to Auth Service

ALL JWT operations MUST go through the external auth service.
This module provides a unified interface but delegates to auth service.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Security consistency via centralized auth service
- Value Impact: Eliminates JWT-related security bugs, ensures single auth source
- Strategic Impact: Improved security posture and compliance
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.clients.auth_client_core import auth_client
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
    user_id: Optional[str] = None
    email: Optional[str] = None
    permissions: Optional[List[str]] = None


class UnifiedJWTValidator:
    """
    Unified JWT Validator - ALL operations go through auth service.
    
    CRITICAL: This class does NOT implement JWT operations directly.
    All JWT operations are delegated to the external auth service.
    """
    
    def __init__(
        self,
        secret: Optional[str] = None,
        algorithm: str = "HS256",
        issuer: str = "netra-auth-service",
        access_token_expire_minutes: Optional[int] = None,
        refresh_token_expire_days: Optional[int] = None
    ):
        """Initialize validator - configuration only, no JWT operations."""
        self.algorithm = algorithm
        self.issuer = issuer
        
        # Use JWT Configuration Builder for consistent timing configuration
        try:
            from shared.jwt_config_builder import JWTConfigBuilder
            builder = JWTConfigBuilder(service="netra_backend")
            self.access_token_expire_minutes = access_token_expire_minutes or builder.timing.get_access_token_expire_minutes()
            self.refresh_token_expire_days = refresh_token_expire_days or builder.timing.get_refresh_token_expire_days()
            logger.info(f"Using JWT Configuration Builder: access_token_expire_minutes={self.access_token_expire_minutes}")
        except Exception as e:
            # Fallback to provided values or defaults
            self.access_token_expire_minutes = access_token_expire_minutes or 15  # Use 15 minutes to match auth service default
            self.refresh_token_expire_days = refresh_token_expire_days or 7
            logger.warning(f"Failed to load JWT config from builder, using fallback: {e}")
        
        # Log warning if direct secret is provided
        if secret:
            logger.warning("Direct JWT secret provided but will be ignored - auth service handles all JWT operations")
    
    async def validate_token_jwt(
        self,
        token: str,
        token_type: Optional[TokenType] = None,
        verify_exp: bool = True
    ) -> TokenValidationResult:
        """
        Validate JWT token via auth service.
        
        ALL validation goes through the external auth service.
        """
        try:
            # Validate through auth service
            result = await auth_client.validate_token_jwt(token)
            
            if not result:
                return TokenValidationResult(
                    valid=False,
                    error="Auth service validation failed"
                )
            
            # Map auth service response to our result structure
            return TokenValidationResult(
                valid=result.get("valid", False),
                user_id=result.get("user_id"),
                email=result.get("email"),
                permissions=result.get("permissions", []),
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidationResult(
                valid=False,
                error=str(e)
            )

    async def verify_token(
        self,
        token: str,
        token_type: Optional[TokenType] = None,
        verify_exp: bool = True
    ) -> TokenValidationResult:
        """
        Verify JWT token - compatibility method for Golden Path Validator.
        
        This method provides the interface expected by Golden Path Validator
        and delegates to validate_token_jwt for actual validation.
        """
        logger.info("verify_token called - delegating to validate_token_jwt for Golden Path compatibility")
        return await self.validate_token_jwt(token, token_type, verify_exp)
    
    def validate_token_sync(
        self,
        token: str,
        token_type: Optional[TokenType] = None,
        verify_exp: bool = True
    ) -> TokenValidationResult:
        """
        Synchronous token validation - NOT SUPPORTED.
        
        Auth service requires async operations.
        """
        logger.error("Synchronous token validation not supported - use async validate_token")
        return TokenValidationResult(
            valid=False,
            error="Synchronous validation not supported - use async method"
        )
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without validation - NOT SUPPORTED.
        
        ALL token operations must go through auth service.
        """
        logger.error("Unsafe token decoding not supported - use auth service")
        return None
    
    async def create_access_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        expire_minutes: Optional[int] = None
    ) -> str:
        """
        Create access token via auth service.
        
        ALL token creation goes through the external auth service.
        """
        try:
            token_data = {
                "user_id": user_id,
                "email": email,
                "permissions": permissions or [],
                "expire_minutes": expire_minutes or self.access_token_expire_minutes
            }
            
            result = await auth_client.create_token(token_data)
            
            if not result:
                raise ValueError("Auth service token creation failed")
            
            return result.get("access_token", "")
            
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise
    
    async def create_refresh_token(
        self,
        user_id: str,
        expire_days: Optional[int] = None
    ) -> str:
        """
        Create refresh token via auth service.
        
        ALL token creation goes through the external auth service.
        """
        try:
            token_data = {
                "user_id": user_id,
                "token_type": "refresh",
                "expire_days": expire_days or self.refresh_token_expire_days
            }
            
            result = await auth_client.create_token(token_data)
            
            if not result:
                raise ValueError("Auth service refresh token creation failed")
            
            return result.get("refresh_token", "")
            
        except Exception as e:
            logger.error(f"Refresh token creation error: {e}")
            raise
    
    async def create_service_token(
        self,
        service_id: str,
        permissions: Optional[List[str]] = None,
        expire_hours: int = 1
    ) -> str:
        """
        Create service-to-service token via auth service.
        
        ALL token creation goes through the external auth service.
        """
        try:
            # Use auth service's dedicated service token endpoint
            token = await auth_client.create_service_token()
            
            if not token:
                raise ValueError("Auth service service token creation failed")
            
            return token
            
        except Exception as e:
            logger.error(f"Service token creation error: {e}")
            raise
    
    def encode_token(self, payload: Dict[str, Any]) -> str:
        """
        Encode JWT token - NOT SUPPORTED.
        
        ALL token operations must go through auth service.
        """
        raise NotImplementedError("Direct JWT encoding not supported - use auth service")
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresh access token via auth service.
        
        ALL token operations go through the external auth service.
        """
        try:
            result = await auth_client.refresh_token(refresh_token)
            
            if not result:
                return None
            
            return result.get("access_token")
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def is_token_expired(self, exp: float) -> bool:
        """Check if token expiration timestamp has passed."""
        return datetime.now(timezone.utc).timestamp() > exp
    
    def get_token_remaining_time(self, exp: float) -> timedelta:
        """Get remaining time before token expires."""
        expiry = datetime.fromtimestamp(exp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(expiry - now, timedelta(0))


# Global validator instance - uses auth service for all operations
jwt_validator = UnifiedJWTValidator()


# Compatibility exports
async def validate_jwt(token: str) -> TokenValidationResult:
    """Validate JWT token via auth service."""
    return await jwt_validator.validate_token_jwt(token)


async def create_jwt(
    user_id: str,
    email: Optional[str] = None,
    permissions: Optional[List[str]] = None
) -> str:
    """Create JWT token via auth service."""
    return await jwt_validator.create_access_token(user_id, email, permissions)