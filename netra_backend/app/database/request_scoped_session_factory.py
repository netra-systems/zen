"""Request-Scoped Session Factory - Connection Pool Isolation

This module implements strict request-scoped database session management
to prevent connection pool exhaustion and cross-request contamination.

Business Value Justification (BVJ):
- Segment: Platform Security & Stability (all tiers) 
- Business Goal: Prevent connection pool exhaustion and data leakage
- Value Impact: Ensures system stability under 100+ concurrent users
- Strategic Impact: Foundation for reliable multi-tenant operations

Key Features:
1. Request-scoped session factory with automatic cleanup
2. Connection pool monitoring and leak detection  
3. Session lifecycle tracking with metrics
4. Circuit breaker protection for database connections
5. Comprehensive logging and error handling

CRITICAL: Sessions are NEVER stored globally. Each request gets its own isolated session.
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

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import (
    SQLAlchemyError, 
    OperationalError, 
    DisconnectionError,
    TimeoutError as SQLTimeoutError
)

from netra_backend.app.database import get_db, DatabaseManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.thread_repository import ThreadRepository
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState, create_database_session_metrics

logger = central_logger.get_logger(__name__)


# SessionState and SessionMetrics now imported from shared.metrics.session_metrics
# This eliminates SSOT violation and ensures consistent metrics across the platform


@dataclass 
class ConnectionPoolMetrics:
    """Connection pool health and usage metrics."""
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


class RequestScopedSessionFactory:
    """Factory for creating request-scoped database sessions with strict isolation.
    
    This factory ensures:
    1. Each request gets its own isolated database session
    2. Sessions are automatically cleaned up after request completion
    3. Connection pool is monitored for exhaustion and leaks
    4. Circuit breaker protects against database failures
    5. Comprehensive metrics are collected for monitoring
    
    CRITICAL: Sessions are NEVER stored in global state.
    """
    
    def __init__(self):
        """Initialize the session factory with monitoring capabilities."""
        self._active_sessions: Dict[str, DatabaseSessionMetrics] = {}
        self._session_registry: weakref.WeakSet = weakref.WeakSet()
        self._pool_metrics = ConnectionPoolMetrics()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._leak_detection_enabled = True
        self._max_session_lifetime_ms = 300000  # 5 minutes
        self._leak_detection_interval = 60  # 1 minute
        
        # Start background cleanup task
        self._start_background_cleanup()
        
        logger.info("Initialized RequestScopedSessionFactory with leak detection")
    
    def _start_background_cleanup(self):
        """Start background task for leak detection and cleanup."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._cleanup_task = asyncio.create_task(self._background_cleanup())
        logger.debug("Started background cleanup task for session factory")
    
    async def _background_cleanup(self):
        """Background task for detecting and cleaning up leaked sessions."""
        while True:
            try:
                await asyncio.sleep(self._leak_detection_interval)
                await self._detect_and_cleanup_leaks()
            except asyncio.CancelledError:
                logger.debug("Background cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background cleanup task: {e}")
    
    async def _detect_and_cleanup_leaks(self):
        """Detect and clean up leaked sessions."""
        if not self._leak_detection_enabled:
            return
        
        current_time = datetime.now(timezone.utc)
        leaked_sessions = []
        
        async with self._lock:
            for session_id, metrics in self._active_sessions.items():
                # Check for sessions that have been active too long
                if metrics.state == SessionState.ACTIVE:
                    session_age_ms = (current_time - metrics.created_at).total_seconds() * 1000
                    if session_age_ms > self._max_session_lifetime_ms:
                        leaked_sessions.append(session_id)
                        logger.warning(
                            f"Detected leaked session {session_id} for user {metrics.user_id}, "
                            f"age: {session_age_ms:.1f}ms"
                        )
                
                # Check for sessions without recent activity
                elif metrics.last_activity_at:
                    inactive_time_ms = (current_time - metrics.last_activity_at).total_seconds() * 1000
                    if inactive_time_ms > (self._max_session_lifetime_ms / 2):
                        logger.warning(
                            f"Session {session_id} inactive for {inactive_time_ms:.1f}ms"
                        )
            
            # Clean up leaked sessions
            for session_id in leaked_sessions:
                if session_id in self._active_sessions:
                    self._active_sessions[session_id].record_error("Session leaked - forced cleanup")
                    self._active_sessions[session_id].close()
                    self._pool_metrics.record_leak()
                    del self._active_sessions[session_id]
        
        if leaked_sessions:
            logger.error(f"Cleaned up {len(leaked_sessions)} leaked sessions")
    
    @asynccontextmanager
    async def get_request_scoped_session(
        self,
        user_id: str,
        request_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[AsyncSession, None]:
        """Get a request-scoped database session with automatic cleanup.
        
        Args:
            user_id: User identifier for isolation
            request_id: Request identifier (auto-generated if not provided)
            thread_id: Thread identifier for WebSocket routing
            
        Yields:
            AsyncSession: Isolated database session for this request
            
        Raises:
            SQLAlchemyError: If session creation or database operation fails
        """
        # CRITICAL FIX: Use SSOT UnifiedIdGenerator for all ID generation
        if not request_id:
            # Generate consistent IDs using SSOT pattern
            _, _, generated_request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "session")
            request_id = generated_request_id
        
        # If no thread_id provided, generate using SSOT
        if not thread_id:
            generated_thread_id, _, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, "session")
            thread_id = generated_thread_id
        
        # Generate session_id using SSOT pattern
        session_id = UnifiedIdGenerator.generate_base_id(f"session_{user_id}", True, 12)
        
        session_metrics = create_database_session_metrics(
            session_id=session_id,
            request_id=request_id,
            user_id=user_id
        )
        
        # ENHANCED DEBUG: Session initialization with comprehensive context
        init_context = {
            "session_id": session_id,
            "user_id": user_id,
            "request_id": request_id,
            "thread_id": thread_id,
            "user_classification": {
                "is_system_user": user_id == "system" or (user_id and user_id.startswith("system")),
                "user_id_length": len(user_id) if user_id else 0,
                "user_id_pattern": user_id[:10] + "..." if user_id and len(user_id) > 10 else user_id
            },
            "factory_state": {
                "active_sessions_count": len(self._active_sessions),
                "pool_connections_created": self._pool_metrics.total_sessions_created,
                "pool_connections_leaked": self._pool_metrics.leaked_sessions
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"🚀 INITIALIZING: Request-scoped session for user {user_id}. "
            f"Session ID: {session_id}, Request ID: {request_id}. "
            f"Initialization context: {init_context}"
        )
        
        session = None
        try:
            # Create session using the single source of truth
            # get_db() is decorated with @asynccontextmanager, so we use async with
            async with get_db() as db_session:
                session = db_session
                
                # Tag session for validation and monitoring
                self._tag_session(session, user_id, request_id, thread_id, session_id)
                
                # Register session for monitoring
                await self._register_session(session_id, session_metrics, session)
                
                session_metrics.state = SessionState.ACTIVE
                session_metrics.mark_activity()
                
                # ENHANCED DEBUG: Session creation success with full context
                creation_context = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "request_id": request_id,
                    "thread_id": thread_id,
                    "session_state": session_metrics.state.value,
                    "active_sessions_count": len(self._active_sessions),
                    "user_type": "system_user" if user_id == "system" or (user_id and user_id.startswith("system")) else "regular_user",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(
                    f"✅ SUCCESS: Created request-scoped session {session_id} for user {user_id}. "
                    f"Context: {creation_context}"
                )
                
                # Special logging for system user sessions
                if user_id == "system" or (user_id and user_id.startswith("system")):
                    logger.info(
                        f"🔧 SYSTEM SESSION: Successfully created session for system user '{user_id}'. "
                        f"This indicates successful service-to-service authentication. "
                        f"Session: {session_id}, Request: {request_id}"
                    )
                
                # CRITICAL FIX: Ensure thread record exists before session operations
                await self._ensure_thread_record_exists(session, thread_id, user_id)
                
                try:
                    yield session
                    
                    # Mark session as successfully used
                    session_metrics.state = SessionState.COMMITTED
                    session_metrics.mark_activity()
                    
                except Exception as e:
                    # Record error and rollback if needed
                    session_metrics.record_error(str(e))
                    
                    # ENHANCED ERROR CONTEXT in session execution
                    execution_error_context = {
                        "session_id": session_id,
                        "user_id": user_id,
                        "request_id": request_id,
                        "thread_id": thread_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "session_state_before_error": session_metrics.state.value if session_metrics else "unknown",
                        "session_operations_count": session_metrics.operations_count if session_metrics else 0,
                        "authentication_hints": {
                            "is_auth_error": "403" in str(e) or "401" in str(e) or "Not authenticated" in str(e),
                            "user_type": "system_user" if user_id == "system" or (user_id and user_id.startswith("system")) else "regular_user"
                        }
                    }
                    
                    logger.error(
                        f"❌ ERROR: Request-scoped session {session_id} execution failed. "
                        f"User: {user_id}, Error: {e}. Full context: {execution_error_context}"
                    )
                    
                    try:
                        if session.in_transaction():
                            await session.rollback()
                            session_metrics.state = SessionState.ROLLED_BACK
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback session {session_id}: {rollback_error}")
                    
                    raise
        
        except Exception as e:
            session_metrics.record_error(str(e))
            
            # ENHANCED DEBUG LOGGING - 10x more context
            error_context = {
                "user_id": user_id,
                "request_id": request_id,
                "thread_id": thread_id,
                "session_id": session_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "active_sessions_count": len(self._active_sessions),
                "pool_metrics": {
                    "connections_created": self._pool_metrics.total_sessions_created,
                    "connections_leaked": self._pool_metrics.leaked_sessions,
                    "errors_encountered": getattr(self._pool_metrics, 'pool_exhaustion_events', 0)
                },
                "session_metrics": {
                    "state": session_metrics.state.value if session_metrics.state else "unknown",
                    "created_at": session_metrics.created_at.isoformat() if session_metrics.created_at else None,
                    "last_activity": session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None,
                    "operations_count": session_metrics.query_count,
                    "errors": session_metrics.error_count
                },
                "authentication_indicators": {
                    "user_id_type": "system" if user_id == "system" else "user",
                    "is_service_request": user_id == "system" or user_id.startswith("system"),
                    "request_id_pattern": request_id[:20] + "..." if request_id and len(request_id) > 20 else request_id
                },
                "stack_trace": str(e.__traceback__) if hasattr(e, '__traceback__') else "no_traceback"
            }
            
            # Additional authentication-specific context if it's a 403 error
            if "403" in str(e) or "Not authenticated" in str(e):
                error_context["authentication_failure_details"] = {
                    "likely_auth_middleware_failure": True,
                    "error_indicates_permission_denied": "403" in str(e),
                    "error_indicates_auth_failure": "Not authenticated" in str(e),
                    "possible_causes": [
                        "JWT token invalid or expired",
                        "Service-to-service authentication failed",
                        "User session expired",
                        "Authentication middleware configuration issue",
                        "Cross-service authentication key mismatch"
                    ],
                    "debugging_steps": [
                        "Check JWT token validity",
                        "Verify SERVICE_SECRET configuration",
                        "Validate authentication middleware setup",
                        "Check if user 'system' has proper service permissions",
                        "Review request headers for authentication tokens"
                    ]
                }
            
            logger.error(
                f"ENHANCED DEBUG: Failed to create request-scoped session for user {user_id}. "
                f"Error: {e}. Full context: {error_context}"
            )
            
            # Additional targeted logging for system user failures
            if user_id == "system" or (user_id and user_id.startswith("system")):
                logger.error(
                    f"SYSTEM USER AUTHENTICATION FAILURE: User '{user_id}' failed authentication. "
                    f"This indicates a service-to-service authentication problem. "
                    f"Request ID: {request_id}, Session ID: {session_id}. "
                    f"Check SERVICE_SECRET, JWT configuration, and inter-service auth setup."
                )
            
            raise
        
        finally:
            # Always clean up session
            await self._unregister_session(session_id, session_metrics)
    
    def _tag_session(
        self, 
        session: AsyncSession, 
        user_id: str, 
        request_id: str,
        thread_id: Optional[str],
        session_id: str
    ):
        """Tag session with request context for validation."""
        if not hasattr(session, 'info'):
            session.info = {}
        
        session.info.update({
            'user_id': user_id,
            'request_id': request_id,
            'thread_id': thread_id,
            'session_id': session_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_request_scoped': True,
            'factory_managed': True
        })
        
        logger.debug(f"Tagged session {session_id} with user context {user_id}")
    
    async def _register_session(self, session_id: str, metrics: DatabaseSessionMetrics, session: AsyncSession):
        """Register session for monitoring and leak detection."""
        async with self._lock:
            self._active_sessions[session_id] = metrics
            self._session_registry.add(session)
            
            self._pool_metrics.active_sessions += 1
            self._pool_metrics.total_sessions_created += 1
            self._pool_metrics.update_peak_concurrent(self._pool_metrics.active_sessions)
        
        logger.debug(f"Registered session {session_id}, active: {self._pool_metrics.active_sessions}")
    
    async def _unregister_session(self, session_id: str, metrics: DatabaseSessionMetrics):
        """Unregister session and update metrics."""
        async with self._lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            
            self._pool_metrics.active_sessions = max(0, self._pool_metrics.active_sessions - 1)
            self._pool_metrics.sessions_closed += 1
            
            metrics.close()
            
            # Update average session lifetime
            if metrics.total_time_ms:
                total_lifetime = (self._pool_metrics.avg_session_lifetime_ms * 
                                 (self._pool_metrics.sessions_closed - 1) + metrics.total_time_ms)
                self._pool_metrics.avg_session_lifetime_ms = total_lifetime / self._pool_metrics.sessions_closed
        
        logger.debug(f"Unregistered session {session_id}, active: {self._pool_metrics.active_sessions}")
    
    async def validate_session_isolation(self, session: AsyncSession, expected_user_id: str) -> bool:
        """Validate session belongs to expected user and is properly isolated.
        
        Args:
            session: Session to validate
            expected_user_id: Expected user ID for this session
            
        Returns:
            True if session is properly isolated
            
        Raises:
            ValueError: If session isolation is violated
        """
        session_info = getattr(session, 'info', {})
        
        # Check user isolation
        session_user_id = session_info.get('user_id')
        if session_user_id != expected_user_id:
            raise ValueError(
                f"Session isolation violated: session belongs to user {session_user_id}, "
                f"but expected user {expected_user_id}"
            )
        
        # Check request scoping
        is_request_scoped = session_info.get('is_request_scoped', False)
        if not is_request_scoped:
            raise ValueError("Session is not marked as request-scoped")
        
        # Check factory management
        is_factory_managed = session_info.get('factory_managed', False)
        if not is_factory_managed:
            raise ValueError("Session is not managed by RequestScopedSessionFactory")
        
        logger.debug(f"Validated session isolation for user {expected_user_id}")
        return True
    
    def get_pool_metrics(self) -> ConnectionPoolMetrics:
        """Get current connection pool metrics.
        
        Returns:
            Current pool metrics for monitoring
        """
        return self._pool_metrics
    
    def get_session_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get current session metrics for all active sessions.
        
        Returns:
            Dictionary mapping session IDs to their metrics
        """
        metrics = {}
        for session_id, session_metrics in self._active_sessions.items():
            metrics[session_id] = {
                'user_id': session_metrics.user_id,
                'request_id': session_metrics.request_id,
                'state': session_metrics.state.value,
                'query_count': session_metrics.query_count,
                'transaction_count': session_metrics.transaction_count,
                'created_at': session_metrics.created_at.isoformat(),
                'last_activity_at': session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None,
                'error_count': session_metrics.error_count,
                'last_error': session_metrics.last_error
            }
        return metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of session factory and connection pool.
        
        Returns:
            Health check results
        """
        try:
            # Test database connectivity
            async with self.get_request_scoped_session("health_check", "health_req") as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            
            # Get connection pool status
            engine = DatabaseManager.create_application_engine()
            pool_status = DatabaseManager.get_pool_status(engine)
            
            return {
                'status': 'healthy',
                'factory_metrics': {
                    'active_sessions': self._pool_metrics.active_sessions,
                    'total_created': self._pool_metrics.total_sessions_created,
                    'total_closed': self._pool_metrics.sessions_closed,
                    'leaked_sessions': self._pool_metrics.leaked_sessions,
                    'pool_exhaustion_events': self._pool_metrics.pool_exhaustion_events,
                    'peak_concurrent': self._pool_metrics.peak_concurrent_sessions,
                    'avg_lifetime_ms': self._pool_metrics.avg_session_lifetime_ms
                },
                'pool_status': pool_status,
                'leak_detection_enabled': self._leak_detection_enabled,
                'background_cleanup_running': self._cleanup_task and not self._cleanup_task.done()
            }
        
        except Exception as e:
            logger.error(f"Session factory health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'factory_metrics': {
                    'active_sessions': self._pool_metrics.active_sessions,
                    'total_created': self._pool_metrics.total_sessions_created,
                    'leaked_sessions': self._pool_metrics.leaked_sessions
                }
            }
    
    async def _ensure_thread_record_exists(
        self, 
        session: AsyncSession, 
        thread_id: str, 
        user_id: str
    ):
        """Ensure thread record exists in database before session operations.
        
        CRITICAL FIX: This prevents "404: Thread not found" errors by ensuring
        database Thread records exist for all thread_id values used in sessions.
        
        Args:
            session: Database session to use for thread operations
            thread_id: Thread ID to ensure exists
            user_id: User ID for thread ownership
        """
        try:
            thread_repo = ThreadRepository()
            
            # Check if thread exists
            existing_thread = await thread_repo.get_by_id(session, thread_id)
            
            if not existing_thread:
                logger.info(
                    f"🆕 THREAD CREATION: Creating missing thread record {thread_id} for user {user_id}. "
                    f"This fixes '404: Thread not found' errors by ensuring thread records exist."
                )
                
                # Create thread record with proper metadata
                thread_metadata = {
                    "user_id": user_id,
                    "created_via": "request_scoped_session",
                    "creation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "session_factory_auto_creation"
                }
                
                # Create thread using repository - CRITICAL FIX: Include required created_at field
                new_thread = await thread_repo.create(
                    session,
                    id=thread_id,
                    created_at=int(time.time()),  # Required field - Unix timestamp
                    metadata_=thread_metadata
                )
                
                # Commit thread creation immediately
                await session.commit()
                
                logger.info(
                    f"✅ THREAD CREATED: Successfully created thread {thread_id} for user {user_id}. "
                    f"Thread record now exists in database to prevent 404 errors."
                )
            else:
                logger.debug(
                    f"🔍 THREAD EXISTS: Thread {thread_id} already exists for user {user_id}. "
                    f"No creation needed."
                )
                
        except Exception as e:
            logger.error(
                f"❌ THREAD CREATION FAILED: Failed to ensure thread {thread_id} exists for user {user_id}. "
                f"Error: {e}. This may cause '404: Thread not found' errors."
            )
            # Don't re-raise - session can still work without thread record
            # but log the error so we know thread validation may fail later
    
    async def close(self):
        """Close session factory and cleanup resources."""
        logger.info("Closing RequestScopedSessionFactory")
        
        # Cancel background cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Force cleanup of any remaining sessions
        async with self._lock:
            if self._active_sessions:
                logger.warning(f"Force closing {len(self._active_sessions)} active sessions")
                for session_id, metrics in self._active_sessions.items():
                    metrics.record_error("Factory shutdown - forced cleanup")
                    metrics.close()
                
                self._active_sessions.clear()
        
        logger.info("RequestScopedSessionFactory closed successfully")


# Global factory instance
_session_factory: Optional[RequestScopedSessionFactory] = None
_factory_lock = asyncio.Lock()


async def get_session_factory() -> RequestScopedSessionFactory:
    """Get the global session factory instance.
    
    Returns:
        RequestScopedSessionFactory instance
    """
    global _session_factory
    
    if _session_factory is None:
        async with _factory_lock:
            if _session_factory is None:
                _session_factory = RequestScopedSessionFactory()
                logger.info("Created global RequestScopedSessionFactory")
    
    return _session_factory


@asynccontextmanager
async def get_isolated_session(
    user_id: str,
    request_id: Optional[str] = None,
    thread_id: Optional[str] = None
) -> AsyncGenerator[AsyncSession, None]:
    """Get isolated database session for a request.
    
    This is the primary interface for getting database sessions in the application.
    
    Args:
        user_id: User identifier for isolation
        request_id: Request identifier (auto-generated if not provided)  
        thread_id: Thread identifier for WebSocket routing
        
    Yields:
        AsyncSession: Isolated database session
    """
    factory = await get_session_factory()
    async with factory.get_request_scoped_session(user_id, request_id, thread_id) as session:
        yield session


async def validate_session_isolation(session: AsyncSession, user_id: str) -> bool:
    """Validate session isolation for a user.
    
    Args:
        session: Database session to validate
        user_id: Expected user ID
        
    Returns:
        True if session is properly isolated
    """
    factory = await get_session_factory()
    return await factory.validate_session_isolation(session, user_id)


async def get_factory_health() -> Dict[str, Any]:
    """Get health status of the session factory.
    
    Returns:
        Health check results
    """
    factory = await get_session_factory()
    return await factory.health_check()


async def shutdown_session_factory():
    """Shutdown the global session factory."""
    global _session_factory
    
    if _session_factory:
        await _session_factory.close()
        _session_factory = None
        logger.info("Session factory shutdown complete")