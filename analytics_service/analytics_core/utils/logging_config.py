"""Analytics Service Logging Configuration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational Excellence and Debug Capability  
- Value Impact: Enables effective monitoring and debugging of analytics data flow
- Strategic Impact: Critical for maintaining service reliability and performance visibility

Provides centralized logging configuration for the Analytics Service with:
- Structured logging for better observability
- Environment-specific log levels
- Request ID tracking for distributed tracing
- Performance monitoring capabilities
- Sensitive data filtering for compliance
"""

import logging
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Union
from pathlib import Path

import structlog


# Context variables for request tracing
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
event_type_context: ContextVar[Optional[str]] = ContextVar('event_type', default=None)


class SensitiveDataFilter:
    """Filter to remove sensitive data from log records."""
    
    # Fields that should never be logged
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'credit_card', 'ssn', 'email', 'phone', 'ip_address',
        'user_agent', 'session_id', 'auth_token'
    }
    
    @classmethod
    def filter_sensitive_data(cls, data: Any) -> Any:
        """Remove or mask sensitive data from log payload."""
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if isinstance(key, str) and any(
                    sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS
                ):
                    filtered[key] = "***REDACTED***"
                else:
                    filtered[key] = cls.filter_sensitive_data(value)
            return filtered
        elif isinstance(data, (list, tuple)):
            return [cls.filter_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            # Don't log potentially sensitive strings longer than 1000 chars
            if len(data) > 1000:
                return f"***LONG_STRING_REDACTED_{len(data)}_CHARS***"
        return data


class AnalyticsLogger:
    """Centralized logger for Analytics Service with security and performance features."""
    
    def __init__(self):
        self._initialized = False
        self._logger = None
        
    def _get_log_level(self) -> str:
        """Get log level from environment with sensible defaults."""
        env = os.getenv('ANALYTICS_ENV', 'development').lower()
        
        # Environment-specific log levels
        level_mapping = {
            'production': 'INFO',
            'staging': 'INFO', 
            'development': 'DEBUG',
            'test': 'WARNING'
        }
        
        # Allow override via explicit env var
        explicit_level = os.getenv('ANALYTICS_LOG_LEVEL')
        if explicit_level:
            return explicit_level.upper()
            
        return level_mapping.get(env, 'INFO')
    
    def _setup_structured_logging(self) -> None:
        """Configure structured logging with security filters."""
        if self._initialized:
            return
            
        # Configure structlog processors
        processors = [
            # Add context variables to log records
            self._add_context_processor,
            # Filter sensitive data
            self._filter_processor,
            # Add timestamps
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
        ]
        
        # Environment-specific formatting
        env = os.getenv('ANALYTICS_ENV', 'development').lower()
        if env == 'production':
            # JSON logging in production
            processors.append(structlog.processors.JSONRenderer())
        else:
            # Human-readable in development
            processors.append(structlog.dev.ConsoleRenderer())
            
        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure Python logging
        log_level = self._get_log_level()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(message)s",
            stream=sys.stdout,
        )
        
        self._logger = structlog.get_logger("analytics_service")
        self._initialized = True
    
    def _add_context_processor(self, logger, method_name, event_dict):
        """Add context variables to log records."""
        request_id = request_id_context.get()
        if request_id:
            event_dict['request_id'] = request_id
            
        user_id = user_id_context.get()
        if user_id:
            event_dict['user_id'] = user_id
            
        event_type = event_type_context.get()
        if event_type:
            event_dict['event_type'] = event_type
            
        # Add service identifier
        event_dict['service'] = 'analytics_service'
        
        return event_dict
    
    def _filter_processor(self, logger, method_name, event_dict):
        """Filter sensitive data from log records."""
        return SensitiveDataFilter.filter_sensitive_data(event_dict)
    
    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """Get a configured logger instance."""
        if not self._initialized:
            self._setup_structured_logging()
            
        if name:
            return self._logger.bind(module=name)
        return self._logger
    
    @contextmanager
    def request_context(self, request_id: str, user_id: Optional[str] = None, 
                       event_type: Optional[str] = None):
        """Context manager for request-scoped logging."""
        request_token = request_id_context.set(request_id)
        user_token = user_id_context.set(user_id) if user_id else None
        event_token = event_type_context.set(event_type) if event_type else None
        
        try:
            yield
        finally:
            request_id_context.reset(request_token)
            if user_token:
                user_id_context.reset(user_token)
            if event_token:
                event_type_context.reset(event_token)


# Global logger instance
analytics_logger = AnalyticsLogger()


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a configured logger for the Analytics Service."""
    return analytics_logger.get_logger(name)


def log_performance(operation: str):
    """Decorator to log performance metrics for operations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.utcnow()
            
            try:
                logger.debug("operation_started", operation=operation, function=func.__name__)
                result = await func(*args, **kwargs)
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    "operation_completed",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="success"
                )
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    "operation_failed",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    status="error"
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.utcnow()
            
            try:
                logger.debug("operation_started", operation=operation, function=func.__name__)
                result = func(*args, **kwargs)
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    "operation_completed",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="success"
                )
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    "operation_failed",
                    operation=operation,
                    function=func.__name__,
                    duration_seconds=duration,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    status="error"
                )
                raise
                
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# Context manager for request tracing
request_context = analytics_logger.request_context


# Export main interfaces
__all__ = [
    'get_logger',
    'log_performance', 
    'request_context',
    'analytics_logger',
    'SensitiveDataFilter'
]