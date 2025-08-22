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
from typing import Any, Dict, List, Optional

from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.logging_config import central_logger as logger


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
    config = get_configuration()
    return config.environment == "testing"

def _is_development_with_mock() -> bool:
    """Check if development environment with mock enabled."""
    config = get_configuration()
    if config.environment == "development":
        return config.clickhouse_mode == "mock"
    return False

def _should_use_mock_clickhouse() -> bool:
    """Check conditions for using mock ClickHouse."""
    return _is_testing_environment() or _is_development_with_mock()

def _get_mock_usage_conditions() -> str:
    """Get description of when mock ClickHouse is used."""
    return "Returns True ONLY when: testing OR development+mock enabled. Default: REAL"

def use_mock_clickhouse() -> bool:
    """Determine if mock ClickHouse should be used.
    
    Returns True based on environment conditions described in _get_mock_usage_conditions().
    """
    return _should_use_mock_clickhouse()


def _get_unified_config():
    """Get unified configuration instance."""
    return get_configuration()

def _extract_https_config(config):
    """Extract appropriate configuration from unified config based on mode."""
    # Use HTTP config for local development, HTTPS for production
    if config.clickhouse_mode == "local":
        return config.clickhouse_https  # This now uses HTTP port for local
    return config.clickhouse_https

def get_clickhouse_config():
    """Get ClickHouse configuration from unified config system.
    
    Returns appropriate config for real ClickHouse connection.
    """
    config = _get_unified_config()
    return _extract_https_config(config)


async def _create_mock_client():
    """Create and manage mock ClickHouse client."""
    config = get_configuration()
    logger.info(f"[ClickHouse] Using MOCK client for {config.environment}")
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
    app_config = get_configuration()
    use_secure = app_config.clickhouse_mode != "local"
    return config, use_secure

def _get_connection_details(config) -> dict:
    """Extract connection details from config."""
    return {
        'host': config.host,
        'port': config.port,
        'user': config.user,
        'password': config.password
    }

def _add_database_and_security(details: dict, config, use_secure: bool) -> dict:
    """Add database and security settings to connection details."""
    details['database'] = config.database
    details['secure'] = use_secure
    return details

def _build_client_params(config, use_secure: bool) -> dict:
    """Build parameters for ClickHouse client creation."""
    details = _get_connection_details(config)
    return _add_database_and_security(details, config, use_secure)

def _create_base_client(config, use_secure: bool):
    """Create base ClickHouse client instance."""
    params = _build_client_params(config, use_secure)
    return ClickHouseDatabase(**params)

async def _test_and_yield_client(client):
    """Test connection and yield client."""
    await client.test_connection()
    logger.info("[ClickHouse] REAL connection established")
    yield client

def _log_connection_attempt(config, use_secure: bool):
    """Log ClickHouse connection attempt."""
    logger.info(f"[ClickHouse] Connecting to instance at {config.host}:{config.port} (secure={use_secure})")

def _create_intercepted_client(config, use_secure: bool):
    """Create ClickHouse client with query interceptor."""
    base_client = _create_base_client(config, use_secure)
    return ClickHouseQueryInterceptor(base_client)

def _handle_connection_error(e: Exception):
    """Handle ClickHouse connection error."""
    logger.error(f"[ClickHouse] REAL connection failed: {str(e)}")
    raise

async def _cleanup_client_connection(client):
    """Clean up ClickHouse client connection."""
    await client.disconnect()
    logger.info("[ClickHouse] REAL connection closed")

async def _setup_real_client():
    """Set up real ClickHouse client configuration and logging."""
    config, use_secure = _get_connection_config()
    _log_connection_attempt(config, use_secure)
    return config, use_secure

async def _connect_and_yield_client(config, use_secure):
    """Connect to ClickHouse and yield client."""
    client = _create_intercepted_client(config, use_secure)
    try:
        async for c in _test_and_yield_client(client):
            yield c
    finally:
        await _cleanup_client_connection(client)

async def _create_real_client():
    """Create and manage REAL ClickHouse client.
    
    This is the default behavior - connects to actual ClickHouse instance.
    """
    config, use_secure = await _setup_real_client()
    try:
        async for c in _connect_and_yield_client(config, use_secure):
            yield c
    except Exception as e:
        _handle_connection_error(e)


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

    def _get_base_connection_params(self, config) -> dict:
        """Get base connection parameters from config."""
        return {
            'host': config.host,
            'port': config.port,
            'user': config.user,
            'password': config.password
        }

    def _add_database_security_params(self, params: dict, config) -> dict:
        """Add database and security parameters."""
        params['database'] = config.database
        params['secure'] = True
        return params

    def _prepare_database_params(self, config) -> dict:
        """Prepare parameters for ClickHouse database creation."""
        params = self._get_base_connection_params(config)
        return self._add_database_security_params(params, config)

    def _build_clickhouse_database(self, config) -> ClickHouseDatabase:
        """Build ClickHouse database client."""
        params = self._prepare_database_params(config)
        return ClickHouseDatabase(**params)
    
    async def _initialize_real_client(self):
        """Initialize real ClickHouse client."""
        logger.info("[ClickHouse Service] Initializing with REAL client")
        config = get_clickhouse_config()
        base_client = self._build_clickhouse_database(config)
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