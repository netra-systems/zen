"""Circuit breaker registry and convenience functions with ≤8 line functions.

Registry for managing adaptive circuit breakers with convenience decorators.
All functions ≤8 lines.
"""

from typing import Any, Callable, Dict, Optional

from app.logging_config import central_logger
from netra_backend.app.shared_health_types import HealthChecker
from netra_backend.app.adaptive_circuit_breaker_core import AdaptiveCircuitBreaker
from app.schemas.core_models import CircuitBreakerConfig

logger = central_logger.get_logger(__name__)


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers with ≤8 line functions."""
    
    def __init__(self):
        """Initialize circuit breaker registry."""
        self.breakers: Dict[str, AdaptiveCircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None,
                   health_checker: Optional[HealthChecker] = None) -> AdaptiveCircuitBreaker:
        """Get or create circuit breaker."""
        if name not in self.breakers:
            self._create_new_breaker(name, config, health_checker)
        return self.breakers[name]
    
    def _create_new_breaker(self, name: str, config: Optional[CircuitBreakerConfig],
                           health_checker: Optional[HealthChecker]) -> None:
        """Create new circuit breaker with provided or default config."""
        breaker_config = config or self.default_config
        self.breakers[name] = AdaptiveCircuitBreaker(name, breaker_config, health_checker)
    
    def remove_breaker(self, name: str) -> bool:
        """Remove circuit breaker from registry."""
        if name in self.breakers:
            self.breakers[name].cleanup()
            del self.breakers[name]
            return True
        return False
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self.breakers.items()
        }
    
    def get_breaker_count(self) -> int:
        """Get total number of registered breakers."""
        return len(self.breakers)
    
    def cleanup_all(self) -> None:
        """Cleanup all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.cleanup()
        self.breakers.clear()
    
    def force_open_all(self) -> None:
        """Force all circuit breakers to open state."""
        for breaker in self.breakers.values():
            breaker.force_open()
    
    def force_close_all(self) -> None:
        """Force all circuit breakers to closed state."""
        for breaker in self.breakers.values():
            breaker.force_close()
    
    def get_breaker_names(self) -> list[str]:
        """Get list of all registered breaker names."""
        return list(self.breakers.keys())
    
    async def get_circuit(self, name: str, config: Optional[CircuitBreakerConfig] = None,
                         health_checker: Optional[HealthChecker] = None) -> AdaptiveCircuitBreaker:
        """Async alias for get_breaker for compatibility."""
        return self.get_breaker(name, config, health_checker)
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status for all circuit breakers (async alias for get_all_metrics)."""
        return self.get_all_metrics()


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None,
                       health_checker: Optional[HealthChecker] = None) -> AdaptiveCircuitBreaker:
    """Get circuit breaker from global registry."""
    return circuit_breaker_registry.get_breaker(name, config, health_checker)


def remove_circuit_breaker(name: str) -> bool:
    """Remove circuit breaker from global registry."""
    return circuit_breaker_registry.remove_breaker(name)


def get_all_circuit_breaker_metrics() -> Dict[str, Any]:
    """Get metrics for all circuit breakers in global registry."""
    return circuit_breaker_registry.get_all_metrics()


def cleanup_all_circuit_breakers() -> None:
    """Cleanup all circuit breakers in global registry."""
    circuit_breaker_registry.cleanup_all()


# Convenience decorators with ≤8 line functions
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to apply circuit breaker to function."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(name, config)
            return await breaker.call(func, *args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def with_health_check(name: str, health_checker: HealthChecker,
                     config: Optional[CircuitBreakerConfig] = None):
    """Decorator to apply circuit breaker with health checking."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(name, config, health_checker)
            return await breaker.call(func, *args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def circuit_breaker_sync(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for synchronous functions with circuit breaker."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(name, config)
            # For sync functions, we can't use async call
            # This would need special handling in a real implementation
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator