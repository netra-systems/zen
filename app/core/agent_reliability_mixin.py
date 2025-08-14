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
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from .error_codes import ErrorSeverity

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
    
    async def _attempt_operation_recovery(
        self,
        operation_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        """Attempt to recover from operation failure."""
        if operation_name in self.recovery_strategies:
            try:
                recovery_func = self.recovery_strategies[operation_name]
                recovery_result = await recovery_func(error, context)
                
                # Update error record to indicate recovery attempt
                if self.error_history:
                    self.error_history[-1].recovery_attempted = True
                    self.error_history[-1].recovery_successful = recovery_result is not None
                
                return recovery_result
                
            except Exception as recovery_error:
                logger.error(f"Recovery failed for {operation_name}: {recovery_error}")
                return None
        
        return None
    
    def register_recovery_strategy(
        self,
        operation_name: str,
        recovery_func: Callable[[Exception, Optional[Dict[str, Any]]], Awaitable[Optional[Any]]]
    ):
        """Register a recovery strategy for a specific operation."""
        self.recovery_strategies[operation_name] = recovery_func
    
    def _register_default_recovery_strategies(self):
        """Register default recovery strategies."""
        # Default strategies for common failure scenarios
        self.register_recovery_strategy("llm_call", self._default_llm_recovery)
        self.register_recovery_strategy("database_query", self._default_db_recovery)
        self.register_recovery_strategy("api_call", self._default_api_recovery)
    
    async def _default_llm_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for LLM failures."""
        # Return a basic fallback response
        return {
            "status": "fallback",
            "message": "Operation completed with limited functionality",
            "error": str(error),
            "fallback_used": True
        }
    
    async def _default_db_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for database failures."""
        # Return cached data if available, otherwise empty result
        return {
            "data": [],
            "cached": True,
            "error": str(error),
            "fallback_used": True
        }
    
    async def _default_api_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for API failures."""
        # Return mock data structure
        return {
            "result": "limited",
            "data": {},
            "error": str(error),
            "fallback_used": True
        }
    
    def get_comprehensive_health_status(self) -> AgentHealthStatus:
        """Get comprehensive health status of the agent."""
        current_time = time.time()
        agent_name = getattr(self, 'name', self.__class__.__name__)
        
        # Calculate metrics
        recent_errors = self._count_recent_errors(300)  # Last 5 minutes
        total_operations = len(self.operation_times) + len(self.error_history)
        success_rate = self._calculate_success_rate()
        avg_response_time = self._calculate_avg_response_time()
        
        # Determine overall health
        overall_health = self._calculate_overall_health(success_rate, recent_errors, avg_response_time)
        
        # Determine status
        status = self._determine_health_status(overall_health, recent_errors)
        
        # Get circuit breaker state
        cb_state = "unknown"
        try:
            cb_status = self.reliability.circuit_breaker.get_status()
            cb_state = cb_status.get("state", "unknown")
        except Exception:
            pass
        
        return AgentHealthStatus(
            agent_name=agent_name,
            overall_health=overall_health,
            circuit_breaker_state=cb_state,
            recent_errors=recent_errors,
            total_operations=total_operations,
            success_rate=success_rate,
            average_response_time=avg_response_time,
            last_error=self.error_history[-1] if self.error_history else None,
            status=status
        )
    
    def _count_recent_errors(self, seconds: int) -> int:
        """Count errors in the last N seconds."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=seconds)
        return len([e for e in self.error_history if e.timestamp >= cutoff_time])
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate over recent operations."""
        total_ops = len(self.operation_times) + len(self.error_history)
        if total_ops == 0:
            return 1.0
        
        successful_ops = len(self.operation_times)
        return successful_ops / total_ops
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.operation_times:
            return 0.0
        
        # Use recent operations for more relevant average
        recent_times = self.operation_times[-20:]  # Last 20 operations
        return sum(recent_times) / len(recent_times)
    
    def _calculate_overall_health(self, success_rate: float, recent_errors: int, avg_response_time: float) -> float:
        """Calculate overall health score."""
        # Start with success rate as base score
        health_score = success_rate
        
        # Penalize for recent errors
        if recent_errors > 0:
            error_penalty = min(recent_errors * 0.1, 0.5)  # Max 50% penalty
            health_score -= error_penalty
        
        # Penalize for slow response times
        if avg_response_time > 5.0:  # If slower than 5 seconds
            time_penalty = min((avg_response_time - 5.0) * 0.1, 0.3)  # Max 30% penalty
            health_score -= time_penalty
        
        return max(0.0, min(1.0, health_score))
    
    def _determine_health_status(self, overall_health: float, recent_errors: int) -> str:
        """Determine health status based on metrics."""
        if overall_health >= 0.8 and recent_errors == 0:
            return "healthy"
        elif overall_health >= 0.5 and recent_errors <= 2:
            return "degraded"
        else:
            return "unhealthy"
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}, "recent_errors": 0}
        
        # Count error types
        error_types = {}
        recent_errors = 0
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        for error in self.error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            if error.timestamp >= cutoff_time:
                recent_errors += 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "recent_errors": recent_errors,
            "last_error": {
                "type": self.error_history[-1].error_type,
                "message": self.error_history[-1].message,
                "timestamp": self.error_history[-1].timestamp.isoformat()
            }
        }
    
    def reset_health_metrics(self):
        """Reset health metrics and error history."""
        self.error_history.clear()
        self.operation_times.clear()
        
        # Reset circuit breaker if needed
        try:
            self.reliability.circuit_breaker.reset()
        except Exception as e:
            logger.warning(f"Failed to reset circuit breaker: {e}")
    
    async def perform_health_check(self) -> AgentHealthStatus:
        """Perform comprehensive health check."""
        self.last_health_check = time.time()
        
        health_status = self.get_comprehensive_health_status()
        
        # Log health status if degraded or unhealthy
        if health_status.status != "healthy":
            logger.warning(
                f"Agent {health_status.agent_name} health status: {health_status.status} "
                f"(health={health_status.overall_health:.2f}, errors={health_status.recent_errors})"
            )
        
        return health_status
    
    def should_perform_health_check(self) -> bool:
        """Check if health check should be performed."""
        return (time.time() - self.last_health_check) >= self.health_check_interval