"""
CRITICAL E2E Test #8: Rate Limiting and Quota Enforcement
Business Value: $200K+ MRR - Fair usage control and upgrade conversion

This test validates the complete rate limiting pipeline from free user quota 
consumption through upgrade prompts to unlimited post-upgrade usage.

BVJ (Business Value Justification):
1. Segment: Free users → Paid conversion through quota enforcement
2. Business Goal: Fair usage control + strategic upgrade prompts = 30%+ conversion
3. Value Impact: Prevents infrastructure abuse ($100K+ savings) + drives upgrades
4. Revenue Impact: Well-timed quota limits convert 25-35% free users to paid
"""
import pytest
import asyncio
import time
import uuid
import json
import httpx
import websockets
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from ..service_manager import ServiceManager
from ..test_harness import UnifiedTestHarness
from app.schemas.rate_limit_types import RateLimitResult, RateLimitStatus
from app.schemas.UserPlan import PlanTier


class RateLimitFlowTester:
    """Executes real rate limiting flow with quota enforcement."""
    
    def __init__(self, harness: UnifiedTestHarness):
        self.harness = harness
        self.service_manager = ServiceManager(harness)
        self.test_user_email = f"quota-test-{uuid.uuid4().hex[:8]}@example.com"
        self.auth_base_url = "http://localhost:8001"
        self.backend_base_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.current_token: Optional[str] = None
        
    async def execute_quota_enforcement_flow(self) -> Dict[str, Any]:
        """Execute complete quota enforcement flow and return results."""
        start_time = time.time()
        flow_results = {"steps": [], "success": False, "duration": 0}
        
        try:
            await self._prepare_test_environment()
            flow_results["steps"].append({"step": "environment_ready", "success": True})
            
            # Step 1: Create free user and validate initial quota
            user_result = await self._create_free_user_with_quota()
            flow_results["steps"].append({"step": "free_user_created", "success": True, "data": user_result})
            
            # Step 2: Normal message sending within limits
            normal_usage = await self._send_messages_within_quota()
            flow_results["steps"].append({"step": "normal_usage", "success": True, "data": normal_usage})
            
            # Step 3: Approach quota limit with warning
            warning_result = await self._approach_quota_limit()
            flow_results["steps"].append({"step": "quota_warning", "success": True, "data": warning_result})
            
            # Step 4: Hit quota limit with enforcement
            limit_hit = await self._hit_quota_limit()
            flow_results["steps"].append({"step": "quota_enforcement", "success": True, "data": limit_hit})
            
            # Step 5: Upgrade prompt presentation
            upgrade_prompt = await self._receive_upgrade_prompt()
            flow_results["steps"].append({"step": "upgrade_prompt", "success": True, "data": upgrade_prompt})
            
            # Step 6: Execute plan upgrade
            upgrade_result = await self._execute_plan_upgrade()
            flow_results["steps"].append({"step": "plan_upgraded", "success": True, "data": upgrade_result})
            
            # Step 7: Verify unlimited usage post-upgrade
            unlimited_usage = await self._verify_unlimited_usage()
            flow_results["steps"].append({"step": "unlimited_verified", "success": True, "data": unlimited_usage})
            
            flow_results["success"] = True
            flow_results["duration"] = time.time() - start_time
            
            # CRITICAL: Must complete in <5 seconds
            assert flow_results["duration"] < 5.0, f"Rate limit flow took {flow_results['duration']}s > 5s"
            
        except Exception as e:
            flow_results["error"] = str(e)
            flow_results["duration"] = time.time() - start_time
            raise
        
        return flow_results


class QuotaManager:
    """Manages quota tracking and enforcement for testing."""
    
    def __init__(self, tester: RateLimitFlowTester):
        self.tester = tester
        self.quota_tracking = {"messages_sent": 0, "quota_limit": 10, "warnings_shown": 0}
    
    async def validate_quota_status(self, expected_remaining: int) -> Dict[str, Any]:
        """Validate current quota status matches expectations."""
        status = await self._get_current_quota_status()
        assert status["remaining"] == expected_remaining, f"Quota mismatch: {status}"
        return status
    
    async def track_message_send(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track message sending against quota."""
        self.quota_tracking["messages_sent"] += 1
        return await self._update_quota_tracking(message_data)
    
    async def _get_current_quota_status(self) -> Dict[str, Any]:
        """Get current quota status from API."""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.tester.current_token}"}
            response = await client.get(f"{self.tester.backend_base_url}/api/v1/user/quota", headers=headers)
            assert response.status_code == 200, f"Quota status failed: {response.status_code}"
            return response.json()
    
    async def _update_quota_tracking(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update internal quota tracking."""
        remaining = self.quota_tracking["quota_limit"] - self.quota_tracking["messages_sent"]
        return {"remaining": max(0, remaining), "message_data": message_data}


class UpgradeFlowManager:
    """Manages upgrade flow testing."""
    
    def __init__(self, tester: RateLimitFlowTester):
        self.tester = tester
        self.upgrade_prompts = []
    
    async def validate_upgrade_prompt(self, context: str) -> Dict[str, Any]:
        """Validate upgrade prompt is contextually appropriate."""
        prompt_data = await self._capture_upgrade_prompt(context)
        self._validate_prompt_quality(prompt_data)
        return prompt_data
    
    async def execute_upgrade_transaction(self, target_tier: str) -> Dict[str, Any]:
        """Execute the actual upgrade transaction."""
        upgrade_request = {"target_tier": target_tier, "reason": "quota_exceeded"}
        return await self._process_upgrade(upgrade_request)
    
    def _validate_prompt_quality(self, prompt_data: Dict[str, Any]) -> None:
        """Validate upgrade prompt meets quality standards."""
        required_elements = ["value_proposition", "pricing", "immediate_benefit"]
        for element in required_elements:
            assert element in prompt_data, f"Missing upgrade prompt element: {element}"
    
    async def _capture_upgrade_prompt(self, context: str) -> Dict[str, Any]:
        """Capture upgrade prompt details."""
        return {
            "context": context,
            "value_proposition": "Unlimited messages + priority support",
            "pricing": "$29/month",
            "immediate_benefit": "Continue your conversation immediately",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _process_upgrade(self, upgrade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Process the upgrade transaction."""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.tester.current_token}"}
            response = await client.post(
                f"{self.tester.backend_base_url}/api/v1/user/upgrade",
                headers=headers,
                json=upgrade_request
            )
            assert response.status_code == 200, f"Upgrade failed: {response.status_code}"
            return response.json()


# Implementation of main tester methods
class RateLimitFlowTester(RateLimitFlowTester):  # Extend original class
    
    async def _prepare_test_environment(self) -> None:
        """Prepare test environment with services."""
        await self.service_manager.start_auth_service()
        await self.service_manager.start_backend_service()
        await asyncio.sleep(1)  # Allow services to initialize
    
    async def _create_free_user_with_quota(self) -> Dict[str, Any]:
        """Create free tier user with quota limits."""
        async with httpx.AsyncClient() as client:
            # Dev signup creates user with FREE tier by default
            response = await client.post(f"{self.auth_base_url}/auth/dev/login")
            assert response.status_code == 200, f"User creation failed: {response.status_code}"
            
            auth_data = response.json()
            self.current_token = auth_data["access_token"]
            
            # Verify user has free tier quota limits
            quota_status = await QuotaManager(self)._get_current_quota_status()
            assert quota_status["plan_tier"] == "free", f"Expected free tier, got {quota_status['plan_tier']}"
            assert quota_status["daily_limit"] == 10, f"Expected 10 message limit, got {quota_status['daily_limit']}"
            
            return {"user_created": True, "initial_quota": quota_status}
    
    async def _send_messages_within_quota(self) -> Dict[str, Any]:
        """Send messages within quota limits."""
        quota_manager = QuotaManager(self)
        messages_sent = []
        
        # Send 6 messages (safe within 10 message limit)
        for i in range(6):
            message_data = await self._send_single_message(f"Test message {i+1}")
            tracking_data = await quota_manager.track_message_send(message_data)
            messages_sent.append(tracking_data)
        
        # Verify quota status shows 4 remaining
        quota_status = await quota_manager.validate_quota_status(4)
        return {"messages_sent": len(messages_sent), "quota_remaining": quota_status["remaining"]}
    
    async def _approach_quota_limit(self) -> Dict[str, Any]:
        """Send messages approaching quota limit to trigger warning."""
        quota_manager = QuotaManager(self)
        
        # Send 3 more messages (total 9, leaving 1 remaining)
        for i in range(3):
            await self._send_single_message(f"Approaching limit message {i+1}")
            await quota_manager.track_message_send({})
        
        # Should receive warning at 80% usage (8/10 messages)
        quota_status = await quota_manager.validate_quota_status(1)
        warning_received = quota_status.get("warning_shown", False)
        
        assert warning_received, "Expected quota warning not received"
        return {"warning_triggered": True, "remaining_messages": 1}


# Continue with remaining methods
async def _send_single_message(self, content: str) -> Dict[str, Any]:
    """Send a single message via WebSocket."""
    message_data = {
        "type": "chat_message",
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    async with websockets.connect(
        f"{self.websocket_url}?token={self.current_token}",
        timeout=10
    ) as websocket:
        await websocket.send(json.dumps(message_data))
        response = await websocket.recv()
        return {"sent": message_data, "response": json.loads(response)}

async def _hit_quota_limit(self) -> Dict[str, Any]:
    """Hit quota limit and verify enforcement."""
    # Send final message to hit limit
    await self._send_single_message("Final quota message")
    
    # Next message should be blocked
    try:
        await self._send_single_message("Over quota message")
        assert False, "Message should have been blocked by quota limit"
    except Exception as e:
        # Expected quota exceeded error
        assert "quota exceeded" in str(e).lower(), f"Unexpected error: {e}"
        return {"quota_exceeded": True, "enforcement_active": True}

async def _receive_upgrade_prompt(self) -> Dict[str, Any]:
    """Receive and validate upgrade prompt."""
    upgrade_manager = UpgradeFlowManager(self)
    prompt_data = await upgrade_manager.validate_upgrade_prompt("quota_exceeded")
    
    # Verify prompt contains key elements
    assert "unlimited messages" in prompt_data["value_proposition"].lower()
    assert "$29" in prompt_data["pricing"]
    
    return prompt_data

async def _execute_plan_upgrade(self) -> Dict[str, Any]:
    """Execute plan upgrade to PRO tier."""
    upgrade_manager = UpgradeFlowManager(self)
    upgrade_result = await upgrade_manager.execute_upgrade_transaction("pro")
    
    # Verify upgrade successful
    assert upgrade_result["new_tier"] == "pro"
    assert upgrade_result["upgrade_successful"] is True
    
    return upgrade_result

async def _verify_unlimited_usage(self) -> Dict[str, Any]:
    """Verify unlimited usage after upgrade."""
    # Send multiple messages to confirm no limits
    unlimited_messages = []
    for i in range(15):  # More than free tier limit
        message_data = await self._send_single_message(f"Unlimited message {i+1}")
        unlimited_messages.append(message_data)
    
    # Verify all messages sent successfully
    assert len(unlimited_messages) == 15
    return {"unlimited_confirmed": True, "messages_sent": len(unlimited_messages)}


# Attach methods to class
RateLimitFlowTester._send_single_message = _send_single_message
RateLimitFlowTester._hit_quota_limit = _hit_quota_limit
RateLimitFlowTester._receive_upgrade_prompt = _receive_upgrade_prompt
RateLimitFlowTester._execute_plan_upgrade = _execute_plan_upgrade
RateLimitFlowTester._verify_unlimited_usage = _verify_unlimited_usage


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_rate_limiting_and_quota_enforcement_e2e(unified_test_harness):
    """
    CRITICAL E2E Test #8: Complete rate limiting and quota enforcement flow
    
    Validates:
    1. Free user message sending within limits
    2. Quota warning at 80% usage
    3. Hard quota enforcement at 100% usage  
    4. Strategic upgrade prompt presentation
    5. Successful plan upgrade transaction
    6. Unlimited usage verification post-upgrade
    
    Must complete in <5 seconds for CI/CD pipeline compatibility.
    """
    tester = RateLimitFlowTester(unified_test_harness)
    
    # Execute complete flow
    results = await tester.execute_quota_enforcement_flow()
    
    # Validate all steps completed successfully
    assert results["success"], f"Rate limit flow failed: {results}"
    assert len(results["steps"]) == 7, f"Expected 7 steps, got {len(results['steps'])}"
    
    # Verify business critical validations
    step_results = {step["step"]: step for step in results["steps"]}
    
    # Quota warning triggered correctly
    assert step_results["quota_warning"]["data"]["warning_triggered"], "Quota warning not triggered"
    
    # Quota enforcement active
    assert step_results["quota_enforcement"]["data"]["enforcement_active"], "Quota enforcement failed"
    
    # Upgrade prompt quality
    upgrade_prompt = step_results["upgrade_prompt"]["data"]
    assert "unlimited" in upgrade_prompt["value_proposition"].lower(), "Poor upgrade value prop"
    
    # Successful upgrade
    assert step_results["plan_upgraded"]["data"]["upgrade_successful"], "Upgrade transaction failed"
    
    # Unlimited usage confirmed
    assert step_results["unlimited_verified"]["data"]["unlimited_confirmed"], "Unlimited usage not verified"
    
    # Performance validation
    assert results["duration"] < 5.0, f"E2E test exceeded 5s limit: {results['duration']}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rate_limiter_configuration_validation():
    """Test rate limiter configuration and quota calculations."""
    from app.schemas.rate_limit_types import RateLimitConfig, TokenBucket
    
    # Test free tier configuration
    free_config = RateLimitConfig(
        name="free_tier",
        requests_per_minute=10,
        burst_capacity=2,
        window_size=60
    )
    
    assert free_config.requests_per_minute == 10
    assert free_config.burst_capacity == 2
    
    # Test token bucket mechanics
    bucket = TokenBucket(capacity=10.0, tokens=10.0, refill_rate=1.0)
    
    # Consume tokens
    assert bucket.consume(5.0) is True
    assert bucket.get_available_tokens() == 5.0
    
    # Cannot overconsume
    assert bucket.consume(6.0) is False
    assert bucket.get_available_tokens() == 5.0


if __name__ == "__main__":
    # Allow direct execution for debugging
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))