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
from datetime import datetime, timedelta
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
    """DEPRECATED: Legacy circuit breaker implementation. Use UnifiedCircuitBreaker instead.
    
    This class is maintained for backward compatibility only. All new code should
    use netra_backend.app.core.resilience.unified_circuit_breaker.UnifiedCircuitBreaker
    or the appropriate domain-specific wrapper from domain_circuit_breakers.py.
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
        self._state_lock = asyncio.Lock()
        self._last_state_change = datetime.utcnow()
        self._sliding_window: List[Dict[str, Any]] = []
        self._recovery_task: Optional[asyncio.Task] = None
        
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
        self.metrics.last_success_time = datetime.utcnow()
        
    def _update_legacy_metrics_on_failure(self) -> None:
        """Update legacy metrics on failed call for backward compatibility."""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.current_consecutive_failures += 1
        self.metrics.current_consecutive_successes = 0
        self.metrics.last_failure_time = datetime.utcnow()
    
    async def _execute_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the actual function call with timeout and error handling."""
        start_time = time.time()
        self.metrics.total_requests += 1
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                # Run sync function in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, func, *args, **kwargs
                )
            
            # Record success
            await self._record_success(time.time() - start_time)
            return result
            
        except asyncio.TimeoutError:
            self.metrics.timeouts += 1
            await self._record_failure("timeout")
            raise CircuitTimeoutException(f"Request timed out after {self.config.timeout}s")
            
        except Exception as e:
            await self._record_failure(type(e).__name__)
            
            # Check if this exception type should trigger the circuit
            if (not self.config.expected_exception_types or 
                type(e).__name__ in self.config.expected_exception_types):
                
                async with self._state_lock:
                    self.metrics.current_consecutive_failures += 1
                    self.metrics.current_consecutive_successes = 0
                    
                    # Check if we should open the circuit
                    if (self.state == CircuitState.CLOSED and 
                        self.metrics.current_consecutive_failures >= self.config.failure_threshold):
                        await self._open_circuit()
                    
                    elif (self.state == CircuitState.HALF_OPEN and 
                          self.metrics.current_consecutive_failures >= 1):
                        await self._open_circuit()
            
            raise
    
    async def _record_success(self, response_time: float) -> None:
        """Record a successful request."""
        async with self._state_lock:
            self.metrics.successful_requests += 1
            self.metrics.current_consecutive_successes += 1
            self.metrics.current_consecutive_failures = 0
            self.metrics.last_success_time = datetime.utcnow()
            
            # Update average response time
            total_successful = self.metrics.successful_requests
            if total_successful == 1:
                self.metrics.average_response_time = response_time
            else:
                self.metrics.average_response_time = (
                    (self.metrics.average_response_time * (total_successful - 1) + response_time) / 
                    total_successful
                )
            
            # Add to sliding window
            self._sliding_window.append({
                "timestamp": time.time(),
                "success": True,
                "response_time": response_time
            })
            
            # Trim sliding window
            self._trim_sliding_window()
            
            # If in half-open state and enough successes, close circuit
            if (self.state == CircuitState.HALF_OPEN and 
                self.metrics.current_consecutive_successes >= self.config.success_threshold):
                await self._close_circuit()
    
    async def _record_failure(self, error_type: str) -> None:
        """Record a failed request."""
        self.metrics.failed_requests += 1
        self.metrics.last_failure_time = datetime.utcnow()
        
        # Add to sliding window
        self._sliding_window.append({
            "timestamp": time.time(),
            "success": False,
            "error_type": error_type
        })
        
        # Trim sliding window
        self._trim_sliding_window()
        
        # Update error rate
        await self._update_error_rate()
    
    def _trim_sliding_window(self) -> None:
        """Trim sliding window to configured size."""
        if len(self._sliding_window) > self.config.sliding_window_size:
            self._sliding_window = self._sliding_window[-self.config.sliding_window_size:]
    
    async def _update_error_rate(self) -> None:
        """Update current error rate based on sliding window."""
        if not self._sliding_window:
            self.metrics.error_rate = 0.0
            return
        
        failures = sum(1 for entry in self._sliding_window if not entry["success"])
        total = len(self._sliding_window)
        self.metrics.error_rate = failures / total if total > 0 else 0.0
    
    async def _check_error_rate(self) -> None:
        """Check if error rate exceeds threshold and should open circuit."""
        if (self.state == CircuitState.CLOSED and 
            len(self._sliding_window) >= self.config.min_requests_threshold and
            self.metrics.error_rate >= self.config.error_rate_threshold):
            
            logger.warning(
                f"Circuit breaker {self.name} error rate {self.metrics.error_rate:.2%} "
                f"exceeds threshold {self.config.error_rate_threshold:.2%}"
            )
            await self._open_circuit()
    
    async def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.metrics.circuit_opened_count += 1
            self._last_state_change = datetime.utcnow()
            logger.error(f"Circuit breaker {self.name} OPENED after {self.metrics.current_consecutive_failures} failures")
            
            # Start recovery timer
            if not self._recovery_task or self._recovery_task.done():
                self._recovery_task = asyncio.create_task(self._schedule_recovery())
    
    async def _close_circuit(self) -> None:
        """Close the circuit breaker."""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.metrics.circuit_closed_count += 1
            self.metrics.current_consecutive_failures = 0
            self._last_state_change = datetime.utcnow()
            logger.info(f"Circuit breaker {self.name} CLOSED after {self.metrics.current_consecutive_successes} successes")
    
    async def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_open = datetime.utcnow() - self._last_state_change
        return time_since_open.total_seconds() >= self.config.recovery_timeout
    
    async def _schedule_recovery(self) -> None:
        """Schedule automatic recovery attempt."""
        try:
            await asyncio.sleep(self.config.recovery_timeout)
            
            async with self._state_lock:
                if self.state == CircuitState.OPEN:
                    # Don't automatically move to HALF_OPEN, wait for next request
                    logger.info(f"Circuit breaker {self.name} ready for recovery attempt")
                    
        except asyncio.CancelledError:
            logger.debug(f"Recovery task cancelled for circuit breaker {self.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "metrics": self.metrics.dict(),
            "config": self.config.dict(),
            "last_state_change": self._last_state_change,
            "sliding_window_size": len(self._sliding_window),
            "is_healthy": self.state == CircuitState.CLOSED
        }
    
    async def reset(self) -> None:
        """Manually reset the circuit breaker."""
        async with self._state_lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitBreakerMetrics()
            self._sliding_window.clear()
            self._last_state_change = datetime.utcnow()
            
            if self._recovery_task and not self._recovery_task.done():
                self._recovery_task.cancel()
            
            logger.info(f"Circuit breaker {self.name} manually reset")
    
    async def force_open(self) -> None:
        """Manually force the circuit breaker open."""
        async with self._state_lock:
            await self._open_circuit()
            logger.warning(f"Circuit breaker {self.name} manually forced open")


class CircuitBreakerManager:
    """Manages multiple circuit breakers across the application."""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
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


# Decorator for circuit breaker protection
def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator to add circuit breaker protection to functions."""
    def decorator(func: Callable) -> Callable:
        circuit_name = name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                manager = get_circuit_breaker_manager()
                return await manager.call_with_circuit_breaker(
                    circuit_name, func, *args, config=config, **kwargs
                )
            return async_wrapper
        else:
            async def sync_wrapper(*args, **kwargs):
                manager = get_circuit_breaker_manager()
                return await manager.call_with_circuit_breaker(
                    circuit_name, func, *args, config=config, **kwargs
                )
            return sync_wrapper
    
    return decorator


# Context manager for circuit breaker protection
@asynccontextmanager
async def circuit_breaker_context(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Context manager for circuit breaker protection."""
    manager = get_circuit_breaker_manager()
    circuit_breaker = manager.create_circuit_breaker(name, config)
    
    try:
        yield circuit_breaker
    except CircuitBreakerException:
        raise
    except Exception as e:
        # Let circuit breaker handle the error
        raise


# Pre-configured circuit breakers for common services
class ServiceCircuitBreakers:
    """Pre-configured circuit breakers for common services."""
    
    @staticmethod
    def get_database_circuit_breaker() -> CircuitBreaker:
        """Get circuit breaker for database operations."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=10.0,
            expected_exception_types=["ConnectionError", "TimeoutError", "DatabaseError"]
        )
        manager = get_circuit_breaker_manager()
        return manager.create_circuit_breaker("database", config)
    
    @staticmethod
    def get_auth_service_circuit_breaker() -> CircuitBreaker:
        """Get circuit breaker for auth service operations."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=15.0,
            expected_exception_types=["HTTPException", "ConnectionError", "TimeoutError"]
        )
        manager = get_circuit_breaker_manager()
        return manager.create_circuit_breaker("auth_service", config)
    
    @staticmethod
    def get_llm_service_circuit_breaker() -> CircuitBreaker:
        """Get circuit breaker for LLM service operations."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=120,  # Longer recovery for expensive LLM calls
            success_threshold=2,
            timeout=60.0,  # Longer timeout for LLM processing
            expected_exception_types=["HTTPException", "TimeoutError", "RateLimitError"]
        )
        manager = get_circuit_breaker_manager()
        return manager.create_circuit_breaker("llm_service", config)
    
    @staticmethod
    def get_clickhouse_circuit_breaker() -> CircuitBreaker:
        """Get circuit breaker for ClickHouse operations."""
        config = CircuitBreakerConfig(
            failure_threshold=4,
            recovery_timeout=45,
            success_threshold=3,
            timeout=20.0,
            expected_exception_types=["ConnectionError", "TimeoutError", "ClickHouseError"]
        )
        manager = get_circuit_breaker_manager()
        return manager.create_circuit_breaker("clickhouse", config)
    
    @staticmethod
    def get_redis_circuit_breaker() -> CircuitBreaker:
        """Get circuit breaker for Redis operations."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=20,  # Quick recovery for cache
            success_threshold=2,
            timeout=5.0,  # Fast timeout for cache operations
            expected_exception_types=["ConnectionError", "TimeoutError", "RedisError"]
        )
        manager = get_circuit_breaker_manager()
        return manager.create_circuit_breaker("redis", config)