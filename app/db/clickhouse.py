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


def _is_testing_environment() -> bool:
    """Check if running in testing environment."""
    return settings.environment == "testing"

def _is_development_with_mock() -> bool:
    """Check if development environment with mock enabled."""
    if settings.environment == "development":
        return getattr(settings, 'use_mock_clickhouse', False)
    return False

def use_mock_clickhouse() -> bool:
    """Determine if mock ClickHouse should be used.
    
    Returns True ONLY when:
    - Environment is "testing" OR
    - Environment is "development" AND mock is explicitly enabled
    
    Default: Use REAL ClickHouse
    """
    return _is_testing_environment() or _is_development_with_mock()


def get_clickhouse_config():
    """Get ClickHouse configuration from unified config system.
    
    Returns appropriate config for real ClickHouse connection.
    Uses unified configuration system for consistency.
    """
    from app.config import get_config
    config = get_config()
    
    # Use HTTPS config as default (can be switched based on needs)
    return config.clickhouse_https


async def _create_mock_client():
    """Create and manage mock ClickHouse client."""
    logger.info(f"[ClickHouse] Using MOCK client for {settings.environment}")
    client = MockClickHouseDatabase()
    try:
        yield client
    finally:
        await client.disconnect()

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
        async for client in _create_mock_client():
            yield client
    else:
        async for client in _create_real_client():
            yield client


def _get_connection_config():
    """Get ClickHouse connection configuration."""
    config = get_clickhouse_config()
    from app.config import get_config
    app_config = get_config()
    use_secure = app_config.clickhouse_mode != "local"
    return config, use_secure

def _create_base_client(config, use_secure: bool):
    """Create base ClickHouse client instance."""
    return ClickHouseDatabase(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        secure=use_secure
    )

async def _test_and_yield_client(client):
    """Test connection and yield client."""
    await client.test_connection()
    logger.info("[ClickHouse] REAL connection established")
    yield client

async def _create_real_client():
    """Create and manage REAL ClickHouse client.
    
    This is the default behavior - connects to actual ClickHouse instance.
    """
    config, use_secure = _get_connection_config()
    logger.info(f"[ClickHouse] Connecting to instance at {config.host}:{config.port} (secure={use_secure})")
    
    try:
        base_client = _create_base_client(config, use_secure)
        client = ClickHouseQueryInterceptor(base_client)
        async for c in _test_and_yield_client(client):
            yield c
    except Exception as e:
        logger.error(f"[ClickHouse] REAL connection failed: {str(e)}")
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
    
    def _initialize_mock_client(self):
        """Initialize mock ClickHouse client."""
        logger.info("[ClickHouse Service] Initializing with MOCK client")
        self._client = MockClickHouseDatabase()

    async def _initialize_real_client(self):
        """Initialize real ClickHouse client."""
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

    async def initialize(self):
        """Initialize ClickHouse connection."""
        if self.force_mock or use_mock_clickhouse():
            self._initialize_mock_client()
        else:
            await self._initialize_real_client()
    
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