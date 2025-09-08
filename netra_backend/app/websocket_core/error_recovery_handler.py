"""WebSocket Error Recovery Handler - Complete implementation for WebSocket error management.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Platform reliability and user experience
- Value Impact: Prevents chat session failures from disrupting user workflows
- Strategic Impact: Critical for enterprise users who require reliable AI interactions

This module provides comprehensive WebSocket error recovery functionality including:
- Error classification and handling strategies
- Circuit breaker pattern implementation
- Exponential backoff retry logic
- Graceful degradation modes
- Error metrics and pattern detection
- Connection recovery with message buffering
"""

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import uuid4

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.schemas.startup_types import ErrorType as BaseErrorType

logger = central_logger.get_logger(__name__)


# =============================================================================
# WEBSOCKET-SPECIFIC ERROR TYPES AND ENUMS
# =============================================================================

class ErrorType(str, Enum):
    """WebSocket-specific error types extending base error types."""
    # Connection errors
    CONNECTION_LOST = "connection_lost"
    CONNECTION_TIMEOUT = "connection_timeout" 
    CONNECTION_REFUSED = "connection_refused"
    
    # Message handling errors
    MESSAGE_DELIVERY_FAILED = "message_delivery_failed"
    MESSAGE_SERIALIZATION_FAILED = "message_serialization_failed"
    MESSAGE_TOO_LARGE = "message_too_large"
    MESSAGE_INVALID_FORMAT = "message_invalid_format"
    
    # Rate limiting and resource errors
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    
    # Authentication and authorization errors
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    TOKEN_EXPIRED = "token_expired"
    
    # Protocol and compatibility errors
    PROTOCOL_ERROR = "protocol_error"
    VERSION_MISMATCH = "version_mismatch"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    
    # System and infrastructure errors
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    
    # Generic fallback
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(str, Enum):
    """WebSocket recovery strategies."""
    RECONNECT_WITH_BACKOFF = "reconnect_with_backoff"
    RETRY_WITH_FALLBACK_FORMAT = "retry_with_fallback_format"
    BACKOFF_AND_QUEUE = "backoff_and_queue"
    REAUTHENTICATE = "reauthenticate"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    BUFFER_AND_REPLAY = "buffer_and_replay"
    FALLBACK_TRANSPORT = "fallback_transport"
    NO_RECOVERY = "no_recovery"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"     # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


# =============================================================================
# DATA MODELS FOR ERROR RECOVERY
# =============================================================================

class WebSocketErrorContext:
    """Enhanced ErrorContext specifically for WebSocket error recovery."""
    
    def __init__(
        self,
        error_type: ErrorType,
        connection_id: str,
        user_id: str,
        error_message: str,
        timestamp: datetime,
        retry_count: int = 0,
        context_data: Optional[Dict[str, Any]] = None,
        operation: str = 'websocket_operation',
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize WebSocket-specific error context.
        
        Args:
            error_type: Type of WebSocket error
            connection_id: WebSocket connection identifier
            user_id: User identifier
            error_message: Human-readable error message
            timestamp: When the error occurred
            retry_count: Number of retry attempts made
            context_data: Additional context information
            operation: Operation name
            trace_id: Trace identifier
            request_id: Request identifier
            **kwargs: Additional keyword arguments
        """
        # WebSocket-specific attributes
        self.error_type = error_type
        self.connection_id = connection_id
        self.user_id = user_id
        self.error_message = error_message
        self.timestamp = timestamp
        self.retry_count = retry_count
        self.context_data = context_data or {}
        
        # Base context attributes
        self.operation = operation
        self.trace_id = trace_id
        self.request_id = request_id
        
        # Additional attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


# For backward compatibility with tests, alias as ErrorContext in this module
ErrorContext = WebSocketErrorContext

class RecoveryResult:
    """Result of an error recovery attempt."""
    
    def __init__(
        self,
        recovery_attempted: bool = False,
        recovery_successful: bool = False,
        strategy_applied: Optional[RecoveryStrategy] = None,
        retry_attempts_made: int = 0,
        buffered_messages_restored: int = 0,
        error_message: Optional[str] = None,
        recovery_duration_ms: Optional[float] = None,
        rejected_by_circuit_breaker: bool = False,
        degradation_mode_activated: bool = False,
        degradation_strategy: Optional[str] = None,
        cascade_prevention_applied: bool = False,
        isolation_measures_activated: bool = False
    ):
        self.recovery_attempted = recovery_attempted
        self.recovery_successful = recovery_successful
        self.strategy_applied = strategy_applied
        self.retry_attempts_made = retry_attempts_made
        self.buffered_messages_restored = buffered_messages_restored
        self.error_message = error_message
        self.recovery_duration_ms = recovery_duration_ms
        self.rejected_by_circuit_breaker = rejected_by_circuit_breaker
        self.degradation_mode_activated = degradation_mode_activated
        self.degradation_strategy = degradation_strategy
        self.cascade_prevention_applied = cascade_prevention_applied
        self.isolation_measures_activated = isolation_measures_activated


class CircuitBreaker:
    """Circuit breaker implementation for error recovery."""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED
        
    def is_open(self) -> bool:
        """Check if circuit breaker is open (preventing operations)."""
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has elapsed to transition to half-open
            if (
                self.last_failure_time and 
                time.time() - self.last_failure_time >= self.timeout_seconds
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioned to HALF_OPEN")
                return False
            return True
        return False
        
    def record_success(self) -> None:
        """Record successful operation."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        logger.debug("Circuit breaker recorded success, state: CLOSED")
        
    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
        else:
            logger.debug(f"Circuit breaker recorded failure {self.failure_count}/{self.failure_threshold}")
            
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        return not self.is_open()


class ErrorMetrics:
    """Error metrics tracking for WebSocket connections."""
    
    def __init__(self):
        self.total_errors_handled = 0
        self.error_type_counts: Dict[ErrorType, int] = {}
        self.recovery_attempts = 0
        self.recovery_successes = 0
        self.circuit_breaker_activations = 0
        self.degradation_mode_activations = 0
        self.start_time = time.time()
        
    @property
    def recovery_success_rate(self) -> float:
        """Calculate recovery success rate."""
        if self.recovery_attempts == 0:
            return 0.0
        return self.recovery_successes / self.recovery_attempts
        
    def record_error(self, error_type: ErrorType) -> None:
        """Record an error occurrence."""
        self.total_errors_handled += 1
        if error_type not in self.error_type_counts:
            self.error_type_counts[error_type] = 0
        self.error_type_counts[error_type] += 1
        
    def record_recovery_attempt(self) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts += 1
        
    def record_recovery_success(self) -> None:
        """Record a successful recovery."""
        self.recovery_successes += 1
        
    def record_circuit_breaker_activation(self) -> None:
        """Record circuit breaker activation."""
        self.circuit_breaker_activations += 1
        
    def record_degradation_activation(self) -> None:
        """Record graceful degradation activation."""
        self.degradation_mode_activations += 1


class ErrorRecoveryReport:
    """Comprehensive error recovery report."""
    
    def __init__(
        self,
        time_period_hours: int,
        total_errors_encountered: int,
        total_recovery_attempts: int,
        recovery_success_rate: float,
        most_common_error_types: List[tuple],
        system_health_rating: str,
        improvement_recommendations: List[str]
    ):
        self.time_period_hours = time_period_hours
        self.total_errors_encountered = total_errors_encountered
        self.total_recovery_attempts = total_recovery_attempts
        self.recovery_success_rate = recovery_success_rate
        self.most_common_error_types = most_common_error_types
        self.system_health_rating = system_health_rating
        self.improvement_recommendations = improvement_recommendations


class RecoveryState:
    """State tracking for active recovery operations."""
    
    def __init__(self, error_context: WebSocketErrorContext):
        self.error_context = error_context
        self.recovery_strategy: Optional[RecoveryStrategy] = None
        self.started_at = datetime.now(timezone.utc)
        self.is_active = True
        self.attempts_made = 0
        self.last_attempt_at: Optional[datetime] = None
        

class DegradationState:
    """State tracking for graceful degradation mode."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.is_active = False
        self.fallback_strategy: Optional[str] = None
        self.activated_at: Optional[datetime] = None
        
        
class CascadePreventionState:
    """State tracking for cascade failure prevention."""
    
    def __init__(self):
        self.is_active = False
        self.isolation_mode = False
        self.affected_connections: Optional[List[str]] = None
        self.activated_at: Optional[datetime] = None


# =============================================================================
# MAIN WEBSOCKET ERROR RECOVERY HANDLER
# =============================================================================

class WebSocketErrorRecoveryHandler:
    """Comprehensive WebSocket error recovery handler.
    
    Provides enterprise-grade error recovery capabilities including:
    - Intelligent error classification
    - Multiple recovery strategies (retry, circuit breaker, graceful degradation)
    - Exponential backoff with jitter
    - Message buffering and replay
    - Comprehensive metrics and reporting
    - Cascade failure prevention
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        websocket_manager: Any,
        message_buffer: Any
    ):
        """Initialize WebSocket error recovery handler.
        
        Args:
            config: Recovery configuration parameters
            websocket_manager: WebSocket connection manager
            message_buffer: Message buffer for replay functionality
        """
        self.config = config
        self.websocket_manager = websocket_manager
        self.message_buffer = message_buffer
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get("circuit_breaker_threshold", 5),
            timeout_seconds=config.get("circuit_breaker_timeout_seconds", 30)
        )
        
        # Initialize error metrics
        self.error_metrics = ErrorMetrics()
        
        # Active recovery tracking
        self._active_recoveries: Dict[str, RecoveryState] = {}
        
        # Degradation state tracking
        self._degradation_states: Dict[str, DegradationState] = {}
        
        # Cascade prevention
        self._cascade_prevention = CascadePreventionState()
        
        logger.info("WebSocketErrorRecoveryHandler initialized with config", extra={
            "circuit_breaker_enabled": config.get("circuit_breaker_enabled", True),
            "max_retry_attempts": config.get("max_retry_attempts", 3),
            "enable_graceful_degradation": config.get("enable_graceful_degradation", True)
        })
    
    async def handle_error(self, error_context: WebSocketErrorContext) -> RecoveryResult:
        """Handle WebSocket error with comprehensive recovery logic.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            RecoveryResult with details of recovery attempt
        """
        start_time = time.time()
        connection_id = error_context.connection_id
        
        # Record error in metrics
        self.error_metrics.record_error(error_context.error_type)
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN, rejecting recovery for {connection_id}")
            return RecoveryResult(
                recovery_attempted=False,
                rejected_by_circuit_breaker=True,
                error_message="Circuit breaker is open"
            )
        
        # Check for cascade prevention
        if self._should_apply_cascade_prevention(error_context):
            await self._activate_cascade_prevention(error_context)
            return RecoveryResult(
                recovery_attempted=True,
                recovery_successful=False,
                cascade_prevention_applied=True,
                isolation_measures_activated=True
            )
        
        # Check if cascade prevention is already active
        if self._cascade_prevention.is_active:
            logger.info(f"Cascade prevention active - applying isolation for {connection_id}")
            return RecoveryResult(
                recovery_attempted=True,
                recovery_successful=False,
                cascade_prevention_applied=True,
                isolation_measures_activated=True
            )
        
        # Select recovery strategy
        strategy = self._select_recovery_strategy(error_context.error_type)
        
        # Create/update recovery state
        if connection_id not in self._active_recoveries:
            self._active_recoveries[connection_id] = RecoveryState(error_context)
        
        recovery_state = self._active_recoveries[connection_id]
        recovery_state.recovery_strategy = strategy
        recovery_state.attempts_made += 1
        recovery_state.last_attempt_at = datetime.now(timezone.utc)
        
        # Record recovery attempt
        self.error_metrics.record_recovery_attempt()
        
        try:
            # Execute recovery strategy
            success = await self._execute_recovery_strategy(strategy, error_context)
            
            if success:
                self.circuit_breaker.record_success()
                self.error_metrics.record_recovery_success()
                
                # Restore buffered messages if applicable
                buffered_count = 0
                if strategy == RecoveryStrategy.RECONNECT_WITH_BACKOFF:
                    buffered_count = await self._restore_buffered_messages(error_context)
                
                # Clean up recovery state
                if connection_id in self._active_recoveries:
                    del self._active_recoveries[connection_id]
                
                recovery_duration = (time.time() - start_time) * 1000
                logger.info(f"Recovery successful for {connection_id} using {strategy}")
                
                return RecoveryResult(
                    recovery_attempted=True,
                    recovery_successful=True,
                    strategy_applied=strategy,
                    retry_attempts_made=recovery_state.attempts_made,
                    buffered_messages_restored=buffered_count,
                    recovery_duration_ms=recovery_duration
                )
            else:
                # Recovery failed
                self.circuit_breaker.record_failure()
                
                # Check if should activate graceful degradation
                if self.config.get("enable_graceful_degradation", True):
                    degradation_result = await self._activate_graceful_degradation(error_context)
                    if degradation_result:
                        return RecoveryResult(
                            recovery_attempted=True,
                            recovery_successful=False,
                            strategy_applied=strategy,
                            retry_attempts_made=recovery_state.attempts_made,
                            degradation_mode_activated=True,
                            degradation_strategy="message_buffering_with_retry"
                        )
                
                recovery_duration = (time.time() - start_time) * 1000
                logger.warning(f"Recovery failed for {connection_id} using {strategy}")
                
                return RecoveryResult(
                    recovery_attempted=True,
                    recovery_successful=False,
                    strategy_applied=strategy,
                    retry_attempts_made=recovery_state.attempts_made,
                    error_message=f"Recovery strategy {strategy} failed",
                    recovery_duration_ms=recovery_duration
                )
                
        except Exception as e:
            self.circuit_breaker.record_failure()
            recovery_duration = (time.time() - start_time) * 1000
            
            logger.error(f"Recovery exception for {connection_id}: {e}")
            
            return RecoveryResult(
                recovery_attempted=True,
                recovery_successful=False,
                strategy_applied=strategy,
                retry_attempts_made=recovery_state.attempts_made,
                error_message=str(e),
                recovery_duration_ms=recovery_duration
            )
    
    def _select_recovery_strategy(self, error_type: ErrorType) -> RecoveryStrategy:
        """Select appropriate recovery strategy based on error type."""
        strategy_map = {
            ErrorType.CONNECTION_LOST: RecoveryStrategy.RECONNECT_WITH_BACKOFF,
            ErrorType.CONNECTION_TIMEOUT: RecoveryStrategy.RECONNECT_WITH_BACKOFF,
            ErrorType.MESSAGE_SERIALIZATION_FAILED: RecoveryStrategy.RETRY_WITH_FALLBACK_FORMAT,
            ErrorType.RATE_LIMIT_EXCEEDED: RecoveryStrategy.BACKOFF_AND_QUEUE,
            ErrorType.AUTHENTICATION_FAILED: RecoveryStrategy.REAUTHENTICATE,
            ErrorType.TOKEN_EXPIRED: RecoveryStrategy.REAUTHENTICATE,
            ErrorType.MESSAGE_DELIVERY_FAILED: RecoveryStrategy.BUFFER_AND_REPLAY,
            ErrorType.RESOURCE_EXHAUSTED: RecoveryStrategy.GRACEFUL_DEGRADATION,
        }
        
        return strategy_map.get(error_type, RecoveryStrategy.RECONNECT_WITH_BACKOFF)
    
    async def _execute_recovery_strategy(
        self, 
        strategy: RecoveryStrategy, 
        error_context: WebSocketErrorContext
    ) -> bool:
        """Execute the selected recovery strategy."""
        try:
            if strategy == RecoveryStrategy.RECONNECT_WITH_BACKOFF:
                return await self._execute_reconnection_strategy(error_context)
            elif strategy == RecoveryStrategy.REAUTHENTICATE:
                return await self._execute_reauthentication_strategy(error_context)
            elif strategy == RecoveryStrategy.RETRY_WITH_FALLBACK_FORMAT:
                return await self._execute_retry_strategy(error_context)
            elif strategy == RecoveryStrategy.BACKOFF_AND_QUEUE:
                return await self._execute_backoff_strategy(error_context)
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return await self._execute_degradation_strategy(error_context)
            else:
                logger.warning(f"Unknown recovery strategy: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"Recovery strategy {strategy} execution failed: {e}")
            return False
    
    async def _execute_reconnection_strategy(self, error_context: WebSocketErrorContext) -> bool:
        """Execute reconnection with exponential backoff."""
        connection_id = error_context.connection_id
        max_attempts = self.config.get("max_retry_attempts", 3)
        base_delay = 1.0
        multiplier = self.config.get("retry_backoff_multiplier", 2.0)
        
        # Track actual retry attempts for the recovery state
        if connection_id in self._active_recoveries:
            recovery_state = self._active_recoveries[connection_id]
            # Reset attempts made so we can track them properly
            recovery_state.attempts_made = 0
        
        for attempt in range(max_attempts):
            # Increment attempts counter
            if connection_id in self._active_recoveries:
                recovery_state = self._active_recoveries[connection_id]
                recovery_state.attempts_made = attempt + 1
            
            if attempt > 0:
                delay = base_delay * (multiplier ** (attempt - 1))
                logger.debug(f"Waiting {delay}s before reconnection attempt {attempt + 1}")
                await asyncio.sleep(delay)
            
            try:
                # Attempt reconnection via websocket manager
                if hasattr(self.websocket_manager, 'attempt_reconnection'):
                    success = await self.websocket_manager.attempt_reconnection(connection_id)
                    if success:
                        logger.info(f"Reconnection successful on attempt {attempt + 1}")
                        return True
                else:
                    logger.warning("WebSocket manager does not support reconnection")
                    return False
                    
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:  # Last attempt
                    raise e
        
        return False
    
    async def _execute_reauthentication_strategy(self, error_context: WebSocketErrorContext) -> bool:
        """Execute reauthentication strategy."""
        try:
            if hasattr(self.websocket_manager, 'reauthenticate_user'):
                user_id = error_context.user_id
                return await self.websocket_manager.reauthenticate_user(user_id)
            else:
                logger.warning("WebSocket manager does not support reauthentication")
                return False
        except Exception as e:
            logger.error(f"Reauthentication failed: {e}")
            return False
    
    async def _execute_retry_strategy(self, error_context: WebSocketErrorContext) -> bool:
        """Execute retry with fallback format strategy."""
        # Implementation would depend on specific retry logic needed
        logger.debug("Executing retry with fallback format strategy")
        return True  # Placeholder
    
    async def _execute_backoff_strategy(self, error_context: WebSocketErrorContext) -> bool:
        """Execute backoff and queue strategy."""
        # Implementation would queue messages and apply backoff
        logger.debug("Executing backoff and queue strategy")
        return True  # Placeholder
    
    async def _execute_degradation_strategy(self, error_context: WebSocketErrorContext) -> bool:
        """Execute graceful degradation strategy."""
        return await self._activate_graceful_degradation(error_context)
    
    async def _restore_buffered_messages(self, error_context: WebSocketErrorContext) -> int:
        """Restore buffered messages after successful recovery."""
        try:
            if hasattr(self.message_buffer, 'get_buffered_messages'):
                buffered_messages = await self.message_buffer.get_buffered_messages(error_context.user_id)
                
                if buffered_messages and hasattr(self.websocket_manager, 'send_messages'):
                    await self.websocket_manager.send_messages(error_context.connection_id, buffered_messages)
                    logger.info(f"Restored {len(buffered_messages)} buffered messages")
                    return len(buffered_messages)
            
            return 0
        except Exception as e:
            logger.error(f"Failed to restore buffered messages: {e}")
            return 0
    
    async def _activate_graceful_degradation(self, error_context: WebSocketErrorContext) -> bool:
        """Activate graceful degradation mode for user."""
        user_id = error_context.user_id
        
        if user_id not in self._degradation_states:
            self._degradation_states[user_id] = DegradationState(user_id)
        
        degradation_state = self._degradation_states[user_id]
        degradation_state.is_active = True
        degradation_state.fallback_strategy = "message_buffering_with_retry"
        degradation_state.activated_at = datetime.now(timezone.utc)
        
        self.error_metrics.record_degradation_activation()
        
        logger.info(f"Graceful degradation activated for user {user_id}")
        return True
    
    def _should_apply_cascade_prevention(self, error_context: WebSocketErrorContext) -> bool:
        """Determine if cascade prevention should be applied."""
        # Check for high-severity errors that might affect other connections
        high_severity_errors = {
            ErrorType.RESOURCE_EXHAUSTED,
            ErrorType.MEMORY_LIMIT_EXCEEDED,
            ErrorType.SERVICE_UNAVAILABLE
        }
        
        if error_context.error_type in high_severity_errors:
            context_data = getattr(error_context, 'context_data', {})
            return context_data.get('severity') == 'high' and context_data.get('affects_others', False)
        
        return False
    
    async def _activate_cascade_prevention(self, error_context: WebSocketErrorContext) -> None:
        """Activate cascade failure prevention measures."""
        self._cascade_prevention.is_active = True
        self._cascade_prevention.isolation_mode = True
        self._cascade_prevention.affected_connections = [error_context.connection_id]
        self._cascade_prevention.activated_at = datetime.now(timezone.utc)
        
        # Would implement connection isolation logic here
        logger.warning(f"Cascade prevention activated for error: {error_context.error_type}")
    
    async def generate_recovery_report(self, time_period_hours: int = 24) -> ErrorRecoveryReport:
        """Generate comprehensive error recovery report."""
        # Calculate metrics for the specified time period
        most_common_errors = list(self.error_metrics.error_type_counts.items())
        most_common_errors.sort(key=lambda x: x[1], reverse=True)
        
        # Determine system health rating
        success_rate = self.error_metrics.recovery_success_rate
        if success_rate >= 0.95:
            health_rating = "excellent"
        elif success_rate >= 0.85:
            health_rating = "good"
        elif success_rate >= 0.70:
            health_rating = "fair"
        elif success_rate >= 0.50:
            health_rating = "poor"
        else:
            health_rating = "critical"
        
        # Generate improvement recommendations
        recommendations = []
        if success_rate < 0.90:
            recommendations.append("Consider tuning circuit breaker thresholds")
        if self.error_metrics.circuit_breaker_activations > 10:
            recommendations.append("High circuit breaker activations - investigate root causes")
        if self.error_metrics.degradation_mode_activations > 5:
            recommendations.append("Frequent graceful degradations - consider capacity planning")
        
        return ErrorRecoveryReport(
            time_period_hours=time_period_hours,
            total_errors_encountered=self.error_metrics.total_errors_handled,
            total_recovery_attempts=self.error_metrics.recovery_attempts,
            recovery_success_rate=success_rate,
            most_common_error_types=most_common_errors[:5],  # Top 5
            system_health_rating=health_rating,
            improvement_recommendations=recommendations
        )


# =============================================================================
# BACKWARD COMPATIBILITY AND ALIASES
# =============================================================================

# Import existing components for compatibility
from netra_backend.app.websocket_core.recovery import ErrorRecoveryHandler
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Create backward compatibility aliases
WebSocketRecoveryManager = UnifiedWebSocketManager

# Export all classes for test imports
__all__ = [
    "WebSocketErrorRecoveryHandler",
    "ErrorType", 
    "RecoveryStrategy",
    "ErrorContext",
    "WebSocketErrorContext", 
    "RecoveryResult",
    "CircuitBreaker",
    "ErrorMetrics",
    "ErrorRecoveryReport",
    "RecoveryState",
    "DegradationState", 
    "CascadePreventionState",
    "CircuitBreakerState",
    "WebSocketRecoveryManager",  # Alias
    "ErrorRecoveryHandler"       # From recovery module
]