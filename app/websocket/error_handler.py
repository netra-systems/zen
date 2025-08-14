"""Core WebSocket error handling functionality.

Provides centralized error handling, logging, and recovery mechanisms.
"""

from typing import Dict, Any, Optional
import asyncio
import time

from app.logging_config import central_logger
from .connection import ConnectionInfo
from .error_types import WebSocketError, ErrorSeverity

logger = central_logger.get_logger(__name__)


class ErrorHandler:
    """Handles WebSocket errors with logging, tracking, and recovery."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_history: Dict[str, WebSocketError] = {}
        self.error_patterns: Dict[str, int] = {}  # Track common error patterns
        self.connection_errors: Dict[str, int] = {}  # Track errors per connection
        self.recovery_timestamps: Dict[str, float] = {}  # Track last recovery attempt time
        self.recovery_backoff: Dict[str, float] = {}  # Track backoff delays
        self._stats = {
            "total_errors": 0,
            "critical_errors": 0,
            "recovered_errors": 0,
            "connection_errors": 0,
            "validation_errors": 0,
            "rate_limit_errors": 0
        }
    
    async def handle_error(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Handle a WebSocket error with appropriate logging and recovery.
        
        Args:
            error: Error to handle
            conn_info: Connection info if available
            
        Returns:
            True if error was handled and recovered from
        """
        # Store error in history
        self.error_history[error.error_id] = error
        
        # Update statistics
        self._stats["total_errors"] += 1
        if error.severity == ErrorSeverity.CRITICAL:
            self._stats["critical_errors"] += 1
        
        # Update connection-specific error tracking
        if conn_info:
            error.connection_id = conn_info.connection_id
            error.user_id = conn_info.user_id
            conn_info.error_count += 1
            self.connection_errors[conn_info.connection_id] = self.connection_errors.get(conn_info.connection_id, 0) + 1
        
        # Track error patterns
        error_pattern = f"{error.error_type}:{error.message[:50]}"
        self.error_patterns[error_pattern] = self.error_patterns.get(error_pattern, 0) + 1
        
        # Log error with appropriate level
        self._log_error(error, conn_info)
        
        # Attempt recovery if error is recoverable
        recovered = False
        if error.recoverable and error.retry_count < error.max_retries:
            recovered = await self._attempt_recovery(error, conn_info)
            if recovered:
                self._stats["recovered_errors"] += 1
        
        return recovered
    
    async def handle_connection_error(self, conn_info: ConnectionInfo, error_message: str, 
                                    error_type: str = "connection_error", 
                                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> WebSocketError:
        """Handle a connection-specific error.
        
        Args:
            conn_info: Connection that experienced the error
            error_message: Error message
            error_type: Type of error
            severity: Error severity
            
        Returns:
            The created WebSocketError
        """
        error = WebSocketError(
            connection_id=conn_info.connection_id,
            user_id=conn_info.user_id,
            error_type=error_type,
            message=error_message,
            severity=severity,
            context={
                "connected_at": conn_info.connected_at.isoformat(),
                "message_count": conn_info.message_count,
                "error_count": conn_info.error_count,
                "last_ping": conn_info.last_ping.isoformat()
            }
        )
        
        self._stats["connection_errors"] += 1
        await self.handle_error(error, conn_info)
        return error
    
    async def handle_validation_error(self, user_id: str, message: str, 
                                    validation_details: Dict[str, Any]) -> WebSocketError:
        """Handle a message validation error.
        
        Args:
            user_id: User who sent the invalid message
            message: Error message
            validation_details: Details about the validation failure
            
        Returns:
            The created WebSocketError
        """
        error = WebSocketError(
            user_id=user_id,
            error_type="validation_error",
            message=message,
            severity=ErrorSeverity.LOW,
            context=validation_details,
            recoverable=False  # Validation errors are not recoverable
        )
        
        self._stats["validation_errors"] += 1
        await self.handle_error(error)
        return error
    
    async def handle_rate_limit_error(self, conn_info: ConnectionInfo, limit_info: Dict[str, Any]) -> WebSocketError:
        """Handle a rate limiting error.
        
        Args:
            conn_info: Connection that was rate limited
            limit_info: Rate limit information
            
        Returns:
            The created WebSocketError
        """
        error = WebSocketError(
            connection_id=conn_info.connection_id,
            user_id=conn_info.user_id,
            error_type="rate_limit_error",
            message="Rate limit exceeded",
            severity=ErrorSeverity.LOW,
            context=limit_info,
            recoverable=True
        )
        
        self._stats["rate_limit_errors"] += 1
        await self.handle_error(error, conn_info)
        return error
    
    def _log_error(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None):
        """Log error with appropriate level and context."""
        log_context = {
            "error_id": error.error_id,
            "error_type": error.error_type,
            "severity": error.severity.value,
            "user_id": error.user_id,
            "connection_id": error.connection_id,
            "recoverable": error.recoverable,
            "retry_count": error.retry_count
        }
        
        if conn_info:
            from datetime import datetime, timezone
            log_context.update({
                "message_count": conn_info.message_count,
                "error_count": conn_info.error_count,
                "connection_duration": (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
            })
        
        log_message = f"WebSocket error: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_context)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_context)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_context)
        else:
            logger.info(log_message, extra=log_context)
    
    async def _attempt_recovery(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from an error with rate limiting."""
        error.retry_count += 1
        
        # Implement rate limiting with exponential backoff
        recovery_key = f"{error.error_type}:{error.connection_id or error.user_id}"
        current_time = time.time()
        
        # Check if we're attempting recovery too soon
        if recovery_key in self.recovery_timestamps:
            last_attempt = self.recovery_timestamps[recovery_key]
            backoff_delay = self.recovery_backoff.get(recovery_key, 1.0)
            
            time_since_last = current_time - last_attempt
            if time_since_last < backoff_delay:
                logger.debug(f"Recovery rate limited for {recovery_key}, waiting {backoff_delay - time_since_last:.1f}s")
                return False
        
        # Update recovery tracking
        self.recovery_timestamps[recovery_key] = current_time
        
        # Calculate exponential backoff (max 60 seconds)
        current_backoff = self.recovery_backoff.get(recovery_key, 1.0)
        next_backoff = min(current_backoff * 2, 60.0)
        self.recovery_backoff[recovery_key] = next_backoff
        
        try:
            # Add delay before recovery attempt
            await asyncio.sleep(min(error.retry_count * 0.5, 5.0))
            
            # Implement recovery strategies based on error type
            if error.error_type == "connection_error":
                return await self._recover_connection_error(error, conn_info)
            elif error.error_type == "rate_limit_error":
                return await self._recover_rate_limit_error(error, conn_info)
            elif error.error_type == "heartbeat_error":
                return await self._recover_heartbeat_error(error, conn_info)
            else:
                # Generic recovery with delay
                logger.info(f"Generic recovery attempted for error {error.error_id} after {current_backoff:.1f}s backoff")
                return False  # Don't auto-recover unknown errors
                
        except Exception as recovery_error:
            logger.error(f"Error during recovery attempt for {error.error_id}: {recovery_error}")
            return False
    
    async def _recover_connection_error(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a connection error."""
        if not conn_info:
            return False
        
        # For connection errors, we typically can't recover the same connection
        # The connection manager should handle cleanup
        logger.info(f"Connection error recovery: marking connection {conn_info.connection_id} for cleanup")
        return False  # Connection needs to be cleaned up
    
    async def _recover_rate_limit_error(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a rate limit error."""
        # For rate limit errors, recovery means waiting and then allowing normal operation
        logger.info(f"Rate limit error recovery: connection {error.connection_id} can resume after window")
        return True
    
    async def _recover_heartbeat_error(self, error: WebSocketError, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a heartbeat error."""
        if not conn_info:
            return False
        
        # For heartbeat errors, check if connection is truly dead
        from starlette.websockets import WebSocketState
        if conn_info.websocket.client_state != WebSocketState.CONNECTED:
            logger.info(f"Heartbeat error: connection {conn_info.connection_id} is closed, cannot recover")
            return False
        
        logger.info(f"Heartbeat error recovery: connection {conn_info.connection_id} may continue")
        return True
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": self._stats["total_errors"],
            "critical_errors": self._stats["critical_errors"],
            "recovered_errors": self._stats["recovered_errors"],
            "connection_errors": self._stats["connection_errors"],
            "validation_errors": self._stats["validation_errors"],
            "rate_limit_errors": self._stats["rate_limit_errors"],
            "recovery_rate": self._stats["recovered_errors"] / max(1, self._stats["total_errors"]),
            "top_error_patterns": dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def get_connection_error_count(self, connection_id: str) -> int:
        """Get error count for a specific connection."""
        return self.connection_errors.get(connection_id, 0)
    
    def is_connection_problematic(self, connection_id: str, threshold: int = 5) -> bool:
        """Check if a connection has too many errors."""
        return self.get_connection_error_count(connection_id) >= threshold
    
    def cleanup_old_errors(self, max_age_hours: int = 24):
        """Clean up old error records."""
        from datetime import datetime, timezone
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        errors_to_remove = []
        for error_id, error in self.error_history.items():
            if error.timestamp.timestamp() < cutoff_time:
                errors_to_remove.append(error_id)
        
        for error_id in errors_to_remove:
            del self.error_history[error_id]
        
        # Clean up old recovery tracking
        recovery_keys_to_remove = []
        for key, timestamp in self.recovery_timestamps.items():
            if timestamp < cutoff_time:
                recovery_keys_to_remove.append(key)
        
        for key in recovery_keys_to_remove:
            del self.recovery_timestamps[key]
            if key in self.recovery_backoff:
                del self.recovery_backoff[key]
        
        if errors_to_remove or recovery_keys_to_remove:
            logger.info(f"Cleaned up {len(errors_to_remove)} old error records and {len(recovery_keys_to_remove)} recovery trackers")


# Default error handler instance
default_error_handler = ErrorHandler()