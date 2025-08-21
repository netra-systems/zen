"""Unified circuit breaker implementation for enterprise resilience.

This module provides enterprise circuit breaker functionality with:
- Import from canonical circuit breaker implementation
- Enterprise-grade configuration extensions
- Integration with unified resilience framework

All functions are ≤8 lines per MANDATORY requirements.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar

# Import canonical circuit breaker implementation
from netra_backend.app.core.circuit_breaker_core import CircuitBreaker
from netra_backend.app.core.circuit_breaker_types import (
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitMetrics,
    CircuitState,
)
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


@dataclass
class EnterpriseCircuitConfig(CircuitConfig):
    """Enhanced circuit breaker configuration for enterprise features."""
    adaptive_threshold: bool = True
    slow_call_threshold: float = 5.0
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        super().__post_init__()
        self._validate_enterprise_settings()
    
    def _validate_enterprise_settings(self) -> None:
        """Validate enterprise-specific settings."""
        if self.slow_call_threshold <= 0:
            raise ValueError("slow_call_threshold must be positive")


class UnifiedCircuitBreaker(CircuitBreaker):
    """Enterprise-grade circuit breaker with unified resilience - delegates to canonical implementation."""
    
    def __init__(self, config: CircuitConfig) -> None:
        """Initialize with enhanced configuration support."""
        # Support both standard and enterprise config
        if isinstance(config, EnterpriseCircuitConfig):
            self._enterprise_config = config
        else:
            self._enterprise_config = None
        super().__init__(config)
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is in closed state."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is in half-open state."""
        return self.state == CircuitState.HALF_OPEN
    
    def has_adaptive_threshold(self) -> bool:
        """Check if adaptive threshold is enabled."""
        return (
            self._enterprise_config and 
            self._enterprise_config.adaptive_threshold
        )
    
    def get_slow_call_threshold(self) -> float:
        """Get slow call threshold for enterprise config."""
        if self._enterprise_config:
            return self._enterprise_config.slow_call_threshold
        return 5.0