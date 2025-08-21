"""
Auth Route Utilities
"""
import os
from typing import Optional
from app.clients.auth_client import auth_client
from app.config import settings


def get_explicit_frontend_url() -> Optional[str]:
    """Get explicit frontend URL from environment variable."""
    if frontend_url := os.getenv("FRONTEND_URL"):
        return frontend_url.rstrip('/')
    return None


def get_env_specific_frontend_url() -> str:
    """Get environment-specific frontend URL."""
    env = auth_client.detect_environment().value
    if env == "staging":
        return "https://app.staging.netrasystems.ai"
    elif env == "production":
        return "https://netrasystems.ai"
    return settings.frontend_url.rstrip('/')


def get_frontend_url_for_environment() -> str:
    """Get the appropriate frontend URL based on environment."""
    if explicit_url := get_explicit_frontend_url():
        return explicit_url
    return get_env_specific_frontend_url()