"""Permission and credential verification module.

Handles user credential validation and password verification.
Each function ≤8 lines, strong typing, secure validation.
"""

from typing import Dict, Any, Optional, List

from app.logging_config import central_logger
from app.core.enhanced_secret_manager import enhanced_secret_manager

logger = central_logger.get_logger(__name__)


class PermissionVerifier:
    """Handles credential and permission verification."""
    
    def __init__(self):
        """Initialize permission verifier."""
        pass
    
    def validate_credentials(self, user_id: str, password: str) -> bool:
        """Validate user credentials."""
        if not self._is_valid_password_format(password):
            return False
        return self._perform_credential_verification(user_id, password)
    
    def _perform_credential_verification(self, user_id: str, password: str) -> bool:
        """Perform credential verification with error handling."""
        try:
            credentials = self._get_stored_credentials(user_id)
            return self._verify_against_stored(password, credentials)
        except Exception as e:
            self._log_credential_error(user_id, e)
            return False
    
    def _is_valid_password_format(self, password: str) -> bool:
        """Check basic password format."""
        return bool(password and len(password) >= 8)
    
    def _get_stored_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user credentials from storage."""
        credentials = enhanced_secret_manager.get_user_credentials(user_id)
        return credentials
    
    def _verify_against_stored(self, password: str, credentials: Optional[Dict[str, Any]]) -> bool:
        """Verify password against stored credentials."""
        if not credentials:
            return False
        password_hash = credentials.get('password_hash')
        return self._verify_password_hash(password, password_hash)
    
    def _verify_password_hash(self, password: str, stored_hash: Optional[str]) -> bool:
        """Verify password against hash."""
        if not stored_hash:
            return False
        return self._perform_hash_verification(password, stored_hash)
    
    def _perform_hash_verification(self, password: str, stored_hash: str) -> bool:
        """Perform hash verification with error handling."""
        try:
            return self._check_bcrypt_hash(password, stored_hash)
        except Exception as e:
            self._log_password_error(e)
            return False
    
    def _check_bcrypt_hash(self, password: str, stored_hash: str) -> bool:
        """Check password with bcrypt."""
        import bcrypt
        password_bytes = password.encode('utf-8')
        hash_bytes = stored_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        try:
            user_permissions = self._get_user_permissions(user_id)
            return self._check_permission_match(permission, user_permissions)
        except Exception as e:
            self._log_permission_error(user_id, e)
            return False
    
    def _get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from storage."""
        permissions = enhanced_secret_manager.get_user_permissions(user_id)
        return permissions or []
    
    def _check_permission_match(self, permission: str, user_permissions: List[str]) -> bool:
        """Check if permission matches user's permissions."""
        return permission in user_permissions
    
    def has_role(self, user_id: str, role: str) -> bool:
        """Check if user has specific role."""
        try:
            user_roles = self._get_user_roles(user_id)
            return self._check_role_match(role, user_roles)
        except Exception as e:
            self._log_role_error(user_id, e)
            return False
    
    def _get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles from storage."""
        roles = enhanced_secret_manager.get_user_roles(user_id)
        return roles or []
    
    def _check_role_match(self, role: str, user_roles: List[str]) -> bool:
        """Check if role matches user's roles."""
        return role in user_roles
    
    def is_account_active(self, user_id: str) -> bool:
        """Check if user account is active."""
        try:
            account_status = self._get_account_status(user_id)
            return self._check_active_status(account_status)
        except Exception as e:
            self._log_account_error(user_id, e)
            return False
    
    def _get_account_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account status from storage."""
        return enhanced_secret_manager.get_account_status(user_id)
    
    def _check_active_status(self, status: Optional[Dict[str, Any]]) -> bool:
        """Check if account status is active."""
        if not status:
            return False
        return status.get('active', False) and not status.get('locked', True)
    
    def is_password_expired(self, user_id: str) -> bool:
        """Check if user password is expired."""
        try:
            password_info = self._get_password_info(user_id)
            return self._check_password_expiry(password_info)
        except Exception as e:
            self._log_password_expiry_error(user_id, e)
            return True  # Fail secure - treat as expired
    
    def _get_password_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get password info from storage."""
        return enhanced_secret_manager.get_password_info(user_id)
    
    def _check_password_expiry(self, info: Optional[Dict[str, Any]]) -> bool:
        """Check if password is expired."""
        if not info:
            return True
        from datetime import datetime, timezone
        expiry_date = info.get('expires_at')
        return expiry_date and datetime.now(timezone.utc) > expiry_date
    
    # Logging methods
    def _log_credential_error(self, user_id: str, error: Exception):
        """Log credential validation error."""
        logger.error(f"Credential validation error for user {user_id}: {error}")
    
    def _log_password_error(self, error: Exception):
        """Log password verification error."""
        logger.error(f"Password verification error: {error}")
    
    def _log_permission_error(self, user_id: str, error: Exception):
        """Log permission check error."""
        logger.error(f"Permission check error for user {user_id}: {error}")
    
    def _log_role_error(self, user_id: str, error: Exception):
        """Log role check error."""
        logger.error(f"Role check error for user {user_id}: {error}")
    
    def _log_account_error(self, user_id: str, error: Exception):
        """Log account status error."""
        logger.error(f"Account status error for user {user_id}: {error}")
    
    def _log_password_expiry_error(self, user_id: str, error: Exception):
        """Log password expiry check error."""
        logger.error(f"Password expiry check error for user {user_id}: {error}")