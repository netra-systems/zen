"""
Security validation helper functions for middleware.
Extracted from security_middleware.py to maintain 8-line function limits.
"""

import re
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from app.logging_config import central_logger
from app.core.exceptions_auth import NetraSecurityException

logger = central_logger.get_logger(__name__)


class SecurityPatterns:
    """Security pattern definitions and regex compilation."""
    
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|GRANT|REVOKE)\b)',
        r'(-{2}|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(\bxp_cmdshell\b)',  # SQL Server command execution
        r'(\bsp_executesql\b)',  # SQL Server stored procedure
        r'(\bINTO\s+OUTFILE\b)',  # MySQL file operations
        r'(\bLOAD_FILE\b)',  # MySQL file reading
        r'(\bUNION\s+ALL\s+SELECT\b)',  # UNION injection
        r'(\bINFORMATION_SCHEMA\b)',  # Schema enumeration
        r'(\bSYS\.\b)',  # System table access
    ]
    
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # event handlers
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<form[^>]*>',  # unauthorized forms
        r'<input[^>]*>',  # unauthorized inputs
        r'vbscript:',  # VBScript
        r'data:text/html',  # Data URLs with HTML
        r'expression\s*\(',  # CSS expressions
        r'@import',  # CSS imports
        r'<link[^>]*>',  # unauthorized stylesheets
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r'(\||\||&|&&|;|`)',  # Command separators
        r'(\$\(|\`)',  # Command substitution
        r'(\bwget\b|\bcurl\b|\bpowershell\b|\bcmd\b|\bsh\b|\bbash\b)',
        r'(\brm\s+|\bdel\s+|\brmdir\b)',  # File deletion
        r'(\bcat\s+|\btype\s+)',  # File reading
        r'(\bchmod\b|\bchown\b)',  # Permission changes
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',  # Directory traversal
        r'\.\.\\\\',  # Windows directory traversal
        r'%2e%2e%2f',  # URL encoded traversal
        r'%2e%2e\/',  # Mixed encoding
        r'/etc/passwd',  # Common target files
        r'/windows/system32',
        r'C:\\',  # Windows paths
    ]


class SecurityValidators:
    """Security validation functions with 8-line limit compliance."""
    
    def __init__(self):
        self.sql_regex = self._compile_pattern_regex(SecurityPatterns.SQL_INJECTION_PATTERNS)
        self.xss_regex = self._compile_pattern_regex(SecurityPatterns.XSS_PATTERNS)
        self.command_regex = self._compile_pattern_regex(SecurityPatterns.COMMAND_INJECTION_PATTERNS)
        self.path_regex = self._compile_pattern_regex(SecurityPatterns.PATH_TRAVERSAL_PATTERNS)
    
    def _compile_pattern_regex(self, patterns: List[str]) -> re.Pattern:
        """Compile security patterns into regex."""
        return re.compile('|'.join(patterns), re.IGNORECASE)
    
    def validate_sql_injection(self, data: str, field_name: str) -> None:
        """Check for SQL injection patterns."""
        if self.sql_regex.search(data):
            self._log_security_threat("SQL injection", field_name, data)
            self._raise_security_exception(f"SQL injection attempt detected in {field_name}")
    
    def validate_xss_attack(self, data: str, field_name: str) -> None:
        """Check for XSS attack patterns."""
        if self.xss_regex.search(data):
            self._log_security_threat("XSS", field_name, data)
            self._raise_security_exception(f"XSS attempt detected in {field_name}")
    
    def validate_command_injection(self, data: str, field_name: str) -> None:
        """Check for command injection patterns."""
        if self.command_regex.search(data):
            self._log_security_threat("Command injection", field_name, data)
            self._raise_security_exception(f"Command injection attempt detected in {field_name}")
    
    def validate_path_traversal(self, data: str, field_name: str) -> None:
        """Check for path traversal patterns."""
        if self.path_regex.search(data):
            self._log_security_threat("Path traversal", field_name, data)
            self._raise_security_exception(f"Path traversal attempt detected in {field_name}")
    
    def _log_security_threat(self, threat_type: str, field_name: str, data: str) -> None:
        """Log security threat with truncated data."""
        logger.error(f"{threat_type} attempt detected in {field_name}: {data[:100]}")
    
    def _raise_security_exception(self, message: str) -> None:
        """Raise standardized security exception."""
        raise NetraSecurityException(message=message)


class RequestValidators:
    """Request-level validation functions."""
    
    @staticmethod
    def validate_request_size(request: Request, max_size: int) -> None:
        """Validate request content length."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
    
    @staticmethod
    def validate_url_length(url_str: str, max_length: int) -> None:
        """Validate URL length."""
        if len(url_str) > max_length:
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="URL too long"
            )
    
    @staticmethod
    def validate_url_characters(url_str: str) -> None:
        """Validate URL for suspicious characters."""
        if re.search(r'[<>"\'\x00-\x1f]', url_str):
            logger.warning(f"Suspicious URL characters: {url_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL characters"
            )
    
    @staticmethod
    def validate_header_size(name: str, value: str, max_size: int) -> None:
        """Validate individual header size."""
        if len(value) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Header {name} too large"
            )
    
    @staticmethod
    def decode_request_body(body: bytes) -> str:
        """Decode request body safely."""
        return body.decode('utf-8', errors='ignore')
    
    @staticmethod
    def handle_encoding_error() -> None:
        """Handle request body encoding errors."""
        logger.warning("Request body contains invalid UTF-8")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request encoding"
        )


class HeaderSanitizer:
    """HTTP header sanitization functions."""
    
    @staticmethod
    def get_allowed_headers() -> Set[str]:
        """Get set of allowed headers."""
        return {
            'content-type', 'authorization', 'user-agent', 'accept',
            'accept-encoding', 'accept-language', 'cache-control',
            'connection', 'host', 'origin', 'referer', 'x-request-id',
            'x-trace-id', 'x-forwarded-for', 'x-real-ip'
        }
    
    @staticmethod
    def is_header_allowed(key: str, value: str, max_size: int, allowed_headers: Set[str]) -> bool:
        """Check if header is allowed."""
        return key.lower() in allowed_headers and len(value) <= max_size
    
    @staticmethod
    def sanitize_header_value(value: str, max_size: int) -> str:
        """Sanitize header value to max size."""
        return value[:max_size]


class IPValidators:
    """IP address validation and extraction functions."""
    
    @staticmethod
    def get_forwarded_headers() -> List[str]:
        """Get list of trusted forwarded headers."""
        return [
            "x-forwarded-for",
            "x-real-ip", 
            "x-client-ip",
            "cf-connecting-ip"
        ]
    
    @staticmethod
    def extract_ip_from_header(request: Request, header: str) -> Optional[str]:
        """Extract IP from forwarded header."""
        if header in request.headers:
            return request.headers[header].split(',')[0].strip()
        return None
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_fallback_ip(request: Request) -> str:
        """Get fallback IP address."""
        return request.client.host if request.client else "unknown"


class RateLimitHelpers:
    """Rate limiting helper functions."""
    
    @staticmethod
    def clean_old_requests(requests_list: List[float], now: float, window: int) -> List[float]:
        """Clean old requests outside time window."""
        return [req_time for req_time in requests_list if now - req_time < window]
    
    @staticmethod
    def should_block_ip(requests_count: int, limit: int) -> bool:
        """Check if IP should be blocked based on request count."""
        return requests_count >= limit
    
    @staticmethod
    def calculate_block_time(minutes: int) -> datetime:
        """Calculate block expiration time."""
        return datetime.now() + timedelta(minutes=minutes)
    
    @staticmethod
    def log_rate_limit_exceeded(identifier: str, block_minutes: int) -> None:
        """Log rate limit exceeded event."""
        logger.warning(f"Rate limit exceeded for {identifier}, blocking for {block_minutes} minutes")
    
    @staticmethod
    def is_sensitive_endpoint(path: str, sensitive_endpoints: Set[str]) -> bool:
        """Check if endpoint is sensitive."""
        return any(endpoint in path for endpoint in sensitive_endpoints)


class AuthAttemptTracker:
    """Authentication attempt tracking functions."""
    
    @staticmethod
    def clean_old_attempts(attempts: List[float], current_time: float, hours: int) -> List[float]:
        """Clean old authentication attempts."""
        cutoff_time = current_time - (hours * 3600)
        return [attempt_time for attempt_time in attempts if attempt_time > cutoff_time]
    
    @staticmethod
    def should_auto_block(failed_count: int, threshold: int) -> bool:
        """Check if IP should be auto-blocked."""
        return failed_count >= threshold
    
    @staticmethod
    def reset_failed_count() -> int:
        """Reset failed authentication count."""
        return 0
    
    @staticmethod
    def log_auth_block(ip_address: str, failed_count: int) -> None:
        """Log authentication-based IP block."""
        logger.error(f"IP {ip_address} blocked due to {failed_count} failed auth attempts")
    
    @staticmethod
    def is_ip_suspicious(failed_count: int, recent_attempts: int, thresholds: Dict[str, int]) -> bool:
        """Check if IP should be treated as suspicious."""
        return (failed_count >= thresholds['failed'] or 
                recent_attempts >= thresholds['recent'])