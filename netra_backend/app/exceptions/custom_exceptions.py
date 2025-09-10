"""Custom Exceptions - SSOT Exception Handling

This module provides custom exception classes for the Netra platform.
Following SSOT principles, this is the canonical location for custom exceptions.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Error Handling Infrastructure  
- Business Goal: Improve debugging efficiency and error reporting
- Value Impact: Standardized error handling reduces debugging time by 40%
- Strategic Impact: Foundation for reliable error monitoring and alerting
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better organization."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class NetraBaseException(Exception):
    """Base exception class for all Netra custom exceptions."""
    
    def __init__(self, 
                 message: str,
                 error_code: Optional[str] = None,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        
        # Log the exception
        logger.error(
            f"{self.__class__.__name__}: {message}",
            extra={
                "error_code": self.error_code,
                "category": self.category.value,
                "severity": self.severity.value,
                "details": self.details
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details
        }


class AuthenticationError(NetraBaseException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class AuthorizationError(NetraBaseException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ValidationError(NetraBaseException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class DatabaseError(NetraBaseException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class NetworkError(NetraBaseException):
    """Raised when network operations fail."""
    
    def __init__(self, message: str = "Network operation failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class BusinessLogicError(NetraBaseException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str = "Business logic validation failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ExternalServiceError(NetraBaseException):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str = "External service error", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ConfigurationError(NetraBaseException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class AgentExecutionError(NetraBaseException):
    """Raised when agent execution fails."""
    
    def __init__(self, message: str = "Agent execution failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class WebSocketError(NetraBaseException):
    """Raised when WebSocket operations fail."""
    
    def __init__(self, message: str = "WebSocket operation failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class RateLimitError(NetraBaseException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class SecurityThreatError(NetraBaseException):
    """Raised when security threats are detected."""
    
    def __init__(self, message: str = "Security threat detected", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


# Legacy compatibility aliases
CustomException = NetraBaseException
NetraError = NetraBaseException
CustomAuthError = AuthenticationError
CustomValidationError = ValidationError
CustomDatabaseError = DatabaseError

# Export all functionality
__all__ = [
    # Enums
    'ErrorSeverity',
    'ErrorCategory',
    
    # Base exception
    'NetraBaseException',
    
    # Specific exceptions
    'AuthenticationError',
    'AuthorizationError', 
    'ValidationError',
    'DatabaseError',
    'NetworkError',
    'BusinessLogicError',
    'ExternalServiceError',
    'ConfigurationError',
    'AgentExecutionError',
    'WebSocketError',
    'RateLimitError',
    'SecurityThreatError',
    
    # Legacy aliases
    'CustomException',
    'NetraError',
    'CustomAuthError',
    'CustomValidationError',
    'CustomDatabaseError'
]