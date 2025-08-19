"""WebSocket Error Recovery Handler

Provides comprehensive error handling and recovery mechanisms for WebSocket connections,
ensuring reliable agent startup and communication continuity.

Business Value: Prevents agent failures worth $100K+ MRR through robust error recovery.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone

from app.logging_config import central_logger
from app.websocket.connection_info import ConnectionInfo, ConnectionState
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class ErrorType(Enum):
    """Types of WebSocket errors for categorized handling."""
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"
    PROTOCOL_ERROR = "protocol_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AGENT_ERROR = "agent_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for WebSocket errors."""
    error_type: ErrorType
    original_error: Exception
    connection_id: str
    user_id: str
    timestamp: datetime
    retry_count: int = 0
    recovery_attempted: bool = False
    agent_state: Optional[Dict[str, Any]] = None


class WebSocketErrorRecoveryHandler:
    """Handles WebSocket errors with recovery strategies."""
    
    def __init__(self):
        self.error_stats = self._initialize_error_stats()
        self.recovery_strategies = self._setup_recovery_strategies()
        self.max_recovery_attempts = 3
        self.recovery_window = 300  # 5 minutes
        
    def _initialize_error_stats(self) -> Dict[str, int]:
        """Initialize error statistics tracking."""
        return {
            "total_errors": 0,
            "authentication_errors": 0,
            "network_errors": 0,
            "protocol_errors": 0,
            "timeout_errors": 0,
            "rate_limit_errors": 0,
            "agent_errors": 0,
            "unknown_errors": 0,
            "recovery_successes": 0,
            "recovery_failures": 0
        }
        
    def _setup_recovery_strategies(self) -> Dict[ErrorType, Callable]:
        """Setup recovery strategies for different error types."""
        return {
            ErrorType.AUTHENTICATION_ERROR: self._handle_auth_error_recovery,
            ErrorType.NETWORK_ERROR: self._handle_network_error_recovery,
            ErrorType.PROTOCOL_ERROR: self._handle_protocol_error_recovery,
            ErrorType.TIMEOUT_ERROR: self._handle_timeout_error_recovery,
            ErrorType.RATE_LIMIT_ERROR: self._handle_rate_limit_recovery,
            ErrorType.AGENT_ERROR: self._handle_agent_error_recovery,
            ErrorType.UNKNOWN_ERROR: self._handle_unknown_error_recovery
        }
        
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error type for appropriate recovery strategy."""
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in ['auth', 'token', 'unauthorized']):
            return ErrorType.AUTHENTICATION_ERROR
        elif any(keyword in error_message for keyword in ['network', 'connection', 'socket']):
            return ErrorType.NETWORK_ERROR
        elif any(keyword in error_message for keyword in ['protocol', 'websocket', 'handshake']):
            return ErrorType.PROTOCOL_ERROR
        elif any(keyword in error_message for keyword in ['timeout', 'time out', 'deadline']):
            return ErrorType.TIMEOUT_ERROR
        elif any(keyword in error_message for keyword in ['rate limit', 'too many requests']):
            return ErrorType.RATE_LIMIT_ERROR
        elif any(keyword in error_message for keyword in ['agent', 'llm', 'model']):
            return ErrorType.AGENT_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
            
    async def handle_error(self, error: Exception, conn_info: ConnectionInfo,
                         agent_state: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Handle WebSocket error with appropriate recovery strategy."""
        error_type = self.classify_error(error)
        self._update_error_stats(error_type)
        
        error_context = ErrorContext(
            error_type=error_type,
            original_error=error,
            connection_id=conn_info.connection_id,
            user_id=conn_info.user_id,
            timestamp=datetime.now(timezone.utc),
            agent_state=agent_state
        )
        
        logger.error(f"WebSocket error for {conn_info.user_id}: {error_type.value} - {error}")
        
        recovery_strategy = self.recovery_strategies.get(error_type)
        if recovery_strategy:
            return await recovery_strategy(error_context)
        
        return None
        
    def _update_error_stats(self, error_type: ErrorType) -> None:
        """Update error statistics."""
        self.error_stats["total_errors"] += 1
        
        stat_key = f"{error_type.value}s"
        if stat_key in self.error_stats:
            self.error_stats[stat_key] += 1
            
    async def _handle_auth_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle authentication error recovery."""
        logger.info(f"Attempting auth error recovery for {context.user_id}")
        
        # For auth errors, return None to force re-authentication
        # The client should reconnect with a fresh token
        await self._notify_client_auth_required(context)
        return None
        
    async def _handle_network_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle network error recovery."""
        logger.info(f"Attempting network error recovery for {context.user_id}")
        
        if context.retry_count < self.max_recovery_attempts:
            # Network errors are good candidates for reconnection
            from app.websocket.reconnection_handler import get_reconnection_handler
            
            reconnection_handler = get_reconnection_handler()
            # Create a mock connection info for reconnection preparation
            conn_info = ConnectionInfo(
                websocket=None,  # Will be provided during reconnection
                user_id=context.user_id,
                connection_id=context.connection_id
            )
            
            return await reconnection_handler.prepare_for_reconnection(
                conn_info, context.agent_state
            )
            
        return None
        
    async def _handle_protocol_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle WebSocket protocol error recovery."""
        logger.info(f"Attempting protocol error recovery for {context.user_id}")
        
        # Protocol errors usually require reconnection
        await self._log_protocol_error_details(context)
        return await self._handle_network_error_recovery(context)
        
    async def _handle_timeout_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle timeout error recovery."""
        logger.info(f"Attempting timeout error recovery for {context.user_id}")
        
        # Timeout errors can often be recovered with reconnection
        return await self._handle_network_error_recovery(context)
        
    async def _handle_rate_limit_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle rate limit error recovery."""
        logger.info(f"Handling rate limit error for {context.user_id}")
        
        # For rate limiting, delay and prepare for reconnection
        await asyncio.sleep(5)  # Wait before allowing reconnection
        return await self._handle_network_error_recovery(context)
        
    async def _handle_agent_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle agent-specific error recovery."""
        logger.info(f"Attempting agent error recovery for {context.user_id}")
        
        # Agent errors may require state cleanup and reconnection
        await self._log_agent_error_details(context)
        
        # Preserve agent state for recovery
        return await self._handle_network_error_recovery(context)
        
    async def _handle_unknown_error_recovery(self, context: ErrorContext) -> Optional[str]:
        """Handle unknown error recovery."""
        logger.warning(f"Attempting unknown error recovery for {context.user_id}")
        
        # For unknown errors, log details and attempt basic recovery
        await self._log_unknown_error_details(context)
        return await self._handle_network_error_recovery(context)
        
    async def _notify_client_auth_required(self, context: ErrorContext) -> None:
        """Notify client that re-authentication is required."""
        logger.info(f"Notifying client {context.user_id} that re-authentication is required")
        # Implementation would send appropriate error response
        
    async def _log_protocol_error_details(self, context: ErrorContext) -> None:
        """Log detailed protocol error information."""
        logger.error(f"Protocol error details for {context.user_id}: {context.original_error}")
        
    async def _log_agent_error_details(self, context: ErrorContext) -> None:
        """Log detailed agent error information."""
        logger.error(f"Agent error details for {context.user_id}: {context.original_error}")
        if context.agent_state:
            logger.debug(f"Agent state at error: {context.agent_state}")
            
    async def _log_unknown_error_details(self, context: ErrorContext) -> None:
        """Log detailed unknown error information."""
        logger.error(f"Unknown error details for {context.user_id}: {context.original_error}")
        logger.debug(f"Error type: {type(context.original_error)}")
        
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_errors = self.error_stats["total_errors"]
        recovery_rate = (self.error_stats["recovery_successes"] / total_errors 
                        if total_errors > 0 else 0.0)
        
        return {
            **self.error_stats.copy(),
            "recovery_rate": recovery_rate,
            "most_common_error": self._get_most_common_error()
        }
        
    def _get_most_common_error(self) -> str:
        """Get the most common error type."""
        error_counts = {k: v for k, v in self.error_stats.items() 
                       if k.endswith('_errors') and v > 0}
        
        if not error_counts:
            return "none"
            
        return max(error_counts, key=error_counts.get).replace('_errors', '')
        
    async def cleanup_old_error_contexts(self) -> int:
        """Clean up old error contexts (placeholder for future implementation)."""
        # This would clean up any stored error contexts older than recovery_window
        return 0
        
    def record_recovery_success(self) -> None:
        """Record a successful error recovery."""
        self.error_stats["recovery_successes"] += 1
        
    def record_recovery_failure(self) -> None:
        """Record a failed error recovery."""
        self.error_stats["recovery_failures"] += 1


# Global instance for WebSocket error recovery
_error_recovery_handler: Optional[WebSocketErrorRecoveryHandler] = None


def get_error_recovery_handler() -> WebSocketErrorRecoveryHandler:
    """Get global error recovery handler instance."""
    global _error_recovery_handler
    if _error_recovery_handler is None:
        _error_recovery_handler = WebSocketErrorRecoveryHandler()
    return _error_recovery_handler