"""
ClickHouse database initialization module.
Creates required tables on application startup.
"""

from typing import List, Tuple

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.core.configuration.base import config_manager
from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.models_clickhouse import (
    LOGS_TABLE_SCHEMA,
    SUPPLY_TABLE_SCHEMA,
    WORKLOAD_EVENTS_TABLE_SCHEMA,
)
from netra_backend.app.logging_config import central_logger as logger

# List of table schemas to create on startup
CLICKHOUSE_TABLES: List[Tuple[str, str]] = [
    ("netra_app_internal_logs", LOGS_TABLE_SCHEMA),
    ("netra_global_supply_catalog", SUPPLY_TABLE_SCHEMA),
    ("workload_events", WORKLOAD_EVENTS_TABLE_SCHEMA),
]

def _should_skip_initialization() -> bool:
    """Check if ClickHouse initialization should be skipped."""
    if settings.environment == "testing":
        logger.info("Skipping ClickHouse initialization in testing environment")
        return True
    return False

def _get_clickhouse_mode_from_env() -> str:
    """Get ClickHouse mode from environment variable."""
    config = config_manager.get_config()
    return getattr(config, 'clickhouse_mode', 'shared').lower()

def _should_skip_for_disabled_mode(mode: str) -> bool:
    """Check if should skip for disabled mode."""
    if mode == "disabled":
        logger.info("ClickHouse is disabled (mode: disabled) - skipping initialization")
        return True
    return False

def _should_skip_for_mock_mode(mode: str) -> bool:
    """Check if should skip for mock mode."""
    if mode == "mock":
        logger.info("ClickHouse is running in mock mode - skipping initialization")
        return True
    return False

def _check_clickhouse_mode() -> bool:
    """Check ClickHouse mode configuration."""
    mode = _get_clickhouse_mode_from_env()
    return (_should_skip_for_disabled_mode(mode) or 
            _should_skip_for_mock_mode(mode))

def _check_development_config() -> bool:
    """Check development environment configuration."""
    if settings.environment == "development" and not settings.dev_mode_clickhouse_enabled:
        logger.info("ClickHouse disabled in development configuration - skipping initialization")
        return True
    return False

async def _test_client_connection(client) -> bool:
    """Test ClickHouse client connection."""
    if not await client.test_connection():
        logger.warning("ClickHouse connection test failed - skipping table initialization")
        return False
    return True

async def _create_single_table(client, table_name: str, schema: str, verbose: bool = False) -> None:
    """Create a single ClickHouse table."""
    try:
        if verbose:
            logger.info(f"Creating ClickHouse table if not exists: {table_name}")
        else:
            logger.debug(f"Creating ClickHouse table if not exists: {table_name}")
        await client.command(schema)
        if verbose:
            logger.info(f"Successfully ensured table exists: {table_name}")
        else:
            logger.debug(f"Successfully ensured table exists: {table_name}")
    except Exception as e:
        logger.error(f"Failed to create table {table_name}: {e}")
        # Continue with other tables even if one fails

async def _create_all_tables(client, verbose: bool = False) -> None:
    """Create all required ClickHouse tables."""
    for table_name, schema in CLICKHOUSE_TABLES:
        await _create_single_table(client, table_name, schema, verbose)

async def _get_existing_tables(client) -> List[str]:
    """Get list of existing ClickHouse tables."""
    try:
        result = await client.execute_query("SHOW TABLES")
        return [row['name'] for row in result if 'name' in row]
    except Exception as e:
        logger.error(f"Failed to query existing tables: {e}")
        return []

async def _verify_workload_events_table(existing_tables: List[str], verbose: bool = False) -> None:
    """Verify workload_events table exists."""
    if 'workload_events' in existing_tables:
        if verbose:
            logger.info("[U+2713] workload_events table verified successfully")
        else:
            logger.debug("[U+2713] workload_events table verified successfully")
    else:
        logger.warning(" WARNING:  workload_events table not found after initialization")

async def _verify_table_creation(client, verbose: bool = False) -> None:
    """Verify all tables were created successfully."""
    try:
        existing_tables = await _get_existing_tables(client)
        if verbose:
            logger.info(f"ClickHouse tables after initialization: {existing_tables}")
        else:
            logger.debug(f"ClickHouse tables after initialization: {existing_tables}")
        await _verify_workload_events_table(existing_tables, verbose)
    except Exception as e:
        logger.error(f"Failed to verify tables: {e}")

async def _initialize_tables_with_client(client, verbose: bool = False) -> None:
    """Initialize tables using provided client."""
    if not await _test_client_connection(client):
        return
    
    await _create_all_tables(client, verbose)
    await _verify_table_creation(client, verbose)

async def initialize_clickhouse_tables(verbose: bool = False) -> None:
    """Initialize all required ClickHouse tables with robust connection handling."""
    if _should_skip_initialization() or _check_clickhouse_mode() or _check_development_config():
        return
    
    config = config_manager.get_config()
    verbose = verbose or getattr(config, 'verbose_tables', False)
    
    # Try to use connection manager for robust table initialization
    try:
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        
        connection_manager = get_clickhouse_connection_manager()
        if connection_manager and connection_manager.connection_health.state.value not in ["disconnected", "failed"]:
            logger.info("Using ClickHouse connection manager for table initialization")
            
            # Use connection manager's robust connection handling
            async with connection_manager.get_connection() as client:
                await _initialize_tables_with_client(client, verbose)
            return
            
    except ImportError:
        logger.debug("Connection manager not available, using direct client")
    except Exception as e:
        logger.warning(f"Connection manager failed for table init, falling back to direct client: {e}")
    
    # Fallback to direct client connection
    try:
        async with get_clickhouse_client() as client:
            await _initialize_tables_with_client(client, verbose)
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")
        # Don't fail the application startup, just log the error

async def _test_workload_events_accessibility(client) -> bool:
    """Test if workload_events table is accessible."""
    try:
        await client.execute_query("SELECT count() FROM workload_events WHERE 1=0")
        logger.info("workload_events table is accessible")
        return True
    except Exception as e:
        logger.error(f"workload_events table verification failed: {e}")
        return False

async def verify_workload_events_table() -> bool:
    """Verify that the workload_events table exists and is accessible."""
    try:
        async with get_clickhouse_client() as client:
            return await _test_workload_events_accessibility(client)
    except Exception as e:
        logger.error(f"workload_events table verification failed: {e}")
        return False

async def _create_workload_events_table(client) -> bool:
    """Create workload_events table using client."""
    try:
        logger.info("Attempting to create workload_events table")
        await client.command(WORKLOAD_EVENTS_TABLE_SCHEMA)
        logger.info("Successfully created workload_events table")
        return True
    except Exception as e:
        logger.error(f"Failed to create workload_events table: {e}")
        return False

async def create_workload_events_table_if_missing() -> bool:
    """Create the workload_events table if it doesn't exist."""
    try:
        async with get_clickhouse_client() as client:
            return await _create_workload_events_table(client)
    except Exception as e:
        logger.error(f"Failed to create workload_events table: {e}")
        return False