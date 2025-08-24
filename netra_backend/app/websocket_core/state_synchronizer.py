"""WebSocket State Synchronizer

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Connection reliability and state consistency
- Value Impact: Ensures WebSocket connections maintain consistent state
- Strategic Impact: Prevents state desynchronization issues
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.sync_types import CriticalCallbackFailure

logger = central_logger.get_logger(__name__)


class ConnectionStateSynchronizer:
    """Handles synchronization of WebSocket connection state."""
    
    def __init__(self, connection_manager: Any):
        """Initialize the state synchronizer.
        
        Args:
            connection_manager: The WebSocket connection manager
        """
        self.connection_manager = connection_manager
        self._callback_handler = self
        self._sync_callbacks: Dict[str, List[Callable]] = {}
        
    def _is_critical_failure(self, exception: Exception) -> bool:
        """Determine if an exception represents a critical failure.
        
        Args:
            exception: The exception to classify
            
        Returns:
            True if the exception is critical, False otherwise
        """
        return isinstance(exception, (ConnectionError, TimeoutError, CriticalCallbackFailure))
        
    def register_sync_callback(self, connection_id: str, callback: Callable) -> None:
        """Register a synchronization callback for a connection.
        
        Args:
            connection_id: The connection identifier
            callback: The callback function to register
        """
        if connection_id not in self._sync_callbacks:
            self._sync_callbacks[connection_id] = []
        self._sync_callbacks[connection_id].append(callback)
        
    async def _notify_sync_callbacks(self, connection_id: str, event_type: str) -> None:
        """Notify all registered callbacks for a connection.
        
        Args:
            connection_id: The connection identifier
            event_type: The type of synchronization event
            
        Raises:
            CriticalCallbackFailure: When critical callbacks fail
        """
        if connection_id not in self._sync_callbacks:
            return
            
        critical_failures = []
        
        for callback in self._sync_callbacks[connection_id]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(connection_id, event_type)
                elif callable(callback):
                    callback(connection_id, event_type)
                else:
                    logger.warning(f"Invalid callback type: {type(callback)}")
            except Exception as e:
                # Classify exception as critical or non-critical
                if self._is_critical_failure(e):
                    critical_failures.append((callback.__name__ if hasattr(callback, '__name__') else str(callback), e))
                else:
                    logger.error(f"Non-critical callback execution failed: {e}")
        
        if critical_failures:
            failure_details = f"Critical callback failures for {connection_id}: {critical_failures}"
            raise CriticalCallbackFailure(
                callback_name=f"multiple_callbacks_{connection_id}",
                original_error=critical_failures[0][1],
                context={"connection_id": connection_id, "event_type": event_type, "failures": critical_failures}
            )
        
    async def synchronize_state(self, callbacks: List[Callable] = None) -> None:
        """Synchronize connection state with optional callbacks.
        
        Args:
            callbacks: Optional list of callbacks to execute
        """
        if not callbacks:
            return
            
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                elif callable(callback):
                    callback()
                else:
                    logger.warning(f"Invalid callback type: {type(callback)}")
            except Exception as e:
                logger.error(f"Callback execution failed: {e}")


# Backward compatibility alias
StateSynchronizer = ConnectionStateSynchronizer
