"""
Database-specific retry strategy implementation.
Handles retry logic for database operations with connection and constraint awareness.
"""

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.core.retry_strategy_base import EnhancedRetryStrategy


class DatabaseRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for database operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if database operation should be retried."""
        if not self._within_retry_limit(context):
            return False
        
        error_msg = str(context.error).lower()
        return self._evaluate_database_retry_conditions(error_msg, context)
    
    def _within_retry_limit(self, context: RecoveryContext) -> bool:
        """Check if within retry attempt limit."""
        return context.retry_count < self.config.max_retries
    
    def _evaluate_database_retry_conditions(self, error_msg: str, context: RecoveryContext) -> bool:
        """Evaluate specific database retry conditions."""
        if self._is_critical_error(context):
            return False
        if self._is_retryable_database_error(error_msg):
            return True
        if self._is_non_retryable_constraint_error(error_msg):
            return False
        return True
    
    def _is_critical_error(self, context: RecoveryContext) -> bool:
        """Check if error is critical severity."""
        return context.severity == ErrorSeverity.CRITICAL
    
    def _is_retryable_database_error(self, error_msg: str) -> bool:
        """Check if error indicates retryable database issues."""
        connection_issues = self._is_connection_issue(error_msg)
        temporary_issues = self._is_temporary_database_issue(error_msg)
        return connection_issues or temporary_issues
    
    def _is_non_retryable_constraint_error(self, error_msg: str) -> bool:
        """Check if error indicates non-retryable constraint violations."""
        return self._is_constraint_violation(error_msg)
    
    def _is_connection_issue(self, error_msg: str) -> bool:
        """Check if error indicates connection issues."""
        connection_terms = ['connection', 'timeout', 'network']
        return any(term in error_msg for term in connection_terms)
    
    def _is_constraint_violation(self, error_msg: str) -> bool:
        """Check if error indicates constraint violations."""
        constraint_terms = ['constraint', 'unique', 'foreign key']
        return any(term in error_msg for term in constraint_terms)
    
    def _is_temporary_database_issue(self, error_msg: str) -> bool:
        """Check if error indicates temporary database issues."""
        temporary_terms = ['deadlock', 'lock timeout', 'busy']
        return any(term in error_msg for term in temporary_terms)