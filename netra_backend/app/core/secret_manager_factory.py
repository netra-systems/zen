"""
Secret manager factory and global instance creation.
Provides factory functions for creating secret managers based on environment.
"""

import os

from netra_backend.app.config import get_config
from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
from netra_backend.app.schemas.config_types import EnvironmentType


def create_secret_manager() -> EnhancedSecretManager:
    """Create secret manager based on environment."""
    config = get_config()
    env_name = getattr(config, 'environment', 'development').lower()
    
    environment = _get_environment_type(env_name)
    
    return EnhancedSecretManager(environment)


def _get_environment_type(env_name: str) -> EnvironmentType:
    """Get environment type from string."""
    if env_name == "production":
        return EnvironmentType.PRODUCTION
    elif env_name == "staging":
        return EnvironmentType.STAGING
    else:
        return EnvironmentType.DEVELOPMENT


# Global instance
enhanced_secret_manager = create_secret_manager()