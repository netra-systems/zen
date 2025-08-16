"""Comprehensive reliability infrastructure for Netra agents.

This module provides the main reliability wrapper and system-wide
health monitoring capabilities for all agent operations.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime, timedelta, UTC

from app.logging_config import central_logger
from .circuit_breaker import CircuitBreaker, CircuitConfig as CircuitBreakerConfig, CircuitState as CircuitBreakerState, CircuitMetrics as ReliabilityMetrics
from .reliability_retry import RetryHandler, RetryConfig

logger = central_logger.get_logger(__name__)


class AgentReliabilityWrapper:
    """Comprehensive reliability wrapper for agent operations"""
    
    def __init__(
        self, 
        agent_name: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        self.agent_name = agent_name
        self._initialize_components(circuit_breaker_config, retry_config)
        self._initialize_error_tracking()
    
    def _initialize_components(
        self, 
        circuit_breaker_config: Optional[CircuitBreakerConfig],
        retry_config: Optional[RetryConfig]
    ) -> None:
        """Initialize circuit breaker and retry handler"""
        cb_config = circuit_breaker_config or CircuitBreakerConfig(name=self.agent_name)
        self.circuit_breaker = CircuitBreaker(cb_config)
        self.retry_handler = RetryHandler(retry_config or RetryConfig())
    
    def _initialize_error_tracking(self) -> None:
        """Initialize error tracking system"""
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
        if not await self.circuit_breaker.can_execute():
            return await self._handle_circuit_breaker_open(operation_name, fallback)
        
        try:
            return await self._execute_operation_successfully(
                operation, operation_name, timeout
            )
        except Exception as e:
            return await self._handle_operation_failure(
                e, operation_name, fallback
            )
    
    async def _handle_circuit_breaker_open(
        self, 
        operation_name: str, 
        fallback: Optional[Callable[[], Awaitable[Any]]]
    ) -> Any:
        """Handle execution when circuit breaker is open"""
        error_msg = f"{self.agent_name}.{operation_name}: Circuit breaker is OPEN"
        logger.warning(error_msg)
        
        if fallback:
            logger.info(f"{self.agent_name}.{operation_name}: Using fallback operation")
            return await self._execute_fallback(fallback, operation_name)
        
        raise RuntimeError(error_msg)
    
    async def _execute_operation_successfully(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        operation_name: str, 
        timeout: Optional[float]
    ) -> Any:
        """Execute operation successfully with protection"""
        result = await self._execute_with_protection(
            operation, operation_name, timeout
        )
        self.circuit_breaker.record_success()
        return result
    
    async def _execute_with_protection(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        operation_name: str, 
        timeout: Optional[float]
    ) -> Any:
        """Execute operation with timeout and retry protection"""
        wrapped_operation = self._create_wrapped_operation(operation, timeout)
        return await self.retry_handler.execute_with_retry(
            wrapped_operation,
            f"{self.agent_name}.{operation_name}",
            self._should_retry_error
        )
    
    def _create_wrapped_operation(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        timeout: Optional[float]
    ) -> Callable[[], Awaitable[Any]]:
        """Create wrapped operation with timeout"""
        async def wrapped_operation():
            if timeout:
                return await asyncio.wait_for(operation(), timeout=timeout)
            return await operation()
        return wrapped_operation
    
    async def _handle_operation_failure(
        self, 
        error: Exception, 
        operation_name: str, 
        fallback: Optional[Callable[[], Awaitable[Any]]]
    ) -> Any:
        """Handle operation failure with circuit breaker and fallback"""
        error_type = type(error).__name__
        self.circuit_breaker.record_failure(error_type)
        self._track_error(operation_name, error)
        
        if fallback:
            return await self._attempt_fallback(error, operation_name, fallback)
        
        raise error
    
    async def _attempt_fallback(
        self, 
        original_error: Exception, 
        operation_name: str, 
        fallback: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Attempt to execute fallback operation"""
        self._log_fallback_attempt(operation_name, original_error)
        try:
            return await self._execute_fallback(fallback, operation_name)
        except Exception as fallback_error:
            self._log_fallback_failure(operation_name, fallback_error)
            raise fallback_error
    
    def _log_fallback_attempt(self, operation_name: str, error: Exception) -> None:
        """Log fallback attempt"""
        logger.warning(
            f"{self.agent_name}.{operation_name}: Primary operation failed, "
            f"trying fallback: {error}"
        )
    
    def _log_fallback_failure(self, operation_name: str, error: Exception) -> None:
        """Log fallback failure"""
        logger.error(
            f"{self.agent_name}.{operation_name}: "
            f"Fallback also failed: {error}"
        )
    
    async def _execute_fallback(
        self, 
        fallback: Callable[[], Awaitable[Any]], 
        operation_name: str
    ) -> Any:
        """Execute fallback operation"""
        try:
            return await fallback()
        except Exception as e:
            self._track_error(f"{operation_name}_fallback", e)
            raise
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried"""
        non_retryable = {
            "ValidationError", "ValueError", "TypeError", 
            "KeyError", "AttributeError", "NotImplementedError",
            "PermissionError", "FileNotFoundError", "ImportError"
        }
        
        error_type = type(error).__name__
        return error_type not in non_retryable
    
    def _track_error(self, operation_name: str, error: Exception) -> None:
        """Track error for monitoring"""
        error_info = self._create_error_info(operation_name, error)
        self.error_history.append(error_info)
        self._maintain_error_history_size()
    
    def _create_error_info(self, operation_name: str, error: Exception) -> Dict[str, Any]:
        """Create error information dictionary"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": operation_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "agent": self.agent_name
        }
    
    def _maintain_error_history_size(self) -> None:
        """Keep error history size manageable"""
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        cb_status = self.circuit_breaker.get_status()
        recent_errors = self._get_recent_errors()
        return self._build_health_status_dict(cb_status, recent_errors)
    
    def _build_health_status_dict(
        self, 
        cb_status: Dict[str, Any], 
        recent_errors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build health status dictionary"""
        return {
            "agent_name": self.agent_name,
            "circuit_breaker": cb_status,
            "recent_errors": len(recent_errors),
            "total_tracked_errors": len(self.error_history),
            "last_error": self.error_history[-1] if self.error_history else None,
            "health_score": self._calculate_health_score()
        }
    
    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """Get errors from the last 5 minutes"""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=5)
        return [
            e for e in self.error_history 
            if datetime.fromisoformat(e["timestamp"]) > cutoff_time
        ]
    
    def _calculate_health_score(self) -> float:
        """Calculate health score (0-1)"""
        metrics = self.circuit_breaker.metrics
        if metrics.total_calls == 0:
            return 1.0
        
        success_rate = metrics.successful_calls / metrics.total_calls
        penalties = self._calculate_health_penalties(metrics)
        return max(0.0, success_rate - penalties)
    
    def _calculate_health_penalties(self, metrics: ReliabilityMetrics) -> float:
        """Calculate combined health penalties"""
        cb_penalty = self._calculate_circuit_breaker_penalty(metrics)
        error_penalty = self._calculate_error_penalty()
        return cb_penalty + error_penalty
    
    def _calculate_circuit_breaker_penalty(self, metrics: ReliabilityMetrics) -> float:
        """Calculate penalty for circuit breaker opens"""
        return min(0.2 * metrics.circuit_breaker_opens, 0.5)
    
    def _calculate_error_penalty(self) -> float:
        """Calculate penalty for recent errors"""
        recent_errors = self._get_recent_errors()
        return min(0.1 * len(recent_errors), 0.3)


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
    agent_health_data = {
        name: wrapper.get_health_status() 
        for name, wrapper in _reliability_registry.items()
    }
    
    healthy_count = _count_healthy_agents()
    
    return {
        "agents": agent_health_data,
        "total_agents": len(_reliability_registry),
        "healthy_agents": healthy_count
    }


def _count_healthy_agents() -> int:
    """Count agents with health score > 0.8"""
    return sum(
        1 for wrapper in _reliability_registry.values() 
        if wrapper._calculate_health_score() > 0.8
    )