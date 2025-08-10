"""Unified, optimized logging system for Netra backend with security and performance improvements."""

import os
import re
import logging
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps
from contextvars import ContextVar

from loguru import logger
from pydantic import BaseModel, Field


# Context variables for request tracking
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class SensitiveDataFilter:
    """Filter sensitive data from log messages."""
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        (r'(password|passwd|pwd|pass)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(api[_\-]?key|apikey)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(secret|token|bearer)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(authorization|auth)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(access[_\-]?token)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(refresh[_\-]?token)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(private[_\-]?key)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        (r'(jwt|JWT)[\s:=]+"?([^"\s]+)"?', r'\1=REDACTED'),
        # Credit card patterns
        (r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', 'XXXX-XXXX-XXXX-XXXX'),
        # SSN patterns
        (r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX'),
        # Email addresses (partial redaction)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'***@\2'),
    ]
    
    # Fields to redact in structured data
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'pass',
        'api_key', 'apikey', 'api-key',
        'secret', 'token', 'bearer',
        'authorization', 'auth',
        'access_token', 'refresh_token',
        'private_key', 'jwt',
        'credit_card', 'card_number',
        'ssn', 'social_security',
        'email', 'phone', 'address'
    }
    
    @classmethod
    def filter_message(cls, message: str) -> str:
        """Filter sensitive data from a log message."""
        if not message:
            return message
            
        filtered = message
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        return filtered
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from a dictionary."""
        if not data:
            return data
            
        filtered = {}
        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS):
                filtered[key] = 'REDACTED'
            elif isinstance(value, dict):
                filtered[key] = cls.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    cls.filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                filtered[key] = cls.filter_message(value)
            else:
                filtered[key] = value
        return filtered


class LogEntry(BaseModel):
    """Structured log entry with context."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str
    message: str
    module: str
    function: Optional[str] = None
    line: Optional[int] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "backend"
    context: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UnifiedLogger:
    """Unified logger with security, performance, and observability features."""
    
    def __init__(self):
        self._initialized = False
        self._log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self._enable_file_logging = os.environ.get("ENABLE_FILE_LOGGING", "false").lower() == "true"
        self._enable_json_logging = os.environ.get("ENABLE_JSON_LOGGING", "false").lower() == "true"
        self._log_file_path = os.environ.get("LOG_FILE_PATH", "logs/netra.log")
        self._filter = SensitiveDataFilter()
        self._setup_logging()
    
    def _setup_logging(self):
        """Initialize the logging system."""
        if self._initialized:
            return
            
        # Remove default loguru handlers
        logger.remove()
        
        # Console handler with filtering
        self._add_console_handler()
        
        # File handler if enabled
        if self._enable_file_logging:
            self._add_file_handler()
        
        # Intercept standard library logging
        self._intercept_stdlib_logging()
        
        self._initialized = True
    
    def _add_console_handler(self):
        """Add console handler with appropriate formatting."""
        if self._enable_json_logging:
            # JSON format for production/structured logging
            logger.add(
                sys.stderr,
                format=self._json_formatter,
                level=self._log_level,
                filter=self._should_log,
                enqueue=True,  # Thread-safe async logging
                backtrace=True,
                diagnose=False  # Don't show variables in tracebacks (security)
            )
        else:
            # Human-readable format for development
            format_string = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )
            
            # Add context if available
            if request_id_context.get() or trace_id_context.get():
                format_string += " | <dim>{extra}</dim>"
            
            logger.add(
                sys.stderr,
                format=format_string,
                level=self._log_level,
                filter=self._should_log,
                enqueue=True,
                backtrace=True,
                diagnose=False
            )
    
    def _add_file_handler(self):
        """Add file handler with rotation."""
        Path(self._log_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            self._log_file_path,
            format=self._json_formatter if self._enable_json_logging else "{time} | {level} | {name}:{function}:{line} | {message}",
            level=self._log_level,
            filter=self._should_log,
            rotation="100 MB",
            retention="7 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=False
        )
    
    def _json_formatter(self, record):
        """Format log record as JSON with context."""
        entry = LogEntry(
            level=record["level"].name,
            message=self._filter.filter_message(record["message"]),
            module=record["name"],
            function=record["function"],
            line=record["line"],
            trace_id=trace_id_context.get(),
            request_id=request_id_context.get(),
            user_id=user_id_context.get(),
            context=self._filter.filter_dict(record.get("extra", {}))
        )
        
        # Add exception info if present
        if record["exception"]:
            exc_info = record["exception"]
            entry.error_details = {
                "type": exc_info.type.__name__ if exc_info.type else None,
                "value": str(exc_info.value) if exc_info.value else None,
                "traceback": exc_info.traceback if exc_info.traceback else None
            }
        
        return entry.json() + "\n"
    
    def _should_log(self, record):
        """Filter to determine if a message should be logged."""
        # Always log errors and above
        if record["level"].no >= logger.level("ERROR").no:
            return True
        
        # Filter out noisy modules in production
        if os.environ.get("ENVIRONMENT") == "production":
            noisy_modules = {"uvicorn.access", "uvicorn.error", "watchfiles"}
            if any(record["name"].startswith(module) for module in noisy_modules):
                return record["level"].no >= logger.level("WARNING").no
        
        return True
    
    def _intercept_stdlib_logging(self):
        """Redirect standard library logging to loguru."""
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # Find caller from where originated the logged message
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )
        
        # Set up interception
        logging.basicConfig(handlers=[InterceptHandler()], level=0)
        
        # Redirect specific loggers
        for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy", "faker"]:
            logging.getLogger(name).handlers = [InterceptHandler()]
    
    def get_logger(self, name: Optional[str] = None):
        """Get a logger instance with the given name."""
        if name:
            return logger.bind(name=name)
        return logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, exc_info: bool = True, **kwargs):
        """Log error message with context and exception info."""
        self._log("ERROR", message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """Log critical message with context and exception info."""
        self._log("CRITICAL", message, exc_info=exc_info, **kwargs)
    
    def _log(self, level: str, message: str, exc_info: bool = False, **kwargs):
        """Internal logging method with filtering and context."""
        # Filter sensitive data
        filtered_message = self._filter.filter_message(message)
        filtered_kwargs = self._filter.filter_dict(kwargs)
        
        # Add context
        context = {
            "trace_id": trace_id_context.get(),
            "request_id": request_id_context.get(),
            "user_id": user_id_context.get(),
            **filtered_kwargs
        }
        
        # Remove None values
        context = {k: v for k, v in context.items() if v is not None}
        
        # Log with appropriate level
        log_method = getattr(logger, level.lower())
        if exc_info and sys.exc_info()[0] is not None:
            log_method(filtered_message, exc_info=True, **context)
        else:
            log_method(filtered_message, **context)
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics."""
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_api_call(self, method: str, url: str, status_code: int, duration: float, **kwargs):
        """Log API call details."""
        self.info(
            f"API Call: {method} {url} -> {status_code}",
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def set_context(self, request_id: Optional[str] = None, 
                    user_id: Optional[str] = None,
                    trace_id: Optional[str] = None):
        """Set logging context for the current async context."""
        if request_id:
            request_id_context.set(request_id)
        if user_id:
            user_id_context.set(user_id)
        if trace_id:
            trace_id_context.set(trace_id)
    
    def clear_context(self):
        """Clear logging context."""
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
    
    async def shutdown(self):
        """Gracefully shutdown logging system."""
        await logger.complete()


# Performance monitoring decorator
def log_execution_time(operation_name: Optional[str] = None):
    """Decorator to log function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                duration = asyncio.get_event_loop().time() - start_time
                central_logger.log_performance(name, duration, status="success")
                return result
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                central_logger.log_performance(name, duration, status="error", error=str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                central_logger.log_performance(name, duration, status="success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                central_logger.log_performance(name, duration, status="error", error=str(e))
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global logger instance
central_logger = UnifiedLogger()

# Convenience function for backward compatibility
def get_central_logger() -> UnifiedLogger:
    """Get the central logger instance."""
    return central_logger