"""Reliability package for Netra backend.

This package contains the unified reliability manager and related components.
"""

from .unified_reliability_manager import (
    get_reliability_manager,
    UnifiedReliabilityManager
)

# Re-export items from core modules for backward compatibility
try:
    from netra_backend.app.core.circuit_breaker import (
        CircuitConfig as CircuitBreakerConfig,
        UnifiedCircuitBreaker as CircuitBreaker,  # Add circuit breaker export
    )
except ImportError:
    from netra_backend.app.core.circuit_breaker_types import CircuitConfig as CircuitBreakerConfig
    CircuitBreaker = None

try:
    from netra_backend.app.core.reliability_retry import RetryConfig
except ImportError:
    # Create basic RetryConfig for compatibility
    from dataclasses import dataclass
    
    @dataclass
    class RetryConfig:
        max_retries: int = 3
        base_delay: float = 1.0
        max_delay: float = 30.0

# Legacy wrapper support - delegate to unified manager
def get_reliability_wrapper(
    agent_name: str,
    circuit_breaker_config: 'CircuitBreakerConfig' = None,
    retry_config: 'RetryConfig' = None
) -> 'UnifiedReliabilityManager':
    """Legacy wrapper function - delegates to unified reliability manager."""
    return get_reliability_manager(
        service_name=agent_name,
        retry_config=retry_config
    )

# Set AgentReliabilityWrapper as an alias for backward compatibility
AgentReliabilityWrapper = UnifiedReliabilityManager

__all__ = [
    'get_reliability_manager',
    'UnifiedReliabilityManager',
    'AgentReliabilityWrapper',
    'get_reliability_wrapper', 
    'CircuitBreaker',  # Add CircuitBreaker to exports
    'CircuitBreakerConfig',
    'RetryConfig'
]