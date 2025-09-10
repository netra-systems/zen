"""Logging formatters and output handlers for the unified logging system.

This module handles:
- Sensitive data filtering
- JSON formatting for structured logging
- Console formatting for development
- Log entry model definitions
"""

import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from netra_backend.app.core.logging_context import (
    request_id_context,
    trace_id_context,
    user_id_context,
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
        return entry.model_dump_json() + "\n"
    
    def _format_traceback_for_gcp(self, exc_traceback) -> Optional[str]:
        """Format traceback object into readable string for GCP logging.
        
        Handles both standard Python tracebacks and Loguru exception structures.
        Returns single-line string with escaped newlines for GCP compatibility.
        
        Args:
            exc_traceback: Traceback object or None
            
        Returns:
            Formatted traceback string or None if no traceback available
        """
        if not exc_traceback:
            return None
            
        try:
            import traceback
            # Convert traceback object to readable string format
            traceback_lines = traceback.format_tb(exc_traceback)
            if traceback_lines:
                # Join all lines and escape newlines for single-line JSON
                traceback_str = ''.join(traceback_lines)
                return traceback_str.replace('\n', '\\n').replace('\r', '\\r')
            else:
                return None
        except Exception as e:
            # Fallback for any traceback processing errors
            return f"Traceback processing error: {str(e)}"
    
    def gcp_json_formatter(self, record) -> str:
        """Format log record as GCP Cloud Logging compatible JSON.
        
        GCP expects specific fields for proper severity mapping:
        - severity: Must use GCP severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL, etc.)
        - message: The log message
        - timestamp: ISO 8601 format timestamp
        - Additional fields for context
        """
        import json
        from datetime import datetime, timezone
        
        # Map loguru levels to GCP severity levels
        severity_mapping = {
            'TRACE': 'DEBUG',
            'DEBUG': 'DEBUG', 
            'INFO': 'INFO',
            'SUCCESS': 'INFO',
            'WARNING': 'WARNING',
            'ERROR': 'ERROR',
            'CRITICAL': 'CRITICAL'
        }
        
        # Safely handle Loguru record structure
        # In Loguru, record is a dict-like object with specific attributes
        try:
            # Handle None or invalid record
            if not record or not hasattr(record, 'get'):
                raise ValueError(f"Invalid record type: {type(record)}")
            
            # Safely get level name - level is a namedtuple with .name, .no, .icon attributes
            level = record.get("level", {})
            if hasattr(level, 'name'):
                level_name = level.name
            elif isinstance(level, str):
                level_name = level
            elif isinstance(level, dict) and 'name' in level:
                level_name = level['name']
            else:
                level_name = 'DEFAULT'
            
            # Safely get timestamp - Loguru provides datetime object
            time_obj = record.get("time")
            if hasattr(time_obj, 'isoformat'):
                timestamp = time_obj.isoformat()
            elif isinstance(time_obj, str):
                timestamp = time_obj
            else:
                timestamp = str(time_obj) if time_obj else datetime.now(timezone.utc).isoformat()
            
            # Safely get message
            message = record.get("message", "")
            if not isinstance(message, str):
                message = str(message)
            
            # Safely get other fields
            module = record.get("name", "")
            function = record.get("function", "")
            line = record.get("line", "")
            
            # Ensure message is single-line by replacing newlines
            filtered_message = self._filter.filter_message(message)
            single_line_message = filtered_message.replace('\n', '\\n').replace('\r', '\\r')
            
            gcp_entry = {
                'severity': severity_mapping.get(level_name, 'DEFAULT'),
                'message': single_line_message,
                'timestamp': timestamp,
                'labels': {
                    'module': str(module) if module else "",
                    'function': str(function) if function else "",
                    'line': str(line) if line else ""
                }
            }
        except Exception as e:
            # Fallback for any unexpected record structure
            import traceback
            # datetime already imported at top of function
            # Ensure error message is single-line  
            error_message = f"Logging formatter error: {str(e)} | Original message: {record.get('message', 'N/A') if isinstance(record, dict) else 'N/A'}"
            single_line_error_message = error_message.replace('\n', '\\n').replace('\r', '\\r')
            single_line_traceback = traceback.format_exc().replace('\n', '\\n').replace('\r', '\\r')
            
            gcp_entry = {
                'severity': 'ERROR',
                'message': single_line_error_message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'labels': {
                    'module': 'logging_formatter',
                    'function': 'gcp_json_formatter',
                    'line': '0',
                    'formatter_error': str(e).replace('\n', '\\n').replace('\r', '\\r'),
                    'traceback': single_line_traceback
                }
            }
        
        # Add context if available (but only if record was valid)
        if isinstance(record, dict) or hasattr(record, 'get'):
            if trace_id := trace_id_context.get():
                gcp_entry['trace'] = trace_id
            if request_id := request_id_context.get():
                gcp_entry['labels']['request_id'] = request_id
            if user_id := user_id_context.get():
                gcp_entry['labels']['user_id'] = user_id
            
            # Add extra context
            if hasattr(record, 'get'):
                if extra := record.get("extra"):
                    filtered_extra = self._filter.filter_dict(extra)
                    if filtered_extra:
                        gcp_entry['context'] = filtered_extra
                
                # Add exception info if present
                if exc := record.get("exception"):
                    if exc and hasattr(exc, 'type'):
                        # Format traceback using proper extraction method
                        traceback_str = None
                        if hasattr(exc, 'traceback') and exc.traceback:
                            traceback_str = self._format_traceback_for_gcp(exc.traceback)
                        
                        gcp_entry['error'] = {
                            'type': exc.type.__name__ if hasattr(exc, 'type') and exc.type else None,
                            'value': str(exc.value) if hasattr(exc, 'value') and exc.value else None,
                            'traceback': traceback_str
                        }
        
        # Use separators to minimize JSON size and ensure single line
        return json.dumps(gcp_entry, separators=(',', ':'), ensure_ascii=False)
    
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
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    def _has_context(self) -> bool:
        """Check if context variables are available."""
        return request_id_context.get() or trace_id_context.get()
    
    def get_file_format(self, enable_json: bool):
        """Get format string for file output."""
        if enable_json:
            return "{message}"  # Simple format, JSON serialization happens separately
        return "{time} | {level} | {name}:{function}:{line} | {message}"




class LogHandlerConfig:
    """Configuration for log handlers."""
    
    def __init__(self, level: str, enable_json: bool = False):
        self.level = level
        self.enable_json = enable_json
        self.formatter = LogFormatter(SensitiveDataFilter())
    
    def add_console_handler(self, should_log_func):
        """Add console handler with appropriate formatting."""
        # During testing, use safer console handling to prevent I/O errors
        from shared.isolated_environment import get_env
        is_testing = get_env().get('TESTING') == '1' or get_env().get('ENVIRONMENT') == 'testing'
        
        if is_testing:
            # During testing, completely skip console handlers to prevent I/O errors
            # Tests should not rely on console output anyway
            pass
        elif self.enable_json:
            self._add_json_console_handler(should_log_func)
        else:
            self._add_readable_console_handler(should_log_func)
    
    def _add_json_console_handler(self, should_log_func):
        """Add JSON format console handler with GCP Cloud Run support."""
        from shared.isolated_environment import get_env
        
        # Check if running in GCP Cloud Run
        is_cloud_run = get_env().get('K_SERVICE') is not None
        environment = get_env().get('ENVIRONMENT', 'development').lower()
        is_gcp = is_cloud_run or environment in ['staging', 'production']
        
        if is_gcp:
            # Use GCP-compatible JSON formatter with custom sink
            def gcp_sink(message):
                """Custom sink that writes formatted JSON to stderr."""
                # In Loguru, message.record is the record dict
                record = message.record if hasattr(message, 'record') else message
                try:
                    json_output = self.formatter.gcp_json_formatter(record)
                    # Ensure single-line output by removing any embedded newlines
                    single_line_json = json_output.replace('\n', '\\n').replace('\r', '\\r')
                    sys.stderr.write(single_line_json + "\n")
                    sys.stderr.flush()
                except Exception as e:
                    # Fallback to ensure logging doesn't fail completely
                    import json
                    from datetime import datetime, timezone
                    # Safely extract message and time from record
                    original_msg = 'N/A'
                    time_str = datetime.now(timezone.utc).isoformat()
                    if isinstance(record, dict):
                        original_msg = record.get('message', 'N/A')
                        time_obj = record.get('time')
                        if hasattr(time_obj, 'isoformat'):
                            time_str = time_obj.isoformat()
                        elif time_obj:
                            time_str = str(time_obj)
                    
                    fallback_entry = {
                        'severity': 'ERROR',
                        'message': f"Logging formatter error: {str(e)} | Original message: {original_msg}",
                        'timestamp': time_str,
                        'error_type': 'LogFormatterError'
                    }
                    json_output = json.dumps(fallback_entry, separators=(',', ':'))
                    # Ensure single-line output by removing any embedded newlines
                    single_line_json = json_output.replace('\n', '\\n').replace('\r', '\\r')
                    sys.stderr.write(single_line_json + "\n")
                    sys.stderr.flush()
            
            logger.add(
                gcp_sink,
                level=self.level,
                filter=should_log_func,
                enqueue=True,
                backtrace=True,
                diagnose=False,
                catch=True
            )
        else:
            # Use standard JSON formatter  
            logger.add(
                sys.stderr,
                format="{message}",
                serialize=self.formatter.json_formatter,
                level=self.level,
                filter=should_log_func,
                enqueue=True,
                backtrace=True,
                diagnose=False,
                catch=True
            )
    
    def _add_readable_console_handler(self, should_log_func):
        """Add human-readable console handler with proper color mapping."""
        from shared.isolated_environment import get_env
        
        # Disable colors in staging/production to prevent ANSI codes in logs
        environment = get_env().get('ENVIRONMENT', 'development').lower()
        should_colorize = environment not in ['staging', 'production', 'prod']
        
        # Use simpler format without color tags for staging/production
        if should_colorize:
            format_string = self.formatter.get_console_format()
        else:
            # Plain format without color tags for staging/production
            format_string = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            )
        
        logger.add(
            sys.stderr,
            format=format_string,
            level=self.level,
            filter=should_log_func,
            colorize=should_colorize,  # Disable colors in staging/production
            enqueue=True,
            backtrace=True,
            diagnose=False,
            catch=True  # Catch exceptions to prevent I/O errors from breaking tests
        )
    
    def add_file_handler(self, file_path: str, should_log_func):
        """Add file handler with rotation."""
        from pathlib import Path
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        if self.enable_json:
            logger.add(
                file_path,
                format="{message}",  # Simple format, JSON serialization happens in serialize
                serialize=self.formatter.json_formatter,
                level=self.level,
                filter=should_log_func,
                rotation="100 MB",
                retention="7 days",
                compression="zip",
                enqueue=True,
                backtrace=True,
                diagnose=False,
                catch=True  # Catch exceptions to prevent I/O errors from breaking tests
            )
        else:
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
                diagnose=False,
                catch=True  # Catch exceptions to prevent I/O errors from breaking tests
            )