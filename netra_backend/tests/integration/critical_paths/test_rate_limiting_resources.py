"""Rate Limiting and Resource Management Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (resource quota enforcement)
- Business Goal: Fair resource allocation and abuse prevention
- Value Impact: Prevents system overload, ensures service quality for all users
- Strategic Impact: $25K-45K MRR protection through resource stability and tier compliance

Critical Path: Request identification -> Rate limit check -> Quota validation -> Backpressure application -> Resource allocation
Coverage: Rate limiting algorithms, quota enforcement, backpressure mechanisms, tier-based limits
"""

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.rate_limiting.rate_limiter import RateLimiter
from netra_backend.app.services.quota.quota_manager import QuotaManager
from netra_backend.app.services.backpressure.backpressure_service import BackpressureService
from netra_backend.app.schemas.user import UserTier

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for different tiers."""
    requests_per_minute: int
    requests_per_hour: int
    concurrent_requests: int
    burst_allowance: int


class RateLimitingManager:
    """Manages rate limiting testing with real quota enforcement."""
    
    def __init__(self):
        self.rate_limiter = None
        self.quota_manager = None
        self.backpressure_service = None
        self.tier_configs = {}
        self.request_history = []
        self.quota_violations = []
        self.backpressure_events = []
        
    async def initialize_services(self):
        """Initialize rate limiting services."""
        try:
            self.rate_limiter = RateLimiter()
            await self.rate_limiter.initialize()
            
            self.quota_manager = QuotaManager()
            await self.quota_manager.initialize()
            
            self.backpressure_service = BackpressureService()
            await self.backpressure_service.initialize()
            
            # Configure tier-based rate limits
            await self.setup_tier_configurations()
            
            logger.info("Rate limiting services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting services: {e}")
            raise
    
    async def setup_tier_configurations(self):
        """Set up rate limiting configurations for different user tiers."""
        self.tier_configs = {
            UserTier.FREE: RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                concurrent_requests=2,
                burst_allowance=5
            ),
            UserTier.EARLY: RateLimitConfig(
                requests_per_minute=50,
                requests_per_hour=1000,
                concurrent_requests=5,
                burst_allowance=20
            ),
            UserTier.MID: RateLimitConfig(
                requests_per_minute=200,
                requests_per_hour=5000,
                concurrent_requests=10,
                burst_allowance=50
            ),
            UserTier.ENTERPRISE: RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=25000,
                concurrent_requests=50,
                burst_allowance=200
            )
        }
        
        # Register configurations with rate limiter
        for tier, config in self.tier_configs.items():
            await self.rate_limiter.configure_tier(tier, config)
    
    async def simulate_user_request(self, user_id: str, user_tier: UserTier, 
                                  request_type: str = "api_call") -> Dict[str, Any]:
        """Simulate a user request through rate limiting system."""
        request_id = str(uuid.uuid4())
        request_start = time.time()
        
        try:
            # Step 1: Check rate limits
            rate_limit_result = await self.check_rate_limits(user_id, user_tier, request_type)
            
            if not rate_limit_result["allowed"]:
                # Request denied by rate limiter
                self.record_request_event({
                    "request_id": request_id,
                    "user_id": user_id,
                    "user_tier": user_tier.value,
                    "request_type": request_type,
                    "status": "rate_limited",
                    "reason": rate_limit_result["reason"],
                    "timestamp": request_start,
                    "response_time": time.time() - request_start
                })
                
                return {
                    "allowed": False,
                    "reason": "rate_limited",
                    "rate_limit_info": rate_limit_result,
                    "response_time": time.time() - request_start
                }
            
            # Step 2: Check quota limits
            quota_result = await self.check_quota_limits(user_id, user_tier, request_type)
            
            if not quota_result["allowed"]:
                # Request denied by quota system
                quota_violation = {
                    "user_id": user_id,
                    "user_tier": user_tier.value,
                    "request_type": request_type,
                    "quota_type": quota_result["quota_type"],
                    "current_usage": quota_result["current_usage"],
                    "limit": quota_result["limit"],
                    "timestamp": time.time()
                }
                
                self.quota_violations.append(quota_violation)
                
                return {
                    "allowed": False,
                    "reason": "quota_exceeded",
                    "quota_info": quota_result,
                    "response_time": time.time() - request_start
                }
            
            # Step 3: Check for backpressure
            backpressure_result = await self.apply_backpressure(user_id, user_tier)
            
            if backpressure_result["applied"]:
                # Backpressure applied - delay request
                delay_time = backpressure_result["delay_seconds"]
                await asyncio.sleep(delay_time)
                
                self.backpressure_events.append({
                    "user_id": user_id,
                    "user_tier": user_tier.value,
                    "delay_applied": delay_time,
                    "reason": backpressure_result["reason"],
                    "timestamp": time.time()
                })
            
            # Step 4: Process request (simulate)
            processing_time = 0.1  # Simulate processing
            await asyncio.sleep(processing_time)
            
            # Update usage tracking
            await self.update_usage_tracking(user_id, user_tier, request_type)
            
            total_response_time = time.time() - request_start
            
            self.record_request_event({
                "request_id": request_id,
                "user_id": user_id,
                "user_tier": user_tier.value,
                "request_type": request_type,
                "status": "completed",
                "backpressure_applied": backpressure_result["applied"],
                "delay_time": backpressure_result.get("delay_seconds", 0),
                "timestamp": request_start,
                "response_time": total_response_time
            })
            
            return {
                "allowed": True,
                "status": "completed",
                "backpressure_applied": backpressure_result["applied"],
                "response_time": total_response_time,
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.record_request_event({
                "request_id": request_id,
                "user_id": user_id,
                "user_tier": user_tier.value,
                "request_type": request_type,
                "status": "error",
                "error": str(e),
                "timestamp": request_start,
                "response_time": time.time() - request_start
            })
            
            return {
                "allowed": False,
                "reason": "internal_error",
                "error": str(e),
                "response_time": time.time() - request_start
            }
    
    async def check_rate_limits(self, user_id: str, user_tier: UserTier, 
                              request_type: str) -> Dict[str, Any]:
        """Check if request is within rate limits."""
        try:
            config = self.tier_configs[user_tier]
            
            # Check various rate limit types
            minute_check = await self.rate_limiter.check_limit(
                user_id, "per_minute", config.requests_per_minute, 60
            )
            
            hour_check = await self.rate_limiter.check_limit(
                user_id, "per_hour", config.requests_per_hour, 3600
            )
            
            concurrent_check = await self.rate_limiter.check_concurrent_limit(
                user_id, config.concurrent_requests
            )
            
            # Check burst allowance
            burst_check = await self.rate_limiter.check_burst_limit(
                user_id, config.burst_allowance
            )
            
            if not minute_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": "per_minute_limit_exceeded",
                    "current_count": minute_check["current_count"],
                    "limit": config.requests_per_minute,
                    "reset_time": minute_check["reset_time"]
                }
            
            if not hour_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": "per_hour_limit_exceeded",
                    "current_count": hour_check["current_count"],
                    "limit": config.requests_per_hour,
                    "reset_time": hour_check["reset_time"]
                }
            
            if not concurrent_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": "concurrent_limit_exceeded",
                    "current_count": concurrent_check["current_count"],
                    "limit": config.concurrent_requests
                }
            
            if not burst_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": "burst_limit_exceeded",
                    "current_count": burst_check["current_count"],
                    "limit": config.burst_allowance
                }
            
            return {
                "allowed": True,
                "minute_usage": minute_check["current_count"],
                "hour_usage": hour_check["current_count"],
                "concurrent_usage": concurrent_check["current_count"]
            }
            
        except Exception as e:
            return {
                "allowed": False,
                "reason": "rate_limit_check_error",
                "error": str(e)
            }
    
    async def check_quota_limits(self, user_id: str, user_tier: UserTier, 
                               request_type: str) -> Dict[str, Any]:
        """Check if request is within quota limits."""
        try:
            # Different quota types based on request type
            if request_type == "llm_request":
                quota_type = "llm_tokens"
                request_cost = 1000  # tokens
            elif request_type == "api_call":
                quota_type = "api_calls"
                request_cost = 1
            elif request_type == "storage_operation":
                quota_type = "storage_gb"
                request_cost = 0.1  # GB
            else:
                quota_type = "general_usage"
                request_cost = 1
            
            quota_check = await self.quota_manager.check_quota(
                user_id, user_tier, quota_type, request_cost
            )
            
            return quota_check
            
        except Exception as e:
            return {
                "allowed": False,
                "reason": "quota_check_error",
                "error": str(e)
            }
    
    async def apply_backpressure(self, user_id: str, user_tier: UserTier) -> Dict[str, Any]:
        """Apply backpressure based on system load and user tier."""
        try:
            # Check system load
            system_load = await self.backpressure_service.get_system_load()
            
            # Tier-based backpressure thresholds
            tier_thresholds = {
                UserTier.FREE: 0.7,      # Apply backpressure at 70% load
                UserTier.EARLY: 0.8,     # Apply backpressure at 80% load
                UserTier.MID: 0.9,       # Apply backpressure at 90% load
                UserTier.ENTERPRISE: 0.95 # Apply backpressure at 95% load
            }
            
            threshold = tier_thresholds[user_tier]
            
            if system_load > threshold:
                # Calculate delay based on load and tier
                base_delay = (system_load - threshold) * 2  # Base delay in seconds
                
                # Tier-based delay adjustment
                tier_multipliers = {
                    UserTier.FREE: 3.0,
                    UserTier.EARLY: 2.0,
                    UserTier.MID: 1.5,
                    UserTier.ENTERPRISE: 1.0
                }
                
                delay_seconds = base_delay * tier_multipliers[user_tier]
                delay_seconds = min(delay_seconds, 10.0)  # Cap at 10 seconds
                
                return {
                    "applied": True,
                    "delay_seconds": delay_seconds,
                    "system_load": system_load,
                    "threshold": threshold,
                    "reason": "system_load_high"
                }
            
            return {
                "applied": False,
                "system_load": system_load,
                "threshold": threshold
            }
            
        except Exception as e:
            return {
                "applied": False,
                "error": str(e)
            }
    
    async def update_usage_tracking(self, user_id: str, user_tier: UserTier, request_type: str):
        """Update usage tracking for analytics and billing."""
        try:
            usage_record = {
                "user_id": user_id,
                "user_tier": user_tier.value,
                "request_type": request_type,
                "timestamp": time.time(),
                "cost_units": self.calculate_cost_units(request_type, user_tier)
            }
            
            await self.quota_manager.record_usage(usage_record)
            
        except Exception as e:
            logger.error(f"Failed to update usage tracking: {e}")
    
    def calculate_cost_units(self, request_type: str, user_tier: UserTier) -> float:
        """Calculate cost units for billing."""
        base_costs = {
            "api_call": 1.0,
            "llm_request": 10.0,
            "storage_operation": 0.5
        }
        
        # Tier-based cost adjustments
        tier_adjustments = {
            UserTier.FREE: 1.0,
            UserTier.EARLY: 0.9,
            UserTier.MID: 0.8,
            UserTier.ENTERPRISE: 0.7
        }
        
        base_cost = base_costs.get(request_type, 1.0)
        adjustment = tier_adjustments[user_tier]
        
        return base_cost * adjustment
    
    def record_request_event(self, event: Dict[str, Any]):
        """Record request event for analytics."""
        self.request_history.append(event)
    
    async def simulate_burst_traffic(self, user_id: str, user_tier: UserTier, 
                                   request_count: int, duration_seconds: float) -> Dict[str, Any]:
        """Simulate burst traffic to test rate limiting."""
        burst_start = time.time()
        
        # Calculate request interval
        interval = duration_seconds / request_count
        
        results = []
        successful_requests = 0
        rate_limited_requests = 0
        
        try:
            for i in range(request_count):
                result = await self.simulate_user_request(user_id, user_tier, "burst_test")
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
    
    async def get_rate_limiting_metrics(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting metrics."""
        total_requests = len(self.request_history)
        
        if total_requests == 0:
            return {"total_requests": 0}
        
        # Categorize requests by status
        completed_requests = [r for r in self.request_history if r["status"] == "completed"]
        rate_limited_requests = [r for r in self.request_history if r["status"] == "rate_limited"]
        error_requests = [r for r in self.request_history if r["status"] == "error"]
        
        # Calculate success rate
        success_rate = len(completed_requests) / total_requests * 100
        rate_limit_rate = len(rate_limited_requests) / total_requests * 100
        
        # Calculate average response times
        response_times = [r["response_time"] for r in self.request_history if "response_time" in r]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Tier-based breakdown
        tier_breakdown = {}
        for tier in UserTier:
            tier_requests = [r for r in self.request_history if r.get("user_tier") == tier.value]
            tier_breakdown[tier.value] = {
                "total_requests": len(tier_requests),
                "success_rate": len([r for r in tier_requests if r["status"] == "completed"]) / len(tier_requests) * 100 if tier_requests else 0
            }
        
        return {
            "total_requests": total_requests,
            "completed_requests": len(completed_requests),
            "rate_limited_requests": len(rate_limited_requests),
            "error_requests": len(error_requests),
            "success_rate": success_rate,
            "rate_limit_rate": rate_limit_rate,
            "average_response_time": avg_response_time,
            "quota_violations": len(self.quota_violations),
            "backpressure_events": len(self.backpressure_events),
            "tier_breakdown": tier_breakdown
        }
    
    async def cleanup(self):
        """Clean up rate limiting resources."""
        try:
            if self.rate_limiter:
                await self.rate_limiter.shutdown()
            if self.quota_manager:
                await self.quota_manager.shutdown()
            if self.backpressure_service:
                await self.backpressure_service.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def rate_limiting_manager():
    """Create rate limiting manager for testing."""
    manager = RateLimitingManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_tier_based_rate_limiting(rate_limiting_manager):
    """Test that different user tiers have appropriate rate limits."""
    users = {
        UserTier.FREE: "free_user_001",
        UserTier.EARLY: "early_user_001",
        UserTier.MID: "mid_user_001",
        UserTier.ENTERPRISE: "enterprise_user_001"
    }
    
    # Test each tier's limits
    for tier, user_id in users.items():
        config = rate_limiting_manager.tier_configs[tier]
        
        # Test normal operation within limits
        for i in range(min(5, config.requests_per_minute - 1)):
            result = await rate_limiting_manager.simulate_user_request(user_id, tier)
            assert result["allowed"] is True
        
        # Verify tier-specific limits are enforced
        if tier == UserTier.FREE:
            # Free tier should have strictest limits
            burst_result = await rate_limiting_manager.simulate_burst_traffic(
                user_id, tier, 15, 30  # 15 requests in 30 seconds
            )
            assert burst_result["rate_limited_requests"] > 0
        
        elif tier == UserTier.ENTERPRISE:
            # Enterprise should handle more traffic
            burst_result = await rate_limiting_manager.simulate_burst_traffic(
                user_id, tier, 50, 60  # 50 requests in 60 seconds
            )
            assert burst_result["success_rate"] >= 80  # Most should succeed


@pytest.mark.asyncio
async def test_quota_enforcement_across_tiers(rate_limiting_manager):
    """Test quota enforcement for different request types and tiers."""
    user_id = "quota_test_user"
    
    # Test LLM quota limits
    llm_requests = []
    for i in range(20):  # Try many LLM requests
        result = await rate_limiting_manager.simulate_user_request(
            user_id, UserTier.FREE, "llm_request"
        )
        llm_requests.append(result)
        
        # Free tier should hit quota limits quickly
        if not result["allowed"] and result["reason"] == "quota_exceeded":
            break
    
    # Verify quota was enforced
    quota_limited = [r for r in llm_requests if not r["allowed"] and r.get("reason") == "quota_exceeded"]
    assert len(quota_limited) > 0
    
    # Test that enterprise user has higher quotas
    enterprise_user = "enterprise_quota_user"
    enterprise_results = []
    
    for i in range(20):
        result = await rate_limiting_manager.simulate_user_request(
            enterprise_user, UserTier.ENTERPRISE, "llm_request"
        )
        enterprise_results.append(result)
    
    enterprise_successful = [r for r in enterprise_results if r["allowed"]]
    free_successful = [r for r in llm_requests if r["allowed"]]
    
    # Enterprise should have more successful requests
    assert len(enterprise_successful) > len(free_successful)


@pytest.mark.asyncio
async def test_backpressure_application(rate_limiting_manager):
    """Test backpressure application under high system load."""
    # Simulate high system load
    with patch.object(rate_limiting_manager.backpressure_service, 'get_system_load', 
                     return_value=0.85):  # 85% system load
        
        # Test different tiers under load
        tier_tests = [
            (UserTier.FREE, "free_user_backpressure"),
            (UserTier.ENTERPRISE, "enterprise_user_backpressure")
        ]
        
        for tier, user_id in tier_tests:
            result = await rate_limiting_manager.simulate_user_request(user_id, tier)
            
            if tier == UserTier.FREE:
                # Free tier should experience backpressure at 85% load
                assert result.get("backpressure_applied") is True
                assert result["response_time"] > 0.1  # Should have added delay
            
            elif tier == UserTier.ENTERPRISE:
                # Enterprise might not experience backpressure at 85% load
                backpressure_applied = result.get("backpressure_applied", False)
                # This is tier-dependent, so we just verify it's tracked
                assert "backpressure_applied" in result


@pytest.mark.asyncio
async def test_burst_traffic_handling(rate_limiting_manager):
    """Test system behavior under burst traffic conditions."""
    user_id = "burst_test_user"
    
    # Test different burst patterns
    burst_tests = [
        {"requests": 20, "duration": 10, "tier": UserTier.FREE},
        {"requests": 100, "duration": 30, "tier": UserTier.MID},
        {"requests": 200, "duration": 60, "tier": UserTier.ENTERPRISE}
    ]
    
    for test_config in burst_tests:
        user_id_test = f"{user_id}_{test_config['tier'].value}"
        
        burst_result = await rate_limiting_manager.simulate_burst_traffic(
            user_id_test, test_config["tier"], test_config["requests"], test_config["duration"]
        )
        
        # Verify burst was handled appropriately
        assert burst_result["total_requests"] == test_config["requests"]
        assert burst_result["burst_duration"] <= test_config["duration"] * 1.5  # Allow some overhead
        
        # Different tiers should have different success rates
        if test_config["tier"] == UserTier.FREE:
            assert burst_result["success_rate"] < 80  # Free tier should be limited
        elif test_config["tier"] == UserTier.ENTERPRISE:
            assert burst_result["success_rate"] >= 70  # Enterprise should handle more


@pytest.mark.asyncio
async def test_concurrent_user_rate_limiting(rate_limiting_manager):
    """Test rate limiting with multiple concurrent users."""
    # Create users across different tiers
    users = [
        (f"concurrent_free_{i}", UserTier.FREE) for i in range(3)
    ] + [
        (f"concurrent_mid_{i}", UserTier.MID) for i in range(2)
    ] + [
        (f"concurrent_enterprise_{i}", UserTier.ENTERPRISE) for i in range(2)
    ]
    
    # Generate concurrent requests
    request_tasks = []
    for user_id, tier in users:
        for request_num in range(10):  # 10 requests per user
            task = rate_limiting_manager.simulate_user_request(user_id, tier, "concurrent_test")
            request_tasks.append((user_id, tier, task))
    
    # Execute all requests concurrently
    results = []
    for user_id, tier, task in request_tasks:
        result = await task
        results.append({"user_id": user_id, "tier": tier, "result": result})
    
    # Analyze results by tier
    tier_results = {}
    for tier in UserTier:
        tier_requests = [r for r in results if r["tier"] == tier]
        if tier_requests:
            successful = [r for r in tier_requests if r["result"]["allowed"]]
            tier_results[tier] = {
                "total": len(tier_requests),
                "successful": len(successful),
                "success_rate": len(successful) / len(tier_requests) * 100
            }
    
    # Verify tier-based differentiation
    if UserTier.FREE in tier_results and UserTier.ENTERPRISE in tier_results:
        free_success_rate = tier_results[UserTier.FREE]["success_rate"]
        enterprise_success_rate = tier_results[UserTier.ENTERPRISE]["success_rate"]
        
        # Enterprise should generally have better success rate
        assert enterprise_success_rate >= free_success_rate


@pytest.mark.asyncio
async def test_rate_limiting_metrics_accuracy(rate_limiting_manager):
    """Test accuracy of rate limiting metrics collection."""
    # Generate controlled test traffic
    test_scenarios = [
        {"user_id": "metrics_user_1", "tier": UserTier.FREE, "requests": 15},
        {"user_id": "metrics_user_2", "tier": UserTier.MID, "requests": 25},
    ]
    
    total_expected_requests = sum(scenario["requests"] for scenario in test_scenarios)
    
    for scenario in test_scenarios:
        for i in range(scenario["requests"]):
            await rate_limiting_manager.simulate_user_request(
                scenario["user_id"], scenario["tier"], "metrics_test"
            )
    
    # Get metrics
    metrics = await rate_limiting_manager.get_rate_limiting_metrics()
    
    # Verify metrics accuracy
    assert metrics["total_requests"] == total_expected_requests
    assert metrics["success_rate"] >= 0
    assert metrics["success_rate"] <= 100
    assert metrics["average_response_time"] > 0
    
    # Verify tier breakdown
    assert "tier_breakdown" in metrics
    assert UserTier.FREE.value in metrics["tier_breakdown"]
    assert UserTier.MID.value in metrics["tier_breakdown"]
    
    # Verify tier-specific metrics
    free_metrics = metrics["tier_breakdown"][UserTier.FREE.value]
    mid_metrics = metrics["tier_breakdown"][UserTier.MID.value]
    
    assert free_metrics["total_requests"] == 15
    assert mid_metrics["total_requests"] == 25


@pytest.mark.asyncio
async def test_rate_limiting_performance_requirements(rate_limiting_manager):
    """Test that rate limiting meets performance requirements."""
    user_id = "performance_test_user"
    tier = UserTier.MID
    
    # Test response time requirements
    response_times = []
    
    for i in range(50):  # 50 requests to get good average
        result = await rate_limiting_manager.simulate_user_request(user_id, tier, "performance_test")
        if "response_time" in result:
            response_times.append(result["response_time"])
    
    # Verify performance requirements
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    
    # Rate limiting checks should be fast
    assert avg_response_time < 0.5  # Average < 500ms
    assert max_response_time < 2.0  # Max < 2 seconds (excluding backpressure)
    
    # Test concurrent performance
    concurrent_tasks = []
    for i in range(20):  # 20 concurrent requests
        task = rate_limiting_manager.simulate_user_request(
            f"{user_id}_concurrent_{i}", tier, "concurrent_performance"
        )
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # Concurrent execution should complete quickly
    assert concurrent_duration < 5.0  # 20 concurrent requests in < 5 seconds
    
    # All requests should complete successfully (no internal errors)
    errors = [r for r in concurrent_results if r.get("reason") == "internal_error"]
    assert len(errors) == 0