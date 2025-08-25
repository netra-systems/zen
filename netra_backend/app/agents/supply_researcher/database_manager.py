"""
DEPRECATED: Supply Database Manager - Use DatabaseManager instead

CRITICAL: This module is deprecated to eliminate SSOT violations.
All database operations now consolidated in DatabaseManager.
"""

# SINGLE SOURCE OF TRUTH: Import from canonical DatabaseManager
from netra_backend.app.db.database_manager import SupplyDatabaseManager

# For backwards compatibility, re-export the class
__all__ = ["SupplyDatabaseManager"]