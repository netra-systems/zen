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
    
    def get_jwt_secret(self) -> str:
        """
        Get JWT secret using the unified JWT secret manager for consistency.
        
        CRITICAL FIX: Now delegates to shared.jwt_secret_manager to ensure
        consistency with auth service. This fixes the WebSocket 403 authentication
        failures caused by JWT secret mismatches between services.
        
        The unified manager ensures IDENTICAL secret resolution logic across
        all services, preventing authentication issues.
        
        Raises:
            ValueError: If no JWT secret is configured for production environment
            
        Returns:
            JWT secret string, properly stripped of whitespace
        """
        try:
            # Use the unified JWT secret manager for consistency across all services
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            logger.debug("Using unified JWT secret manager for consistent secret resolution")
            return secret
        except Exception as e:
            logger.error(f"Failed to use unified JWT secret manager: {e}")
            logger.warning("Falling back to local JWT secret resolution")
            
            # Fallback to local resolution if unified manager fails
            environment = self.get_secret('ENVIRONMENT', 'development').lower()
            
            # 1. Try environment-specific secret first
            env_specific_key = f"JWT_SECRET_{environment.upper()}"
            secret = self.get_secret(env_specific_key)
            if secret:
                logger.debug(f"Fallback: Using environment-specific JWT secret: {env_specific_key}")
                return secret.strip()
            
            # 2. Try generic JWT_SECRET_KEY
            secret = self.get_secret('JWT_SECRET_KEY')
            if secret:
                logger.debug("Fallback: Using generic JWT_SECRET_KEY")
                return secret.strip()
            
            # 3. Try legacy JWT_SECRET
            secret = self.get_secret('JWT_SECRET')
            if secret:
                logger.warning("Fallback: Using legacy JWT_SECRET (DEPRECATED)")
                return secret.strip()
            
            # 4. Development fallback
            if environment == 'development':
                logger.warning("Fallback: Using development default JWT secret")
                return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
            
            # 5. Production/staging validation - must have explicit secret
            if environment in ['production', 'staging']:
                logger.critical(f"JWT secret not configured for {environment} environment")
                raise ValueError(f"JWT secret not configured for {environment} environment")
            
            # 6. Default fallback for other environments
            logger.warning(f"Fallback: Using default JWT secret for {environment} environment")
            return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"


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
    """Get JWT secret using the global secrets manager"""
    return get_secrets_manager().get_jwt_secret()


# Alias for backwards compatibility
UnifiedSecretManager = UnifiedSecretsManager