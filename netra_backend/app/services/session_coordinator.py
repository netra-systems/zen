"""
Session Coordinator

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User experience & platform stability
- Value Impact: Ensures consistent session management across services
- Strategic Impact: Prevents session conflicts and improves user retention

Implements atomic session operations with session locking and coordination.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import json

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SessionState(Enum):
    """Session states."""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    EXPIRED = "expired"
    LOCKED = "locked"
    INVALIDATED = "invalidated"


@dataclass
class SessionLock:
    """Session lock for atomic operations."""
    session_id: str
    lock_id: str
    locked_by: str
    locked_at: datetime
    expires_at: datetime
    operation: str = "unknown"


@dataclass
class SessionData:
    """Session data with metadata."""
    session_id: str
    user_id: str
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    state: SessionState = SessionState.ACTIVE
    data: Dict[str, Any] = field(default_factory=dict)
    tokens: Dict[str, str] = field(default_factory=dict)  # access_token, refresh_token, etc.
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'state': self.state.value,
            'data': self.data,
            'tokens': self.tokens,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            state=SessionState(data['state']),
            data=data.get('data', {}),
            tokens=data.get('tokens', {}),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )


@dataclass
class CoordinatorConfig:
    """Configuration for session coordinator."""
    default_session_timeout_minutes: int = 60 * 24  # 24 hours
    cleanup_interval_seconds: int = 300  # 5 minutes
    lock_timeout_seconds: int = 30
    max_sessions_per_user: int = 10
    session_extension_minutes: int = 30


class SessionCoordinator:
    """Coordinates session management with atomic operations."""
    
    def __init__(self, config: Optional[CoordinatorConfig] = None):
        """Initialize session coordinator."""
        self.config = config or CoordinatorConfig()
        
        # Session storage (in-memory for now, could be backed by Redis)
        self.sessions: Dict[str, SessionData] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.session_locks: Dict[str, SessionLock] = {}
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self.stats = {
            'sessions_created': 0,
            'sessions_invalidated': 0,
            'sessions_expired': 0,
            'lock_acquisitions': 0,
            'lock_timeouts': 0,
            'race_conditions_prevented': 0
        }
    
    async def start(self) -> None:
        """Start session coordinator."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Session coordinator started")
    
    async def stop(self) -> None:
        """Stop session coordinator."""
        self._shutdown = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Session coordinator stopped")
    
    async def create_session(
        self,
        user_id: str,
        timeout_minutes: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """
        Create new session for user.
        
        Args:
            user_id: User ID
            timeout_minutes: Session timeout (uses default if not specified)
            ip_address: Client IP address
            user_agent: Client user agent
            initial_data: Initial session data
            
        Returns:
            Created session data
        """
        # Check session limits
        await self._enforce_session_limits(user_id)
        
        # Create session
        session_id = self._generate_session_id()
        now = datetime.now(timezone.utc)
        timeout = timeout_minutes or self.config.default_session_timeout_minutes
        
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_accessed=now,
            expires_at=now + timedelta(minutes=timeout),
            data=initial_data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store session
        self.sessions[session_id] = session
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        self.stats['sessions_created'] += 1
        logger.info(f"Created session {session_id} for user {user_id}")
        
        return session
    
    async def get_session(self, session_id: str, extend_session: bool = True) -> Optional[SessionData]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            extend_session: Whether to extend session expiration
            
        Returns:
            Session data if found and valid, None otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check if session is expired
        now = datetime.now(timezone.utc)
        if session.expires_at <= now:
            await self._expire_session(session_id)
            return None
        
        # Check if session is active
        if session.state != SessionState.ACTIVE:
            return None
        
        # Extend session if requested
        if extend_session:
            await self._extend_session(session_id)
        
        return session
    
    async def update_session(
        self,
        session_id: str,
        data_updates: Optional[Dict[str, Any]] = None,
        token_updates: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Update session data atomically.
        
        Args:
            session_id: Session ID
            data_updates: Data updates to apply
            token_updates: Token updates to apply
            
        Returns:
            True if update was successful
        """
        # Acquire lock
        lock_id = await self._acquire_session_lock(session_id, "update")
        if not lock_id:
            return False
        
        try:
            session = self.sessions.get(session_id)
            if not session or session.state != SessionState.ACTIVE:
                return False
            
            # Apply updates
            if data_updates:
                session.data.update(data_updates)
            
            if token_updates:
                session.tokens.update(token_updates)
            
            # Update last accessed time
            session.last_accessed = datetime.now(timezone.utc)
            
            logger.debug(f"Updated session {session_id}")
            return True
            
        finally:
            await self._release_session_lock(session_id, lock_id)
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate specific session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if session was invalidated
        """
        # Acquire lock
        lock_id = await self._acquire_session_lock(session_id, "invalidate")
        if not lock_id:
            return False
        
        try:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            # Mark as invalidated
            session.state = SessionState.INVALIDATED
            
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
            
            self.stats['sessions_invalidated'] += 1
            logger.info(f"Invalidated session {session_id}")
            return True
            
        finally:
            await self._release_session_lock(session_id, lock_id)
    
    async def invalidate_user_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            except_session_id: Session ID to exclude from invalidation
            
        Returns:
            Number of sessions invalidated
        """
        user_session_ids = self.user_sessions.get(user_id, set()).copy()
        if except_session_id:
            user_session_ids.discard(except_session_id)
        
        invalidated_count = 0
        
        for session_id in user_session_ids:
            if await self.invalidate_session(session_id):
                invalidated_count += 1
        
        logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
        return invalidated_count
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[SessionData]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active sessions
            
        Returns:
            List of user sessions
        """
        user_session_ids = self.user_sessions.get(user_id, set())
        sessions = []
        
        for session_id in user_session_ids:
            session = self.sessions.get(session_id)
            if session:
                if not active_only or session.state == SessionState.ACTIVE:
                    sessions.append(session)
        
        return sessions
    
    async def extend_session(self, session_id: str, additional_minutes: Optional[int] = None) -> bool:
        """
        Extend session expiration time.
        
        Args:
            session_id: Session ID
            additional_minutes: Minutes to add (uses default if not specified)
            
        Returns:
            True if session was extended
        """
        return await self._extend_session(session_id, additional_minutes)
    
    async def _acquire_session_lock(self, session_id: str, operation: str) -> Optional[str]:
        """Acquire atomic lock on session."""
        lock_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.config.lock_timeout_seconds)
        
        # Check if already locked
        existing_lock = self.session_locks.get(session_id)
        if existing_lock:
            if existing_lock.expires_at > now:
                # Lock still valid
                self.stats['lock_timeouts'] += 1
                return None
            else:
                # Lock expired, remove it
                del self.session_locks[session_id]
        
        # Acquire lock
        lock = SessionLock(
            session_id=session_id,
            lock_id=lock_id,
            locked_by=f"session_coordinator_{id(self)}",
            locked_at=now,
            expires_at=expires_at,
            operation=operation
        )
        
        self.session_locks[session_id] = lock
        self.stats['lock_acquisitions'] += 1
        
        return lock_id
    
    async def _release_session_lock(self, session_id: str, lock_id: str) -> bool:
        """Release session lock."""
        lock = self.session_locks.get(session_id)
        if lock and lock.lock_id == lock_id:
            del self.session_locks[session_id]
            return True
        return False
    
    async def _extend_session(self, session_id: str, additional_minutes: Optional[int] = None) -> bool:
        """Extend session expiration."""
        session = self.sessions.get(session_id)
        if not session or session.state != SessionState.ACTIVE:
            return False
        
        additional = additional_minutes or self.config.session_extension_minutes
        session.expires_at = max(
            session.expires_at,
            datetime.now(timezone.utc) + timedelta(minutes=additional)
        )
        session.last_accessed = datetime.now(timezone.utc)
        
        return True
    
    async def _enforce_session_limits(self, user_id: str) -> None:
        """Enforce session limits for user."""
        user_sessions = await self.get_user_sessions(user_id, active_only=True)
        
        if len(user_sessions) >= self.config.max_sessions_per_user:
            # Remove oldest sessions
            sessions_by_age = sorted(user_sessions, key=lambda s: s.last_accessed)
            sessions_to_remove = sessions_by_age[:len(user_sessions) - self.config.max_sessions_per_user + 1]
            
            for session in sessions_to_remove:
                await self.invalidate_session(session.session_id)
    
    async def _expire_session(self, session_id: str) -> None:
        """Mark session as expired."""
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.EXPIRED
            
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
            
            self.stats['sessions_expired'] += 1
    
    async def _cleanup_loop(self) -> None:
        """Cleanup expired sessions and locks."""
        while not self._shutdown:
            try:
                await self._cleanup_expired_data()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def _cleanup_expired_data(self) -> None:
        """Clean up expired sessions and locks."""
        now = datetime.now(timezone.utc)
        
        # Clean up expired sessions
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if session.expires_at <= now and session.state == SessionState.ACTIVE:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._expire_session(session_id)
        
        # Remove old expired/invalidated sessions
        old_sessions = []
        cutoff_time = now - timedelta(hours=24)  # Keep for 24 hours for audit
        
        for session_id, session in self.sessions.items():
            if (session.state in [SessionState.EXPIRED, SessionState.INVALIDATED] and
                session.last_accessed < cutoff_time):
                old_sessions.append(session_id)
        
        for session_id in old_sessions:
            session = self.sessions[session_id]
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
            del self.sessions[session_id]
        
        # Clean up expired locks
        expired_locks = []
        for session_id, lock in self.session_locks.items():
            if lock.expires_at <= now:
                expired_locks.append(session_id)
        
        for session_id in expired_locks:
            del self.session_locks[session_id]
        
        if expired_sessions or old_sessions or expired_locks:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions, "
                        f"{len(old_sessions)} old sessions, {len(expired_locks)} expired locks")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"sess_{int(time.time())}_{uuid.uuid4().hex[:16]}"
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        active_sessions = sum(1 for s in self.sessions.values() if s.state == SessionState.ACTIVE)
        
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': active_sessions,
            'users_with_sessions': len(self.user_sessions),
            'active_locks': len(self.session_locks),
            **self.stats
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session information."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        lock = self.session_locks.get(session_id)
        
        return {
            **session.to_dict(),
            'is_locked': lock is not None,
            'lock_info': {
                'locked_by': lock.locked_by,
                'locked_at': lock.locked_at.isoformat(),
                'expires_at': lock.expires_at.isoformat(),
                'operation': lock.operation
            } if lock else None
        }


# Global session coordinator instance
_session_coordinator: Optional[SessionCoordinator] = None


def get_session_coordinator(config: Optional[CoordinatorConfig] = None) -> SessionCoordinator:
    """Get global session coordinator instance."""
    global _session_coordinator
    if _session_coordinator is None:
        _session_coordinator = SessionCoordinator(config)
    return _session_coordinator


async def create_user_session(
    user_id: str,
    timeout_minutes: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> SessionData:
    """Convenience function to create user session."""
    coordinator = get_session_coordinator()
    return await coordinator.create_session(user_id, timeout_minutes, ip_address, user_agent)


async def get_user_session(session_id: str, extend_session: bool = True) -> Optional[SessionData]:
    """Convenience function to get user session."""
    coordinator = get_session_coordinator()
    return await coordinator.get_session(session_id, extend_session)