"""
WebSocket Ticket Authentication Coordination - Issue #1313 Implementation

Business Impact: Fixes critical WebSocket handshake race conditions causing 1011 errors in Cloud Run,
restoring $500K+ ARR chat functionality by ensuring proper auth coordination.

Technical Impact: Implements pre-authenticated ticket system that allows WebSocket connections to 
verify authentication without waiting for JWT validation during handshake, eliminating race conditions.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.unified_auth_ssot import (
    AuthTicketManager,
    AuthTicket,
    WebSocketAuthResult,
    get_ticket_manager
)

logger = get_logger(__name__)


@dataclass
class WebSocketHandshakeState:
    """Tracks WebSocket handshake state to prevent race conditions."""
    connection_id: str
    handshake_started: float
    auth_verified: bool = False
    ticket_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    handshake_completed: bool = False
    
    def is_expired(self, timeout_seconds: int = 30) -> bool:
        """Check if handshake has expired."""
        return time.time() - self.handshake_started > timeout_seconds


class WebSocketTicketCoordinator:
    """
    SSOT: WebSocket Ticket Coordination for Race Condition Prevention
    
    Addresses Issue #1313 by implementing a coordination layer that:
    1. Pre-validates authentication tickets before WebSocket handshake
    2. Maintains handshake state to prevent race conditions
    3. Provides fast-path authentication for ticket-based connections
    4. Implements graceful degradation for JWT-based authentication
    """
    
    def __init__(self):
        """Initialize the coordinator with ticket manager and handshake tracking."""
        self._ticket_manager = get_ticket_manager()
        self._handshake_states: Dict[str, WebSocketHandshakeState] = {}
        self._coordination_lock = asyncio.Lock()
        
    async def prepare_websocket_authentication(
        self, 
        connection_id: str,
        ticket_id: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Prepare authentication for WebSocket connection BEFORE handshake.
        
        This is the key method for preventing race conditions - it validates
        authentication credentials before the WebSocket handshake begins,
        storing the validated user context for instant retrieval during handshake.
        
        Args:
            connection_id: Unique connection identifier
            ticket_id: Authentication ticket ID if available
            jwt_token: JWT token if ticket not available
            
        Returns:
            Tuple of (success, user_context) - user_context is pre-validated
        """
        async with self._coordination_lock:
            try:
                # Initialize handshake state
                handshake_state = WebSocketHandshakeState(
                    connection_id=connection_id,
                    handshake_started=time.time(),
                    ticket_id=ticket_id
                )
                
                self._handshake_states[connection_id] = handshake_state
                
                logger.info(f"🎫 Preparing WebSocket auth for connection {connection_id}")
                
                # Fast path: Ticket-based authentication (prevents race conditions)
                if ticket_id:
                    user_context = await self._validate_ticket_fast_path(ticket_id)
                    if user_context:
                        handshake_state.auth_verified = True
                        handshake_state.user_context = user_context
                        logger.info(f"✅ Ticket auth prepared for connection {connection_id}")
                        return True, user_context
                    else:
                        logger.warning(f"❌ Ticket validation failed for connection {connection_id}")
                
                # Fallback path: JWT validation (higher race condition risk)
                if jwt_token:
                    user_context = await self._validate_jwt_fallback(jwt_token)
                    if user_context:
                        handshake_state.auth_verified = True
                        handshake_state.user_context = user_context
                        logger.info(f"✅ JWT auth prepared for connection {connection_id}")
                        return True, user_context
                    else:
                        logger.warning(f"❌ JWT validation failed for connection {connection_id}")
                
                # All authentication failed
                logger.error(f"❌ All auth methods failed for connection {connection_id}")
                return False, None
                
            except Exception as e:
                logger.error(f"❌ Auth preparation error for connection {connection_id}: {e}")
                return False, None
    
    async def get_prepared_auth_context(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve pre-validated authentication context for WebSocket handshake.
        
        This provides instant authentication without waiting for validation,
        eliminating the race condition between handshake and auth verification.
        
        Args:
            connection_id: Unique connection identifier
            
        Returns:
            Pre-validated user context or None if not available
        """
        handshake_state = self._handshake_states.get(connection_id)
        
        if not handshake_state:
            logger.debug(f"No handshake state found for connection {connection_id}")
            return None
            
        if handshake_state.is_expired():
            logger.warning(f"Handshake state expired for connection {connection_id}")
            await self.cleanup_connection(connection_id)
            return None
            
        if not handshake_state.auth_verified:
            logger.debug(f"Auth not verified for connection {connection_id}")
            return None
            
        logger.info(f"🚀 Providing prepared auth context for connection {connection_id}")
        return handshake_state.user_context
    
    async def mark_handshake_completed(self, connection_id: str) -> bool:
        """
        Mark WebSocket handshake as completed successfully.
        
        Args:
            connection_id: Unique connection identifier
            
        Returns:
            True if marked successfully, False if state not found
        """
        handshake_state = self._handshake_states.get(connection_id)
        
        if not handshake_state:
            logger.warning(f"Cannot mark completed - no handshake state for {connection_id}")
            return False
            
        handshake_state.handshake_completed = True
        logger.info(f"✅ WebSocket handshake completed for connection {connection_id}")
        return True
    
    async def cleanup_connection(self, connection_id: str) -> None:
        """
        Clean up handshake state for completed or failed connections.
        
        Args:
            connection_id: Unique connection identifier
        """
        async with self._coordination_lock:
            if connection_id in self._handshake_states:
                del self._handshake_states[connection_id]
                logger.debug(f"🧹 Cleaned up handshake state for connection {connection_id}")
    
    async def get_handshake_statistics(self) -> Dict[str, Any]:
        """
        Get current handshake coordination statistics for monitoring.
        
        Returns:
            Dictionary with coordination statistics
        """
        current_time = time.time()
        active_handshakes = len(self._handshake_states)
        
        completed_handshakes = sum(
            1 for state in self._handshake_states.values() 
            if state.handshake_completed
        )
        
        expired_handshakes = sum(
            1 for state in self._handshake_states.values()
            if state.is_expired()
        )
        
        ticket_auth_count = sum(
            1 for state in self._handshake_states.values()
            if state.ticket_id is not None
        )
        
        return {
            "active_handshakes": active_handshakes,
            "completed_handshakes": completed_handshakes,
            "expired_handshakes": expired_handshakes,
            "ticket_auth_count": ticket_auth_count,
            "jwt_auth_count": active_handshakes - ticket_auth_count,
            "coordination_enabled": True,
            "timestamp": current_time
        }
    
    async def _validate_ticket_fast_path(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Fast path ticket validation that prevents race conditions.
        
        Args:
            ticket_id: Authentication ticket ID
            
        Returns:
            User context dictionary if valid, None otherwise
        """
        try:
            ticket = await self._ticket_manager.validate_ticket(ticket_id)
            
            if ticket:
                return {
                    "user_id": ticket.user_id,
                    "email": ticket.email,
                    "permissions": ticket.permissions,
                    "auth_method": "ticket-fast-path",
                    "ticket_id": ticket_id,
                    "ticket_metadata": ticket.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ticket fast path validation error: {e}")
            return None
    
    async def _validate_jwt_fallback(self, jwt_token: str) -> Optional[Dict[str, Any]]:
        """
        Fallback JWT validation (higher race condition risk).
        
        Args:
            jwt_token: JWT token to validate
            
        Returns:
            User context dictionary if valid, None otherwise
        """
        try:
            # Import here to avoid circular dependencies
            from netra_backend.app.clients.auth_client_core import auth_client
            
            validation_result = await auth_client.validate_token_jwt(jwt_token)
            
            if validation_result and validation_result.get('valid'):
                return {
                    "user_id": validation_result.get('user_id'),
                    "email": validation_result.get('email'),
                    "permissions": validation_result.get('permissions', []),
                    "auth_method": "jwt-fallback",
                    "jwt_token": jwt_token[:20] + "..." if jwt_token else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"JWT fallback validation error: {e}")
            return None
    
    async def cleanup_expired_handshakes(self) -> int:
        """
        Periodic cleanup of expired handshake states.
        
        Returns:
            Number of expired handshakes cleaned up
        """
        async with self._coordination_lock:
            expired_connections = [
                conn_id for conn_id, state in self._handshake_states.items()
                if state.is_expired()
            ]
            
            for conn_id in expired_connections:
                del self._handshake_states[conn_id]
                
            if expired_connections:
                logger.info(f"🧹 Cleaned up {len(expired_connections)} expired handshakes")
                
            return len(expired_connections)


# SSOT EXPORT: Single coordinator instance
websocket_ticket_coordinator = WebSocketTicketCoordinator()


async def prepare_websocket_auth(
    connection_id: str,
    ticket_id: Optional[str] = None,
    jwt_token: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    SSOT FUNCTION: Prepare WebSocket authentication to prevent race conditions.
    
    This function should be called BEFORE WebSocket handshake to pre-validate
    authentication and eliminate race conditions in Cloud Run environments.
    
    Args:
        connection_id: Unique connection identifier
        ticket_id: Authentication ticket ID (preferred)
        jwt_token: JWT token (fallback)
        
    Returns:
        Tuple of (success, user_context) for instant handshake use
    """
    return await websocket_ticket_coordinator.prepare_websocket_authentication(
        connection_id=connection_id,
        ticket_id=ticket_id,
        jwt_token=jwt_token
    )


async def get_prepared_auth_context(connection_id: str) -> Optional[Dict[str, Any]]:
    """
    SSOT FUNCTION: Get pre-validated auth context for instant handshake.
    
    Args:
        connection_id: Unique connection identifier
        
    Returns:
        Pre-validated user context or None
    """
    return await websocket_ticket_coordinator.get_prepared_auth_context(connection_id)


async def mark_handshake_completed(connection_id: str) -> bool:
    """
    SSOT FUNCTION: Mark WebSocket handshake as completed.
    
    Args:
        connection_id: Unique connection identifier
        
    Returns:
        True if marked successfully
    """
    return await websocket_ticket_coordinator.mark_handshake_completed(connection_id)


async def cleanup_connection(connection_id: str) -> None:
    """
    SSOT FUNCTION: Clean up connection state.
    
    Args:
        connection_id: Unique connection identifier
    """
    await websocket_ticket_coordinator.cleanup_connection(connection_id)


def get_websocket_ticket_coordinator() -> WebSocketTicketCoordinator:
    """
    Get the global WebSocket ticket coordinator instance.
    
    Returns:
        WebSocketTicketCoordinator: The global coordinator instance
    """
    return websocket_ticket_coordinator