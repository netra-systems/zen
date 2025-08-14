"""
Enhanced authentication security with multi-factor protection.
Implements comprehensive authentication checks, session management, and security monitoring.
"""

import hashlib
import hmac
import time
import secrets
import jwt
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from ipaddress import ip_address, ip_network

from app.logging_config import central_logger
from app.core.exceptions import NetraSecurityException
from app.core.enhanced_secret_manager import enhanced_secret_manager

logger = central_logger.get_logger(__name__)


class AuthenticationResult(str, Enum):
    """Authentication result types."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_MFA = "requires_mfa"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SessionStatus(str, Enum):
    """Session status types."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


@dataclass
class AuthenticationAttempt:
    """Track authentication attempts."""
    user_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    result: AuthenticationResult
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class SecuritySession:
    """Enhanced session with security tracking."""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    status: SessionStatus
    security_flags: Dict[str, Any]
    csrf_token: str


class SecurityMetrics:
    """Track security metrics for monitoring."""
    
    def __init__(self):
        self.failed_login_attempts = 0
        self.successful_logins = 0
        self.blocked_attempts = 0
        self.suspicious_activities = 0
        self.session_hijacking_attempts = 0
        self.csrf_attempts = 0
        self.reset_time = datetime.utcnow()
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.__init__()
    
    def get_security_score(self) -> float:
        """Calculate security health score (0-1)."""
        total_attempts = self.failed_login_attempts + self.successful_logins
        if total_attempts == 0:
            return 1.0
        
        success_rate = self.successful_logins / total_attempts
        threat_ratio = (self.blocked_attempts + self.suspicious_activities) / max(1, total_attempts)
        
        return max(0.0, success_rate - (threat_ratio * 0.5))


class EnhancedAuthSecurity:
    """Enhanced authentication security manager."""
    
    def __init__(self):
        self.attempts_log: List[AuthenticationAttempt] = []
        self.active_sessions: Dict[str, SecuritySession] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_users: Dict[str, datetime] = {}
        self.metrics = SecurityMetrics()
        
        # Security configuration
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=8)
        self.max_concurrent_sessions = 3
        self.ip_whitelist = self._load_ip_whitelist()
        self.trusted_networks = self._load_trusted_networks()
        
    def _load_ip_whitelist(self) -> List[str]:
        """Load IP whitelist from configuration."""
        # In production, this would be loaded from secure configuration
        return ["127.0.0.1", "::1"]  # localhost only for dev
    
    def _load_trusted_networks(self) -> List[str]:
        """Load trusted network ranges."""
        # In production, this would include corporate networks
        return ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
    
    def authenticate_user(self, user_id: str, password: str, ip_address: str,
                         user_agent: str, additional_factors: Optional[Dict] = None) -> Tuple[AuthenticationResult, Optional[str]]:
        """Authenticate user with enhanced security checks."""
        
        try:
            # Pre-authentication security checks
            preauth_result = self._pre_authentication_checks(user_id, ip_address)
            if preauth_result != AuthenticationResult.SUCCESS:
                self._log_attempt(user_id, ip_address, user_agent, preauth_result)
                return preauth_result, None
            
            # Validate credentials (this would integrate with your user service)
            credentials_valid = self._validate_credentials(user_id, password)
            
            if not credentials_valid:
                self._handle_failed_authentication(user_id, ip_address, user_agent)
                return AuthenticationResult.FAILED, None
            
            # Check if MFA is required
            if self._requires_mfa(user_id, ip_address):
                if not additional_factors or not self._validate_mfa(user_id, additional_factors):
                    self._log_attempt(user_id, ip_address, user_agent, AuthenticationResult.REQUIRES_MFA)
                    return AuthenticationResult.REQUIRES_MFA, None
            
            # Create secure session
            session_id = self._create_secure_session(user_id, ip_address, user_agent)
            
            # Log successful authentication
            self._log_attempt(user_id, ip_address, user_agent, AuthenticationResult.SUCCESS)
            self.metrics.successful_logins += 1
            
            # Clear failed attempts for user
            self._clear_failed_attempts(user_id)
            
            return AuthenticationResult.SUCCESS, session_id
            
        except Exception as e:
            logger.error(f"Authentication error for user {user_id}: {e}")
            self._log_attempt(user_id, ip_address, user_agent, AuthenticationResult.FAILED, str(e))
            return AuthenticationResult.FAILED, None
    
    def _pre_authentication_checks(self, user_id: str, ip_address: str) -> AuthenticationResult:
        """Perform pre-authentication security checks."""
        
        # Check if IP is blocked
        if ip_address in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[ip_address]:
                logger.warning(f"Authentication attempt from blocked IP: {ip_address}")
                self.metrics.blocked_attempts += 1
                return AuthenticationResult.BLOCKED
            else:
                # Remove expired block
                del self.blocked_ips[ip_address]
        
        # Check if user is suspended
        if user_id in self.suspicious_users:
            if datetime.utcnow() < self.suspicious_users[user_id]:
                logger.warning(f"Authentication attempt for suspended user: {user_id}")
                return AuthenticationResult.SUSPENDED
            else:
                # Remove expired suspension
                del self.suspicious_users[user_id]
        
        # Check rate limiting for this IP
        recent_attempts = self._get_recent_attempts_by_ip(ip_address, minutes=5)
        if len(recent_attempts) > 10:  # More than 10 attempts in 5 minutes
            self._block_ip(ip_address, minutes=30)
            logger.warning(f"Rate limiting triggered for IP: {ip_address}")
            return AuthenticationResult.BLOCKED
        
        # Check for failed attempts for this user
        user_failed_attempts = self._get_failed_attempts_for_user(user_id)
        if len(user_failed_attempts) >= self.max_failed_attempts:
            self._suspend_user(user_id, minutes=15)
            logger.warning(f"Max failed attempts reached for user: {user_id}")
            return AuthenticationResult.BLOCKED
        
        return AuthenticationResult.SUCCESS
    
    def _validate_credentials(self, user_id: str, password: str) -> bool:
        """Validate user credentials (placeholder - integrate with your user service)."""
        # This is a placeholder - in reality, this would:
        # 1. Query the user database
        # 2. Verify password hash with bcrypt/scrypt
        # 3. Check if account is active
        # 4. Verify account status
        
        # For now, simulate validation
        if not user_id or not password:
            return False
        
        # Basic length checks
        if len(password) < 8:
            return False
        
        # In production, this would be:
        # user = user_service.get_user(user_id)
        # return user and user.is_active and bcrypt.checkpw(password, user.password_hash)
        
        return True  # Placeholder
    
    def _requires_mfa(self, user_id: str, ip_address: str) -> bool:
        """Determine if MFA is required for this authentication."""
        
        # Always require MFA for production
        environment = enhanced_secret_manager.environment.value
        if environment == "production":
            return True
        
        # Require MFA if logging in from new/untrusted IP
        if not self._is_trusted_ip(ip_address):
            return True
        
        # Require MFA if there have been recent suspicious activities
        if user_id in self.suspicious_users:
            return True
        
        # Check user preferences (would be loaded from database)
        # user_preferences = user_service.get_security_preferences(user_id)
        # return user_preferences.mfa_enabled
        
        return False  # Default for development
    
    def _validate_mfa(self, user_id: str, factors: Dict[str, Any]) -> bool:
        """Validate multi-factor authentication."""
        
        # Check TOTP token
        totp_token = factors.get("totp")
        if totp_token:
            return self._validate_totp(user_id, totp_token)
        
        # Check SMS code
        sms_code = factors.get("sms")
        if sms_code:
            return self._validate_sms_code(user_id, sms_code)
        
        # Check backup codes
        backup_code = factors.get("backup_code")
        if backup_code:
            return self._validate_backup_code(user_id, backup_code)
        
        return False
    
    def _validate_totp(self, user_id: str, totp_token: str) -> bool:
        """Validate TOTP token (placeholder)."""
        # This would integrate with a TOTP library like pyotp
        # totp = pyotp.TOTP(user_secret)
        # return totp.verify(totp_token, valid_window=1)
        
        return len(totp_token) == 6 and totp_token.isdigit()  # Placeholder
    
    def _validate_sms_code(self, user_id: str, sms_code: str) -> bool:
        """Validate SMS verification code (placeholder)."""
        # This would check against stored SMS codes
        return len(sms_code) == 6 and sms_code.isdigit()  # Placeholder
    
    def _validate_backup_code(self, user_id: str, backup_code: str) -> bool:
        """Validate backup recovery code (placeholder)."""
        # This would check against stored backup codes and mark as used
        return len(backup_code) == 8  # Placeholder
    
    def _create_secure_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a secure session with comprehensive tracking."""
        
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Generate CSRF token
        csrf_token = secrets.token_urlsafe(24)
        
        # Check for concurrent sessions
        user_sessions = [s for s in self.active_sessions.values() if s.user_id == user_id]
        if len(user_sessions) >= self.max_concurrent_sessions:
            # Revoke oldest session
            oldest_session = min(user_sessions, key=lambda s: s.last_activity)
            self._revoke_session(oldest_session.session_id, "concurrent_limit")
        
        # Create session
        session = SecuritySession(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.session_timeout,
            status=SessionStatus.ACTIVE,
            security_flags={
                "is_trusted_ip": self._is_trusted_ip(ip_address),
                "requires_mfa": self._requires_mfa(user_id, ip_address),
                "created_from_new_device": self._is_new_device(user_id, user_agent)
            },
            csrf_token=csrf_token
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created secure session {session_id} for user {user_id}")
        
        return session_id
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str]]:
        """Validate session with security checks."""
        
        if session_id not in self.active_sessions:
            return False, "Session not found"
        
        session = self.active_sessions[session_id]
        
        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            self._revoke_session(session_id, "expired")
            return False, "Session expired"
        
        # Check if session is revoked
        if session.status != SessionStatus.ACTIVE:
            return False, f"Session {session.status}"
        
        # Security checks
        security_issues = []
        
        # Check IP consistency
        if session.ip_address != ip_address:
            logger.warning(f"IP address mismatch for session {session_id}: {session.ip_address} -> {ip_address}")
            security_issues.append("ip_mismatch")
            session.status = SessionStatus.SUSPICIOUS
        
        # Check user agent consistency (basic check)
        if session.user_agent != user_agent:
            logger.warning(f"User agent change for session {session_id}")
            security_issues.append("user_agent_change")
        
        # Check for session hijacking indicators
        if self._detect_session_hijacking(session, ip_address, user_agent):
            logger.error(f"Potential session hijacking detected for session {session_id}")
            self._revoke_session(session_id, "hijacking_detected")
            self.metrics.session_hijacking_attempts += 1
            return False, "Session security violation"
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        
        # Log security issues but don't block if minor
        if security_issues:
            logger.warning(f"Session security issues for {session_id}: {security_issues}")
            session.security_flags.update({"security_issues": security_issues})
        
        return True, None
    
    def _detect_session_hijacking(self, session: SecuritySession, current_ip: str, current_user_agent: str) -> bool:
        """Detect potential session hijacking."""
        
        # Geographic location change (would need GeoIP service)
        # if geoip_service.get_country(session.ip_address) != geoip_service.get_country(current_ip):
        #     return True
        
        # Rapid IP changes
        if session.ip_address != current_ip:
            time_since_creation = datetime.utcnow() - session.created_at
            if time_since_creation < timedelta(minutes=5):  # IP changed within 5 minutes
                return True
        
        # Suspicious user agent changes
        if (session.user_agent != current_user_agent and 
            not self._is_reasonable_ua_change(session.user_agent, current_user_agent)):
            return True
        
        return False
    
    def _is_reasonable_ua_change(self, old_ua: str, new_ua: str) -> bool:
        """Check if user agent change is reasonable (e.g., browser update)."""
        # Simple check - in production this would be more sophisticated
        old_parts = old_ua.split()
        new_parts = new_ua.split()
        
        # If the base browser is the same, it's probably an update
        if len(old_parts) > 0 and len(new_parts) > 0:
            return old_parts[0] == new_parts[0]
        
        return False
    
    def _is_trusted_ip(self, ip_address: str) -> bool:
        """Check if IP address is trusted."""
        if ip_address in self.ip_whitelist:
            return True
        
        try:
            ip = ip_address(ip_address)
            for network_str in self.trusted_networks:
                network = ip_network(network_str, strict=False)
                if ip in network:
                    return True
        except ValueError:
            logger.warning(f"Invalid IP address format: {ip_address}")
        
        return False
    
    def _is_new_device(self, user_id: str, user_agent: str) -> bool:
        """Check if this is a new device for the user."""
        # Check recent sessions for this user agent
        recent_sessions = [
            s for s in self.active_sessions.values()
            if s.user_id == user_id and s.user_agent == user_agent
        ]
        return len(recent_sessions) == 0
    
    def _handle_failed_authentication(self, user_id: str, ip_address: str, user_agent: str):
        """Handle failed authentication attempt."""
        self._log_attempt(user_id, ip_address, user_agent, AuthenticationResult.FAILED)
        self.metrics.failed_login_attempts += 1
        
        # Check if we should block the IP or user
        failed_attempts = self._get_failed_attempts_for_user(user_id)
        if len(failed_attempts) >= self.max_failed_attempts - 1:  # One more and they're blocked
            logger.warning(f"User {user_id} approaching max failed attempts")
    
    def _block_ip(self, ip_address: str, minutes: int = 15):
        """Block IP address for specified duration."""
        block_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.blocked_ips[ip_address] = block_until
        logger.warning(f"Blocked IP {ip_address} until {block_until}")
    
    def _suspend_user(self, user_id: str, minutes: int = 15):
        """Suspend user for specified duration."""
        suspend_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.suspicious_users[user_id] = suspend_until
        logger.warning(f"Suspended user {user_id} until {suspend_until}")
    
    def _revoke_session(self, session_id: str, reason: str):
        """Revoke a session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = SessionStatus.REVOKED
            logger.info(f"Revoked session {session_id} for user {session.user_id}: {reason}")
    
    def _log_attempt(self, user_id: str, ip_address: str, user_agent: str, 
                    result: AuthenticationResult, failure_reason: Optional[str] = None):
        """Log authentication attempt."""
        attempt = AuthenticationAttempt(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            result=result,
            failure_reason=failure_reason
        )
        
        self.attempts_log.append(attempt)
        
        # Keep only last 10000 attempts
        if len(self.attempts_log) > 10000:
            self.attempts_log = self.attempts_log[-10000:]
    
    def _get_recent_attempts_by_ip(self, ip_address: str, minutes: int = 15) -> List[AuthenticationAttempt]:
        """Get recent authentication attempts from an IP."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            attempt for attempt in self.attempts_log
            if attempt.ip_address == ip_address and attempt.timestamp > cutoff_time
        ]
    
    def _get_failed_attempts_for_user(self, user_id: str, minutes: int = 60) -> List[AuthenticationAttempt]:
        """Get recent failed attempts for a user."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            attempt for attempt in self.attempts_log
            if (attempt.user_id == user_id and 
                attempt.result == AuthenticationResult.FAILED and 
                attempt.timestamp > cutoff_time)
        ]
    
    def _clear_failed_attempts(self, user_id: str):
        """Clear failed attempts for user after successful login."""
        # Remove from suspicious users if present
        if user_id in self.suspicious_users:
            del self.suspicious_users[user_id]
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        return {
            "active_sessions": len(self.active_sessions),
            "blocked_ips": len(self.blocked_ips),
            "suspicious_users": len(self.suspicious_users),
            "metrics": {
                "failed_logins": self.metrics.failed_login_attempts,
                "successful_logins": self.metrics.successful_logins,
                "blocked_attempts": self.metrics.blocked_attempts,
                "security_score": self.metrics.get_security_score()
            },
            "recent_attempts": len([
                a for a in self.attempts_log 
                if a.timestamp > datetime.utcnow() - timedelta(hours=1)
            ])
        }


# Global instance
enhanced_auth_security = EnhancedAuthSecurity()