"""Staging test base utilities."""

import os
from typing import Optional
# Use backend-specific isolated environment
try:
    from netra_backend.app.core.isolated_environment import get_env
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()

def get_staging_url() -> str:
    """Get staging URL."""
    return get_env().get("STAGING_URL", "https://staging.netrasystems.ai")

def get_staging_api_key() -> Optional[str]:
    """Get staging API key."""
    return get_env().get("STAGING_API_KEY")

class StagingTestBase:
    """Base class for staging tests."""
    
    def __init__(self):
        self.staging_url = get_staging_url()
        self.api_key = get_staging_api_key()
    
    def is_staging_available(self) -> bool:
        """Check if staging is available."""
        return bool(self.api_key)
