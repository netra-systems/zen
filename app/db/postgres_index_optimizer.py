"""PostgreSQL index optimization and management.

This module provides PostgreSQL-specific database index optimization
with proper async/await handling and modular architecture.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.logging_config import central_logger
from app.db.postgres import get_async_db, async_engine
from app.db.index_optimizer_core import (
    IndexRecommendation,
    IndexCreationResult, 
    DatabaseValidation,
    IndexNameGenerator,
    QueryAnalyzer,
    IndexExistenceChecker,
    PerformanceMetrics,
    DatabaseErrorHandler
)

logger = central_logger.get_logger(__name__)


class PostgreSQLConnectionManager:
    """Manage PostgreSQL async connections safely."""
    
    @staticmethod
    async def get_raw_connection():
        """Get raw connection with proper validation."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return None
        if not DatabaseValidation.validate_raw_connection_method(async_engine):
            logger.error("async_engine missing raw_connection method")
            return None
        try:
            return await async_engine.raw_connection()
        except Exception as e:
            logger.error(f"Failed to get raw connection: {e}")
            return None
    
    @staticmethod
    async def execute_on_raw_connection(conn, query: str):
        """Execute query on raw connection."""
        async_conn = conn.driver_connection
        await async_conn.execute(query)
    
    @staticmethod
    async def close_connection_safely(conn):
        """Close connection with error handling."""
        try:
            await conn.close()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")


class PostgreSQLIndexCreator:
    """Handle PostgreSQL index creation operations."""
    
    def __init__(self):
        self.connection_manager = PostgreSQLConnectionManager()
        self.index_checker = IndexExistenceChecker()
    
    async def _build_create_index_query(self, table_name: str, columns: List[str],
                                      index_name: str, index_type: str) -> str:
        """Build CREATE INDEX query."""
        column_list = ", ".join(columns)
        return f"""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} 
            ON {table_name} USING {index_type} ({column_list})
        """
    
    async def _execute_index_creation(self, query: str) -> bool:
        """Execute index creation with proper connection handling."""
        conn = await self.connection_manager.get_raw_connection()
        if conn is None:
            return False
        
        try:
            await self.connection_manager.execute_on_raw_connection(conn, query)
            return True
        finally:
            await self.connection_manager.close_connection_safely(conn)
    
    async def create_single_index(self, table_name: str, columns: List[str],
                                index_name: str, index_type: str = "btree") -> IndexCreationResult:
        """Create a single database index."""
        if self.index_checker.index_exists(index_name):
            return IndexCreationResult(index_name, True, "", True)
        
        try:
            query = await self._build_create_index_query(
                table_name, columns, index_name, index_type
            )
            success = await self._execute_index_creation(query)
            
            if success:
                self.index_checker.add_existing_index(index_name)
                return IndexCreationResult(index_name, True)
            else:
                return IndexCreationResult(index_name, False, "Connection failed")
            
        except Exception as e:
            if DatabaseErrorHandler.is_already_exists_error(e):
                self.index_checker.add_existing_index(index_name)
                return IndexCreationResult(index_name, True, "", True)
            else:
                error_msg = str(e)
                DatabaseErrorHandler.log_index_creation_error(index_name, e)
                return IndexCreationResult(index_name, False, error_msg)


class PostgreSQLIndexLoader:
    """Load existing PostgreSQL indexes."""
    
    async def load_existing_indexes(self, session) -> Set[str]:
        """Load existing database indexes."""
        try:
            query = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            result = await session.execute(query)
            indexes = {row[0] for row in result.fetchall()}
            logger.debug(f"Loaded {len(indexes)} existing indexes")
            return indexes
        except Exception as e:
            logger.error(f"Error loading existing indexes: {e}")
            return set()


class PostgreSQLPerformanceAnalyzer:
    """Analyze PostgreSQL query performance."""
    
    def __init__(self):
        from app.db.postgres_query_analyzer import (
            PostgreSQLSlowQueryAnalyzer,
            PostgreSQLRecommendationProvider
        )
        self.slow_query_analyzer = PostgreSQLSlowQueryAnalyzer()
        self.recommendation_provider = PostgreSQLRecommendationProvider()
    
    async def get_slow_queries(self, session) -> List[Tuple]:
        """Get slow queries from pg_stat_statements."""
        return await self.slow_query_analyzer.get_slow_queries(session)
    
    def analyze_query_for_recommendations(self, query_data: Tuple) -> List[IndexRecommendation]:
        """Analyze query and generate recommendations."""
        return self.slow_query_analyzer.analyze_single_query(query_data)


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
    
    async def create_performance_indexes(self) -> Dict[str, bool]:
        """Create recommended performance indexes."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            DatabaseValidation.log_engine_unavailable("index creation")
            return {}
        
        results = {}
        async with get_async_db() as session:
            # Load existing indexes first
            existing = await self.index_loader.load_existing_indexes(session)
            for index_name in existing:
                self.index_creator.index_checker.add_existing_index(index_name)
            
            # Create each performance index
            for table_name, columns, index_type, reason in self._performance_indexes:
                index_name = IndexNameGenerator.generate_index_name(table_name, columns)
                
                result = await self.index_creator.create_single_index(
                    table_name, columns, index_name, index_type
                )
                results[index_name] = result.success
                
                if result.success and not result.already_exists:
                    DatabaseErrorHandler.log_index_creation_success(
                        index_name, table_name, columns, reason
                    )
                elif not result.success:
                    logger.warning(f"Failed to create index {index_name}: {result.error_message}")
        
        return results
    
    async def analyze_query_performance(self) -> List[IndexRecommendation]:
        """Analyze query performance and recommend indexes."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return self._get_general_recommendations()
        
        recommendations = []
        async with get_async_db() as session:
            # Get slow queries and analyze
            slow_queries = await self.performance_analyzer.get_slow_queries(session)
            
            for query_data in slow_queries:
                query_recommendations = self.performance_analyzer.analyze_query_for_recommendations(query_data)
                recommendations.extend(query_recommendations)
            
            # Fallback to general recommendations if no slow queries
            if not recommendations:
                recommendations.extend(
                    self.performance_analyzer.recommendation_provider.get_all_recommendations()
                )
        
        return recommendations
    
    def _get_general_recommendations(self) -> List[IndexRecommendation]:
        """Get general index recommendations."""
        return self.performance_analyzer.recommendation_provider.get_general_recommendations()
    
    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Get index usage statistics."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return {}
        
        async with get_async_db() as session:
            try:
                query = text("""
                    SELECT 
                        indexrelname as index_name,
                        relname as table_name,
                        idx_scan as times_used,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched
                    FROM pg_stat_user_indexes
                    ORDER BY idx_scan DESC
                """)
                
                result = await session.execute(query)
                stats = []
                for row in result.fetchall():
                    stats.append({
                        "index_name": row[0],
                        "table_name": row[1], 
                        "times_used": row[2],
                        "tuples_read": row[3],
                        "tuples_fetched": row[4]
                    })
                
                return {"index_usage": stats}
                
            except Exception as e:
                logger.error(f"Error getting index usage stats: {e}")
                return {}