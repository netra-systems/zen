"""Callback execution helper for WebSocket reconnection.

Handles safe callback execution with failure propagation.
"""

from typing import Callable, Optional
from app.logging_config import central_logger
from .reconnection_types import DisconnectReason, CallbackType, ReconnectionState
from .callback_failure_manager import CallbackFailureManager
from .reconnection_exceptions import StateNotificationFailure, CriticalCallbackFailure

logger = central_logger.get_logger(__name__)


class CallbackExecutor:
    """Executes callbacks with proper failure handling."""
    
    def __init__(self, connection_id: str, failure_manager: CallbackFailureManager):
        self.connection_id = connection_id
        self.failure_manager = failure_manager
        
    async def execute_state_change(self, callback: Callable, state: ReconnectionState) -> None:
        """Execute state change callback with critical failure propagation."""
        if not callback:
            return
            
        try:
            await self.failure_manager.execute_callback_safely(
                CallbackType.STATE_CHANGE, 
                callback, 
                self.connection_id, 
                state
            )
        except (StateNotificationFailure, CriticalCallbackFailure):
            raise
            
    async def execute_connect(self, callback: Callable) -> None:
        """Execute connect callback with failure handling."""
        if not callback:
            return
            
        await self.failure_manager.execute_callback_safely(
            CallbackType.CONNECT,
            callback,
            self.connection_id
        )
        
    async def execute_disconnect(self, callback: Callable, reason: DisconnectReason) -> None:
        """Execute disconnect callback with failure handling."""
        if not callback:
            return
            
        await self.failure_manager.execute_callback_safely(
            CallbackType.DISCONNECT,
            callback,
            self.connection_id,
            reason
        )