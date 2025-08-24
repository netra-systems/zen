"""
Unified Exception Handling Framework - Single source of truth for exception patterns.
Eliminates 1000+ duplicate exception handling patterns across the codebase.

This module provides standardized exception handling, logging, and recovery patterns
that should be used throughout the entire system.
"""
from typing import Optional, Dict, Any, Callable, Type, Union, List
from functools import wraps
import traceback
import sys
import asyncio
from datetime import datetime, UTC
from enum import Enum

from shared.logging import get_logger


class ErrorSeverity(Enum):
    """Standard error severity levels."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Standard error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    EXTERNAL_API = "external_api"
    LLM_PROVIDER = "llm_provider"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class NetraBaseException(Exception):
    """
    Base exception class for all Netra-specific exceptions.
    
    This replaces all custom exception classes and provides
    standardized error handling capabilities.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now(UTC)
        
    def _generate_error_code(self) -> str:
        """Generate a unique error code."""
        import uuid
        return f"ERR-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class AuthenticationError(NetraBaseException):
    """Authentication-related errors."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHENTICATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class AuthorizationError(NetraBaseException):
    """Authorization-related errors."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHORIZATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ValidationError(NetraBaseException):
    """Data validation errors."""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class DatabaseError(NetraBaseException):
    """Database operation errors."""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        kwargs.setdefault('category', ErrorCategory.DATABASE)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class NetworkError(NetraBaseException):
    """Network-related errors."""
    
    def __init__(self, message: str = "Network operation failed", **kwargs):
        kwargs.setdefault('category', ErrorCategory.NETWORK)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class LLMProviderError(NetraBaseException):
    """LLM provider API errors."""
    
    def __init__(self, message: str = "LLM provider operation failed", **kwargs):
        kwargs.setdefault('category', ErrorCategory.LLM_PROVIDER)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ConfigurationError(NetraBaseException):
    """Configuration-related errors."""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONFIGURATION)
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class UnifiedExceptionHandler:
    """
    Unified exception handler that provides standardized error handling,
    logging, and recovery patterns across the entire system.
    """
    
    def __init__(self, logger_name: Optional[str] = None):
        self.logger = get_logger(logger_name or __name__)
        self.error_metrics: Dict[str, int] = {}
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}
    
    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        should_reraise: bool = True,
        custom_message: Optional[str] = None
    ) -> Optional[NetraBaseException]:
        """
        Handle an exception with unified logging and classification.
        
        Args:
            exception: The exception to handle
            context: Additional context information
            should_reraise: Whether to reraise the exception
            custom_message: Custom error message override
            
        Returns:
            NetraBaseException if not reraised
        """
        # Convert to NetraBaseException if needed
        if isinstance(exception, NetraBaseException):
            netra_exception = exception
        else:
            netra_exception = self._convert_to_netra_exception(exception, custom_message)
        
        # Add context
        if context:
            netra_exception.context.update(context)
        
        # Log the exception
        self._log_exception(netra_exception)
        
        # Update metrics
        self._update_metrics(netra_exception)
        
        # Try recovery if strategy exists
        recovery_result = self._attempt_recovery(netra_exception)
        if recovery_result:
            self.logger.info(f"Exception recovery successful: {netra_exception.error_code}")
            return netra_exception
        
        # Reraise if requested
        if should_reraise:
            raise netra_exception
        
        return netra_exception
    
    def _convert_to_netra_exception(
        self,
        exception: Exception,
        custom_message: Optional[str] = None
    ) -> NetraBaseException:
        """Convert standard exceptions to NetraBaseException."""
        message = custom_message or str(exception)
        
        # Map common exception types to Netra exceptions
        exception_mapping = {
            ValueError: ValidationError,
            KeyError: ValidationError,
            TypeError: ValidationError,
            ConnectionError: NetworkError,
            TimeoutError: NetworkError,
            PermissionError: AuthorizationError,
            FileNotFoundError: ValidationError,
        }
        
        exception_class = exception_mapping.get(type(exception), NetraBaseException)
        
        return exception_class(
            message=message,
            original_exception=exception,
            context={"original_type": type(exception).__name__}
        )
    
    def _log_exception(self, exception: NetraBaseException) -> None:
        """Log exception with appropriate level based on severity."""
        log_data = {
            "error_code": exception.error_code,
            "category": exception.category.value,
            "severity": exception.severity.value,
            "context": exception.context
        }
        
        if exception.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH):
            self.logger.error(f"Exception: {exception.message}", extra=log_data, exc_info=True)
        elif exception.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Exception: {exception.message}", extra=log_data)
        else:
            self.logger.info(f"Exception: {exception.message}", extra=log_data)
    
    def _update_metrics(self, exception: NetraBaseException) -> None:
        """Update error metrics."""
        metric_key = f"{exception.category.value}_{exception.severity.value}"
        self.error_metrics[metric_key] = self.error_metrics.get(metric_key, 0) + 1
    
    def _attempt_recovery(self, exception: NetraBaseException) -> bool:
        """Attempt to recover from exception using registered strategies."""
        for exception_type, strategy in self.recovery_strategies.items():
            if isinstance(exception.original_exception, exception_type):
                try:
                    return strategy(exception)
                except Exception as e:
                    self.logger.warning(f"Recovery strategy failed: {e}")
        return False
    
    def register_recovery_strategy(
        self,
        exception_type: Type[Exception],
        strategy: Callable[[NetraBaseException], bool]
    ) -> None:
        """Register a recovery strategy for a specific exception type."""
        self.recovery_strategies[exception_type] = strategy
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current error metrics."""
        return self.error_metrics.copy()


# Global exception handler instance
_global_handler = UnifiedExceptionHandler()


def handle_exceptions(
    reraise: bool = True,
    custom_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    logger_name: Optional[str] = None
):
    """
    Decorator for unified exception handling.
    
    This decorator replaces all try/except patterns in function definitions.
    
    Usage:
        @handle_exceptions(reraise=False)
        def my_function():
            # Function code that might raise exceptions
            pass
    """
    def decorator(func):
        handler = UnifiedExceptionHandler(logger_name or func.__module__)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    return handler.handle_exception(
                        e, context=context, should_reraise=reraise, custom_message=custom_message
                    )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    return handler.handle_exception(
                        e, context=context, should_reraise=reraise, custom_message=custom_message
                    )
            return sync_wrapper
    return decorator


class ExceptionContext:
    """
    Context manager for unified exception handling.
    
    This replaces try/except blocks in code.
    
    Usage:
        with ExceptionContext() as ctx:
            # Code that might raise exceptions
            pass
        
        if ctx.has_error:
            # Handle error case
            print(f"Error: {ctx.error.message}")
    """
    
    def __init__(
        self,
        suppress: bool = False,
        logger_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.suppress = suppress
        self.handler = UnifiedExceptionHandler(logger_name)
        self.context = context
        self.error: Optional[NetraBaseException] = None
        self.has_error: bool = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.has_error = True
            self.error = self.handler.handle_exception(
                exc_val,
                context=self.context,
                should_reraise=not self.suppress
            )
        
        return self.suppress


def safe_call(
    func: Callable,
    *args,
    default_return: Any = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Safely call a function with unified exception handling.
    
    This replaces try/except patterns around function calls.
    
    Args:
        func: Function to call
        *args: Arguments to pass to function
        default_return: Value to return if function fails
        context: Additional context for error handling
        **kwargs: Keyword arguments to pass to function
        
    Returns:
        Function result or default_return if exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        _global_handler.handle_exception(
            e, context=context, should_reraise=False
        )
        return default_return


async def safe_async_call(
    func: Callable,
    *args,
    default_return: Any = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Safely call an async function with unified exception handling.
    
    Args:
        func: Async function to call
        *args: Arguments to pass to function
        default_return: Value to return if function fails
        context: Additional context for error handling
        **kwargs: Keyword arguments to pass to function
        
    Returns:
        Function result or default_return if exception occurred
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        _global_handler.handle_exception(
            e, context=context, should_reraise=False
        )
        return default_return