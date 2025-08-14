"""Agent reliability mixin providing comprehensive error recovery patterns.

This module provides a mixin class that can be inherited by agents to add
comprehensive error recovery, health monitoring, and resilience patterns.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.logging_config import central_logger
from .reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig, ErrorSeverity
)

logger = central_logger.get_logger(__name__)


@dataclass
class AgentError:
    """Represents an error that occurred during agent execution."""
    error_id: str
    agent_name: str
    operation: str
    error_type: str
    message: str
    timestamp: datetime
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class AgentHealthStatus:
    """Comprehensive health status for an agent."""
    agent_name: str
    overall_health: float  # 0.0 to 1.0
    circuit_breaker_state: str
    recent_errors: int
    total_operations: int
    success_rate: float
    average_response_time: float
    last_error: Optional[AgentError] = None
    status: str = "healthy"  # healthy, degraded, unhealthy


class AgentReliabilityMixin:
    """Mixin providing comprehensive reliability features for agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get agent name from self.name or class name
        agent_name = getattr(self, 'name', self.__class__.__name__)
        
        # Initialize reliability wrapper with agent-specific configuration
        self.reliability = get_reliability_wrapper(
            agent_name,
            self._get_circuit_breaker_config(),
            self._get_retry_config()
        )
        
        # Error tracking
        self.error_history: List[AgentError] = []
        self.max_error_history = 50
        
        # Performance tracking
        self.operation_times: List[float] = []
        self.max_operation_history = 100
        
        # Health monitoring
        self.last_health_check = time.time()
        self.health_check_interval = 60  # seconds
        
        # Recovery strategies
        self.recovery_strategies: Dict[str, Callable] = {}
        self._register_default_recovery_strategies()
    
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
        
        try:
            result = await self.reliability.execute_safely(
                operation,
                operation_name,
                fallback=fallback,
                timeout=timeout or 30.0
            )
            
            # Record successful operation
            execution_time = time.time() - start_time
            self._record_successful_operation(operation_name, execution_time)
            
            return result
            
        except Exception as e:
            # Record failed operation
            execution_time = time.time() - start_time
            await self._record_failed_operation(operation_name, e, execution_time, context)
            
            # Attempt recovery if strategy exists
            recovery_result = await self._attempt_operation_recovery(
                operation_name, e, context
            )
            
            if recovery_result is not None:
                return recovery_result
            
            # Re-raise if no recovery
            raise e
    
    async def _record_failed_operation(
        self,
        operation_name: str,
        error: Exception,
        execution_time: float,
        context: Optional[Dict[str, Any]]
    ):
        """Record a failed operation for monitoring."""
        error_record = AgentError(
            error_id=f"{int(time.time() * 1000)}_{len(self.error_history)}",
            agent_name=getattr(self, 'name', self.__class__.__name__),
            operation=operation_name,
            error_type=type(error).__name__,
            message=str(error),
            timestamp=datetime.utcnow(),
            severity=self._classify_error_severity(error),
            context=context or {}
        )
        
        self.error_history.append(error_record)
        
        # Keep history size manageable
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]\n        \n        # Log error with appropriate level\n        self._log_error(error_record)\n    \n    def _record_successful_operation(self, operation_name: str, execution_time: float):\n        \"\"\"Record a successful operation for monitoring.\"\"\"\n        self.operation_times.append(execution_time)\n        \n        # Keep history size manageable\n        if len(self.operation_times) > self.max_operation_history:\n            self.operation_times = self.operation_times[-self.max_operation_history:]\n    \n    def _classify_error_severity(self, error: Exception) -> ErrorSeverity:\n        \"\"\"Classify error severity based on error type.\"\"\"\n        # Critical errors that require immediate attention\n        critical_errors = [\n            \"SystemExit\", \"KeyboardInterrupt\", \"MemoryError\",\n            \"OutOfMemoryError\", \"RecursionError\"\n        ]\n        \n        # High severity errors that indicate serious problems\n        high_errors = [\n            \"ConnectionError\", \"TimeoutError\", \"DatabaseError\",\n            \"AuthenticationError\", \"PermissionError\"\n        ]\n        \n        # Medium severity errors that may be transient\n        medium_errors = [\n            \"HTTPError\", \"RequestException\", \"ValidationError\",\n            \"ConfigurationError\", \"ServiceUnavailableError\"\n        ]\n        \n        error_type = type(error).__name__\n        \n        if error_type in critical_errors:\n            return ErrorSeverity.CRITICAL\n        elif error_type in high_errors:\n            return ErrorSeverity.HIGH\n        elif error_type in medium_errors:\n            return ErrorSeverity.MEDIUM\n        else:\n            return ErrorSeverity.LOW\n    \n    def _log_error(self, error_record: AgentError):\n        \"\"\"Log error with appropriate level.\"\"\"\n        log_message = f\"Agent {error_record.agent_name} operation {error_record.operation} failed: {error_record.message}\"\n        \n        log_context = {\n            \"error_id\": error_record.error_id,\n            \"agent_name\": error_record.agent_name,\n            \"operation\": error_record.operation,\n            \"error_type\": error_record.error_type,\n            \"severity\": error_record.severity.value,\n            \"context\": error_record.context\n        }\n        \n        if error_record.severity == ErrorSeverity.CRITICAL:\n            logger.critical(log_message, extra=log_context)\n        elif error_record.severity == ErrorSeverity.HIGH:\n            logger.error(log_message, extra=log_context)\n        elif error_record.severity == ErrorSeverity.MEDIUM:\n            logger.warning(log_message, extra=log_context)\n        else:\n            logger.info(log_message, extra=log_context)\n    \n    async def _attempt_operation_recovery(\n        self,\n        operation_name: str,\n        error: Exception,\n        context: Optional[Dict[str, Any]]\n    ) -> Any:\n        \"\"\"Attempt to recover from operation failure.\"\"\"\n        # Check if we have a specific recovery strategy\n        if operation_name in self.recovery_strategies:\n            try:\n                logger.info(f\"Attempting recovery for operation {operation_name}\")\n                recovery_result = await self.recovery_strategies[operation_name](error, context)\n                \n                # Update error record if recovery successful\n                if self.error_history:\n                    self.error_history[-1].recovery_attempted = True\n                    self.error_history[-1].recovery_successful = True\n                \n                return recovery_result\n                \n            except Exception as recovery_error:\n                logger.error(f\"Recovery failed for operation {operation_name}: {recovery_error}\")\n                \n                # Update error record\n                if self.error_history:\n                    self.error_history[-1].recovery_attempted = True\n                    self.error_history[-1].recovery_successful = False\n        \n        return None\n    \n    def register_recovery_strategy(\n        self,\n        operation_name: str,\n        recovery_function: Callable[[Exception, Optional[Dict[str, Any]]], Awaitable[Any]]\n    ):\n        \"\"\"Register a recovery strategy for a specific operation.\"\"\"\n        self.recovery_strategies[operation_name] = recovery_function\n        logger.debug(f\"Registered recovery strategy for operation: {operation_name}\")\n    \n    def _register_default_recovery_strategies(self):\n        \"\"\"Register default recovery strategies.\"\"\"\n        # Default timeout recovery\n        async def timeout_recovery(error: Exception, context: Optional[Dict[str, Any]]) -> Any:\n            if isinstance(error, asyncio.TimeoutError):\n                logger.info(\"Attempting timeout recovery with reduced scope\")\n                # Return minimal result for timeout\n                return {\"status\": \"partial\", \"error\": \"Operation timed out\", \"recovery\": True}\n            raise error\n        \n        # Default connection recovery\n        async def connection_recovery(error: Exception, context: Optional[Dict[str, Any]]) -> Any:\n            if \"connection\" in str(error).lower():\n                logger.info(\"Attempting connection recovery\")\n                # Wait briefly and return connection error status\n                await asyncio.sleep(1)\n                return {\"status\": \"connection_failed\", \"recovery\": True}\n            raise error\n        \n        # Register default strategies\n        self.recovery_strategies[\"timeout\"] = timeout_recovery\n        self.recovery_strategies[\"connection\"] = connection_recovery\n    \n    def get_health_status(self) -> AgentHealthStatus:\n        \"\"\"Get comprehensive health status for this agent.\"\"\"\n        now = time.time()\n        \n        # Get reliability stats\n        reliability_stats = self.reliability.get_health_status()\n        \n        # Calculate recent errors (last 5 minutes)\n        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)\n        recent_errors = sum(\n            1 for error in self.error_history \n            if error.timestamp > recent_cutoff\n        )\n        \n        # Calculate average response time\n        avg_response_time = (\n            sum(self.operation_times) / len(self.operation_times)\n            if self.operation_times else 0.0\n        )\n        \n        # Get circuit breaker status\n        cb_status = self.reliability.circuit_breaker.get_status()\n        \n        # Calculate overall health\n        health_score = reliability_stats[\"health_score\"]\n        \n        # Determine status\n        if health_score > 0.8:\n            status = \"healthy\"\n        elif health_score > 0.5:\n            status = \"degraded\"\n        else:\n            status = \"unhealthy\"\n        \n        return AgentHealthStatus(\n            agent_name=getattr(self, 'name', self.__class__.__name__),\n            overall_health=health_score,\n            circuit_breaker_state=cb_status[\"state\"],\n            recent_errors=recent_errors,\n            total_operations=cb_status[\"metrics\"][\"total_calls\"],\n            success_rate=cb_status[\"metrics\"][\"success_rate\"],\n            average_response_time=avg_response_time,\n            last_error=self.error_history[-1] if self.error_history else None,\n            status=status\n        )\n    \n    def get_error_summary(self) -> Dict[str, Any]:\n        \"\"\"Get summary of recent errors.\"\"\"\n        if not self.error_history:\n            return {\"total_errors\": 0, \"error_types\": {}, \"severity_breakdown\": {}}\n        \n        # Count error types\n        error_types = {}\n        severity_breakdown = {}\n        \n        for error in self.error_history:\n            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1\n            severity_breakdown[error.severity.value] = severity_breakdown.get(error.severity.value, 0) + 1\n        \n        return {\n            \"total_errors\": len(self.error_history),\n            \"error_types\": error_types,\n            \"severity_breakdown\": severity_breakdown,\n            \"recent_errors\": [\n                {\n                    \"error_id\": error.error_id,\n                    \"operation\": error.operation,\n                    \"error_type\": error.error_type,\n                    \"message\": error.message,\n                    \"timestamp\": error.timestamp.isoformat(),\n                    \"severity\": error.severity.value,\n                    \"recovery_attempted\": error.recovery_attempted,\n                    \"recovery_successful\": error.recovery_successful\n                }\n                for error in self.error_history[-10:]  # Last 10 errors\n            ]\n        }\n    \n    async def perform_health_check(self) -> bool:\n        \"\"\"Perform a health check for this agent.\"\"\"\n        if time.time() - self.last_health_check < self.health_check_interval:\n            return True  # Skip if checked recently\n        \n        try:\n            # Basic health check - can be overridden by subclasses\n            health_status = self.get_health_status()\n            \n            self.last_health_check = time.time()\n            \n            # Log health status if degraded\n            if health_status.status != \"healthy\":\n                logger.warning(\n                    f\"Agent {health_status.agent_name} health check: {health_status.status} \"\n                    f\"(health score: {health_status.overall_health:.2f})\"\n                )\n            \n            return health_status.status != \"unhealthy\"\n            \n        except Exception as e:\n            logger.error(f\"Health check failed for agent {getattr(self, 'name', self.__class__.__name__)}: {e}\")\n            return False\n    \n    def reset_health_metrics(self):\n        \"\"\"Reset health metrics (useful for testing or after recovery).\"\"\"\n        self.error_history.clear()\n        self.operation_times.clear()\n        logger.info(f\"Reset health metrics for agent {getattr(self, 'name', self.__class__.__name__)}\")