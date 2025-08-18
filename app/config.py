"""UNIFIED Configuration Management - Single Source of Truth

**CRITICAL: All configuration MUST use this unified system**

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related incidents  
- Value Impact: +$12K MRR from improved reliability
- Revenue Impact: Prevents data inconsistency losses

🔴 CRITICAL AUTH ARCHITECTURE WARNING:
- This config is for the MAIN BACKEND only
- Auth service has its OWN configuration
- Auth service runs SEPARATELY on port 8001
- NEVER add auth implementation config here
- Auth connection config goes in AUTH_SERVICE_URL env var

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md

**MANDATORY**: All configuration access MUST use this file.
Eliminates 110+ file duplications and ensures Enterprise reliability.
"""

# NEW: Import unified configuration system
from app.core.configuration.base import (
    get_unified_config, 
    reload_unified_config,
    validate_config_integrity,
    config_manager as unified_config_manager
)
from app.schemas.Config import AppConfig

# DEPRECATED: Old config manager - kept for backward compatibility only
try:
    from app.config_manager import ConfigManager as LegacyConfigManager
    _legacy_config_manager = LegacyConfigManager()
except ImportError:
    _legacy_config_manager = None

# PRIMARY: Unified configuration access (PREFERRED)
def get_config() -> AppConfig:
    """Get the unified application configuration.
    
    **PREFERRED METHOD**: Use this for all new code.
    Single source of truth for Enterprise reliability.
    """
    return get_unified_config()

def reload_config():
    """Reload the unified configuration (hot-reload capability)."""
    reload_unified_config()

def validate_configuration() -> tuple[bool, list]:
    """Validate configuration integrity for Enterprise customers."""
    return validate_config_integrity()

# BACKWARD COMPATIBILITY: Legacy access methods
config_manager = unified_config_manager  # Export unified manager
settings = get_config()  # Auto-load settings

# LEGACY FALLBACK: Only used if unified system fails
def get_legacy_config() -> AppConfig:
    """DEPRECATED: Legacy configuration access - use get_config() instead."""
    if _legacy_config_manager:
        return _legacy_config_manager.get_config()
    return get_config()  # Fallback to unified system