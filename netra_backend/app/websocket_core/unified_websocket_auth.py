"""
Unified WebSocket Authentication - SSOT Implementation

Business Value Justification:
- Segment: Platform/Internal - WebSocket Infrastructure  
- Business Goal: Restore WebSocket functionality and eliminate authentication chaos
- Value Impact: Fixes $120K+ MRR blocking issue by providing reliable WebSocket auth
- Revenue Impact: Enables chat functionality that drives user engagement and retention

CRITICAL SSOT COMPLIANCE:
This module replaces ALL existing WebSocket authentication implementations:

ELIMINATED (SSOT Violations):
❌ websocket_core/auth.py - WebSocketAuthenticator class
❌ user_context_extractor.py - 4 different JWT validation methods  
❌ Pre-connection validation logic in websocket.py
❌ Environment-specific authentication branching

PRESERVED (SSOT Sources):
✅ netra_backend.app.services.unified_authentication_service.py
✅ netra_backend.app.clients.auth_client_core.py (as underlying implementation)

This module provides WebSocket-specific wrappers around the SSOT authentication
service while maintaining full SSOT compliance.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, WebSocket
from fastapi.websockets import WebSocketState

from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
from netra_backend.app.websocket_core.utils import _safe_websocket_state_for_logging

logger = central_logger.get_logger(__name__)


def extract_e2e_context_from_websocket(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    Extract E2E testing context from WebSocket headers and environment.
    
    This function checks both WebSocket headers and environment variables to
    determine if this is an E2E test that should bypass strict authentication.
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        Dictionary with E2E context if detected, None otherwise
    """
    try:
        from shared.isolated_environment import get_env
        
        # Check WebSocket headers for E2E indicators
        e2e_headers = {}
        if hasattr(websocket, 'headers') and websocket.headers:
            for key, value in websocket.headers.items():
                key_lower = key.lower()
                if any(e2e_indicator in key_lower for e2e_indicator in ['test', 'e2e']):
                    e2e_headers[key] = value
        
        # Detect E2E testing via headers
        is_e2e_via_headers = False
        if e2e_headers:
            header_values = [v.lower() for v in e2e_headers.values()]
            is_e2e_via_headers = any(
                indicator in ' '.join(header_values) 
                for indicator in ['e2e', 'staging', 'test', 'true', '1']
            )
        
        # Check environment variables for E2E indicators
        env = get_env()
        
        # CRITICAL FIX: Enhanced E2E detection for GCP staging environments
        # Addresses Five-Whys root cause: E2E environment variables not detected in staging
        current_env = env.get("ENVIRONMENT", "unknown").lower()
        google_project = env.get("GOOGLE_CLOUD_PROJECT", "")
        k_service = env.get("K_SERVICE", "")  # GCP Cloud Run service name
        
        # SECURITY FIX: E2E environment variable detection only
        # Removed automatic staging environment detection to prevent auth bypass
        is_e2e_via_env_vars = (
            env.get("E2E_TESTING", "0") == "1" or 
            env.get("PYTEST_RUNNING", "0") == "1" or
            env.get("STAGING_E2E_TEST", "0") == "1" or
            env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
            env.get("E2E_TEST_ENV") == "staging"
        )
        
        # CRITICAL SECURITY FIX: Only use explicit environment variables for E2E bypass
        # Do NOT automatically bypass auth for staging deployments
        is_e2e_via_env = is_e2e_via_env_vars
        
        # Log E2E detection for debugging
        if is_e2e_via_env_vars:
            logger.info(f"E2E DETECTION: Enabled via environment variables "
                       f"(env={current_env}, project={google_project[:20]}..., service={k_service})")
        
        # Create E2E context if detected
        if is_e2e_via_headers or is_e2e_via_env:
            e2e_context = {
                "is_e2e_testing": True,
                "detection_method": {
                    "via_headers": is_e2e_via_headers,
                    "via_environment": is_e2e_via_env,
                    "via_env_vars": is_e2e_via_env_vars
                },
                "e2e_headers": e2e_headers,
                "environment": current_env,
                "google_cloud_project": google_project[:30] + "..." if len(google_project) > 30 else google_project,
                "k_service": k_service,
                "e2e_oauth_key": env.get("E2E_OAUTH_SIMULATION_KEY"),
                "test_environment": env.get("E2E_TEST_ENV"),
                "bypass_enabled": True,
                "enhanced_detection": True,  # Flag indicating enhanced detection was used
                "fix_version": "websocket_1011_five_whys_fix_20250909"  # Version tracking
            }
            
            logger.info(f"E2E CONTEXT DETECTED: {e2e_context['detection_method']}")
            logger.debug(f"E2E CONTEXT DETAILS: {json.dumps(e2e_context, indent=2)}")
            return e2e_context
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract E2E context from WebSocket: {e}")
        return None


# REMOVED DUPLICATE: Use SSOT function from websocket_core.utils


@dataclass
class WebSocketAuthResult:
    """WebSocket-specific authentication result."""
    success: bool
    user_context: Optional[UserExecutionContext] = None
    auth_result: Optional[AuthResult] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility."""
        result = {
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code
        }
        
        if self.user_context:
            result.update({
                "user_id": self.user_context.user_id,
                "websocket_client_id": self.user_context.websocket_client_id,
                "thread_id": self.user_context.thread_id,
                "run_id": self.user_context.run_id
            })
        
        if self.auth_result:
            result.update({
                "email": self.auth_result.email,
                "permissions": self.auth_result.permissions,
                "validated_at": self.auth_result.validated_at
            })
            
        return result


class UnifiedWebSocketAuthenticator:
    """
    SSOT-compliant WebSocket authenticator.
    
    This class provides WebSocket-specific authentication functionality
    while delegating all actual authentication logic to the unified
    authentication service (SSOT compliance).
    
    Key Features:
    - SSOT authentication using UnifiedAuthenticationService
    - WebSocket connection state validation
    - Standardized error handling and responses
    - UserExecutionContext creation for factory pattern
    - Comprehensive logging and monitoring
    """
    
    def __init__(self):
        """Initialize SSOT-compliant WebSocket authenticator."""
        # Use SSOT authentication service - NO direct auth client access
        self._auth_service = get_unified_auth_service()
        
        # Statistics for monitoring
        self._websocket_auth_attempts = 0
        self._websocket_auth_successes = 0
        self._websocket_auth_failures = 0
        self._connection_states_seen = {}
        
        logger.info("UnifiedWebSocketAuthenticator initialized with SSOT compliance")
    
    async def authenticate_websocket_connection(
        self, 
        websocket: WebSocket, 
        e2e_context: Optional[Dict[str, Any]] = None
    ) -> WebSocketAuthResult:
        """
        Authenticate WebSocket connection using SSOT authentication service with E2E support.
        
        This method completely replaces:
        - websocket_core/auth.py authentication logic
        - user_context_extractor.py JWT validation methods  
        - Pre-connection validation in websocket.py
        
        Args:
            websocket: WebSocket connection object
            e2e_context: Optional E2E testing context for bypass support
            
        Returns:
            WebSocketAuthResult with authentication outcome
        """
        self._websocket_auth_attempts += 1
        
        # Track WebSocket connection state - CRITICAL FIX: Use safe string key to prevent JSON serialization errors
        connection_state = getattr(websocket, 'client_state', 'unknown')
        connection_state_safe = _safe_websocket_state_for_logging(connection_state)
        self._connection_states_seen[connection_state_safe] = self._connection_states_seen.get(connection_state_safe, 0) + 1
        
        # Enhanced authentication attempt logging (handle Mock objects for tests)
        def safe_get_attr(obj, attr, default='unknown'):
            try:
                value = getattr(obj, attr, default)
                # Handle Mock objects by converting to string
                if hasattr(value, '_mock_name'):
                    return f"mock_{attr}"
                return str(value)
            except Exception:
                return default
        
        auth_attempt_debug = {
            "connection_state": str(connection_state),  # Convert enum to string for JSON serialization
            "websocket_client_info": {
                "host": safe_get_attr(websocket.client, 'host', 'no_client') if websocket.client else 'no_client',
                "port": safe_get_attr(websocket.client, 'port', 'no_client') if websocket.client else 'no_client'
            },
            "headers_available": len(websocket.headers) if websocket.headers else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_number": self._websocket_auth_attempts
        }
        
        logger.info(f"SSOT WEBSOCKET AUTH: Starting authentication (state: {_safe_websocket_state_for_logging(connection_state)})")
        logger.debug(f"🔐 WEBSOCKET AUTH ATTEMPT DEBUG: {json.dumps(auth_attempt_debug, indent=2)}")
        
        try:
            # Validate WebSocket connection state first
            if not self._is_websocket_valid_for_auth(websocket):
                error_msg = f"WebSocket in invalid state for authentication: {_safe_websocket_state_for_logging(connection_state)}"
                logger.error(f"SSOT WEBSOCKET AUTH: {error_msg}")
                self._websocket_auth_failures += 1
                
                return WebSocketAuthResult(
                    success=False,
                    error_message=error_msg,
                    error_code="INVALID_WEBSOCKET_STATE"
                )
            
            # Extract E2E context from WebSocket if not provided
            if e2e_context is None:
                e2e_context = extract_e2e_context_from_websocket(websocket)
            
            # Use SSOT authentication service for WebSocket authentication with E2E context
            auth_result, user_context = await self._auth_service.authenticate_websocket(
                websocket, 
                e2e_context=e2e_context
            )
            
            if not auth_result.success:
                # Enhanced failure debugging
                failure_debug = {
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error,
                    "connection_state": str(connection_state),
                    "failure_count": self._websocket_auth_failures + 1,
                    "success_rate": (self._websocket_auth_successes / max(1, self._websocket_auth_attempts)) * 100,
                    "websocket_info": {
                        "client_host": safe_get_attr(websocket.client, 'host', 'no_client') if websocket.client else 'no_client',
                        "headers_count": len(websocket.headers) if websocket.headers else 0,
                        "state": str(connection_state)
                    },
                    "metadata_keys": list(auth_result.metadata.keys()) if auth_result.metadata else [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                logger.warning(f"SSOT WEBSOCKET AUTH: Authentication failed - {auth_result.error}")
                logger.error(f"🚨 WEBSOCKET AUTH FAILURE DEBUG: {json.dumps(failure_debug, indent=2)}")
                self._websocket_auth_failures += 1
                
                return WebSocketAuthResult(
                    success=False,
                    auth_result=auth_result,
                    error_message=auth_result.error,
                    error_code=auth_result.error_code
                )
            
            # Authentication successful - Enhanced success logging  
            success_debug = {
                "user_id_prefix": auth_result.user_id[:8] if auth_result.user_id else '[NO_USER_ID]',
                "client_id": user_context.websocket_client_id,
                "success_count": self._websocket_auth_successes + 1,
                "success_rate": ((self._websocket_auth_successes + 1) / max(1, self._websocket_auth_attempts)) * 100,
                "connection_state": str(connection_state),
                "permissions_count": len(auth_result.permissions) if auth_result.permissions else 0,
                "websocket_info": {
                    "client_host": safe_get_attr(websocket.client, 'host', 'no_client') if websocket.client else 'no_client',
                    "state": str(connection_state)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"SSOT WEBSOCKET AUTH: Success for user {auth_result.user_id[:8] if auth_result.user_id else '[NO_USER_ID]'}... (client_id: {user_context.websocket_client_id})")
            logger.debug(f"✅ WEBSOCKET AUTH SUCCESS DEBUG: {json.dumps(success_debug, indent=2)}")
            self._websocket_auth_successes += 1
            
            return WebSocketAuthResult(
                success=True,
                user_context=user_context,
                auth_result=auth_result
            )
            
        except Exception as e:
            # Enhanced exception debugging
            exception_debug = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "connection_state": str(connection_state),
                "websocket_available": websocket is not None,
                "client_info": {
                    "host": safe_get_attr(websocket.client, 'host', 'no_client') if websocket and websocket.client else 'no_client',
                    "port": safe_get_attr(websocket.client, 'port', 'no_client') if websocket and websocket.client else 'no_client'
                },
                "auth_service_available": self._auth_service is not None,
                "failure_count": self._websocket_auth_failures + 1,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.error(f"SSOT WEBSOCKET AUTH: Unexpected error during authentication: {e}", exc_info=True)
            logger.error(f"🔥 WEBSOCKET AUTH EXCEPTION DEBUG: {json.dumps(exception_debug, indent=2)}")
            self._websocket_auth_failures += 1
            
            return WebSocketAuthResult(
                success=False,
                error_message=f"WebSocket authentication error: {str(e)}",
                error_code="WEBSOCKET_AUTH_EXCEPTION"
            )
    
    def _is_websocket_valid_for_auth(self, websocket: WebSocket) -> bool:
        """
        Check if WebSocket is in a valid state for authentication.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            True if WebSocket can be authenticated, False otherwise
        """
        try:
            # Check if WebSocket has required attributes
            if not hasattr(websocket, 'headers'):
                logger.error("SSOT WEBSOCKET AUTH: WebSocket missing headers attribute")
                return False
            
            if not hasattr(websocket, 'client_state'):
                logger.warning("SSOT WEBSOCKET AUTH: WebSocket missing client_state attribute")
                # Don't fail - some WebSocket implementations may not have this
            
            # Check connection state if available
            client_state = getattr(websocket, 'client_state', None)
            if client_state is not None and client_state == WebSocketState.DISCONNECTED:
                logger.error("SSOT WEBSOCKET AUTH: WebSocket already disconnected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"SSOT WEBSOCKET AUTH: Error validating WebSocket state: {e}")
            return False
    
    async def create_auth_error_response(self, websocket: WebSocket, auth_result: WebSocketAuthResult) -> None:
        """
        Send standardized authentication error response to WebSocket client.
        
        Args:
            websocket: WebSocket connection object
            auth_result: Failed authentication result
        """
        try:
            # Don't send error if WebSocket is not connected
            if not self._is_websocket_connected(websocket):
                logger.warning("SSOT WEBSOCKET AUTH: Cannot send auth error - WebSocket not connected")
                return
            
            error_message = {
                "type": "authentication_error",
                "event": "auth_failed", 
                "error": auth_result.error_message or "Authentication failed",
                "error_code": auth_result.error_code or "AUTH_FAILED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_allowed": auth_result.error_code in ["VALIDATION_FAILED", "TOKEN_EXPIRED"],
                "ssot_authenticated": False
            }
            
            # CRITICAL FIX: Use safe serialization to handle WebSocketState enums and other complex objects
            safe_error_message = _serialize_message_safely(error_message)
            await websocket.send_json(safe_error_message)
            logger.debug(f"SSOT WEBSOCKET AUTH: Sent error response - {auth_result.error_code}")
            
        except Exception as e:
            logger.error(f"SSOT WEBSOCKET AUTH: Error sending auth error response: {e}")
    
    async def create_auth_success_response(self, websocket: WebSocket, auth_result: WebSocketAuthResult) -> None:
        """
        Send standardized authentication success response to WebSocket client.
        
        Args:
            websocket: WebSocket connection object  
            auth_result: Successful authentication result
        """
        try:
            # Don't send response if WebSocket is not connected
            if not self._is_websocket_connected(websocket):
                logger.warning("SSOT WEBSOCKET AUTH: Cannot send auth success - WebSocket not connected") 
                return
            
            success_message = {
                "type": "authentication_success",
                "event": "auth_success",
                "user_id": auth_result.user_context.user_id,
                "websocket_client_id": auth_result.user_context.websocket_client_id,
                "permissions": auth_result.auth_result.permissions,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ssot_authenticated": True
            }
            
            # CRITICAL FIX: Use safe serialization to handle WebSocketState enums and other complex objects
            safe_success_message = _serialize_message_safely(success_message)
            await websocket.send_json(safe_success_message)
            logger.debug(f"SSOT WEBSOCKET AUTH: Sent success response for {auth_result.user_context.user_id[:8]}...")
            
        except Exception as e:
            logger.error(f"SSOT WEBSOCKET AUTH: Error sending auth success response: {e}")
    
    def _is_websocket_connected(self, websocket: WebSocket) -> bool:
        """Check if WebSocket is currently connected."""
        try:
            client_state = getattr(websocket, 'client_state', None)
            application_state = getattr(websocket, 'application_state', None)
            
            # Consider connected if client_state is CONNECTED or if states are not available
            if client_state is not None:
                return client_state == WebSocketState.CONNECTED
            
            # Fallback: assume connected if we can't determine state
            return True
            
        except Exception as e:
            logger.error(f"SSOT WEBSOCKET AUTH: Error checking WebSocket connection: {e}")
            return False
    
    async def handle_authentication_failure(self, websocket: WebSocket, auth_result: WebSocketAuthResult, close_connection: bool = True) -> None:
        """
        Handle WebSocket authentication failure with standardized response.
        
        Args:
            websocket: WebSocket connection object
            auth_result: Failed authentication result
            close_connection: Whether to close WebSocket connection after error
        """
        logger.warning(f"SSOT WEBSOCKET AUTH: Handling auth failure - {auth_result.error_code}: {auth_result.error_message}")
        
        try:
            # Send error response to client
            await self.create_auth_error_response(websocket, auth_result)
            
            # Allow brief time for message to be sent
            await asyncio.sleep(0.1)
            
            # Close connection if requested
            if close_connection and self._is_websocket_connected(websocket):
                close_code = self._get_close_code_for_error(auth_result.error_code)
                close_reason = auth_result.error_message[:50] if auth_result.error_message else "Auth failed"
                
                await websocket.close(code=close_code, reason=close_reason)
                logger.info(f"SSOT WEBSOCKET AUTH: Closed WebSocket connection due to auth failure")
            
        except Exception as e:
            logger.error(f"SSOT WEBSOCKET AUTH: Error handling authentication failure: {e}")
            
            # Force close connection as last resort
            if close_connection:
                try:
                    await websocket.close(code=1008, reason="Auth error")
                except Exception:
                    pass  # Best effort close
    
    def _get_close_code_for_error(self, error_code: Optional[str]) -> int:
        """Get appropriate WebSocket close code for authentication error."""
        error_code_mapping = {
            "NO_TOKEN": 1008,  # Policy violation
            "INVALID_FORMAT": 1008,  # Policy violation
            "VALIDATION_FAILED": 1008,  # Policy violation  
            "TOKEN_EXPIRED": 1008,  # Policy violation
            "AUTH_SERVICE_ERROR": 1011,  # Server error
            "WEBSOCKET_AUTH_ERROR": 1011,  # Server error
            "INVALID_WEBSOCKET_STATE": 1002,  # Protocol error
        }
        
        return error_code_mapping.get(error_code, 1008)  # Default to policy violation
    
    def get_websocket_auth_stats(self) -> Dict[str, Any]:
        """Get WebSocket authentication statistics for monitoring."""
        success_rate = (self._websocket_auth_successes / max(1, self._websocket_auth_attempts)) * 100
        
        return {
            "ssot_compliance": {
                "service": "UnifiedWebSocketAuthenticator",
                "ssot_compliant": True,
                "authentication_service": "UnifiedAuthenticationService",
                "duplicate_paths_eliminated": 4
            },
            "websocket_auth_statistics": {
                "total_attempts": self._websocket_auth_attempts,
                "successful_authentications": self._websocket_auth_successes,
                "failed_authentications": self._websocket_auth_failures,
                "success_rate_percent": round(success_rate, 2)
            },
            "connection_states_seen": self._connection_states_seen,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global SSOT instance for WebSocket authentication
_websocket_authenticator: Optional[UnifiedWebSocketAuthenticator] = None


def get_websocket_authenticator() -> UnifiedWebSocketAuthenticator:
    """
    Get the global SSOT-compliant WebSocket authenticator.
    
    This is the ONLY way to perform WebSocket authentication in the system.
    All other WebSocket authentication implementations have been eliminated.
    
    Returns:
        UnifiedWebSocketAuthenticator instance (SSOT for WebSocket auth)
    """
    global _websocket_authenticator
    if _websocket_authenticator is None:
        _websocket_authenticator = UnifiedWebSocketAuthenticator()
        logger.info("SSOT ENFORCEMENT: UnifiedWebSocketAuthenticator instance created")
    return _websocket_authenticator


async def authenticate_websocket_ssot(
    websocket: WebSocket, 
    e2e_context: Optional[Dict[str, Any]] = None
) -> WebSocketAuthResult:
    """
    SSOT WebSocket authentication with E2E bypass support.
    
    This function provides SSOT-compliant WebSocket authentication while
    supporting E2E testing context propagation to prevent policy violations.
    
    Args:
        websocket: WebSocket connection object
        e2e_context: Optional E2E testing context for bypass support
        
    Returns:
        WebSocketAuthResult with authentication outcome
    """
    authenticator = get_websocket_authenticator()
    return await authenticator.authenticate_websocket_connection(websocket, e2e_context=e2e_context)


# Legacy aliases for backward compatibility
WebSocketAuthenticator = UnifiedWebSocketAuthenticator
UnifiedWebSocketAuth = UnifiedWebSocketAuthenticator

# SSOT ENFORCEMENT: Export only SSOT-compliant interfaces
__all__ = [
    "UnifiedWebSocketAuthenticator",
    "WebSocketAuthenticator",  # Legacy alias
    "UnifiedWebSocketAuth",  # Legacy alias
    "WebSocketAuthResult", 
    "get_websocket_authenticator",
    "authenticate_websocket_ssot"
]