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

logger = central_logger.get_logger(__name__)


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
    
    async def authenticate_websocket_connection(self, websocket: WebSocket) -> WebSocketAuthResult:
        """
        Authenticate WebSocket connection using SSOT authentication service.
        
        This method completely replaces:
        - websocket_core/auth.py authentication logic
        - user_context_extractor.py JWT validation methods  
        - Pre-connection validation in websocket.py
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            WebSocketAuthResult with authentication outcome
        """
        self._websocket_auth_attempts += 1
        
        # Track WebSocket connection state
        connection_state = getattr(websocket, 'client_state', 'unknown')
        self._connection_states_seen[connection_state] = self._connection_states_seen.get(connection_state, 0) + 1
        
        # Enhanced authentication attempt logging
        auth_attempt_debug = {
            "connection_state": connection_state,
            "websocket_client_info": {
                "host": getattr(websocket.client, 'host', 'unknown') if websocket.client else 'no_client',
                "port": getattr(websocket.client, 'port', 'unknown') if websocket.client else 'no_client'
            },
            "headers_available": len(websocket.headers) if websocket.headers else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_number": self._websocket_auth_attempts
        }
        
        logger.info(f"SSOT WEBSOCKET AUTH: Starting authentication (state: {connection_state})")
        logger.debug(f"🔐 WEBSOCKET AUTH ATTEMPT DEBUG: {json.dumps(auth_attempt_debug, indent=2)}")
        
        try:
            # Validate WebSocket connection state first
            if not self._is_websocket_valid_for_auth(websocket):
                error_msg = f"WebSocket in invalid state for authentication: {connection_state}"
                logger.error(f"SSOT WEBSOCKET AUTH: {error_msg}")
                self._websocket_auth_failures += 1
                
                return WebSocketAuthResult(
                    success=False,
                    error_message=error_msg,
                    error_code="INVALID_WEBSOCKET_STATE"
                )
            
            # Use SSOT authentication service for WebSocket authentication
            auth_result, user_context = await self._auth_service.authenticate_websocket(websocket)
            
            if not auth_result.success:
                # Enhanced failure debugging
                failure_debug = {
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error,
                    "connection_state": connection_state,
                    "failure_count": self._websocket_auth_failures + 1,
                    "success_rate": (self._websocket_auth_successes / max(1, self._websocket_auth_attempts)) * 100,
                    "websocket_info": {
                        "client_host": getattr(websocket.client, 'host', 'unknown') if websocket.client else 'no_client',
                        "headers_count": len(websocket.headers) if websocket.headers else 0,
                        "state": connection_state
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
                "connection_state": connection_state,
                "permissions_count": len(auth_result.permissions) if auth_result.permissions else 0,
                "websocket_info": {
                    "client_host": getattr(websocket.client, 'host', 'unknown') if websocket.client else 'no_client',
                    "state": connection_state
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
                "connection_state": connection_state,
                "websocket_available": websocket is not None,
                "client_info": {
                    "host": getattr(websocket.client, 'host', 'unknown') if websocket and websocket.client else 'no_client',
                    "port": getattr(websocket.client, 'port', 'unknown') if websocket and websocket.client else 'no_client'
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
            
            await websocket.send_json(error_message)
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
            
            await websocket.send_json(success_message)
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


async def authenticate_websocket_ssot(websocket: WebSocket) -> WebSocketAuthResult:
    """
    Convenience function for SSOT WebSocket authentication.
    
    This function provides a simple interface for WebSocket authentication
    while ensuring SSOT compliance.
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        WebSocketAuthResult with authentication outcome
    """
    authenticator = get_websocket_authenticator()
    return await authenticator.authenticate_websocket_connection(websocket)


# SSOT ENFORCEMENT: Export only SSOT-compliant interfaces
__all__ = [
    "UnifiedWebSocketAuthenticator",
    "WebSocketAuthResult", 
    "get_websocket_authenticator",
    "authenticate_websocket_ssot"
]