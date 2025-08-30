"""
String utilities for sanitization, validation, and security.

Provides centralized string operations including XSS prevention,
input validation, and security-focused string processing.
"""

import html
import re
import urllib.parse
from pathlib import Path
from typing import Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StringUtils:
    """Utility class for string operations and security."""
    
    def __init__(self):
        """Initialize string utilities."""
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        self.alphanumeric_pattern = re.compile(r'^[a-zA-Z0-9]+$')
    
    def sanitize_html(self, text: str) -> str:
        """Sanitize HTML content to prevent XSS attacks.
        
        Args:
            text: Raw HTML text to sanitize
            
        Returns:
            Sanitized HTML text
        """
        if not text:
            return text
        
        # Remove dangerous tags and attributes
        sanitized = self._remove_dangerous_tags(text)
        
        # Escape remaining HTML
        sanitized = html.escape(sanitized, quote=True)
        
        return sanitized
    
    def _remove_dangerous_tags(self, text: str) -> str:
        """Remove dangerous HTML tags and attributes."""
        # Remove script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove event handlers
        text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*on\w+\s*=\s*[^>\s]*', '', text, flags=re.IGNORECASE)
        
        # Remove javascript: URLs
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        return text
    
    def escape_sql(self, text: str) -> str:
        """Escape SQL special characters to prevent injection.
        
        Args:
            text: Text to escape
            
        Returns:
            SQL-escaped text
        """
        if not text:
            return text
        
        # Basic SQL escaping - replace single quotes
        escaped = text.replace("'", "''")
        
        # Remove or escape other dangerous SQL characters
        escaped = escaped.replace(";", "\\;")
        escaped = escaped.replace("--", "\\--")
        escaped = escaped.replace("/*", "\\/*")
        escaped = escaped.replace("*/", "\\*/")
        
        return escaped
    
    def sanitize_path(self, path: str) -> str:
        """Sanitize file path to prevent directory traversal.
        
        Args:
            path: File path to sanitize
            
        Returns:
            Sanitized path
        """
        if not path:
            return path
        
        # Remove directory traversal attempts
        sanitized = path.replace("..", "")
        sanitized = sanitized.replace("./", "")
        sanitized = sanitized.replace("\\", "/")
        
        # Use pathlib to normalize
        try:
            normalized = Path(sanitized).as_posix()
            # Ensure the path doesn't start with /
            if normalized.startswith('/'):
                normalized = normalized[1:]
            return normalized
        except Exception as e:
            logger.warning(f"Path sanitization failed: {e}")
            return ""
    
    def is_valid_email(self, email: str) -> bool:
        """Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format, False otherwise
        """
        if not email:
            return False
        return bool(self.email_pattern.match(email))
    
    def is_valid_url(self, url: str) -> bool:
        """Validate URL format and safety.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid and safe URL, False otherwise
        """
        if not url:
            return False
        
        # Check for dangerous protocols
        if url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
            return False
        
        return bool(self.url_pattern.match(url))
    
    def is_alphanumeric(self, text: str) -> bool:
        """Check if text contains only alphanumeric characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if alphanumeric only, False otherwise
        """
        if not text:
            return False
        return bool(self.alphanumeric_pattern.match(text))
    
    def truncate(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to specified length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add when truncated
            
        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.
        
        Args:
            text: Text to normalize
            
        Returns:
            Text with normalized whitespace
        """
        if not text:
            return text
        
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', text)
        return normalized.strip()
    
    def remove_control_characters(self, text: str) -> str:
        """Remove control characters from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text without control characters
        """
        if not text:
            return text
        
        # Remove control characters except newline, tab, and carriage return
        return ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')