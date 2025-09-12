"""
Retry Mechanism - Progressive retry logic with circuit breaker patterns.

Provides sophisticated retry logic with exponential backoff, jitter,
circuit breaker patterns, and environment-specific configurations.
Integrates with existing reliability patterns while providing systematic
retry coordination for service dependency resolution.
"""

import asyncio
import logging
import random
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.logging_config import central_logger
from .models import (
    EnvironmentType,
    RetryContext,
    RetryStrategy,
    ServiceConfiguration,
    ServiceType,
)


class CircuitBreakerState:
    """Circuit breaker state tracking for service retries."""
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed, open, half_open
        self.failure_threshold = 5
        self.recovery_timeout = 30.0  # seconds
        self.half_open_max_calls = 3
        self.half_open_calls = 0


class RetryMechanism:
    """
    Progressive retry mechanism with circuit breaker and environment awareness.
    
    Provides intelligent retry logic that adapts to service failures,
    implements circuit breaker patterns to prevent cascade failures,
    and adjusts retry strategies based on environment configuration.
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize retry mechanism."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        
        # Circuit breaker state per service
        self._circuit_breakers: Dict[ServiceType, CircuitBreakerState] = {}
        
        # Service configuration cache
        self._service_configs: Dict[ServiceType, ServiceConfiguration] = {}
        self._initialize_service_configs()
        
        # Statistics tracking
        self._retry_stats: Dict[ServiceType, Dict[str, int]] = {}
    
    def _initialize_service_configs(self) -> None:
        """Initialize service configurations for current environment."""
        for service_type in ServiceType:
            self._service_configs[service_type] = ServiceConfiguration.for_environment(
                service_type, self.environment
            )
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        service_type: ServiceType,
        operation_name: str = "operation"
    ) -> Any:
        """
        Execute an operation with retry logic and circuit breaker protection.
        
        Args:
            operation: Async callable to execute with retry
            service_type: Type of service for configuration
            operation_name: Name of operation for logging
            
        Returns:
            Result of successful operation execution
            
        Raises:
            Exception: Final exception after all retries exhausted
        """
        config = self._service_configs[service_type]
        circuit_breaker = self._get_circuit_breaker(service_type)
        
        # Check circuit breaker state
        if not self._can_execute(circuit_breaker):
            raise Exception(f"Circuit breaker OPEN for {service_type.value} - too many failures")
        
        # Initialize retry context
        retry_context = RetryContext(
            service_type=service_type,
            attempt_number=0,
            total_attempts=config.max_retries + 1  # +1 for initial attempt
        )
        
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            retry_context.attempt_number = attempt + 1
            
            try:
                self.logger.debug(
                    f"Attempting {operation_name} for {service_type.value} "
                    f"(attempt {attempt + 1}/{config.max_retries + 1})"
                )
                
                # Execute operation with timeout
                result = await asyncio.wait_for(
                    operation(),
                    timeout=config.timeout_seconds
                )
                
                # Success - update circuit breaker and stats
                self._record_success(circuit_breaker, service_type)
                self._update_retry_stats(service_type, "success", attempt)
                
                if attempt > 0:
                    self.logger.info(
                        f"[U+2713] {operation_name} succeeded for {service_type.value} "
                        f"after {attempt} retries"
                    )
                
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                retry_context.last_error = f"Timeout after {config.timeout_seconds}s"
                self.logger.warning(
                    f"[U+23F1][U+FE0F] {operation_name} timeout for {service_type.value} "
                    f"(attempt {attempt + 1}/{config.max_retries + 1})"
                )
                
            except Exception as e:
                last_exception = e
                retry_context.last_error = str(e)
                self.logger.warning(
                    f" FAIL:  {operation_name} failed for {service_type.value} "
                    f"(attempt {attempt + 1}/{config.max_retries + 1}): {str(e)}"
                )
            
            # Record failure
            self._record_failure(circuit_breaker, service_type)
            
            # Don't retry on final attempt
            if attempt < config.max_retries:
                # Calculate retry delay
                retry_delay = self._calculate_retry_delay(
                    config, attempt, retry_context
                )
                
                retry_context.retry_delay_seconds = retry_delay
                retry_context.accumulated_delay += retry_delay
                
                self.logger.debug(
                    f"Retrying {operation_name} for {service_type.value} "
                    f"in {retry_delay:.2f}s"
                )
                
                await asyncio.sleep(retry_delay)
                
                # Check circuit breaker again before retry
                if not self._can_execute(circuit_breaker):
                    self.logger.error(
                        f" FIRE:  Circuit breaker opened during retry for {service_type.value}"
                    )
                    break
        
        # All retries exhausted - update stats and raise final exception
        self._update_retry_stats(service_type, "failure", config.max_retries)
        
        self.logger.error(
            f"[U+1F6AB] All retry attempts exhausted for {operation_name} on {service_type.value} "
            f"(total delay: {retry_context.accumulated_delay:.2f}s)"
        )
        
        if last_exception:
            # Enhance exception with retry context
            error_message = (
                f"{operation_name} failed for {service_type.value} after "
                f"{config.max_retries + 1} attempts. Last error: {str(last_exception)}"
            )
            
            # Safe exception construction with Python 3.11+ compatibility
            try:
                # Attempt dynamic construction for simple cases
                enhanced_exception = type(last_exception)(error_message)
            except (TypeError, ValueError) as construction_error:
                # Fallback for complex exception constructors (UnicodeDecodeError, etc.)
                self.logger.debug(
                    f"Failed to construct {type(last_exception).__name__} with message: {construction_error}. "
                    f"Using RuntimeError wrapper."
                )
                # Create a RuntimeError with detailed information
                enhanced_exception = RuntimeError(
                    f"{error_message} (Original exception: {type(last_exception).__name__}: {str(last_exception)})"
                )
            
            # Preserve exception chain for debugging
            raise enhanced_exception from last_exception
        else:
            raise Exception(f"{operation_name} failed for {service_type.value} - no error details")
    
    def _get_circuit_breaker(self, service_type: ServiceType) -> CircuitBreakerState:
        """Get or create circuit breaker for service type."""
        if service_type not in self._circuit_breakers:
            self._circuit_breakers[service_type] = CircuitBreakerState()
        return self._circuit_breakers[service_type]
    
    def _can_execute(self, circuit_breaker: CircuitBreakerState) -> bool:
        """Check if operation can execute based on circuit breaker state."""
        current_time = time.time()
        
        if circuit_breaker.state == "closed":
            return True
        elif circuit_breaker.state == "open":
            # Check if recovery timeout has elapsed
            if current_time - circuit_breaker.last_failure_time >= circuit_breaker.recovery_timeout:
                circuit_breaker.state = "half_open"
                circuit_breaker.half_open_calls = 0
                self.logger.info("Circuit breaker moving from OPEN to HALF_OPEN")
                return True
            return False
        elif circuit_breaker.state == "half_open":
            # Allow limited calls in half-open state
            return circuit_breaker.half_open_calls < circuit_breaker.half_open_max_calls
        
        return False
    
    def _record_success(self, circuit_breaker: CircuitBreakerState, service_type: ServiceType) -> None:
        """Record successful operation in circuit breaker."""
        circuit_breaker.success_count += 1
        
        if circuit_breaker.state == "half_open":
            circuit_breaker.half_open_calls += 1
            if circuit_breaker.half_open_calls >= circuit_breaker.half_open_max_calls:
                # Enough successful calls - close circuit breaker
                circuit_breaker.state = "closed"
                circuit_breaker.failure_count = 0
                circuit_breaker.half_open_calls = 0
                self.logger.info(f"Circuit breaker CLOSED for {service_type.value}")
        elif circuit_breaker.state == "closed":
            # Reset failure count on success
            if circuit_breaker.failure_count > 0:
                circuit_breaker.failure_count = max(0, circuit_breaker.failure_count - 1)
    
    def _record_failure(self, circuit_breaker: CircuitBreakerState, service_type: ServiceType) -> None:
        """Record failed operation in circuit breaker."""
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = time.time()
        
        if circuit_breaker.state == "half_open":
            # Failure in half-open state - back to open
            circuit_breaker.state = "open"
            self.logger.warning(f"Circuit breaker OPEN for {service_type.value} (half-open failure)")
        elif circuit_breaker.state == "closed":
            # Check if we should open circuit breaker
            if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                circuit_breaker.state = "open"
                self.logger.error(
                    f"Circuit breaker OPENED for {service_type.value} "
                    f"({circuit_breaker.failure_count} failures)"
                )
    
    def _calculate_retry_delay(
        self,
        config: ServiceConfiguration,
        attempt: int,
        retry_context: RetryContext
    ) -> float:
        """Calculate retry delay based on strategy and attempt number."""
        base_delay = config.retry_delay_base
        
        if config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt)
            # Add jitter ( +/- 25% of delay)
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay = max(0.1, delay + jitter)  # Minimum 100ms delay
            
        elif config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            # Linear increase with jitter
            delay = base_delay * (1 + attempt)
            jitter = delay * 0.1 * (2 * random.random() - 1)
            delay = max(0.1, delay + jitter)
            
        elif config.retry_strategy == RetryStrategy.FIXED_INTERVAL:
            # Fixed delay with small jitter
            delay = base_delay
            jitter = delay * 0.05 * (2 * random.random() - 1)
            delay = max(0.1, delay + jitter)
            
        else:  # NO_RETRY or unknown
            delay = 0.0
        
        # Cap maximum delay based on environment
        max_delay = {
            EnvironmentType.TESTING: 2.0,
            EnvironmentType.DEVELOPMENT: 10.0,
            EnvironmentType.STAGING: 30.0,
            EnvironmentType.PRODUCTION: 60.0
        }.get(self.environment, 10.0)
        
        return min(delay, max_delay)
    
    def _update_retry_stats(
        self,
        service_type: ServiceType,
        outcome: str,
        attempts: int
    ) -> None:
        """Update retry statistics for monitoring."""
        if service_type not in self._retry_stats:
            self._retry_stats[service_type] = {
                "success_count": 0,
                "failure_count": 0,
                "total_attempts": 0,
                "total_retries": 0
            }
        
        stats = self._retry_stats[service_type]
        
        if outcome == "success":
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1
        
        stats["total_attempts"] += attempts + 1  # +1 for initial attempt
        stats["total_retries"] += attempts
    
    def get_circuit_breaker_status(self, service_type: ServiceType) -> Dict[str, Any]:
        """Get current circuit breaker status for a service."""
        if service_type not in self._circuit_breakers:
            return {"state": "not_initialized"}
        
        circuit_breaker = self._circuit_breakers[service_type]
        current_time = time.time()
        
        status = {
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
            "success_count": circuit_breaker.success_count,
            "failure_threshold": circuit_breaker.failure_threshold,
        }
        
        if circuit_breaker.state == "open":
            time_until_recovery = circuit_breaker.recovery_timeout - (
                current_time - circuit_breaker.last_failure_time
            )
            status["time_until_recovery_seconds"] = max(0, time_until_recovery)
        elif circuit_breaker.state == "half_open":
            status["half_open_calls"] = circuit_breaker.half_open_calls
            status["half_open_max_calls"] = circuit_breaker.half_open_max_calls
        
        return status
    
    def get_retry_statistics(self, service_type: Optional[ServiceType] = None) -> Dict[str, Any]:
        """Get retry statistics for monitoring and debugging."""
        if service_type:
            return self._retry_stats.get(service_type, {})
        else:
            return {
                "environment": self.environment.value,
                "service_stats": self._retry_stats.copy(),
                "circuit_breaker_states": {
                    service.value: self.get_circuit_breaker_status(service)
                    for service in self._circuit_breakers.keys()
                }
            }
    
    def reset_circuit_breaker(self, service_type: ServiceType) -> bool:
        """Manually reset circuit breaker for a service (admin function)."""
        if service_type in self._circuit_breakers:
            circuit_breaker = self._circuit_breakers[service_type]
            circuit_breaker.state = "closed"
            circuit_breaker.failure_count = 0
            circuit_breaker.half_open_calls = 0
            self.logger.info(f"Circuit breaker manually reset for {service_type.value}")
            return True
        return False
    
    def configure_circuit_breaker(
        self,
        service_type: ServiceType,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[float] = None
    ) -> None:
        """Configure circuit breaker parameters for a service."""
        circuit_breaker = self._get_circuit_breaker(service_type)
        
        if failure_threshold is not None:
            circuit_breaker.failure_threshold = failure_threshold
        
        if recovery_timeout is not None:
            circuit_breaker.recovery_timeout = recovery_timeout
        
        self.logger.info(
            f"Circuit breaker configured for {service_type.value}: "
            f"threshold={circuit_breaker.failure_threshold}, "
            f"recovery_timeout={circuit_breaker.recovery_timeout}s"
        )