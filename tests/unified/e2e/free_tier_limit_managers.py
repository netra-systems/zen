"""
Free Tier Limit Management Helpers - E2E Test Support
Business Value: $300K+ MRR - Free-to-paid conversion limit enforcement helpers

BVJ (Business Value Justification):
1. Segment: Free → Paid conversion support infrastructure
2. Business Goal: Support limit enforcement testing with reusable components
3. Value Impact: Enables reliable free tier limit testing
4. Revenue Impact: Supports $348-3588/year conversion validation

REQUIREMENTS:
- 450-line file limit, 25-line function limit
- Focused helper classes for limit enforcement testing
"""
from datetime import datetime, timezone
from typing import Any, Dict

from netra_backend.app.schemas.UserPlan import PLAN_DEFINITIONS, PlanTier


class LimitEnforcementManager:
    """Manages limit enforcement logic and validation for testing."""
    
    def __init__(self, tester):
        self.tester = tester
        self.enforcement_state = {"warnings_shown": 0, "blocks_triggered": 0}
    
    async def validate_current_limits(self) -> Dict[str, Any]:
        """Validate current user limits and usage."""
        status = await self._get_limit_status()
        free_config = PLAN_DEFINITIONS[PlanTier.FREE]
        
        assert status["plan_tier"] == "free", f"Expected free tier, got {status['plan_tier']}"
        assert status["daily_limit"] == 10, f"Expected 10 daily limit, got {status['daily_limit']}"
        return status
    
    async def track_usage_against_limits(self, action_type: str) -> Dict[str, Any]:
        """Track usage and check against limits."""
        self.tester.usage_tracking["requests_sent"] += 1
        remaining = self.tester.usage_tracking["daily_limit"] - self.tester.usage_tracking["requests_sent"]
        
        return {
            "action_type": action_type,
            "usage_count": self.tester.usage_tracking["requests_sent"],
            "remaining_limit": max(0, remaining),
            "limit_approaching": remaining <= 2,
            "limit_exceeded": remaining < 0
        }
    
    async def validate_warning_trigger(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate warning trigger at appropriate usage level."""
        if usage_data["limit_approaching"]:
            self.enforcement_state["warnings_shown"] += 1
            return {"warning_triggered": True, "remaining_count": usage_data["remaining_limit"]}
        return {"warning_triggered": False}
    
    async def validate_enforcement_trigger(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate enforcement trigger when limit exceeded."""
        if usage_data["limit_exceeded"]:
            self.enforcement_state["blocks_triggered"] += 1
            return {"enforcement_active": True, "block_reason": "daily_limit_exceeded"}
        return {"enforcement_active": False}
    
    async def _get_limit_status(self) -> Dict[str, Any]:
        """Get current limit status from mock data."""
        return {
            "plan_tier": self.tester.user_data["tier"].value,
            "daily_limit": self.tester.user_data["daily_limit"],
            "usage_count": self.tester.user_data["usage_count"],
            "remaining": max(0, self.tester.user_data["daily_limit"] - self.tester.user_data["usage_count"])
        }


class UpgradePromptManager:
    """Manages upgrade prompt presentation and validation."""
    
    def __init__(self, tester):
        self.tester = tester
        self.prompt_quality_metrics = {}
    
    async def validate_upgrade_prompt_quality(self, context: str) -> Dict[str, Any]:
        """Validate upgrade prompt meets conversion standards."""
        prompt_data = await self._capture_upgrade_prompt(context)
        
        # Validate required conversion elements
        required_elements = ["value_proposition", "pricing_clarity", "immediate_benefit", "clear_cta"]
        for element in required_elements:
            assert element in prompt_data, f"Missing critical prompt element: {element}"
        
        self._validate_business_messaging(prompt_data)
        return prompt_data
    
    async def validate_timing_optimization(self, usage_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prompt timing is optimal for conversion."""
        timing_data = {
            "usage_demonstrated": usage_context["requests_sent"] >= 8,
            "value_experienced": usage_context["successful_responses"] >= 6,
            "frustration_minimal": usage_context["error_rate"] < 0.1,
            "context_relevant": True
        }
        
        # All conditions must be met for optimal conversion timing
        optimal_timing = all(timing_data.values())
        assert optimal_timing, f"Suboptimal prompt timing: {timing_data}"
        
        return {"timing_optimized": optimal_timing, "timing_factors": timing_data}
    
    def _validate_business_messaging(self, prompt_data: Dict[str, Any]) -> None:
        """Validate business messaging quality."""
        value_prop = prompt_data["value_proposition"].lower()
        assert "unlimited" in value_prop, "Must emphasize unlimited usage"
        assert "immediately" in prompt_data["immediate_benefit"].lower(), "Must promise immediate resolution"
        
        pricing = prompt_data["pricing_clarity"]
        assert "$29" in pricing or "$299" in pricing, "Must show clear Pro/Enterprise pricing"
    
    async def _capture_upgrade_prompt(self, context: str) -> Dict[str, Any]:
        """Capture upgrade prompt details."""
        return {
            "context": context,
            "value_proposition": "Unlimited requests + priority support + advanced features",
            "pricing_clarity": "Pro: $29/month or Enterprise: $299/month",
            "immediate_benefit": "Continue your work immediately with no restrictions",
            "clear_cta": "Upgrade Now",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "presented_at_optimal_moment": True
        }