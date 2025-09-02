"""Session Memory Manager - WebSocket & Session Memory Cleanup

Business Value Justification:
- Segment: Platform/Core Infrastructure  
- Business Goal: Memory Leak Prevention & Resource Management
- Value Impact: Eliminates memory leaks from disconnected sessions, prevents OOM
- Strategic Impact: Critical for production stability and user experience

This service handles memory cleanup for disconnected WebSocket sessions and user sessions:
- Detects disconnected WebSocket connections
- Cleans up abandoned user session resources  
- Manages session-scoped resource pools
- Prevents memory leaks from orphaned sessions
- Provides session isolation and cleanup hooks
"""

import asyncio
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.memory_optimization_service import get_memory_service

logger = central_logger.get_logger(__name__)


class SessionState(Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    CLEANING_UP = "cleaning_up"
    DISPOSED = "disposed"


@dataclass
class SessionResource:
    """Resource tracked within a session."""
    resource_id: str
    resource_type: str
    instance: Any
    created_at: datetime
    cleanup_callback: Optional[Callable] = None
    memory_estimate_mb: float = 0.0
    last_accessed: Optional[datetime] = None


@dataclass  
class UserSession:
    """User session with resource tracking and cleanup."""
    session_id: str
    user_id: str
    thread_id: Optional[str]
    websocket_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    state: SessionState = SessionState.ACTIVE
    resources: Dict[str, SessionResource] = field(default_factory=dict)
    cleanup_callbacks: List[Callable] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    _disposed: bool = field(default=False, init=False)


class SessionMemoryManager:
    """Manages memory cleanup for user sessions and WebSocket connections.
    
    This service provides:
    - Automatic cleanup of disconnected WebSocket sessions
    - User session resource tracking and disposal
    - Memory leak prevention for orphaned sessions
    - Session-scoped resource pools with automatic cleanup
    - Integration with WebSocket connection lifecycle
    """
    
    def __init__(self):
        """Initialize session memory manager."""
        self.memory_service = get_memory_service()
        
        # Session tracking
        self._user_sessions: Dict[str, UserSession] = {}
        self._websocket_sessions: Dict[str, str] = {}  # websocket_id -> session_id
        self._session_lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Configuration
        self.session_timeout_seconds = 3600  # 1 hour
        self.idle_timeout_seconds = 1800     # 30 minutes
        self.cleanup_interval_seconds = 300  # 5 minutes
        
        # Weak references for tracking
        self._tracked_objects: weakref.WeakSet = weakref.WeakSet()
        
        logger.info("SessionMemoryManager initialized")
    
    async def start(self) -> None:
        """Start session memory management."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start background cleanup
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("✅ SessionMemoryManager started")
    
    async def stop(self) -> None:
        """Stop session memory management."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        # Clean up all sessions
        async with self._session_lock:
            sessions_to_cleanup = list(self._user_sessions.values())
        
        for session in sessions_to_cleanup:
            await self._dispose_session(session)
        
        logger.info("✅ SessionMemoryManager stopped")
    
    async def create_user_session(
        self,
        session_id: str,
        user_id: str,
        thread_id: Optional[str] = None,
        websocket_id: Optional[str] = None
    ) -> UserSession:
        """Create new user session with resource tracking.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            thread_id: Optional chat thread ID
            websocket_id: Optional WebSocket connection ID
            
        Returns:
            Created user session
        """
        now = datetime.now(timezone.utc)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            thread_id=thread_id,
            websocket_id=websocket_id,
            created_at=now,
            last_activity=now
        )
        
        async with self._session_lock:
            # Clean up any existing session with same ID
            if session_id in self._user_sessions:
                old_session = self._user_sessions[session_id]
                await self._dispose_session(old_session)
            
            # Register new session
            self._user_sessions[session_id] = session
            
            # Track WebSocket association
            if websocket_id:
                self._websocket_sessions[websocket_id] = session_id
        
        logger.info(f"📱 Created user session {session_id} for user {user_id}")
        return session
    
    async def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """Get user session by ID."""
        async with self._session_lock:
            return self._user_sessions.get(session_id)
    
    async def register_session_resource(
        self,
        session_id: str,
        resource_id: str,
        resource_type: str,
        instance: Any,
        cleanup_callback: Optional[Callable] = None,
        memory_estimate_mb: float = 0.0
    ) -> bool:
        """Register resource within user session for automatic cleanup.
        
        Args:
            session_id: Session to register resource in
            resource_id: Unique resource identifier within session
            resource_type: Type of resource (e.g., 'db_session', 'tool_dispatcher')
            instance: Resource instance
            cleanup_callback: Optional cleanup function
            memory_estimate_mb: Estimated memory usage in MB
            
        Returns:
            True if registered successfully, False if session not found
        """
        session = await self.get_user_session(session_id)
        if not session or session._disposed:
            logger.warning(f"Cannot register resource {resource_id} - session {session_id} not found")
            return False
        
        resource = SessionResource(
            resource_id=resource_id,
            resource_type=resource_type,
            instance=instance,
            created_at=datetime.now(timezone.utc),
            cleanup_callback=cleanup_callback,
            memory_estimate_mb=memory_estimate_mb,
            last_accessed=datetime.now(timezone.utc)
        )
        
        session.resources[resource_id] = resource
        session.memory_usage_mb += memory_estimate_mb
        session.last_activity = datetime.now(timezone.utc)
        
        # Track with weak reference
        self._tracked_objects.add(instance)
        
        logger.debug(f"📦 Registered {resource_type} resource {resource_id} in session {session_id} "
                    f"(+{memory_estimate_mb}MB)")
        
        return True
    
    async def update_session_activity(self, session_id: str) -> None:
        """Update session last activity timestamp."""
        session = await self.get_user_session(session_id)
        if session and not session._disposed:
            session.last_activity = datetime.now(timezone.utc)
            if session.state == SessionState.IDLE:
                session.state = SessionState.ACTIVE
                logger.debug(f"📱 Session {session_id} reactivated")
    
    async def websocket_connected(self, websocket_id: str, session_id: str) -> None:
        """Handle WebSocket connection for session."""
        async with self._session_lock:
            self._websocket_sessions[websocket_id] = session_id
        
        session = await self.get_user_session(session_id)
        if session:
            session.websocket_id = websocket_id
            session.last_activity = datetime.now(timezone.utc)
            session.state = SessionState.ACTIVE
            
        logger.debug(f"🔌 WebSocket {websocket_id} connected to session {session_id}")
    
    async def websocket_disconnected(self, websocket_id: str) -> None:
        """Handle WebSocket disconnection and cleanup session resources."""
        async with self._session_lock:
            session_id = self._websocket_sessions.pop(websocket_id, None)
        
        if not session_id:
            logger.debug(f"🔌 WebSocket {websocket_id} disconnected (no session)")
            return
        
        session = await self.get_user_session(session_id)
        if session:
            session.websocket_id = None
            session.state = SessionState.DISCONNECTED
            session.last_activity = datetime.now(timezone.utc)
            
            logger.info(f"🔌 WebSocket {websocket_id} disconnected from session {session_id} - "
                       f"marking for cleanup")
            
            # Schedule immediate cleanup for disconnected session
            asyncio.create_task(self._delayed_session_cleanup(session, delay_seconds=30))
    
    async def _delayed_session_cleanup(self, session: UserSession, delay_seconds: int = 30) -> None:
        """Cleanup session after delay to handle reconnections."""
        await asyncio.sleep(delay_seconds)
        
        # Check if session was reconnected
        current_session = await self.get_user_session(session.session_id)
        if (current_session and 
            current_session.state == SessionState.DISCONNECTED and
            not current_session.websocket_id):
            
            logger.info(f"🧹 Auto-cleaning disconnected session {session.session_id}")
            await self._dispose_session(current_session)
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Manually cleanup specific session.
        
        Args:
            session_id: Session to cleanup
            
        Returns:
            True if session was cleaned up, False if not found
        """
        session = await self.get_user_session(session_id)
        if not session:
            return False
        
        await self._dispose_session(session)
        return True
    
    async def _dispose_session(self, session: UserSession) -> None:
        """Dispose session and all its resources."""
        if session._disposed:
            return
        
        logger.info(f"🗑️ Disposing session {session.session_id} "
                   f"({len(session.resources)} resources, {session.memory_usage_mb:.1f}MB)")
        
        session.state = SessionState.CLEANING_UP
        
        try:
            # Clean up all session resources
            for resource_id, resource in session.resources.items():
                try:
                    logger.debug(f"  🗑️ Cleaning up {resource.resource_type}: {resource_id}")
                    
                    # Call cleanup callback if available
                    if resource.cleanup_callback:
                        if asyncio.iscoroutinefunction(resource.cleanup_callback):
                            await resource.cleanup_callback()
                        else:
                            resource.cleanup_callback()
                    
                    # Try standard cleanup methods
                    instance = resource.instance
                    if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                        if asyncio.iscoroutinefunction(instance.cleanup):
                            await instance.cleanup()
                        else:
                            instance.cleanup()
                    elif hasattr(instance, 'dispose') and callable(instance.dispose):
                        if asyncio.iscoroutinefunction(instance.dispose):
                            await instance.dispose()
                        else:
                            instance.dispose()
                    elif hasattr(instance, 'close') and callable(instance.close):
                        if asyncio.iscoroutinefunction(instance.close):
                            await instance.close()
                        else:
                            instance.close()
                    
                except Exception as e:
                    logger.error(f"Error cleaning up resource {resource_id}: {e}")
            
            # Run session-level cleanup callbacks
            for callback in session.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in session cleanup callback: {e}")
            
            # Clear all references
            session.resources.clear()
            session.cleanup_callbacks.clear()
            session._disposed = True
            session.state = SessionState.DISPOSED
            
            # Remove from tracking
            async with self._session_lock:
                self._user_sessions.pop(session.session_id, None)
                
                # Remove WebSocket association if exists
                if session.websocket_id:
                    self._websocket_sessions.pop(session.websocket_id, None)
            
            logger.info(f"✅ Disposed session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Error disposing session {session.session_id}: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        logger.info("🧹 Started session cleanup loop")
        
        while self._is_running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval_seconds)
        
        logger.info("🧹 Session cleanup loop stopped")
    
    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired and idle sessions."""
        now = datetime.now(timezone.utc)
        sessions_to_cleanup = []
        sessions_to_idle = []
        
        async with self._session_lock:
            for session in self._user_sessions.values():
                if session._disposed:
                    continue
                
                time_since_activity = (now - session.last_activity).total_seconds()
                
                # Mark for cleanup if expired or disconnected too long
                if (time_since_activity > self.session_timeout_seconds or
                    (session.state == SessionState.DISCONNECTED and time_since_activity > 300)):
                    sessions_to_cleanup.append(session)
                
                # Mark as idle if inactive
                elif (session.state == SessionState.ACTIVE and 
                      time_since_activity > self.idle_timeout_seconds):
                    sessions_to_idle.append(session)
        
        # Clean up expired sessions
        for session in sessions_to_cleanup:
            logger.info(f"🕰️ Cleaning up expired session {session.session_id} "
                       f"(inactive for {(now - session.last_activity).total_seconds():.0f}s)")
            await self._dispose_session(session)
        
        # Mark sessions as idle
        for session in sessions_to_idle:
            session.state = SessionState.IDLE
            logger.debug(f"😴 Session {session.session_id} marked as idle")
        
        if sessions_to_cleanup or sessions_to_idle:
            logger.info(f"🧹 Cleanup complete: {len(sessions_to_cleanup)} expired, "
                       f"{len(sessions_to_idle)} idle")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("🔍 Started session monitoring loop")
        
        while self._is_running:
            try:
                await self._log_session_stats()
                await asyncio.sleep(600)  # Every 10 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session monitoring: {e}")
                await asyncio.sleep(600)
        
        logger.info("🔍 Session monitoring loop stopped")
    
    async def _log_session_stats(self) -> None:
        """Log session statistics."""
        async with self._session_lock:
            total_sessions = len(self._user_sessions)
            active_sessions = sum(1 for s in self._user_sessions.values() 
                                if s.state == SessionState.ACTIVE)
            idle_sessions = sum(1 for s in self._user_sessions.values() 
                              if s.state == SessionState.IDLE)
            disconnected_sessions = sum(1 for s in self._user_sessions.values() 
                                      if s.state == SessionState.DISCONNECTED)
            
            total_memory_mb = sum(s.memory_usage_mb for s in self._user_sessions.values())
            total_resources = sum(len(s.resources) for s in self._user_sessions.values())
        
        if total_sessions > 0:
            logger.info(f"📊 Sessions: {total_sessions} total ({active_sessions} active, "
                       f"{idle_sessions} idle, {disconnected_sessions} disconnected), "
                       f"{total_resources} resources, {total_memory_mb:.1f}MB")
    
    @asynccontextmanager
    async def session_scope(
        self,
        session_id: str,
        user_id: str,
        thread_id: Optional[str] = None,
        websocket_id: Optional[str] = None
    ):
        """Create scoped session with automatic cleanup.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            thread_id: Optional chat thread ID
            websocket_id: Optional WebSocket connection ID
            
        Yields:
            UserSession: Session with automatic cleanup
            
        Example:
            async with session_manager.session_scope(session_id, user_id) as session:
                await session_manager.register_session_resource(
                    session_id, 'db_session', 'database', db_session
                )
                # Automatic cleanup on exit
        """
        session = await self.create_user_session(session_id, user_id, thread_id, websocket_id)
        try:
            yield session
        finally:
            if not session._disposed:
                await self._dispose_session(session)
    
    def get_status(self) -> Dict[str, Any]:
        """Get session manager status."""
        active_sessions = sum(1 for s in self._user_sessions.values() 
                            if s.state == SessionState.ACTIVE)
        idle_sessions = sum(1 for s in self._user_sessions.values() 
                          if s.state == SessionState.IDLE)
        disconnected_sessions = sum(1 for s in self._user_sessions.values() 
                                  if s.state == SessionState.DISCONNECTED)
        
        total_memory_mb = sum(s.memory_usage_mb for s in self._user_sessions.values())
        total_resources = sum(len(s.resources) for s in self._user_sessions.values())
        
        return {
            'is_running': self._is_running,
            'sessions': {
                'total': len(self._user_sessions),
                'active': active_sessions,
                'idle': idle_sessions,
                'disconnected': disconnected_sessions
            },
            'resources': {
                'total': total_resources,
                'memory_usage_mb': total_memory_mb
            },
            'websockets': {
                'connected': len(self._websocket_sessions)
            },
            'config': {
                'session_timeout_seconds': self.session_timeout_seconds,
                'idle_timeout_seconds': self.idle_timeout_seconds,
                'cleanup_interval_seconds': self.cleanup_interval_seconds
            }
        }


# Global service instance
_session_manager: Optional[SessionMemoryManager] = None


def get_session_manager() -> SessionMemoryManager:
    """Get global session memory manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionMemoryManager()
    return _session_manager


async def initialize_session_manager() -> SessionMemoryManager:
    """Initialize and start session memory manager."""
    manager = get_session_manager()
    if not manager._is_running:
        await manager.start()
    return manager


async def shutdown_session_manager() -> None:
    """Shutdown session memory manager."""
    global _session_manager
    if _session_manager and _session_manager._is_running:
        await _session_manager.stop()
        _session_manager = None