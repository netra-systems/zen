"""PostgreSQL Manager - Minimal implementation for integration tests.

This module provides PostgreSQL management functionality as a compatibility layer.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Import the actual DatabaseManager and create an alias
from netra_backend.app.db.database_manager import DatabaseManager

# Compatibility alias for integration tests
PostgreSQLManager = DatabaseManager