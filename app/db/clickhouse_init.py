"""
ClickHouse database initialization module.
Creates required tables on application startup.
"""

from typing import List, Tuple
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import (
    LOGS_TABLE_SCHEMA,
    SUPPLY_TABLE_SCHEMA,
    WORKLOAD_EVENTS_TABLE_SCHEMA
)
from app.config import settings
from app.logging_config import central_logger as logger


# List of table schemas to create on startup
CLICKHOUSE_TABLES: List[Tuple[str, str]] = [
    ("netra_app_internal_logs", LOGS_TABLE_SCHEMA),
    ("netra_global_supply_catalog", SUPPLY_TABLE_SCHEMA),
    ("workload_events", WORKLOAD_EVENTS_TABLE_SCHEMA),
]

async def initialize_clickhouse_tables() -> None:
    """
    Initialize all required ClickHouse tables.
    This function should be called on application startup.
    """
    # Skip initialization in test mode or when ClickHouse is disabled
    import os
    
    if settings.environment == "testing":
        logger.info("Skipping ClickHouse initialization in testing environment")
        return
    
    # Check service mode from environment (set by dev launcher)
    clickhouse_mode = os.environ.get("CLICKHOUSE_MODE", "shared").lower()
    
    if clickhouse_mode == "disabled":
        logger.info("ClickHouse is disabled (mode: disabled) - skipping initialization")
        return
    elif clickhouse_mode == "mock":
        logger.info("ClickHouse is running in mock mode - skipping initialization")
        return
    
    if settings.environment == "development" and not settings.dev_mode_clickhouse_enabled:
        logger.info("ClickHouse disabled in development configuration - skipping initialization")
        return
    
    try:
        async with get_clickhouse_client() as client:
            # Test connection first
            if not await client.test_connection():
                logger.warning("ClickHouse connection test failed - skipping table initialization")
                return
            
            # Create each table
            for table_name, schema in CLICKHOUSE_TABLES:
                try:
                    logger.info(f"Creating ClickHouse table if not exists: {table_name}")
                    await client.command(schema)
                    logger.info(f"Successfully ensured table exists: {table_name}")
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")
                    # Continue with other tables even if one fails
                    continue
            
            # Verify tables were created
            try:
                result = await client.execute_query("SHOW TABLES")
                existing_tables = [row['name'] for row in result if 'name' in row]
                logger.info(f"ClickHouse tables after initialization: {existing_tables}")
                
                # Check if workload_events table exists
                if 'workload_events' in existing_tables:
                    logger.info("✓ workload_events table verified successfully")
                else:
                    logger.warning("⚠ workload_events table not found after initialization")
                    
            except Exception as e:
                logger.error(f"Failed to verify tables: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")
        # Don't fail the application startup, just log the error
        # The application can still work with PostgreSQL

async def verify_workload_events_table() -> bool:
    """
    Verify that the workload_events table exists and is accessible.
    Returns True if the table exists and is accessible, False otherwise.
    """
    try:
        async with get_clickhouse_client() as client:
            # Try to select from the table
            result = await client.execute_query(
                "SELECT count() FROM workload_events WHERE 1=0"
            )
            logger.info("workload_events table is accessible")
            return True
    except Exception as e:
        logger.error(f"workload_events table verification failed: {e}")
        return False

async def create_workload_events_table_if_missing() -> bool:
    """
    Explicitly create the workload_events table if it doesn't exist.
    This can be called when queries fail due to missing table.
    Returns True if successful, False otherwise.
    """
    try:
        async with get_clickhouse_client() as client:
            logger.info("Attempting to create workload_events table")
            await client.command(WORKLOAD_EVENTS_TABLE_SCHEMA)
            logger.info("Successfully created workload_events table")
            return True
    except Exception as e:
        logger.error(f"Failed to create workload_events table: {e}")
        return False