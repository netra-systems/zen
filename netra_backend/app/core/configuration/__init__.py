"""Configuration module - Unified configuration management.

This module provides centralized configuration access for the Netra backend application.
All configuration imports should go through this module.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Provides single source of truth for configuration access
- Strategic Impact: Foundation for consistent configuration management

SSOT COMPATIBILITY BRIDGE - Issue #667 Phase 1:
Provides backwards-compatible imports during gradual migration to single configuration manager.
Protects $500K+ ARR by maintaining Golden Path functionality during consolidation.
"""

from typing import Any, Optional

# Import the SSOT unified configuration manager and functions
# NOTE: These imports are delayed to avoid circular dependencies
def get_unified_config():
    """Get unified config - lazy import to avoid circular dependency."""
    from netra_backend.app.config import get_config
    return get_config()

def get_config():
    """Get config - lazy import to avoid circular dependency."""
    from netra_backend.app.config import get_config as _get_config
    return _get_config()

def reload_unified_config():
    """Reload config - lazy import to avoid circular dependency."""
    from netra_backend.app.config import reload_config
    return reload_config()

def validate_config_integrity():
    """Validate config - lazy import to avoid circular dependency."""
    from netra_backend.app.config import validate_configuration
    return validate_configuration()

class UnifiedConfigManager:
    """Lazy proxy for UnifiedConfigManager to avoid circular imports."""
    def __new__(cls, *args, **kwargs):
        from netra_backend.app.config import UnifiedConfigManager as _UnifiedConfigManager
        return _UnifiedConfigManager(*args, **kwargs)

# Lazy proxy for config_manager
class _ConfigManagerProxy:
    def __getattr__(self, name):
        from netra_backend.app.config import config_manager
        return getattr(config_manager, name)

unified_config_manager = _ConfigManagerProxy()

# Import configuration loader and validator
from netra_backend.app.core.configuration.loader import ConfigurationLoader
from netra_backend.app.core.configuration.validator import ConfigurationValidator

# SSOT Configuration Access Functions
def get_configuration():
    """Get configuration - SSOT alias for get_unified_config."""
    return get_unified_config()

# ============================================================================
# PHASE 1 COMPATIBILITY BRIDGE - Issue #667
# ============================================================================

# DEPRECATED: Backwards compatibility aliases for gradual migration
# These redirect to the SSOT UnifiedConfigManager until Phase 5 removal

# Compatibility for UnifiedConfigurationManager (from managers/)
UnifiedConfigurationManager = UnifiedConfigManager

# Compatibility for ConfigurationManager (from services/)
ConfigurationManager = UnifiedConfigManager

def get_configuration_manager(user_id: Optional[str] = None, **kwargs) -> UnifiedConfigManager:
    """SSOT factory for configuration management.

    Compatibility bridge for factory pattern during migration.
    All parameters except user_id are ignored in Phase 1 for simplicity.

    Args:
        user_id: User ID for potential future user-specific configs (unused in Phase 1)
        **kwargs: Additional arguments (ignored for compatibility)

    Returns:
        UnifiedConfigManager: The SSOT configuration manager
    """
    return UnifiedConfigManager()

# ============================================================================
# ENHANCED SSOT API COMPATIBILITY
# ============================================================================

def get_polymorphic_config(key: Optional[str] = None, default: Any = None):
    """Polymorphic get_config function supporting both signatures.

    Supports two calling patterns:
    - get_config() -> AppConfig (Golden Path pattern)
    - get_config(key: str, default: Any) -> Any (legacy pattern)

    Args:
        key: Configuration key (None for full AppConfig)
        default: Default value if key not found

    Returns:
        AppConfig if key is None, otherwise specific config value
    """
    if key is None:
        # Golden Path pattern: return full AppConfig
        return get_unified_config()
    else:
        # Legacy pattern: return specific value
        config = get_unified_config()
        # Simple dot notation parsing for compatibility
        keys = key.split('.')
        value = config
        try:
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default
            return value
        except (AttributeError, TypeError):
            return default

# SSOT validation (delayed to avoid circular imports)
def _validate_ssot():
    """Validate SSOT configuration system."""
    from netra_backend.app.config import UnifiedConfigManager as _UnifiedConfigManager, get_config as _get_config
    assert hasattr(_UnifiedConfigManager, 'get_config'), "SSOT config manager missing get_config method"
    assert callable(_get_config), "SSOT get_config function not callable"

# Defer validation to avoid circular import during module loading
import atexit
atexit.register(_validate_ssot)

# Export all components including compatibility bridge
__all__ = [
    # SSOT Exports
    "unified_config_manager",
    "get_unified_config",
    "get_config",  # Golden Path SSOT
    "get_configuration",
    "reload_unified_config",
    "validate_config_integrity",
    "UnifiedConfigManager",  # SSOT class
    "ConfigurationLoader",
    "ConfigurationValidator",
    "get_configuration_manager",  # SSOT factory
    "get_polymorphic_config",  # Enhanced compatibility

    # DEPRECATED: Phase 1 compatibility (remove in Phase 5)
    "UnifiedConfigurationManager",  # Alias to SSOT
    "ConfigurationManager",         # Alias to SSOT
]