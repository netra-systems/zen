"""Logging context management and correlation IDs for the unified logging system.

This module handles:
- Request ID context management
- User ID tracking
- Trace ID correlation
- Context variable operations
- Performance monitoring decorators
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any
from functools import wraps
from contextvars import ContextVar

from loguru import logger


# Context variables for request tracking
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class LoggingContext:
    """Manages logging context for requests and operations."""
    
    def __init__(self):
        self._contexts = {
            'request_id': request_id_context,
            'user_id': user_id_context,
            'trace_id': trace_id_context
        }
    
    def set_context(self, request_id: Optional[str] = None, 
                    user_id: Optional[str] = None,
                    trace_id: Optional[str] = None):
        """Set logging context for the current async context."""
        self._set_if_provided('request_id', request_id)
        self._set_if_provided('user_id', user_id)
        self._set_if_provided('trace_id', trace_id)
    
    def _set_if_provided(self, context_name: str, value: Optional[str]):
        """Set context variable if value is provided."""
        if value:
            self._contexts[context_name].set(value)
    
    def clear_context(self):
        """Clear all logging context variables."""
        for context_var in self._contexts.values():
            context_var.set(None)
    
    def get_context(self) -> Dict[str, Optional[str]]:
        """Get current context values."""
        return {
            name: context_var.get() 
            for name, context_var in self._contexts.items()
        }
    
    def get_filtered_context(self) -> Dict[str, str]:
        """Get context with non-None values only."""
        return {
            name: value
            for name, value in self.get_context().items()
            if value is not None
        }


class PerformanceTracker:
    """Tracks performance metrics for operations."""
    
    def __init__(self, logger_instance):
        self._logger = logger_instance
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics."""
        self._logger.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_api_call(self, method: str, url: str, status_code: int, 
                     duration: float, **kwargs):
        """Log API call details."""
        self._logger.info(
            f"API Call: {method} {url} -> {status_code}",
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )


class ExecutionTimeDecorator:
    """Decorator for logging function execution time."""
    
    def __init__(self, performance_tracker: PerformanceTracker):
        self._tracker = performance_tracker
    
    def log_execution_time(self, operation_name: Optional[str] = None):
        """Decorator to log function execution time."""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                return self._create_async_wrapper(func, operation_name)
            else:
                return self._create_sync_wrapper(func, operation_name)
        return decorator
    
    def _create_async_wrapper(self, func, operation_name: Optional[str]):
        """Create async wrapper for performance tracking."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            name = self._get_operation_name(func, operation_name)
            
            try:
                result = await func(*args, **kwargs)
                duration = asyncio.get_event_loop().time() - start_time
                self._tracker.log_performance(name, duration, status="success")
                return result
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                self._tracker.log_performance(name, duration, status="error", error=str(e))
                raise
        return async_wrapper
    
    def _create_sync_wrapper(self, func, operation_name: Optional[str]):
        """Create sync wrapper for performance tracking."""
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            name = self._get_operation_name(func, operation_name)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                self._tracker.log_performance(name, duration, status="success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                self._tracker.log_performance(name, duration, status="error", error=str(e))
                raise
        return sync_wrapper
    
    def _get_operation_name(self, func, operation_name: Optional[str]) -> str:
        """Get operation name for logging."""
        return operation_name or f"{func.__module__}.{func.__name__}"


class ContextFilter:
    """Filters log records based on environment and context."""
    
    def __init__(self):
        self._environment = os.environ.get("ENVIRONMENT", "development")
        self._noisy_modules = {"uvicorn.access", "uvicorn.error", "watchfiles"}
    
    def should_log(self, record) -> bool:
        """Determine if a message should be logged."""
        if self._is_error_or_above(record):
            return True
        
        if self._is_production():
            return self._should_log_in_production(record)
        
        return True
    
    def _is_error_or_above(self, record) -> bool:
        """Check if log level is error or above."""
        return record["level"].no >= logger.level("ERROR").no
    
    def _is_production(self) -> bool:
        """Check if running in production environment."""
        return self._environment == "production"
    
    def _should_log_in_production(self, record) -> bool:
        """Determine if should log in production environment."""
        if self._is_noisy_module(record["name"]):
            return record["level"].no >= logger.level("WARNING").no
        return True
    
    def _is_noisy_module(self, module_name: str) -> bool:
        """Check if module is considered noisy in production."""
        return any(module_name.startswith(module) for module in self._noisy_modules)


class StandardLibraryInterceptor:
    """Intercepts standard library logging and redirects to loguru."""
    
    def setup_interception(self):
        """Set up interception of standard library logging."""
        import logging
        
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                StandardLibraryInterceptor._emit_to_loguru(record)
        
        self._configure_logging(InterceptHandler)
        self._configure_specific_loggers(InterceptHandler)
    
    @staticmethod
    def _emit_to_loguru(record):
        """Emit standard library log record to loguru."""
        import logging
        
        level = StandardLibraryInterceptor._get_loguru_level_static(record)
        frame, depth = StandardLibraryInterceptor._find_caller_frame_static()
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )
    
    @staticmethod
    def _get_loguru_level_static(record):
        """Get corresponding loguru level."""
        try:
            return logger.level(record.levelname).name
        except ValueError:
            return record.levelno
    
    def _get_loguru_level(self, record):
        """Get corresponding loguru level (instance method for compatibility)."""
        return StandardLibraryInterceptor._get_loguru_level_static(record)
    
    @staticmethod
    def _find_caller_frame_static():
        """Find caller frame for proper log attribution."""
        import logging
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        return frame, depth
    
    def _find_caller_frame(self):
        """Find caller frame for proper log attribution (instance method for compatibility)."""
        return StandardLibraryInterceptor._find_caller_frame_static()
    
    def _configure_logging(self, handler_class):
        """Configure basic logging with interceptor."""
        import logging
        logging.basicConfig(handlers=[handler_class()], level=0)
    
    def _configure_specific_loggers(self, handler_class):
        """Configure specific loggers with interceptor."""
        import logging
        
        logger_names = [
            "uvicorn", "uvicorn.error", "uvicorn.access", 
            "sqlalchemy", "faker"
        ]
        
        for name in logger_names:
            logging.getLogger(name).handlers = [handler_class()]


# Global instances for context management
_logging_context = LoggingContext()
_context_filter = ContextFilter()
_stdlib_interceptor = StandardLibraryInterceptor()

# Convenience functions for context management
def set_logging_context(request_id: Optional[str] = None, 
                       user_id: Optional[str] = None,
                       trace_id: Optional[str] = None):
    """Set logging context - convenience function."""
    _logging_context.set_context(request_id, user_id, trace_id)


def clear_logging_context():
    """Clear logging context - convenience function."""
    _logging_context.clear_context()


def get_logging_context() -> Dict[str, Optional[str]]:
    """Get current logging context - convenience function."""
    return _logging_context.get_context()


def should_log_record(record) -> bool:
    """Check if record should be logged - convenience function."""
    return _context_filter.should_log(record)


def setup_stdlib_interception():
    """Setup standard library logging interception - convenience function."""
    _stdlib_interceptor.setup_interception()