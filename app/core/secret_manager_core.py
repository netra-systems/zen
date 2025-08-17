"""
Core enhanced secret manager functionality.
Main secret management with access control and security features.
"""

from typing import Dict, Optional, Any, List, Set
from datetime import datetime, timedelta, timezone

from app.logging_config import central_logger
from app.core.exceptions_auth import NetraSecurityException
from app.schemas.config_types import EnvironmentType
from app.core.secret_manager_types import SecretAccessLevel, SecretMetadata
from app.core.secret_manager_encryption import SecretEncryption
from app.core.secret_manager_loading import SecretLoader
from app.core.secret_manager_auth import SecretManagerAuth

logger = central_logger.get_logger(__name__)


class EnhancedSecretManager:
    """Enhanced secret manager with security controls."""
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        self.environment = environment
        self.encryption = SecretEncryption()
        self.secrets: Dict[str, str] = {}
        self.metadata: Dict[str, SecretMetadata] = {}
        self.access_log: List[Dict[str, Any]] = []
        
        # Initialize components
        self.loader = SecretLoader(self)
        self.auth = SecretManagerAuth(self)
        
        # Load secrets based on environment
        self.loader.load_secrets()
        
        # Security settings
        self._initialize_security_settings()
    
    def get_secret(self, secret_name: str, component: str) -> Optional[str]:
        """Get a secret value with access control."""
        try:
            self._validate_access(secret_name, component)
            
            if not self._secret_exists(secret_name):
                self._raise_secret_not_found(secret_name)
            
            self._check_secret_expiry(secret_name)
            
            return self._decrypt_and_log_access(secret_name, component)
            
        except Exception as e:
            self._handle_access_failure(secret_name, component, e)
            raise
    
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate a secret with new value."""
        try:
            if not self._can_rotate_secret(secret_name):
                return False
            
            self._update_secret_value(secret_name, new_value)
            self._update_rotation_metadata(secret_name)
            
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
            "secrets_by_access_level": self._get_secrets_by_level(),
            "secrets_needing_rotation": len(self.get_secrets_needing_rotation()),
            "blocked_components": len(self.blocked_components),
            "total_access_attempts": sum(self.access_attempts.values()),
            "access_log_entries": len(self.access_log)
        }
    
    def cleanup_access_log(self, days_to_keep: int = 30) -> None:
        """Clean up old access log entries."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        self.access_log = self._filter_recent_logs(cutoff_date)
        
        logger.info(f"Cleaned up access log, kept {len(self.access_log)} entries")
    
    def _register_secret(self, name: str, value: str, access_level: SecretAccessLevel,
                        rotation_days: int = 90) -> None:
        """Register a secret with metadata."""
        encrypted_value = self.encryption.encrypt_secret(value)
        self.secrets[name] = encrypted_value
        
        metadata = SecretMetadata(name, access_level, self.environment, rotation_days)
        self.metadata[name] = metadata
        
        logger.info(f"Registered secret {name} with access level {access_level}")
    
    def _initialize_security_settings(self) -> None:
        """Initialize security settings."""
        self.max_access_attempts = 5
        self.access_attempts: Dict[str, int] = {}
        self.blocked_components: Set[str] = set()
    
    def _validate_access(self, secret_name: str, component: str) -> None:
        """Validate component access to secret."""
        self._check_component_blocked(component)
        self._check_environment_isolation(secret_name)
        self._check_access_attempts(component)
    
    def _secret_exists(self, secret_name: str) -> bool:
        """Check if secret exists."""
        return secret_name in self.secrets
    
    def _raise_secret_not_found(self, secret_name: str) -> None:
        """Raise exception for secret not found."""
        logger.warning(f"Secret {secret_name} not found")
        raise NetraSecurityException(message=f"Secret {secret_name} not found")
    
    def _check_secret_expiry(self, secret_name: str) -> None:
        """Check if secret is expired."""
        metadata = self.metadata[secret_name]
        if metadata.is_expired:
            logger.error(f"Secret {secret_name} is expired and needs rotation")
            raise NetraSecurityException(message=f"Secret {secret_name} is expired")
    
    def _decrypt_and_log_access(self, secret_name: str, component: str) -> str:
        """Decrypt secret and log access."""
        encrypted_value = self.secrets[secret_name]
        secret_value = self.encryption.decrypt_secret(encrypted_value)
        
        metadata = self.metadata[secret_name]
        metadata.record_access(component)
        self._log_access(secret_name, component, "SUCCESS")
        
        return secret_value
    
    def _handle_access_failure(self, secret_name: str, component: str, error: Exception) -> None:
        """Handle failed access attempt."""
        self._log_access(secret_name, component, f"FAILED: {error}")
        self._record_failed_attempt(component)
    
    def _can_rotate_secret(self, secret_name: str) -> bool:
        """Check if secret can be rotated."""
        if secret_name not in self.secrets:
            logger.error(f"Cannot rotate non-existent secret: {secret_name}")
            return False
        return True
    
    def _update_secret_value(self, secret_name: str, new_value: str) -> None:
        """Update secret value with encryption."""
        encrypted_value = self.encryption.encrypt_secret(new_value)
        self.secrets[secret_name] = encrypted_value
    
    def _update_rotation_metadata(self, secret_name: str) -> None:
        """Update rotation metadata."""
        metadata = self.metadata[secret_name]
        metadata.last_rotated = datetime.now(timezone.utc)
    
    def _get_secrets_by_level(self) -> Dict[str, int]:
        """Get secrets count by access level."""
        return {
            level.value: sum(1 for m in self.metadata.values() if m.access_level == level)
            for level in SecretAccessLevel
        }
    
    def _filter_recent_logs(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Filter access logs to keep only recent entries."""
        return [
            entry for entry in self.access_log
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_date
        ]
    
    def _check_component_blocked(self, component: str) -> None:
        """Check if component is blocked."""
        if component in self.blocked_components:
            raise NetraSecurityException(
                message=f"Component {component} is blocked from accessing secrets"
            )
    
    def _check_environment_isolation(self, secret_name: str) -> None:
        """Check environment isolation rules."""
        if self.environment == EnvironmentType.PRODUCTION:
            if not secret_name.startswith("prod-"):
                raise NetraSecurityException(
                    message=f"Production environment cannot access non-production secret: {secret_name}"
                )
    
    def _check_access_attempts(self, component: str) -> None:
        """Check if component exceeded access attempts."""
        if self.access_attempts.get(component, 0) >= self.max_access_attempts:
            self.blocked_components.add(component)
            raise NetraSecurityException(
                message=f"Component {component} exceeded access attempts"
            )
    
    def _log_access(self, secret_name: str, component: str, result: str) -> None:
        """Log secret access attempt."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "secret_name": secret_name,
            "component": component,
            "result": result,
            "environment": self.environment.value
        }
        self.access_log.append(log_entry)
        
        self._maintain_log_size()
    
    def _maintain_log_size(self) -> None:
        """Maintain access log size."""
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]
    
    def _record_failed_attempt(self, component: str) -> None:
        """Record failed access attempt."""
        self.access_attempts[component] = self.access_attempts.get(component, 0) + 1