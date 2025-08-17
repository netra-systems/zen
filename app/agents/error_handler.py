"""Centralized error handling and recovery mechanisms for agents."""

import asyncio
import time
from uuid import uuid4
from typing import Dict, Optional, Callable, Awaitable, List, Union, Any
from enum import Enum
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Import ErrorSeverity and ErrorCategory from single source of truth
from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory


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


# Import DatabaseError from canonical location
from app.core.exceptions_database import DatabaseError


# Import WebSocketError from canonical location
from app.core.exceptions_websocket import WebSocketError


class ErrorRecoveryStrategy:
    """Strategy for error recovery based on error type."""
    
    # Strategy constants
    RETRY = "retry"
    ABORT = "abort"
    FALLBACK = "fallback"
    
    @staticmethod
    def get_recovery_delay(error: AgentError, attempt: int) -> float:
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
        delay = base_delay * (2 ** attempt)
        max_delay = 30.0  # Maximum 30 seconds
        
        return min(delay, max_delay)
    
    @staticmethod
    def should_retry(error: AgentError, attempt: int = 1) -> bool:
        """Determine if error should be retried based on attempt number."""
        max_attempts = 5
        if attempt >= max_attempts:
            return False
        if not error.recoverable:
            return False
        return ErrorRecoveryStrategy._check_retry_conditions(error)
    
    @staticmethod
    def get_strategy(error: AgentError) -> str:
        """Get recovery strategy for the given error."""
        if error.severity == ErrorSeverity.CRITICAL:
            return ErrorRecoveryStrategy.ABORT
        if error.category == ErrorCategory.VALIDATION:
            return ErrorRecoveryStrategy.ABORT
        if ErrorRecoveryStrategy._is_always_retryable_category(error.category):
            return ErrorRecoveryStrategy.RETRY
        return ErrorRecoveryStrategy.FALLBACK
    
    @staticmethod
    def _check_retry_conditions(error: AgentError) -> bool:
        """Check specific retry conditions for error."""
        if ErrorRecoveryStrategy._is_non_retryable_category(error.category):
            return False
        if ErrorRecoveryStrategy._is_always_retryable_category(error.category):
            return True
        return ErrorRecoveryStrategy._check_conditional_retry(error)
    
    @staticmethod
    def _is_non_retryable_category(category: ErrorCategory) -> bool:
        """Check if error category should never be retried."""
        return category == ErrorCategory.VALIDATION
    
    @staticmethod
    def _is_always_retryable_category(category: ErrorCategory) -> bool:
        """Check if error category should always be retried."""
        retryable_categories = [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.WEBSOCKET]
        return category in retryable_categories
    
    @staticmethod
    def _check_conditional_retry(error: AgentError) -> bool:
        """Check conditional retry based on severity and category."""
        if error.category in [ErrorCategory.DATABASE, ErrorCategory.PROCESSING]:
            return error.severity != ErrorSeverity.CRITICAL
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
        agent_error = self._process_error(error, context)
        return await self._attempt_error_recovery(agent_error, context, fallback_operation)
    
    def _process_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Process and log error for recovery."""
        agent_error = self._convert_to_agent_error(error, context)
        self._log_error(agent_error)
        self._store_error(agent_error)
        return agent_error
    
    async def _attempt_error_recovery(
        self, agent_error: AgentError, context: ErrorContext, fallback_operation
    ) -> Any:
        """Attempt recovery through retry or fallback."""
        if self._should_retry_operation(agent_error, context):
            return await self._retry_with_delay(agent_error, context)
        return await self._try_fallback_or_raise(agent_error, context, fallback_operation)
    
    async def _try_fallback_or_raise(
        self, agent_error: AgentError, context: ErrorContext, fallback_operation
    ) -> Any:
        """Try fallback operation or raise error."""
        if fallback_operation:
            return await self._execute_fallback(fallback_operation, context)
        raise agent_error
    
    async def _execute_fallback(self, fallback_operation, context: ErrorContext) -> Any:
        """Execute fallback operation with error handling."""
        try:
            logger.info(f"Using fallback operation for {context.operation_name}")
            return await fallback_operation()
        except Exception as fallback_error:
            logger.error(f"Fallback operation failed: {fallback_error}")
            raise
    
    def _convert_to_agent_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Convert generic exception to AgentError."""
        if isinstance(error, AgentError):
            error.context = context
            return error
        
        error_type = type(error).__name__
        category = self._determine_error_category(error_type)
        severity = self._determine_error_severity(error_type)
        
        return AgentError(
            message=str(error),
            severity=severity,
            category=category,
            context=context,
            recoverable=self._is_error_recoverable(category)
        )
    
    def _get_category_mapping(self) -> dict:
        """Get mapping of exception types to error categories."""
        return {
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
    
    def _determine_error_category(self, error_type: str) -> ErrorCategory:
        """Determine error category based on exception type."""
        category_mapping = self._get_category_mapping()
        return category_mapping.get(error_type, ErrorCategory.UNKNOWN)
    
    def _determine_error_severity(self, error_type: str) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        error_type_lower = error_type.lower()
        
        if 'validation' in error_type_lower:
            return ErrorSeverity.HIGH
        elif 'websocket' in error_type_lower:
            return ErrorSeverity.LOW
        elif 'memory' in error_type_lower:
            return ErrorSeverity.CRITICAL
        else:
            return ErrorSeverity.MEDIUM
    
    def _is_error_recoverable(self, category: ErrorCategory) -> bool:
        """Determine if error is recoverable based on category."""
        non_recoverable = [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]
        return category not in non_recoverable

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
        
        recent_errors = self._get_recent_errors()
        category_counts, severity_counts = self._count_error_types(recent_errors)
        return self._build_stats_response(recent_errors, category_counts, severity_counts)
    
    def _get_recent_errors(self) -> List[AgentError]:
        """Get errors from the last hour."""
        cutoff_time = time.time() - 3600  # Last hour
        return [e for e in self.error_history if time.time() - e.timestamp < 3600]
    
    def _count_error_types(self, errors: List[AgentError]) -> tuple:
        """Count errors by category and severity."""
        category_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        for error in errors:
            self._increment_count(category_counts, error.category.value)
            self._increment_count(severity_counts, error.severity.value)
        return category_counts, severity_counts
    
    def _increment_count(self, count_dict: Dict[str, int], key: str) -> None:
        """Increment count for a key in dictionary."""
        count_dict[key] = count_dict.get(key, 0) + 1
    
    def _build_stats_response(
        self, recent_errors: List[AgentError], category_counts: Dict, severity_counts: Dict
    ) -> Dict[str, Union[int, Dict[str, int], Dict[str, Union[str, float]]]]:
        """Build complete statistics response."""
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_categories": category_counts,
            "error_severities": severity_counts,
            "last_error": self._get_last_error_info()
        }
    
    def _get_last_error_info(self) -> Optional[Dict[str, Union[str, float]]]:
        """Get information about the last error."""
        if not self.error_history:
            return None
        last_error = self.error_history[-1]
        return {
            "message": last_error.message,
            "category": last_error.category.value,
            "severity": last_error.severity.value,
            "timestamp": last_error.timestamp
        }


# Global error handler instance
global_error_handler = AgentErrorHandler()


def handle_agent_error(operation_name: str):
    """Decorator to handle agent errors with recovery."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            context = _create_error_context(operation_name, self, kwargs)
            return await _execute_with_retry(func, self, args, kwargs, context, operation_name)
        return wrapper
    return decorator

def _create_error_context(operation_name: str, agent_instance, kwargs: dict) -> ErrorContext:
    """Create error context for operation."""
    return ErrorContext(
        trace_id=str(uuid4()),
        operation=operation_name,
        agent_name=getattr(agent_instance, 'name', 'Unknown'),
        operation_name=operation_name,
        run_id=kwargs.get('run_id', 'unknown')
    )

async def _execute_with_retry(
    func, agent_instance, args, kwargs, context: ErrorContext, operation_name: str
) -> Any:
    """Execute function with retry logic."""
    max_attempts = 3
    for attempt in range(max_attempts):
        context.retry_count = attempt
        result = await _attempt_execution(func, agent_instance, args, kwargs, context, operation_name, attempt, max_attempts)
        if result is not None:
            return result

async def _attempt_execution(
    func, agent_instance, args, kwargs, context: ErrorContext, operation_name: str, attempt: int, max_attempts: int
) -> Any:
    """Attempt single execution with error handling."""
    try:
        return await func(agent_instance, *args, **kwargs)
    except Exception as e:
        return await _handle_execution_error(e, context, operation_name, agent_instance, attempt, max_attempts)

async def _handle_execution_error(
    error: Exception, context: ErrorContext, operation_name: str, 
    agent_instance, attempt: int, max_attempts: int
) -> Any:
    """Handle execution error with retry or fallback logic."""
    if attempt == max_attempts - 1:
        return await _handle_final_attempt_error(error, context, operation_name, agent_instance)
    return await _handle_retry_attempt_error(error, context, operation_name, agent_instance, attempt)

async def _handle_final_attempt_error(
    error: Exception, context: ErrorContext, operation_name: str, agent_instance
) -> Any:
    """Handle error on final attempt."""
    fallback = getattr(agent_instance, f'_fallback_{operation_name}', None)
    return await global_error_handler.handle_error(error, context, fallback)

async def _handle_retry_attempt_error(
    error: Exception, context: ErrorContext, operation_name: str, 
    agent_instance, attempt: int
) -> Optional[Any]:
    """Handle error on retry attempt."""
    agent_error = global_error_handler._convert_to_agent_error(error, context)
    if not global_error_handler.recovery_strategy.should_retry(agent_error):
        fallback = getattr(agent_instance, f'_fallback_{operation_name}', None)
        return await global_error_handler.handle_error(error, context, fallback)
    
    delay = ErrorRecoveryStrategy.get_recovery_delay(agent_error, attempt)
    await asyncio.sleep(delay)
    return None