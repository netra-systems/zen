"""
ClickHouse Schema Management for Trace Persistence
Provides table creation, verification, and management utilities
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path

# Import transaction error handling for specific error types
from netra_backend.app.db.transaction_errors import (
    TableCreationError, ColumnModificationError, IndexCreationError,
    classify_error
)

# SSOT ClickHouse import and availability check
from netra_backend.app.db.clickhouse import get_clickhouse_client, ClickHouseClient, CLICKHOUSE_AVAILABLE
try:
    from clickhouse_connect.driver.exceptions import DatabaseError as ServerException
    # clickhouse-connect doesn't have ErrorCodes, create a simple version
    class ErrorCodes:
        TABLE_ALREADY_EXISTS = 57
        DATABASE_ALREADY_EXISTS = 82
except (ImportError, ModuleNotFoundError):
    # Create dummy exception classes for when ClickHouse is not available
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
        
        self.migration_path = Path(__file__).parent.parent.parent / 'migrations' / 'clickhouse'
        
    def _get_client(self):
        """Get ClickHouse client as async context manager.

        Returns:
            AsyncContextManager that yields ClickHouseClient when used with 'async with'
        """
        return get_clickhouse_client()
    
    async def create_tables(self) -> bool:
        """
        Create all ClickHouse tables from migration files.
        Returns True if all tables created successfully.
        """
        try:
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
            async with self._get_client() as client:
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
    
    async def _database_exists(self, client: ClickHouseClient) -> bool:
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
    
    async def _table_exists(self, client: ClickHouseClient, table_name: str) -> bool:
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
    
    async def _verify_table_structure(self, client: ClickHouseClient, table_name: str) -> bool:
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
    
    async def create_table(self, table_name: str, table_schema: str) -> bool:
        """
        Create a single table with specific error handling.
        
        Args:
            table_name: Name of the table to create
            table_schema: SQL schema definition for the table
            
        Returns:
            True if table creation successful, False otherwise
            
        Raises:
            TableCreationError: For table creation specific errors
        """
        try:
            async with self._get_client() as client:
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, table_schema
                )
                logger.info(f"Successfully created table {table_name}")
                return True
        except Exception as e:
            # Classify the error for specific handling
            classified_error = classify_error(e)
            if isinstance(classified_error, TableCreationError):
                logger.error(f"Table creation failed for {table_name}: {classified_error}")
                raise TableCreationError(f"Failed to create table '{table_name}': {classified_error}") from e
            else:
                # Re-raise other classified errors
                logger.error(f"Error creating table {table_name}: {classified_error}")
                raise classified_error from e

    async def modify_column(self, table_name: str, column_name: str, new_type: str) -> bool:
        """
        Modify a column in the specified table.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to modify
            new_type: New column type
            
        Returns:
            True if column modification successful, False otherwise
            
        Raises:
            ColumnModificationError: For column modification specific errors
        """
        try:
            async with self._get_client() as client:
                alter_query = f"ALTER TABLE {self.database}.{table_name} MODIFY COLUMN {column_name} {new_type}"
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, alter_query
                )
                logger.info(f"Successfully modified column {column_name} in {table_name}")
                return True
        except Exception as e:
            # Classify the error for specific handling
            classified_error = classify_error(e)
            if isinstance(classified_error, ColumnModificationError):
                logger.error(f"Column modification failed for {table_name}.{column_name}: {classified_error}")
                raise ColumnModificationError(
                    f"Failed to modify column '{column_name}' in table '{table_name}' "
                    f"from existing type to '{new_type}': {classified_error}"
                ) from e
            else:
                # Re-raise other classified errors
                logger.error(f"Error modifying column {table_name}.{column_name}: {classified_error}")
                raise classified_error from e

    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> bool:
        """
        Create an index on the specified table.
        
        Args:
            table_name: Name of the table
            index_name: Name of the index to create
            columns: List of column names for the index
            
        Returns:
            True if index creation successful, False otherwise
            
        Raises:
            IndexCreationError: For index creation specific errors
        """
        try:
            async with self._get_client() as client:
                columns_str = ", ".join(columns)
                index_query = f"ALTER TABLE {self.database}.{table_name} ADD INDEX {index_name} ({columns_str}) TYPE minmax GRANULARITY 1"
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, index_query
                )
                logger.info(f"Successfully created index {index_name} on {table_name}")
                return True
        except Exception as e:
            # Classify the error for specific handling
            classified_error = classify_error(e)
            if isinstance(classified_error, IndexCreationError):
                logger.error(f"Index creation failed for {table_name}.{index_name}: {classified_error}")
                raise IndexCreationError(
                    f"Failed to create index '{index_name}' on table '{table_name}' "
                    f"with columns {columns}: {classified_error}"
                ) from e
            else:
                # Re-raise other classified errors
                logger.error(f"Error creating index {table_name}.{index_name}: {classified_error}")
                raise classified_error from e

    async def execute_migration(self, migration_name: str, migration_steps: List[str]) -> bool:
        """
        Execute a database migration with rollback context on failure.
        
        Args:
            migration_name: Name of the migration
            migration_steps: List of SQL statements to execute
            
        Returns:
            True if migration successful, False otherwise
            
        Raises:
            Various schema errors with rollback context
        """
        completed_steps = []
        try:
            async with self._get_client() as client:
                for step_num, statement in enumerate(migration_steps, 1):
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None, client.execute, statement
                        )
                        completed_steps.append(statement)
                        logger.debug(f"Migration {migration_name}: Completed step {step_num}/{len(migration_steps)}")
                    except Exception as e:
                        # Classify the error and add migration context
                        classified_error = classify_error(e)
                        error_message = (
                            f"Migration Error: Migration '{migration_name}' failed at step {step_num} of {len(migration_steps)}. "
                            f"Completed Steps: {len(completed_steps)} statements executed successfully. "
                            f"Failed Statement: {statement[:100]}... "
                            f"Rollback Required: Consider reversing the {len(completed_steps)} completed operations. "
                            f"Error: {classified_error}"
                        )
                        
                        # Raise the appropriate error type with migration context
                        if isinstance(classified_error, TableCreationError):
                            raise TableCreationError(error_message) from e
                        elif isinstance(classified_error, ColumnModificationError):
                            raise ColumnModificationError(error_message) from e
                        elif isinstance(classified_error, IndexCreationError):
                            raise IndexCreationError(error_message) from e
                        else:
                            # For other classified errors, raise them with context
                            if hasattr(classified_error, 'context'):
                                # It's a custom schema error, create new instance with message
                                raise classified_error.__class__(error_message) from e
                            else:
                                # It's a SQLAlchemy or other error, just raise the classified error
                                raise classified_error from e
            
            logger.info(f"Migration {migration_name}: All {len(migration_steps)} steps completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration {migration_name} failed: {e}")
            raise

    async def drop_table(self, table_name: str) -> bool:
        """
        Drop a table with dependency error handling.
        
        Args:
            table_name: Name of the table to drop
            
        Returns:
            True if table drop successful, False otherwise
            
        Raises:
            Various errors with dependency context
        """
        try:
            async with self._get_client() as client:
                drop_query = f"DROP TABLE IF EXISTS {self.database}.{table_name}"
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, drop_query
                )
                logger.info(f"Successfully dropped table {table_name}")
                return True
        except Exception as e:
            # Classify the error and add dependency context if needed
            classified_error = classify_error(e)
            error_str = str(e).lower()
            
            # Check for dependency errors
            if "referenced by" in error_str or "materialized view" in error_str:
                error_message = (
                    f"Table Dependency Error: Cannot drop table '{table_name}' due to dependencies. "
                    f"Error: {classified_error}. "
                    f"Resolution Steps: 1) Identify dependent objects, 2) Drop dependencies first, 3) Retry table drop."
                )
                raise TableCreationError(error_message) from e
            else:
                logger.error(f"Error dropping table {table_name}: {classified_error}")
                raise classified_error from e

    async def validate_table_constraints(self, table_name: str) -> bool:
        """
        Validate table constraints.
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            True if validation successful, False otherwise
            
        Raises:
            Various errors with constraint context
        """
        try:
            async with self._get_client() as client:
                # Simple validation query - check if table is readable
                validation_query = f"SELECT count() FROM {self.database}.{table_name} LIMIT 1"
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, validation_query
                )
                logger.info(f"Table constraints validated for {table_name}")
                return True
        except Exception as e:
            # Classify the error and add constraint context if needed
            classified_error = classify_error(e)
            error_str = str(e).lower()
            
            # Check for constraint violation patterns
            if "constraint" in error_str or "check" in error_str or "violated" in error_str:
                error_message = (
                    f"Constraint Violation Error: Table '{table_name}' constraint validation failed. "
                    f"Error: {classified_error}. "
                    f"Fix Suggestion: Review table constraints and data integrity."
                )
                raise ColumnModificationError(error_message) from e
            else:
                logger.error(f"Error validating table constraints for {table_name}: {classified_error}")
                raise classified_error from e

    def close(self):
        """Close ClickHouse connection.

        Note: Since we now use async context managers,
        connections are automatically closed when exiting the context.
        This method is kept for backward compatibility.
        """
        # No-op since connections are automatically managed by async context managers
        pass


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


# Backward compatibility aliases
ClickHouseSchema = ClickHouseTraceSchema
ClickHouseSchemaManager = ClickHouseTraceSchema