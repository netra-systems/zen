"""Circuit Breaker Manager for API Gateway

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (reliability and performance)
- Business Goal: Prevent cascade failures and maintain service availability
- Value Impact: Ensures API stability under high load and failure conditions
- Strategic Impact: Critical for enterprise-grade API reliability

Manages circuit breakers for API endpoints with intelligent failure detection.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Blocking requests
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    test_request_timeout: int = 5
    success_threshold: int = 3
    rolling_window_size: int = 100
    minimum_requests: int = 10


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    total_requests: int = 0
    failed_requests: int = 0
    successful_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0


@dataclass
class CircuitBreaker:
    """Individual circuit breaker instance."""
    name: str
    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    stats: CircuitBreakerStats = field(default_factory=CircuitBreakerStats)
    last_state_change: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recent_results: List[bool] = field(default_factory=list)
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.current_consecutive_successes += 1
        self.stats.current_consecutive_failures = 0
        self.stats.last_success_time = datetime.now(timezone.utc)
        self._update_recent_results(True)
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.current_consecutive_failures += 1
        self.stats.current_consecutive_successes = 0
        self.stats.last_failure_time = datetime.now(timezone.utc)
        self._update_recent_results(False)
    
    def _update_recent_results(self, success: bool) -> None:
        """Update rolling window of recent results."""
        self.recent_results.append(success)
        if len(self.recent_results) > self.config.rolling_window_size:
            self.recent_results.pop(0)
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if len(self.recent_results) < self.config.minimum_requests:
            return 0.0
        failures = sum(1 for result in self.recent_results if not result)
        return failures / len(self.recent_results)
    
    @property
    def should_open(self) -> bool:
        """Check if circuit should open."""
        return (self.stats.current_consecutive_failures >= self.config.failure_threshold or
                self.failure_rate > 0.5)
    
    @property
    def should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self.state != CircuitState.OPEN:
            return False
        time_since_last_change = (datetime.now(timezone.utc) - self.last_state_change).total_seconds()
        return time_since_last_change >= self.config.recovery_timeout
    
    @property
    def should_close(self) -> bool:
        """Check if circuit should close from half-open."""
        return self.stats.current_consecutive_successes >= self.config.success_threshold


class CircuitBreakerManager:
    """Manages circuit breakers for API endpoints."""
    
    def __init__(self):
        """Initialize the circuit breaker manager."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
        self._lock = asyncio.Lock()
    
    async def register_endpoint(self, endpoint: str, config: Optional[CircuitBreakerConfig] = None) -> None:
        """Register an endpoint with a circuit breaker."""
        async with self._lock:
            if endpoint in self._circuit_breakers:
                logger.warning(f"Circuit breaker for endpoint {endpoint} already exists")
                return
            
            breaker_config = config or self._default_config
            circuit_breaker = CircuitBreaker(
                name=endpoint,
                config=breaker_config
            )
            self._circuit_breakers[endpoint] = circuit_breaker
            logger.info(f"Registered circuit breaker for endpoint: {endpoint}")
    
    async def is_request_allowed(self, endpoint: str) -> bool:
        """Check if a request to the endpoint is allowed."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            if not circuit_breaker:
                # No circuit breaker configured, allow request
                return True
            
            await self._update_circuit_state(circuit_breaker)
            
            if circuit_breaker.state == CircuitState.CLOSED:
                return True
            elif circuit_breaker.state == CircuitState.HALF_OPEN:
                # Allow limited test requests
                return True
            else:  # OPEN
                return False
    
    async def record_success(self, endpoint: str) -> None:
        """Record a successful request to an endpoint."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            if not circuit_breaker:
                return
            
            circuit_breaker.record_success()
            await self._update_circuit_state(circuit_breaker)
            logger.debug(f"Recorded success for endpoint: {endpoint}")
    
    async def record_failure(self, endpoint: str) -> None:
        """Record a failed request to an endpoint."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            if not circuit_breaker:
                return
            
            circuit_breaker.record_failure()
            await self._update_circuit_state(circuit_breaker)
            logger.debug(f"Recorded failure for endpoint: {endpoint}")
    
    async def get_circuit_state(self, endpoint: str) -> Optional[CircuitState]:
        """Get the current state of a circuit breaker."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            return circuit_breaker.state if circuit_breaker else None
    
    async def get_circuit_stats(self, endpoint: str) -> Optional[CircuitBreakerStats]:
        """Get statistics for a circuit breaker."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            return circuit_breaker.stats if circuit_breaker else None
    
    async def get_all_circuits(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all circuit breakers."""
        async with self._lock:
            result = {}
            for endpoint, breaker in self._circuit_breakers.items():
                result[endpoint] = {
                    "state": breaker.state.value,
                    "failure_rate": breaker.failure_rate,
                    "stats": {
                        "total_requests": breaker.stats.total_requests,
                        "failed_requests": breaker.stats.failed_requests,
                        "successful_requests": breaker.stats.successful_requests,
                        "consecutive_failures": breaker.stats.current_consecutive_failures,
                        "consecutive_successes": breaker.stats.current_consecutive_successes
                    }
                }
            return result
    
    async def force_open(self, endpoint: str) -> bool:
        """Manually force a circuit breaker to open."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            if not circuit_breaker:
                return False
            
            await self._transition_to_open(circuit_breaker)
            logger.warning(f"Manually forced circuit breaker open for endpoint: {endpoint}")
            return True
    
    async def force_close(self, endpoint: str) -> bool:
        """Manually force a circuit breaker to close."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(endpoint)
            if not circuit_breaker:
                return False
            
            await self._transition_to_closed(circuit_breaker)
            logger.info(f"Manually forced circuit breaker closed for endpoint: {endpoint}")
            return True
    
    async def _update_circuit_state(self, circuit_breaker: CircuitBreaker) -> None:
        """Update the state of a circuit breaker based on current conditions."""
        if circuit_breaker.state == CircuitState.CLOSED:
            if circuit_breaker.should_open:
                await self._transition_to_open(circuit_breaker)
        
        elif circuit_breaker.state == CircuitState.OPEN:
            if circuit_breaker.should_attempt_reset:
                await self._transition_to_half_open(circuit_breaker)
        
        elif circuit_breaker.state == CircuitState.HALF_OPEN:
            if circuit_breaker.should_close:
                await self._transition_to_closed(circuit_breaker)
            elif circuit_breaker.should_open:
                await self._transition_to_open(circuit_breaker)
    
    async def _transition_to_open(self, circuit_breaker: CircuitBreaker) -> None:
        """Transition circuit breaker to open state."""
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.last_state_change = datetime.now(timezone.utc)
        circuit_breaker.stats.state_changes += 1
        logger.warning(f"Circuit breaker opened for: {circuit_breaker.name}")
    
    async def _transition_to_half_open(self, circuit_breaker: CircuitBreaker) -> None:
        """Transition circuit breaker to half-open state."""
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.last_state_change = datetime.now(timezone.utc)
        circuit_breaker.stats.state_changes += 1
        circuit_breaker.stats.current_consecutive_successes = 0
        logger.info(f"Circuit breaker half-opened for: {circuit_breaker.name}")
    
    async def _transition_to_closed(self, circuit_breaker: CircuitBreaker) -> None:
        """Transition circuit breaker to closed state."""
        circuit_breaker.state = CircuitState.CLOSED
        circuit_breaker.last_state_change = datetime.now(timezone.utc)
        circuit_breaker.stats.state_changes += 1
        circuit_breaker.stats.current_consecutive_failures = 0
        logger.info(f"Circuit breaker closed for: {circuit_breaker.name}")
    
    async def cleanup_inactive_circuits(self, max_age_hours: int = 24) -> int:
        """Clean up inactive circuit breakers."""
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            inactive_circuits = []
            
            for endpoint, breaker in self._circuit_breakers.items():
                if breaker.stats.last_success_time and breaker.stats.last_failure_time:
                    last_activity = max(breaker.stats.last_success_time, breaker.stats.last_failure_time)
                elif breaker.stats.last_success_time:
                    last_activity = breaker.stats.last_success_time
                elif breaker.stats.last_failure_time:
                    last_activity = breaker.stats.last_failure_time
                else:
                    last_activity = breaker.last_state_change
                
                if (current_time - last_activity).total_seconds() > max_age_hours * 3600:
                    inactive_circuits.append(endpoint)
            
            for endpoint in inactive_circuits:
                del self._circuit_breakers[endpoint]
            
            logger.info(f"Cleaned up {len(inactive_circuits)} inactive circuit breakers")
            return len(inactive_circuits)


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()