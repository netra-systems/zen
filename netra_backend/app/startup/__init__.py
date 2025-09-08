"""
Startup management module for Netra AI platform.

Provides migration tracking, status persistence, and startup validation.
Addresses GAP-001 (CRITICAL) and GAP-005 (MEDIUM) from startup_coverage.xml.
"""

from netra_backend.app.startup.error_aggregator import ErrorAggregator, error_aggregator
from netra_backend.app.startup.migration_models import FailedMigration, MigrationState
# from netra_backend.app.startup.migration_state_manager import MigrationStateManager  # Module not found
from netra_backend.app.startup.migration_tracker import MigrationTracker
from netra_backend.app.startup.status_manager import (
    StartupStatusManager,
    startup_status_manager,
)

__all__ = [
    "MigrationTracker", "FailedMigration", "MigrationState",  # "MigrationStateManager",
    "ErrorAggregator", "error_aggregator", "StartupStatusManager", "startup_status_manager"
]