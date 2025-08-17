"""Agent Error Handler Module.

Central error handling class for agent operations.
Manages error processing, recovery, and statistics.
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Awaitable, List, Union, Any

from app.logging_config import central_logger
from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory
from app.schemas.shared_types import ErrorContext
from app.core.exceptions_agent import AgentError
from .error_recovery_strategy import ErrorRecoveryStrategy

logger = central_logger.get_logger(__name__)


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
        return await self._attempt_error_recovery(
            agent_error, context, fallback_operation
        )
    
    def _process_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Process and log error for recovery."""
        agent_error = self._convert_to_agent_error(error, context)
        self._log_error(agent_error)
        self._store_error(agent_error)
        return agent_error
    
    async def _attempt_error_recovery(
        self, 
        agent_error: AgentError, 
        context: ErrorContext, 
        fallback_operation
    ) -> Any:
        """Attempt recovery through retry or fallback."""
        if self._should_retry_operation(agent_error, context):
            return await self._retry_with_delay(agent_error, context)
        return await self._try_fallback_or_raise(
            agent_error, context, fallback_operation
        )
    
    async def _try_fallback_or_raise(
        self, 
        agent_error: AgentError, 
        context: ErrorContext, 
        fallback_operation
    ) -> Any:
        """Try fallback operation or raise error."""
        if fallback_operation:
            return await self._execute_fallback(fallback_operation, context)
        raise agent_error
    
    async def _execute_fallback(
        self, 
        fallback_operation, 
        context: ErrorContext
    ) -> Any:
        """Execute fallback operation with error handling."""
        try:
            logger.info(f"Using fallback operation for {context.operation_name}")
            return await fallback_operation()
        except Exception as fallback_error:
            logger.error(f"Fallback operation failed: {fallback_error}")
            raise
    
    def _convert_to_agent_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> AgentError:
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
        
        severity_checks = [
            ('validation', ErrorSeverity.HIGH),
            ('websocket', ErrorSeverity.LOW),
            ('memory', ErrorSeverity.CRITICAL)
        ]
        
        for check, severity in severity_checks:
            if check in error_type_lower:
                return severity
        
        return ErrorSeverity.MEDIUM
    
    def _is_error_recoverable(self, category: ErrorCategory) -> bool:
        """Determine if error is recoverable based on category."""
        non_recoverable = [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]
        return category not in non_recoverable

    def _log_error(self, error: AgentError) -> None:
        """Log error with appropriate level."""
        context = error.context
        log_message = f"{context.agent_name}.{context.operation_name}: {error.message}"
        
        log_levels = [
            (ErrorSeverity.CRITICAL, logger.critical),
            (ErrorSeverity.HIGH, logger.error),
            (ErrorSeverity.MEDIUM, logger.warning)
        ]
        
        for severity, log_func in log_levels:
            if error.severity == severity:
                log_func(log_message)
                return
        
        logger.info(log_message)
    
    def _store_error(self, error: AgentError) -> None:
        """Store error in history."""
        self.error_history.append(error)
        
        # Keep history size manageable
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _should_retry_operation(
        self, 
        error: AgentError, 
        context: ErrorContext
    ) -> bool:
        """Determine if operation should be retried."""
        if context.retry_count >= context.max_retries:
            return False
        
        return self.recovery_strategy.should_retry(error)
    
    async def _retry_with_delay(
        self, 
        error: AgentError, 
        context: ErrorContext
    ) -> None:
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
        self, 
        recent_errors: List[AgentError], 
        category_counts: Dict, 
        severity_counts: Dict
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