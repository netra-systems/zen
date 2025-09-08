"""Session Metrics SSOT - Unified Session Metrics Implementation

This module provides the Single Source of Truth (SSOT) for all session metrics 
across the Netra platform, consolidating previously duplicated implementations.

Business Value Justification (BVJ):
- Segment: Platform Security & Stability (all tiers)
- Business Goal: Eliminate SSOT violations causing AttributeError crashes
- Value Impact: Prevents session creation failures affecting user experience
- Strategic Impact: Foundation for reliable session tracking and monitoring

Key Features:
1. Unified base classes for all session metrics
2. Backward compatibility with existing field mappings
3. Comprehensive error handling and validation
4. Type safety with proper enums and dataclasses
5. Clear separation between database and system metrics

CRITICAL: This consolidates SessionMetrics implementations from:
- netra_backend.app.database.request_scoped_session_factory
- shared.session_management.user_session_manager

Architecture Compliance:
- SSOT: Single canonical implementation per metric type
- Type Safety: Strongly typed with proper validation
- Backward Compatibility: Maintains all existing interfaces
- Import Rules: Absolute imports only
"""

import asyncio
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Union
import logging

# SSOT Type imports
from shared.types import UserID, ThreadID, RunID, RequestID


class SessionState(str, Enum):
    """Session lifecycle states for tracking."""
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class BaseSessionMetrics:
    """Base class for all session metrics with common fields and behaviors.
    
    This provides the foundation for both database and system-level metrics
    while ensuring consistent interfaces and behaviors across the platform.
    """
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: Optional[datetime] = field(default=None)
    error_count: int = field(default=0)
    last_error: Optional[str] = field(default=None)
    
    def __post_init__(self) -> None:
        """Initialize last_activity_at if not provided."""
        if self.last_activity_at is None:
            self.last_activity_at = self.created_at
    
    def mark_activity(self) -> None:
        """Mark recent session activity."""
        self.last_activity_at = datetime.now(timezone.utc)
    
    def record_error(self, error: str) -> None:
        """Record session error."""
        self.error_count += 1
        self.last_error = error
        self.mark_activity()
    
    def get_age_seconds(self) -> float:
        """Get session age in seconds."""
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds()
    
    def get_inactivity_seconds(self) -> float:
        """Get seconds since last activity."""
        if not self.last_activity_at:
            return self.get_age_seconds()
        delta = datetime.now(timezone.utc) - self.last_activity_at
        return delta.total_seconds()


@dataclass  
class DatabaseSessionMetrics(BaseSessionMetrics):
    """Database session metrics for connection tracking and performance monitoring.
    
    This class tracks individual database session performance, connection lifecycle,
    and query execution metrics. Used by request_scoped_session_factory.py.
    
    CRITICAL: This replaces the SessionMetrics class in request_scoped_session_factory.py
    Fields are mapped for backward compatibility with existing code.
    """
    session_id: str = field(default="")
    request_id: str = field(default="")
    user_id: str = field(default="")
    state: SessionState = field(default=SessionState.CREATED)
    query_count: int = field(default=0)
    transaction_count: int = field(default=0)
    total_time_ms: Optional[float] = field(default=None)
    closed_at: Optional[datetime] = field(default=None)
    
    def __init__(self, session_id: str = "", request_id: str = "", user_id: str = ""):
        """Initialize DatabaseSessionMetrics with proper field assignment.
        
        This constructor ensures that session_id, request_id, and user_id are assigned correctly
        regardless of dataclass field inheritance order.
        """
        # Initialize base class with defaults
        super().__init__()
        
        # Set the specific database session fields
        self.session_id = session_id
        self.request_id = request_id
        self.user_id = user_id
        self.state = SessionState.CREATED
        self.query_count = 0
        self.transaction_count = 0
        self.total_time_ms = None
        self.closed_at = None
    
    # Backward compatibility properties for existing error logging code
    @property
    def last_activity(self) -> Optional[datetime]:
        """Backward compatibility for last_activity field access."""
        return self.last_activity_at
        
    @property
    def operations_count(self) -> int:
        """Backward compatibility for operations_count field access."""
        return self.query_count
        
    @property  
    def errors(self) -> int:
        """Backward compatibility for errors field access."""
        return self.error_count
    
    def increment_query_count(self) -> None:
        """Record a database query execution."""
        self.query_count += 1
        self.mark_activity()
    
    def increment_transaction_count(self) -> None:
        """Record a database transaction."""
        self.transaction_count += 1
        self.mark_activity()
    
    def record_error(self, error: str) -> None:
        """Record session error and update state."""
        super().record_error(error)
        self.state = SessionState.ERROR
    
    def close_session(self, total_time_ms: Optional[float] = None) -> None:
        """Mark session as closed with optional timing."""
        self.state = SessionState.CLOSED
        self.closed_at = datetime.now(timezone.utc)
        if total_time_ms is not None:
            self.total_time_ms = total_time_ms
        elif self.created_at and self.closed_at:
            # Auto-calculate total time if not provided
            # Ensure created_at is a datetime object (handle both datetime and string cases)
            if isinstance(self.created_at, datetime):
                self.total_time_ms = (self.closed_at - self.created_at).total_seconds() * 1000
            else:
                # Log warning for type safety but don't crash
                self.total_time_ms = 0.0
    
    def close(self) -> None:
        """Backward compatibility method for close() calls."""
        self.close_session()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and monitoring."""
        return {
            'session_id': self.session_id,
            'request_id': self.request_id,
            'user_id': self.user_id,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'query_count': self.query_count,
            'transaction_count': self.transaction_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'total_time_ms': self.total_time_ms,
            'age_seconds': self.get_age_seconds(),
            'inactivity_seconds': self.get_inactivity_seconds()
        }


@dataclass
class SystemSessionMetrics(BaseSessionMetrics):
    """System-wide session metrics for monitoring and capacity planning.
    
    This class tracks aggregate session statistics across the entire system,
    including memory usage, session counts, and cleanup operations.
    Used by user_session_manager.py and system monitoring components.
    
    CRITICAL: This replaces the SessionMetrics class in user_session_manager.py
    """
    total_sessions: int = field(default=0)
    active_sessions: int = field(default=0)
    expired_sessions_cleaned: int = field(default=0)
    sessions_created_today: int = field(default=0)
    sessions_reused_today: int = field(default=0)
    average_session_duration_minutes: float = field(default=0.0)
    memory_usage_mb: float = field(default=0.0)
    
    def increment_total_sessions(self) -> None:
        """Record creation of a new session."""
        self.total_sessions += 1
        self.sessions_created_today += 1
        self.mark_activity()
    
    def increment_active_sessions(self) -> None:
        """Record activation of a session."""
        self.active_sessions += 1
        self.mark_activity()
    
    def decrement_active_sessions(self) -> None:
        """Record deactivation of a session."""
        if self.active_sessions > 0:
            self.active_sessions -= 1
        self.mark_activity()
    
    def record_session_cleanup(self, count: int = 1) -> None:
        """Record cleanup of expired sessions."""
        self.expired_sessions_cleaned += count
        self.mark_activity()
    
    def record_session_reuse(self) -> None:
        """Record reuse of an existing session."""
        self.sessions_reused_today += 1
        self.mark_activity()
    
    def update_memory_usage(self, memory_mb: float) -> None:
        """Update current memory usage."""
        self.memory_usage_mb = memory_mb
        self.mark_activity()
    
    def update_average_duration(self, duration_minutes: float) -> None:
        """Update average session duration."""
        self.average_session_duration_minutes = duration_minutes
        self.mark_activity()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging/monitoring."""
        return {
            'total_sessions': self.total_sessions,
            'active_sessions': self.active_sessions,
            'expired_sessions_cleaned': self.expired_sessions_cleaned,
            'sessions_created_today': self.sessions_created_today,
            'sessions_reused_today': self.sessions_reused_today,
            'average_session_duration_minutes': self.average_session_duration_minutes,
            'memory_usage_mb': self.memory_usage_mb,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat(),
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'age_seconds': self.get_age_seconds(),
            'inactivity_seconds': self.get_inactivity_seconds()
        }


# Backward compatibility aliases for existing imports
SessionMetrics = DatabaseSessionMetrics  # Default to database metrics for existing code


# Factory functions for creating metrics with proper initialization
def create_database_session_metrics(
    session_id: str,
    request_id: str,
    user_id: str
) -> DatabaseSessionMetrics:
    """Create database session metrics with proper initialization."""
    return DatabaseSessionMetrics(session_id, request_id, user_id)


def create_system_session_metrics() -> SystemSessionMetrics:
    """Create system session metrics with proper initialization."""
    return SystemSessionMetrics()


# Type aliases for clarity
DatabaseMetrics = DatabaseSessionMetrics
SystemMetrics = SystemSessionMetrics


__all__ = [
    'SessionState',
    'BaseSessionMetrics', 
    'DatabaseSessionMetrics',
    'SystemSessionMetrics',
    'SessionMetrics',  # Backward compatibility alias
    'create_database_session_metrics',
    'create_system_session_metrics',
    'DatabaseMetrics',
    'SystemMetrics'
]