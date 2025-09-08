"""
Enhanced input validation system with comprehensive security checks.
Validates all inputs to prevent injection attacks, XSS, and other security vulnerabilities.
"""

# Import core validation functionality
from netra_backend.app.core.input_sanitizers import InputNormalizer, InputSanitizer
from netra_backend.app.core.input_validators import (
    EnhancedInputValidator,
    SecurityValidationResult,
    basic_validator,
    moderate_validator,
    strict_validator,
    validate_input_data,
)
from netra_backend.app.core.validation_rules import SecurityThreat, ValidationLevel

# Create alias for backward compatibility
InputValidator = EnhancedInputValidator

# Re-export for backward compatibility
__all__ = [
    'ValidationLevel',
    'SecurityThreat', 
    'SecurityValidationResult',
    'EnhancedInputValidator',
    'InputValidator',  # Alias
    'validate_input_data',
    'strict_validator',
    'moderate_validator', 
    'basic_validator',
    'InputNormalizer',
    'InputSanitizer'
]