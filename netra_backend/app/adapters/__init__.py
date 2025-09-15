"""
Adapter Layer for Interface Migration

This module provides adapter classes to bridge interface differences
during the migration from legacy patterns to SSOT patterns.
"""

from .legacy_to_ssot_adapter import LegacyToSSOTAdapter

__all__ = ["LegacyToSSOTAdapter"]