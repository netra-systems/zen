"""Triage Request Validator

This module handles validation and security checks for user requests.
"""

import re
from .models import ValidationStatus


class RequestValidator:
    """Validates and sanitizes user requests"""
    
    def __init__(self):
        """Initialize the request validator"""
        self.injection_patterns = self._get_injection_patterns()
    
    def _get_injection_patterns(self):
        """Get injection attack patterns."""
        script_patterns = self._get_script_patterns()
        sql_patterns = self._get_sql_patterns()
        command_patterns = self._get_command_patterns()
        return script_patterns + sql_patterns + command_patterns
    
    def _get_script_patterns(self):
        """Get script injection patterns."""
        return [
            r'<script', r'javascript:', r"eval\s*\(",
            r"document\.cookie", r"<img.*onerror"
        ]
    
    def _get_sql_patterns(self):
        """Get SQL injection patterns."""
        return [
            r'DROP\s+TABLE', r'DELETE\s+FROM', r'INSERT\s+INTO',
            r'UNION\s+SELECT', r"'\s*OR\s*'", r";\s*DELETE",
            r"--\s*$", r"admin'\s*--", r"SELECT.*FROM.*users",
            r"SELECT.*FROM.*secrets"
        ]
    
    def _get_command_patterns(self):
        """Get command injection patterns."""
        return [
            r"rm\s+-rf\s+/", r"cat\s+/etc/passwd", r";\s*curl\s+",
            r"\$\(", r"`.*`", r"/etc/passwd", r"&&\s*rm", r"\|\s*rm"
        ]
    
    def validate_request(self, request: str) -> ValidationStatus:
        """Validate and sanitize the user request"""
        validation = ValidationStatus()
        
        self._perform_all_validation_checks(request, validation)
        return validation
    
    def _perform_all_validation_checks(self, request: str, validation: ValidationStatus):
        """Perform all validation checks on request."""
        validation = self._check_length(request, validation)
        validation = self._check_security(request, validation)
        validation = self._check_edge_cases(request, validation)
    
    def _check_length(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check request length limits"""
        if len(request) > 10000:
            self._add_length_error(validation, "Request exceeds maximum length of 10000 characters")
        elif len(request) < 3:
            self._add_length_error(validation, "Request is too short to process")
        
        return validation
    
    def _add_length_error(self, validation: ValidationStatus, error_message: str):
        """Add length validation error."""
        validation.validation_errors.append(error_message)
        validation.is_valid = False
    
    def _check_security(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check for potential security issues"""
        for pattern in self.injection_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                self._add_security_error(validation)
                break
        
        return validation
    
    def _add_security_error(self, validation: ValidationStatus):
        """Add security validation error."""
        validation.validation_errors.append("Potentially malicious pattern detected")
        validation.is_valid = False
    
    def _check_edge_cases(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check for edge cases and add warnings"""
        self._check_request_length_warning(request, validation)
        self._check_alphabetic_characters(request, validation)
        return validation
    
    def _check_request_length_warning(self, request: str, validation: ValidationStatus):
        """Check if request is very long and add warning."""
        if len(request) > 5000:
            validation.warnings.append("Request is very long, processing may take longer")
    
    def _check_alphabetic_characters(self, request: str, validation: ValidationStatus):
        """Check if request contains alphabetic characters."""
        if not re.search(r'[a-zA-Z]', request):
            validation.warnings.append("Request contains no alphabetic characters")