"""
API-specific retry strategy implementation.
Handles retry logic for API operations based on HTTP status codes and error types.
"""

from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.core.retry_strategy_base import EnhancedRetryStrategy


class ApiRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for API operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if API operation should be retried."""
        if not self._within_retry_limit(context):
            return False
        
        status_code = context.metadata.get('status_code')
        if status_code:
            return self._should_retry_based_on_status_code(status_code)
        return self._should_retry_based_on_error_message(context.error)
    
    def _within_retry_limit(self, context: RecoveryContext) -> bool:
        """Check if within retry attempt limit."""
        return context.retry_count < self.config.max_retries
    
    def _should_retry_based_on_status_code(self, status_code: int) -> bool:
        """Determine retry based on HTTP status code."""
        if self._is_server_error(status_code):
            return True
        return not self._is_client_error(status_code)
    
    def _should_retry_based_on_error_message(self, error: Exception) -> bool:
        """Determine retry based on error message."""
        error_msg = str(error).lower()
        return self._is_network_related_error(error_msg)
    
    def _is_server_error(self, status_code: int) -> bool:
        """Check if status code indicates server error."""
        server_errors = [429, 500, 502, 503, 504]
        return status_code in server_errors
    
    def _is_client_error(self, status_code: int) -> bool:
        """Check if status code indicates client error."""
        client_error_range = range(400, 500)
        return status_code in client_error_range
    
    def _is_network_related_error(self, error_msg: str) -> bool:
        """Check if error message indicates network issues."""
        network_terms = ['timeout', 'connection', 'network']
        return any(term in error_msg for term in network_terms)