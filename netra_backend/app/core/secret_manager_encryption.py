"""
Secret encryption and decryption functionality.
Handles secure encryption/decryption of secret values using Fernet.
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from netra_backend.app.config import get_config
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SecretEncryption:
    """Handle secret encryption/decryption."""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize with master key for encryption."""
        if master_key:
            self._fernet = self._create_fernet_from_key(master_key)
        else:
            self._fernet = self._create_fernet_from_env()
    
    def encrypt_secret(self, secret_value: str) -> str:
        """Encrypt a secret value."""
        return self._fernet.encrypt(secret_value.encode()).decode()
    
    def decrypt_secret(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        return self._fernet.decrypt(encrypted_value.encode()).decode()
    
    def _create_fernet_from_key(self, master_key: str) -> Fernet:
        """Create Fernet instance from master key."""
        key_bytes = master_key.encode()
        kdf = self._create_kdf()
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key)
    
    def _create_fernet_from_env(self) -> Fernet:
        """Create Fernet instance from environment variable."""
        config = get_config()
        fernet_key = getattr(config, 'fernet_key', None)
        if fernet_key:
            return Fernet(fernet_key.encode())
        else:
            return self._generate_development_key()
    
    def _create_kdf(self) -> PBKDF2HMAC:
        """Create key derivation function."""
        return PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'netra_salt_2024',  # In production, use random salt per secret
            iterations=100000,
        )
    
    def _generate_development_key(self) -> Fernet:
        """Generate new key for development only."""
        logger.warning("No FERNET_KEY found, generating new key for development")
        return Fernet(Fernet.generate_key())