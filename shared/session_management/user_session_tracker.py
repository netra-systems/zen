"""UserSessionTracker - SSOT for User-Level Session Management and Tracking

This module provides user-focused session tracking and management functionality
as part of the SessionMetrics SSOT violation remediation. Previously, this functionality
was mixed into the name-conflicted SessionMetrics class.

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core chat continuity and user experience
- Business Goal: Enable seamless multi-turn AI conversations and user engagement tracking
- Value Impact: Delivers 90% of platform value through reliable user session continuity
- Strategic Impact: Foundation for user behavior analytics and engagement optimization

Key Features:
- User-focused session lifecycle management and tracking
- Chat continuity preservation across multiple interactions
- User behavior and engagement analytics
- Session-based user experience optimization
- Multi-user isolation and privacy protection
- User activity pattern analysis and insights

Architecture Integration:
This UserSessionTracker replaces the user-focused SessionMetrics from
user_session_manager.py, providing clear business-focused naming that reflects
its true purpose: user-level session tracking and engagement analytics.

SSOT Compliance:
- Resolves SSOT violation by providing single source of truth for user metrics
- Business-focused naming eliminates confusion with system-level metrics  
- Unified interface through SessionMetricsProvider
- Strongly typed user metrics with proper privacy controls
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from threading import Lock
from contextlib import asynccontextmanager

from shared.types import UserID, ThreadID, SessionID, RequestID
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class UserEngagementMetrics:
    """User engagement and behavior tracking metrics.
    
    This tracks user-level engagement patterns, session usage, and behavior
    analytics to optimize user experience and business value.
    """
    total_sessions: int = 0
    active_sessions: int = 0
    expired_sessions_cleaned: int = 0
    sessions_created_today: int = 0
    sessions_reused_today: int = 0
    average_session_duration_minutes: float = 0.0
    memory_usage_mb: float = 0.0
    
    # User behavior analytics
    total_messages_sent: int = 0
    total_agent_executions: int = 0
    avg_messages_per_session: float = 0.0
    user_retention_days: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Business engagement metrics
    feature_usage_count: Dict[str, int] = field(default_factory=dict)
    conversion_indicators: Dict[str, Any] = field(default_factory=dict)
    user_satisfaction_score: Optional[float] = None
    
    def update_activity(self) -> None:
        """Update user activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def record_message_sent(self) -> None:
        """Record user message sent."""
        self.total_messages_sent += 1
        self.update_activity()
        
        # Update average messages per session
        if self.active_sessions > 0:
            self.avg_messages_per_session = self.total_messages_sent / self.active_sessions
    
    def record_agent_execution(self) -> None:
        """Record agent execution for user."""
        self.total_agent_executions += 1
        self.update_activity()
    
    def record_feature_usage(self, feature_name: str) -> None:
        """Record usage of a specific feature."""
        if feature_name not in self.feature_usage_count:
            self.feature_usage_count[feature_name] = 0
        self.feature_usage_count[feature_name] += 1
        self.update_activity()
    
    def get_inactivity_minutes(self) -> float:
        """Get minutes since last user activity."""
        delta = datetime.now(timezone.utc) - self.last_activity
        return delta.total_seconds() / 60.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for analytics."""
        return {
            'total_sessions': self.total_sessions,
            'active_sessions': self.active_sessions,
            'expired_sessions_cleaned': self.expired_sessions_cleaned,
            'sessions_created_today': self.sessions_created_today,
            'sessions_reused_today': self.sessions_reused_today,
            'average_session_duration_minutes': self.average_session_duration_minutes,
            'memory_usage_mb': self.memory_usage_mb,
            'total_messages_sent': self.total_messages_sent,
            'total_agent_executions': self.total_agent_executions,
            'avg_messages_per_session': self.avg_messages_per_session,
            'user_retention_days': self.user_retention_days,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'inactivity_minutes': self.get_inactivity_minutes(),
            'feature_usage_count': dict(self.feature_usage_count),
            'conversion_indicators': dict(self.conversion_indicators),
            'user_satisfaction_score': self.user_satisfaction_score
        }


@dataclass
class UserSessionInfo:
    """Enhanced user session information with engagement tracking."""
    user_id: UserID
    thread_id: ThreadID
    session_id: SessionID
    request_id: RequestID
    created_at: datetime
    last_activity: datetime
    websocket_connection_id: Optional[str] = None
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # User engagement tracking
    messages_in_session: int = 0
    agent_executions_in_session: int = 0
    features_used_in_session: List[str] = field(default_factory=list)
    session_quality_score: Optional[float] = None
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def get_age_minutes(self) -> float:
        """Get session age in minutes."""
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds() / 60.0
    
    def get_inactivity_minutes(self) -> float:
        """Get minutes since last activity."""
        delta = datetime.now(timezone.utc) - self.last_activity
        return delta.total_seconds() / 60.0
    
    def record_message(self) -> None:
        """Record user message in this session."""
        self.messages_in_session += 1
        self.update_activity()
    
    def record_agent_execution(self) -> None:
        """Record agent execution in this session."""
        self.agent_executions_in_session += 1
        self.update_activity()
    
    def record_feature_usage(self, feature_name: str) -> None:
        """Record feature usage in this session."""
        if feature_name not in self.features_used_in_session:
            self.features_used_in_session.append(feature_name)
        self.update_activity()
    
    def calculate_session_quality(self) -> float:
        """Calculate session quality score based on engagement."""
        # Simple scoring algorithm - can be enhanced
        score = 0.0
        
        # Message activity score (0-40 points)
        message_score = min(40, self.messages_in_session * 5)
        score += message_score
        
        # Agent execution score (0-30 points)  
        agent_score = min(30, self.agent_executions_in_session * 10)
        score += agent_score
        
        # Feature usage diversity score (0-20 points)
        feature_score = min(20, len(self.features_used_in_session) * 5)
        score += feature_score
        
        # Session duration score (0-10 points)
        duration_minutes = self.get_age_minutes()
        duration_score = min(10, duration_minutes / 6)  # 1 point per 6 minutes, max 10
        score += duration_score
        
        self.session_quality_score = score
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session info to dictionary for analytics."""
        return {
            'user_id': str(self.user_id)[:8] + '...',  # Anonymized for privacy
            'thread_id': str(self.thread_id),
            'session_id': str(self.session_id),
            'request_id': str(self.request_id),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'age_minutes': self.get_age_minutes(),
            'inactivity_minutes': self.get_inactivity_minutes(),
            'websocket_connection_id': self.websocket_connection_id,
            'messages_in_session': self.messages_in_session,
            'agent_executions_in_session': self.agent_executions_in_session,
            'features_used_in_session': list(self.features_used_in_session),
            'session_quality_score': self.session_quality_score,
            'metadata_keys': list(self.session_metadata.keys())
        }


class UserSessionTrackerError(Exception):
    """Raised when user session tracking operations fail."""
    pass


class UserSessionTracker:
    """SSOT for user-level session tracking and engagement analytics.
    
    This class provides comprehensive user session tracking as a Single Source
    of Truth (SSOT) for user-focused session operations. It focuses on user
    behavior analytics, engagement tracking, and session quality optimization.
    
    Key Design Principles:
    - User-centric session tracking and analytics
    - Privacy-focused data collection and storage
    - Engagement optimization and quality scoring
    - Business value measurement and conversion tracking
    - Multi-user isolation and security
    - Real-time user behavior insights
    
    Business Focus:
    Unlike system-focused session management, this tracker focuses on user behavior,
    engagement patterns, and business value optimization for individual users.
    """
    
    def __init__(self, 
                 cleanup_interval_minutes: int = 30,
                 max_session_age_hours: int = 24,
                 max_inactive_minutes: int = 120,
                 enable_analytics: bool = True):
        """Initialize UserSessionTracker with analytics and cleanup settings.
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (default 30 minutes)
            max_session_age_hours: Maximum session age before cleanup (default 24 hours)
            max_inactive_minutes: Maximum inactivity before cleanup (default 2 hours)
            enable_analytics: Enable user behavior analytics tracking
        """
        self._user_sessions: Dict[str, UserSessionInfo] = {}
        self._user_metrics: Dict[UserID, UserEngagementMetrics] = {}
        self._session_lock = Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval_minutes = cleanup_interval_minutes
        self._max_session_age_hours = max_session_age_hours
        self._max_inactive_minutes = max_inactive_minutes
        self._enable_analytics = enable_analytics
        self._daily_reset_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        logger.info(f"Initialized UserSessionTracker with cleanup_interval={cleanup_interval_minutes}min, "
                   f"max_age={max_session_age_hours}h, max_inactive={max_inactive_minutes}min, "
                   f"analytics_enabled={enable_analytics}")
    
    async def start_analytics_tracking(self) -> None:
        """Start background analytics tracking tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("User analytics tracking already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._background_analytics())
        logger.info("Started user session analytics background tracking")
    
    async def stop_analytics_tracking(self) -> None:
        """Stop background analytics tracking tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped user session analytics background tracking")
    
    async def _background_analytics(self) -> None:
        """Background analytics task for user behavior tracking."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_minutes * 60)
                
                # Clean up expired sessions
                cleaned_count = await self.cleanup_expired_sessions()
                if cleaned_count > 0:
                    logger.info(f"User analytics cleanup removed {cleaned_count} expired sessions")
                
                # Update user engagement metrics
                if self._enable_analytics:
                    await self._update_user_engagement_metrics()
                
                # Reset daily counters if needed
                self._reset_daily_metrics_if_needed()
                
            except asyncio.CancelledError:
                logger.info("User analytics tracking task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in user analytics tracking: {e}", exc_info=True)
    
    async def _update_user_engagement_metrics(self) -> None:
        """Update user engagement and behavior analytics."""
        with self._session_lock:
            for user_id, metrics in self._user_metrics.items():
                # Update session quality scores
                user_sessions = [session for session in self._user_sessions.values() 
                               if session.user_id == user_id]
                
                if user_sessions:
                    # Calculate average session quality
                    quality_scores = [session.calculate_session_quality() for session in user_sessions]
                    avg_quality = sum(quality_scores) / len(quality_scores)
                    
                    # Update conversion indicators based on session quality
                    if avg_quality > 80:
                        metrics.conversion_indicators['high_engagement'] = True
                    if avg_quality > 60:
                        metrics.conversion_indicators['moderate_engagement'] = True
                    
                    # Update user satisfaction score (simple heuristic)
                    metrics.user_satisfaction_score = avg_quality / 100.0
    
    def _reset_daily_metrics_if_needed(self) -> None:
        """Reset daily metrics if we've crossed into a new day."""
        now = datetime.now(timezone.utc)
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if current_day > self._daily_reset_time:
            logger.info("Resetting daily user session metrics")
            with self._session_lock:
                for metrics in self._user_metrics.values():
                    metrics.sessions_created_today = 0
                    metrics.sessions_reused_today = 0
            self._daily_reset_time = current_day
    
    def _generate_session_key(self, user_id: UserID, thread_id: ThreadID) -> str:
        """Generate consistent session key for storage."""
        return f"{user_id}:{thread_id}"
    
    def _get_user_metrics(self, user_id: UserID) -> UserEngagementMetrics:
        """Get or create user engagement metrics."""
        if user_id not in self._user_metrics:
            self._user_metrics[user_id] = UserEngagementMetrics()
        return self._user_metrics[user_id]
    
    async def track_user_session(self, 
                                user_id: UserID, 
                                thread_id: ThreadID,
                                session_id: SessionID,
                                request_id: RequestID,
                                websocket_connection_id: Optional[str] = None) -> UserSessionInfo:
        """Track a new or existing user session.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier for conversation continuity
            session_id: Session identifier
            request_id: Request identifier
            websocket_connection_id: Optional WebSocket connection ID
            
        Returns:
            UserSessionInfo: Session tracking information
            
        Raises:
            UserSessionTrackerError: If session tracking fails
        """
        try:
            session_key = self._generate_session_key(user_id, thread_id)
            
            with self._session_lock:
                # Check for existing session
                if session_key in self._user_sessions:
                    existing_session = self._user_sessions[session_key]
                    existing_session.update_activity()
                    
                    # Update WebSocket connection if provided
                    if websocket_connection_id:
                        existing_session.websocket_connection_id = websocket_connection_id
                    
                    # Update user metrics
                    user_metrics = self._get_user_metrics(user_id)
                    user_metrics.sessions_reused_today += 1
                    user_metrics.update_activity()
                    
                    logger.debug(f"Updated existing user session tracking for {user_id}, thread {thread_id}")
                    return existing_session
                
                # Create new session tracking
                now = datetime.now(timezone.utc)
                session_info = UserSessionInfo(
                    user_id=user_id,
                    thread_id=thread_id,
                    session_id=session_id,
                    request_id=request_id,
                    created_at=now,
                    last_activity=now,
                    websocket_connection_id=websocket_connection_id
                )
                
                self._user_sessions[session_key] = session_info
                
                # Update user metrics
                user_metrics = self._get_user_metrics(user_id)
                user_metrics.total_sessions += 1
                user_metrics.active_sessions += 1
                user_metrics.sessions_created_today += 1
                user_metrics.update_activity()
                
                logger.info(f"Created new user session tracking for {user_id}, thread {thread_id}")
                return session_info
                
        except Exception as e:
            logger.error(f"Failed to track user session for {user_id}: {e}", exc_info=True)
            raise UserSessionTrackerError(f"User session tracking failed: {str(e)}") from e
    
    async def record_user_message(self, user_id: UserID, thread_id: ThreadID) -> bool:
        """Record user message for engagement tracking.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            
        Returns:
            True if message was recorded
        """
        session_key = self._generate_session_key(user_id, thread_id)
        
        with self._session_lock:
            if session_key in self._user_sessions:
                self._user_sessions[session_key].record_message()
                
                # Update user metrics
                user_metrics = self._get_user_metrics(user_id)
                user_metrics.record_message_sent()
                
                return True
        
        return False
    
    async def record_agent_execution(self, user_id: UserID, thread_id: ThreadID) -> bool:
        """Record agent execution for user engagement tracking.
        
        Args:
            user_id: User identifier  
            thread_id: Thread identifier
            
        Returns:
            True if execution was recorded
        """
        session_key = self._generate_session_key(user_id, thread_id)
        
        with self._session_lock:
            if session_key in self._user_sessions:
                self._user_sessions[session_key].record_agent_execution()
                
                # Update user metrics
                user_metrics = self._get_user_metrics(user_id)
                user_metrics.record_agent_execution()
                
                return True
        
        return False
    
    async def record_feature_usage(self, user_id: UserID, thread_id: ThreadID, 
                                 feature_name: str) -> bool:
        """Record feature usage for user behavior tracking.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            feature_name: Name of feature used
            
        Returns:
            True if usage was recorded
        """
        session_key = self._generate_session_key(user_id, thread_id)
        
        with self._session_lock:
            if session_key in self._user_sessions:
                self._user_sessions[session_key].record_feature_usage(feature_name)
                
                # Update user metrics
                user_metrics = self._get_user_metrics(user_id)
                user_metrics.record_feature_usage(feature_name)
                
                return True
        
        return False
    
    async def get_user_engagement_metrics(self, user_id: UserID) -> UserEngagementMetrics:
        """Get engagement metrics for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserEngagementMetrics: User's engagement metrics
        """
        with self._session_lock:
            return self._get_user_metrics(user_id)
    
    async def get_session_info(self, user_id: UserID, thread_id: ThreadID) -> Optional[UserSessionInfo]:
        """Get session information for a user's thread.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            
        Returns:
            UserSessionInfo if found, None otherwise
        """
        session_key = self._generate_session_key(user_id, thread_id)
        
        with self._session_lock:
            return self._user_sessions.get(session_key)
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired user sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.now(timezone.utc)
            expired_keys = []
            
            with self._session_lock:
                for session_key, session_info in self._user_sessions.items():
                    # Check age limits
                    age_minutes = session_info.get_age_minutes()
                    inactivity_minutes = session_info.get_inactivity_minutes()
                    
                    should_cleanup = (
                        age_minutes > (self._max_session_age_hours * 60) or
                        inactivity_minutes > self._max_inactive_minutes
                    )
                    
                    if should_cleanup:
                        expired_keys.append(session_key)
                        logger.debug(f"Marking user session for cleanup: {session_key} "
                                   f"(age: {age_minutes:.1f}min, inactive: {inactivity_minutes:.1f}min)")
                
                # Remove expired sessions and update metrics
                for key in expired_keys:
                    if key in self._user_sessions:
                        session_info = self._user_sessions[key]
                        
                        # Update user metrics
                        if session_info.user_id in self._user_metrics:
                            self._user_metrics[session_info.user_id].active_sessions -= 1
                            self._user_metrics[session_info.user_id].expired_sessions_cleaned += 1
                        
                        del self._user_sessions[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired user sessions")
            
            return len(expired_keys)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired user sessions: {e}", exc_info=True)
            return 0
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get user analytics summary across all users.
        
        Returns:
            Analytics summary with anonymized user data
        """
        with self._session_lock:
            total_users = len(self._user_metrics)
            total_sessions = sum(metrics.total_sessions for metrics in self._user_metrics.values())
            total_messages = sum(metrics.total_messages_sent for metrics in self._user_metrics.values())
            total_executions = sum(metrics.total_agent_executions for metrics in self._user_metrics.values())
            
            # Calculate averages
            avg_sessions_per_user = total_sessions / total_users if total_users > 0 else 0
            avg_messages_per_user = total_messages / total_users if total_users > 0 else 0
            
            # Feature usage analytics
            all_features = set()
            for metrics in self._user_metrics.values():
                all_features.update(metrics.feature_usage_count.keys())
            
            feature_usage_summary = {}
            for feature in all_features:
                usage_count = sum(
                    metrics.feature_usage_count.get(feature, 0) 
                    for metrics in self._user_metrics.values()
                )
                feature_usage_summary[feature] = usage_count
            
            return {
                'total_users_tracked': total_users,
                'total_sessions_tracked': len(self._user_sessions),
                'total_user_sessions': total_sessions,
                'total_messages_sent': total_messages,
                'total_agent_executions': total_executions,
                'avg_sessions_per_user': avg_sessions_per_user,
                'avg_messages_per_user': avg_messages_per_user,
                'feature_usage_summary': feature_usage_summary,
                'analytics_enabled': self._enable_analytics
            }


# Global user session tracker instance
_global_user_tracker: Optional[UserSessionTracker] = None
_tracker_lock = Lock()


def get_user_session_tracker(cleanup_interval_minutes: int = 30,
                            max_session_age_hours: int = 24,
                            max_inactive_minutes: int = 120,
                            enable_analytics: bool = True) -> UserSessionTracker:
    """Get or create the global user session tracker instance.
    
    Args:
        cleanup_interval_minutes: How often to run cleanup (default 30 minutes)
        max_session_age_hours: Maximum session age before cleanup (default 24 hours)
        max_inactive_minutes: Maximum inactivity before cleanup (default 2 hours)
        enable_analytics: Enable user behavior analytics tracking
        
    Returns:
        UserSessionTracker: Global tracker instance
    """
    global _global_user_tracker
    
    with _tracker_lock:
        if _global_user_tracker is None:
            _global_user_tracker = UserSessionTracker(
                cleanup_interval_minutes=cleanup_interval_minutes,
                max_session_age_hours=max_session_age_hours,
                max_inactive_minutes=max_inactive_minutes,
                enable_analytics=enable_analytics
            )
            logger.info("Created global UserSessionTracker instance")
        
        return _global_user_tracker


async def initialize_user_session_tracker() -> UserSessionTracker:
    """Initialize the global user session tracker and start analytics.
    
    This should be called during application startup.
    
    Returns:
        UserSessionTracker: Initialized tracker
    """
    tracker = get_user_session_tracker()
    await tracker.start_analytics_tracking()
    logger.info("Initialized UserSessionTracker with background analytics")
    return tracker


async def shutdown_user_session_tracker() -> None:
    """Shutdown the global user session tracker.
    
    This should be called during application shutdown.
    """
    global _global_user_tracker
    
    if _global_user_tracker:
        await _global_user_tracker.stop_analytics_tracking()
        cleaned_count = await _global_user_tracker.cleanup_expired_sessions()
        logger.info(f"Shutdown UserSessionTracker - cleaned {cleaned_count} sessions")
        _global_user_tracker = None


# Export public interface
__all__ = [
    'UserSessionTracker',
    'UserSessionInfo',
    'UserEngagementMetrics',
    'UserSessionTrackerError',
    'get_user_session_tracker',
    'initialize_user_session_tracker',
    'shutdown_user_session_tracker'
]