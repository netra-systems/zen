"""
JWT Performance Optimization - Phase 1 JWT SSOT Remediation
Performance enhancements for increased auth service load
Includes caching, connection pooling, rate limiting, and monitoring
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field

from auth_service.auth_core.redis_manager import auth_redis_manager
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    current_load: int = 0
    peak_load: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class JWTPerformanceOptimizer:
    """
    Performance optimization for JWT validation APIs
    
    Features:
    - Response caching with TTL
    - Rate limiting per service/user
    - Connection pooling for database
    - Monitoring and metrics collection
    - Circuit breaker patterns
    """
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.rate_limits = defaultdict(deque)  # Rate limiting per client
        self.circuit_breakers = {}  # Circuit breakers per service
        self.cache_enabled = True
        self.rate_limit_enabled = True
        
        # Performance thresholds
        self.max_requests_per_minute = 1000
        self.cache_ttl_seconds = 300  # 5 minutes
        self.circuit_breaker_threshold = 5  # failures before opening
        self.circuit_breaker_timeout = 60  # seconds
        
        logger.info("JWT Performance Optimizer initialized")
    
    async def track_request(self, operation: str, client_id: str = None) -> Optional[str]:
        """
        Track incoming request and check rate limits
        
        Returns:
            None if request is allowed, error message if rate limited
        """
        try:
            self.metrics.total_requests += 1
            self.metrics.current_load += 1
            
            if self.metrics.current_load > self.metrics.peak_load:
                self.metrics.peak_load = self.metrics.current_load
            
            # Check rate limits if enabled
            if self.rate_limit_enabled and client_id:
                if await self._is_rate_limited(client_id):
                    return "rate_limit_exceeded"
            
            # Check circuit breaker for operation
            if await self._is_circuit_breaker_open(operation):
                return "service_temporarily_unavailable"
            
            return None
            
        except Exception as e:
            logger.error(f"Request tracking error: {e}")
            return None
    
    async def track_response(self, operation: str, success: bool, response_time: float, 
                           client_id: str = None) -> None:
        """
        Track response completion and update metrics
        """
        try:
            self.metrics.current_load = max(0, self.metrics.current_load - 1)
            
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
                await self._record_circuit_breaker_failure(operation)
            
            # Update response time metrics
            self.response_times.append(response_time)
            
            if response_time > self.metrics.max_response_time:
                self.metrics.max_response_time = response_time
            
            if response_time < self.metrics.min_response_time:
                self.metrics.min_response_time = response_time
            
            # Calculate rolling average
            if self.response_times:
                self.metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
            
        except Exception as e:
            logger.error(f"Response tracking error: {e}")
    
    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available
        """
        if not self.cache_enabled:
            return None
        
        try:
            if auth_redis_manager.enabled:
                # Try Redis cache first
                redis_client = auth_redis_manager.get_client()
                if redis_client:
                    cached_data = await redis_client.get(cache_key)
                    if cached_data:
                        self.metrics.cache_hits += 1
                        import json
                        return json.loads(cached_data)
            
            # Cache miss
            self.metrics.cache_misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            self.metrics.cache_misses += 1
            return None
    
    async def cache_response(self, cache_key: str, response_data: Dict[str, Any], 
                           ttl: int = None) -> bool:
        """
        Cache response data with TTL
        """
        if not self.cache_enabled:
            return False
        
        try:
            ttl = ttl or self.cache_ttl_seconds
            
            if auth_redis_manager.enabled:
                redis_client = auth_redis_manager.get_client()
                if redis_client:
                    import json
                    await redis_client.setex(
                        cache_key, 
                        ttl, 
                        json.dumps(response_data, default=str)
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
    
    async def _is_rate_limited(self, client_id: str) -> bool:
        """
        Check if client has exceeded rate limits
        """
        try:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old requests
            client_requests = self.rate_limits[client_id]
            while client_requests and client_requests[0] < minute_ago:
                client_requests.popleft()
            
            # Check if limit exceeded
            if len(client_requests) >= self.max_requests_per_minute:
                logger.warning(f"Rate limit exceeded for client: {client_id}")
                return True
            
            # Record this request
            client_requests.append(now)
            return False
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return False
    
    async def _is_circuit_breaker_open(self, operation: str) -> bool:
        """
        Check if circuit breaker is open for operation
        """
        try:
            breaker = self.circuit_breakers.get(operation)
            if not breaker:
                return False
            
            # Check if circuit breaker has timed out and can be reset
            if breaker['opened_at'] + self.circuit_breaker_timeout < time.time():
                del self.circuit_breakers[operation]
                logger.info(f"Circuit breaker reset for operation: {operation}")
                return False
            
            return breaker['is_open']
            
        except Exception as e:
            logger.error(f"Circuit breaker check error: {e}")
            return False
    
    async def _record_circuit_breaker_failure(self, operation: str) -> None:
        """
        Record failure for circuit breaker
        """
        try:
            if operation not in self.circuit_breakers:
                self.circuit_breakers[operation] = {
                    'failures': 0,
                    'is_open': False,
                    'opened_at': None
                }
            
            breaker = self.circuit_breakers[operation]
            breaker['failures'] += 1
            
            # Open circuit breaker if threshold exceeded
            if breaker['failures'] >= self.circuit_breaker_threshold and not breaker['is_open']:
                breaker['is_open'] = True
                breaker['opened_at'] = time.time()
                logger.warning(f"Circuit breaker opened for operation: {operation}")
            
        except Exception as e:
            logger.error(f"Circuit breaker failure recording error: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics
        """
        try:
            return {
                "requests": {
                    "total": self.metrics.total_requests,
                    "successful": self.metrics.successful_requests,
                    "failed": self.metrics.failed_requests,
                    "success_rate": (
                        self.metrics.successful_requests / max(1, self.metrics.total_requests) * 100
                    )
                },
                "cache": {
                    "hits": self.metrics.cache_hits,
                    "misses": self.metrics.cache_misses,
                    "hit_rate": (
                        self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses) * 100
                    ),
                    "enabled": self.cache_enabled
                },
                "response_times": {
                    "average_ms": round(self.metrics.avg_response_time * 1000, 2),
                    "max_ms": round(self.metrics.max_response_time * 1000, 2),
                    "min_ms": round(self.metrics.min_response_time * 1000, 2) if self.metrics.min_response_time != float('inf') else 0
                },
                "load": {
                    "current": self.metrics.current_load,
                    "peak": self.metrics.peak_load
                },
                "rate_limiting": {
                    "enabled": self.rate_limit_enabled,
                    "max_requests_per_minute": self.max_requests_per_minute,
                    "active_clients": len(self.rate_limits)
                },
                "circuit_breakers": {
                    "active": len([b for b in self.circuit_breakers.values() if b['is_open']]),
                    "total": len(self.circuit_breakers)
                },
                "last_reset": self.metrics.last_reset.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance stats error: {e}")
            return {"error": "stats_unavailable"}
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        try:
            self.metrics = PerformanceMetrics()
            self.response_times.clear()
            logger.info("Performance metrics reset")
        except Exception as e:
            logger.error(f"Metrics reset error: {e}")
    
    def generate_cache_key(self, operation: str, **params) -> str:
        """
        Generate cache key for operation and parameters
        """
        try:
            # Sort parameters for consistent key generation
            sorted_params = sorted(params.items())
            param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            return f"jwt_api:{operation}:{param_string}"
        except Exception as e:
            logger.error(f"Cache key generation error: {e}")
            return f"jwt_api:{operation}:error"

class ConnectionPoolManager:
    """
    Connection pool management for database and external services
    """
    
    def __init__(self):
        self.pools = {}
        self.max_connections = 20
        self.min_connections = 5
        self.connection_timeout = 30
        
    async def get_database_pool(self) -> Optional[Any]:
        """
        Get database connection pool
        """
        try:
            if "database" not in self.pools:
                # Initialize database pool
                await self._initialize_database_pool()
            
            return self.pools.get("database")
            
        except Exception as e:
            logger.error(f"Database pool error: {e}")
            return None
    
    async def _initialize_database_pool(self) -> None:
        """
        Initialize database connection pool
        """
        try:
            # This would initialize actual database pool
            # For now, just mark as initialized
            self.pools["database"] = {
                "initialized": True,
                "max_connections": self.max_connections,
                "current_connections": 0
            }
            
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Database pool initialization error: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics
        """
        return {
            "pools": list(self.pools.keys()),
            "configuration": {
                "max_connections": self.max_connections,
                "min_connections": self.min_connections,
                "connection_timeout": self.connection_timeout
            }
        }

# Global performance optimizer instance
jwt_performance_optimizer = JWTPerformanceOptimizer()
connection_pool_manager = ConnectionPoolManager()

# Performance decorator for API endpoints
def track_performance(operation_name: str):
    """
    Decorator to track performance of API operations
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            client_id = kwargs.get('client_id') or 'unknown'
            
            # Track request start
            rate_limit_error = await jwt_performance_optimizer.track_request(operation_name, client_id)
            if rate_limit_error:
                return {"error": rate_limit_error}
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Track successful response
                response_time = time.time() - start_time
                await jwt_performance_optimizer.track_response(operation_name, True, response_time, client_id)
                
                return result
                
            except Exception as e:
                # Track failed response
                response_time = time.time() - start_time
                await jwt_performance_optimizer.track_response(operation_name, False, response_time, client_id)
                raise e
        
        return wrapper
    return decorator