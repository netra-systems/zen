"""
Supply Researcher Agent - Legacy Compatibility Module

This module maintains backward compatibility while delegating to the new
modular supply_researcher package. All functionality has been moved to focused
modules under 300 lines each.
"""

# Import from modular implementation
from netra_backend.app.supply_researcher import (
    SupplyResearcherAgent,
    ResearchType
)

# Maintain backward compatibility - all legacy code removed
# All classes and functions now imported from supply_researcher module

__all__ = [
    "SupplyResearcherAgent",
    "ResearchType"
]