"""Reliability Management System

Circuit breaker and retry patterns for agent execution:
- Circuit breaker pattern implementation
- Exponential backoff retry logic
- Rate limiting and throttling
- Health monitoring integration

Business Value: Prevents cascading failures, improves system resilience.

IMPORTANT: This module maintains backward compatibility by importing
from the new modular structure. All classes are now implemented in
their respective focused modules:
- circuit_breaker.py - Circuit breaker implementation
- retry_manager.py - Retry logic and backoff
- reliability_manager.py - Health monitoring and coordination  
- rate_limiter.py - Rate limiting functionality
"""

# Import all classes from their respective modules for backward compatibility
from netra_backend.app.agents.base.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerMetrics, 
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitBreakerState
)

from netra_backend.app.agents.base.retry_manager import RetryManager

from netra_backend.app.agents.base.reliability_manager import ReliabilityManager

from netra_backend.app.agents.base.rate_limiter import RateLimiter

# Export all classes for backward compatibility
__all__ = [
    'CircuitBreakerConfig',
    'CircuitBreakerMetrics',
    'CircuitBreaker', 
    'CircuitBreakerOpenException',
    'CircuitBreakerState',
    'RetryManager',
    'ReliabilityManager',
    'RateLimiter'
]