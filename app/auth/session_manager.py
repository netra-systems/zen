"""Core session lifecycle management - MODULAR ARCHITECTURE.

Handles session creation, basic operations, and user session management.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import secrets

from app.logging_config import central_logger
from .enhanced_auth_core import SecuritySession, SessionStatus, SecurityConfiguration

logger = central_logger.get_logger(__name__)


class SessionLifecycleManager:
    """Manages core session lifecycle operations."""
    
    def __init__(self, config: SecurityConfiguration):
        """Initialize session lifecycle manager."""
        self.config = config
        self.active_sessions: Dict[str, SecuritySession] = {}
    
    def create_secure_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a secure session with comprehensive tracking."""
        session_id = self._generate_session_id()
        csrf_token = self._generate_csrf_token()
        self._enforce_concurrent_session_limit(user_id)
        session = self._build_security_session(session_id, user_id, ip_address, user_agent, csrf_token)
        self._store_and_log_session(session_id, session, user_id)
        return session_id
    
    def _store_and_log_session(self, session_id: str, session: SecuritySession, user_id: str) -> None:
        """Store session and log creation."""
        self.active_sessions[session_id] = session
        self._log_session_creation(session_id, user_id)
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(24)
    
    def _enforce_concurrent_session_limit(self, user_id: str) -> None:
        """Enforce maximum concurrent sessions per user."""
        user_sessions = self._get_user_sessions(user_id)
        if len(user_sessions) >= self.config.max_concurrent_sessions:
            oldest_session = self._find_oldest_session(user_sessions)
            self._revoke_session(oldest_session.session_id, "concurrent_limit")
    
    def _get_user_sessions(self, user_id: str) -> List[SecuritySession]:
        """Get all active sessions for a user."""
        return [s for s in self.active_sessions.values() if s.user_id == user_id]
    
    def _find_oldest_session(self, sessions: List[SecuritySession]) -> SecuritySession:
        """Find the oldest session by last activity."""
        return min(sessions, key=lambda s: s.last_activity)
    
    def _build_security_session(self, session_id: str, user_id: str, ip_address: str, 
                               user_agent: str, csrf_token: str) -> SecuritySession:
        """Build a complete security session object."""
        now = datetime.now(timezone.utc)
        security_flags = self._build_security_flags(user_id, ip_address, user_agent)
        return self._create_session_object(session_id, user_id, ip_address, user_agent, 
                                         csrf_token, now, security_flags)
    
    def _create_session_object(self, session_id: str, user_id: str, ip_address: str,
                              user_agent: str, csrf_token: str, now: datetime, 
                              security_flags: Dict[str, Any]) -> SecuritySession:
        """Create the SecuritySession object."""
        return SecuritySession(
            session_id=session_id, user_id=user_id, ip_address=ip_address,
            user_agent=user_agent, created_at=now, last_activity=now,
            expires_at=now + self.config.session_timeout, status=SessionStatus.ACTIVE,
            security_flags=security_flags, csrf_token=csrf_token
        )
    
    def _build_security_flags(self, user_id: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Build security flags for session."""
        return {
            "is_trusted_ip": self._is_trusted_ip(ip_address),
            "requires_mfa": self._requires_mfa(user_id, ip_address),
            "created_from_new_device": self._is_new_device(user_id, user_agent)
        }
    
    def _is_trusted_ip(self, ip_address: str) -> bool:
        """Check if IP address is trusted."""
        return ip_address in self.config.ip_whitelist
    
    def _requires_mfa(self, user_id: str, ip_address: str) -> bool:
        """Check if MFA is required."""
        return not self._is_trusted_ip(ip_address)
    
    def _is_new_device(self, user_id: str, user_agent: str) -> bool:
        """Check if this is a new device for the user."""
        recent_sessions = self._get_matching_user_agent_sessions(user_id, user_agent)
        return len(recent_sessions) == 0
    
    def _get_matching_user_agent_sessions(self, user_id: str, user_agent: str) -> List[SecuritySession]:
        """Get sessions for user with matching user agent."""
        return [
            s for s in self.active_sessions.values()
            if s.user_id == user_id and s.user_agent == user_agent
        ]
    
    def _revoke_session(self, session_id: str, reason: str) -> None:
        """Revoke a session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = SessionStatus.REVOKED
            self._log_session_revocation(session_id, session.user_id, reason)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for monitoring."""
        if session_id not in self.active_sessions:
            return None
        session = self.active_sessions[session_id]
        return self._build_session_info_dict(session)
    
    def _build_session_info_dict(self, session: SecuritySession) -> Dict[str, Any]:
        """Build session information dictionary."""
        return {
            "session_id": session.session_id, "user_id": session.user_id,
            "created_at": session.created_at, "last_activity": session.last_activity,
            "status": session.status.value, "security_flags": session.security_flags
        }
    
    def get_user_session_count(self, user_id: str) -> int:
        """Get count of active sessions for a user."""
        return len(self._get_user_sessions(user_id))
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user and return count."""
        user_sessions = self._get_user_sessions(user_id)
        for session in user_sessions:
            self._revoke_session(session.session_id, "admin_revoked")
        return len(user_sessions)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status for all sessions."""
        return {
            "total_active_sessions": len(self.active_sessions),
            "suspicious_sessions": self._count_suspicious_sessions()
        }
    
    def _count_suspicious_sessions(self) -> int:
        """Count sessions marked as suspicious."""
        return len([
            s for s in self.active_sessions.values() 
            if s.status == SessionStatus.SUSPICIOUS
        ])
    
    # Logging helper methods
    def _log_session_creation(self, session_id: str, user_id: str) -> None:
        """Log session creation."""
        logger.info(f"Created secure session {session_id} for user {user_id}")
    
    def _log_session_revocation(self, session_id: str, user_id: str, reason: str) -> None:
        """Log session revocation."""
        logger.info(f"Revoked session {session_id} for user {user_id}: {reason}")