"""Unified, optimized logging system for Netra backend with security and performance improvements.

Main logger interface providing:
- Centralized logging configuration
- Integration with formatters and context management
- Backward compatibility with existing code
- Simple API for logging operations
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from loguru import logger
from netra_backend.app.core.isolated_environment import get_env

from netra_backend.app.core.logging_context import (
    ExecutionTimeDecorator,
    LoggingContext,
    PerformanceTracker,
    request_id_context,
    setup_stdlib_interception,
    should_log_record,
    trace_id_context,
    user_id_context,
)

# Import the modular components
from netra_backend.app.core.logging_formatters import (
    LogHandlerConfig,
    SensitiveDataFilter,
)


class UnifiedLogger:
    """Unified logger with security, performance, and observability features."""
    
    def __init__(self):
        self._initialized = False
        self._config = None  # Will be lazy-loaded
        self._config_loaded = False  # Cache flag to prevent repeated loading
        self._filter = SensitiveDataFilter()
        self._context = LoggingContext()
        self._performance = PerformanceTracker(self)
        self._decorator = ExecutionTimeDecorator(self._performance)
        # Don't setup logging during init to avoid circular imports
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from unified config with caching."""
        # Return cached config if already loaded
        if self._config_loaded and self._config is not None:
            return self._config
        
        # Check if secrets are still loading to prevent premature initialization
        if get_env().get('NETRA_SECRETS_LOADING') == 'true':
            # Use fallback config during secret loading phase
            loaded_config = self._get_fallback_config()
            # Don't cache during loading phase
            return loaded_config
            
        try:
            # Avoid circular import during module initialization
            from netra_backend.app.core.configuration import unified_config_manager
            # Check if config manager is in loading state to prevent recursion
            if hasattr(unified_config_manager, '_loading') and unified_config_manager._loading:
                # Use fallback during config loading phase
                loaded_config = self._get_fallback_config()
            else:
                config = unified_config_manager.get_config()
                loaded_config = {
                    'log_level': getattr(config, 'log_level', 'INFO').upper(),
                    'enable_file_logging': getattr(config, 'enable_file_logging', False),
                    'enable_json_logging': getattr(config, 'enable_json_logging', False),
                    'log_file_path': getattr(config, 'log_file_path', 'logs/netra.log')
                }
        except (ImportError, Exception):
            # Fallback configuration if config module not available or any error
            loaded_config = self._get_fallback_config()
        
        # Cache the config and mark as loaded
        self._config = loaded_config
        self._config_loaded = True
        return loaded_config
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration for bootstrap phase."""
        # Disable file logging completely during testing
        is_testing = get_env().get('TESTING') == '1' or get_env().get('ENVIRONMENT') == 'testing'
        return {
            'log_level': get_env().get('LOG_LEVEL', 'INFO').upper(),
            'enable_file_logging': False,  # Never enable file logging in fallback
            'enable_json_logging': False,
            'log_file_path': 'logs/netra.log'
        }
    
    
    def _setup_logging(self):
        """Initialize the logging system."""
        if self._initialized:
            return
        # Load config (uses caching internally)
        self._config = self._load_config()
        self._configure_handlers()
        
        # Skip standard library interception during testing to prevent I/O errors
        is_testing = get_env().get('TESTING') == '1' or get_env().get('ENVIRONMENT') == 'testing'
        if not is_testing:
            setup_stdlib_interception()
        
        self._initialized = True
    
    def _configure_handlers(self):
        """Configure logging handlers."""
        # Check if we're in test environment and skip handler configuration
        is_testing = get_env().get('TESTING') == '1' or get_env().get('ENVIRONMENT') == 'testing'
        
        # Safely remove existing handlers to prevent I/O errors during test cleanup
        try:
            # Remove all existing handlers (stop is deprecated in favor of remove)
            logger.remove()
        except (ValueError, OSError, AttributeError) as e:
            # Ignore errors during handler removal (e.g., closed file handlers)
            # This commonly occurs during test teardown when files are already closed
            pass
        
        # Skip file handler configuration entirely during testing
        if is_testing:
            # Only add a minimal handler for tests to prevent I/O issues
            try:
                logger.add(
                    sink=lambda message: None,  # No-op sink for tests
                    level="ERROR",
                    filter=should_log_record
                )
            except (ValueError, OSError):
                pass
            return
        
        # Suppress SQLAlchemy verbose logging unless in TRACE mode
        import logging
        if self._config['log_level'] != 'TRACE':
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
        
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
        # Ensure logging is setup when logger is requested
        if not self._initialized:
            self._setup_logging()
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

def get_logger(name: Optional[str] = None):
    """Get a logger instance with the given name."""
    return central_logger.get_logger(name)