"""Ghost Connection Management Module

Handles detection, cleanup, and monitoring of ghost WebSocket connections.
Implements atomic state management to prevent resource leaks.

Business Value: Prevents connection limit exhaustion and resource leaks
that could impact system reliability and user experience.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection_info import ConnectionInfo, ConnectionState

logger = central_logger.get_logger(__name__)


class GhostConnectionManager:
    """Manages ghost connection detection and cleanup operations."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
    async def cleanup_ghost_connections(self, all_connections: List[ConnectionInfo]) -> None:
        """Clean up ghost connections from registry."""
        ghost_connections = self._identify_ghost_connections(all_connections)
        
        for ghost_conn in ghost_connections:
            await self._handle_ghost_connection(ghost_conn)
            
    def _identify_ghost_connections(self, all_connections: List[ConnectionInfo]) -> List[ConnectionInfo]:
        """Identify ghost connections from connection list."""
        return [conn for conn in all_connections if conn.is_ghost_connection()]
        
    async def _handle_ghost_connection(self, ghost_conn: ConnectionInfo) -> None:
        """Handle cleanup of a single ghost connection."""
        user_id = ghost_conn.user_id
        if ghost_conn.should_retry_closure():
            await self._retry_connection_closure(user_id, ghost_conn)
        else:
            self._force_cleanup_connection(user_id, ghost_conn)
            
    async def _retry_connection_closure(self, user_id: str, ghost_conn: ConnectionInfo) -> None:
        """Retry closure for a failed connection."""
        if ghost_conn.transition_to_closing():
            await self._execute_atomic_connection_closure(user_id, ghost_conn)
            
    async def _execute_atomic_connection_closure(self, user_id: str, ghost_conn: ConnectionInfo) -> None:
        """Execute connection closure with atomic state management."""
        try:
            result = await self._attempt_connection_closure(ghost_conn)
            if result.success:
                ghost_conn.transition_to_closed()
            else:
                ghost_conn.transition_to_failed()
        except Exception as e:
            logger.warning(f"Exception during ghost connection closure: {e}")
            ghost_conn.transition_to_failed()
            
    async def _attempt_connection_closure(self, ghost_conn: ConnectionInfo):
        """Attempt to close ghost connection via orchestrator."""
        return await self.orchestrator.close_connection(
            ghost_conn, code=1001, reason="Ghost connection cleanup"
        )
        
    def _force_cleanup_connection(self, user_id: str, ghost_conn: ConnectionInfo) -> None:
        """Force cleanup of a ghost connection."""
        ghost_conn.transition_to_closed()
        logger.info(f"Force cleaned ghost connection {ghost_conn.connection_id}")
        
    async def get_ghost_connections_count(self, all_connections: List[ConnectionInfo]) -> int:
        """Get count of ghost connections for monitoring."""
        return len(self._identify_ghost_connections(all_connections))
        
    def get_connections_by_state(self, all_connections: List[ConnectionInfo]) -> Dict[str, int]:
        """Get connection count by state for monitoring."""
        state_counts = {state.value: 0 for state in ConnectionState}
        
        for conn in all_connections:
            state_counts[conn.state.value] += 1
            
        return state_counts


class AtomicConnectionCloser:
    """Handles atomic connection closure operations."""
    
    def __init__(self, orchestrator, ghost_manager: GhostConnectionManager):
        self.orchestrator = orchestrator
        self.ghost_manager = ghost_manager
        
    async def close_connection_atomically(self, user_id: str, conn_info: ConnectionInfo,
                                        code: int = 1000, reason: str = "Normal closure") -> bool:
        """Close connection using atomic state management."""
        if not conn_info.transition_to_closing():
            return False  # Connection already closing or failed
            
        try:
            result = await self._attempt_connection_closure(conn_info, code, reason)
            if result.success:
                conn_info.transition_to_closed()
                return True
            else:
                self._handle_failed_closure(conn_info)
                return False
        except Exception as e:
            logger.warning(f"Exception during atomic connection closure: {e}")
            self._handle_failed_closure(conn_info)
            return False
            
    async def _attempt_connection_closure(self, conn_info: ConnectionInfo, code: int, reason: str):
        """Attempt to close connection via orchestrator."""
        return await self.orchestrator.close_connection(conn_info, code, reason)
        
    def _handle_failed_closure(self, conn_info: ConnectionInfo) -> None:
        """Handle failed connection closure."""
        conn_info.transition_to_failed()
        logger.warning(f"Failed to close connection {conn_info.connection_id}, marked as failed")


class ConnectionStateMonitor:
    """Monitors connection states and provides health metrics."""
    
    def __init__(self, ghost_manager: GhostConnectionManager):
        self.ghost_manager = ghost_manager
        
    async def get_connection_health_metrics(self, all_connections: List[ConnectionInfo]) -> Dict[str, Any]:
        """Get comprehensive connection health metrics."""
        state_counts = self.ghost_manager.get_connections_by_state(all_connections)
        ghost_count = await self.ghost_manager.get_ghost_connections_count(all_connections)
        
        return {
            "total_connections": len(all_connections),
            "connections_by_state": state_counts,
            "ghost_connections": ghost_count,
            "health_status": self._determine_health_status(state_counts, ghost_count)
        }
        
    def _determine_health_status(self, state_counts: Dict[str, int], ghost_count: int) -> str:
        """Determine overall connection health status."""
        total_connections = sum(state_counts.values())
        if total_connections == 0:
            return "healthy"
            
        ghost_ratio = ghost_count / total_connections if total_connections > 0 else 0
        
        if ghost_ratio > 0.2:  # More than 20% ghost connections
            return "degraded"
        elif ghost_ratio > 0.1:  # More than 10% ghost connections
            return "warning"
        else:
            return "healthy"
            
    def get_stale_connections(self, all_connections: List[ConnectionInfo]) -> List[ConnectionInfo]:
        """Get connections that are stale and need attention."""
        stale_connections = []
        current_time = datetime.now(timezone.utc)
        
        for conn in all_connections:
            if self._is_connection_stale(conn, current_time):
                stale_connections.append(conn)
                
        return stale_connections
        
    def _is_connection_stale(self, conn: ConnectionInfo, current_time: datetime) -> bool:
        """Check if connection is stale based on timing criteria."""
        if conn.state == ConnectionState.CLOSING and conn.last_failure_time:
            time_diff = (current_time - conn.last_failure_time).total_seconds()
            return time_diff > 60  # 60 seconds timeout
        return False