"""Demo service for handling enterprise demonstration functionality.

This module re-exports the refactored demo service components.
"""

from netra_backend.app.services.demo import (
    DemoService,
    get_demo_service,
    INDUSTRY_FACTORS
)

# Re-export for backward compatibility
__all__ = ["DemoService", "get_demo_service", "INDUSTRY_FACTORS"]