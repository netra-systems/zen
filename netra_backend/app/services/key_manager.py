"""
Key Manager Service

Provides key management and encryption functionality.
Manages API keys, encryption keys, and other sensitive data.
"""

import logging
import os
import secrets
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """Types of keys managed by the key manager"""
    API_KEY = "api_key"
    ENCRYPTION_KEY = "encryption_key"
    SIGNING_KEY = "signing_key"
    JWT_SECRET = "jwt_secret"
    DATABASE_KEY = "database_key"


@dataclass
class ManagedKey:
    """Represents a managed key"""
    key_id: str
    key_type: KeyType
    value: str
    metadata: Dict[str, Any]
    created_at: float
    expires_at: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        import time
        return time.time() > self.expires_at


class KeyManager:
    """
    Key management service.
    
    Provides centralized management of keys, secrets, and cryptographic materials.
    """
    
    def __init__(self):
        self._keys: Dict[str, ManagedKey] = {}
        self._key_cache: Dict[str, str] = {}
        logger.info("KeyManager initialized")
    
    def generate_key(self, 
                    key_id: str, 
                    key_type: KeyType,
                    length: int = 32,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a new key.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key to generate
            length: Key length in bytes
            metadata: Additional metadata
            
        Returns:
            Generated key value
        """
        import time
        
        # Generate secure random key
        key_value = secrets.token_hex(length)
        
        managed_key = ManagedKey(
            key_id=key_id,
            key_type=key_type,
            value=key_value,
            metadata=metadata or {},
            created_at=time.time()
        )
        
        self._keys[key_id] = managed_key
        self._key_cache[key_id] = key_value
        
        logger.info(f"Generated {key_type.value} key: {key_id}")
        return key_value
    
    def store_key(self,
                 key_id: str,
                 key_type: KeyType,
                 value: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 expires_at: Optional[float] = None) -> None:
        """
        Store an existing key.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key
            value: Key value
            metadata: Additional metadata
            expires_at: Expiration timestamp
        """
        import time
        
        managed_key = ManagedKey(
            key_id=key_id,
            key_type=key_type,
            value=value,
            metadata=metadata or {},
            created_at=time.time(),
            expires_at=expires_at
        )
        
        self._keys[key_id] = managed_key
        self._key_cache[key_id] = value
        
        logger.info(f"Stored {key_type.value} key: {key_id}")
    
    def get_key(self, key_id: str) -> Optional[str]:
        """
        Get a key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Key value or None if not found
        """
        # Check cache first
        if key_id in self._key_cache:
            # Verify key is not expired
            if key_id in self._keys:
                managed_key = self._keys[key_id]
                if managed_key.is_expired:
                    self.delete_key(key_id)
                    return None
            return self._key_cache[key_id]
        
        # Check managed keys
        if key_id in self._keys:
            managed_key = self._keys[key_id]
            if managed_key.is_expired:
                self.delete_key(key_id)
                return None
            
            # Update cache
            self._key_cache[key_id] = managed_key.value
            return managed_key.value
        
        return None
    
    def get_or_generate_key(self, 
                           key_id: str, 
                           key_type: KeyType,
                           length: int = 32) -> str:
        """
        Get existing key or generate new one.
        
        Args:
            key_id: Key identifier
            key_type: Type of key
            length: Key length for generation
            
        Returns:
            Key value
        """
        existing_key = self.get_key(key_id)
        if existing_key:
            return existing_key
        
        return self.generate_key(key_id, key_type, length)
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete a key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if deleted, False if not found
        """
        deleted = False
        
        if key_id in self._keys:
            del self._keys[key_id]
            deleted = True
        
        if key_id in self._key_cache:
            del self._key_cache[key_id]
            deleted = True
        
        if deleted:
            logger.info(f"Deleted key: {key_id}")
        
        return deleted
    
    def list_keys(self, key_type: Optional[KeyType] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all keys with metadata.
        
        Args:
            key_type: Filter by key type
            
        Returns:
            Dictionary of key metadata
        """
        result = {}
        
        for key_id, managed_key in self._keys.items():
            if key_type and managed_key.key_type != key_type:
                continue
            
            result[key_id] = {
                'key_type': managed_key.key_type.value,
                'created_at': managed_key.created_at,
                'expires_at': managed_key.expires_at,
                'is_expired': managed_key.is_expired,
                'metadata': managed_key.metadata
            }
        
        return result
    
    def rotate_key(self, key_id: str, length: int = 32) -> Optional[str]:
        """
        Rotate an existing key.
        
        Args:
            key_id: Key identifier
            length: New key length
            
        Returns:
            New key value or None if key not found
        """
        if key_id not in self._keys:
            return None
        
        managed_key = self._keys[key_id]
        new_value = secrets.token_hex(length)
        
        # Update key value
        managed_key.value = new_value
        managed_key.created_at = time.time()
        self._key_cache[key_id] = new_value
        
        logger.info(f"Rotated key: {key_id}")
        return new_value
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys.
        
        Returns:
            Number of keys cleaned up
        """
        expired_keys = []
        
        for key_id, managed_key in self._keys.items():
            if managed_key.is_expired:
                expired_keys.append(key_id)
        
        for key_id in expired_keys:
            self.delete_key(key_id)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired keys")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get key manager statistics"""
        key_types = {}
        expired_count = 0
        
        for managed_key in self._keys.values():
            key_type = managed_key.key_type.value
            key_types[key_type] = key_types.get(key_type, 0) + 1
            
            if managed_key.is_expired:
                expired_count += 1
        
        return {
            'total_keys': len(self._keys),
            'cached_keys': len(self._key_cache),
            'expired_keys': expired_count,
            'key_types': key_types
        }


# Global key manager instance
_key_manager = None


def get_key_manager() -> KeyManager:
    """Get global key manager instance"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def get_key(key_id: str) -> Optional[str]:
    """Convenience function to get a key"""
    return get_key_manager().get_key(key_id)


def generate_key(key_id: str, key_type: KeyType, **kwargs) -> str:
    """Convenience function to generate a key"""
    return get_key_manager().generate_key(key_id, key_type, **kwargs)


def get_or_generate_key(key_id: str, key_type: KeyType, **kwargs) -> str:
    """Convenience function to get or generate a key"""
    return get_key_manager().get_or_generate_key(key_id, key_type, **kwargs)