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
from typing import Optional, Any, Dict
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
                # Use BackendEnvironment for proper Redis URL configuration
                backend_env = BackendEnvironment()
                redis_url = backend_env.get_redis_url()
                
                # Create new client instance
                self._client = redis.from_url(redis_url, decode_responses=True)
                
                # Test connection with timeout
                await asyncio.wait_for(self._client.ping(), timeout=5.0)
                
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
                        # Health check with timeout
                        await asyncio.wait_for(self._client.ping(), timeout=5.0)
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
                await self._client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
        
        # Cleanup circuit breaker
        if hasattr(self._circuit_breaker, 'cleanup'):
            self._circuit_breaker.cleanup()
        
        self._connected = False
        self._client = None
        
        logger.info("Redis manager shutdown complete")
    
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
        
        return await self._attempt_connection()
    
    async def reset_circuit_breaker(self):
        """Reset the circuit breaker to closed state.
        
        Useful for manual recovery or testing scenarios.
        """
        await self._circuit_breaker.reset()
        logger.info("Redis circuit breaker reset to closed state")


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


async def get_redis() -> RedisManager:
    """Get Redis manager instance."""
    return redis_manager