"""Configuration module - Unified configuration management.

This module provides centralized configuration access for the Netra backend application.
All configuration imports should go through this module.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Provides single source of truth for configuration access
- Strategic Impact: Foundation for consistent configuration management
"""

# Import the unified configuration manager and functions
from netra_backend.app.core.configuration.base import (
    config_manager as unified_config_manager,
    get_unified_config,
    reload_unified_config,
    validate_config_integrity,
    UnifiedConfigManager,
)

# Import configuration loader and validator
from netra_backend.app.core.configuration.loader import ConfigurationLoader
from netra_backend.app.core.configuration.validator import ConfigurationValidator

# Alias for backward compatibility
def get_configuration():
    """Get configuration - alias for get_unified_config for backward compatibility."""
    return get_unified_config()

# Export main components
__all__ = [
    "unified_config_manager",
    "get_unified_config", 
    "get_configuration",
    "reload_unified_config",
    "validate_config_integrity",
    "UnifiedConfigManager",
    "ConfigurationLoader",
    "ConfigurationValidator",
]