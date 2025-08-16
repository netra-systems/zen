"""Adaptive circuit breaker patterns with health checks and recovery.

Provides intelligent circuit breakers that adapt to system conditions and
include proactive health monitoring and automatic recovery mechanisms.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.logging_config import central_logger

# Import unified types from single source of truth
from app.schemas.core_enums import CircuitBreakerState
from app.schemas.core_models import CircuitBreakerConfig, HealthCheckResult

# Import consolidated health checkers from single sources of truth
from .shared_health_types import DatabaseHealthChecker
from .circuit_breaker_health_checkers import ApiHealthChecker

logger = central_logger.get_logger(__name__)

# Use CircuitBreakerState as CircuitState for backward compatibility
CircuitState = CircuitBreakerState


class HealthStatus(Enum):
    """Health check statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthChecker(ABC):
    """Abstract base for health check implementations."""
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        pass


# DatabaseHealthChecker imported from shared_health_types.py


# ApiHealthChecker imported from circuit_breaker_health_checkers.py


class AdaptiveCircuitBreaker:
    """Adaptive circuit breaker with health monitoring."""
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        health_checker: Optional[HealthChecker] = None
    ):
        """Initialize adaptive circuit breaker."""
        self.name = name
        self.config = config
        self.health_checker = health_checker
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.slow_requests = 0
        
        # Health monitoring
        self.last_health_check: Optional[HealthCheckResult] = None
        self.health_history: List[HealthCheckResult] = []
        
        # Adaptive behavior
        self.adaptive_failure_threshold = config.failure_threshold
        self.recent_response_times: List[float] = []
        
        # Background health checking
        self._health_check_task: Optional[asyncio.Task] = None
        self._start_health_monitoring()
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection."""
        self.total_requests += 1
        self._validate_request_allowed()
        start_time = datetime.now()
        try:
            result = await self._execute_operation(operation, start_time, *args, **kwargs)
            return result
        except Exception as e:
            self._handle_operation_failure(start_time)
            raise e
    
    def _validate_request_allowed(self) -> None:
        """Validate if request should be allowed through circuit breaker"""
        if not self.should_allow_request():
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
    
    async def _execute_operation(self, operation: Callable, start_time: datetime, *args, **kwargs) -> Any:
        """Execute operation and record success"""
        result = await operation(*args, **kwargs)
        response_time = (datetime.now() - start_time).total_seconds()
        self._record_success(response_time)
        return result
    
    def _handle_operation_failure(self, start_time: datetime) -> None:
        """Handle operation failure and record metrics"""
        response_time = (datetime.now() - start_time).total_seconds()
        self._record_failure(response_time)
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed through circuit."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self, response_time: float) -> None:
        """Record successful operation."""
        self.successful_requests += 1
        self._track_response_time(response_time)
        self._check_slow_request(response_time)
        self._handle_success_state_transition()
    
    def _track_response_time(self, response_time: float) -> None:
        """Track response time and maintain recent history"""
        self.recent_response_times.append(response_time)
        if len(self.recent_response_times) > 100:
            self.recent_response_times = self.recent_response_times[-50:]
    
    def _check_slow_request(self, response_time: float) -> None:
        """Check if request is slow and update metrics"""
        if response_time > self.config.slow_call_threshold:
            self.slow_requests += 1
    
    def _handle_success_state_transition(self) -> None:
        """Handle circuit breaker state transitions on success"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _record_failure(self, response_time: float) -> None:
        """Record failed operation."""
        self.failed_requests += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self._handle_adaptive_threshold()
        self._handle_failure_state_transition()
    
    def _handle_adaptive_threshold(self) -> None:
        """Handle adaptive threshold adjustment on failure"""
        if self.config.adaptive_threshold:
            self._adapt_failure_threshold()
    
    def _handle_failure_state_transition(self) -> None:
        """Handle circuit breaker state transitions on failure"""
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.adaptive_failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _adapt_failure_threshold(self) -> None:
        """Adapt failure threshold based on system conditions."""
        # Consider average response time
        if self.recent_response_times:
            avg_response_time = sum(self.recent_response_times) / len(self.recent_response_times)
            
            # Lower threshold if system is slow
            if avg_response_time > self.config.slow_call_threshold:
                self.adaptive_failure_threshold = max(
                    self.config.failure_threshold - 1, 2
                )
            else:
                self.adaptive_failure_threshold = min(
                    self.config.failure_threshold + 1, 10
                )
        
        # Consider health check results
        if self.last_health_check:
            if self.last_health_check.status == HealthStatus.DEGRADED:
                self.adaptive_failure_threshold = max(
                    self.adaptive_failure_threshold - 1, 2
                )
            elif self.last_health_check.status == HealthStatus.HEALTHY:
                self.adaptive_failure_threshold = min(
                    self.adaptive_failure_threshold + 1, 8
                )
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if not self.last_failure_time:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        timeout_reached = time_since_failure.total_seconds() >= self.config.timeout_seconds
        
        # Consider health check status
        health_ok = True
        if self.last_health_check:
            health_ok = self.last_health_check.status != HealthStatus.UNHEALTHY
        
        return timeout_reached and health_ok
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def _transition_to_open(self) -> None:
        """Transition circuit to open state."""
        logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self.health_checker and not self._health_check_task:
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.health_checker:
                    health_result = await self.health_checker.check_health()
                    self.last_health_check = health_result
                    self.health_history.append(health_result)
                    
                    # Keep only recent history
                    if len(self.health_history) > 100:
                        self.health_history = self.health_history[-50:]
                    
                    # Log significant health changes
                    if health_result.status == HealthStatus.UNHEALTHY:
                        logger.warning(
                            f"Health check failed for {self.name}: {health_result.details}"
                        )
                    elif health_result.status == HealthStatus.HEALTHY and self.state == CircuitState.OPEN:
                        logger.info(f"Health recovered for {self.name}, may attempt reset")
                        
            except Exception as e:
                logger.error(f"Health check error for {self.name}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'slow_requests': self.slow_requests,
            'failure_rate': self.failed_requests / max(self.total_requests, 1),
            'adaptive_threshold': self.adaptive_failure_threshold,
            'last_state_change': self.last_state_change.isoformat(),
            'last_health_status': self.last_health_check.status.value if self.last_health_check else None,
            'avg_response_time': sum(self.recent_response_times) / len(self.recent_response_times) if self.recent_response_times else 0
        }
    
    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        logger.warning(f"Forcing circuit breaker {self.name} to OPEN")
        self._transition_to_open()
    
    def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        logger.info(f"Forcing circuit breaker {self.name} to CLOSED")
        self._transition_to_closed()
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._health_check_task:
            self._health_check_task.cancel()


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# CircuitBreakerRegistry moved to circuit_breaker_registry_adaptive.py
# Import from there for consolidated single source of truth