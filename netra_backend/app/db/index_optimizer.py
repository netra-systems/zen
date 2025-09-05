"""Database index optimization and management.

This module provides backward compatibility wrapper for the new modular 
database index optimization system with proper async/await handling.
"""

from typing import Any, Dict, List

from netra_backend.app.db.clickhouse_index_optimizer import ClickHouseIndexOptimizer

# Import from new modular structure
from netra_backend.app.db.index_optimizer_core import IndexRecommendation
from netra_backend.app.db.postgres_index_optimizer import PostgreSQLIndexOptimizer
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseIndexManager:
    """Simplified database index manager for startup compatibility."""
    
    def __init__(self):
        self.postgres_optimizer = PostgreSQLIndexOptimizer()
        self.clickhouse_optimizer = ClickHouseIndexOptimizer()
        logger.info("DatabaseIndexManager initialized")
    
    async def optimize_all_databases(self):
        """Optimize indexes for all databases."""
        try:
            # Run optimizations in parallel
            import asyncio
            results = await asyncio.gather(
                self.postgres_optimizer.optimize(),
                self.clickhouse_optimizer.optimize(),
                return_exceptions=True
            )
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    db_name = ["PostgreSQL", "ClickHouse"][i]
                    logger.warning(f"Index optimization failed for {db_name}: {result}")
                    
            logger.info("Database index optimization completed")
        except Exception as e:
            logger.error(f"Failed to optimize database indexes: {e}")


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