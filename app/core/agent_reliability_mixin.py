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
            self.error_history = self.error_history[-self.max_error_history:]
        
        # Log error with appropriate level
        self._log_error(error_record)
    
    def _record_successful_operation(self, operation_name: str, execution_time: float):
        """Record a successful operation for monitoring."""
        self.operation_times.append(execution_time)
        
        # Keep history size manageable
        if len(self.operation_times) > self.max_operation_history:
            self.operation_times = self.operation_times[-self.max_operation_history:]
    
    def _classify_error_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity based on error type."""
        # Critical errors that require immediate attention
        critical_errors = [
            "SystemExit", "KeyboardInterrupt", "MemoryError",
            "OutOfMemoryError", "RecursionError"
        ]
        
        # High severity errors that indicate serious problems
        high_errors = [
            "ConnectionError", "TimeoutError", "DatabaseError",
            "AuthenticationError", "PermissionError"
        ]
        
        # Medium severity errors that may be transient
        medium_errors = [
            "HTTPError", "RequestException", "ValidationError",
            "ConfigurationError", "ServiceUnavailableError"
        ]
        
        error_type = type(error).__name__
        
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        elif error_type in high_errors:
            return ErrorSeverity.HIGH
        elif error_type in medium_errors:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _log_error(self, error_record: AgentError):
        """Log error with appropriate level."""
        log_message = f"Agent {error_record.agent_name} operation {error_record.operation} failed: {error_record.message}"
        
        log_context = {
            "error_id": error_record.error_id,
            "agent_name": error_record.agent_name,
            "operation": error_record.operation,
            "error_type": error_record.error_type,
            "severity": error_record.severity.value,
            "context": error_record.context
        }
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_context)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_context)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_context)
        else:
            logger.info(log_message, extra=log_context)