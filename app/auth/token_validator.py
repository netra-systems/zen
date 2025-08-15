"""Token validation module - TOTP, SMS, and backup codes.

Handles multi-factor authentication token validation.
Each function ≤8 lines, strong typing, secure validation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
import hashlib
import hmac
import struct

from app.logging_config import central_logger
from app.core.enhanced_secret_manager import enhanced_secret_manager

logger = central_logger.get_logger(__name__)


class TokenValidator:
    """Handles MFA token validation operations."""
    
    def __init__(self):
        """Initialize token validator."""
        pass
    
    def validate_totp(self, user_id: str, totp_token: str) -> bool:
        """Validate TOTP token."""
        if not self._is_valid_totp_format(totp_token):
            return False
        try:
            user_secret = self._get_user_totp_secret(user_id)
            return self._check_totp_validity(user_secret, totp_token)
        except Exception as e:
            self._log_totp_error(user_id, e)
            return False
    
    def _is_valid_totp_format(self, totp_token: str) -> bool:
        """Check TOTP token format."""
        return bool(totp_token and len(totp_token) == 6 and totp_token.isdigit())
    
    def _check_totp_validity(self, user_secret: Optional[str], totp_token: str) -> bool:
        """Check TOTP token validity."""
        if not user_secret:
            return False
        return self._check_totp_time_windows(user_secret, totp_token)
    
    def _check_totp_time_windows(self, user_secret: str, totp_token: str) -> bool:
        """Check TOTP against time windows."""
        current_time = int(time.time() // 30)
        for offset in [-1, 0, 1]:
            if self._verify_totp_window(user_secret, totp_token, current_time + offset):
                return True
        return False
    
    def _verify_totp_window(self, secret: str, token: str, time_counter: int) -> bool:
        """Verify TOTP for specific time window."""
        expected_token = self._generate_totp_token(secret, time_counter)
        return token == expected_token
    
    def _generate_totp_token(self, secret: str, time_counter: int) -> str:
        """Generate TOTP token."""
        key = secret.encode()
        packed_time = struct.pack('>Q', time_counter)
        hash_digest = hmac.new(key, packed_time, hashlib.sha1).digest()
        return self._extract_totp_code(hash_digest)
    
    def _extract_totp_code(self, hash_digest: bytes) -> str:
        """Extract 6-digit code from HMAC."""
        offset = hash_digest[-1] & 0x0f
        code_bytes = hash_digest[offset:offset + 4]
        code = struct.unpack('>I', code_bytes)[0] & 0x7fffffff
        return f"{code % 1000000:06d}"
    
    def validate_sms_code(self, user_id: str, sms_code: str) -> bool:
        """Validate SMS code."""
        if not self._is_valid_sms_format(sms_code):
            return False
        try:
            stored_codes = self._get_user_sms_codes(user_id)
            return self._check_sms_validity(user_id, sms_code, stored_codes)
        except Exception as e:
            self._log_sms_error(user_id, e)
            return False
    
    def _is_valid_sms_format(self, sms_code: str) -> bool:
        """Check SMS code format."""
        return bool(sms_code and len(sms_code) == 6 and sms_code.isdigit())
    
    def _check_sms_validity(self, user_id: str, code: str, stored: Dict[str, datetime]) -> bool:
        """Check SMS code validity."""
        current_time = datetime.now(timezone.utc)
        for stored_code, expiry_time in stored.items():
            if self._is_valid_sms_match(code, stored_code, current_time, expiry_time):
                self._invalidate_sms_code(user_id, code)
                return True
        return False
    
    def _is_valid_sms_match(self, code: str, stored: str, now: datetime, expiry: datetime) -> bool:
        """Check if SMS code matches and not expired."""
        return stored == code and now < expiry
    
    def validate_backup_code(self, user_id: str, backup_code: str) -> bool:
        """Validate backup recovery code."""
        if not self._is_valid_backup_format(backup_code):
            return False
        try:
            stored_codes = self._get_user_backup_codes(user_id)
            return self._check_backup_validity(user_id, backup_code, stored_codes)
        except Exception as e:
            self._log_backup_error(user_id, e)
            return False
    
    def _is_valid_backup_format(self, backup_code: str) -> bool:
        """Check backup code format."""
        return bool(backup_code and len(backup_code) == 8)
    
    def _check_backup_validity(self, user_id: str, code: str, stored: List[Dict[str, Any]]) -> bool:
        """Check backup code validity."""
        for code_entry in stored:
            if self._is_unused_backup_match(code, code_entry):
                self._mark_backup_used(user_id, code)
                return True
        return False
    
    def _is_unused_backup_match(self, code: str, entry: Dict[str, Any]) -> bool:
        """Check if backup code matches and unused."""
        return entry["code"] == code and not entry["used"]
    
    def _mark_backup_used(self, user_id: str, backup_code: str):
        """Mark backup code as used."""
        enhanced_secret_manager.mark_backup_code_used(user_id, backup_code)
        self._log_backup_used(user_id)
    
    # Storage access methods
    def _get_user_totp_secret(self, user_id: str) -> Optional[str]:
        """Get TOTP secret for user."""
        return enhanced_secret_manager.get_user_totp_secret(user_id)
    
    def _get_user_sms_codes(self, user_id: str) -> Dict[str, datetime]:
        """Get SMS codes for user."""
        return enhanced_secret_manager.get_user_sms_codes(user_id)
    
    def _invalidate_sms_code(self, user_id: str, sms_code: str):
        """Mark SMS code as used."""
        enhanced_secret_manager._invalidate_sms_code(user_id, sms_code)
    
    def _get_user_backup_codes(self, user_id: str) -> List[Dict[str, Any]]:
        """Get backup codes for user."""
        return enhanced_secret_manager.get_user_backup_codes(user_id) or []
    
    # Logging methods
    def _log_totp_error(self, user_id: str, error: Exception):
        """Log TOTP validation error."""
        logger.error(f"TOTP validation error for user {user_id}: {error}")
    
    def _log_sms_error(self, user_id: str, error: Exception):
        """Log SMS validation error."""
        logger.error(f"SMS validation error for user {user_id}: {error}")
    
    def _log_backup_error(self, user_id: str, error: Exception):
        """Log backup code validation error."""
        logger.error(f"Backup code validation error for user {user_id}: {error}")
    
    def _log_backup_used(self, user_id: str):
        """Log backup code usage."""
        logger.info(f"Backup code used for user {user_id}")