"""
Session Isolation Manager - SSOT for User Session Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Ensure complete isolation between user sessions
- Value Impact: Prevents data leakage and ensures user privacy
- Strategic Impact: Critical for multi-tenant system security and compliance
"""

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import asyncio
import threading

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class IsolationLevel(Enum):
    """Levels of session isolation."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    ENTERPRISE = "enterprise"


class SessionStatus(Enum):
    """Status of user session."""
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclass
class SessionContext:
    """Isolated context for a user session."""
    session_id: str
    user_id: str
    thread_id: str
    run_id: str
    created_at: datetime
    last_activity: datetime
    isolation_level: IsolationLevel
    status: SessionStatus
    metadata: Dict[str, Any]
    resources: Dict[str, Any]
    permissions: Set[str]


@dataclass
class IsolationPolicy:
    """Policy for session isolation."""
    isolation_level: IsolationLevel
    session_timeout_minutes: int
    max_concurrent_sessions: int
    resource_cleanup_interval: int
    cross_session_access_allowed: bool
    audit_all_operations: bool
    encrypted_storage: bool


class SessionIsolationManager:
    """SSOT Session Isolation Manager for complete user session separation.
    
    This class manages user session isolation, ensuring that user data,
    resources, and operations are completely separated between sessions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize session isolation manager.
        
        Args:
            config: Optional configuration for isolation policies
        """
        self.config = config or self._get_default_config()
        self._sessions: Dict[str, SessionContext] = {}
        self._user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self._isolation_policies: Dict[str, IsolationPolicy] = {}
        self._lock = threading.RLock()
        
        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())
        
        logger.info("SessionIsolationManager initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default isolation configuration."""
        return {
            "default_isolation_level": IsolationLevel.STANDARD,
            "session_timeout_minutes": 60,
            "max_sessions_per_user": 5,
            "cleanup_interval_minutes": 10,
            "audit_enabled": True,
            "encryption_enabled": True,
            "cross_session_prevention": True
        }
    
    def create_isolated_session(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        isolation_level: Optional[IsolationLevel] = None,
        permissions: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """Create a new isolated session for a user.
        
        Args:
            user_id: User identifier
            thread_id: Optional thread identifier
            run_id: Optional run identifier  
            isolation_level: Level of isolation required
            permissions: Set of permissions for the session
            metadata: Additional session metadata
            
        Returns:
            New SessionContext for the user
            
        Raises:
            RuntimeError: If maximum sessions exceeded or isolation fails
        """
        with self._lock:
            # Check session limits
            user_session_count = len(self._user_sessions.get(user_id, set()))
            max_sessions = self.config["max_sessions_per_user"]
            
            if user_session_count >= max_sessions:
                # Cleanup expired sessions first
                self._cleanup_expired_sessions(user_id)
                user_session_count = len(self._user_sessions.get(user_id, set()))
                
                if user_session_count >= max_sessions:
                    raise RuntimeError(f"Maximum sessions ({max_sessions}) exceeded for user {user_id}")
            
            # Generate IDs
            session_id = str(uuid.uuid4())
            thread_id = thread_id or f"thread_{user_id}_{session_id[:8]}"
            run_id = run_id or f"run_{session_id[:8]}"
            
            # Set isolation level
            isolation_level = isolation_level or self.config["default_isolation_level"]
            
            # Create session context
            now = datetime.now(timezone.utc)
            session_context = SessionContext(
                session_id=session_id,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                created_at=now,
                last_activity=now,
                isolation_level=isolation_level,
                status=SessionStatus.ACTIVE,
                metadata=metadata or {},
                resources={},
                permissions=permissions or set()
            )
            
            # Store session
            self._sessions[session_id] = session_context
            
            # Track user sessions
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
            
            # Set up isolation policy
            self._setup_isolation_policy(session_id, isolation_level)
            
            logger.info(
                f"Created isolated session {session_id[:8]} for user {user_id} "
                f"with {isolation_level.value} isolation"
            )
            
            return session_context
    
    def _setup_isolation_policy(self, session_id: str, isolation_level: IsolationLevel) -> None:
        """Set up isolation policy for a session."""
        timeout_minutes = self.config["session_timeout_minutes"]
        
        # Adjust timeout based on isolation level
        if isolation_level == IsolationLevel.ENTERPRISE:
            timeout_minutes = 120  # 2 hours
        elif isolation_level == IsolationLevel.STRICT:
            timeout_minutes = 90   # 1.5 hours
        elif isolation_level == IsolationLevel.BASIC:
            timeout_minutes = 30   # 30 minutes
        
        policy = IsolationPolicy(
            isolation_level=isolation_level,
            session_timeout_minutes=timeout_minutes,
            max_concurrent_sessions=self.config["max_sessions_per_user"],
            resource_cleanup_interval=self.config["cleanup_interval_minutes"],
            cross_session_access_allowed=isolation_level == IsolationLevel.BASIC,
            audit_all_operations=self.config["audit_enabled"],
            encrypted_storage=self.config["encryption_enabled"]
        )
        
        self._isolation_policies[session_id] = policy
    
    def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """Get session context by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionContext or None if not found or expired
        """
        with self._lock:
            if session_id not in self._sessions:
                return None
            
            session = self._sessions[session_id]
            
            # Check if session is expired
            if self._is_session_expired(session):
                self._terminate_session(session_id)
                return None
            
            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            
            return session
    
    def validate_session_isolation(self, session_id: str, target_resource: str) -> bool:
        """Validate that a session can access a resource without breaking isolation.
        
        Args:
            session_id: Session identifier
            target_resource: Resource being accessed
            
        Returns:
            True if access is allowed under isolation policy
        """
        with self._lock:
            session = self.get_session_context(session_id)
            if not session:
                return False
            
            policy = self._isolation_policies.get(session_id)
            if not policy:
                return False
            
            # Check cross-session access
            if not policy.cross_session_access_allowed:
                # Ensure resource belongs to this session
                if not self._resource_belongs_to_session(target_resource, session_id):
                    logger.warning(f"Cross-session access denied: {session_id} -> {target_resource}")
                    return False
            
            # Check permissions
            required_permission = self._get_required_permission(target_resource)
            if required_permission and required_permission not in session.permissions:
                logger.warning(f"Permission denied: {session_id} -> {target_resource}")
                return False
            
            return True
    
    def _resource_belongs_to_session(self, resource: str, session_id: str) -> bool:
        """Check if a resource belongs to a specific session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        # Check if resource is in session resources
        if resource in session.resources:
            return True
        
        # Check if resource contains session identifiers
        if any(identifier in resource for identifier in [
            session.session_id, session.thread_id, session.run_id, session.user_id
        ]):
            return True
        
        return False
    
    def _get_required_permission(self, resource: str) -> Optional[str]:
        """Get required permission for accessing a resource."""
        # Simple permission mapping
        if "admin" in resource.lower():
            return "admin"
        elif "write" in resource.lower():
            return "write"
        elif "read" in resource.lower():
            return "read"
        else:
            return None
    
    def register_session_resource(
        self,
        session_id: str,
        resource_name: str,
        resource_data: Any
    ) -> bool:
        """Register a resource with a session for isolation tracking.
        
        Args:
            session_id: Session identifier
            resource_name: Name of the resource
            resource_data: Resource data to store
            
        Returns:
            True if resource was registered successfully
        """
        with self._lock:
            session = self.get_session_context(session_id)
            if not session:
                return False
            
            # Store resource in session context
            session.resources[resource_name] = resource_data
            
            logger.debug(f"Registered resource {resource_name} with session {session_id[:8]}")
            return True
    
    def terminate_session(self, session_id: str) -> bool:
        """Manually terminate a session and clean up resources.
        
        Args:
            session_id: Session identifier to terminate
            
        Returns:
            True if session was terminated successfully
        """
        return self._terminate_session(session_id)
    
    def _terminate_session(self, session_id: str) -> bool:
        """Internal method to terminate a session."""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            session.status = SessionStatus.TERMINATED
            
            # Clean up resources
            self._cleanup_session_resources(session_id)
            
            # Remove from user sessions tracking
            user_id = session.user_id
            if user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]
            
            # Remove session and policy
            del self._sessions[session_id]
            if session_id in self._isolation_policies:
                del self._isolation_policies[session_id]
            
            logger.info(f"Terminated session {session_id[:8]} for user {user_id}")
            return True
    
    def _cleanup_session_resources(self, session_id: str) -> None:
        """Clean up all resources associated with a session."""
        if session_id not in self._sessions:
            return
        
        session = self._sessions[session_id]
        resource_count = len(session.resources)
        
        # Clear all session resources
        session.resources.clear()
        
        logger.debug(f"Cleaned up {resource_count} resources for session {session_id[:8]}")
    
    def _is_session_expired(self, session: SessionContext) -> bool:
        """Check if a session has expired."""
        if session.status != SessionStatus.ACTIVE:
            return True
        
        policy = self._isolation_policies.get(session.session_id)
        if not policy:
            return True
        
        timeout = timedelta(minutes=policy.session_timeout_minutes)
        return (datetime.now(timezone.utc) - session.last_activity) > timeout
    
    def _cleanup_expired_sessions(self, user_id: Optional[str] = None) -> None:
        """Clean up expired sessions for a user or all users."""
        with self._lock:
            sessions_to_cleanup = []
            
            if user_id:
                # Clean up sessions for specific user
                session_ids = self._user_sessions.get(user_id, set()).copy()
                for session_id in session_ids:
                    if session_id in self._sessions:
                        session = self._sessions[session_id]
                        if self._is_session_expired(session):
                            sessions_to_cleanup.append(session_id)
            else:
                # Clean up all expired sessions
                for session_id, session in self._sessions.items():
                    if self._is_session_expired(session):
                        sessions_to_cleanup.append(session_id)
            
            # Terminate expired sessions
            for session_id in sessions_to_cleanup:
                self._terminate_session(session_id)
            
            if sessions_to_cleanup:
                logger.info(f"Cleaned up {len(sessions_to_cleanup)} expired sessions")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task for expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.config["cleanup_interval_minutes"] * 60)
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    def get_user_sessions(self, user_id: str) -> List[SessionContext]:
        """Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active SessionContext objects
        """
        with self._lock:
            if user_id not in self._user_sessions:
                return []
            
            sessions = []
            for session_id in self._user_sessions[user_id].copy():
                session = self.get_session_context(session_id)
                if session:
                    sessions.append(session)
            
            return sessions
    
    def get_isolation_metrics(self) -> Dict[str, Any]:
        """Get metrics about session isolation.
        
        Returns:
            Dictionary with isolation metrics
        """
        with self._lock:
            total_sessions = len(self._sessions)
            active_sessions = sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)
            total_users = len(self._user_sessions)
            
            isolation_levels = {}
            for session in self._sessions.values():
                level = session.isolation_level.value
                isolation_levels[level] = isolation_levels.get(level, 0) + 1
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_users": total_users,
                "sessions_per_user": total_sessions / max(1, total_users),
                "isolation_levels": isolation_levels,
                "average_session_resources": sum(
                    len(s.resources) for s in self._sessions.values()
                ) / max(1, total_sessions)
            }


# Export for test compatibility
__all__ = [
    'SessionIsolationManager',
    'SessionContext',
    'IsolationPolicy',
    'IsolationLevel',
    'SessionStatus'
]