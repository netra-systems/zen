from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from app.db.clickhouse_base import ClickHouseDatabase
from app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from app.config import settings
from app.logging_config import central_logger as logger


class DisabledClickHouseDatabase:
    """ClickHouse client for when ClickHouse is disabled in development mode.
    
    Provides safe fallback behavior without hardcoded test data.
    """
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query with disabled ClickHouse - returns empty results."""
        logger.debug(f"ClickHouse disabled - Execute query logged: {query[:50]}...")
        return self._create_empty_result_set()
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute parameterized query with disabled ClickHouse."""
        logger.debug(f"ClickHouse disabled - Parameterized query logged: {query[:50]}...")
        return self._create_schema_aware_result(query, params)
    
    async def fetch(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch data with disabled ClickHouse - returns empty results."""
        logger.debug(f"ClickHouse disabled - Fetch query logged: {query[:50]}...")
        return self._create_schema_aware_result(query, params)
    
    async def disconnect(self):
        """Disconnect - no-op for disabled client."""
        logger.debug("ClickHouse disabled - Disconnect called")
    
    async def test_connection(self) -> bool:
        """Test connection - always succeeds for disabled client."""
        logger.debug("ClickHouse disabled - Connection test passed")
        return True
    
    def ping(self) -> bool:
        """Ping - always succeeds for disabled client."""
        logger.debug("ClickHouse disabled - Ping successful")
        return True
    
    async def command(self, cmd: str, parameters: Optional[Dict[str, Any]] = None, 
                     settings: Optional[Dict[str, Any]] = None) -> Any:
        """Execute command with disabled ClickHouse - no-op for schema operations."""
        logger.debug(f"ClickHouse disabled - Command logged: {cmd[:50]}...")
        return None
    
    def _create_empty_result_set(self) -> List[Dict[str, Any]]:
        """Create empty result set for queries."""
        return []
    
    def _create_schema_aware_result(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create schema-aware empty results based on query structure."""
        # Log the query structure for debugging
        logger.debug(f"Query structure analyzed for disabled ClickHouse")
        
        # Return empty results - the application should handle empty datasets gracefully
        return self._create_empty_result_set()

def _is_clickhouse_disabled() -> bool:
    """Check if ClickHouse is disabled in current environment."""
    dev_disabled = settings.environment == "development" and not settings.dev_mode_clickhouse_enabled
    return dev_disabled or settings.environment == "testing"

async def _create_disabled_client():
    """Create and manage disabled ClickHouse client."""
    logger.info(f"ClickHouse disabled in {settings.environment} mode - using disabled client")
    client = DisabledClickHouseDatabase()
    try:
        yield client
    finally:
        await client.disconnect()

def _get_clickhouse_config():
    """Get ClickHouse configuration based on environment."""
    if settings.environment == "development":
        return settings.clickhouse_https_dev
    return settings.clickhouse_https

def _create_base_client(config):
    """Create base ClickHouse client with configuration."""
    return ClickHouseDatabase(
        host=config.host, port=config.port, user=config.user,
        password=config.password, database=config.database, secure=True
    )

def _wrap_client_with_interceptor(base_client):
    """Wrap client with query interceptor for array syntax fixes."""
    return ClickHouseQueryInterceptor(base_client)

async def _cleanup_client(client):
    """Clean up ClickHouse client connection."""
    if client:
        await client.disconnect()

async def _create_enabled_client():
    """Create and configure enabled ClickHouse client."""
    config = _get_clickhouse_config()
    base_client = _create_base_client(config)
    return _wrap_client_with_interceptor(base_client)

async def _handle_disabled_client():
    """Handle disabled client creation and management."""
    async for client in _create_disabled_client():
        yield client

async def _handle_enabled_client():
    """Handle enabled client creation and cleanup."""
    client = await _create_enabled_client()
    try:
        yield client
    finally:
        await _cleanup_client(client)

@asynccontextmanager
async def get_clickhouse_client():
    """Dependency provider for ClickHouse client with proper connection management."""
    if _is_clickhouse_disabled():
        async for client in _handle_disabled_client():
            yield client
    else:
        async for client in _handle_enabled_client():
            yield client