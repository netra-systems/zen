"""
Data Sanitization and PII Filtering

Comprehensive data sanitization to ensure no personally identifiable information
or sensitive data is included in telemetry traces.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SanitizationConfig:
    """Configuration for data sanitization"""
    # Patterns to redact (regex patterns)
    pii_patterns: List[str] = None
    # Fields to always redact
    sensitive_fields: List[str] = None
    # Maximum string length before truncation
    max_string_length: int = 1000
    # Maximum depth for nested objects
    max_depth: int = 10
    # Redaction placeholder
    redaction_placeholder: str = "[REDACTED]"
    # Whether to enable aggressive sanitization
    aggressive_mode: bool = True
    # Community analytics mode - extra anonymization
    community_mode: bool = False

    def __post_init__(self):
        if self.pii_patterns is None:
            self.pii_patterns = [
                # Email addresses
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                # Phone numbers (US format)
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                # Social Security Numbers
                r'\b\d{3}-\d{2}-\d{4}\b',
                # Credit card numbers (basic pattern)
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                # IP addresses
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
                # URLs with potential sensitive info
                r'https?://[^\s]+',
                # Potential API keys (long alphanumeric strings)
                r'\b[A-Za-z0-9]{32,}\b',
                # File paths that might contain usernames
                r'/Users/[^/\s]+',
                r'C:\\Users\\[^\\s]+',
                # UUIDs (might be sensitive)
                r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
            ]

        if self.sensitive_fields is None:
            self.sensitive_fields = [
                # Authentication related
                'password', 'passwd', 'pwd', 'secret', 'token', 'auth',
                'authorization', 'credential', 'key', 'api_key', 'apikey',
                'access_token', 'refresh_token', 'bearer', 'oauth',

                # Personal information
                'email', 'username', 'user_id', 'userid', 'ssn', 'sin',
                'phone', 'telephone', 'mobile', 'address', 'street',
                'zip', 'postal', 'city', 'state', 'country',

                # Financial
                'credit_card', 'creditcard', 'cc', 'account', 'bank',
                'routing', 'iban', 'swift',

                # Internal identifiers
                'session_id', 'sessionid', 'trace_id', 'span_id',
                'request_id', 'correlation_id',

                # Common sensitive prefixes/suffixes
                'private', 'internal', 'confidential'
            ]

        # Add community analytics patterns if in community mode
        if self.community_mode:
            # Additional patterns for community analytics anonymization
            self.pii_patterns.extend([
                # File paths (more aggressive for community)
                r'/[^/\s]+/[^/\s]+',  # Any nested path
                r'[A-Z]:\\[^\s]+',    # Windows paths
                # Hostnames and machine names
                r'\b[a-zA-Z0-9-]+\.(local|lan|corp|internal)\b',
                # Project names that might be sensitive
                r'(project|workspace|repo)[-_][a-zA-Z0-9]+',
            ])

            self.sensitive_fields.extend([
                # Additional fields for community anonymization
                'hostname', 'machine', 'computer', 'device',
                'workspace', 'project', 'repo', 'repository',
                'organization', 'org', 'company', 'client',
                'tenant', 'instance', 'environment', 'env'
            ])


class DataSanitizer:
    """
    Comprehensive data sanitizer for telemetry data

    Ensures no PII or sensitive information leaks into telemetry traces.
    """

    _config = SanitizationConfig()
    _compiled_patterns = None

    @classmethod
    def configure(cls, config: SanitizationConfig):
        """Configure sanitization settings"""
        cls._config = config
        cls._compiled_patterns = None  # Reset compiled patterns

    @classmethod
    def _get_compiled_patterns(cls):
        """Get compiled regex patterns (cached)"""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in cls._config.pii_patterns
            ]
        return cls._compiled_patterns

    @classmethod
    def sanitize_value(cls, value: Any, depth: int = 0) -> Any:
        """
        Sanitize a value recursively

        Args:
            value: Value to sanitize
            depth: Current recursion depth

        Returns:
            Sanitized value
        """
        # Prevent infinite recursion
        if depth > cls._config.max_depth:
            return "[MAX_DEPTH_EXCEEDED]"

        try:
            # Handle None
            if value is None:
                return None

            # Handle strings
            if isinstance(value, str):
                return cls._sanitize_string(value)

            # Handle numbers and booleans (pass through)
            if isinstance(value, (int, float, bool)):
                return value

            # Handle dictionaries
            if isinstance(value, dict):
                return cls._sanitize_dict(value, depth)

            # Handle lists/tuples
            if isinstance(value, (list, tuple)):
                return cls._sanitize_list(value, depth)

            # Handle other types by converting to string and sanitizing
            return cls._sanitize_string(str(value))

        except Exception as e:
            logger.debug(f"Error sanitizing value: {e}")
            return cls._config.redaction_placeholder

    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """Sanitize a string value"""
        if not text:
            return text

        # Truncate if too long
        if len(text) > cls._config.max_string_length:
            text = text[:cls._config.max_string_length] + "..."

        # Apply PII pattern matching
        sanitized = text
        for pattern in cls._get_compiled_patterns():
            sanitized = pattern.sub(cls._config.redaction_placeholder, sanitized)

        return sanitized

    @classmethod
    def _sanitize_dict(cls, data: dict, depth: int) -> dict:
        """Sanitize a dictionary"""
        sanitized = {}

        for key, value in data.items():
            # Check if key is sensitive
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in cls._config.sensitive_fields):
                sanitized[key] = cls._config.redaction_placeholder
            else:
                sanitized[key] = cls.sanitize_value(value, depth + 1)

        return sanitized

    @classmethod
    def _sanitize_list(cls, data: Union[list, tuple], depth: int) -> list:
        """Sanitize a list or tuple"""
        sanitized = [
            cls.sanitize_value(item, depth + 1)
            for item in data
        ]
        return sanitized

    @classmethod
    def sanitize_span_attributes(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize span attributes for telemetry

        Args:
            attributes: Dictionary of span attributes

        Returns:
            Sanitized attributes dictionary
        """
        if not attributes:
            return {}

        sanitized = {}
        for key, value in attributes.items():
            # Sanitize both key and value
            sanitized_key = cls._sanitize_string(str(key))
            sanitized_value = cls.sanitize_value(value)

            # Convert complex values to strings
            if not isinstance(sanitized_value, (str, int, float, bool, type(None))):
                sanitized_value = str(sanitized_value)

            sanitized[sanitized_key] = sanitized_value

        return sanitized

    @classmethod
    def sanitize_exception(cls, exception: Exception) -> Dict[str, str]:
        """
        Sanitize exception information

        Args:
            exception: Exception to sanitize

        Returns:
            Sanitized exception data
        """
        try:
            return {
                "exception.type": type(exception).__name__,
                "exception.message": cls._sanitize_string(str(exception)),
                "exception.module": getattr(type(exception), '__module__', 'unknown')
            }
        except Exception as e:
            logger.debug(f"Error sanitizing exception: {e}")
            return {
                "exception.type": "unknown",
                "exception.message": cls._config.redaction_placeholder
            }

    @classmethod
    def sanitize_error_context(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize error context information

        Args:
            context: Error context dictionary

        Returns:
            Sanitized context
        """
        if not context:
            return {}

        # Create sanitized copy
        sanitized = {}

        for key, value in context.items():
            # Special handling for common error context fields
            if key in ['traceback', 'stack_trace']:
                # Sanitize traceback information
                sanitized[key] = cls._sanitize_traceback(str(value))
            elif key in ['request', 'response']:
                # Handle HTTP request/response data
                sanitized[key] = cls._sanitize_http_data(value)
            else:
                sanitized[key] = cls.sanitize_value(value)

        return sanitized

    @classmethod
    def _sanitize_traceback(cls, traceback: str) -> str:
        """Sanitize traceback information"""
        if not traceback:
            return traceback

        # Remove file paths that might contain usernames
        sanitized = traceback

        # Remove user-specific paths
        path_patterns = [
            r'/Users/[^/\s]+',
            r'C:\\Users\\[^\\s]+',
            r'/home/[^/\s]+',
        ]

        for pattern in path_patterns:
            sanitized = re.sub(pattern, '/[USER]', sanitized, flags=re.IGNORECASE)

        return cls._sanitize_string(sanitized)

    @classmethod
    def _sanitize_http_data(cls, data: Any) -> Any:
        """Sanitize HTTP request/response data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = str(key).lower()

                # Redact sensitive HTTP headers and fields
                if key_lower in ['authorization', 'cookie', 'set-cookie', 'x-api-key']:
                    sanitized[key] = cls._config.redaction_placeholder
                elif 'token' in key_lower or 'auth' in key_lower:
                    sanitized[key] = cls._config.redaction_placeholder
                else:
                    sanitized[key] = cls.sanitize_value(value)
            return sanitized
        else:
            return cls.sanitize_value(data)

    @classmethod
    def is_sensitive_field(cls, field_name: str) -> bool:
        """
        Check if a field name is considered sensitive

        Args:
            field_name: Field name to check

        Returns:
            True if field is sensitive
        """
        field_lower = str(field_name).lower()
        return any(sensitive in field_lower for sensitive in cls._config.sensitive_fields)

    @classmethod
    def create_safe_identifier(cls, original: str, prefix: str = "id") -> str:
        """
        Create a safe, non-reversible identifier from an original value

        Args:
            original: Original identifier
            prefix: Prefix for the safe identifier

        Returns:
            Safe identifier
        """
        import hashlib

        # Create hash of the original value
        hash_obj = hashlib.sha256(original.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()

        # Return first 8 characters with prefix
        return f"{prefix}_{hash_hex[:8]}"


# Global sanitizer instance
sanitizer = DataSanitizer()