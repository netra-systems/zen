"""Unified, optimized logging system for Netra backend with security and performance improvements.

Main logger interface providing:
- Centralized logging configuration
- Integration with formatters and context management
- Backward compatibility with existing code
- Simple API for logging operations
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any

from loguru import logger

# Import the modular components
from .logging_formatters import SensitiveDataFilter, LogHandlerConfig
from .logging_context import (
    request_id_context,
    user_id_context, 
    trace_id_context,
    LoggingContext,
    PerformanceTracker,
    ExecutionTimeDecorator,
    should_log_record,
    setup_stdlib_interception
)


class UnifiedLogger:
    """Unified logger with security, performance, and observability features."""
    
    def __init__(self):
        self._initialized = False
        self._config = self._load_config()
        self._filter = SensitiveDataFilter()
        self._context = LoggingContext()
        self._performance = PerformanceTracker(self)
        self._decorator = ExecutionTimeDecorator(self._performance)
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from environment."""
        return {
            'log_level': os.environ.get("LOG_LEVEL", "INFO").upper(),
            'enable_file_logging': os.environ.get("ENABLE_FILE_LOGGING", "false").lower() == "true",
            'enable_json_logging': os.environ.get("ENABLE_JSON_LOGGING", "false").lower() == "true",
            'log_file_path': os.environ.get("LOG_FILE_PATH", "logs/netra.log")
        }
    
    def _setup_logging(self):
        """Initialize the logging system."""
        if self._initialized:
            return
        self._configure_handlers()
        setup_stdlib_interception()
        self._initialized = True
    
    def _configure_handlers(self):
        """Configure logging handlers."""
        logger.remove()
        handler_config = LogHandlerConfig(
            self._config['log_level'], 
            self._config['enable_json_logging']
        )
        handler_config.add_console_handler(should_log_record)
        if self._config['enable_file_logging']:
            handler_config.add_file_handler(
                self._config['log_file_path'], 
                should_log_record
            )
    
    def get_logger(self, name: Optional[str] = None):
        """Get a logger instance with the given name."""
        return logger.bind(name=name) if name else logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, exc_info: bool = True, **kwargs):
        """Log error message with context and exception info."""
        self._log("error", message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """Log critical message with context and exception info."""
        self._log("critical", message, exc_info=exc_info, **kwargs)
    
    def _log(self, level: str, message: str, exc_info: bool = False, **kwargs):
        """Internal logging method with filtering and context."""
        filtered_message = self._filter.filter_message(message)
        filtered_kwargs = self._filter.filter_dict(kwargs)
        context = self._build_log_context(filtered_kwargs)
        self._emit_log(level, filtered_message, exc_info, context)
    
    def _build_log_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build log context with correlation IDs."""
        context = self._context.get_filtered_context()
        context.update(kwargs)
        return context
    
    def _emit_log(self, level: str, message: str, exc_info: bool, context: Dict[str, Any]):
        """Emit log message with proper exception handling."""
        log_method = getattr(logger, level)
        if exc_info and self._has_exception_info():
            log_method(message, exc_info=True, **context)
        else:
            log_method(message, **context)
    
    def _has_exception_info(self) -> bool:
        """Check if current exception info is available."""
        import sys
        return sys.exc_info()[0] is not None
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics."""
        self._performance.log_performance(operation, duration, **kwargs)
    
    def log_api_call(self, method: str, url: str, status_code: int, duration: float, **kwargs):
        """Log API call details."""
        self._performance.log_api_call(method, url, status_code, duration, **kwargs)
    
    def set_context(self, request_id: Optional[str] = None, 
                    user_id: Optional[str] = None,
                    trace_id: Optional[str] = None):
        """Set logging context for the current async context."""
        self._context.set_context(request_id, user_id, trace_id)
    
    def clear_context(self):
        """Clear logging context."""
        self._context.clear_context()
    
    async def shutdown(self):
        """Gracefully shutdown logging system."""
        await logger.complete()
    
    def get_execution_time_decorator(self):
        """Get execution time decorator for this logger instance."""
        return self._decorator.log_execution_time


# Create global logger instance
central_logger = UnifiedLogger()

# Performance monitoring decorator - global convenience function
def log_execution_time(operation_name: Optional[str] = None):
    """Decorator to log function execution time."""
    return central_logger.get_execution_time_decorator()(operation_name)

# Convenience function for backward compatibility
def get_central_logger() -> UnifiedLogger:
    """Get the central logger instance."""
    return central_logger