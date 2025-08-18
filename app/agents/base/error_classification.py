"""Error classification system.

Business Value: Enables intelligent error handling and recovery strategies.
"""

from typing import Dict, Type, Optional
from enum import Enum
from dataclasses import dataclass

from app.core.error_codes import ErrorSeverity


class ErrorCategory(Enum):
    """Error category classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    LLM = "llm"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorClassification:
    """Error classification details."""
    category: ErrorCategory
    severity: ErrorSeverity
    is_retryable: bool
    requires_fallback: bool
    recovery_time_seconds: Optional[int] = None


class ErrorClassifier:
    """Classifies exceptions into structured error categories."""
    
    def __init__(self):
        self._error_classifiers = self._initialize_error_classifiers()
    
    def _initialize_error_classifiers(self) -> Dict[Type[Exception], ErrorClassification]:
        """Initialize error classification mapping."""
        from .agent_errors import ValidationError, ExternalServiceError, DatabaseError
        return self._build_error_classifier_mapping(ValidationError, ExternalServiceError, DatabaseError)
    
    def _create_validation_classification(self) -> ErrorClassification:
        """Create classification for validation errors."""
        return ErrorClassification(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            is_retryable=False,
            requires_fallback=False
        )
    
    def _create_service_classification(self) -> ErrorClassification:
        """Create classification for external service errors."""
        return ErrorClassification(
            category=ErrorCategory.EXTERNAL_SERVICE, severity=ErrorSeverity.MEDIUM,
            is_retryable=True, requires_fallback=True, recovery_time_seconds=30
        )
    
    def _create_database_classification(self) -> ErrorClassification:
        """Create classification for database errors."""
        return ErrorClassification(
            category=ErrorCategory.DATABASE, severity=ErrorSeverity.HIGH,
            is_retryable=True, requires_fallback=True, recovery_time_seconds=60
        )
    
    def classify_error(self, error: Exception) -> ErrorClassification:
        """Classify an error into categories."""
        for error_type, classification in self._error_classifiers.items():
            if isinstance(error, error_type):
                return classification
        
        return self._classify_by_message(error)
    
    def _classify_by_message(self, error: Exception) -> ErrorClassification:
        """Classify error by analyzing message content."""
        message = str(error).lower()
        
        if self._is_network_related_error(message):
            return self._create_network_classification()
        
        return self._create_unknown_classification()
    
    def _is_network_related_error(self, message: str) -> bool:
        """Check if error message indicates network issue."""
        network_terms = ["timeout", "connection"]
        return any(term in message for term in network_terms)
    
    def _create_network_classification(self) -> ErrorClassification:
        """Create classification for network errors."""
        return ErrorClassification(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            is_retryable=True,
            requires_fallback=True
        )
    
    def _create_unknown_classification(self) -> ErrorClassification:
        """Create classification for unknown errors."""
        return ErrorClassification(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            is_retryable=False,
            requires_fallback=True
        )