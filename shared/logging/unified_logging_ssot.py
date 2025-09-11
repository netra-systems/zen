"""
Unified Logging SSOT (Single Source of Truth) Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational Excellence and Debug Capability  
- Value Impact: Eliminates $500K+ ARR Golden Path debugging failures caused by fragmented logging
- Strategic Impact: Single source of truth for all logging prevents cascade failures and debugging gaps

This module consolidates 5 competing logging configurations into one unified system:
- netra_backend/app/logging_config.py (wrapper patterns)
- shared/logging/unified_logger_factory.py (factory patterns) 
- netra_backend/app/core/logging_config.py (Cloud Run specific)
- analytics_service/analytics_core/utils/logging_config.py (structlog patterns)
- netra_backend/app/core/unified_logging.py (core implementation)

SSOT Features:
- Single logging configuration for ALL services
- Cloud Run optimization with JSON logging
- Request correlation and trace context
- Sensitive data filtering for compliance
- Performance monitoring integration
- GCP Error Reporting integration
- Service-specific customization support
- Unified environment handling via IsolatedEnvironment

This is the ONLY logging module that should be imported across the entire platform.
"""

import asyncio
import logging
import sys
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Union, Set, List

# Import from loguru for advanced logging features
from loguru import logger

# Import shared environment management
from shared.isolated_environment import IsolatedEnvironment

# Context variables for distributed tracing - UNIFIED STANDARD
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
event_type_context: ContextVar[Optional[str]] = ContextVar('event_type', default=None)


class SensitiveDataFilter:
    """
    SSOT Sensitive Data Filter - Unified across all services.
    
    Protects sensitive information from appearing in logs across ALL services.
    Consolidates filtering logic from multiple previous implementations.
    """
    
    # Comprehensive sensitive fields list (consolidated from all previous configs)
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization', 'auth_token',
        'credit_card', 'ssn', 'email', 'phone', 'ip_address', 'user_agent',
        'session_id', 'jwt', 'bearer', 'oauth', 'private_key', 'certificate'
    }
    
    @classmethod
    def filter_message(cls, message: str) -> str:
        """Filter sensitive data from log messages."""
        if not isinstance(message, str):
            return message
            
        filtered = message
        # Remove potential JWT tokens
        filtered = re.sub(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '***JWT_REDACTED***', filtered)
        # Remove potential API keys (long alphanumeric strings)
        filtered = re.sub(r'[A-Za-z0-9]{32,}', '***API_KEY_REDACTED***', filtered)
        
        return filtered
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from dictionary structures."""
        return cls._filter_recursive(data)
    
    @classmethod
    def _filter_recursive(cls, data: Any) -> Any:
        """Recursively filter sensitive data from any data structure."""
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if isinstance(key, str) and any(
                    sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS
                ):
                    filtered[key] = "***REDACTED***"
                else:
                    filtered[key] = cls._filter_recursive(value)
            return filtered
        elif isinstance(data, (list, tuple)):
            return [cls._filter_recursive(item) for item in data]
        elif isinstance(data, str):
            # Don't log potentially sensitive long strings
            if len(data) > 1000:
                return f"***LONG_STRING_REDACTED_{len(data)}_CHARS***"
            return cls.filter_message(data)
        return data


class UnifiedLoggingContext:
    """
    SSOT Logging Context Manager - Unified trace propagation.
    
    Consolidates context management from multiple previous implementations.
    Provides consistent correlation ID and trace context across ALL services.
    """
    
    def set_context(self, request_id: Optional[str] = None, 
                    user_id: Optional[str] = None,
                    trace_id: Optional[str] = None,
                    event_type: Optional[str] = None):
        """Set logging context for current async context."""
        if request_id:
            request_id_context.set(request_id)
        if user_id:
            user_id_context.set(user_id)
        if trace_id:
            trace_id_context.set(trace_id)
        if event_type:
            event_type_context.set(event_type)
    
    def clear_context(self):
        """Clear all logging context."""
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
        event_type_context.set(None)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current logging context as dictionary."""
        context = {}
        
        request_id = request_id_context.get()
        if request_id:
            context['request_id'] = request_id
            
        user_id = user_id_context.get()
        if user_id:
            context['user_id'] = user_id
            
        trace_id = trace_id_context.get()
        if trace_id:
            context['trace_id'] = trace_id
            
        event_type = event_type_context.get()
        if event_type:
            context['event_type'] = event_type
        
        return context
    
    @contextmanager
    def request_context(self, request_id: str, user_id: Optional[str] = None, 
                       trace_id: Optional[str] = None, event_type: Optional[str] = None):
        """Context manager for request-scoped logging."""
        # Save current context
        old_request = request_id_context.get()
        old_user = user_id_context.get()
        old_trace = trace_id_context.get()
        old_event = event_type_context.get()
        
        # Set new context
        request_id_context.set(request_id)
        if user_id:
            user_id_context.set(user_id)
        if trace_id:
            trace_id_context.set(trace_id)
        if event_type:
            event_type_context.set(event_type)
        
        try:
            yield
        finally:
            # Restore old context
            request_id_context.set(old_request)
            user_id_context.set(old_user)
            trace_id_context.set(old_trace)
            event_type_context.set(old_event)


class UnifiedLoggingSSOT:
    """
    SSOT Unified Logger - Single source of truth for ALL logging.
    
    This class consolidates features from:
    - UnifiedLoggerFactory (factory patterns)
    - AnalyticsLogger (structured logging)
    - UnifiedLogger (core implementation)
    - Cloud Run logging (GCP optimization)
    
    This is the ONLY logger class that should be used across the platform.
    """
    
    _instance: Optional['UnifiedLoggingSSOT'] = None
    _initialized = False
    
    def __new__(cls) -> 'UnifiedLoggingSSOT':
        """Ensure singleton pattern for SSOT compliance."""
        if cls._instance is None:
            cls._instance = super(UnifiedLoggingSSOT, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize SSOT logger with consolidated configuration."""
        if self._initialized:
            return
            
        self._config = None
        self._config_loaded = False
        self._filter = SensitiveDataFilter()
        self._context = UnifiedLoggingContext()
        
        # GCP Error Reporter integration (lazy initialization)
        self._gcp_reporter = None
        self._gcp_enabled = self._should_enable_gcp_reporting()
        self._gcp_initialized = False
        
        # Service identification
        self._service_name = self._infer_service_name()
        
        # Don't setup logging during init to avoid circular imports
        self._initialized = True
    
    def _infer_service_name(self) -> str:
        """Infer service name from environment and process context."""
        env = IsolatedEnvironment.get_instance()
        
        # Check for explicit service name
        service_name = env.get('SERVICE_NAME')
        if service_name:
            return service_name
            
        # Infer from the main module path
        main_module = sys.modules.get('__main__')
        if main_module and hasattr(main_module, '__file__'):
            main_file = Path(main_module.__file__)
            
            # Check service directories
            if 'auth_service' in str(main_file):
                return 'auth-service'
            elif 'analytics_service' in str(main_file):
                return 'analytics-service'
            elif 'dev_launcher' in str(main_file):
                return 'dev-launcher'
            elif 'netra_backend' in str(main_file):
                return 'netra-backend'
            elif 'test' in str(main_file) or 'pytest' in str(main_file):
                return 'test-runner'
        
        return 'netra-service'
    
    def _should_enable_gcp_reporting(self) -> bool:
        """Determine if GCP error reporting should be enabled."""
        env = IsolatedEnvironment.get_instance()
        
        # Never enable in testing mode
        if self._is_testing_mode():
            return False
            
        # Check environment markers
        is_cloud_run = env.get('K_SERVICE') is not None
        environment = env.get('ENVIRONMENT', 'development').lower()
        is_staging_or_prod = environment in ['staging', 'production']
        is_explicitly_enabled = env.get('ENABLE_GCP_ERROR_REPORTING', '').lower() == 'true'
        
        return is_cloud_run or is_staging_or_prod or is_explicitly_enabled
    
    def _is_testing_mode(self) -> bool:
        """Check if we're currently in testing mode."""
        env = IsolatedEnvironment.get_instance()
        return env.get('TESTING') == '1' or env.get('ENVIRONMENT') == 'testing'
    
    def _load_config(self) -> Dict[str, Any]:
        """Load unified logging configuration with fallback."""
        if self._config_loaded and self._config is not None:
            return self._config
        
        env = IsolatedEnvironment.get_instance()
        
        # Check if secrets are loading
        if env.get('NETRA_SECRETS_LOADING') == 'true':
            return self._get_fallback_config()
            
        try:
            # Try to get advanced config from unified config manager
            from netra_backend.app.core.configuration import unified_config_manager
            
            if hasattr(unified_config_manager, '_loading') and unified_config_manager._loading:
                loaded_config = self._get_fallback_config()
            else:
                config = unified_config_manager.get_config()
                loaded_config = {
                    'log_level': getattr(config, 'log_level', 'INFO').upper(),
                    'enable_file_logging': getattr(config, 'enable_file_logging', False),
                    'enable_json_logging': self._should_use_json_logging(),
                    'log_file_path': getattr(config, 'log_file_path', f'logs/{self._service_name}.log')
                }
        except (ImportError, Exception):
            loaded_config = self._get_fallback_config()
        
        self._config = loaded_config
        self._config_loaded = True
        return loaded_config
    
    def _should_use_json_logging(self) -> bool:
        """Determine if JSON logging should be used (Cloud Run optimization)."""
        env = IsolatedEnvironment.get_instance()
        
        # Force JSON logging for GCP environments
        is_cloud_run = env.get('K_SERVICE') is not None
        environment = env.get('ENVIRONMENT', 'development').lower()
        is_gcp = is_cloud_run or environment in ['staging', 'production']
        
        return is_gcp
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration for bootstrap and error scenarios."""
        env = IsolatedEnvironment.get_instance()
        
        return {
            'log_level': env.get('LOG_LEVEL', 'INFO').upper(),
            'enable_file_logging': False,  # Never enable file logging in fallback
            'enable_json_logging': self._should_use_json_logging(),
            'log_file_path': f'logs/{self._service_name}.log'
        }
    
    def _setup_logging(self):
        """Initialize the unified logging system."""
        if hasattr(self, '_setup_complete') and self._setup_complete:
            return
            
        # Load configuration
        self._config = self._load_config()
        
        # Configure Cloud Run specific settings
        self._configure_cloud_run_logging()
        
        # Configure handlers based on environment
        self._configure_handlers()
        
        # Set up exception handler for GCP
        self._setup_exception_handler()
        
        # Skip stdlib interception during testing
        if not self._is_testing_mode():
            self._setup_stdlib_interception()
        
        self._setup_complete = True
    
    def _configure_cloud_run_logging(self):
        """Configure logging for Cloud Run environments (anti-ANSI)."""
        env = IsolatedEnvironment.get_instance()
        
        # Disable colored output in environment
        env.set('NO_COLOR', '1', source='cloud_run_logging')
        env.set('FORCE_COLOR', '0', source='cloud_run_logging')
        env.set('PY_COLORS', '0', source='cloud_run_logging')
        
        # Disable colored tracebacks in Python 3.11+
        if hasattr(sys, '_xoptions'):
            sys._xoptions['no_debug_ranges'] = True
        
        # Disable colorama if present
        try:
            import colorama
            colorama.init(strip=True, convert=False)
        except ImportError:
            pass
    
    def _configure_handlers(self):
        """Configure unified logging handlers."""
        is_testing = self._is_testing_mode()
        
        # Remove existing handlers safely
        try:
            logger.remove()
        except (ValueError, OSError, AttributeError):
            pass
        
        # Minimal handler for testing
        if is_testing:
            logger.add(
                sink=lambda message: None,  # No-op sink for tests
                level="ERROR",
                filter=self._should_log_record
            )
            return
        
        # Suppress SQLAlchemy verbose logging unless in TRACE mode
        if self._config['log_level'] != 'TRACE':
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
        
        # Configure console handler with proper formatting
        if self._config['enable_json_logging']:
            # JSON format for GCP Cloud Run - use custom sink to avoid format string issues
            def json_sink(message):
                """Custom sink that outputs JSON directly to stdout."""
                json_formatter = self._get_json_formatter()
                json_output = json_formatter(message.record)
                sys.stdout.write(json_output + '\n')
                sys.stdout.flush()
            
            logger.add(
                sink=json_sink,
                level=self._config['log_level'],
                filter=self._should_log_record,
                serialize=False  # We handle JSON serialization in the sink
            )
        else:
            # Human-readable format for development
            logger.add(
                sys.stdout,
                level=self._config['log_level'],
                format=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self._service_name} - {{name}} - {{level}} - {{message}}",
                filter=self._should_log_record
            )
        
        # Add file handler if enabled
        if self._config['enable_file_logging']:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            logger.add(
                self._config['log_file_path'],
                level=self._config['log_level'],
                format=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self._service_name} - {{name}} - {{level}} - {{message}}",
                filter=self._should_log_record,
                rotation="100 MB",
                retention="30 days"
            )
    
    def _get_json_formatter(self):
        """Get JSON formatter for GCP Cloud Run compatibility."""
        def json_formatter(record):
            """Format log record as JSON for GCP Cloud Logging."""
            # Extract context
            context = self._context.get_context()
            
            # Build log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'severity': record['level'].name,
                'service': self._service_name,
                'logger': record.get('name', 'root'),
                'message': record['message']
            }
            
            # Add context if present
            if context:
                log_entry.update(context)
            
            # Add extra data
            if record.get('extra'):
                log_entry.update(record['extra'])
            
            # Add exception info if present
            if record['exception']:
                log_entry['error'] = {
                    'type': record['exception'].type.__name__,
                    'message': str(record['exception'].value),
                    'traceback': record['exception'].traceback
                }
            
            return json.dumps(log_entry, separators=(',', ':'))
        
        return json_formatter
    
    def _should_log_record(self, record) -> bool:
        """Determine if a log record should be processed."""
        # Filter based on level
        level_hierarchy = {
            'TRACE': 0, 'DEBUG': 1, 'INFO': 2, 
            'WARNING': 3, 'ERROR': 4, 'CRITICAL': 5
        }
        
        current_level = level_hierarchy.get(self._config['log_level'], 2)
        record_level = level_hierarchy.get(record['level'].name, 2)
        
        return record_level >= current_level
    
    def _setup_exception_handler(self):
        """Set up custom exception handler for GCP environments."""
        env = IsolatedEnvironment.get_instance()
        environment = env.get('ENVIRONMENT', 'development').lower()
        
        if environment not in ['staging', 'production']:
            return
        
        def exception_handler(exc_type, exc_value, exc_traceback):
            """Custom exception handler with JSON output for GCP."""
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            if self._config['enable_json_logging']:
                # JSON format for GCP Cloud Logging
                import traceback
                tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                traceback_str = ''.join(tb_lines).replace('\n', '\\n').replace('\r', '')
                
                error_entry = {
                    'severity': 'CRITICAL',
                    'message': f"Uncaught exception: {exc_type.__name__}: {str(exc_value)}",
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'service': self._service_name,
                    'error': {
                        'type': exc_type.__name__,
                        'message': str(exc_value),
                        'traceback': traceback_str
                    }
                }
                
                sys.stderr.write(json.dumps(error_entry, separators=(',', ':')) + '\n')
                sys.stderr.flush()
            else:
                # Standard format without colors
                import traceback
                tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                clean_lines = [re.sub(r'\x1b\[[0-9;]*m', '', line) for line in tb_lines]
                sys.stderr.write(''.join(clean_lines))
        
        sys.excepthook = exception_handler
    
    def _setup_stdlib_interception(self):
        """Set up standard library logging interception."""
        # Intercept standard logging calls and route to loguru
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level if it exists
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # Find caller from where logging call originated
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    def _ensure_gcp_reporter_initialized(self):
        """Lazy initialization of GCP Error Reporter."""
        if not self._gcp_enabled or self._gcp_initialized:
            return
            
        try:
            from netra_backend.app.services.monitoring.gcp_error_reporter import get_error_reporter
            self._gcp_reporter = get_error_reporter()
            self._gcp_initialized = True
            
            if not self._is_testing_mode():
                logger.info(f"[GCP Integration] Error Reporter enabled for {self._service_name}")
                
        except Exception as e:
            logger.error(f"[GCP Integration] Error Reporter initialization failed: {e}")
            self._gcp_enabled = False
            self._gcp_initialized = True
    
    def get_logger(self, name: Optional[str] = None):
        """Get a logger instance - SSOT interface."""
        if not hasattr(self, '_setup_complete'):
            self._setup_logging()
            
        return logger.bind(name=name, service=self._service_name) if name else logger.bind(service=self._service_name)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with SSOT filtering."""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with SSOT filtering."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with SSOT filtering."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, exc_info: bool = True, exception: Optional[Exception] = None, **kwargs):
        """Log error message with SSOT filtering and GCP reporting."""
        self._log("ERROR", message, exc_info=exc_info, exception=exception, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with SSOT filtering and GCP reporting."""
        self._log("CRITICAL", message, exc_info=exc_info, exception=exception, **kwargs)
    
    def _log(self, level: str, message: str, exc_info: bool = False, exception: Optional[Exception] = None, **kwargs):
        """Internal SSOT logging method with unified filtering and context."""
        # Apply SSOT filtering
        filtered_message = self._filter.filter_message(message)
        filtered_kwargs = self._filter.filter_dict(kwargs)
        
        # Add SSOT context
        context = self._context.get_context()
        context.update(filtered_kwargs)
        
        # Ensure logging is set up
        if not hasattr(self, '_setup_complete'):
            self._setup_logging()
        
        # Emit log message
        log_method = getattr(logger, level.lower())
        if exc_info and self._has_exception_info():
            log_method(filtered_message, **context)
        else:
            log_method(filtered_message, **context)
        
        # Auto-report to GCP for ERROR and CRITICAL levels
        if level.upper() in ['ERROR', 'CRITICAL'] and self._gcp_enabled:
            self._ensure_gcp_reporter_initialized()
            if self._gcp_reporter:
                self._report_to_gcp(filtered_message, level, exception, context)
    
    def _has_exception_info(self) -> bool:
        """Check if current exception info is available."""
        return sys.exc_info()[0] is not None
    
    def _report_to_gcp(self, message: str, level: str, exception: Optional[Exception], context: Dict[str, Any]):
        """Report to GCP Error Reporting with SSOT context."""
        try:
            # Map log level to GCP severity
            from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
            
            level_mapping = {
                'CRITICAL': ErrorSeverity.CRITICAL,
                'ERROR': ErrorSeverity.ERROR,
                'WARNING': ErrorSeverity.WARNING,
                'INFO': ErrorSeverity.INFO,
                'DEBUG': ErrorSeverity.INFO
            }
            severity = level_mapping.get(level.upper(), ErrorSeverity.ERROR)
            
            # Build unified context
            extra_context = {
                'log_level': level.upper(),
                'service': self._service_name,
                'logger_name': 'unified_logging_ssot',
                'integration_source': 'ssot_auto_report'
            }
            extra_context.update(context)
            
            user_id = context.get('user_id')
            
            if exception:
                self._gcp_reporter.report_exception(
                    exception,
                    user=user_id,
                    extra_context=extra_context
                )
            else:
                self._gcp_reporter.report_message(
                    message,
                    severity=severity,
                    user=user_id,
                    extra_context=extra_context
                )
                
        except Exception as e:
            # Safe failure - don't break logging
            logger.error(f"[GCP Integration] Failed to report to GCP: {e}")
    
    def set_context(self, **context_kwargs):
        """Set SSOT logging context."""
        self._context.set_context(**context_kwargs)
    
    def clear_context(self):
        """Clear SSOT logging context."""
        self._context.clear_context()
    
    def get_context(self) -> Dict[str, Any]:
        """Get current SSOT logging context."""
        return self._context.get_context()
    
    @contextmanager
    def request_context(self, **context_kwargs):
        """SSOT request context manager."""
        with self._context.request_context(**context_kwargs):
            yield
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics with SSOT context."""
        perf_context = {
            'operation': operation,
            'duration_seconds': duration,
            'performance_metric': True
        }
        perf_context.update(kwargs)
        self.info(f"Performance: {operation} completed in {duration:.3f}s", **perf_context)
    

    def log_api_call(self, method: str, url: str, status_code: int, duration: float, **kwargs):
        """Log API call details with SSOT context."""
        api_context = {
            'api_method': method,
            'api_url': url,
            'api_status_code': status_code,
            'api_duration_seconds': duration,
            'api_call_metric': True
        }
        api_context.update(kwargs)
        log_level = 'WARNING' if status_code >= 400 else 'INFO'
        message = f'API Call: {method} {url} -> {status_code} ({duration:.3f}s)'
        
        if log_level == 'WARNING':
            self.warning(message, **api_context)
        else:
            self.info(message, **api_context)
    
    def get_execution_time_decorator(self):
        """Get execution time decorator for backward compatibility."""
        def execution_time_decorator(operation_name: str):
            """Decorator to log execution time."""
            def decorator(func):
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = datetime.utcnow()
                    try:
                        result = func(*args, **kwargs)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.log_performance(operation_name, duration)
                        return result
                    except Exception as e:
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.error(f'Operation {operation_name} failed after {duration:.3f}s: {e}')
                        raise
                
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = datetime.utcnow()
                    try:
                        result = await func(*args, **kwargs)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.log_performance(operation_name, duration)
                        return result
                    except Exception as e:
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.error(f'Operation {operation_name} failed after {duration:.3f}s: {e}')
                        raise
                
                # Return appropriate wrapper based on function type
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    return async_wrapper
                else:
                    return sync_wrapper
            return decorator
        return execution_time_decorator

    async def shutdown(self):
        """Gracefully shutdown SSOT logging system."""
        await logger.complete()


# SSOT Global Instance - Singleton
_ssot_logger_instance: Optional[UnifiedLoggingSSOT] = None


def get_ssot_logger() -> UnifiedLoggingSSOT:
    """Get the SSOT logger instance - ONLY function for logger access."""
    global _ssot_logger_instance
    if _ssot_logger_instance is None:
        _ssot_logger_instance = UnifiedLoggingSSOT()
    return _ssot_logger_instance


def get_logger(name: Optional[str] = None):
    """
    SSOT Logger Interface - Replaces ALL logging patterns.
    
    This function replaces ALL instances of:
    - import logging; logger = logging.getLogger(__name__)
    - from netra_backend.app.logging_config import central_logger
    - from shared.logging.unified_logger_factory import get_logger
    - Any other logging initialization patterns
    
    Usage:
        from shared.logging.unified_logging_ssot import get_logger
        logger = get_logger(__name__)  # or just get_logger()
    """
    ssot_logger = get_ssot_logger()
    return ssot_logger.get_logger(name)


def log_performance(operation: str):
    """SSOT Performance logging decorator."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            ssot_logger = get_ssot_logger()
            start_time = datetime.utcnow()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                ssot_logger.log_performance(operation, duration, function=func.__name__, status="success")
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                ssot_logger.error(
                    f"Performance: {operation} failed in {duration:.3f}s",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="error",
                    error_type=type(e).__name__,
                    exception=e
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            ssot_logger = get_ssot_logger()
            start_time = datetime.utcnow()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                ssot_logger.log_performance(operation, duration, function=func.__name__, status="success")
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                ssot_logger.error(
                    f"Performance: {operation} failed in {duration:.3f}s",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="error",
                    error_type=type(e).__name__,
                    exception=e
                )
                raise
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# SSOT Context Manager - Global Access
def request_context(**context_kwargs):
    """SSOT request context manager - global access."""
    ssot_logger = get_ssot_logger()
    return ssot_logger.request_context(**context_kwargs)


# Reset function for testing
def reset_logging():
    """Reset SSOT logging configuration (for testing)."""
    global _ssot_logger_instance
    if _ssot_logger_instance:
        _ssot_logger_instance = None


# Export SSOT interfaces only
__all__ = [
    'get_logger',              # Primary SSOT interface
    'get_ssot_logger',         # Advanced SSOT interface
    'log_performance',         # Performance decorator
    'request_context',         # Context manager
    'reset_logging',           # Testing utility
    'UnifiedLoggingSSOT',      # Core SSOT class
    'SensitiveDataFilter',     # Utility class
    'UnifiedLoggingContext'    # Utility class
]