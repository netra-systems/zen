"""
Startup management module for Netra AI platform.

Provides migration tracking, status persistence, and startup validation.
Addresses GAP-001 (CRITICAL) and GAP-005 (MEDIUM) from startup_coverage.xml.
"""

from .migration_tracker import MigrationTracker
from .migration_models import FailedMigration, MigrationState
from .migration_state_manager import MigrationStateManager
from .error_aggregator import ErrorAggregator, error_aggregator
from .status_manager import StartupStatusManager, startup_status_manager

__all__ = [
    "MigrationTracker", "FailedMigration", "MigrationState", "MigrationStateManager",
    "ErrorAggregator", "error_aggregator", "StartupStatusManager", "startup_status_manager"
]