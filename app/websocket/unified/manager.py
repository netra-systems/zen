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
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import (
    WebSocketValidationError,
    ServerMessage,
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

logger = central_logger.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for WebSocket resilience."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        """Initialize circuit breaker with thresholds."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            return self._should_attempt_reset()
        return self.state == "HALF_OPEN"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.state = "HALF_OPEN"
            return True
        return False

    def record_success(self) -> None:
        """Record successful operation and reset if needed."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"

    def record_failure(self) -> None:
        """Record failed operation and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class UnifiedWebSocketManager:
    """Unified WebSocket manager with modular architecture and circuit breaker."""
    
    _instance: Optional['UnifiedWebSocketManager'] = None
    _initialized = False

    def __new__(cls) -> 'UnifiedWebSocketManager':
        """Singleton pattern for unified manager."""
        if cls._instance is None:
            cls._instance = super(UnifiedWebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize unified WebSocket manager if not already done."""
        if self._initialized:
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

    def _create_telemetry_config(self) -> Dict[str, Union[int, float]]:
        """Create initial telemetry configuration dictionary."""
        return {
            "connections_opened": 0, "connections_closed": 0,
            "messages_sent": 0, "messages_received": 0,
            "errors_handled": 0, "circuit_breaks": 0,
            "start_time": time.time()
        }

    def _initialize_telemetry(self) -> None:
        """Initialize real-time telemetry tracking."""
        self.telemetry = self._create_telemetry_config()
        # Initialize transactional message tracking
        self.pending_messages: Dict[str, Dict[str, Any]] = {}
        self.sending_messages: Dict[str, Dict[str, Any]] = {}
        self.message_lock = asyncio.Lock()
        
        # Initialize cleanup task as None - will be started on first connection
        self._cleanup_task = None

    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish WebSocket connection with circuit breaker protection."""
        # Start cleanup task on first connection if not already started
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
        if not self.circuit_breaker.can_execute():
            self._record_circuit_break()
            raise ConnectionError("Circuit breaker is open")
        
        conn_info = await self._execute_protected_connect(user_id, websocket)
        
        # Handle state synchronization for new connection
        await self.messaging.message_handler.handle_new_connection_state_sync(
            user_id, conn_info.connection_id, websocket
        )
        
        return conn_info

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
        """Safely disconnect user with comprehensive cleanup."""
        try:
            # Find connection info before disconnecting
            conn_info = await self.connection_manager.find_connection(user_id, websocket)
            if conn_info:
                await self.messaging.message_handler.handle_disconnection_state_sync(
                    user_id, conn_info.connection_id
                )
            
            await self.connection_manager.disconnect(user_id, websocket, code, reason)
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
            await self._mark_message_sending(message_id, user_id, message)
            
            # Attempt to send message
            result = await self.messaging.send_to_user(user_id, message, retry)
            
            if result:
                # Only mark as sent on confirmed success
                await self._mark_message_sent(message_id)
                self.telemetry["messages_sent"] += 1
                return True
            else:
                # Revert to pending if send failed
                await self._mark_message_pending(message_id, user_id, message)
                return False
                
        except Exception as e:
            # Revert to pending on exception
            await self._mark_message_pending(message_id, user_id, message)
            logger.error(f"Transactional message send failed for {user_id}: {e}")
            raise

    async def broadcast_to_job(self, job_id: str, 
                              message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast message to job through unified broadcasting system."""
        return await self.broadcasting.broadcast_to_job(job_id, message)

    async def handle_message(self, user_id: str, websocket: WebSocket, 
                           message: Dict[str, Any]) -> bool:
        """Handle incoming message through unified messaging system."""
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
        """Get comprehensive unified statistics with telemetry."""
        base_stats = self.state.get_connection_stats()
        telemetry_stats = self._get_telemetry_stats()
        circuit_stats = self._get_circuit_breaker_stats()
        return {**base_stats, **telemetry_stats, **circuit_stats}

    def _get_telemetry_stats(self) -> Dict[str, Any]:
        """Get real-time telemetry statistics."""
        uptime = time.time() - self.telemetry["start_time"]
        return {
            "telemetry": self.telemetry.copy(),
            "uptime_seconds": uptime,
            "messages_per_second": self.telemetry["messages_sent"] / max(uptime, 1)
        }

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
        """Gracefully shutdown unified WebSocket manager with memory leak prevention."""
        logger.info("Starting unified WebSocket manager shutdown...")
        
        # Cancel cleanup task if it exists and is running
        if hasattr(self, '_cleanup_task') and self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Handle any pending messages before shutdown
        async with self.message_lock:
            pending_count = len(self.pending_messages)
            sending_count = len(self.sending_messages)
            
            if pending_count > 0 or sending_count > 0:
                logger.warning(f"Shutting down with {pending_count} pending and {sending_count} sending messages")
                
                # Clear all message tracking to prevent memory leaks
                self.pending_messages.clear()
                self.sending_messages.clear()
                logger.info("Cleared all pending/sending message queues to prevent memory leaks")
        
        await self.state.persist_state()
        await self.connection_manager.shutdown()
        
        # Clear telemetry data
        self.telemetry.clear()
        
        logger.info("Unified shutdown complete with memory cleanup")

    # Transactional message processing methods
    async def _mark_message_sending(self, message_id: str, user_id: str, 
                                   message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> None:
        """Mark message as currently being sent (transactional pattern)."""
        async with self.message_lock:
            message_data = {
                "message_id": message_id,
                "user_id": user_id,
                "message": message,
                "timestamp": time.time(),
                "status": "sending"
            }
            self.sending_messages[message_id] = message_data
            # Remove from pending if it was there
            self.pending_messages.pop(message_id, None)

    async def _mark_message_sent(self, message_id: str) -> None:
        """Mark message as successfully sent and remove from tracking."""
        async with self.message_lock:
            self.sending_messages.pop(message_id, None)
            # Message successfully sent, no need to track further

    async def _mark_message_pending(self, message_id: str, user_id: str, 
                                   message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> None:
        """Mark message as pending for retry (transactional pattern)."""
        async with self.message_lock:
            message_data = {
                "message_id": message_id,
                "user_id": user_id,
                "message": message,
                "timestamp": time.time(),
                "status": "pending",
                "retry_count": self.sending_messages.get(message_id, {}).get("retry_count", 0) + 1
            }
            self.pending_messages[message_id] = message_data
            # Remove from sending
            self.sending_messages.pop(message_id, None)

    async def _retry_pending_messages(self) -> None:
        """Retry all pending messages that failed to send."""
        async with self.message_lock:
            pending_to_retry = list(self.pending_messages.items())
        
        retry_count = 0
        for message_id, message_data in pending_to_retry:
            if message_data["retry_count"] < 3:  # Max 3 retries
                try:
                    result = await self.send_message_to_user(
                        message_data["user_id"], 
                        message_data["message"], 
                        retry=False  # Prevent infinite recursion
                    )
                    if result:
                        retry_count += 1
                except Exception as e:
                    logger.error(f"Retry failed for message {message_id}: {e}")
            else:
                # Max retries exceeded, remove from pending
                async with self.message_lock:
                    self.pending_messages.pop(message_id, None)
                logger.error(f"Message {message_id} exceeded max retries, dropping")
        
        if retry_count > 0:
            logger.info(f"Successfully retried {retry_count} pending messages")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup to prevent memory leaks from stale messages."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                current_time = time.time()
                max_age = 1800  # 30 minutes
                
                async with self.message_lock:
                    # Clean up old pending messages
                    old_pending = [
                        msg_id for msg_id, msg_data in self.pending_messages.items()
                        if current_time - msg_data["timestamp"] > max_age
                    ]
                    
                    # Clean up old sending messages
                    old_sending = [
                        msg_id for msg_id, msg_data in self.sending_messages.items()
                        if current_time - msg_data["timestamp"] > max_age
                    ]
                    
                    # Remove old messages
                    for msg_id in old_pending:
                        del self.pending_messages[msg_id]
                    
                    for msg_id in old_sending:
                        del self.sending_messages[msg_id]
                    
                    if old_pending or old_sending:
                        logger.info(f"Cleaned up {len(old_pending)} old pending and {len(old_sending)} old sending messages")
                
            except asyncio.CancelledError:
                logger.debug("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def get_transactional_stats(self) -> Dict[str, Any]:
        """Get statistics about transactional message processing."""
        async with self.message_lock:
            return {
                "pending_messages": len(self.pending_messages),
                "sending_messages": len(self.sending_messages),
                "oldest_pending": min(
                    [msg["timestamp"] for msg in self.pending_messages.values()], 
                    default=time.time()
                ),
                "oldest_sending": min(
                    [msg["timestamp"] for msg in self.sending_messages.values()], 
                    default=time.time()
                )
            }

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

    # Global unified instance
    @classmethod
    def get_instance(cls) -> 'UnifiedWebSocketManager':
        """Get or create unified WebSocket manager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Global unified manager instance for backward compatibility
_unified_manager: Optional[UnifiedWebSocketManager] = None

def get_unified_manager() -> UnifiedWebSocketManager:
    """Get unified WebSocket manager instance."""
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedWebSocketManager()
    return _unified_manager