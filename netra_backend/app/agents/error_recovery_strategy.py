"""Error Recovery Strategy Module.

Handles error recovery strategies and retry logic.
Provides delay calculation and retry decision making.
"""

from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory
from app.core.exceptions_agent import AgentError


class ErrorRecoveryStrategy:
    """Strategy for error recovery based on error type."""
    
    # Strategy constants
    RETRY = "retry"
    ABORT = "abort"
    FALLBACK = "fallback"
    
    @staticmethod
    def get_recovery_delay(error: AgentError, attempt: int) -> float:
        """Calculate recovery delay based on error type and retry count."""
        base_delays = ErrorRecoveryStrategy._get_base_delays()
        base_delay = base_delays.get(error.category, 2.0)
        delay = base_delay * (2 ** attempt)
        max_delay = 30.0
        return min(delay, max_delay)
    
    @staticmethod
    def _get_base_delays() -> dict:
        """Get base delay mapping for different error categories."""
        return {
            ErrorCategory.NETWORK: 2.0,
            ErrorCategory.DATABASE: 1.0,
            ErrorCategory.WEBSOCKET: 0.5,
            ErrorCategory.TIMEOUT: 5.0,
            ErrorCategory.RESOURCE: 3.0,
            ErrorCategory.PROCESSING: 1.0,
            ErrorCategory.UNKNOWN: 2.0
        }
    
    @staticmethod
    def should_retry(error: AgentError, attempt: int = 1) -> bool:
        """Determine if error should be retried based on attempt number."""
        max_attempts = 5
        if attempt >= max_attempts:
            return False
        if not error.recoverable:
            return False
        return ErrorRecoveryStrategy._check_retry_conditions(error)
    
    @staticmethod
    def get_strategy(error: AgentError) -> str:
        """Get recovery strategy for the given error."""
        if error.severity == ErrorSeverity.CRITICAL:
            return ErrorRecoveryStrategy.ABORT
        if error.category == ErrorCategory.VALIDATION:
            return ErrorRecoveryStrategy.ABORT
        if ErrorRecoveryStrategy._is_always_retryable_category(error.category):
            return ErrorRecoveryStrategy.RETRY
        return ErrorRecoveryStrategy.FALLBACK
    
    @staticmethod
    def _check_retry_conditions(error: AgentError) -> bool:
        """Check specific retry conditions for error."""
        if ErrorRecoveryStrategy._is_non_retryable_category(error.category):
            return False
        if ErrorRecoveryStrategy._is_always_retryable_category(error.category):
            return True
        return ErrorRecoveryStrategy._check_conditional_retry(error)
    
    @staticmethod
    def _is_non_retryable_category(category: ErrorCategory) -> bool:
        """Check if error category should never be retried."""
        return category == ErrorCategory.VALIDATION
    
    @staticmethod
    def _is_always_retryable_category(category: ErrorCategory) -> bool:
        """Check if error category should always be retried."""
        retryable_categories = [
            ErrorCategory.NETWORK, 
            ErrorCategory.TIMEOUT, 
            ErrorCategory.WEBSOCKET
        ]
        return category in retryable_categories
    
    @staticmethod
    def _check_conditional_retry(error: AgentError) -> bool:
        """Check conditional retry based on severity and category."""
        if error.category in [ErrorCategory.DATABASE, ErrorCategory.PROCESSING]:
            return error.severity != ErrorSeverity.CRITICAL
        return error.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]