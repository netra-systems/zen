"""Comprehensive reliability infrastructure for Netra agents.

This module provides circuit breakers, retry logic, error recovery, and 
monitoring capabilities for all agent operations.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union
from datetime import datetime, timedelta
import random
import logging

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    name: str = "default"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class ReliabilityMetrics:
    """Metrics for reliability monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_breaker_opens: int = 0
    recovery_attempts: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    error_types: Dict[str, int] = field(default_factory=dict)


class CircuitBreaker:
    """Enhanced circuit breaker with metrics and logging"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.metrics = ReliabilityMetrics()
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
                return True
            return False
        else:  # HALF_OPEN
            return self.half_open_calls < self.config.half_open_max_calls
    
    def record_success(self) -> None:
        """Record successful execution"""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_closed()
        self.failure_count = 0
        self.last_failure_time = None
    
    def record_failure(self, error_type: str = "unknown") -> None:
        """Record failed execution"""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = time.time()
        self.metrics.error_types[error_type] = self.metrics.error_types.get(error_type, 0) + 1
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
        elif self.failure_count >= self.config.failure_threshold:
            self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if recovery timeout has passed"""
        if not self.last_failure_time:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        if self.state != CircuitBreakerState.OPEN:
            logger.warning(f"Circuit breaker {self.config.name} OPENED after {self.failure_count} failures")
            self.metrics.circuit_breaker_opens += 1
        self.state = CircuitBreakerState.OPEN
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        logger.info(f"Circuit breaker {self.config.name} attempting recovery (HALF_OPEN)")
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_calls = 0
        self.metrics.recovery_attempts += 1
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        logger.info(f"Circuit breaker {self.config.name} recovered (CLOSED)")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "half_open_max_calls": self.config.half_open_max_calls
            },
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "success_rate": (
                    self.metrics.successful_calls / self.metrics.total_calls 
                    if self.metrics.total_calls > 0 else 0
                ),
                "circuit_breaker_opens": self.metrics.circuit_breaker_opens,
                "recovery_attempts": self.metrics.recovery_attempts,
                "error_types": self.metrics.error_types
            }
        }


class RetryHandler:
    """Exponential backoff retry handler with jitter"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute_with_retry(
        self, 
        func: Callable[[], Awaitable[Any]], 
        operation_name: str = "operation",
        error_classifier: Optional[Callable[[Exception], bool]] = None
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this error
                if error_classifier and not error_classifier(e):
                    logger.warning(f"{operation_name}: Non-retryable error on attempt {attempt + 1}: {e}")
                    raise e
                
                if attempt == self.config.max_retries:
                    logger.error(f"{operation_name}: Final attempt {attempt + 1} failed: {e}")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"{operation_name}: Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add up to 25% jitter
            jitter = delay * 0.25 * random.random()
            delay += jitter
        
        return delay


class AgentReliabilityWrapper:
    """Comprehensive reliability wrapper for agent operations"""
    
    def __init__(
        self, 
        agent_name: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        self.agent_name = agent_name
        
        # Initialize circuit breaker
        cb_config = circuit_breaker_config or CircuitBreakerConfig(name=agent_name)
        self.circuit_breaker = CircuitBreaker(cb_config)
        
        # Initialize retry handler
        self.retry_handler = RetryHandler(retry_config or RetryConfig())
        
        # Error tracking
        self.error_history: List[Dict[str, Any]] = []
        self.max_error_history = 100
    
    async def execute_safely(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """Execute operation with full reliability protection"""
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            error_msg = f"{self.agent_name}.{operation_name}: Circuit breaker is OPEN"
            logger.warning(error_msg)
            
            if fallback:
                logger.info(f"{self.agent_name}.{operation_name}: Using fallback operation")
                return await self._execute_fallback(fallback, operation_name)
            
            raise RuntimeError(error_msg)
        
        try:
            # Execute with timeout and retry
            async def wrapped_operation():
                if timeout:
                    return await asyncio.wait_for(operation(), timeout=timeout)
                return await operation()
            
            result = await self.retry_handler.execute_with_retry(
                wrapped_operation,
                f"{self.agent_name}.{operation_name}",
                self._should_retry_error
            )
            
            # Record success
            self.circuit_breaker.record_success()
            return result
            
        except Exception as e:
            # Record failure
            error_type = type(e).__name__
            self.circuit_breaker.record_failure(error_type)
            
            # Track error
            self._track_error(operation_name, e)
            
            # Try fallback if available
            if fallback:
                logger.warning(f"{self.agent_name}.{operation_name}: Primary operation failed, trying fallback: {e}")
                try:
                    return await self._execute_fallback(fallback, operation_name)
                except Exception as fallback_error:
                    logger.error(f"{self.agent_name}.{operation_name}: Fallback also failed: {fallback_error}")
                    raise fallback_error
            
            # Re-raise original error
            raise e
    
    async def _execute_fallback(self, fallback: Callable[[], Awaitable[Any]], operation_name: str) -> Any:
        """Execute fallback operation"""
        try:
            return await fallback()
        except Exception as e:
            self._track_error(f"{operation_name}_fallback", e)
            raise
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried"""
        # Don't retry validation errors or client errors
        non_retryable = [
            "ValidationError", "ValueError", "TypeError", 
            "KeyError", "AttributeError", "NotImplementedError"
        ]
        
        error_type = type(error).__name__
        return error_type not in non_retryable
    
    def _track_error(self, operation_name: str, error: Exception) -> None:
        """Track error for monitoring"""
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "agent": self.agent_name
        }
        
        self.error_history.append(error_info)
        
        # Keep history size manageable
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        cb_status = self.circuit_breaker.get_status()
        
        recent_errors = [
            e for e in self.error_history 
            if datetime.fromisoformat(e["timestamp"]) > datetime.utcnow() - timedelta(minutes=5)
        ]
        
        return {
            "agent_name": self.agent_name,
            "circuit_breaker": cb_status,
            "recent_errors": len(recent_errors),
            "total_tracked_errors": len(self.error_history),
            "last_error": self.error_history[-1] if self.error_history else None,
            "health_score": self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate health score (0-1)"""
        metrics = self.circuit_breaker.metrics
        
        if metrics.total_calls == 0:
            return 1.0
        
        success_rate = metrics.successful_calls / metrics.total_calls
        
        # Penalize for circuit breaker opens
        cb_penalty = min(0.2 * metrics.circuit_breaker_opens, 0.5)
        
        # Penalize for recent errors
        recent_errors = [
            e for e in self.error_history 
            if datetime.fromisoformat(e["timestamp"]) > datetime.utcnow() - timedelta(minutes=5)
        ]
        error_penalty = min(0.1 * len(recent_errors), 0.3)
        
        return max(0.0, success_rate - cb_penalty - error_penalty)


# Global registry for reliability wrappers
_reliability_registry: Dict[str, AgentReliabilityWrapper] = {}


def get_reliability_wrapper(
    agent_name: str,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    retry_config: Optional[RetryConfig] = None
) -> AgentReliabilityWrapper:
    """Get or create reliability wrapper for agent"""
    if agent_name not in _reliability_registry:
        _reliability_registry[agent_name] = AgentReliabilityWrapper(
            agent_name, circuit_breaker_config, retry_config
        )
    return _reliability_registry[agent_name]


def get_system_health() -> Dict[str, Any]:
    """Get system-wide health status"""
    return {
        "agents": {
            name: wrapper.get_health_status() 
            for name, wrapper in _reliability_registry.items()
        },
        "total_agents": len(_reliability_registry),
        "healthy_agents": sum(
            1 for wrapper in _reliability_registry.values() 
            if wrapper._calculate_health_score() > 0.8
        )
    }