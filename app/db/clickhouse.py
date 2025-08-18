"""
ClickHouse Database Module - Real by Default
Provides clear separation between real and mock ClickHouse clients

Business Value Justification (BVJ):
- Segment: Growth & Enterprise  
- Business Goal: Ensure reliable analytics data collection
- Value Impact: 100% analytics accuracy for decision making
- Revenue Impact: Enables data-driven pricing optimization (+$15K MRR)
"""

from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from app.db.clickhouse_base import ClickHouseDatabase
from app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from app.config import settings
from app.logging_config import central_logger as logger


class MockClickHouseDatabase:
    """Mock ClickHouse client for testing and local development.
    
    Returns empty results without connecting to real database.
    ONLY used when explicitly configured for testing.
    """
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query - returns empty results in mock mode."""
        logger.debug(f"[MOCK ClickHouse] Query: {query[:100]}...")
        return []
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute parameterized query - returns empty results in mock mode."""
        logger.debug(f"[MOCK ClickHouse] Parameterized: {query[:100]}...")
        return []
    
    async def fetch(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch data - returns empty results in mock mode."""
        logger.debug(f"[MOCK ClickHouse] Fetch: {query[:100]}...")
        return []
    
    async def disconnect(self):
        """Disconnect - no-op for mock client."""
        logger.debug("[MOCK ClickHouse] Disconnect called")
    
    async def test_connection(self) -> bool:
        """Test connection - always succeeds for mock client."""
        logger.debug("[MOCK ClickHouse] Connection test (mock)")
        return True
    
    def ping(self) -> bool:
        """Ping - always succeeds for mock client."""
        logger.debug("[MOCK ClickHouse] Ping (mock)")
        return True
    
    async def command(self, cmd: str, parameters: Optional[Dict[str, Any]] = None, 
                     settings: Optional[Dict[str, Any]] = None) -> Any:
        """Execute command - no-op for mock client."""
        logger.debug(f"[MOCK ClickHouse] Command: {cmd[:100]}...")
        return None


def use_mock_clickhouse() -> bool:
    """Determine if mock ClickHouse should be used.
    
    Returns True ONLY when:
    - Environment is "testing" OR
    - Environment is "development" AND mock is explicitly enabled
    
    Default: Use REAL ClickHouse
    """
    if settings.environment == "testing":
        return True
    
    if settings.environment == "development":
        # Check for explicit mock flag (defaults to False - use real)
        return getattr(settings, 'use_mock_clickhouse', False)
    
    # Production always uses real
    return False


def get_clickhouse_config():
    """Get ClickHouse configuration based on environment.
    
    Returns appropriate config for real ClickHouse connection.
    Uses environment variables for all settings.
    """
    import os
    from app.schemas.Config import ClickHouseHTTPSConfig
    
    # Determine which port to use based on mode
    clickhouse_mode = os.environ.get("CLICKHOUSE_MODE", "shared").lower()
    
    if clickhouse_mode == "local":
        # For local mode, use HTTP port (8123)
        port = int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123"))
    else:
        # For shared/cloud mode, use HTTPS port (8443)
        port = 8443
    
    # Always use environment variables for configuration
    return ClickHouseHTTPSConfig(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        port=port,
        user=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "netra_dev_password"),
        database=os.environ.get("CLICKHOUSE_DB", "netra_dev")
    )


@asynccontextmanager
async def get_clickhouse_client():
    """Get ClickHouse client - REAL by default.
    
    Returns:
        - Real ClickHouse client (default)
        - Mock client only when explicitly configured for testing
    
    Usage:
        async with get_clickhouse_client() as client:
            results = await client.execute("SELECT * FROM events")
    """
    if use_mock_clickhouse():
        # Use mock for testing
        logger.info(f"[ClickHouse] Using MOCK client for {settings.environment}")
        client = MockClickHouseDatabase()
        try:
            yield client
        finally:
            await client.disconnect()
    else:
        # Use REAL ClickHouse (default)
        async for client in _create_real_client():
            yield client


async def _create_real_client():
    """Create and manage REAL ClickHouse client.
    
    This is the default behavior - connects to actual ClickHouse instance.
    """
    import os
    config = get_clickhouse_config()
    
    # Determine if we should use secure connection
    clickhouse_mode = os.environ.get("CLICKHOUSE_MODE", "shared").lower()
    use_secure = clickhouse_mode != "local"
    
    logger.info(f"[ClickHouse] Connecting to instance at {config.host}:{config.port} (secure={use_secure})")
    
    try:
        # Create real client
        base_client = ClickHouseDatabase(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            secure=use_secure
        )
        
        # Wrap with query interceptor for compatibility
        client = ClickHouseQueryInterceptor(base_client)
        
        # Test connection
        await client.test_connection()
        logger.info("[ClickHouse] REAL connection established")
        
        yield client
        
    except Exception as e:
        logger.error(f"[ClickHouse] REAL connection failed: {str(e)}")
        # Don't fall back to mock - fail explicitly
        raise
    finally:
        if 'client' in locals():
            await client.disconnect()
            logger.info("[ClickHouse] REAL connection closed")


class ClickHouseService:
    """Service class for ClickHouse operations.
    
    Provides high-level methods with clear real/mock distinction.
    """
    
    def __init__(self, force_mock: bool = False):
        """Initialize service.
        
        Args:
            force_mock: Force use of mock client (for testing only)
        """
        self.force_mock = force_mock
        self._client = None
    
    async def initialize(self):
        """Initialize ClickHouse connection."""
        if self.force_mock or use_mock_clickhouse():
            logger.info("[ClickHouse Service] Initializing with MOCK client")
            self._client = MockClickHouseDatabase()
        else:
            logger.info("[ClickHouse Service] Initializing with REAL client")
            config = get_clickhouse_config()
            base_client = ClickHouseDatabase(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                secure=True
            )
            self._client = ClickHouseQueryInterceptor(base_client)
            await self._client.test_connection()
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query on ClickHouse."""
        if not self._client:
            await self.initialize()
        return await self._client.execute(query, params)
    
    async def close(self):
        """Close ClickHouse connection."""
        if self._client:
            await self._client.disconnect()
            self._client = None
    
    @property
    def is_mock(self) -> bool:
        """Check if using mock client."""
        return isinstance(self._client, MockClickHouseDatabase)
    
    @property
    def is_real(self) -> bool:
        """Check if using real client."""
        return not self.is_mock and self._client is not None


# Backward compatibility exports
DisabledClickHouseDatabase = MockClickHouseDatabase  # Alias for compatibility