"""Core circuit breaker implementation - Single Source of Truth for base CircuitBreaker functionality.

This module provides the canonical CircuitBreaker implementation that serves as the base
for all circuit breaker variants in the system. This maintains backwards compatibility
while providing a foundation for the unified resilience framework.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide stable base circuit breaker for legacy compatibility
- Value Impact: Ensures existing code continues to work during unified transition
- Strategic Impact: Foundation for consolidated resilience architecture

All functions adhere to ≤8 line complexity limit per MANDATORY requirements.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from netra_backend.app.core.circuit_breaker_types import (
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitMetrics,
    CircuitState,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class CircuitBreaker:
    """Core circuit breaker implementation providing basic resilience patterns.
    
    This is the canonical implementation that other circuit breakers extend.
    Provides fundamental state management, failure tracking, and recovery logic.
    """
    
    def __init__(self, config: CircuitConfig) -> None:
        """Initialize circuit breaker with provided configuration."""
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
    async def call(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute operation with circuit breaker protection."""
        if not self.can_execute():
            self.metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(self.config.name)
        return await self._execute_operation(operation, *args, **kwargs)
        
    def can_execute(self) -> bool:
        """Check if operation can be executed based on current state."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            return self._should_attempt_recovery()
        else:  # HALF_OPEN
            return self._consecutive_failures < self.config.half_open_max_calls
            
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
        
    async def _execute_operation(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute the operation with timeout and error handling."""
        self.metrics.total_calls += 1
        start_time = time.time()
        try:
            result = await self._call_with_timeout(operation, *args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(time.time() - start_time, type(e).__name__)
            raise
            
    async def _call_with_timeout(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Call operation with configured timeout."""
        if asyncio.iscoroutinefunction(operation):
            return await asyncio.wait_for(
                operation(*args, **kwargs), 
                timeout=self.config.timeout_seconds
            )
        else:
            return await asyncio.get_event_loop().run_in_executor(
                None, operation, *args, **kwargs
            )
            
    def _record_success(self, response_time: float) -> None:
        """Record successful operation execution."""
        self.metrics.successful_calls += 1
        self._consecutive_successes += 1
        self._consecutive_failures = 0
        self.last_success_time = time.time()
        self._handle_success_state_transition()
        
    def _handle_success_state_transition(self) -> None:
        """Handle state transitions after successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            if self._consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure tracking on success
            self._consecutive_failures = 0
            
    def _record_failure(self, response_time: float, error_type: str) -> None:
        """Record failed operation execution."""
        self.metrics.failed_calls += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        self.last_failure_time = time.time()
        self._handle_failure_state_transition()
        
    def _handle_failure_state_transition(self) -> None:
        """Handle state transitions after failed execution."""
        if self._consecutive_failures >= self.config.failure_threshold:
            if self.state == CircuitState.CLOSED:
                self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
                
    def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state."""
        logger.warning(f"Circuit breaker '{self.config.name}' -> OPEN")
        self.state = CircuitState.OPEN
        self.metrics.state_changes += 1
        
    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state."""
        logger.info(f"Circuit breaker '{self.config.name}' -> HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.metrics.state_changes += 1
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.config.name}' -> CLOSED")
        self.state = CircuitState.CLOSED
        self.metrics.state_changes += 1
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
    def get_metrics(self) -> CircuitMetrics:
        """Get current circuit breaker metrics."""
        return self.metrics
        
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            'name': self.config.name,
            'state': self.state.value,
            'is_healthy': self.state == CircuitState.CLOSED,
            'consecutive_failures': self._consecutive_failures,
            'consecutive_successes': self._consecutive_successes,
            'total_calls': self.metrics.total_calls,
            'successful_calls': self.metrics.successful_calls,
            'failed_calls': self.metrics.failed_calls,
            'rejected_calls': self.metrics.rejected_calls
        }
        
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        logger.info(f"Resetting circuit breaker '{self.config.name}'")
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        
    # Compatibility properties
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
        
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED
        
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == CircuitState.HALF_OPEN
        
    def record_success(self) -> None:
        """Record success for compatibility with legacy code."""
        self._record_success(0.0)
        
    def record_failure(self, error_type: str = "generic_error") -> None:
        """Record failure for compatibility with legacy code."""
        self._record_failure(0.0, error_type)