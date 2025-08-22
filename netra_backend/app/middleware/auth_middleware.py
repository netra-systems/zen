"""
Auth Middleware for JWT token validation and authentication.

Handles authentication middleware chain functionality including:
- JWT token extraction from Authorization headers
- Token validation and expiration checking
- User context setup
- Permission enforcement

Business Value Justification (BVJ):
- Segment: ALL (Security foundation for all tiers)
- Business Goal: Secure authentication for all API endpoints
- Value Impact: Prevents unauthorized access, ensures compliance
- Strategic Impact: Foundation for enterprise-grade security
"""

import jwt
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.exceptions_auth import AuthenticationError, TokenExpiredError, TokenInvalidError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.auth_types import RequestContext

logger = central_logger.get_logger(__name__)


class AuthMiddleware:
    """Authentication middleware for JWT token validation."""
    
    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        excluded_paths: List[str] = None
    ):
        """Initialize auth middleware.
        
        Args:
            jwt_secret: Secret key for JWT validation
            jwt_algorithm: JWT algorithm to use
            excluded_paths: Paths that don't require authentication
        """
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.excluded_paths = excluded_paths or []
        logger.info(f"AuthMiddleware initialized with {len(self.excluded_paths)} excluded paths")
    
    async def process(self, context: RequestContext, handler: Callable) -> Any:
        """Process authentication for the request.
        
        Args:
            context: Request context containing headers, path, etc.
            handler: Next handler in the chain
            
        Returns:
            Handler result if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Skip auth for excluded paths
        if self._is_excluded_path(context.path):
            return await handler(context)
        
        # Extract and validate token
        token = self._extract_token(context)
        token_data = self._validate_token(token)
        
        # Update context with auth info
        context.authenticated = True
        context.user_id = token_data.get("user_id") or token_data.get("sub")
        context.permissions = token_data.get("permissions", [])
        
        return await handler(context)
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        return any(excluded in path for excluded in self.excluded_paths)
    
    def _extract_token(self, context: RequestContext) -> str:
        """Extract JWT token from Authorization header.
        
        Args:
            context: Request context
            
        Returns:
            JWT token string
            
        Raises:
            AuthenticationError: If token is missing or malformed
        """
        auth_header = context.headers.get("Authorization", "").strip()
        
        if not auth_header:
            raise AuthenticationError("No authorization header")
        
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Invalid authorization format")
        
        token = auth_header[7:].strip()  # Remove "Bearer " prefix
        if not token:
            raise AuthenticationError("Empty token")
        
        return token
    
    def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and extract payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenInvalidError: If token is invalid
            TokenExpiredError: If token is expired
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": True}
            )
            
            # Additional expiration check
            exp = payload.get("exp")
            if exp and exp < time.time():
                raise TokenExpiredError("Token expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token expired")
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise TokenInvalidError("Token validation failed")
    
    def check_permissions(self, required_permissions: List[str], user_permissions: List[str]) -> bool:
        """Check if user has required permissions.
        
        Args:
            required_permissions: List of required permissions
            user_permissions: List of user's permissions
            
        Returns:
            True if user has all required permissions
        """
        if not required_permissions:
            return True
        
        return all(perm in user_permissions for perm in required_permissions)