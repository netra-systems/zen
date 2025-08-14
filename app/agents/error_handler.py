"""Centralized error handling and recovery mechanisms for agents."""

import asyncio
import time
from uuid import uuid4
from typing import Dict, Optional, Callable, Awaitable, List, Union, Any
from enum import Enum
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Import ErrorSeverity from single source of truth
from app.core.error_codes import ErrorSeverity


class ErrorCategory(Enum):
    """Error category classification."""
    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    PROCESSING = "processing"
    WEBSOCKET = "websocket"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


# Import ErrorContext from single source of truth
from app.schemas.shared_types import ErrorContext


# Import AgentError from canonical location
from app.core.exceptions_agent import AgentError


class AgentValidationError(AgentError):
    """Error for agent input validation failures."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=False
        )


class NetworkError(AgentError):
    """Error for network-related failures."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            recoverable=True
        )


class DatabaseError(AgentError):
    """Error for database-related failures."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context,
            recoverable=True
        )


# Import WebSocketError from canonical location
from app.core.exceptions_websocket import WebSocketError


class ErrorRecoveryStrategy:
    """Strategy for error recovery based on error type."""
    
    @staticmethod
    def get_recovery_delay(error: AgentError, retry_count: int) -> float:
        """Calculate recovery delay based on error type and retry count."""
        base_delays = {
            ErrorCategory.NETWORK: 2.0,
            ErrorCategory.DATABASE: 1.0,
            ErrorCategory.WEBSOCKET: 0.5,
            ErrorCategory.TIMEOUT: 5.0,
            ErrorCategory.RESOURCE: 3.0,
            ErrorCategory.PROCESSING: 1.0,
            ErrorCategory.UNKNOWN: 2.0
        }
        
        base_delay = base_delays.get(error.category, 2.0)
        # Exponential backoff with jitter
        delay = base_delay * (2 ** retry_count)
        max_delay = 30.0  # Maximum 30 seconds
        
        return min(delay, max_delay)
    
    @staticmethod
    def should_retry(error: AgentError) -> bool:
        """Determine if error should be retried."""
        if not error.recoverable:
            return False
        
        # Never retry validation errors
        if error.category == ErrorCategory.VALIDATION:
            return False
        
        # Always retry network and timeout errors
        if error.category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return True
        
        # Retry database and processing errors based on severity
        if error.category in [ErrorCategory.DATABASE, ErrorCategory.PROCESSING]:
            return error.severity != ErrorSeverity.CRITICAL
        
        # Retry WebSocket errors (they're usually temporary)
        if error.category == ErrorCategory.WEBSOCKET:
            return True
        
        # Default to retry for medium or low severity
        return error.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]


class AgentErrorHandler:
    """Centralized error handler for all agent operations."""
    
    def __init__(self):
        self.error_history: List[AgentError] = []
        self.recovery_strategy = ErrorRecoveryStrategy()
        self.max_history = 100
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        fallback_operation: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> Any:
        """Handle error with appropriate recovery strategy."""
        
        # Convert to AgentError if needed
        agent_error = self._convert_to_agent_error(error, context)
        
        # Log error
        self._log_error(agent_error)
        
        # Store in history
        self._store_error(agent_error)
        
        # Determine if we should retry
        if self._should_retry_operation(agent_error, context):
            return await self._retry_with_delay(agent_error, context)
        
        # Try fallback if available
        if fallback_operation:
            try:
                logger.info(f"Using fallback operation for {context.operation_name}")
                return await fallback_operation()
            except Exception as fallback_error:
                logger.error(f"Fallback operation failed: {fallback_error}")
        
        # If no recovery possible, re-raise as AgentError
        raise agent_error
    
    def _convert_to_agent_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Convert generic exception to AgentError."""
        if isinstance(error, AgentError):
            error.context = context
            return error
        
        # Map common exception types to categories
        category_mapping = {
            'ValidationError': ErrorCategory.VALIDATION,
            'pydantic.ValidationError': ErrorCategory.VALIDATION,
            'ConnectionError': ErrorCategory.NETWORK,
            'TimeoutError': ErrorCategory.TIMEOUT,
            'asyncio.TimeoutError': ErrorCategory.TIMEOUT,
            'WebSocketDisconnect': ErrorCategory.WEBSOCKET,
            'DatabaseError': ErrorCategory.DATABASE,
            'MemoryError': ErrorCategory.RESOURCE,
            'FileNotFoundError': ErrorCategory.CONFIGURATION,
        }
        
        error_type = type(error).__name__
        category = category_mapping.get(error_type, ErrorCategory.UNKNOWN)
        
        # Determine severity based on error type
        severity = ErrorSeverity.MEDIUM
        if 'validation' in error_type.lower():
            severity = ErrorSeverity.HIGH
        elif 'websocket' in error_type.lower():
            severity = ErrorSeverity.LOW
        elif 'memory' in error_type.lower():
            severity = ErrorSeverity.CRITICAL
        
        return AgentError(
            message=str(error),
            severity=severity,
            category=category,
            context=context,
            recoverable=category not in [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]
        )
    
    def _log_error(self, error: AgentError) -> None:
        """Log error with appropriate level."""
        context = error.context
        log_message = f"{context.agent_name}.{context.operation_name}: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _store_error(self, error: AgentError) -> None:
        """Store error in history."""
        self.error_history.append(error)
        
        # Keep history size manageable
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _should_retry_operation(self, error: AgentError, context: ErrorContext) -> bool:
        """Determine if operation should be retried."""
        if context.retry_count >= context.max_retries:
            return False
        
        return self.recovery_strategy.should_retry(error)
    
    async def _retry_with_delay(self, error: AgentError, context: ErrorContext) -> None:
        """Retry operation after appropriate delay."""
        delay = self.recovery_strategy.get_recovery_delay(error, context.retry_count)
        
        logger.info(
            f"Retrying {context.operation_name} in {delay:.2f}s "
            f"(attempt {context.retry_count + 1}/{context.max_retries})"
        )
        
        await asyncio.sleep(delay)
        raise AgentError(
            message=f"Retry required for {context.operation_name}",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.PROCESSING,
            context=context,
            recoverable=True
        )
    
    def get_error_stats(self) -> Dict[str, Union[int, Dict[str, int], List[Dict[str, Union[str, float]]]]]:
        """Get error statistics."""
        if not self.error_history:
            return {"total_errors": 0}
        
        recent_errors = [
            e for e in self.error_history 
            if time.time() - e.timestamp < 3600  # Last hour
        ]
        
        category_counts: Dict[str, int] = {}
        severity_counts = {}
        
        for error in recent_errors:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_categories": category_counts,
            "error_severities": severity_counts,
            "last_error": {
                "message": self.error_history[-1].message,
                "category": self.error_history[-1].category.value,
                "severity": self.error_history[-1].severity.value,
                "timestamp": self.error_history[-1].timestamp
            } if self.error_history else None
        }


# Global error handler instance
global_error_handler = AgentErrorHandler()


def handle_agent_error(operation_name: str):
    """Decorator to handle agent errors with recovery."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            context = ErrorContext(
                trace_id=str(uuid4()),
                operation=operation_name,
                agent_name=getattr(self, 'name', 'Unknown'),
                operation_name=operation_name,
                run_id=kwargs.get('run_id', 'unknown')
            )
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    context.retry_count = attempt
                    return await func(self, *args, **kwargs)
                    
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt, handle error and potentially re-raise
                        fallback = getattr(self, f'_fallback_{operation_name}', None)
                        return await global_error_handler.handle_error(e, context, fallback)
                    
                    # Convert and check if retryable
                    agent_error = global_error_handler._convert_to_agent_error(e, context)
                    if not global_error_handler.recovery_strategy.should_retry(agent_error):
                        # Non-retryable error, handle immediately
                        fallback = getattr(self, f'_fallback_{operation_name}', None)
                        return await global_error_handler.handle_error(e, context, fallback)
                    
                    # Wait before retry
                    delay = ErrorRecoveryStrategy.get_recovery_delay(agent_error, attempt)
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator