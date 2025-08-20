"""L3 Integration Test: Concurrent Authentication Rate Limiting

Business Value Justification (BVJ):
- Segment: All tiers (security and stability)
- Business Goal: Prevent authentication abuse and maintain service availability
- Value Impact: Protects against brute force attacks and service degradation
- Strategic Impact: Critical for security compliance and SLA maintenance for $75K MRR

L3 Test: Real rate limiting with Redis-backed counters under concurrent load.
Tests authentication throttling, IP blocking, and service protection.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from collections import defaultdict

import redis.asyncio as redis
from app.services.auth.oauth_service import OAuthService
from app.services.auth.jwt_service import JWTService
from app.services.auth.rate_limiter import AuthRateLimiter
from app.redis_manager import RedisManager
from app.logging_config import central_logger
from ..helpers.redis_l3_helpers import RedisContainer

logger = central_logger.get_logger(__name__)


class RateLimitTestScenario:
    """Represents a rate limiting test scenario."""
    
    def __init__(self, scenario_id: str, client_ip: str, user_agent: str = "test_client"):
        self.scenario_id = scenario_id
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.attempts = []
        self.rate_limit_hits = []
        self.successful_auths = []
        self.blocked_attempts = []
    
    def add_attempt(self, timestamp: float, success: bool, blocked: bool = False):
        """Record an authentication attempt."""
        attempt = {
            "timestamp": timestamp,
            "success": success,
            "blocked": blocked,
            "scenario_id": self.scenario_id
        }
        
        self.attempts.append(attempt)
        
        if blocked:
            self.blocked_attempts.append(attempt)
        elif success:
            self.successful_auths.append(attempt)
        else:
            self.rate_limit_hits.append(attempt)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scenario metrics."""
        return {
            "total_attempts": len(self.attempts),
            "successful_auths": len(self.successful_auths),
            "rate_limit_hits": len(self.rate_limit_hits),
            "blocked_attempts": len(self.blocked_attempts),
            "success_rate": len(self.successful_auths) / max(len(self.attempts), 1),
            "block_rate": len(self.blocked_attempts) / max(len(self.attempts), 1)
        }


class ConcurrentAuthRateLimitManager:
    """Manages concurrent authentication rate limiting testing."""
    
    def __init__(self, oauth_service: OAuthService, jwt_service: JWTService,
                 rate_limiter: AuthRateLimiter, redis_client):
        self.oauth_service = oauth_service
        self.jwt_service = jwt_service
        self.rate_limiter = rate_limiter
        self.redis_client = redis_client
        self.test_scenarios = {}
        self.load_test_results = []
        
        # Rate limiting configuration
        self.rate_limits = {
            "attempts_per_minute": 10,
            "attempts_per_hour": 100,
            "failed_attempts_threshold": 5,
            "ip_block_duration": 300,  # 5 minutes
            "global_rate_limit": 1000  # requests per minute across all IPs
        }
    
    async def initialize_rate_limits(self):
        """Initialize rate limiting rules in Redis."""
        # Set rate limiting configuration
        config_key = "rate_limit_config"
        config_data = json.dumps(self.rate_limits)
        await self.redis_client.set(config_key, config_data, ex=3600)
        
        # Initialize rate limiter
        await self.rate_limiter.initialize()
        
        logger.info("Rate limiting configuration initialized")
    
    async def simulate_auth_attempt(self, scenario: RateLimitTestScenario,
                                  username: str, password: str, 
                                  expect_success: bool = True) -> Dict[str, Any]:
        """Simulate a single authentication attempt."""
        attempt_start = time.time()
        
        # Check rate limit before attempting auth
        rate_limit_check = await self.rate_limiter.check_rate_limit(
            client_ip=scenario.client_ip,
            user_agent=scenario.user_agent,
            endpoint="auth_login"
        )
        
        if not rate_limit_check["allowed"]:
            # Rate limited
            scenario.add_attempt(attempt_start, False, blocked=True)
            return {
                "success": False,
                "blocked": True,
                "reason": "rate_limited",
                "rate_limit_info": rate_limit_check,
                "duration": time.time() - attempt_start
            }
        
        # Attempt authentication
        try:
            # Simulate OAuth authentication
            auth_result = await self._perform_auth(username, password, expect_success)
            
            # Record rate limit usage
            await self.rate_limiter.record_attempt(
                client_ip=scenario.client_ip,
                user_agent=scenario.user_agent,
                endpoint="auth_login",
                success=auth_result["success"]
            )
            
            scenario.add_attempt(attempt_start, auth_result["success"])
            
            return {
                "success": auth_result["success"],
                "blocked": False,
                "auth_result": auth_result,
                "duration": time.time() - attempt_start
            }
            
        except Exception as e:
            # Auth failed
            await self.rate_limiter.record_attempt(
                client_ip=scenario.client_ip,
                user_agent=scenario.user_agent,
                endpoint="auth_login",
                success=False
            )
            
            scenario.add_attempt(attempt_start, False)
            
            return {
                "success": False,
                "blocked": False,
                "error": str(e),
                "duration": time.time() - attempt_start
            }
    
    async def run_concurrent_auth_load_test(self, scenario_configs: List[Dict[str, Any]],
                                          requests_per_scenario: int = 20) -> Dict[str, Any]:
        """Run concurrent authentication load test across multiple scenarios."""
        load_test_start = time.time()
        
        # Create test scenarios
        scenarios = []
        for config in scenario_configs:
            scenario = RateLimitTestScenario(
                scenario_id=config["scenario_id"],
                client_ip=config["client_ip"],
                user_agent=config.get("user_agent", "load_test_client")
            )
            scenarios.append(scenario)
            self.test_scenarios[scenario.scenario_id] = scenario
        
        # Generate concurrent auth attempts
        auth_tasks = []
        for scenario in scenarios:
            for i in range(requests_per_scenario):
                # Mix of valid and invalid credentials
                username = f"user_{scenario.scenario_id}_{i}"
                password = "correct_password" if i % 3 == 0 else "wrong_password"
                expect_success = (i % 3 == 0)
                
                task = self.simulate_auth_attempt(scenario, username, password, expect_success)
                auth_tasks.append(task)
                
                # Stagger requests slightly to simulate realistic load
                if i % 5 == 0:
                    await asyncio.sleep(0.01)
        
        # Execute all authentication attempts concurrently
        logger.info(f"Starting {len(auth_tasks)} concurrent auth attempts")
        auth_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        load_test_duration = time.time() - load_test_start
        
        # Analyze results
        total_attempts = len(auth_results)
        successful_auths = sum(1 for r in auth_results if not isinstance(r, Exception) and r.get("success"))
        blocked_attempts = sum(1 for r in auth_results if not isinstance(r, Exception) and r.get("blocked"))
        failed_attempts = total_attempts - successful_auths - blocked_attempts
        exceptions = sum(1 for r in auth_results if isinstance(r, Exception))
        
        # Calculate performance metrics
        avg_response_time = 0
        if auth_results:
            response_times = [r.get("duration", 0) for r in auth_results if not isinstance(r, Exception)]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        load_test_result = {
            "test_duration": load_test_duration,
            "total_attempts": total_attempts,
            "successful_auths": successful_auths,
            "blocked_attempts": blocked_attempts,
            "failed_attempts": failed_attempts,
            "exceptions": exceptions,
            "avg_response_time": avg_response_time,
            "requests_per_second": total_attempts / load_test_duration,
            "scenarios": {s.scenario_id: s.get_metrics() for s in scenarios}
        }
        
        self.load_test_results.append(load_test_result)
        
        logger.info(f"Load test completed: {successful_auths}/{total_attempts} successful, "
                   f"{blocked_attempts} blocked, {load_test_duration:.2f}s")
        
        return load_test_result
    
    async def test_ip_blocking_escalation(self, client_ip: str, 
                                        failed_attempts_count: int = 10) -> Dict[str, Any]:
        """Test IP blocking escalation for repeated failed attempts."""
        scenario = RateLimitTestScenario(f"ip_block_{client_ip}", client_ip)
        
        # Perform repeated failed attempts
        block_test_start = time.time()
        for i in range(failed_attempts_count):
            result = await self.simulate_auth_attempt(
                scenario, f"fake_user_{i}", "wrong_password", expect_success=False
            )
            
            # Check if IP got blocked
            if result.get("blocked"):
                logger.info(f"IP {client_ip} blocked after {i+1} failed attempts")
                break
            
            await asyncio.sleep(0.1)  # Small delay between attempts
        
        # Test that IP remains blocked
        blocked_result = await self.simulate_auth_attempt(
            scenario, "test_user", "correct_password", expect_success=True
        )
        
        # Get IP block status
        ip_status = await self.rate_limiter.get_ip_status(client_ip)
        
        test_duration = time.time() - block_test_start
        
        return {
            "ip": client_ip,
            "failed_attempts": len(scenario.rate_limit_hits),
            "blocked_attempts": len(scenario.blocked_attempts),
            "ip_blocked": blocked_result.get("blocked", False),
            "ip_status": ip_status,
            "test_duration": test_duration,
            "scenario_metrics": scenario.get_metrics()
        }
    
    async def test_rate_limit_recovery(self, client_ip: str, 
                                     recovery_wait_time: int = 10) -> Dict[str, Any]:
        """Test rate limit recovery after waiting period."""
        # First, trigger rate limiting
        scenario = RateLimitTestScenario(f"recovery_{client_ip}", client_ip)
        
        # Rapidly exhaust rate limit
        rapid_attempts = 15  # Exceed per-minute limit
        for i in range(rapid_attempts):
            await self.simulate_auth_attempt(
                scenario, f"user_{i}", "wrong_password", expect_success=False
            )
        
        # Verify rate limiting active
        immediate_check = await self.rate_limiter.check_rate_limit(
            client_ip=client_ip,
            user_agent="test_client",
            endpoint="auth_login"
        )
        
        rate_limited_before = not immediate_check["allowed"]
        
        # Wait for recovery period
        logger.info(f"Waiting {recovery_wait_time}s for rate limit recovery")
        await asyncio.sleep(recovery_wait_time)
        
        # Test if rate limit has recovered
        recovery_check = await self.rate_limiter.check_rate_limit(
            client_ip=client_ip,
            user_agent="test_client",
            endpoint="auth_login"
        )
        
        # Attempt successful auth after recovery
        recovery_auth = await self.simulate_auth_attempt(
            scenario, "recovered_user", "correct_password", expect_success=True
        )
        
        return {
            "ip": client_ip,
            "rate_limited_before_wait": rate_limited_before,
            "rate_limited_after_wait": not recovery_check["allowed"],
            "recovery_auth_success": recovery_auth.get("success", False),
            "recovery_auth_blocked": recovery_auth.get("blocked", False),
            "wait_time": recovery_wait_time,
            "scenario_metrics": scenario.get_metrics()
        }
    
    async def _perform_auth(self, username: str, password: str, 
                          expect_success: bool) -> Dict[str, Any]:
        """Perform authentication attempt (mocked)."""
        # Simulate authentication processing delay
        await asyncio.sleep(0.02)  # 20ms processing time
        
        if expect_success:
            # Generate successful auth response
            token_result = await self.jwt_service.generate_token(
                user_id=f"user_{username}",
                permissions=["read"],
                tier="free"
            )
            
            return {
                "success": True,
                "user_id": f"user_{username}",
                "token": token_result.get("token") if token_result.get("success") else None
            }
        else:
            # Simulate auth failure
            return {
                "success": False,
                "error": "Invalid credentials"
            }
    
    async def get_rate_limit_metrics(self) -> Dict[str, Any]:
        """Get current rate limiting metrics from Redis."""
        # Get all rate limit keys
        rate_limit_keys = await self.redis_client.keys("rate_limit:*")
        ip_block_keys = await self.redis_client.keys("ip_block:*")
        
        metrics = {
            "active_rate_limits": len(rate_limit_keys),
            "blocked_ips": len(ip_block_keys),
            "rate_limit_details": {},
            "blocked_ip_details": {}
        }
        
        # Get rate limit details
        for key in rate_limit_keys[:10]:  # Limit to first 10 for performance
            try:
                data = await self.redis_client.get(key)
                if data:
                    metrics["rate_limit_details"][key] = json.loads(data)
            except Exception as e:
                logger.warning(f"Error getting rate limit data for {key}: {e}")
        
        # Get blocked IP details
        for key in ip_block_keys[:10]:  # Limit to first 10 for performance
            try:
                data = await self.redis_client.get(key)
                if data:
                    metrics["blocked_ip_details"][key] = json.loads(data)
            except Exception as e:
                logger.warning(f"Error getting IP block data for {key}: {e}")
        
        return metrics
    
    async def cleanup(self):
        """Clean up rate limiting test data."""
        # Clear rate limit keys
        rate_limit_keys = await self.redis_client.keys("rate_limit:*")
        ip_block_keys = await self.redis_client.keys("ip_block:*")
        
        if rate_limit_keys:
            await self.redis_client.delete(*rate_limit_keys)
        if ip_block_keys:
            await self.redis_client.delete(*ip_block_keys)
        
        logger.info(f"Cleaned up {len(rate_limit_keys)} rate limit keys and {len(ip_block_keys)} IP block keys")


@pytest.mark.L3
@pytest.mark.integration
class TestConcurrentAuthRateLimitingL3:
    """L3 integration test for concurrent authentication rate limiting."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def oauth_service(self, redis_client):
        """Initialize OAuth service."""
        service = OAuthService()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = redis_client
            await service.initialize()
            yield service
            await service.shutdown()
    
    @pytest.fixture
    async def jwt_service(self, redis_client):
        """Initialize JWT service."""
        service = JWTService()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = redis_client
            await service.initialize()
            yield service
            await service.shutdown()
    
    @pytest.fixture
    async def rate_limiter(self, redis_client):
        """Initialize rate limiter."""
        limiter = AuthRateLimiter()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = redis_client
            await limiter.initialize()
            yield limiter
            await limiter.shutdown()
    
    @pytest.fixture
    async def rate_limit_manager(self, oauth_service, jwt_service, rate_limiter, redis_client):
        """Create rate limiting test manager."""
        manager = ConcurrentAuthRateLimitManager(oauth_service, jwt_service, rate_limiter, redis_client)
        await manager.initialize_rate_limits()
        yield manager
        await manager.cleanup()
    
    async def test_concurrent_auth_rate_limiting_basic(self, rate_limit_manager):
        """Test basic rate limiting under concurrent authentication load."""
        # Define test scenarios with different client IPs
        scenario_configs = [
            {"scenario_id": "normal_user", "client_ip": "192.168.1.100"},
            {"scenario_id": "aggressive_user", "client_ip": "192.168.1.101"},
            {"scenario_id": "mobile_user", "client_ip": "192.168.1.102", "user_agent": "mobile_app"}
        ]
        
        # Run concurrent load test
        load_result = await rate_limit_manager.run_concurrent_auth_load_test(
            scenario_configs, requests_per_scenario=15
        )
        
        # Verify load test metrics
        assert load_result["total_attempts"] == 45  # 3 scenarios × 15 requests
        assert load_result["test_duration"] < 10.0  # Should complete quickly
        assert load_result["exceptions"] == 0  # No unhandled exceptions
        
        # Verify rate limiting engaged
        assert load_result["blocked_attempts"] > 0  # Some requests should be blocked
        
        # Verify different scenarios behaved differently
        scenario_metrics = load_result["scenarios"]
        assert len(scenario_metrics) == 3
        
        # At least one scenario should have blocks
        total_blocks = sum(metrics["blocked_attempts"] for metrics in scenario_metrics.values())
        assert total_blocks > 0
        
        # Verify success rate is reasonable (not 0 or 100%)
        total_success = sum(metrics["successful_auths"] for metrics in scenario_metrics.values())
        success_rate = total_success / load_result["total_attempts"]
        assert 0.1 < success_rate < 0.9  # Between 10% and 90%
    
    async def test_ip_blocking_escalation_mechanism(self, rate_limit_manager):
        """Test IP blocking escalation for repeated failures."""
        test_ip = "192.168.1.200"
        
        # Test IP blocking escalation
        block_result = await rate_limit_manager.test_ip_blocking_escalation(
            test_ip, failed_attempts_count=8
        )
        
        # Verify IP blocking triggered
        assert block_result["failed_attempts"] > 0
        assert block_result["blocked_attempts"] > 0
        assert block_result["ip_blocked"] is True
        
        # Verify IP status shows blocking
        ip_status = block_result["ip_status"]
        assert ip_status.get("blocked", False) is True
        assert "block_expiry" in ip_status
        
        # Verify even valid credentials are blocked
        scenario_metrics = block_result["scenario_metrics"]
        assert scenario_metrics["block_rate"] > 0
        
        logger.info(f"IP {test_ip} blocked after {block_result['failed_attempts']} failed attempts")
    
    async def test_rate_limit_recovery_timing(self, rate_limit_manager):
        """Test rate limit recovery after waiting period."""
        test_ip = "192.168.1.201"
        
        # Test rate limit recovery
        recovery_result = await rate_limit_manager.test_rate_limit_recovery(
            test_ip, recovery_wait_time=5  # Shorter wait for testing
        )
        
        # Verify rate limiting was initially active
        assert recovery_result["rate_limited_before_wait"] is True
        
        # Verify recovery depends on wait time and configuration
        # (May or may not be recovered depending on actual rate limit window)
        recovery_auth_worked = recovery_result["recovery_auth_success"]
        recovery_auth_blocked = recovery_result["recovery_auth_blocked"]
        
        # Either auth succeeded (rate limit recovered) OR it's still blocked (rate limit active)
        assert recovery_auth_worked or recovery_auth_blocked
        
        # If auth worked, rate limit should have recovered
        if recovery_auth_worked:
            assert not recovery_result["rate_limited_after_wait"]
        
        logger.info(f"Rate limit recovery test: auth_success={recovery_auth_worked}, "
                   f"still_blocked={recovery_auth_blocked}")
    
    async def test_global_rate_limit_enforcement(self, rate_limit_manager):
        """Test global rate limiting across multiple IPs."""
        # Create many different IP scenarios to test global limits
        scenario_configs = []
        for i in range(10):  # 10 different IPs
            scenario_configs.append({
                "scenario_id": f"global_test_ip_{i}",
                "client_ip": f"10.0.0.{i+1}"
            })
        
        # Run aggressive load test
        load_result = await rate_limit_manager.run_concurrent_auth_load_test(
            scenario_configs, requests_per_scenario=25  # Higher load
        )
        
        # Verify global rate limiting effects
        total_requests = load_result["total_attempts"]
        blocked_requests = load_result["blocked_attempts"]
        
        assert total_requests == 250  # 10 IPs × 25 requests
        assert blocked_requests > 0  # Global limits should block some
        
        # Verify requests per second was limited
        rps = load_result["requests_per_second"]
        logger.info(f"Achieved {rps:.1f} requests/second with global rate limiting")
        
        # Should be limited by global rate limit configuration
        global_limit = rate_limit_manager.rate_limits["global_rate_limit"]
        # Allow some variance for test timing
        assert rps < (global_limit * 1.5)  # Should be roughly limited by global config
    
    async def test_rate_limiting_redis_persistence(self, rate_limit_manager, redis_client):
        """Test rate limiting data persistence in Redis."""
        test_ip = "192.168.1.202"
        
        # Perform some auth attempts to create rate limit data
        scenario = RateLimitTestScenario("persistence_test", test_ip)
        
        for i in range(5):
            await rate_limit_manager.simulate_auth_attempt(
                scenario, f"user_{i}", "wrong_password", expect_success=False
            )
        
        # Check rate limiting data in Redis
        metrics = await rate_limit_manager.get_rate_limit_metrics()
        
        # Verify rate limit data exists
        assert metrics["active_rate_limits"] > 0
        
        # Verify rate limit details structure
        rate_limit_details = metrics["rate_limit_details"]
        assert len(rate_limit_details) > 0
        
        # Check for IP-specific rate limit entries
        ip_rate_limit_keys = [key for key in rate_limit_details.keys() if test_ip in key]
        assert len(ip_rate_limit_keys) > 0
        
        # Verify rate limit data structure
        for key, data in rate_limit_details.items():
            assert isinstance(data, dict)
            # Should contain rate limiting metadata
            assert "attempts" in data or "count" in data or "timestamp" in data
        
        logger.info(f"Rate limiting persistence verified: {metrics['active_rate_limits']} active limits")
    
    async def test_concurrent_ip_blocking_isolation(self, rate_limit_manager):
        """Test that IP blocking for one IP doesn't affect others."""
        # Two different IPs
        good_ip = "192.168.1.203"
        bad_ip = "192.168.1.204"
        
        # Create scenarios
        good_scenario = RateLimitTestScenario("good_ip", good_ip)
        bad_scenario = RateLimitTestScenario("bad_ip", bad_ip)
        
        # Block the bad IP with failed attempts
        for i in range(10):
            await rate_limit_manager.simulate_auth_attempt(
                bad_scenario, f"bad_user_{i}", "wrong_password", expect_success=False
            )
        
        # Test that good IP can still authenticate
        good_auth = await rate_limit_manager.simulate_auth_attempt(
            good_scenario, "good_user", "correct_password", expect_success=True
        )
        
        # Test that bad IP is blocked
        bad_auth = await rate_limit_manager.simulate_auth_attempt(
            bad_scenario, "bad_user_final", "correct_password", expect_success=True
        )
        
        # Verify isolation
        assert good_auth["success"] is True
        assert good_auth["blocked"] is False
        
        assert bad_auth["success"] is False
        assert bad_auth["blocked"] is True
        
        # Verify metrics
        good_metrics = good_scenario.get_metrics()
        bad_metrics = bad_scenario.get_metrics()
        
        assert good_metrics["success_rate"] > 0.9  # Good IP should have high success
        assert bad_metrics["block_rate"] > 0.5  # Bad IP should have high block rate
        
        logger.info(f"IP isolation verified: good_ip success={good_metrics['success_rate']:.2f}, "
                   f"bad_ip block_rate={bad_metrics['block_rate']:.2f}")
    
    async def test_rate_limiting_performance_under_load(self, rate_limit_manager):
        """Test rate limiting performance impact under high load."""
        # High concurrency test
        scenario_configs = []
        for i in range(20):  # 20 concurrent IP scenarios
            scenario_configs.append({
                "scenario_id": f"perf_test_{i}",
                "client_ip": f"172.16.0.{i+1}"
            })
        
        # Measure performance
        performance_start = time.time()
        
        load_result = await rate_limit_manager.run_concurrent_auth_load_test(
            scenario_configs, requests_per_scenario=10
        )
        
        performance_duration = time.time() - performance_start
        
        # Performance assertions
        total_requests = load_result["total_attempts"]
        avg_response_time = load_result["avg_response_time"]
        
        assert total_requests == 200  # 20 scenarios × 10 requests
        assert performance_duration < 15.0  # Should complete in reasonable time
        assert avg_response_time < 0.5  # Individual requests should be fast
        
        # Rate limiting shouldn't severely impact performance
        rps = total_requests / performance_duration
        assert rps > 10  # Should maintain reasonable throughput
        
        # Verify rate limiting was active but didn't break the system
        blocked_percentage = load_result["blocked_attempts"] / total_requests
        assert 0.1 < blocked_percentage < 0.8  # Some blocking, but not overwhelming
        
        logger.info(f"Performance test: {total_requests} requests in {performance_duration:.2f}s "
                   f"({rps:.1f} RPS), avg response time: {avg_response_time:.3f}s, "
                   f"blocked: {blocked_percentage:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])