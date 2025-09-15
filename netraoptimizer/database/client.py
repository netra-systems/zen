"""
NetraOptimizer Database Client

Low-level database connection and operation logic.
Single responsibility: managing database connections and executing queries.
"""

import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool, Connection

from ..config import config as local_config
from ..cloud_config import cloud_config
from .models import ExecutionRecord, CommandPattern

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Manages database connections and executes queries.
    This is the only class that directly interacts with the database.
    """

    def __init__(self, database_url: Optional[str] = None, use_cloud_sql: bool = None):
        """
        Initialize the database client.

        Args:
            database_url: Optional database URL override
            use_cloud_sql: If True, use CloudSQL configuration. If None, auto-detect based on environment
        """
        # Determine whether to use CloudSQL configuration
        if use_cloud_sql is None:
            # Auto-detect based on environment
            env = cloud_config.environment
            use_cloud_sql = env in ["staging", "production"] or cloud_config.get_database_config().get("is_cloud_sql", False)

        if use_cloud_sql:
            # Use CloudSQL configuration
            self.database_url = database_url or cloud_config.get_database_url(sync=False)
            logger.info(f"Using CloudSQL configuration for environment: {cloud_config.environment}")
        else:
            # Use local configuration
            self.database_url = database_url or local_config.database_url
            logger.info("Using local database configuration")

        self._pool: Optional[Pool] = None

    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        if not self._pool:
            try:
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    max_queries=50000,
                    max_cacheable_statement_size=0  # Disable statement caching for JSONB
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise

    async def close(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool."""
        if not self._pool:
            await self.initialize()

        async with self._pool.acquire() as connection:
            yield connection

    async def insert_execution(self, record: ExecutionRecord) -> bool:
        """
        Insert an execution record into the database.

        Args:
            record: The ExecutionRecord to insert

        Returns:
            True if successful, False otherwise
        """
        import json

        try:
            async with self.acquire() as conn:
                # Convert dict fields to JSON strings for asyncpg
                await conn.execute("""
                    INSERT INTO command_executions (
                        id, timestamp, batch_id, execution_sequence,
                        command_raw, command_base, command_args, command_features,
                        workspace_context, session_context,
                        total_tokens, input_tokens, output_tokens, cached_tokens,
                        fresh_tokens, cache_hit_rate,
                        execution_time_ms, tool_calls, status, error_message,
                        cost_usd, fresh_cost_usd, cache_savings_usd,
                        output_characteristics, model_version
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                        $21, $22, $23, $24::jsonb, $25
                    )
                """,
                    record.id,
                    record.timestamp,
                    record.batch_id,
                    record.execution_sequence,
                    record.command_raw,
                    record.command_base,
                    json.dumps(record.command_args) if record.command_args else None,
                    json.dumps(record.command_features) if record.command_features else None,
                    json.dumps(record.workspace_context) if record.workspace_context else None,
                    json.dumps(record.session_context) if record.session_context else None,
                    record.total_tokens,
                    record.input_tokens,
                    record.output_tokens,
                    record.cached_tokens,
                    record.fresh_tokens,
                    record.cache_hit_rate,
                    record.execution_time_ms,
                    record.tool_calls,
                    record.status,
                    record.error_message,
                    record.cost_usd,
                    record.fresh_cost_usd,
                    record.cache_savings_usd,
                    json.dumps(record.output_characteristics) if record.output_characteristics else None,
                    record.model_version
                )

                logger.debug(f"Inserted execution record: {record.id}")
                return True

        except Exception as e:
            logger.error(f"Failed to insert execution record: {e}")
            return False

    async def get_recent_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent execution records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of execution records as dictionaries
        """
        try:
            async with self.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM command_executions
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve recent executions: {e}")
            return []

    async def get_command_statistics(self, command_base: str, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for a specific command over the last N days.

        Args:
            command_base: The base command to analyze
            days: Number of days to look back

        Returns:
            Dictionary of statistics
        """
        try:
            async with self.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as execution_count,
                        AVG(total_tokens) as avg_tokens,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_tokens) as median_tokens,
                        AVG(cache_hit_rate) as avg_cache_rate,
                        AVG(execution_time_ms) as avg_duration_ms,
                        SUM(cost_usd) as total_cost,
                        AVG(tool_calls) as avg_tool_calls
                    FROM command_executions
                    WHERE command_base = $1
                    AND timestamp > NOW() - INTERVAL '%s days'
                    AND status = 'completed'
                """ % days, command_base)

                return dict(row) if row else {}

        except Exception as e:
            logger.error(f"Failed to get command statistics: {e}")
            return {}

    async def upsert_command_pattern(self, pattern: CommandPattern) -> bool:
        """
        Insert or update a command pattern.

        Args:
            pattern: The CommandPattern to upsert

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.acquire() as conn:
                await conn.execute("""
                    INSERT INTO command_patterns (
                        pattern_signature, command_base,
                        statistics_30d, token_drivers, cache_patterns,
                        optimization_insights, failure_patterns,
                        last_updated, sample_size
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (pattern_signature)
                    DO UPDATE SET
                        statistics_30d = $3,
                        token_drivers = $4,
                        cache_patterns = $5,
                        optimization_insights = $6,
                        failure_patterns = $7,
                        last_updated = $8,
                        sample_size = $9
                """,
                    pattern.pattern_signature,
                    pattern.command_base,
                    pattern.statistics_30d,
                    pattern.token_drivers,
                    pattern.cache_patterns,
                    pattern.optimization_insights,
                    pattern.failure_patterns,
                    pattern.last_updated,
                    pattern.sample_size
                )

                logger.debug(f"Upserted command pattern: {pattern.pattern_signature}")
                return True

        except Exception as e:
            logger.error(f"Failed to upsert command pattern: {e}")
            return False