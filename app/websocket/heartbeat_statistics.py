"""Heartbeat statistics collection and reporting."""

from typing import Dict, Any, Optional
from datetime import datetime


class HeartbeatStatistics:
    """Manages heartbeat statistics collection and reporting."""
    
    def __init__(self):
        """Initialize statistics tracking."""
        self._stats = self._create_initial_stats()
    
    def _create_initial_stats(self) -> Dict[str, int]:
        """Create initial statistics dictionary."""
        return {
            "total_pings_sent": 0,
            "total_pongs_received": 0,
            "connections_timed_out": 0,
            "heartbeat_failures": 0
        }
    
    def increment_ping_sent(self) -> None:
        """Increment ping sent counter."""
        self._stats["total_pings_sent"] += 1
    
    def increment_pong_received(self) -> None:
        """Increment pong received counter."""
        self._stats["total_pongs_received"] += 1
    
    def increment_timeout(self) -> None:
        """Increment timeout counter."""
        self._stats["connections_timed_out"] += 1
    
    def increment_failure(self) -> None:
        """Increment failure counter."""
        self._stats["heartbeat_failures"] += 1
    
    def get_base_stats(self, active_count: int, missed_total: int) -> Dict[str, Any]:
        """Get base statistics with current counts."""
        base = self._stats.copy()
        base["active_heartbeats"] = active_count
        base["total_missed_heartbeats"] = missed_total
        return base
    
    def get_config_stats(self, config) -> Dict[str, Any]:
        """Get configuration statistics."""
        return {
            "interval_seconds": config.interval_seconds,
            "timeout_seconds": config.timeout_seconds,
            "max_missed_heartbeats": config.max_missed_heartbeats
        }
    
    def build_connection_info(self, conn_id: str, conn_info, 
                            missed_count: int, config, task) -> Dict[str, Any]:
        """Build heartbeat info for specific connection."""
        return {
            "connection_id": conn_id,
            "is_alive": True,  # Determined by caller
            "last_ping": self._format_timestamp(conn_info.last_ping),
            "last_pong": self._format_timestamp(conn_info.last_pong),
            "missed_heartbeats": missed_count,
            "max_missed_heartbeats": config.max_missed_heartbeats,
            "heartbeat_active": not task.done()
        }
    
    def _format_timestamp(self, timestamp: Optional[datetime]) -> Optional[str]:
        """Format timestamp for output."""
        return timestamp.isoformat() if timestamp else None