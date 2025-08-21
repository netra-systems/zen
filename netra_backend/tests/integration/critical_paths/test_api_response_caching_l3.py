"""API Response Caching L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API performance optimization)
- Business Goal: Reduce response times and backend load
- Value Impact: Improves user experience, reduces infrastructure costs
- Strategic Impact: $15K MRR protection through efficient resource utilization

Critical Path: Request analysis -> Cache lookup -> Cache hit/miss -> Response generation -> Cache storage
Coverage: Cache strategies, TTL management, cache invalidation, cache warming, performance optimization
"""

import pytest
import asyncio
import time
import uuid
import logging
import hashlib
import aiohttp
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
from enum import Enum

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.api_gateway.cache_manager import ApiCacheManager
from netra_backend.app.services.api_gateway.cache_strategies import CacheStrategy
from netra_backend.app.services.redis.redis_cache import RedisCache
from netra_backend.app.services.metrics.cache_metrics import CacheMetricsService

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class CacheRule:
    """Cache rule configuration for endpoints."""
    endpoint_pattern: str
    cache_strategy: str  # time_based, content_based, user_based, no_cache
    ttl_seconds: int
    cache_key_params: List[str]  # Parameters to include in cache key
    invalidation_triggers: List[str]  # Events that invalidate cache
    compression_enabled: bool
    max_cache_size_mb: float


class ApiCacheManager:
    """Manages L3 API response caching tests with real Redis caching."""
    
    def __init__(self):
        self.cache_manager = None
        self.redis_cache = None
        self.metrics_service = None
        self.test_server = None
        self.cache_rules = {}
        self.cache_hits = []
        self.cache_misses = []
        self.cache_invalidations = []
        self.response_times = []
        self.cache_storage = {}  # In-memory for testing
        
    async def initialize_caching(self):
        """Initialize API caching services for L3 testing."""
        try:
            self.cache_manager = ApiCacheManager()
            await self.cache_manager.initialize()
            
            self.redis_cache = RedisCache()
            await self.redis_cache.initialize()
            
            self.metrics_service = CacheMetricsService()
            await self.metrics_service.initialize()
            
            # Configure cache rules for different endpoints
            await self.setup_cache_rules()
            
            # Start test server with caching
            await self.start_cached_test_server()
            
            logger.info("API caching services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize API caching services: {e}")
            raise
    
    async def setup_cache_rules(self):
        """Configure caching rules for different API endpoints."""
        self.cache_rules = {
            # User data - time-based caching
            "/api/v1/users/{user_id}": CacheRule(
                endpoint_pattern="/api/v1/users/{user_id}",
                cache_strategy="time_based",
                ttl_seconds=300,  # 5 minutes
                cache_key_params=["user_id"],
                invalidation_triggers=["user_updated", "profile_changed"],
                compression_enabled=True,
                max_cache_size_mb=10.0
            ),
            # Thread list - user-based caching
            "/api/v1/threads": CacheRule(
                endpoint_pattern="/api/v1/threads",
                cache_strategy="user_based",
                ttl_seconds=600,  # 10 minutes
                cache_key_params=["user_id", "limit", "offset"],
                invalidation_triggers=["thread_created", "thread_deleted"],
                compression_enabled=True,
                max_cache_size_mb=50.0
            ),
            # Agent configurations - content-based caching
            "/api/v1/agents/config": CacheRule(
                endpoint_pattern="/api/v1/agents/config",
                cache_strategy="content_based",
                ttl_seconds=3600,  # 1 hour
                cache_key_params=["version", "feature_flags"],
                invalidation_triggers=["config_updated", "deployment"],
                compression_enabled=False,
                max_cache_size_mb=5.0
            ),
            # Metrics data - short-term caching
            "/api/v1/metrics": CacheRule(
                endpoint_pattern="/api/v1/metrics",
                cache_strategy="time_based",
                ttl_seconds=60,  # 1 minute
                cache_key_params=["timerange", "granularity"],
                invalidation_triggers=["metrics_updated"],
                compression_enabled=True,
                max_cache_size_mb=100.0
            ),
            # Real-time data - no caching
            "/api/v1/websocket/status": CacheRule(
                endpoint_pattern="/api/v1/websocket/status",
                cache_strategy="no_cache",
                ttl_seconds=0,
                cache_key_params=[],
                invalidation_triggers=[],
                compression_enabled=False,
                max_cache_size_mb=0.0
            ),
            # Static content - long-term caching
            "/api/v1/static/{resource}": CacheRule(
                endpoint_pattern="/api/v1/static/{resource}",
                cache_strategy="content_based",
                ttl_seconds=86400,  # 24 hours
                cache_key_params=["resource", "version"],
                invalidation_triggers=["static_updated"],
                compression_enabled=True,
                max_cache_size_mb=200.0
            )
        }
        
        # Register cache rules
        for pattern, rule in self.cache_rules.items():
            await self.cache_manager.add_cache_rule(pattern, rule)
    
    async def start_cached_test_server(self):
        """Start test server with caching middleware."""
        from aiohttp import web
        
        async def cache_middleware(request, handler):
            """Caching middleware for test server."""
            start_time = time.time()
            
            # Check if endpoint should be cached
            cache_rule = await self.find_cache_rule(request.path)
            
            if not cache_rule or cache_rule.cache_strategy == "no_cache":
                # No caching - proceed normally
                response = await handler(request)
                self.record_response_time(request.path, time.time() - start_time, "no_cache")
                return response
            
            # Generate cache key
            cache_key = await self.generate_cache_key(request, cache_rule)
            
            # Check cache
            cached_response = await self.get_cached_response(cache_key)
            
            if cached_response:
                # Cache hit
                self.record_cache_hit(request.path, cache_key, cache_rule.cache_strategy)
                self.record_response_time(request.path, time.time() - start_time, "cache_hit")
                
                return web.Response(
                    status=200,
                    headers={
                        "X-Cache-Status": "HIT",
                        "X-Cache-Key": cache_key,
                        "X-Cache-TTL": str(cached_response["ttl_remaining"]),
                        "Content-Type": "application/json"
                    },
                    body=cached_response["data"]
                )
            
            # Cache miss - generate response
            self.record_cache_miss(request.path, cache_key, cache_rule.cache_strategy)
            
            response = await handler(request)
            
            # Store in cache if successful
            if response.status == 200:
                response_data = response.text if hasattr(response, 'text') else str(response.body)
                await self.store_cached_response(
                    cache_key, response_data, cache_rule.ttl_seconds, cache_rule
                )
            
            # Add cache headers
            response.headers["X-Cache-Status"] = "MISS"
            response.headers["X-Cache-Key"] = cache_key
            
            self.record_response_time(request.path, time.time() - start_time, "cache_miss")
            
            return response
        
        async def handle_users(request):
            """Handle user API requests."""
            user_id = request.match_info.get('user_id', 'default')
            
            # Simulate database lookup delay
            await asyncio.sleep(0.2)
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "user_id": user_id,
                    "name": f"User {user_id}",
                    "created_at": "2024-01-01T00:00:00Z",
                    "timestamp": time.time()
                }
            )
        
        async def handle_threads(request):
            """Handle thread listing requests."""
            user_id = request.headers.get("X-User-ID", "anonymous")
            limit = int(request.query.get("limit", "10"))
            offset = int(request.query.get("offset", "0"))
            
            # Simulate database query delay
            await asyncio.sleep(0.3)
            
            threads = []
            for i in range(offset, offset + limit):
                threads.append({
                    "thread_id": f"thread_{i}",
                    "title": f"Thread {i}",
                    "user_id": user_id,
                    "created_at": "2024-01-01T00:00:00Z"
                })
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "threads": threads,
                    "total": 100,
                    "limit": limit,
                    "offset": offset,
                    "timestamp": time.time()
                }
            )
        
        async def handle_agent_config(request):
            """Handle agent configuration requests."""
            version = request.query.get("version", "latest")
            feature_flags = request.query.get("feature_flags", "default")
            
            # Simulate configuration processing delay
            await asyncio.sleep(0.1)
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "version": version,
                    "feature_flags": feature_flags,
                    "config": {
                        "max_tokens": 4096,
                        "temperature": 0.7,
                        "timeout": 30
                    },
                    "timestamp": time.time()
                }
            )
        
        async def handle_metrics(request):
            """Handle metrics requests."""
            timerange = request.query.get("timerange", "1h")
            granularity = request.query.get("granularity", "5m")
            
            # Simulate metrics calculation delay
            await asyncio.sleep(0.4)
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "timerange": timerange,
                    "granularity": granularity,
                    "metrics": {
                        "requests_per_second": 125.5,
                        "error_rate": 0.02,
                        "avg_response_time": 0.15
                    },
                    "timestamp": time.time()
                }
            )
        
        async def handle_websocket_status(request):
            """Handle real-time WebSocket status (no cache)."""
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "active_connections": 42,
                    "messages_per_second": 15.3,
                    "status": "healthy",
                    "timestamp": time.time()
                }
            )
        
        async def handle_static_resource(request):
            """Handle static resource requests."""
            resource = request.match_info.get('resource', 'default')
            version = request.query.get("version", "v1")
            
            # Simulate static file serving
            await asyncio.sleep(0.05)
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "resource": resource,
                    "version": version,
                    "content": f"Static content for {resource}",
                    "timestamp": time.time()
                }
            )
        
        # Create app with caching middleware
        app = web.Application(middlewares=[cache_middleware])
        
        # Register routes
        app.router.add_get('/api/v1/users/{user_id}', handle_users)
        app.router.add_get('/api/v1/threads', handle_threads)
        app.router.add_get('/api/v1/agents/config', handle_agent_config)
        app.router.add_get('/api/v1/metrics', handle_metrics)
        app.router.add_get('/api/v1/websocket/status', handle_websocket_status)
        app.router.add_get('/api/v1/static/{resource}', handle_static_resource)
        
        # Start server
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Cached test server started on {self.test_server.sockets[0].getsockname()}")
    
    async def find_cache_rule(self, path: str) -> Optional[CacheRule]:
        """Find matching cache rule for path."""
        for pattern, rule in self.cache_rules.items():
            if self.path_matches_pattern(path, pattern):
                return rule
        return None
    
    def path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
        # Simple pattern matching for test purposes
        if "{" not in pattern:
            return path == pattern
        
        # Handle path parameters
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                continue  # Parameter match
            elif pattern_part != path_part:
                return False
        
        return True
    
    async def generate_cache_key(self, request, cache_rule: CacheRule) -> str:
        """Generate cache key for request."""
        key_components = [request.path, request.method]
        
        # Add cache key parameters
        for param in cache_rule.cache_key_params:
            if param in request.match_info:
                key_components.append(f"{param}:{request.match_info[param]}")
            elif param in request.query:
                key_components.append(f"{param}:{request.query[param]}")
            elif param == "user_id" and "X-User-ID" in request.headers:
                key_components.append(f"user_id:{request.headers['X-User-ID']}")
        
        # Generate hash
        key_string = "|".join(key_components)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"api_cache:{cache_key}"
    
    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get response from cache."""
        if cache_key in self.cache_storage:
            cached_item = self.cache_storage[cache_key]
            
            # Check TTL
            if time.time() < cached_item["expires_at"]:
                ttl_remaining = int(cached_item["expires_at"] - time.time())
                return {
                    "data": cached_item["data"],
                    "ttl_remaining": ttl_remaining
                }
            else:
                # Expired - remove from cache
                del self.cache_storage[cache_key]
        
        return None
    
    async def store_cached_response(self, cache_key: str, data: str, 
                                  ttl_seconds: int, cache_rule: CacheRule):
        """Store response in cache."""
        expires_at = time.time() + ttl_seconds
        
        # Apply compression if enabled
        if cache_rule.compression_enabled:
            data = self.compress_data(data)
        
        self.cache_storage[cache_key] = {
            "data": data,
            "expires_at": expires_at,
            "rule": cache_rule,
            "created_at": time.time()
        }
    
    def compress_data(self, data: str) -> str:
        """Simulate data compression."""
        # Simple compression simulation
        return data  # In real implementation, use gzip or similar
    
    def record_cache_hit(self, path: str, cache_key: str, strategy: str):
        """Record cache hit for metrics."""
        hit = {
            "path": path,
            "cache_key": cache_key,
            "strategy": strategy,
            "timestamp": time.time()
        }
        self.cache_hits.append(hit)
    
    def record_cache_miss(self, path: str, cache_key: str, strategy: str):
        """Record cache miss for metrics."""
        miss = {
            "path": path,
            "cache_key": cache_key,
            "strategy": strategy,
            "timestamp": time.time()
        }
        self.cache_misses.append(miss)
    
    def record_response_time(self, path: str, response_time: float, cache_status: str):
        """Record response time for performance analysis."""
        timing = {
            "path": path,
            "response_time": response_time,
            "cache_status": cache_status,
            "timestamp": time.time()
        }
        self.response_times.append(timing)
    
    async def make_cached_request(self, path: str, query_params: Optional[Dict[str, str]] = None,
                                headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make HTTP request through caching layer."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        if query_params:
            query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
            url = f"{url}?{query_string}"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers or {}) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "cache_status": response.headers.get("X-Cache-Status", "UNKNOWN")
                    }
                    
                    if response.status == 200:
                        result["body"] = await response.json()
                    else:
                        result["body"] = await response.text()
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e),
                "cache_status": "ERROR"
            }
    
    async def test_cache_hit_ratio(self, path: str, request_count: int, 
                                 query_params: Optional[Dict[str, str]] = None,
                                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Test cache hit ratio for repeated requests."""
        results = []
        cache_hits = 0
        cache_misses = 0
        
        for i in range(request_count):
            result = await self.make_cached_request(path, query_params, headers)
            results.append(result)
            
            if result["cache_status"] == "HIT":
                cache_hits += 1
            elif result["cache_status"] == "MISS":
                cache_misses += 1
            
            # Small delay between requests
            await asyncio.sleep(0.01)
        
        cache_hit_ratio = cache_hits / (cache_hits + cache_misses) * 100 if (cache_hits + cache_misses) > 0 else 0
        
        return {
            "total_requests": request_count,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_ratio": cache_hit_ratio,
            "results": results
        }
    
    async def test_cache_performance_improvement(self, path: str, iterations: int) -> Dict[str, Any]:
        """Test performance improvement from caching."""
        # Clear cache first
        self.cache_storage.clear()
        
        # Make initial request (cache miss)
        miss_result = await self.make_cached_request(path)
        miss_time = miss_result["response_time"]
        
        # Make subsequent requests (cache hits)
        hit_times = []
        for i in range(iterations):
            hit_result = await self.make_cached_request(path)
            if hit_result["cache_status"] == "HIT":
                hit_times.append(hit_result["response_time"])
        
        avg_hit_time = sum(hit_times) / len(hit_times) if hit_times else 0
        performance_improvement = ((miss_time - avg_hit_time) / miss_time * 100) if miss_time > 0 else 0
        
        return {
            "cache_miss_time": miss_time,
            "average_hit_time": avg_hit_time,
            "performance_improvement_percent": performance_improvement,
            "hit_count": len(hit_times)
        }
    
    async def invalidate_cache(self, triggers: List[str]):
        """Simulate cache invalidation based on triggers."""
        keys_to_remove = []
        
        for cache_key, cached_item in self.cache_storage.items():
            rule = cached_item["rule"]
            if any(trigger in rule.invalidation_triggers for trigger in triggers):
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            del self.cache_storage[key]
            self.cache_invalidations.append({
                "cache_key": key,
                "triggers": triggers,
                "timestamp": time.time()
            })
        
        return len(keys_to_remove)
    
    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        total_hits = len(self.cache_hits)
        total_misses = len(self.cache_misses)
        total_requests = total_hits + total_misses
        
        if total_requests == 0:
            return {"total_requests": 0}
        
        # Calculate hit ratio
        hit_ratio = (total_hits / total_requests) * 100
        
        # Cache strategy breakdown
        strategy_breakdown = {}
        for hit in self.cache_hits:
            strategy = hit["strategy"]
            strategy_breakdown[strategy] = strategy_breakdown.get(strategy, {"hits": 0, "misses": 0})
            strategy_breakdown[strategy]["hits"] += 1
        
        for miss in self.cache_misses:
            strategy = miss["strategy"]
            strategy_breakdown[strategy] = strategy_breakdown.get(strategy, {"hits": 0, "misses": 0})
            strategy_breakdown[strategy]["misses"] += 1
        
        # Response time analysis
        hit_times = [rt["response_time"] for rt in self.response_times if rt["cache_status"] == "cache_hit"]
        miss_times = [rt["response_time"] for rt in self.response_times if rt["cache_status"] == "cache_miss"]
        
        avg_hit_time = sum(hit_times) / len(hit_times) if hit_times else 0
        avg_miss_time = sum(miss_times) / len(miss_times) if miss_times else 0
        
        return {
            "total_requests": total_requests,
            "cache_hits": total_hits,
            "cache_misses": total_misses,
            "hit_ratio": hit_ratio,
            "cache_invalidations": len(self.cache_invalidations),
            "strategy_breakdown": strategy_breakdown,
            "average_hit_time": avg_hit_time,
            "average_miss_time": avg_miss_time,
            "performance_improvement": ((avg_miss_time - avg_hit_time) / avg_miss_time * 100) if avg_miss_time > 0 else 0,
            "cache_size": len(self.cache_storage),
            "configured_rules": len(self.cache_rules)
        }
    
    async def cleanup(self):
        """Clean up cache resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
            
            if self.cache_manager:
                await self.cache_manager.shutdown()
            
            if self.redis_cache:
                await self.redis_cache.shutdown()
            
            if self.metrics_service:
                await self.metrics_service.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def api_cache_manager():
    """Create API cache manager for L3 testing."""
    manager = ApiCacheManager()
    await manager.initialize_caching()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_time_based_caching(api_cache_manager):
    """Test time-based caching with TTL."""
    path = "/api/v1/users/123"
    
    # Test cache hit ratio with repeated requests
    cache_test = await api_cache_manager.test_cache_hit_ratio(path, 5)
    
    assert cache_test["cache_misses"] == 1  # First request is a miss
    assert cache_test["cache_hits"] == 4    # Subsequent requests are hits
    assert cache_test["cache_hit_ratio"] == 80.0  # 4/5 = 80%
    
    # Verify cache headers
    first_miss = cache_test["results"][0]
    assert first_miss["cache_status"] == "MISS"
    
    first_hit = cache_test["results"][1]
    assert first_hit["cache_status"] == "HIT"
    assert "X-Cache-TTL" in first_hit["headers"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_user_based_caching(api_cache_manager):
    """Test user-based caching with different users."""
    path = "/api/v1/threads"
    
    # Test with different users
    user1_headers = {"X-User-ID": "user1"}
    user2_headers = {"X-User-ID": "user2"}
    
    # User 1 requests
    user1_result1 = await api_cache_manager.make_cached_request(path, headers=user1_headers)
    user1_result2 = await api_cache_manager.make_cached_request(path, headers=user1_headers)
    
    assert user1_result1["cache_status"] == "MISS"  # First request for user1
    assert user1_result2["cache_status"] == "HIT"   # Cached for user1
    
    # User 2 requests
    user2_result1 = await api_cache_manager.make_cached_request(path, headers=user2_headers)
    user2_result2 = await api_cache_manager.make_cached_request(path, headers=user2_headers)
    
    assert user2_result1["cache_status"] == "MISS"  # First request for user2
    assert user2_result2["cache_status"] == "HIT"   # Cached for user2
    
    # Different users should have different cache entries
    assert user1_result1["headers"]["X-Cache-Key"] != user2_result1["headers"]["X-Cache-Key"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_content_based_caching(api_cache_manager):
    """Test content-based caching with different parameters."""
    path = "/api/v1/agents/config"
    
    # Test with different parameters
    params1 = {"version": "v1", "feature_flags": "default"}
    params2 = {"version": "v2", "feature_flags": "default"}
    params3 = {"version": "v1", "feature_flags": "default"}  # Same as params1
    
    result1 = await api_cache_manager.make_cached_request(path, query_params=params1)
    result2 = await api_cache_manager.make_cached_request(path, query_params=params2)
    result3 = await api_cache_manager.make_cached_request(path, query_params=params3)
    
    assert result1["cache_status"] == "MISS"  # First request with params1
    assert result2["cache_status"] == "MISS"  # Different params = different cache
    assert result3["cache_status"] == "HIT"   # Same params as result1
    
    # Different parameters should generate different cache keys
    assert result1["headers"]["X-Cache-Key"] != result2["headers"]["X-Cache-Key"]
    assert result1["headers"]["X-Cache-Key"] == result3["headers"]["X-Cache-Key"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_no_cache_strategy(api_cache_manager):
    """Test endpoints configured for no caching."""
    path = "/api/v1/websocket/status"
    
    # Make multiple requests - should never cache
    results = []
    for i in range(3):
        result = await api_cache_manager.make_cached_request(path)
        results.append(result)
    
    # All requests should bypass cache
    for result in results:
        assert "X-Cache-Status" not in result["headers"] or result.get("cache_status") == "no_cache"
    
    # Response data should be different (timestamps)
    timestamps = [result["body"]["timestamp"] for result in results]
    assert len(set(timestamps)) == 3  # All different timestamps


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_performance_improvement(api_cache_manager):
    """Test performance improvement from caching."""
    path = "/api/v1/metrics"
    query_params = {"timerange": "1h", "granularity": "5m"}
    
    # Test performance improvement
    perf_test = await api_cache_manager.test_cache_performance_improvement(path, 5)
    
    assert perf_test["cache_miss_time"] > 0
    assert perf_test["average_hit_time"] > 0
    assert perf_test["hit_count"] == 5
    
    # Cache hits should be significantly faster than misses
    assert perf_test["average_hit_time"] < perf_test["cache_miss_time"]
    assert perf_test["performance_improvement_percent"] > 50  # At least 50% improvement


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_invalidation(api_cache_manager):
    """Test cache invalidation on triggers."""
    path = "/api/v1/users/456"
    
    # Populate cache
    result1 = await api_cache_manager.make_cached_request(path)
    result2 = await api_cache_manager.make_cached_request(path)
    
    assert result1["cache_status"] == "MISS"
    assert result2["cache_status"] == "HIT"
    
    # Trigger cache invalidation
    invalidated_count = await api_cache_manager.invalidate_cache(["user_updated"])
    assert invalidated_count > 0
    
    # Next request should be a cache miss
    result3 = await api_cache_manager.make_cached_request(path)
    assert result3["cache_status"] == "MISS"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_ttl_expiration(api_cache_manager):
    """Test cache TTL expiration."""
    # Use metrics endpoint with 60-second TTL
    path = "/api/v1/metrics"
    
    # Make initial request
    result1 = await api_cache_manager.make_cached_request(path)
    assert result1["cache_status"] == "MISS"
    
    # Immediate subsequent request should hit cache
    result2 = await api_cache_manager.make_cached_request(path)
    assert result2["cache_status"] == "HIT"
    
    # Manually expire cache entry (simulate TTL expiration)
    cache_key = result1["headers"]["X-Cache-Key"]
    if cache_key in api_cache_manager.cache_storage:
        api_cache_manager.cache_storage[cache_key]["expires_at"] = time.time() - 1
    
    # Next request should be a miss due to expiration
    result3 = await api_cache_manager.make_cached_request(path)
    assert result3["cache_status"] == "MISS"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_cache_requests(api_cache_manager):
    """Test concurrent requests to cached endpoints."""
    path = "/api/v1/static/config.json"
    query_params = {"version": "v1"}
    
    # Make concurrent requests
    concurrent_tasks = []
    for i in range(10):
        task = api_cache_manager.make_cached_request(path, query_params)
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks)
    
    # Should have one miss and multiple hits
    cache_misses = [r for r in results if r["cache_status"] == "MISS"]
    cache_hits = [r for r in results if r["cache_status"] == "HIT"]
    
    assert len(cache_misses) >= 1  # At least one miss
    assert len(cache_hits) >= 8   # Most should be hits
    
    # All successful requests should return same content
    successful_results = [r for r in results if r["status_code"] == 200]
    for result in successful_results[1:]:
        assert result["body"]["resource"] == successful_results[0]["body"]["resource"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_size_limits(api_cache_manager):
    """Test cache size management."""
    # Get initial cache size
    initial_metrics = await api_cache_manager.get_cache_metrics()
    initial_size = initial_metrics["cache_size"]
    
    # Make requests to different endpoints to populate cache
    endpoints = [
        "/api/v1/users/100",
        "/api/v1/users/101", 
        "/api/v1/users/102",
        "/api/v1/agents/config",
        "/api/v1/metrics"
    ]
    
    for endpoint in endpoints:
        await api_cache_manager.make_cached_request(endpoint)
    
    # Check cache growth
    final_metrics = await api_cache_manager.get_cache_metrics()
    final_size = final_metrics["cache_size"]
    
    assert final_size > initial_size
    assert final_size <= initial_size + len(endpoints)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_metrics_accuracy(api_cache_manager):
    """Test accuracy of cache metrics collection."""
    # Generate test traffic with known patterns
    test_scenarios = [
        ("/api/v1/users/200", 3),  # 1 miss, 2 hits
        ("/api/v1/agents/config", 2),  # 1 miss, 1 hit
        ("/api/v1/websocket/status", 2),  # 2 requests, no cache
    ]
    
    for path, count in test_scenarios:
        for i in range(count):
            await api_cache_manager.make_cached_request(path)
    
    # Get metrics
    metrics = await api_cache_manager.get_cache_metrics()
    
    # Verify metrics accuracy
    assert metrics["total_requests"] >= 7  # At least our test requests
    assert metrics["cache_hits"] >= 3      # At least 3 cache hits
    assert metrics["cache_misses"] >= 2    # At least 2 cache misses
    assert 0 <= metrics["hit_ratio"] <= 100
    
    # Verify performance metrics
    assert metrics["average_hit_time"] > 0
    assert metrics["average_miss_time"] > 0
    assert metrics["average_hit_time"] < metrics["average_miss_time"]
    assert metrics["performance_improvement"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cache_strategy_effectiveness(api_cache_manager):
    """Test effectiveness of different caching strategies."""
    # Test different strategies
    strategy_tests = [
        ("/api/v1/users/300", "time_based", 5),
        ("/api/v1/threads", "user_based", 4),
        ("/api/v1/agents/config", "content_based", 3)
    ]
    
    strategy_results = {}
    
    for path, strategy, request_count in strategy_tests:
        headers = {"X-User-ID": "test_user"} if strategy == "user_based" else None
        
        cache_test = await api_cache_manager.test_cache_hit_ratio(
            path, request_count, headers=headers
        )
        
        strategy_results[strategy] = cache_test
    
    # All strategies should achieve good hit ratios
    for strategy, result in strategy_results.items():
        assert result["cache_hit_ratio"] >= 60  # At least 60% hit ratio
        assert result["cache_misses"] >= 1      # Should have at least one miss
        assert result["cache_hits"] >= 2       # Should have multiple hits
    
    # Time-based should have highest hit ratio (most repeated requests)
    time_based_ratio = strategy_results["time_based"]["cache_hit_ratio"]
    user_based_ratio = strategy_results["user_based"]["cache_hit_ratio"]
    
    assert time_based_ratio >= user_based_ratio