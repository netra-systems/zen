"""
Recovery and resilience methods for SyntheticDataService - Backward compatibility module
"""

# Import the modular components for backward compatibility
from netra_backend.app.services.synthetic_data.recovery_mixin import RecoveryMixin
from netra_backend.app.services.api_gateway.circuit_breaker import ApiCircuitBreaker as CircuitBreaker
from netra_backend.app.services.synthetic_data.transaction import Transaction

# Re-export for backward compatibility
__all__ = [
    'RecoveryMixin',
    'CircuitBreaker', 
    'Transaction'
]