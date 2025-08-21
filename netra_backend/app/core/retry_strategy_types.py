"""
Retry strategy types and base interfaces.
Defines basic types and abstract interfaces used across the retry system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.schemas.shared_types import (
    BackoffStrategy,
    JitterType,
    RetryConfig,
)


@dataclass
class EnhancedRetryConfig:
    """Enhanced configuration extending the base RetryConfig."""
    base_config: RetryConfig
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter_type: JitterType = JitterType.FULL


class RetryStrategyInterface(ABC):
    """Abstract interface for retry strategies."""
    
    @abstractmethod
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if operation should be retried."""
        pass
    
    @abstractmethod
    def get_retry_delay(self, retry_count: int) -> float:
        """Calculate delay before next retry."""
        pass
    
    @abstractmethod
    def record_attempt(self, operation_id: str) -> None:
        """Record retry attempt."""
        pass


class RetryHistoryMixin:
    """Mixin for managing retry attempt history."""
    
    def __init__(self):
        self.attempt_history: Dict[str, List[datetime]] = {}
    
    def record_attempt(self, operation_id: str) -> None:
        """Record retry attempt."""
        self._initialize_operation_history(operation_id)
        self._add_attempt_timestamp(operation_id)
    
    def _initialize_operation_history(self, operation_id: str) -> None:
        """Initialize history for operation if not exists."""
        if operation_id not in self.attempt_history:
            self.attempt_history[operation_id] = []
    
    def _add_attempt_timestamp(self, operation_id: str) -> None:
        """Add current timestamp to operation history."""
        self.attempt_history[operation_id].append(datetime.now())