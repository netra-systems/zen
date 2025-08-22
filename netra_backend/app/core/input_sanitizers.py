"""
Input sanitization and normalization functionality.
Provides comprehensive sanitization for detected security threats.
"""

import base64
import html
import re
import urllib.parse
from typing import List, Set

from netra_backend.app.core.validation_rules import SecurityThreat


class InputNormalizer:
    """Normalizes input for better threat detection."""
    
    @staticmethod
    def normalize_for_detection(input_value: str) -> str:
        """Normalize input for better threat detection."""
        normalized = urllib.parse.unquote(input_value)
        normalized = html.unescape(normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.lower()
        return normalized


class InputSanitizer:
    """Sanitizes input based on detected threats."""
    
    def __init__(self, suspicious_chars: Set[str]):
        self.suspicious_chars = suspicious_chars
    
    def sanitize_input(self, input_value: str, threats: List[SecurityThreat]) -> str:
        """Sanitize input based on detected threats."""
        sanitized = input_value
        sanitized = self._sanitize_web_threats(sanitized, threats)
        sanitized = self._sanitize_injection_threats(sanitized, threats)
        sanitized = self._sanitize_system_threats(sanitized, threats)
        return sanitized
    
    def _sanitize_web_threats(self, sanitized: str, threats: List[SecurityThreat]) -> str:
        """Sanitize XSS and script injection threats."""
        if SecurityThreat.XSS in threats or SecurityThreat.SCRIPT_INJECTION in threats:
            sanitized = html.escape(sanitized, quote=True)
        return sanitized
    
    def _sanitize_injection_threats(self, sanitized: str, threats: List[SecurityThreat]) -> str:
        """Sanitize SQL and command injection threats."""
        if SecurityThreat.SQL_INJECTION in threats:
            sanitized = re.sub(r'[;\'\"\\]', '', sanitized)
        if SecurityThreat.COMMAND_INJECTION in threats:
            sanitized = re.sub(r'[;&|`$()]', '', sanitized)
        return sanitized
    
    def _sanitize_system_threats(self, sanitized: str, threats: List[SecurityThreat]) -> str:
        """Sanitize path traversal threats."""
        if SecurityThreat.PATH_TRAVERSAL in threats:
            sanitized = sanitized.replace('../', '').replace('..\\', '')
        return sanitized


class EncodingAnalyzer:
    """Analyzes input for encoding issues and suspicious content."""
    
    def __init__(self, suspicious_chars: Set[str]):
        self.suspicious_chars = suspicious_chars
    
    def is_double_encoded(self, input_value: str, decoded: str) -> bool:
        """Check if input is double URL encoded."""
        return decoded != input_value and urllib.parse.unquote(decoded) != decoded
    
    def has_suspicious_base64_content(self, input_value: str) -> bool:
        """Check if base64 content contains suspicious characters."""
        try:
            decoded_b64 = base64.b64decode(input_value).decode('utf-8', errors='ignore')
            return any(char in decoded_b64 for char in self.suspicious_chars)
        except Exception:
            return False
    
    def is_valid_base64_format(self, input_value: str) -> bool:
        """Check if string matches base64 format."""
        pattern_match = re.match(r'^[A-Za-z0-9+/]*={0,2}$', input_value)
        correct_length = len(input_value) % 4 == 0
        return bool(pattern_match and correct_length)


class SecurityValidator:
    """Validates input for security-specific context types."""
    
    def has_dangerous_protocol(self, url: str) -> bool:
        """Check if URL has dangerous protocol."""
        return bool(re.match(r'^(javascript|data|vbscript|file):', url, re.IGNORECASE))
    
    def has_valid_url_format(self, url: str) -> bool:
        """Check if URL has valid format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url, re.IGNORECASE))
    
    def has_path_traversal(self, filename: str) -> bool:
        """Check if filename contains path traversal."""
        return '..' in filename or '/' in filename or '\\' in filename
    
    def has_dangerous_extension(self, filename: str) -> bool:
        """Check if filename has dangerous extension."""
        dangerous_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        return file_ext in dangerous_extensions
    
    def is_valid_email_format(self, email: str) -> bool:
        """Check if email has valid format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def is_valid_json_format(self, json_str: str) -> bool:
        """Check if string is valid JSON."""
        import json
        try:
            json.loads(json_str)
            return True
        except json.JSONDecodeError:
            return False


class ContentTypeValidator:
    """Validates content based on specific types."""
    
    def __init__(self, security_validator: SecurityValidator):
        self.security_validator = security_validator
    
    def validate_email_content(self, email: str) -> tuple[bool, str]:
        """Validate email content and return issues."""
        if not self.security_validator.is_valid_email_format(email):
            return False, "Invalid email format"
        return True, ""
    
    def validate_url_content(self, url: str) -> tuple[bool, str]:
        """Validate URL content and return issues."""
        if self.security_validator.has_dangerous_protocol(url):
            return False, "Dangerous URL protocol detected"
        if not self.security_validator.has_valid_url_format(url):
            return False, "Invalid URL format"
        return True, ""
    
    def validate_filename_content(self, filename: str) -> tuple[bool, str]:
        """Validate filename content and return issues."""
        if self.security_validator.has_path_traversal(filename):
            return False, "Path traversal in filename"
        if self.security_validator.has_dangerous_extension(filename):
            return False, "Potentially dangerous file extension"
        return True, ""
    
    def validate_json_content(self, json_str: str) -> tuple[bool, str]:
        """Validate JSON content and return issues."""
        if not self.security_validator.is_valid_json_format(json_str):
            return False, "Invalid JSON format"
        return True, ""