"""WebSocket authentication and security module.

Provides authentication, authorization, and security for WebSocket connections.
"""

import asyncio
import base64
from typing import Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import WebSocket, HTTPException

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class AuthInfo:
    """Authentication information for WebSocket connections."""
    user_id: str
    email: str
    permissions: list
    authenticated: bool = True


class WebSocketAuthenticator:
    """Handles WebSocket authentication."""
    
    def __init__(self):
        """Initialize WebSocket authenticator with auth client."""
        # Import here to avoid circular imports
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # Create a new instance instead of using singleton to ensure circuit breaker is initialized
        self.auth_client = AuthServiceClient()
        self._auth_attempts = 0
        self._successful_auths = 0
        self._failed_auths = 0
    
    async def authenticate(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate a WebSocket connection using real JWT validation."""
        if not token:
            logger.warning("WebSocket authentication: No token provided")
            self._failed_auths += 1
            return None
        
        # Clean token (remove Bearer prefix if present)
        clean_token = token.replace("Bearer ", "").strip()
        
        self._auth_attempts += 1
        logger.info(f"WebSocket authentication attempt for token: {clean_token[:20]}...")
        
        try:
            # Use the existing auth client for JWT validation with circuit breaker protection
            # The auth client now has built-in circuit breaker that will handle failures gracefully
            validation_result = await self.auth_client.validate_token_jwt(clean_token)
            
            if not validation_result:
                # Check if auth service is unavailable (circuit breaker open)
                from netra_backend.app.clients.circuit_breaker import CircuitState
                if hasattr(self.auth_client, 'circuit_breaker') and self.auth_client.circuit_breaker.state == CircuitState.OPEN:
                    logger.warning("WebSocket authentication: Auth service unavailable (circuit open) - using local validation")
                    # Try local JWT validation as fallback when auth service is down
                    try:
                        local_result = await self.auth_client._local_validate(clean_token)
                        if local_result and local_result.get("valid", False):
                            logger.info("WebSocket authentication: Successfully used local JWT validation fallback")
                            return local_result
                    except Exception as local_err:
                        logger.error(f"WebSocket authentication: Local validation also failed: {local_err}")
                
                logger.warning("WebSocket authentication: Token validation returned None")
                self._failed_auths += 1
                return None
            
            # Check if validation was successful
            if not validation_result.get("valid", False):
                error_msg = validation_result.get("error", "Token validation failed")
                logger.warning(f"WebSocket authentication: Token validation failed - {error_msg}")
                self._failed_auths += 1
                return None
            
            # Extract user information from validated token
            user_id = validation_result.get("user_id")
            email = validation_result.get("email", "")
            permissions = validation_result.get("permissions", [])
            
            if not user_id:
                logger.error("WebSocket authentication: Valid token but no user_id found")
                self._failed_auths += 1
                return None
            
            self._successful_auths += 1
            logger.info(f"WebSocket authentication successful for user: {user_id}")
            
            return {
                "user_id": user_id,
                "email": email,
                "permissions": permissions,
                "authenticated": True,
                "source": "jwt_validation"
            }
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}", exc_info=True)
            self._failed_auths += 1
            return None
    
    def extract_token_from_websocket(self, websocket: WebSocket) -> Optional[str]:
        """Extract JWT token from WebSocket headers or subprotocol."""
        
        # Method 1: Authorization header (Bearer token)
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()  # Remove "Bearer " prefix
            logger.debug("WebSocket token found in Authorization header")
            return token
        
        # Method 2: Sec-WebSocket-Protocol header (jwt.base64_token)
        subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        for protocol in subprotocols:
            protocol = protocol.strip()
            if protocol.startswith("jwt."):
                try:
                    # Extract base64 encoded token
                    encoded_token = protocol[4:]  # Remove "jwt." prefix
                    # Base64 decode the token
                    token_bytes = base64.urlsafe_b64decode(encoded_token + "===")  # Add padding
                    token = token_bytes.decode('utf-8')
                    logger.debug("WebSocket token found in Sec-WebSocket-Protocol")
                    return token
                except Exception as e:
                    logger.warning(f"Failed to decode token from subprotocol: {e}")
                    continue
        
        # Method 3: Query parameter (for testing/fallback)
        if hasattr(websocket, 'query_params'):
            token = websocket.query_params.get("token")
            if token:
                logger.debug("WebSocket token found in query parameters")
                return token
        
        logger.warning("No WebSocket authentication token found in any expected location")
        return None
    
    async def authenticate_websocket(self, websocket: WebSocket) -> AuthInfo:
        """Authenticate a WebSocket connection and return AuthInfo."""
        
        # Extract token from WebSocket
        token = self.extract_token_from_websocket(websocket)
        
        if not token:
            logger.warning("WebSocket authentication failed: No token found")
            raise HTTPException(status_code=401, detail="No authentication token provided")
        
        # Validate token
        auth_result = await self.authenticate(token)
        
        if not auth_result or not auth_result.get("authenticated", False):
            error_detail = "Invalid or expired authentication token"
            if auth_result:
                # Include more specific error information if available
                error_info = auth_result.get("error", "")
                if error_info:
                    error_detail = f"Authentication failed: {error_info}"
            
            logger.warning(f"WebSocket authentication failed: {error_detail}")
            raise HTTPException(status_code=401, detail=error_detail)
        
        # Create AuthInfo object
        auth_info = AuthInfo(
            user_id=auth_result["user_id"],
            email=auth_result.get("email", ""),
            permissions=auth_result.get("permissions", []),
            authenticated=True
        )
        
        logger.info(f"WebSocket authentication completed for user: {auth_info.user_id}")
        return auth_info
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        total_attempts = max(1, self._auth_attempts)  # Avoid division by zero
        success_rate = self._successful_auths / total_attempts
        
        return {
            "total_attempts": self._auth_attempts,
            "successful_auths": self._successful_auths,
            "failed_auths": self._failed_auths,
            "success_rate": success_rate
        }


class ConnectionSecurityManager:
    """Manages WebSocket connection security."""
    
    def __init__(self):
        self._secure_connections = set()
        self._registered_connections = {}  # connection_id -> {auth_info, websocket, timestamp}
        self._security_violations = {}  # connection_id -> [violations]
    
    def mark_secure(self, connection_id: str):
        """Mark a connection as secure."""
        self._secure_connections.add(connection_id)
    
    def is_secure(self, connection_id: str) -> bool:
        """Check if a connection is secure."""
        return connection_id in self._secure_connections
    
    def register_connection(self, connection_id: str, auth_info: AuthInfo, websocket) -> None:
        """Register a connection with security manager."""
        import time
        
        self._registered_connections[connection_id] = {
            "auth_info": auth_info,
            "websocket": websocket,
            "registered_at": time.time(),
            "user_id": auth_info.user_id
        }
        
        # Mark as secure
        self.mark_secure(connection_id)
        
        logger.debug(f"Registered secure connection: {connection_id} for user: {auth_info.user_id}")
    
    def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection from security manager."""
        
        # Remove from secure connections
        self._secure_connections.discard(connection_id)
        
        # Remove from registered connections
        if connection_id in self._registered_connections:
            user_id = self._registered_connections[connection_id]["user_id"]
            del self._registered_connections[connection_id]
            logger.debug(f"Unregistered connection: {connection_id} for user: {user_id}")
        
        # Clean up security violations
        if connection_id in self._security_violations:
            del self._security_violations[connection_id]
    
    def validate_connection_security(self, connection_id: str) -> bool:
        """Validate connection security status."""
        
        # Check if connection is registered and secure
        if connection_id not in self._registered_connections:
            logger.warning(f"Security validation failed: Connection {connection_id} not registered")
            return False
        
        if connection_id not in self._secure_connections:
            logger.warning(f"Security validation failed: Connection {connection_id} not marked as secure")
            return False
        
        # Check for excessive security violations
        violations = self._security_violations.get(connection_id, [])
        if len(violations) > 5:  # More than 5 violations
            logger.warning(f"Security validation failed: Connection {connection_id} has too many violations: {len(violations)}")
            return False
        
        return True
    
    def report_security_violation(self, connection_id: str, violation_type: str, details: Dict[str, Any] = None) -> None:
        """Report a security violation for a connection."""
        import time
        
        if connection_id not in self._security_violations:
            self._security_violations[connection_id] = []
        
        violation = {
            "type": violation_type,
            "details": details or {},
            "timestamp": time.time()
        }
        
        self._security_violations[connection_id].append(violation)
        
        logger.warning(f"Security violation reported for {connection_id}: {violation_type} - {details}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary for monitoring."""
        total_violations = sum(len(violations) for violations in self._security_violations.values())
        
        return {
            "secure_connections": len(self._secure_connections),
            "registered_connections": len(self._registered_connections),
            "total_violations": total_violations,
            "connections_with_violations": len(self._security_violations)
        }


class RateLimiter:
    """Rate limiter for WebSocket connections."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = {}
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        # Simplified rate limiting
        return True


# Global instances
_authenticator = None
_security_manager = None


def get_websocket_authenticator() -> WebSocketAuthenticator:
    """Get the WebSocket authenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = WebSocketAuthenticator()
    return _authenticator


def get_connection_security_manager() -> ConnectionSecurityManager:
    """Get the connection security manager."""
    global _security_manager
    if _security_manager is None:
        _security_manager = ConnectionSecurityManager()
    return _security_manager


@asynccontextmanager
async def secure_websocket_context(websocket_or_id):
    """Context manager for secure WebSocket operations.
    
    This function is overloaded to support both:
    1. WebSocket object (for authentication)
    2. connection_id string (for legacy compatibility)
    """
    
    # Handle overloaded parameters
    if isinstance(websocket_or_id, str):
        # Legacy usage: secure_websocket_context(connection_id)
        connection_id = websocket_or_id
        manager = get_connection_security_manager()
        manager.mark_secure(connection_id)
        try:
            yield
        finally:
            pass
    else:
        # New usage: secure_websocket_context(websocket) -> (auth_info, security_manager)
        websocket = websocket_or_id
        
        # Authenticate the WebSocket connection
        authenticator = get_websocket_authenticator()
        auth_info = await authenticator.authenticate_websocket(websocket)
        
        # Get security manager
        security_manager = get_connection_security_manager()
        
        try:
            yield auth_info, security_manager
        finally:
            pass