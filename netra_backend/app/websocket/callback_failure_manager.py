"""Callback failure management for WebSocket reconnection.

Handles callback criticality, circuit breaking, and failure propagation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    from netra_backend.app.logging_config import central_logger

    from .reconnection_exceptions import (
        CallbackCircuitBreakerOpen,
        CriticalCallbackFailure,
        StateNotificationFailure,
    )
    from .reconnection_types import (
        CallbackCircuitBreaker,
        CallbackCriticality,
        CallbackFailure,
        CallbackType,
    )
except ImportError:
    # For standalone testing
    import logging
    central_logger = type('Logger', (), {'get_logger': lambda self, name: logging.getLogger(name)})()
    from reconnection_exceptions import (
        CallbackCircuitBreakerOpen,
        CriticalCallbackFailure,
        StateNotificationFailure,
    )
    from reconnection_types import (
        CallbackCircuitBreaker,
        CallbackCriticality,
        CallbackFailure,
        CallbackType,
    )

logger = central_logger.get_logger(__name__)


class CallbackFailureManager:
    """Manages callback failures and circuit breaking."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.circuit_breakers: Dict[CallbackType, CallbackCircuitBreaker] = {}
        self.criticality_map = self._initialize_criticality_map()
        self.failure_history: List[CallbackFailure] = []
        self._setup_circuit_breakers()

    def _initialize_criticality_map(self) -> Dict[CallbackType, CallbackCriticality]:
        """Initialize callback criticality mapping."""
        return {
            CallbackType.STATE_CHANGE: CallbackCriticality.CRITICAL,
            CallbackType.CONNECT: CallbackCriticality.IMPORTANT,
            CallbackType.DISCONNECT: CallbackCriticality.NON_CRITICAL
        }

    def _setup_circuit_breakers(self) -> None:
        """Setup circuit breakers for each callback type."""
        for callback_type in CallbackType:
            self.circuit_breakers[callback_type] = CallbackCircuitBreaker()

    async def execute_callback_safely(self, callback_type: CallbackType, 
                                    callback: Callable, *args, **kwargs) -> None:
        """Execute callback with failure handling and circuit breaking."""
        if self._is_circuit_breaker_open(callback_type):
            raise CallbackCircuitBreakerOpen(callback_type, 
                                           self.circuit_breakers[callback_type].failure_count)
        
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
            await self._handle_callback_success(callback_type)
        except Exception as e:
            await self._handle_callback_failure(callback_type, e)

    def _is_circuit_breaker_open(self, callback_type: CallbackType) -> bool:
        """Check if circuit breaker is open."""
        breaker = self.circuit_breakers[callback_type]
        if not breaker.is_open:
            return False
        return not self._should_reset_circuit_breaker(breaker)

    def _should_reset_circuit_breaker(self, breaker: CallbackCircuitBreaker) -> bool:
        """Check if circuit breaker should be reset."""
        if not breaker.last_failure_time:
            return True
        elapsed_ms = self._calculate_elapsed_ms(breaker.last_failure_time)
        return elapsed_ms > breaker.reset_timeout_ms

    def _calculate_elapsed_ms(self, start_time: datetime) -> float:
        """Calculate elapsed milliseconds from start time."""
        return (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    async def _handle_callback_success(self, callback_type: CallbackType) -> None:
        """Handle successful callback execution."""
        breaker = self.circuit_breakers[callback_type]
        if breaker.is_open:
            await self._reset_circuit_breaker(callback_type)

    async def _reset_circuit_breaker(self, callback_type: CallbackType) -> None:
        """Reset circuit breaker after successful execution."""
        breaker = self.circuit_breakers[callback_type]
        breaker.is_open = False
        breaker.failure_count = 0
        breaker.recent_failures.clear()
        logger.info(f"Reset {callback_type.value} circuit breaker for {self.connection_id}")

    async def _handle_callback_failure(self, callback_type: CallbackType, error: Exception) -> None:
        """Handle callback failure with criticality and circuit breaking."""
        failure = self._create_failure_record(callback_type, error)
        self._record_failure(callback_type, failure)
        await self._update_circuit_breaker(callback_type, failure)
        await self._propagate_failure_if_critical(callback_type, error)

    def _create_failure_record(self, callback_type: CallbackType, error: Exception) -> CallbackFailure:
        """Create failure record for tracking."""
        return CallbackFailure(
            callback_type=callback_type,
            timestamp=datetime.now(timezone.utc),
            error_message=str(error),
            criticality=self.criticality_map[callback_type]
        )

    def _record_failure(self, callback_type: CallbackType, failure: CallbackFailure) -> None:
        """Record failure in history."""
        self.failure_history.append(failure)
        self._cleanup_old_failures()

    def _cleanup_old_failures(self) -> None:
        """Keep only recent failure history."""
        if len(self.failure_history) > 100:
            self.failure_history = self.failure_history[-50:]

    async def _update_circuit_breaker(self, callback_type: CallbackType, 
                                    failure: CallbackFailure) -> None:
        """Update circuit breaker state."""
        breaker = self.circuit_breakers[callback_type]
        breaker.failure_count += 1
        breaker.last_failure_time = failure.timestamp
        breaker.recent_failures.append(failure)
        await self._check_circuit_breaker_threshold(callback_type, breaker)

    async def _check_circuit_breaker_threshold(self, callback_type: CallbackType,
                                             breaker: CallbackCircuitBreaker) -> None:
        """Check if circuit breaker threshold is exceeded."""
        if breaker.failure_count >= breaker.failure_threshold:
            breaker.is_open = True
            logger.warning(f"Opened {callback_type.value} circuit breaker for {self.connection_id}")

    async def _propagate_failure_if_critical(self, callback_type: CallbackType, 
                                           error: Exception) -> None:
        """Propagate failure if callback is critical."""
        criticality = self.criticality_map[callback_type]
        if criticality == CallbackCriticality.CRITICAL:
            if callback_type == CallbackType.STATE_CHANGE:
                raise StateNotificationFailure(error, self.connection_id)
            raise CriticalCallbackFailure(callback_type, error)
        elif criticality == CallbackCriticality.IMPORTANT:
            logger.warning(f"Important {callback_type.value} callback failed for {self.connection_id}: {error}")
        else:
            logger.info(f"Non-critical {callback_type.value} callback failed for {self.connection_id}: {error}")

    def get_failure_metrics(self) -> Dict[str, Any]:
        """Get callback failure metrics."""
        return {
            'total_failures': len(self.failure_history),
            'critical_failures': sum(1 for f in self.failure_history 
                                   if f.criticality == CallbackCriticality.CRITICAL),
            'circuit_breakers': {
                cb_type.value: {
                    'is_open': breaker.is_open,
                    'failure_count': breaker.failure_count,
                    'recent_failures': len(breaker.recent_failures)
                } for cb_type, breaker in self.circuit_breakers.items()
            }
        }

    def set_callback_criticality(self, callback_type: CallbackType, 
                                criticality: CallbackCriticality) -> None:
        """Update callback criticality level."""
        self.criticality_map[callback_type] = criticality
        logger.info(f"Updated {callback_type.value} criticality to {criticality.value}")