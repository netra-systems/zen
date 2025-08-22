"""WebSocket State Synchronization Callback Handler.

Handles callback execution with proper exception handling and criticality classification.
"""

import asyncio
from typing import Callable, Optional, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.sync_types import CriticalCallbackFailure

logger = central_logger.get_logger(__name__)


class CallbackHandler:
    """Handles callback execution with exception handling."""
    
    def __init__(self):
        """Initialize callback handler."""
        pass
    
    async def execute_callbacks(self, callbacks: Set[Callable], connection_id: str, event_type: str) -> None:
        """Execute callbacks with proper exception handling."""
        if not callbacks:
            return
        
        callback_tasks = await self._create_callback_tasks(callbacks, connection_id, event_type)
        if callback_tasks:
            await self._execute_callback_tasks(callback_tasks, connection_id)
    
    async def _create_callback_tasks(self, callbacks: Set[Callable], connection_id: str, event_type: str) -> list:
        """Create tasks for all callbacks."""
        callback_tasks = []
        for callback in callbacks:
            task = await self._process_single_callback(callback, connection_id, event_type)
            if task:
                callback_tasks.append(task)
        return callback_tasks
    
    async def _process_single_callback(self, callback: Callable, connection_id: str, event_type: str) -> Optional[asyncio.Task]:
        """Process single callback with error handling."""
        try:
            return await self._create_single_callback_task(callback, connection_id, event_type)
        except Exception as e:
            logger.error(f"Error creating callback task for {connection_id}: {e}")
            return None
    
    async def _create_single_callback_task(self, callback: Callable, connection_id: str, event_type: str) -> Optional[asyncio.Task]:
        """Create task for a single callback."""
        if not callable(callback):
            raise TypeError(f"Callback must be callable, got {type(callback)}")
        
        if asyncio.iscoroutinefunction(callback):
            return asyncio.create_task(callback(connection_id, event_type))
        else:
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(None, callback, connection_id, event_type)
    
    async def _execute_callback_tasks(self, callback_tasks: list, connection_id: str) -> None:
        """Execute callback tasks with explicit exception handling."""
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*callback_tasks, return_exceptions=True),
                timeout=5.0
            )
            await self._inspect_callback_results(results, connection_id)
        except CriticalCallbackFailure:
            raise  # Propagate critical failures
        except (asyncio.TimeoutError, Exception) as e:
            await self._handle_callback_error(e, connection_id)
    
    async def _inspect_callback_results(self, results: list, connection_id: str) -> None:
        """Inspect callback results for exceptions."""
        failures = [r for r in results if isinstance(r, Exception)]
        if not failures:
            return
        
        await self._handle_callback_failures(failures, connection_id)
    
    async def _handle_callback_failures(self, failures: list, connection_id: str) -> None:
        """Handle callback failures by criticality."""
        for failure in failures:
            await self._log_callback_failure(failure, connection_id)
        
        critical_failures = [f for f in failures if self._is_critical_failure(f)]
        if critical_failures:
            raise CriticalCallbackFailure(
                f"Critical callback failures for {connection_id}: {len(critical_failures)} failures"
            )
    
    def _is_critical_failure(self, failure: Exception) -> bool:
        """Determine if failure is critical."""
        critical_types = (ConnectionError, TimeoutError, CriticalCallbackFailure)
        return isinstance(failure, critical_types)
    
    async def _log_callback_failure(self, failure: Exception, connection_id: str) -> None:
        """Log callback failure based on criticality."""
        if self._is_critical_failure(failure):
            logger.error(f"CRITICAL callback failure for {connection_id}: {failure}")
        else:
            logger.warning(f"Non-critical callback failure for {connection_id}: {failure}")
    
    async def _handle_callback_error(self, error: Exception, connection_id: str) -> None:
        """Handle callback execution errors."""
        if isinstance(error, asyncio.TimeoutError):
            logger.warning(f"Callback timeout for connection {connection_id}")
        else:
            logger.error(f"Callback execution error for {connection_id}: {error}")