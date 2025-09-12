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

# JWT import REMOVED - SSOT compliance: ALL JWT operations delegated to UnifiedAuthInterface
from fastapi import WebSocket, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from shared.id_generation import UnifiedIdGenerator

# SSOT COMPLIANCE: Direct import of auth service client (no fallback)
from netra_backend.app.clients.auth_client_core import auth_client

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
        # SSOT COMPLIANCE: No direct JWT configuration in backend
        # All JWT operations delegated to auth service
        self.auth_service = self._get_auth_service()
        
        logger.debug("UserContextExtractor initialized")
    
    def _get_auth_service(self):
        """
        Get auth service client for JWT validation.
        
        SSOT COMPLIANCE: Pure delegation to auth service client.
        No fallback paths or conditional logic.
        
        Returns:
            Auth service client for JWT validation
        """
        # SSOT COMPLIANCE: Use auth_client directly (eliminates conditional paths)
        from netra_backend.app.clients.auth_client_core import auth_client
        return auth_client
    
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
    
    async def validate_and_decode_jwt(self, token: str, fast_path_enabled: bool = False) -> Optional[Dict[str, Any]]:
        """
        SSOT JWT validation - Pure delegation to auth service.
        
        SSOT REMEDIATION: This method now provides pure delegation to the auth service
        without any local JWT validation logic. All JWT operations are consolidated
        in the auth service SSOT (JWTHandler.validate_token()).
        
        Args:
            token: JWT token string
            fast_path_enabled: If True, use optimized validation for E2E tests
            
        Returns:
            Decoded JWT payload if valid, None otherwise
        """
        from shared.isolated_environment import get_env
        
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        logger.info(f"SSOT JWT: Delegating token validation to auth service (env: {environment})")
        
        try:
            # SSOT COMPLIANCE: Pure delegation to auth service
            validation_result = await self.auth_service.validate_token(token)
            
            if not validation_result or not validation_result.get('valid'):
                logger.warning(f"SSOT JWT: Auth service validation failed (env: {environment})")
                return None
                
            # Extract payload from validation result
            payload = validation_result.get('payload', {})
            if not payload:
                # Build payload from validation result for backward compatibility
                payload = {
                    'sub': validation_result.get('user_id'),
                    'user_id': validation_result.get('user_id'),
                    'email': validation_result.get('email'),
                    'permissions': validation_result.get('permissions', []),
                    'exp': validation_result.get('exp'),
                    'iat': validation_result.get('iat')
                }
            
            # Basic validation
            user_id = payload.get("sub")
            if not user_id or user_id == "None":
                logger.warning("SSOT JWT: Token missing valid user ID claim")
                return None
            
            logger.info(f"SSOT JWT: Validation successful for user {user_id[:8]}... (env: {environment})")
            payload["source"] = "auth_service_ssot"
            return payload
            
        except Exception as e:
            logger.error(f"SSOT JWT: Validation error - {e} (type: {type(e).__name__})")
            return None
    
    # SSOT COMPLIANCE: All fallback validation methods eliminated
    # Pure delegation to auth service ensures SSOT compliance and eliminates JWT secret mismatches
    
    def create_user_context_from_jwt(
        self, 
        jwt_payload: Dict[str, Any], 
        websocket: WebSocket,
        additional_metadata: Optional[Dict[str, Any]] = None,
        preliminary_connection_id: Optional[str] = None
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
            
            # Generate unique identifiers for this connection using SSOT
            connection_timestamp = datetime.now(timezone.utc).timestamp()
            
            # Use SSOT for thread_id and run_id generation
            thread_id = (
                jwt_payload.get("thread_id") or
                additional_metadata.get("thread_id") if additional_metadata else None or
                UnifiedIdGenerator.generate_base_id("thread_ws", True, 8)
            )
            
            run_id = (
                jwt_payload.get("run_id") or
                additional_metadata.get("run_id") if additional_metadata else None or
                UnifiedIdGenerator.generate_base_id("run_ws", True, 8)
            )
            
            # Generate request ID using SSOT (unique per connection)
            request_id = UnifiedIdGenerator.generate_base_id("ws_req", True, 8)
            
            # PASS-THROUGH FIX: Generate WebSocket client ID using preliminary_connection_id if provided
            if preliminary_connection_id:
                # Use provided preliminary connection ID to preserve state machine continuity
                websocket_client_id = preliminary_connection_id
                logger.info(f"PASS-THROUGH FIX: Using preliminary_connection_id {preliminary_connection_id} for context creation")
            else:
                # Generate WebSocket client ID using SSOT (unique per WebSocket connection)
                websocket_client_id = UnifiedIdGenerator.generate_websocket_client_id(user_id, connection_timestamp)
                logger.debug(f"Generated new websocket_client_id: {websocket_client_id}")
            
            # Create UserExecutionContext
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                websocket_client_id=websocket_client_id
            )
            
            logger.info(
                f"Created UserExecutionContext for WebSocket connection: "
                f"user={user_id[:8]}..., conn_id={websocket_client_id}"
            )
            
            return user_context
            
        except Exception as e:
            logger.error(f"Failed to create UserExecutionContext from JWT: {e}")
            raise ValueError(f"Invalid JWT payload for context creation: {e}") from e
    
    async def extract_user_context_from_websocket(
        self, 
        websocket: WebSocket,
        additional_metadata: Optional[Dict[str, Any]] = None,
        preliminary_connection_id: Optional[str] = None
    ) -> Tuple[UserExecutionContext, Dict[str, Any]]:
        """
        Extract complete user context from WebSocket connection with E2E fast path support.
        
        This is the main function that combines JWT extraction, validation,
        and context creation into a single operation.
        
        Args:
            websocket: WebSocket connection object
            additional_metadata: Additional context metadata
            preliminary_connection_id: Optional preliminary connection ID to preserve state machine continuity
            
        Returns:
            Tuple of (UserExecutionContext, auth_info_dict)
            
        Raises:
            HTTPException: If authentication fails or context cannot be created
        """
        try:
            # CRITICAL FIX: Check for E2E test headers to enable fast path
            e2e_headers = {
                "X-Test-Type": websocket.headers.get("x-test-type", "").lower(),
                "X-Test-Environment": websocket.headers.get("x-test-environment", "").lower(),
                "X-E2E-Test": websocket.headers.get("x-e2e-test", "").lower(),
                "X-Test-Mode": websocket.headers.get("x-test-mode", "").lower(),
                "X-Auth-Fast-Path": websocket.headers.get("x-auth-fast-path", "").lower()
            }
            
            # Determine if E2E fast path should be enabled
            is_e2e_test = (
                e2e_headers["X-Test-Type"] in ["e2e", "integration"] or
                e2e_headers["X-Test-Environment"] in ["staging", "test"] or
                e2e_headers["X-E2E-Test"] in ["true", "1", "yes"] or
                e2e_headers["X-Test-Mode"] in ["true", "1", "test"] or
                e2e_headers["X-Auth-Fast-Path"] in ["enabled", "true", "1"]
            )
            
            logger.info(f" SEARCH:  E2E Detection in context extractor: {is_e2e_test}")
            logger.info(f" SEARCH:  E2E Headers: {e2e_headers}")
            
            # Extract JWT token
            jwt_token = self.extract_jwt_from_websocket(websocket)
            if not jwt_token:
                logger.critical(f" ALERT:  GOLDEN PATH TOKEN EXTRACTION FAILURE: No JWT token found in WebSocket connection")
                logger.warning("No JWT token found in WebSocket connection")
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required: No JWT token found in WebSocket headers or subprotocols"
                )
            
            # Log that we found a token (helps debugging)
            logger.debug(f"JWT token found in WebSocket connection, proceeding with validation")
            
            # Validate and decode JWT using resilient validation with optional fast path
            jwt_payload = await self.validate_and_decode_jwt(jwt_token, fast_path_enabled=is_e2e_test)
            if not jwt_payload:
                # This is the key fix - different error message for validation failure
                logger.critical(f" ALERT:  GOLDEN PATH JWT VALIDATION FAILURE: Token validation failed - likely secret mismatch, expiration, or malformed token")
                logger.warning("JWT token validation failed - likely due to secret mismatch or expiration")
                raise HTTPException(
                    status_code=401,
                    detail="Authentication failed: Invalid or expired JWT token (validation failed)"
                )
            
            # Create user context
            user_context = self.create_user_context_from_jwt(
                jwt_payload, 
                websocket, 
                additional_metadata,
                preliminary_connection_id
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
            logger.info(f" PASS:  GOLDEN PATH CONTEXT SUCCESS: Successfully created user context for WebSocket connection: user={user_context.user_id[:8]}..., context={user_context.websocket_client_id}")
            logger.info(
                f"Successfully authenticated WebSocket connection: "
                f"user={user_context.user_id[:8]}..., "
                f"context={user_context.websocket_client_id}, "
                f"permissions={len(auth_info['permissions'])}"
            )
            
            return user_context, auth_info
            
        except HTTPException:
            # Re-raise HTTP exceptions (authentication failures)
            raise
        except Exception as e:
            logger.critical(f" ALERT:  GOLDEN PATH CONTEXT EXCEPTION: Unexpected error during WebSocket context extraction: {e} (type: {type(e).__name__})")
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
        timestamp = datetime.now(timezone.utc).timestamp()
        
        # Use SSOT for test context ID generation
        thread_id = (additional_metadata.get("thread_id") if additional_metadata 
                    else UnifiedIdGenerator.generate_base_id("test_thread", True, 8))
        run_id = (additional_metadata.get("run_id") if additional_metadata 
                 else UnifiedIdGenerator.generate_base_id("test_run", True, 8))
        request_id = UnifiedIdGenerator.generate_base_id("test_req", True, 8)
        websocket_client_id = UnifiedIdGenerator.generate_websocket_client_id(user_id, timestamp)
        
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_client_id
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
    additional_metadata: Optional[Dict[str, Any]] = None,
    preliminary_connection_id: Optional[str] = None
) -> Tuple[UserExecutionContext, Dict[str, Any]]:
    """
    Convenience function to extract user context from WebSocket.
    
    CRITICAL FIX: This function is now async to support resilient JWT validation
    that uses the same logic as REST endpoints, ensuring consistent authentication.
    
    Args:
        websocket: WebSocket connection object
        additional_metadata: Additional context metadata
        preliminary_connection_id: Optional preliminary connection ID to preserve state machine continuity
        
    Returns:
        Tuple of (UserExecutionContext, auth_info_dict)
        
    Raises:
        HTTPException: If authentication fails
    """
    extractor = get_user_context_extractor()
    return await extractor.extract_user_context_from_websocket(websocket, additional_metadata, preliminary_connection_id)


class WebSocketUserContextExtractor(UserContextExtractor):
    """
    WebSocket-specific user context extractor.
    
    This class extends UserContextExtractor with WebSocket-specific functionality
    for the comprehensive WebSocket phase integration tests.
    
    Business Value Justification (BVJ):
    - Segment: Platform/Internal - Test Infrastructure
    - Business Goal: Enable comprehensive WebSocket testing
    - Value Impact: Ensures WebSocket authentication works correctly
    - Strategic Impact: Prevents WebSocket authentication failures in production
    """
    
    def __init__(self):
        """Initialize WebSocket-specific context extractor."""
        super().__init__()
        self._extraction_count = 0
        self._successful_extractions = 0
        self._failed_extractions = 0
        
    async def extract_context_with_metrics(self, websocket: WebSocket) -> Tuple[UserExecutionContext, Dict[str, Any]]:
        """Extract user context with detailed metrics tracking."""
        self._extraction_count += 1
        
        try:
            context, auth_info = await self.extract_user_context_from_websocket(websocket)
            self._successful_extractions += 1
            
            # Add extraction metrics to auth info
            auth_info["extraction_metrics"] = {
                "extraction_count": self._extraction_count,
                "successful_extractions": self._successful_extractions,
                "failed_extractions": self._failed_extractions,
                "success_rate": self._successful_extractions / self._extraction_count
            }
            
            return context, auth_info
            
        except Exception as e:
            self._failed_extractions += 1
            logger.error(f"Context extraction failed: {e}")
            raise
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics for monitoring."""
        total_extractions = max(1, self._extraction_count)  # Avoid division by zero
        
        return {
            "total_extractions": self._extraction_count,
            "successful_extractions": self._successful_extractions,
            "failed_extractions": self._failed_extractions,
            "success_rate": self._successful_extractions / total_extractions
        }
    
    def reset_stats(self):
        """Reset extraction statistics."""
        self._extraction_count = 0
        self._successful_extractions = 0
        self._failed_extractions = 0


__all__ = [
    "UserContextExtractor",
    "WebSocketUserContextExtractor",
    "get_user_context_extractor", 
    "extract_websocket_user_context"
]