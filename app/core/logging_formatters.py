"""Logging formatters and output handlers for the unified logging system.

This module handles:
- Sensitive data filtering
- JSON formatting for structured logging
- Console formatting for development
- Log entry model definitions
"""

import re
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from loguru import logger
from .logging_context import (
    request_id_context,
    user_id_context,
    trace_id_context
)


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
    
    model_config = ConfigDict()


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
        return cls._apply_patterns(message)
    
    @classmethod
    def _apply_patterns(cls, text: str) -> str:
        """Apply sensitive data patterns to filter text."""
        filtered = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        return filtered
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from a dictionary."""
        if not data:
            return data
        return cls._filter_dict_recursive(data)
    
    @classmethod
    def _filter_dict_recursive(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal recursive filtering method."""
        filtered = {}
        for key, value in data.items():
            filtered[key] = cls._filter_value(key, value)
        return filtered
    
    @classmethod
    def _filter_value(cls, key: str, value: Any) -> Any:
        """Filter a single value based on key and type."""
        if cls._is_sensitive_key(key):
            return 'REDACTED'
        elif isinstance(value, dict):
            return cls._filter_dict_recursive(value)
        elif isinstance(value, list):
            return cls._filter_list(value)
        elif isinstance(value, str):
            return cls.filter_message(value)
        else:
            return value
    
    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        """Check if a key contains sensitive information."""
        return any(sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS)
    
    @classmethod
    def _filter_list(cls, items: list) -> list:
        """Filter a list of items."""
        return [
            cls._filter_dict_recursive(item) if isinstance(item, dict) else item
            for item in items
        ]


class LogFormatter:
    """Handles log formatting for different output formats."""
    
    def __init__(self, filter_instance: SensitiveDataFilter):
        self._filter = filter_instance
    
    def json_formatter(self, record) -> str:
        """Format log record as JSON with context."""
        entry = self._create_log_entry(record)
        self._add_exception_info(record, entry)
        return entry.json() + "\n"
    
    def _create_log_entry(self, record) -> LogEntry:
        """Create a LogEntry from a loguru record."""
        return LogEntry(
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
    
    def _add_exception_info(self, record, entry: LogEntry):
        """Add exception details to log entry if present."""
        if record["exception"]:
            exc_info = record["exception"]
            entry.error_details = self._extract_exception_details(exc_info)
    
    def _extract_exception_details(self, exc_info) -> Dict[str, Any]:
        """Extract exception information for logging."""
        return {
            "type": exc_info.type.__name__ if exc_info.type else None,
            "value": str(exc_info.value) if exc_info.value else None,
            "traceback": exc_info.traceback if exc_info.traceback else None
        }
    
    def get_console_format(self) -> str:
        """Get human-readable format string for console output."""
        base_format = self._get_base_console_format()
        if self._has_context():
            return base_format + " | <dim>{extra}</dim>"
        return base_format
    
    def _get_base_console_format(self) -> str:
        """Get the base console format string."""
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    def _has_context(self) -> bool:
        """Check if context variables are available."""
        return request_id_context.get() or trace_id_context.get()
    
    def get_file_format(self, enable_json: bool) -> str:
        """Get format string for file output."""
        if enable_json:
            return self.json_formatter
        return "{time} | {level} | {name}:{function}:{line} | {message}"


class LogHandlerConfig:
    """Configuration for log handlers."""
    
    def __init__(self, level: str, enable_json: bool = False):
        self.level = level
        self.enable_json = enable_json
        self.formatter = LogFormatter(SensitiveDataFilter())
    
    def add_console_handler(self, should_log_func):
        """Add console handler with appropriate formatting."""
        if self.enable_json:
            self._add_json_console_handler(should_log_func)
        else:
            self._add_readable_console_handler(should_log_func)
    
    def _add_json_console_handler(self, should_log_func):
        """Add JSON format console handler."""
        logger.add(
            sys.stderr,
            format=self.formatter.json_formatter,
            level=self.level,
            filter=should_log_func,
            enqueue=True,
            backtrace=True,
            diagnose=False
        )
    
    def _add_readable_console_handler(self, should_log_func):
        """Add human-readable console handler."""
        def format_with_caller(record):
            # Use caller info if available, otherwise use standard
            extra = record.get('extra', {})
            if 'caller_module' in extra and 'caller_function' in extra and 'caller_line' in extra:
                location = f"{extra['caller_module']}:{extra['caller_function']}:{extra['caller_line']}"
            else:
                location = f"{record['name']}:{record['function']}:{record['line']}"
            
            time_str = record['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            level = record['level'].name
            message = self.formatter._filter.filter_message(record['message'])
            return f"{time_str} | {level:8} | {location} | {message}\n"
        
        logger.add(
            sys.stderr,
            format=format_with_caller,
            level=self.level,
            filter=should_log_func,
            enqueue=True,
            backtrace=True,
            diagnose=False
        )
    
    def add_file_handler(self, file_path: str, should_log_func):
        """Add file handler with rotation."""
        from pathlib import Path
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            file_path,
            format=self.formatter.get_file_format(self.enable_json),
            level=self.level,
            filter=should_log_func,
            rotation="100 MB",
            retention="7 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=False
        )