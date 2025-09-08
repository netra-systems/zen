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
from shared.isolated_environment import get_env

# Lazy imports to avoid circular dependencies
# These will be imported when needed in the methods that use them
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.monitoring.gcp_error_reporter import GCPErrorReporter
    from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity

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
    """Unified logger with security, performance, and observability features.
    
    Now includes automatic GCP Error Reporting integration for ERROR and CRITICAL messages.
    """
    
    def __init__(self):
        self._initialized = False
        self._config = None  # Will be lazy-loaded
        self._config_loaded = False  # Cache flag to prevent repeated loading
        self._filter = SensitiveDataFilter()
        self._context = LoggingContext()
        self._performance = PerformanceTracker(self)
        self._decorator = ExecutionTimeDecorator(self._performance)
        
        # GCP Error Reporter integration (lazy initialization)
        self._gcp_reporter = None
        self._gcp_enabled = self._should_enable_gcp_reporting()
        self._gcp_initialized = False
        
        # Don't setup logging during init to avoid circular imports
    
    def _ensure_gcp_reporter_initialized(self):
        """Lazy initialization of GCP Error Reporter to avoid circular imports."""
        if not self._gcp_enabled or self._gcp_initialized:
            return
            
        try:
            # Lazy import to avoid circular dependency
            from netra_backend.app.services.monitoring.gcp_error_reporter import get_error_reporter
            
            self._gcp_reporter = get_error_reporter()
            self._gcp_initialized = True
            
            # Only log success if not in testing mode to avoid noise
            if not self._is_testing_mode():
                self._log_integration_behavior("GCP Error Reporter integration enabled")
                
        except Exception as e:
            # Safe failure - don't break logging if GCP setup fails
            self._log_integration_behavior(f"GCP Error Reporter initialization failed: {e}", is_error=True)
            self._gcp_enabled = False
            self._gcp_initialized = True  # Mark as initialized to avoid retry
    
    def _map_log_level_to_severity(self, level: str):
        """Map log level to GCP ErrorSeverity enum.
        
        Args:
            level: Log level string (debug, info, warning, error, critical)
            
        Returns:
            ErrorSeverity: Corresponding GCP severity level
        """
        # Lazy import to avoid circular dependency
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        
        level_upper = level.upper()
        mapping = {
            'CRITICAL': ErrorSeverity.CRITICAL,
            'ERROR': ErrorSeverity.ERROR,
            'WARNING': ErrorSeverity.WARNING,
            'INFO': ErrorSeverity.INFO,
            'DEBUG': ErrorSeverity.INFO,  # Map DEBUG to INFO for GCP
        }
        return mapping.get(level_upper, ErrorSeverity.ERROR)  # Default to ERROR if unknown
    
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
                # Check if running in GCP Cloud Run or staging/production
                is_cloud_run = get_env().get('K_SERVICE') is not None
                environment = get_env().get('ENVIRONMENT', 'development').lower()
                is_gcp = is_cloud_run or environment in ['staging', 'production']
                
                loaded_config = {
                    'log_level': getattr(config, 'log_level', 'INFO').upper(),
                    'enable_file_logging': getattr(config, 'enable_file_logging', False),
                    # Force JSON logging for GCP environments
                    'enable_json_logging': is_gcp or getattr(config, 'enable_json_logging', False),
                    'log_file_path': getattr(config, 'log_file_path', 'logs/netra.log')
                }
        except (ImportError, Exception):
            # Fallback configuration if config module not available or any error
            loaded_config = self._get_fallback_config()
        
        # Cache the config and mark as loaded
        self._config = loaded_config
        self._config_loaded = True
        return loaded_config
    
    def _should_enable_gcp_reporting(self) -> bool:
        """Determine if GCP error reporting should be enabled based on environment.
        
        Returns True for:
        - GCP Cloud Run environments (K_SERVICE present)
        - Staging/Production environments
        - Explicitly enabled via ENABLE_GCP_ERROR_REPORTING=true
        
        Returns False for:
        - Development/Testing environments
        - When explicitly disabled
        """
        # Never enable in testing mode to avoid noise and conflicts
        if self._is_testing_mode():
            return False
            
        # Check environment markers
        is_cloud_run = get_env().get('K_SERVICE') is not None
        environment = get_env().get('ENVIRONMENT', 'development').lower()
        is_staging_or_prod = environment in ['staging', 'production']
        is_explicitly_enabled = get_env().get('ENABLE_GCP_ERROR_REPORTING', '').lower() == 'true'
        
        return is_cloud_run or is_staging_or_prod or is_explicitly_enabled
    
    def _is_testing_mode(self) -> bool:
        """Check if we're currently in testing mode."""
        return get_env().get('TESTING') == '1' or get_env().get('ENVIRONMENT') == 'testing'
    
    def _log_integration_behavior(self, message: str, is_error: bool = False):
        """Log GCP integration behavior for debugging and monitoring.
        
        Uses direct loguru logger to avoid recursion with our own _log method.
        """
        try:
            if is_error:
                logger.error(f"[GCP Integration] {message}")
            else:
                logger.info(f"[GCP Integration] {message}")
        except Exception:
            # Completely silent failure to prevent infinite recursion
            pass
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration for bootstrap phase."""
        # Disable file logging completely during testing
        is_testing = self._is_testing_mode()
        # Check if running in GCP Cloud Run or staging/production
        is_cloud_run = get_env().get('K_SERVICE') is not None
        environment = get_env().get('ENVIRONMENT', 'development').lower()
        is_gcp = is_cloud_run or environment in ['staging', 'production']
        
        return {
            'log_level': get_env().get('LOG_LEVEL', 'INFO').upper(),
            'enable_file_logging': False,  # Never enable file logging in fallback
            'enable_json_logging': is_gcp,  # Enable JSON for GCP environments
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
    
    def error(self, message: str, exc_info: bool = True, exception: Optional[Exception] = None, **kwargs):
        """Log error message with context and exception info.
        
        Now automatically reports to GCP Error Reporting in staging/production environments.
        
        Args:
            message: Error message to log
            exc_info: Whether to include current exception info in log
            exception: Optional explicit exception to report to GCP
            **kwargs: Additional context data
        """
        self._log("error", message, exc_info=exc_info, exception=exception, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with context and exception info.
        
        Now automatically reports to GCP Error Reporting in staging/production environments.
        
        Args:
            message: Critical error message to log
            exc_info: Whether to include current exception info in log
            exception: Optional explicit exception to report to GCP
            **kwargs: Additional context data
        """
        self._log("critical", message, exc_info=exc_info, exception=exception, **kwargs)
    
    def _log(self, level: str, message: str, exc_info: bool = False, exception: Optional[Exception] = None, **kwargs):
        """Internal logging method with filtering and context.
        
        Now includes automatic GCP error reporting for ERROR and CRITICAL levels.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            exc_info: Whether to include exception info in log
            exception: Optional explicit exception to report to GCP
            **kwargs: Additional context data
        """
        filtered_message = self._filter.filter_message(message)
        filtered_kwargs = self._filter.filter_dict(kwargs)
        context = self._build_log_context(filtered_kwargs)
        
        # Emit the log message first (existing functionality)
        self._emit_log(level, filtered_message, exc_info, context)
        
        # Auto-report to GCP for ERROR and CRITICAL levels
        level_upper = level.upper()
        if level_upper in ['ERROR', 'CRITICAL'] and self._gcp_enabled:
            self._ensure_gcp_reporter_initialized()
            if self._gcp_reporter:
                self._report_to_gcp(filtered_message, level, exception, filtered_kwargs)
    
    def _build_log_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build log context with correlation IDs."""
        context = self._context.get_filtered_context()
        context.update(kwargs)
        return context
    
    def _report_to_gcp(self, message: str, level: str, exception: Optional[Exception], context: Dict[str, Any]):
        """Report error message to GCP Error Reporting.
        
        Args:
            message: Error message to report
            level: Log level
            exception: Optional exception object
            context: Additional context data
        """
        try:
            severity = self._map_log_level_to_severity(level)
            
            # Build extra context for GCP
            extra_context = {
                'log_level': level.upper(),
                'logger_name': 'unified_logger',
                'integration_source': 'unified_logging_auto_report'
            }
            extra_context.update(context)
            
            # Extract user context if available
            user_id = context.get('user_id')
            
            if exception:
                # Report the actual exception
                self._gcp_reporter.report_exception(
                    exception,
                    user=user_id,
                    extra_context=extra_context
                )
                self._log_integration_behavior(f"Reported exception to GCP: {type(exception).__name__}")
            else:
                # Report as error message
                self._gcp_reporter.report_message(
                    message,
                    severity=severity,
                    user=user_id,
                    extra_context=extra_context
                )
                self._log_integration_behavior(f"Reported {level.upper()} message to GCP")
                
        except Exception as e:
            # Safe error handling - GCP failures should not break logging
            self._log_integration_behavior(f"Failed to report to GCP: {e}", is_error=True)
    
    def _emit_log(self, level: str, message: str, exc_info: bool, context: Dict[str, Any]):
        """Emit log message with proper exception handling."""
        # Use depth=4 to skip the call chain:
        # 1. _emit_log (this method)
        # 2. _log (the general log method with GCP reporting)
        # 3. error/warning/info (the specific log level method)
        # 4. actual caller
        # This ensures the actual caller location is shown in logs
        if exc_info and self._has_exception_info():
            logger.opt(depth=4, exception=True).log(level.upper(), message, **context)
        else:
            logger.opt(depth=4).log(level.upper(), message, **context)
    
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