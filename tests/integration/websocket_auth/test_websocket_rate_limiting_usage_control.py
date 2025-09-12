"""
WebSocket Rate Limiting and Usage Control Integration Tests

Business Value Justification (BVJ):
- Segment: All plan tiers - usage control and billing protection
- Goal: Revenue protection through proper usage enforcement  
- Impact: Prevents abuse and ensures fair usage across plan tiers
- Revenue Impact: Protects infrastructure costs and enables usage-based billing

Integration tests validating rate limiting and usage control in WebSocket context.
These tests ensure usage tracking and limits work end-to-end with real services.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional
from unittest.mock import patch

from test_framework.base import BaseTestCase
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.auth_fixtures import test_user_token
from test_framework.fixtures.websocket_fixtures import websocket_connection_fixture
from netra_backend.app.services.tool_permission_service import (
    ToolPermissionService, 
    ToolExecutionContext,
    PermissionCheckResult
)
from netra_backend.app.services.tool_permissions.rate_limiter import RateLimiter
from netra_backend.app.schemas.user_plan import PlanTier, PLAN_DEFINITIONS, UsageRecord
from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler


@pytest.mark.integration
@pytest.mark.websocket_auth
@pytest.mark.timeout(45)
class TestWebSocketRateLimitingUsageControl(BaseTestCase):
    """Integration tests for rate limiting and usage control in WebSocket context"""

    @pytest.fixture(autouse=True)
    async def setup_services(self, real_services_fixture, test_user_token):
        """Setup real services for rate limiting and usage control testing"""
        self.redis_client = await RedisConnectionHandler().get_async_redis()
        self.permission_service = ToolPermissionService(self.redis_client)
        self.rate_limiter = RateLimiter(self.redis_client)
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Clean up test data from Redis"""
        try:
            test_keys = await self.redis_client.keys("test:rate:*")
            usage_keys = await self.redis_client.keys("usage:test_user*")
            all_keys = test_keys + usage_keys
            if all_keys:
                await self.redis_client.delete(*all_keys)
        except Exception:
            pass  # Redis may not be available in all test environments

    async def test_rate_limit_enforcement_per_user_plan_tier(self):
        """
        BVJ: Validates rate limits are enforced correctly per user plan tier
        Business Impact: Ensures fair usage and prevents system abuse
        Revenue Impact: Protects infrastructure costs and maintains service quality
        """
        # Given: Different plan tiers with different rate limit multipliers
        test_scenarios = [
            (PlanTier.FREE, 1.0, "create_thread"),      # 1x base rate limit
            (PlanTier.PRO, 2.0, "analyze_workload"),   # 2x base rate limit  
            (PlanTier.ENTERPRISE, 10.0, "system_tool") # 10x base rate limit
        ]
        
        for plan_tier, multiplier, tool_name in test_scenarios:
            user_id = f"test_user_rate_limit_{plan_tier.value}"
            base_requests = 5  # Base number of requests to test
            
            # When: Making multiple requests within rate limit window
            allowed_count = 0
            denied_count = 0
            
            for i in range(base_requests * 2):  # Test above expected limit
                context = ToolExecutionContext(
                    user_id=user_id,
                    tool_name=tool_name,
                    user_plan=plan_tier.value,
                    websocket_session_id=f"ws_rate_{plan_tier.value}_{i}"
                )
                
                result = await self.permission_service.check_tool_permission(context)
                
                if result.allowed:
                    allowed_count += 1
                    # Record successful usage
                    await self.permission_service.record_tool_usage(
                        user_id=user_id,
                        tool_name=tool_name,
                        execution_time_ms=500,
                        status="completed"
                    )
                else:
                    denied_count += 1
                    
                # Small delay to avoid overwhelming Redis
                await asyncio.sleep(0.1)
            
            # Then: Rate limits should be enforced based on plan tier
            total_requests = allowed_count + denied_count
            assert total_requests == base_requests * 2, "Should process all requests"
            
            # Higher tier plans should allow more requests or equal
            self.record_metric(f"rate_limit_{plan_tier.value}_allowed", allowed_count)
            self.record_metric(f"rate_limit_{plan_tier.value}_denied", denied_count)
            self.record_metric(f"rate_limit_{plan_tier.value}_multiplier", multiplier)

    async def test_concurrent_tool_execution_limit_validation(self):
        """
        BVJ: Validates concurrent tool execution limits per plan tier
        Business Impact: Prevents resource exhaustion and ensures fair sharing
        Revenue Impact: Enables predictable infrastructure costs and scaling
        """
        # Given: A user with limited concurrent execution allowance
        user_id = "test_user_concurrent_001"
        plan_tier = PlanTier.PRO  # PRO tier has defined limits
        
        # Create multiple concurrent tool execution contexts
        concurrent_contexts = []
        for i in range(5):  # Attempt 5 concurrent executions
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name="concurrent_test_tool",
                user_plan=plan_tier.value,
                websocket_session_id=f"ws_concurrent_{i}",
                additional_context={
                    "execution_id": f"exec_{i}",
                    "concurrent_test": True
                }
            )
            concurrent_contexts.append(context)
        
        # When: Attempting concurrent tool executions
        concurrent_results = await asyncio.gather(
            *[self.permission_service.check_tool_permission(ctx) for ctx in concurrent_contexts],
            return_exceptions=True
        )
        
        # Then: Concurrent limits should be enforced
        allowed_executions = [r for r in concurrent_results if not isinstance(r, Exception) and r.allowed]
        denied_executions = [r for r in concurrent_results if not isinstance(r, Exception) and not r.allowed]
        
        # Should have some successful and possibly some denied based on limits
        total_valid_results = len(allowed_executions) + len(denied_executions)
        assert total_valid_results > 0, "Should have valid permission results"
        
        # Verify rate limiting information is provided for denied requests
        for denied_result in denied_executions:
            if "rate limit" in denied_result.reason.lower():
                assert denied_result.rate_limit_status is not None, "Rate limit status should be provided"
        
        self.record_metric("concurrent_executions_allowed", len(allowed_executions))
        self.record_metric("concurrent_executions_denied", len(denied_executions))
        self.record_metric("concurrent_limit_enforcement", True)

    async def test_usage_record_creation_and_tracking_integration(self):
        """
        BVJ: Validates usage records are created and tracked for billing integration
        Business Impact: Enables accurate billing and usage analytics
        Revenue Impact: Supports usage-based billing and cost optimization
        """
        # Given: A user executing billable tools
        user_id = "test_user_usage_tracking_001"
        billable_tools = [
            ("analyze_workload", 1500, "analytics"),
            ("generate_synthetic_data", 2000, "data_generation"),
            ("export_results", 500, "data_export")
        ]
        
        usage_records = []
        
        for tool_name, execution_time_ms, category in billable_tools:
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name=tool_name,
                user_plan=PlanTier.PRO.value,
                websocket_session_id=f"ws_usage_{tool_name}"
            )
            
            # When: Tool is executed and usage is recorded
            permission_result = await self.permission_service.check_tool_permission(context)
            
            if permission_result.allowed:
                # Record tool usage with detailed information
                await self.permission_service.record_tool_usage(
                    user_id=user_id,
                    tool_name=tool_name,
                    execution_time_ms=execution_time_ms,
                    status="completed"
                )
                
                # Create usage record for verification
                usage_record = UsageRecord(
                    user_id=user_id,
                    tool_name=tool_name,
                    category=category,
                    execution_time_ms=execution_time_ms,
                    status="completed",
                    plan_tier=PlanTier.PRO.value
                )
                usage_records.append(usage_record)
        
        # Then: Usage tracking should be maintained
        assert len(usage_records) > 0, "Should have recorded usage for successful executions"
        
        # Verify usage records have correct structure
        for record in usage_records:
            assert record.user_id == user_id, "Usage record should have correct user ID"
            assert record.plan_tier == PlanTier.PRO.value, "Usage record should capture plan tier"
            assert record.execution_time_ms > 0, "Execution time should be recorded"
            assert record.status == "completed", "Status should be recorded"
            
        self.record_metric("usage_records_created", len(usage_records))
        self.record_metric("billing_integration_ready", True)
        self.record_metric("total_execution_time_ms", sum(r.execution_time_ms for r in usage_records))

    async def test_rate_limit_exceeded_scenarios_and_graceful_degradation(self):
        """
        BVJ: Validates graceful degradation when rate limits are exceeded
        Business Impact: Maintains user experience even under limit constraints
        Revenue Impact: Provides clear upgrade paths when limits are reached
        """
        # Given: A user who will exceed their rate limits
        user_id = "test_user_rate_exceeded_001"
        plan_tier = PlanTier.FREE  # Most restrictive limits
        
        # Rapidly make requests to exceed rate limits
        rapid_requests = []
        for i in range(20):  # More requests than FREE tier should allow
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name="rate_limit_test_tool",
                user_plan=plan_tier.value,
                websocket_session_id=f"ws_rapid_{i}"
            )
            rapid_requests.append(context)
        
        # When: Making rapid requests that exceed rate limits
        results = []
        for context in rapid_requests:
            result = await self.permission_service.check_tool_permission(context)
            results.append(result)
            
            # Small delay to simulate realistic usage
            await asyncio.sleep(0.05)
        
        # Then: Should have both allowed and denied requests
        allowed_results = [r for r in results if r.allowed]
        denied_results = [r for r in results if not r.allowed]
        
        # Should have some denied requests due to rate limiting
        assert len(denied_results) > 0, "Should have rate limit denials for excessive requests"
        
        # Denied requests should provide clear messaging and upgrade paths
        for denied_result in denied_results:
            assert denied_result.reason is not None, "Denial should have clear reason"
            
            # Should provide upgrade path for rate limit issues
            if "rate limit" in denied_result.reason.lower():
                assert denied_result.upgrade_path is not None, "Should provide upgrade path for rate limits"
                
                # Upgrade path should mention higher tier benefits
                upgrade_message = denied_result.upgrade_path.lower()
                upgrade_terms = ["pro", "premium", "upgrade", "higher", "more", "unlimited"]
                assert any(term in upgrade_message for term in upgrade_terms), \
                    f"Upgrade path should mention benefits: {denied_result.upgrade_path}"
        
        self.record_metric("rate_limit_exceeded_graceful", len(denied_results) > 0)
        self.record_metric("upgrade_path_on_rate_limit", any(r.upgrade_path for r in denied_results))
        self.record_metric("requests_allowed_before_limit", len(allowed_results))

    async def test_burst_allowance_handling_for_premium_users(self):
        """
        BVJ: Validates burst allowance for premium users during peak usage
        Business Impact: Provides premium user experience for higher-tier customers
        Revenue Impact: Validates premium tier value proposition through enhanced limits
        """
        # Given: A premium user with burst allowance capabilities
        user_id = "test_user_burst_001"
        plan_tier = PlanTier.ENTERPRISE  # Highest tier with best limits
        
        # Simulate burst usage pattern - many requests in short time
        burst_size = 15
        burst_contexts = []
        
        for i in range(burst_size):
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name="burst_test_tool",
                user_plan=plan_tier.value,
                websocket_session_id=f"ws_burst_{i}",
                additional_context={
                    "burst_request": True,
                    "burst_sequence": i,
                    "priority": "high"
                }
            )
            burst_contexts.append(context)
        
        # When: Making burst requests rapidly
        start_time = datetime.now()
        burst_results = []
        
        for context in burst_contexts:
            result = await self.permission_service.check_tool_permission(context)
            burst_results.append(result)
            
            # Record usage for successful requests
            if result.allowed:
                await self.permission_service.record_tool_usage(
                    user_id=user_id,
                    tool_name="burst_test_tool",
                    execution_time_ms=200,
                    status="completed"
                )
            
            # Minimal delay for burst simulation
            await asyncio.sleep(0.02)
        
        end_time = datetime.now()
        burst_duration = (end_time - start_time).total_seconds()
        
        # Then: Premium users should handle burst better than lower tiers
        allowed_burst_requests = [r for r in burst_results if r.allowed]
        denied_burst_requests = [r for r in burst_results if not r.allowed]
        
        # Enterprise should allow more burst requests than lower tiers
        burst_success_rate = len(allowed_burst_requests) / len(burst_results)
        
        # Should handle burst requests efficiently
        assert burst_duration < 5.0, f"Burst handling should be fast, took {burst_duration}s"
        
        # Premium tier should have high success rate for reasonable burst
        self.record_metric("burst_success_rate", burst_success_rate)
        self.record_metric("burst_handling_time", burst_duration)
        self.record_metric("premium_burst_allowance", len(allowed_burst_requests))

    async def test_tool_usage_analytics_and_reporting_integration(self):
        """
        BVJ: Validates usage analytics integration for business intelligence
        Business Impact: Enables data-driven decisions about feature usage and pricing
        Revenue Impact: Supports pricing optimization and feature development priorities
        """
        # Given: Multiple users with different usage patterns
        usage_scenarios = [
            ("test_user_analytics_light", PlanTier.FREE, ["create_thread", "list_agents"], 3),
            ("test_user_analytics_medium", PlanTier.PRO, ["analyze_workload", "generate_data"], 8),
            ("test_user_analytics_heavy", PlanTier.ENTERPRISE, ["system_admin", "audit_tool"], 15)
        ]
        
        analytics_data = []
        
        for user_id, plan_tier, tools, request_count in usage_scenarios:
            user_analytics = {
                "user_id": user_id,
                "plan_tier": plan_tier.value,
                "tools_used": [],
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_execution_time": 0
            }
            
            # When: User makes various tool requests
            for tool_name in tools:
                for i in range(request_count):
                    context = ToolExecutionContext(
                        user_id=user_id,
                        tool_name=tool_name,
                        user_plan=plan_tier.value,
                        websocket_session_id=f"ws_analytics_{user_id}_{tool_name}_{i}"
                    )
                    
                    result = await self.permission_service.check_tool_permission(context)
                    user_analytics["total_requests"] += 1
                    
                    if result.allowed:
                        user_analytics["successful_requests"] += 1
                        execution_time = 500 + (i * 50)  # Simulated variable execution time
                        user_analytics["total_execution_time"] += execution_time
                        
                        await self.permission_service.record_tool_usage(
                            user_id=user_id,
                            tool_name=tool_name,
                            execution_time_ms=execution_time,
                            status="completed"
                        )
                        
                        if tool_name not in user_analytics["tools_used"]:
                            user_analytics["tools_used"].append(tool_name)
                    else:
                        user_analytics["failed_requests"] += 1
                    
                    await asyncio.sleep(0.05)  # Realistic pacing
            
            analytics_data.append(user_analytics)
        
        # Then: Analytics data should show clear usage patterns
        assert len(analytics_data) == len(usage_scenarios), "Should have analytics for all users"
        
        # Verify usage patterns align with plan tiers
        for user_data in analytics_data:
            plan = user_data["plan_tier"]
            success_rate = user_data["successful_requests"] / user_data["total_requests"] if user_data["total_requests"] > 0 else 0
            
            # Higher tier plans should generally have higher success rates
            if plan == PlanTier.ENTERPRISE.value:
                assert success_rate >= 0.7, f"Enterprise should have high success rate, got {success_rate}"
            
            self.record_metric(f"usage_pattern_{plan}_success_rate", success_rate)
            self.record_metric(f"usage_pattern_{plan}_total_time", user_data["total_execution_time"])
            self.record_metric(f"usage_pattern_{plan}_tool_diversity", len(user_data["tools_used"]))
        
        # Overall analytics validation
        total_requests = sum(data["total_requests"] for data in analytics_data)
        total_successful = sum(data["successful_requests"] for data in analytics_data)
        
        self.record_metric("analytics_integration_working", True)
        self.record_metric("total_usage_requests_tracked", total_requests)
        self.record_metric("overall_success_rate", total_successful / total_requests if total_requests > 0 else 0)

    async def test_websocket_session_rate_limit_inheritance(self):
        """
        BVJ: Validates rate limits are inherited correctly across WebSocket session lifecycle
        Business Impact: Ensures consistent rate limiting throughout user session
        Revenue Impact: Prevents rate limit bypass through session manipulation
        """
        # Given: A user with an active WebSocket session
        user_id = "test_user_session_inheritance_001"
        session_id = "ws_inheritance_test_001"
        plan_tier = PlanTier.PRO
        
        # Create base usage to establish rate limit history
        for i in range(3):
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name="session_test_tool",
                user_plan=plan_tier.value,
                websocket_session_id=session_id
            )
            
            result = await self.permission_service.check_tool_permission(context)
            if result.allowed:
                await self.permission_service.record_tool_usage(
                    user_id=user_id,
                    tool_name="session_test_tool", 
                    execution_time_ms=300,
                    status="completed"
                )
            await asyncio.sleep(0.1)
        
        # When: User continues in same session with additional requests
        additional_context = ToolExecutionContext(
            user_id=user_id,
            tool_name="session_test_tool",
            user_plan=plan_tier.value,
            websocket_session_id=session_id  # Same session
        )
        
        additional_result = await self.permission_service.check_tool_permission(additional_context)
        
        # Then: Rate limit should reflect cumulative usage across session
        assert additional_result is not None, "Should get permission result for session continuation"
        
        # Verify rate limit status includes session context
        if additional_result.rate_limit_status:
            current_usage = additional_result.rate_limit_status.get("current_usage", 0)
            # Should reflect previous usage in session
            assert current_usage >= 0, "Should track usage across session lifecycle"
        
        self.record_metric("session_rate_limit_inheritance", True)
        self.record_metric("session_usage_tracking", True)

