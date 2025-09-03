# Redis Manager for netra_backend service
# Provides Redis connectivity and operations for the backend service
# UPDATED: Now uses RedisConfigurationBuilder for unified configuration

import asyncio
import redis.asyncio as redis
from typing import Dict, Optional

from netra_backend.app.core.configuration.base import get_unified_config
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger as logger
from shared.redis_config_builder import RedisConfigurationBuilder


class RedisManager:
    def __init__(self, test_mode: bool = False):
        self.redis_client = None
        self.enabled = self._check_if_enabled()
        self.test_mode = test_mode
        self.test_locks: Dict[str, str] = {}  # For test mode leader locks
        self._redis_builder = self._create_redis_builder()
    
    def _namespace_key(self, user_id: Optional[str], key: str) -> str:
        """Namespace Redis key by user for isolation.
        
        Args:
            user_id: User identifier for namespacing. None uses 'system' namespace.
            key: Original Redis key
            
        Returns:
            Namespaced key in format 'user:{user_id}:{key}' or 'system:{key}'
        """
        namespace = user_id if user_id is not None else "system"
        return f"user:{namespace}:{key}"

    def reinitialize_configuration(self):
        """Reinitialize Redis configuration for environment changes (test support)."""
        # Clear existing client connection
        if self.redis_client:
            # Don't await here since this is not async - client will be recreated on next use
            self.redis_client = None
        
        # Recreate configuration builder with current environment
        self._redis_builder = self._create_redis_builder()
        
        # Re-check if Redis should be enabled
        self.enabled = self._check_if_enabled()
        
        logger.debug("Redis configuration reinitialized for environment changes")

    def _is_redis_disabled_by_flag(self) -> bool:
        """Check if Redis is disabled by operational flag."""
        config = get_unified_config()
        disabled = getattr(config, 'disable_redis', False)
        if disabled:
            logger.info("Redis is disabled by configuration")
            return True
        return False

    def _get_redis_mode(self) -> str:
        """Get Redis mode from configuration."""
        config = get_unified_config()
        return getattr(config, 'redis_mode', 'shared').lower()

    def _handle_redis_mode(self, redis_mode: str):
        """Handle Redis mode logic."""
        if redis_mode == "disabled":
            logger.info("Redis is disabled (mode: disabled)")
            return False
        elif redis_mode == "standalone":
            logger.info("Redis is running in standalone mode")
            return True
        return None

    def _check_development_redis(self) -> bool:
        """Check Redis availability in development mode."""
        config = get_unified_config()
        if config.environment == "development":
            enabled = config.dev_mode_redis_enabled
            if not enabled:
                logger.info("Redis is disabled in development configuration")
            return enabled
        return True

    def _check_if_enabled(self):
        """Determine Redis service availability based on environment configuration."""
        if self._is_redis_disabled_by_flag():
            return False
        return self._check_redis_mode_and_development()

    def _check_redis_mode_and_development(self):
        """Check Redis mode and development settings."""
        redis_mode = self._get_redis_mode()
        mode_result = self._handle_redis_mode(redis_mode)
        if mode_result is not None:
            return mode_result
        return self._check_development_redis()

    def _create_redis_builder(self) -> RedisConfigurationBuilder:
        """Create Redis configuration builder with current environment."""
        env = get_env()
        env_vars = {
            "ENVIRONMENT": env.get("ENVIRONMENT"),
            "NETRA_ENVIRONMENT": env.get("NETRA_ENVIRONMENT"),
            "K_SERVICE": env.get("K_SERVICE"),
            "GCP_PROJECT_ID": env.get("GCP_PROJECT_ID"),
            "REDIS_URL": env.get("REDIS_URL"),
            "REDIS_HOST": env.get("REDIS_HOST"),
            "REDIS_PORT": env.get("REDIS_PORT"),
            "REDIS_DB": env.get("REDIS_DB"),
            "REDIS_PASSWORD": env.get("REDIS_PASSWORD"),
            "REDIS_USERNAME": env.get("REDIS_USERNAME"),
            "REDIS_SSL": env.get("REDIS_SSL"),
            "REDIS_FALLBACK_ENABLED": env.get("REDIS_FALLBACK_ENABLED"),
            "REDIS_REQUIRED": env.get("REDIS_REQUIRED"),
        }
        return RedisConfigurationBuilder(env_vars)
    
    def _create_redis_client(self):
        """Create Redis client with configuration from RedisConfigurationBuilder."""
        try:
            # Get client configuration from Redis builder
            client_config = self._redis_builder.get_config_for_environment()
            
            # Log configuration for debugging (without sensitive data)
            safe_config = {k: v for k, v in client_config.items() if k not in ['password', 'username']}
            logger.debug(f"Creating Redis client with config: {safe_config}")
            
            # Create Redis client with configuration
            return redis.Redis(**client_config)
            
        except AttributeError as e:
            # Handle case where RedisConfigurationBuilder might not be properly initialized
            logger.error(f"Redis configuration builder not properly initialized: {e}")
            if self.test_mode or (hasattr(self._redis_builder, 'environment') and self._redis_builder.environment == "development"):
                logger.warning("Using minimal fallback Redis configuration")
                return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            raise
            
        except Exception as e:
            logger.error(f"Failed to create Redis client from builder: {e}")
            
            # Fallback for development mode only
            if hasattr(self._redis_builder, 'environment') and self._redis_builder.environment == "development":
                if hasattr(self._redis_builder, 'development') and self._redis_builder.development.should_allow_fallback():
                    logger.warning("Using fallback Redis configuration for development")
                    fallback_config = self._redis_builder.development.get_fallback_config()
                    if fallback_config:
                        return redis.Redis(**fallback_config)
            
            raise

    async def _test_redis_connection(self):
        """Test Redis connection with timeout protection."""
        import asyncio
        from shared.isolated_environment import get_env
        
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        # CRITICAL FIX: Environment-aware connection test timeouts
        if environment == "staging":
            timeout = 10.0  # Longer timeout for staging
        elif environment == "production":
            timeout = 15.0  # Longest timeout for production
        else:
            timeout = 5.0   # Standard timeout for development
            
        try:
            await asyncio.wait_for(self.redis_client.ping(), timeout=timeout)
            logger.info(f"Redis connected successfully in {environment} environment")
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"Redis ping timeout after {timeout}s in {environment} environment") from e

    def _handle_connection_error(self, error: Exception):
        """Handle Redis connection errors."""
        logger.warning(f"Redis connection failed: {error}. Service will operate without Redis.")
        self.redis_client = None
        self.enabled = False  # Disable Redis manager when connection fails

    async def initialize(self):
        """Initialize Redis connection. Standard async initialization interface."""
        return await self.connect()

    async def connect(self):
        """Connect to Redis if enabled with retry logic and exponential backoff."""
        # Reset enabled status for reconnection attempts (allows recovery after failures)
        if not hasattr(self, '_initial_enabled_check_done') or not self._initial_enabled_check_done:
            self._initial_enabled_check_done = True
            if not self.enabled:
                logger.info("Redis connection skipped - service is disabled in development mode")
                return
        elif not self.enabled:
            # Re-check if we should be enabled on reconnection attempts
            self.enabled = self._check_if_enabled()
            if not self.enabled:
                logger.info("Redis connection skipped - service is disabled in development mode")
                return
                
        # CRITICAL FIX: Implement retry logic with exponential backoff for staging reliability
        environment = self._redis_builder.environment
        if environment == "staging":
            max_retries = 3
            base_delay = 1.0
        elif environment == "production":
            max_retries = 2  
            base_delay = 0.5
        else:
            max_retries = 1  # Single attempt for development
            base_delay = 0.2
            
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Exponential backoff with jitter
                    import random
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.1)
                    logger.info(f"Redis connection retry {attempt}/{max_retries} after {delay:.2f}s delay")
                    await asyncio.sleep(delay)
                    
                self.redis_client = self._create_redis_client()
                await self._test_redis_connection()
                
                if attempt > 0:
                    logger.info(f"Redis connection successful after {attempt} retries")
                return
                
            except Exception as e:
                last_error = e
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                
                # For the last attempt, handle differently
                if attempt == max_retries:
                    break
                    
        # All retry attempts failed - handle based on environment and test mode
        if self.test_mode:
            logger.debug(f"Test mode fallback - graceful handling of Redis connection error: {last_error}")
            self._handle_connection_error(last_error)
            return
        
        # In pytest environment (but not test_mode fallback), re-raise exceptions for test validation
        env = get_env()
        if env.get("PYTEST_CURRENT_TEST"):
            logger.debug(f"Pytest detected - disabling Redis manager and re-raising connection exception: {last_error}")
            self._handle_connection_error(last_error)  # Disable manager before re-raising
            raise
        
        # Handle connection failure based on environment policy
        if environment == "staging" and self._redis_builder.staging.should_fail_fast():
            logger.error(f"Redis connection failed in staging environment after {max_retries + 1} attempts: {last_error}. Fail-fast mode enabled.")
            self._handle_connection_error(last_error)
            raise
        elif environment == "production":
            logger.error(f"Redis connection failed in production environment after {max_retries + 1} attempts: {last_error}")
            self._handle_connection_error(last_error)
            raise
        
        # Development fallback logic
        if environment == "development" and self._redis_builder.development.should_allow_fallback():
            logger.warning(f"Remote Redis failed after retries: {last_error}. Attempting local fallback...")
            try:
                fallback_config = self._redis_builder.development.get_fallback_config()
                if fallback_config:
                    self.redis_client = redis.Redis(**fallback_config)
                    await self._test_redis_connection()
                    logger.info("Successfully connected to local Redis fallback")
                    return
            except Exception as fallback_error:
                logger.error(f"Local Redis fallback also failed: {fallback_error}")
        
        # If no fallback worked or not allowed, handle as error
        self._handle_connection_error(last_error)

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.aclose()

    async def get_client(self):
        """Get the Redis client instance with health check. Returns None if not connected or disabled."""
        # Try to connect if not connected yet and Redis is enabled
        if self.redis_client is None and self.enabled:
            try:
                await self.connect()
            except Exception as e:
                logger.debug(f"Failed to connect to Redis: {e}")
                return None
        
        # CRITICAL FIX: Health check before returning client
        if self.redis_client and hasattr(self.redis_client, 'get'):
            # Perform quick health check for staging/production
            environment = self._redis_builder.environment
            if environment in ["staging", "production"]:
                try:
                    # Quick ping with short timeout
                    await asyncio.wait_for(self.redis_client.ping(), timeout=2.0)
                except Exception as e:
                    logger.warning(f"Redis client failed health check: {e}. Attempting reconnection...")
                    self.redis_client = None
                    try:
                        await self.connect()
                        return self.redis_client if self.redis_client else None
                    except Exception as reconnect_error:
                        logger.error(f"Redis reconnection failed: {reconnect_error}")
                        return None
            return self.redis_client
        return None
    
    async def get(self, key: str, user_id: Optional[str] = None):
        """Get a value from Redis with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.get(actual_key)
            except Exception as e:
                # Check if this is a fallback test (test_mode=True specifically set)
                if self.test_mode:
                    logger.debug(f"Test mode fallback - returning None for Redis operation timeout: {e}")
                    return None
                
                # In pytest environment (but not test_mode fallback), re-raise exceptions for test validation
                env = get_env()
                if env.get("PYTEST_CURRENT_TEST"):
                    logger.debug(f"Pytest detected - re-raising Redis operation exception: {e}")
                    raise
                    
                # In production, log warning and return None for graceful degradation
                logger.warning(f"Redis get operation failed for key {actual_key}: {e}")
                return None
        return None
    
    async def set(self, key: str, value: str, ex: int = None, expire: int = None, user_id: Optional[str] = None):
        """Set a value in Redis with optional expiration and user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            # Support both 'ex' and 'expire' for backward compatibility
            expiration = ex or expire
            return await self.redis_client.set(actual_key, value, ex=expiration)
        return None
    
    async def delete(self, *keys, **kwargs):
        """Delete one or more keys from Redis with optional user namespacing"""
        user_id = kwargs.get('user_id')
        if self.redis_client and keys:
            try:
                if user_id is not None:
                    actual_keys = [self._namespace_key(user_id, key) for key in keys]
                    return await self.redis_client.delete(*actual_keys)
                else:
                    return await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Failed to delete keys {keys}: {e}")
                return 0
        return 0

    def _calculate_list_range(self, limit: int) -> int:
        """Calculate list range end index."""
        return limit - 1 if limit else -1

    async def _fetch_list_items(self, key: str, limit: int):
        """Fetch list items from Redis."""
        end_index = self._calculate_list_range(limit)
        return await self.redis_client.lrange(key, 0, end_index)

    async def get_list(self, key: str, limit: int = None):
        """Get list items from Redis"""
        if self.redis_client:
            return await self._get_list_with_error_handling(key, limit)
        return []

    async def _get_list_with_error_handling(self, key: str, limit: int):
        """Get list with error handling."""
        try:
            return await self._fetch_list_items(key, limit)
        except Exception as e:
            logger.warning(f"Failed to get list {key}: {e}")
            return []

    async def _push_and_trim_list(self, key: str, value: str, max_size: int):
        """Push item and trim list if needed."""
        await self.redis_client.lpush(key, value)
        if max_size:
            await self.redis_client.ltrim(key, 0, max_size - 1)

    async def add_to_list(self, key: str, value: str, max_size: int = None):
        """Add item to Redis list with optional size limit"""
        if self.redis_client:
            try:
                await self._push_and_trim_list(key, value, max_size)
                return True
            except Exception as e:
                logger.warning(f"Failed to add to list {key}: {e}")
                return False
        return False

    # Additional Redis methods needed by test files
    async def keys(self, pattern: str = "*", user_id: Optional[str] = None):
        """Get keys matching pattern from Redis with optional user namespacing"""
        if self.redis_client:
            try:
                if user_id is not None:
                    namespaced_pattern = self._namespace_key(user_id, pattern)
                    keys = await self.redis_client.keys(namespaced_pattern)
                    # Remove namespace prefix from returned keys
                    namespace_prefix = f"user:{user_id}:"
                    return [key.replace(namespace_prefix, "", 1) for key in keys if key.startswith(namespace_prefix)]
                else:
                    return await self.redis_client.keys(pattern)
            except Exception as e:
                logger.warning(f"Failed to get keys with pattern {pattern}: {e}")
                return []
        return []

    async def lpop(self, key: str, user_id: Optional[str] = None):
        """Pop item from left side of list with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.lpop(actual_key)
            except Exception as e:
                logger.warning(f"Failed to lpop from {actual_key}: {e}")
                return None
        return None

    async def lpush(self, key: str, *values, **kwargs):
        """Push items to left side of list with optional user namespacing"""
        user_id = kwargs.get('user_id')
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.lpush(actual_key, *values)
            except Exception as e:
                logger.warning(f"Failed to lpush to {actual_key}: {e}")
                return 0
        return 0

    async def ttl(self, key: str, user_id: Optional[str] = None):
        """Get time to live for key with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.ttl(actual_key)
            except Exception as e:
                logger.warning(f"Failed to get ttl for {actual_key}: {e}")
                return -1
        return -1

    async def expire(self, key: str, seconds: int, user_id: Optional[str] = None):
        """Set expiration time for key with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.expire(actual_key, seconds)
            except Exception as e:
                logger.warning(f"Failed to set expire for {actual_key}: {e}")
                return False
        return False

    async def hset(self, key: str, field_or_mapping, value=None, user_id: Optional[str] = None):
        """Set hash field(s) with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                if value is not None:
                    # hset(key, field, value) format
                    return await self.redis_client.hset(actual_key, field_or_mapping, value)
                else:
                    # hset(key, mapping) format
                    return await self.redis_client.hset(actual_key, mapping=field_or_mapping)
            except Exception as e:
                logger.warning(f"Failed to hset {actual_key}: {e}")
                return 0
        return 0

    async def hget(self, key: str, field: str, user_id: Optional[str] = None):
        """Get hash field value with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.hget(actual_key, field)
            except Exception as e:
                logger.warning(f"Failed to hget {actual_key} {field}: {e}")
                return None
        return None

    async def hgetall(self, key: str, user_id: Optional[str] = None):
        """Get all hash fields and values with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.hgetall(actual_key)
            except Exception as e:
                logger.warning(f"Failed to hgetall {actual_key}: {e}")
                return {}
        return {}

    async def zadd(self, key: str, mapping: dict):
        """Add members to sorted set"""
        if self.redis_client:
            try:
                return await self.redis_client.zadd(key, mapping)
            except Exception as e:
                logger.warning(f"Failed to zadd to {key}: {e}")
                return 0
        return 0

    async def zrangebyscore(self, key: str, min_val, max_val):
        """Get members from sorted set by score range"""
        if self.redis_client:
            try:
                return await self.redis_client.zrangebyscore(key, min_val, max_val)
            except Exception as e:
                logger.warning(f"Failed to zrangebyscore from {key}: {e}")
                return []
        return []

    async def rpop(self, key: str, user_id: Optional[str] = None):
        """Pop item from right side of list with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.rpop(actual_key)
            except Exception as e:
                logger.warning(f"Failed to rpop from {actual_key}: {e}")
                return None
        return None

    async def llen(self, key: str, user_id: Optional[str] = None):
        """Get length of list with optional user namespacing"""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return await self.redis_client.llen(actual_key)
            except Exception as e:
                logger.warning(f"Failed to get llen of {actual_key}: {e}")
                return 0
        return 0

    async def scard(self, key: str):
        """Get number of members in set"""
        if self.redis_client:
            try:
                return await self.redis_client.scard(key)
            except Exception as e:
                logger.warning(f"Failed to get scard of {key}: {e}")
                return 0
        return 0

    async def scan_keys(self, pattern: str):
        """Scan keys matching pattern (equivalent to keys but more efficient)"""
        if self.redis_client:
            try:
                return await self.redis_client.keys(pattern)
            except Exception as e:
                logger.warning(f"Failed to scan keys with pattern {pattern}: {e}")
                return []
        return []

    async def setex(self, key: str, time: int, value: str, user_id: Optional[str] = None) -> bool:
        """Set key-value pair with expiration and optional user namespacing."""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                await self.redis_client.setex(actual_key, time, value)
                return True
            except Exception as e:
                logger.warning(f"Failed to setex {actual_key}: {e}")
                return False
        return False

    async def exists(self, key: str, user_id: Optional[str] = None) -> bool:
        """Check if key exists in Redis with optional user namespacing."""
        actual_key = self._namespace_key(user_id, key) if user_id is not None else key
        if self.redis_client:
            try:
                return bool(await self.redis_client.exists(actual_key))
            except Exception as e:
                logger.warning(f"Failed to check exists for {actual_key}: {e}")
                return False
        return False

    async def acquire_leader_lock(self, instance_id: str, ttl: int = 30) -> bool:
        """
        Acquire distributed leader lock to prevent split-brain.
        
        Args:
            instance_id: Unique instance identifier
            ttl: Lock time-to-live in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        # Test mode - simulate lock behavior without Redis
        if self.test_mode:
            lock_key = "leader_lock"
            
            if lock_key not in self.test_locks:
                # No one has the lock, acquire it
                self.test_locks[lock_key] = instance_id
                logger.info(f"Leader lock acquired by {instance_id} (test mode)")
                return True
            else:
                # Someone else has the lock
                current_leader = self.test_locks[lock_key]
                logger.debug(f"Leader lock held by {current_leader}, {instance_id} failed to acquire (test mode)")
                return False
        
        # Normal mode - actual Redis
        if not self.redis_client:
            return False
            
        lock_key = "leader_lock"
        
        try:
            # Use SET with NX (only if not exists) and EX (expiration)
            result = await self.redis_client.set(
                lock_key, 
                instance_id, 
                nx=True,  # Only set if key doesn't exist
                ex=ttl    # Set expiration time
            )
            
            if result:
                logger.info(f"Leader lock acquired by {instance_id}")
                return True
            else:
                current_leader = await self.redis_client.get(lock_key)
                logger.debug(f"Leader lock held by {current_leader}, {instance_id} failed to acquire")
                return False
                
        except Exception as e:
            logger.error(f"Redis leader lock error: {e}")
            return False
            
    async def release_leader_lock(self, instance_id: str) -> bool:
        """
        Release leader lock if held by this instance.
        
        Args:
            instance_id: Instance identifier that should hold the lock
            
        Returns:
            True if lock released, False otherwise
        """
        # Test mode - simulate lock behavior without Redis
        if self.test_mode:
            lock_key = "leader_lock"
            
            if lock_key in self.test_locks and self.test_locks[lock_key] == instance_id:
                del self.test_locks[lock_key]
                logger.info(f"Leader lock released by {instance_id} (test mode)")
                return True
            else:
                logger.warning(f"Lock not held by {instance_id}, cannot release (test mode)")
                return False
        
        # Normal mode - actual Redis
        if not self.redis_client:
            return False
            
        lock_key = "leader_lock"
        
        try:
            # Lua script to atomically check and release
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, 1, lock_key, instance_id)
            
            if result:
                logger.info(f"Leader lock released by {instance_id}")
                return True
            else:
                logger.warning(f"Lock not held by {instance_id}, cannot release")
                return False
                
        except Exception as e:
            logger.error(f"Redis leader lock release error: {e}")
            return False

    async def ping(self) -> bool:
        """Test Redis connection."""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False

    def pipeline(self):
        """Create Redis pipeline for batch operations."""
        if self.redis_client:
            return self.redis_client.pipeline()
        return None

# Main instance for netra_backend service
redis_manager = RedisManager()

# Export for compatibility
unified_redis_manager = redis_manager
