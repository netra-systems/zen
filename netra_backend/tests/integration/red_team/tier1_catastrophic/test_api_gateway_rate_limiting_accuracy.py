"""
RED TEAM TEST 9: API Gateway Rate Limiting Accuracy

DESIGN TO FAIL: This test is DESIGNED to FAIL initially to validate:
1. Rate limiting with real Redis counters
2. Cross-service rate limit coordination
3. Rate limit resets and time windows

These tests use real rate limiting infrastructure and will expose actual issues.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
import httpx
import redis.asyncio as redis
from unittest.mock import patch, AsyncMock
import json
from typing import List, Dict, Any

from netra_backend.app.core.config import get_settings
from netra_backend.app.services.rate_limiter import RateLimiter
from netra_backend.app.redis_manager import RedisManager

# Import absolute paths  
from netra_backend.tests.helpers.redis_test_helpers import (
    create_test_redis_client,
    clear_redis_test_data,
    generate_test_rate_limit_keys
)


class TestApiGatewayRateLimitingAccuracy:
    """
    RED TEAM Test Suite: API Gateway Rate Limiting Accuracy
    
    DESIGNED TO FAIL: These tests expose real rate limiting vulnerabilities
    """
    
    @pytest.fixture
    async def settings(self):
        """Get application settings"""
        return get_settings()
    
    @pytest.fixture
    async def redis_client(self, settings):
        """Real Redis client for rate limiting"""
        client = redis.Redis.from_url(settings.redis_url)
        await client.ping()  # Verify connection
        yield client
        await client.close()
    
    @pytest.fixture
    async def redis_manager(self, settings):
        """Real Redis manager"""
        manager = RedisManager(settings)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def rate_limiter(self, redis_manager, settings):
        """Real rate limiter instance"""
        return RateLimiter(redis_manager, settings)
    
    @pytest.fixture(autouse=True)
    async def cleanup_redis(self, redis_client):
        """Clean up Redis between tests"""
        yield
        # Clean up all test rate limit keys
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_real_redis_counters_fails(self, rate_limiter, redis_client):
        """
        DESIGNED TO FAIL: Test rate limiting with real Redis counters
        
        This test WILL FAIL because:
        1. Rate limit counters may not be atomic
        2. Race conditions in counter increments
        3. Redis keys may not expire properly
        4. Counter accuracy issues under load
        """
        user_id = "test_user_123"
        endpoint = "/api/v1/test"
        rate_limit = 5  # 5 requests per minute
        window_seconds = 60
        
        # Configure rate limit for this test
        await rate_limiter.set_rate_limit(user_id, endpoint, rate_limit, window_seconds)
        
        # Make requests up to the limit
        allowed_requests = 0
        denied_requests = 0
        
        for i in range(rate_limit + 3):  # Try 3 more than limit
            is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint)
            
            if is_allowed:
                allowed_requests += 1
            else:
                denied_requests += 1
        
        # THIS WILL FAIL: Rate limiting likely has accuracy issues
        assert allowed_requests == rate_limit, \
            f"Expected exactly {rate_limit} allowed requests, got {allowed_requests}"
        
        assert denied_requests == 3, \
            f"Expected exactly 3 denied requests, got {denied_requests}"
        
        # Check Redis counter accuracy
        counter_key = f"rate_limit:{user_id}:{endpoint}"
        redis_count = await redis_client.get(counter_key)
        
        if redis_count:
            redis_count = int(redis_count)
            # THIS ASSERTION WILL FAIL: Redis counter may be inaccurate
            assert redis_count == rate_limit, \
                f"Redis counter should be {rate_limit}, but is {redis_count}"
        else:
            # THIS WILL FAIL: Counter should exist after rate limiting
            pytest.fail("Rate limit counter not found in Redis")
        
        # Check TTL is set correctly
        ttl = await redis_client.ttl(counter_key)
        # THIS WILL FAIL: TTL may not be set or incorrect
        assert ttl > 0 and ttl <= window_seconds, \
            f"Rate limit key TTL should be between 1 and {window_seconds}, got {ttl}"
    
    @pytest.mark.asyncio
    async def test_cross_service_rate_limit_coordination_fails(self, rate_limiter, redis_client):
        """
        DESIGNED TO FAIL: Test cross-service rate limit coordination
        
        This test WILL FAIL because:
        1. Services don't coordinate rate limits properly
        2. Shared user limits not enforced across services
        3. Service-specific limits conflict with global limits
        4. No proper rate limit aggregation
        """
        user_id = "cross_service_user"
        global_rate_limit = 10  # 10 requests per minute across all services
        service_rate_limit = 7   # 7 requests per minute per service
        
        services = ["auth_service", "backend_service", "websocket_service"]
        endpoints = ["/auth/login", "/api/v1/threads", "/ws/connect"]
        
        # Set global rate limit
        await rate_limiter.set_global_rate_limit(user_id, global_rate_limit, 60)
        
        # Set per-service rate limits
        for service, endpoint in zip(services, endpoints):
            await rate_limiter.set_service_rate_limit(user_id, service, endpoint, service_rate_limit, 60)
        
        # Track requests across services
        total_allowed = 0
        service_requests = {service: 0 for service in services}
        
        # Make requests round-robin across services
        for i in range(15):  # More than global limit
            service = services[i % len(services)]
            endpoint = endpoints[i % len(endpoints)]
            
            # Check both global and service-specific limits
            global_allowed = await rate_limiter.check_global_rate_limit(user_id)
            service_allowed = await rate_limiter.check_service_rate_limit(user_id, service, endpoint)
            
            # Request should be allowed only if both limits allow it
            request_allowed = global_allowed and service_allowed
            
            if request_allowed:
                total_allowed += 1
                service_requests[service] += 1
                # Increment counters
                await rate_limiter.increment_global_counter(user_id)
                await rate_limiter.increment_service_counter(user_id, service, endpoint)
        
        # THIS WILL FAIL: Cross-service coordination likely broken
        assert total_allowed <= global_rate_limit, \
            f"Global rate limit exceeded: {total_allowed} > {global_rate_limit}"
        
        # Check per-service limits
        for service, count in service_requests.items():
            # THIS WILL FAIL: Service limits may not be enforced properly
            assert count <= service_rate_limit, \
                f"Service {service} rate limit exceeded: {count} > {service_rate_limit}"
        
        # Verify Redis coordination
        global_key = f"rate_limit:global:{user_id}"
        global_count = await redis_client.get(global_key)
        
        if global_count:
            global_count = int(global_count)
            # THIS WILL FAIL: Global counter may not match allowed requests
            assert global_count == total_allowed, \
                f"Global Redis counter mismatch: {global_count} != {total_allowed}"
        else:
            pytest.fail("Global rate limit counter missing in Redis")
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_and_time_windows_fail(self, rate_limiter, redis_client):
        """
        DESIGNED TO FAIL: Test rate limit resets and time windows
        
        This test WILL FAIL because:
        1. Time windows may not reset properly
        2. Counter resets have race conditions
        3. TTL management is inaccurate
        4. Sliding vs fixed windows implemented incorrectly
        """
        user_id = "time_window_user"
        endpoint = "/api/v1/test"
        rate_limit = 3
        window_seconds = 5  # Short window for testing
        
        # Set up rate limit
        await rate_limiter.set_rate_limit(user_id, endpoint, rate_limit, window_seconds)
        
        # Phase 1: Use up the rate limit
        for i in range(rate_limit):
            is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint)
            # THIS WILL FAIL if rate limiting is broken from the start
            assert is_allowed, f"Request {i+1} should be allowed but was denied"
        
        # Verify limit is reached
        is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint) 
        assert not is_allowed, "Request should be denied after reaching limit"
        
        # Get current TTL
        counter_key = f"rate_limit:{user_id}:{endpoint}"
        initial_ttl = await redis_client.ttl(counter_key)
        
        # THIS WILL FAIL: TTL should be set correctly
        assert initial_ttl > 0, f"TTL should be positive, got {initial_ttl}"
        assert initial_ttl <= window_seconds, f"TTL {initial_ttl} exceeds window {window_seconds}"
        
        # Phase 2: Wait for partial time window
        await asyncio.sleep(2)
        
        # Check TTL decreased
        mid_ttl = await redis_client.ttl(counter_key)
        # THIS WILL FAIL: TTL should decrease over time
        assert mid_ttl < initial_ttl, f"TTL should decrease: {mid_ttl} >= {initial_ttl}"
        
        # Should still be denied
        is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint)
        assert not is_allowed, "Request should still be denied before window reset"
        
        # Phase 3: Wait for complete window reset
        await asyncio.sleep(4)  # Total 6 seconds > 5 second window
        
        # Check if counter was reset
        counter_value = await redis_client.get(counter_key)
        
        # THIS WILL FAIL: Counter should be reset or key should expire
        if counter_value is not None:
            counter_value = int(counter_value)
            # If key exists, it should be 0 or small value
            assert counter_value < rate_limit, \
                f"Counter should reset after window, but is {counter_value}"
        
        # Phase 4: Test new window allows requests
        fresh_requests_allowed = 0
        for i in range(rate_limit + 1):
            is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint)
            if is_allowed:
                fresh_requests_allowed += 1
            else:
                break
        
        # THIS WILL FAIL: Should allow full rate limit again after reset
        assert fresh_requests_allowed == rate_limit, \
            f"After window reset, should allow {rate_limit} requests, got {fresh_requests_allowed}"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_concurrent_requests_race_condition(self, rate_limiter, redis_client):
        """
        DESIGNED TO FAIL: Test rate limiting under concurrent load
        
        This test WILL FAIL because:
        1. Race conditions in counter increments
        2. Non-atomic check-and-increment operations
        3. Redis pipeline issues
        4. Inaccurate counting under load
        """
        user_id = "concurrent_user"
        endpoint = "/api/v1/concurrent"
        rate_limit = 5
        concurrent_requests = 20
        
        # Set up rate limit
        await rate_limiter.set_rate_limit(user_id, endpoint, rate_limit, 60)
        
        # Track results from concurrent requests
        results = []
        
        async def make_request(request_id):
            """Make a single request and track result"""
            try:
                is_allowed = await rate_limiter.check_rate_limit(user_id, endpoint)
                return {"id": request_id, "allowed": is_allowed, "error": None}
            except Exception as e:
                return {"id": request_id, "allowed": False, "error": str(e)}
        
        # Launch concurrent requests
        tasks = [make_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        allowed_count = sum(1 for r in successful_results if r.get("allowed", False))
        errors = [r for r in successful_results if r.get("error") is not None]
        
        # THIS WILL FAIL: Concurrent requests may exceed rate limit
        assert allowed_count <= rate_limit, \
            f"Race condition: {allowed_count} requests allowed, limit is {rate_limit}"
        
        # Should allow exactly the rate limit (no more, no less due to race conditions)
        assert allowed_count == rate_limit, \
            f"Rate limiting inaccurate under concurrency: {allowed_count} != {rate_limit}"
        
        # Check for errors during concurrent access
        # THIS WILL FAIL: Concurrent access may cause Redis errors
        assert len(errors) == 0, f"Errors during concurrent rate limiting: {errors}"
        
        # Verify final Redis counter state
        counter_key = f"rate_limit:{user_id}:{endpoint}"
        final_count = await redis_client.get(counter_key)
        
        if final_count:
            final_count = int(final_count)
            # THIS WILL FAIL: Final count should match allowed requests
            assert final_count == allowed_count, \
                f"Redis counter mismatch: {final_count} != {allowed_count}"
        else:
            pytest.fail("Rate limit counter missing after concurrent requests")
    
    @pytest.mark.asyncio
    async def test_rate_limit_bypass_vulnerabilities(self, rate_limiter, redis_client):
        """
        DESIGNED TO FAIL: Test for rate limit bypass vulnerabilities
        
        This test WILL FAIL because:
        1. Rate limits can be bypassed with different key formats
        2. Case sensitivity issues in user IDs
        3. Special characters break rate limiting
        4. Header manipulation bypasses limits
        """
        base_user_id = "bypass_test_user"
        endpoint = "/api/v1/bypass"
        rate_limit = 2
        
        # Set up rate limit
        await rate_limiter.set_rate_limit(base_user_id, endpoint, rate_limit, 60)
        
        # Use up the normal rate limit
        for i in range(rate_limit):
            is_allowed = await rate_limiter.check_rate_limit(base_user_id, endpoint)
            assert is_allowed, f"Normal request {i+1} should be allowed"
        
        # Verify limit is reached
        is_allowed = await rate_limiter.check_rate_limit(base_user_id, endpoint)
        assert not is_allowed, "Should be rate limited"
        
        # Test bypass attempts
        bypass_attempts = [
            base_user_id.upper(),  # Case variation
            base_user_id.lower(),  # Case variation
            f" {base_user_id}",     # Leading space
            f"{base_user_id} ",     # Trailing space
            f"{base_user_id}\n",    # Newline
            f"{base_user_id}\t",    # Tab
            base_user_id.replace("_", "-"),  # Character substitution
            f"user://{base_user_id}",  # URI format
            f"{base_user_id}#fragment",  # Fragment
            f"{base_user_id}?param=1",  # Query param
        ]
        
        successful_bypasses = []
        
        for bypass_id in bypass_attempts:
            try:
                is_allowed = await rate_limiter.check_rate_limit(bypass_id, endpoint)
                if is_allowed:
                    successful_bypasses.append(bypass_id)
            except Exception as e:
                # Rate limiter crashes are also a problem
                successful_bypasses.append(f"{bypass_id} (crashed: {e})")
        
        # THIS WILL FAIL: Some bypass attempts will succeed
        assert len(successful_bypasses) == 0, \
            f"Rate limit bypass vulnerabilities found: {successful_bypasses}"
        
        # Test endpoint variations
        endpoint_variations = [
            endpoint.upper(),
            endpoint + "/",
            endpoint + "?param=1",
            endpoint + "#fragment",
            endpoint.replace("/", "%2F"),  # URL encoding
            endpoint + "/../bypass",
        ]
        
        endpoint_bypasses = []
        
        for variant_endpoint in endpoint_variations:
            try:
                is_allowed = await rate_limiter.check_rate_limit(base_user_id, variant_endpoint)
                if is_allowed:
                    endpoint_bypasses.append(variant_endpoint)
            except Exception:
                pass  # Expected for some variations
        
        # THIS WILL FAIL: Endpoint variations may bypass rate limits
        assert len(endpoint_bypasses) == 0, \
            f"Rate limit endpoint bypass vulnerabilities: {endpoint_bypasses}"