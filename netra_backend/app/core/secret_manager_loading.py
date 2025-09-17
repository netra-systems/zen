"""
Secret loading functionality for different environments.
Handles loading secrets from various sources based on environment.
"""

import os
from typing import Dict, List, Optional

from netra_backend.app.config import get_config
from netra_backend.app.core.secret_manager_types import SecretAccessLevel
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.config_types import EnvironmentType

logger = central_logger.get_logger(__name__)


class SecretLoader:
    """Handles loading secrets from different sources based on environment."""
    
    def __init__(self, secret_manager):
        """Initialize with reference to main secret manager."""
        self.secret_manager = secret_manager
        self._config = get_config()
    
    def load_secrets(self) -> None:
        """Load secrets based on environment configuration."""
        if self.secret_manager.environment == EnvironmentType.PRODUCTION:
            self._load_production_secrets()
        elif self.secret_manager.environment == EnvironmentType.STAGING:
            self._load_staging_secrets() 
        else:
            self._load_development_secrets()
    
    def _load_production_secrets(self) -> None:
        """Load production secrets from secure sources."""
        logger.info("Loading production secrets from Google Secret Manager")
        
        production_patterns = self._get_production_patterns()
        self._load_secrets_by_patterns(production_patterns, SecretAccessLevel.CRITICAL, 30)
    
    def _load_staging_secrets(self) -> None:
        """Load staging secrets with staging- prefix."""
        logger.info("Loading staging secrets")
        
        staging_patterns = self._get_staging_patterns()
        self._load_secrets_by_patterns(staging_patterns, SecretAccessLevel.RESTRICTED, 60)
    
    def _load_development_secrets(self) -> None:
        """Load development secrets with dev- prefix."""
        logger.info("Loading development secrets")
        
        dev_secrets = self._get_development_secrets()
        self._register_development_secrets(dev_secrets)
    
    def get_from_secret_manager(self, secret_name: str) -> Optional[str]:
        """Get secret from Google Secret Manager or environment."""
        env_value = self._get_from_environment(secret_name)
        if env_value:
            return env_value
        
        self._log_secret_not_found(secret_name)
        return None
    
    def _get_production_patterns(self) -> List[str]:
        """Get production secret name patterns."""
        return [
            "prod-database-password",
            "prod-api-key", 
            "prod-jwt-secret",
            "prod-encryption-key"
        ]
    
    def _get_staging_patterns(self) -> List[str]:
        """Get staging secret name patterns."""
        return [
            "staging-database-password",
            "staging-api-key",
            "staging-jwt-secret"
        ]
    
    def _get_development_secrets(self) -> Dict[str, str]:
        """Get development secrets from environment variables."""
        return {
            "dev-database-password": getattr(self._config, 'dev_database_password', "dev_password_123"),
            "dev-api-key": getattr(self._config, 'dev_api_key', "dev_api_key_456"), 
            "dev-jwt-secret": getattr(self._config, 'dev_jwt_secret', "dev_jwt_secret_789"),
            "dev-encryption-key": getattr(self._config, 'dev_encryption_key', "dev_encryption_key_012")
        }
    
    def _load_secrets_by_patterns(self, patterns: List[str], access_level: SecretAccessLevel, rotation_days: int) -> None:
        """Load secrets by name patterns."""
        for secret_name in patterns:
            try:
                secret_value = self.get_from_secret_manager(secret_name)
                if secret_value:
                    self._register_secret_value(secret_name, secret_value, access_level, rotation_days)
            except Exception as e:
                self._log_secret_load_error(secret_name, e, access_level)
    
    def _register_development_secrets(self, dev_secrets: Dict[str, str]) -> None:
        """Register development secrets."""
        for secret_name, secret_value in dev_secrets.items():
            self.secret_manager._register_secret(
                secret_name,
                secret_value,
                SecretAccessLevel.INTERNAL,
                rotation_days=180  # Longer rotation for development
            )
    
    def _get_from_environment(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variable."""
        attr_name = secret_name.lower().replace("-", "_")
        return getattr(self._config, attr_name, None)
    
    def _log_secret_not_found(self, secret_name: str) -> None:
        """Log when secret is not found."""
        logger.warning(f"Secret {secret_name} not found in environment")
    
    def _register_secret_value(self, secret_name: str, secret_value: str, access_level: SecretAccessLevel, rotation_days: int) -> None:
        """Register a secret value with the secret manager."""
        self.secret_manager._register_secret(
            secret_name, 
            secret_value,
            access_level,
            rotation_days=rotation_days
        )
    
    def _log_secret_load_error(self, secret_name: str, error: Exception, access_level: SecretAccessLevel) -> None:
        """Log secret loading error."""
        if access_level == SecretAccessLevel.CRITICAL:
            logger.error(f"Failed to load production secret {secret_name}: {error}")
        else:
            logger.warning(f"Failed to load staging secret {secret_name}: {error}")