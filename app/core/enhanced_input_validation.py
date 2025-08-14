"""
Enhanced input validation system with comprehensive security checks.
Validates all inputs to prevent injection attacks, XSS, and other security vulnerabilities.
"""

import re
import html
import json
import base64
import urllib.parse
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ValidationError

from app.logging_config import central_logger
from app.core.exceptions import NetraSecurityException

logger = central_logger.get_logger(__name__)


class ValidationLevel(str, Enum):
    """Input validation strictness levels."""
    BASIC = "basic"          # Basic format validation
    MODERATE = "moderate"    # Additional security checks
    STRICT = "strict"        # Maximum security validation
    PARANOID = "paranoid"    # Ultra-strict for sensitive data


class SecurityThreat(str, Enum):
    """Types of security threats to detect."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    SCRIPT_INJECTION = "script_injection"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    LDAP_INJECTION = "ldap_injection"
    XML_INJECTION = "xml_injection"
    JSON_INJECTION = "json_injection"
    HEADER_INJECTION = "header_injection"


class ValidationResult(BaseModel):
    """Result of input validation."""
    is_valid: bool = Field(..., description="Whether input passed validation")
    sanitized_value: Optional[str] = Field(default=None, description="Sanitized input value")
    threats_detected: List[SecurityThreat] = Field(default_factory=list, description="Security threats found")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    confidence_score: float = Field(default=1.0, description="Confidence in validation (0-1)")


class ThreatPattern:
    """Security threat detection patterns."""
    
    # SQL Injection patterns
    SQL_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(-{2}|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(\bxp_cmdshell\b)',  # SQL Server command execution
        r'(\b(sp_|xp_)\w+)',  # SQL Server stored procedures
        r'(;\s*(DROP|DELETE|INSERT|UPDATE))',  # Statement chaining
        r'(\bUNION\s+(ALL\s+)?SELECT)',  # Union-based injections
        r'(\bINTO\s+OUTFILE\b)',  # File operations
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'expression\s*\(',  # CSS expressions
        r'url\s*\(\s*["\']?\s*javascript:',
        r'data:[^;]*;base64',  # Data URLs
    ]
    
    # Script injection patterns
    SCRIPT_PATTERNS = [
        r'<script[^>]*>',
        r'</script>',
        r'javascript:',
        r'vbscript:',
        r'file:',
        r'data:text/html',
        r'&#x\w+;',  # HTML entities
        r'&\w+;',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'%2e%2e%2f',
        r'%2e%2e%5c',
        r'%252e%252e%252f',
        r'%c0%ae%c0%ae%c0%af',
        r'/etc/passwd',
        r'/etc/shadow',
        r'C:\\Windows\\System32',
    ]
    
    # Command injection patterns
    COMMAND_PATTERNS = [
        r'[;&|`$]',  # Command separators
        r'\$\{.*\}',  # Variable expansion
        r'\$\(.*\)',  # Command substitution
        r'`.*`',      # Backticks
        r'>\s*/dev/',  # Output redirection
        r'\|\s*(curl|wget|nc|netcat)',  # Network commands
    ]
    
    # LDAP injection patterns
    LDAP_PATTERNS = [
        r'\*\)\(',
        r'\)\(&',
        r'\|\(&',
        r'[()=*|&]',  # LDAP special characters
    ]
    
    # XML injection patterns
    XML_PATTERNS = [
        r'<!ENTITY',
        r'SYSTEM\s+["\']',
        r'PUBLIC\s+["\']',
        r'<!DOCTYPE',
        r'&\w+;',
        r'<!\[CDATA\[',
    ]


class EnhancedInputValidator:
    """Comprehensive input validator with threat detection."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.threat_patterns = self._compile_patterns()
        self.max_input_length = self._get_max_length()
        self.suspicious_chars = set('<>"\'&;|`$(){}[]\\')
        
    def _compile_patterns(self) -> Dict[SecurityThreat, List[re.Pattern]]:
        """Compile regex patterns for threat detection."""
        patterns = {}
        
        patterns[SecurityThreat.SQL_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SQL_PATTERNS
        ]
        
        patterns[SecurityThreat.XSS] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.XSS_PATTERNS
        ]
        
        patterns[SecurityThreat.SCRIPT_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SCRIPT_PATTERNS
        ]
        
        patterns[SecurityThreat.PATH_TRAVERSAL] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.PATH_TRAVERSAL_PATTERNS
        ]
        
        patterns[SecurityThreat.COMMAND_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.COMMAND_PATTERNS
        ]
        
        patterns[SecurityThreat.LDAP_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.LDAP_PATTERNS
        ]
        
        patterns[SecurityThreat.XML_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.XML_PATTERNS
        ]
        
        return patterns
    
    def _get_max_length(self) -> int:
        """Get maximum input length based on validation level."""
        length_limits = {
            ValidationLevel.BASIC: 100000,     # 100KB
            ValidationLevel.MODERATE: 50000,   # 50KB
            ValidationLevel.STRICT: 10000,     # 10KB
            ValidationLevel.PARANOID: 1000     # 1KB
        }
        return length_limits[self.validation_level]
    
    def validate_input(self, input_value: str, field_name: str = "input",
                      context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Comprehensive input validation."""
        try:
            if not input_value:
                return ValidationResult(
                    is_valid=True,
                    sanitized_value="",
                    confidence_score=1.0
                )
            
            result = ValidationResult(is_valid=True, sanitized_value=input_value)
            
            # Basic checks
            self._check_length(input_value, result)
            self._check_encoding(input_value, result)
            
            # Threat detection
            threats = self._detect_threats(input_value)
            result.threats_detected.extend(threats)
            
            # Determine if input is valid based on threats
            if threats:
                result.is_valid = False
                result.errors.append(f"Security threats detected in {field_name}: {[t.value for t in threats]}")
                result.confidence_score = 0.0
            
            # Sanitization
            if result.is_valid or self.validation_level in [ValidationLevel.BASIC, ValidationLevel.MODERATE]:
                result.sanitized_value = self._sanitize_input(input_value, threats)
            
            # Additional context-based validation
            if context:
                self._validate_context(input_value, context, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Input validation error for {field_name}: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                confidence_score=0.0
            )
    
    def _check_length(self, input_value: str, result: ValidationResult) -> None:
        """Check input length."""
        if len(input_value) > self.max_input_length:
            result.warnings.append(f"Input length ({len(input_value)}) exceeds maximum ({self.max_input_length})")
            result.confidence_score *= 0.8
    
    def _check_encoding(self, input_value: str, result: ValidationResult) -> None:
        """Check for encoding issues."""
        try:
            # Check for double encoding
            decoded = urllib.parse.unquote(input_value)
            if decoded != input_value and urllib.parse.unquote(decoded) != decoded:
                result.warnings.append("Potential double URL encoding detected")
                result.confidence_score *= 0.9
            
            # Check for base64 encoding
            if re.match(r'^[A-Za-z0-9+/]*={0,2}$', input_value) and len(input_value) % 4 == 0:
                try:
                    decoded_b64 = base64.b64decode(input_value).decode('utf-8', errors='ignore')
                    if any(char in decoded_b64 for char in self.suspicious_chars):
                        result.warnings.append("Suspicious base64 encoded content")
                        result.confidence_score *= 0.7
                except Exception:
                    pass
                    
        except Exception as e:
            result.warnings.append(f"Encoding check failed: {e}")
    
    def _detect_threats(self, input_value: str) -> List[SecurityThreat]:
        """Detect security threats in input."""
        threats = []
        
        # Normalize input for better detection
        normalized_input = self._normalize_for_detection(input_value)
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if pattern.search(normalized_input):
                    threats.append(threat_type)
                    logger.warning(f"Detected {threat_type.value} in input: {input_value[:100]}...")
                    break  # Only record each threat type once
        
        return threats
    
    def _normalize_for_detection(self, input_value: str) -> str:
        """Normalize input for better threat detection."""
        # URL decode
        normalized = urllib.parse.unquote(input_value)
        
        # HTML decode
        normalized = html.unescape(normalized)
        
        # Remove whitespace variations
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Handle case variations
        normalized = normalized.lower()
        
        return normalized
    
    def _sanitize_input(self, input_value: str, threats: List[SecurityThreat]) -> str:
        """Sanitize input based on detected threats."""
        sanitized = input_value
        
        # HTML escape for XSS protection
        if SecurityThreat.XSS in threats or SecurityThreat.SCRIPT_INJECTION in threats:
            sanitized = html.escape(sanitized, quote=True)
        
        # Remove dangerous characters for SQL injection
        if SecurityThreat.SQL_INJECTION in threats:
            sanitized = re.sub(r'[;\'\"\\]', '', sanitized)
        
        # Encode path traversal sequences
        if SecurityThreat.PATH_TRAVERSAL in threats:
            sanitized = sanitized.replace('../', '').replace('..\\', '')
        
        # Remove command injection characters
        if SecurityThreat.COMMAND_INJECTION in threats:
            sanitized = re.sub(r'[;&|`$()]', '', sanitized)
        
        return sanitized
    
    def _validate_context(self, input_value: str, context: Dict[str, Any], 
                         result: ValidationResult) -> None:
        """Perform context-specific validation."""
        input_type = context.get('type', 'general')
        
        if input_type == 'email':
            self._validate_email(input_value, result)
        elif input_type == 'url':
            self._validate_url(input_value, result)
        elif input_type == 'filename':
            self._validate_filename(input_value, result)
        elif input_type == 'json':
            self._validate_json(input_value, result)
    
    def _validate_email(self, email: str, result: ValidationResult) -> None:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result.warnings.append("Invalid email format")
            result.confidence_score *= 0.8
    
    def _validate_url(self, url: str, result: ValidationResult) -> None:
        """Validate URL format and security."""
        # Check for suspicious protocols
        if re.match(r'^(javascript|data|vbscript|file):', url, re.IGNORECASE):
            result.is_valid = False
            result.errors.append("Dangerous URL protocol detected")
            return
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            result.warnings.append("Invalid URL format")
            result.confidence_score *= 0.8
    
    def _validate_filename(self, filename: str, result: ValidationResult) -> None:
        """Validate filename security."""
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            result.is_valid = False
            result.errors.append("Path traversal in filename")
            return
        
        # Check for dangerous extensions
        dangerous_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext in dangerous_extensions:
            result.warnings.append("Potentially dangerous file extension")
            result.confidence_score *= 0.5
    
    def _validate_json(self, json_str: str, result: ValidationResult) -> None:
        """Validate JSON input."""
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            result.warnings.append(f"Invalid JSON format: {e}")
            result.confidence_score *= 0.7
    
    def validate_bulk(self, inputs: Dict[str, str], 
                     contexts: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, ValidationResult]:
        """Validate multiple inputs efficiently."""
        results = {}
        
        for field_name, input_value in inputs.items():
            context = contexts.get(field_name) if contexts else None
            results[field_name] = self.validate_input(input_value, field_name, context)
        
        return results


# Validation decorators for easy use
def validate_input_data(validation_level: ValidationLevel = ValidationLevel.MODERATE):
    """Decorator to validate function input data."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = EnhancedInputValidator(validation_level)
            
            # Validate string arguments
            for i, arg in enumerate(args):
                if isinstance(arg, str):
                    result = validator.validate_input(arg, f"arg_{i}")
                    if not result.is_valid:
                        raise NetraSecurityException(
                            f"Invalid input in argument {i}: {result.errors}",
                            error_code="INVALID_INPUT"
                        )
            
            # Validate string keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = validator.validate_input(value, key)
                    if not result.is_valid:
                        raise NetraSecurityException(
                            f"Invalid input in parameter {key}: {result.errors}",
                            error_code="INVALID_INPUT"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global validator instances
strict_validator = EnhancedInputValidator(ValidationLevel.STRICT)
moderate_validator = EnhancedInputValidator(ValidationLevel.MODERATE)
basic_validator = EnhancedInputValidator(ValidationLevel.BASIC)