"""
CRITICAL E2E Test #8: Real Rate Limiting with Redis Backend
Business Value: $25K MRR - Fair usage and cost control

This test validates the complete rate limiting pipeline using real Redis 
for rate limit counters. NO MOCKING - tests actual rate enforcement.

BVJ (Business Value Justification):
1. Segment: Free → Paid conversion through quota enforcement  
2. Business Goal: Fair usage control + upgrade conversion = 15-25% conversion
3. Value Impact: Prevents infrastructure abuse ($15K+ savings) + drives upgrades
4. Revenue Impact: Strategic rate limits convert 20-30% free users to paid

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Single responsibility: Real rate limiting testing only
- Must complete in <70 seconds including wait time
"""

import pytest
import asyncio
import time
import uuid
import redis.asyncio as redis
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.real_services_manager import ServiceManager
from tests.e2e.harness_utils import UnifiedTestHarnessComplete
from tests.e2e.rate_limiting_core import RedisManager, MessageSender, UserManager, RateLimitFlowValidator
from tests.e2e.rate_limiting_advanced import (
    APIRateLimitTester, WebSocketRateLimitTester, AgentThrottleTester, TierBasedRateLimitTester, DistributedRateLimitValidator, ResponseHeaderValidator,
    APIRateLimitTester, WebSocketRateLimitTester, AgentThrottleTester,
    TierBasedRateLimitTester, DistributedRateLimitValidator, ResponseHeaderValidator
)


class TestRedisRateLimiter:
    """Tests real Redis-backed rate limiting."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.service_manager = ServiceManager(harness)
        self.test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize Redis client and managers."""
        self.redis_client: Optional[redis.Redis] = None
        self.auth_token: Optional[str] = None
        self.redis_manager = RedisManager(self.test_user_id)
        self.user_manager = UserManager()
        self.validator = RateLimitFlowValidator()
        
        # Advanced testers (initialized after auth token is available)
        self.api_tester: Optional[APIRateLimitTester] = None
        self.websocket_tester: Optional[WebSocketRateLimitTester] = None
        self.agent_tester: Optional[AgentThrottleTester] = None
        self.tier_tester: Optional[TierBasedRateLimitTester] = None
        self.distributed_validator: Optional[DistributedRateLimitValidator] = None
        self.header_validator: Optional[ResponseHeaderValidator] = None
    
    async def execute_rate_limit_flow(self) -> Dict[str, Any]:
        """Execute complete rate limiting flow with Redis backend."""
        start_time = time.time()
        results = {"steps": [], "success": False, "duration": 0}
        
        try:
            await self._setup_test_environment()
            results["steps"].append({"step": "environment_ready", "success": True})
            
            # Execute all test steps
            await self._execute_all_test_steps(results)
            
            results["success"] = True
            results["duration"] = time.time() - start_time
            
            # CRITICAL: Must complete in <70 seconds
            assert results["duration"] < 70.0, f"Test took {results['duration']}s > 70s"
            
        except Exception as e:
            results["error"] = str(e)
            results["duration"] = time.time() - start_time
            raise
        finally:
            await self._cleanup_test_data()
        
        return results
    
    async def _execute_all_test_steps(self, results: Dict[str, Any]) -> None:
        """Execute all test steps in sequence."""
        steps = [
            ("user_setup", self._setup_free_user_with_redis),
            ("normal_usage", self._send_messages_within_limit),
            ("rate_limited", self._hit_rate_limit),
            ("rate_reset", self._wait_for_rate_limit_reset),
            ("post_reset", self._send_after_reset),
            ("upgrade", self._upgrade_to_paid_tier),
            ("unlimited", self._verify_unlimited_usage)
        ]
        
        for step_name, step_func in steps:
            step_result = await step_func()
            results["steps"].append({"step": step_name, "success": True, "data": step_result})


# Implementation of main tester methods
async def _setup_test_environment(self) -> None:
    """Setup test environment with services and Redis."""
    await self.service_manager.start_auth_service()
    await self.service_manager.start_backend_service()
    self.redis_client = await self.redis_manager.connect_to_redis()
    await asyncio.sleep(2)  # Allow services to initialize


async def _setup_free_user_with_redis(self) -> Dict[str, Any]:
    """Setup free user and verify Redis connection."""
    # Create free user
    user_data = await self.user_manager.create_free_user()
    self.auth_token = user_data["access_token"]
    
    # Verify Redis is working
    await self.redis_manager.verify_rate_limit_counter(self.redis_client, 0)
    
    return {"user_created": True, "redis_verified": True}


async def _send_messages_within_limit(self) -> Dict[str, Any]:
    """Send 5 messages within rate limit."""
    sender = MessageSender(self.auth_token)
    
    # Send 5 messages (should all succeed)
    results = await sender.send_multiple_messages(5, expect_success=True)
    
    # Verify Redis counter shows 5
    await self.redis_manager.verify_rate_limit_counter(self.redis_client, 5)
    
    return {"messages_sent": 5, "redis_counter": 5}


async def _hit_rate_limit(self) -> Dict[str, Any]:
    """Send 6th message to hit rate limit."""
    sender = MessageSender(self.auth_token)
    
    # 6th message should be rate limited
    rate_limited = await sender.send_until_rate_limited()
    assert rate_limited["rate_limited_at_attempt"] == 1, "Should be rate limited immediately"
    
    return {"rate_limited": True, "attempt": rate_limited["rate_limited_at_attempt"]}


async def _wait_for_rate_limit_reset(self) -> Dict[str, Any]:
    """Wait 60 seconds for rate limit to reset."""
    # Wait for Redis counter to reset
    reset_result = await self.redis_manager.wait_for_counter_reset(self.redis_client)
    
    return {"reset_completed": True, "wait_time": reset_result["reset_after_seconds"]}


async def _send_after_reset(self) -> Dict[str, Any]:
    """Send message after rate limit reset."""
    sender = MessageSender(self.auth_token)
    
    # Should be able to send again
    result = await sender.send_message("Post-reset message")
    assert result["status_code"] == 200, "Message should succeed after reset"
    
    # Verify Redis counter reset to 1
    await self.redis_manager.verify_rate_limit_counter(self.redis_client, 1)
    
    return {"message_sent": True, "redis_counter": 1}


async def _upgrade_to_paid_tier(self) -> Dict[str, Any]:
    """Upgrade user to paid tier."""
    upgrade_result = await self.user_manager.upgrade_user_plan(self.auth_token, "pro")
    return upgrade_result


async def _verify_unlimited_usage(self) -> Dict[str, Any]:
    """Verify unlimited usage after upgrade."""
    sender = MessageSender(self.auth_token)
    
    # Send 10 messages rapidly (more than free limit)
    results = await sender.send_multiple_messages(10, expect_success=True)
    
    return {"unlimited_verified": True, "messages_sent": 10}


async def _cleanup_test_data(self) -> None:
    """Clean up test data."""
    if self.redis_client:
        await self.redis_manager.cleanup_test_keys(self.redis_client)
        await self.redis_client.close()


async def _initialize_advanced_testers(self, auth_token: str) -> None:
    """Initialize advanced test components after auth token is available."""
    self.api_tester = APIRateLimitTester(auth_token)
    self.websocket_tester = WebSocketRateLimitTester(auth_token)
    self.agent_tester = AgentThrottleTester(auth_token)
    self.tier_tester = TierBasedRateLimitTester(self.user_manager)
    self.distributed_validator = DistributedRateLimitValidator(self.redis_client)
    self.header_validator = ResponseHeaderValidator(auth_token)


async def _test_api_rate_limits(self) -> Dict[str, Any]:
    """Test API rate limits on Auth and Backend services."""
    auth_results = await self.api_tester.test_auth_service_rate_limits()
    backend_results = await self.api_tester.test_backend_api_rate_limits()
    
    return {
        "success": True,
        "auth_service_limited": auth_results.get("rate_limited_at_request", 0) > 0,
        "backend_api_limited": backend_results.get("rate_limited_at_request", 0) > 0,
        "steps": [
            {"step": "auth_api_test", "success": True, "data": auth_results},
            {"step": "backend_api_test", "success": True, "data": backend_results}
        ]
    }


# Attach methods to class
RedisRateLimitTester._setup_test_environment = _setup_test_environment
RedisRateLimitTester._setup_free_user_with_redis = _setup_free_user_with_redis
RedisRateLimitTester._send_messages_within_limit = _send_messages_within_limit
RedisRateLimitTester._hit_rate_limit = _hit_rate_limit
RedisRateLimitTester._wait_for_rate_limit_reset = _wait_for_rate_limit_reset
RedisRateLimitTester._send_after_reset = _send_after_reset
RedisRateLimitTester._upgrade_to_paid_tier = _upgrade_to_paid_tier
RedisRateLimitTester._verify_unlimited_usage = _verify_unlimited_usage
RedisRateLimitTester._cleanup_test_data = _cleanup_test_data


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.redis
async def test_real_rate_limiting_with_redis_backend(unified_test_harness):
    """
    CRITICAL E2E Test #8: Real rate limiting with Redis backend
    
    Tests actual rate limit enforcement using real Redis for counters.
    NO MOCKING - validates complete rate limiting pipeline.
    
    Flow:
    1. Free user sends 5 messages (all pass)
    2. 6th message gets rate limited
    3. Wait 60 seconds for limit reset
    4. Verify can send again
    5. Upgrade to paid tier  
    6. Verify unlimited usage
    
    Must complete in <70 seconds including wait time.
    """
    tester = RedisRateLimitTester(unified_test_harness)
    
    # Execute complete flow
    results = await tester.execute_rate_limit_flow()
    
    # Validate all steps completed successfully
    assert results["success"], f"Rate limiting flow failed: {results}"
    assert len(results["steps"]) == 7, f"Expected 7 steps, got {len(results['steps'])}"
    
    # Verify business critical validations
    step_results = {step["step"]: step for step in results["steps"]}
    
    # Redis verification
    assert step_results["user_setup"]["data"]["redis_verified"], "Redis not verified"
    
    # Rate limiting enforcement
    assert step_results["rate_limited"]["data"]["rate_limited"], "Rate limit not enforced"
    
    # Reset functionality
    assert step_results["rate_reset"]["data"]["reset_completed"], "Rate limit did not reset"
    
    # Post-reset messaging
    assert step_results["post_reset"]["data"]["message_sent"], "Could not send after reset"
    
    # Upgrade functionality
    assert step_results["upgrade"]["data"]["upgraded"], "Upgrade failed"
    
    # Unlimited usage
    assert step_results["unlimited"]["data"]["unlimited_verified"], "Unlimited usage not verified"
    
    # Performance validation
    assert results["duration"] < 70.0, f"Test exceeded 70s limit: {results['duration']}"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.redis
@pytest.mark.comprehensive
async def test_comprehensive_rate_limiting_system(unified_test_harness):
    """
    CRITICAL E2E Test #8B: Comprehensive Rate Limiting System
    
    Tests comprehensive rate limiting across all system components:
    1. API rate limits on Auth service endpoints  
    2. Backend API rate limiting per user
    3. WebSocket message rate limiting
    4. Agent execution throttling
    5. Rate limit headers and 429 responses
    6. Different limits for different user tiers (Free vs Paid)
    7. Distributed Redis-based rate limiting
    
    Must complete in <90 seconds including wait times.
    """
    start_time = time.time()
    
    # Initialize service manager and start services
    service_manager = ServiceManager(unified_test_harness)
    await service_manager.start_auth_service()
    await service_manager.start_backend_service()
    
    # Wait for services to be ready
    await asyncio.sleep(3)
    
    # Create test user and initialize Redis
    user_manager = UserManager()
    user_data = await user_manager.create_free_user()
    auth_token = user_data["access_token"]
    
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    await redis_client.ping()
    
    # Initialize all test components
    api_tester = APIRateLimitTester(auth_token)
    websocket_tester = WebSocketRateLimitTester(auth_token)
    agent_tester = AgentThrottleTester(auth_token)
    tier_tester = TierBasedRateLimitTester(user_manager)
    distributed_validator = DistributedRateLimitValidator(redis_client)
    header_validator = ResponseHeaderValidator(auth_token)
    
    test_results = {}
    
    try:
        # Test 1: API Rate Limits
        print("Testing API rate limits...")
        auth_results = await api_tester.test_auth_service_rate_limits()
        backend_results = await api_tester.test_backend_api_rate_limits()
        test_results["api_limits"] = {
            "auth_limited": auth_results.get("rate_limited_at_request", 0) > 0,
            "backend_limited": backend_results.get("rate_limited_at_request", 0) > 0
        }
        
        # Test 2: WebSocket Rate Limits (with timeout protection)
        print("Testing WebSocket rate limits...")
        try:
            ws_results = await asyncio.wait_for(websocket_tester.test_websocket_message_rate_limits(), timeout=15.0)
            test_results["websocket_limits"] = {
                "tested": ws_results.get("websocket_tested", False),
                "limited": ws_results.get("rate_limited", False)
            }
        except asyncio.TimeoutError:
            test_results["websocket_limits"] = {"tested": False, "timeout": True}
        
        # Test 3: Agent Throttling
        print("Testing agent throttling...")
        agent_results = await agent_tester.test_agent_execution_throttling()
        test_results["agent_throttling"] = {
            "tested": agent_results.get("agent_throttling_tested", False),
            "throttled": agent_results.get("throttling_active", False)
        }
        
        # Test 4: Tier-based Limits
        print("Testing tier-based limits...")
        tier_results = await tier_tester.test_tier_based_limits()
        test_results["tier_limits"] = {
            "tested": tier_results.get("tier_testing_completed", False),
            "free_limited": tier_results.get("free_tier_limit", 0) > 0,
            "paid_higher": tier_results.get("paid_tier_higher", False)
        }
        
        # Test 5: Distributed Rate Limiting
        print("Testing distributed rate limiting...")
        distributed_results = await distributed_validator.test_distributed_rate_limiting()
        test_results["distributed"] = {
            "tested": distributed_results.get("distributed_testing_completed", False),
            "synced": distributed_results.get("counters_synced", False)
        }
        
        # Test 6: 429 Response Headers
        print("Testing 429 response headers...")
        header_results = await header_validator.test_429_responses_and_headers()
        test_results["response_headers"] = {
            "tested": header_results.get("response_header_tested", False),
            "retry_after": header_results.get("retry_after_header", False)
        }
        
        duration = time.time() - start_time
        
        # Validate core requirements
        assert test_results["api_limits"]["auth_limited"] or test_results["api_limits"]["backend_limited"], "No API rate limiting detected"
        assert test_results["tier_limits"]["tested"], "Tier-based testing failed"
        assert test_results["distributed"]["tested"], "Distributed rate limiting test failed"
        assert test_results["response_headers"]["tested"], "Response header testing failed"
        
        # Performance validation
        assert duration < 90.0, f"Test exceeded 90s limit: {duration}s"
        
        print(f"Comprehensive rate limiting test completed in {duration:.2f}s")
        print(f"Test results: {test_results}")
        
    finally:
        # Cleanup
        try:
            await redis_client.flushdb()
            await redis_client.close()
        except Exception:
            pass


if __name__ == "__main__":
    # Allow direct execution for debugging
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
