"""
Auth Route Utilities
"""
from typing import Optional

from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.configuration import unified_config_manager


def get_explicit_frontend_url() -> Optional[str]:
    """Get explicit frontend URL from unified config."""
    config = unified_config_manager.get_config()
    frontend_url = getattr(config, 'frontend_url', None)
    if frontend_url:
        return frontend_url.rstrip('/')
    return None


def get_env_specific_frontend_url() -> str:
    """Get environment-specific frontend URL."""
    env = auth_client.detect_environment().value
    if env == "staging":
        return "https://app.staging.netrasystems.ai"
    elif env == "production":
        return "https://netrasystems.ai"
    config = unified_config_manager.get_config()
    return getattr(config, 'frontend_url', 'http://localhost:3000').rstrip('/')


def get_frontend_url_for_environment() -> str:
    """Get the appropriate frontend URL based on environment."""
    if explicit_url := get_explicit_frontend_url():
        return explicit_url
    return get_env_specific_frontend_url()