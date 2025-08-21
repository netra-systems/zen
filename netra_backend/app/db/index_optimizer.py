"""Database index optimization and management.

This module provides backward compatibility wrapper for the new modular 
database index optimization system with proper async/await handling.
"""

from typing import Any, Dict, List

from netra_backend.app.db.clickhouse_index_optimizer import ClickHouseIndexOptimizer
from netra_backend.app.db.database_index_manager import DatabaseIndexManager

# Import from new modular structure
from netra_backend.app.db.index_optimizer_core import IndexRecommendation
from netra_backend.app.db.postgres_index_optimizer import PostgreSQLIndexOptimizer
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Backward compatibility exports
__all__ = [
    'IndexRecommendation',
    'PostgreSQLIndexOptimizer', 
    'ClickHouseIndexOptimizer',
    'DatabaseIndexManager',
    'index_manager'
]

# Global instance for backward compatibility
index_manager = DatabaseIndexManager()