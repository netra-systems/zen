"""Unified circuit breaker implementation for enterprise resilience.

This module provides enterprise circuit breaker functionality with:
- Direct integration with unified circuit breaker implementation
- Enterprise-grade configuration extensions
- Integration with unified resilience framework

All functions are  <= 8 lines per MANDATORY requirements.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar

# Import unified circuit breaker directly (avoid circular imports)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker as BaseUnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
)
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
class EnterpriseCircuitConfig(UnifiedCircuitConfig):
    """Enhanced circuit breaker configuration for enterprise features."""
    # Additional enterprise settings (beyond UnifiedCircuitConfig)
    monitoring_enabled: bool = True
    alert_on_open: bool = True
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        super().__post_init__()
        self._validate_enterprise_settings()
    
    def _validate_enterprise_settings(self) -> None:
        """Validate enterprise-specific settings."""
        # Enterprise-specific validations
        pass


class UnifiedCircuitBreaker(BaseUnifiedCircuitBreaker):
    """Enterprise-grade circuit breaker with unified resilience - extends base implementation."""
    
    def __init__(self, config: UnifiedCircuitConfig, **kwargs) -> None:
        """Initialize with enhanced configuration support."""
        # Support both standard and enterprise config
        if isinstance(config, EnterpriseCircuitConfig):
            self._enterprise_config = config
        else:
            self._enterprise_config = None
        super().__init__(config, **kwargs)
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is in closed state."""
        return self.state == UnifiedCircuitBreakerState.CLOSED
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is in half-open state."""
        return self.state == UnifiedCircuitBreakerState.HALF_OPEN
    
    def has_adaptive_threshold(self) -> bool:
        """Check if adaptive threshold is enabled."""
        return self.config.adaptive_threshold
    
    def get_slow_call_threshold(self) -> float:
        """Get slow call threshold for enterprise config."""
        return self.config.slow_call_threshold