"""
Cache entry structure for dev launcher caching system.

Provides cache entry data structure with TTL, hashing, and encryption support.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import base64


@dataclass
class CacheEntry:
    """
    Individual cache entry with TTL and content tracking.
    """
    key: str
    content_hash: str
    value: Any
    created_at: datetime
    ttl_seconds: Optional[int] = None
    encrypted: bool = False
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        age = datetime.now() - self.created_at
        return age.total_seconds() > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class CacheEncryption:
    """
    Handles encryption/decryption for sensitive cache data.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize with encryption key."""
        self._key = key or Fernet.generate_key()
        self._cipher = Fernet(self._key)
    
    def encrypt_value(self, value: Any) -> str:
        """Encrypt cache value."""
        json_str = json.dumps(value)
        encrypted_data = self._cipher.encrypt(json_str.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_value(self, encrypted_value: str) -> Any:
        """Decrypt cache value."""
        encrypted_data = base64.b64decode(encrypted_value.encode())
        decrypted_data = self._cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    
    def get_key_string(self) -> str:
        """Get key as string for storage."""
        return base64.b64encode(self._key).decode()
    
    @classmethod
    def from_key_string(cls, key_string: str) -> 'CacheEncryption':
        """Create from key string."""
        key = base64.b64decode(key_string.encode())
        return cls(key)


class ContentHasher:
    """
    Content-based hashing utilities for cache keys.
    """
    
    @staticmethod
    def hash_content(content: Union[str, bytes, Any]) -> str:
        """Generate SHA-256 hash of content."""
        if isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True).encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def hash_file_content(file_path: str) -> str:
        """Generate hash of file contents."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError):
            return ""
    
    @staticmethod
    def hash_multiple_files(file_paths: list) -> str:
        """Generate combined hash of multiple files."""
        combined_hash = hashlib.sha256()
        for file_path in sorted(file_paths):
            file_hash = ContentHasher.hash_file_content(file_path)
            combined_hash.update(f"{file_path}:{file_hash}".encode())
        return combined_hash.hexdigest()


class CacheValidator:
    """
    Cache validation utilities.
    """
    
    @staticmethod
    def validate_entry(entry: CacheEntry, current_content_hash: str) -> bool:
        """Validate cache entry against current content."""
        if entry.is_expired():
            return False
        
        return entry.content_hash == current_content_hash
    
    @staticmethod
    def validate_ttl(entry: CacheEntry) -> bool:
        """Check if entry is within TTL."""
        return not entry.is_expired()
    
    @staticmethod
    def get_remaining_ttl(entry: CacheEntry) -> Optional[int]:
        """Get remaining TTL in seconds."""
        if entry.ttl_seconds is None:
            return None
        
        age = datetime.now() - entry.created_at
        remaining = entry.ttl_seconds - age.total_seconds()
        return max(0, int(remaining))


# TTL presets for different cache types
TTL_PRESETS = {
    'permanent': None,
    'session': 3600 * 8,      # 8 hours
    'daily': 3600 * 24,       # 24 hours
    'weekly': 3600 * 24 * 7,  # 7 days
    'hourly': 3600,           # 1 hour
    'short': 300,             # 5 minutes
}