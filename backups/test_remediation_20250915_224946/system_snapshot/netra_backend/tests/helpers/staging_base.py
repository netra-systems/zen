"""Staging test base utilities."""

from typing import Optional

from shared.isolated_environment import get_env

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
