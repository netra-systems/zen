"""GCP Error Reporter - Singleton pattern for reporting errors to GCP Error Reporting.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Production visibility and rapid incident response
3. Value Impact: Reduces MTTR by surfacing errors in GCP monitoring dashboards
4. Revenue Impact: Supports $15K+ MRR enterprise reliability requirements

CRITICAL: This module ensures errors are visible in GCP Cloud Run error reporting.
"""

import asyncio
import logging
import os
import sys
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional
from contextvars import ContextVar

from loguru import logger

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity

# Use loguru directly to avoid circular import with unified_logging

# Context variable for request metadata
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})

try:
    from google.cloud import error_reporting
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    error_reporting = None


class GCPErrorReporter:
    """Singleton GCP Error Reporter for centralized error reporting with Client Manager integration."""
    
    _instance: Optional['GCPErrorReporter'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.client: Optional[error_reporting.Client] = None
            self.client_manager: Optional['GCPClientManager'] = None  # Integration with Client Manager
            self.enabled = self._should_enable()
            self._rate_limit_counter = 0
            self._rate_limit_max = 100  # Max errors per minute
            self._rate_limit_window_start = None
            
            if self.enabled:
                self._initialize_client()
            
            GCPErrorReporter._initialized = True
    
    def set_client_manager(self, client_manager: 'GCPClientManager') -> None:
        """Set the client manager for proper lifecycle management."""
        self.client_manager = client_manager
        logger.debug("GCP Client Manager set for error reporter")
    
    def _should_enable(self) -> bool:
        """Check if GCP error reporting should be enabled."""
        # Enable if running in GCP Cloud Run or if explicitly enabled
        is_cloud_run = os.getenv('K_SERVICE') is not None
        is_gcp_project = os.getenv('GCP_PROJECT') is not None
        is_explicitly_enabled = os.getenv('ENABLE_GCP_ERROR_REPORTING', '').lower() == 'true'
        
        return GCP_AVAILABLE and (is_cloud_run or is_gcp_project or is_explicitly_enabled)
    
    def _initialize_client(self):
        """Initialize GCP Error Reporting client."""
        try:
            self.client = error_reporting.Client()
            logger.info("GCP Error Reporting client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GCP Error Reporting: {e}")
            self.enabled = False
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        import time
        current_time = time.time()
        
        # Reset window if needed
        if self._rate_limit_window_start is None or \
           current_time - self._rate_limit_window_start > 60:
            self._rate_limit_window_start = current_time
            self._rate_limit_counter = 0
        
        # Check limit
        if self._rate_limit_counter >= self._rate_limit_max:
            return False
        
        self._rate_limit_counter += 1
        return True
    
    def report_exception(self, 
                        exception: Exception,
                        user: Optional[str] = None,
                        http_context: Optional[Dict[str, Any]] = None,
                        extra_context: Optional[Dict[str, Any]] = None):
        """Report an exception to GCP Error Reporting.
        
        Args:
            exception: The exception to report
            user: User identifier (email or ID)
            http_context: HTTP request context (method, url, etc.)
            extra_context: Additional context data
        """
        if not self.enabled or not self.client:
            return
        
        if not self._check_rate_limit():
            logger.warning("GCP error reporting rate limit exceeded")
            return
        
        try:
            # Get context from context variable if not provided
            ctx = request_context.get()
            if not user and 'user_id' in ctx:
                user = ctx['user_id']
            if not http_context and 'http_context' in ctx:
                http_context = ctx['http_context']
            
            # Build context for error reporting
            context = {}
            if http_context:
                context['httpRequest'] = http_context
            if user:
                context['user'] = user
            
            # Add extra context as custom properties
            if extra_context:
                context.update(extra_context)
            
            # Add trace ID if available
            if 'trace_id' in ctx:
                context['trace_id'] = ctx['trace_id']
            
            # Report to GCP
            self.client.report_exception(
                http_context=context.get('httpRequest'),
                user=context.get('user')
            )
            
            logger.debug(f"Reported exception to GCP: {type(exception).__name__}")
            
        except Exception as e:
            # Don't let error reporting failures break the app
            logger.error(f"Failed to report error to GCP: {e}")
    
    def report_message(self, 
                      message: str,
                      severity: ErrorSeverity = ErrorSeverity.ERROR,
                      user: Optional[str] = None,
                      extra_context: Optional[Dict[str, Any]] = None):
        """Report an error message to GCP Error Reporting.
        
        Args:
            message: Error message to report
            severity: Error severity level
            user: User identifier
            extra_context: Additional context
        """
        if not self.enabled or not self.client:
            return
        
        if not self._check_rate_limit():
            return
        
        try:
            # Create a synthetic exception for the message
            class ReportedError(Exception):
                pass
            
            exception = ReportedError(message)
            self.report_exception(exception, user=user, extra_context=extra_context)
            
        except Exception as e:
            logger.error(f"Failed to report message to GCP: {e}")
    
    async def report_error(self, 
                          error: Exception, 
                          context: Optional[Dict[str, Any]] = None) -> bool:
        """Report an error to GCP Error Reporting with enhanced client manager integration.
        
        Args:
            error: The exception to report
            context: Business context including user_id, error_type, etc.
            
        Returns:
            bool: True if error was reported successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"GCP error reporting not enabled, skipping: {type(error).__name__}")
            return False
        
        if not self._check_rate_limit():
            logger.warning("GCP error reporting rate limit exceeded")
            return False
        
        try:
            # Use client manager if available for better client lifecycle management
            if self.client_manager:
                client = await self.client_manager.get_error_reporting_client_async()
            else:
                client = self.client
            
            if not client:
                logger.debug("No GCP client available for error reporting")
                return False
            
            # Extract context information
            user_id = None
            http_context = None
            extra_context = {}
            
            if context:
                user_id = context.get('user_id')
                http_context = context.get('http_context')
                # Copy all context as extra context
                extra_context.update(context)
            
            # Add enhanced context for client manager integration
            extra_context['client_source'] = 'client_manager' if self.client_manager else 'direct'
            extra_context['integration_version'] = 'v2_enhanced'
            
            # Report the exception with context
            self.report_exception(
                exception=error,
                user=user_id,
                http_context=http_context,
                extra_context=extra_context
            )
            
            logger.debug(f"Successfully reported error to GCP: {type(error).__name__}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to report error to GCP: {e}")
            return False


class GCPErrorLoggingHandler(logging.Handler):
    """Custom logging handler that integrates with GCP Error Reporting.
    
    This handler intercepts ERROR and CRITICAL level logs and automatically
    creates GCP Error objects with full context preservation.
    """
    
    def __init__(self, gcp_reporter: GCPErrorReporter):
        super().__init__()
        self.gcp_reporter = gcp_reporter
        self.setLevel(logging.ERROR)  # Only handle ERROR and above
    
    def emit(self, record: logging.LogRecord):
        """Convert log record to GCP Error and report.
        
        Args:
            record: Python logging record to process
        """
        if not self.gcp_reporter.enabled or not self.gcp_reporter.client:
            return
        
        try:
            # Create exception from log record
            if record.exc_info:
                # Use actual exception if available
                exception = record.exc_info[1]
            else:
                # Create synthetic exception for the message
                class LoggedError(Exception):
                    pass
                exception = LoggedError(record.getMessage())
            
            # Extract context from log record
            extra_context = {
                'logger_name': record.name,
                'log_level': record.levelname,
                'filename': record.filename,
                'line_number': record.lineno,
                'function_name': record.funcName,
                'module': record.module,
                'integration_source': 'gcp_logging_handler'
            }
            
            # Add any extra fields from log record
            if hasattr(record, '__dict__'):
                for key, value in record.__dict__.items():
                    if key not in ['name', 'levelname', 'levelno', 'pathname', 'filename',
                                   'module', 'lineno', 'funcName', 'created', 'msecs',
                                   'relativeCreated', 'thread', 'threadName', 'processName',
                                   'process', 'msg', 'args', 'exc_info', 'exc_text', 'stack_info']:
                        extra_context[key] = str(value) if value is not None else None
            
            # Get context from context variable
            ctx = request_context.get()
            user_id = ctx.get('user_id')
            http_context = ctx.get('http_context')
            
            # Merge context
            if ctx:
                extra_context.update(ctx)
            
            # Report to GCP with full context
            self.gcp_reporter.report_exception(
                exception=exception,
                user=user_id,
                http_context=http_context,
                extra_context=extra_context
            )
            
        except Exception as e:
            # Don't let error reporting failures break logging
            # Use direct loguru to avoid recursion
            logger.error(f"GCP Logging Handler failed to report error: {e}")


# Singleton instance
_reporter = GCPErrorReporter()


def get_error_reporter() -> GCPErrorReporter:
    """Get the singleton error reporter instance."""
    return _reporter


def report_exception(exception: Exception, **kwargs):
    """Convenience function to report an exception."""
    _reporter.report_exception(exception, **kwargs)


def report_error(message: str, **kwargs):
    """Convenience function to report an error message."""
    _reporter.report_message(message, **kwargs)


def set_request_context(user_id: Optional[str] = None,
                        trace_id: Optional[str] = None,
                        http_context: Optional[Dict[str, Any]] = None,
                        **kwargs):
    """Set request context for error reporting.
    
    Call this at the beginning of request handling to provide context
    that will be automatically included in error reports.
    """
    ctx = {
        'user_id': user_id,
        'trace_id': trace_id,
        'http_context': http_context,
        **kwargs
    }
    request_context.set({k: v for k, v in ctx.items() if v is not None})


def clear_request_context():
    """Clear the request context."""
    request_context.set({})


def gcp_reportable(reraise: bool = True, 
                   severity: ErrorSeverity = ErrorSeverity.ERROR):
    """Decorator to mark functions where errors should be reported to GCP.
    
    Args:
        reraise: Whether to re-raise the exception after reporting
        severity: Default severity level for errors
    
    Usage:
        @gcp_reportable()
        async def critical_function():
            # This function's errors will be reported to GCP
            pass
        
        @gcp_reportable(reraise=False)
        def handled_but_reported():
            # Errors reported but not re-raised
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Report to GCP
                extra_context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'severity': severity.value if hasattr(severity, 'value') else str(severity)
                }
                
                # Include NetraException details if available
                if isinstance(e, NetraException):
                    extra_context['error_code'] = str(e.error_details.code)
                    extra_context['error_severity'] = str(e.error_details.severity)
                    if e.error_details.details:
                        extra_context['error_details'] = e.error_details.details
                
                report_exception(e, extra_context=extra_context)
                
                if reraise:
                    raise
                return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Report to GCP
                extra_context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'severity': severity.value if hasattr(severity, 'value') else str(severity)
                }
                
                # Include NetraException details if available
                if isinstance(e, NetraException):
                    extra_context['error_code'] = str(e.error_details.code)
                    extra_context['error_severity'] = str(e.error_details.severity)
                    if e.error_details.details:
                        extra_context['error_details'] = e.error_details.details
                
                report_exception(e, extra_context=extra_context)
                
                if reraise:
                    raise
                return None
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def install_exception_handlers(app=None):
    """Install global exception handlers and logging handler for GCP error reporting.
    
    Args:
        app: Optional FastAPI/Starlette app instance
    """
    original_excepthook = sys.excepthook
    
    def gcp_excepthook(exc_type, exc_value, exc_traceback):
        """Global exception hook for uncaught exceptions."""
        # Report to GCP
        if exc_type != KeyboardInterrupt:
            report_exception(exc_value, extra_context={
                'type': 'uncaught_exception',
                'traceback': ''.join(traceback.format_tb(exc_traceback))
            })
        
        # Call original handler
        original_excepthook(exc_type, exc_value, exc_traceback)
    
    # Install synchronous exception handler
    sys.excepthook = gcp_excepthook
    
    # Install async exception handler if asyncio is available
    try:
        loop = asyncio.get_event_loop()
        original_handler = loop.get_exception_handler()
        
        def async_exception_handler(loop, context):
            """Async exception handler for uncaught async exceptions."""
            exception = context.get('exception')
            if exception:
                report_exception(exception, extra_context={
                    'type': 'uncaught_async_exception',
                    'message': context.get('message', ''),
                    'future': str(context.get('future', ''))
                })
            
            # Call original handler if exists
            if original_handler:
                original_handler(loop, context)
            else:
                # Default handling
                loop.default_exception_handler(context)
        
        loop.set_exception_handler(async_exception_handler)
        
    except RuntimeError:
        # No event loop yet, will be set up later
        pass
    
    # Install GCP Logging Handler to Python's logging system
    # This ensures logger.error() calls create GCP Error objects
    reporter = get_error_reporter()
    if reporter.enabled:
        gcp_handler = GCPErrorLoggingHandler(reporter)
        # Add to root logger to catch all logger.error() calls
        logging.getLogger().addHandler(gcp_handler)
        logger.info("GCP Logging Handler installed for Python logging integration")
    
    # If FastAPI/Starlette app provided, add middleware
    if app:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        
        class GCPErrorReportingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Set request context
                set_request_context(
                    http_context={
                        'method': request.method,
                        'url': str(request.url),
                        'userAgent': request.headers.get('user-agent', ''),
                        'referrer': request.headers.get('referer', ''),
                        'remoteIp': request.client.host if request.client else None
                    }
                )
                
                try:
                    response = await call_next(request)
                    return response
                except Exception as e:
                    # Report to GCP before re-raising
                    report_exception(e)
                    raise
                finally:
                    # Clear context
                    clear_request_context()
        
        app.add_middleware(GCPErrorReportingMiddleware)
        logger.info("GCP Error Reporting middleware installed")