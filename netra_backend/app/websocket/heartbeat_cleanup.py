"""Heartbeat cleanup and shutdown operations."""

import asyncio
from typing import Dict, List

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HeartbeatCleanup:
    """Handles heartbeat cleanup and shutdown operations."""
    
    def __init__(self, connection_manager, heartbeat_tasks: Dict[str, asyncio.Task], 
                 missed_heartbeats: Dict[str, int]):
        """Initialize cleanup handler."""
        self.connection_manager = connection_manager
        self.heartbeat_tasks = heartbeat_tasks
        self.missed_heartbeats = missed_heartbeats
    
    async def cleanup_dead_connections(self, is_alive_callback) -> None:
        """Check all monitored connections and clean up dead ones."""
        dead_connections = self._identify_dead_connections(is_alive_callback)
        await self._cleanup_identified_connections(dead_connections)
    
    def _identify_dead_connections(self, is_alive_callback) -> List[str]:
        """Identify connections that are dead."""
        dead_connections = []
        for connection_id, task in list(self.heartbeat_tasks.items()):
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            if not conn_info or not is_alive_callback(conn_info):
                dead_connections.append(connection_id)
        return dead_connections
    
    async def _cleanup_identified_connections(self, dead_connections: List[str]) -> None:
        """Clean up identified dead connections."""
        for connection_id in dead_connections:
            await self._stop_heartbeat_for_connection(connection_id)
            logger.info(f"Cleaned up heartbeat for dead connection {connection_id}")
    
    async def _stop_heartbeat_for_connection(self, connection_id: str) -> None:
        """Stop heartbeat monitoring for a connection."""
        if connection_id not in self.heartbeat_tasks:
            return
        task = self.heartbeat_tasks[connection_id]
        await self._safely_cancel_task(task, connection_id)
        self._cleanup_tracking_data(connection_id)
    
    async def _safely_cancel_task(self, task: asyncio.Task, connection_id: str) -> None:
        """Safely cancel task with error handling."""
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error stopping heartbeat for {connection_id}: {e}")
    
    def _cleanup_tracking_data(self, connection_id: str) -> None:
        """Clean up tracking data for connection."""
        self.heartbeat_tasks.pop(connection_id, None)
        self.missed_heartbeats.pop(connection_id, None)
    
    async def shutdown_all_heartbeats(self, statistics) -> None:
        """Stop all heartbeat monitoring."""
        logger.info("Shutting down all heartbeat monitoring...")
        tasks_to_cancel = self._gather_tasks_to_cancel()
        await self._cancel_all_tasks(tasks_to_cancel)
        self._clear_all_tracking_data()
        self._log_shutdown_complete(statistics)
    
    def _gather_tasks_to_cancel(self) -> List[asyncio.Task]:
        """Gather all active tasks that need cancellation."""
        tasks_to_cancel = []
        for connection_id, task in self.heartbeat_tasks.items():
            if not task.done():
                task.cancel()
                tasks_to_cancel.append(task)
        return tasks_to_cancel
    
    async def _cancel_all_tasks(self, tasks_to_cancel: List[asyncio.Task]) -> None:
        """Cancel all tasks and wait for completion."""
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
    
    def _clear_all_tracking_data(self) -> None:
        """Clear all heartbeat tracking data."""
        self.heartbeat_tasks.clear()
        self.missed_heartbeats.clear()
    
    def _log_shutdown_complete(self, statistics) -> None:
        """Log shutdown completion with final stats."""
        active_count = len(self.heartbeat_tasks)
        missed_total = sum(self.missed_heartbeats.values())
        stats = statistics.get_base_stats(active_count, missed_total)
        logger.info(f"Heartbeat shutdown complete. Final stats: {stats}")
    
    def cleanup_connection_resources(self, conn_info) -> None:
        """Clean up heartbeat resources for connection."""
        self.heartbeat_tasks.pop(conn_info.connection_id, None)
        self.missed_heartbeats.pop(conn_info.connection_id, None)