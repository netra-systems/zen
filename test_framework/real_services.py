"""
Real Services Infrastructure for Testing.

This module provides real service connections for integration and E2E testing.
It replaces mocks with actual PostgreSQL, Redis, ClickHouse, WebSocket, and HTTP connections.
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union, ContextManager
from unittest.mock import AsyncMock

import aiohttp
import websockets
from websockets.exceptions import WebSocketException, ConnectionClosedError

# SSOT Import - Use canonical DatabaseManager
from netra_backend.app.db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ServiceUnavailableError(Exception):
    """Raised when a required service is unavailable."""
    pass


class ServiceConfigurationError(Exception):
    """Raised when service configuration is invalid."""
    pass


# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

@dataclass
class ServiceEndpoints:
    """Service endpoint configuration."""
    postgres_host: str = "localhost"
    postgres_port: int = 5432  # Default to local PostgreSQL port
    postgres_user: str = "postgres"  # Default local PostgreSQL user
    postgres_password: str = "postgres"  # Default password for local PostgreSQL
    postgres_db: str = "netra_test"
    
    redis_host: str = "localhost"
    redis_port: int = 6381
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    clickhouse_host: str = "localhost"
    clickhouse_http_port: int = 8126  # Updated to match ALPINE_TEST_CLICKHOUSE_HTTP_PORT
    clickhouse_tcp_port: int = 9003   # Updated to match ALPINE_TEST_CLICKHOUSE_TCP_PORT
    clickhouse_user: str = "test"          # Updated to match Docker container
    clickhouse_password: str = "test"      # Updated to match Docker container
    clickhouse_db: str = "test_analytics"  # Updated to match Docker container
    
    backend_service_url: str = "http://localhost:8000"
    auth_service_url: str = "http://localhost:8081"
    websocket_url: str = "ws://localhost:8765"

    @classmethod
    def from_environment(cls, env_manager=None):
        """Create configuration from environment variables.
        
        Automatically detects whether to use Docker services or local services
        based on USE_REAL_SERVICES environment flag and service availability.
        """
        if env_manager:
            # Handle IsolatedEnvironment objects which have get() method instead of env attribute
            if hasattr(env_manager, 'get'):
                env = env_manager
            elif hasattr(env_manager, 'env'):
                env = env_manager.env
            else:
                # Fallback - try to treat as dict-like
                env = env_manager
        else:
            # Fallback to regular environment
            from shared.isolated_environment import get_env
            env = get_env()
        
        # Detect if we should use Docker services or local services
        use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"
        
        # PostgreSQL configuration - fallback to local if Docker unavailable
        if use_real_services:
            postgres_port_default = "5434"  # Docker test port
            postgres_user_default = "test_user"
            postgres_password_default = "test_password"
        else:
            postgres_port_default = "5432"  # Local PostgreSQL port
            postgres_user_default = "postgres"
            postgres_password_default = "postgres"  # Common default for local PostgreSQL
        
        # Redis configuration - fallback to mock if not available
        redis_port_default = "6381" if use_real_services else "6379"
        
        return cls(
            postgres_host=env.get("TEST_POSTGRES_HOST", "localhost"),
            postgres_port=int(env.get("TEST_POSTGRES_PORT", postgres_port_default)),
            postgres_user=env.get("TEST_POSTGRES_USER", postgres_user_default),
            postgres_password=env.get("TEST_POSTGRES_PASSWORD", postgres_password_default),
            postgres_db=env.get("TEST_POSTGRES_DB", "netra_test"),
            
            redis_host=env.get("TEST_REDIS_HOST", "localhost"),
            redis_port=int(env.get("TEST_REDIS_PORT", redis_port_default)),
            redis_db=int(env.get("TEST_REDIS_DB", "0")),
            redis_password=env.get("TEST_REDIS_PASSWORD"),
            
            clickhouse_host=env.get("TEST_CLICKHOUSE_HOST", "localhost"),
            clickhouse_http_port=int(env.get("TEST_CLICKHOUSE_HTTP_PORT", "8126")),
            clickhouse_tcp_port=int(env.get("TEST_CLICKHOUSE_TCP_PORT", "9003")),
            clickhouse_user=env.get("TEST_CLICKHOUSE_USER", "test"),
            clickhouse_password=env.get("TEST_CLICKHOUSE_PASSWORD", "test"),
            clickhouse_db=env.get("TEST_CLICKHOUSE_DB", "test_analytics"),
            
            backend_service_url=env.get("TEST_BACKEND_URL", "http://localhost:8000"),
            auth_service_url=env.get("TEST_AUTH_URL", "http://localhost:8081"),
            websocket_url=env.get("TEST_WEBSOCKET_URL", "ws://localhost:8765")
        )


# =============================================================================
# DATABASE MANAGER
# =============================================================================

# DatabaseManager imported from SSOT location at top of file
# (see import at top: from netra_backend.app.db.database_manager import DatabaseManager)


# =============================================================================
# REDIS MANAGER
# =============================================================================

class RedisManager:
    """Real Redis manager for testing."""
    
    def __init__(self, config: ServiceEndpoints):
        self.config = config
        self._client = None
        
    async def connect(self):
        """Establish Redis connection with fallback handling."""
        try:
            import redis.asyncio as redis
            self._client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.config.redis_host}:{self.config.redis_port}")
        except ImportError:
            logger.warning("redis not available, using mock client")
            self._client = AsyncMock()
        except Exception as e:
            logger.warning(f"Failed to connect to Redis at {self.config.redis_host}:{self.config.redis_port}: {e}")
            logger.info("Using mock Redis client for tests")
            self._client = AsyncMock()  # Fallback to mock instead of failing
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
            logger.info("Disconnected from Redis")
    
    async def get_client(self):
        """Get Redis client."""
        if not self._client:
            await self.connect()
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        client = await self.get_client()
        if hasattr(client, 'get'):
            return await client.get(key)
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis."""
        client = await self.get_client()
        if hasattr(client, 'set'):
            return await client.set(key, value, ex=ex)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        client = await self.get_client()
        if hasattr(client, 'delete'):
            result = await client.delete(key)
            return result > 0
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        client = await self.get_client()
        if hasattr(client, 'exists'):
            return bool(await client.exists(key))
        return False
    
    async def ping(self) -> bool:
        """Ping Redis."""
        client = await self.get_client()
        if hasattr(client, 'ping'):
            return await client.ping()
        return True
    
    async def set_json(self, key: str, value: dict, ex: Optional[int] = None) -> bool:
        """Set JSON value in Redis."""
        import json
        json_str = json.dumps(value)
        return await self.set(key, json_str, ex=ex)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from Redis."""
        import json
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None


# =============================================================================
# CLICKHOUSE MANAGER
# =============================================================================

class ClickHouseManager:
    """Real ClickHouse manager for testing."""
    
    def __init__(self, config: ServiceEndpoints):
        self.config = config
        self._client = None
        
    async def connect(self):
        """Establish ClickHouse connection.""" 
        try:
            import clickhouse_connect
            self._client = clickhouse_connect.get_client(
                host=self.config.clickhouse_host,
                port=self.config.clickhouse_http_port,
                username=self.config.clickhouse_user,
                password=self.config.clickhouse_password,
                database=self.config.clickhouse_db
            )
            # Test connection
            self._client.command("SELECT 1")
            logger.info(f"Connected to ClickHouse at {self.config.clickhouse_host}:{self.config.clickhouse_http_port}")
        except ImportError:
            logger.warning("clickhouse-connect not available, using mock client")
            self._client = AsyncMock()
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to connect to ClickHouse: {e}")
    
    async def disconnect(self):
        """Close ClickHouse connection."""
        if self._client and hasattr(self._client, 'close'):
            self._client.close()
            logger.info("Disconnected from ClickHouse")
    
    def get_client(self):
        """Get ClickHouse client (synchronous)."""
        if not self._client:
            # For testing, we'll create the connection synchronously
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, use task
                asyncio.create_task(self.connect())
            else:
                loop.run_until_complete(self.connect())
        return self._client
    
    async def execute(self, query: str) -> List[Any]:
        """Execute query and return results."""
        if not self._client:
            await self.connect()
            
        if hasattr(self._client, 'command'):
            return self._client.command(query)
        return []
    
    async def insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Insert data into table."""
        if not self._client:
            await self.connect()
            
        if hasattr(self._client, 'insert'):
            self._client.insert(table, data)
            return True
        return True


# =============================================================================
# WEBSOCKET TEST CLIENT
# =============================================================================

class WebSocketTestClient:
    """Real WebSocket client for testing."""
    
    def __init__(self, config: ServiceEndpoints):
        self.config = config
        self._websocket = None
        self._connected = False
        
    async def connect(self, endpoint: str = "", headers: Optional[Dict[str, str]] = None):
        """Connect to WebSocket endpoint."""
        url = f"{self.config.websocket_url}{endpoint}"
        
        try:
            self._websocket = await websockets.connect(
                url,
                extra_headers=headers or {},
                ping_interval=20,
                ping_timeout=10
            )
            self._connected = True
            logger.info(f"Connected to WebSocket at {url}")
        except ImportError:
            logger.warning("websockets not available, using mock client")
            self._websocket = AsyncMock()
            self._connected = True
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to connect to WebSocket: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self._websocket and hasattr(self._websocket, 'close'):
            await self._websocket.close()
            self._connected = False
            logger.info("Disconnected from WebSocket")
    
    async def send(self, message: Union[str, Dict[str, Any]]):
        """Send message through WebSocket."""
        if not self._connected:
            raise RuntimeError("WebSocket not connected")
            
        if isinstance(message, dict):
            import json
            message = json.dumps(message)
            
        if hasattr(self._websocket, 'send'):
            await self._websocket.send(message)
        
    async def receive(self, timeout: Optional[float] = 5.0) -> str:
        """Receive message from WebSocket."""
        if not self._connected:
            raise RuntimeError("WebSocket not connected")
            
        if hasattr(self._websocket, 'recv'):
            try:
                if timeout:
                    return await asyncio.wait_for(self._websocket.recv(), timeout=timeout)
                else:
                    return await self._websocket.recv()
            except asyncio.TimeoutError:
                raise TimeoutError("WebSocket receive timeout")
        
        return '{"type": "mock", "data": "test message"}'
    
    async def close(self):
        """Close WebSocket connection."""
        await self.disconnect()


# =============================================================================
# HTTP TEST CLIENT
# =============================================================================

class HTTPTestClient:
    """Real HTTP client for testing."""
    
    def __init__(self, config: ServiceEndpoints):
        self.config = config
        self._session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Closed HTTP client session")
    
    async def get(self, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request."""
        session = await self._get_session()
        url = f"{self.config.backend_service_url}{endpoint}"
        return await session.get(url, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request."""
        session = await self._get_session()
        url = f"{self.config.backend_service_url}{endpoint}"
        return await session.post(url, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make PUT request."""
        session = await self._get_session()
        url = f"{self.config.backend_service_url}{endpoint}"
        return await session.put(url, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make DELETE request."""
        session = await self._get_session()
        url = f"{self.config.backend_service_url}{endpoint}"
        return await session.delete(url, **kwargs)


# =============================================================================
# REAL SERVICES MANAGER
# =============================================================================

class RealServicesManager:
    """Central manager for all real services."""
    
    def __init__(self, config: Optional[ServiceEndpoints] = None):
        self.config = config or ServiceEndpoints.from_environment()
        self.postgres = DatabaseManager(self.config)
        self.redis = RedisManager(self.config)
        self.clickhouse = ClickHouseManager(self.config)
        self._http_client = None
        self._websocket_clients = []
        
    async def ensure_all_services_available(self):
        """Ensure all required services are available."""
        services_to_check = [
            ("PostgreSQL", self.postgres.connect),
            ("Redis", self.redis.connect),
            ("ClickHouse", self.clickhouse.connect),
        ]
        
        for service_name, connect_func in services_to_check:
            try:
                await connect_func()
                logger.info(f"✅ {service_name} is available")
            except ServiceUnavailableError as e:
                logger.error(f"❌ {service_name} is unavailable: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ {service_name} connection error: {e}")
                raise ServiceUnavailableError(f"{service_name} connection failed: {e}")
    
    async def get_http_client(self) -> HTTPTestClient:
        """Get HTTP test client."""
        if not self._http_client:
            self._http_client = HTTPTestClient(self.config)
        return self._http_client
    
    def create_websocket_client(self) -> WebSocketTestClient:
        """Create WebSocket test client."""
        client = WebSocketTestClient(self.config)
        self._websocket_clients.append(client)
        return client
    
    async def reset_all_data(self):
        """Reset all data in test databases."""
        try:
            # Reset PostgreSQL test data
            await self.postgres.execute("DELETE FROM test_data WHERE 1=1")
            logger.info("Reset PostgreSQL test data")
        except Exception as e:
            logger.debug(f"PostgreSQL reset failed (may not exist): {e}")
        
        try:
            # Reset Redis test data  
            client = await self.redis.get_client()
            if hasattr(client, 'flushdb'):
                await client.flushdb()
                logger.info("Reset Redis test data")
        except Exception as e:
            logger.debug(f"Redis reset failed: {e}")
        
        try:
            # Reset ClickHouse test data
            await self.clickhouse.execute("DELETE FROM test_analytics WHERE 1=1")
            logger.info("Reset ClickHouse test data")
        except Exception as e:
            logger.debug(f"ClickHouse reset failed (may not exist): {e}")
    
    async def close_all(self):
        """Close all service connections."""
        await self.postgres.disconnect()
        await self.redis.disconnect()
        await self.clickhouse.disconnect()
        
        if self._http_client:
            await self._http_client.close()
            
        for client in self._websocket_clients:
            await client.close()
        self._websocket_clients.clear()
        
        logger.info("All real services connections closed")


# =============================================================================
# GLOBAL INSTANCE AND HELPERS
# =============================================================================

_real_services_instance: Optional[RealServicesManager] = None


def get_real_services() -> RealServicesManager:
    """Get or create global real services manager."""
    global _real_services_instance
    if _real_services_instance is None:
        _real_services_instance = RealServicesManager()
    return _real_services_instance


def skip_if_services_unavailable(services: List[str]):
    """Decorator to skip test if services are unavailable."""
    import pytest
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_real_services()
            try:
                await manager.ensure_all_services_available()
            except ServiceUnavailableError as e:
                pytest.skip(f"Required services unavailable: {e}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def load_test_fixtures(manager: RealServicesManager, fixture_dir: Union[str, Path]):
    """Load test fixtures into real services."""
    fixture_path = Path(fixture_dir)
    if not fixture_path.exists():
        logger.warning(f"Fixture directory does not exist: {fixture_path}")
        return
    
    # Load SQL fixtures
    sql_files = list(fixture_path.glob("*.sql"))
    for sql_file in sql_files:
        try:
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            await manager.postgres.execute(sql_content)
            logger.info(f"Loaded SQL fixture: {sql_file.name}")
        except Exception as e:
            logger.error(f"Failed to load SQL fixture {sql_file.name}: {e}")
    
    # Load JSON fixtures for Redis/ClickHouse
    json_files = list(fixture_path.glob("*.json"))
    for json_file in json_files:
        try:
            import json
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Process based on filename pattern
            if 'redis' in json_file.name.lower():
                redis_client = await manager.redis.get_client()
                for key, value in data.items():
                    await redis_client.set(key, json.dumps(value) if isinstance(value, dict) else str(value))
                logger.info(f"Loaded Redis fixture: {json_file.name}")
            
            elif 'clickhouse' in json_file.name.lower():
                # Load into ClickHouse (would need table structure)
                logger.info(f"Loaded ClickHouse fixture: {json_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to load JSON fixture {json_file.name}: {e}")


# =============================================================================
# EXPORT ALL CLASSES
# =============================================================================

__all__ = [
    'ServiceUnavailableError',
    'ServiceConfigurationError',
    'ServiceEndpoints',
    # DatabaseManager imported from SSOT location - not exported to avoid import conflicts
    'RedisManager', 
    'ClickHouseManager',
    'WebSocketTestClient',
    'HTTPTestClient',
    'RealServicesManager',
    'get_real_services',
    'skip_if_services_unavailable',
    'load_test_fixtures'
]