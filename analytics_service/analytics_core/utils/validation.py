"""Analytics Service Data Validation Utilities

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (data quality and compliance)
- Business Goal: Data Integrity and Regulatory Compliance
- Value Impact: Ensures high-quality analytics data and protects customer PII
- Strategic Impact: Enables reliable AI insights and meets compliance requirements

Provides comprehensive validation utilities for:
- Event data validation and sanitization
- PII detection and removal for compliance
- Input sanitization for security
- Rate limit validation for resource protection
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    USER_AGENT = "user_agent"
    SESSION_ID = "session_id"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_data: Optional[Dict[str, Any]] = None
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)


class PIIDetector:
    """Detects and handles Personally Identifiable Information (PII)."""
    
    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        PIIType.PHONE: re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
        PIIType.SSN: re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        PIIType.CREDIT_CARD: re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        PIIType.IP_ADDRESS: re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        PIIType.SESSION_ID: re.compile(r'\b[a-fA-F0-9]{32,128}\b'),  # Common session ID patterns
    }
    
    # Sensitive field names (case-insensitive)
    SENSITIVE_FIELDS = {
        'email', 'mail', 'e_mail', 'email_address',
        'phone', 'telephone', 'mobile', 'phone_number',
        'ssn', 'social_security', 'social_security_number',
        'credit_card', 'creditcard', 'cc_number', 'card_number',
        'password', 'passwd', 'pwd', 'secret',
        'token', 'auth_token', 'access_token', 'bearer_token',
        'api_key', 'apikey', 'key',
        'session_id', 'sessionid', 'session',
        'user_agent', 'useragent', 'ua',
        'ip_address', 'ipaddress', 'ip', 'remote_addr',
        'authorization', 'auth'
    }
    
    @classmethod
    def detect_pii_in_text(cls, text: str) -> List[Tuple[PIIType, str]]:
        """Detect PII patterns in text content."""
        if not isinstance(text, str):
            return []
            
        detected = []
        for pii_type, pattern in cls.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = ''.join(match)  # Join tuple matches
                    detected.append((pii_type, match))
        
        return detected
    
    @classmethod
    def is_sensitive_field(cls, field_name: str) -> bool:
        """Check if a field name indicates sensitive data."""
        if not isinstance(field_name, str):
            return False
        return field_name.lower() in cls.SENSITIVE_FIELDS
    
    @classmethod
    def sanitize_pii(cls, data: Any, hash_pii: bool = True) -> Any:
        """Remove or hash PII from data structures."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if cls.is_sensitive_field(str(key)):
                    if hash_pii and isinstance(value, str):
                        sanitized[key] = cls._hash_value(value)
                    else:
                        sanitized[key] = "***PII_REMOVED***"
                else:
                    sanitized[key] = cls.sanitize_pii(value, hash_pii)
            return sanitized
        elif isinstance(data, (list, tuple)):
            return [cls.sanitize_pii(item, hash_pii) for item in data]
        elif isinstance(data, str):
            # Check for PII patterns in text content
            detected = cls.detect_pii_in_text(data)
            if detected:
                sanitized_text = data
                for pii_type, match in detected:
                    if hash_pii:
                        replacement = cls._hash_value(match)
                    else:
                        replacement = f"***{pii_type.value.upper()}_REMOVED***"
                    sanitized_text = sanitized_text.replace(match, replacement)
                return sanitized_text
        
        return data
    
    @staticmethod
    def _hash_value(value: str) -> str:
        """Create a consistent hash of a sensitive value."""
        return f"hash_{hashlib.sha256(value.encode()).hexdigest()[:16]}"


class AnalyticsEventValidator:
    """Validates analytics event data structures."""
    
    # Required fields for valid events
    REQUIRED_FIELDS = {'event_type', 'timestamp', 'user_id'}
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = {'session_id', 'page_url', 'user_agent'}
    
    # Maximum sizes for various fields
    MAX_FIELD_SIZES = {
        'event_type': 100,
        'page_url': 2048,
        'user_agent': 500,
        'custom_data': 10240,  # 10KB JSON
    }
    
    # Valid event types
    VALID_EVENT_TYPES = {
        'page_view', 'click', 'form_submit', 'scroll', 'download',
        'search', 'purchase', 'signup', 'login', 'logout',
        'video_play', 'video_pause', 'error', 'custom'
    }
    
    @classmethod
    def validate_event(cls, event_data: Dict[str, Any], strict: bool = False) -> ValidationResult:
        """Validate analytics event data."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(event_data, dict):
            result.add_error("Event data must be a dictionary")
            return result
        
        # Check required fields
        missing_fields = cls.REQUIRED_FIELDS - set(event_data.keys())
        if missing_fields:
            result.add_error(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check recommended fields (warnings only)
        missing_recommended = cls.RECOMMENDED_FIELDS - set(event_data.keys())
        if missing_recommended:
            result.add_warning(f"Missing recommended fields: {', '.join(missing_recommended)}")
        
        # Validate individual fields
        for field, value in event_data.items():
            field_errors = cls._validate_field(field, value, strict)
            result.errors.extend(field_errors)
            if field_errors:
                result.is_valid = False
        
        # Create sanitized version
        if result.is_valid or not strict:
            result.sanitized_data = PIIDetector.sanitize_pii(event_data)
        
        return result
    
    @classmethod
    def _validate_field(cls, field_name: str, value: Any, strict: bool = False) -> List[str]:
        """Validate an individual field."""
        errors = []
        
        # Check field size limits
        if field_name in cls.MAX_FIELD_SIZES:
            max_size = cls.MAX_FIELD_SIZES[field_name]
            if isinstance(value, str) and len(value) > max_size:
                errors.append(f"Field '{field_name}' exceeds maximum size of {max_size} characters")
        
        # Validate specific field types
        if field_name == 'event_type':
            if not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string")
            elif strict and value not in cls.VALID_EVENT_TYPES:
                errors.append(f"Invalid event_type '{value}'. Must be one of: {', '.join(cls.VALID_EVENT_TYPES)}")
        
        elif field_name == 'timestamp':
            if not cls._is_valid_timestamp(value):
                errors.append(f"Field '{field_name}' must be a valid ISO timestamp or Unix timestamp")
        
        elif field_name == 'user_id':
            if not isinstance(value, (str, int)) or (isinstance(value, str) and not value.strip()):
                errors.append(f"Field '{field_name}' must be a non-empty string or integer")
        
        elif field_name == 'page_url':
            if not isinstance(value, str) or not cls._is_valid_url(value):
                errors.append(f"Field '{field_name}' must be a valid URL")
        
        return errors
    
    @staticmethod
    def _is_valid_timestamp(value: Any) -> bool:
        """Check if a value is a valid timestamp."""
        if isinstance(value, (int, float)):
            # Unix timestamp validation (reasonable range)
            return 0 < value < 9999999999  # Year 1970 to ~2286
        elif isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except (ValueError, TypeError):
                return False
        return False
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Basic URL validation."""
        if not isinstance(url, str):
            return False
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None


class InputSanitizer:
    """Sanitizes input data for security and data quality."""
    
    # Characters to remove or replace
    DANGEROUS_CHARS = ['<', '>', '"', "'", '&', '\x00', '\r']
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(--|#|/\*|\*/)',
        r'(\bOR\s+\d+\s*=\s*\d+\b)',
        r'(\bAND\s+\d+\s*=\s*\d+\b)'
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove dangerous characters
        sanitized = value
        for char in cls.DANGEROUS_CHARS:
            sanitized = sanitized.replace(char, '')
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning("Potential SQL injection attempt detected", 
                             pattern=pattern, input_sample=sanitized[:100])
                # Remove suspicious content
                sanitized = re.sub(pattern, '[REMOVED]', sanitized, flags=re.IGNORECASE)
        
        # Trim to max length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data."""
        sanitized = {}
        for key, value in data.items():
            clean_key = cls.sanitize_string(str(key), 100)  # Limit key length
            
            if isinstance(value, str):
                sanitized[clean_key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    cls.sanitize_string(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value
        
        return sanitized


class RateLimitValidator:
    """Validates rate limits for API endpoints."""
    
    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        'events': 1000,      # Event ingestion
        'queries': 100,      # Analytics queries
        'exports': 10,       # Data exports
    }
    
    @classmethod
    def validate_rate_limit(cls, endpoint: str, request_count: int, 
                          time_window_minutes: int = 1) -> ValidationResult:
        """Validate if request is within rate limits."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        limit = cls.DEFAULT_LIMITS.get(endpoint, 100)  # Default fallback
        
        # Calculate rate per minute
        rate_per_minute = request_count / time_window_minutes if time_window_minutes > 0 else request_count
        
        if rate_per_minute > limit:
            result.add_error(f"Rate limit exceeded for {endpoint}: {rate_per_minute:.1f} > {limit} requests/minute")
        elif rate_per_minute > limit * 0.8:  # Warning at 80% of limit
            result.add_warning(f"Approaching rate limit for {endpoint}: {rate_per_minute:.1f}/{limit} requests/minute")
        
        return result


# Convenience functions for common validations
def validate_analytics_event(event_data: Dict[str, Any], strict: bool = False) -> ValidationResult:
    """Convenience function for event validation."""
    return AnalyticsEventValidator.validate_event(event_data, strict)


def sanitize_user_input(data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """Convenience function for input sanitization."""
    if isinstance(data, str):
        return InputSanitizer.sanitize_string(data)
    elif isinstance(data, dict):
        return InputSanitizer.sanitize_dict(data)
    else:
        return data


def remove_pii(data: Any, hash_pii: bool = True) -> Any:
    """Convenience function for PII removal."""
    return PIIDetector.sanitize_pii(data, hash_pii)


# Export main interfaces
__all__ = [
    'ValidationError',
    'ValidationResult', 
    'PIIType',
    'PIIDetector',
    'AnalyticsEventValidator',
    'InputSanitizer',
    'RateLimitValidator',
    'validate_analytics_event',
    'sanitize_user_input',
    'remove_pii'
]