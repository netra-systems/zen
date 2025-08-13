"""Configuration and validation exceptions - compliant with 8-line function limit."""

from typing import List, Optional, Dict, Any
from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class ConfigurationError(NetraException):
    """Raised when configuration issues are encountered."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Configuration error occurred",
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ValidationError(NetraException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str = None, validation_errors: List[str] = None, **kwargs):
        details = self._build_validation_details(kwargs.get('details', {}), validation_errors)
        super().__init__(
            message=message or "Data validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            user_message="Please check your input and try again",
            **kwargs
        )
    
    def _build_validation_details(self, details: Dict[str, Any], validation_errors: Optional[List[str]]) -> Dict[str, Any]:
        """Build details dict with validation errors."""
        if validation_errors:
            details['validation_errors'] = validation_errors
        return details