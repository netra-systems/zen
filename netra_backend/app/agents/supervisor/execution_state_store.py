"""ExecutionStateStore for global monitoring infrastructure.

This module provides the ExecutionStateStore class that tracks executions across
all users for monitoring, analytics, and system health purposes. This is separate
from execution state and does not interfere with user isolation.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Monitoring & Analytics
- Value Impact: Enables system-wide monitoring and performance optimization
- Strategic Impact: Critical for production operations and capacity planning

Key Features:
- Global execution tracking for monitoring (not for runtime logic)
- User-aggregated statistics for analytics
- System health metrics and alerts
- Performance trend analysis
- Capacity planning data
- No impact on user isolation (monitoring only)
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a single execution for monitoring."""
    execution_id: str
    user_id: str
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserStats:
    """Statistics for a single user."""
    user_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    concurrent_executions: int = 0
    last_execution_time: Optional[datetime] = None
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SystemStats:
    """System-wide execution statistics."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    concurrent_executions: int = 0
    active_users: int = 0
    avg_execution_time: float = 0.0
    executions_per_minute: float = 0.0
    peak_concurrent_executions: int = 0
    uptime_seconds: float = 0.0


class ExecutionStateStore:
    """Global execution monitoring store.
    
    This store tracks executions globally for monitoring and analytics purposes.
    It does NOT interfere with execution logic or user isolation. It's purely
    for observability and system health monitoring.
    
    Key Design Principles:
    - Monitoring only (no impact on execution logic)
    - User privacy-aware (aggregated stats only)
    - Performance optimized (async, bounded memory)
    - Thread-safe for concurrent access
    - Automatic cleanup of old data
    """
    
    MAX_RECORDS = 10000  # Maximum execution records to keep
    MAX_USER_STATS = 1000  # Maximum user stat records
    CLEANUP_INTERVAL = 300  # Cleanup every 5 minutes
    RECORD_TTL_HOURS = 24  # Keep records for 24 hours
    
    def __init__(self):
        """Initialize the execution state store."""
        # Execution records (bounded for memory management)
        self._execution_records: Dict[str, ExecutionRecord] = {}
        self._execution_queue = deque(maxlen=self.MAX_RECORDS)
        
        # User statistics (aggregated)
        self._user_stats: Dict[str, UserStats] = {}
        
        # System-wide metrics
        self._system_stats = SystemStats()
        self._start_time = datetime.now(timezone.utc)
        
        # Performance tracking
        self._recent_executions = deque(maxlen=100)  # Last 100 executions for rate calculation
        self._concurrent_tracking: Dict[str, Set[str]] = defaultdict(set)  # user_id -> set of execution_ids
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        logger.info("ExecutionStateStore initialized for global monitoring")
    
    async def record_execution_start(self, 
                                   execution_id: str,
                                   user_context: UserExecutionContext,
                                   agent_name: str,
                                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record the start of an execution.
        
        Args:
            execution_id: Unique execution identifier
            user_context: User execution context (for user_id only)
            agent_name: Name of the agent being executed
            metadata: Optional execution metadata
        """
        try:
            async with self._lock:
                started_at = datetime.now(timezone.utc)
                
                # Create execution record
                record = ExecutionRecord(
                    execution_id=execution_id,
                    user_id=user_context.user_id,
                    agent_name=agent_name,
                    started_at=started_at,
                    metadata=metadata or {}
                )
                
                # Store record
                self._execution_records[execution_id] = record
                self._execution_queue.append(execution_id)
                
                # Update user stats
                await self._update_user_stats_start(user_context.user_id, started_at)
                
                # Update system stats
                self._system_stats.total_executions += 1
                self._system_stats.concurrent_executions += 1
                
                # Track concurrent executions per user
                self._concurrent_tracking[user_context.user_id].add(execution_id)
                
                # Update peak concurrent if needed
                if self._system_stats.concurrent_executions > self._system_stats.peak_concurrent_executions:
                    self._system_stats.peak_concurrent_executions = self._system_stats.concurrent_executions
                
                # Start cleanup task if not running
                if not self._cleanup_task:
                    self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                
                logger.debug(f"Recorded execution start: {execution_id} (user: {user_context.user_id})")
                
        except Exception as e:
            logger.error(f"Error recording execution start: {e}")
    
    async def record_execution_complete(self, 
                                      execution_id: str,
                                      result: AgentExecutionResult) -> None:
        """Record the completion of an execution.
        
        Args:
            execution_id: Unique execution identifier
            result: Execution result
        """
        try:
            async with self._lock:
                completed_at = datetime.now(timezone.utc)
                
                # Get execution record
                record = self._execution_records.get(execution_id)
                if not record:
                    logger.warning(f"No execution record found for {execution_id}")
                    return
                
                # Update record
                record.completed_at = completed_at
                record.duration_seconds = result.execution_time or (
                    (completed_at - record.started_at).total_seconds()
                )
                record.success = result.success
                record.error = result.error
                
                # Update user stats
                await self._update_user_stats_complete(
                    record.user_id, record.duration_seconds, result.success
                )
                
                # Update system stats
                self._system_stats.concurrent_executions -= 1
                if result.success:
                    self._system_stats.successful_executions += 1
                else:
                    self._system_stats.failed_executions += 1
                
                # Update concurrent tracking
                if record.user_id in self._concurrent_tracking:
                    self._concurrent_tracking[record.user_id].discard(execution_id)
                
                # Track for rate calculation
                self._recent_executions.append(completed_at)
                
                logger.debug(f"Recorded execution complete: {execution_id} "
                           f"(duration: {record.duration_seconds:.2f}s, success: {result.success})")
                
        except Exception as e:
            logger.error(f"Error recording execution complete: {e}")
    
    async def _update_user_stats_start(self, user_id: str, started_at: datetime) -> None:
        """Update user statistics on execution start."""
        if user_id not in self._user_stats:
            if len(self._user_stats) >= self.MAX_USER_STATS:
                # Remove oldest user stats to prevent memory bloat
                oldest_user = min(self._user_stats.keys(), 
                                key=lambda u: self._user_stats[u].first_seen)
                del self._user_stats[oldest_user]
                logger.debug(f"Removed oldest user stats for {oldest_user}")
            
            self._user_stats[user_id] = UserStats(user_id=user_id)
        
        stats = self._user_stats[user_id]
        stats.concurrent_executions += 1
    
    async def _update_user_stats_complete(self, user_id: str, duration: float, success: bool) -> None:
        """Update user statistics on execution complete."""
        if user_id not in self._user_stats:
            return
        
        stats = self._user_stats[user_id]
        stats.total_executions += 1
        stats.concurrent_executions = max(0, stats.concurrent_executions - 1)
        stats.total_execution_time += duration
        stats.last_execution_time = datetime.now(timezone.utc)
        
        if success:
            stats.successful_executions += 1
        else:
            stats.failed_executions += 1
        
        # Update average
        if stats.total_executions > 0:
            stats.avg_execution_time = stats.total_execution_time / stats.total_executions
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with user statistics or None if not found
        """
        try:
            stats = self._user_stats.get(user_id)
            if not stats:
                return None
            
            return {
                'user_id': stats.user_id,
                'total_executions': stats.total_executions,
                'successful_executions': stats.successful_executions,
                'failed_executions': stats.failed_executions,
                'success_rate': stats.successful_executions / max(stats.total_executions, 1),
                'avg_execution_time': stats.avg_execution_time,
                'concurrent_executions': stats.concurrent_executions,
                'last_execution_time': stats.last_execution_time.isoformat() if stats.last_execution_time else None,
                'first_seen': stats.first_seen.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get aggregated global statistics.
        
        Returns:
            Dictionary with system-wide statistics
        """
        try:
            # Calculate uptime
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            
            # Calculate executions per minute from recent activity
            current_time = datetime.now(timezone.utc)
            recent_cutoff = current_time - timedelta(minutes=1)
            recent_count = sum(1 for ts in self._recent_executions if ts >= recent_cutoff)
            
            # Calculate average execution time
            total_time = sum(
                record.duration_seconds or 0 
                for record in self._execution_records.values() 
                if record.completed_at
            )
            completed_count = sum(1 for record in self._execution_records.values() if record.completed_at)
            avg_time = total_time / max(completed_count, 1)
            
            return {
                'total_executions': self._system_stats.total_executions,
                'successful_executions': self._system_stats.successful_executions,
                'failed_executions': self._system_stats.failed_executions,
                'success_rate': self._system_stats.successful_executions / max(self._system_stats.total_executions, 1),
                'concurrent_executions': self._system_stats.concurrent_executions,
                'peak_concurrent_executions': self._system_stats.peak_concurrent_executions,
                'active_users': len([u for u, s in self._user_stats.items() if s.concurrent_executions > 0]),
                'total_users_seen': len(self._user_stats),
                'avg_execution_time': avg_time,
                'executions_per_minute': recent_count,
                'uptime_seconds': uptime,
                'uptime_hours': uptime / 3600,
                'memory_usage': {
                    'execution_records': len(self._execution_records),
                    'user_stats': len(self._user_stats),
                    'recent_executions_tracked': len(self._recent_executions)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {'error': str(e)}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics.
        
        Returns:
            Dictionary with system health indicators
        """
        try:
            stats = self.get_global_stats()
            
            # Health indicators
            success_rate = stats.get('success_rate', 0)
            avg_time = stats.get('avg_execution_time', 0)
            concurrent = stats.get('concurrent_executions', 0)
            peak_concurrent = stats.get('peak_concurrent_executions', 0)
            
            # Health scoring (0-100)
            health_score = 100
            
            # Deduct points for issues
            if success_rate < 0.95:  # Less than 95% success
                health_score -= (0.95 - success_rate) * 200
            
            if avg_time > 30:  # Executions taking longer than 30s
                health_score -= min(avg_time - 30, 50)
            
            if concurrent > peak_concurrent * 0.8:  # Near peak capacity
                health_score -= 20
            
            health_score = max(0, min(100, health_score))
            
            # Status
            if health_score >= 90:
                status = 'excellent'
            elif health_score >= 75:
                status = 'good'
            elif health_score >= 50:
                status = 'degraded'
            else:
                status = 'critical'
            
            return {
                'status': status,
                'health_score': round(health_score, 1),
                'indicators': {
                    'success_rate': success_rate,
                    'avg_execution_time': avg_time,
                    'concurrent_load': concurrent / max(peak_concurrent, 1),
                    'memory_usage': len(self._execution_records) / self.MAX_RECORDS
                },
                'recommendations': self._get_health_recommendations(health_score, stats),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'status': 'unknown', 'error': str(e)}
    
    def _get_health_recommendations(self, health_score: float, stats: Dict[str, Any]) -> List[str]:
        """Get health recommendations based on current metrics."""
        recommendations = []
        
        if stats.get('success_rate', 1) < 0.95:
            recommendations.append("Investigate execution failures - success rate below 95%")
        
        if stats.get('avg_execution_time', 0) > 30:
            recommendations.append("Optimize execution performance - average time exceeds 30s")
        
        if stats.get('concurrent_executions', 0) > stats.get('peak_concurrent_executions', 0) * 0.8:
            recommendations.append("Consider scaling - approaching peak concurrent capacity")
        
        memory_usage = len(self._execution_records) / self.MAX_RECORDS
        if memory_usage > 0.8:
            recommendations.append("Memory usage high - consider reducing retention period")
        
        if health_score < 75:
            recommendations.append("System health degraded - review execution patterns and resources")
        
        return recommendations
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for old records."""
        logger.info("Starting ExecutionStateStore cleanup loop")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Wait for cleanup interval or shutdown
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.CLEANUP_INTERVAL
                    )
                    break  # Shutdown event triggered
                    
                except asyncio.TimeoutError:
                    # Timeout reached, perform cleanup
                    await self._cleanup_old_records()
                
        except asyncio.CancelledError:
            logger.info("ExecutionStateStore cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in ExecutionStateStore cleanup loop: {e}")
        
        logger.info("ExecutionStateStore cleanup loop stopped")
    
    async def _cleanup_old_records(self) -> None:
        """Clean up old execution records to prevent memory leaks."""
        try:
            async with self._lock:
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time - timedelta(hours=self.RECORD_TTL_HOURS)
                
                # Find old records
                old_record_ids = []
                for execution_id, record in self._execution_records.items():
                    if record.started_at < cutoff_time:
                        old_record_ids.append(execution_id)
                
                # Remove old records
                for execution_id in old_record_ids:
                    del self._execution_records[execution_id]
                
                # Clean up empty concurrent tracking
                empty_users = []
                for user_id, executions in self._concurrent_tracking.items():
                    if not executions:
                        empty_users.append(user_id)
                
                for user_id in empty_users:
                    del self._concurrent_tracking[user_id]
                
                if old_record_ids:
                    logger.info(f"Cleaned up {len(old_record_ids)} old execution records")
                
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the execution state store."""
        logger.info("Shutting down ExecutionStateStore")
        
        try:
            # Signal cleanup task to stop
            self._shutdown_event.set()
            
            # Wait for cleanup task to finish
            if self._cleanup_task:
                try:
                    await asyncio.wait_for(self._cleanup_task, timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning("Cleanup task did not finish in time, cancelling")
                    self._cleanup_task.cancel()
                    try:
                        await self._cleanup_task
                    except asyncio.CancelledError:
                        pass
            
            # Clear all data
            self._execution_records.clear()
            self._user_stats.clear()
            self._recent_executions.clear()
            self._concurrent_tracking.clear()
            
            logger.info("✅ ExecutionStateStore shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during ExecutionStateStore shutdown: {e}")
            raise


# Singleton instance
_store_instance: Optional[ExecutionStateStore] = None
_store_lock = asyncio.Lock()


async def get_execution_state_store() -> ExecutionStateStore:
    """Get singleton ExecutionStateStore instance.
    
    Returns:
        ExecutionStateStore: Global execution monitoring store
    """
    global _store_instance
    
    async with _store_lock:
        if _store_instance is None:
            _store_instance = ExecutionStateStore()
            logger.info("Created singleton ExecutionStateStore instance")
        
        return _store_instance