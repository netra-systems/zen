"""Comprehensive reliability infrastructure for Netra agents.

 WARNING: [U+FE0F]  MIGRATION TO UNIFIED RELIABILITY MANAGER  WARNING: [U+FE0F]

This module is being migrated to use UnifiedReliabilityManager as the SSOT.
The AgentReliabilityWrapper class now delegates to the unified implementation
while maintaining backward compatibility.

For new code, use:
    from netra_backend.app.core.reliability.unified_reliability_manager import get_reliability_manager

This module provides the main reliability wrapper and system-wide
health monitoring capabilities for all agent operations.
"""

import asyncio
import time
import warnings
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.circuit_breaker import CircuitConfig as CircuitBreakerConfig
from netra_backend.app.core.circuit_breaker import CircuitMetrics as ReliabilityMetrics
from netra_backend.app.core.circuit_breaker import CircuitState as CircuitBreakerState
from netra_backend.app.core.reliability_retry import RetryConfig, RetryHandler
from netra_backend.app.logging_config import central_logger

# Import unified reliability manager
from netra_backend.app.core.reliability.unified_reliability_manager import get_reliability_manager

logger = central_logger.get_logger(__name__)


class AgentReliabilityWrapper:
    """Comprehensive reliability wrapper for agent operations
    
     WARNING: [U+FE0F]  DEPRECATED: This class now delegates to UnifiedReliabilityManager.
    Use get_reliability_manager() directly for new code.
    """
    
    def __init__(
        self, 
        agent_name: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        warnings.warn(
            "AgentReliabilityWrapper is deprecated. Use UnifiedReliabilityManager via "
            "get_reliability_manager() for better functionality and WebSocket integration.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.agent_name = agent_name
        
        # Convert legacy retry config to unified format if provided
        if retry_config is None:
            from netra_backend.app.schemas.shared_types import RetryConfig as UnifiedRetryConfig
            retry_config = UnifiedRetryConfig()
        elif hasattr(retry_config, 'max_retries'):
            # Convert old-style RetryConfig to new format
            from netra_backend.app.schemas.shared_types import RetryConfig as UnifiedRetryConfig
            retry_config = UnifiedRetryConfig(
                max_retries=retry_config.max_retries,
                base_delay=retry_config.base_delay,
                max_delay=retry_config.max_delay,
                timeout_seconds=retry_config.timeout
            )
        
        # Get unified manager instance
        self._unified_manager = get_reliability_manager(
            service_name=agent_name,
            retry_config=retry_config
        )
        
        # Keep legacy setup for compatibility
        self._setup_reliability_components(circuit_breaker_config, retry_config)
        
        logger.info(f"Created AgentReliabilityWrapper adapter for {agent_name} - consider migrating to UnifiedReliabilityManager")
    
    def _setup_reliability_components(
        self, 
        circuit_breaker_config: Optional[CircuitBreakerConfig],
        retry_config: Optional[RetryConfig]
    ) -> None:
        """Setup reliability components and error tracking"""
        self._initialize_components(circuit_breaker_config, retry_config)
        self._initialize_error_tracking()
    
    def _initialize_components(
        self, 
        circuit_breaker_config: Optional[CircuitBreakerConfig],
        retry_config: Optional[RetryConfig]
    ) -> None:
        """Initialize circuit breaker and retry handler"""
        cb_config = self._get_circuit_breaker_config(circuit_breaker_config)
        self.circuit_breaker = CircuitBreaker(cb_config)
        self.retry_handler = RetryHandler(retry_config or RetryConfig())
    
    def _get_circuit_breaker_config(
        self, 
        circuit_breaker_config: Optional[CircuitBreakerConfig]
    ) -> CircuitBreakerConfig:
        """Get circuit breaker configuration"""
        return circuit_breaker_config or CircuitBreakerConfig(name=self.agent_name)
    
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
        # Delegate to unified manager for enhanced functionality
        return await self._unified_manager.execute_with_reliability(
            operation=operation,
            operation_name=operation_name,
            fallback=fallback,
            timeout=timeout,
            emit_events=False  # Legacy mode doesn't emit WebSocket events by default
        )
    
    async def _execute_with_circuit_breaker_check(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]],
        timeout: Optional[float]
    ) -> Any:
        """Execute operation after checking circuit breaker"""
        if not await self.circuit_breaker.can_execute_async():
            return await self._handle_circuit_breaker_open(operation_name, fallback)
        return await self._try_execute_operation(operation, operation_name, fallback, timeout)
    
    async def _try_execute_operation(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]],
        timeout: Optional[float]
    ) -> Any:
        """Try to execute operation with error handling"""
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
        error_msg = self._create_circuit_breaker_error_message(operation_name)
        logger.warning(error_msg)
        return await self._try_fallback_for_open_circuit(operation_name, fallback, error_msg)
    
    def _create_circuit_breaker_error_message(self, operation_name: str) -> str:
        """Create error message for open circuit breaker"""
        return f"{self.agent_name}.{operation_name}: Circuit breaker is OPEN"
    
    async def _try_fallback_for_open_circuit(
        self, 
        operation_name: str, 
        fallback: Optional[Callable[[], Awaitable[Any]]],
        error_msg: str
    ) -> Any:
        """Try fallback for open circuit or raise error"""
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
        self._record_successful_execution()
        return result
    
    def _record_successful_execution(self) -> None:
        """Record successful execution in circuit breaker"""
        self.circuit_breaker.record_success()
    
    async def _execute_with_protection(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        operation_name: str, 
        timeout: Optional[float]
    ) -> Any:
        """Execute operation with timeout and retry protection"""
        wrapped_operation = self._create_wrapped_operation(operation, timeout)
        operation_id = self._create_operation_id(operation_name)
        return await self.retry_handler.execute_with_retry(
            wrapped_operation, operation_id, self._should_retry_error
        )
    
    def _create_operation_id(self, operation_name: str) -> str:
        """Create unique operation identifier"""
        return f"{self.agent_name}.{operation_name}"
    
    def _create_wrapped_operation(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        timeout: Optional[float]
    ) -> Callable[[], Awaitable[Any]]:
        """Create wrapped operation with timeout"""
        if timeout:
            return self._create_timeout_wrapped_operation(operation, timeout)
        return operation
    
    def _create_timeout_wrapped_operation(
        self, 
        operation: Callable[[], Awaitable[Any]], 
        timeout: float
    ) -> Callable[[], Awaitable[Any]]:
        """Create operation wrapped with timeout"""
        async def wrapped_operation():
            return await asyncio.wait_for(operation(), timeout=timeout)
        return wrapped_operation
    
    async def _handle_operation_failure(
        self, 
        error: Exception, 
        operation_name: str, 
        fallback: Optional[Callable[[], Awaitable[Any]]]
    ) -> Any:
        """Handle operation failure with circuit breaker and fallback"""
        self._record_operation_failure(error, operation_name)
        return await self._try_fallback_or_raise(error, operation_name, fallback)
    
    def _record_operation_failure(self, error: Exception, operation_name: str) -> None:
        """Record operation failure in monitoring systems"""
        error_type = type(error).__name__
        self.circuit_breaker.record_failure(error_type)
        self._track_error(operation_name, error)
    
    async def _try_fallback_or_raise(
        self, 
        error: Exception, 
        operation_name: str, 
        fallback: Optional[Callable[[], Awaitable[Any]]]
    ) -> Any:
        """Try fallback operation or raise original error"""
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
        return await self._execute_fallback_with_error_handling(
            fallback, operation_name
        )
    
    async def _execute_fallback_with_error_handling(
        self, 
        fallback: Callable[[], Awaitable[Any]], 
        operation_name: str
    ) -> Any:
        """Execute fallback with proper error handling"""
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
            self._handle_fallback_error(operation_name, e)
    
    def _handle_fallback_error(self, operation_name: str, error: Exception) -> None:
        """Handle fallback execution error"""
        fallback_operation_name = f"{operation_name}_fallback"
        self._track_error(fallback_operation_name, error)
        raise error
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried"""
        non_retryable = self._get_non_retryable_error_types()
        error_type = type(error).__name__
        return error_type not in non_retryable
    
    def _get_non_retryable_error_types(self) -> set[str]:
        """Get set of non-retryable error types"""
        return {
            "ValidationError", "ValueError", "TypeError", 
            "KeyError", "AttributeError", "NotImplementedError",
            "PermissionError", "FileNotFoundError", "ImportError"
        }
    
    def _track_error(self, operation_name: str, error: Exception) -> None:
        """Track error for monitoring"""
        error_info = self._create_error_info(operation_name, error)
        self.error_history.append(error_info)
        self._maintain_error_history_size()
    
    def _create_error_info(self, operation_name: str, error: Exception) -> Dict[str, Any]:
        """Create error information dictionary"""
        timestamp = datetime.now(UTC).isoformat()
        error_type = type(error).__name__
        error_message = str(error)
        return self._build_error_info_dict(
            timestamp, operation_name, error_type, error_message
        )
    
    def _build_error_info_dict(
        self, 
        timestamp: str, 
        operation_name: str, 
        error_type: str, 
        error_message: str
    ) -> Dict[str, Any]:
        """Build error information dictionary"""
        return {
            "timestamp": timestamp,
            "operation": operation_name,
            "error_type": error_type,
            "error_message": error_message,
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
        last_error = self._get_last_error_info()
        health_score = self._calculate_health_score()
        return self._create_health_status_dict(
            cb_status, recent_errors, last_error, health_score
        )
    
    def _get_last_error_info(self) -> Optional[Dict[str, Any]]:
        """Get last error information if available"""
        return self.error_history[-1] if self.error_history else None
    
    def _create_health_status_dict(
        self, 
        cb_status: Dict[str, Any], 
        recent_errors: List[Dict[str, Any]], 
        last_error: Optional[Dict[str, Any]], 
        health_score: float
    ) -> Dict[str, Any]:
        """Create complete health status dictionary"""
        return {
            "agent_name": self.agent_name,
            "circuit_breaker": cb_status,
            "recent_errors": len(recent_errors),
            "total_tracked_errors": len(self.error_history),
            "last_error": last_error,
            "health_score": health_score
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
        return self._calculate_score_with_penalties(metrics)
    
    def _calculate_score_with_penalties(self, metrics: ReliabilityMetrics) -> float:
        """Calculate health score with penalties applied"""
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
        _create_and_register_wrapper(agent_name, circuit_breaker_config, retry_config)
    return _reliability_registry[agent_name]


def _create_and_register_wrapper(
    agent_name: str,
    circuit_breaker_config: Optional[CircuitBreakerConfig],
    retry_config: Optional[RetryConfig]
) -> None:
    """Create and register new reliability wrapper"""
    _reliability_registry[agent_name] = AgentReliabilityWrapper(
        agent_name, circuit_breaker_config, retry_config
    )


def get_system_health() -> Dict[str, Any]:
    """Get system-wide health status"""
    agent_health_data = _collect_agent_health_data()
    healthy_count = _count_healthy_agents()
    return _build_system_health_dict(agent_health_data, healthy_count)


def _collect_agent_health_data() -> Dict[str, Dict[str, Any]]:
    """Collect health data from all registered agents"""
    return {
        name: wrapper.get_health_status() 
        for name, wrapper in _reliability_registry.items()
    }


def _build_system_health_dict(
    agent_health_data: Dict[str, Dict[str, Any]], 
    healthy_count: int
) -> Dict[str, Any]:
    """Build system health status dictionary"""
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