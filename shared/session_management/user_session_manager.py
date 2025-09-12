"""UserSessionManager - SSOT Implementation for User Session Lifecycle Management

This module provides comprehensive session management functionality as a Single Source 
of Truth (SSOT) for user session lifecycle operations across the entire Netra platform.

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Core chat continuity functionality
- Business Goal: Enable proper multi-turn AI conversations and prevent memory leaks
- Value Impact: Delivers 90% of platform value through reliable chat continuity
- Strategic Impact: CRITICAL - Prevents session memory leaks and enables true multi-user support

Key Features:
- Complete session lifecycle management (create, retrieve, update, cleanup)
- Integration with existing UnifiedIdGenerator session management
- Multi-user isolation with proper thread management
- WebSocket connection lifecycle integration
- Automatic cleanup of inactive sessions with configurable timeouts
- Comprehensive logging and monitoring for session operations
- Memory leak prevention through proper session cleanup
- Thread-safe operations with proper locking mechanisms

Architecture Integration:
This UserSessionManager builds upon and enhances the existing UnifiedIdGenerator
session management while providing a higher-level SSOT interface for all
session-related operations throughout the system.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from threading import Lock
from contextlib import asynccontextmanager

# SSOT imports
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.metrics.session_metrics import SystemSessionMetrics, SessionMetrics, create_system_session_metrics
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# SessionMetrics now imported from shared.metrics.session_metrics
# This eliminates SSOT violation and uses SystemSessionMetrics


@dataclass
class UserSession:
    """Enhanced user session with full lifecycle management."""
    user_id: str
    thread_id: str
    run_id: str
    request_id: str
    created_at: datetime
    last_activity: datetime
    websocket_connection_id: Optional[str] = None
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    execution_context: Optional[UserExecutionContext] = None
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for logging."""
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'request_id': self.request_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'age_minutes': self.get_age_minutes(),
            'inactivity_minutes': self.get_inactivity_minutes(),
            'websocket_connection_id': self.websocket_connection_id,
            'has_execution_context': self.execution_context is not None,
            'metadata_keys': list(self.session_metadata.keys())
        }


class SessionManagerError(Exception):
    """Raised when session management operations fail."""
    pass


class UserSessionManager:
    """SSOT for user session and context management.
    
    This class provides comprehensive session lifecycle management as a Single Source
    of Truth (SSOT) for all user session operations. It integrates with the existing
    UnifiedIdGenerator session management while providing enhanced functionality.
    
    Key Design Principles:
    - Session reuse over creation for conversation continuity
    - Multi-user isolation with proper thread management
    - Automatic cleanup to prevent memory leaks
    - Thread-safe operations with proper locking
    - Comprehensive logging for debugging and monitoring
    - WebSocket lifecycle integration
    - Memory usage monitoring and optimization
    """
    
    def __init__(self, 
                 cleanup_interval_minutes: int = 30,
                 max_session_age_hours: int = 24,
                 max_inactive_minutes: int = 120):
        """Initialize UserSessionManager with configurable cleanup settings.
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (default 30 minutes)
            max_session_age_hours: Maximum session age before cleanup (default 24 hours)
            max_inactive_minutes: Maximum inactivity before cleanup (default 2 hours)
        """
        self._sessions: Dict[str, UserSession] = {}
        self._session_lock = Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval_minutes = cleanup_interval_minutes
        self._max_session_age_hours = max_session_age_hours
        self._max_inactive_minutes = max_inactive_minutes
        self._metrics = create_system_session_metrics()
        self._daily_reset_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        logger.info(f"Initialized UserSessionManager with cleanup_interval={cleanup_interval_minutes}min, "
                   f"max_age={max_session_age_hours}h, max_inactive={max_inactive_minutes}min")
    
    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("Cleanup task already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Started session cleanup background task")
    
    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped session cleanup background task")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task that runs in the background."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_minutes * 60)
                cleaned_count = await self.cleanup_expired_sessions()
                if cleaned_count > 0:
                    logger.info(f"Background cleanup removed {cleaned_count} expired sessions")
                    
                # Reset daily counters if needed
                self._reset_daily_metrics_if_needed()
                
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}", exc_info=True)
                # Continue running despite errors
    
    def _reset_daily_metrics_if_needed(self) -> None:
        """Reset daily metrics if we've crossed into a new day."""
        now = datetime.now(timezone.utc)
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if current_day > self._daily_reset_time:
            logger.info("Resetting daily session metrics")
            self._metrics.sessions_created_today = 0
            self._metrics.sessions_reused_today = 0
            self._daily_reset_time = current_day
    
    def _generate_session_key(self, user_id: str, thread_id: str) -> str:
        """Generate consistent session key for storage."""
        return f"{user_id}:{thread_id}"
    
    async def get_or_create_user_session(self, 
                                        user_id: str, 
                                        thread_id: str,
                                        run_id: Optional[str] = None,
                                        websocket_connection_id: Optional[str] = None) -> UserExecutionContext:
        """Get existing session or create new one ONLY if needed - CRITICAL for chat continuity.
        
        This is the core method that implements proper session management for conversation
        continuity. It ensures that existing sessions are reused rather than creating
        new ones for every message, which was the root cause of memory leaks and broken
        chat continuity.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for conversation continuity
            run_id: Optional run identifier for specific agent executions
            websocket_connection_id: Optional WebSocket connection ID
            
        Returns:
            UserExecutionContext: Either existing context (for continuity) or new context
            
        Raises:
            SessionManagerError: If session creation/retrieval fails
            InvalidContextError: If context validation fails
        """
        try:
            session_key = self._generate_session_key(user_id, thread_id)
            
            with self._session_lock:
                # Check for existing session first (CRITICAL: maintains continuity)
                if session_key in self._sessions:
                    existing_session = self._sessions[session_key]
                    existing_session.update_activity()
                    
                    # Handle run_id logic for existing sessions
                    if run_id and run_id != existing_session.run_id:
                        # Different run_id means new agent execution within same thread
                        logger.info(f"Creating new run {run_id} within existing session {session_key}")
                        existing_session.run_id = run_id
                        existing_session.request_id = UnifiedIdGenerator.generate_base_id("req")
                    
                    # Update WebSocket connection if provided
                    if websocket_connection_id:
                        existing_session.websocket_connection_id = websocket_connection_id
                    
                    # Update/create execution context
                    if existing_session.execution_context:
                        # Update existing context with any new connection info
                        if websocket_connection_id and websocket_connection_id != existing_session.execution_context.websocket_client_id:
                            existing_session.execution_context = existing_session.execution_context.with_websocket_connection(websocket_connection_id)
                    else:
                        # Create new execution context for existing session
                        existing_session.execution_context = UserExecutionContext.from_request(
                            user_id=existing_session.user_id,
                            thread_id=existing_session.thread_id,
                            run_id=existing_session.run_id,
                            request_id=existing_session.request_id,
                            websocket_client_id=existing_session.websocket_connection_id
                        )
                    
                    # Update metrics
                    self._metrics.record_session_reuse()
                    
                    logger.debug(f"Reused existing session for user {user_id}, thread {thread_id}")
                    return existing_session.execution_context
                
                # Create new session only if genuinely needed
                logger.info(f"Creating new session for user {user_id}, thread {thread_id}")
                
                # Use UnifiedIdGenerator for session management integration
                session_data = UnifiedIdGenerator.get_or_create_user_session(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    operation="chat"
                )
                
                # Generate WebSocket connection ID if not provided
                if not websocket_connection_id:
                    websocket_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
                
                # Create UserExecutionContext
                execution_context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=session_data["thread_id"],
                    run_id=session_data["run_id"],
                    request_id=session_data["request_id"],
                    websocket_client_id=websocket_connection_id
                )
                
                # Create and store UserSession
                now = datetime.now(timezone.utc)
                user_session = UserSession(
                    user_id=user_id,
                    thread_id=session_data["thread_id"],
                    run_id=session_data["run_id"],
                    request_id=session_data["request_id"],
                    created_at=now,
                    last_activity=now,
                    websocket_connection_id=websocket_connection_id,
                    execution_context=execution_context
                )
                
                self._sessions[session_key] = user_session
                
                # Update metrics
                self._metrics.increment_total_sessions()
                self._metrics.increment_active_sessions()
                
                logger.info(f"Created new session for user {user_id}, thread {thread_id}: {execution_context.get_correlation_id()}")
                return execution_context
                
        except Exception as e:
            logger.error(f"Failed to get or create session for user {user_id}: {e}", exc_info=True)
            raise SessionManagerError(f"Session management failed: {str(e)}") from e
    
    async def get_existing_session(self, user_id: str, thread_id: str) -> Optional[UserExecutionContext]:
        """Get existing session without creating new one.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            
        Returns:
            UserExecutionContext if session exists, None otherwise
        """
        try:
            session_key = self._generate_session_key(user_id, thread_id)
            
            with self._session_lock:
                if session_key in self._sessions:
                    session = self._sessions[session_key]
                    session.update_activity()
                    logger.debug(f"Retrieved existing session for user {user_id}, thread {thread_id}")
                    return session.execution_context
                
                logger.debug(f"No existing session found for user {user_id}, thread {thread_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get existing session for user {user_id}: {e}", exc_info=True)
            return None
    
    async def update_session_websocket(self, user_id: str, thread_id: str, 
                                     websocket_connection_id: str) -> bool:
        """Update WebSocket connection for existing session.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            websocket_connection_id: New WebSocket connection ID
            
        Returns:
            True if session was updated, False if session not found
        """
        try:
            session_key = self._generate_session_key(user_id, thread_id)
            
            with self._session_lock:
                if session_key in self._sessions:
                    session = self._sessions[session_key]
                    session.websocket_connection_id = websocket_connection_id
                    session.update_activity()
                    
                    # Update execution context with new WebSocket connection
                    if session.execution_context:
                        session.execution_context = session.execution_context.with_websocket_connection(websocket_connection_id)
                    
                    logger.info(f"Updated WebSocket connection for session {session_key}: {websocket_connection_id}")
                    return True
                
                logger.warning(f"Cannot update WebSocket for non-existent session: {session_key}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update WebSocket for session {user_id}:{thread_id}: {e}", exc_info=True)
            return False
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        try:
            with self._session_lock:
                keys_to_remove = [key for key in self._sessions.keys() 
                                 if key.startswith(f"{user_id}:")]
                
                for key in keys_to_remove:
                    del self._sessions[key]
                
                # Update metrics
                for _ in keys_to_remove:
                    self._metrics.decrement_active_sessions()
                
                logger.info(f"Invalidated {len(keys_to_remove)} sessions for user {user_id}")
                return len(keys_to_remove)
                
        except Exception as e:
            logger.error(f"Failed to invalidate sessions for user {user_id}: {e}", exc_info=True)
            return 0
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions to prevent memory leaks.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.now(timezone.utc)
            expired_keys = []
            
            with self._session_lock:
                for session_key, session in self._sessions.items():
                    # Check age limits
                    age_minutes = session.get_age_minutes()
                    inactivity_minutes = session.get_inactivity_minutes()
                    
                    should_cleanup = (
                        age_minutes > (self._max_session_age_hours * 60) or
                        inactivity_minutes > self._max_inactive_minutes
                    )
                    
                    if should_cleanup:
                        expired_keys.append(session_key)
                        logger.debug(f"Marking session for cleanup: {session_key} "
                                   f"(age: {age_minutes:.1f}min, inactive: {inactivity_minutes:.1f}min)")
                
                # Remove expired sessions
                for key in expired_keys:
                    del self._sessions[key]
                
                # Update metrics
                for _ in expired_keys:
                    self._metrics.decrement_active_sessions()
                self._metrics.record_session_cleanup(len(expired_keys))
            
            # Also clean up UnifiedIdGenerator sessions
            unified_cleaned = UnifiedIdGenerator.cleanup_expired_sessions(self._max_session_age_hours)
            
            total_cleaned = len(expired_keys) + unified_cleaned
            if total_cleaned > 0:
                logger.info(f"Cleaned up {len(expired_keys)} UserSession objects and "
                           f"{unified_cleaned} UnifiedIdGenerator sessions")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}", exc_info=True)
            return 0
    
    def get_session_metrics(self) -> SystemSessionMetrics:
        """Get current session management metrics.
        
        Returns:
            SystemSessionMetrics object with current statistics
        """
        try:
            with self._session_lock:
                # Update active session count
                self._metrics.active_sessions = len(self._sessions)
                
                # Calculate average session duration
                if self._sessions:
                    total_duration = sum(session.get_age_minutes() for session in self._sessions.values())
                    duration_minutes = total_duration / len(self._sessions)
                    self._metrics.update_average_duration(duration_minutes)
                else:
                    self._metrics.update_average_duration(0.0)
                
                # Estimate memory usage (rough calculation)
                session_count = len(self._sessions)
                estimated_mb = session_count * 0.01  # Rough estimate: 10KB per session
                self._metrics.update_memory_usage(estimated_mb)
            
            logger.debug(f"Session metrics: {self._metrics.to_dict()}")
            return self._metrics
            
        except Exception as e:
            logger.error(f"Failed to get session metrics: {e}", exc_info=True)
            return create_system_session_metrics()
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions for monitoring.
        
        Returns:
            List of session dictionaries with anonymized data
        """
        try:
            with self._session_lock:
                sessions = []
                for session_key, session in self._sessions.items():
                    session_dict = session.to_dict()
                    # Anonymize sensitive data
                    session_dict['user_id'] = session_dict['user_id'][:8] + '...'
                    session_dict['session_key'] = session_key.replace(session.user_id, session.user_id[:8] + '...')
                    sessions.append(session_dict)
                
                return sorted(sessions, key=lambda s: s['created_at'], reverse=True)
                
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}", exc_info=True)
            return []
    
    @asynccontextmanager
    async def managed_session(self, user_id: str, thread_id: str, 
                             run_id: Optional[str] = None,
                             websocket_connection_id: Optional[str] = None):
        """Async context manager for session lifecycle management.
        
        This context manager ensures proper session cleanup and resource management
        for one-off operations that need session context.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            run_id: Optional run identifier
            websocket_connection_id: Optional WebSocket connection ID
            
        Yields:
            UserExecutionContext: Managed session context
            
        Example:
            async with session_manager.managed_session(user_id, thread_id) as context:
                # Use context for operations
                result = await some_agent.execute(context)
            # Session is automatically updated/cleaned up
        """
        context = None
        try:
            logger.debug(f"Starting managed session for user {user_id}, thread {thread_id}")
            context = await self.get_or_create_user_session(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_connection_id=websocket_connection_id
            )
            yield context
            
        except Exception as e:
            logger.error(f"Exception in managed session for user {user_id}: {e}", exc_info=True)
            raise
        finally:
            if context:
                # Update last activity for the session
                session_key = self._generate_session_key(user_id, thread_id)
                with self._session_lock:
                    if session_key in self._sessions:
                        self._sessions[session_key].update_activity()
                        
                logger.debug(f"Completed managed session for user {user_id}, thread {thread_id}")


# Global session manager instance - SSOT singleton
_global_session_manager: Optional[UserSessionManager] = None
_manager_lock = Lock()


def get_session_manager(cleanup_interval_minutes: int = 30,
                       max_session_age_hours: int = 24,
                       max_inactive_minutes: int = 120) -> UserSessionManager:
    """Get or create the global session manager instance - SSOT pattern.
    
    Args:
        cleanup_interval_minutes: How often to run cleanup (default 30 minutes)
        max_session_age_hours: Maximum session age before cleanup (default 24 hours)  
        max_inactive_minutes: Maximum inactivity before cleanup (default 2 hours)
        
    Returns:
        UserSessionManager: Global session manager instance
    """
    global _global_session_manager
    
    with _manager_lock:
        if _global_session_manager is None:
            _global_session_manager = UserSessionManager(
                cleanup_interval_minutes=cleanup_interval_minutes,
                max_session_age_hours=max_session_age_hours,
                max_inactive_minutes=max_inactive_minutes
            )
            logger.info("Created global UserSessionManager instance")
        
        return _global_session_manager


async def initialize_session_manager() -> UserSessionManager:
    """Initialize the global session manager and start cleanup tasks.
    
    This should be called during application startup.
    
    Returns:
        UserSessionManager: Initialized session manager
    """
    session_manager = get_session_manager()
    await session_manager.start_cleanup_task()
    logger.info("Initialized UserSessionManager with background cleanup")
    return session_manager


async def shutdown_session_manager() -> None:
    """Shutdown the global session manager and cleanup tasks.
    
    This should be called during application shutdown.
    """
    global _global_session_manager
    
    if _global_session_manager:
        await _global_session_manager.stop_cleanup_task()
        # Run final cleanup
        cleaned_count = await _global_session_manager.cleanup_expired_sessions()
        logger.info(f"Shutdown UserSessionManager - final cleanup removed {cleaned_count} sessions")
        _global_session_manager = None


# Convenience functions for common patterns
async def get_user_session(user_id: str, thread_id: str, 
                          run_id: Optional[str] = None,
                          websocket_connection_id: Optional[str] = None) -> UserExecutionContext:
    """Convenience function to get user session using global manager.
    
    Args:
        user_id: User identifier
        thread_id: Thread identifier
        run_id: Optional run identifier
        websocket_connection_id: Optional WebSocket connection ID
        
    Returns:
        UserExecutionContext: Session context
    """
    session_manager = get_session_manager()
    return await session_manager.get_or_create_user_session(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        websocket_connection_id=websocket_connection_id
    )


async def get_session_metrics() -> SystemSessionMetrics:
    """Convenience function to get session metrics.
    
    Returns:
        SystemSessionMetrics: Current session metrics
    """
    session_manager = get_session_manager()
    return session_manager.get_session_metrics()


# Export public interface
__all__ = [
    'UserSessionManager',
    'UserSession', 
    'SystemSessionMetrics',
    'SessionManagerError',
    'get_session_manager',
    'initialize_session_manager',
    'shutdown_session_manager',
    'get_user_session',
    'get_session_metrics'
]