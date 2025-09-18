"""
Agent reliability management system.
Handles circuit breakers, retry logic, and failure recovery for agent operations.
"""

from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime, timedelta, UTC
import asyncio
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded threshold, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


class ReliabilityManager:
    """Manages reliability patterns for agent operations."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 half_open_max_calls: int = 3):
        """
        Initialize reliability manager.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open state
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_call_count = 0
        self._successful_calls = 0
        
        logger.debug(f"Initialized ReliabilityManager with threshold={failure_threshold}")
    
    async def execute_with_reliability(self, 
                                     operation: Callable[[], Awaitable[Any]],
                                     operation_name: str = "unknown") -> Any:
        """
        Execute operation with reliability patterns (circuit breaker, retry).
        
        Args:
            operation: Async operation to execute
            operation_name: Name of operation for logging
            
        Returns:
            Operation result
            
        Raises:
            Exception: If operation fails after all reliability patterns
        """
        # Check circuit breaker
        if not await self._can_execute():
            raise RuntimeError(f"Circuit breaker is OPEN for {operation_name}")
        
        try:
            # Execute operation with retry logic
            result = await self._execute_with_retry(operation, operation_name)
            
            # Record success
            await self._record_success()
            
            return result
            
        except Exception as e:
            # Record failure
            await self._record_failure(operation_name, str(e))
            raise
    
    async def _can_execute(self) -> bool:
        """Check if operation can be executed based on circuit breaker state."""
        if self._circuit_state == CircuitState.CLOSED:
            return True
        
        if self._circuit_state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if (self._last_failure_time and 
                datetime.now(UTC) - self._last_failure_time >= timedelta(seconds=self.recovery_timeout)):
                # Move to half-open state
                self._circuit_state = CircuitState.HALF_OPEN
                self._half_open_call_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
        
        if self._circuit_state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self._half_open_call_count < self.half_open_max_calls
        
        return False
    
    async def _execute_with_retry(self, 
                                operation: Callable[[], Awaitable[Any]],
                                operation_name: str,
                                max_retries: int = 3) -> Any:
        """Execute operation with retry logic."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Wait before retry with exponential backoff
                    wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                    logger.info(f"Retrying {operation_name} (attempt {attempt + 1}) after {wait_time}s")
                    await asyncio.sleep(wait_time)
                
                result = await operation()
                
                if attempt > 0:
                    logger.info(f"Operation {operation_name} succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Operation {operation_name} failed (attempt {attempt + 1}): {e}")
                
                # Don't retry certain types of errors
                if self._is_non_retryable_error(e):
                    logger.info(f"Non-retryable error for {operation_name}: {e}")
                    break
        
        # All retries exhausted
        logger.error(f"Operation {operation_name} failed after {max_retries} retries")
        raise last_exception
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if error should not be retried."""
        non_retryable_types = [
            ValueError,  # Invalid input
            TypeError,   # Programming error
            # Add more non-retryable error types as needed
        ]
        
        return any(isinstance(error, error_type) for error_type in non_retryable_types)
    
    async def _record_success(self) -> None:
        """Record successful operation."""
        self._successful_calls += 1
        
        if self._circuit_state == CircuitState.HALF_OPEN:
            # Check if we should close the circuit
            if self._successful_calls >= 2:  # Require at least 2 successes
                self._circuit_state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_call_count = 0
                logger.info("Circuit breaker moved to CLOSED state after successful recovery")
        
        # Reset failure count on success in closed state
        if self._circuit_state == CircuitState.CLOSED:
            self._failure_count = 0
    
    async def _record_failure(self, operation_name: str, error_message: str) -> None:
        """Record failed operation."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(UTC)
        
        logger.warning(f"Recorded failure for {operation_name}: {error_message}")
        logger.debug(f"Failure count: {self._failure_count}/{self.failure_threshold}")
        
        # Check if we should open the circuit
        if (self._circuit_state in [CircuitState.CLOSED, CircuitState.HALF_OPEN] and 
            self._failure_count >= self.failure_threshold):
            
            self._circuit_state = CircuitState.OPEN
            self._half_open_call_count = 0
            self._successful_calls = 0
            
            logger.error(f"Circuit breaker OPENED after {self._failure_count} failures")
        
        # Update half-open call count
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._half_open_call_count += 1
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": self._circuit_state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "successful_calls": self._successful_calls,
            "last_failure_time": self._last_failure_time,
            "half_open_call_count": self._half_open_call_count,
            "can_execute": asyncio.run(self._can_execute()) if asyncio.get_event_loop().is_running() else None
        }
    
    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_call_count = 0
        self._successful_calls = 0
        self._last_failure_time = None
        
        logger.info("Circuit breaker manually reset to CLOSED state")
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of reliability manager."""
        can_execute = await self._can_execute()
        
        health_status = "healthy"
        if self._circuit_state == CircuitState.OPEN:
            health_status = "degraded"
        elif self._circuit_state == CircuitState.HALF_OPEN:
            health_status = "recovering"
        
        return {
            "status": health_status,
            "circuit_state": self._circuit_state.value,
            "can_execute": can_execute,
            "failure_count": self._failure_count,
            "successful_calls": self._successful_calls,
            "timestamp": datetime.now(UTC)
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of reliability manager (synchronous version)."""
        health_status = "healthy"
        if self._circuit_state == CircuitState.OPEN:
            health_status = "degraded"
        elif self._circuit_state == CircuitState.HALF_OPEN:
            health_status = "recovering"
        
        # Calculate overall health
        overall_health = health_status
        
        return {
            "status": health_status,
            "overall_health": overall_health,
            "circuit_state": self._circuit_state.value,
            "failure_count": self._failure_count,
            "successful_calls": self._successful_calls,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "timestamp": datetime.now(UTC)
        }
    
    def reset_metrics(self) -> None:
        """Reset reliability manager metrics."""
        self._failure_count = 0
        self._successful_calls = 0
        self._half_open_call_count = 0
        self._last_failure_time = None
        self._circuit_state = CircuitState.CLOSED
        logger.info("Reliability manager metrics reset")
    
    def reset_health_tracking(self) -> None:
        """Reset health tracking state."""
        self.reset_metrics()  # Same as reset_metrics for now


__all__ = [
    "ReliabilityManager",
    "CircuitState",
]