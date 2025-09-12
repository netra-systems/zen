"""
Circuit Breaker Pattern Implementation for Auth Service Resilience.

Prevents cascading failures when auth service is unavailable by:
- Tracking failure rates and opening circuit when threshold exceeded
- Automatically recovering when service becomes available
- Providing fallback behavior during outages

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Prevent auth service outages from crashing backend
- Value Impact: Maintains service availability even when auth is degraded
- Strategic Impact: Enterprise-grade resilience pattern for production reliability
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded threshold, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening
    success_threshold: int = 2  # Number of successes in half-open before closing
    timeout: float = 15.0  # CRITICAL FIX: Reduced from 60s to prevent WebSocket blocking
    half_open_max_calls: int = 3  # Max concurrent calls in half-open state
    
    # Failure detection
    failure_rate_threshold: float = 0.5  # Open if failure rate exceeds this
    min_calls_for_rate: int = 10  # Minimum calls before calculating failure rate
    
    # Timeouts
    call_timeout: float = 5.0  # Timeout for individual calls
    
    # Recovery - CRITICAL FIX: Reduced from 300s to prevent WebSocket blocking
    reset_timeout: float = 60.0  # Reset statistics after this many seconds of success
    
    @classmethod
    def create_demo_config(cls) -> 'CircuitBreakerConfig':
        """Create relaxed configuration for demo mode.
        
        Demo mode settings:
        - Higher failure threshold (10 instead of 5)
        - Shorter timeout (30s instead of 60s)
        - More lenient failure rate (0.7 instead of 0.5)
        - Faster recovery (30s instead of 60s)
        
        Returns:
            CircuitBreakerConfig with demo mode settings
        """
        return cls(
            failure_threshold=10,  # Relaxed from 5
            success_threshold=2,   # Keep same
            timeout=30.0,         # Reduced from 60s
            half_open_max_calls=5, # Increased from 3
            failure_rate_threshold=0.7,  # Relaxed from 0.5
            min_calls_for_rate=5,  # Reduced from 10
            call_timeout=10.0,     # Increased from 5.0s
            reset_timeout=30.0     # Reduced from 60s
        )


@dataclass
class CircuitBreakerStats:
    """Statistics tracking for circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: list = field(default_factory=list)
    
    def reset(self):
        """Reset statistics."""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    Usage:
        breaker = CircuitBreaker(name="auth_service")
        
        async def call_auth_service():
            return await auth_client.validate_token(token)
        
        try:
            result = await breaker.call(call_auth_service)
        except CircuitBreakerOpen:
            # Use fallback behavior
            result = cached_validation_result
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Name for logging and identification
            config: Circuit breaker configuration
            fallback: Optional fallback function when circuit is open
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._last_state_change = time.time()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized: threshold={self.config.failure_threshold}")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED
    
    async def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            CircuitBreakerOpen: If circuit is open and no fallback available
            Exception: Original exception if circuit is closed
        """
        # Check if we should transition from OPEN to HALF_OPEN
        await self._check_state_transition()
        
        if self._state == CircuitState.OPEN:
            if self.fallback:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, using fallback")
                return await self._execute_fallback(*args, **kwargs)
            raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is OPEN")
        
        if self._state == CircuitState.HALF_OPEN:
            # Limit concurrent calls in half-open state
            async with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    if self.fallback:
                        return await self._execute_fallback(*args, **kwargs)
                    raise CircuitBreakerHalfOpen(f"Circuit breaker '{self.name}' is HALF_OPEN with max calls exceeded")
                self._half_open_calls += 1
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )
            await self._on_success()
            return result
            
        except asyncio.TimeoutError as e:
            await self._on_failure(e)
            raise CircuitBreakerTimeout(f"Call timed out after {self.config.call_timeout}s") from e
            
        except Exception as e:
            await self._on_failure(e)
            raise
            
        finally:
            if self._state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self._half_open_calls -= 1
    
    async def _execute_fallback(self, *args, **kwargs) -> Any:
        """Execute fallback function."""
        if self.fallback:
            try:
                return await self.fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback for '{self.name}' failed: {e}")
                raise
        if self._state == CircuitState.HALF_OPEN:
            raise CircuitBreakerHalfOpen(f"No fallback available for '{self.name}' in HALF_OPEN state")
        raise CircuitBreakerOpen(f"No fallback available for '{self.name}'")
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self._stats.successful_calls += 1
            self._stats.total_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to_closed()
            
            # Reset stats if we've been successful for a while
            if (self._stats.last_failure_time and 
                time.time() - self._stats.last_failure_time > self.config.reset_timeout):
                self._stats.reset()
    
    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        async with self._lock:
            self._stats.failed_calls += 1
            self._stats.total_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()
            
            logger.warning(
                f"Circuit breaker '{self.name}' failure #{self._stats.consecutive_failures}: {error}"
            )
            
            # Check if we should open the circuit
            should_open = False
            
            # Check consecutive failures
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                should_open = True
                
            # Check failure rate
            elif (self._stats.total_calls >= self.config.min_calls_for_rate and
                  self._stats.failure_rate > self.config.failure_rate_threshold):
                should_open = True
            
            if should_open and self._state != CircuitState.OPEN:
                await self._transition_to_open()
            elif self._state == CircuitState.HALF_OPEN:
                # Single failure in half-open returns to open
                await self._transition_to_open()
    
    async def _check_state_transition(self):
        """Check if state should transition."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                time_since_change = time.time() - self._last_state_change
                if time_since_change >= self.config.timeout:
                    await self._transition_to_half_open()
    
    async def _transition_to_open(self):
        """Transition to OPEN state."""
        previous_state = self._state
        self._state = CircuitState.OPEN
        self._last_state_change = time.time()
        self._half_open_calls = 0
        
        self._stats.state_changes.append({
            'from': previous_state.value,
            'to': CircuitState.OPEN.value,
            'time': datetime.now().isoformat(),
            'reason': f"Failures: {self._stats.consecutive_failures}, Rate: {self._stats.failure_rate:.2%}"
        })
        
        logger.error(
            f"Circuit breaker '{self.name}' OPENED: "
            f"consecutive_failures={self._stats.consecutive_failures}, "
            f"failure_rate={self._stats.failure_rate:.2%}"
        )
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state."""
        previous_state = self._state
        self._state = CircuitState.CLOSED
        self._last_state_change = time.time()
        self._half_open_calls = 0
        
        # Reset statistics on successful recovery
        self._stats.reset()
        
        self._stats.state_changes.append({
            'from': previous_state.value,
            'to': CircuitState.CLOSED.value,
            'time': datetime.now().isoformat(),
            'reason': 'Service recovered'
        })
        
        logger.info(f"Circuit breaker '{self.name}' CLOSED: Service recovered")
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        previous_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._last_state_change = time.time()
        self._half_open_calls = 0
        
        # Reset consecutive counters for testing
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes = 0
        
        self._stats.state_changes.append({
            'from': previous_state.value,
            'to': CircuitState.HALF_OPEN.value,
            'time': datetime.now().isoformat(),
            'reason': 'Testing recovery'
        })
        
        logger.info(f"Circuit breaker '{self.name}' HALF-OPEN: Testing service recovery")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            'name': self.name,
            'state': self._state.value,
            'stats': {
                'total_calls': self._stats.total_calls,
                'successful_calls': self._stats.successful_calls,
                'failed_calls': self._stats.failed_calls,
                'failure_rate': f"{self._stats.failure_rate:.2%}",
                'consecutive_failures': self._stats.consecutive_failures,
                'consecutive_successes': self._stats.consecutive_successes,
                'last_failure': datetime.fromtimestamp(self._stats.last_failure_time).isoformat() 
                    if self._stats.last_failure_time else None,
                'last_success': datetime.fromtimestamp(self._stats.last_success_time).isoformat()
                    if self._stats.last_success_time else None,
            },
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'timeout': self.config.timeout,
                'failure_rate_threshold': f"{self.config.failure_rate_threshold:.0%}",
            },
            'state_changes': self._stats.state_changes[-5:]  # Last 5 state changes
        }
    
    async def reset(self):
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._stats.reset()
            self._last_state_change = time.time()
            self._half_open_calls = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerTimeout(Exception):
    """Raised when a call through circuit breaker times out."""
    pass


class CircuitBreakerHalfOpen(Exception):
    """Raised when circuit breaker is in half-open state and max calls exceeded."""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker instance with demo mode support.
    
    Args:
        name: Circuit breaker name
        config: Configuration (used only on first creation)
        fallback: Fallback function (used only on first creation)
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        # If no config provided, try to use demo mode config
        if config is None:
            try:
                from netra_backend.app.core.configuration.demo import get_backend_demo_config
                demo_config = get_backend_demo_config()
                if demo_config.is_demo_mode():
                    config = CircuitBreakerConfig.create_demo_config()
                    logger.info(f"🎭 DEMO MODE: Using relaxed circuit breaker configuration for '{name}'")
            except Exception as e:
                logger.warning(f"Failed to load demo config for circuit breaker '{name}': {e}")
        
        _circuit_breakers[name] = CircuitBreaker(name, config, fallback)
    return _circuit_breakers[name]


async def get_all_circuit_breaker_stats() -> Dict[str, Any]:
    """Get statistics for all circuit breakers."""
    return {
        name: breaker.get_stats()
        for name, breaker in _circuit_breakers.items()
    }