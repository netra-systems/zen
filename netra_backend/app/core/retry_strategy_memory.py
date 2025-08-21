"""
Memory-aware retry strategy implementation.
Handles retry logic with consideration for system memory pressure.
"""

from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.retry_strategy_base import EnhancedRetryStrategy
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MemoryAwareRetryStrategy(EnhancedRetryStrategy):
    """Retry strategy that considers memory pressure."""
    
    def __init__(self, config, memory_threshold: float = 0.8):
        """Initialize with memory threshold."""
        super().__init__(config)
        self.memory_threshold = memory_threshold
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Check if retry is safe considering memory usage."""
        if not self._within_retry_limit(context):
            return False
        if self._memory_prevents_retry():
            return False
        if self._is_memory_related_error(context.error):
            return False
        return not self._is_critical_error(context)
    
    def _within_retry_limit(self, context: RecoveryContext) -> bool:
        """Check if within retry attempt limit."""
        return context.retry_count < self.config.max_retries
    
    def _memory_prevents_retry(self) -> bool:
        """Check if memory usage prevents retry."""
        if self._get_memory_usage() > self.memory_threshold:
            self._log_high_memory_warning()
            return True
        return False
    
    def _is_memory_related_error(self, error: Exception) -> bool:
        """Check if error is memory-related."""
        error_msg = str(error).lower()
        return 'memory' in error_msg
    
    def _is_critical_error(self, context: RecoveryContext) -> bool:
        """Check if error is critical severity."""
        return context.severity == ErrorSeverity.CRITICAL
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            return self._get_psutil_memory_usage()
        except ImportError:
            return self._get_fallback_memory_usage()
    
    def _get_psutil_memory_usage(self) -> float:
        """Get memory usage using psutil."""
        import psutil
        return psutil.virtual_memory().percent / 100.0
    
    def _get_fallback_memory_usage(self) -> float:
        """Get fallback memory usage estimate."""
        return 0.5
    
    def _log_high_memory_warning(self) -> None:
        """Log warning about high memory usage."""
        logger.warning(f"Skipping retry due to high memory usage")