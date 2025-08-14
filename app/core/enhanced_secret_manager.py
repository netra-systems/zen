"""
Enhanced secret management system with multiple security layers.
Implements secure secret storage, rotation, and access control following PRODUCTION_SECRETS_ISOLATION.xml.
"""

import os
import json
import hashlib
import time
from typing import Dict, Optional, Any, List, Set
from datetime import datetime, timedelta
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.logging_config import central_logger
from app.core.exceptions import NetraSecurityException
from app.schemas.config_types import SecretType, EnvironmentType

logger = central_logger.get_logger(__name__)


class SecretAccessLevel(str, Enum):
    """Secret access levels for permission control."""
    PUBLIC = "public"          # Non-sensitive configuration
    INTERNAL = "internal"      # Internal app secrets  
    RESTRICTED = "restricted"  # Database passwords, API keys
    CRITICAL = "critical"      # Production secrets, encryption keys


class SecretMetadata:
    """Metadata for secret tracking and rotation."""
    
    def __init__(self, secret_name: str, access_level: SecretAccessLevel,
                 environment: EnvironmentType, rotation_days: int = 90):
        self.secret_name = secret_name
        self.access_level = access_level
        self.environment = environment
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.last_rotated = datetime.utcnow()
        self.rotation_days = rotation_days
        self.access_count = 0
        self.authorized_components: Set[str] = set()
    
    @property
    def needs_rotation(self) -> bool:
        """Check if secret needs rotation."""
        days_since_rotation = (datetime.utcnow() - self.last_rotated).days
        return days_since_rotation >= self.rotation_days
    
    @property
    def is_expired(self) -> bool:
        """Check if secret is expired (past rotation deadline)."""
        days_since_rotation = (datetime.utcnow() - self.last_rotated).days
        return days_since_rotation > (self.rotation_days + 30)  # 30 day grace period
    
    def record_access(self, component: str) -> None:
        """Record secret access."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
        self.authorized_components.add(component)


class SecretEncryption:
    """Handle secret encryption/decryption."""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize with master key for encryption."""
        if master_key:
            self._fernet = self._create_fernet_from_key(master_key)
        else:
            # Generate key from environment or create new one
            self._fernet = self._create_fernet_from_env()
    
    def _create_fernet_from_key(self, master_key: str) -> Fernet:
        """Create Fernet instance from master key."""
        key_bytes = master_key.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'netra_salt_2024',  # In production, use random salt per secret
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key)
    
    def _create_fernet_from_env(self) -> Fernet:
        """Create Fernet instance from environment variable."""
        fernet_key = os.environ.get("FERNET_KEY")
        if fernet_key:
            return Fernet(fernet_key.encode())
        else:
            # Generate new key (development only)
            logger.warning("No FERNET_KEY found, generating new key for development")
            return Fernet(Fernet.generate_key())
    
    def encrypt_secret(self, secret_value: str) -> str:
        """Encrypt a secret value."""
        return self._fernet.encrypt(secret_value.encode()).decode()
    
    def decrypt_secret(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        return self._fernet.decrypt(encrypted_value.encode()).decode()


class EnhancedSecretManager:
    """Enhanced secret manager with security controls."""
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        self.environment = environment
        self.encryption = SecretEncryption()
        self.secrets: Dict[str, str] = {}
        self.metadata: Dict[str, SecretMetadata] = {}
        self.access_log: List[Dict[str, Any]] = []
        
        # Load secrets based on environment
        self._load_secrets()
        
        # Security settings
        self.max_access_attempts = 5
        self.access_attempts: Dict[str, int] = {}
        self.blocked_components: Set[str] = set()
    
    def _load_secrets(self) -> None:
        """Load secrets based on environment configuration."""
        if self.environment == EnvironmentType.PRODUCTION:
            self._load_production_secrets()
        elif self.environment == EnvironmentType.STAGING:
            self._load_staging_secrets() 
        else:
            self._load_development_secrets()
    
    def _load_production_secrets(self) -> None:
        """Load production secrets from secure sources."""
        logger.info("Loading production secrets from Google Secret Manager")
        
        # Production secrets follow strict naming pattern: prod-*
        production_patterns = [
            "prod-database-password",
            "prod-api-key", 
            "prod-jwt-secret",
            "prod-encryption-key"
        ]
        
        for secret_name in production_patterns:
            try:
                # In production, this would use Google Secret Manager
                secret_value = self._get_from_secret_manager(secret_name)
                if secret_value:
                    self._register_secret(
                        secret_name, 
                        secret_value,
                        SecretAccessLevel.CRITICAL,
                        rotation_days=30  # Shorter rotation for production
                    )
            except Exception as e:
                logger.error(f"Failed to load production secret {secret_name}: {e}")
    
    def _load_staging_secrets(self) -> None:
        """Load staging secrets with staging- prefix."""
        logger.info("Loading staging secrets")
        
        staging_patterns = [
            "staging-database-password",
            "staging-api-key",
            "staging-jwt-secret"
        ]
        
        for secret_name in staging_patterns:
            try:
                secret_value = self._get_from_secret_manager(secret_name)
                if secret_value:
                    self._register_secret(
                        secret_name,
                        secret_value, 
                        SecretAccessLevel.RESTRICTED,
                        rotation_days=60
                    )
            except Exception as e:
                logger.warning(f"Failed to load staging secret {secret_name}: {e}")
    
    def _load_development_secrets(self) -> None:
        """Load development secrets with dev- prefix."""
        logger.info("Loading development secrets")
        
        # Development secrets from environment variables
        dev_secrets = {
            "dev-database-password": os.environ.get("DEV_DATABASE_PASSWORD", "dev_password_123"),
            "dev-api-key": os.environ.get("DEV_API_KEY", "dev_api_key_456"), 
            "dev-jwt-secret": os.environ.get("DEV_JWT_SECRET", "dev_jwt_secret_789"),
            "dev-encryption-key": os.environ.get("DEV_ENCRYPTION_KEY", "dev_encryption_key_012")
        }
        
        for secret_name, secret_value in dev_secrets.items():
            self._register_secret(
                secret_name,
                secret_value,
                SecretAccessLevel.INTERNAL,
                rotation_days=180  # Longer rotation for development
            )
    
    def _get_from_secret_manager(self, secret_name: str) -> Optional[str]:
        """Get secret from Google Secret Manager or environment."""
        # First try environment variable
        env_value = os.environ.get(secret_name.upper().replace("-", "_"))
        if env_value:
            return env_value
        
        # In production, this would integrate with Google Secret Manager
        # For now, return None to indicate secret not found
        logger.warning(f"Secret {secret_name} not found in environment")
        return None
    
    def _register_secret(self, name: str, value: str, access_level: SecretAccessLevel,
                        rotation_days: int = 90) -> None:
        """Register a secret with metadata."""
        # Encrypt the secret value
        encrypted_value = self.encryption.encrypt_secret(value)
        self.secrets[name] = encrypted_value
        
        # Create metadata
        metadata = SecretMetadata(name, access_level, self.environment, rotation_days)
        self.metadata[name] = metadata
        
        logger.info(f"Registered secret {name} with access level {access_level}")
    
    def get_secret(self, secret_name: str, component: str) -> Optional[str]:
        """Get a secret value with access control."""
        try:
            # Security checks
            self._validate_access(secret_name, component)
            
            # Check if secret exists
            if secret_name not in self.secrets:
                logger.warning(f"Secret {secret_name} not found")
                return None
            
            # Check if secret is expired
            metadata = self.metadata[secret_name]
            if metadata.is_expired:
                logger.error(f"Secret {secret_name} is expired and needs rotation")
                raise NetraSecurityException(
                    f"Secret {secret_name} is expired",
                    error_code="SECRET_EXPIRED"
                )
            
            # Decrypt and return secret
            encrypted_value = self.secrets[secret_name]
            secret_value = self.encryption.decrypt_secret(encrypted_value)
            
            # Record access
            metadata.record_access(component)
            self._log_access(secret_name, component, "SUCCESS")
            
            return secret_value
            
        except Exception as e:
            self._log_access(secret_name, component, f"FAILED: {e}")
            self._record_failed_attempt(component)
            raise
    
    def _validate_access(self, secret_name: str, component: str) -> None:
        """Validate component access to secret."""
        # Check if component is blocked
        if component in self.blocked_components:
            raise NetraSecurityException(
                f"Component {component} is blocked from accessing secrets",
                error_code="COMPONENT_BLOCKED"
            )
        
        # Check environment isolation
        if self.environment == EnvironmentType.PRODUCTION:
            if not secret_name.startswith("prod-"):
                raise NetraSecurityException(
                    f"Production environment cannot access non-production secret: {secret_name}",
                    error_code="ENVIRONMENT_VIOLATION"
                )
        
        # Check access attempts
        if self.access_attempts.get(component, 0) >= self.max_access_attempts:
            self.blocked_components.add(component)
            raise NetraSecurityException(
                f"Component {component} exceeded access attempts",
                error_code="TOO_MANY_ATTEMPTS"
            )
    
    def _log_access(self, secret_name: str, component: str, result: str) -> None:
        """Log secret access attempt."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "secret_name": secret_name,
            "component": component,
            "result": result,
            "environment": self.environment.value
        }
        self.access_log.append(log_entry)
        
        # Keep only last 1000 log entries
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]
    
    def _record_failed_attempt(self, component: str) -> None:
        """Record failed access attempt."""
        self.access_attempts[component] = self.access_attempts.get(component, 0) + 1
    
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate a secret with new value."""
        try:
            if secret_name not in self.secrets:
                logger.error(f"Cannot rotate non-existent secret: {secret_name}")
                return False
            
            # Encrypt new value
            encrypted_value = self.encryption.encrypt_secret(new_value)
            self.secrets[secret_name] = encrypted_value
            
            # Update metadata
            metadata = self.metadata[secret_name]
            metadata.last_rotated = datetime.utcnow()
            
            logger.info(f"Successfully rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_name}: {e}")
            return False
    
    def get_secrets_needing_rotation(self) -> List[str]:
        """Get list of secrets that need rotation."""
        return [
            name for name, metadata in self.metadata.items()
            if metadata.needs_rotation
        ]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring."""
        return {
            "total_secrets": len(self.secrets),
            "secrets_by_access_level": {
                level.value: sum(1 for m in self.metadata.values() if m.access_level == level)
                for level in SecretAccessLevel
            },
            "secrets_needing_rotation": len(self.get_secrets_needing_rotation()),
            "blocked_components": len(self.blocked_components),
            "total_access_attempts": sum(self.access_attempts.values()),
            "access_log_entries": len(self.access_log)
        }
    
    def cleanup_access_log(self, days_to_keep: int = 30) -> None:
        """Clean up old access log entries."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        self.access_log = [
            entry for entry in self.access_log
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_date
        ]
        
        logger.info(f"Cleaned up access log, kept {len(self.access_log)} entries")


# Global secret manager instance - initialized with environment detection
def create_secret_manager() -> EnhancedSecretManager:
    """Create secret manager based on environment."""
    env_name = os.environ.get("ENVIRONMENT", "development").lower()
    
    if env_name == "production":
        environment = EnvironmentType.PRODUCTION
    elif env_name == "staging":
        environment = EnvironmentType.STAGING
    else:
        environment = EnvironmentType.DEVELOPMENT
    
    return EnhancedSecretManager(environment)


# Global instance
enhanced_secret_manager = create_secret_manager()