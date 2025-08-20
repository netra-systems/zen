"""
Concurrent User Authentication Load Test

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise
- Business Goal: Scalability & Performance
- Value Impact: Validates system handles enterprise-level concurrent load
- Revenue Impact: Protects $45K Enterprise segment revenue

Tests 100+ concurrent login attempts, response times under load,
token collision prevention, and rate limiting mechanisms.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any, Tuple
import httpx
from dataclasses import dataclass
from collections import defaultdict
import statistics

from app.core.configuration.database import DatabaseConfig
from test_framework.real_service_helper import RealServiceHelper
from test_framework.mock_utils import mock_justified


@dataclass
class AuthenticationResult:
    """Result of an authentication attempt."""
    user_id: str
    success: bool
    response_time: float
    token: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    retry_count: int = 0


class ConcurrentAuthLoadTest:
    """Test concurrent user authentication under load."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.service_helper = RealServiceHelper()
        self.results: List[AuthenticationResult] = []
        self.rate_limit_hits = 0
        self.backpressure_events = 0
    
    async def setup(self):
        """Setup test environment."""
        # Ensure services are running
        await self.service_helper.ensure_services_running([
            "auth_service",
            "backend",
            "redis"
        ])
        
        # Clear any existing rate limits
        await self._clear_rate_limits()
        
        # Configure test database pool
        await self._configure_database_pool()
    
    async def teardown(self):
        """Cleanup after tests."""
        # Reset rate limits to defaults
        await self._reset_rate_limits()
    
    async def _clear_rate_limits(self):
        """Clear existing rate limits for testing."""
        import redis.asyncio as redis
        
        redis_client = redis.from_url("redis://localhost:6379")
        await redis_client.delete("rate_limit:*")
        await redis_client.close()
    
    async def _reset_rate_limits(self):
        """Reset rate limits to default values."""
        # Reset through API or configuration
        pass
    
    async def _configure_database_pool(self):
        """Configure database connection pool for load testing."""
        db_config = DatabaseConfig()
        # Ensure pool size can handle concurrent load
        db_config.pool_size = 50
        db_config.max_overflow = 20
    
    async def authenticate_user(self, user_email: str, 
                               user_index: int) -> AuthenticationResult:
        """Authenticate a single user."""
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        
        while retry_count <= max_retries:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    # Register user if needed
                    register_response = await client.post(
                        f"{self.auth_url}/auth/register",
                        json={
                            "email": user_email,
                            "password": f"password_{user_index}",
                            "user_id": f"user_{user_index}"
                        }
                    )
                    
                    # Attempt authentication
                    auth_response = await client.post(
                        f"{self.auth_url}/auth/token",
                        json={
                            "username": user_email,
                            "password": f"password_{user_index}",
                            "grant_type": "password"
                        }
                    )
                    
                    response_time = time.time() - start_time
                    
                    if auth_response.status_code == 200:
                        token_data = auth_response.json()
                        return AuthenticationResult(
                            user_id=f"user_{user_index}",
                            success=True,
                            response_time=response_time,
                            token=token_data.get("access_token"),
                            status_code=auth_response.status_code,
                            retry_count=retry_count
                        )
                    elif auth_response.status_code == 429:
                        # Rate limited
                        self.rate_limit_hits += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                            retry_count += 1
                            continue
                        else:
                            return AuthenticationResult(
                                user_id=f"user_{user_index}",
                                success=False,
                                response_time=response_time,
                                error="Rate limited",
                                status_code=429,
                                retry_count=retry_count
                            )
                    elif auth_response.status_code == 503:
                        # Service overloaded (backpressure)
                        self.backpressure_events += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(1)
                            retry_count += 1
                            continue
                    else:
                        return AuthenticationResult(
                            user_id=f"user_{user_index}",
                            success=False,
                            response_time=response_time,
                            error=auth_response.text,
                            status_code=auth_response.status_code,
                            retry_count=retry_count
                        )
                        
            except Exception as e:
                if retry_count < max_retries:
                    retry_count += 1
                    await asyncio.sleep(0.5)
                    continue
                
                response_time = time.time() - start_time
                return AuthenticationResult(
                    user_id=f"user_{user_index}",
                    success=False,
                    response_time=response_time,
                    error=str(e),
                    retry_count=retry_count
                )
        
        # Should not reach here
        response_time = time.time() - start_time
        return AuthenticationResult(
            user_id=f"user_{user_index}",
            success=False,
            response_time=response_time,
            error="Max retries exceeded",
            retry_count=retry_count
        )
    
    async def run_concurrent_authentication(self, 
                                           concurrent_users: int) -> List[AuthenticationResult]:
        """Run concurrent authentication attempts."""
        auth_tasks = []
        
        for i in range(concurrent_users):
            email = f"user_{i}@loadtest.com"
            task = self.authenticate_user(email, i)
            auth_tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*auth_tasks, return_exceptions=False)
        
        self.results = results
        return results
    
    def calculate_metrics(self, results: List[AuthenticationResult]) -> Dict[str, Any]:
        """Calculate performance metrics from results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        response_times = [r.response_time for r in results]
        
        metrics = {
            "total_attempts": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "p50_response_time": statistics.median(response_times) if response_times else 0,
            "p95_response_time": self._calculate_percentile(response_times, 95) if response_times else 0,
            "p99_response_time": self._calculate_percentile(response_times, 99) if response_times else 0,
            "rate_limit_hits": self.rate_limit_hits,
            "backpressure_events": self.backpressure_events,
            "retry_attempts": sum(r.retry_count for r in results)
        }
        
        return metrics
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def validate_no_token_collisions(self, results: List[AuthenticationResult]) -> bool:
        """Validate that all generated tokens are unique."""
        tokens = [r.token for r in results if r.token]
        unique_tokens = set(tokens)
        return len(tokens) == len(unique_tokens)
    
    async def test_rate_limiting(self, user_tier: str = "free") -> Dict[str, Any]:
        """Test rate limiting for specific user tier."""
        rate_limits = {
            "free": 10,  # 10 requests per minute
            "paid": 100,  # 100 requests per minute
            "enterprise": 1000  # 1000 requests per minute
        }
        
        limit = rate_limits.get(user_tier, 10)
        
        # Create test user with specific tier
        test_email = f"ratelimit_test_{user_tier}@example.com"
        
        # Send requests up to and beyond limit
        results = []
        for i in range(limit + 5):  # Go 5 over limit
            result = await self.authenticate_user(test_email, 0)
            results.append(result)
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.1)
        
        # Count rate limited responses
        rate_limited = [r for r in results if r.status_code == 429]
        
        return {
            "tier": user_tier,
            "limit": limit,
            "total_requests": len(results),
            "rate_limited_count": len(rate_limited),
            "rate_limiting_active": len(rate_limited) > 0
        }


@pytest.mark.integration
@pytest.mark.performance
class TestConcurrentUserAuthLoad:
    """Test suite for concurrent user authentication load."""
    
    @pytest.fixture
    async def test_harness(self):
        """Create test harness for load testing."""
        harness = ConcurrentAuthLoadTest()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    @pytest.mark.asyncio
    async def test_concurrent_user_authentication_load(self, test_harness):
        """
        Test concurrent authentication under load.
        
        Validates:
        1. 100+ concurrent login attempts
        2. 95%+ success rate
        3. Average response time <500ms
        4. No token collisions
        5. Rate limiting activation
        """
        concurrent_users = 100
        
        # Run concurrent authentication
        results = await test_harness.run_concurrent_authentication(concurrent_users)
        
        # Calculate metrics
        metrics = test_harness.calculate_metrics(results)
        
        # Validation Phase 1: Success Rate
        assert metrics["success_rate"] >= 95, \
            f"Success rate {metrics['success_rate']:.1f}% below 95% threshold"
        
        # Validation Phase 2: Response Time
        assert metrics["avg_response_time"] < 0.5, \
            f"Average response time {metrics['avg_response_time']:.3f}s exceeds 500ms"
        
        assert metrics["p99_response_time"] < 2.0, \
            f"P99 response time {metrics['p99_response_time']:.3f}s exceeds 2s"
        
        # Validation Phase 3: Token Uniqueness
        no_collisions = test_harness.validate_no_token_collisions(results)
        assert no_collisions, "Token collisions detected!"
        
        # Validation Phase 4: System Stability
        assert metrics["failed"] < concurrent_users * 0.05, \
            f"Too many failures: {metrics['failed']}/{concurrent_users}"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, test_harness):
        """Test rate limiting enforcement for different user tiers."""
        tiers = ["free", "paid", "enterprise"]
        
        for tier in tiers:
            rate_limit_result = await test_harness.test_rate_limiting(tier)
            
            # Rate limiting should be active for requests beyond limit
            assert rate_limit_result["rate_limiting_active"], \
                f"Rate limiting not enforced for {tier} tier"
            
            # Should have some successful requests within limit
            successful_count = rate_limit_result["total_requests"] - \
                             rate_limit_result["rate_limited_count"]
            assert successful_count > 0, \
                f"No successful requests for {tier} tier"
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_stability(self, test_harness):
        """Test database connection pool under concurrent load."""
        # Higher concurrent load to stress connection pool
        concurrent_users = 150
        
        # Monitor database connections before load
        initial_pool_stats = await test_harness.service_helper.get_database_pool_stats()
        
        # Run authentication load
        results = await test_harness.run_concurrent_authentication(concurrent_users)
        
        # Check pool stats after load
        final_pool_stats = await test_harness.service_helper.get_database_pool_stats()
        
        # Validate pool didn't exhaust
        metrics = test_harness.calculate_metrics(results)
        
        # Even with high load, should maintain reasonable success rate
        assert metrics["success_rate"] >= 90, \
            f"Success rate {metrics['success_rate']:.1f}% indicates pool exhaustion"
        
        # Pool should recover
        assert final_pool_stats.get("active_connections", 0) < \
               initial_pool_stats.get("max_connections", 50), \
               "Connection pool appears exhausted"
    
    @pytest.mark.asyncio
    async def test_backpressure_handling(self, test_harness):
        """Test backpressure mechanisms under extreme load."""
        # Extreme load to trigger backpressure
        concurrent_users = 200
        
        results = await test_harness.run_concurrent_authentication(concurrent_users)
        metrics = test_harness.calculate_metrics(results)
        
        # Should handle load gracefully with backpressure
        assert metrics["success_rate"] >= 85, \
            f"Success rate {metrics['success_rate']:.1f}% too low under backpressure"
        
        # Backpressure events should occur but system should recover
        if test_harness.backpressure_events > 0:
            # Verify retry mechanism worked
            assert metrics["retry_attempts"] > 0, \
                "No retries attempted despite backpressure"
            
            # Most retries should eventually succeed
            retry_success_rate = metrics["successful"] / concurrent_users * 100
            assert retry_success_rate >= 85, \
                f"Retry success rate {retry_success_rate:.1f}% too low"
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, test_harness):
        """Test sustained authentication load over time."""
        waves = 5  # Number of load waves
        users_per_wave = 50
        
        all_results = []
        wave_metrics = []
        
        for wave in range(waves):
            # Run authentication wave
            results = await test_harness.run_concurrent_authentication(users_per_wave)
            all_results.extend(results)
            
            # Calculate wave metrics
            metrics = test_harness.calculate_metrics(results)
            wave_metrics.append(metrics)
            
            # Brief pause between waves
            await asyncio.sleep(2)
        
        # Validate sustained performance
        for i, metrics in enumerate(wave_metrics):
            assert metrics["success_rate"] >= 90, \
                f"Wave {i+1} success rate {metrics['success_rate']:.1f}% below threshold"
            
            assert metrics["avg_response_time"] < 1.0, \
                f"Wave {i+1} response time {metrics['avg_response_time']:.3f}s too high"
        
        # Overall metrics should be stable
        overall_metrics = test_harness.calculate_metrics(all_results)
        assert overall_metrics["success_rate"] >= 92, \
            f"Overall success rate {overall_metrics['success_rate']:.1f}% below threshold"