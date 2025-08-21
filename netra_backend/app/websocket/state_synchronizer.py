"""WebSocket Connection State Synchronization.

Ensures consistent connection state tracking across all components
and prevents desynchronization issues.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Callable, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.connection import ConnectionInfo, ConnectionManager
from netra_backend.app.error_types import ErrorSeverity
from netra_backend.app.sync_types import SyncState, StateCheckpoint
from netra_backend.app.callback_handler import CallbackHandler

logger = central_logger.get_logger(__name__)


class ConnectionStateSynchronizer:
    """Manages connection state synchronization."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize state synchronizer."""
        self.connection_manager = connection_manager
        self.checkpoints: Dict[str, StateCheckpoint] = {}
        self.sync_callbacks: Dict[str, Set[Callable]] = {}
        self.desync_threshold_seconds = 30
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        self._sync_interval = 5  # Check every 5 seconds instead of 10
        self._max_concurrent_checks = 10  # Limit concurrent checks
        self._callback_handler = CallbackHandler()
    
    async def start_monitoring(self) -> None:
        """Start state synchronization monitoring."""
        if self._running:
            return
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Connection state synchronizer started")
    
    async def stop_monitoring(self) -> None:
        """Stop state synchronization monitoring."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Connection state synchronizer stopped")
    
    async def register_connection(self, conn_info: ConnectionInfo) -> None:
        """Register connection for state monitoring."""
        checkpoint = StateCheckpoint(
            connection_id=conn_info.connection_id,
            websocket_state=conn_info.websocket.client_state.name,
            internal_state="connected"
        )
        self.checkpoints[conn_info.connection_id] = checkpoint
        logger.debug(f"Registered connection {conn_info.connection_id} for state sync")
    
    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection from state monitoring."""
        self.checkpoints.pop(connection_id, None)
        self.sync_callbacks.pop(connection_id, None)
        logger.debug(f"Unregistered connection {connection_id} from state sync")
    
    async def check_connection_sync(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection state is synchronized."""
        registration_result = await self._validate_connection_registration(conn_info)
        if registration_result:
            return registration_result
        
        checkpoint = self.checkpoints[conn_info.connection_id]
        return await self._check_state_and_activity(conn_info, checkpoint)
    
    async def _validate_connection_registration(self, conn_info: ConnectionInfo) -> Optional[bool]:
        """Validate and handle connection registration."""
        if conn_info.connection_id not in self.checkpoints:
            await self.register_connection(conn_info)
            return True
        return None
    
    async def _check_state_and_activity(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> bool:
        """Check state mismatch and activity timeout."""
        current_ws_state = conn_info.websocket.client_state.name
        
        if checkpoint.websocket_state != current_ws_state:
            await self._handle_state_desync(conn_info, checkpoint)
            return False
        
        return await self._check_activity_timeout(conn_info, checkpoint)
    
    async def _check_activity_timeout(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> bool:
        """Check for activity timeout and handle if needed."""
        time_since_activity = (datetime.now(timezone.utc) - checkpoint.last_activity).total_seconds()
        if time_since_activity > self.desync_threshold_seconds:
            await self._handle_activity_timeout(conn_info, checkpoint)
            return False
        return True
    
    async def update_connection_activity(self, connection_id: str) -> None:
        """Update connection activity timestamp."""
        if connection_id in self.checkpoints:
            self.checkpoints[connection_id].last_activity = datetime.now(timezone.utc)
    
    def register_sync_callback(self, connection_id: str, callback: Callable) -> None:
        """Register callback for synchronization events."""
        if connection_id not in self.sync_callbacks:
            self.sync_callbacks[connection_id] = set()
        self.sync_callbacks[connection_id].add(callback)
    
    async def _sync_loop(self) -> None:
        """Main synchronization monitoring loop with resilience."""
        retry_count = 0
        while self._running:
            try:
                retry_count = await self._handle_sync_loop_iteration(retry_count)
            except asyncio.CancelledError:
                break
            except Exception as e:
                retry_count = await self._handle_sync_error(e, retry_count)
    
    async def _handle_sync_loop_iteration(self, retry_count: int) -> int:
        """Handle single sync loop iteration."""
        await self._perform_sync_check_concurrent()
        await asyncio.sleep(self._sync_interval)
        return 0  # Reset retry count on success
    
    async def _perform_sync_check_concurrent(self) -> None:
        """Perform concurrent synchronization checks with limits."""
        connection_items = list(self.checkpoints.items())
        if not connection_items:
            return
        
        tasks = await self._create_concurrent_check_tasks(connection_items)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _create_concurrent_check_tasks(self, connection_items: list) -> list:
        """Create concurrent check tasks with semaphore protection."""
        semaphore = asyncio.Semaphore(self._max_concurrent_checks)
        tasks = [self._check_single_connection(connection_id, semaphore) 
                for connection_id, _ in connection_items]
        return tasks
    
    async def _handle_state_desync(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> None:
        """Handle connection state desynchronization."""
        logger.warning(
            f"State desync detected for {conn_info.connection_id}: "
            f"checkpoint={checkpoint.websocket_state} vs actual={conn_info.websocket.client_state.name}"
        )
        
        await self._update_desync_state(conn_info, checkpoint)
    
    async def _update_desync_state(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> None:
        """Update desynchronization state and notify."""
        checkpoint.sync_status = SyncState.DESYNCED
        checkpoint.websocket_state = conn_info.websocket.client_state.name
        
        # Notify callbacks
        await self._notify_sync_callbacks(conn_info.connection_id, "state_desync")
    
    async def _handle_activity_timeout(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> None:
        """Handle connection activity timeout."""
        logger.warning(f"Activity timeout for {conn_info.connection_id}")
        
        checkpoint.sync_status = SyncState.DESYNCED
        
        # Notify callbacks
        await self._notify_sync_callbacks(conn_info.connection_id, "activity_timeout")
    
    async def _check_single_connection(self, connection_id: str, semaphore: asyncio.Semaphore) -> None:
        """Check single connection with semaphore protection."""
        async with semaphore:
            try:
                await self._perform_connection_check(connection_id)
            except Exception as e:
                logger.error(f"Error checking connection {connection_id}: {e}")
    
    async def _perform_connection_check(self, connection_id: str) -> None:
        """Perform the actual connection check."""
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            await self.unregister_connection(connection_id)
            return
        await self.check_connection_sync(conn_info)
    
    async def _notify_sync_callbacks(self, connection_id: str, event_type: str) -> None:
        """Notify registered callbacks about sync events."""
        callbacks = self.sync_callbacks.get(connection_id, set())
        if callbacks:
            await self._callback_handler.execute_callbacks(callbacks, connection_id, event_type)
    
    async def _handle_sync_error(self, error: Exception, retry_count: int) -> int:
        """Handle sync loop error with retry logic."""
        retry_count += 1
        backoff_time = self._calculate_backoff_time(retry_count)
        logger.error(f"Sync loop error (attempt {retry_count}): {error}")
        
        retry_count = self._check_max_retries(retry_count)
        await asyncio.sleep(backoff_time)
        return retry_count
    
    def _calculate_backoff_time(self, retry_count: int) -> float:
        """Calculate exponential backoff time."""
        return min(5 * (2 ** retry_count), 60)
    
    def _check_max_retries(self, retry_count: int) -> int:
        """Check and reset retry count if max retries exceeded."""
        if retry_count >= 3:  # max_retries
            logger.error("Max retries exceeded, resetting sync state")
            return 0
        return retry_count
    
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        sync_counts = self._calculate_sync_statistics()
        return self._build_sync_stats_dict(sync_counts)
    
    def _build_sync_stats_dict(self, sync_counts: Dict[str, Any]) -> Dict[str, Any]:
        """Build synchronization statistics dictionary."""
        return {
            "total_monitored_connections": sync_counts["total"],
            "synced_connections": sync_counts["synced"],
            "desynced_connections": sync_counts["desynced"],
            "sync_rate": sync_counts["rate"],
            "monitoring_active": self._running
        }
    
    def _calculate_sync_statistics(self) -> Dict[str, Any]:
        """Calculate synchronization statistics."""
        total_connections = len(self.checkpoints)
        synced_count = sum(1 for cp in self.checkpoints.values() if cp.sync_status == SyncState.SYNCED)
        desynced_count = total_connections - synced_count
        sync_rate = synced_count / total_connections if total_connections > 0 else 1.0
        
        return {
            "total": total_connections, 
            "synced": synced_count, 
            "desynced": desynced_count, 
            "rate": sync_rate
        }