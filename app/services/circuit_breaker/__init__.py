"""Circuit Breaker Service Package

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable test execution and prevent circuit breaker import errors
- Value Impact: Ensures test suite can import circuit breaker dependencies
- Strategic Impact: Maintains compatibility for circuit breaker functionality
"""

from .circuit_breaker_manager import CircuitBreakerManager
from .service_health_monitor import ServiceHealthMonitor
from .failure_detector import FailureDetector

__all__ = ["CircuitBreakerManager", "ServiceHealthMonitor", "FailureDetector"]