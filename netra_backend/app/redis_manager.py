"""Redis Manager - Enhanced implementation with automatic recovery and resilience.

This module provides robust Redis connection management for the Netra backend application
with automatic reconnection, exponential backoff, health monitoring, and circuit breaker integration.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity  
- Value Impact: Enables reliable Redis operations with automatic failure recovery
- Strategic Impact: Foundation for resilient caching and session management

Key Features:
- Automatic reconnection with exponential backoff (1s -> 60s max)
- Background reconnection task for permanent failure recovery
- Health monitoring with periodic connection validation (30s intervals)
- Circuit breaker pattern integration for resilience
- Missing get_client() method for llm_cache_core.py compatibility
"""

import asyncio
import logging
import time
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker, 
    UnifiedCircuitConfig, 
    UnifiedCircuitBreakerState
)

logger = logging.getLogger(__name__)


class RedisManager:
    """Enhanced Redis connection manager with automatic recovery and resilience.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Background reconnection task for permanent failure recovery
    - Health monitoring with periodic connection validation
    - Circuit breaker integration for resilience
    - Compatible get_client() method for cache operations
    """
    
    def __init__(self):
        self._client: Optional[Any] = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Exponential backoff configuration
        self._base_retry_delay = 1.0  # Start at 1 second
        self._max_retry_delay = 60.0  # Max 60 seconds
        self._max_reconnect_attempts = 10
        self._current_retry_delay = self._base_retry_delay
        self._consecutive_failures = 0
        
        # Health monitoring configuration
        self._last_health_check = None
        self._health_check_interval = 30.0  # 30 seconds
        
        # Circuit breaker for Redis operations
        circuit_config = UnifiedCircuitConfig(
            name="redis_operations",
            failure_threshold=5,
            success_threshold=2,
            recovery_timeout=60,
            timeout_seconds=30.0
        )
        self._circuit_breaker = UnifiedCircuitBreaker(circuit_config)
        
        logger.info("Enhanced RedisManager initialized with automatic recovery")
    
    async def initialize(self):
        """Initialize Redis connection with automatic recovery setup."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - using mock implementation")
            self._connected = False
            return
        
        # Attempt initial connection with recovery on failure
        await self._attempt_connection(is_initial=True)
        
        # Start background tasks for monitoring and recovery
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for reconnection and health monitoring."""
        if not self._reconnect_task or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(
                self._background_reconnection_task(),
                name="redis_reconnection"
            )
        
        if not self._health_monitor_task or self._health_monitor_task.done():
            self._health_monitor_task = asyncio.create_task(
                self._health_monitoring_task(),
                name="redis_health_monitor"
            )
        
        logger.info("Redis background monitoring tasks started")
    
    async def _attempt_connection(self, is_initial: bool = False) -> bool:
        """Attempt Redis connection with proper error handling.
        
        Args:
            is_initial: Whether this is the initial connection attempt
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        async with self._connection_lock:
            try:
                # Clean up any existing client that might be from different event loop
                if self._client:
                    try:
                        # Use aclose() to avoid deprecation warnings
                        if hasattr(self._client, 'aclose'):
                            await self._client.aclose()
                        else:
                            await self._client.close()
                    except Exception as close_error:
                        logger.debug(f"Error closing previous Redis client: {close_error}")
                    self._client = None
                
                # Use BackendEnvironment for proper Redis URL configuration
                backend_env = BackendEnvironment()
                redis_url = backend_env.get_redis_url()
                
                # For tests: Use test-specific Redis port if available
                # CRITICAL FIX: Proper test environment detection using multiple indicators
                is_test_environment = (
                    get_env().get("PYTEST_CURRENT_TEST") is not None or
                    get_env().get("TESTING", "").lower() == "true" or
                    get_env().get("TEST_COLLECTION_MODE") == "1" or
                    get_env().get("ENVIRONMENT", "").lower() in ["test", "testing"] or
                    get_env().get("TEST_DISABLE_REDIS", "true").lower() == "false"
                )
                
                if is_test_environment:
                    # Use test Redis port 6381 instead of 6379, and database 0 instead of 15
                    if ':6379/' in redis_url:
                        redis_url = redis_url.replace(':6379/', ':6381/')
                    if '/15' in redis_url:
                        redis_url = redis_url.replace('/15', '/0')
                    logger.info(f"Test environment detected - using Redis URL: {redis_url}")
                else:
                    logger.debug(f"Production environment - using Redis URL: {redis_url}")
                
                # Create new client instance in current event loop
                self._client = redis.from_url(redis_url, decode_responses=True)
                
                # Test connection with timeout (reduced for faster readiness checks)
                await asyncio.wait_for(self._client.ping(), timeout=2.0)
                
                # Connection successful
                self._connected = True
                self._consecutive_failures = 0
                self._current_retry_delay = self._base_retry_delay
                self._circuit_breaker.record_success()
                
                connection_type = "Initial" if is_initial else "Recovery"
                logger.info(f"Redis {connection_type.lower()} connection successful: {redis_url}")
                
                return True
                
            except Exception as e:
                self._connected = False
                self._client = None
                self._consecutive_failures += 1
                self._circuit_breaker.record_failure(str(type(e).__name__))
                
                error_type = "Initial connection" if is_initial else "Reconnection"
                logger.error(
                    f"Redis {error_type.lower()} failed (attempt {self._consecutive_failures}): {e}"
                )
                
                return False
    
    async def _background_reconnection_task(self):
        """Background task for automatic reconnection attempts.
        
        Implements exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        Max 10 reconnection attempts before giving up temporarily.
        """
        while not self._shutdown_event.is_set():
            try:
                # Only attempt reconnection if we're not connected
                if not self._connected and self._consecutive_failures > 0:
                    
                    # Check if we should attempt reconnection
                    if self._consecutive_failures <= self._max_reconnect_attempts:
                        logger.info(
                            f"Attempting Redis reconnection (attempt {self._consecutive_failures}/{self._max_reconnect_attempts}) "
                            f"after {self._current_retry_delay}s delay"
                        )
                        
                        success = await self._attempt_connection()
                        
                        if not success:
                            # Exponential backoff: double delay, cap at max
                            self._current_retry_delay = min(
                                self._current_retry_delay * 2,
                                self._max_retry_delay
                            )
                            
                            # Wait before next attempt
                            await asyncio.sleep(self._current_retry_delay)
                        else:
                            logger.info("Redis reconnection successful")
                    else:
                        logger.warning(
                            f"Max reconnection attempts ({self._max_reconnect_attempts}) reached. "
                            "Waiting 5 minutes before retrying..."
                        )
                        # Wait 5 minutes before resetting attempt counter
                        await asyncio.sleep(300)
                        self._consecutive_failures = 1  # Reset to 1 to allow retries
                        self._current_retry_delay = self._base_retry_delay
                else:
                    # Connected or no failures - check every 30 seconds
                    await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                logger.info("Redis reconnection task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Redis reconnection task: {e}")
                await asyncio.sleep(30)  # Wait before retrying task
    
    async def _health_monitoring_task(self):
        """Background task for periodic health monitoring.
        
        Validates Redis connection every 30 seconds and triggers
        recovery if connection is lost.
        """
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._connected and self._client:
                    try:
                        # Health check with timeout (reduced for faster feedback)
                        await asyncio.wait_for(self._client.ping(), timeout=2.0)
                        self._last_health_check = time.time()
                        logger.debug("Redis health check passed")
                        
                    except Exception as e:
                        logger.warning(f"Redis health check failed: {e}")
                        self._connected = False
                        self._consecutive_failures += 1
                        self._circuit_breaker.record_failure("HealthCheckFailed")
                        
                        # Trigger reconnection attempt
                        logger.info("Triggering Redis reconnection due to failed health check")
                        
            except asyncio.CancelledError:
                logger.info("Redis health monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Redis health monitoring task: {e}")
                await asyncio.sleep(30)  # Wait before retrying task
    
    async def shutdown(self):
        """Shutdown Redis connection and cleanup background tasks."""
        try:
            # Check if we're still in a running event loop
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop - perform synchronous cleanup only
                logger.info("No event loop - performing synchronous Redis cleanup")
                self._connected = False
                self._client = None
                return
            
            # Signal shutdown to background tasks
            self._shutdown_event.set()
            
            # Cancel background tasks
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass
            
            if self._health_monitor_task and not self._health_monitor_task.done():
                self._health_monitor_task.cancel()
                try:
                    await self._health_monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Close Redis connection
            if self._client and self._connected:
                try:
                    # Use aclose() to avoid deprecation warnings
                    if hasattr(self._client, 'aclose'):
                        await self._client.aclose()
                    else:
                        await self._client.close()
                    logger.info("Redis connection closed")
                except Exception as e:
                    # Don't fail shutdown on connection close errors
                    logger.debug(f"Error closing Redis connection (non-critical): {e}")
            
            # Cleanup circuit breaker
            if hasattr(self._circuit_breaker, 'cleanup'):
                self._circuit_breaker.cleanup()
            
            self._connected = False
            self._client = None
            
            logger.info("Redis manager shutdown complete")
            
        except Exception as e:
            logger.debug(f"Error during Redis shutdown (non-critical): {e}")
            # Ensure cleanup even if shutdown fails
            self._connected = False
            self._client = None
    
    async def get_client(self):
        """Get Redis client with automatic recovery attempts.
        
        Required by llm_cache_core.py for cache operations.
        
        Returns:
            Redis client if connected, None if unavailable after recovery attempts
        """
        if not REDIS_AVAILABLE:
            logger.debug("Redis not available - returning None")
            return None
        
        # Check circuit breaker state
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - get_client blocked")
            return None
        
        # CRITICAL FIX: Check if client was created in different event loop
        # This fixes the "Future attached to different loop" error in tests
        current_loop = None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running - this is fine for some use cases
            pass
        
        # If client exists but was created in different loop, force reconnection
        if self._client and current_loop:
            try:
                # Test if client works in current loop by attempting a simple ping
                await asyncio.wait_for(self._client.ping(), timeout=0.5)
            except (RuntimeError, asyncio.TimeoutError, Exception) as e:
                # Client not working in current loop - force reconnection
                logger.info(f"Redis client loop mismatch detected: {e.__class__.__name__} - forcing reconnection")
                self._connected = False
                self._client = None
        
        # If not connected, attempt recovery
        if not self._connected or not self._client:
            logger.info("Redis client requested but not connected - attempting recovery")
            success = await self._attempt_connection()
            if not success:
                logger.warning("Redis recovery failed - returning None")
                return None
        
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis with automatic recovery."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - get operation blocked")
            return None
        
        # Attempt to get client with recovery
        client = await self.get_client()
        if not client:
            logger.debug("Redis client not available - get operation skipped")
            return None
        
        try:
            result = await client.get(key)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            # Trigger reconnection attempt
            self._consecutive_failures += 1
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with automatic recovery."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - set operation blocked")
            return False
        
        # Attempt to get client with recovery
        client = await self.get_client()
        if not client:
            logger.debug("Redis client not available - set operation skipped")
            return False
        
        try:
            await client.set(key, value, ex=ex)
            self._circuit_breaker.record_success()
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            # Trigger reconnection attempt
            self._consecutive_failures += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis with automatic recovery."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - delete operation blocked")
            return False
        
        # Attempt to get client with recovery
        client = await self.get_client()
        if not client:
            logger.debug("Redis client not available - delete operation skipped")
            return False
        
        try:
            result = await client.delete(key)
            self._circuit_breaker.record_success()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            # Trigger reconnection attempt
            self._consecutive_failures += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis with automatic recovery."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - exists check blocked")
            return False
        
        # Attempt to get client with recovery
        client = await self.get_client()
        if not client:
            logger.debug("Redis client not available - exists check skipped")
            return False
        
        try:
            result = await client.exists(key)
            self._circuit_breaker.record_success()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            # Trigger reconnection attempt
            self._consecutive_failures += 1
            return False
    
    @asynccontextmanager
    async def pipeline(self):
        """Get Redis pipeline for batch operations with automatic recovery."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - pipeline blocked")
            yield MockPipeline()
            return
        
        # Attempt to get client with recovery
        client = await self.get_client()
        if not client:
            logger.debug("Redis client not available - using mock pipeline")
            yield MockPipeline()
            return
        
        try:
            pipe = client.pipeline()
            self._circuit_breaker.record_success()
            yield pipe
        except Exception as e:
            logger.error(f"Redis pipeline error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            # Trigger reconnection attempt
            self._consecutive_failures += 1
            yield MockPipeline()
    
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - lpush operation skipped")
            return 0
        
        try:
            result = await self._client.lpush(key, *values)
            return result
        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return 0
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from the right of a list."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - rpop operation skipped")
            return None
        
        try:
            return await self._client.rpop(key)
        except Exception as e:
            logger.error(f"Redis rpop error: {e}")
            return None
    
    async def llen(self, key: str) -> int:
        """Get length of a list."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - llen operation skipped")
            return 0
        
        try:
            result = await self._client.llen(key)
            return result
        except Exception as e:
            logger.error(f"Redis llen error: {e}")
            return 0
    
    async def keys(self, pattern: str) -> list:
        """Get keys matching pattern."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - keys operation skipped")
            return []
        
        try:
            result = await self._client.keys(pattern)
            return result
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []
    
    async def incr(self, key: str) -> int:
        """Increment a key's value."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - incr operation skipped")
            return 0
        
        try:
            result = await self._client.incr(key)
            return result
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if not self._connected or not self._client:
            logger.warning("Redis not connected - expire operation skipped")
            return False
        
        try:
            result = await self._client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed Redis manager status including circuit breaker state.
        
        Returns:
            Dict containing connection status, health metrics, and circuit breaker state
        """
        return {
            "connected": self._connected,
            "client_available": self._client is not None,
            "consecutive_failures": self._consecutive_failures,
            "current_retry_delay": self._current_retry_delay,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "last_health_check": self._last_health_check,
            "background_tasks": {
                "reconnect_task_active": self._reconnect_task is not None and not self._reconnect_task.done(),
                "health_monitor_active": self._health_monitor_task is not None and not self._health_monitor_task.done()
            },
            "circuit_breaker": self._circuit_breaker.get_status()
        }
    
    async def force_reconnect(self) -> bool:
        """Force an immediate reconnection attempt.
        
        Useful for testing or manual recovery scenarios.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        logger.info("Force reconnection requested")
        self._connected = False
        self._consecutive_failures = 0  # Reset failure count for fresh attempt
        self._current_retry_delay = self._base_retry_delay  # Reset retry delay
        
        # Clean up existing client to ensure fresh connection
        if self._client:
            try:
                if hasattr(self._client, 'aclose'):
                    await self._client.aclose()
                else:
                    await self._client.close()
            except Exception as e:
                logger.debug(f"Error closing client during force reconnect: {e}")
            self._client = None
        
        return await self._attempt_connection()
    
    def reinitialize_configuration(self):
        """Reinitialize Redis configuration from environment variables.
        
        This method re-reads configuration from environment variables and prepares
        for a fresh connection attempt. Useful for tests that modify environment
        variables after initialization.
        """
        logger.info("Reinitializing Redis configuration from environment")
        # Force disconnection to ensure fresh connection attempt
        self._connected = False
        self._consecutive_failures = 0
        self._current_retry_delay = self._base_retry_delay
        
        # Clean up existing client to force new connection
        if self._client:
            self._client = None
        
        # Configuration will be re-read in next connection attempt
        logger.info("Redis configuration reinitialized")
    
    async def reset_circuit_breaker(self):
        """Reset the circuit breaker to closed state.
        
        Useful for manual recovery or testing scenarios.
        """
        await self._circuit_breaker.reset()
        logger.info("Redis circuit breaker reset to closed state")
    
    # ============================================================================
    # SSOT CONSOLIDATION: Cache Management Methods
    # (Merged from netra_backend.app.cache.redis_cache_manager)
    # ============================================================================
    
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Get multiple values from Redis."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - mget operation blocked")
            return [None] * len(keys)
        
        client = await self.get_client()
        if not client:
            return [None] * len(keys)
        try:
            result = await client.mget(keys)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            logger.error(f"Redis mget error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            self._consecutive_failures += 1
            return [None] * len(keys)

    async def mset(self, mapping: Dict[str, str]) -> bool:
        """Set multiple key-value pairs."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - mset operation blocked")
            return False
        
        client = await self.get_client()
        if not client:
            return False
        try:
            await client.mset(mapping)
            self._circuit_breaker.record_success()
            return True
        except Exception as e:
            logger.error(f"Redis mset error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            self._consecutive_failures += 1
            return False

    async def setex(self, key: str, time: int, value: str) -> bool:
        """Set key with expiration."""
        return await self.set(key, value, ex=time)

    async def scan_keys(self, pattern: str) -> List[str]:
        """Scan for keys matching pattern."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - scan_keys operation blocked")
            return []
        
        client = await self.get_client()
        if not client:
            return []
        try:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            self._circuit_breaker.record_success()
            return keys
        except Exception as e:
            logger.error(f"Redis scan_keys error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            self._consecutive_failures += 1
            return []

    async def memory_usage(self, key: str) -> Optional[int]:
        """Get memory usage of a key."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - memory_usage operation blocked")
            return None
        
        client = await self.get_client()
        if not client:
            return None
        try:
            result = await client.memory_usage(key)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            logger.debug(f"Redis memory_usage error (command may not be available): {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            return None

    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Redis circuit breaker is open - ttl operation blocked")
            return -2
        
        client = await self.get_client()
        if not client:
            return -2
        try:
            result = await client.ttl(key)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            logger.error(f"Redis ttl error: {e}")
            self._circuit_breaker.record_failure(str(type(e).__name__))
            self._connected = False
            self._consecutive_failures += 1
            return -2

    # Cache Statistics Support
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "connected": self._connected,
            "consecutive_failures": self._consecutive_failures,
            "circuit_breaker_state": self._circuit_breaker.get_status()
        }
    
    # ============================================================================
    # SSOT CONSOLIDATION: Auth Service Compatibility Methods
    # (Merged from auth_service.auth_core.redis_manager)
    # ============================================================================
    
    async def store_session(self, session_id: str, session_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Store session data (auth service compatibility)."""
        import json
        session_json = json.dumps(session_data, default=str)
        return await self.set(f"auth:session:{session_id}", session_json, ex=ttl_seconds)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data (auth service compatibility)."""
        import json
        session_json = await self.get(f"auth:session:{session_id}")
        if session_json:
            try:
                return json.loads(session_json)
            except json.JSONDecodeError:
                return None
        return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete session (auth service compatibility)."""
        return await self.delete(f"auth:session:{session_id}")

    async def blacklist_token(self, token: str, ttl_seconds: int = 86400) -> bool:
        """Blacklist token (auth service compatibility)."""
        return await self.set(f"auth:blacklist:{token}", "blacklisted", ex=ttl_seconds)

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted (auth service compatibility)."""
        return await self.exists(f"auth:blacklist:{token}")
    
    async def extend_session(self, session_id: str, ttl_seconds: int = 3600) -> bool:
        """Extend session TTL (auth service compatibility)."""
        return await self.expire(f"auth:session:{session_id}", ttl_seconds)
    
    async def cache_user_data(self, user_id: str, user_data: Dict[str, Any], ttl_seconds: int = 1800) -> bool:
        """Cache user data for fast lookup (auth service compatibility)."""
        import json
        user_json = json.dumps(user_data, default=str)
        return await self.set(f"auth:user:{user_id}", user_json, ex=ttl_seconds)
    
    async def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data (auth service compatibility)."""
        import json
        user_json = await self.get(f"auth:user:{user_id}")
        if user_json:
            try:
                return json.loads(user_json)
            except json.JSONDecodeError:
                return None
        return None
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate cached user data (auth service compatibility)."""
        return await self.delete(f"auth:user:{user_id}")
    
    async def cache_user_permissions(self, user_id: str, permissions: List[str], ttl_seconds: int = 1800) -> bool:
        """Cache user permissions (auth service compatibility)."""
        import json
        permissions_json = json.dumps(permissions)
        return await self.set(f"auth:perm:{user_id}", permissions_json, ex=ttl_seconds)
    
    async def get_cached_permissions(self, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions (auth service compatibility)."""
        import json
        permissions_json = await self.get(f"auth:perm:{user_id}")
        if permissions_json:
            try:
                return json.loads(permissions_json)
            except json.JSONDecodeError:
                return None
        return None


class MockPipeline:
    """Mock pipeline for when Redis is not available."""
    
    def __init__(self):
        pass
    
    async def execute(self):
        """Mock execute method."""
        return []
    
    def set(self, key: str, value: str, ex: Optional[int] = None):
        """Mock set method."""
        pass
    
    def delete(self, key: str):
        """Mock delete method."""
        pass
    
    def lpush(self, key: str, *values: str):
        """Mock lpush method."""
        pass
    
    def incr(self, key: str):
        """Mock incr method."""
        pass
    
    def expire(self, key: str, seconds: int):
        """Mock expire method."""
        pass


# Global instance
redis_manager = RedisManager()

# Auth service compatibility alias
auth_redis_manager = redis_manager


async def get_redis() -> RedisManager:
    """Get Redis manager instance."""
    return redis_manager


def get_redis_manager() -> RedisManager:
    """Get Redis manager instance - synchronous version for compatibility with integration tests."""
    return redis_manager


class UserCacheManager:
    """User-specific caching operations using Redis."""
    
    def __init__(self, redis_manager: RedisManager = None):
        self.redis_manager = redis_manager or redis_manager
    
    async def get_user_cache(self, user_id: str, key: str) -> Optional[str]:
        """Get user-specific cached value."""
        cache_key = f"user:{user_id}:{key}"
        return await self.redis_manager.get(cache_key)
    
    async def set_user_cache(self, user_id: str, key: str, value: str, ttl: int = 3600) -> bool:
        """Set user-specific cached value."""
        cache_key = f"user:{user_id}:{key}"
        return await self.redis_manager.set(cache_key, value, ex=ttl)
    
    async def clear_user_cache(self, user_id: str, key: str = None) -> bool:
        """Clear user-specific cache."""
        if key:
            cache_key = f"user:{user_id}:{key}"
            return await self.redis_manager.delete(cache_key)
        else:
            # Clear all user cache
            pattern = f"user:{user_id}:*"
            keys = await self.redis_manager.keys(pattern)
            if keys:
                for k in keys:
                    await self.redis_manager.delete(k)
            return True