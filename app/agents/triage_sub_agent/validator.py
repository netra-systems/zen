"""Triage Request Validator

This module handles validation and security checks for user requests.
"""

import re
from .models import ValidationStatus


class RequestValidator:
    """Validates and sanitizes user requests"""
    
    def __init__(self):
        """Initialize the request validator"""
        self.injection_patterns = [
            r'<script',
            r'javascript:',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UNION\s+SELECT',
            r"'\s*OR\s*'",
            r";\s*DELETE",
            r"--\s*$",
            r"admin'\s*--",
            r"eval\s*\(",
            r"document\.cookie",
            r"<img.*onerror",
            r"SELECT.*FROM.*users",
            r"SELECT.*FROM.*secrets",
            # Command injection patterns
            r"rm\s+-rf\s+/",
            r"cat\s+/etc/passwd",
            r";\s*curl\s+",
            r"\$\(",
            r"`.*`",
            r"/etc/passwd",
            r"&&\s*rm",
            r"\|\s*rm"
        ]
    
    def validate_request(self, request: str) -> ValidationStatus:
        """Validate and sanitize the user request"""
        validation = ValidationStatus()
        
        # Check request length
        validation = self._check_length(request, validation)
        
        # Check for injection patterns
        validation = self._check_security(request, validation)
        
        # Add warnings for edge cases
        validation = self._check_edge_cases(request, validation)
        
        return validation
    
    def _check_length(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check request length limits"""
        if len(request) > 10000:
            validation.validation_errors.append(
                "Request exceeds maximum length of 10000 characters"
            )
            validation.is_valid = False
        elif len(request) < 3:
            validation.validation_errors.append("Request is too short to process")
            validation.is_valid = False
        
        return validation
    
    def _check_security(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check for potential security issues"""
        for pattern in self.injection_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                validation.validation_errors.append("Potentially malicious pattern detected")
                validation.is_valid = False
                break
        
        return validation
    
    def _check_edge_cases(self, request: str, validation: ValidationStatus) -> ValidationStatus:
        """Check for edge cases and add warnings"""
        if len(request) > 5000:
            validation.warnings.append(
                "Request is very long, processing may take longer"
            )
        
        if not re.search(r'[a-zA-Z]', request):
            validation.warnings.append("Request contains no alphabetic characters")
        
        return validation