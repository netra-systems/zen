"""ClickHouse index optimization and management.

This module provides ClickHouse-specific database optimization
with proper async/await handling and modular architecture.
"""

from typing import Dict, List, Tuple, Any

from app.logging_config import central_logger
from app.db.clickhouse import get_clickhouse_client

logger = central_logger.get_logger(__name__)


class ClickHouseTableChecker:
    """Check ClickHouse table existence and properties."""
    
    @staticmethod
    async def table_exists(client, table_name: str) -> bool:
        """Check if table exists in ClickHouse."""
        try:
            result = await client.execute_query(
                f"SELECT name FROM system.tables WHERE name = '{table_name}'"
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False
    
    @staticmethod
    async def get_table_engine_info(client, table_name: str) -> Dict[str, str]:
        """Get table engine information."""
        try:
            query = f"""
                SELECT engine, order_by_expression
                FROM system.tables 
                WHERE name = '{table_name}'
            """
            result = await client.execute_query(query)
            if result:
                return {
                    'engine': result[0].get('engine', ''),
                    'order_by_expression': result[0].get('order_by_expression', '')
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting engine info for {table_name}: {e}")
            return {}


class ClickHouseEngineOptimizer:
    """Optimize ClickHouse table engines."""
    
    def __init__(self):
        self.table_checker = ClickHouseTableChecker()
        self._setup_performance_indexes()
    
    def _setup_performance_indexes(self):
        """Setup predefined performance optimizations."""
        self._performance_indexes = [
            ("netra_content_corpus", ["id", "created_at"], "MergeTree ORDER BY optimization"),
            ("netra_audit_events", ["timestamp", "user_id"], "Time-series optimization"),
            ("netra_performance_metrics", ["timestamp", "metric_type"], "Metrics time-series"),
            ("netra_agent_logs", ["timestamp", "agent_id"], "Agent log optimization"),
        ]
    
    async def _check_order_by_optimization(self, current_order_by: str, 
                                         expected_columns: List[str]) -> bool:
        """Check if ORDER BY needs optimization."""
        expected_order_by = ', '.join(expected_columns)
        return expected_order_by.lower() in current_order_by.lower()
    
    async def _evaluate_table_optimization(self, client, table_name: str, 
                                         order_by_cols: List[str], reason: str) -> bool:
        """Evaluate if table needs optimization."""
        if not await self.table_checker.table_exists(client, table_name):
            logger.debug(f"Table {table_name} does not exist, skipping optimization")
            return False
        
        engine_info = await self.table_checker.get_table_engine_info(client, table_name)
        
        if engine_info.get('engine') == 'MergeTree':
            current_order_by = engine_info.get('order_by_expression', '')
            is_optimized = await self._check_order_by_optimization(current_order_by, order_by_cols)
            
            if not is_optimized:
                logger.info(f"Table {table_name} could benefit from ORDER BY optimization: {reason}")
                return False
            return True
        
        return False
    
    async def optimize_table_engines(self) -> Dict[str, bool]:
        """Optimize ClickHouse table engines for performance."""
        results = {}
        
        async with get_clickhouse_client() as client:
            for table_name, order_by_cols, reason in self._performance_indexes:
                try:
                    is_optimized = await self._evaluate_table_optimization(
                        client, table_name, order_by_cols, reason
                    )
                    results[table_name] = is_optimized
                        
                except Exception as e:
                    logger.error(f"Error optimizing table {table_name}: {e}")
                    results[table_name] = False
        
        return results


class ClickHouseMaterializedViewCreator:
    """Create ClickHouse materialized views."""
    
    def __init__(self):
        self.table_checker = ClickHouseTableChecker()
        self._setup_required_tables()
    
    def _setup_required_tables(self):
        """Setup required tables mapping."""
        self.required_tables = {
            "user_daily_activity": "netra_audit_events",
            "hourly_performance_metrics": "netra_performance_metrics"
        }
    
    async def _create_user_activity_view(self, client) -> None:
        """Create user daily activity materialized view."""
        view_sql = """
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
        """
        await client.execute_query(view_sql)
    
    async def _create_performance_metrics_view(self, client) -> None:
        """Create hourly performance metrics materialized view."""
        view_sql = """
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
        await client.execute_query(view_sql)
    
    async def _create_view_by_name(self, client, view_name: str) -> None:
        """Create specific materialized view by name."""
        if view_name == "user_daily_activity":
            await self._create_user_activity_view(client)
        elif view_name == "hourly_performance_metrics":
            await self._create_performance_metrics_view(client)
        else:
            raise ValueError(f"Unknown view name: {view_name}")
    
    async def create_single_view(self, client, view_name: str, base_table: str) -> bool:
        """Create a single materialized view."""
        try:
            if not await self.table_checker.table_exists(client, base_table):
                logger.debug(f"Base table {base_table} does not exist, skipping view {view_name}")
                return False
            
            await self._create_view_by_name(client, view_name)
            logger.info(f"Created materialized view: {view_name}")
            return True
            
        except Exception as e:
            logger.debug(f"Could not create view {view_name}: {e}")
            return False
    
    async def create_materialized_views(self) -> Dict[str, bool]:
        """Create materialized views for common aggregations."""
        results = {}
        
        async with get_clickhouse_client() as client:
            for view_name, base_table in self.required_tables.items():
                success = await self.create_single_view(client, view_name, base_table)
                results[view_name] = success
        
        return results


class ClickHouseIndexOptimizer:
    """ClickHouse index optimization and management."""
    
    def __init__(self):
        self.engine_optimizer = ClickHouseEngineOptimizer()
        self.view_creator = ClickHouseMaterializedViewCreator()
    
    async def optimize_table_engines(self) -> Dict[str, bool]:
        """Optimize ClickHouse table engines for performance."""
        return await self.engine_optimizer.optimize_table_engines()
    
    async def create_materialized_views(self) -> Dict[str, bool]:
        """Create materialized views for common aggregations."""
        return await self.view_creator.create_materialized_views()
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary."""
        try:
            table_optimizations = await self.optimize_table_engines()
            materialized_views = await self.create_materialized_views()
            
            return {
                "table_optimizations": table_optimizations,
                "materialized_views": materialized_views,
                "total_tables": len(table_optimizations),
                "optimized_tables": sum(table_optimizations.values()),
                "total_views": len(materialized_views),
                "created_views": sum(materialized_views.values())
            }
        except Exception as e:
            logger.error(f"Error getting ClickHouse optimization summary: {e}")
            return {"error": str(e)}