"""WebSocket Error Validator - Test Compatibility Module

COMPATIBILITY MODULE: This module provides error validation functionality for
WebSocket tests that expect structured error handling validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Test Infrastructure)
- Business Goal: Enable comprehensive WebSocket error testing
- Value Impact: Ensures WebSocket errors are properly validated and handled
- Revenue Impact: Protects $500K+ ARR by ensuring chat reliability

COMPLIANCE NOTES:
- This is a COMPATIBILITY MODULE for test infrastructure
- Provides structured error validation for WebSocket operations
- Follows SSOT principles by integrating with unified error handling
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketErrorType(Enum):
    """WebSocket error types for validation."""
    CONNECTION_FAILED = "connection_failed"
    MESSAGE_DELIVERY_FAILED = "message_delivery_failed"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN = "unknown"


class WebSocketErrorSeverity(Enum):
    """WebSocket error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventCriticality(Enum):
    """Event criticality levels for test compatibility (alias for WebSocketErrorSeverity)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Validation result data structure for test compatibility."""
    is_valid: bool
    issues: List[str]
    warnings: List[str] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    
    def __post_init__(self):
        self.error_count = len(self.issues) if self.issues else 0
        self.warning_count = len(self.warnings) if self.warnings else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'is_valid': self.is_valid,
            'issues': self.issues or [],
            'warnings': self.warnings or [],
            'error_count': self.error_count,
            'warning_count': self.warning_count
        }


@dataclass
class WebSocketError:
    """WebSocket error data structure."""
    error_type: WebSocketErrorType
    severity: WebSocketErrorSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    connection_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    recoverable: bool = True
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'error_type': self.error_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details or {},
            'user_id': self.user_id,
            'connection_id': self.connection_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'recoverable': self.recoverable
        }


class WebSocketErrorValidator:
    """Validator for WebSocket errors with comprehensive validation rules."""
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        logger.debug("WebSocketErrorValidator initialized")
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules for different error scenarios."""
        return {
            'connection_timeout_ms': 30000,
            'message_size_limit_bytes': 1024 * 1024,  # 1MB
            'rate_limit_per_minute': 100,
            'required_fields': ['error_type', 'severity', 'message'],
            'severity_escalation': {
                WebSocketErrorType.CONNECTION_FAILED: WebSocketErrorSeverity.HIGH,
                WebSocketErrorType.AUTHENTICATION_FAILED: WebSocketErrorSeverity.CRITICAL,
                WebSocketErrorType.TIMEOUT: WebSocketErrorSeverity.MEDIUM,
                WebSocketErrorType.RATE_LIMITED: WebSocketErrorSeverity.MEDIUM,
                WebSocketErrorType.INTERNAL_ERROR: WebSocketErrorSeverity.HIGH
            }
        }
    
    def validate_error(self, error: Union[WebSocketError, Dict[str, Any]]) -> List[str]:
        """
        Validate a WebSocket error for completeness and compliance.
        
        Args:
            error: WebSocket error to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Convert dict to WebSocketError if needed
        if isinstance(error, dict):
            try:
                error = self._dict_to_websocket_error(error)
            except Exception as e:
                issues.append(f"Failed to parse error dict: {e}")
                return issues
        
        # Validate required fields
        for field in self.validation_rules['required_fields']:
            if not hasattr(error, field) or getattr(error, field) is None:
                issues.append(f"Missing required field: {field}")
        
        # Validate error type
        if not isinstance(error.error_type, WebSocketErrorType):
            issues.append("error_type must be a valid WebSocketErrorType")
        
        # Validate severity
        if not isinstance(error.severity, WebSocketErrorSeverity):
            issues.append("severity must be a valid WebSocketErrorSeverity")
        
        # Validate message
        if not error.message or len(error.message.strip()) == 0:
            issues.append("message cannot be empty")
        elif len(error.message) > 1000:
            issues.append("message too long (max 1000 characters)")
        
        # Validate severity escalation rules
        expected_severity = self.validation_rules['severity_escalation'].get(error.error_type)
        if expected_severity and error.severity.value != expected_severity.value:
            issues.append(
                f"Severity mismatch for {error.error_type.value}: "
                f"expected {expected_severity.value}, got {error.severity.value}"
            )
        
        # Validate user_id format if present
        if error.user_id and not isinstance(error.user_id, str):
            issues.append("user_id must be a string")
        
        # Validate connection_id format if present
        if error.connection_id and not isinstance(error.connection_id, str):
            issues.append("connection_id must be a string")
        
        return issues
    
    def _dict_to_websocket_error(self, error_dict: Dict[str, Any]) -> WebSocketError:
        """Convert dictionary to WebSocketError."""
        # Parse error type
        error_type_str = error_dict.get('error_type', 'unknown')
        try:
            error_type = WebSocketErrorType(error_type_str)
        except ValueError:
            error_type = WebSocketErrorType.UNKNOWN
        
        # Parse severity
        severity_str = error_dict.get('severity', 'medium')
        try:
            severity = WebSocketErrorSeverity(severity_str)
        except ValueError:
            severity = WebSocketErrorSeverity.MEDIUM
        
        # Parse timestamp
        timestamp = None
        if error_dict.get('timestamp'):
            try:
                timestamp = datetime.fromisoformat(error_dict['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                timestamp = datetime.now(timezone.utc)
        
        return WebSocketError(
            error_type=error_type,
            severity=severity,
            message=error_dict.get('message', ''),
            details=error_dict.get('details'),
            user_id=error_dict.get('user_id'),
            connection_id=error_dict.get('connection_id'),
            timestamp=timestamp,
            recoverable=error_dict.get('recoverable', True)
        )
    
    def validate_error_recovery(self, error: WebSocketError) -> Dict[str, Any]:
        """
        Validate error recovery options and recommendations.
        
        Args:
            error: WebSocket error to analyze
            
        Returns:
            Recovery analysis and recommendations
        """
        recovery_analysis = {
            'is_recoverable': error.recoverable,
            'recommended_actions': [],
            'retry_strategy': None,
            'escalation_required': False
        }
        
        # Determine recovery actions based on error type
        if error.error_type == WebSocketErrorType.CONNECTION_FAILED:
            recovery_analysis['recommended_actions'].extend([
                'retry_connection',
                'check_network_connectivity',
                'validate_server_availability'
            ])
            recovery_analysis['retry_strategy'] = 'exponential_backoff'
        
        elif error.error_type == WebSocketErrorType.AUTHENTICATION_FAILED:
            recovery_analysis['recommended_actions'].extend([
                'refresh_authentication_token',
                'redirect_to_login'
            ])
            recovery_analysis['escalation_required'] = True
        
        elif error.error_type == WebSocketErrorType.TIMEOUT:
            recovery_analysis['recommended_actions'].extend([
                'retry_with_longer_timeout',
                'check_message_size'
            ])
            recovery_analysis['retry_strategy'] = 'linear_backoff'
        
        elif error.error_type == WebSocketErrorType.RATE_LIMITED:
            recovery_analysis['recommended_actions'].extend([
                'implement_rate_limiting_backoff',
                'queue_messages_for_later'
            ])
            recovery_analysis['retry_strategy'] = 'rate_limited_backoff'
        
        elif error.severity == WebSocketErrorSeverity.CRITICAL:
            recovery_analysis['escalation_required'] = True
            recovery_analysis['recommended_actions'].append('immediate_escalation')
        
        return recovery_analysis
    
    def create_test_error(self, 
                         error_type: WebSocketErrorType,
                         severity: WebSocketErrorSeverity = WebSocketErrorSeverity.MEDIUM,
                         message: str = "Test error",
                         **kwargs) -> WebSocketError:
        """
        Create a test WebSocket error for validation testing.
        
        Args:
            error_type: Type of error to create
            severity: Severity level (defaults to MEDIUM)
            message: Error message
            **kwargs: Additional error attributes
            
        Returns:
            WebSocketError instance for testing
        """
        return WebSocketError(
            error_type=error_type,
            severity=severity,
            message=message,
            details=kwargs.get('details'),
            user_id=kwargs.get('user_id'),
            connection_id=kwargs.get('connection_id'),
            timestamp=kwargs.get('timestamp'),
            recoverable=kwargs.get('recoverable', True)
        )


class WebSocketErrorHandler:
    """Handler for processing and managing WebSocket errors."""
    
    def __init__(self, validator: Optional[WebSocketErrorValidator] = None):
        self.validator = validator or WebSocketErrorValidator()
        self.error_history: List[WebSocketError] = []
        logger.debug("WebSocketErrorHandler initialized")
    
    async def handle_error(self, error: Union[WebSocketError, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Handle a WebSocket error with validation and recovery recommendations.
        
        Args:
            error: WebSocket error to handle
            
        Returns:
            Error handling result with validation and recovery info
        """
        # Validate the error
        if isinstance(error, dict):
            error = self.validator._dict_to_websocket_error(error)
        
        validation_issues = self.validator.validate_error(error)
        recovery_analysis = self.validator.validate_error_recovery(error)
        
        # Store error in history
        self.error_history.append(error)
        
        # Log error based on severity
        if error.severity == WebSocketErrorSeverity.CRITICAL:
            logger.critical(f"Critical WebSocket error: {error.message}")
        elif error.severity == WebSocketErrorSeverity.HIGH:
            logger.error(f"High severity WebSocket error: {error.message}")
        elif error.severity == WebSocketErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity WebSocket error: {error.message}")
        else:
            logger.info(f"Low severity WebSocket error: {error.message}")
        
        return {
            'error': error.to_dict(),
            'validation_issues': validation_issues,
            'recovery_analysis': recovery_analysis,
            'handled_at': datetime.now(timezone.utc).isoformat(),
            'is_valid': len(validation_issues) == 0
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about handled errors."""
        if not self.error_history:
            return {
                'total_errors': 0,
                'by_type': {},
                'by_severity': {},
                'recoverable_percentage': 0.0
            }
        
        by_type = {}
        by_severity = {}
        recoverable_count = 0
        
        for error in self.error_history:
            # Count by type
            type_key = error.error_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Count by severity
            severity_key = error.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
            
            # Count recoverable
            if error.recoverable:
                recoverable_count += 1
        
        return {
            'total_errors': len(self.error_history),
            'by_type': by_type,
            'by_severity': by_severity,
            'recoverable_percentage': (recoverable_count / len(self.error_history)) * 100
        }
    
    def clear_error_history(self):
        """Clear the error history."""
        self.error_history.clear()
        logger.debug("Error history cleared")


# Factory functions for test compatibility

def create_websocket_error_validator() -> WebSocketErrorValidator:
    """Create a WebSocket error validator instance."""
    return WebSocketErrorValidator()


def create_websocket_error_handler(validator: Optional[WebSocketErrorValidator] = None) -> WebSocketErrorHandler:
    """Create a WebSocket error handler instance."""
    return WebSocketErrorHandler(validator)


def get_websocket_validator() -> WebSocketErrorValidator:
    """Get or create a WebSocket validator instance (compatibility function)."""
    return create_websocket_error_validator()


def reset_websocket_validator():
    """Reset WebSocket validator state (compatibility function for tests)."""
    # This is a no-op function for stateless validator compatibility
    logger.debug("WebSocket validator reset called (stateless validator - no-op)")
    pass


# Legacy alias for test compatibility
WebSocketEventValidator = WebSocketErrorValidator

# Export classes and functions
__all__ = [
    'WebSocketError',
    'WebSocketErrorType',
    'WebSocketErrorSeverity',
    'EventCriticality',
    'WebSocketErrorValidator',
    'WebSocketEventValidator',  # Legacy alias
    'WebSocketErrorHandler',
    'ValidationResult',
    'create_websocket_error_validator',
    'create_websocket_error_handler',
    'get_websocket_validator',
    'reset_websocket_validator'
]

logger.info("WebSocket Error Validator compatibility module loaded")