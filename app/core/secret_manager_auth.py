"""
Secret manager authentication functionality.
Handles user credentials, TOTP secrets, SMS codes, and backup codes.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.logging_config import central_logger
from app.schemas.config_types import EnvironmentType

logger = central_logger.get_logger(__name__)


class SecretManagerAuth:
    """Authentication-related secret management functionality."""
    
    def __init__(self, secret_manager):
        """Initialize with reference to main secret manager."""
        self.secret_manager = secret_manager
    
    def get_user_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user credentials for authentication."""
        try:
            secret_name = f"user-credentials-{user_id}"
            
            if self._is_development():
                return self._get_mock_credentials()
            
            return self._get_production_credentials(secret_name)
            
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return None
    
    def get_user_totp_secret(self, user_id: str) -> Optional[str]:
        """Get TOTP secret for user MFA."""
        try:
            secret_name = f"user-totp-{user_id}"
            
            if self._is_development():
                return f"mock_totp_secret_for_{user_id}"
            
            return self.secret_manager.get_secret(secret_name, "auth_service")
            
        except Exception as e:
            logger.error(f"Failed to get TOTP secret for user {user_id}: {e}")
            return None
    
    def get_user_sms_verification_code(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get SMS verification code for user."""
        try:
            secret_name = f"user-sms-code-{user_id}"
            
            if self._is_development():
                return self._get_mock_sms_code()
            
            return self._get_production_sms_code(secret_name)
            
        except Exception as e:
            logger.error(f"Failed to get SMS code for user {user_id}: {e}")
            return None
    
    def invalidate_user_sms_code(self, user_id: str) -> None:
        """Invalidate SMS verification code for user."""
        try:
            secret_name = f"user-sms-code-{user_id}"
            
            if self._is_development():
                self._log_development_invalidation(user_id)
                return
            
            self._invalidate_production_sms_code(secret_name)
            
        except Exception as e:
            logger.error(f"Failed to invalidate SMS code for user {user_id}: {e}")
    
    def get_user_backup_codes(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get backup recovery codes for user."""
        try:
            secret_name = f"user-backup-codes-{user_id}"
            
            if self._is_development():
                return self._get_mock_backup_codes()
            
            return self._get_production_backup_codes(secret_name)
            
        except Exception as e:
            logger.error(f"Failed to get backup codes for user {user_id}: {e}")
            return None
    
    def mark_backup_code_used(self, user_id: str, backup_code: str) -> None:
        """Mark backup code as used."""
        try:
            if self._is_development():
                self._log_development_backup_usage(user_id, backup_code)
                return
            
            self._mark_production_backup_code_used(user_id, backup_code)
            
        except Exception as e:
            logger.error(f"Failed to mark backup code as used for user {user_id}: {e}")
    
    def get_user_sms_codes(self, user_id: str) -> Dict[str, datetime]:
        """Get user SMS codes with expiry times."""
        sms_data = self.get_user_sms_verification_code(user_id)
        if not sms_data:
            return {}
        
        return self._convert_sms_timestamps(sms_data)
    
    def invalidate_sms_code(self, user_id: str, sms_code: str) -> None:
        """Remove specific SMS code from user's valid codes."""
        try:
            sms_codes = self.get_user_sms_codes(user_id)
            if sms_code not in sms_codes:
                return
            
            self._remove_sms_code(user_id, sms_code, sms_codes)
                
        except Exception as e:
            logger.error(f"Failed to invalidate SMS code {sms_code} for user {user_id}: {e}")
    
    def _is_development(self) -> bool:
        """Check if running in development environment."""
        return self.secret_manager.environment == EnvironmentType.DEVELOPMENT
    
    def _get_mock_credentials(self) -> Dict[str, Any]:
        """Get mock credentials for development."""
        import bcrypt
        password = "valid_password123"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        return {
            "password_hash": hashed,
            "salt": "mock_salt",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_production_credentials(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get production credentials from secure storage."""
        credentials_data = self.secret_manager.get_secret(secret_name, "auth_service")
        if credentials_data:
            return json.loads(credentials_data)
        return None
    
    def _get_mock_sms_code(self) -> Dict[str, Any]:
        """Get mock SMS code for development."""
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        return {
            "123456": expiry_time,
            "789012": expiry_time
        }
    
    def _get_production_sms_code(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get production SMS code from secure storage."""
        sms_data = self.secret_manager.get_secret(secret_name, "auth_service")
        if sms_data:
            return json.loads(sms_data)
        return None
    
    def _log_development_invalidation(self, user_id: str) -> None:
        """Log SMS invalidation for development."""
        logger.info(f"SMS code invalidated for user {user_id} (development)")
    
    def _invalidate_production_sms_code(self, secret_name: str) -> None:
        """Invalidate production SMS code."""
        if secret_name in self.secret_manager.secrets:
            del self.secret_manager.secrets[secret_name]
            if secret_name in self.secret_manager.metadata:
                del self.secret_manager.metadata[secret_name]
    
    def _get_mock_backup_codes(self) -> List[Dict[str, Any]]:
        """Get mock backup codes for development."""
        return [
            {"code": "12345678", "used": False},
            {"code": "87654321", "used": False},
            {"code": "11223344", "used": True}
        ]
    
    def _get_production_backup_codes(self, secret_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get production backup codes from secure storage."""
        backup_data = self.secret_manager.get_secret(secret_name, "auth_service")
        if backup_data:
            return json.loads(backup_data)
        return None
    
    def _log_development_backup_usage(self, user_id: str, backup_code: str) -> None:
        """Log backup code usage for development."""
        logger.info(f"Backup code {backup_code} marked as used for user {user_id} (development)")
    
    def _mark_production_backup_code_used(self, user_id: str, backup_code: str) -> None:
        """Mark production backup code as used."""
        backup_codes = self.get_user_backup_codes(user_id)
        if not backup_codes:
            return
        
        self._update_backup_code_status(user_id, backup_code, backup_codes)
    
    def _convert_sms_timestamps(self, sms_data: Dict[str, Any]) -> Dict[str, datetime]:
        """Convert string timestamps back to datetime objects."""
        result = {}
        for code, expiry_str in sms_data.items():
            if isinstance(expiry_str, str):
                result[code] = datetime.fromisoformat(expiry_str)
            else:
                result[code] = expiry_str
        return result
    
    def _remove_sms_code(self, user_id: str, sms_code: str, sms_codes: Dict[str, datetime]) -> None:
        """Remove SMS code and save updated codes."""
        del sms_codes[sms_code]
        
        secret_name = f"user-sms-code-{user_id}"
        updated_data = json.dumps({
            code: expiry.isoformat() for code, expiry in sms_codes.items()
        })
        encrypted_value = self.secret_manager.encryption.encrypt_secret(updated_data)
        self.secret_manager.secrets[secret_name] = encrypted_value
    
    def _update_backup_code_status(self, user_id: str, backup_code: str, backup_codes: List[Dict[str, Any]]) -> None:
        """Update backup code status and save."""
        for code_entry in backup_codes:
            if code_entry["code"] == backup_code:
                code_entry["used"] = True
                break
        
        secret_name = f"user-backup-codes-{user_id}"
        updated_data = json.dumps(backup_codes)
        encrypted_value = self.secret_manager.encryption.encrypt_secret(updated_data)
        self.secret_manager.secrets[secret_name] = encrypted_value