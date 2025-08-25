"""Agent reliability mixin providing comprehensive error recovery patterns.

This module provides a mixin class that can be inherited by agents to add
comprehensive error recovery, health monitoring, and resilience patterns.
"""

import time
from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.core.error_handlers.agents.agent_error_handler import AgentErrorHandler
from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor
from netra_backend.app.core.agent_recovery import AgentRecoveryManager
from netra_backend.app.core.agent_reliability_types import AgentHealthStatus
from netra_backend.app.core.reliability import (
    CircuitBreakerConfig,
    RetryConfig,
    get_reliability_wrapper,
)


class AgentReliabilityMixin:
    """Mixin providing comprehensive reliability features for agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        agent_name = self._get_agent_name()
        self._initialize_reliability(agent_name)
        self._initialize_components()

    def _get_agent_name(self) -> str:
        """Get agent name from self.name or class name."""
        return getattr(self, 'name', self.__class__.__name__)

    def _initialize_reliability(self, agent_name: str) -> None:
        """Initialize reliability wrapper with agent-specific configuration."""
        self.reliability = get_reliability_wrapper(
            agent_name,
            self._get_circuit_breaker_config(),
            self._get_retry_config()
        )

    def _initialize_components(self) -> None:
        """Initialize reliability components."""
        self.error_handler = AgentErrorHandler()
        self.health_monitor = AgentHealthMonitor()
        self.recovery_manager = AgentRecoveryManager()
        
        # Initialize additional expected attributes
        self.max_error_history = 50
        self.max_operation_history = 100 
        self.health_check_interval = 60
        self.recovery_strategies = {
            "llm_call": self._default_recovery_strategy,
            "database_query": self._default_recovery_strategy,
            "api_call": self._default_recovery_strategy
        }
    
    def _default_recovery_strategy(self, *args, **kwargs):
        """Default recovery strategy that does nothing but doesn't raise errors."""
        return None
    
    def _record_successful_operation(self, operation_name: str, execution_time: float):
        """Record a successful operation for monitoring."""
        self.health_monitor.record_successful_operation(operation_name, execution_time)
    
    async def _attempt_operation_recovery(self, operation_name: str, error: Exception, context: dict):
        """Attempt recovery for a failed operation."""
        return await self.recovery_manager.attempt_operation_recovery(
            operation_name, error, context, self.error_history
        )
    
    def _get_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Get circuit breaker configuration for this agent."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            name=getattr(self, 'name', self.__class__.__name__)
        )
    
    def _get_retry_config(self) -> RetryConfig:
        """Get retry configuration for this agent."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0
        )
    
    async def execute_with_reliability(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]] = None,
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute operation with full reliability protection."""
        start_time = time.time()
        return await self._execute_with_error_handling(
            operation, operation_name, fallback, timeout, start_time, context
        )

    async def _execute_with_error_handling(
        self, operation: Callable[[], Awaitable[Any]], operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]], timeout: Optional[float],
        start_time: float, context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute operation with error handling and fallback."""
        try:
            return await self._execute_operation_safely(
                operation, operation_name, fallback, timeout, start_time
            )
        except Exception as e:
            return await self._handle_operation_failure(
                operation_name, e, start_time, context
            )

    async def _execute_operation_safely(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]],
        timeout: Optional[float],
        start_time: float
    ) -> Any:
        """Execute operation safely and record success."""
        result = await self.reliability.execute_safely(
            operation, operation_name, fallback=fallback, timeout=timeout or 30.0
        )
        execution_time = time.time() - start_time
        self.health_monitor.record_successful_operation(operation_name, execution_time)
        return result

    async def _handle_operation_failure(
        self,
        operation_name: str,
        error: Exception,
        start_time: float,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Handle operation failure with recording and recovery."""
        await self._record_operation_failure(operation_name, error, start_time, context)
        return await self._attempt_recovery_or_reraise(operation_name, error, context)

    async def _record_operation_failure(
        self, operation_name: str, error: Exception, start_time: float, context: Optional[Dict[str, Any]]
    ) -> None:
        """Record the failed operation for monitoring."""
        execution_time = time.time() - start_time
        agent_name = self._get_agent_name()
        await self.error_handler.record_failed_operation(
            operation_name, error, execution_time, context, agent_name
        )

    async def _attempt_recovery_or_reraise(
        self, operation_name: str, error: Exception, context: Optional[Dict[str, Any]]
    ) -> Any:
        """Attempt recovery or re-raise the original error."""
        recovery_result = await self.recovery_manager.attempt_operation_recovery(
            operation_name, error, context, self.error_handler.error_history
        )
        if recovery_result is not None:
            return recovery_result
        raise error

    def register_recovery_strategy(
        self,
        operation_name: str,
        recovery_func: Callable[[Exception, Optional[Dict[str, Any]]], Awaitable[Optional[Any]]]
    ) -> None:
        """Register a recovery strategy for a specific operation."""
        self.recovery_manager.register_recovery_strategy(operation_name, recovery_func)
        # Also update the local recovery_strategies dict for test compatibility
        self.recovery_strategies[operation_name] = recovery_func

    def get_comprehensive_health_status(self) -> AgentHealthStatus:
        """Get comprehensive health status of the agent."""
        agent_name = self._get_agent_name()
        return self.health_monitor.get_comprehensive_health_status(
            agent_name, self.error_handler.error_history, self.reliability
        )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        return self.health_monitor.get_error_summary(self.error_handler.error_history)

    def reset_health_metrics(self) -> None:
        """Reset health metrics and error history."""
        self.error_handler.error_history.clear()
        self.health_monitor.reset_health_metrics(self.reliability)

    async def perform_health_check(self) -> AgentHealthStatus:
        """Perform comprehensive health check."""
        agent_name = self._get_agent_name()
        return await self.health_monitor.perform_health_check(
            agent_name, self.error_handler.error_history, self.reliability
        )

    def should_perform_health_check(self) -> bool:
        """Check if health check should be performed."""
        return self.health_monitor.should_perform_health_check()

    # Convenience properties for backward compatibility
    @property  
    def error_history(self):
        """Get error history from error handler."""
        return self.error_handler.error_history if hasattr(self, 'error_handler') else []
        
    @error_history.setter
    def error_history(self, value):
        """Set error history on the error handler."""
        if hasattr(self, 'error_handler'):
            self.error_handler.error_history = value

    @property
    def operation_times(self):
        """Get operation times from health monitor."""
        return self.health_monitor.operation_times if hasattr(self, 'health_monitor') else []