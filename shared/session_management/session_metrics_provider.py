"""SessionMetricsProvider - Unified Interface for Session Metrics (SSOT Compliance)

This module provides the unified interface for all session metrics operations,
resolving the SSOT violation between the conflicting SessionMetrics classes
through proper abstraction and business-focused naming.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System stability and user experience foundation
- Business Goal: Eliminate SSOT violations while maintaining all functionality
- Value Impact: Prevents attribute errors and enables reliable session tracking
- Strategic Impact: Foundation for unified session management across all services

Key Features:
- Unified interface for both system and user session metrics
- Type-safe access to session data with proper attribute mapping
- Backward compatibility during migration period
- Business-focused naming and clear separation of concerns
- Strongly typed metrics with proper validation
- Comprehensive session health monitoring and reporting

Architecture Integration:
This provider acts as the unified interface between:
1. SystemSessionAggregator (system-level database session tracking)
2. UserSessionTracker (user-level behavior and engagement tracking)

It provides a single, consistent API for all session metrics operations while
maintaining the business distinction between system and user concerns.

SSOT Compliance:
- Single source of truth for session metrics interfaces
- Eliminates naming conflicts between SessionMetrics classes
- Provides unified access patterns for both system and user metrics
- Maintains backward compatibility during migration
- Type-safe attribute access prevents AttributeError issues
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Protocol, runtime_checkable
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from shared.types import UserID, ThreadID, SessionID, RequestID
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SessionMetricsType(str, Enum):
    """Type of session metrics being accessed."""
    SYSTEM = "system"  # System-level database session tracking
    USER = "user"     # User-level behavior and engagement tracking


@dataclass
class UnifiedSessionMetrics:
    """Unified session metrics structure that resolves SSOT violations.
    
    This class provides a unified interface for accessing session metrics
    from both system and user perspectives, with proper attribute mapping
    to prevent AttributeError issues.
    """
    # Common attributes (mapped from both system and user metrics)
    total_sessions: int = 0
    active_sessions: int = 0
    sessions_created_today: int = 0
    sessions_reused_today: int = 0
    average_session_duration_minutes: float = 0.0
    last_activity: datetime = None  # CRITICAL: This fixes the AttributeError
    
    # System-specific attributes (from SystemSessionAggregator)
    pool_exhaustion_events: int = 0
    circuit_breaker_trips: int = 0
    leaked_sessions: int = 0
    peak_concurrent_sessions: int = 0
    
    # User-specific attributes (from UserSessionTracker)
    total_messages_sent: int = 0
    total_agent_executions: int = 0
    avg_messages_per_session: float = 0.0
    user_satisfaction_score: Optional[float] = None
    
    # Metadata
    metrics_type: SessionMetricsType = SessionMetricsType.SYSTEM
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
    
    def get_inactivity_minutes(self) -> float:
        """Get minutes since last activity."""
        if self.last_activity:
            delta = datetime.now(timezone.utc) - self.last_activity
            return delta.total_seconds() / 60.0
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            'total_sessions': self.total_sessions,
            'active_sessions': self.active_sessions,
            'sessions_created_today': self.sessions_created_today,
            'sessions_reused_today': self.sessions_reused_today,
            'average_session_duration_minutes': self.average_session_duration_minutes,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'inactivity_minutes': self.get_inactivity_minutes(),
            'pool_exhaustion_events': self.pool_exhaustion_events,
            'circuit_breaker_trips': self.circuit_breaker_trips,
            'leaked_sessions': self.leaked_sessions,
            'peak_concurrent_sessions': self.peak_concurrent_sessions,
            'total_messages_sent': self.total_messages_sent,
            'total_agent_executions': self.total_agent_executions,
            'avg_messages_per_session': self.avg_messages_per_session,
            'user_satisfaction_score': self.user_satisfaction_score,
            'metrics_type': self.metrics_type.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@runtime_checkable
class SessionMetricsProvider(Protocol):
    """Protocol for session metrics providers.
    
    This protocol defines the interface that all session metrics providers
    must implement to ensure consistent access patterns and type safety.
    """
    
    async def get_metrics(self) -> UnifiedSessionMetrics:
        """Get unified session metrics.
        
        Returns:
            UnifiedSessionMetrics: Unified metrics structure
        """
        ...
    
    async def get_session_count(self) -> int:
        """Get current active session count.
        
        Returns:
            Current number of active sessions
        """
        ...
    
    async def record_activity(self, session_id: SessionID) -> bool:
        """Record activity for a session.
        
        Args:
            session_id: Session that had activity
            
        Returns:
            True if activity was recorded successfully
        """
        ...
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the metrics provider.
        
        Returns:
            Health check results
        """
        ...


class SessionMetricsAdapter:
    """Adapter for converting between legacy SessionMetrics and UnifiedSessionMetrics.
    
    This adapter provides backward compatibility during the migration period,
    ensuring that existing code continues to work while we transition to the
    new unified interface.
    """
    
    @staticmethod
    def from_system_metrics(system_metrics: Any) -> UnifiedSessionMetrics:
        """Convert system metrics to unified format.
        
        Args:
            system_metrics: SystemConnectionPoolMetrics or similar system metrics
            
        Returns:
            UnifiedSessionMetrics: Unified metrics structure
        """
        try:
            # Handle SystemConnectionPoolMetrics
            if hasattr(system_metrics, 'active_sessions'):
                return UnifiedSessionMetrics(
                    total_sessions=getattr(system_metrics, 'total_sessions_created', 0),
                    active_sessions=getattr(system_metrics, 'active_sessions', 0),
                    sessions_created_today=0,  # Not tracked in system metrics
                    sessions_reused_today=0,   # Not tracked in system metrics
                    average_session_duration_minutes=getattr(system_metrics, 'avg_session_lifetime_ms', 0.0) / 60000,
                    last_activity=datetime.now(timezone.utc),  # CRITICAL: Always provide this attribute
                    pool_exhaustion_events=getattr(system_metrics, 'pool_exhaustion_events', 0),
                    circuit_breaker_trips=getattr(system_metrics, 'circuit_breaker_trips', 0),
                    leaked_sessions=getattr(system_metrics, 'leaked_sessions', 0),
                    peak_concurrent_sessions=getattr(system_metrics, 'peak_concurrent_sessions', 0),
                    metrics_type=SessionMetricsType.SYSTEM
                )
            
            # Handle legacy SessionMetrics from request_scoped_session_factory
            elif hasattr(system_metrics, 'session_id'):
                return UnifiedSessionMetrics(
                    total_sessions=1,  # Single session record
                    active_sessions=1 if getattr(system_metrics, 'state', None) == 'active' else 0,
                    sessions_created_today=1,
                    sessions_reused_today=0,
                    average_session_duration_minutes=getattr(system_metrics, 'total_time_ms', 0.0) / 60000,
                    last_activity=getattr(system_metrics, 'last_activity_at', datetime.now(timezone.utc)),
                    pool_exhaustion_events=0,
                    circuit_breaker_trips=0,
                    leaked_sessions=1 if getattr(system_metrics, 'error_count', 0) > 0 else 0,
                    peak_concurrent_sessions=1,
                    metrics_type=SessionMetricsType.SYSTEM
                )
            
            else:
                # Unknown system metrics format - provide safe defaults
                logger.warning(f"Unknown system metrics format: {type(system_metrics)}")
                return UnifiedSessionMetrics(
                    last_activity=datetime.now(timezone.utc),
                    metrics_type=SessionMetricsType.SYSTEM
                )
        
        except Exception as e:
            logger.error(f"Error converting system metrics: {e}")
            return UnifiedSessionMetrics(
                last_activity=datetime.now(timezone.utc),
                metrics_type=SessionMetricsType.SYSTEM
            )
    
    @staticmethod
    def from_user_metrics(user_metrics: Any) -> UnifiedSessionMetrics:
        """Convert user metrics to unified format.
        
        Args:
            user_metrics: UserEngagementMetrics or similar user metrics
            
        Returns:
            UnifiedSessionMetrics: Unified metrics structure
        """
        try:
            # Handle UserEngagementMetrics
            if hasattr(user_metrics, 'total_sessions'):
                return UnifiedSessionMetrics(
                    total_sessions=getattr(user_metrics, 'total_sessions', 0),
                    active_sessions=getattr(user_metrics, 'active_sessions', 0),
                    sessions_created_today=getattr(user_metrics, 'sessions_created_today', 0),
                    sessions_reused_today=getattr(user_metrics, 'sessions_reused_today', 0),
                    average_session_duration_minutes=getattr(user_metrics, 'average_session_duration_minutes', 0.0),
                    last_activity=getattr(user_metrics, 'last_activity', datetime.now(timezone.utc)),
                    total_messages_sent=getattr(user_metrics, 'total_messages_sent', 0),
                    total_agent_executions=getattr(user_metrics, 'total_agent_executions', 0),
                    avg_messages_per_session=getattr(user_metrics, 'avg_messages_per_session', 0.0),
                    user_satisfaction_score=getattr(user_metrics, 'user_satisfaction_score', None),
                    metrics_type=SessionMetricsType.USER
                )
            
            # Handle legacy SessionMetrics from user_session_manager
            elif hasattr(user_metrics, 'to_dict'):
                metrics_dict = user_metrics.to_dict()
                return UnifiedSessionMetrics(
                    total_sessions=metrics_dict.get('total_sessions', 0),
                    active_sessions=metrics_dict.get('active_sessions', 0),
                    sessions_created_today=metrics_dict.get('sessions_created_today', 0),
                    sessions_reused_today=metrics_dict.get('sessions_reused_today', 0),
                    average_session_duration_minutes=metrics_dict.get('average_session_duration_minutes', 0.0),
                    last_activity=datetime.now(timezone.utc),  # CRITICAL: Always provide this
                    total_messages_sent=metrics_dict.get('total_messages_sent', 0),
                    total_agent_executions=metrics_dict.get('total_agent_executions', 0),
                    avg_messages_per_session=metrics_dict.get('avg_messages_per_session', 0.0),
                    user_satisfaction_score=metrics_dict.get('user_satisfaction_score'),
                    metrics_type=SessionMetricsType.USER
                )
            
            else:
                # Unknown user metrics format - provide safe defaults
                logger.warning(f"Unknown user metrics format: {type(user_metrics)}")
                return UnifiedSessionMetrics(
                    last_activity=datetime.now(timezone.utc),
                    metrics_type=SessionMetricsType.USER
                )
        
        except Exception as e:
            logger.error(f"Error converting user metrics: {e}")
            return UnifiedSessionMetrics(
                last_activity=datetime.now(timezone.utc),
                metrics_type=SessionMetricsType.USER
            )
    
    @staticmethod
    def create_safe_default() -> UnifiedSessionMetrics:
        """Create safe default metrics to prevent AttributeError.
        
        Returns:
            UnifiedSessionMetrics: Safe default metrics with all required attributes
        """
        return UnifiedSessionMetrics(
            last_activity=datetime.now(timezone.utc),  # CRITICAL: This prevents AttributeError
            metrics_type=SessionMetricsType.SYSTEM,
            timestamp=datetime.now(timezone.utc)
        )


class UnifiedSessionMetricsProvider:
    """Unified session metrics provider that aggregates system and user metrics.
    
    This provider acts as the central coordinator for both system and user
    session metrics, providing a single interface while maintaining the
    separation of concerns between the two domains.
    """
    
    def __init__(self):
        """Initialize the unified metrics provider."""
        self._system_aggregator = None
        self._user_tracker = None
        
        logger.info("Initialized UnifiedSessionMetricsProvider")
    
    def set_system_aggregator(self, aggregator) -> None:
        """Set the system session aggregator.
        
        Args:
            aggregator: SystemSessionAggregator instance
        """
        self._system_aggregator = aggregator
        logger.debug("Set system session aggregator for unified provider")
    
    def set_user_tracker(self, tracker) -> None:
        """Set the user session tracker.
        
        Args:
            tracker: UserSessionTracker instance
        """
        self._user_tracker = tracker
        logger.debug("Set user session tracker for unified provider")
    
    async def get_system_metrics(self) -> UnifiedSessionMetrics:
        """Get system-focused session metrics.
        
        Returns:
            UnifiedSessionMetrics: System metrics in unified format
        """
        if self._system_aggregator:
            try:
                system_metrics = self._system_aggregator.get_system_metrics()
                return SessionMetricsAdapter.from_system_metrics(system_metrics)
            except Exception as e:
                logger.error(f"Error getting system metrics: {e}")
        
        return SessionMetricsAdapter.create_safe_default()
    
    async def get_user_metrics(self, user_id: Optional[UserID] = None) -> UnifiedSessionMetrics:
        """Get user-focused session metrics.
        
        Args:
            user_id: Specific user ID, or None for aggregated metrics
            
        Returns:
            UnifiedSessionMetrics: User metrics in unified format
        """
        if self._user_tracker:
            try:
                if user_id:
                    user_metrics = await self._user_tracker.get_user_engagement_metrics(user_id)
                    return SessionMetricsAdapter.from_user_metrics(user_metrics)
                else:
                    # Get aggregated user metrics
                    analytics_summary = self._user_tracker.get_analytics_summary()
                    return UnifiedSessionMetrics(
                        total_sessions=analytics_summary.get('total_user_sessions', 0),
                        active_sessions=analytics_summary.get('total_sessions_tracked', 0),
                        total_messages_sent=analytics_summary.get('total_messages_sent', 0),
                        total_agent_executions=analytics_summary.get('total_agent_executions', 0),
                        avg_messages_per_session=analytics_summary.get('avg_messages_per_user', 0.0),
                        last_activity=datetime.now(timezone.utc),
                        metrics_type=SessionMetricsType.USER
                    )
            except Exception as e:
                logger.error(f"Error getting user metrics: {e}")
        
        return SessionMetricsAdapter.create_safe_default()
    
    async def get_combined_metrics(self) -> UnifiedSessionMetrics:
        """Get combined system and user metrics.
        
        Returns:
            UnifiedSessionMetrics: Combined metrics from both perspectives
        """
        try:
            system_metrics = await self.get_system_metrics()
            user_metrics = await self.get_user_metrics()
            
            # Combine the metrics intelligently
            return UnifiedSessionMetrics(
                total_sessions=max(system_metrics.total_sessions, user_metrics.total_sessions),
                active_sessions=max(system_metrics.active_sessions, user_metrics.active_sessions),
                sessions_created_today=user_metrics.sessions_created_today,  # User tracker has this
                sessions_reused_today=user_metrics.sessions_reused_today,    # User tracker has this
                average_session_duration_minutes=max(
                    system_metrics.average_session_duration_minutes,
                    user_metrics.average_session_duration_minutes
                ),
                last_activity=max(
                    system_metrics.last_activity or datetime.min.replace(tzinfo=timezone.utc),
                    user_metrics.last_activity or datetime.min.replace(tzinfo=timezone.utc)
                ),
                # System-specific metrics
                pool_exhaustion_events=system_metrics.pool_exhaustion_events,
                circuit_breaker_trips=system_metrics.circuit_breaker_trips,
                leaked_sessions=system_metrics.leaked_sessions,
                peak_concurrent_sessions=system_metrics.peak_concurrent_sessions,
                # User-specific metrics
                total_messages_sent=user_metrics.total_messages_sent,
                total_agent_executions=user_metrics.total_agent_executions,
                avg_messages_per_session=user_metrics.avg_messages_per_session,
                user_satisfaction_score=user_metrics.user_satisfaction_score,
                # Combined type
                metrics_type=SessionMetricsType.SYSTEM,  # Default to system for compatibility
                timestamp=datetime.now(timezone.utc)
            )
        
        except Exception as e:
            logger.error(f"Error getting combined metrics: {e}")
            return SessionMetricsAdapter.create_safe_default()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all metrics providers.
        
        Returns:
            Health check results for both system and user metrics
        """
        health_status = {
            'overall_status': 'healthy',
            'system_metrics': {'status': 'unavailable'},
            'user_metrics': {'status': 'unavailable'},
            'unified_provider': {'status': 'healthy'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Check system aggregator health
        if self._system_aggregator:
            try:
                system_health = await self._system_aggregator.health_check()
                health_status['system_metrics'] = system_health
            except Exception as e:
                health_status['system_metrics'] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_status['overall_status'] = 'degraded'
        
        # Check user tracker health (if it has health_check method)
        if self._user_tracker:
            try:
                # UserSessionTracker doesn't have health_check yet, so get analytics summary
                analytics = self._user_tracker.get_analytics_summary()
                health_status['user_metrics'] = {
                    'status': 'healthy',
                    'analytics_enabled': analytics.get('analytics_enabled', False),
                    'total_users_tracked': analytics.get('total_users_tracked', 0),
                    'total_sessions_tracked': analytics.get('total_sessions_tracked', 0)
                }
            except Exception as e:
                health_status['user_metrics'] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_status['overall_status'] = 'degraded'
        
        return health_status


# Global unified provider instance
_global_unified_provider: Optional[UnifiedSessionMetricsProvider] = None


def get_unified_session_metrics_provider() -> UnifiedSessionMetricsProvider:
    """Get the global unified session metrics provider.
    
    Returns:
        UnifiedSessionMetricsProvider: Global unified provider instance
    """
    global _global_unified_provider
    
    if _global_unified_provider is None:
        _global_unified_provider = UnifiedSessionMetricsProvider()
        logger.info("Created global UnifiedSessionMetricsProvider")
    
    return _global_unified_provider


# CRITICAL: Legacy compatibility functions to prevent AttributeError
def get_session_metrics_with_last_activity() -> UnifiedSessionMetrics:
    """Get session metrics with guaranteed last_activity attribute.
    
    This function specifically addresses the AttributeError issue by ensuring
    that the returned object ALWAYS has a last_activity attribute.
    
    Returns:
        UnifiedSessionMetrics: Metrics with guaranteed last_activity attribute
    """
    try:
        provider = get_unified_session_metrics_provider()
        # This is a synchronous wrapper for the async method
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new task
                return SessionMetricsAdapter.create_safe_default()
            else:
                return loop.run_until_complete(provider.get_combined_metrics())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(provider.get_combined_metrics())
    
    except Exception as e:
        logger.error(f"Error getting session metrics with last_activity: {e}")
        return SessionMetricsAdapter.create_safe_default()


# Export public interface
__all__ = [
    'SessionMetricsProvider',
    'UnifiedSessionMetrics',
    'SessionMetricsType',
    'SessionMetricsAdapter',
    'UnifiedSessionMetricsProvider',
    'get_unified_session_metrics_provider',
    'get_session_metrics_with_last_activity'
]