"""Session validation and security checks - MODULAR ARCHITECTURE.

Handles session validation, expiration checks, and security validation.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone

from app.logging_config import central_logger
from .enhanced_auth_core import SecuritySession, SessionStatus
from .session_security import SessionSecurityChecker

logger = central_logger.get_logger(__name__)


class SessionValidator:
    """Validates sessions with comprehensive security checks."""
    
    def __init__(self, active_sessions: Dict[str, SecuritySession]):
        """Initialize session validator."""
        self.active_sessions = active_sessions
        self.security_checker = SessionSecurityChecker()
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str]]:
        """Validate session with security checks."""
        basic_validation = self._perform_basic_validation(session_id)
        if not basic_validation[0]:
            return basic_validation
        
        session = self.active_sessions[session_id]
        return self._perform_security_validation(session, ip_address, user_agent)
    
    def _perform_basic_validation(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Perform basic session validation checks."""
        if not self._session_exists(session_id):
            return False, "Session not found"
        
        session = self.active_sessions[session_id]
        expiration_check = self._check_session_expiration(session)
        if not expiration_check[0]:
            return expiration_check
        
        return self._check_session_status(session)
    
    def _session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self.active_sessions
    
    def _check_session_expiration(self, session: SecuritySession) -> Tuple[bool, Optional[str]]:
        """Check if session is expired."""
        if self._is_session_expired(session):
            self._revoke_session(session.session_id, "expired")
            return False, "Session expired"
        return True, None
    
    def _is_session_expired(self, session: SecuritySession) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > session.expires_at
    
    def _check_session_status(self, session: SecuritySession) -> Tuple[bool, Optional[str]]:
        """Check if session is in active status."""
        if not self._is_session_active(session):
            return False, f"Session {session.status}"
        return True, None
    
    def _is_session_active(self, session: SecuritySession) -> bool:
        """Check if session is in active status."""
        return session.status == SessionStatus.ACTIVE
    
    def _perform_security_validation(self, session: SecuritySession, ip_address: str, 
                                   user_agent: str) -> Tuple[bool, Optional[str]]:
        """Perform comprehensive security validation."""
        security_issues = self._detect_security_issues(session, ip_address, user_agent)
        
        hijacking_result = self._check_for_hijacking(session, ip_address, user_agent)
        if not hijacking_result[0]:
            return hijacking_result
        
        self._finalize_validation(session, security_issues)
        return True, None
    
    def _detect_security_issues(self, session: SecuritySession, ip_address: str, 
                               user_agent: str) -> List[str]:
        """Detect security issues with session."""
        issues = []
        
        if self._has_ip_mismatch(session, ip_address):
            issues.append("ip_mismatch")
            session.status = SessionStatus.SUSPICIOUS
            self._log_ip_mismatch(session, ip_address)
        
        if self._has_user_agent_change(session, user_agent):
            issues.append("user_agent_change")
            self._log_user_agent_change(session)
        
        return issues
    
    def _has_ip_mismatch(self, session: SecuritySession, ip_address: str) -> bool:
        """Check if IP address has changed."""
        return session.ip_address != ip_address
    
    def _has_user_agent_change(self, session: SecuritySession, user_agent: str) -> bool:
        """Check if user agent has changed."""
        return session.user_agent != user_agent
    
    def _check_for_hijacking(self, session: SecuritySession, ip_address: str, 
                           user_agent: str) -> Tuple[bool, Optional[str]]:
        """Check for potential session hijacking."""
        if self.security_checker.detect_session_hijacking(session, ip_address, user_agent):
            return self._handle_hijacking_detection(session)
        return True, None
    
    def _handle_hijacking_detection(self, session: SecuritySession) -> Tuple[bool, str]:
        """Handle detected session hijacking."""
        self._revoke_session(session.session_id, "hijacking_detected")
        self._log_hijacking_attempt(session)
        return False, "Session security violation"
    
    def _finalize_validation(self, session: SecuritySession, security_issues: List[str]) -> None:
        """Finalize validation with activity update and logging."""
        self._update_session_activity(session)
        self._log_security_issues(session, security_issues)
    
    def _update_session_activity(self, session: SecuritySession) -> None:
        """Update session last activity timestamp."""
        session.last_activity = datetime.now(timezone.utc)
    
    def _log_security_issues(self, session: SecuritySession, issues: List[str]) -> None:
        """Log security issues for session."""
        if issues:
            logger.warning(f"Session security issues for {session.session_id}: {issues}")
            session.security_flags.update({"security_issues": issues})
    
    def _revoke_session(self, session_id: str, reason: str) -> None:
        """Revoke a session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = SessionStatus.REVOKED
            logger.info(f"Revoked session {session_id}: {reason}")
    
    def _log_ip_mismatch(self, session: SecuritySession, new_ip: str) -> None:
        """Log IP address mismatch."""
        logger.warning(
            f"IP mismatch for session {session.session_id}: {session.ip_address} -> {new_ip}"
        )
    
    def _log_user_agent_change(self, session: SecuritySession) -> None:
        """Log user agent change."""
        logger.warning(f"User agent change for session {session.session_id}")
    
    def _log_hijacking_attempt(self, session: SecuritySession) -> None:
        """Log potential session hijacking."""
        logger.error(f"Potential session hijacking detected for session {session.session_id}")