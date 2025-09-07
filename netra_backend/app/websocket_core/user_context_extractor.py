"""
User Context Extractor - JWT to UserExecutionContext Conversion

This module provides utilities for extracting UserExecutionContext from JWT tokens
and WebSocket connections. This is critical for the factory pattern migration as
every WebSocket manager instance requires a valid UserExecutionContext.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable secure user context extraction for factory pattern
- Value Impact: Ensures proper user isolation by extracting context from authentication
- Revenue Impact: Prevents security breaches by enforcing proper context validation

CRITICAL SECURITY FUNCTION:
This extractor ensures that every WebSocket connection has proper user context
for the factory pattern, preventing the security vulnerabilities that existed
in the singleton pattern:

1. User ID validation and extraction from JWT
2. Request metadata extraction for tracing
3. Connection-specific context creation
4. Security validation and error handling
5. Context sanitization and validation

The extracted context is used to create isolated WebSocket manager instances,
ensuring complete user isolation and preventing cross-user data leakage.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple
from dataclasses import asdict

import jwt
from fastapi import WebSocket, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UserContextExtractor:
    """
    Utility class for extracting UserExecutionContext from WebSocket connections.
    
    This class handles:
    1. JWT token extraction from WebSocket headers/subprotocols
    2. Token validation and decoding
    3. User information extraction
    4. UserExecutionContext creation with proper validation
    5. Security logging and error handling
    """
    
    def __init__(self):
        """Initialize the user context extractor."""
        # JWT configuration (should match your auth service)
        self.jwt_algorithm = "HS256"
        self.jwt_secret_key = self._get_jwt_secret()
        
        logger.debug("UserContextExtractor initialized")
    
    def _get_jwt_secret(self) -> str:
        """
        Get JWT secret key from environment.
        
        Uses unified JWT secret manager to ensure consistency with auth service.
        This prevents WebSocket authentication failures caused by JWT secret 
        mismatches between services.
        
        Returns:
            JWT secret key string
            
        Raises:
            RuntimeError: If JWT secret is not configured
        """
        # Always use the unified JWT secret manager - no fallbacks
        from shared.jwt_secret_manager import get_unified_jwt_secret
        from shared.isolated_environment import get_env
        
        secret = get_unified_jwt_secret()
        
        # Log for debugging (without exposing the actual secret)
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        logger.debug(f"WebSocket using unified JWT secret for {environment} environment")
        
        return secret
    
    def extract_jwt_from_websocket(self, websocket: WebSocket) -> Optional[str]:
        """
        Extract JWT token from WebSocket connection.
        
        Supports two methods:
        1. Authorization header: "Bearer <token>"
        2. Sec-WebSocket-Protocol: "jwt.<base64url_encoded_token>"
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            JWT token string if found, None otherwise
        """
        try:
            # Method 1: Authorization header
            auth_header = websocket.headers.get("authorization")
            if auth_header:
                scheme, token = get_authorization_scheme_param(auth_header)
                if scheme.lower() == "bearer" and token:
                    logger.debug("JWT token extracted from Authorization header")
                    return token
            
            # Method 2: WebSocket subprotocol
            subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
            for subprotocol in subprotocols:
                subprotocol = subprotocol.strip()
                if subprotocol.startswith("jwt."):
                    # Extract base64url encoded token
                    encoded_token = subprotocol[4:]  # Remove "jwt." prefix
                    try:
                        # Decode base64url token
                        import base64
                        # Add padding if needed
                        missing_padding = len(encoded_token) % 4
                        if missing_padding:
                            encoded_token += '=' * (4 - missing_padding)
                        
                        token = base64.urlsafe_b64decode(encoded_token).decode('utf-8')
                        logger.debug("JWT token extracted from WebSocket subprotocol")
                        return token
                    except Exception as e:
                        logger.warning(f"Failed to decode JWT from subprotocol: {e}")
                        continue
            
            logger.debug("No JWT token found in WebSocket headers or subprotocols")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JWT from WebSocket: {e}")
            return None
    
    async def validate_and_decode_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate and decode JWT token using UNIFIED JWT validation logic.
        
        CRITICAL FIX: This now uses direct JWT validation with the SAME unified JWT secret
        that REST middleware uses, ensuring consistent JWT secret resolution and
        preventing the 403 WebSocket authentication failures in staging.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded JWT payload if valid, None otherwise
        """
        import hashlib
        import jwt
        from shared.isolated_environment import get_env
        from shared.jwt_secret_manager import get_unified_jwt_secret, get_unified_jwt_algorithm
        
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Enhanced diagnostic logging for staging
        logger.info(f"🔍 WEBSOCKET JWT VALIDATION - Starting UNIFIED token validation in {environment}")
        logger.info(f"🔍 WEBSOCKET JWT VALIDATION - Token length: {len(token) if token else 0}")
        logger.info(f"🔍 WEBSOCKET JWT VALIDATION - Token prefix: {token[:20]}..." if token and len(token) > 20 else token)
        
        # CRITICAL FIX: Use SAME JWT secret resolution as REST middleware
        try:
            # Get the unified JWT secret - same as REST middleware
            jwt_secret = get_unified_jwt_secret()
            jwt_algorithm = get_unified_jwt_algorithm()
            
            # Debug logging to confirm secret consistency
            secret_hash = hashlib.md5(jwt_secret.encode()).hexdigest()[:16]
            logger.info(f"🔍 WEBSOCKET JWT VALIDATION - Using UNIFIED JWT secret (hash: {secret_hash})")
            logger.info(f"🔍 WEBSOCKET JWT VALIDATION - Using algorithm: {jwt_algorithm}")
            logger.info("🔍 WEBSOCKET JWT VALIDATION - Same secret resolution as REST middleware!")
            
            # Decode and validate JWT using unified secret
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=[jwt_algorithm]
            )
            
            # Basic validation
            user_id = payload.get("sub")
            if not user_id or user_id == "None":
                logger.warning("🔍 WEBSOCKET JWT - token missing 'sub' (user ID) claim")
                logger.info(f"🔍 WEBSOCKET JWT - Payload keys: {list(payload.keys())}")
                return None
            
            # Success logging with unified approach confirmation
            logger.info(f"✅ WEBSOCKET JWT VALIDATION SUCCESS - Token validated for user: {user_id[:8]}...")
            logger.info(f"✅ WEBSOCKET JWT VALIDATION SUCCESS - Email: {payload.get('email', 'N/A')}")
            logger.info(f"✅ WEBSOCKET JWT VALIDATION SUCCESS - Permissions: {len(payload.get('permissions', []))}")
            logger.info("✅ WEBSOCKET JWT VALIDATION SUCCESS - Using UNIFIED JWT secret (same as REST)")
            
            return payload
            
        except jwt.ExpiredSignatureError as e:
            logger.error(f"❌ WEBSOCKET JWT FAILED - Token expired: {e}")
            return None
        except jwt.InvalidSignatureError as e:
            logger.error(f"❌ WEBSOCKET JWT FAILED - Signature verification failed: {e}")
            logger.error("❌ This indicates JWT secret mismatch between WebSocket and REST")
            logger.error(f"❌ Environment: {environment}, Secret hash: {hashlib.md5(jwt_secret.encode()).hexdigest()[:16] if 'jwt_secret' in locals() else 'NOT_LOADED'}")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ WEBSOCKET JWT FAILED - Invalid token format: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ WEBSOCKET JWT FAILED - Unexpected error: {e}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            
            # In staging/production, try fallback to resilient validation
            if environment in ["staging", "production"]:
                logger.warning("🔄 STAGING/PRODUCTION: Falling back to resilient validation as last resort")
                return await self._resilient_validation_fallback(token)
            
            return None
    
    async def _resilient_validation_fallback(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Resilient validation fallback - only used when unified JWT validation fails.
        This uses the same resilient validation logic as auth_client_core.
        """
        from shared.isolated_environment import get_env
        
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        logger.warning(f"🔄 RESILIENT FALLBACK - Attempting resilient validation in {environment}")
        
        try:
            from netra_backend.app.clients.auth_client_core import validate_token_with_resilience, AuthOperationType
            
            # Use the same resilient validation that REST endpoints use
            validation_result = await validate_token_with_resilience(token, AuthOperationType.TOKEN_VALIDATION)
            
            logger.info(f"🔄 RESILIENT FALLBACK - Result: success={validation_result.get('success', False)}, valid={validation_result.get('valid', False)}")
            
            if validation_result.get("success") and validation_result.get("valid"):
                # Success - create JWT-compatible payload
                user_id = validation_result.get('user_id')
                email = validation_result.get('email', '')
                permissions = validation_result.get('permissions', [])
                
                jwt_payload = {
                    "sub": user_id,
                    "email": email,
                    "permissions": permissions,
                    "iat": int(time.time()),
                    "source": "resilient_fallback"
                }
                
                logger.warning(f"⚠️ RESILIENT FALLBACK SUCCESS - Token validated via fallback for user: {user_id[:8] if user_id else 'unknown'}...")
                return jwt_payload
            else:
                error_msg = validation_result.get("error", "Unknown validation failure")
                logger.error(f"❌ RESILIENT FALLBACK FAILED - {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ RESILIENT FALLBACK ERROR - {e}")
            return None
    
    async def _legacy_jwt_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Legacy JWT validation using direct secret resolution (less reliable).
        This is only used as fallback in development environments.
        """
        import hashlib
        from shared.isolated_environment import get_env
        
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Only allow legacy fallback in development
        if environment in ["staging", "production"]:
            logger.error("❌ Legacy JWT validation not allowed in staging/production")
            return None
        
        logger.warning("⚠️  Using legacy JWT validation - less reliable than resilient validation")
        
        secret_hash = hashlib.md5(self.jwt_secret_key.encode()).hexdigest()[:16] if self.jwt_secret_key else "NO_SECRET"
        logger.info(f"🔍 LEGACY JWT VALIDATION - Using secret hash: {secret_hash}")
        logger.info(f"🔍 LEGACY JWT VALIDATION - Algorithm: {self.jwt_algorithm}")
        
        try:
            # Decode and validate JWT using local secret
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # Basic validation
            if not payload.get("sub"):  # Subject (user ID)
                logger.warning("🔍 LEGACY JWT - token missing 'sub' (user ID) claim")
                logger.info(f"🔍 LEGACY JWT - Payload keys: {list(payload.keys())}")
                return None
            
            # Success logging
            user_id = payload.get('sub', 'unknown')
            logger.info(f"✅ LEGACY JWT SUCCESS - Token decoded for user: {user_id[:8]}...")
            
            return payload
            
        except jwt.ExpiredSignatureError as e:
            logger.error(f"❌ LEGACY JWT FAILED - Token expired: {e}")
            return None
        except jwt.InvalidSignatureError as e:
            logger.error(f"❌ LEGACY JWT FAILED - Signature verification failed: {e}")
            logger.error("❌ This indicates JWT secret mismatch in legacy validation")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ LEGACY JWT FAILED - Invalid token format: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ LEGACY JWT FAILED - Unexpected error: {e}")
            return None
    
    def create_user_context_from_jwt(
        self, 
        jwt_payload: Dict[str, Any], 
        websocket: WebSocket,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> UserExecutionContext:
        """
        Create UserExecutionContext from JWT payload.
        
        Args:
            jwt_payload: Decoded JWT payload
            websocket: WebSocket connection object
            additional_metadata: Additional context metadata
            
        Returns:
            UserExecutionContext instance
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Extract user ID from JWT
            user_id = jwt_payload.get("sub")
            if not user_id or user_id == "None":
                raise ValueError("JWT payload missing valid 'sub' (user ID) claim")
            
            # Generate unique identifiers for this connection
            connection_timestamp = datetime.now(timezone.utc).timestamp()
            unique_id = str(uuid.uuid4())
            
            # Extract or generate thread ID
            thread_id = (
                jwt_payload.get("thread_id") or
                additional_metadata.get("thread_id") if additional_metadata else None or
                f"thread_{unique_id[:8]}"
            )
            
            # Extract or generate run ID  
            run_id = (
                jwt_payload.get("run_id") or
                additional_metadata.get("run_id") if additional_metadata else None or
                f"run_{unique_id[:8]}"
            )
            
            # Generate request ID (unique per connection)
            request_id = f"ws_req_{int(connection_timestamp)}_{unique_id[:8]}"
            
            # Generate WebSocket connection ID (unique per WebSocket connection)
            websocket_connection_id = f"ws_{user_id[:8]}_{int(connection_timestamp)}_{unique_id[:8]}"
            
            # Create UserExecutionContext
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                websocket_connection_id=websocket_connection_id
            )
            
            logger.info(
                f"Created UserExecutionContext for WebSocket connection: "
                f"user={user_id[:8]}..., conn_id={websocket_connection_id}"
            )
            
            return user_context
            
        except Exception as e:
            logger.error(f"Failed to create UserExecutionContext from JWT: {e}")
            raise ValueError(f"Invalid JWT payload for context creation: {e}") from e
    
    async def extract_user_context_from_websocket(
        self, 
        websocket: WebSocket,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[UserExecutionContext, Dict[str, Any]]:
        """
        Extract complete user context from WebSocket connection.
        
        This is the main function that combines JWT extraction, validation,
        and context creation into a single operation.
        
        Args:
            websocket: WebSocket connection object
            additional_metadata: Additional context metadata
            
        Returns:
            Tuple of (UserExecutionContext, auth_info_dict)
            
        Raises:
            HTTPException: If authentication fails or context cannot be created
        """
        try:
            # Extract JWT token
            jwt_token = self.extract_jwt_from_websocket(websocket)
            if not jwt_token:
                logger.warning("No JWT token found in WebSocket connection")
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required: No JWT token found in WebSocket headers or subprotocols"
                )
            
            # Log that we found a token (helps debugging)
            logger.debug(f"JWT token found in WebSocket connection, proceeding with validation")
            
            # Validate and decode JWT using resilient validation (same as REST)
            jwt_payload = await self.validate_and_decode_jwt(jwt_token)
            if not jwt_payload:
                # This is the key fix - different error message for validation failure
                logger.warning("JWT token validation failed - likely due to secret mismatch or expiration")
                raise HTTPException(
                    status_code=401,
                    detail="Authentication failed: Invalid or expired JWT token (validation failed)"
                )
            
            # Create user context
            user_context = self.create_user_context_from_jwt(
                jwt_payload, 
                websocket, 
                additional_metadata
            )
            
            # Extract additional auth info
            auth_info = {
                "user_id": user_context.user_id,
                "token_issued_at": jwt_payload.get("iat"),
                "token_expires_at": jwt_payload.get("exp"),
                "token_issuer": jwt_payload.get("iss"),
                "permissions": jwt_payload.get("permissions", []),
                "roles": jwt_payload.get("roles", []),
                "session_id": jwt_payload.get("session_id"),
                "client_info": {
                    "user_agent": websocket.headers.get("user-agent", ""),
                    "origin": websocket.headers.get("origin", ""),
                    "host": websocket.headers.get("host", "")
                }
            }
            
            # Security logging
            logger.info(
                f"Successfully authenticated WebSocket connection: "
                f"user={user_context.user_id[:8]}..., "
                f"context={user_context.websocket_connection_id}, "
                f"permissions={len(auth_info['permissions'])}"
            )
            
            return user_context, auth_info
            
        except HTTPException:
            # Re-raise HTTP exceptions (authentication failures)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during WebSocket context extraction: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal authentication error: {str(e)}"
            ) from e
    
    def create_test_user_context(
        self, 
        user_id: str = "test_user", 
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> UserExecutionContext:
        """
        Create a test UserExecutionContext for development/testing.
        
        Args:
            user_id: User ID for test context
            additional_metadata: Additional context metadata
            
        Returns:
            UserExecutionContext instance for testing
        """
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).timestamp()
        
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=additional_metadata.get("thread_id", f"test_thread_{unique_id[:8]}") if additional_metadata else f"test_thread_{unique_id[:8]}",
            run_id=additional_metadata.get("run_id", f"test_run_{unique_id[:8]}") if additional_metadata else f"test_run_{unique_id[:8]}",
            request_id=f"test_req_{int(timestamp)}_{unique_id[:8]}",
            websocket_connection_id=f"test_ws_{int(timestamp)}_{unique_id[:8]}"
        )
        
        logger.debug(f"Created test UserExecutionContext: {context}")
        return context


# Global extractor instance
_extractor_instance: Optional[UserContextExtractor] = None


def get_user_context_extractor() -> UserContextExtractor:
    """
    Get the global user context extractor instance.
    
    Returns:
        UserContextExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = UserContextExtractor()
    return _extractor_instance


async def extract_websocket_user_context(
    websocket: WebSocket,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[UserExecutionContext, Dict[str, Any]]:
    """
    Convenience function to extract user context from WebSocket.
    
    CRITICAL FIX: This function is now async to support resilient JWT validation
    that uses the same logic as REST endpoints, ensuring consistent authentication.
    
    Args:
        websocket: WebSocket connection object
        additional_metadata: Additional context metadata
        
    Returns:
        Tuple of (UserExecutionContext, auth_info_dict)
        
    Raises:
        HTTPException: If authentication fails
    """
    extractor = get_user_context_extractor()
    return await extractor.extract_user_context_from_websocket(websocket, additional_metadata)


__all__ = [
    "UserContextExtractor",
    "get_user_context_extractor",
    "extract_websocket_user_context"
]