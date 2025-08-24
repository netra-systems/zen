"""API Gateway Rate Limiting L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API consumption control)
- Business Goal: Fair API usage and abuse prevention
- Value Impact: Prevents API overload, ensures quality service across user tiers
- Strategic Impact: $15K MRR protection through API gateway reliability

Critical Path: Request identification -> Rate limit check -> Gateway enforcement -> Response generation -> Metrics collection
Coverage: API gateway rate limiting, per-endpoint limits, burst handling, tier-based enforcement
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import aiohttp
import pytest

from netra_backend.app.schemas.user import UserTier
from netra_backend.app.services.api_gateway.gateway_manager import ApiGatewayManager

from netra_backend.app.services.api_gateway.rate_limiter import ApiGatewayRateLimiter
from netra_backend.app.services.metrics.gateway_metrics import GatewayMetricsService

logger = logging.getLogger(__name__)

@dataclass
class EndpointConfig:
    """Rate limiting configuration for API endpoints."""
    requests_per_minute: int
    requests_per_hour: int
    burst_allowance: int
    priority_level: int  # 1-5, higher = more important

class ApiGatewayRateLimitingManager:
    """Manages L3 API gateway rate limiting tests with real HTTP clients."""
    
    def __init__(self):
        self.gateway_manager = None
        self.rate_limiter = None
        self.metrics_service = None
        self.test_server = None
        self.test_endpoints = {}
        self.request_history = []
        self.rate_limit_violations = []
        self.gateway_metrics = {}
        
    async def initialize_gateway(self):
        """Initialize API gateway services for L3 testing."""
        try:
            self.gateway_manager = ApiGatewayManager()
            await self.gateway_manager.initialize()
            
            self.rate_limiter = ApiGatewayRateLimiter()
            await self.rate_limiter.initialize()
            
            self.metrics_service = GatewayMetricsService()
            await self.metrics_service.initialize()
            
            # Configure test endpoints with different limits
            await self.setup_test_endpoints()
            
            # Start test server for L3 validation
            await self.start_test_server()
            
            logger.info("API gateway rate limiting services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize API gateway services: {e}")
            raise
    
    async def setup_test_endpoints(self):
        """Configure test endpoints with tier-based rate limits."""
        self.test_endpoints = {
            "/api/v1/chat": EndpointConfig(
                requests_per_minute=50,
                requests_per_hour=1000,
                burst_allowance=10,
                priority_level=5  # High priority
            ),
            "/api/v1/threads": EndpointConfig(
                requests_per_minute=100,
                requests_per_hour=2000,
                burst_allowance=20,
                priority_level=4
            ),
            "/api/v1/agents": EndpointConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_allowance=5,
                priority_level=3
            ),
            "/api/v1/metrics": EndpointConfig(
                requests_per_minute=200,
                requests_per_hour=5000,
                burst_allowance=50,
                priority_level=2
            ),
            "/api/v1/health": EndpointConfig(
                requests_per_minute=1000,
                requests_per_hour=10000,
                burst_allowance=100,
                priority_level=1  # Low priority, high volume
            )
        }
        
        # Register endpoints with gateway
        for endpoint, config in self.test_endpoints.items():
            await self.gateway_manager.register_endpoint(endpoint, config)
    
    async def start_test_server(self):
        """Start test server for L3 HTTP validation."""
        from aiohttp import web
        
        async def handle_request(request):
            """Handle test API requests with rate limiting."""
            endpoint = request.path
            user_id = request.headers.get("X-User-ID", "anonymous")
            user_tier = UserTier(request.headers.get("X-User-Tier", "free"))
            
            # Apply rate limiting
            rate_limit_result = await self.check_endpoint_rate_limit(
                user_id, user_tier, endpoint
            )
            
            if not rate_limit_result["allowed"]:
                # Rate limit exceeded
                self.record_rate_limit_violation(user_id, endpoint, rate_limit_result)
                
                return web.Response(
                    status=429,
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                        "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                        "X-RateLimit-Reset": str(rate_limit_result["reset_time"]),
                        "Retry-After": str(rate_limit_result["retry_after"])
                    },
                    text="Rate limit exceeded"
                )
            
            # Record successful request
            self.record_successful_request(user_id, endpoint, user_tier)
            
            # Simulate endpoint processing
            processing_time = 0.1
            await asyncio.sleep(processing_time)
            
            return web.Response(
                status=200,
                headers={
                    "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                    "X-Processing-Time": str(processing_time)
                },
                json={"status": "success", "endpoint": endpoint}
            )
        
        app = web.Application()
        
        # Register all test endpoints
        for endpoint in self.test_endpoints.keys():
            app.router.add_get(endpoint, handle_request)
            app.router.add_post(endpoint, handle_request)
        
        # Start server on dynamic port
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Test server started on {self.test_server.sockets[0].getsockname()}")
    
    async def check_endpoint_rate_limit(self, user_id: str, user_tier: UserTier, 
                                      endpoint: str) -> Dict[str, Any]:
        """Check rate limits for specific endpoint and user."""
        try:
            if endpoint not in self.test_endpoints:
                return {"allowed": True, "reason": "endpoint_not_configured"}
            
            config = self.test_endpoints[endpoint]
            
            # Apply tier-based adjustments
            tier_multipliers = {
                UserTier.FREE: 1.0,
                UserTier.EARLY: 2.0,
                UserTier.MID: 5.0,
                UserTier.ENTERPRISE: 10.0
            }
            
            multiplier = tier_multipliers[user_tier]
            effective_limit = int(config.requests_per_minute * multiplier)
            
            # Check rate limit with gateway
            limit_check = await self.rate_limiter.check_limit(
                user_id, endpoint, effective_limit, window_seconds=60
            )
            
            if not limit_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": "rate_limit_exceeded",
                    "limit": effective_limit,
                    "remaining": limit_check["remaining"],
                    "reset_time": limit_check["reset_time"],
                    "retry_after": limit_check["retry_after"]
                }
            
            return {
                "allowed": True,
                "limit": effective_limit,
                "remaining": limit_check["remaining"],
                "reset_time": limit_check["reset_time"]
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return {
                "allowed": False,
                "reason": "internal_error",
                "error": str(e)
            }
    
    def record_rate_limit_violation(self, user_id: str, endpoint: str, 
                                  rate_limit_result: Dict[str, Any]):
        """Record rate limit violation for metrics."""
        violation = {
            "user_id": user_id,
            "endpoint": endpoint,
            "timestamp": time.time(),
            "reason": rate_limit_result["reason"],
            "limit": rate_limit_result.get("limit"),
            "remaining": rate_limit_result.get("remaining")
        }
        self.rate_limit_violations.append(violation)
    
    def record_successful_request(self, user_id: str, endpoint: str, user_tier: UserTier):
        """Record successful request for metrics."""
        request = {
            "user_id": user_id,
            "endpoint": endpoint,
            "user_tier": user_tier.value,
            "timestamp": time.time(),
            "status": "success"
        }
        self.request_history.append(request)
    
    async def make_http_request(self, endpoint: str, user_id: str, 
                              user_tier: UserTier = UserTier.FREE) -> Dict[str, Any]:
        """Make HTTP request to test endpoint."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{endpoint}"
        
        headers = {
            "X-User-ID": user_id,
            "X-User-Tier": user_tier.value
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "allowed": response.status != 429
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
                "allowed": False
            }
    
    async def simulate_burst_traffic(self, endpoint: str, user_id: str, 
                                   user_tier: UserTier, request_count: int, 
                                   duration_seconds: float) -> Dict[str, Any]:
        """Simulate burst traffic to test rate limiting."""
        burst_start = time.time()
        interval = duration_seconds / request_count
        
        results = []
        successful_requests = 0
        rate_limited_requests = 0
        
        try:
            for i in range(request_count):
                result = await self.make_http_request(endpoint, user_id, user_tier)
                results.append(result)
                
                if result["allowed"]:
                    successful_requests += 1
                else:
                    rate_limited_requests += 1
                
                # Wait before next request
                if i < request_count - 1:
                    await asyncio.sleep(interval)
            
            burst_duration = time.time() - burst_start
            
            return {
                "endpoint": endpoint,
                "user_tier": user_tier.value,
                "total_requests": request_count,
                "successful_requests": successful_requests,
                "rate_limited_requests": rate_limited_requests,
                "success_rate": successful_requests / request_count * 100,
                "burst_duration": burst_duration,
                "actual_rps": request_count / burst_duration,
                "results": results
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "burst_duration": time.time() - burst_start,
                "partial_results": results
            }
    
    @pytest.mark.asyncio
    async def test_concurrent_endpoint_requests(self, endpoints: List[str], 
                                              concurrent_users: int) -> Dict[str, Any]:
        """Test concurrent requests across multiple endpoints."""
        start_time = time.time()
        
        # Create concurrent request tasks
        tasks = []
        for i in range(concurrent_users):
            user_id = f"concurrent_user_{i}"
            tier = UserTier.MID if i % 2 == 0 else UserTier.FREE
            
            for endpoint in endpoints:
                task = self.make_http_request(endpoint, user_id, tier)
                tasks.append((user_id, endpoint, tier, task))
        
        # Execute all requests concurrently
        results = []
        for user_id, endpoint, tier, task in tasks:
            result = await task
            results.append({
                "user_id": user_id,
                "endpoint": endpoint,
                "tier": tier.value,
                "result": result
            })
        
        execution_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r["result"]["allowed"]]
        rate_limited = [r for r in results if not r["result"]["allowed"]]
        
        # Group by endpoint
        endpoint_stats = {}
        for endpoint in endpoints:
            endpoint_results = [r for r in results if r["endpoint"] == endpoint]
            endpoint_successful = [r for r in endpoint_results if r["result"]["allowed"]]
            
            endpoint_stats[endpoint] = {
                "total_requests": len(endpoint_results),
                "successful_requests": len(endpoint_successful),
                "success_rate": len(endpoint_successful) / len(endpoint_results) * 100 if endpoint_results else 0
            }
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "rate_limited_requests": len(rate_limited),
            "success_rate": len(successful) / len(results) * 100,
            "execution_time": execution_time,
            "rps": len(results) / execution_time,
            "endpoint_stats": endpoint_stats,
            "results": results
        }
    
    async def get_gateway_metrics(self) -> Dict[str, Any]:
        """Get comprehensive gateway rate limiting metrics."""
        total_requests = len(self.request_history)
        total_violations = len(self.rate_limit_violations)
        
        if total_requests == 0:
            return {"total_requests": 0, "violations": 0}
        
        # Endpoint breakdown
        endpoint_breakdown = {}
        for endpoint in self.test_endpoints.keys():
            endpoint_requests = [r for r in self.request_history if r["endpoint"] == endpoint]
            endpoint_violations = [v for v in self.rate_limit_violations if v["endpoint"] == endpoint]
            
            if endpoint_requests or endpoint_violations:
                endpoint_breakdown[endpoint] = {
                    "requests": len(endpoint_requests),
                    "violations": len(endpoint_violations),
                    "violation_rate": len(endpoint_violations) / (len(endpoint_requests) + len(endpoint_violations)) * 100 if (endpoint_requests or endpoint_violations) else 0
                }
        
        # Tier breakdown
        tier_breakdown = {}
        for tier in UserTier:
            tier_requests = [r for r in self.request_history if r["user_tier"] == tier.value]
            tier_breakdown[tier.value] = len(tier_requests)
        
        return {
            "total_requests": total_requests,
            "total_violations": total_violations,
            "violation_rate": total_violations / (total_requests + total_violations) * 100 if (total_requests + total_violations) > 0 else 0,
            "endpoint_breakdown": endpoint_breakdown,
            "tier_breakdown": tier_breakdown,
            "configured_endpoints": len(self.test_endpoints)
        }
    
    async def cleanup(self):
        """Clean up gateway resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
            
            if self.gateway_manager:
                await self.gateway_manager.shutdown()
            
            if self.rate_limiter:
                await self.rate_limiter.shutdown()
            
            if self.metrics_service:
                await self.metrics_service.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def api_gateway_manager():
    """Create API gateway manager for L3 testing."""
    manager = ApiGatewayRateLimitingManager()
    await manager.initialize_gateway()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_endpoint_rate_limiting_enforcement(api_gateway_manager):
    """Test rate limiting enforcement at the gateway level."""
    endpoint = "/api/v1/chat"
    user_id = "test_rate_limit_user"
    user_tier = UserTier.FREE
    
    # Make requests within limits
    for i in range(5):
        result = await api_gateway_manager.make_http_request(endpoint, user_id, user_tier)
        assert result["status_code"] == 200
        assert result["allowed"] is True
        assert "X-RateLimit-Limit" in result["headers"]
        assert "X-RateLimit-Remaining" in result["headers"]
    
    # Attempt burst to exceed limits
    burst_result = await api_gateway_manager.simulate_burst_traffic(
        endpoint, user_id, user_tier, 60, 30  # 60 requests in 30 seconds
    )
    
    # Should have some rate limited requests
    assert burst_result["rate_limited_requests"] > 0
    assert burst_result["success_rate"] < 100
    
    # Verify rate limiting headers in failed requests
    failed_results = [r for r in burst_result["results"] if not r["allowed"]]
    for result in failed_results[:3]:  # Check first few failures
        assert result["status_code"] == 429
        assert "Retry-After" in result["headers"]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_tier_based_rate_limit_differentiation(api_gateway_manager):
    """Test that different user tiers get different rate limits."""
    endpoint = "/api/v1/threads"
    
    # Test different tiers
    tier_tests = [
        (UserTier.FREE, "free_user", 20),
        (UserTier.MID, "mid_user", 20),
        (UserTier.ENTERPRISE, "enterprise_user", 20)
    ]
    
    tier_results = {}
    
    for tier, user_id, request_count in tier_tests:
        burst_result = await api_gateway_manager.simulate_burst_traffic(
            endpoint, user_id, tier, request_count, 15  # 20 requests in 15 seconds
        )
        
        tier_results[tier] = burst_result
    
    # Enterprise should have highest success rate
    enterprise_success = tier_results[UserTier.ENTERPRISE]["success_rate"]
    mid_success = tier_results[UserTier.MID]["success_rate"]
    free_success = tier_results[UserTier.FREE]["success_rate"]
    
    assert enterprise_success >= mid_success
    assert mid_success >= free_success
    
    # Enterprise should have fewer rate limit violations
    enterprise_limited = tier_results[UserTier.ENTERPRISE]["rate_limited_requests"]
    free_limited = tier_results[UserTier.FREE]["rate_limited_requests"]
    
    assert enterprise_limited <= free_limited

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_concurrent_endpoint_rate_limiting(api_gateway_manager):
    """Test rate limiting with concurrent requests across endpoints."""
    endpoints = ["/api/v1/chat", "/api/v1/threads", "/api/v1/agents"]
    concurrent_users = 10
    
    result = await api_gateway_manager.test_concurrent_endpoint_requests(
        endpoints, concurrent_users
    )
    
    # Should handle concurrent requests without errors
    assert result["total_requests"] == len(endpoints) * concurrent_users
    assert result["execution_time"] < 10.0  # Should complete within 10 seconds
    
    # Each endpoint should receive requests
    for endpoint in endpoints:
        endpoint_stats = result["endpoint_stats"][endpoint]
        assert endpoint_stats["total_requests"] == concurrent_users
        
        # High-priority endpoints should have better success rates
        if endpoint == "/api/v1/chat":  # Highest priority
            assert endpoint_stats["success_rate"] >= 70

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_burst_traffic_circuit_breaking(api_gateway_manager):
    """Test circuit breaking behavior under extreme burst traffic."""
    endpoint = "/api/v1/agents"
    user_id = "burst_test_user"
    
    # Generate extreme burst traffic
    extreme_burst = await api_gateway_manager.simulate_burst_traffic(
        endpoint, user_id, UserTier.FREE, 100, 10  # 100 requests in 10 seconds
    )
    
    # Should enforce rate limits aggressively
    assert extreme_burst["rate_limited_requests"] > 50
    assert extreme_burst["success_rate"] < 50
    
    # Wait for rate limit window to reset
    await asyncio.sleep(65)  # Wait for 1-minute window reset
    
    # Subsequent requests should succeed
    recovery_result = await api_gateway_manager.make_http_request(
        endpoint, user_id, UserTier.FREE
    )
    assert recovery_result["status_code"] == 200
    assert recovery_result["allowed"] is True

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_rate_limit_header_accuracy(api_gateway_manager):
    """Test accuracy of rate limiting headers."""
    endpoint = "/api/v1/metrics"
    user_id = "header_test_user"
    user_tier = UserTier.MID
    
    # Make initial request
    result = await api_gateway_manager.make_http_request(endpoint, user_id, user_tier)
    
    assert result["status_code"] == 200
    assert "X-RateLimit-Limit" in result["headers"]
    assert "X-RateLimit-Remaining" in result["headers"]
    
    initial_remaining = int(result["headers"]["X-RateLimit-Remaining"])
    limit = int(result["headers"]["X-RateLimit-Limit"])
    
    # Make another request
    result2 = await api_gateway_manager.make_http_request(endpoint, user_id, user_tier)
    
    assert result2["status_code"] == 200
    remaining_after = int(result2["headers"]["X-RateLimit-Remaining"])
    
    # Remaining count should decrease
    assert remaining_after == initial_remaining - 1
    assert limit > remaining_after

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_gateway_metrics_collection(api_gateway_manager):
    """Test collection of gateway rate limiting metrics."""
    # Generate test traffic across endpoints
    test_scenarios = [
        ("/api/v1/chat", "metrics_user_1", UserTier.FREE, 10),
        ("/api/v1/threads", "metrics_user_2", UserTier.MID, 15),
        ("/api/v1/health", "metrics_user_3", UserTier.ENTERPRISE, 20)
    ]
    
    for endpoint, user_id, tier, count in test_scenarios:
        for i in range(count):
            await api_gateway_manager.make_http_request(endpoint, user_id, tier)
    
    # Get metrics
    metrics = await api_gateway_manager.get_gateway_metrics()
    
    # Verify metrics accuracy
    assert metrics["total_requests"] == 45  # 10 + 15 + 20
    assert metrics["configured_endpoints"] == 5
    
    # Verify endpoint breakdown
    assert "/api/v1/chat" in metrics["endpoint_breakdown"]
    assert "/api/v1/threads" in metrics["endpoint_breakdown"]
    assert "/api/v1/health" in metrics["endpoint_breakdown"]
    
    # Verify tier breakdown
    assert metrics["tier_breakdown"]["free"] == 10
    assert metrics["tier_breakdown"]["mid"] == 15
    assert metrics["tier_breakdown"]["enterprise"] == 20

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
@pytest.mark.asyncio
async def test_rate_limiting_performance_requirements(api_gateway_manager):
    """Test rate limiting performance meets requirements."""
    endpoint = "/api/v1/health"
    user_id = "performance_test_user"
    
    # Test response time under normal load
    response_times = []
    
    for i in range(20):
        result = await api_gateway_manager.make_http_request(
            endpoint, user_id, UserTier.MID
        )
        if result["allowed"]:
            response_times.append(result["response_time"])
    
    # Calculate performance metrics
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    
    # Rate limiting should add minimal overhead
    assert avg_response_time < 0.5  # Average < 500ms
    assert max_response_time < 1.0  # Max < 1 second
    
    # Test concurrent performance
    concurrent_tasks = []
    for i in range(15):
        task = api_gateway_manager.make_http_request(
            endpoint, f"perf_user_{i}", UserTier.MID
        )
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # Concurrent execution should be efficient
    assert concurrent_duration < 3.0  # 15 requests in < 3 seconds
    
    # Most requests should succeed (health endpoint has high limits)
    successful = [r for r in concurrent_results if r["allowed"]]
    assert len(successful) >= 12  # At least 80% success rate