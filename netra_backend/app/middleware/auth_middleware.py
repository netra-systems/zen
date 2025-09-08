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

# JWT import removed - SSOT compliance: all JWT operations delegated to auth service
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
        self.jwt_secret = self._validate_and_clean_jwt_secret(jwt_secret)
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
    
    async def _validate_token(self, token: str) -> Dict[str, Any]:
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
            # SSOT COMPLIANCE: Use auth service for token validation
            from netra_backend.app.clients.auth_client_core import auth_client
            
            validation_result = await auth_client.validate_token(token)
            if not validation_result or not validation_result.get('valid'):
                error = validation_result.get('error', 'Token validation failed') if validation_result else 'Auth service unavailable'
                if 'expired' in error.lower():
                    raise TokenExpiredError(error)
                else:
                    raise TokenInvalidError(error)
            
            # Return payload in expected format
            payload = validation_result.get('payload', {})
            if not payload:
                # Build payload from validation result for backward compatibility
                payload = {
                    'user_id': validation_result.get('user_id'),
                    'sub': validation_result.get('user_id'),
                    'email': validation_result.get('email'),
                    'permissions': validation_result.get('permissions', []),
                    'exp': validation_result.get('exp'),
                    'iat': validation_result.get('iat')
                }
            
            # Additional expiration check
            exp = payload.get("exp")
            if exp and exp < time.time():
                raise TokenExpiredError("Token expired")
            
            return payload
            
        except (TokenExpiredError, TokenInvalidError):
            raise
        except Exception as e:
            logger.error(f"Auth middleware token validation error: {str(e)}")
            raise TokenInvalidError("Token validation failed")
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
    
    def _validate_and_clean_jwt_secret(self, jwt_secret: str) -> str:
        """Validate and clean JWT secret.
        
        Args:
            jwt_secret: Raw JWT secret
            
        Returns:
            Clean, validated JWT secret
            
        Raises:
            ValueError: If JWT secret is invalid
        """
        if not jwt_secret:
            raise ValueError("JWT secret cannot be empty")
        
        # CRITICAL: Trim whitespace from secrets (common staging issue)
        cleaned_secret = jwt_secret.strip()
        
        if not cleaned_secret:
            raise ValueError("JWT secret cannot be empty after trimming whitespace")
        
        # Validate minimum length for security  
        if len(cleaned_secret) < 32:
            raise ValueError(
                f"JWT secret must be at least 32 characters for security, "
                f"got {len(cleaned_secret)} characters"
            )
        
        logger.info(f"JWT secret validated: {len(cleaned_secret)} characters")
        return cleaned_secret