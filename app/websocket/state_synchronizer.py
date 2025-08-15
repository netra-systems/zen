"""WebSocket Connection State Synchronization.

Ensures consistent connection state tracking across all components
and prevents desynchronization issues.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from app.logging_config import central_logger
from .connection import ConnectionInfo, ConnectionManager
from .error_types import ErrorSeverity

logger = central_logger.get_logger(__name__)


class SyncState(str, Enum):
    """Connection synchronization states."""
    SYNCED = "synced"
    DESYNCED = "desynced"
    SYNCING = "syncing"
    FAILED = "failed"


@dataclass
class StateCheckpoint:
    """Connection state checkpoint."""
    connection_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    websocket_state: str = ""
    internal_state: str = ""
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sync_status: SyncState = SyncState.SYNCED


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
        if conn_info.connection_id not in self.checkpoints:
            await self.register_connection(conn_info)
            return True
        
        checkpoint = self.checkpoints[conn_info.connection_id]
        current_ws_state = conn_info.websocket.client_state.name
        
        # Check for state mismatch
        if checkpoint.websocket_state != current_ws_state:
            await self._handle_state_desync(conn_info, checkpoint)
            return False
        
        # Check for activity timeout
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
        """Main synchronization monitoring loop."""
        while self._running:
            try:
                await self._perform_sync_check()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_sync_check(self) -> None:
        """Perform synchronization check on all connections."""
        for connection_id, checkpoint in list(self.checkpoints.items()):
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            
            if not conn_info:
                # Connection no longer exists
                await self.unregister_connection(connection_id)
                continue
            
            await self.check_connection_sync(conn_info)
    
    async def _handle_state_desync(self, conn_info: ConnectionInfo, checkpoint: StateCheckpoint) -> None:
        """Handle connection state desynchronization."""
        logger.warning(
            f"State desync detected for {conn_info.connection_id}: "
            f"checkpoint={checkpoint.websocket_state} vs actual={conn_info.websocket.client_state.name}"
        )
        
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
    
    async def _notify_sync_callbacks(self, connection_id: str, event_type: str) -> None:
        """Notify registered callbacks about sync events."""
        callbacks = self.sync_callbacks.get(connection_id, set())
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(connection_id, event_type)
                else:
                    callback(connection_id, event_type)
            except Exception as e:
                logger.error(f"Sync callback error for {connection_id}: {e}")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        total_connections = len(self.checkpoints)
        synced_count = sum(1 for cp in self.checkpoints.values() if cp.sync_status == SyncState.SYNCED)
        desynced_count = total_connections - synced_count
        
        return {
            "total_monitored_connections": total_connections,
            "synced_connections": synced_count,
            "desynced_connections": desynced_count,
            "sync_rate": synced_count / total_connections if total_connections > 0 else 1.0,
            "monitoring_active": self._running
        }