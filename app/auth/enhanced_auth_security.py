"""Enhanced authentication security - MODULAR ARCHITECTURE.

Main authentication security manager that orchestrates all security components.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timezone

from app.logging_config import central_logger
from .enhanced_auth_core import (
    AuthenticationResult, AuthenticationAttempt, SecurityMetrics, SecurityConfiguration
)
from .enhanced_auth_validator import AuthenticationValidator
from .enhanced_auth_sessions_modular import AuthSessionManager

logger = central_logger.get_logger(__name__)


class EnhancedAuthSecurity:
    """Enhanced authentication security manager - modular design."""
    
    def __init__(self):
        """Initialize authentication security with modular components."""
        self.config = SecurityConfiguration()
        self.validator = AuthenticationValidator(self.config)
        self.session_manager = AuthSessionManager(self.config)
        self.metrics = SecurityMetrics()
        self.attempts_log: List[AuthenticationAttempt] = []
    
    def authenticate_user(self, user_id: str, password: str, ip_address: str,
                         user_agent: str, additional_factors: Optional[Dict] = None) -> Tuple[AuthenticationResult, Optional[str]]:
        """Authenticate user with enhanced security checks."""
        try:
            return self._execute_authentication_flow(
                user_id, password, ip_address, user_agent, additional_factors
            )
        except Exception as e:
            return self._handle_authentication_error(user_id, ip_address, user_agent, e)
    
    def _check_preauth_flow(self, user_id: str, ip_address: str, user_agent: str) -> Optional[Tuple[AuthenticationResult, None]]:
        """Check pre-authentication and return early failure if needed."""
        preauth_result = self._perform_preauth_checks(user_id, ip_address, user_agent)
        if preauth_result != AuthenticationResult.SUCCESS:
            return preauth_result, None
        return None

    def _execute_authentication_flow(self, user_id: str, password: str, ip_address: str,
                                   user_agent: str, additional_factors: Optional[Dict]) -> Tuple[AuthenticationResult, Optional[str]]:
        """Execute the complete authentication flow."""
        preauth_failure = self._check_preauth_flow(user_id, ip_address, user_agent)
        if preauth_failure:
            return preauth_failure
        credentials_result = self._check_credentials_flow(user_id, password, ip_address, user_agent)
        if credentials_result != AuthenticationResult.SUCCESS:
            return credentials_result, None
        return self._complete_authentication_flow(user_id, ip_address, user_agent, additional_factors)
    
    def _check_credentials_flow(self, user_id: str, password: str, ip_address: str, user_agent: str) -> AuthenticationResult:
        """Check user credentials in the flow."""
        if not self._validate_user_credentials(user_id, password, ip_address, user_agent):
            return AuthenticationResult.FAILED
        return AuthenticationResult.SUCCESS
    
    def _complete_authentication_flow(self, user_id: str, ip_address: str, user_agent: str, 
                                    additional_factors: Optional[Dict]) -> Tuple[AuthenticationResult, Optional[str]]:
        """Complete the authentication flow with MFA and session creation."""
        mfa_result = self._handle_mfa_validation(user_id, ip_address, user_agent, additional_factors)
        if mfa_result != AuthenticationResult.SUCCESS:
            return mfa_result, None
        return self._finalize_successful_authentication(user_id, ip_address, user_agent)
    
    def _perform_preauth_checks(self, user_id: str, ip_address: str, user_agent: str) -> AuthenticationResult:
        """Perform pre-authentication security checks."""
        preauth_result = self.validator.pre_authentication_checks(user_id, ip_address)
        if preauth_result != AuthenticationResult.SUCCESS:
            self._log_authentication_attempt(user_id, ip_address, user_agent, preauth_result)
        return preauth_result
    
    def _validate_user_credentials(self, user_id: str, password: str, ip_address: str, user_agent: str) -> bool:
        """Validate user credentials."""
        credentials_valid = self.validator.validate_credentials(user_id, password)
        if not credentials_valid:
            self._handle_failed_authentication(user_id, ip_address, user_agent)
        return credentials_valid
    
    def _check_mfa_requirement(self, user_id: str, ip_address: str) -> bool:
        """Check if MFA is required for authentication."""
        return self.validator.requires_mfa(user_id, ip_address)

    def _handle_mfa_validation(self, user_id: str, ip_address: str, user_agent: str, 
                              additional_factors: Optional[Dict]) -> AuthenticationResult:
        """Handle MFA validation if required."""
        if not self._check_mfa_requirement(user_id, ip_address):
            return AuthenticationResult.SUCCESS
        if not additional_factors or not self.validator.validate_mfa(user_id, additional_factors):
            self._log_authentication_attempt(user_id, ip_address, user_agent, AuthenticationResult.REQUIRES_MFA)
            return AuthenticationResult.REQUIRES_MFA
        return AuthenticationResult.SUCCESS
    
    def _record_successful_login(self, user_id: str, ip_address: str, user_agent: str) -> None:
        """Record successful login metrics and cleanup."""
        self._log_authentication_attempt(user_id, ip_address, user_agent, AuthenticationResult.SUCCESS)
        self.metrics.successful_logins += 1
        self._clear_failed_attempts(user_id)

    def _finalize_successful_authentication(self, user_id: str, ip_address: str, user_agent: str) -> Tuple[AuthenticationResult, str]:
        """Finalize successful authentication."""
        session_id = self.session_manager.create_secure_session(user_id, ip_address, user_agent)
        self._record_successful_login(user_id, ip_address, user_agent)
        return AuthenticationResult.SUCCESS, session_id
    
    def _handle_authentication_error(self, user_id: str, ip_address: str, user_agent: str, error: Exception) -> Tuple[AuthenticationResult, None]:
        """Handle authentication errors."""
        logger.error(f"Authentication error for user {user_id}: {error}")
        self._log_authentication_attempt(user_id, ip_address, user_agent, AuthenticationResult.FAILED, str(error))
        return AuthenticationResult.FAILED, None
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str]]:
        """Validate session with security checks."""
        result, message = self.session_manager.validate_session(session_id, ip_address, user_agent)
        if not result and "hijacking" in str(message):
            self.metrics.session_hijacking_attempts += 1
        return result, message
    
    def _handle_failed_authentication(self, user_id: str, ip_address: str, user_agent: str):
        """Handle failed authentication attempt."""
        self._log_authentication_attempt(user_id, ip_address, user_agent, AuthenticationResult.FAILED)
        self.metrics.failed_login_attempts += 1
        self._check_failure_threshold(user_id)
    
    def _check_failure_threshold(self, user_id: str) -> None:
        """Check if user is approaching max failed attempts."""
        failed_attempts = self.validator._get_failed_attempts_for_user(user_id)
        if len(failed_attempts) >= self.config.max_failed_attempts - 1:
            logger.warning(f"User {user_id} approaching max failed attempts")
    
    def _clear_failed_attempts(self, user_id: str):
        """Clear failed attempts for user after successful login."""
        if user_id in self.validator.suspicious_users:
            del self.validator.suspicious_users[user_id]
    
    def _log_authentication_attempt(self, user_id: str, ip_address: str, user_agent: str, 
                                   result: AuthenticationResult, failure_reason: Optional[str] = None):
        """Log authentication attempt."""
        attempt = self._create_auth_attempt(user_id, ip_address, user_agent, result, failure_reason)
        self._store_auth_attempt(attempt)
        self._cleanup_old_attempts()
    
    def _create_auth_attempt(self, user_id: str, ip_address: str, user_agent: str,
                           result: AuthenticationResult, failure_reason: Optional[str]) -> AuthenticationAttempt:
        """Create authentication attempt object."""
        return AuthenticationAttempt(
            user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            timestamp=datetime.now(timezone.utc), result=result, failure_reason=failure_reason
        )
    
    def _store_auth_attempt(self, attempt: AuthenticationAttempt) -> None:
        """Store authentication attempt in logs."""
        self.attempts_log.append(attempt)
        self.validator.attempts_log.append(attempt)
    
    def _cleanup_old_attempts(self) -> None:
        """Keep only last 10000 attempts."""
        if len(self.attempts_log) > 10000:
            self.attempts_log = self.attempts_log[-10000:]
    
    def _build_security_metrics(self) -> Dict[str, Any]:
        """Build security metrics dictionary."""
        return {
            "failed_logins": self.metrics.failed_login_attempts,
            "successful_logins": self.metrics.successful_logins,
            "blocked_attempts": self.metrics.blocked_attempts,
            "security_score": self.metrics.get_security_score(),
            "hijacking_attempts": self.metrics.session_hijacking_attempts
        }

    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        session_status = self.session_manager.get_security_status()
        return {
            "active_sessions": session_status["total_active_sessions"],
            "blocked_ips": len(self.validator.blocked_ips),
            "suspicious_users": len(self.validator.suspicious_users),
            "suspicious_sessions": session_status["suspicious_sessions"],
            "metrics": self._build_security_metrics(),
            "recent_attempts": self._count_recent_attempts()
        }
    
    def _count_recent_attempts(self) -> int:
        """Count recent authentication attempts."""
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        return len([
            a for a in self.attempts_log 
            if a.timestamp > cutoff_time
        ])
    
    def revoke_session(self, session_id: str, reason: str = "admin_revoked"):
        """Revoke a specific session."""
        self.session_manager._revoke_session(session_id, reason)
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        return self.session_manager.revoke_all_user_sessions(user_id)
    
    def get_user_session_count(self, user_id: str) -> int:
        """Get active session count for a user."""
        return self.session_manager.get_user_session_count(user_id)
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return self.session_manager.cleanup_expired_sessions()
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self.session_manager.get_session_info(session_id)
    
    def reset_security_metrics(self):
        """Reset security metrics."""
        self.metrics.reset_metrics()
    
    # Backward compatibility methods for existing code
    @property
    def active_sessions(self) -> Dict[str, Any]:
        """Get active sessions for backward compatibility."""
        return self.session_manager.active_sessions
    
    @property
    def blocked_ips(self) -> Dict[str, datetime]:
        """Get blocked IPs for backward compatibility."""
        return self.validator.blocked_ips
    
    @property
    def suspicious_users(self) -> Dict[str, datetime]:
        """Get suspicious users for backward compatibility."""
        return self.validator.suspicious_users


# Global instance
enhanced_auth_security = EnhancedAuthSecurity()
