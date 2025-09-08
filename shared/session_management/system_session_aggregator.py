"""SystemSessionAggregator - SSOT for System-Level Session Lifecycle Metrics

This module provides system-wide session tracking and database connection pool management
as part of the SessionMetrics SSOT violation remediation. Previously, this functionality
was mixed into the name-conflicted SessionMetrics class.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System stability monitoring for all tiers
- Business Goal: Prevent system-wide session leaks and connection pool exhaustion  
- Value Impact: Enables reliable system monitoring for 100+ concurrent users
- Strategic Impact: Foundation for system-wide health monitoring and alerting

Key Features:
- Database session lifecycle tracking with performance metrics
- Connection pool monitoring and leak detection
- System health aggregation across all user sessions
- Circuit breaker protection metrics
- Comprehensive logging and error tracking
- System-wide resource utilization monitoring

Architecture Integration:
This SystemSessionAggregator replaces the database-focused SessionMetrics from
request_scoped_session_factory.py, providing clear business-focused naming
that reflects its true purpose: system-wide session aggregation.

SSOT Compliance:
- Resolves SSOT violation by providing single source of truth for system metrics
- Business-focused naming eliminates confusion with user-level metrics
- Unified interface through SessionMetricsProvider
- Strongly typed metrics with proper enum states
"""

import asyncio
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional, Set, Any, ContextManager
from collections import defaultdict
from enum import Enum

from shared.types import UserID, SessionID, RequestID
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SystemSessionState(str, Enum):
    """System session lifecycle states for tracking."""
    CREATED = "created"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class SystemSessionRecord:
    """Individual system session record with lifecycle and performance tracking.
    
    This represents a single database session at the system level, tracking
    its performance characteristics and resource utilization.
    """
    session_id: SessionID
    request_id: RequestID
    user_id: UserID
    created_at: datetime
    state: SystemSessionState = SystemSessionState.CREATED
    query_count: int = 0
    transaction_count: int = 0
    total_time_ms: Optional[float] = None
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    def mark_activity(self):
        """Mark recent session activity."""
        self.last_activity = datetime.now(timezone.utc)
    
    def record_error(self, error: str):
        """Record session error."""
        self.error_count += 1
        self.last_error = error
        self.state = SystemSessionState.ERROR
        self.mark_activity()
    
    def close(self):
        """Mark session as closed."""
        self.closed_at = datetime.now(timezone.utc)
        self.state = SystemSessionState.CLOSED
        if self.created_at and self.closed_at:
            self.total_time_ms = (self.closed_at - self.created_at).total_seconds() * 1000


@dataclass 
class SystemConnectionPoolMetrics:
    """System-wide connection pool health and usage metrics."""
    active_sessions: int = 0
    total_sessions_created: int = 0
    sessions_closed: int = 0
    pool_exhaustion_events: int = 0
    circuit_breaker_trips: int = 0
    leaked_sessions: int = 0
    avg_session_lifetime_ms: float = 0.0
    peak_concurrent_sessions: int = 0
    last_pool_exhaustion: Optional[datetime] = None
    last_leak_detection: Optional[datetime] = None
    
    def update_peak_concurrent(self, current: int):
        """Update peak concurrent sessions."""
        if current > self.peak_concurrent_sessions:
            self.peak_concurrent_sessions = current
    
    def record_pool_exhaustion(self):
        """Record pool exhaustion event."""
        self.pool_exhaustion_events += 1
        self.last_pool_exhaustion = datetime.now(timezone.utc)
    
    def record_leak(self):
        """Record session leak detection."""
        self.leaked_sessions += 1
        self.last_leak_detection = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for monitoring."""
        return {
            'active_sessions': self.active_sessions,
            'total_sessions_created': self.total_sessions_created,
            'sessions_closed': self.sessions_closed,
            'pool_exhaustion_events': self.pool_exhaustion_events,
            'circuit_breaker_trips': self.circuit_breaker_trips,
            'leaked_sessions': self.leaked_sessions,
            'avg_session_lifetime_ms': self.avg_session_lifetime_ms,
            'peak_concurrent_sessions': self.peak_concurrent_sessions,
            'last_pool_exhaustion': self.last_pool_exhaustion.isoformat() if self.last_pool_exhaustion else None,
            'last_leak_detection': self.last_leak_detection.isoformat() if self.last_leak_detection else None
        }


class SystemSessionAggregator:
    """SSOT for system-wide session lifecycle tracking and connection pool management.
    
    This class provides comprehensive system-level session monitoring as a Single Source
    of Truth (SSOT) for database session lifecycle operations. It focuses on system-wide
    resource tracking, connection pool health, and leak detection.
    
    Key Design Principles:
    - System-wide resource utilization tracking
    - Connection pool health monitoring
    - Session leak detection and prevention
    - Circuit breaker pattern implementation
    - Comprehensive performance metrics
    - Real-time system health aggregation
    
    Business Focus:
    Unlike user-focused session management, this aggregator focuses on system stability,
    resource utilization, and infrastructure health monitoring across all users.
    """
    
    def __init__(self, 
                 cleanup_interval_minutes: int = 15,
                 max_session_lifetime_ms: int = 300000,  # 5 minutes
                 leak_detection_interval: int = 60):  # 1 minute
        """Initialize SystemSessionAggregator with monitoring capabilities.
        
        Args:
            cleanup_interval_minutes: How often to run leak detection cleanup
            max_session_lifetime_ms: Maximum session lifetime before leak detection
            leak_detection_interval: How often to check for leaks (seconds)
        """
        self._active_sessions: Dict[SessionID, SystemSessionRecord] = {}
        self._session_registry: weakref.WeakSet = weakref.WeakSet()
        self._pool_metrics = SystemConnectionPoolMetrics()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._leak_detection_enabled = True
        self._max_session_lifetime_ms = max_session_lifetime_ms
        self._leak_detection_interval = leak_detection_interval
        
        logger.info(f"Initialized SystemSessionAggregator with cleanup_interval={cleanup_interval_minutes}min, "
                   f"max_lifetime={max_session_lifetime_ms}ms, leak_detection={leak_detection_interval}s")
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("System session monitoring already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._background_monitoring())
        logger.info("Started system session background monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped system session background monitoring")
    
    async def _background_monitoring(self) -> None:
        """Background monitoring task for leak detection and metrics collection."""
        while True:
            try:
                await asyncio.sleep(self._leak_detection_interval)
                leaked_count = await self._detect_and_cleanup_leaks()
                if leaked_count > 0:
                    logger.warning(f"System monitoring detected and cleaned {leaked_count} leaked sessions")
                    
                # Update system health metrics
                await self._update_system_health_metrics()
                
            except asyncio.CancelledError:
                logger.info("System session monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in system session monitoring: {e}", exc_info=True)
    
    async def _detect_and_cleanup_leaks(self) -> int:
        """Detect and clean up leaked sessions."""
        if not self._leak_detection_enabled:
            return 0
        
        current_time = datetime.now(timezone.utc)
        leaked_sessions = []
        
        async with self._lock:
            for session_id, record in self._active_sessions.items():
                # Check for sessions that have been active too long
                if record.state == SystemSessionState.ACTIVE:
                    session_age_ms = (current_time - record.created_at).total_seconds() * 1000
                    if session_age_ms > self._max_session_lifetime_ms:
                        leaked_sessions.append(session_id)
                        logger.warning(
                            f"System detected leaked session {session_id} for user {record.user_id}, "
                            f"age: {session_age_ms:.1f}ms"
                        )
                
                # Check for sessions without recent activity
                elif record.last_activity:
                    inactive_time_ms = (current_time - record.last_activity).total_seconds() * 1000
                    if inactive_time_ms > (self._max_session_lifetime_ms / 2):
                        logger.warning(
                            f"System session {session_id} inactive for {inactive_time_ms:.1f}ms"
                        )
            
            # Clean up leaked sessions
            for session_id in leaked_sessions:
                if session_id in self._active_sessions:
                    self._active_sessions[session_id].record_error("System leaked - forced cleanup")
                    self._active_sessions[session_id].close()
                    self._pool_metrics.record_leak()
                    del self._active_sessions[session_id]
        
        return len(leaked_sessions)
    
    async def _update_system_health_metrics(self) -> None:
        """Update system-wide health and performance metrics."""
        async with self._lock:
            self._pool_metrics.active_sessions = len(self._active_sessions)
            
            # Calculate average session lifetime
            if self._active_sessions:
                total_lifetime = sum(
                    (datetime.now(timezone.utc) - record.created_at).total_seconds() * 1000
                    for record in self._active_sessions.values()
                )
                self._pool_metrics.avg_session_lifetime_ms = total_lifetime / len(self._active_sessions)
            else:
                self._pool_metrics.avg_session_lifetime_ms = 0.0
            
            # Update peak concurrent tracking
            self._pool_metrics.update_peak_concurrent(len(self._active_sessions))
    
    async def register_session(self, session_id: SessionID, request_id: RequestID, 
                             user_id: UserID) -> SystemSessionRecord:
        """Register a new system session for tracking.
        
        Args:
            session_id: Unique session identifier
            request_id: Request identifier
            user_id: User identifier
            
        Returns:
            SystemSessionRecord: Tracking record for this session
        """
        record = SystemSessionRecord(
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc)
        )
        
        async with self._lock:
            self._active_sessions[session_id] = record
            self._pool_metrics.active_sessions += 1
            self._pool_metrics.total_sessions_created += 1
            self._pool_metrics.update_peak_concurrent(self._pool_metrics.active_sessions)
        
        logger.debug(f"Registered system session {session_id} for user {user_id}")
        return record
    
    async def unregister_session(self, session_id: SessionID) -> bool:
        """Unregister session and update system metrics.
        
        Args:
            session_id: Session to unregister
            
        Returns:
            True if session was found and unregistered
        """
        async with self._lock:
            if session_id in self._active_sessions:
                record = self._active_sessions[session_id]
                record.close()
                
                # Update system metrics
                self._pool_metrics.active_sessions = max(0, self._pool_metrics.active_sessions - 1)
                self._pool_metrics.sessions_closed += 1
                
                # Update average session lifetime
                if record.total_time_ms:
                    total_lifetime = (self._pool_metrics.avg_session_lifetime_ms * 
                                     (self._pool_metrics.sessions_closed - 1) + record.total_time_ms)
                    self._pool_metrics.avg_session_lifetime_ms = total_lifetime / self._pool_metrics.sessions_closed
                
                del self._active_sessions[session_id]
                logger.debug(f"Unregistered system session {session_id}")
                return True
        
        return False
    
    async def record_session_activity(self, session_id: SessionID) -> bool:
        """Record activity for a session.
        
        Args:
            session_id: Session that had activity
            
        Returns:
            True if session was found and updated
        """
        async with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].mark_activity()
                return True
        
        return False
    
    async def record_session_error(self, session_id: SessionID, error: str) -> bool:
        """Record error for a session.
        
        Args:
            session_id: Session that had an error
            error: Error description
            
        Returns:
            True if session was found and updated
        """
        async with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].record_error(error)
                return True
        
        return False
    
    def get_system_metrics(self) -> SystemConnectionPoolMetrics:
        """Get current system-wide metrics.
        
        Returns:
            SystemConnectionPoolMetrics: Current system metrics
        """
        return self._pool_metrics
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of active sessions.
        
        Returns:
            Dictionary with anonymized session summary data
        """
        summary = {
            'total_active_sessions': len(self._active_sessions),
            'sessions_by_state': defaultdict(int),
            'sessions_by_user_type': defaultdict(int),
            'error_sessions': 0,
            'avg_session_age_minutes': 0.0
        }
        
        if self._active_sessions:
            total_age = 0.0
            for record in self._active_sessions.values():
                # Count by state
                summary['sessions_by_state'][record.state.value] += 1
                
                # Count by user type (anonymized)
                user_type = "system" if record.user_id.startswith("system") else "user"
                summary['sessions_by_user_type'][user_type] += 1
                
                # Count errors
                if record.error_count > 0:
                    summary['error_sessions'] += 1
                
                # Track age
                age_minutes = (datetime.now(timezone.utc) - record.created_at).total_seconds() / 60.0
                total_age += age_minutes
            
            summary['avg_session_age_minutes'] = total_age / len(self._active_sessions)
        
        return summary
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system session health check.
        
        Returns:
            Health check results with system status
        """
        try:
            metrics = self.get_system_metrics()
            session_summary = self.get_session_summary()
            
            # Determine health status
            status = "healthy"
            warnings = []
            
            if metrics.leaked_sessions > 10:
                warnings.append(f"High leak count: {metrics.leaked_sessions}")
                status = "degraded"
            
            if metrics.pool_exhaustion_events > 0:
                warnings.append(f"Pool exhaustion events: {metrics.pool_exhaustion_events}")
                status = "degraded"
            
            if metrics.active_sessions > 1000:  # High load threshold
                warnings.append(f"High active session count: {metrics.active_sessions}")
                status = "warning"
            
            return {
                'status': status,
                'warnings': warnings,
                'system_metrics': metrics.to_dict(),
                'session_summary': session_summary,
                'monitoring_enabled': self._leak_detection_enabled,
                'background_monitoring_running': self._cleanup_task and not self._cleanup_task.done()
            }
        
        except Exception as e:
            logger.error(f"System session health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'system_metrics': self._pool_metrics.to_dict() if self._pool_metrics else {}
            }
    
    async def force_cleanup_all(self) -> int:
        """Force cleanup of all active sessions (emergency use only).
        
        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            session_count = len(self._active_sessions)
            
            if session_count > 0:
                logger.warning(f"EMERGENCY: Force cleaning up {session_count} active system sessions")
                
                for session_id, record in self._active_sessions.items():
                    record.record_error("Emergency force cleanup")
                    record.close()
                
                self._active_sessions.clear()
                self._pool_metrics.active_sessions = 0
            
            return session_count


# Global system session aggregator instance
_global_system_aggregator: Optional[SystemSessionAggregator] = None
_aggregator_lock = asyncio.Lock()


async def get_system_session_aggregator() -> SystemSessionAggregator:
    """Get the global system session aggregator instance.
    
    Returns:
        SystemSessionAggregator: Global aggregator instance
    """
    global _global_system_aggregator
    
    if _global_system_aggregator is None:
        async with _aggregator_lock:
            if _global_system_aggregator is None:
                _global_system_aggregator = SystemSessionAggregator()
                await _global_system_aggregator.start_monitoring()
                logger.info("Created global SystemSessionAggregator")
    
    return _global_system_aggregator


async def shutdown_system_session_aggregator():
    """Shutdown the global system session aggregator."""
    global _global_system_aggregator
    
    if _global_system_aggregator:
        await _global_system_aggregator.stop_monitoring()
        cleaned_count = await _global_system_aggregator.force_cleanup_all()
        logger.info(f"Shutdown SystemSessionAggregator - cleaned {cleaned_count} sessions")
        _global_system_aggregator = None


# Export public interface
__all__ = [
    'SystemSessionAggregator',
    'SystemSessionRecord',
    'SystemConnectionPoolMetrics',
    'SystemSessionState',
    'get_system_session_aggregator',
    'shutdown_system_session_aggregator'
]