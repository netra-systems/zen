"""
Startup management module for Netra AI platform.

Provides migration tracking, status persistence, and startup validation.
Addresses GAP-001 (CRITICAL) and GAP-005 (MEDIUM) from startup_coverage.xml.
"""

from .migration_tracker import MigrationTracker

__all__ = ["MigrationTracker"]