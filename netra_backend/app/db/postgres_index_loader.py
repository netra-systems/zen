"""PostgreSQL Index Loading and Performance Analysis

Loading existing indexes and analyzing query performance.
"""

from typing import List, Set, Tuple

from sqlalchemy import text

from netra_backend.app.db.index_optimizer_core import IndexRecommendation
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PostgreSQLIndexLoader:
    """Load existing PostgreSQL indexes."""
    
    async def _execute_index_query(self, session) -> Set[str]:
        """Execute query to get existing indexes."""
        query = text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        result = await session.execute(query)
        return {row[0] for row in result.fetchall()}
    
    async def load_existing_indexes(self, session) -> Set[str]:
        """Load existing database indexes."""
        try:
            indexes = await self._execute_index_query(session)
            logger.debug(f"Loaded {len(indexes)} existing indexes")
            return indexes
        except Exception as e:
            logger.error(f"Error loading existing indexes: {e}")
            return set()


class PostgreSQLPerformanceAnalyzer:
    """Analyze PostgreSQL query performance."""
    
    def __init__(self):
        from netra_backend.app.db.postgres_query_analyzer import (
            PostgreSQLRecommendationProvider,
            PostgreSQLSlowQueryAnalyzer,
        )
        self.slow_query_analyzer = PostgreSQLSlowQueryAnalyzer()
        self.recommendation_provider = PostgreSQLRecommendationProvider()
    
    async def get_slow_queries(self, session) -> List[Tuple]:
        """Get slow queries from pg_stat_statements."""
        return await self.slow_query_analyzer.get_slow_queries(session)
    
    def analyze_query_for_recommendations(self, query_data: Tuple) -> List[IndexRecommendation]:
        """Analyze query and generate recommendations."""
        return self.slow_query_analyzer.analyze_single_query(query_data)