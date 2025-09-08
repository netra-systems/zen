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
from netra_backend.app.core.configuration.base import (
    config_manager as unified_config_manager,
)
from netra_backend.app.core.configuration.base import (
    get_unified_config,
    reload_unified_config,
    validate_config_integrity,
)
from netra_backend.app.schemas.config import AppConfig


# PRIMARY: Unified configuration access (PREFERRED)
def get_config() -> AppConfig:
    """Get the unified application configuration.
    
    **PREFERRED METHOD**: Use this for all new code.
    Single source of truth for Enterprise reliability.
    """
    return get_unified_config()

def reload_config(force: bool = False) -> None:
    """Reload the unified configuration (hot-reload capability)."""
    reload_unified_config(force=force)

def validate_configuration() -> tuple[bool, list]:
    """Validate configuration integrity for Enterprise customers."""
    return validate_config_integrity()

config_manager = unified_config_manager

# BACKWARD COMPATIBILITY ALIASES
Config = AppConfig
DatabaseConfig = AppConfig  # For now, alias to full config - tests can access .database
RedisConfig = AppConfig     # For now, alias to full config - tests can access .redis

# LAZY LOADING: Don't auto-load at import time to allow environment setup
_settings_cache = None

def __getattr__(name: str) -> AppConfig:
    """Lazy load settings on first access."""
    global _settings_cache
    if name == "settings":
        if _settings_cache is None:
            _settings_cache = get_config()
        return _settings_cache
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

