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
from app.core.exceptions_auth import NetraSecurityException

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


# ValidationResult imported from shared_types.py
# Using import alias for this specific validation context
from app.schemas.shared_types import ValidationResult as BaseValidationResult

class SecurityValidationResult(BaseValidationResult):
    """Extended validation result for security-specific validation."""
    threats_detected: List[str] = Field(default_factory=list, description="Security threats found")


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
        self._compile_injection_patterns(patterns)
        self._compile_web_attack_patterns(patterns)
        self._compile_system_attack_patterns(patterns)
        self._compile_data_attack_patterns(patterns)
        return patterns
    
    def _compile_injection_patterns(self, patterns: Dict[SecurityThreat, List[re.Pattern]]) -> None:
        """Compile SQL and command injection patterns."""
        patterns[SecurityThreat.SQL_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SQL_PATTERNS
        ]
        patterns[SecurityThreat.COMMAND_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.COMMAND_PATTERNS
        ]
    
    def _compile_web_attack_patterns(self, patterns: Dict[SecurityThreat, List[re.Pattern]]) -> None:
        """Compile XSS and script injection patterns."""
        patterns[SecurityThreat.XSS] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.XSS_PATTERNS
        ]
        patterns[SecurityThreat.SCRIPT_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SCRIPT_PATTERNS
        ]
    
    def _compile_system_attack_patterns(self, patterns: Dict[SecurityThreat, List[re.Pattern]]) -> None:
        """Compile path traversal and LDAP injection patterns."""
        patterns[SecurityThreat.PATH_TRAVERSAL] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.PATH_TRAVERSAL_PATTERNS
        ]
        patterns[SecurityThreat.LDAP_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.LDAP_PATTERNS
        ]
    
    def _compile_data_attack_patterns(self, patterns: Dict[SecurityThreat, List[re.Pattern]]) -> None:
        """Compile XML injection patterns."""
        patterns[SecurityThreat.XML_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.XML_PATTERNS
        ]
    
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
                      context: Optional[Dict[str, Any]] = None) -> BaseValidationResult:
        """Comprehensive input validation."""
        try:
            if not input_value:
                return self._create_empty_input_result()
            return self._perform_comprehensive_validation(input_value, field_name, context)
        except Exception as e:
            return self._create_error_result(field_name, e)
    
    def _create_empty_input_result(self) -> BaseValidationResult:
        """Create result for empty input."""
        return BaseValidationResult(
            is_valid=True,
            sanitized_value="",
            confidence_score=1.0
        )
    
    def _create_base_validation_result(self, input_value: str) -> BaseValidationResult:
        """Create base validation result object."""
        return BaseValidationResult(is_valid=True, sanitized_value=input_value)
    
    def _perform_basic_validation_checks(self, input_value: str, result: BaseValidationResult) -> None:
        """Perform basic validation checks."""
        self._check_length(input_value, result)
        self._check_encoding(input_value, result)
    
    def _detect_and_process_threats(self, input_value: str, result: BaseValidationResult, field_name: str) -> List[SecurityThreat]:
        """Detect threats and update result validity."""
        threats = self._detect_threats(input_value)
        result.threats_detected.extend(threats)
        if threats:
            self._mark_result_as_invalid(result, field_name, threats)
        return threats
    
    def _mark_result_as_invalid(self, result: BaseValidationResult, field_name: str, threats: List[SecurityThreat]) -> None:
        """Mark validation result as invalid due to threats."""
        result.is_valid = False
        result.errors.append(f"Security threats detected in {field_name}: {[t.value for t in threats]}")
        result.confidence_score = 0.0
    
    def _apply_context_validation(self, input_value: str, context: Optional[Dict[str, Any]], result: BaseValidationResult) -> None:
        """Apply context-specific validation if provided."""
        if context:
            self._validate_context(input_value, context, result)
    
    def _create_error_result(self, field_name: str, error: Exception) -> BaseValidationResult:
        """Create validation result for error cases."""
        logger.error(f"Input validation error for {field_name}: {error}")
        return BaseValidationResult(
            is_valid=False,
            errors=[f"Validation error: {str(error)}"],
            confidence_score=0.0
        )
    
    def _perform_comprehensive_validation(self, input_value: str, field_name: str, 
                                        context: Optional[Dict[str, Any]]) -> BaseValidationResult:
        """Perform comprehensive validation on input value."""
        result = self._create_base_validation_result(input_value)
        self._perform_basic_validation_checks(input_value, result)
        threats = self._detect_and_process_threats(input_value, result, field_name)
        result.sanitized_value = self._sanitize_input(input_value, threats)
        self._apply_context_validation(input_value, context, result)
        return result
    
    def _check_threat_patterns(self, patterns: List[re.Pattern], normalized_input: str, 
                             threat_type: SecurityThreat, input_value: str) -> bool:
        """Check if any pattern matches the normalized input."""
        for pattern in patterns:
            if pattern.search(normalized_input):
                logger.warning(f"Detected {threat_type.value} in input: {input_value[:100]}...")
                return True
        return False
    
    def _has_dangerous_protocol(self, url: str) -> bool:
        """Check if URL has dangerous protocol."""
        return bool(re.match(r'^(javascript|data|vbscript|file):', url, re.IGNORECASE))
    
    def _has_valid_url_format(self, url: str) -> bool:
        """Check if URL has valid format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url, re.IGNORECASE))
    
    def _has_path_traversal(self, filename: str) -> bool:
        """Check if filename contains path traversal."""
        return '..' in filename or '/' in filename or '\\' in filename
    
    def _has_dangerous_extension(self, filename: str) -> bool:
        """Check if filename has dangerous extension."""
        dangerous_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        return file_ext in dangerous_extensions
    
    def _is_double_encoded(self, input_value: str, decoded: str) -> bool:
        """Check if input is double URL encoded."""
        return decoded != input_value and urllib.parse.unquote(decoded) != decoded
    
    def _has_suspicious_base64_content(self, input_value: str) -> bool:
        """Check if base64 content contains suspicious characters."""
        decoded_b64 = base64.b64decode(input_value).decode('utf-8', errors='ignore')
        return any(char in decoded_b64 for char in self.suspicious_chars)
    
    def _check_length(self, input_value: str, result: BaseValidationResult) -> None:
        """Check input length."""
        if len(input_value) > self.max_input_length:
            result.warnings.append(f"Input length ({len(input_value)}) exceeds maximum ({self.max_input_length})")
            result.confidence_score *= 0.8
    
    def _check_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for encoding issues."""
        try:
            self._check_double_url_encoding(input_value, result)
            self._check_base64_encoding(input_value, result)
        except Exception as e:
            result.warnings.append(f"Encoding check failed: {e}")
    
    def _check_double_url_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for double URL encoding."""
        decoded = urllib.parse.unquote(input_value)
        if self._is_double_encoded(input_value, decoded):
            result.warnings.append("Potential double URL encoding detected")
            result.confidence_score *= 0.9
    
    def _check_base64_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for suspicious base64 encoded content."""
        if not self._is_valid_base64_format(input_value):
            return
        try:
            if self._has_suspicious_base64_content(input_value):
                result.warnings.append("Suspicious base64 encoded content")
                result.confidence_score *= 0.7
        except Exception:
            pass
    
    def _is_valid_base64_format(self, input_value: str) -> bool:
        """Check if string matches base64 format."""
        pattern_match = re.match(r'^[A-Za-z0-9+/]*={0,2}$', input_value)
        correct_length = len(input_value) % 4 == 0
        return bool(pattern_match and correct_length)
    
    def _detect_threats(self, input_value: str) -> List[SecurityThreat]:
        """Detect security threats in input."""
        threats = []
        normalized_input = self._normalize_for_detection(input_value)
        
        for threat_type, patterns in self.threat_patterns.items():
            if self._check_threat_patterns(patterns, normalized_input, threat_type, input_value):
                threats.append(threat_type)
        return threats
    
    def _normalize_for_detection(self, input_value: str) -> str:
        """Normalize input for better threat detection."""
        normalized = urllib.parse.unquote(input_value)
        normalized = html.unescape(normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.lower()
        return normalized
    
    def _sanitize_input(self, input_value: str, threats: List[SecurityThreat]) -> str:
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
    
    def _validate_context(self, input_value: str, context: Dict[str, Any], 
                         result: BaseValidationResult) -> None:
        """Perform context-specific validation."""
        input_type = context.get('type', 'general')
        validation_map = {
            'email': self._validate_email, 'url': self._validate_url,
            'filename': self._validate_filename, 'json': self._validate_json
        }
        if input_type in validation_map:
            validation_map[input_type](input_value, result)
    
    def _validate_email(self, email: str, result: BaseValidationResult) -> None:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result.warnings.append("Invalid email format")
            result.confidence_score *= 0.8
    
    def _validate_url(self, url: str, result: BaseValidationResult) -> None:
        """Validate URL format and security."""
        if self._has_dangerous_protocol(url):
            result.is_valid = False
            result.errors.append("Dangerous URL protocol detected")
            return
        if not self._has_valid_url_format(url):
            result.warnings.append("Invalid URL format")
            result.confidence_score *= 0.8
    
    def _validate_filename(self, filename: str, result: BaseValidationResult) -> None:
        """Validate filename security."""
        if self._has_path_traversal(filename):
            result.is_valid = False
            result.errors.append("Path traversal in filename")
            return
        if self._has_dangerous_extension(filename):
            result.warnings.append("Potentially dangerous file extension")
            result.confidence_score *= 0.5
    
    def _validate_json(self, json_str: str, result: BaseValidationResult) -> None:
        """Validate JSON input."""
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            result.warnings.append(f"Invalid JSON format: {e}")
            result.confidence_score *= 0.7
    
    def validate_bulk(self, inputs: Dict[str, str], 
                     contexts: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, BaseValidationResult]:
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
            _validate_positional_arguments(validator, args)
            _validate_keyword_arguments(validator, kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def _validate_positional_arguments(validator: EnhancedInputValidator, args: tuple) -> None:
    """Validate positional string arguments."""
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            result = validator.validate_input(arg, f"arg_{i}")
            if not result.is_valid:
                _raise_validation_exception(f"argument {i}", result.errors)

def _validate_keyword_arguments(validator: EnhancedInputValidator, kwargs: dict) -> None:
    """Validate keyword string arguments."""
    for key, value in kwargs.items():
        if isinstance(value, str):
            result = validator.validate_input(value, key)
            if not result.is_valid:
                _raise_validation_exception(f"parameter {key}", result.errors)

def _raise_validation_exception(location: str, errors: list) -> None:
    """Raise NetraSecurityException for validation failures."""
    raise NetraSecurityException(
        message=f"Invalid input in {location}: {errors}"
    )


# Global validator instances
strict_validator = EnhancedInputValidator(ValidationLevel.STRICT)
moderate_validator = EnhancedInputValidator(ValidationLevel.MODERATE)
basic_validator = EnhancedInputValidator(ValidationLevel.BASIC)