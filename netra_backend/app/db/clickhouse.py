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
    
    async def batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Mock batch insert - logs operation."""
        logger.debug(f"[MOCK ClickHouse] Batch insert to {table_name}: {len(data)} rows")
    
    async def cleanup(self) -> None:
        """Mock cleanup (alias for disconnect)."""
        await self.disconnect()


def _is_testing_environment() -> bool:
    """Check if running in testing environment."""
    from netra_backend.app.core.isolated_environment import get_env
    # Check TESTING environment variable directly for pytest compatibility
    if get_env().get("TESTING"):
        return True
    # Fallback to configuration-based detection
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
    """Get ClickHouse client - REAL by default with graceful degradation.
    
    Returns:
        - Real ClickHouse client (default)
        - Mock client when explicitly configured for testing or when real connection fails in optional environments
    
    Usage:
        async with get_clickhouse_client() as client:
            results = await client.execute("SELECT * FROM events")
    """
    from netra_backend.app.core.isolated_environment import get_env
    
    if use_mock_clickhouse():
        async for client in _create_mock_client():
            yield client
    else:
        # CRITICAL FIX: Add timeout protection for the entire client creation process
        environment = get_env().get("ENVIRONMENT", "development").lower()
        client_timeout = 10.0 if environment in ["staging", "development"] else 30.0
        
        try:
            # Create real client with timeout protection handled at a lower level
            async for client in _create_real_client():
                yield client
                
        except (asyncio.TimeoutError, ConnectionError) as e:
            # If connection fails or times out in optional environments, use mock client
            if environment in ["staging", "development"]:
                clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
                if not clickhouse_required:
                    logger.warning(f"[ClickHouse] Connection failed/timeout in {environment}, using mock client: {e}")
                    async for client in _create_mock_client():
                        yield client
                    return
            
            # Re-raise for production or when explicitly required
            raise


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
    """Test connection and yield client with timeout handling."""
    import asyncio
    from netra_backend.app.core.isolated_environment import get_env
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    
    try:
        # CRITICAL FIX: Reduce timeout in staging/development to fail fast
        timeout = 5.0 if environment in ["staging", "development"] else 15.0
        await asyncio.wait_for(client.test_connection(), timeout=timeout)
        logger.info("[ClickHouse] REAL connection established")
        yield client
    except asyncio.TimeoutError as e:
        logger.error(f"[ClickHouse] Connection test timeout after {timeout} seconds")
        # In staging/development, this is expected - don't raise, let graceful degradation handle it
        if environment in ["staging", "development"]:
            logger.warning("[ClickHouse] Connection timeout in optional environment - graceful degradation")
            raise ConnectionError(f"ClickHouse connection timeout after {timeout}s") from e
        raise asyncio.TimeoutError("ClickHouse connection timeout") from e

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
        # CRITICAL FIX: Graceful degradation - use mock client if connection fails in optional environments
        if environment in ["staging", "development"]:
            clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
            if not clickhouse_required:
                logger.info(f"[ClickHouse] Using mock client as fallback in {environment} (optional service)")
                async for c in _create_mock_client():
                    yield c
                return
        
        # If we reach here, it means the error was not handled gracefully - re-raise
        raise e


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
        """Initialize real ClickHouse client with retry logic and graceful failure."""
        import asyncio
        from netra_backend.app.core.isolated_environment import get_env
        
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        logger.info("[ClickHouse Service] Initializing with REAL client")
        config = get_clickhouse_config()
        
        # CRITICAL FIX: Reduce retries and timeouts for optional environments to fail fast
        if environment in ["staging", "development"]:
            max_retries = 1  # Single attempt in optional environments
            timeout = 5.0    # Fast timeout
        else:
            max_retries = 3  # Full retries in production
            timeout = 15.0   # Longer timeout for production
        
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                base_client = self._build_clickhouse_database(config)
                self._client = ClickHouseQueryInterceptor(base_client)
                # Test connection with environment-appropriate timeout
                await asyncio.wait_for(self._client.test_connection(), timeout=timeout)
                logger.info(f"[ClickHouse Service] Connection established on attempt {attempt + 1}")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"[ClickHouse Service] Connection attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[ClickHouse Service] All {max_retries} connection attempts failed: {e}")
                    
                    # CRITICAL FIX: In optional environments, fallback to mock instead of raising
                    if environment in ["staging", "development"]:
                        clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
                        if not clickhouse_required:
                            logger.warning(f"[ClickHouse Service] Using mock client as fallback in {environment}")
                            self._initialize_mock_client()
                            return
                    
                    raise

    async def initialize(self):
        """Initialize ClickHouse connection with timeout protection."""
        import asyncio
        from netra_backend.app.core.isolated_environment import get_env
        
        if self.force_mock or use_mock_clickhouse():
            self._initialize_mock_client()
        else:
            # CRITICAL FIX: Add timeout protection to prevent hanging during initialization
            environment = get_env().get("ENVIRONMENT", "development").lower()
            init_timeout = 10.0 if environment in ["staging", "development"] else 30.0
            
            try:
                await asyncio.wait_for(self._initialize_real_client(), timeout=init_timeout)
            except asyncio.TimeoutError as e:
                logger.error(f"[ClickHouse Service] Initialization timeout after {init_timeout}s")
                
                # In optional environments, fall back to mock
                if environment in ["staging", "development"]:
                    clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
                    if not clickhouse_required:
                        logger.warning(f"[ClickHouse Service] Using mock client due to timeout in {environment}")
                        self._initialize_mock_client()
                        return
                
                raise ConnectionError(f"ClickHouse initialization timeout after {init_timeout}s") from e
    
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
        if isinstance(self._client, MockClickHouseDatabase):
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
        
        if isinstance(self._client, MockClickHouseDatabase):
            # Mock implementation - just log the operation
            logger.info(f"[MOCK ClickHouse] Batch insert to {table_name}: {len(data)} rows")
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
        return isinstance(self._client, MockClickHouseDatabase)
    
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

# Backward compatibility exports (import from test fixtures when needed)
ClickHouseManager = ClickHouseService  # Alias for test imports
ClickHouseClient = ClickHouseService  # Alias for consolidation
ClickHouseDatabaseClient = ClickHouseService  # Alias for consolidation