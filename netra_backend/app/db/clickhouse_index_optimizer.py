"""ClickHouse index optimization and management.

This module provides ClickHouse-specific database optimization
with proper async/await handling and modular architecture.
"""

from typing import Dict, List, Tuple, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.clickhouse import get_clickhouse_client

logger = central_logger.get_logger(__name__)


class ClickHouseTableChecker:
    """Check ClickHouse table existence and properties."""
    
    @staticmethod
    async def _execute_table_check_query(client, table_name: str):
        """Execute table existence check query."""
        return await client.execute_query(
            f"SELECT name FROM system.tables WHERE name = '{table_name}'"
        )
    
    @staticmethod
    async def table_exists(client, table_name: str) -> bool:
        """Check if table exists in ClickHouse."""
        try:
            result = await ClickHouseTableChecker._execute_table_check_query(client, table_name)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False
    
    @staticmethod
    async def _build_engine_info_query(table_name: str) -> str:
        """Build query for engine information."""
        return f"""
            SELECT engine, order_by_expression
            FROM system.tables 
            WHERE name = '{table_name}'
        """
    
    async def _parse_engine_result(result: List[Dict]) -> Dict[str, str]:
        """Parse engine information result."""
        if result:
            return {
                'engine': result[0].get('engine', ''),
                'order_by_expression': result[0].get('order_by_expression', '')
            }
        return {}
    
    async def _execute_engine_info_query(client, query: str) -> List[Dict]:
        """Execute engine information query."""
        return await client.execute_query(query)
    
    @staticmethod
    async def _handle_engine_info_error(e: Exception, table_name: str) -> Dict[str, str]:
        """Handle engine info retrieval error."""
        logger.error(f"Error getting engine info for {table_name}: {e}")
        return {}
    
    async def get_table_engine_info(client, table_name: str) -> Dict[str, str]:
        """Get table engine information."""
        try:
            query = await ClickHouseTableChecker._build_engine_info_query(table_name)
            result = await ClickHouseTableChecker._execute_engine_info_query(client, query)
            return await ClickHouseTableChecker._parse_engine_result(result)
        except Exception as e:
            return await ClickHouseTableChecker._handle_engine_info_error(e, table_name)


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
    
    async def _check_table_exists_for_optimization(self, client, table_name: str) -> bool:
        """Check if table exists for optimization."""
        if not await self.table_checker.table_exists(client, table_name):
            logger.debug(f"Table {table_name} does not exist, skipping optimization")
            return False
        return True
    
    async def _check_merge_tree_engine(self, engine_info: Dict[str, str]) -> bool:
        """Check if table uses MergeTree engine."""
        return engine_info.get('engine') == 'MergeTree'
    
    async def _log_optimization_suggestion(self, table_name: str, reason: str) -> None:
        """Log optimization suggestion for table."""
        logger.info(f"Table {table_name} could benefit from ORDER BY optimization: {reason}")
    
    async def _check_order_by_and_log(self, current_order_by: str, order_by_cols: List[str], 
                                     table_name: str, reason: str) -> bool:
        """Check order by optimization and log if needed."""
        is_optimized = await self._check_order_by_optimization(current_order_by, order_by_cols)
        if not is_optimized:
            await self._log_optimization_suggestion(table_name, reason)
        return is_optimized
    
    async def _evaluate_merge_tree_optimization(self, engine_info: Dict[str, str], 
                                              order_by_cols: List[str], 
                                              table_name: str, reason: str) -> bool:
        """Evaluate MergeTree table optimization."""
        if not await self._check_merge_tree_engine(engine_info):
            return False
        current_order_by = engine_info.get('order_by_expression', '')
        return await self._check_order_by_and_log(current_order_by, order_by_cols, table_name, reason)
    
    async def _evaluate_table_optimization(self, client, table_name: str, 
                                         order_by_cols: List[str], reason: str) -> bool:
        """Evaluate if table needs optimization."""
        if not await self._check_table_exists_for_optimization(client, table_name):
            return False
        
        engine_info = await self.table_checker.get_table_engine_info(client, table_name)
        return await self._evaluate_merge_tree_optimization(engine_info, order_by_cols, table_name, reason)
    
    async def _process_single_table_optimization(self, client, table_name: str, 
                                               order_by_cols: List[str], reason: str) -> bool:
        """Process optimization for a single table."""
        try:
            return await self._evaluate_table_optimization(client, table_name, order_by_cols, reason)
        except Exception as e:
            logger.error(f"Error optimizing table {table_name}: {e}")
            return False
    
    async def _process_all_table_optimizations(self, client) -> Dict[str, bool]:
        """Process optimizations for all tables."""
        results = {}
        for table_name, order_by_cols, reason in self._performance_indexes:
            is_optimized = await self._process_single_table_optimization(client, table_name, order_by_cols, reason)
            results[table_name] = is_optimized
        return results
    
    async def optimize_table_engines(self) -> Dict[str, bool]:
        """Optimize ClickHouse table engines for performance."""
        async with get_clickhouse_client() as client:
            return await self._process_all_table_optimizations(client)


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
    
    def _get_user_activity_view_columns(self) -> str:
        """Get columns for user activity view."""
        return """user_id,
                toDate(timestamp) as date,
                count() as activity_count,
                uniq(session_id) as unique_sessions"""
    
    def _get_user_activity_view_definition(self) -> str:
        """Get user activity view definition part."""
        return """CREATE MATERIALIZED VIEW IF NOT EXISTS user_daily_activity
            ENGINE = SummingMergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (user_id, date)"""
    
    def _get_user_activity_view_from_parts(self) -> str:
        """Build view SQL from parts."""
        return f"""FROM netra_audit_events
            WHERE user_id != ''
            GROUP BY user_id, toDate(timestamp)"""
    
    def _get_user_activity_view_sql(self) -> str:
        """Get SQL for user daily activity materialized view."""
        columns = self._get_user_activity_view_columns()
        definition = self._get_user_activity_view_definition()
        from_part = self._get_user_activity_view_from_parts()
        return f"""{definition}
            AS SELECT {columns}
            {from_part}"""
    
    async def _create_user_activity_view(self, client) -> None:
        """Create user daily activity materialized view."""
        view_sql = self._get_user_activity_view_sql()
        await client.execute_query(view_sql)
    
    def _get_performance_metrics_view_columns(self) -> str:
        """Get columns for performance metrics view."""
        return """metric_type,
                toStartOfHour(timestamp) as hour,
                avg(value) as avg_value,
                max(value) as max_value,
                min(value) as min_value,
                count() as sample_count"""
    
    def _get_performance_metrics_view_definition(self) -> str:
        """Get performance metrics view definition part."""
        return """CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_performance_metrics
            ENGINE = SummingMergeTree()
            PARTITION BY toYYYYMM(hour)
            ORDER BY (metric_type, hour)"""
    
    def _get_performance_metrics_view_sql(self) -> str:
        """Get SQL for hourly performance metrics materialized view."""
        columns = self._get_performance_metrics_view_columns()
        definition = self._get_performance_metrics_view_definition()
        return f"""{definition}
            AS SELECT {columns}
            FROM netra_performance_metrics
            GROUP BY metric_type, toStartOfHour(timestamp)"""
    
    async def _create_performance_metrics_view(self, client) -> None:
        """Create hourly performance metrics materialized view."""
        view_sql = self._get_performance_metrics_view_sql()
        await client.execute_query(view_sql)
    
    async def _create_view_by_name(self, client, view_name: str) -> None:
        """Create specific materialized view by name."""
        if view_name == "user_daily_activity":
            await self._create_user_activity_view(client)
        elif view_name == "hourly_performance_metrics":
            await self._create_performance_metrics_view(client)
        else:
            raise ValueError(f"Unknown view name: {view_name}")
    
    async def _check_base_table_exists(self, client, base_table: str, view_name: str) -> bool:
        """Check if base table exists for view creation."""
        if not await self.table_checker.table_exists(client, base_table):
            logger.debug(f"Base table {base_table} does not exist, skipping view {view_name}")
            return False
        return True
    
    async def _execute_view_creation(self, client, view_name: str) -> None:
        """Execute view creation and log success."""
        await self._create_view_by_name(client, view_name)
        logger.info(f"Created materialized view: {view_name}")
    
    async def _handle_view_creation_error(self, e: Exception, view_name: str) -> bool:
        """Handle view creation error."""
        logger.debug(f"Could not create view {view_name}: {e}")
        return False
    
    async def _attempt_view_creation(self, client, view_name: str, base_table: str) -> bool:
        """Attempt view creation if base table exists."""
        if not await self._check_base_table_exists(client, base_table, view_name):
            return False
        await self._execute_view_creation(client, view_name)
        return True
    
    async def create_single_view(self, client, view_name: str, base_table: str) -> bool:
        """Create a single materialized view."""
        try:
            return await self._attempt_view_creation(client, view_name, base_table)
        except Exception as e:
            return await self._handle_view_creation_error(e, view_name)
    
    async def _create_all_views(self, client) -> Dict[str, bool]:
        """Create all required materialized views."""
        results = {}
        for view_name, base_table in self.required_tables.items():
            success = await self.create_single_view(client, view_name, base_table)
            results[view_name] = success
        return results
    
    async def create_materialized_views(self) -> Dict[str, bool]:
        """Create materialized views for common aggregations."""
        async with get_clickhouse_client() as client:
            return await self._create_all_views(client)


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
    
    async def _calculate_table_stats(self, table_optimizations: Dict[str, bool]) -> Dict[str, Any]:
        """Calculate table optimization statistics."""
        return {
            "total_tables": len(table_optimizations),
            "optimized_tables": sum(table_optimizations.values())
        }
    
    async def _calculate_view_stats(self, materialized_views: Dict[str, bool]) -> Dict[str, Any]:
        """Calculate view creation statistics."""
        return {
            "total_views": len(materialized_views),
            "created_views": sum(materialized_views.values())
        }
    
    async def _combine_stats_dicts(self, table_optimizations: Dict[str, bool], 
                                 materialized_views: Dict[str, bool],
                                 table_stats: Dict[str, Any], view_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all statistics dictionaries."""
        base_stats = {"table_optimizations": table_optimizations, "materialized_views": materialized_views}
        return {**base_stats, **table_stats, **view_stats}
    
    async def _build_optimization_stats_dict(self, table_optimizations: Dict[str, bool], 
                                            materialized_views: Dict[str, bool]) -> Dict[str, Any]:
        """Build optimization statistics dictionary."""
        table_stats = await self._calculate_table_stats(table_optimizations)
        view_stats = await self._calculate_view_stats(materialized_views)
        return await self._combine_stats_dicts(table_optimizations, materialized_views, table_stats, view_stats)
    
    async def _calculate_optimization_stats(self, table_optimizations: Dict[str, bool], 
                                           materialized_views: Dict[str, bool]) -> Dict[str, Any]:
        """Calculate optimization statistics."""
        return await self._build_optimization_stats_dict(table_optimizations, materialized_views)
    
    async def _execute_optimization_operations(self) -> Tuple[Dict[str, bool], Dict[str, bool]]:
        """Execute table and view optimization operations."""
        table_optimizations = await self.optimize_table_engines()
        materialized_views = await self.create_materialized_views()
        return table_optimizations, materialized_views
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary."""
        try:
            table_optimizations, materialized_views = await self._execute_optimization_operations()
            return await self._calculate_optimization_stats(table_optimizations, materialized_views)
        except Exception as e:
            logger.error(f"Error getting ClickHouse optimization summary: {e}")
            return {"error": str(e)}