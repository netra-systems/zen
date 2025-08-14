"""Database index optimization and management.

This module provides automated database index creation and optimization
for improved query performance across PostgreSQL and ClickHouse databases.
"""

from typing import Dict, List, Optional, Set, Tuple
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text, Index, Column
from sqlalchemy.exc import ProgrammingError

from app.logging_config import central_logger
from app.db.postgres import get_async_db, async_engine
from app.db.clickhouse import get_clickhouse_client

logger = central_logger.get_logger(__name__)


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str = "btree"  # btree, hash, gin, gist for PostgreSQL
    reason: str = ""
    estimated_benefit: float = 0.0
    priority: int = 1  # 1=high, 2=medium, 3=low


class PostgreSQLIndexOptimizer:
    """PostgreSQL index optimization and management."""
    
    def __init__(self):
        self.existing_indexes: Set[str] = set()
        self._performance_indexes = [
            # User table optimizations
            ("userbase", ["email"], "btree", "Unique email lookups"),
            ("userbase", ["created_at"], "btree", "User creation time queries"),
            ("userbase", ["plan_tier", "is_active"], "btree", "Plan and status filtering"),
            ("userbase", ["role", "is_developer"], "btree", "Role-based access control"),
            
            # Audit log optimizations  
            ("corpus_audit_logs", ["timestamp"], "btree", "Time-based audit queries"),
            ("corpus_audit_logs", ["user_id", "timestamp"], "btree", "User audit history"),
            ("corpus_audit_logs", ["action", "status"], "btree", "Action and status filtering"),
            ("corpus_audit_logs", ["corpus_id", "action"], "btree", "Corpus operation tracking"),
            ("corpus_audit_logs", ["resource_type", "resource_id"], "btree", "Resource tracking"),
            ("corpus_audit_logs", ["ip_address"], "btree", "IP-based audit queries"),
            ("corpus_audit_logs", ["request_id"], "btree", "Request correlation"),
            
            # Secret management optimizations
            ("secret", ["user_id"], "btree", "User secret lookups"),
            ("secret", ["provider", "is_active"], "btree", "Provider and status filtering"),
            ("secret", ["created_at"], "btree", "Secret creation tracking"),
            
            # Agent state optimizations
            ("agent_states", ["user_id", "updated_at"], "btree", "User state queries"),
            ("agent_states", ["session_id"], "btree", "Session-based state lookups"),
            ("agent_states", ["agent_type", "status"], "btree", "Agent type and status filtering"),
            
            # Composite indexes for complex queries
            ("userbase", ["plan_tier", "plan_expires_at", "is_active"], "btree", "Plan expiration queries"),
            ("corpus_audit_logs", ["user_id", "action", "timestamp"], "btree", "User action timeline"),
            ("corpus_audit_logs", ["corpus_id", "timestamp", "status"], "btree", "Corpus operation history"),
        ]
    
    async def create_performance_indexes(self) -> Dict[str, bool]:
        """Create recommended performance indexes."""
        results = {}
        
        if not async_engine:
            logger.warning("Async engine not available, skipping index creation")
            return results
        
        async with get_async_db() as session:
            # Load existing indexes first
            await self._load_existing_indexes(session)
            
            for table_name, columns, index_type, reason in self._performance_indexes:
                index_name = f"idx_{table_name}_{'_'.join(columns)}"
                
                if index_name in self.existing_indexes:
                    logger.debug(f"Index {index_name} already exists, skipping")
                    results[index_name] = True
                    continue
                
                try:
                    success = await self._create_index(
                        session, table_name, columns, index_name, index_type
                    )
                    results[index_name] = success
                    
                    if success:
                        logger.info(f"Created index {index_name} on {table_name}({', '.join(columns)}) - {reason}")
                    else:
                        logger.warning(f"Failed to create index {index_name}")
                        
                except Exception as e:
                    logger.error(f"Error creating index {index_name}: {e}")
                    results[index_name] = False
        
        return results
    
    async def _load_existing_indexes(self, session) -> None:
        """Load existing database indexes."""
        try:
            query = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            result = await session.execute(query)
            self.existing_indexes = {row[0] for row in result.fetchall()}
            logger.debug(f"Loaded {len(self.existing_indexes)} existing indexes")
        except Exception as e:
            logger.error(f"Error loading existing indexes: {e}")
    
    async def _create_index(self, session, table_name: str, columns: List[str], 
                           index_name: str, index_type: str = "btree") -> bool:
        """Create a database index."""
        try:
            # Build column list
            column_list = ", ".join(columns)
            
            # Create index query
            create_query = f"""
                CREATE INDEX CONCURRENTLY {index_name} 
                ON {table_name} USING {index_type} ({column_list})
            """
            
            await session.execute(text(create_query))
            await session.commit()
            
            self.existing_indexes.add(index_name)
            return True
            
        except ProgrammingError as e:
            if "already exists" in str(e):
                logger.debug(f"Index {index_name} already exists")
                self.existing_indexes.add(index_name)
                return True
            else:
                logger.error(f"Error creating index {index_name}: {e}")
                await session.rollback()
                return False
        except Exception as e:
            logger.error(f"Unexpected error creating index {index_name}: {e}")
            await session.rollback()
            return False
    
    async def analyze_query_performance(self) -> List[IndexRecommendation]:
        """Analyze query performance and recommend indexes."""
        recommendations = []
        
        if not async_engine:
            return recommendations
        
        async with get_async_db() as session:
            try:
                # Get slow queries from pg_stat_statements if available
                slow_queries_query = text("""
                    SELECT query, calls, total_time, mean_time, rows
                    FROM pg_stat_statements 
                    WHERE mean_time > 100  -- queries slower than 100ms
                    ORDER BY mean_time DESC
                    LIMIT 20
                """)
                
                result = await session.execute(slow_queries_query)
                for row in result.fetchall():
                    query, calls, total_time, mean_time, rows = row
                    
                    # Parse query for potential index recommendations
                    table_recommendations = self._analyze_query_for_indexes(query)
                    for rec in table_recommendations:
                        rec.estimated_benefit = min(mean_time / 100.0, 5.0)  # Cap at 5x benefit
                        recommendations.append(rec)
                
            except Exception as e:
                logger.debug(f"pg_stat_statements not available or error: {e}")
                # Fallback to general recommendations
                recommendations.extend(self._get_general_recommendations())
        
        return recommendations
    
    def _analyze_query_for_indexes(self, query: str) -> List[IndexRecommendation]:
        """Analyze a query and recommend indexes."""
        recommendations = []
        query_lower = query.lower()
        
        # Extract WHERE clause conditions
        where_match = re.search(r'where\s+(.+?)(?:\s+order\s+by|\s+group\s+by|\s+limit|$)', query_lower)
        if where_match:
            where_clause = where_match.group(1)
            
            # Look for equality conditions
            eq_conditions = re.findall(r'(\w+)\s*=\s*', where_clause)
            if eq_conditions:
                # Extract table name
                from_match = re.search(r'from\s+(\w+)', query_lower)
                if from_match:
                    table_name = from_match.group(1)
                    recommendations.append(IndexRecommendation(
                        table_name=table_name,
                        columns=eq_conditions[:3],  # Limit to 3 columns
                        reason=f"WHERE clause equality conditions: {', '.join(eq_conditions)}"
                    ))
        
        # Look for ORDER BY clauses
        order_match = re.search(r'order\s+by\s+([\w\s,]+)', query_lower)
        if order_match:
            order_columns = [col.strip() for col in order_match.group(1).split(',')]
            from_match = re.search(r'from\s+(\w+)', query_lower)
            if from_match:
                table_name = from_match.group(1)
                recommendations.append(IndexRecommendation(
                    table_name=table_name,
                    columns=order_columns[:2],  # Limit to 2 columns for ORDER BY
                    reason=f"ORDER BY optimization: {', '.join(order_columns)}"
                ))
        
        return recommendations
    
    def _get_general_recommendations(self) -> List[IndexRecommendation]:
        """Get general index recommendations."""
        return [
            IndexRecommendation(
                table_name="userbase",
                columns=["email"],
                reason="Frequent user lookups by email",
                priority=1
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs", 
                columns=["timestamp"],
                reason="Time-based audit queries",
                priority=1
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs",
                columns=["user_id", "action"],
                reason="User action filtering",
                priority=2
            )
        ]
    
    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Get index usage statistics."""
        if not async_engine:
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


class ClickHouseIndexOptimizer:
    """ClickHouse index optimization and management."""
    
    def __init__(self):
        self._performance_indexes = [
            # Primary key optimizations for typical ClickHouse tables
            ("netra_content_corpus", ["id", "created_at"], "MergeTree ORDER BY optimization"),
            ("netra_audit_events", ["timestamp", "user_id"], "Time-series optimization"),
            ("netra_performance_metrics", ["timestamp", "metric_type"], "Metrics time-series"),
            ("netra_agent_logs", ["timestamp", "agent_id"], "Agent log optimization"),
        ]
    
    async def optimize_table_engines(self) -> Dict[str, bool]:
        """Optimize ClickHouse table engines for performance."""
        results = {}
        
        async with get_clickhouse_client() as client:
            for table_name, order_by_cols, reason in self._performance_indexes:
                try:
                    # Check if table exists
                    table_check = await client.execute_query(
                        f"SELECT name FROM system.tables WHERE name = '{table_name}'"
                    )
                    
                    if not table_check:
                        logger.debug(f"Table {table_name} does not exist, skipping optimization")
                        continue
                    
                    # Get current table engine
                    engine_query = f"""
                        SELECT engine, order_by_expression
                        FROM system.tables 
                        WHERE name = '{table_name}'
                    """
                    engine_info = await client.execute_query(engine_query)
                    
                    if engine_info and engine_info[0].get('engine') == 'MergeTree':
                        current_order_by = engine_info[0].get('order_by_expression', '')
                        expected_order_by = ', '.join(order_by_cols)
                        
                        if expected_order_by.lower() not in current_order_by.lower():
                            logger.info(f"Table {table_name} could benefit from ORDER BY optimization: {reason}")
                            # Note: ClickHouse requires recreating table to change ORDER BY
                            results[table_name] = False
                        else:
                            results[table_name] = True
                    else:
                        results[table_name] = False
                        
                except Exception as e:
                    logger.error(f"Error optimizing table {table_name}: {e}")
                    results[table_name] = False
        
        return results
    
    async def create_materialized_views(self) -> Dict[str, bool]:
        """Create materialized views for common aggregations."""
        views = {
            "user_daily_activity": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS user_daily_activity
                ENGINE = SummingMergeTree()
                PARTITION BY toYYYYMM(date)
                ORDER BY (user_id, date)
                AS SELECT
                    user_id,
                    toDate(timestamp) as date,
                    count() as activity_count,
                    uniq(session_id) as unique_sessions
                FROM netra_audit_events
                WHERE user_id != ''
                GROUP BY user_id, toDate(timestamp)
            """,
            
            "hourly_performance_metrics": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_performance_metrics
                ENGINE = SummingMergeTree()
                PARTITION BY toYYYYMM(hour)
                ORDER BY (metric_type, hour)
                AS SELECT
                    metric_type,
                    toStartOfHour(timestamp) as hour,
                    avg(value) as avg_value,
                    max(value) as max_value,
                    min(value) as min_value,
                    count() as sample_count
                FROM netra_performance_metrics
                GROUP BY metric_type, toStartOfHour(timestamp)
            """
        }
        
        results = {}
        async with get_clickhouse_client() as client:
            for view_name, view_sql in views.items():
                try:
                    await client.execute_query(view_sql)
                    results[view_name] = True
                    logger.info(f"Created materialized view: {view_name}")
                except Exception as e:
                    logger.error(f"Error creating materialized view {view_name}: {e}")
                    results[view_name] = False
        
        return results


class DatabaseIndexManager:
    """Unified database index management."""
    
    def __init__(self):
        self.postgres_optimizer = PostgreSQLIndexOptimizer()
        self.clickhouse_optimizer = ClickHouseIndexOptimizer()
    
    async def optimize_all_databases(self) -> Dict[str, Any]:
        """Run optimization on all databases."""
        results = {
            "postgres": {},
            "clickhouse": {},
            "recommendations": []
        }
        
        # PostgreSQL optimizations
        try:
            postgres_indexes = await self.postgres_optimizer.create_performance_indexes()
            postgres_recommendations = await self.postgres_optimizer.analyze_query_performance()
            postgres_stats = await self.postgres_optimizer.get_index_usage_stats()
            
            results["postgres"] = {
                "indexes_created": postgres_indexes,
                "recommendations": [rec.__dict__ for rec in postgres_recommendations],
                "usage_stats": postgres_stats
            }
        except Exception as e:
            logger.error(f"PostgreSQL optimization error: {e}")
            results["postgres"]["error"] = str(e)
        
        # ClickHouse optimizations
        try:
            clickhouse_tables = await self.clickhouse_optimizer.optimize_table_engines()
            clickhouse_views = await self.clickhouse_optimizer.create_materialized_views()
            
            results["clickhouse"] = {
                "table_optimizations": clickhouse_tables,
                "materialized_views": clickhouse_views
            }
        except Exception as e:
            logger.error(f"ClickHouse optimization error: {e}")
            results["clickhouse"]["error"] = str(e)
        
        return results
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "postgres_stats": {},
            "clickhouse_stats": {},
            "recommendations": []
        }
        
        # Get PostgreSQL stats
        try:
            report["postgres_stats"] = await self.postgres_optimizer.get_index_usage_stats()
        except Exception as e:
            logger.error(f"Error getting PostgreSQL stats: {e}")
        
        # Get recommendations
        try:
            recommendations = await self.postgres_optimizer.analyze_query_performance()
            report["recommendations"] = [rec.__dict__ for rec in recommendations]
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
        
        return report


# Global instance
index_manager = DatabaseIndexManager()