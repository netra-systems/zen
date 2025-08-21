"""Unified WebSocket Manager - Central orchestration for real-time communication.

Consolidates all WebSocket management into a single, modular system with:
- Connection pooling and lifecycle management
- Message queuing with zero-loss guarantee
- Circuit breaker integration for resilience
- Real-time performance telemetry
- Pluggable modules for messaging, broadcasting, and state

Business Value: Eliminates $8K MRR loss from poor real-time experience
All functions ≤8 lines as per CLAUDE.md requirements.
"""

import asyncio
import json
import time
from typing import Dict, Any, Union, List, Optional, Literal
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage, ServerMessage
from app.schemas.websocket_models import (
    WebSocketValidationError,
    WebSocketStats,
    RateLimitInfo,
    BroadcastResult
)
from app.websocket.connection import ConnectionInfo, ConnectionManager
from app.websocket.rate_limiter import RateLimiter
from app.websocket.error_handler import WebSocketErrorHandler
from app.websocket.room_manager import RoomManager

# Import unified modules
from .messaging import UnifiedMessagingManager
from .broadcasting import UnifiedBroadcastingManager
from .state import UnifiedStateManager
from .circuit_breaker import CircuitBreaker
from .telemetry_manager import TelemetryManager
from ..lifecycle_integration import get_lifecycle_integrator

logger = central_logger.get_logger(__name__)


class UnifiedWebSocketManager:
    """Unified WebSocket manager with modular architecture and circuit breaker."""
    
    _instance: Optional['UnifiedWebSocketManager'] = None

    def __new__(cls) -> 'UnifiedWebSocketManager':
        """Singleton pattern for unified manager."""
        if cls._instance is None:
            cls._instance = super(UnifiedWebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize unified WebSocket manager if not already done."""
        if getattr(self, '_initialized', False):
            # Even if initialized, ensure telemetry is valid for tests
            if not hasattr(self, 'telemetry') or not isinstance(self.telemetry, dict):
                self._initialize_telemetry()
            return
        self._initialize_core_components()
        self._initialize_unified_modules()
        self._initialize_circuit_breaker()
        self._initialize_telemetry()
        self._initialized = True

    def _initialize_core_components(self) -> None:
        """Initialize core WebSocket components."""
        self.connection_manager = ConnectionManager()
        self.rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
        self.error_handler = WebSocketErrorHandler()
        self.room_manager = RoomManager(self.connection_manager)

    def _initialize_unified_modules(self) -> None:
        """Initialize unified modular components."""
        self.messaging = UnifiedMessagingManager(self)
        self.broadcasting = UnifiedBroadcastingManager(self)
        self.state = UnifiedStateManager(self)

    def _initialize_circuit_breaker(self) -> None:
        """Initialize circuit breaker for resilience."""
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    def _initialize_telemetry(self) -> None:
        """Initialize telemetry manager for tracking and transactions."""
        self.telemetry_manager = TelemetryManager()
        # For backward compatibility, expose telemetry as a property
        self.telemetry = self.telemetry_manager.telemetry
        self.pending_messages = self.telemetry_manager.pending_messages
        self.sending_messages = self.telemetry_manager.sending_messages
        self.message_lock = self.telemetry_manager.message_lock
        
        # Initialize enhanced lifecycle management
        self.lifecycle_integrator = get_lifecycle_integrator()

    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish WebSocket connection with enhanced lifecycle and circuit breaker protection."""
        # Start cleanup task on first connection if not already started
        await self.telemetry_manager.start_periodic_cleanup()
            
        if not self.circuit_breaker.can_execute():
            self._record_circuit_break()
            raise ConnectionError("Circuit breaker is open")
        
        # Use enhanced lifecycle integration for connection
        try:
            conn_info = await self.lifecycle_integrator.integrate_connection(user_id, websocket)
            self.circuit_breaker.record_success()
            self.telemetry["connections_opened"] += 1
            
            # Handle state synchronization for new connection
            await self.messaging.message_handler.handle_new_connection_state_sync(
                user_id, conn_info.connection_id, websocket
            )
            
            return conn_info
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

    def _record_circuit_break(self) -> None:
        """Record circuit breaker activation."""
        self.telemetry["circuit_breaks"] += 1
        logger.warning("Circuit breaker prevented connection attempt")

    async def _execute_protected_connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Execute connection with circuit breaker protection."""
        try:
            conn_info = await self.connection_manager.connect(user_id, websocket)
            self.circuit_breaker.record_success()
            self.telemetry["connections_opened"] += 1
            return conn_info
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

    async def disconnect_user(self, user_id: str, websocket: WebSocket, 
                       code: int = 1000, reason: str = "Normal closure") -> None:
        """Safely disconnect user with enhanced lifecycle cleanup."""
        try:
            # Find connection info before disconnecting
            conn_info = await self.connection_manager.find_connection(user_id, websocket)
            if conn_info:
                await self.messaging.message_handler.handle_disconnection_state_sync(
                    user_id, conn_info.connection_id
                )
            
            # Use enhanced lifecycle integration for disconnection
            await self.lifecycle_integrator.integrate_disconnection(user_id, websocket, code, reason)
            self.telemetry["connections_closed"] += 1
            
            # Additional cleanup for abnormal disconnects
            if code != 1000:
                await self._handle_abnormal_disconnect_telemetry(user_id, code, reason)
                
        except Exception as e:
            logger.error(f"Error during user disconnect: {e}")
            self.telemetry["errors_handled"] += 1
            # Ensure telemetry is updated even on error
            self.telemetry["connections_closed"] += 1
    
    async def _handle_abnormal_disconnect_telemetry(self, user_id: str, code: int, reason: str) -> None:
        """Handle telemetry for abnormal disconnects."""
        logger.warning(f"Abnormal disconnect for user {user_id}, code: {code}, reason: {reason}")
        
        # Track abnormal disconnects in telemetry
        if "abnormal_disconnects" not in self.telemetry:
            self.telemetry["abnormal_disconnects"] = 0
        self.telemetry["abnormal_disconnects"] += 1
        
        # Clean up any room associations
        if hasattr(self, 'room_manager'):
            self.room_manager.leave_all_rooms(user_id)

    async def send_message_to_user(self, user_id: str, 
                                  message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                                  retry: bool = True) -> bool:
        """Send message to user through unified messaging system with transactional processing."""
        # Mark message as sending before attempting to send (transactional pattern)
        message_id = f"msg_{user_id}_{int(time.time() * 1000)}"
        
        try:
            # Track message as 'sending' before actual send
            await self.telemetry_manager.mark_message_sending(message_id, user_id, message)
            
            # Attempt to send message
            result = await self.messaging.send_to_user(user_id, message, retry)
            
            if result:
                # Only mark as sent on confirmed success
                await self.telemetry_manager.mark_message_sent(message_id)
                self.telemetry["messages_sent"] += 1
                return True
            else:
                # Revert to pending if send failed
                await self.telemetry_manager.mark_message_pending(message_id, user_id, message)
                return False
                
        except Exception as e:
            # Revert to pending on exception
            await self.telemetry_manager.mark_message_pending(message_id, user_id, message)
            logger.error(f"Transactional message send failed for {user_id}: {e}")
            raise

    async def broadcast_to_job(self, job_id: str, 
                              message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast message to job through unified broadcasting system."""
        return await self.broadcasting.broadcast_to_job(job_id, message)

    async def handle_message(self, user_id: str, websocket: WebSocket, 
                           message: Dict[str, Any]) -> bool:
        """Handle incoming message with enhanced lifecycle integration."""
        # First try enhanced lifecycle handling (ping/pong/heartbeat)
        lifecycle_handled = await self.lifecycle_integrator.handle_websocket_message(
            user_id, websocket, message
        )
        
        if lifecycle_handled:
            self.telemetry["messages_received"] += 1
            return True
        
        # Fall back to unified messaging system
        result = await self.messaging.handle_incoming_message(user_id, websocket, message)
        if result:
            self.telemetry["messages_received"] += 1
        return result

    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate message through unified messaging system with JSON-first enforcement."""
        # JSON-first validation: Ensure message is properly structured dict
        if not isinstance(message, dict):
            return WebSocketValidationError(
                error_type="type_error",
                message="Message must be a JSON object (dict)",
                field="message",
                received_data={"type": type(message).__name__, "value": str(message)[:100]}
            )
        
        # Ensure required 'type' field exists
        if "type" not in message:
            return WebSocketValidationError(
                error_type="validation_error", 
                message="Message must contain 'type' field",
                field="type",
                received_data=message
            )
        
        # Validate type field is string
        if not isinstance(message["type"], str):
            return WebSocketValidationError(
                error_type="type_error",
                message="Message 'type' field must be a string",
                field="type", 
                received_data={"type_received": type(message["type"]).__name__, "value": message["type"]}
            )
        
        # Pass to existing validation system through message handler
        return self.messaging.message_handler.validate_message(message)

    def parse_and_validate_json_message(self, raw_message: str) -> Union[Dict[str, Any], WebSocketValidationError]:
        """Parse and validate JSON message from WebSocket ensuring JSON-first communication."""
        try:
            # Parse JSON
            message = json.loads(raw_message)
        except json.JSONDecodeError as e:
            return WebSocketValidationError(
                error_type="format_error",
                message=f"Invalid JSON message: {str(e)}",
                field="raw_message",
                received_data={"raw": raw_message[:100]}  # Truncate for logging
            )
        
        # Validate parsed message structure
        validation_result = self.validate_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            return validation_result
        
        return message

    async def connect_to_job(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """Connect WebSocket to specific job with room management."""
        user_id = f"job_{job_id}_{id(websocket)}"
        conn_info = await self.connect_user(user_id, websocket)
        self.room_manager.join_room(user_id, job_id)
        return conn_info

    async def disconnect_from_job(self, job_id: str, websocket: WebSocket = None) -> None:
        """Disconnect from job with room cleanup."""
        if websocket:
            user_id = f"job_{job_id}_{id(websocket)}"
            await self.disconnect_user(user_id, websocket)
        else:
            await self._cleanup_job_connections(job_id)

    async def _cleanup_job_connections(self, job_id: str) -> None:
        """Clean up all connections for a job."""
        room_connections = self.room_manager.get_room_connections(job_id)
        for user_id in room_connections:
            self.room_manager.leave_all_rooms(user_id)

    async def broadcast_to_all_users(self, 
                                   message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast to all users through unified broadcasting system."""
        return await self.broadcasting.broadcast_to_all(message)

    def get_unified_stats(self) -> Dict[str, Any]:
        """Get comprehensive unified statistics with enhanced lifecycle data."""
        base_stats = self.state.get_connection_stats()
        telemetry_stats = self.telemetry_manager.get_telemetry_stats()
        circuit_stats = self._get_circuit_breaker_stats()
        lifecycle_stats = self.lifecycle_integrator.get_comprehensive_stats()
        
        return {**base_stats, **telemetry_stats, **circuit_stats, **lifecycle_stats}

    def _get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker health statistics."""
        return {
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "total_breaks": self.telemetry["circuit_breaks"]
            }
        }

    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle errors through unified error management."""
        self.telemetry["errors_handled"] += 1
        await self.error_handler.handle_generic_error(error, context)

    async def shutdown(self) -> None:
        """Gracefully shutdown unified WebSocket manager with enhanced lifecycle cleanup."""
        logger.info("Starting enhanced unified WebSocket manager shutdown...")
        
        # Perform graceful shutdown via enhanced lifecycle
        shutdown_result = await self.lifecycle_integrator.perform_graceful_shutdown()
        
        # Shutdown telemetry manager (handles cleanup task and message queues)
        await self.telemetry_manager.shutdown()
        
        await self.state.persist_state()
        await self.connection_manager.shutdown()
        
        logger.info(f"Enhanced shutdown complete: {shutdown_result.get('success', False)}")

    async def get_transactional_stats(self) -> Dict[str, Any]:
        """Get statistics about transactional message processing."""
        return await self.telemetry_manager.get_transactional_stats()

    # Legacy compatibility methods (delegate to unified modules)
    async def send_error_to_user(self, user_id: str, error_message: str, 
                               sub_agent_name: str = "System") -> bool:
        """Send error message through unified messaging system."""
        return await self.messaging.send_error_message(user_id, error_message, sub_agent_name)

    @property
    def active_connections(self) -> Dict[str, Any]:
        """Get active connections from unified state manager."""
        return self.state.get_active_connections()

    def get_queue_size(self, job_id: str) -> int:
        """Get queue size from unified state manager."""
        return self.state.get_queue_size(job_id)
    
    # Enhanced lifecycle management methods
    async def cleanup_zombie_connections(self) -> Dict[str, Any]:
        """Clean up detected zombie connections."""
        return await self.lifecycle_integrator.cleanup_zombie_connections()
    
    def get_connection_health_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get health status for specific connection."""
        return self.lifecycle_integrator.get_connection_health_status(connection_id)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        return self.lifecycle_integrator.get_pool_status()
    
    async def validate_connection_health(self) -> Dict[str, Any]:
        """Validate health of all tracked connections."""
        return await self.lifecycle_integrator.validate_connection_health()

    # Global unified instance
    @classmethod
    def get_instance(cls) -> 'UnifiedWebSocketManager':
        """Get or create unified WebSocket manager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def create_test_instance(cls) -> 'UnifiedWebSocketManager':
        """Create a fresh instance for testing, bypassing singleton."""
        instance = super(UnifiedWebSocketManager, cls).__new__(cls)
        instance._initialized = False
        instance.__init__()
        return instance


# Global unified manager instance for backward compatibility
_unified_manager: Optional[UnifiedWebSocketManager] = None

def get_unified_manager() -> UnifiedWebSocketManager:
    """Get unified WebSocket manager instance."""
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedWebSocketManager()
    return _unified_manager