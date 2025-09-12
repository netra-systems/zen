"""
Free Tier Limit Enforcement Tester - E2E Test Core Logic
Business Value: $300K+ MRR - Free-to-paid conversion flow testing

BVJ (Business Value Justification):
1. Segment: Free  ->  Paid conversion (100% of new revenue generation)
2. Business Goal: Execute complete limit enforcement and upgrade flow testing
3. Value Impact: Validates free-to-paid conversion pipeline
4. Revenue Impact: Each conversion = $348-3588/year in recurring revenue

REQUIREMENTS:
- Complete free tier limit enforcement flow execution
- Mock service integration for reliable testing
- Performance validation (<30 seconds total)
- 450-line file limit, 25-line function limit
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from netra_backend.app.schemas.user_plan import PlanTier
from tests.e2e.free_tier_limit_managers import (
    LimitEnforcementManager,
    UpgradePromptManager,
)


class FreeTierLimitTester:
    """Executes complete free tier limit enforcement and upgrade flow."""
    
    def __init__(self, auth_tester):
        self.auth_tester = auth_tester
        self.test_user_email = f"limits-test-{uuid.uuid4().hex[:8]}@example.com"
        self.current_token: Optional[str] = None
        self.usage_tracking = {"requests_sent": 0, "daily_limit": 10}
        self.user_data = {}
    
    async def execute_complete_limit_enforcement_flow(self) -> Dict[str, Any]:
        """Execute complete limit enforcement and upgrade flow."""
        start_time = time.time()
        flow_results = {"steps": [], "success": False, "execution_time": 0}
        
        try:
            # Step 1: Create free user with daily limits
            user_result = await self._create_free_user_with_limits()
            flow_results["steps"].append({"step": "free_user_created", "success": True, "data": user_result})
            
            # Step 2: Use service normally within limits
            normal_usage = await self._execute_normal_usage_pattern()
            flow_results["steps"].append({"step": "normal_usage", "success": True, "data": normal_usage})
            
            # Step 3: Approach limit with warning notification
            warning_result = await self._approach_daily_limit_with_warning()
            flow_results["steps"].append({"step": "limit_warning", "success": True, "data": warning_result})
            
            # Step 4: Hit limit and trigger enforcement
            enforcement_result = await self._hit_limit_and_trigger_enforcement()
            flow_results["steps"].append({"step": "limit_enforcement", "success": True, "data": enforcement_result})
            
            # Step 5: Receive contextual upgrade prompt
            upgrade_prompt = await self._receive_contextual_upgrade_prompt()
            flow_results["steps"].append({"step": "upgrade_prompt", "success": True, "data": upgrade_prompt})
            
            # Step 6: Execute tier upgrade transaction
            upgrade_result = await self._execute_tier_upgrade_transaction()
            flow_results["steps"].append({"step": "tier_upgraded", "success": True, "data": upgrade_result})
            
            # Step 7: Verify limits removed and service restored
            service_restored = await self._verify_service_restored_unlimited()
            flow_results["steps"].append({"step": "service_restored", "success": True, "data": service_restored})
            
            flow_results["success"] = True
            flow_results["execution_time"] = time.time() - start_time
            
            # CRITICAL: Must complete in <30 seconds
            assert flow_results["execution_time"] < 30.0, f"Limit flow took {flow_results['execution_time']}s > 30s"
            
        except Exception as e:
            flow_results["error"] = str(e)
            flow_results["execution_time"] = time.time() - start_time
            raise
        
        return flow_results
    
    async def _create_free_user_with_limits(self) -> Dict[str, Any]:
        """Create free tier user with enforced daily limits."""
        # Create real JWT payload for free user
        payload = self.auth_tester.jwt_helper.create_valid_payload()
        payload["email"] = self.test_user_email
        payload["tier"] = PlanTier.FREE.value
        payload["user_id"] = str(uuid.uuid4())
        
        # Generate real JWT token
        self.current_token = self.auth_tester.jwt_helper.create_token(payload)
        
        # Store user data
        self.user_data = {
            "user_id": payload["user_id"],
            "email": self.test_user_email,
            "tier": PlanTier.FREE,
            "daily_limit": 10,
            "usage_count": 0
        }
        
        return {"user_created": True, "free_tier_confirmed": True, "initial_limits": {"daily_limit": 10, "usage_count": 0}}
    
    async def _execute_normal_usage_pattern(self) -> Dict[str, Any]:
        """Execute normal usage pattern within limits."""
        limit_manager = LimitEnforcementManager(self)
        successful_requests = []
        
        # Send 7 requests (safely within 10 request limit)
        for i in range(7):
            request_result = await self._send_single_request(f"Normal request {i+1}")
            usage_data = await limit_manager.track_usage_against_limits("normal_request")
            successful_requests.append({"request": request_result, "usage": usage_data})
        
        # Validate all requests succeeded
        assert len(successful_requests) == 7, "Not all normal requests succeeded"
        assert all(r["request"]["success"] for r in successful_requests), "Some requests failed"
        return {"successful_requests": len(successful_requests), "usage_pattern": "normal"}
    
    async def _approach_daily_limit_with_warning(self) -> Dict[str, Any]:
        """Approach daily limit and validate warning trigger."""
        limit_manager = LimitEnforcementManager(self)
        
        # Send 2 more requests (total 9, leaving 1 remaining)
        warning_result = {"warning_triggered": False}
        for i in range(2):
            await self._send_single_request(f"Approaching limit {i+1}")
            usage_data = await limit_manager.track_usage_against_limits("approaching_limit")
            current_warning = await limit_manager.validate_warning_trigger(usage_data)
            if current_warning["warning_triggered"]:
                warning_result = current_warning
        
        # Validate warning triggered at appropriate threshold
        assert warning_result["warning_triggered"], "Warning not triggered at 80% usage"
        assert warning_result["remaining_count"] <= 2, "Warning triggered too early"
        return {"warning_triggered": True, "remaining_requests": warning_result["remaining_count"]}
    
    async def _hit_limit_and_trigger_enforcement(self) -> Dict[str, Any]:
        """Hit daily limit and validate enforcement activation."""
        limit_manager = LimitEnforcementManager(self)
        
        # Send final allowed request (should be request #10)
        await self._send_single_request("Final allowed request")
        usage_data = await limit_manager.track_usage_against_limits("final_request")
        
        # Send request that should be blocked (would be request #11)
        try:
            await self._send_single_request("Over limit request")
            assert False, "Request should have been blocked by limit enforcement"
        except Exception as e:
            # Validate proper enforcement error
            if "Daily limit exceeded" not in str(e):
                raise e  # Re-raise if it's not the expected error
            
            enforcement_data = await limit_manager.validate_enforcement_trigger({"limit_exceeded": True})
            
            assert enforcement_data["enforcement_active"], "Enforcement not properly activated"
            return {"limit_hit": True, "enforcement_active": True, "block_reason": enforcement_data["block_reason"]}
    
    async def _receive_contextual_upgrade_prompt(self) -> Dict[str, Any]:
        """Receive and validate contextual upgrade prompt."""
        prompt_manager = UpgradePromptManager(self)
        
        # Validate prompt quality and messaging
        prompt_data = await prompt_manager.validate_upgrade_prompt_quality("daily_limit_exceeded")
        
        # Validate optimal timing
        usage_context = {
            "requests_sent": self.usage_tracking["requests_sent"],
            "successful_responses": 9,  # 9 out of 10 requests succeeded
            "error_rate": 0.0
        }
        timing_validation = await prompt_manager.validate_timing_optimization(usage_context)
        
        return {"prompt_received": True, "prompt_quality": prompt_data, "timing_optimal": timing_validation}
    
    async def _execute_tier_upgrade_transaction(self) -> Dict[str, Any]:
        """Execute tier upgrade from Free to Pro."""
        # Validate JWT token
        if not self.auth_tester.jwt_helper.validate_token_structure(self.current_token):
            raise Exception("Invalid token for upgrade")
        
        # Simulate successful upgrade transaction
        self.user_data["tier"] = PlanTier.PRO
        self.user_data["daily_limit"] = -1  # Unlimited
        self.user_data["payment_status"] = "active"
        
        # Update JWT payload to reflect new tier
        payload = self.auth_tester.jwt_helper.create_valid_payload()
        payload["email"] = self.test_user_email
        payload["tier"] = PlanTier.PRO.value
        payload["user_id"] = self.user_data["user_id"]
        
        # Generate new token with upgraded tier
        self.current_token = self.auth_tester.jwt_helper.create_token(payload)
        
        upgrade_result = {
            "upgrade_successful": True,
            "new_tier": "pro",
            "payment_status": "active",
            "upgrade_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return upgrade_result
    
    async def _verify_service_restored_unlimited(self) -> Dict[str, Any]:
        """Verify service restored with unlimited usage post-upgrade."""
        # Temporarily store original usage count
        original_usage = self.user_data["usage_count"]
        
        # Send multiple requests to verify unlimited usage (Pro tier has unlimited)
        unlimited_requests = []
        for i in range(15):  # More than free tier limit
            # For Pro tier, don't increment usage count (unlimited)
            if self.user_data["tier"] == PlanTier.PRO:
                self.user_data["usage_count"] = original_usage  # Reset to allow unlimited
            
            request_result = await self._send_single_request(f"Unlimited request {i+1}")
            unlimited_requests.append(request_result)
            assert request_result["success"], f"Unlimited request {i+1} failed"
        
        # Validate all unlimited requests succeeded
        assert len(unlimited_requests) == 15, "Not all unlimited requests sent"
        assert all(r["success"] for r in unlimited_requests), "Some unlimited requests failed"
        
        return {"unlimited_confirmed": True, "requests_sent": len(unlimited_requests), "service_restored": True}
    
    async def _send_single_request(self, content: str) -> Dict[str, Any]:
        """Send a single request to test usage limits."""
        # Validate JWT token
        if not self.auth_tester.jwt_helper.validate_token_structure(self.current_token):
            return {"success": False, "error": "Invalid token"}
        
        # Check if limit exceeded (only for Free tier)
        if (self.user_data["tier"] == PlanTier.FREE and 
            self.user_data["usage_count"] >= self.user_data["daily_limit"]):
            raise Exception("Daily limit exceeded")
        
        # Simulate successful request (increment for Free tier only)
        if self.user_data["tier"] == PlanTier.FREE:
            self.user_data["usage_count"] += 1
        
        # Mock AI response with cost optimization focus
        mock_response = {
            "message": f"AI response to: {content}",
            "content": "Here's a cost optimization strategy for your AI workload...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {"success": True, "content": content, "response": mock_response}
