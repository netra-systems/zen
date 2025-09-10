"""
ClickHouse Schema Management for Trace Persistence
Provides table creation, verification, and management utilities
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path

# Try to import ClickHouse driver, use no-op if not available
try:
    from clickhouse_driver import Client
    from clickhouse_driver.errors import ServerException, ErrorCodes
    CLICKHOUSE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CLICKHOUSE_AVAILABLE = False
    # Create dummy classes for when ClickHouse is not available
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def execute(self, *args, **kwargs):
            raise RuntimeError("ClickHouse driver not available")
        def disconnect(self):
            pass
    
    class ServerException(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__("ClickHouse driver not available")
            self.code = None
    
    class ErrorCodes:
        TABLE_ALREADY_EXISTS = 57
        DATABASE_ALREADY_EXISTS = 81

logger = logging.getLogger(__name__)



class ClickHouseTraceSchema:
    """
    Manages ClickHouse schema for trace data persistence.
    Handles table creation, verification, and statistics.
    """
    
    # Table definitions for easy reference
    TABLES = [
        'agent_executions',
        'agent_events',
        'performance_metrics',
        'trace_correlations',
        'error_logs'
    ]
    
    MATERIALIZED_VIEWS = [
        'mv_user_execution_summary',
        'mv_error_patterns',
        'mv_performance_trends',
        'mv_agent_interactions'
    ]
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 9000,
        database: str = 'netra_traces',
        user: str = 'default',
        password: str = '',
        **kwargs
    ):
        """Initialize ClickHouse schema manager."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.client_kwargs = kwargs
        
        self._client: Optional[Client] = None
        self.migration_path = Path(__file__).parent.parent.parent / 'migrations' / 'clickhouse'
        
    def _get_client(self) -> Client:
        """Get or create ClickHouse client."""
        if self._client is None:
            self._client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                **self.client_kwargs
            )
        return self._client
    
    async def create_tables(self) -> bool:
        """
        Create all ClickHouse tables from migration files.
        Returns True if all tables created successfully.
        """
        try:
            client = self._get_client()
            
            # Process all migration files in order
            migration_files = sorted(self.migration_path.glob('*.sql'))
            if not migration_files:
                logger.error(f"No migration files found in {self.migration_path}")
                return False
            
            total_statements = 0
            for migration_file in migration_files:
                logger.info(f"Processing migration: {migration_file.name}")
                
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                # Split SQL into individual statements
                statements = self._parse_sql_statements(sql_content)
                
                # Execute each statement
                for idx, statement in enumerate(statements):
                    if statement.strip():
                        try:
                            await asyncio.get_event_loop().run_in_executor(
                                None, client.execute, statement
                            )
                            total_statements += 1
                            logger.debug(f"Executed statement {idx + 1}/{len(statements)} from {migration_file.name}")
                        except ServerException as e:
                            # Ignore "already exists" errors
                            if e.code not in [ErrorCodes.TABLE_ALREADY_EXISTS, 
                                             ErrorCodes.DATABASE_ALREADY_EXISTS]:
                                logger.error(f"Failed to execute statement {idx + 1} from {migration_file.name}: {e}")
                                raise
            
            logger.info(f"Successfully executed {total_statements} statements from {len(migration_files)} migration files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False
    
    async def verify_schema(self) -> Dict[str, bool]:
        """
        Verify that all required tables exist and have correct structure.
        Returns dict mapping table names to verification status.
        """
        verification_status = {}
        
        try:
            client = self._get_client()
            
            # Check database exists
            db_exists = await self._database_exists(client)
            verification_status['database'] = db_exists
            
            if not db_exists:
                logger.warning(f"Database {self.database} does not exist")
                return verification_status
            
            # Check each table
            for table in self.TABLES:
                exists = await self._table_exists(client, table)
                verification_status[table] = exists
                
                if exists:
                    # Verify table structure
                    structure_valid = await self._verify_table_structure(client, table)
                    verification_status[f"{table}_structure"] = structure_valid
            
            # Check materialized views
            for view in self.MATERIALIZED_VIEWS:
                exists = await self._table_exists(client, view)
                verification_status[view] = exists
            
            # Log summary
            total_checks = len(verification_status)
            passed_checks = sum(1 for v in verification_status.values() if v)
            logger.info(f"Schema verification: {passed_checks}/{total_checks} checks passed")
            
            return verification_status
            
        except Exception as e:
            logger.error(f"Failed to verify schema: {e}")
            return verification_status
    
    async def get_table_stats(self) -> Dict[str, int]:
        """
        Get row counts and size statistics for all tables.
        Returns dict mapping table names to row counts.
        """
        stats = {}
        
        try:
            client = self._get_client()
            
            for table in self.TABLES:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        client.execute,
                        f"SELECT count() as count FROM {self.database}.{table}"
                    )
                    stats[table] = result[0][0] if result else 0
                except Exception as e:
                    logger.warning(f"Failed to get stats for {table}: {e}")
                    stats[table] = -1
            
            # Get database size
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    client.execute,
                    f"""
                    SELECT 
                        sum(bytes_on_disk) as total_bytes,
                        sum(rows) as total_rows
                    FROM system.parts
                    WHERE database = '{self.database}' AND active
                    """
                )
                if result:
                    stats['total_bytes'] = result[0][0] or 0
                    stats['total_rows'] = result[0][1] or 0
            except Exception as e:
                logger.warning(f"Failed to get database size: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return stats
    
    async def truncate_table(self, table_name: str) -> bool:
        """
        Truncate a specific table (for testing/maintenance).
        Returns True if successful.
        """
        if table_name not in self.TABLES:
            logger.error(f"Invalid table name: {table_name}")
            return False
        
        try:
            client = self._get_client()
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"TRUNCATE TABLE {self.database}.{table_name}"
            )
            
            logger.info(f"Successfully truncated table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to truncate table {table_name}: {e}")
            return False
    
    async def optimize_tables(self) -> Dict[str, bool]:
        """
        Optimize tables for better performance (merge parts).
        Returns dict mapping table names to optimization status.
        """
        optimization_status = {}
        
        try:
            client = self._get_client()
            
            for table in self.TABLES:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        client.execute,
                        f"OPTIMIZE TABLE {self.database}.{table} FINAL"
                    )
                    optimization_status[table] = True
                    logger.debug(f"Optimized table {table}")
                except Exception as e:
                    logger.warning(f"Failed to optimize {table}: {e}")
                    optimization_status[table] = False
            
            return optimization_status
            
        except Exception as e:
            logger.error(f"Failed to optimize tables: {e}")
            return optimization_status
    
    async def drop_all_tables(self) -> bool:
        """
        Drop all tables (DANGEROUS - for testing only).
        Returns True if successful.
        """
        try:
            client = self._get_client()
            
            # Drop materialized views first
            for view in self.MATERIALIZED_VIEWS:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        client.execute,
                        f"DROP TABLE IF EXISTS {self.database}.{view}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to drop view {view}: {e}")
            
            # Drop tables
            for table in self.TABLES:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        client.execute,
                        f"DROP TABLE IF EXISTS {self.database}.{table}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to drop table {table}: {e}")
            
            logger.info("Dropped all tables and views")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            return False
    
    async def get_table_columns(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get column information for a specific table.
        Returns list of dicts with column name, type, and default.
        """
        if table_name not in self.TABLES:
            logger.error(f"Invalid table name: {table_name}")
            return []
        
        try:
            client = self._get_client()
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"""
                SELECT 
                    name,
                    type,
                    default_expression
                FROM system.columns
                WHERE database = '{self.database}' AND table = '{table_name}'
                ORDER BY position
                """
            )
            
            columns = []
            for row in result:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'default': row[2] or ''
                })
            
            return columns
            
        except Exception as e:
            logger.error(f"Failed to get columns for {table_name}: {e}")
            return []
    
    # Private helper methods
    
    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL content into individual statements."""
        # Remove comments
        lines = []
        for line in sql_content.split('\n'):
            # Remove SQL comments
            if not line.strip().startswith('--'):
                lines.append(line)
        
        # Join and split by semicolons
        sql = '\n'.join(lines)
        statements = sql.split(';')
        
        # Filter out empty statements
        return [s.strip() for s in statements if s.strip()]
    
    async def _database_exists(self, client: Client) -> bool:
        """Check if database exists."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"SELECT 1 FROM system.databases WHERE name = '{self.database}'"
            )
            return bool(result)
        except Exception:
            return False
    
    async def _table_exists(self, client: Client, table_name: str) -> bool:
        """Check if table exists."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"""
                SELECT 1 FROM system.tables 
                WHERE database = '{self.database}' AND name = '{table_name}'
                """
            )
            return bool(result)
        except Exception:
            return False
    
    async def _verify_table_structure(self, client: Client, table_name: str) -> bool:
        """Verify table has expected structure."""
        try:
            # Get column count
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"""
                SELECT count() FROM system.columns
                WHERE database = '{self.database}' AND table = '{table_name}'
                """
            )
            
            # Basic validation - tables should have multiple columns
            column_count = result[0][0] if result else 0
            return column_count > 5  # All our tables have more than 5 columns
            
        except Exception:
            return False
    
    def close(self):
        """Close ClickHouse connection."""
        if self._client:
            self._client.disconnect()
            self._client = None


# Convenience functions for module-level usage

async def create_clickhouse_schema(
    host: str = 'localhost',
    port: int = 9000,
    **kwargs
) -> bool:
    """
    Create all ClickHouse tables for trace persistence.
    Convenience function for quick setup.
    """
    schema = ClickHouseTraceSchema(host=host, port=port, **kwargs)
    try:
        return await schema.create_tables()
    finally:
        schema.close()


async def verify_clickhouse_schema(
    host: str = 'localhost',
    port: int = 9000,
    **kwargs
) -> Dict[str, bool]:
    """
    Verify ClickHouse schema is properly set up.
    Convenience function for health checks.
    """
    schema = ClickHouseTraceSchema(host=host, port=port, **kwargs)
    try:
        return await schema.verify_schema()
    finally:
        schema.close()


# Backward compatibility alias
ClickHouseSchema = ClickHouseTraceSchema