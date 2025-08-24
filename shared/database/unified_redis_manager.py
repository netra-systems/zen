"""
Unified Redis Connection Manager - Cross-Service Redis Utilities

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate Redis connection duplication across all services  
- Value Impact: Single source of truth for Redis connection logic, retry patterns, and error handling
- Strategic Impact: Consistent Redis behavior, reduced maintenance overhead, unified monitoring

This module provides unified Redis connection management that can be used across:
- auth_service (session management, OAuth state)
- netra_backend (caching, pubsub, rate limiting)  
- dev_launcher (service discovery, health checks)

Key functionality:
- Unified connection creation with fallback logic
- Consistent retry patterns with exponential backoff
- Environment-aware connection configuration
- Cross-service compatible interface
- Graceful degradation when Redis unavailable

Replaces 8+ duplicate Redis connection implementations with a single unified manager.
Each function ≤25 lines, class ≤300 lines total.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Import Redis with both sync and async support
try:
    import redis
    import redis.asyncio as redis_async
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from dev_launcher.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class RedisMode(Enum):
    """Redis operation modes."""
    DISABLED = "disabled"
    LOCAL = "local"
    REMOTE = "remote"
    SHARED = "shared"
    STANDALONE = "standalone"


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    db: int = 0
    decode_responses: bool = True
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0


class UnifiedRedisManager:
    """
    Unified Redis connection manager for all services.
    
    Provides consistent Redis connection handling, retry logic, and error handling
    across auth_service, netra_backend, and dev_launcher.
    """
    
    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self.redis_client = None
        self._async_client = None
        self.config = RedisConfig()
        self.env = IsolatedEnvironment()
        self.enabled = self._determine_redis_availability()
        self._connection_attempts = 0
        
    def _determine_redis_availability(self) -> bool:
        """Determine if Redis should be enabled based on environment."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available")
            return False
            
        # Check explicit disable flags
        if self.env.get("REDIS_DISABLED", "false").lower() == "true":
            logger.info("Redis disabled by REDIS_DISABLED flag")
            return False
            
        # Check environment-specific settings
        environment = self.env.get("ENVIRONMENT", "development").lower()
        if environment == "staging":
            # Redis typically disabled in staging for some services
            return self.env.get("STAGING_REDIS_ENABLED", "false").lower() == "true"
            
        # Default to enabled for development/production
        return True
    
    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration from environment."""
        config = RedisConfig()
        
        # Basic connection settings
        config.host = self.env.get("REDIS_HOST", "localhost")
        config.port = int(self.env.get("REDIS_PORT", "6379"))
        config.username = self.env.get("REDIS_USERNAME")
        config.password = self.env.get("REDIS_PASSWORD")
        config.db = int(self.env.get("REDIS_DB", "0"))
        
        # Connection timeouts
        config.socket_connect_timeout = int(self.env.get("REDIS_CONNECT_TIMEOUT", "5"))
        config.socket_timeout = int(self.env.get("REDIS_SOCKET_TIMEOUT", "5"))
        
        # Retry configuration
        config.max_retries = int(self.env.get("REDIS_MAX_RETRIES", "3"))
        config.backoff_factor = float(self.env.get("REDIS_BACKOFF_FACTOR", "1.0"))
        
        return config
    
    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from environment or construct from config."""
        # Try direct URL first
        redis_url = self.env.get("REDIS_URL")
        if redis_url:
            return redis_url
            
        # Construct from components
        config = self._load_redis_config()
        auth_part = ""
        if config.username and config.password:
            auth_part = f"{config.username}:{config.password}@"
        elif config.password:
            auth_part = f":{config.password}@"
            
        return f"redis://{auth_part}{config.host}:{config.port}/{config.db}"
    
    def _create_sync_client(self) -> Optional[redis.Redis]:
        """Create synchronous Redis client."""
        try:
            redis_url = self._get_redis_url()
            if redis_url:
                return redis.from_url(
                    redis_url,
                    decode_responses=self.config.decode_responses,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    socket_timeout=self.config.socket_timeout,
                    retry_on_timeout=self.config.retry_on_timeout,
                    health_check_interval=self.config.health_check_interval
                )
            else:
                config = self._load_redis_config()
                return redis.Redis(
                    host=config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    db=config.db,
                    decode_responses=config.decode_responses,
                    socket_connect_timeout=config.socket_connect_timeout,
                    socket_timeout=config.socket_timeout,
                    retry_on_timeout=config.retry_on_timeout,
                    health_check_interval=config.health_check_interval
                )
        except Exception as e:
            logger.error(f"Failed to create sync Redis client: {e}")
            return None
    
    async def _create_async_client(self) -> Optional[redis_async.Redis]:
        """Create asynchronous Redis client."""
        try:
            redis_url = self._get_redis_url()
            if redis_url:
                return redis_async.from_url(
                    redis_url,
                    decode_responses=self.config.decode_responses,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    socket_timeout=self.config.socket_timeout
                )
            else:
                config = self._load_redis_config()
                return redis_async.Redis(
                    host=config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    db=config.db,
                    decode_responses=config.decode_responses,
                    socket_connect_timeout=config.socket_connect_timeout,
                    socket_timeout=config.socket_timeout
                )
        except Exception as e:
            logger.error(f"Failed to create async Redis client: {e}")
            return None
    
    def _test_connection(self, client) -> bool:
        """Test Redis connection (sync)."""
        try:
            client.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis connection test failed: {e}")
            return False
    
    async def _test_connection_async(self, client) -> bool:
        """Test Redis connection (async)."""
        try:
            await client.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis async connection test failed: {e}")
            return False
    
    def _try_fallback_connections(self) -> Optional[redis.Redis]:
        """Try fallback connection strategies."""
        fallback_configs = [
            {"host": "localhost", "port": 6379},
            {"host": "127.0.0.1", "port": 6379},
        ]
        
        # Add test container ports if available
        test_redis_host = self.env.get("TEST_REDIS_HOST", "localhost")
        test_redis_port = self.env.get("TEST_REDIS_PORT")
        if test_redis_port:
            fallback_configs.insert(0, {"host": test_redis_host, "port": int(test_redis_port)})
        
        for config in fallback_configs:
            try:
                client = redis.Redis(
                    host=config["host"],
                    port=config["port"],
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1
                )
                if self._test_connection(client):
                    logger.info(f"Connected to fallback Redis: {config['host']}:{config['port']}")
                    return client
            except Exception:
                continue
        
        return None
    
    def connect(self) -> bool:
        """
        Establish synchronous Redis connection.
        
        Returns:
            True if connection successful or Redis disabled, False if failed
        """
        if not self.enabled:
            logger.debug(f"Redis disabled for {self.service_name}")
            return True  # Not an error if disabled
        
        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            try:
                self.redis_client = self._create_sync_client()
                if self.redis_client and self._test_connection(self.redis_client):
                    logger.info(f"Redis connected for {self.service_name}")
                    self._connection_attempts = 0
                    return True
            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            # Try fallback on last attempt
            if attempt == max_retries - 1:
                self.redis_client = self._try_fallback_connections()
                if self.redis_client:
                    return True
                    
            # Exponential backoff
            if attempt < max_retries - 1:
                backoff_time = self.config.backoff_factor * (2 ** attempt)
                time.sleep(min(backoff_time, 10))  # Cap at 10 seconds
        
        logger.warning(f"Redis connection failed for {self.service_name} - operating without Redis")
        self.redis_client = None
        self._connection_attempts += 1
        return False
    
    async def connect_async(self) -> bool:
        """
        Establish asynchronous Redis connection.
        
        Returns:
            True if connection successful or Redis disabled, False if failed
        """
        if not self.enabled:
            logger.debug(f"Redis disabled for {self.service_name}")
            return True  # Not an error if disabled
        
        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            try:
                self._async_client = await self._create_async_client()
                if self._async_client and await self._test_connection_async(self._async_client):
                    logger.info(f"Redis async connected for {self.service_name}")
                    self._connection_attempts = 0
                    return True
            except Exception as e:
                logger.warning(f"Redis async connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            # Exponential backoff
            if attempt < max_retries - 1:
                backoff_time = self.config.backoff_factor * (2 ** attempt)
                await asyncio.sleep(min(backoff_time, 10))  # Cap at 10 seconds
        
        logger.warning(f"Redis async connection failed for {self.service_name} - operating without Redis")
        self._async_client = None
        self._connection_attempts += 1
        return False
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get synchronous Redis client."""
        return self.redis_client
    
    def get_async_client(self) -> Optional[redis_async.Redis]:
        """Get asynchronous Redis client."""
        return self._async_client
    
    def is_available(self) -> bool:
        """Check if Redis is available and connected."""
        return self.redis_client is not None or self._async_client is not None
    
    def disconnect(self) -> None:
        """Disconnect synchronous Redis client."""
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception as e:
                logger.debug(f"Error closing Redis connection: {e}")
            finally:
                self.redis_client = None
    
    async def disconnect_async(self) -> None:
        """Disconnect asynchronous Redis client."""
        if self._async_client:
            try:
                await self._async_client.close()
            except Exception as e:
                logger.debug(f"Error closing async Redis connection: {e}")
            finally:
                self._async_client = None
    
    # Common Redis operations with error handling
    def safe_get(self, key: str, default: Any = None) -> Any:
        """Safely get value from Redis with fallback."""
        if not self.redis_client:
            return default
        try:
            result = self.redis_client.get(key)
            return result if result is not None else default
        except Exception as e:
            logger.debug(f"Redis GET failed for {key}: {e}")
            return default
    
    def safe_set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Safely set value in Redis."""
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.set(key, value, ex=ex))
        except Exception as e:
            logger.debug(f"Redis SET failed for {key}: {e}")
            return False
    
    def safe_delete(self, *keys: str) -> int:
        """Safely delete keys from Redis."""
        if not self.redis_client or not keys:
            return 0
        try:
            return self.redis_client.delete(*keys)
        except Exception as e:
            logger.debug(f"Redis DELETE failed for {keys}: {e}")
            return 0


# Global instances for common service patterns
def get_redis_manager(service_name: str) -> UnifiedRedisManager:
    """Get Redis manager instance for a service."""
    if not hasattr(get_redis_manager, '_instances'):
        get_redis_manager._instances = {}
    
    if service_name not in get_redis_manager._instances:
        get_redis_manager._instances[service_name] = UnifiedRedisManager(service_name)
    
    return get_redis_manager._instances[service_name]


# Common service managers
auth_redis_manager = get_redis_manager("auth_service")
backend_redis_manager = get_redis_manager("netra_backend") 
launcher_redis_manager = get_redis_manager("dev_launcher")