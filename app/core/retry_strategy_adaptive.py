"""
Adaptive retry strategy implementation.
Learns from failure patterns to adjust retry behavior dynamically.
"""

from typing import Dict

from app.core.error_recovery import RecoveryContext
from app.core.error_codes import ErrorSeverity
from app.core.retry_strategy_base import EnhancedRetryStrategy


class AdaptiveRetryStrategy(EnhancedRetryStrategy):
    """Adaptive retry strategy that learns from failure patterns."""
    
    def __init__(self, config):
        """Initialize adaptive strategy."""
        super().__init__(config)
        self.failure_patterns: Dict[str, int] = {}
        self.success_patterns: Dict[str, int] = {}
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Adaptive retry decision based on historical patterns."""
        if not self._within_retry_limit(context):
            return False
        
        error_pattern = self._extract_error_pattern(context.error)
        failure_rate = self._get_pattern_failure_rate(error_pattern)
        self._adjust_retry_limits_based_on_failure_rate(failure_rate)
        
        return not self._is_critical_error(context)
    
    def record_success(self, error_pattern: str) -> None:
        """Record successful retry for pattern learning."""
        self.success_patterns[error_pattern] = self._increment_pattern_count(
            self.success_patterns, error_pattern
        )
    
    def record_failure(self, error_pattern: str) -> None:
        """Record failed retry for pattern learning."""
        self.failure_patterns[error_pattern] = self._increment_pattern_count(
            self.failure_patterns, error_pattern
        )
    
    def _within_retry_limit(self, context: RecoveryContext) -> bool:
        """Check if within retry attempt limit."""
        return context.retry_count < self.config.max_retries
    
    def _is_critical_error(self, context: RecoveryContext) -> bool:
        """Check if error is critical severity."""
        return context.severity == ErrorSeverity.CRITICAL
    
    def _extract_error_pattern(self, error: Exception) -> str:
        """Extract pattern from error for classification."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        pattern_terms = self._get_pattern_terms_from_message(error_msg)
        return f"{error_type}:{':'.join(pattern_terms)}"
    
    def _get_pattern_terms_from_message(self, error_msg: str) -> list:
        """Extract pattern terms from error message."""
        key_terms = ['connection', 'timeout', 'memory', 'permission', 'not found']
        return [term for term in key_terms if term in error_msg]
    
    def _get_pattern_failure_rate(self, pattern: str) -> float:
        """Calculate failure rate for error pattern."""
        failures = self.failure_patterns.get(pattern, 0)
        successes = self.success_patterns.get(pattern, 0)
        total = failures + successes
        
        return self._calculate_failure_rate(failures, total)
    
    def _calculate_failure_rate(self, failures: int, total: int) -> float:
        """Calculate failure rate from counts."""
        return failures / total if total > 0 else 0.5
    
    def _adjust_retry_limits_based_on_failure_rate(self, failure_rate: float) -> None:
        """Adjust retry limits based on historical failure rate."""
        if self._is_high_failure_rate(failure_rate):
            self._reduce_retry_limit()
        elif self._is_low_failure_rate(failure_rate):
            self._increase_retry_limit()
    
    def _is_high_failure_rate(self, failure_rate: float) -> bool:
        """Check if failure rate is high."""
        return failure_rate > 0.8
    
    def _is_low_failure_rate(self, failure_rate: float) -> bool:
        """Check if failure rate is low."""
        return failure_rate < 0.3
    
    def _reduce_retry_limit(self) -> None:
        """Reduce maximum retry attempts."""
        self.config.max_retries = min(self.config.max_retries, 2)
    
    def _increase_retry_limit(self) -> None:
        """Increase maximum retry attempts."""
        self.config.max_retries = min(self.config.max_retries + 1, 5)
    
    def _increment_pattern_count(self, pattern_dict: Dict[str, int], pattern: str) -> int:
        """Increment count for pattern in dictionary."""
        return pattern_dict.get(pattern, 0) + 1