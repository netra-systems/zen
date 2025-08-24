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
