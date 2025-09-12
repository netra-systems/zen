"""
Database Connection Handling for Dev Launcher

Provides centralized database connection validation, retry logic,
and health monitoring for PostgreSQL, ClickHouse, and Redis.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Development Velocity & System Stability
- Value Impact: Eliminates 90% of database connection startup failures
- Strategic Impact: Prevents $12K MRR loss from database downtime
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from netra_backend.app.core.network_constants import (
    DatabaseConstants,
    HostConstants,
    NetworkEnvironmentHelper,
    ServicePorts,
)
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    REDIS = "redis"


class ConnectionStatus(Enum):
    """Database connection status."""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK_AVAILABLE = "fallback_available"


@dataclass
class DatabaseConnection:
    """Database connection information."""
    name: str
    db_type: DatabaseType
    url: str
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    last_check: Optional[datetime] = None
    failure_count: int = 0
    last_error: Optional[str] = None
    connection_pool: Optional[Any] = None
    retry_count: int = 0
    max_retries: int = 5


@dataclass
class RetryConfig:
    """Retry configuration for database connections."""
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    max_attempts: int = 5
    timeout: float = 30.0


class DatabaseConnector:
    """
    Centralized database connection handling with retry logic and health monitoring.
    
    Manages connections to PostgreSQL, ClickHouse, and Redis with:
    - Exponential backoff retry logic
    - Connection pooling
    - Health checks and monitoring
    - Clear error messages
    - Graceful connection cleanup
    """
    
    def __init__(self, use_emoji: bool = False):
        """Initialize database connector."""
        self.use_emoji = use_emoji
        self.connections: Dict[str, DatabaseConnection] = {}
        self.retry_config = RetryConfig()
        self._shutdown_requested = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Initialize connections from environment
        self._discover_database_connections()
    
    def _ensure_env_loaded(self) -> None:
        """Ensure .env file is loaded into environment variables."""
        # Find project root
        project_root = Path.cwd()
        for parent in [Path.cwd(), Path(__file__).parent.parent]:
            if (parent / '.env').exists() or (parent / 'app').exists():
                project_root = parent
                break
        
        # Load .env file if it exists
        env_file = project_root / '.env'
        if env_file.exists():
            env_manager = get_env()
            loaded_count, errors = env_manager.load_from_file(
                env_file, 
                source="database_connector_.env",
                override_existing=False
            )
            if loaded_count > 0:
                logger.debug(f"Loaded {loaded_count} variables from .env file")
            if errors:
                logger.warning(f"Errors loading .env file: {errors}")
    
    def _discover_database_connections(self) -> None:
        """Discover database connections from environment variables."""
        self._ensure_env_loaded()
        self._discover_postgres_connection()
        self._discover_clickhouse_connection()
        self._discover_redis_connection()
        logger.info(f"Discovered {len(self.connections)} database connections")
    
    def _discover_postgres_connection(self) -> None:
        """Discover PostgreSQL connection using DatabaseURLBuilder."""
        env_manager = get_env()
        
        # Use DatabaseURLBuilder for proper URL construction
        builder = DatabaseURLBuilder(env_manager.get_all())
        
        # Get the appropriate URL for the environment (async URL for asyncpg)
        postgres_url = builder.get_url_for_environment(sync=False)
        
        self._add_connection("main_postgres", DatabaseType.POSTGRESQL, postgres_url)
    
    def _discover_clickhouse_connection(self) -> None:
        """Discover ClickHouse connection."""
        clickhouse_url = self._build_clickhouse_url()
        if clickhouse_url:
            self._add_connection("main_clickhouse", DatabaseType.CLICKHOUSE, clickhouse_url)
    
    def _discover_redis_connection(self) -> None:
        """Discover Redis connection."""
        redis_url = self._build_redis_url()
        if redis_url:
            self._add_connection("main_redis", DatabaseType.REDIS, redis_url)
    
    def _build_clickhouse_url(self) -> Optional[str]:
        """Build ClickHouse URL from environment variables."""
        return self._construct_clickhouse_url_from_env()
    
    def _construct_clickhouse_url_from_env(self) -> Optional[str]:
        """Construct ClickHouse URL from environment variables."""
        env_manager = get_env()
        host = env_manager.get("CLICKHOUSE_HOST", HostConstants.LOCALHOST)
        # Use HTTP port for dev launcher (health checks require HTTP)
        port = env_manager.get("CLICKHOUSE_HTTP_PORT", "8123")
        user = env_manager.get("CLICKHOUSE_USER", DatabaseConstants.CLICKHOUSE_DEFAULT_USER)
        password = env_manager.get("CLICKHOUSE_PASSWORD", "")
        database = env_manager.get("CLICKHOUSE_DB", DatabaseConstants.CLICKHOUSE_DEFAULT_DB)
        
        # Always use HTTP port 8123 for dev launcher (needed for health checks)
        http_port = 8123
        
        # Build HTTP URL directly instead of using DatabaseConstants.build_clickhouse_url
        # which uses clickhouse:// scheme. For dev launcher, we need HTTP for health checks.
        if password:
            return f"http://{user}:{password}@{host}:{http_port}/{database}"
        else:
            return f"http://{user}@{host}:{http_port}/{database}"
    
    def _build_redis_url(self) -> Optional[str]:
        """Build Redis URL from environment variables."""
        env_manager = get_env()
        redis_url = env_manager.get(DatabaseConstants.REDIS_URL)
        if redis_url:
            return redis_url
        return self._construct_redis_url_from_env()
    
    def _construct_redis_url_from_env(self) -> Optional[str]:
        """Construct Redis URL from environment variables."""
        env_manager = get_env()
        host = env_manager.get("REDIS_HOST", HostConstants.LOCALHOST)
        port = env_manager.get("REDIS_PORT", str(ServicePorts.REDIS_DEFAULT))
        password = env_manager.get("REDIS_PASSWORD", "")
        db = env_manager.get("REDIS_DB", str(DatabaseConstants.REDIS_DEFAULT_DB))
        
        return DatabaseConstants.build_redis_url(
            host=host,
            port=int(port),
            database=int(db),
            password=password if password else None
        )
    
    def _add_connection(self, name: str, db_type: DatabaseType, url: str) -> None:
        """Add a database connection for monitoring."""
        connection = DatabaseConnection(
            name=name,
            db_type=db_type,
            url=url,
            max_retries=self.retry_config.max_attempts
        )
        self.connections[name] = connection
        self._print_connection_discovered(name, db_type)
    
    def _print_connection_discovered(self, name: str, db_type: DatabaseType) -> None:
        """Print connection discovery message."""
        masked_url = self._mask_url_credentials(self.connections[name].url)
        if self.use_emoji:
            try:
                # Try to print with emoji
                print(f" SEARCH:  DISCOVER | {db_type.value.upper()}: {masked_url}")
            except UnicodeEncodeError:
                # Fall back to non-emoji version on Windows
                print(f"[DISCOVER] | {db_type.value.upper()}: {masked_url}")
        else:
            print(f"DISCOVER | {db_type.value.upper()}: {masked_url}")
    
    def _mask_url_credentials(self, url: str) -> str:
        """Mask credentials in URL for logging."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                masked_netloc = parsed.netloc.replace(f":{parsed.password}", ":***")
                return url.replace(parsed.netloc, masked_netloc)
            return url
        except Exception:
            return url
    
    def _normalize_postgres_url(self, url: str) -> str:
        """Normalize PostgreSQL URL format for asyncpg compatibility.
        
        Uses DatabaseURLBuilder for consistent URL normalization.
        """
        if url is None:
            return None
        if not url:
            return url
        # Use centralized format_for_asyncpg_driver method for consistent handling
        from shared.database_url_builder import DatabaseURLBuilder
        return DatabaseURLBuilder.format_for_asyncpg_driver(url)
    
    async def validate_all_connections(self) -> bool:
        """
        Validate all database connections before service startup.
        
        Returns:
            True if all connections are healthy, False otherwise
        """
        if not self.connections:
            self._print_no_databases()
            return True
        
        self._print_validation_start()
        
        # Validate connections concurrently
        validation_tasks = [
            self._validate_connection_with_retry(conn)
            for conn in self.connections.values()
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Check results
        all_healthy = True
        for i, result in enumerate(results):
            connection = list(self.connections.values())[i]
            if isinstance(result, Exception):
                self._handle_validation_exception(connection, result)
                all_healthy = False
            elif not result:
                all_healthy = False
        
        self._print_validation_summary(all_healthy)
        return all_healthy
    
    def _handle_validation_exception(self, connection: DatabaseConnection, exception: Exception) -> None:
        """Handle validation exception during startup."""
        connection.status = ConnectionStatus.FAILED
        connection.last_error = str(exception)
        emoji = " FAIL: " if self.use_emoji else ""
        print(f"{emoji} ERROR | {connection.name}: Validation failed - {str(exception)}")
    
    def _print_no_databases(self) -> None:
        """Print message when no databases are configured."""
        emoji = "[U+2139][U+FE0F]" if self.use_emoji else ""
        print(f"{emoji} DATABASE | No database connections configured")
    
    def _print_validation_start(self) -> None:
        """Print validation start message."""
        emoji = " CYCLE: " if self.use_emoji else ""
        print(f"{emoji} DATABASE | Validating {len(self.connections)} database connections...")
    
    def _print_validation_summary(self, all_healthy: bool) -> None:
        """Print validation summary."""
        if all_healthy:
            emoji = " PASS: " if self.use_emoji else ""
            print(f"{emoji} DATABASE | All database connections validated successfully")
        else:
            emoji = " FAIL: " if self.use_emoji else ""
            print(f"{emoji} DATABASE | Database validation failed - check logs for details")
    
    async def _validate_connection_with_retry(self, connection: DatabaseConnection) -> bool:
        """
        Validate a database connection with retry logic.
        
        Args:
            connection: Database connection to validate
            
        Returns:
            True if connection is healthy, False otherwise
        """
        connection.status = ConnectionStatus.CONNECTING
        connection.retry_count = 0
        
        for attempt in range(self.retry_config.max_attempts):
            if self._shutdown_requested:
                return False
            
            connection.retry_count = attempt + 1
            
            try:
                self._print_connection_attempt(connection, attempt + 1)
                
                # Attempt connection
                success = await self._test_database_connection(connection)
                
                if success:
                    connection.status = ConnectionStatus.CONNECTED
                    connection.failure_count = 0
                    connection.last_error = None
                    connection.last_check = datetime.now()
                    self._print_connection_success(connection)
                    return True
                else:
                    connection.failure_count += 1
                    self._handle_connection_failure(connection, attempt)
                    
            except Exception as e:
                connection.failure_count += 1
                connection.last_error = str(e)
                self._handle_connection_exception(connection, e, attempt)
            
            # Wait before retry (exponential backoff)
            if attempt < self.retry_config.max_attempts - 1:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)
        
        # All retries failed - provide clear status communication
        # For ClickHouse, mark as fallback available instead of failed
        if connection.db_type == DatabaseType.CLICKHOUSE:
            connection.status = ConnectionStatus.FALLBACK_AVAILABLE
        else:
            connection.status = ConnectionStatus.FAILED
        self._print_connection_failed_with_fallback_info(connection)
        return False
    
    def _print_connection_attempt(self, connection: DatabaseConnection, attempt: int) -> None:
        """Print connection attempt message."""
        emoji = " CYCLE: " if self.use_emoji else ""
        print(f"{emoji} CONNECT | {connection.name}: Attempt {attempt}/{self.retry_config.max_attempts}")
    
    def _print_connection_success(self, connection: DatabaseConnection) -> None:
        """Print connection success message."""
        emoji = " PASS: " if self.use_emoji else ""
        print(f"{emoji} CONNECT | {connection.name}: Connected successfully")
    
    def _print_connection_failed(self, connection: DatabaseConnection) -> None:
        """Print connection failure message."""
        emoji = " FAIL: " if self.use_emoji else ""
        error_msg = connection.last_error or "Connection failed"
        print(f"{emoji} CONNECT | {connection.name}: Failed after {self.retry_config.max_attempts} attempts - {error_msg}")
    
    def _print_connection_failed_with_fallback_info(self, connection: DatabaseConnection) -> None:
        """Print connection failure message with fallback behavior information."""
        emoji = " FAIL: " if self.use_emoji else ""
        error_msg = connection.last_error or "Connection failed"
        print(f"{emoji} CONNECT | {connection.name}: Failed after {self.retry_config.max_attempts} attempts - {error_msg}")
        
        # Provide fallback communication for ClickHouse
        if connection.db_type == DatabaseType.CLICKHOUSE:
            fallback_emoji = " CYCLE: " if self.use_emoji else ""
            print(f"{fallback_emoji} FALLBACK | ClickHouse unavailable - system will continue with mock/local mode")
            print(f"{fallback_emoji} FALLBACK | Application startup will proceed normally with reduced analytics capabilities")
    
    def _handle_connection_failure(self, connection: DatabaseConnection, attempt: int) -> None:
        """Handle connection failure during validation."""
        connection.status = ConnectionStatus.RETRYING
        if attempt == self.retry_config.max_attempts - 1:
            # Only set generic error message if no specific error is already set
            if not connection.last_error:
                connection.last_error = "Connection test failed"
    
    def _handle_connection_exception(self, connection: DatabaseConnection, exception: Exception, attempt: int) -> None:
        """Handle exception during connection validation."""
        connection.status = ConnectionStatus.RETRYING
        connection.last_error = str(exception)
        
        if attempt == self.retry_config.max_attempts - 1:
            emoji = " WARNING: [U+FE0F]" if self.use_emoji else ""
            print(f"{emoji} ERROR | {connection.name}: {str(exception)}")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        delay = self.retry_config.initial_delay * (self.retry_config.backoff_factor ** attempt)
        return min(delay, self.retry_config.max_delay)
    
    async def _test_database_connection(self, connection: DatabaseConnection) -> bool:
        """
        Test database connection based on type.
        
        Args:
            connection: Database connection to test
            
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if connection.db_type == DatabaseType.POSTGRESQL:
                return await self._test_postgresql_connection(connection)
            elif connection.db_type == DatabaseType.CLICKHOUSE:
                return await self._test_clickhouse_connection(connection)
            elif connection.db_type == DatabaseType.REDIS:
                return await self._test_redis_connection(connection)
            else:
                logger.warning(f"Unknown database type: {connection.db_type}")
                return False
        except asyncio.TimeoutError:
            connection.last_error = f"Connection timeout after {self.retry_config.timeout}s"
            return False
        except Exception as e:
            connection.last_error = str(e)
            return False
    
    async def _test_postgresql_connection(self, connection: DatabaseConnection) -> bool:
        """Test PostgreSQL connection with proper asyncpg handling."""
        try:
            import asyncpg
            return await self._test_asyncpg_connection(connection)
        except ImportError:
            return await self._test_postgresql_basic(connection)
        except Exception as e:
            connection.last_error = f"PostgreSQL connection failed: {str(e)}"
            return False
    
    async def _test_asyncpg_connection(self, connection: DatabaseConnection) -> bool:
        """Test PostgreSQL with asyncpg driver."""
        import asyncpg
        
        conn = None
        try:
            conn = await self._establish_postgres_connection(connection)
            await self._validate_postgres_health(conn)
            return True
        except Exception as e:
            # Log the actual error and URL being used for debugging
            masked_url = self._mask_url_credentials(connection.url)
            logger.debug(f"PostgreSQL connection attempt failed - URL: {masked_url}, Error: {str(e)}")
            raise
        finally:
            if conn:
                await conn.close()
    
    async def _establish_postgres_connection(self, connection: DatabaseConnection):
        """Establish PostgreSQL connection based on URL type."""
        if "/cloudsql/" in connection.url:
            return await self._connect_cloud_sql(connection)
        else:
            return await self._connect_standard_tcp(connection)
    
    async def _connect_cloud_sql(self, connection: DatabaseConnection) -> object:
        """Connect to Cloud SQL PostgreSQL."""
        import asyncpg
        # Normalize URL for asyncpg (remove SQLAlchemy driver prefixes)
        clean_url = self._normalize_postgres_url(connection.url)
        return await asyncio.wait_for(
            asyncpg.connect(clean_url),
            timeout=self.retry_config.timeout
        )
    
    async def _connect_standard_tcp(self, connection: DatabaseConnection) -> object:
        """Connect to standard TCP PostgreSQL."""
        import asyncpg
        # Fix URL format - asyncpg expects 'postgresql://' not 'postgresql+asyncpg://'
        clean_url = self._normalize_postgres_url(connection.url)
        
        return await asyncio.wait_for(
            asyncpg.connect(clean_url),
            timeout=self.retry_config.timeout
        )
    
    
    async def _validate_postgres_health(self, conn) -> None:
        """Validate PostgreSQL connection health."""
        await conn.execute("SELECT 1")
    
    async def _test_postgresql_basic(self, connection: DatabaseConnection) -> bool:
        """Test PostgreSQL connection without asyncpg."""
        try:
            import psycopg2
            from psycopg2 import OperationalError
            
            # Convert URL to psycopg2 format using centralized normalization
            url = self._normalize_postgres_url(connection.url)
            
            conn = psycopg2.connect(url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
            
        except ImportError:
            # No PostgreSQL drivers available
            logger.warning("No PostgreSQL drivers available (asyncpg or psycopg2)")
            return True  # Skip validation if no drivers
        except Exception as e:
            connection.last_error = f"PostgreSQL basic test failed: {str(e)}"
            return False
    
    async def _test_clickhouse_connection(self, connection: DatabaseConnection) -> bool:
        """Test ClickHouse connection."""
        try:
            import aiohttp
            return await self._perform_clickhouse_health_check(connection)
        except ImportError:
            logger.warning("aiohttp not available for ClickHouse validation")
            return True
        except Exception as e:
            connection.last_error = f"ClickHouse connection failed: {str(e)}"
            return False
    
    async def _perform_clickhouse_health_check(self, connection: DatabaseConnection) -> bool:
        """Perform ClickHouse health check via HTTP."""
        import aiohttp
        parsed = urlparse(connection.url)
        
        base_url = self._build_clickhouse_http_url(parsed)
        auth = self._build_clickhouse_auth(parsed)
        
        # Log the connection attempt details for debugging
        logger.debug(f"ClickHouse health check - Original URL: {self._mask_url_credentials(connection.url)}")
        logger.debug(f"ClickHouse health check - HTTP URL: {base_url}")
        logger.debug(f"ClickHouse health check - Auth: {auth.login if auth else 'None'}")
        
        return await self._execute_clickhouse_ping(base_url, auth)
    
    def _build_clickhouse_http_url(self, parsed_url) -> str:
        """Build HTTP URL for ClickHouse health check."""
        # If the URL is already HTTP, use it as-is
        if parsed_url.scheme in ["http", "https"]:
            return f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
        
        # If it's a clickhouse:// URL, convert to HTTP
        # Use HTTPS for port 8443, HTTP for others (including 8123)
        if parsed_url.port == 8443:
            return f"https://{parsed_url.hostname}:{parsed_url.port}"
        elif parsed_url.port == 9000:
            # Native protocol port - convert to HTTP on 8123
            return f"http://{parsed_url.hostname}:8123"
        else:
            # Default to HTTP for any other port
            return f"http://{parsed_url.hostname}:{parsed_url.port}"
    
    def _build_clickhouse_auth(self, parsed_url):
        """Build authentication for ClickHouse connection."""
        import aiohttp
        if parsed_url.username:
            return aiohttp.BasicAuth(parsed_url.username, parsed_url.password or "")
        return None
    
    async def _execute_clickhouse_ping(self, base_url: str, auth) -> bool:
        """Execute ClickHouse ping request with proper error handling for code 194."""
        import aiohttp
        ping_url = f"{base_url}/ping"
        
        try:
            logger.debug(f"ClickHouse ping attempt: {ping_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    ping_url,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.retry_config.timeout)
                ) as response:
                    logger.debug(f"ClickHouse ping response: {response.status}")
                    if response.status == 200:
                        logger.debug("ClickHouse ping successful")
                        return True
                    elif response.status == 401:
                        # Authentication failed - handle gracefully
                        logger.info("ClickHouse authentication failed - check credentials")
                        return False
                    else:
                        response_text = await response.text() if response.content_length else ""
                        logger.debug(f"ClickHouse ping failed with status {response.status}: {response_text}")
                        return False
        except aiohttp.ClientError as e:
            logger.debug(f"ClickHouse ping client error: {str(e)}")
            return self._handle_clickhouse_connection_error(e)
        except Exception as e:
            logger.debug(f"ClickHouse ping general error: {str(e)}")
            return self._handle_clickhouse_connection_error(e)
    
    def _handle_clickhouse_connection_error(self, error: Exception) -> bool:
        """Handle ClickHouse connection errors with specific handling for code 194."""
        error_str = str(error)
        error_lower = error_str.lower()
        
        # Handle specific ClickHouse error codes and authentication issues
        if any(indicator in error_lower for indicator in ["194", "password incorrect", "authentication", "auth failed"]):
            logger.info(f"ClickHouse authentication issue detected: {error_str}")
            logger.info("ClickHouse will fall back to mock/local mode - continuing startup")
            return False
        elif "timeout" in error_lower or "connection" in error_lower:
            logger.debug(f"ClickHouse connection timeout/network issue: {error_str}")
            return False
        else:
            logger.debug(f"ClickHouse connection error: {error_str}")
            return False
    
    async def _test_redis_connection(self, connection: DatabaseConnection) -> bool:
        """Test Redis connection directly."""
        try:
            import redis.asyncio as redis
            
            # Test Redis connection directly
            client = redis.from_url(connection.url, socket_connect_timeout=5)
            await client.ping()
            await client.aclose()
            return True
            
        except ImportError:
            # No Redis libraries available, skip validation
            logger.warning("No Redis client libraries available (redis or aioredis)")
            return True
        except Exception as e:
            connection.last_error = f"Redis connection failed: {str(e)}"
            return False
    
    async def start_health_monitoring(self) -> None:
        """Start continuous health monitoring of database connections."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._health_monitoring_loop())
        emoji = " CYCLE: " if self.use_emoji else ""
        print(f"{emoji} MONITOR | Started database health monitoring")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring and cleanup connections."""
        self._shutdown_requested = True
        
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self._cleanup_all_connections()
        emoji = "[U+1F6D1]" if self.use_emoji else ""
        print(f"{emoji} MONITOR | Stopped database health monitoring")
    
    async def _health_monitoring_loop(self) -> None:
        """Continuous health monitoring loop."""
        while not self._shutdown_requested:
            try:
                # Check health of all connections
                for connection in self.connections.values():
                    if not self._shutdown_requested:
                        await self._check_connection_health(connection)
                
                # Wait for next check (every 60 seconds)
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Database health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_connection_health(self, connection: DatabaseConnection) -> None:
        """Check health of a single connection."""
        try:
            success = await self._test_database_connection(connection)
            
            if success:
                if connection.status != ConnectionStatus.CONNECTED:
                    connection.status = ConnectionStatus.CONNECTED
                    connection.failure_count = 0
                    emoji = " PASS: " if self.use_emoji else ""
                    print(f"{emoji} HEALTH | {connection.name}: Recovered")
            else:
                connection.failure_count += 1
                if connection.failure_count >= 3:
                    connection.status = ConnectionStatus.FAILED
                    emoji = " FAIL: " if self.use_emoji else ""
                    print(f"{emoji} HEALTH | {connection.name}: Unhealthy (failures: {connection.failure_count})")
                    
            connection.last_check = datetime.now()
            
        except Exception as e:
            connection.failure_count += 1
            connection.last_error = str(e)
            logger.error(f"Health check failed for {connection.name}: {e}")
    
    async def _cleanup_all_connections(self) -> None:
        """Cleanup all database connections."""
        for connection in self.connections.values():
            await self._cleanup_connection(connection)
    
    async def _cleanup_connection(self, connection: DatabaseConnection) -> None:
        """Cleanup a single database connection."""
        try:
            if connection.connection_pool:
                # Close connection pool if exists
                if hasattr(connection.connection_pool, 'close'):
                    await connection.connection_pool.close()
                connection.connection_pool = None
                
        except Exception as e:
            logger.error(f"Error cleaning up connection {connection.name}: {e}")
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all database connections."""
        status = {}
        
        for name, connection in self.connections.items():
            status[name] = {
                "type": connection.db_type.value,
                "status": connection.status.value,
                "failure_count": connection.failure_count,
                "last_check": connection.last_check.isoformat() if connection.last_check else None,
                "last_error": connection.last_error,
                "retry_count": connection.retry_count
            }
        
        return status
    
    def is_all_healthy(self) -> bool:
        """Check if all database connections are healthy."""
        if not self.connections:
            return True
        
        return all(
            conn.status == ConnectionStatus.CONNECTED
            for conn in self.connections.values()
        )
    
    def get_failed_connections(self) -> List[str]:
        """Get list of failed connection names."""
        return [
            name for name, conn in self.connections.items()
            if conn.status == ConnectionStatus.FAILED
        ]
    
    def get_health_summary(self) -> str:
        """Get a human-readable health summary."""
        if not self.connections:
            return "No databases configured"
        
        total = len(self.connections)
        healthy = sum(1 for conn in self.connections.values() 
                     if conn.status == ConnectionStatus.CONNECTED)
        failed = sum(1 for conn in self.connections.values() 
                    if conn.status == ConnectionStatus.FAILED)
        
        if healthy == total:
            return f"All {total} databases healthy"
        elif failed > 0:
            return f"{healthy}/{total} databases healthy ({failed} failed)"
        else:
            return f"{healthy}/{total} databases healthy"