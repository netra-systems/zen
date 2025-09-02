"""
Circuit Breaker Service for Service Failure Recovery

This module implements circuit breaker patterns to prevent cascading failures
across microservices and provide graceful degradation under load.

Business Value Justification (BVJ):
- Segment: Platform/Internal (protects all tiers)
- Business Goal: Prevent cascading failures and service outages
- Value Impact: Protects $45K+ MRR by maintaining service availability
- Strategic Impact: Enables resilient architecture for enterprise reliability
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    get_unified_circuit_breaker_manager
)

logger = central_logger.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Failure state - requests fail immediately
    HALF_OPEN = "half_open"  # Testing state - limited requests allowed


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Consecutive failures to open circuit
    recovery_timeout: int = 60  # Seconds before attempting recovery
    success_threshold: int = 3  # Successes in half-open to close circuit
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception_types: List[str] = []  # Exceptions that trigger circuit
    sliding_window_size: int = 10  # Size of sliding window for error rate
    error_rate_threshold: float = 0.5  # Error rate (0-1) to open circuit
    min_requests_threshold: int = 3  # Min requests before considering error rate


class CircuitBreakerMetrics(BaseModel):
    """Circuit breaker metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    circuit_closed_count: int = 0
    timeouts: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0


class CircuitBreakerException(Exception):
    """Circuit breaker specific exceptions."""
    pass


class CircuitOpenException(CircuitBreakerException):
    """Exception raised when circuit is open."""
    pass


class CircuitTimeoutException(CircuitBreakerException):
    """Exception raised when request times out."""
    pass


class CircuitBreaker:
    """DEPRECATED: Lightweight wrapper around UnifiedCircuitBreaker for backward compatibility.
    
    This class provides minimal compatibility layer over UnifiedCircuitBreaker.
    All new code should use UnifiedCircuitBreaker directly.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        logger.warning(f"Using deprecated CircuitBreaker for {name}. Migrate to UnifiedCircuitBreaker.")
        self.name = name
        self.config = config
        
        # Create unified circuit breaker with legacy config mapping
        unified_config = self._convert_to_unified_config(name, config)
        manager = get_unified_circuit_breaker_manager()
        self._unified_breaker = manager.create_circuit_breaker(name, unified_config)
        
        # Legacy compatibility properties
        self.metrics = CircuitBreakerMetrics()
        
    def _convert_to_unified_config(self, name: str, config: CircuitBreakerConfig) -> UnifiedCircuitConfig:
        """Convert legacy config to unified config."""
        return UnifiedCircuitConfig(
            name=name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=float(config.recovery_timeout),
            success_threshold=config.success_threshold,
            timeout_seconds=config.timeout,
            sliding_window_size=config.sliding_window_size,
            error_rate_threshold=config.error_rate_threshold,
            min_requests_threshold=config.min_requests_threshold,
            expected_exception_types=config.expected_exception_types
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current state from unified breaker."""
        unified_state = self._unified_breaker.state.value
        return CircuitState(unified_state)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection - delegates to unified breaker."""
        try:
            result = await self._unified_breaker.call(func, *args, **kwargs)
            # Update legacy metrics for backward compatibility
            self._update_legacy_metrics_on_success()
            return result
        except Exception as e:
            self._update_legacy_metrics_on_failure()
            # Map unified breaker exceptions to legacy exceptions for compatibility
            if "CircuitBreakerOpenError" in str(type(e).__name__):
                raise CircuitOpenException(str(e))
            raise
    
    def _update_legacy_metrics_on_success(self) -> None:
        """Update legacy metrics on successful call for backward compatibility."""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.current_consecutive_successes += 1
        self.metrics.current_consecutive_failures = 0
        self.metrics.last_success_time = datetime.now(timezone.utc)
        
    def _update_legacy_metrics_on_failure(self) -> None:
        """Update legacy metrics on failed call for backward compatibility."""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.current_consecutive_failures += 1
        self.metrics.current_consecutive_successes = 0
        self.metrics.last_failure_time = datetime.now(timezone.utc)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        unified_status = self._unified_breaker.get_status()
        return {
            "name": self.name,
            "state": self.state.value,
            "metrics": self.metrics.dict(),
            "config": self.config.dict(),
            "is_healthy": self.state == CircuitState.CLOSED,
            "unified_status": unified_status  # Include unified status for debugging
        }
    
    async def reset(self) -> None:
        """Manually reset the circuit breaker."""
        await self._unified_breaker.reset()
        self.metrics = CircuitBreakerMetrics()
        logger.info(f"Circuit breaker {self.name} manually reset")
    
    async def force_open(self) -> None:
        """Manually force the circuit breaker open."""
        await self._unified_breaker.force_open()
        logger.warning(f"Circuit breaker {self.name} manually forced open")


class CircuitBreakerManager:
    """DEPRECATED: Legacy circuit breaker manager. Delegates to UnifiedCircuitBreakerManager."""
    
    def __init__(self):
        logger.warning("Using deprecated CircuitBreakerManager. Migrate to UnifiedCircuitBreakerManager.")
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
        self._unified_manager = get_unified_circuit_breaker_manager()
    
    def create_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Create or get existing circuit breaker."""
        if name in self._circuit_breakers:
            return self._circuit_breakers[name]
        
        if config is None:
            config = self._default_config
        
        circuit_breaker = CircuitBreaker(name, config)
        self._circuit_breakers[name] = circuit_breaker
        logger.info(f"Created circuit breaker: {name}")
        
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get existing circuit breaker."""
        return self._circuit_breakers.get(name)
    
    async def call_with_circuit_breaker(
        self,
        name: str,
        func: Callable,
        *args,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection."""
        circuit_breaker = self.create_circuit_breaker(name, config)
        return await circuit_breaker.call(func, *args, **kwargs)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: cb.get_status()
            for name, cb in self._circuit_breakers.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all circuit breakers."""
        total_breakers = len(self._circuit_breakers)
        healthy_breakers = sum(
            1 for cb in self._circuit_breakers.values()
            if cb.state == CircuitState.CLOSED
        )
        
        return {
            "total_circuit_breakers": total_breakers,
            "healthy_circuit_breakers": healthy_breakers,
            "unhealthy_circuit_breakers": total_breakers - healthy_breakers,
            "overall_health": "healthy" if healthy_breakers == total_breakers else "degraded",
            "circuit_breaker_names": list(self._circuit_breakers.keys())
        }
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        reset_tasks = [cb.reset() for cb in self._circuit_breakers.values()]
        await asyncio.gather(*reset_tasks, return_exceptions=True)
        logger.info(f"Reset {len(self._circuit_breakers)} circuit breakers")


# Global circuit breaker manager
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager."""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


# DEPRECATED: Decorator for circuit breaker protection - use unified_circuit_breaker instead
def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None
):
    """DEPRECATED: Decorator to add circuit breaker protection. Use unified_circuit_breaker instead."""
    from netra_backend.app.core.resilience.unified_circuit_breaker import unified_circuit_breaker, UnifiedCircuitConfig
    
    logger.warning("Using deprecated circuit_breaker decorator. Migrate to unified_circuit_breaker.")
    
    # Convert legacy config to unified config if provided
    unified_config = None
    if config:
        unified_config = UnifiedCircuitConfig(
            name=name or "legacy_decorator",
            failure_threshold=config.failure_threshold,
            recovery_timeout=float(config.recovery_timeout),
            success_threshold=config.success_threshold,
            timeout_seconds=config.timeout,
            sliding_window_size=config.sliding_window_size,
            error_rate_threshold=config.error_rate_threshold,
            min_requests_threshold=config.min_requests_threshold,
            expected_exception_types=config.expected_exception_types
        )
    
    # Delegate to unified decorator
    return unified_circuit_breaker(name, unified_config)


# DEPRECATED: Context manager for circuit breaker protection - use unified_circuit_breaker_context instead
@asynccontextmanager
async def circuit_breaker_context(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """DEPRECATED: Context manager for circuit breaker protection. Use unified_circuit_breaker_context instead."""
    from netra_backend.app.core.resilience.unified_circuit_breaker import unified_circuit_breaker_context, UnifiedCircuitConfig
    
    logger.warning("Using deprecated circuit_breaker_context. Migrate to unified_circuit_breaker_context.")
    
    # Convert legacy config to unified config if provided
    unified_config = None
    if config:
        unified_config = UnifiedCircuitConfig(
            name=name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=float(config.recovery_timeout),
            success_threshold=config.success_threshold,
            timeout_seconds=config.timeout,
            sliding_window_size=config.sliding_window_size,
            error_rate_threshold=config.error_rate_threshold,
            min_requests_threshold=config.min_requests_threshold,
            expected_exception_types=config.expected_exception_types
        )
    
    # Delegate to unified context manager
    async with unified_circuit_breaker_context(name, unified_config) as unified_breaker:
        # Wrap unified breaker in legacy interface for compatibility
        legacy_wrapper = CircuitBreaker(name, config or CircuitBreakerConfig())
        legacy_wrapper._unified_breaker = unified_breaker
        yield legacy_wrapper


# DEPRECATED: Pre-configured circuit breakers for common services - use UnifiedServiceCircuitBreakers instead
class ServiceCircuitBreakers:
    """DEPRECATED: Pre-configured circuit breakers. Use UnifiedServiceCircuitBreakers instead."""
    
    @staticmethod
    def get_database_circuit_breaker() -> CircuitBreaker:
        """DEPRECATED: Get circuit breaker for database operations. Use UnifiedServiceCircuitBreakers.get_database_circuit_breaker() instead."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers
        
        logger.warning("Using deprecated ServiceCircuitBreakers.get_database_circuit_breaker(). Migrate to UnifiedServiceCircuitBreakers.")
        
        # Get unified circuit breaker and wrap it for legacy compatibility
        unified_breaker = UnifiedServiceCircuitBreakers.get_database_circuit_breaker()
        
        # Create legacy wrapper 
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=10.0,
            expected_exception_types=["ConnectionError", "TimeoutError", "DatabaseError"]
        )
        legacy_wrapper = CircuitBreaker("database", config)
        legacy_wrapper._unified_breaker = unified_breaker
        return legacy_wrapper
    
    @staticmethod
    def get_auth_service_circuit_breaker() -> CircuitBreaker:
        """DEPRECATED: Use UnifiedServiceCircuitBreakers.get_auth_service_circuit_breaker() instead."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers
        logger.warning("Using deprecated ServiceCircuitBreakers.get_auth_service_circuit_breaker(). Migrate to UnifiedServiceCircuitBreakers.")
        
        unified_breaker = UnifiedServiceCircuitBreakers.get_auth_service_circuit_breaker()
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60, success_threshold=3, timeout=15.0)
        legacy_wrapper = CircuitBreaker("auth_service", config)
        legacy_wrapper._unified_breaker = unified_breaker
        return legacy_wrapper
    
    @staticmethod
    def get_llm_service_circuit_breaker() -> CircuitBreaker:
        """DEPRECATED: Use UnifiedServiceCircuitBreakers.get_llm_service_circuit_breaker() instead."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers
        logger.warning("Using deprecated ServiceCircuitBreakers.get_llm_service_circuit_breaker(). Migrate to UnifiedServiceCircuitBreakers.")
        
        unified_breaker = UnifiedServiceCircuitBreakers.get_llm_service_circuit_breaker()
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120, success_threshold=2, timeout=60.0)
        legacy_wrapper = CircuitBreaker("llm_service", config)
        legacy_wrapper._unified_breaker = unified_breaker
        return legacy_wrapper
    
    @staticmethod
    def get_clickhouse_circuit_breaker() -> CircuitBreaker:
        """DEPRECATED: Use UnifiedServiceCircuitBreakers.get_clickhouse_circuit_breaker() instead."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers
        logger.warning("Using deprecated ServiceCircuitBreakers.get_clickhouse_circuit_breaker(). Migrate to UnifiedServiceCircuitBreakers.")
        
        unified_breaker = UnifiedServiceCircuitBreakers.get_clickhouse_circuit_breaker()
        config = CircuitBreakerConfig(failure_threshold=4, recovery_timeout=45, success_threshold=3, timeout=20.0)
        legacy_wrapper = CircuitBreaker("clickhouse", config)
        legacy_wrapper._unified_breaker = unified_breaker
        return legacy_wrapper
    
    @staticmethod
    def get_redis_circuit_breaker() -> CircuitBreaker:
        """DEPRECATED: Use UnifiedServiceCircuitBreakers.get_redis_circuit_breaker() instead."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers
        logger.warning("Using deprecated ServiceCircuitBreakers.get_redis_circuit_breaker(). Migrate to UnifiedServiceCircuitBreakers.")
        
        unified_breaker = UnifiedServiceCircuitBreakers.get_redis_circuit_breaker()
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=20, success_threshold=2, timeout=5.0)
        legacy_wrapper = CircuitBreaker("redis", config)
        legacy_wrapper._unified_breaker = unified_breaker
        return legacy_wrapper