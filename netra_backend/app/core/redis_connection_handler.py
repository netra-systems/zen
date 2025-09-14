"""Redis Connection Handler for Netra Backend

**CRITICAL**: Enterprise-Grade Redis Connection Management
Provides environment-aware Redis connection configuration with proper
host resolution and connection pooling for staging and production environments.

Business Value: Prevents cache and session failures costing $30K+ MRR
Critical for session persistence and caching performance.

Each function  <= 8 lines, file  <= 300 lines.
"""

import logging
from typing import Dict, Any, Optional

# MIGRATED: Use SSOT Redis import pattern
from shared.isolated_environment import get_env

from netra_backend.app.core.configuration.base import UnifiedConfigManager

logger = logging.getLogger(__name__)


class RedisConnectionError(Exception):
    """Raised when Redis connection operations fail."""
    pass


class RedisConnectionHandler:
    """Enterprise Redis connection handler with environment-aware configuration.
    
    **CRITICAL**: All Redis connections MUST use this handler.
    Provides proper host resolution, connection pooling, and environment-specific configuration.
    """
    
    def __init__(self):
        """Initialize Redis connection handler with environment configuration."""
        self.env = get_env().get("ENVIRONMENT", "development").lower()
        self._config = UnifiedConfigManager().get_config()
        self._connection_pool = None
        self._connection_info = self._build_connection_info()
        
    def _build_connection_info(self) -> Dict[str, Any]:
        """Build Redis connection information based on environment."""
        # Get base configuration
        host = get_env().get("REDIS_HOST", "localhost")
        port = int(get_env().get("REDIS_PORT", "6379"))
        db = int(get_env().get("REDIS_DB", "0"))
        
        # Environment-specific host resolution
        if self.env == "staging":
            # In staging, never use localhost
            if host in ["localhost", "127.0.0.1"]:
                # Override with proper staging Redis host
                host = get_env().get("REDIS_STAGING_HOST") or "redis-staging.internal"
                logger.warning(f"Overriding localhost Redis with staging host: {host}")
                
        elif self.env == "production":
            # In production, never use localhost
            if host in ["localhost", "127.0.0.1"]:
                # Override with proper production Redis host
                host = get_env().get("REDIS_PRODUCTION_HOST") or "redis-production.internal"
                logger.warning(f"Overriding localhost Redis with production host: {host}")
        
        # Build connection info
        connection_info = {
            "host": host,
            "port": port,
            "db": db,
            "environment": self.env,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30
        }
        
        # Add SSL configuration for staging/production
        if self.env in ["staging", "production"]:
            connection_info["ssl"] = True
            connection_info["ssl_cert_reqs"] = "required" 
            connection_info["ssl_check_hostname"] = True
            
        return connection_info
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get Redis connection information."""
        return self._connection_info.copy()
    
    def create_connection_pool(self):
        """Create Redis connection pool with proper configuration."""
        if self._connection_pool is None:
            try:
                # Use SSOT Redis import pattern
                import redis
                
                pool_config = {
                    "host": self._connection_info["host"],
                    "port": self._connection_info["port"],
                    "db": self._connection_info["db"],
                    "socket_timeout": self._connection_info["socket_timeout"],
                    "socket_connect_timeout": self._connection_info["socket_connect_timeout"],
                    "retry_on_timeout": self._connection_info["retry_on_timeout"],
                    "health_check_interval": self._connection_info["health_check_interval"],
                    "max_connections": 20,
                    "connection_class": redis.Connection
                }
                
                # Add SSL for staging/production
                if self.env in ["staging", "production"]:
                    pool_config.update({
                        "ssl": self._connection_info["ssl"],
                        "ssl_cert_reqs": self._connection_info["ssl_cert_reqs"],
                        "ssl_check_hostname": self._connection_info["ssl_check_hostname"]
                    })
                
                self._connection_pool = redis.ConnectionPool(**pool_config)
                logger.info(f"Created Redis connection pool for {self.env} environment: {self._connection_info['host']}:{self._connection_info['port']}")
                
            except Exception as e:
                raise RedisConnectionError(f"Failed to create Redis connection pool: {e}")
                
        return self._connection_pool
    
    def get_redis_client(self, enable_circuit_breaker: bool = True):
        """Get Redis client with proper connection configuration and circuit breaker.

        Args:
            enable_circuit_breaker: Enable graceful degradation for Redis failures

        Returns:
            Redis client or None if circuit breaker is open
        """
        try:
            # Use SSOT Redis import pattern
            import redis

            # CRITICAL FIX: Add circuit breaker for Issue #1029 Redis connection failures
            if enable_circuit_breaker and not self._check_circuit_breaker():
                logger.warning("Redis circuit breaker is OPEN - returning None for graceful degradation")
                return None

            # Create Redis client directly with connection info
            client = redis.Redis(
                host=self._connection_info["host"],
                port=self._connection_info["port"],
                db=self._connection_info["db"],
                socket_timeout=self._connection_info["socket_timeout"],
                socket_connect_timeout=self._connection_info["socket_connect_timeout"],
                retry_on_timeout=self._connection_info["retry_on_timeout"],
                health_check_interval=self._connection_info["health_check_interval"],
                decode_responses=True
            )

            # Test connection
            client.ping()
            self._record_success()
            logger.info(f"Redis client connected successfully to {self._connection_info['host']} ({self.env})")
            return client

        except Exception as e:
            self._record_failure()
            if enable_circuit_breaker:
                logger.warning(f"Redis connection failed, circuit breaker updated: {e}")
                return None  # Graceful degradation
            else:
                raise RedisConnectionError(f"Failed to create Redis client: {e}")

    def _check_circuit_breaker(self) -> bool:
        """Check if Redis circuit breaker allows connections.

        Returns:
            True if connections allowed, False if circuit breaker is open
        """
        import time

        # Initialize circuit breaker state if not exists
        if not hasattr(self, '_circuit_breaker_failures'):
            self._circuit_breaker_failures = 0
            self._circuit_breaker_last_failure = 0
            self._circuit_breaker_threshold = 3  # Open after 3 failures
            self._circuit_breaker_timeout = 60   # Retry after 60 seconds

        current_time = time.time()

        # If we have too many failures and haven't waited long enough, circuit is open
        if (self._circuit_breaker_failures >= self._circuit_breaker_threshold and
            current_time - self._circuit_breaker_last_failure < self._circuit_breaker_timeout):
            return False

        # If enough time has passed, allow retry (half-open state)
        if current_time - self._circuit_breaker_last_failure >= self._circuit_breaker_timeout:
            self._circuit_breaker_failures = 0  # Reset for retry attempt

        return True

    def _record_success(self):
        """Record successful Redis connection (circuit breaker)."""
        self._circuit_breaker_failures = 0

    def _record_failure(self):
        """Record failed Redis connection (circuit breaker)."""
        import time
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
        logger.warning(f"Redis circuit breaker failure count: {self._circuit_breaker_failures}")

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status for monitoring."""
        import time

        if not hasattr(self, '_circuit_breaker_failures'):
            return {"state": "closed", "failures": 0, "threshold": 0}

        current_time = time.time()
        is_open = (self._circuit_breaker_failures >= self._circuit_breaker_threshold and
                  current_time - self._circuit_breaker_last_failure < self._circuit_breaker_timeout)

        return {
            "state": "open" if is_open else "closed",
            "failures": self._circuit_breaker_failures,
            "threshold": self._circuit_breaker_threshold,
            "seconds_until_retry": max(0, self._circuit_breaker_timeout -
                                     (current_time - self._circuit_breaker_last_failure)) if is_open else 0,
            "last_failure_timestamp": self._circuit_breaker_last_failure
        }
    
    def validate_connection(self) -> Dict[str, Any]:
        """Validate Redis connection and return status."""
        status = {
            "environment": self.env,
            "host": self._connection_info["host"],
            "port": self._connection_info["port"],
            "connected": False,
            "response_time_ms": None,
            "error": None
        }
        
        try:
            import time
            start_time = time.time()
            
            client = self.get_redis_client()
            pong = client.ping()
            
            end_time = time.time()
            status["connected"] = bool(pong)
            status["response_time_ms"] = round((end_time - start_time) * 1000, 2)
            
        except Exception as e:
            status["error"] = str(e)
            logger.error(f"Redis connection validation failed: {e}")
            
        return status
    
    def get_environment_config_status(self) -> Dict[str, Any]:
        """Get Redis environment configuration status for monitoring."""
        config_status = {
            "environment": self.env,
            "host_configured": bool(self._connection_info["host"]),
            "localhost_warning": self._connection_info["host"] in ["localhost", "127.0.0.1"],
            "ssl_enabled": self._connection_info.get("ssl", False),
            "connection_info": self._connection_info
        }
        
        # Add environment-specific warnings
        if self.env in ["staging", "production"] and config_status["localhost_warning"]:
            config_status["warning"] = f"Redis using localhost in {self.env} environment - should use proper Redis service"
            
        return config_status
    
    @classmethod 
    def get_recommended_config(cls, environment: str) -> Dict[str, str]:
        """Get recommended Redis configuration for specific environment."""
        configs = {
            "development": {
                "REDIS_HOST": "localhost",
                "REDIS_PORT": "6379",
                "REDIS_DB": "0"
            },
            "staging": {
                "REDIS_HOST": "redis-staging.internal",
                "REDIS_PORT": "6380",
                "REDIS_DB": "1",
                "REDIS_STAGING_HOST": "redis-staging.internal"
            },
            "production": {
                "REDIS_HOST": "redis-production.internal", 
                "REDIS_PORT": "6380",
                "REDIS_DB": "2",
                "REDIS_PRODUCTION_HOST": "redis-production.internal"
            }
        }
        
        return configs.get(environment.lower(), configs["development"])