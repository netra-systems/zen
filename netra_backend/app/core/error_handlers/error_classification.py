"""Error classification and categorization logic.

Provides consistent error classification across the system.
Maps exception types to categories and severities.
"""

from typing import Dict
from dataclasses import dataclass

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.core.exceptions_agent import AgentError


@dataclass
class ErrorClassification:
    """Error classification result."""
    category: ErrorCategory
    severity: ErrorSeverity
    is_retryable: bool
    requires_fallback: bool


class ErrorClassifier:
    """Classifies errors into categories and determines handling strategy."""
    
    def __init__(self):
        """Initialize error classifier with mapping tables."""
        self._category_map = self._build_category_mapping()
        self._severity_map = self._build_severity_mapping()
        self._retryable_categories = self._build_retryable_categories()
        self._fallback_categories = self._build_fallback_categories()
    
    def classify_error(self, error: Exception) -> ErrorClassification:
        """Classify error and determine handling strategy."""
        error_type = type(error).__name__
        category = self._determine_category(error_type)
        severity = self._determine_severity(error_type)
        
        return ErrorClassification(
            category=category,
            severity=severity,
            is_retryable=self._is_retryable(category),
            requires_fallback=self._requires_fallback(category)
        )
    
    def _build_category_mapping(self) -> Dict[str, ErrorCategory]:
        """Build exception type to category mapping."""
        return {
            # Validation errors
            'ValidationError': ErrorCategory.VALIDATION,
            'pydantic.ValidationError': ErrorCategory.VALIDATION,
            
            # Network errors
            'ConnectionError': ErrorCategory.NETWORK,
            'TimeoutError': ErrorCategory.TIMEOUT,
            'asyncio.TimeoutError': ErrorCategory.TIMEOUT,
            
            # WebSocket errors
            'WebSocketDisconnect': ErrorCategory.WEBSOCKET,
            
            # Database errors
            'DatabaseError': ErrorCategory.DATABASE,
            'SQLAlchemyError': ErrorCategory.DATABASE,
            
            # Resource errors
            'MemoryError': ErrorCategory.RESOURCE,
            
            # Configuration errors
            'FileNotFoundError': ErrorCategory.CONFIGURATION,
            'ConfigurationError': ErrorCategory.CONFIGURATION,
        }
    
    def _build_severity_mapping(self) -> Dict[str, ErrorSeverity]:
        """Build error type to severity mapping."""
        return {
            'ValidationError': ErrorSeverity.HIGH,
            'MemoryError': ErrorSeverity.CRITICAL,
            'WebSocketDisconnect': ErrorSeverity.LOW,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'DatabaseError': ErrorSeverity.HIGH,
        }
    
    def _build_retryable_categories(self) -> set:
        """Build set of retryable error categories."""
        return {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.WEBSOCKET,
            ErrorCategory.RESOURCE
        }
    
    def _build_fallback_categories(self) -> set:
        """Build set of categories requiring fallback."""
        return {
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.PROCESSING,
            ErrorCategory.TIMEOUT
        }
    
    def _determine_category(self, error_type: str) -> ErrorCategory:
        """Determine error category from exception type."""
        return self._category_map.get(error_type, ErrorCategory.UNKNOWN)
    
    def _determine_severity(self, error_type: str) -> ErrorSeverity:
        """Determine error severity from exception type."""
        # Check direct mapping first
        if error_type in self._severity_map:
            return self._severity_map[error_type]
        
        # Check keywords in error type
        error_type_lower = error_type.lower()
        if 'validation' in error_type_lower:
            return ErrorSeverity.HIGH
        elif 'memory' in error_type_lower:
            return ErrorSeverity.CRITICAL
        elif 'websocket' in error_type_lower:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _is_retryable(self, category: ErrorCategory) -> bool:
        """Determine if error category is retryable."""
        return category in self._retryable_categories
    
    def _requires_fallback(self, category: ErrorCategory) -> bool:
        """Determine if error category requires fallback."""
        return category in self._fallback_categories