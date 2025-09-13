"""Configuration Service

⚠️  DEPRECATION WARNING - ISSUE #667 SSOT CONSOLIDATION ⚠️
This file contains DUPLICATE configuration functionality that will be removed in a future release.

CANONICAL SSOT LOCATION: netra_backend.app.core.configuration.base
USE THIS INSTEAD: from netra_backend.app.core.configuration.base import get_unified_config

Migration Guide:
1. Replace imports from this module with imports from netra_backend.app.core.configuration.base
2. Use get_unified_config() for configuration access instead of custom loaders
3. All environment access should go through the canonical SSOT patterns

Business Impact: Using deprecated duplicates creates technical debt and maintenance overhead.
This migration protects the $500K+ ARR Golden Path by consolidating to proven SSOT patterns.

ORIGINAL: Provides configuration management services.
"""

import logging
import warnings
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentConfigLoader:
    """Loads configuration from environment variables.

    DEPRECATED: Use netra_backend.app.core.configuration.base.get_unified_config() instead.
    """

    def __init__(self):
        # ISSUE #667: DEPRECATION WARNING for duplicate configuration service
        warnings.warn(
            "DEPRECATED: EnvironmentConfigLoader from netra_backend.app.services.configuration_service "
            "is a DUPLICATE. Use netra_backend.app.core.configuration.base.get_unified_config() instead. "
            "This duplicate will be removed in a future release. "
            "Migration guide: https://github.com/netra-development/netra-core-generation-1/issues/667",
            DeprecationWarning,
            stacklevel=2
        )
        self.config = {}
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment."""
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        return env.get_all()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration using DatabaseURLBuilder SSOT."""
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        
        env = get_env()
        builder = DatabaseURLBuilder(env.get_all())
        
        # Get database URL using SSOT pattern
        database_url = builder.get_url_for_environment()
        if not database_url:
            # Fallback for development/test environments
            database_url = builder.development.default_url
        
        return {
            'DATABASE_URL': database_url,
            'DATABASE_POOL_SIZE': 10
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        return {
            'REDIS_URL': 'redis://localhost:6379/0'
        }


class ConfigurationValidator:
    """Validates configuration settings."""
    
    @staticmethod
    def validate_database_config(config: Dict[str, Any]) -> bool:
        """Validate database configuration using DatabaseURLBuilder SSOT."""
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        
        # First check if DATABASE_URL key exists in config
        if 'DATABASE_URL' not in config:
            return False
        
        # Validate using DatabaseURLBuilder if environment is available
        try:
            env = get_env()
            builder = DatabaseURLBuilder(env.get_all())
            is_valid, error = builder.validate()
            return is_valid
        except Exception:
            # Fallback to basic validation if DatabaseURLBuilder fails
            database_url = config.get('DATABASE_URL', '')
            return bool(database_url and len(database_url) > 0)
    
    @staticmethod
    def validate_redis_config(config: Dict[str, Any]) -> bool:
        """Validate Redis configuration."""
        required_keys = ['REDIS_URL']
        for key in required_keys:
            if key not in config:
                return False
        return True


class ConfigurationManager:
    """Manages application configuration.

    DEPRECATION WARNING: This class is deprecated as part of Issue #667 SSOT remediation.
    Please migrate to netra_backend.app.core.configuration.base.UnifiedConfigManager
    for the Single Source of Truth configuration management.

    Migration Guide:
    - Replace: from netra_backend.app.services.configuration_service import ConfigurationManager
    - With: from netra_backend.app.core.configuration.base import UnifiedConfigManager
    - Use: get_config_value(key, default) instead of get_config(key, default)
    """

    def __init__(self):
        warnings.warn(
            "ConfigurationManager is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.UnifiedConfigManager instead. "
            "See migration guide for details.",
            DeprecationWarning,
            stacklevel=2
        )
        self.validator = ConfigurationValidator()
        self._config_cache: Dict[str, Any] = {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config_cache.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config_cache[key] = value
    
    def validate_config(self) -> bool:
        """Validate current configuration."""
        try:
            db_valid = self.validator.validate_database_config(self._config_cache)
            redis_valid = self.validator.validate_redis_config(self._config_cache)
            return db_valid and redis_valid
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# ============================================================================
# SSOT CONSOLIDATION COMPATIBILITY (Issue #667)
# ============================================================================

# Import the CANONICAL SSOT UnifiedConfigurationManager for consolidation
try:
    from netra_backend.app.core.configuration.base import (
        UnifiedConfigManager as SSotManager,
        config_manager as ssot_config_manager
    )
    
    class ConfigurationManagerBackwardCompat:
        """
        Backward compatibility wrapper for ConfigurationManager -> SSOT UnifiedConfigurationManager.
        Maintains the interface while delegating to the SSOT implementation.
        """
        
        def __init__(self):
            # Use CANONICAL SSOT global manager instance
            self._ssot_manager = ssot_config_manager
            self.validator = ConfigurationValidator()  # Keep original validator for compatibility
            self._config_cache = {}  # Compatibility cache
        
        def get_config(self, key: str, default: Any = None) -> Any:
            """Get configuration value using SSOT."""
            return self._ssot_manager.get(key, default)
        
        def set_config(self, key: str, value: Any) -> None:
            """Set configuration value using SSOT."""
            self._ssot_manager.set(key, value)
            # Also update compatibility cache
            self._config_cache[key] = value
        
        def validate_config(self) -> bool:
            """Validate configuration using SSOT."""
            validation_result = self._ssot_manager.validate_all_configurations()
            return validation_result.is_valid
    
    # Replace the original ConfigurationManager with compatibility wrapper
    _OriginalConfigurationManager = ConfigurationManager
    ConfigurationManager = ConfigurationManagerBackwardCompat
    
except ImportError as e:
    # Fallback to original implementation if SSOT not available
    # This allows graceful degradation during migration
    logger.warning(f"SSOT ConfigurationManager not available, using fallback: {e}")
    pass

# Alias for backward compatibility
ConfigurationService = ConfigurationManager