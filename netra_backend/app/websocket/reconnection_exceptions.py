"""WebSocket reconnection exceptions.

Custom exceptions for callback failure propagation and circuit breaker handling.
"""

from typing import List, Optional
try:
    from .reconnection_types import CallbackType, CallbackFailure
except ImportError:
    from reconnection_types import CallbackType, CallbackFailure


class ReconnectionException(Exception):
    """Base exception for reconnection failures."""
    pass


class CriticalCallbackFailure(ReconnectionException):
    """Critical callback failure that should affect system behavior."""
    
    def __init__(self, callback_type: CallbackType, original_error: Exception):
        self.callback_type = callback_type
        self.original_error = original_error
        super().__init__(f"Critical {callback_type.value} callback failed: {original_error}")


class CallbackCircuitBreakerOpen(ReconnectionException):
    """Circuit breaker is open due to repeated callback failures."""
    
    def __init__(self, callback_type: CallbackType, failure_count: int):
        self.callback_type = callback_type
        self.failure_count = failure_count
        super().__init__(f"{callback_type.value} circuit breaker open after {failure_count} failures")


class StateNotificationFailure(ReconnectionException):
    """State change notification failed critically."""
    
    def __init__(self, original_error: Exception, connection_id: str):
        self.original_error = original_error
        self.connection_id = connection_id
        super().__init__(f"State notification failed for {connection_id}: {original_error}")


class CallbackBatchFailure(ReconnectionException):
    """Multiple callback failures occurred."""
    
    def __init__(self, failures: List[CallbackFailure]):
        self.failures = failures
        self.critical_count = sum(1 for f in failures if f.criticality.value == "critical")
        super().__init__(f"Batch callback failure: {len(failures)} total, {self.critical_count} critical")