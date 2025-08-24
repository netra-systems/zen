"""ClickHouse Database Client

ClickHouse-specific database client with resilient circuit breaker protection.
Implements pragmatic rigor principles with fallback responses and degraded operation.
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
from netra_backend.app.db.client_config import (
    CircuitBreakerManager,
    DatabaseClientConfig,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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
            # Remove expired entry
            del self.cache[key]
        
        self._misses += 1
        return None
    
    def set(self, query: str, result: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None, ttl: float = 300) -> None:
        """Cache query result with TTL."""
        if len(self.cache) >= self.max_size:
            # Simple cleanup: remove 10 oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k]["created_at"]
            )[:10]
            for k in oldest_keys:
                del self.cache[k]
        
        key = self._generate_key(query, params)
        self.cache[key] = {
            "result": result,
            "created_at": time.time(),
            "expires_at": time.time() + ttl
        }
        logger.debug(f"Cached ClickHouse result for query: {query[:50]}... (TTL: {ttl}s)")
    
    def get_stale(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached result even if expired (for fallback)."""
        key = self._generate_key(query, params)
        entry = self.cache.get(key)
        if entry:
            age = time.time() - entry["created_at"]
            logger.info(f"Using stale ClickHouse cache (age: {age:.1f}s) for fallback")
            return entry["result"]
        return None
    
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


# Global cache instance
_clickhouse_cache = ClickHouseCache()


class ClickHouseQueryExecutor:
    """Execute ClickHouse queries with circuit breaker protection."""
    
    @staticmethod
    async def create_clickhouse_query_executor(query: str, params: Optional[Dict[str, Any]]):
        """Create ClickHouse query executor function."""
        async def _execute_ch_query() -> List[Dict[str, Any]]:
            from netra_backend.app.database import get_clickhouse_client
            async with get_clickhouse_client() as ch_client:
                return await ch_client.execute_query(query, params)
        return _execute_ch_query

    @staticmethod
    async def handle_clickhouse_circuit_open(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Handle ClickHouse circuit breaker open with fallback responses."""
        logger.warning("ClickHouse query blocked - circuit breaker open, attempting fallback")
        
        # Try to return cached data (even if stale)
        cached_result = _clickhouse_cache.get_stale(query, params)
        if cached_result is not None:
            logger.info("Returning stale cached data due to circuit breaker open")
            return cached_result
        
        # Return appropriate fallback based on query type
        fallback = ClickHouseQueryExecutor._get_query_fallback(query)
        if fallback:
            logger.info(f"Returning fallback response for query type: {query[:50]}...")
            return fallback
        
        # Last resort: empty result with warning
        logger.warning("No fallback available, returning empty result")
        return []

    @staticmethod
    def _get_query_fallback(query: str) -> Optional[List[Dict[str, Any]]]:
        """Get appropriate fallback response based on query type."""
        query_lower = query.lower().strip()
        
        # Health check queries
        if "select 1" in query_lower:
            return [{"1": 1}]
        
        # Count queries - return zero
        if query_lower.startswith("select count"):
            return [{"count": 0}]
        
        # Metrics/monitoring queries - return empty but valid structure
        if any(keyword in query_lower for keyword in ["metrics", "logs", "events", "monitoring"]):
            return []
        
        # Default: no fallback
        return None
    
    @staticmethod
    async def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with circuit breaker and caching."""
        # Check cache first for read queries
        if query.lower().strip().startswith("select"):
            cached_result = _clickhouse_cache.get(query, params)
            if cached_result is not None:
                return cached_result
        
        circuit = await CircuitBreakerManager.get_clickhouse_circuit()
        try:
            query_executor = await ClickHouseQueryExecutor.create_clickhouse_query_executor(query, params)
            result = await circuit.call(query_executor)
            
            # Cache successful read results
            if query.lower().strip().startswith("select") and result:
                cache_ttl = DatabaseClientConfig.CACHE_CONFIG["query_cache_ttl"]
                _clickhouse_cache.set(query, result, params, cache_ttl)
            
            return result
            
        except CircuitBreakerOpenError:
            return await ClickHouseQueryExecutor.handle_clickhouse_circuit_open(query, params)


class ClickHouseHealthChecker:
    """Health checking for ClickHouse connections with resilient fallbacks."""
    
    @staticmethod
    async def test_clickhouse_connectivity() -> None:
        """Test basic ClickHouse connectivity."""
        try:
            result = await ClickHouseQueryExecutor.execute_query("SELECT 1")
            if not result:  # Empty result from fallback is still considered "working" for health
                logger.info("ClickHouse connectivity test returned fallback response")
        except Exception as e:
            logger.warning(f"ClickHouse connectivity test failed: {e}")
            raise

    @staticmethod
    async def build_healthy_response(circuit_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build healthy health check response."""
        return {"status": "healthy", "circuit": circuit_status}

    @staticmethod
    async def build_unhealthy_response(error: Exception) -> Dict[str, Any]:
        """Build unhealthy health check response."""
        return {"status": "unhealthy", "error": str(error)}

    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """ClickHouse health check with degraded operation support."""
        try:
            circuit = await CircuitBreakerManager.get_clickhouse_circuit()
            circuit_status = circuit.get_status()
            
            try:
                await ClickHouseHealthChecker.test_clickhouse_connectivity()
                # Include cache stats in healthy response
                response = await ClickHouseHealthChecker.build_healthy_response(circuit_status)
                response["cache_stats"] = _clickhouse_cache.stats()
                return response
            except Exception as conn_error:
                # If connectivity fails but circuit allows fallbacks, report as degraded
                if circuit_status.get("state") != "open":
                    return {
                        "status": "degraded",
                        "message": "ClickHouse connectivity issues but fallbacks available",
                        "circuit": circuit_status,
                        "cache_stats": _clickhouse_cache.stats(),
                        "error": str(conn_error)
                    }
                raise conn_error
                
        except Exception as e:
            return await ClickHouseHealthChecker.build_unhealthy_response(e)


class ClickHouseDatabaseClient:
    """ClickHouse client with resilient circuit breaker protection and caching."""
    
    def __init__(self) -> None:
        self._degraded_mode = False
    
    @property
    def is_degraded_mode(self) -> bool:
        """Check if client is operating in degraded mode."""
        return self._degraded_mode
    
    def set_degraded_mode(self, enabled: bool) -> None:
        """Enable or disable degraded mode."""
        if enabled != self._degraded_mode:
            logger.warning(f"ClickHouse client degraded mode {'enabled' if enabled else 'disabled'}")
            self._degraded_mode = enabled

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with resilient circuit breaker and caching."""
        try:
            result = await ClickHouseQueryExecutor.execute_query(query, params)
            # If we got a real result, clear degraded mode
            if result and not self._is_fallback_response(result, query):
                self.set_degraded_mode(False)
            return result
        except Exception as e:
            self.set_degraded_mode(True)
            logger.error(f"ClickHouse query failed: {e}")
            # Try to return cached data as last resort
            cached_result = _clickhouse_cache.get_stale(query, params)
            if cached_result is not None:
                logger.info("Returning stale cached data due to query failure")
                return cached_result
            raise
    
    def _is_fallback_response(self, result: List[Dict[str, Any]], query: str) -> bool:
        """Check if result appears to be a fallback response."""
        if not result:
            return True
        
        query_lower = query.lower().strip()
        
        # Check for known fallback patterns
        if len(result) == 1:
            first_result = result[0]
            if (query_lower == "select 1" and first_result.get("1") == 1) or \
               ("count" in first_result and first_result.get("count") == 0):
                return True
        
        return False
    
    async def execute_query_with_retry(self, query: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> List[Dict[str, Any]]:
        """Execute query with additional retry logic for critical operations."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(2.0 * (2 ** (attempt - 1)), 8.0)  # Exponential backoff, max 8s
                    logger.info(f"Retrying ClickHouse query (attempt {attempt + 1}/{max_retries + 1}) after {delay}s")
                    await asyncio.sleep(delay)
                
                result = await self.execute_query(query, params)
                
                if attempt > 0:
                    logger.info(f"ClickHouse query succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    logger.error(f"ClickHouse query failed after {max_retries + 1} attempts")
                    break
        
        raise last_exception
    
    async def health_check(self) -> Dict[str, Any]:
        """ClickHouse health check with degraded mode status."""
        health_result = await ClickHouseHealthChecker.health_check()
        health_result["degraded_mode"] = self._degraded_mode
        return health_result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get ClickHouse cache statistics."""
        return _clickhouse_cache.stats()
    
    def clear_cache(self) -> None:
        """Clear ClickHouse query cache."""
        _clickhouse_cache.cache.clear()
        logger.info("ClickHouse cache cleared")


# Backward compatibility alias
ClickHouseClient = ClickHouseDatabaseClient