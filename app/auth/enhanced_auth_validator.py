"""Authentication validation module - MODULAR ARCHITECTURE.

Composer module that orchestrates auth validation through specialized modules.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Any

from app.logging_config import central_logger
from app.core.enhanced_secret_manager import enhanced_secret_manager
from .enhanced_auth_core import (
    AuthenticationResult, AuthenticationAttempt, SecurityConfiguration
)
from .token_validator import TokenValidator
from .session_checker import SessionChecker
from .permission_verifier import PermissionVerifier

logger = central_logger.get_logger(__name__)


class AuthenticationValidator:
    """Orchestrates authentication validation through modular components."""
    
    def __init__(self, config: SecurityConfiguration):
        """Initialize validator with modular components."""
        self.config = config
        self.token_validator = TokenValidator()
        self.session_checker = SessionChecker(config)
        self.permission_verifier = PermissionVerifier()
    
    def pre_authentication_checks(self, user_id: str, ip_address: str) -> AuthenticationResult:
        """Perform pre-authentication security checks."""
        ip_check = self._check_ip_security(ip_address)
        if ip_check != AuthenticationResult.SUCCESS:
            return ip_check
        user_check = self._check_user_security(user_id)
        if user_check != AuthenticationResult.SUCCESS:
            return user_check
        return AuthenticationResult.SUCCESS
    
    def _check_ip_security(self, ip_address: str) -> AuthenticationResult:
        """Check IP-related security constraints."""
        if self.session_checker.is_ip_blocked(ip_address):
            return AuthenticationResult.BLOCKED
        if self.session_checker.is_rate_limited(ip_address):
            return AuthenticationResult.BLOCKED
        return AuthenticationResult.SUCCESS
    
    def _check_user_security(self, user_id: str) -> AuthenticationResult:
        """Check user-related security constraints."""
        if self.session_checker.is_user_suspended(user_id):
            return AuthenticationResult.SUSPENDED
        if self.session_checker.has_too_many_failures(user_id):
            return AuthenticationResult.BLOCKED
        return AuthenticationResult.SUCCESS
    
    
    def validate_credentials(self, user_id: str, password: str) -> bool:
        """Validate user credentials."""
        return self.permission_verifier.validate_credentials(user_id, password)
    
    def requires_mfa(self, user_id: str, ip_address: str) -> bool:
        """Determine if MFA is required."""
        if self._is_production_environment():
            return True
        if not self.session_checker.is_trusted_ip(ip_address):
            return True
        if self.session_checker.is_user_suspended(user_id):
            return True
        return False
    
    def _is_production_environment(self) -> bool:
        """Check if running in production."""
        return enhanced_secret_manager.environment.value == "production"
    
    def validate_mfa(self, user_id: str, factors: Dict[str, Any]) -> bool:
        """Validate multi-factor authentication."""
        if self._try_totp_validation(user_id, factors):
            return True
        if self._try_sms_validation(user_id, factors):
            return True
        if self._try_backup_validation(user_id, factors):
            return True
        return False
    
    def _try_totp_validation(self, user_id: str, factors: Dict[str, Any]) -> bool:
        """Try TOTP token validation."""
        totp_token = factors.get("totp")
        if totp_token:
            return self.token_validator.validate_totp(user_id, totp_token)
        return False
    
    def _try_sms_validation(self, user_id: str, factors: Dict[str, Any]) -> bool:
        """Try SMS code validation."""
        sms_code = factors.get("sms")
        if sms_code:
            return self.token_validator.validate_sms_code(user_id, sms_code)
        return False
    
    def _try_backup_validation(self, user_id: str, factors: Dict[str, Any]) -> bool:
        """Try backup code validation."""
        backup_code = factors.get("backup_code")
        if backup_code:
            return self.token_validator.validate_backup_code(user_id, backup_code)
        return False
    
    
    def record_attempt(self, attempt: AuthenticationAttempt):
        """Record authentication attempt."""
        self.session_checker.add_attempt(attempt)
    
    def is_account_active(self, user_id: str) -> bool:
        """Check if account is active."""
        return self.permission_verifier.is_account_active(user_id)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check user permission."""
        return self.permission_verifier.has_permission(user_id, permission)
    
    def has_role(self, user_id: str, role: str) -> bool:
        """Check user role."""
        return self.permission_verifier.has_role(user_id, role)
    
    def is_password_expired(self, user_id: str) -> bool:
        """Check password expiry."""
        return self.permission_verifier.is_password_expired(user_id)
