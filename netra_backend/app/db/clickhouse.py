"""
ClickHouse Database Module - Real by Default
Provides clear separation between real and mock ClickHouse clients

Business Value Justification (BVJ):
- Segment: Growth & Enterprise  
- Business Goal: Ensure reliable analytics data collection
- Value Impact: 100% analytics accuracy for decision making
- Revenue Impact: Enables data-driven pricing optimization (+$15K MRR)
"""

import asyncio
import hashlib
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.logging_config import central_logger as logger


class ClickHouseCache:
    """Simple cache for ClickHouse query results with TTL support."""
    
    def __init__(self, max_size: int = 500):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from query and parameters."""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        if params:
            params_str = str(sorted(params.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"ch:{query_hash}:p:{params_hash}"
        return f"ch:{query_hash}"
    
    def get(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached result if not expired."""
        key = self._generate_key(query, params)
        entry = self.cache.get(key)
        
        if entry and time.time() < entry["expires_at"]:
            self._hits += 1
            logger.debug(f"ClickHouse cache hit for query: {query[:50]}...")
            return entry["result"]
        elif entry:
            del self.cache[key]
        
        self._misses += 1
        return None
    
    def set(self, query: str, result: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None, ttl: float = 300) -> None:
        """Cache query result with TTL."""
        if len(self.cache) >= self.max_size:
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k]["created_at"])[:10]
            for k in oldest_keys:
                del self.cache[k]
        
        key = self._generate_key(query, params)
        self.cache[key] = {
            "result": result,
            "created_at": time.time(),
            "expires_at": time.time() + ttl
        }
        logger.debug(f"Cached ClickHouse result for query: {query[:50]}... (TTL: {ttl}s)")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        logger.info("ClickHouse cache cleared")


# Global cache instance
_clickhouse_cache = ClickHouseCache()


# Mock client removed - NO MOCKS IN DEV MODE
# Real services only per CLAUDE.md section 2.4


def _is_testing_environment() -> bool:
    """Check if running in testing environment."""
    from netra_backend.app.core.isolated_environment import get_env
    
    # Check TESTING environment variable directly for pytest compatibility
    if get_env().get("TESTING"):
        return True
    # Fallback to configuration-based detection
    config = get_configuration()
    return config.environment == "testing"

def _is_real_database_test() -> bool:
    """Check if this is a test that explicitly requires real database connections."""
    import sys
    from netra_backend.app.core.isolated_environment import get_env
    
    # Check if we're running under pytest
    if 'pytest' not in sys.modules:
        return False
    
    # Check for environment variable that indicates real database test
    # This will be set by the pytest collection hook for real_database marked tests
    if get_env().get("PYTEST_REAL_DATABASE_TEST", "").lower() == "true":
        return True
    
    # Alternative approach: check the test name from PYTEST_CURRENT_TEST
    current_test = get_env().get("PYTEST_CURRENT_TEST", "")
    if "real_database" in current_test.lower():
        return True
    
    return False

def _should_disable_clickhouse_for_tests() -> bool:
    """Check if ClickHouse should be disabled for the current test context."""
    from netra_backend.app.core.isolated_environment import get_env
    
    # Always check if we're in a real database test first
    if _is_real_database_test():
        return False  # Allow real ClickHouse for @pytest.mark.real_database tests
    
    # Check test framework ClickHouse disable settings for regular tests
    clickhouse_disabled_by_framework = (
        get_env().get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        get_env().get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    return clickhouse_disabled_by_framework

def use_mock_clickhouse() -> bool:
    """Determine if mock ClickHouse should be used.
    
    NO MOCKS IN DEV MODE - only in testing environment.
    Development MUST use real ClickHouse connections.
    Tests marked with @pytest.mark.real_database should attempt real connections.
    """
    # Check if we're in a testing environment AND ClickHouse is disabled for this context
    return _is_testing_environment() and _should_disable_clickhouse_for_tests()


def _get_unified_config():
    """Get unified configuration instance."""
    return get_configuration()

def _extract_clickhouse_config(config):
    """Extract appropriate ClickHouse configuration from unified config based on mode."""
    # Use HTTP config for local development, HTTPS for production/remote
    if config.clickhouse_mode == "local" or config.environment == "development":
        # Use HTTP port (8123) for local development
        return config.clickhouse_http
    else:
        # Use HTTPS port (8443) for production/staging
        return config.clickhouse_https

def get_clickhouse_config():
    """Get ClickHouse configuration from unified config system.
    
    Returns appropriate config for real ClickHouse connection.
    Uses HTTP (port 8123) for local development, HTTPS (port 8443) for production.
    """
    config = _get_unified_config()
    return _extract_clickhouse_config(config)


# No-op test client for testing environments where ClickHouse is disabled

class NoOpClickHouseClient:
    """No-op ClickHouse client for testing environments.
    
    This provides the same interface as a real ClickHouse client but performs no operations.
    Allows unit tests to run without external dependencies while maintaining interface compatibility.
    """
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute no-op query - returns empty result for testing."""
        logger.debug(f"[ClickHouse NoOp] Simulated query execution: {query[:50]}...")
        return []
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute no-op query (alias for execute)."""
        return await self.execute(query, params)
    
    async def test_connection(self) -> bool:
        """Simulate successful connection test."""
        return True
    
    async def disconnect(self) -> None:
        """No-op disconnect."""
        pass

@asynccontextmanager
async def _create_test_noop_client():
    """Create a no-op ClickHouse client for testing environments.
    
    This client provides the same interface as real ClickHouse clients but performs no operations,
    allowing unit tests to run without external dependencies.
    """
    client = NoOpClickHouseClient()
    logger.debug("[ClickHouse] Using no-op client for testing environment")
    try:
        yield client
    finally:
        await client.disconnect()

@asynccontextmanager
async def get_clickhouse_client():
    """Get ClickHouse client - REAL connections only in dev/prod.
    
    NO MOCKS IN DEV MODE - development must use real ClickHouse.
    Tests marked with @pytest.mark.real_database will attempt real connections
    and raise connection errors that can be handled gracefully by the test.
    
    Usage:
        async with get_clickhouse_client() as client:
            results = await client.execute("SELECT * FROM events")
    """
    from netra_backend.app.core.isolated_environment import get_env
    
    if use_mock_clickhouse():
        # Only for regular testing environment where ClickHouse is explicitly disabled
        # Provide a no-op client that allows tests to run without external dependencies
        async with _create_test_noop_client() as client:
            yield client
            return
    
    # Use real client in development, production, and real database tests
    environment = get_env().get("ENVIRONMENT", "development").lower()
    client_timeout = 10.0 if environment in ["staging", "development"] else 30.0
    
    try:
        # Create real client with timeout protection handled at a lower level
        async for client in _create_real_client():
            yield client
            
    except (asyncio.TimeoutError, ConnectionError) as e:
        # In test environment with real_database mark, let the test handle the connection failure
        if _is_testing_environment() and _is_real_database_test():
            logger.debug(f"[ClickHouse] Real database test connection failed: {e}")
            raise  # Let the test handle this gracefully
        
        # NO MOCK FALLBACK for dev/prod - fail fast
        logger.error(f"[ClickHouse] Connection failed in {environment}: {e}")
        raise RuntimeError(f"ClickHouse connection required in {environment} mode. Please ensure ClickHouse is running.") from e


def _get_connection_config():
    """Get ClickHouse connection configuration."""
    config = get_clickhouse_config()
    app_config = get_configuration()
    # Never use HTTPS for localhost or Docker container connections to avoid SSL errors
    is_local_or_docker = config.host in ["localhost", "127.0.0.1", "::1", "clickhouse", "netra-clickhouse"]
    # Also check if we're in development environment
    is_development = app_config.environment == "development"
    use_secure = app_config.clickhouse_mode != "local" and not is_local_or_docker and not is_development
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
    """Test connection and yield client with enhanced timeout handling and retry logic.
    
    Enhanced with async generator protection against corruption and staging-specific timeouts.
    """
    import asyncio
    from netra_backend.app.core.isolated_environment import get_env
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    client_yielded = False
    
    try:
        # CRITICAL FIX: Increase timeouts for staging to prevent connection failures
        if environment == "staging":
            timeout = 15.0  # Increased from 5 to 15 seconds for staging
        elif environment == "production":
            timeout = 20.0  # Longer timeout for production
        else:
            timeout = 5.0   # Standard timeout for development
            
        # Shield connection test from cancellation
        await asyncio.shield(asyncio.wait_for(client.test_connection(), timeout=timeout))
        logger.info(f"[ClickHouse] REAL connection established in {environment} environment")
        client_yielded = True
        yield client
    except asyncio.CancelledError:
        # Handle task cancellation gracefully
        logger.warning(f"[ClickHouse] Connection test cancelled for {environment}")
        # If already yielded, let cleanup proceed normally
        if client_yielded:
            raise
        # Otherwise, re-raise after potential cleanup
        raise
    except asyncio.TimeoutError as e:
        logger.error(f"[ClickHouse] Connection test timeout after {timeout} seconds in {environment}")
        # In staging/development, this is expected - don't raise, let graceful degradation handle it
        if environment in ["staging", "development"]:
            logger.warning(f"[ClickHouse] Connection timeout in {environment} environment - graceful degradation")
            raise ConnectionError(f"ClickHouse connection timeout after {timeout}s in {environment}") from e
        raise asyncio.TimeoutError("ClickHouse connection timeout") from e
    except GeneratorExit:
        # Handle generator cleanup silently
        pass

def _log_connection_attempt(config, use_secure: bool):
    """Log ClickHouse connection attempt."""
    logger.info(f"[ClickHouse] Connecting to instance at {config.host}:{config.port} (secure={use_secure})")

def _create_intercepted_client(config, use_secure: bool):
    """Create ClickHouse client with query interceptor."""
    base_client = _create_base_client(config, use_secure)
    return ClickHouseQueryInterceptor(base_client)

def _handle_connection_error(e: Exception):
    """Handle ClickHouse connection error with environment-aware handling."""
    from netra_backend.app.core.isolated_environment import get_env
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    
    logger.error(f"[ClickHouse] REAL connection failed in {environment}: {str(e)}")
    
    # CRITICAL FIX: ClickHouse is always optional in staging - never block startup
    if environment == "staging":
        logger.warning("[ClickHouse] Connection failed in staging (optional service) - using graceful degradation")
        return  # Never raise in staging - ClickHouse is always optional
    
    # In development, ClickHouse is also optional unless explicitly required
    if environment == "development":
        clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
        if not clickhouse_required:
            logger.warning("[ClickHouse] Connection failed in development but not required - graceful degradation")
            return
    
    # Only raise in production or when explicitly required
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
    With graceful degradation for optional environments.
    """
    from netra_backend.app.core.isolated_environment import get_env
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    
    config, use_secure = await _setup_real_client()
    try:
        async for c in _connect_and_yield_client(config, use_secure):
            yield c
    except Exception as e:
        _handle_connection_error(e)
        # NO MOCK FALLBACK - fail fast in dev/staging mode
        logger.error(f"[ClickHouse] Connection failed in {environment}: {e}")
        raise RuntimeError(f"ClickHouse connection required in {environment} mode. Please ensure ClickHouse is running.") from e


class ClickHouseService:
    """Service class for ClickHouse operations.
    
    Provides high-level methods with clear real/mock distinction,
    circuit breaker protection, retry logic, and caching.
    """
    
    def __init__(self, force_mock: bool = False):
        """Initialize service.
        
        Args:
            force_mock: Force use of mock client (for testing only)
        """
        self.force_mock = force_mock
        self._client = None
        self._circuit_breaker = UnifiedCircuitBreaker(
            name="clickhouse",
            failure_threshold=5,
            recovery_timeout=30
        )
        self._metrics = {"queries": 0, "failures": 0, "timeouts": 0}
    
    # Mock client initialization removed - NO MOCKS IN DEV MODE

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
        # Never use HTTPS for localhost connections to avoid SSL errors
        is_localhost = config.host in ["localhost", "127.0.0.1", "::1"]
        use_secure = not is_localhost and config.port == 8443
        params['database'] = config.database
        params['secure'] = use_secure
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
        """Initialize real ClickHouse client with enhanced retry logic and graceful failure."""
        import asyncio
        from netra_backend.app.core.isolated_environment import get_env
        
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        logger.info("[ClickHouse Service] Initializing with REAL client")
        config = get_clickhouse_config()
        
        # CRITICAL FIX: Increase retries and timeouts for staging to prevent connection failures
        if environment == "staging":
            max_retries = 3   # Increased retries for staging
            timeout = 15.0    # Longer timeout for staging
        elif environment == "production":
            max_retries = 3   # Full retries in production
            timeout = 20.0    # Longer timeout for production
        else:
            max_retries = 1   # Single attempt in development
            timeout = 5.0     # Fast timeout for development
        
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                base_client = self._build_clickhouse_database(config)
                self._client = ClickHouseQueryInterceptor(base_client)
                # Test connection with environment-appropriate timeout
                await asyncio.wait_for(self._client.test_connection(), timeout=timeout)
                logger.info(f"[ClickHouse Service] Connection established on attempt {attempt + 1} in {environment} environment")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    import random
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(f"[ClickHouse Service] Connection attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[ClickHouse Service] All {max_retries} connection attempts failed in {environment}: {e}")
                    
                    # CRITICAL FIX: Enhanced fallback logic for optional environments
                    if environment in ["staging", "development"]:
                        clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
                        if not clickhouse_required:
                            logger.warning(f"[ClickHouse Service] ClickHouse optional in {environment}, continuing without it")
                            # Don't initialize mock - let service handle graceful degradation
                            return
                    
                    raise

    async def initialize(self):
        """Initialize ClickHouse connection with timeout protection."""
        import asyncio
        from netra_backend.app.core.isolated_environment import get_env
        
        if self.force_mock or use_mock_clickhouse():
            # In testing environment with ClickHouse disabled, use NoOp client
            self._client = NoOpClickHouseClient()
            logger.info("[ClickHouse Service] Initialized with NoOp client for testing environment")
            return
        
        # ALWAYS use real client in development and production
        environment = get_env().get("ENVIRONMENT", "development").lower()
        init_timeout = 10.0 if environment in ["staging", "development"] else 30.0
        
        try:
            await asyncio.wait_for(self._initialize_real_client(), timeout=init_timeout)
        except asyncio.TimeoutError as e:
            # NO MOCK FALLBACK - fail fast in dev mode
            logger.error(f"[ClickHouse Service] Initialization timeout after {init_timeout}s")
            raise ConnectionError(f"ClickHouse initialization timeout after {init_timeout}s. Please ensure ClickHouse is running.") from e
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query with circuit breaker protection and caching."""
        # Check cache first for read queries
        if query.lower().strip().startswith("select"):
            cached_result = _clickhouse_cache.get(query, params)
            if cached_result is not None:
                return cached_result
        
        try:
            self._metrics["queries"] += 1
            result = await self._execute_with_circuit_breaker(query, params)
            
            # Cache successful read results
            if query.lower().strip().startswith("select") and result:
                _clickhouse_cache.set(query, result, params, ttl=300)
            
            return result
        except Exception as e:
            self._metrics["failures"] += 1
            logger.error(f"ClickHouse query failed: {e}")
            raise
    
    async def _execute_with_circuit_breaker(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query with circuit breaker protection."""
        async def _execute():
            if not self._client:
                await self.initialize()
            return await self._client.execute(query, params)
        
        try:
            return await self._circuit_breaker.call(_execute)
        except Exception as e:
            # Try to return cached data as fallback
            if query.lower().strip().startswith("select"):
                cached_result = _clickhouse_cache.get(query, params)
                if cached_result is not None:
                    logger.info("Returning cached data due to circuit breaker failure")
                    return cached_result
            raise
    
    async def close(self):
        """Close ClickHouse connection."""
        if self._client:
            await self._client.disconnect()
            self._client = None
    
    async def ping(self) -> bool:
        """Test ClickHouse connection availability."""
        if not self._client:
            await self.initialize()
        # Check for mock/NoOp clients
        try:
            from test_framework.fixtures.clickhouse_fixtures import MockClickHouseDatabase
            if isinstance(self._client, (MockClickHouseDatabase, NoOpClickHouseClient)):
                return True
        except ImportError:
            if isinstance(self._client, NoOpClickHouseClient):
                return True
        try:
            await self._client.test_connection()
            return True
        except Exception:
            return False
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, 
                          timeout: Optional[float] = None, max_memory_usage: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute query with optional timeout and memory limits (alias for execute)."""
        return await self.execute(query, params)
    
    async def execute_with_retry(self, query: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> List[Dict[str, Any]]:
        """Execute query with retry logic for critical operations."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(2.0 * (2 ** (attempt - 1)), 8.0)  # Exponential backoff, max 8s
                    logger.info(f"Retrying ClickHouse query (attempt {attempt + 1}/{max_retries + 1}) after {delay}s")
                    await asyncio.sleep(delay)
                
                result = await self.execute(query, params)
                
                if attempt > 0:
                    logger.info(f"ClickHouse query succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    logger.error(f"ClickHouse query failed after {max_retries + 1} attempts")
                    break
        
        raise last_exception
    
    async def batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Insert batch of data into ClickHouse table."""
        if not self._client:
            await self.initialize()
        
        # Check for mock/NoOp clients
        try:
            from test_framework.fixtures.clickhouse_fixtures import MockClickHouseDatabase
            if isinstance(self._client, (MockClickHouseDatabase, NoOpClickHouseClient)):
                # Mock implementation - just log the operation
                logger.info(f"[MOCK ClickHouse] Batch insert to {table_name}: {len(data)} rows")
                return
        except ImportError:
            if isinstance(self._client, NoOpClickHouseClient):
                # NoOp implementation - just log the operation
                logger.info(f"[NoOp ClickHouse] Batch insert to {table_name}: {len(data)} rows")
                return
        
        # For real implementation, we'll use a simple INSERT query
        # This is a basic implementation - could be enhanced with proper bulk insert
        if not data:
            return
        
        # Get column names from first row
        columns = list(data[0].keys())
        
        # Build INSERT query
        columns_str = ", ".join(columns)
        values_placeholder = ", ".join([f"%({col})s" for col in columns])
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_placeholder})"
        
        # Execute insert for each row (basic implementation)
        for row in data:
            await self.execute(query, row)
    
    async def cleanup(self) -> None:
        """Cleanup method (alias for close) for test compatibility."""
        await self.close()
    
    @property
    def is_mock(self) -> bool:
        """Check if using mock client."""
        # Import here to avoid circular imports and maintain clean separation
        try:
            from test_framework.fixtures.clickhouse_fixtures import MockClickHouseDatabase
            return isinstance(self._client, (MockClickHouseDatabase, NoOpClickHouseClient))
        except ImportError:
            # If test fixtures not available, check for NoOp client only
            return isinstance(self._client, NoOpClickHouseClient)
    
    @property
    def is_real(self) -> bool:
        """Check if using real client."""
        return not self.is_mock and self._client is not None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return _clickhouse_cache.stats()
    
    def clear_cache(self) -> None:
        """Clear query cache."""
        _clickhouse_cache.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection and query metrics."""
        try:
            cb_state = getattr(self._circuit_breaker, 'state', 'unknown')
            cb_state_name = cb_state.name if hasattr(cb_state, 'name') else str(cb_state)
        except:
            cb_state_name = 'unknown'
            
        return {
            "queries_executed": self._metrics["queries"],
            "query_failures": self._metrics["failures"], 
            "timeout_errors": self._metrics["timeouts"],
            "circuit_breaker_state": cb_state_name,
            "cache_stats": _clickhouse_cache.stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with circuit breaker status."""
        try:
            # Test basic connectivity
            result = await self.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "connectivity": "ok" if result else "degraded", 
                "metrics": self.get_metrics(),
                "cache_stats": _clickhouse_cache.stats()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": self.get_metrics(),
                "cache_stats": _clickhouse_cache.stats()
            }
    
    async def check_health(self) -> Dict[str, Any]:
        """Alias for health_check for backward compatibility."""
        return await self.health_check()


# Global service instance for easy access
_global_service = None

def get_clickhouse_service() -> ClickHouseService:
    """Get global ClickHouse service instance."""
    global _global_service
    if _global_service is None:
        _global_service = ClickHouseService()
    return _global_service

async def create_agent_state_history_table():
    """Create ClickHouse agent_state_history table for time-series analytics.
    
    This table stores completed agent runs for historical analysis and performance metrics.
    Optimized for time-series queries and analytics dashboards.
    """
    # Use canonical SSOT implementation
    async with get_clickhouse_client() as client:
        # Create the agent state history table with optimal partitioning
        create_table_query = """
        CREATE TABLE IF NOT EXISTS agent_state_history (
        -- Primary identifiers
        run_id String,
        thread_id String,
        user_id Nullable(String),
        snapshot_id String,
        
        -- Time series data (partitioned by date)
        created_at DateTime64(3) DEFAULT now64(3),
        completed_at Nullable(DateTime64(3)),
        
        -- Agent execution metadata
        agent_phase String DEFAULT 'unknown',
        checkpoint_type String DEFAULT 'final',
        execution_status String DEFAULT 'completed',
        
        -- State and performance data
        state_size_kb UInt32,
        step_count UInt16 DEFAULT 0,
        execution_time_ms Nullable(UInt32),
        memory_usage_mb Nullable(UInt16),
        
        -- State classification for analytics
        state_complexity Enum8('simple'=1, 'moderate'=2, 'complex'=3, 'very_complex'=4),
        recovery_point Bool DEFAULT false,
        
        -- Compressed state data for recovery (if needed)
        state_data_compressed Nullable(String),
        compression_ratio Nullable(Float32),
        
        -- Analytics dimensions
        date Date MATERIALIZED toDate(created_at),
        hour UInt8 MATERIALIZED toHour(created_at)
    )
    ENGINE = MergeTree()
    PARTITION BY date
    ORDER BY (run_id, created_at)
    TTL created_at + INTERVAL 90 DAY
    SETTINGS index_granularity = 8192
    """
    
        try:
            await client.execute(create_table_query)
            logger.info("[ClickHouse] agent_state_history table created successfully")
            
            # Create indexes for common query patterns
            await _create_agent_state_indexes(client)
            
            return True
        except Exception as e:
            logger.error(f"[ClickHouse] Failed to create agent_state_history table: {e}")
            return False

async def _create_agent_state_indexes(client):
    """Create optimized indexes for agent state queries."""
    indexes = [
        # Index for user analytics
        "ALTER TABLE agent_state_history ADD INDEX idx_user_date (user_id, date) TYPE minmax GRANULARITY 1",
        # Index for performance analysis
        "ALTER TABLE agent_state_history ADD INDEX idx_execution_time (execution_time_ms) TYPE minmax GRANULARITY 1",
        # Index for thread-based queries
        "ALTER TABLE agent_state_history ADD INDEX idx_thread_phase (thread_id, agent_phase) TYPE set(100) GRANULARITY 1"
    ]
    
    for index_query in indexes:
        try:
            await client.execute(index_query)
        except Exception as e:
            # Indexes might already exist, which is fine
            logger.debug(f"[ClickHouse] Index creation info: {e}")

async def insert_agent_state_history(run_id: str, state_data: dict, metadata: dict = None):
    """Insert completed agent state into ClickHouse for analytics.
    
    Args:
        run_id: Agent run identifier
        state_data: Final state data from agent execution
        metadata: Additional execution metadata
    """
    # Use canonical SSOT implementation
    async with get_clickhouse_client() as client:
        # Prepare analytics record
        record = _prepare_state_history_record(run_id, state_data, metadata or {})
        
        insert_query = """
        INSERT INTO agent_state_history (
            run_id, thread_id, user_id, snapshot_id,
            created_at, completed_at, agent_phase, checkpoint_type,
            execution_status, state_size_kb, step_count, execution_time_ms,
            memory_usage_mb, state_complexity, recovery_point,
            state_data_compressed, compression_ratio
        ) VALUES
        """
        
        try:
            await client.execute(insert_query, record)
            logger.debug(f"[ClickHouse] Inserted state history for run {run_id}")
            return True
        except Exception as e:
            logger.error(f"[ClickHouse] Failed to insert state history for {run_id}: {e}")
            return False

def _prepare_state_history_record(run_id: str, state_data: dict, metadata: dict) -> dict:
    """Prepare state history record for ClickHouse insertion."""
    import json
    from datetime import datetime
    
    # Calculate state metrics
    state_json = json.dumps(state_data)
    state_size_kb = len(state_json.encode('utf-8')) // 1024
    
    # Determine state complexity based on size and structure
    if state_size_kb < 10:
        complexity = 'simple'
    elif state_size_kb < 50:
        complexity = 'moderate'
    elif state_size_kb < 200:
        complexity = 'complex'
    else:
        complexity = 'very_complex'
    
    now = datetime.utcnow()
    
    return {
        'run_id': run_id,
        'thread_id': metadata.get('thread_id', 'unknown'),
        'user_id': metadata.get('user_id'),
        'snapshot_id': metadata.get('snapshot_id', run_id),
        'created_at': metadata.get('created_at', now),
        'completed_at': metadata.get('completed_at', now),
        'agent_phase': metadata.get('agent_phase', 'completed'),
        'checkpoint_type': metadata.get('checkpoint_type', 'final'),
        'execution_status': metadata.get('execution_status', 'completed'),
        'state_size_kb': state_size_kb,
        'step_count': metadata.get('step_count', 0),
        'execution_time_ms': metadata.get('execution_time_ms'),
        'memory_usage_mb': metadata.get('memory_usage_mb'),
        'state_complexity': complexity,
        'recovery_point': metadata.get('is_recovery_point', False),
        'state_data_compressed': None,  # TODO: Add compression if needed
        'compression_ratio': None
    }

# Backward compatibility exports (import from test fixtures when needed)
ClickHouseManager = ClickHouseService  # Alias for test imports
ClickHouseClient = ClickHouseService  # Alias for consolidation
ClickHouseDatabaseClient = ClickHouseService  # Alias for consolidation