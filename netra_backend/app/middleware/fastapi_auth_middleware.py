"""
FastAPI-compatible Auth Middleware for JWT token validation.

Integrates the auth middleware with FastAPI's middleware system for 
authentication middleware chain functionality including:
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
from typing import Any, Callable, List, Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from netra_backend.app.core.config import get_settings
from netra_backend.app.core.exceptions_auth import AuthenticationError, TokenExpiredError, TokenInvalidError
from netra_backend.app.clients.auth_resilience_service import (
    get_auth_resilience_service,
    AuthOperationType,
    validate_token_with_resilience,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FastAPIAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI-compatible authentication middleware for JWT token validation."""
    
    def __init__(
        self,
        app,
        excluded_paths: List[str] = None,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256"
    ):
        """Initialize FastAPI auth middleware.
        
        Args:
            app: FastAPI application instance
            excluded_paths: Paths that don't require authentication
            jwt_secret: Secret key for JWT validation (defaults from config)
            jwt_algorithm: JWT algorithm to use
        """
        super().__init__(app)
        
        # Get configuration
        settings = get_settings()
        self.jwt_secret = jwt_secret or settings.jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        
        # Default excluded paths for health checks and metrics
        default_excluded = ["/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc"]
        self.excluded_paths = excluded_paths or default_excluded
        
        logger.info(f"FastAPIAuthMiddleware initialized with {len(self.excluded_paths)} excluded paths")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process authentication for the request.
        
        Args:
            request: FastAPI Request object
            call_next: Next handler in the chain
            
        Returns:
            Response from handler if authentication successful
            
        Raises:
            HTTPException: If authentication fails (401 or 403)
        """
        # Skip auth for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Extract token
            token = self._extract_token(request)
            
            # Determine operation type based on path
            operation_type = self._determine_operation_type(request.url.path)
            
            # Validate token with resilience mechanisms
            validation_result = await validate_token_with_resilience(token, operation_type)
            
            if not validation_result["success"] or not validation_result["valid"]:
                # Handle resilience failure
                if validation_result.get("fallback_used"):
                    logger.warning(f"Using fallback auth for {request.url.path}: {validation_result.get('source', 'unknown')}")
                else:
                    raise AuthenticationError(validation_result.get("error", "Token validation failed"))
            
            # Add auth info to request state for downstream handlers
            request.state.authenticated = True
            request.state.user_id = validation_result.get("user_id")
            request.state.permissions = validation_result.get("permissions", [])
            request.state.token_data = validation_result
            request.state.auth_resilience_mode = validation_result.get("resilience_mode")
            request.state.auth_fallback_used = validation_result.get("fallback_used", False)
            
            # Add resilience headers to response
            response = await call_next(request)
            response.headers["X-Auth-Resilience-Mode"] = validation_result.get("resilience_mode", "normal")
            if validation_result.get("fallback_used"):
                response.headers["X-Auth-Fallback-Source"] = validation_result.get("source", "unknown")
            
            return response
            
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for {request.url.path}: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail={"error": "authentication_failed", "message": str(e)},
                headers={"WWW-Authenticate": "Bearer"}
            )
        except (TokenExpiredError, TokenInvalidError) as e:
            logger.warning(f"Token validation failed for {request.url.path}: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail={"error": "token_invalid", "message": str(e)},
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected auth error for {request.url.path}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"error": "auth_system_error", "message": "Authentication system error"}
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        return any(excluded in path for excluded in self.excluded_paths)
    
    def _extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            JWT token string
            
        Raises:
            AuthenticationError: If token is missing or malformed
        """
        auth_header = request.headers.get("authorization", "").strip()
        
        if not auth_header:
            raise AuthenticationError("No authorization header")
        
        if not auth_header.lower().startswith("bearer "):
            raise AuthenticationError("Invalid authorization format")
        
        token = auth_header[7:].strip()  # Remove "Bearer " prefix
        if not token:
            raise AuthenticationError("Empty token")
        
        return token
    
    def _validate_token(self, token: str) -> dict[str, Any]:
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
    
    def _determine_operation_type(self, path: str) -> AuthOperationType:
        """Determine the type of auth operation based on request path."""
        path_lower = path.lower()
        
        if any(health_path in path_lower for health_path in ["/health", "/status"]):
            return AuthOperationType.HEALTH_CHECK
        elif any(monitor_path in path_lower for monitor_path in ["/metrics", "/monitoring"]):
            return AuthOperationType.MONITORING
        elif "/auth/login" in path_lower:
            return AuthOperationType.LOGIN
        elif "/auth/logout" in path_lower:
            return AuthOperationType.LOGOUT
        elif "/auth/refresh" in path_lower:
            return AuthOperationType.TOKEN_REFRESH
        else:
            return AuthOperationType.TOKEN_VALIDATION
    
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