# Triage Validators Module - Request validation and sanitization
import re
from typing import List
from app.agents.triage.models import ValidationStatus

class RequestValidator:
    """Validates and sanitizes user requests."""
    
    MAX_REQUEST_LENGTH = 10000
    MIN_REQUEST_LENGTH = 3
    
    @staticmethod
    def validate(request: str) -> ValidationStatus:
        """Validate and sanitize the user request."""
        validation = ValidationStatus()
        
        # Check request length
        if len(request) > RequestValidator.MAX_REQUEST_LENGTH:
            validation.validation_errors.append(
                f"Request exceeds maximum length of {RequestValidator.MAX_REQUEST_LENGTH} characters"
            )
            validation.is_valid = False
        elif len(request) < RequestValidator.MIN_REQUEST_LENGTH:
            validation.validation_errors.append("Request is too short to process")
            validation.is_valid = False
        
        # Check for injection patterns
        if RequestValidator._has_injection_patterns(request):
            validation.validation_errors.append("Potentially malicious pattern detected")
            validation.is_valid = False
        
        # Add warnings for edge cases
        if len(request) > 5000:
            validation.warnings.append("Request is very long, processing may take longer")
        
        if not re.search(r'[a-zA-Z]', request):
            validation.warnings.append("Request contains no alphabetic characters")
        
        return validation
    
    @staticmethod
    def _has_injection_patterns(request: str) -> bool:
        """Check for common injection patterns."""
        patterns = RequestValidator._get_injection_patterns()
        for pattern in patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def _get_injection_patterns() -> List[str]:
        """Get list of injection patterns to check."""
        return [
            r'<script', r'javascript:', r'DROP\s+TABLE', r'DELETE\s+FROM',
            r'INSERT\s+INTO', r'UNION\s+SELECT', r"'\s*OR\s*'", r";\s*DELETE",
            r"--\s*$", r"admin'\s*--", r"eval\s*\(", r"document\.cookie",
            r"<img.*onerror", r"SELECT.*FROM.*users", r"SELECT.*FROM.*secrets",
            r"rm\s+-rf\s+/", r"cat\s+/etc/passwd", r";\s*curl\s+", r"\$\(",
            r"`.*`", r"/etc/passwd", r"&&\s*rm", r"\|\s*rm"
        ]