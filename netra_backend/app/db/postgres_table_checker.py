"""PostgreSQL table existence checker.

Validates table existence before index creation.
"""

from typing import Set

from sqlalchemy import text

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PostgreSQLTableChecker:
    """Check table existence in PostgreSQL."""
    
    def __init__(self):
        self._cached_tables: Set[str] = set()
        self._cache_loaded = False
    
    async def load_existing_tables(self, session) -> Set[str]:
        """Load existing tables from database."""
        try:
            query = text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            result = await session.execute(query)
            tables = {row[0] for row in result.fetchall()}
            self._cached_tables = tables
            self._cache_loaded = True
            logger.debug(f"Loaded {len(tables)} existing tables")
            return tables
        except Exception as e:
            logger.error(f"Error loading tables: {e}")
            return set()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in cache."""
        if not self._cache_loaded:
            logger.warning("Table cache not loaded")
            return False
        return table_name in self._cached_tables
    
    def get_missing_tables(self, required_tables: Set[str]) -> Set[str]:
        """Get list of missing tables."""
        if not self._cache_loaded:
            return required_tables
        return required_tables - self._cached_tables