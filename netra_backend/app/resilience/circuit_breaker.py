"""
Circuit Breaker Implementation for Infrastructure Dependencies

This module provides a comprehensive circuit breaker pattern implementation
for infrastructure dependencies to prevent cascade failures and enable
graceful degradation during infrastructure outages.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability and Customer Experience Protection
- Value Impact: Prevents cascade failures that could take down entire chat functionality
- Strategic Impact: Protects $500K+ ARR by maintaining service availability during infrastructure issues

Key Features:
- Multiple circuit breaker states (CLOSED, OPEN, HALF_OPEN)
- Configurable failure thresholds and recovery criteria
- Automatic state transitions based on success/failure patterns
- Integration with infrastructure resilience monitoring
- Performance impact tracking and alerting
- Graceful fallback mechanisms

Circuit Breaker States:
- CLOSED: Normal operation, all requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing recovery, limited requests allowed through

SSOT Compliance:
- Uses centralized configuration and logging
- Integrates with existing infrastructure monitoring
- Follows factory pattern for service isolation
- Maintains absolute imports and proper error handling
"""

import asyncio
import logging
import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import deque
import statistics

from netra_backend.app.core.config import get_config
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing fast due to threshold breach
    HALF_OPEN = "half_open" # Testing recovery with limited requests


class FailureType(Enum):
    """Types of failures that can trigger circuit breaker."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    # Failure thresholds
    failure_threshold: int = 5  # Number of failures to trigger OPEN state
    success_threshold: int = 3  # Number of successes to close from HALF_OPEN
    timeout_threshold: float = 30.0  # Seconds before considering operation timeout

    # Timing configuration
    recovery_timeout: float = 60.0  # Seconds before attempting recovery (OPEN -> HALF_OPEN)
    half_open_max_requests: int = 5  # Maximum requests allowed in HALF_OPEN state
    monitoring_window: float = 300.0  # Seconds for rolling window analysis

    # Advanced configuration
    failure_rate_threshold: float = 0.5  # Failure rate to trigger OPEN (0.0-1.0)
    minimum_requests: int = 10  # Minimum requests before failure rate calculation
    slow_call_threshold: float = 10.0  # Seconds to consider a call "slow"
    slow_call_rate_threshold: float = 0.8  # Slow call rate to trigger OPEN

    # Fallback configuration
    enable_fallback: bool = True
    fallback_cache_ttl: float = 300.0  # Seconds to cache fallback responses
    enable_graceful_degradation: bool = True

    # Monitoring and alerting
    enable_metrics: bool = True
    enable_alerts: bool = True
    alert_on_state_change: bool = True
    performance_tracking: bool = True
    
    @classmethod
    def for_infrastructure_service(cls, service_name: str, environment: str = "development") -> "CircuitBreakerConfig":
        """Create infrastructure-aware circuit breaker configuration."""
        # Base configuration
        config = cls()
        
        # Environment-specific adjustments for infrastructure pressure
        if environment in ["staging", "production"]:
            # Cloud environments need more tolerance for infrastructure delays
            config.timeout_threshold = 60.0  # Longer timeout for cloud infrastructure
            config.recovery_timeout = 120.0  # Longer recovery window
            config.failure_threshold = 7  # More failures before opening (infrastructure can be slow)
            config.slow_call_threshold = 30.0  # Higher threshold for "slow" calls
        else:
            # Development environment can be more aggressive
            config.timeout_threshold = 15.0
            config.recovery_timeout = 30.0
            config.failure_threshold = 3
            config.slow_call_threshold = 5.0
        
        # Service-specific optimizations
        if service_name in ["database", "auth_service"]:
            # Critical services get extra tolerance but faster alerting
            config.failure_threshold += 2
            config.alert_on_state_change = True
            config.enable_alerts = True
        elif service_name == "websocket":
            # WebSocket needs faster recovery for user experience
            config.recovery_timeout *= 0.5
            config.half_open_max_requests = 10
        
        return config


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracking for circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    circuit_breaker_opens: int = 0
    circuit_breaker_half_opens: int = 0
    fallback_executions: int = 0

    # Performance metrics
    total_execution_time: float = 0.0
    max_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    recent_execution_times: deque = field(default_factory=lambda: deque(maxlen=100))

    # Failure tracking by type
    failure_counts_by_type: Dict[FailureType, int] = field(default_factory=dict)

    # State transition tracking
    state_changes: List[Dict[str, Any]] = field(default_factory=list)
    last_state_change: Optional[datetime] = None

    # Time tracking
    total_time_open: float = 0.0
    total_time_half_open: float = 0.0
    current_state_start_time: Optional[datetime] = None

    def add_execution_time(self, execution_time: float) -> None:
        """Add execution time to metrics."""
        self.total_execution_time += execution_time
        self.recent_execution_times.append(execution_time)

        if execution_time > self.max_execution_time:
            self.max_execution_time = execution_time
        if execution_time < self.min_execution_time:
            self.min_execution_time = execution_time

    def get_average_execution_time(self) -> float:
        """Get average execution time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_execution_time / self.total_requests

    def get_recent_average_execution_time(self) -> float:
        """Get recent average execution time."""
        if not self.recent_execution_times:
            return 0.0
        return statistics.mean(self.recent_execution_times)

    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    def get_failure_rate(self) -> float:
        """Get failure rate as fraction (0.0-1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def record_state_change(self, old_state: CircuitBreakerState,
                           new_state: CircuitBreakerState, reason: str) -> None:
        """Record a state change event."""
        now = datetime.now()

        # Calculate time in previous state
        if self.current_state_start_time:
            time_in_state = (now - self.current_state_start_time).total_seconds()

            if old_state == CircuitBreakerState.OPEN:
                self.total_time_open += time_in_state
            elif old_state == CircuitBreakerState.HALF_OPEN:
                self.total_time_half_open += time_in_state

        # Record the state change
        self.state_changes.append({
            'timestamp': now.isoformat(),
            'old_state': old_state.value,
            'new_state': new_state.value,
            'reason': reason,
            'time_in_previous_state': time_in_state if self.current_state_start_time else 0
        })

        self.last_state_change = now
        self.current_state_start_time = now

        # Update counters
        if new_state == CircuitBreakerState.OPEN:
            self.circuit_breaker_opens += 1
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self.circuit_breaker_half_opens += 1


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is in OPEN state."""

    def __init__(self, service_name: str, state: CircuitBreakerState,
                 last_failure_reason: str = None):
        self.service_name = service_name
        self.state = state
        self.last_failure_reason = last_failure_reason

        message = f"Circuit breaker OPEN for {service_name}"
        if last_failure_reason:
            message += f" (last failure: {last_failure_reason})"
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker implementation for infrastructure dependencies.

    Provides automatic failure detection, state management, and graceful
    degradation for infrastructure services.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            config: Configuration for circuit breaker behavior
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self._state = CircuitBreakerState.CLOSED
        self._lock = threading.Lock()

        # Failure tracking
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._last_failure_reason: Optional[str] = None

        # Request tracking for HALF_OPEN state
        self._half_open_requests = 0

        # Metrics
        self._metrics = CircuitBreakerMetrics()
        if self.config.enable_metrics:
            self._metrics.current_state_start_time = datetime.now()

        # Fallback cache
        self._fallback_cache: Dict[str, Any] = {}
        self._fallback_cache_timestamps: Dict[str, datetime] = {}

        # Event handlers
        self._state_change_handlers: List[Callable[[str, CircuitBreakerState, CircuitBreakerState, str], None]] = []
        self._failure_handlers: List[Callable[[str, FailureType, str], None]] = []

        logger.debug(f"Circuit breaker '{name}' initialized with config: {self.config}")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is in CLOSED state."""
        return self.state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is in OPEN state."""
        return self.state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is in HALF_OPEN state."""
        return self.state == CircuitBreakerState.HALF_OPEN

    def add_state_change_handler(self, handler: Callable[[str, CircuitBreakerState, CircuitBreakerState, str], None]) -> None:
        """Add handler for state change events."""
        self._state_change_handlers.append(handler)

    def add_failure_handler(self, handler: Callable[[str, FailureType, str], None]) -> None:
        """Add handler for failure events."""
        self._failure_handlers.append(handler)

    async def call(self, func: Callable[..., T], *args, fallback: Optional[Callable[..., T]] = None, **kwargs) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Arguments for function
            fallback: Optional fallback function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerException: When circuit breaker is OPEN and no fallback
        """
        # Check if request should be allowed
        if not self._should_allow_request():
            if fallback and self.config.enable_fallback:
                logger.warning(f"Circuit breaker {self.name} is OPEN, executing fallback")
                try:
                    result = await self._execute_fallback(fallback, *args, **kwargs)
                    self._record_fallback_execution()
                    return result
                except Exception as e:
                    logger.error(f"Fallback execution failed for {self.name}: {e}")

            raise CircuitBreakerException(self.name, self._state, self._last_failure_reason)

        # Execute the function
        start_time = time.time()
        try:
            # Set timeout if configured
            if self.config.timeout_threshold > 0:
                result = await asyncio.wait_for(
                    self._execute_function(func, *args, **kwargs),
                    timeout=self.config.timeout_threshold
                )
            else:
                result = await self._execute_function(func, *args, **kwargs)

            execution_time = time.time() - start_time
            await self._record_success(execution_time)

            return result

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            await self._record_failure(FailureType.TIMEOUT, f"Operation timed out after {execution_time:.2f}s")
            raise

        except Exception as e:
            execution_time = time.time() - start_time
            failure_type = self._classify_failure(e)
            await self._record_failure(failure_type, str(e))
            raise

    async def _execute_function(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute the target function."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    async def _execute_fallback(self, fallback: Callable[..., T], *args, **kwargs) -> T:
        """Execute fallback function with caching if enabled."""
        cache_key = f"{fallback.__name__}_{hash(str(args) + str(kwargs))}"

        # Check cache first
        if self.config.enable_fallback and cache_key in self._fallback_cache:
            cache_time = self._fallback_cache_timestamps.get(cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self.config.fallback_cache_ttl:
                logger.debug(f"Returning cached fallback result for {self.name}")
                return self._fallback_cache[cache_key]

        # Execute fallback
        if asyncio.iscoroutinefunction(fallback):
            result = await fallback(*args, **kwargs)
        else:
            result = fallback(*args, **kwargs)

        # Cache result
        if self.config.enable_fallback:
            self._fallback_cache[cache_key] = result
            self._fallback_cache_timestamps[cache_key] = datetime.now()

        return result

    def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on circuit breaker state."""
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            elif self._state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has elapsed
                if self._last_failure_time:
                    time_since_failure = (datetime.now() - self._last_failure_time).total_seconds()
                    if time_since_failure >= self.config.recovery_timeout:
                        self._transition_to_half_open("Recovery timeout elapsed")
                        return True
                return False

            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited requests in half-open state
                if self._half_open_requests < self.config.half_open_max_requests:
                    self._half_open_requests += 1
                    return True
                return False

        return False

    async def _record_success(self, execution_time: float) -> None:
        """Record successful operation."""
        with self._lock:
            self._success_count += 1
            self._last_success_time = datetime.now()

            # Update metrics
            if self.config.enable_metrics:
                self._metrics.total_requests += 1
                self._metrics.successful_requests += 1
                self._metrics.add_execution_time(execution_time)

            # State transition logic
            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed("Success threshold reached in HALF_OPEN")
            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

        logger.debug(f"Circuit breaker {self.name} recorded success in {execution_time:.3f}s")

    async def _record_failure(self, failure_type: FailureType, reason: str) -> None:
        """Record failed operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            self._last_failure_reason = reason

            # Update metrics
            if self.config.enable_metrics:
                self._metrics.total_requests += 1
                self._metrics.failed_requests += 1

                if failure_type == FailureType.TIMEOUT:
                    self._metrics.timeouts += 1

                # Track failures by type
                if failure_type not in self._metrics.failure_counts_by_type:
                    self._metrics.failure_counts_by_type[failure_type] = 0
                self._metrics.failure_counts_by_type[failure_type] += 1

            # State transition logic
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state returns to open
                self._transition_to_open(f"Failure in HALF_OPEN state: {reason}")
            elif self._state == CircuitBreakerState.CLOSED:
                # Check if failure threshold reached
                should_open = False

                # Simple failure count threshold
                if self._failure_count >= self.config.failure_threshold:
                    should_open = True

                # Failure rate threshold (if we have enough requests)
                elif (self.config.enable_metrics and
                      self._metrics.total_requests >= self.config.minimum_requests):
                    failure_rate = self._metrics.get_failure_rate()
                    if failure_rate >= self.config.failure_rate_threshold:
                        should_open = True

                if should_open:
                    self._transition_to_open(f"Failure threshold exceeded: {reason}")

        # Trigger failure handlers
        for handler in self._failure_handlers:
            try:
                handler(self.name, failure_type, reason)
            except Exception as e:
                logger.error(f"Failure handler error for {self.name}: {e}")

        logger.warning(f"Circuit breaker {self.name} recorded failure: {failure_type.value} - {reason}")

    def _transition_to_open(self, reason: str) -> None:
        """Transition circuit breaker to OPEN state."""
        old_state = self._state
        self._state = CircuitBreakerState.OPEN
        self._success_count = 0  # Reset success count

        if self.config.enable_metrics:
            self._metrics.record_state_change(old_state, self._state, reason)

        self._trigger_state_change_handlers(old_state, self._state, reason)

        # Enhanced logging for infrastructure debugging
        logger.warning(f"🔴 CIRCUIT BREAKER OPENED: {self.name}")
        logger.warning(f"  Reason: {reason}")
        logger.warning(f"  Previous state: {old_state.value}")
        logger.warning(f"  Failure count: {self._failure_count}")
        logger.warning(f"  Last failure: {self._last_failure_time}")
        logger.warning(f"  Last failure reason: {self._last_failure_reason}")
        logger.warning(f"  This service is now FAILING FAST - check infrastructure status")
        
        # Critical infrastructure warning
        if self.name in ["database", "auth_service", "websocket"]:
            logger.critical(f"CRITICAL: {self.name} circuit breaker opened - CHAT FUNCTIONALITY IMPACTED")
            logger.critical(f"Infrastructure team attention required: {self.name} service degraded")

    def _transition_to_half_open(self, reason: str) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_requests = 0
        self._success_count = 0

        if self.config.enable_metrics:
            self._metrics.record_state_change(old_state, self._state, reason)

        self._trigger_state_change_handlers(old_state, self._state, reason)

        logger.info(f"Circuit breaker {self.name} half-opened: {reason}")

    def _transition_to_closed(self, reason: str) -> None:
        """Transition circuit breaker to CLOSED state."""
        old_state = self._state
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0

        if self.config.enable_metrics:
            self._metrics.record_state_change(old_state, self._state, reason)

        self._trigger_state_change_handlers(old_state, self._state, reason)

        # Enhanced recovery logging for infrastructure debugging
        logger.info(f"✅ CIRCUIT BREAKER RECOVERED: {self.name}")
        logger.info(f"  Reason: {reason}")
        logger.info(f"  Previous state: {old_state.value}")
        logger.info(f"  Service restored to normal operation")
        
        # Critical infrastructure recovery notification
        if self.name in ["database", "auth_service", "websocket"]:
            logger.info(f"🎉 INFRASTRUCTURE RECOVERY: {self.name} service restored - chat functionality available")
            logger.info(f"Infrastructure team: {self.name} service health restored")

    def _trigger_state_change_handlers(self, old_state: CircuitBreakerState,
                                      new_state: CircuitBreakerState, reason: str) -> None:
        """Trigger state change event handlers."""
        for handler in self._state_change_handlers:
            try:
                handler(self.name, old_state, new_state, reason)
            except Exception as e:
                logger.error(f"State change handler error for {self.name}: {e}")

    def _classify_failure(self, exception: Exception) -> FailureType:
        """Classify exception into failure type."""
        error_type = type(exception).__name__.lower()

        if "timeout" in error_type or isinstance(exception, asyncio.TimeoutError):
            return FailureType.TIMEOUT
        elif "connection" in error_type or "network" in error_type:
            return FailureType.CONNECTION_ERROR
        elif "unavailable" in error_type or "503" in str(exception):
            return FailureType.SERVICE_UNAVAILABLE
        elif "auth" in error_type or "401" in str(exception) or "403" in str(exception):
            return FailureType.AUTHENTICATION_ERROR
        elif "rate" in error_type or "429" in str(exception):
            return FailureType.RATE_LIMIT_EXCEEDED
        else:
            return FailureType.UNKNOWN_ERROR

    def _record_fallback_execution(self) -> None:
        """Record fallback execution in metrics."""
        if self.config.enable_metrics:
            self._metrics.fallback_executions += 1

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        with self._lock:
            return self._metrics

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
                'last_success_time': self._last_success_time.isoformat() if self._last_success_time else None,
                'last_failure_reason': self._last_failure_reason,
                'half_open_requests': self._half_open_requests,
                'metrics': {
                    'total_requests': self._metrics.total_requests,
                    'success_rate': self._metrics.get_success_rate(),
                    'failure_rate': self._metrics.get_failure_rate(),
                    'average_execution_time': self._metrics.get_average_execution_time(),
                    'recent_average_execution_time': self._metrics.get_recent_average_execution_time(),
                    'fallback_executions': self._metrics.fallback_executions,
                    'circuit_breaker_opens': self._metrics.circuit_breaker_opens,
                    'total_time_open': self._metrics.total_time_open,
                    'failure_counts_by_type': {k.value: v for k, v in self._metrics.failure_counts_by_type.items()}
                } if self.config.enable_metrics else {},
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'success_threshold': self.config.success_threshold,
                    'recovery_timeout': self.config.recovery_timeout,
                    'timeout_threshold': self.config.timeout_threshold,
                    'enable_fallback': self.config.enable_fallback
                }
            }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            old_state = self._state
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_requests = 0
            self._last_failure_time = None
            self._last_success_time = None
            self._last_failure_reason = None

            if self.config.enable_metrics:
                self._metrics = CircuitBreakerMetrics()
                self._metrics.current_state_start_time = datetime.now()

            # Clear caches
            self._fallback_cache.clear()
            self._fallback_cache_timestamps.clear()

        logger.info(f"Circuit breaker {self.name} reset from {old_state.value} to CLOSED")


class CircuitBreakerManager:
    """
    Centralized manager for multiple circuit breakers.

    Provides registration, configuration, and monitoring for all circuit breakers
    in the application.
    """

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
        self._lock = threading.Lock()

        # Global event handlers
        self._global_state_change_handlers: List[Callable[[str, CircuitBreakerState, CircuitBreakerState, str], None]] = []
        self._global_failure_handlers: List[Callable[[str, FailureType, str], None]] = []

        logger.info("Circuit breaker manager initialized")

    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create circuit breaker by name.

        Args:
            name: Circuit breaker name
            config: Optional configuration (uses default if not provided)

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._circuit_breakers:
                effective_config = config or self._default_config
                circuit_breaker = CircuitBreaker(name, effective_config)

                # Add global handlers
                for handler in self._global_state_change_handlers:
                    circuit_breaker.add_state_change_handler(handler)
                for handler in self._global_failure_handlers:
                    circuit_breaker.add_failure_handler(handler)

                self._circuit_breakers[name] = circuit_breaker
                logger.debug(f"Created new circuit breaker: {name}")

            return self._circuit_breakers[name]

    def add_global_state_change_handler(self, handler: Callable[[str, CircuitBreakerState, CircuitBreakerState, str], None]) -> None:
        """Add global state change handler to all circuit breakers."""
        self._global_state_change_handlers.append(handler)

        # Add to existing circuit breakers
        with self._lock:
            for circuit_breaker in self._circuit_breakers.values():
                circuit_breaker.add_state_change_handler(handler)

    def add_global_failure_handler(self, handler: Callable[[str, FailureType, str], None]) -> None:
        """Add global failure handler to all circuit breakers."""
        self._global_failure_handlers.append(handler)

        # Add to existing circuit breakers
        with self._lock:
            for circuit_breaker in self._circuit_breakers.values():
                circuit_breaker.add_failure_handler(handler)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        with self._lock:
            return {name: cb.get_status() for name, cb in self._circuit_breakers.items()}

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of all circuit breakers."""
        with self._lock:
            total_breakers = len(self._circuit_breakers)
            open_breakers = sum(1 for cb in self._circuit_breakers.values() if cb.is_open)
            half_open_breakers = sum(1 for cb in self._circuit_breakers.values() if cb.is_half_open)
            closed_breakers = sum(1 for cb in self._circuit_breakers.values() if cb.is_closed)

            overall_health = "healthy"
            if open_breakers > 0:
                overall_health = "critical" if open_breakers > total_breakers * 0.5 else "degraded"
            elif half_open_breakers > 0:
                overall_health = "recovering"

            return {
                'overall_health': overall_health,
                'total_circuit_breakers': total_breakers,
                'closed_breakers': closed_breakers,
                'open_breakers': open_breakers,
                'half_open_breakers': half_open_breakers,
                'open_breaker_names': [name for name, cb in self._circuit_breakers.items() if cb.is_open],
                'half_open_breaker_names': [name for name, cb in self._circuit_breakers.items() if cb.is_half_open],
                'timestamp': datetime.now().isoformat()
            }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._lock:
            for circuit_breaker in self._circuit_breakers.values():
                circuit_breaker.reset()
        logger.info("All circuit breakers reset")

    def reset_circuit_breaker(self, name: str) -> bool:
        """Reset specific circuit breaker by name."""
        with self._lock:
            if name in self._circuit_breakers:
                self._circuit_breakers[name].reset()
                logger.info(f"Circuit breaker {name} reset")
                return True
            return False


# Global circuit breaker manager instance
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None
_manager_lock = threading.Lock()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance."""
    global _circuit_breaker_manager

    with _manager_lock:
        if _circuit_breaker_manager is None:
            _circuit_breaker_manager = CircuitBreakerManager()
        return _circuit_breaker_manager


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get circuit breaker by name from global manager."""
    manager = get_circuit_breaker_manager()
    return manager.get_circuit_breaker(name, config)


@asynccontextmanager
async def circuit_breaker_protection(service_name: str, operation_name: str = None,
                                    config: Optional[CircuitBreakerConfig] = None,
                                    fallback: Optional[Callable] = None):
    """
    Context manager for circuit breaker protection.

    Args:
        service_name: Name of the service being protected
        operation_name: Optional operation name for logging
        config: Optional circuit breaker configuration
        fallback: Optional fallback function

    Usage:
        async with circuit_breaker_protection("database", "get_user") as cb:
            result = await some_database_operation()
    """
    circuit_breaker = get_circuit_breaker(service_name, config)
    operation_desc = f"{service_name}.{operation_name}" if operation_name else service_name

    logger.debug(f"Circuit breaker protection enabled for {operation_desc}")

    try:
        yield circuit_breaker
    except CircuitBreakerException:
        if fallback:
            logger.warning(f"Circuit breaker open for {operation_desc}, executing fallback")
            try:
                if asyncio.iscoroutinefunction(fallback):
                    result = await fallback()
                else:
                    result = fallback()
                yield result
                return
            except Exception as e:
                logger.error(f"Fallback failed for {operation_desc}: {e}")
        raise


# Export public interface
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitBreakerException",
    "CircuitBreakerMetrics",
    "FailureType",
    "get_circuit_breaker_manager",
    "get_circuit_breaker",
    "circuit_breaker_protection"
]