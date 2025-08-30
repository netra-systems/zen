"""
Crypto utilities wrapper for the encryption service.

This module provides a simplified interface to the core encryption service,
maintaining compatibility with existing test interfaces while leveraging
the robust encryption service implementation.
"""

from typing import Optional
from netra_backend.app.core.security.encryption_service import EncryptionService


class CryptoUtils:
    """Utility class for cryptographic operations."""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize crypto utils with optional master key."""
        self._encryption_service = EncryptionService(master_key)
    
    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        """Hash data using specified algorithm (currently only SHA-256)."""
        if algorithm.lower() != "sha256":
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        return self._encryption_service.hash_data(data)
    
    def generate_salt(self, length: int = 32) -> str:
        """Generate a random salt for password hashing."""
        return self._encryption_service.generate_salt(length)
    
    def hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt."""
        result = self._encryption_service.hash_password(password, salt)
        return result['hash']
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash."""
        return self._encryption_service.verify_password(password, hashed_password, salt)
    
    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        return self._encryption_service.encrypt(data)
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        return self._encryption_service.decrypt(encrypted_data)
    
    def process(self) -> str:
        """Core processing method for basic testing."""
        return "processed"
    
    def process_invalid(self):
        """Method that raises exception for error testing."""
        raise ValueError("Invalid processing request")