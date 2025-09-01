"""Security module for agent execution protection.

This module provides comprehensive security and resilience controls for agent execution,
including resource protection, timeout enforcement, and circuit breaker patterns.

Components:
- ResourceGuard: Memory, CPU, and concurrency limits
- CircuitBreaker: Failure detection and automatic recovery
- SecurityMetrics: Comprehensive monitoring and alerting

Business Value: Ensures system stability, prevents DoS attacks, and provides
graceful degradation under load or failure conditions.
"""

from .resource_guard import ResourceGuard, ResourceLimits, ResourceUsage, UserResourceTracker
from .circuit_breaker import (
    SystemCircuitBreaker, 
    AgentCircuitBreaker, 
    CircuitBreakerConfig,
    CircuitState,
    FailureType
)

__all__ = [
    'ResourceGuard',
    'ResourceLimits', 
    'ResourceUsage',
    'UserResourceTracker',
    'SystemCircuitBreaker',
    'AgentCircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitState',
    'FailureType'
]