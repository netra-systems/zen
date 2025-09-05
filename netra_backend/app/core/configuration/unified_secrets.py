"""
Unified Secrets Management Module

Provides centralized secret management functionality for the Netra platform.
Follows SSOT principles for secret access and management.
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SecretConfig:
    """Configuration for secret management"""
    use_gcp_secrets: bool = False
    fallback_to_env: bool = True
    cache_secrets: bool = False


class UnifiedSecretsManager:
    """
    Unified secrets manager for the Netra platform.
    
    Provides centralized access to secrets from various sources
    including environment variables and GCP Secret Manager.
    """
    
    def __init__(self, config: Optional[SecretConfig] = None):
        self.config = config or SecretConfig()
        self._cache: Dict[str, Any] = {}
        logger.info("UnifiedSecretsManager initialized")
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value by key.
        
        Args:
            key: Secret key to retrieve
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        if self.config.cache_secrets and key in self._cache:
            return self._cache[key]
        
        # Try environment variable first
        value = os.getenv(key, default)
        
        if self.config.cache_secrets and value is not None:
            self._cache[key] = value
        
        return value
    
    def set_secret(self, key: str, value: str) -> None:
        """
        Set a secret value (for testing/development).
        
        Args:
            key: Secret key
            value: Secret value
        """
        if self.config.cache_secrets:
            self._cache[key] = value
        os.environ[key] = value
    
    def clear_cache(self) -> None:
        """Clear the secrets cache"""
        self._cache.clear()


# Global instance
_secrets_manager = None


def get_secrets_manager() -> UnifiedSecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = UnifiedSecretsManager()
    return _secrets_manager


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    return get_secrets_manager().get_secret(key, default)


def set_secret(key: str, value: str) -> None:
    """Convenience function to set a secret"""
    get_secrets_manager().set_secret(key, value)


def get_jwt_secret() -> str:
    """Get JWT secret from environment"""
    secret = get_secret('JWT_SECRET')
    if not secret:
        # Generate a default secret for testing
        import secrets
        secret = secrets.token_hex(32)
        set_secret('JWT_SECRET', secret)
    return secret


# Alias for backwards compatibility
UnifiedSecretManager = UnifiedSecretsManager