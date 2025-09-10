"""
Data Sanitizer - SSOT Security Implementation

This module provides data sanitization functionality for the Netra platform.
Following SSOT principles, this is the canonical implementation for data sanitization.

Business Value: Security/Internal - Risk Reduction & Security Compliance
Sanitizes user inputs and system outputs to prevent security vulnerabilities
including XSS, SQL injection, LDAP injection, and other data-based attacks.

CRITICAL: This is a minimal SSOT-compliant implementation to resolve import errors.
Full implementation follows CLAUDE.md SSOT patterns.
"""

import re
import html
import json
import base64
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from shared.isolated_environment import get_env


class SanitizationType(Enum):
    """Types of sanitization that can be applied."""
    HTML_OUTPUT = "html_output"
    SQL_PARAMETER = "sql_parameter"
    LDAP_FILTER = "ldap_filter"
    JSON_OUTPUT = "json_output"
    FILE_PATH = "file_path"
    COMMAND_PARAMETER = "command_parameter"
    URL_PARAMETER = "url_parameter"
    GENERIC_TEXT = "generic_text"


@dataclass
class SanitizationConfig:
    """Configuration for data sanitization operations."""
    sanitization_type: SanitizationType
    preserve_whitespace: bool = True
    max_length: Optional[int] = None
    allowed_tags: Optional[List[str]] = None
    allowed_attributes: Optional[List[str]] = None
    strict_mode: bool = False
    encoding: str = "utf-8"
    remove_dangerous_patterns: bool = True
    custom_patterns: Optional[List[str]] = None


@dataclass
class SanitizedOutput:
    """Result of data sanitization operation."""
    is_safe: bool
    original_input: str
    sanitized_output: str
    sanitization_type: SanitizationType
    removed_patterns: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class DataSanitizer:
    """
    SSOT Data Sanitizer.
    
    This is the canonical implementation for all data sanitization across the platform.
    """
    
    def __init__(self):
        """Initialize data sanitizer with SSOT environment."""
        self._env = get_env()
        self._sanitization_enabled = self._env.get("DATA_SANITIZATION_ENABLED", "true").lower() == "true"
        self._strict_mode = self._env.get("DATA_SANITIZATION_STRICT", "false").lower() == "true"
        self._max_input_length = int(self._env.get("MAX_SANITIZATION_INPUT_LENGTH", "100000"))
        
        # Common dangerous patterns
        self._dangerous_html_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>.*?</style>"
        ]
        
        self._dangerous_sql_patterns = [
            r"[';\"\\]",
            r"--",
            r"/\*",
            r"\*/",
            r"\bUNION\b",
            r"\bSELECT\b",
            r"\bINSERT\b",
            r"\bUPDATE\b",
            r"\bDELETE\b",
            r"\bDROP\b",
            r"\bCREATE\b",
            r"\bALTER\b"
        ]
        
        self._dangerous_ldap_patterns = [
            r"[*()\\]",
            r"\x00",  # Null byte
            r"/",
            r"&",
            r"|",
            r"!",
            r"="
        ]
        
        self._dangerous_command_patterns = [
            r"[;&|`$()]",
            r"\.\./",
            r"\.\.\\",
            r"\bcat\b",
            r"\bls\b",
            r"\brm\b",
            r"\bwget\b",
            r"\bcurl\b",
            r"\bnc\b",
            r"\btelnet\b"
        ]
        
        # Safe HTML tags and attributes
        self._safe_html_tags = [
            'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'div', 'span', 'blockquote', 'code', 'pre'
        ]
        
        self._safe_html_attributes = [
            'class', 'id', 'title', 'alt', 'href', 'src'
        ]
    
    def sanitize_for_html_output(self, 
                                input_data: str, 
                                config: Optional[SanitizationConfig] = None) -> SanitizedOutput:
        """
        Sanitize data for safe HTML output.
        
        Args:
            input_data: Data to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if config is None:
            config = SanitizationConfig(
                sanitization_type=SanitizationType.HTML_OUTPUT,
                strict_mode=self._strict_mode
            )
        
        return self._sanitize_data(input_data, config)
    
    def sanitize_ldap_filter(self, 
                           ldap_filter: str, 
                           config: Optional[SanitizationConfig] = None) -> SanitizedOutput:
        """
        Sanitize LDAP filter for safe query execution.
        
        Args:
            ldap_filter: LDAP filter to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if config is None:
            config = SanitizationConfig(
                sanitization_type=SanitizationType.LDAP_FILTER,
                strict_mode=True
            )
        
        return self._sanitize_data(ldap_filter, config)
    
    def sanitize_sql_parameter(self, 
                             parameter: str, 
                             config: Optional[SanitizationConfig] = None) -> SanitizedOutput:
        """
        Sanitize SQL parameter for safe query execution.
        
        Args:
            parameter: SQL parameter to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if config is None:
            config = SanitizationConfig(
                sanitization_type=SanitizationType.SQL_PARAMETER,
                strict_mode=True
            )
        
        return self._sanitize_data(parameter, config)
    
    def sanitize_json_output(self, 
                           json_data: Union[str, Dict[str, Any]], 
                           config: Optional[SanitizationConfig] = None) -> SanitizedOutput:
        """
        Sanitize JSON data for safe output.
        
        Args:
            json_data: JSON data to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if config is None:
            config = SanitizationConfig(
                sanitization_type=SanitizationType.JSON_OUTPUT
            )
        
        # Convert to string if needed
        if isinstance(json_data, dict):
            input_str = json.dumps(json_data)
        else:
            input_str = str(json_data)
        
        return self._sanitize_data(input_str, config)
    
    def sanitize_file_path(self, 
                          file_path: str, 
                          config: Optional[SanitizationConfig] = None) -> SanitizedOutput:
        """
        Sanitize file path for safe file system operations.
        
        Args:
            file_path: File path to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if config is None:
            config = SanitizationConfig(
                sanitization_type=SanitizationType.FILE_PATH,
                strict_mode=True
            )
        
        return self._sanitize_data(file_path, config)
    
    def _sanitize_data(self, input_data: str, config: SanitizationConfig) -> SanitizedOutput:
        """
        Core sanitization logic.
        
        Args:
            input_data: Data to sanitize
            config: Sanitization configuration
            
        Returns:
            Sanitized output result
        """
        if not self._sanitization_enabled:
            return SanitizedOutput(
                is_safe=True,
                original_input=input_data,
                sanitized_output=input_data,
                sanitization_type=config.sanitization_type,
                removed_patterns=[],
                warnings=["Data sanitization is disabled"],
                metadata={"sanitization_enabled": False}
            )
        
        # Validate input length
        if len(input_data) > self._max_input_length:
            return SanitizedOutput(
                is_safe=False,
                original_input=input_data,
                sanitized_output="",
                sanitization_type=config.sanitization_type,
                removed_patterns=[],
                warnings=[f"Input exceeds maximum length of {self._max_input_length}"],
                metadata={"input_length": len(input_data), "max_length": self._max_input_length}
            )
        
        sanitized_output = input_data
        removed_patterns = []
        warnings = []
        
        # Apply sanitization based on type
        if config.sanitization_type == SanitizationType.HTML_OUTPUT:
            sanitized_output, removed = self._sanitize_html(sanitized_output, config)
            removed_patterns.extend(removed)
            
        elif config.sanitization_type == SanitizationType.SQL_PARAMETER:
            sanitized_output, removed = self._sanitize_sql(sanitized_output, config)
            removed_patterns.extend(removed)
            
        elif config.sanitization_type == SanitizationType.LDAP_FILTER:
            sanitized_output, removed = self._sanitize_ldap(sanitized_output, config)
            removed_patterns.extend(removed)
            
        elif config.sanitization_type == SanitizationType.FILE_PATH:
            sanitized_output, removed = self._sanitize_file_path(sanitized_output, config)
            removed_patterns.extend(removed)
            
        elif config.sanitization_type == SanitizationType.COMMAND_PARAMETER:
            sanitized_output, removed = self._sanitize_command(sanitized_output, config)
            removed_patterns.extend(removed)
            
        else:
            # Generic text sanitization
            sanitized_output, removed = self._sanitize_generic(sanitized_output, config)
            removed_patterns.extend(removed)
        
        # Apply custom patterns if specified
        if config.custom_patterns:
            for pattern in config.custom_patterns:
                if re.search(pattern, sanitized_output, re.IGNORECASE):
                    sanitized_output = re.sub(pattern, "", sanitized_output, flags=re.IGNORECASE)
                    removed_patterns.append(pattern)
        
        # Apply length limit if specified
        if config.max_length and len(sanitized_output) > config.max_length:
            sanitized_output = sanitized_output[:config.max_length]
            warnings.append(f"Output truncated to {config.max_length} characters")
        
        # Determine if result is safe
        is_safe = len(removed_patterns) == 0 or not config.strict_mode
        
        return SanitizedOutput(
            is_safe=is_safe,
            original_input=input_data,
            sanitized_output=sanitized_output,
            sanitization_type=config.sanitization_type,
            removed_patterns=removed_patterns,
            warnings=warnings,
            metadata={
                "original_length": len(input_data),
                "sanitized_length": len(sanitized_output),
                "strict_mode": config.strict_mode,
                "sanitization_enabled": self._sanitization_enabled
            }
        )
    
    def _sanitize_html(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Sanitize HTML content."""
        removed_patterns = []
        sanitized = input_str
        
        # Remove dangerous HTML patterns
        for pattern in self._dangerous_html_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE | re.DOTALL):
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)
                removed_patterns.append(pattern)
        
        # HTML escape if strict mode
        if config.strict_mode:
            sanitized = html.escape(sanitized)
        
        return sanitized, removed_patterns
    
    def _sanitize_sql(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Sanitize SQL parameters."""
        removed_patterns = []
        sanitized = input_str
        
        # Remove dangerous SQL patterns
        for pattern in self._dangerous_sql_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
                removed_patterns.append(pattern)
        
        # Escape single quotes
        sanitized = sanitized.replace("'", "''")
        
        return sanitized, removed_patterns
    
    def _sanitize_ldap(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Sanitize LDAP filters."""
        removed_patterns = []
        sanitized = input_str
        
        # Escape LDAP special characters
        ldap_escapes = {
            '*': r'\2a',
            '(': r'\28',
            ')': r'\29',
            '\\': r'\5c',
            '\x00': r'\00',
            '/': r'\2f'
        }
        
        for char, escape in ldap_escapes.items():
            if char in sanitized:
                sanitized = sanitized.replace(char, escape)
                removed_patterns.append(f"LDAP special character: {char}")
        
        return sanitized, removed_patterns
    
    def _sanitize_file_path(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Sanitize file paths."""
        removed_patterns = []
        sanitized = input_str
        
        # Remove directory traversal patterns
        dangerous_path_patterns = [r"\.\.[\\/]", r"[\\/]\.\."]
        for pattern in dangerous_path_patterns:
            if re.search(pattern, sanitized):
                sanitized = re.sub(pattern, "", sanitized)
                removed_patterns.append(pattern)
        
        # Remove null bytes
        if '\x00' in sanitized:
            sanitized = sanitized.replace('\x00', '')
            removed_patterns.append("null_byte")
        
        return sanitized, removed_patterns
    
    def _sanitize_command(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Sanitize command parameters."""
        removed_patterns = []
        sanitized = input_str
        
        # Remove dangerous command patterns
        for pattern in self._dangerous_command_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
                removed_patterns.append(pattern)
        
        return sanitized, removed_patterns
    
    def _sanitize_generic(self, input_str: str, config: SanitizationConfig) -> tuple[str, List[str]]:
        """Generic text sanitization."""
        removed_patterns = []
        sanitized = input_str
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        if sanitized != input_str:
            removed_patterns.append("control_characters")
        
        return sanitized, removed_patterns


# SSOT Factory Function
def create_data_sanitizer() -> DataSanitizer:
    """
    SSOT factory function for creating data sanitizer instances.
    
    Returns:
        Configured data sanitizer
    """
    return DataSanitizer()


# Export SSOT interface
__all__ = [
    "DataSanitizer",
    "SanitizationConfig", 
    "SanitizedOutput",
    "SanitizationType",
    "create_data_sanitizer"
]