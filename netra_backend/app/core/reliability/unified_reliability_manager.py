"""
Unified Reliability Manager - Single Source of Truth for All Reliability Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate reliability manager duplication across all services  
- Value Impact: Consistent reliability behavior, unified health monitoring, standardized error handling
- Strategic Impact: Improved system reliability, reduced operational complexity, consistent SLA behavior

Consolidates:
- ReliabilityManager (agent-focused)
- AgentReliabilityWrapper (system-wide)  
- Multiple retry logic variations
- Circuit breaker patterns
- Health monitoring systems

Key Features:
- Integrates UnifiedRetryHandler as the retry SSOT
- WebSocket event emission for real-time reliability updates
- Comprehensive health tracking and monitoring
- Circuit breaker pattern integration
- Backward compatibility with existing agents
- Performance optimized for high-throughput scenarios
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    RetryConfig as UnifiedRetryConfig,
    RetryResult,
    RetryStrategy,
    RetryDecision
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    get_unified_circuit_breaker_manager
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import (
    RetryConfig,
    AgentStatus,
    ErrorContext,
    ProcessingResult
)

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.websocket_core.manager import WebSocketManager

logger = central_logger.get_logger(__name__)


class UnifiedReliabilityManager:
    """
    Unified Reliability Manager - SSOT for all reliability patterns.
    
    Consolidates all reliability management functionality including:
    - Retry logic coordination using UnifiedRetryHandler
    - Circuit breaker protection
    - Health monitoring and tracking
    - WebSocket event emission for real-time updates
    - Execution success/failure recording
    
    This replaces:
    - ReliabilityManager
    - AgentReliabilityWrapper
    - Duplicate retry managers across services
    """
    
    def __init__(
        self,
        service_name: str,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[UnifiedCircuitConfig] = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        websocket_notifier: Optional['WebSocketNotifier'] = None
    ):
        self.service_name = service_name
        self.websocket_manager = websocket_manager
        self.websocket_notifier = websocket_notifier
        
        # Initialize retry handling with unified handler
        self._setup_retry_handler(retry_config)
        
        # Initialize circuit breaker
        self._setup_circuit_breaker(circuit_breaker_config)
        
        # Initialize health tracking
        self._initialize_health_tracking()
        
        # Initialize WebSocket reliability event types
        self._reliability_event_types = {
            'reliability_started',
            'retry_attempt', 
            'reliability_failure',
            'circuit_breaker_opened',
            'circuit_breaker_closed',
            'health_degraded',
            'health_recovered'
        }
    
    def _setup_retry_handler(self, retry_config: Optional[RetryConfig]) -> None:
        """Setup unified retry handler with configuration conversion."""
        if retry_config is None:
            retry_config = RetryConfig()
        
        # Convert shared RetryConfig to UnifiedRetryHandler format
        unified_config = self._convert_to_unified_config(retry_config)
        self.retry_handler = UnifiedRetryHandler(self.service_name, unified_config)
        
        # Store original config for compatibility
        self.retry_config = retry_config
    
    def _convert_to_unified_config(self, config: RetryConfig) -> UnifiedRetryConfig:
        """Convert shared RetryConfig to UnifiedRetryHandler RetryConfig."""
        # Map strategy types
        strategy_mapping = {
            'exponential': RetryStrategy.EXPONENTIAL,
            'linear': RetryStrategy.LINEAR, 
            'fixed': RetryStrategy.FIXED,
            'fibonacci': RetryStrategy.FIBONACCI
        }
        
        strategy = strategy_mapping.get(
            config.backoff_strategy.value.lower(), 
            RetryStrategy.EXPONENTIAL
        )
        
        return UnifiedRetryConfig(
            max_attempts=config.get_max_attempts(),
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            strategy=strategy,
            backoff_multiplier=config.get_backoff_multiplier(),
            jitter_range=config.jitter_range,
            timeout_seconds=config.get_timeout_seconds(),
            retryable_exceptions=self._build_retryable_exceptions(config),
            non_retryable_exceptions=self._build_non_retryable_exceptions(config),
            circuit_breaker_enabled=config.circuit_breaker_enabled,
            circuit_breaker_failure_threshold=config.circuit_breaker_failure_threshold,
            circuit_breaker_recovery_timeout=config.circuit_breaker_recovery_timeout,
            metrics_enabled=config.metrics_enabled
        )
    
    def _build_retryable_exceptions(self, config: RetryConfig) -> tuple:
        """Build tuple of retryable exception types."""
        if not config.retryable_exceptions:
            # Default retryable exceptions
            return (ConnectionError, TimeoutError, OSError, RuntimeError)
        
        exceptions = []
        for exc_name in config.retryable_exceptions:
            try:
                exc_type = getattr(__builtins__, exc_name, None)
                if exc_type and isinstance(exc_type, type) and issubclass(exc_type, Exception):
                    exceptions.append(exc_type)
            except (AttributeError, TypeError):
                logger.warning(f"Invalid retryable exception type: {exc_name}")
        
        return tuple(exceptions) if exceptions else (Exception,)
    
    def _build_non_retryable_exceptions(self, config: RetryConfig) -> tuple:
        """Build tuple of non-retryable exception types."""
        if not config.non_retryable_exceptions:
            # Default non-retryable exceptions
            return (ValueError, TypeError, AttributeError, ImportError)
        
        exceptions = []
        for exc_name in config.non_retryable_exceptions:
            try:
                exc_type = getattr(__builtins__, exc_name, None)
                if exc_type and isinstance(exc_type, type) and issubclass(exc_type, Exception):
                    exceptions.append(exc_type)
            except (AttributeError, TypeError):
                logger.warning(f"Invalid non-retryable exception type: {exc_name}")
        
        return tuple(exceptions) if exceptions else (ValueError, TypeError)
    
    def _setup_circuit_breaker(self, circuit_config: Optional[UnifiedCircuitConfig]) -> None:
        """Setup unified circuit breaker."""
        if circuit_config is None and self.retry_config.circuit_breaker_enabled:
            # Create default circuit breaker config from retry config
            circuit_config = UnifiedCircuitConfig(
                name=f"{self.service_name}_reliability_circuit",
                failure_threshold=self.retry_config.circuit_breaker_failure_threshold,
                recovery_timeout=self.retry_config.circuit_breaker_recovery_timeout,
                timeout_seconds=self.retry_config.get_timeout_seconds()
            )
        
        if circuit_config:
            manager = get_unified_circuit_breaker_manager()
            self.circuit_breaker = manager.create_circuit_breaker(
                circuit_config.name, circuit_config
            )
        else:
            self.circuit_breaker = None
    
    def _initialize_health_tracking(self) -> None:
        """Initialize comprehensive health tracking."""
        self.health_stats = {
            "total_executions": 0,
            "successful_executions": 0, 
            "failed_executions": 0,
            "retry_attempts": 0,
            "circuit_breaker_trips": 0,
            "average_execution_time_ms": 0.0,
            "last_execution_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "consecutive_failures": 0,
            "consecutive_successes": 0
        }
        
        # Error tracking
        self.error_history: List[Dict[str, Any]] = []
        self.max_error_history = 100
        
        # Performance tracking
        self.execution_times: List[float] = []
        self.max_execution_history = 50
    
    async def execute_with_reliability(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        context: Optional['AgentExecutionContext'] = None,
        fallback: Optional[Callable[[], Awaitable[Any]]] = None,
        timeout: Optional[float] = None,
        emit_events: bool = True
    ) -> Any:
        """
        Execute operation with full reliability protection.
        
        Args:
            operation: The operation to execute
            operation_name: Name for logging and monitoring
            context: Optional execution context for WebSocket events
            fallback: Optional fallback operation
            timeout: Optional operation timeout
            emit_events: Whether to emit WebSocket events
        
        Returns:
            Operation result
            
        Raises:
            Exception: If operation fails after all retries and no fallback
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        
        # Emit reliability started event
        if emit_events and context:
            await self._emit_reliability_event(
                'reliability_started',
                context,
                {
                    'operation_name': operation_name,
                    'execution_id': execution_id,
                    'max_attempts': self.retry_handler.config.max_attempts,
                    'timeout_seconds': timeout or self.retry_handler.config.timeout_seconds
                }
            )
        
        self.health_stats["total_executions"] += 1
        
        try:
            # Execute with retry protection
            result = await self._execute_with_retry_protection(
                operation, operation_name, context, timeout, emit_events, execution_id
            )
            
            # Record success
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            await self._record_execution_success(execution_time)
            
            return result
            
        except Exception as e:
            # Record failure
            execution_time = (time.time() - start_time) * 1000
            await self._record_execution_failure(e, operation_name, execution_time)
            
            # Emit failure event
            if emit_events and context:
                await self._emit_reliability_event(
                    'reliability_failure',
                    context,
                    {
                        'operation_name': operation_name,
                        'execution_id': execution_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'execution_time_ms': execution_time,
                        'retry_attempts': getattr(e, 'retry_attempts', 0)
                    }
                )
            
            # Try fallback if available
            if fallback:
                try:
                    logger.info(f"Executing fallback for {operation_name}")
                    fallback_result = await fallback()
                    logger.info(f"Fallback succeeded for {operation_name}")
                    return fallback_result
                except Exception as fallback_error:
                    logger.error(f"Fallback failed for {operation_name}: {fallback_error}")
                    raise e  # Raise original error
            
            raise e
    
    async def _execute_with_retry_protection(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        context: Optional['AgentExecutionContext'],
        timeout: Optional[float],
        emit_events: bool,
        execution_id: str
    ) -> Any:
        """Execute operation with retry protection and event emission."""
        
        # Wrap operation with timeout if specified
        if timeout:
            async def timeout_wrapped():
                return await asyncio.wait_for(operation(), timeout=timeout)
            wrapped_operation = timeout_wrapped
        else:
            wrapped_operation = operation
        
        # Track retry attempts for events
        attempt_count = 0
        
        async def retry_aware_operation():
            nonlocal attempt_count
            attempt_count += 1
            
            # Emit retry attempt event (except first attempt)
            if attempt_count > 1 and emit_events and context:
                await self._emit_reliability_event(
                    'retry_attempt',
                    context,
                    {
                        'operation_name': operation_name,
                        'execution_id': execution_id,
                        'attempt_number': attempt_count,
                        'max_attempts': self.retry_handler.config.max_attempts
                    }
                )
            
            return await wrapped_operation()
        
        # Use unified retry handler
        result = await self.retry_handler.execute_with_retry_async(retry_aware_operation)
        
        if result.success:
            # Update retry stats
            if result.total_attempts > 1:
                self.health_stats["retry_attempts"] += result.total_attempts - 1
            return result.result
        else:
            # Add retry info to exception for event emission
            if result.final_exception:
                setattr(result.final_exception, 'retry_attempts', result.total_attempts)
            raise result.final_exception or RuntimeError("Operation failed without exception details")
    
    async def _record_execution_success(self, execution_time_ms: float) -> None:
        """Record successful execution."""
        self.health_stats["successful_executions"] += 1
        self.health_stats["consecutive_successes"] += 1
        self.health_stats["consecutive_failures"] = 0
        self.health_stats["last_success_time"] = datetime.now(UTC)
        
        # Update execution time tracking
        self.execution_times.append(execution_time_ms)
        if len(self.execution_times) > self.max_execution_history:
            self.execution_times.pop(0)
        
        # Calculate average execution time
        if self.execution_times:
            self.health_stats["average_execution_time_ms"] = sum(self.execution_times) / len(self.execution_times)
        
        # Record success in circuit breaker
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
    
    async def _record_execution_failure(
        self, 
        error: Exception, 
        operation_name: str, 
        execution_time_ms: float
    ) -> None:
        """Record execution failure."""
        self.health_stats["failed_executions"] += 1
        self.health_stats["consecutive_failures"] += 1
        self.health_stats["consecutive_successes"] = 0
        self.health_stats["last_failure_time"] = datetime.now(UTC)
        
        # Record in circuit breaker
        if self.circuit_breaker:
            self.circuit_breaker.record_failure(type(error).__name__)
        
        # Track error in history
        self._track_error_in_history(operation_name, error, execution_time_ms)
    
    def _track_error_in_history(
        self, 
        operation_name: str, 
        error: Exception, 
        execution_time_ms: float
    ) -> None:
        """Track error in history for monitoring."""
        error_info = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation_name": operation_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "execution_time_ms": execution_time_ms,
            "service": self.service_name
        }
        
        self.error_history.append(error_info)
        
        # Maintain history size
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
    
    async def _emit_reliability_event(
        self,
        event_type: str,
        context: 'AgentExecutionContext',
        event_data: Dict[str, Any]
    ) -> None:
        """Emit WebSocket reliability event for real-time monitoring."""
        if not self.websocket_manager and not self.websocket_notifier:
            return
        
        if event_type not in self._reliability_event_types:
            logger.warning(f"Unknown reliability event type: {event_type}")
            return
        
        # Build event payload
        payload = {
            "event_type": event_type,
            "service_name": self.service_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            **event_data
        }
        
        try:
            if self.websocket_manager:
                # Direct WebSocket manager usage
                await self.websocket_manager.send_to_thread(
                    context.thread_id,
                    {
                        "type": f"reliability_{event_type}",
                        "payload": payload
                    }
                )
            elif self.websocket_notifier:
                # Use WebSocket notifier for enhanced functionality
                from netra_backend.app.schemas.websocket_models import WebSocketMessage
                message = WebSocketMessage(
                    type=f"reliability_{event_type}",
                    payload=payload
                )
                await self.websocket_notifier._send_websocket_message(
                    context.thread_id, message
                )
            
            logger.debug(f"Emitted reliability event: {event_type} for {context.agent_name}")
            
        except Exception as e:
            # Don't let WebSocket failures break reliability operations
            logger.warning(f"Failed to emit reliability event {event_type}: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        success_rate = self._calculate_success_rate()
        health_score = self._calculate_health_score()
        recent_errors = self._get_recent_errors()
        
        status = {
            "service_name": self.service_name,
            "overall_health": self._determine_health_status(health_score),
            "health_score": health_score,
            "success_rate": success_rate,
            "statistics": self.health_stats.copy(),
            "recent_errors": len(recent_errors),
            "total_tracked_errors": len(self.error_history)
        }
        
        # Add circuit breaker status if available
        if self.circuit_breaker:
            status["circuit_breaker"] = self.circuit_breaker.get_status()
        
        # Add retry configuration info
        status["retry_config"] = {
            "max_attempts": self.retry_handler.config.max_attempts,
            "base_delay": self.retry_handler.config.base_delay,
            "max_delay": self.retry_handler.config.max_delay,
            "strategy": self.retry_handler.config.strategy.value,
            "circuit_breaker_enabled": self.retry_handler.config.circuit_breaker_enabled
        }
        
        return status
    
    def _calculate_success_rate(self) -> float:
        """Calculate current success rate."""
        total = self.health_stats["total_executions"]
        if total <= 0:
            return 1.0
        return self.health_stats["successful_executions"] / total
    
    def _calculate_health_score(self) -> float:
        """Calculate comprehensive health score (0-1)."""
        success_rate = self._calculate_success_rate()
        
        # Start with success rate
        score = success_rate
        
        # Apply penalties for consecutive failures
        consecutive_failures = self.health_stats["consecutive_failures"]
        if consecutive_failures > 0:
            failure_penalty = min(0.3, consecutive_failures * 0.1)
            score -= failure_penalty
        
        # Apply penalties for recent errors
        recent_errors = self._get_recent_errors()
        error_penalty = min(0.2, len(recent_errors) * 0.05)
        score -= error_penalty
        
        # Apply circuit breaker penalty
        if self.circuit_breaker:
            cb_status = self.circuit_breaker.get_status()
            if cb_status.get('state') == 'OPEN':
                score -= 0.4
            elif cb_status.get('state') == 'HALF_OPEN':
                score -= 0.2
        
        return max(0.0, score)
    
    def _determine_health_status(self, health_score: float) -> str:
        """Determine health status from score."""
        if health_score >= 0.9:
            return "healthy"
        elif health_score >= 0.7:
            return "degraded"
        elif health_score >= 0.5:
            return "unhealthy"
        else:
            return "critical"
    
    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """Get errors from the last 5 minutes."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=5)
        return [
            e for e in self.error_history
            if datetime.fromisoformat(e["timestamp"]) > cutoff_time
        ]
    
    def reset_health_tracking(self) -> None:
        """Reset health tracking statistics."""
        self._initialize_health_tracking()
        
        # Reset circuit breaker if available
        if self.circuit_breaker:
            self.circuit_breaker.reset()
    
    # Backward compatibility methods for existing code
    
    async def execute_safely(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """Backward compatibility method for AgentReliabilityWrapper."""
        return await self.execute_with_reliability(
            operation, operation_name, None, fallback, timeout, emit_events=False
        )
    
    def with_timeout(self, timeout_seconds: float) -> 'UnifiedReliabilityManager':
        """Create new manager with specified timeout."""
        new_config = RetryConfig(**self.retry_config.__dict__)
        new_config.timeout_seconds_float = timeout_seconds
        
        return UnifiedReliabilityManager(
            self.service_name,
            new_config,
            websocket_manager=self.websocket_manager,
            websocket_notifier=self.websocket_notifier
        )
    
    def with_max_attempts(self, max_attempts: int) -> 'UnifiedReliabilityManager':
        """Create new manager with specified max attempts.""" 
        new_config = RetryConfig(**self.retry_config.__dict__)
        new_config.max_attempts = max_attempts
        
        return UnifiedReliabilityManager(
            self.service_name,
            new_config,
            websocket_manager=self.websocket_manager,
            websocket_notifier=self.websocket_notifier
        )


# Global registry for reliability managers
_reliability_manager_registry: Dict[str, UnifiedReliabilityManager] = {}


def get_reliability_manager(
    service_name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[UnifiedCircuitConfig] = None,
    websocket_manager: Optional['WebSocketManager'] = None,
    websocket_notifier: Optional['WebSocketNotifier'] = None
) -> UnifiedReliabilityManager:
    """
    Get or create unified reliability manager for service.
    
    This is the main entry point for all reliability management needs.
    """
    cache_key = f"{service_name}_{id(websocket_manager)}"
    
    if cache_key not in _reliability_manager_registry:
        _reliability_manager_registry[cache_key] = UnifiedReliabilityManager(
            service_name,
            retry_config,
            circuit_breaker_config,
            websocket_manager,
            websocket_notifier
        )
    
    return _reliability_manager_registry[cache_key]


def get_system_reliability_health() -> Dict[str, Any]:
    """Get system-wide reliability health status."""
    managers_health = {}
    healthy_count = 0
    total_count = len(_reliability_manager_registry)
    
    for key, manager in _reliability_manager_registry.items():
        health = manager.get_health_status()
        managers_health[key] = health
        
        if health['health_score'] > 0.8:
            healthy_count += 1
    
    return {
        "system_health": "healthy" if healthy_count / max(total_count, 1) > 0.8 else "degraded",
        "managers": managers_health,
        "total_managers": total_count,
        "healthy_managers": healthy_count,
        "health_ratio": healthy_count / max(total_count, 1)
    }


# Factory functions for common reliability patterns

def create_database_reliability_manager(
    service_name: str,
    websocket_manager: Optional['WebSocketManager'] = None
) -> UnifiedReliabilityManager:
    """Create reliability manager optimized for database operations."""
    config = RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        backoff_factor=2.0,
        timeout_seconds=60,
        retryable_exceptions=['ConnectionError', 'TimeoutError', 'OSError'],
        non_retryable_exceptions=['ValueError', 'TypeError', 'AttributeError'],
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=5,
        circuit_breaker_recovery_timeout=60.0
    )
    
    return get_reliability_manager(service_name, config, None, websocket_manager)


def create_llm_reliability_manager(
    service_name: str,
    websocket_manager: Optional['WebSocketManager'] = None
) -> UnifiedReliabilityManager:
    """Create reliability manager optimized for LLM operations."""
    config = RetryConfig(
        max_retries=4,
        base_delay=2.0,
        max_delay=120.0,
        backoff_factor=2.5,
        timeout_seconds=300,
        retryable_exceptions=['ConnectionError', 'TimeoutError', 'OSError'],
        non_retryable_exceptions=['ValueError', 'TypeError'],
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=3,
        circuit_breaker_recovery_timeout=180.0
    )
    
    return get_reliability_manager(service_name, config, None, websocket_manager)


def create_agent_reliability_manager(
    service_name: str,
    websocket_manager: Optional['WebSocketManager'] = None,
    websocket_notifier: Optional['WebSocketNotifier'] = None
) -> UnifiedReliabilityManager:
    """Create reliability manager optimized for agent operations with WebSocket events."""
    config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        timeout_seconds=120,
        retryable_exceptions=['ConnectionError', 'TimeoutError', 'OSError', 'RuntimeError'],
        non_retryable_exceptions=['ValueError', 'TypeError', 'AttributeError', 'ImportError'],
        circuit_breaker_enabled=False,  # Agents handle their own circuit breaking
        metrics_enabled=True
    )
    
    return get_reliability_manager(
        service_name, config, None, websocket_manager, websocket_notifier
    )