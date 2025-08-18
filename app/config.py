"""Simplified configuration management with validation and reduced circular dependencies.

Refactored into modular components for better maintainability and adherence to 300-line limit.

🔴 CRITICAL AUTH ARCHITECTURE WARNING:
- This config is for the MAIN BACKEND only
- Auth service has its OWN configuration
- Auth service runs SEPARATELY on port 8001
- NEVER add auth implementation config here
- Auth connection config goes in AUTH_SERVICE_URL env var

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""

from app.config_manager import ConfigManager
from app.schemas.Config import AppConfig

# Global configuration manager instance
_config_manager = ConfigManager()
config_manager = _config_manager  # Export for backward compatibility

# Convenient access functions
def get_config() -> AppConfig:
    """Get the current application configuration."""
    return _config_manager.get_config()

def reload_config():
    """Reload the configuration from environment."""
    _config_manager.reload_config()

# For backward compatibility
settings = get_config()