"""Staging test base utilities."""

import os
from typing import Optional


def get_staging_url() -> str:
    """Get staging URL."""
    return os.getenv("STAGING_URL", "https://staging.netra.ai")

def get_staging_api_key() -> Optional[str]:
    """Get staging API key."""
    return os.getenv("STAGING_API_KEY")

class StagingTestBase:
    """Base class for staging tests."""
    
    def __init__(self):
        self.staging_url = get_staging_url()
        self.api_key = get_staging_api_key()
    
    def is_staging_available(self) -> bool:
        """Check if staging is available."""
        return bool(self.api_key)
