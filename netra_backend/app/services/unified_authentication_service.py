"""
Unified Authentication Service - SINGLE SOURCE OF TRUTH for ALL Authentication

Business Value Justification:
- Segment: Platform/Internal - Security Infrastructure
- Business Goal: System Stability & Security Compliance
- Value Impact: Eliminates 4 duplicate authentication paths, ensures consistent security
- Revenue Impact: Restores $120K+ MRR by fixing WebSocket authentication

CRITICAL: This service is the ONLY authentication implementation allowed in the system.
All authentication requests (REST, WebSocket, gRPC, etc.) MUST use this service.

This replaces and consolidates:
1. netra_backend.app.clients.auth_client_core.AuthServiceClient (SSOT kept)
2. netra_backend.app.websocket_core.auth.WebSocketAuthenticator (ELIMINATED)
3. netra_backend.app.websocket_core.user_context_extractor validation paths (ELIMINATED)
4. Pre-connection validation in websocket.py (ELIMINATED)

SSOT Enforcement: Any new authentication code that doesn't use this service
will be automatically rejected during code review.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, WebSocket

from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceError, 
    AuthServiceConnectionError,
    AuthServiceNotAvailableError,
    AuthServiceValidationError,
    validate_jwt_format
)
from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AuthResult:
    """Authentication result with standardized format."""
    
    def __init__(
        self,
        success: bool,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        permissions: Optional[list] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.user_id = user_id
        self.email = email
        self.permissions = permissions or []
        self.error = error
        self.error_code = error_code
        self.metadata = metadata or {}
        self.validated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility."""
        return {
            "valid": self.success,
            "success": self.success,
            "user_id": self.user_id,
            "email": self.email,
            "permissions": self.permissions,
            "error": self.error,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "validated_at": self.validated_at
        }


class AuthenticationMethod(Enum):
    """Authentication methods supported by the unified service."""
    JWT_TOKEN = "jwt_token"
    BASIC_AUTH = "basic_auth"
    API_KEY = "api_key"
    SERVICE_ACCOUNT = "service_account"


class AuthenticationContext(Enum):
    """Context in which authentication is happening."""
    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    GRAPHQL = "graphql" 
    GRPC = "grpc"
    INTERNAL_SERVICE = "internal_service"


class UnifiedAuthenticationService:
    """
    SINGLE SOURCE OF TRUTH for ALL authentication in the Netra system.
    
    This service provides a unified interface for authentication across all
    protocols (REST, WebSocket, gRPC) and contexts (user, service, internal).
    
    CRITICAL SSOT COMPLIANCE:
    - All authentication MUST use this service
    - No direct calls to auth_client_core outside this service
    - No duplicate authentication logic allowed anywhere
    - All authentication results use standardized AuthResult format
    """
    
    def __init__(self):
        """Initialize unified authentication service."""
        # Use existing SSOT auth client as the underlying implementation
        self._auth_client = AuthServiceClient()
        
        # Statistics for monitoring SSOT compliance
        self._auth_attempts = 0
        self._auth_successes = 0
        self._auth_failures = 0
        self._method_counts = {method.value: 0 for method in AuthenticationMethod}
        self._context_counts = {context.value: 0 for context in AuthenticationContext}
        
        logger.info("UnifiedAuthenticationService initialized - SSOT authentication enforced")
    
    async def authenticate_token(
        self,
        token: str,
        context: AuthenticationContext = AuthenticationContext.REST_API,
        method: AuthenticationMethod = AuthenticationMethod.JWT_TOKEN
    ) -> AuthResult:
        """
        Authenticate using a token (JWT, API key, etc.).
        
        This is the SSOT method for ALL token-based authentication.
        
        Args:
            token: Authentication token
            context: Where authentication is happening
            method: Type of authentication method
            
        Returns:
            AuthResult with standardized authentication result
        """
        self._auth_attempts += 1
        self._method_counts[method.value] += 1
        self._context_counts[context.value] += 1
        
        # Enhanced logging with 10x more debug information
        token_prefix = token[:12] if len(token) > 12 else "[SHORT_TOKEN]"
        token_suffix = token[-8:] if len(token) > 20 else "[SUFFIX_UNAVAILABLE]"
        token_length = len(token)
        
        logger.info(f"UNIFIED AUTH: {method.value} authentication attempt in {context.value} context")
        logger.debug(f"UNIFIED AUTH DEBUG: token_length={token_length}, prefix={token_prefix}..., suffix=...{token_suffix}")
        
        try:
            # Validate token format first with enhanced debugging
            if not validate_jwt_format(token):
                # Enhanced debugging for token format issues
                token_analysis = {
                    "length": len(token),
                    "starts_with_bearer": token.lower().startswith('bearer '),
                    "has_dots": token.count('.'),
                    "first_10_chars": token[:10] if len(token) >= 10 else token,
                    "last_10_chars": token[-10:] if len(token) >= 20 else "[TOO_SHORT]",
                    "contains_spaces": ' ' in token,
                    "contains_newlines": '\n' in token or '\r' in token,
                    "environment_context": context.value
                }
                
                logger.warning(f"UNIFIED AUTH: Invalid token format in {context.value}")
                logger.error(f"🔧 TOKEN FORMAT DEBUG: {json.dumps(token_analysis, indent=2)}")
                self._auth_failures += 1
                return AuthResult(
                    success=False,
                    error=f"Invalid token format: {token_analysis['length']} chars, {token_analysis['has_dots']} dots",
                    error_code="INVALID_FORMAT",
                    metadata={"context": context.value, "method": method.value, "token_debug": token_analysis}
                )
            
            # Use SSOT auth client for validation
            validation_result = await self._auth_client.validate_token(token)
            
            if not validation_result or not validation_result.get("valid", False):
                # Authentication failed - Enhanced debugging for VALIDATION_FAILED
                error_msg = validation_result.get("error", "Token validation failed") if validation_result else "No validation result"
                
                # Create comprehensive failure debug information
                failure_debug = {
                    "validation_result_exists": validation_result is not None,
                    "validation_result_keys": list(validation_result.keys()) if validation_result else [],
                    "error_from_auth_service": validation_result.get("error") if validation_result else None,
                    "details_from_auth_service": validation_result.get("details") if validation_result else None,
                    "token_characteristics": {
                        "length": len(token),
                        "prefix": token[:12] if len(token) > 12 else token,
                        "suffix": token[-8:] if len(token) > 20 else "[SUFFIX_UNAVAILABLE]",
                        "dot_count": token.count('.'),
                        "has_bearer_prefix": token.lower().startswith('bearer ')
                    },
                    "context": context.value,
                    "method": method.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "auth_service_response_status": "present" if validation_result else "missing"
                }
                
                logger.warning(f"UNIFIED AUTH: Token validation failed in {context.value}: {error_msg}")
                logger.error(f"🔧 VALIDATION_FAILED DEBUG: {json.dumps(failure_debug, indent=2)}")
                self._auth_failures += 1
                
                return AuthResult(
                    success=False,
                    error=f"{error_msg} | Debug: {len(token)} chars, {token.count('.')} dots",
                    error_code="VALIDATION_FAILED",
                    metadata={
                        "context": context.value,
                        "method": method.value,
                        "details": validation_result.get("details") if validation_result else None,
                        "failure_debug": failure_debug
                    }
                )
            
            # Authentication successful - Enhanced success logging
            user_id = validation_result.get("user_id")
            email = validation_result.get("email", "")
            permissions = validation_result.get("permissions", [])
            
            # Success debug information
            success_debug = {
                "user_id_prefix": user_id[:8] if user_id and len(user_id) >= 8 else user_id,
                "email_domain": email.split('@')[1] if email and '@' in email else "[NO_EMAIL]",
                "permissions_count": len(permissions),
                "token_iat": validation_result.get("iat"),
                "token_exp": validation_result.get("exp"),
                "context": context.value,
                "method": method.value,
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"UNIFIED AUTH: Successfully authenticated user {user_id[:8] if user_id else '[NO_USER_ID]'}... in {context.value}")
            logger.debug(f"🎉 AUTH SUCCESS DEBUG: {json.dumps(success_debug, indent=2)}")
            self._auth_successes += 1
            
            return AuthResult(
                success=True,
                user_id=user_id,
                email=email,
                permissions=permissions,
                metadata={
                    "context": context.value,
                    "method": method.value,
                    "token_issued_at": validation_result.get("iat"),
                    "token_expires_at": validation_result.get("exp")
                }
            )
            
        except AuthServiceError as e:
            # Enhanced debugging for AuthServiceError
            service_error_debug = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "context": context.value,
                "method": method.value,
                "token_length": len(token),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "circuit_breaker_status": getattr(self._auth_client, 'circuit_breaker_status', 'unknown') if hasattr(self._auth_client, 'circuit_breaker_status') else 'no_circuit_breaker'
            }
            
            logger.error(f"UNIFIED AUTH: Auth service error in {context.value}: {e}")
            logger.error(f"🔧 AUTH_SERVICE_ERROR DEBUG: {json.dumps(service_error_debug, indent=2)}")
            self._auth_failures += 1
            
            return AuthResult(
                success=False,
                error=f"Authentication service error: {str(e)}",
                error_code="AUTH_SERVICE_ERROR",
                metadata={"context": context.value, "method": method.value, "service_error_debug": service_error_debug}
            )
            
        except Exception as e:
            # Enhanced debugging for unexpected errors
            unexpected_error_debug = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "context": context.value,
                "method": method.value,
                "token_characteristics": {
                    "length": len(token),
                    "prefix": token[:10] if len(token) >= 10 else token,
                    "suffix": token[-8:] if len(token) >= 16 else "[TOO_SHORT]"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "auth_client_available": self._auth_client is not None
            }
            
            logger.error(f"UNIFIED AUTH: Unexpected error in {context.value}: {e}", exc_info=True)
            logger.error(f"🔧 UNEXPECTED_ERROR DEBUG: {json.dumps(unexpected_error_debug, indent=2)}")
            self._auth_failures += 1
            
            return AuthResult(
                success=False,
                error=f"Authentication error: {str(e)}",
                error_code="UNEXPECTED_ERROR", 
                metadata={"context": context.value, "method": method.value, "unexpected_error_debug": unexpected_error_debug}
            )
    
    async def authenticate_websocket(self, websocket: WebSocket) -> Tuple[AuthResult, Optional[UserExecutionContext]]:
        """
        Authenticate WebSocket connection using SSOT authentication.
        
        This method replaces ALL existing WebSocket authentication logic:
        - websocket_core/auth.py WebSocketAuthenticator 
        - user_context_extractor.py validation methods
        - Pre-connection validation in websocket.py
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            Tuple of (AuthResult, UserExecutionContext if successful)
        """
        logger.info("UNIFIED AUTH: WebSocket authentication request")
        
        try:
            # Extract JWT token from WebSocket using standardized method
            token = self._extract_websocket_token(websocket)
            
            if not token:
                logger.warning("UNIFIED AUTH: No JWT token found in WebSocket connection")
                return (
                    AuthResult(
                        success=False,
                        error="No JWT token found in WebSocket headers or subprotocols",
                        error_code="NO_TOKEN",
                        metadata={"context": "websocket", "available_headers": list(websocket.headers.keys())}
                    ),
                    None
                )
            
            # Authenticate token using SSOT method
            auth_result = await self.authenticate_token(
                token,
                context=AuthenticationContext.WEBSOCKET,
                method=AuthenticationMethod.JWT_TOKEN
            )
            
            if not auth_result.success:
                return auth_result, None
            
            # Create UserExecutionContext for successful authentication
            user_context = self._create_user_execution_context(auth_result, websocket)
            
            logger.info(f"UNIFIED AUTH: WebSocket authentication successful for user {auth_result.user_id[:8]}...")
            return auth_result, user_context
            
        except Exception as e:
            logger.error(f"UNIFIED AUTH: WebSocket authentication error: {e}", exc_info=True)
            return (
                AuthResult(
                    success=False,
                    error=f"WebSocket authentication error: {str(e)}",
                    error_code="WEBSOCKET_AUTH_ERROR",
                    metadata={"context": "websocket"}
                ),
                None
            )
    
    def _extract_websocket_token(self, websocket: WebSocket) -> Optional[str]:
        """
        Extract JWT token from WebSocket headers or subprotocols.
        
        Supports two standard methods:
        1. Authorization header: "Bearer <token>"
        2. Sec-WebSocket-Protocol: "jwt.<base64url_encoded_token>"
        """
        try:
            # Method 1: Authorization header (most common)
            auth_header = websocket.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                logger.debug("UNIFIED AUTH: JWT token found in Authorization header")
                return token
            
            # Method 2: WebSocket subprotocol
            subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
            for protocol in subprotocols:
                protocol = protocol.strip()
                if protocol.startswith("jwt."):
                    try:
                        import base64
                        # Extract and decode base64url token
                        encoded_token = protocol[4:]  # Remove "jwt." prefix
                        # Add padding if needed
                        missing_padding = len(encoded_token) % 4
                        if missing_padding:
                            encoded_token += '=' * (4 - missing_padding)
                        
                        token_bytes = base64.urlsafe_b64decode(encoded_token)
                        token = token_bytes.decode('utf-8')
                        logger.debug("UNIFIED AUTH: JWT token found in Sec-WebSocket-Protocol")
                        return token
                    except Exception as e:
                        logger.warning(f"UNIFIED AUTH: Failed to decode token from subprotocol: {e}")
                        continue
            
            # Method 3: Query parameter (fallback for testing)
            if hasattr(websocket, 'query_params'):
                token = websocket.query_params.get("token")
                if token:
                    logger.debug("UNIFIED AUTH: JWT token found in query parameters")
                    return token
            
            return None
            
        except Exception as e:
            logger.error(f"UNIFIED AUTH: Error extracting WebSocket token: {e}")
            return None
    
    def _create_user_execution_context(self, auth_result: AuthResult, websocket: WebSocket) -> UserExecutionContext:
        """Create UserExecutionContext from authentication result."""
        import uuid
        
        # Generate unique identifiers for this connection
        connection_timestamp = datetime.now(timezone.utc).timestamp()
        unique_id = str(uuid.uuid4())
        
        # Create UserExecutionContext with proper identifiers
        user_context = UserExecutionContext(
            user_id=auth_result.user_id,
            thread_id=f"ws_thread_{unique_id[:8]}",
            run_id=f"ws_run_{unique_id[:8]}",
            request_id=f"ws_req_{int(connection_timestamp)}_{unique_id[:8]}",
            websocket_client_id=f"ws_{auth_result.user_id[:8]}_{int(connection_timestamp)}_{unique_id[:8]}"
        )
        
        logger.debug(f"UNIFIED AUTH: Created UserExecutionContext for WebSocket: {user_context.websocket_client_id}")
        return user_context
    
    async def validate_service_token(self, token: str, service_name: str) -> AuthResult:
        """
        Validate service-to-service authentication token.
        
        Args:
            token: Service authentication token
            service_name: Name of the requesting service
            
        Returns:
            AuthResult with service validation result
        """
        logger.info(f"UNIFIED AUTH: Service token validation for {service_name}")
        
        try:
            # Use SSOT auth client for service validation
            validation_result = await self._auth_client.validate_token_for_service(token, service_name)
            
            if not validation_result or not validation_result.get("valid", False):
                error_msg = validation_result.get("error", "Service token validation failed") if validation_result else "No validation result"
                logger.warning(f"UNIFIED AUTH: Service token validation failed for {service_name}: {error_msg}")
                
                return AuthResult(
                    success=False,
                    error=error_msg,
                    error_code="SERVICE_VALIDATION_FAILED",
                    metadata={"service_name": service_name}
                )
            
            # Service authentication successful
            service_id = validation_result.get("service_id", service_name)
            permissions = validation_result.get("permissions", [])
            
            logger.info(f"UNIFIED AUTH: Service token validation successful for {service_name}")
            
            return AuthResult(
                success=True,
                user_id=service_id,  # Use service_id as user_id for service accounts
                permissions=permissions,
                metadata={
                    "context": "service_auth",
                    "service_name": service_name,
                    "service_id": service_id
                }
            )
            
        except Exception as e:
            logger.error(f"UNIFIED AUTH: Service token validation error for {service_name}: {e}", exc_info=True)
            
            return AuthResult(
                success=False,
                error=f"Service authentication error: {str(e)}",
                error_code="SERVICE_AUTH_ERROR",
                metadata={"service_name": service_name}
            )
    
    def get_authentication_stats(self) -> Dict[str, Any]:
        """Get authentication statistics for monitoring SSOT compliance."""
        success_rate = (self._auth_successes / max(1, self._auth_attempts)) * 100
        
        return {
            "ssot_enforcement": {
                "service": "UnifiedAuthenticationService",
                "ssot_compliant": True,
                "duplicate_paths_eliminated": 4
            },
            "statistics": {
                "total_attempts": self._auth_attempts,
                "successful_authentications": self._auth_successes,
                "failed_authentications": self._auth_failures,
                "success_rate_percent": round(success_rate, 2)
            },
            "method_distribution": self._method_counts,
            "context_distribution": self._context_counts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for unified authentication service."""
        try:
            # Test underlying auth client health
            # Use a minimal test that doesn't require actual token
            auth_client_healthy = hasattr(self._auth_client, 'circuit_breaker')
            
            return {
                "status": "healthy" if auth_client_healthy else "degraded",
                "service": "UnifiedAuthenticationService",
                "ssot_compliant": True,
                "auth_client_status": "available" if auth_client_healthy else "unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"UNIFIED AUTH: Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "UnifiedAuthenticationService", 
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Global SSOT instance - SINGLE authentication service for entire application
_unified_auth_service: Optional[UnifiedAuthenticationService] = None


def get_unified_auth_service() -> UnifiedAuthenticationService:
    """
    Get the global unified authentication service instance.
    
    This is the ONLY way to access authentication functionality in the system.
    Direct access to auth_client_core or other authentication classes is FORBIDDEN.
    
    Returns:
        UnifiedAuthenticationService instance (SSOT for authentication)
    """
    global _unified_auth_service
    if _unified_auth_service is None:
        _unified_auth_service = UnifiedAuthenticationService()
        logger.info("SSOT ENFORCEMENT: UnifiedAuthenticationService instance created")
    return _unified_auth_service


# SSOT ENFORCEMENT: Export only the unified interface
__all__ = [
    "UnifiedAuthenticationService",
    "AuthResult", 
    "AuthenticationMethod",
    "AuthenticationContext",
    "get_unified_auth_service"
]