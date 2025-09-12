"""
Circuit Breaker - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
UnifiedCircuitBreaker implementation from the core resilience module.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) 
- Business Goal: Prevent cascade failures and maintain service reliability
- Value Impact: Ensures system stability during high load or service degradation
- Strategic Impact: Critical for maintaining SLA commitments and user experience
"""

# SSOT Import: Use existing UnifiedCircuitBreaker from core resilience module
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker as CircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
    unified_circuit_breaker_context
)

# Export for test compatibility
__all__ = [
    'CircuitBreaker',
    'UnifiedCircuitConfig', 
    'UnifiedCircuitBreakerState',
    'unified_circuit_breaker_context'
]