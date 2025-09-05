"""
Unified circuit breaker implementation.
Enhanced implementation with proper status and metrics tracking.
"""

import time
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class UnifiedCircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class UnifiedCircuitConfig(BaseModel):
    """Configuration for unified circuit breaker."""
    name: str = "default"
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: Optional[type] = None


class UnifiedCircuitBreaker:
    """Enhanced unified circuit breaker implementation with metrics and status tracking."""
    
    def __init__(self, config: UnifiedCircuitConfig):
        self.config = config
        self.state = UnifiedCircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_calls = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.opened_at = None
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        self.total_calls += 1
        
        if self.state == UnifiedCircuitBreakerState.OPEN:
            # Check if we should try half-open
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.config.recovery_timeout:
                self.state = UnifiedCircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs) if callable(func) else func
            
            # Success - reset failure count and close circuit if half-open
            self.success_count += 1
            self.failure_count = 0
            self.last_success_time = time.time()
            
            if self.state == UnifiedCircuitBreakerState.HALF_OPEN:
                self.state = UnifiedCircuitBreakerState.CLOSED
                self.opened_at = None
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Check if we should open the circuit
            if self.failure_count >= self.config.failure_threshold:
                if self.state == UnifiedCircuitBreakerState.CLOSED:
                    self.opened_at = time.time()
                self.state = UnifiedCircuitBreakerState.OPEN
            
            raise
            
    def get_state(self) -> UnifiedCircuitBreakerState:
        """Get current state."""
        return self.state
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed circuit breaker status and metrics."""
        now = time.time()
        
        return {
            "state": self.state.value,
            "status": self.state.value,
            "name": self.config.name,
            "is_healthy": self.state == UnifiedCircuitBreakerState.CLOSED,
            "can_execute": self.state != UnifiedCircuitBreakerState.OPEN,
            "metrics": {
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "total_calls": self.total_calls,
                "failure_threshold": self.config.failure_threshold,
                "success_rate": self.success_count / max(1, self.total_calls),
                "error_rate": self.failure_count / max(1, self.total_calls),
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
                "opened_at": self.opened_at,
                "time_since_opened": (now - self.opened_at) if self.opened_at else None,
                "recovery_timeout": self.config.recovery_timeout
            },
            "domain": "unified"
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = UnifiedCircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_calls = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.opened_at = None
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution."""
        if self.state == UnifiedCircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.config.recovery_timeout:
                return True
            return False
        return True

    def record_success(self) -> None:
        """Record a successful operation."""
        self.success_count += 1
        self.failure_count = 0
        self.last_success_time = time.time()
        
        if self.state == UnifiedCircuitBreakerState.HALF_OPEN:
            self.state = UnifiedCircuitBreakerState.CLOSED
            self.opened_at = None

    def record_failure(self, error_type: str = "Exception") -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        # Check if we should open the circuit
        if self.failure_count >= self.config.failure_threshold:
            if self.state == UnifiedCircuitBreakerState.CLOSED:
                self.opened_at = time.time()
            self.state = UnifiedCircuitBreakerState.OPEN


class UnifiedCircuitBreakerManager:
    """Manager for unified circuit breakers."""
    
    def __init__(self):
        self.breakers: Dict[str, UnifiedCircuitBreaker] = {}
    
    def get_breaker(self, name: str) -> UnifiedCircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.breakers:
            config = UnifiedCircuitConfig()
            self.breakers[name] = UnifiedCircuitBreaker(config)
        return self.breakers[name]
    
    def create_breaker(self, name: str, config: UnifiedCircuitConfig) -> UnifiedCircuitBreaker:
        """Create a circuit breaker with specific config."""
        self.breakers[name] = UnifiedCircuitBreaker(config)
        return self.breakers[name]
    
    def create_circuit_breaker(self, name: str, config: UnifiedCircuitConfig) -> UnifiedCircuitBreaker:
        """Alias for create_breaker for backward compatibility."""
        return self.create_breaker(name, config)


class UnifiedServiceCircuitBreakers:
    """Service-level circuit breakers."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.manager = UnifiedCircuitBreakerManager()
    
    def get_breaker(self, operation: str) -> UnifiedCircuitBreaker:
        """Get circuit breaker for specific operation."""
        return self.manager.get_breaker(f"{self.service_name}_{operation}")


# Global manager instance
_unified_manager = UnifiedCircuitBreakerManager()


def get_unified_circuit_breaker_manager() -> UnifiedCircuitBreakerManager:
    """Get global unified circuit breaker manager."""
    return _unified_manager


def unified_circuit_breaker(name: str, config: Optional[UnifiedCircuitConfig] = None):
    """Decorator for applying circuit breaker protection to functions.
    
    Args:
        name: Name of the circuit breaker
        config: Optional configuration for the circuit breaker
    
    Returns:
        Decorator function that wraps the target function with circuit breaker protection
    """
    import functools
    import asyncio
    from typing import Callable
    
    def decorator(func: Callable):
        # Create or get the circuit breaker for this function
        if config:
            breaker = _unified_manager.create_breaker(name, config)
        else:
            breaker = _unified_manager.get_breaker(name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Wrapper for async functions."""
            # Check if circuit is open before attempting
            if breaker.state == UnifiedCircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if breaker.last_failure_time and (time.time() - breaker.last_failure_time) > breaker.config.recovery_timeout:
                    breaker.state = UnifiedCircuitBreakerState.HALF_OPEN
                else:
                    from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(f"Circuit breaker {name} is open")
            
            breaker.total_calls += 1
            
            try:
                # Execute the wrapped function
                result = await func(*args, **kwargs)
                
                # Success - update metrics
                breaker.success_count += 1
                breaker.failure_count = 0
                breaker.last_success_time = time.time()
                
                # Close circuit if it was half-open
                if breaker.state == UnifiedCircuitBreakerState.HALF_OPEN:
                    breaker.state = UnifiedCircuitBreakerState.CLOSED
                    breaker.opened_at = None
                
                return result
                
            except Exception as e:
                # Failure - update metrics
                breaker.failure_count += 1
                breaker.last_failure_time = time.time()
                
                # Check if we should open the circuit
                if breaker.failure_count >= breaker.config.failure_threshold:
                    if breaker.state == UnifiedCircuitBreakerState.CLOSED:
                        breaker.opened_at = time.time()
                    breaker.state = UnifiedCircuitBreakerState.OPEN
                
                # Re-raise the original exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Wrapper for sync functions."""
            # Check if circuit is open before attempting
            if breaker.state == UnifiedCircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if breaker.last_failure_time and (time.time() - breaker.last_failure_time) > breaker.config.recovery_timeout:
                    breaker.state = UnifiedCircuitBreakerState.HALF_OPEN
                else:
                    from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(f"Circuit breaker {name} is open")
            
            breaker.total_calls += 1
            
            try:
                # Execute the wrapped function
                result = func(*args, **kwargs)
                
                # Success - update metrics
                breaker.success_count += 1
                breaker.failure_count = 0
                breaker.last_success_time = time.time()
                
                # Close circuit if it was half-open
                if breaker.state == UnifiedCircuitBreakerState.HALF_OPEN:
                    breaker.state = UnifiedCircuitBreakerState.CLOSED
                    breaker.opened_at = None
                
                return result
                
            except Exception as e:
                # Failure - update metrics
                breaker.failure_count += 1
                breaker.last_failure_time = time.time()
                
                # Check if we should open the circuit
                if breaker.failure_count >= breaker.config.failure_threshold:
                    if breaker.state == UnifiedCircuitBreakerState.CLOSED:
                        breaker.opened_at = time.time()
                    breaker.state = UnifiedCircuitBreakerState.OPEN
                
                # Re-raise the original exception
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def unified_circuit_breaker_context(name: str):
    """Context manager for unified circuit breaker."""
    class UnifiedCircuitBreakerContext:
        def __init__(self, breaker_name: str):
            self.breaker = unified_circuit_breaker(breaker_name)
        
        def __enter__(self):
            return self.breaker
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.breaker.failure_count += 1
    
    return UnifiedCircuitBreakerContext(name)