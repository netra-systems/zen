"""Real services test infrastructure for eliminating mocks.

This module provides comprehensive real service helpers to replace all 5766 mock violations
across the codebase. It creates actual connections to test databases, Redis, ClickHouse, 
and other services running in docker-compose.test.yml.

Key principles:
- NO MOCKS: All interactions use real services
- Fast setup/teardown with connection pooling
- Proper isolation between test runs
- Real data fixtures that work with actual databases
- WebSocket testing with real connections
- Service health monitoring and retry logic

Usage:
    @pytest.fixture
    async def real_postgres(real_services):
        async with real_services.postgres() as db:
            yield db
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from urllib.parse import urlparse

import pytest

# Service dependencies - fail gracefully if not available
try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    asyncpg = None
    POSTGRES_AVAILABLE = False
    
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    
try:
    import clickhouse_driver
    from clickhouse_driver import Client as ClickHouseClient
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    clickhouse_driver = None
    ClickHouseClient = None
    CLICKHOUSE_AVAILABLE = False
    
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False

try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    httpx = None
    HTTP_AVAILABLE = False

# Type checking imports
if TYPE_CHECKING:
    import redis.asyncio as redis_types
    import asyncpg as asyncpg_types
    import httpx as httpx_types
    from clickhouse_driver import Client as ClickHouseClient_types

# Always import from environment isolation
from test_framework.environment_isolation import get_test_env_manager


logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for real test services."""
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5434
    postgres_user: str = "test_user"
    postgres_password: str = "test_pass"
    postgres_database: str = "netra_test"
    
    # Redis
    redis_host: str = "localhost"  
    redis_port: int = 6381
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9002
    clickhouse_user: str = "test_user"
    clickhouse_password: str = "test_pass"
    clickhouse_database: str = "netra_test_analytics"
    
    # Service URLs
    auth_service_url: str = "http://localhost:8082"
    backend_service_url: str = "http://localhost:8001"
    websocket_url: str = "ws://localhost:8001/ws"
    
    # Timeouts
    connection_timeout: float = 10.0
    query_timeout: float = 30.0
    service_startup_timeout: float = 60.0
    
    # Health check
    health_check_interval: float = 1.0
    max_health_check_retries: int = 30


class RealServiceError(Exception):
    """Base exception for real service errors."""
    pass


class ServiceUnavailableError(RealServiceError):
    """Raised when a required service is not available."""
    pass


class DatabaseManager:
    """Manages real PostgreSQL database connections and operations."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._pool: Optional['asyncpg.Pool'] = None
        self._connection_count = 0
        
    @property
    def connection_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@"
                f"{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_database}")
    
    async def ensure_available(self) -> bool:
        """Ensure PostgreSQL service is available."""
        if not POSTGRES_AVAILABLE:
            raise ServiceUnavailableError("asyncpg not installed")
            
        for attempt in range(self.config.max_health_check_retries):
            try:
                conn = await asyncpg.connect(
                    self.connection_url,
                    timeout=self.config.connection_timeout
                )
                await conn.fetchval("SELECT 1")
                await conn.close()
                logger.info(f"PostgreSQL service available at {self.config.postgres_host}:{self.config.postgres_port}")
                return True
            except Exception as e:
                if attempt == self.config.max_health_check_retries - 1:
                    logger.error(f"PostgreSQL not available after {attempt + 1} attempts: {e}")
                    raise ServiceUnavailableError(f"PostgreSQL not available: {e}")
                await asyncio.sleep(self.config.health_check_interval)
        return False
    
    async def get_pool(self) -> 'asyncpg.Pool':
        """Get or create connection pool."""
        if self._pool is None:
            await self.ensure_available()
            self._pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=2,
                max_size=10,
                timeout=self.config.connection_timeout,
                command_timeout=self.config.query_timeout
            )
        return self._pool
    
    @asynccontextmanager
    async def connection(self) -> AsyncIterator['asyncpg.Connection']:
        """Get a database connection from the pool."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            self._connection_count += 1
            try:
                yield conn
            finally:
                self._connection_count -= 1
    
    @asynccontextmanager  
    async def transaction(self) -> AsyncIterator['asyncpg.Connection']:
        """Get a database connection with an automatic transaction."""
        async with self.connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List['asyncpg.Record']:
        """Fetch multiple rows."""
        async with self.connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional['asyncpg.Record']:
        """Fetch a single row.""" 
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value."""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def reset_database(self, preserve_tables: Optional[List[str]] = None) -> None:
        """Reset database to clean state while preserving specified tables."""
        preserve_tables = preserve_tables or []
        
        async with self.connection() as conn:
            # Get all tables
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            
            # Drop tables not in preserve list
            for table_record in tables:
                table_name = table_record['tablename']
                if table_name not in preserve_tables:
                    await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            
            # Reset sequences
            sequences = await conn.fetch("""
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_schema = 'public'
            """)
            
            for seq_record in sequences:
                seq_name = seq_record['sequence_name']
                await conn.execute(f'ALTER SEQUENCE "{seq_name}" RESTART WITH 1')
    
    async def load_test_schema(self, schema_path: str) -> None:
        """Load test database schema from file."""
        if not os.path.exists(schema_path):
            logger.warning(f"Schema file not found: {schema_path}")
            return
            
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        async with self.connection() as conn:
            await conn.execute(schema_sql)
        
        logger.info(f"Loaded test schema from {schema_path}")
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


class RedisManager:
    """Manages real Redis connections and operations."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._client: Optional['redis.Redis'] = None
        
    @property
    def connection_url(self) -> str:
        """Get Redis connection URL."""
        auth_part = f":{self.config.redis_password}@" if self.config.redis_password else ""
        return f"redis://{auth_part}{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"
    
    async def ensure_available(self) -> bool:
        """Ensure Redis service is available."""
        if not REDIS_AVAILABLE:
            raise ServiceUnavailableError("redis not installed")
            
        for attempt in range(self.config.max_health_check_retries):
            try:
                client = redis.Redis.from_url(
                    self.connection_url,
                    decode_responses=True,
                    socket_timeout=self.config.connection_timeout
                )
                await client.ping()
                await client.aclose()
                logger.info(f"Redis service available at {self.config.redis_host}:{self.config.redis_port}")
                return True
            except Exception as e:
                if attempt == self.config.max_health_check_retries - 1:
                    logger.error(f"Redis not available after {attempt + 1} attempts: {e}")
                    raise ServiceUnavailableError(f"Redis not available: {e}")
                await asyncio.sleep(self.config.health_check_interval)
        return False
    
    async def get_client(self) -> 'redis.Redis':
        """Get or create Redis client."""
        if self._client is None:
            await self.ensure_available()
            self._client = redis.Redis.from_url(
                self.connection_url,
                decode_responses=True,
                socket_timeout=self.config.connection_timeout,
                socket_connect_timeout=self.config.connection_timeout
            )
        return self._client
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        client = await self.get_client()
        return await client.set(key, value, ex=ex)
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key.""" 
        client = await self.get_client()
        return await client.get(key)
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        client = await self.get_client()
        return await client.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self.get_client()
        return bool(await client.exists(key))
    
    async def flushdb(self) -> bool:
        """Flush current database."""
        client = await self.get_client()
        return await client.flushdb()
    
    async def ping(self) -> bool:
        """Ping Redis server."""
        client = await self.get_client()
        return await client.ping()
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None


class ClickHouseManager:
    """Manages real ClickHouse connections and operations."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._client: Optional['ClickHouseClient'] = None
    
    async def ensure_available(self) -> bool:
        """Ensure ClickHouse service is available."""
        if not CLICKHOUSE_AVAILABLE:
            raise ServiceUnavailableError("clickhouse-driver not installed")
            
        for attempt in range(self.config.max_health_check_retries):
            try:
                client = ClickHouseClient(
                    host=self.config.clickhouse_host,
                    port=self.config.clickhouse_port,
                    user=self.config.clickhouse_user,
                    password=self.config.clickhouse_password,
                    database=self.config.clickhouse_database,
                    connect_timeout=self.config.connection_timeout
                )
                client.execute("SELECT 1")
                client.disconnect()
                logger.info(f"ClickHouse service available at {self.config.clickhouse_host}:{self.config.clickhouse_port}")
                return True
            except Exception as e:
                if attempt == self.config.max_health_check_retries - 1:
                    logger.error(f"ClickHouse not available after {attempt + 1} attempts: {e}")
                    raise ServiceUnavailableError(f"ClickHouse not available: {e}")
                await asyncio.sleep(self.config.health_check_interval)
        return False
    
    def get_client(self) -> 'ClickHouseClient':
        """Get or create ClickHouse client."""
        if self._client is None:
            self._client = ClickHouseClient(
                host=self.config.clickhouse_host,
                port=self.config.clickhouse_port,
                user=self.config.clickhouse_user,
                password=self.config.clickhouse_password,
                database=self.config.clickhouse_database,
                connect_timeout=self.config.connection_timeout
            )
        return self._client
    
    async def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a query."""
        # ClickHouse driver is sync, run in thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_execute, query, params
        )
    
    def _sync_execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """Synchronous execute wrapper."""
        client = self.get_client()
        return client.execute(query, params or {})
    
    async def insert_data(self, table: str, data: List[Dict]) -> None:
        """Insert data into table."""
        if not data:
            return
            
        columns = list(data[0].keys())
        values = [list(row.values()) for row in data]
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES"
        
        await asyncio.get_event_loop().run_in_executor(
            None, self._sync_insert, query, values
        )
    
    def _sync_insert(self, query: str, values: List[List]) -> None:
        """Synchronous insert wrapper."""
        client = self.get_client()
        client.execute(query, values)
    
    async def reset_database(self) -> None:
        """Reset ClickHouse database to clean state."""
        # Get all tables
        tables = await self.execute("SHOW TABLES")
        
        # Drop all tables
        for table_row in tables:
            table_name = table_row[0]  # First column is table name
            await self.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    def close(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            self._client.disconnect()
            self._client = None


class WebSocketTestClient:
    """Real WebSocket client for testing WebSocket functionality."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._websocket = None
        self._connected = False
    
    async def connect(self, path: str = "", headers: Optional[Dict] = None) -> None:
        """Connect to WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            raise ServiceUnavailableError("websockets not installed")
            
        url = f"{self.config.websocket_url.rstrip('/')}/{path.lstrip('/')}"
        
        try:
            # Handle websockets library version compatibility
            connect_kwargs = {
                "open_timeout": self.config.connection_timeout
            }
            
            # Only add additional_headers if headers are provided
            if headers:
                connect_kwargs["additional_headers"] = headers
                
            self._websocket = await websockets.connect(url, **connect_kwargs)
            self._connected = True
            logger.info(f"WebSocket connected to {url}")
        except Exception as e:
            raise ServiceUnavailableError(f"WebSocket connection failed: {e}")
    
    async def send(self, message: Union[str, Dict]) -> None:
        """Send message to WebSocket."""
        if not self._connected or not self._websocket:
            raise RealServiceError("WebSocket not connected")
            
        if isinstance(message, dict):
            import json
            message = json.dumps(message)
            
        await self._websocket.send(message)
    
    async def receive(self, timeout: Optional[float] = None) -> str:
        """Receive message from WebSocket."""
        if not self._connected or not self._websocket:
            raise RealServiceError("WebSocket not connected")
            
        return await asyncio.wait_for(
            self._websocket.recv(),
            timeout=timeout or self.config.query_timeout
        )
    
    async def receive_json(self, timeout: Optional[float] = None) -> Dict:
        """Receive and parse JSON message."""
        message = await self.receive(timeout)
        import json
        return json.loads(message)
    
    async def close(self) -> None:
        """Close WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        self._connected = False


class HTTPTestClient:
    """Real HTTP client for testing REST API functionality."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._client: Optional['httpx.AsyncClient'] = None
    
    async def get_client(self) -> 'httpx.AsyncClient':
        """Get or create HTTP client."""
        if self._client is None:
            if not HTTP_AVAILABLE:
                raise ServiceUnavailableError("httpx not installed")
            
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.query_timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client
    
    async def request(self, method: str, url: str, **kwargs) -> 'httpx.Response':
        """Make HTTP request."""
        client = await self.get_client()
        return await client.request(method, url, **kwargs)
    
    async def get(self, url: str, **kwargs) -> 'httpx.Response':
        """Make GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> 'httpx.Response':
        """Make POST request."""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> 'httpx.Response':
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> 'httpx.Response':
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class RealServicesManager:
    """Central manager for all real test services."""
    
    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or self._load_config_from_env()
        
        # Service managers
        self._postgres_manager = DatabaseManager(self.config)
        self._redis_manager = RedisManager(self.config)  
        self._clickhouse_manager = ClickHouseManager(self.config)
        
        # Test clients
        self._websocket_clients: List[WebSocketTestClient] = []
        self._http_client: Optional[HTTPTestClient] = None
    
    @asynccontextmanager
    async def postgres(self) -> AsyncIterator[DatabaseManager]:
        """Get PostgreSQL database manager as async context manager."""
        await self._postgres_manager.ensure_available()
        try:
            yield self._postgres_manager
        finally:
            pass  # Connection cleanup is handled by the manager itself
    
    @asynccontextmanager
    async def redis(self) -> AsyncIterator[RedisManager]:
        """Get Redis manager as async context manager."""
        await self._redis_manager.ensure_available()
        try:
            yield self._redis_manager
        finally:
            pass  # Connection cleanup is handled by the manager itself
    
    @property
    def clickhouse(self) -> ClickHouseManager:
        """Get the ClickHouse manager."""
        return self._clickhouse_manager
    
    def _load_config_from_env(self) -> ServiceConfig:
        """Load configuration from environment variables."""
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        return ServiceConfig(
            # PostgreSQL
            postgres_host=env.get("TEST_POSTGRES_HOST", "localhost"),
            postgres_port=int(env.get("TEST_POSTGRES_PORT", "5434")),
            postgres_user=env.get("TEST_POSTGRES_USER", "test"),
            postgres_password=env.get("TEST_POSTGRES_PASSWORD", "test"),
            postgres_database=env.get("TEST_POSTGRES_DB", "netra_test"),
            
            # Redis
            redis_host=env.get("TEST_REDIS_HOST", "localhost"),
            redis_port=int(env.get("TEST_REDIS_PORT", "6381")),
            redis_db=int(env.get("TEST_REDIS_DB", "0")),
            redis_password=env.get("TEST_REDIS_PASSWORD"),
            
            # ClickHouse
            clickhouse_host=env.get("TEST_CLICKHOUSE_HOST", "localhost"),
            clickhouse_port=int(env.get("TEST_CLICKHOUSE_TCP_PORT", "9000")),
            clickhouse_user=env.get("TEST_CLICKHOUSE_USER", "test"),
            clickhouse_password=env.get("TEST_CLICKHOUSE_PASSWORD", "test"),
            clickhouse_database=env.get("TEST_CLICKHOUSE_DB", "netra_test_analytics"),
            
            # Service URLs
            auth_service_url=env.get("TEST_AUTH_SERVICE_URL", "http://localhost:8082"),
            backend_service_url=env.get("TEST_BACKEND_SERVICE_URL", "http://localhost:8001"),
            websocket_url=env.get("TEST_WEBSOCKET_URL", "ws://localhost:8001/ws"),
            
            # Timeouts
            connection_timeout=float(env.get("TEST_CONNECTION_TIMEOUT", "10.0")),
            query_timeout=float(env.get("TEST_QUERY_TIMEOUT", "30.0")),
            service_startup_timeout=float(env.get("TEST_SERVICE_STARTUP_TIMEOUT", "60.0")),
            
            # Health check
            health_check_interval=float(env.get("TEST_HEALTH_CHECK_INTERVAL", "1.0")),
            max_health_check_retries=int(env.get("TEST_MAX_HEALTH_CHECK_RETRIES", "30")),
        )
    
    async def ensure_all_services_available(self) -> None:
        """Ensure all required services are available."""
        logger.info("Checking availability of all real services...")
        
        # Check services in parallel
        tasks = [
            self._postgres_manager.ensure_available(),
            self._redis_manager.ensure_available(),
            self._clickhouse_manager.ensure_available(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        failed_services = []
        for i, result in enumerate(results):
            service_names = ["PostgreSQL", "Redis", "ClickHouse"]
            if isinstance(result, Exception):
                failed_services.append(f"{service_names[i]}: {result}")
        
        if failed_services:
            error_msg = f"Required services not available:\n" + "\n".join(failed_services)
            logger.error(error_msg)
            raise ServiceUnavailableError(error_msg)
        
        logger.info("All real services are available and ready")
    
    async def reset_all_data(self) -> None:
        """Reset all databases to clean state."""
        logger.info("Resetting all test data...")
        
        # Reset in parallel where possible
        tasks = [
            self._redis_manager.flushdb(),
            self._postgres_manager.reset_database(),
            self._clickhouse_manager.reset_database(),
        ]
        
        await asyncio.gather(*tasks)
        logger.info("All test data reset completed")
    
    def create_websocket_client(self) -> WebSocketTestClient:
        """Create a new WebSocket test client."""
        client = WebSocketTestClient(self.config)
        self._websocket_clients.append(client)
        return client
    
    async def get_http_client(self) -> HTTPTestClient:
        """Get HTTP test client."""
        if self._http_client is None:
            self._http_client = HTTPTestClient(self.config)
        return self._http_client
    
    async def close_all(self) -> None:
        """Close all connections and cleanup."""
        logger.info("Closing all real service connections...")
        
        # Close WebSocket clients
        for ws_client in self._websocket_clients:
            await ws_client.close()
        self._websocket_clients.clear()
        
        # Close HTTP client
        if self._http_client:
            await self._http_client.close()
            self._http_client = None
        
        # Close service managers
        await self._postgres_manager.close()
        await self._redis_manager.close()
        self._clickhouse_manager.close()
        
        logger.info("All real service connections closed")


# Global instance for convenient access
_global_real_services: Optional[RealServicesManager] = None


def get_real_services() -> RealServicesManager:
    """Get global real services manager instance."""
    global _global_real_services
    if _global_real_services is None:
        _global_real_services = RealServicesManager()
    return _global_real_services


# ============================================================================
# PYTEST FIXTURES FOR REAL SERVICES
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
async def real_services_manager() -> AsyncIterator[RealServicesManager]:
    """Session-scoped real services manager."""
    manager = get_real_services()
    
    # Ensure all services are available at the start of the session
    await manager.ensure_all_services_available()
    
    try:
        yield manager
    finally:
        # Cleanup at end of session
        await manager.close_all()


@pytest.fixture(scope="function")
async def real_services(real_services_manager: RealServicesManager) -> AsyncIterator[RealServicesManager]:
    """Function-scoped real services with automatic data cleanup.""" 
    # Reset data before each test
    await real_services_manager.reset_all_data()
    
    yield real_services_manager
    
    # Optional: Reset after test as well for extra cleanliness
    # await real_services_manager.reset_all_data()


@pytest.fixture(scope="function") 
async def real_postgres(real_services: RealServicesManager) -> AsyncIterator[DatabaseManager]:
    """Real PostgreSQL database for testing."""
    async with real_services.postgres() as db:
        yield db


@pytest.fixture(scope="function")
async def real_redis(real_services: RealServicesManager) -> AsyncIterator[RedisManager]:
    """Real Redis cache for testing."""
    async with real_services.redis() as redis_client:
        yield redis_client


@pytest.fixture(scope="function")
async def real_clickhouse(real_services: RealServicesManager) -> AsyncIterator[ClickHouseManager]:
    """Real ClickHouse analytics for testing."""
    yield real_services.clickhouse


@pytest.fixture(scope="function") 
async def real_websocket_client(real_services: RealServicesManager) -> AsyncIterator[WebSocketTestClient]:
    """Real WebSocket client for testing."""
    client = real_services.create_websocket_client()
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def real_http_client(real_services: RealServicesManager) -> AsyncIterator[HTTPTestClient]:
    """Real HTTP client for testing."""
    client = await real_services.get_http_client()
    yield client


# ============================================================================
# CONVENIENCE FUNCTIONS FOR MIGRATION FROM MOCKS
# ============================================================================

def skip_if_services_unavailable():
    """Pytest skip decorator for tests requiring real services."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                manager = get_real_services()
                await manager.ensure_all_services_available()
            except ServiceUnavailableError as e:
                pytest.skip(f"Real services not available: {e}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def load_test_fixtures(manager: RealServicesManager, fixture_dir: str) -> None:
    """Load test fixtures into real databases."""
    import json
    from pathlib import Path
    
    fixture_path = Path(fixture_dir)
    if not fixture_path.exists():
        logger.warning(f"Fixture directory not found: {fixture_dir}")
        return
    
    # Load PostgreSQL fixtures
    postgres_fixtures = fixture_path / "postgres"
    if postgres_fixtures.exists():
        async with manager.postgres() as postgres_manager:
            for fixture_file in postgres_fixtures.glob("*.sql"):
                with open(fixture_file) as f:
                    await postgres_manager.execute(f.read())
    
    # Load Redis fixtures
    redis_fixtures = fixture_path / "redis" 
    if redis_fixtures.exists():
        async with manager.redis() as redis_manager:
            for fixture_file in redis_fixtures.glob("*.json"):
                with open(fixture_file) as f:
                    data = json.load(f)
                    for key, value in data.items():
                        await redis_manager.set(key, value)
    
    # Load ClickHouse fixtures
    clickhouse_fixtures = fixture_path / "clickhouse"
    if clickhouse_fixtures.exists():
        for fixture_file in clickhouse_fixtures.glob("*.json"):
            with open(fixture_file) as f:
                tables_data = json.load(f)
                for table_name, rows in tables_data.items():
                    if rows:
                        await manager.clickhouse.insert_data(table_name, rows)
    
    logger.info(f"Loaded test fixtures from {fixture_dir}")


# Example usage and migration guide
"""
MIGRATION FROM MOCKS TO REAL SERVICES:

Before (using mocks):
    @pytest.fixture
    def mock_database():
        mock = MagicMock()
        mock.execute = AsyncMock(return_value=None)
        return mock
    
    async def test_user_creation(mock_database):
        await user_service.create_user("test@example.com")
        mock_database.execute.assert_called_once()

After (using real services):
    async def test_user_creation(real_postgres):
        # Test with real database
        user_id = await user_service.create_user("test@example.com")
        
        # Verify in real database
        user = await real_postgres.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            "test@example.com"
        )
        assert user is not None
        assert user['email'] == "test@example.com"

Benefits:
- Tests real database constraints, triggers, indexes
- Catches actual SQL errors and type mismatches  
- Tests real connection pooling and transaction behavior
- Validates actual data serialization/deserialization
- No mock setup/maintenance overhead
- Higher confidence in production behavior
"""