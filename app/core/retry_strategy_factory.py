"""
Retry strategy factory and default configurations.
Creates appropriate retry strategies based on operation types.
"""

from typing import Optional

from app.core.error_recovery import OperationType
from app.schemas.shared_types import RetryConfig, BackoffStrategy, JitterType
from app.core.retry_strategy_base import EnhancedRetryStrategy
from app.core.retry_strategy_database import DatabaseRetryStrategy
from app.core.retry_strategy_api import ApiRetryStrategy
from app.core.retry_strategy_memory import MemoryAwareRetryStrategy
from app.core.retry_strategy_adaptive import AdaptiveRetryStrategy


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
        
        strategy_map = RetryStrategyFactory._get_strategy_mapping()
        strategy_class = strategy_map.get(operation_type, AdaptiveRetryStrategy)
        
        return strategy_class(config)
    
    @staticmethod
    def _get_strategy_mapping():
        """Get mapping of operation types to strategy classes."""
        return {
            OperationType.DATABASE_READ: DatabaseRetryStrategy,
            OperationType.DATABASE_WRITE: DatabaseRetryStrategy,
            OperationType.EXTERNAL_API: ApiRetryStrategy,
            OperationType.AGENT_EXECUTION: MemoryAwareRetryStrategy,
        }


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