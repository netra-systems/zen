"""Enhanced retry strategies with exponential backoff, jitter, and adaptive patterns.

Provides sophisticated retry mechanisms for different failure scenarios with
configurable backoff strategies and failure pattern recognition.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.core.error_recovery import RecoveryContext, OperationType
from app.core.error_codes import ErrorSeverity
from app.schemas.shared_types import RetryConfig
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BackoffStrategy(Enum):
    """Types of backoff strategies for retries."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear" 
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class JitterType(Enum):
    """Types of jitter to add to retry delays."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


# RetryConfig now imported from shared_types.py
# Additional fields for enhanced retry functionality
@dataclass
class EnhancedRetryConfig:
    """Enhanced configuration extending the base RetryConfig."""
    base_config: RetryConfig
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter_type: JitterType = JitterType.FULL


class EnhancedRetryStrategy(ABC):
    """Base class for enhanced retry strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry strategy."""
        self.config = config
        self.attempt_history: Dict[str, List[datetime]] = {}
    
    @abstractmethod
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if operation should be retried."""
        pass
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Calculate delay before next retry."""
        base_delay = self._calculate_base_delay(retry_count)
        jittered_delay = self._apply_jitter(base_delay, retry_count)
        return min(jittered_delay, self.config.max_delay)
    
    def _calculate_base_delay(self, retry_count: int) -> float:
        """Calculate base delay based on backoff strategy."""
        if self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            return self.config.base_delay * (2 ** retry_count)
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            return self.config.base_delay * (retry_count + 1)
        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            return self.config.base_delay * self._fibonacci(retry_count + 1)
        else:  # FIXED
            return self.config.base_delay
    
    def _apply_jitter(self, delay: float, retry_count: int) -> float:
        """Apply jitter to delay."""
        if self.config.jitter_type == JitterType.NONE:
            return delay
        elif self.config.jitter_type == JitterType.FULL:
            return random.uniform(0, delay)
        elif self.config.jitter_type == JitterType.EQUAL:
            return delay * 0.5 + random.uniform(0, delay * 0.5)
        else:  # DECORRELATED
            previous_delay = delay if retry_count == 0 else delay / 2
            return random.uniform(self.config.base_delay, previous_delay * 3)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def record_attempt(self, operation_id: str) -> None:
        """Record retry attempt."""
        if operation_id not in self.attempt_history:
            self.attempt_history[operation_id] = []
        self.attempt_history[operation_id].append(datetime.now())


class DatabaseRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for database operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if database operation should be retried."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        error_msg = str(context.error).lower()
        
        # Always retry on connection issues
        if any(term in error_msg for term in ['connection', 'timeout', 'network']):
            return True
        
        # Don't retry on constraint violations
        if any(term in error_msg for term in ['constraint', 'unique', 'foreign key']):
            return False
        
        # Retry on temporary database issues
        if any(term in error_msg for term in ['deadlock', 'lock timeout', 'busy']):
            return True
        
        return context.severity != ErrorSeverity.CRITICAL


class ApiRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for API operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if API operation should be retried."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        # Check status code if available
        status_code = context.metadata.get('status_code')
        if status_code:
            # Retry on server errors and rate limits
            if status_code in [429, 500, 502, 503, 504]:
                return True
            # Don't retry on client errors
            if 400 <= status_code < 500:
                return False
        
        # Retry on timeout and connection errors
        error_msg = str(context.error).lower()
        return any(term in error_msg for term in ['timeout', 'connection', 'network'])


class MemoryAwareRetryStrategy(EnhancedRetryStrategy):
    """Retry strategy that considers memory pressure."""
    
    def __init__(self, config: RetryConfig, memory_threshold: float = 0.8):
        """Initialize with memory threshold."""
        super().__init__(config)
        self.memory_threshold = memory_threshold
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Check if retry is safe considering memory usage."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        # Don't retry if memory usage is high
        if self._get_memory_usage() > self.memory_threshold:
            logger.warning(f"Skipping retry due to high memory usage")
            return False
        
        # Standard retry logic
        error_msg = str(context.error).lower()
        if 'memory' in error_msg:
            return False
        
        return context.severity != ErrorSeverity.CRITICAL
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100.0
        except ImportError:
            # Fallback if psutil not available
            return 0.5


class AdaptiveRetryStrategy(EnhancedRetryStrategy):
    """Adaptive retry strategy that learns from failure patterns."""
    
    def __init__(self, config: RetryConfig):
        """Initialize adaptive strategy."""
        super().__init__(config)
        self.failure_patterns: Dict[str, int] = {}
        self.success_patterns: Dict[str, int] = {}
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Adaptive retry decision based on historical patterns."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        error_pattern = self._extract_error_pattern(context.error)
        
        # Learn from patterns
        failure_rate = self._get_pattern_failure_rate(error_pattern)
        
        # Adjust retry likelihood based on historical success
        if failure_rate > 0.8:  # High failure rate
            self.config.max_retries = min(self.config.max_retries, 2)
        elif failure_rate < 0.3:  # Low failure rate
            self.config.max_retries = min(self.config.max_retries + 1, 5)
        
        return context.severity != ErrorSeverity.CRITICAL
    
    def record_success(self, error_pattern: str) -> None:
        """Record successful retry for pattern learning."""
        self.success_patterns[error_pattern] = (
            self.success_patterns.get(error_pattern, 0) + 1
        )
    
    def record_failure(self, error_pattern: str) -> None:
        """Record failed retry for pattern learning."""
        self.failure_patterns[error_pattern] = (
            self.failure_patterns.get(error_pattern, 0) + 1
        )
    
    def _extract_error_pattern(self, error: Exception) -> str:
        """Extract pattern from error for classification."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Create pattern signature
        key_terms = ['connection', 'timeout', 'memory', 'permission', 'not found']
        pattern_terms = [term for term in key_terms if term in error_msg]
        
        return f"{error_type}:{':'.join(pattern_terms)}"
    
    def _get_pattern_failure_rate(self, pattern: str) -> float:
        """Calculate failure rate for error pattern."""
        failures = self.failure_patterns.get(pattern, 0)
        successes = self.success_patterns.get(pattern, 0)
        total = failures + successes
        
        return failures / total if total > 0 else 0.5


class RetryStrategyFactory:
    """Factory for creating retry strategies."""
    
    @staticmethod
    def create_strategy(
        operation_type: OperationType,
        config: Optional[RetryConfig] = None
    ) -> EnhancedRetryStrategy:
        """Create appropriate retry strategy for operation type."""
        if config is None:
            config = RetryConfig()
        
        if operation_type in [OperationType.DATABASE_READ, OperationType.DATABASE_WRITE]:
            return DatabaseRetryStrategy(config)
        elif operation_type == OperationType.EXTERNAL_API:
            return ApiRetryStrategy(config)
        elif operation_type == OperationType.AGENT_EXECUTION:
            return MemoryAwareRetryStrategy(config)
        else:
            return AdaptiveRetryStrategy(config)


# Default retry configurations for different operations
DEFAULT_RETRY_CONFIGS = {
    OperationType.DATABASE_READ: RetryConfig(
        max_retries=3,
        base_delay=0.1,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.EQUAL
    ),
    OperationType.DATABASE_WRITE: RetryConfig(
        max_retries=2,
        base_delay=0.5,
        backoff_strategy=BackoffStrategy.LINEAR,
        jitter_type=JitterType.FULL
    ),
    OperationType.EXTERNAL_API: RetryConfig(
        max_retries=4,
        base_delay=1.0,
        max_delay=60.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.DECORRELATED
    ),
    OperationType.LLM_REQUEST: RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=120.0,
        backoff_strategy=BackoffStrategy.FIBONACCI,
        jitter_type=JitterType.FULL
    ),
    OperationType.WEBSOCKET_SEND: RetryConfig(
        max_retries=2,
        base_delay=0.1,
        backoff_strategy=BackoffStrategy.FIXED,
        jitter_type=JitterType.NONE
    ),
    OperationType.AGENT_EXECUTION: RetryConfig(
        max_retries=2,
        base_delay=1.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.EQUAL
    )
}


# Global retry manager for centralized strategy management
class RetryManager:
    """Centralized retry strategy manager."""
    
    def __init__(self):
        """Initialize retry manager."""
        self.strategies: Dict[str, EnhancedRetryStrategy] = {}
        self.metrics: Dict[str, Dict[str, int]] = {}
    
    def get_strategy(
        self,
        operation_type: OperationType,
        operation_id: Optional[str] = None
    ) -> EnhancedRetryStrategy:
        """Get or create retry strategy for operation."""
        cache_key = f"{operation_type.value}:{operation_id or 'default'}"
        
        if cache_key not in self.strategies:
            config = DEFAULT_RETRY_CONFIGS.get(operation_type, RetryConfig())
            self.strategies[cache_key] = RetryStrategyFactory.create_strategy(
                operation_type, config
            )
        
        return self.strategies[cache_key]
    
    def record_retry_attempt(
        self,
        operation_type: OperationType,
        success: bool
    ) -> None:
        """Record retry attempt for metrics."""
        if operation_type.value not in self.metrics:
            self.metrics[operation_type.value] = {
                'attempts': 0, 'successes': 0, 'failures': 0
            }
        
        self.metrics[operation_type.value]['attempts'] += 1
        if success:
            self.metrics[operation_type.value]['successes'] += 1
        else:
            self.metrics[operation_type.value]['failures'] += 1
    
    def get_retry_metrics(self) -> Dict[str, Any]:
        """Get retry operation metrics."""
        return {
            'total_metrics': self.metrics,
            'active_strategies': len(self.strategies),
            'strategy_types': {
                strategy_id: type(strategy).__name__
                for strategy_id, strategy in self.strategies.items()
            }
        }


# Global retry manager instance
retry_manager = RetryManager()