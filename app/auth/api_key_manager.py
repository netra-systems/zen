"""
API Key Management and Rotation System.
Implements secure API key generation, rotation, and lifecycle management.
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from app.logging_config import central_logger
from app.core.exceptions_auth import NetraSecurityException

logger = central_logger.get_logger(__name__)


class ApiKeyStatus(str, Enum):
    """API key status types."""
    ACTIVE = "active"
    EXPIRED = "expired" 
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


class ApiKeyScope(str, Enum):
    """API key permission scopes."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    SERVICE = "service"


@dataclass
class ApiKey:
    """API key model with metadata."""
    key_id: str
    user_id: str
    key_hash: str  # Hashed version of the key
    name: str
    scope: ApiKeyScope
    status: ApiKeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int
    rate_limit: int  # requests per minute
    metadata: Dict[str, str]


class ApiKeyManager:
    """Manages API key lifecycle and rotation."""
    
    def __init__(self):
        self.keys: Dict[str, ApiKey] = {}
        self.key_hashes: Dict[str, str] = {}  # hash -> key_id mapping
        self.user_keys: Dict[str, List[str]] = {}  # user_id -> key_ids
        
        # Configuration
        self.default_expiry_days = 90
        self.max_keys_per_user = 10
        self.key_length = 32
        self.rotation_warning_days = 7
        
    def generate_api_key(self, user_id: str, name: str, scope: ApiKeyScope,
                        expires_in_days: Optional[int] = None,
                        rate_limit: int = 1000) -> Tuple[str, str]:
        """Generate a new API key.
        
        Returns:
            Tuple of (api_key, key_id)
        """
        # Check user key limit
        user_key_count = len(self.user_keys.get(user_id, []))
        if user_key_count >= self.max_keys_per_user:
            raise NetraSecurityException(
                f"User {user_id} has reached maximum API key limit"
            )
        
        # Generate secure API key
        raw_key = self._generate_secure_key()
        key_id = secrets.token_urlsafe(16)
        key_hash = self._hash_key(raw_key)
        
        # Calculate expiry
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        elif self.default_expiry_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.default_expiry_days)
        
        # Create API key
        api_key = ApiKey(
            key_id=key_id,
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            scope=scope,
            status=ApiKeyStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            last_used=None,
            usage_count=0,
            rate_limit=rate_limit,
            metadata={}
        )
        
        # Store key
        self.keys[key_id] = api_key
        self.key_hashes[key_hash] = key_id
        
        if user_id not in self.user_keys:
            self.user_keys[user_id] = []
        self.user_keys[user_id].append(key_id)
        
        logger.info(f"Generated API key {key_id} for user {user_id}")
        return raw_key, key_id
    
    def validate_api_key(self, raw_key: str) -> Optional[ApiKey]:
        """Validate an API key and return key info if valid."""
        if not raw_key:
            return None
        
        key_hash = self._hash_key(raw_key)
        key_id = self.key_hashes.get(key_hash)
        
        if not key_id or key_id not in self.keys:
            return None
        
        api_key = self.keys[key_id]
        
        # Check if key is active
        if api_key.status != ApiKeyStatus.ACTIVE:
            logger.warning(f"API key {key_id} is not active: {api_key.status}")
            return None
        
        # Check expiry
        if api_key.expires_at and datetime.now(timezone.utc) > api_key.expires_at:
            logger.warning(f"API key {key_id} has expired")
            self._mark_key_expired(key_id)
            return None
        
        # Update usage
        api_key.last_used = datetime.now(timezone.utc)
        api_key.usage_count += 1
        
        return api_key
    
    def rotate_api_key(self, key_id: str) -> Tuple[str, str]:
        """Rotate an existing API key."""
        if key_id not in self.keys:
            raise NetraSecurityException(f"API key {key_id} not found")
        
        old_key = self.keys[key_id]
        
        if old_key.status != ApiKeyStatus.ACTIVE:
            raise NetraSecurityException(f"Cannot rotate inactive key {key_id}")
        
        # Generate new key
        new_raw_key, new_key_id = self.generate_api_key(
            user_id=old_key.user_id,
            name=f"{old_key.name} (rotated)",
            scope=old_key.scope,
            rate_limit=old_key.rate_limit
        )
        
        # Mark old key for rotation
        old_key.status = ApiKeyStatus.PENDING_ROTATION
        old_key.metadata["rotated_to"] = new_key_id
        old_key.metadata["rotation_date"] = datetime.now(timezone.utc).isoformat()
        
        # Update new key metadata
        self.keys[new_key_id].metadata["rotated_from"] = key_id
        
        logger.info(f"Rotated API key {key_id} to {new_key_id}")
        return new_raw_key, new_key_id
    
    def revoke_api_key(self, key_id: str, reason: str = "manual_revocation") -> bool:
        """Revoke an API key."""
        if key_id not in self.keys:
            return False
        
        api_key = self.keys[key_id]
        api_key.status = ApiKeyStatus.REVOKED
        api_key.metadata["revocation_reason"] = reason
        api_key.metadata["revocation_date"] = datetime.now(timezone.utc).isoformat()
        
        # Remove from hash lookup
        if api_key.key_hash in self.key_hashes:
            del self.key_hashes[api_key.key_hash]
        
        logger.info(f"Revoked API key {key_id}: {reason}")
        return True
    
    def list_user_keys(self, user_id: str) -> List[Dict]:
        """List all API keys for a user."""
        user_key_ids = self.user_keys.get(user_id, [])
        keys_info = []
        
        for key_id in user_key_ids:
            if key_id in self.keys:
                api_key = self.keys[key_id]
                keys_info.append({
                    "key_id": key_id,
                    "name": api_key.name,
                    "scope": api_key.scope,
                    "status": api_key.status,
                    "created_at": api_key.created_at,
                    "expires_at": api_key.expires_at,
                    "last_used": api_key.last_used,
                    "usage_count": api_key.usage_count,
                    "needs_rotation": self._needs_rotation(api_key)
                })
        
        return keys_info
    
    def cleanup_expired_keys(self) -> int:
        """Clean up expired keys and return count."""
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for key_id, api_key in list(self.keys.items()):
            if (api_key.expires_at and now > api_key.expires_at and 
                api_key.status == ApiKeyStatus.ACTIVE):
                self._mark_key_expired(key_id)
                expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired API keys")
        return expired_count
    
    def get_rotation_candidates(self) -> List[Dict]:
        """Get keys that need rotation."""
        candidates = []
        
        for key_id, api_key in self.keys.items():
            if self._needs_rotation(api_key):
                candidates.append({
                    "key_id": key_id,
                    "user_id": api_key.user_id,
                    "name": api_key.name,
                    "expires_at": api_key.expires_at,
                    "days_until_expiry": (api_key.expires_at - datetime.now(timezone.utc)).days
                    if api_key.expires_at else None
                })
        
        return candidates
    
    def _generate_secure_key(self) -> str:
        """Generate a cryptographically secure API key."""
        return secrets.token_urlsafe(self.key_length)
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _mark_key_expired(self, key_id: str) -> None:
        """Mark a key as expired."""
        if key_id in self.keys:
            api_key = self.keys[key_id]
            api_key.status = ApiKeyStatus.EXPIRED
            
            # Remove from hash lookup
            if api_key.key_hash in self.key_hashes:
                del self.key_hashes[api_key.key_hash]
    
    def _needs_rotation(self, api_key: ApiKey) -> bool:
        """Check if a key needs rotation."""
        if api_key.status != ApiKeyStatus.ACTIVE:
            return False
        
        if not api_key.expires_at:
            return False
        
        warning_date = api_key.expires_at - timedelta(days=self.rotation_warning_days)
        return datetime.now(timezone.utc) > warning_date
    
    def get_security_metrics(self) -> Dict:
        """Get security metrics for API keys."""
        total_keys = len(self.keys)
        active_keys = sum(1 for k in self.keys.values() if k.status == ApiKeyStatus.ACTIVE)
        expired_keys = sum(1 for k in self.keys.values() if k.status == ApiKeyStatus.EXPIRED)
        revoked_keys = sum(1 for k in self.keys.values() if k.status == ApiKeyStatus.REVOKED)
        rotation_needed = len(self.get_rotation_candidates())
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "revoked_keys": revoked_keys,
            "rotation_needed": rotation_needed,
            "users_with_keys": len(self.user_keys),
            "average_keys_per_user": total_keys / max(1, len(self.user_keys))
        }


# Global instance
api_key_manager = ApiKeyManager()