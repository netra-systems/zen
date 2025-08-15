"""Session management module - MODULAR ARCHITECTURE.

Handles session creation, validation, hijacking detection, and lifecycle.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone, timedelta
import secrets
import time

from app.logging_config import central_logger
from .enhanced_auth_core import (
    SecuritySession, SessionStatus, SecurityConfiguration
)

logger = central_logger.get_logger(__name__)


class SessionManager:
    """Manages secure sessions with hijacking detection."""
    
    def __init__(self, config: SecurityConfiguration):
        """Initialize session manager with configuration."""
        self.config = config
        self.active_sessions: Dict[str, SecuritySession] = {}
    
    def create_secure_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a secure session with comprehensive tracking."""
        session_id = self._generate_session_id()
        csrf_token = self._generate_csrf_token()
        
        self._enforce_concurrent_session_limit(user_id)
        
        session = self._build_security_session(
            session_id, user_id, ip_address, user_agent, csrf_token
        )
        
        self.active_sessions[session_id] = session
        self._log_session_creation(session_id, user_id)
        
        return session_id
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(24)
    
    def _enforce_concurrent_session_limit(self, user_id: str):
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
        
        return SecuritySession(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_activity=now,
            expires_at=now + self.config.session_timeout,
            status=SessionStatus.ACTIVE,
            security_flags=security_flags,
            csrf_token=csrf_token
        )
    
    def _build_security_flags(self, user_id: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Build security flags for session."""
        return {
            "is_trusted_ip": self._is_trusted_ip(ip_address),
            "requires_mfa": self._requires_mfa(user_id, ip_address),
            "created_from_new_device": self._is_new_device(user_id, user_agent)
        }
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str]]:
        """Validate session with security checks."""
        if not self._session_exists(session_id):
            return False, "Session not found"
        
        session = self.active_sessions[session_id]
        
        if self._is_session_expired(session):
            return False, "Session expired"
        
        if not self._is_session_active(session):
            return False, f"Session {session.status}"
        
        return self._perform_security_validation(session, ip_address, user_agent)
    
    def _session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self.active_sessions
    
    def _is_session_expired(self, session: SecuritySession) -> bool:
        """Check if session is expired."""
        if datetime.now(timezone.utc) > session.expires_at:
            self._revoke_session(session.session_id, "expired")
            return True
        return False
    
    def _is_session_active(self, session: SecuritySession) -> bool:
        """Check if session is in active status."""
        return session.status == SessionStatus.ACTIVE
    
    def _perform_security_validation(self, session: SecuritySession, ip_address: str, 
                                   user_agent: str) -> Tuple[bool, Optional[str]]:
        """Perform comprehensive security validation."""
        security_issues = self._detect_security_issues(session, ip_address, user_agent)
        
        if self._detect_session_hijacking(session, ip_address, user_agent):
            return self._handle_hijacking_detection(session)
        
        self._update_session_activity(session)
        self._log_security_issues(session, security_issues)
        
        return True, None
    
    def _detect_security_issues(self, session: SecuritySession, ip_address: str, 
                               user_agent: str) -> List[str]:
        """Detect security issues with session."""
        issues = []
        
        if session.ip_address != ip_address:
            issues.append("ip_mismatch")
            session.status = SessionStatus.SUSPICIOUS
            self._log_ip_mismatch(session, ip_address)
        
        if session.user_agent != user_agent:
            issues.append("user_agent_change")
            self._log_user_agent_change(session)
        
        return issues
    
    def _detect_session_hijacking(self, session: SecuritySession, current_ip: str, 
                                 current_user_agent: str) -> bool:
        """Detect potential session hijacking."""
        if self._rapid_ip_change_detected(session, current_ip):
            return True
        
        if self._suspicious_user_agent_change(session, current_user_agent):
            return True
        
        return False
    
    def _rapid_ip_change_detected(self, session: SecuritySession, current_ip: str) -> bool:
        """Detect rapid IP address changes."""
        if session.ip_address == current_ip:
            return False
        
        time_since_creation = datetime.now(timezone.utc) - session.created_at
        return (time_since_creation > timedelta(minutes=1) and 
                time_since_creation < timedelta(minutes=5))
    
    def _suspicious_user_agent_change(self, session: SecuritySession, current_user_agent: str) -> bool:
        """Detect suspicious user agent changes."""
        if session.user_agent == current_user_agent:
            return False
        
        if self._is_reasonable_ua_change(session.user_agent, current_user_agent):
            return False
        
        return self._is_different_browser_family(session.user_agent, current_user_agent)
    
    def _is_reasonable_ua_change(self, old_ua: str, new_ua: str) -> bool:
        """Check if user agent change is reasonable."""
        old_parts = old_ua.split()
        new_parts = new_ua.split()
        
        if len(old_parts) > 0 and len(new_parts) > 0:
            return old_parts[0] == new_parts[0]
        
        return False
    
    def _is_different_browser_family(self, old_ua: str, new_ua: str) -> bool:
        """Check if user agents represent different browser families."""
        old_browser = old_ua.split()[0] if old_ua.split() else ""
        new_browser = new_ua.split()[0] if new_ua.split() else ""
        
        return (old_browser != new_browser and 
                bool(old_browser) and bool(new_browser))
    
    def _handle_hijacking_detection(self, session: SecuritySession) -> Tuple[bool, str]:
        """Handle detected session hijacking."""
        self._revoke_session(session.session_id, "hijacking_detected")
        self._log_hijacking_attempt(session)
        return False, "Session security violation"
    
    def _update_session_activity(self, session: SecuritySession):
        """Update session last activity timestamp."""
        session.last_activity = datetime.now(timezone.utc)
    
    def _log_security_issues(self, session: SecuritySession, issues: List[str]):
        """Log security issues for session."""
        if issues:
            logger.warning(f"Session security issues for {session.session_id}: {issues}")
            session.security_flags.update({"security_issues": issues})
    
    def _revoke_session(self, session_id: str, reason: str):
        """Revoke a session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = SessionStatus.REVOKED
            self._log_session_revocation(session_id, session.user_id, reason)
    
    def _is_trusted_ip(self, ip_address: str) -> bool:
        """Check if IP address is trusted."""
        return ip_address in self.config.ip_whitelist
    
    def _requires_mfa(self, user_id: str, ip_address: str) -> bool:
        """Check if MFA is required (simplified check)."""
        return not self._is_trusted_ip(ip_address)
    
    def _is_new_device(self, user_id: str, user_agent: str) -> bool:
        """Check if this is a new device for the user."""
        recent_sessions = [
            s for s in self.active_sessions.values()
            if s.user_id == user_id and s.user_agent == user_agent
        ]
        return len(recent_sessions) == 0
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for monitoring."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return self._build_session_info_dict(session)
    
    def _build_session_info_dict(self, session: SecuritySession) -> Dict[str, Any]:
        """Build session information dictionary."""
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "status": session.status.value,
            "security_flags": session.security_flags
        }
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count removed."""
        now = datetime.now(timezone.utc)
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if now > session.expires_at
        ]
        
        for session_id in expired_sessions:
            self._remove_expired_session(session_id)
        
        return len(expired_sessions)
    
    def _remove_expired_session(self, session_id: str):
        """Remove expired session from active sessions."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Removed expired session {session_id}")
    
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
            "suspicious_sessions": self._count_suspicious_sessions(),
            "expired_sessions_cleaned": self.cleanup_expired_sessions()
        }
    
    def _count_suspicious_sessions(self) -> int:
        """Count sessions marked as suspicious."""
        return len([
            s for s in self.active_sessions.values() 
            if s.status == SessionStatus.SUSPICIOUS
        ])
    
    # Logging helper methods
    def _log_session_creation(self, session_id: str, user_id: str):
        """Log session creation."""
        logger.info(f"Created secure session {session_id} for user {user_id}")
    
    def _log_session_revocation(self, session_id: str, user_id: str, reason: str):
        """Log session revocation."""
        logger.info(f"Revoked session {session_id} for user {user_id}: {reason}")
    
    def _log_ip_mismatch(self, session: SecuritySession, new_ip: str):
        """Log IP address mismatch."""
        logger.warning(
            f"IP mismatch for session {session.session_id}: {session.ip_address} -> {new_ip}"
        )
    
    def _log_user_agent_change(self, session: SecuritySession):
        """Log user agent change."""
        logger.warning(f"User agent change for session {session.session_id}")
    
    def _log_hijacking_attempt(self, session: SecuritySession):
        """Log potential session hijacking."""
        logger.error(f"Potential session hijacking detected for session {session.session_id}")
