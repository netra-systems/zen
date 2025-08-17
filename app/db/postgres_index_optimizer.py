"""PostgreSQL index optimization and management.

Main PostgreSQL index optimizer with modular architecture.
"""

from typing import Dict, List, Any
from sqlalchemy import text

from app.logging_config import central_logger
from app.db.postgres import get_async_db, async_engine
from app.db.index_optimizer_core import (
    IndexRecommendation,
    DatabaseValidation,
    IndexNameGenerator,
    DatabaseErrorHandler
)
from .postgres_index_creator import PostgreSQLIndexCreator
from .postgres_index_loader import PostgreSQLIndexLoader, PostgreSQLPerformanceAnalyzer

logger = central_logger.get_logger(__name__)


class PostgreSQLIndexOptimizer:
    """PostgreSQL index optimization and management."""
    
    def __init__(self):
        self.index_creator = PostgreSQLIndexCreator()
        self.index_loader = PostgreSQLIndexLoader()
        self.performance_analyzer = PostgreSQLPerformanceAnalyzer()
        self._setup_performance_indexes()
    
    def _setup_performance_indexes(self):
        """Setup predefined performance indexes."""
        self._performance_indexes = [
            # User table optimizations
            ("userbase", ["email"], "btree", "Unique email lookups"),
            ("userbase", ["created_at"], "btree", "User creation time queries"),
            ("userbase", ["plan_tier", "is_active"], "btree", "Plan filtering"),
            ("userbase", ["role", "is_developer"], "btree", "Role access control"),
            
            # Audit log optimizations  
            ("corpus_audit_logs", ["timestamp"], "btree", "Time-based queries"),
            ("corpus_audit_logs", ["user_id", "timestamp"], "btree", "User history"),
            ("corpus_audit_logs", ["action", "status"], "btree", "Action filtering"),
            ("corpus_audit_logs", ["corpus_id", "action"], "btree", "Corpus ops"),
            
            # Secret management
            ("secret", ["user_id"], "btree", "User secret lookups"),
            ("secret", ["provider", "is_active"], "btree", "Provider filtering"),
            
            # Agent state optimizations
            ("agent_states", ["user_id", "updated_at"], "btree", "User states"),
            ("agent_states", ["session_id"], "btree", "Session lookups"),
        ]
    
    async def _load_and_register_existing_indexes(self, session) -> None:
        """Load existing indexes and register them."""
        existing = await self.index_loader.load_existing_indexes(session)
        for index_name in existing:
            self.index_creator.index_checker.add_existing_index(index_name)
    
    async def _create_single_performance_index(self, table_name: str, columns: List[str], 
                                             index_type: str, reason: str) -> tuple:
        """Create single performance index and return result."""
        index_name = IndexNameGenerator.generate_index_name(table_name, columns)
        result = await self.index_creator.create_single_index(table_name, columns, index_name, index_type)
        return index_name, result
    
    async def _log_index_creation_result(self, result, index_name: str, table_name: str, 
                                       columns: List[str], reason: str) -> None:
        """Log index creation result."""
        if result.success and not result.already_exists:
            DatabaseErrorHandler.log_index_creation_success(index_name, table_name, columns, reason)
        elif not result.success:
            logger.warning(f"Failed to create index {index_name}: {result.error_message}")
    
    async def _create_all_performance_indexes(self, session) -> Dict[str, bool]:
        """Create all performance indexes."""
        results = {}
        for table_name, columns, index_type, reason in self._performance_indexes:
            index_name, result = await self._create_single_performance_index(table_name, columns, index_type, reason)
            results[index_name] = result.success
            await self._log_index_creation_result(result, index_name, table_name, columns, reason)
        return results
    
    async def create_performance_indexes(self) -> Dict[str, bool]:
        """Create recommended performance indexes."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            DatabaseValidation.log_engine_unavailable("index creation")
            return {}
        
        async with get_async_db() as session:
            await self._load_and_register_existing_indexes(session)
            return await self._create_all_performance_indexes(session)
    
    async def _analyze_slow_queries(self, session) -> List[IndexRecommendation]:
        """Analyze slow queries and generate recommendations."""
        recommendations = []
        slow_queries = await self.performance_analyzer.get_slow_queries(session)
        
        for query_data in slow_queries:
            query_recommendations = self.performance_analyzer.analyze_query_for_recommendations(query_data)
            recommendations.extend(query_recommendations)
        return recommendations
    
    async def _get_fallback_recommendations(self, recommendations: List[IndexRecommendation]) -> List[IndexRecommendation]:
        """Get fallback recommendations if no slow queries found."""
        if not recommendations:
            recommendations.extend(self.performance_analyzer.recommendation_provider.get_all_recommendations())
        return recommendations
    
    async def analyze_query_performance(self) -> List[IndexRecommendation]:
        """Analyze query performance and recommend indexes."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return self._get_general_recommendations()
        
        async with get_async_db() as session:
            recommendations = await self._analyze_slow_queries(session)
            return await self._get_fallback_recommendations(recommendations)
    
    def _get_general_recommendations(self) -> List[IndexRecommendation]:
        """Get general index recommendations."""
        return self.performance_analyzer.recommendation_provider.get_general_recommendations()
    
    async def _build_usage_stats_query(self) -> str:
        """Build index usage statistics query."""
        return """
            SELECT 
                indexrelname as index_name,
                relname as table_name,
                idx_scan as times_used,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
        """
    
    async def _parse_usage_stats_result(self, result) -> List[Dict[str, Any]]:
        """Parse index usage statistics result."""
        stats = []
        for row in result.fetchall():
            stats.append({
                "index_name": row[0], "table_name": row[1], 
                "times_used": row[2], "tuples_read": row[3], "tuples_fetched": row[4]
            })
        return stats
    
    async def _execute_usage_stats_query(self, session) -> Dict[str, Any]:
        """Execute usage statistics query."""
        query_text = await self._build_usage_stats_query()
        query = text(query_text)
        result = await session.execute(query)
        stats = await self._parse_usage_stats_result(result)
        return {"index_usage": stats}
    
    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Get index usage statistics."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return {}
        
        async with get_async_db() as session:
            try:
                return await self._execute_usage_stats_query(session)
            except Exception as e:
                logger.error(f"Error getting index usage stats: {e}")
                return {}