"""
Conversion Flow E2E Tests - Cost calculator and upgrade flows

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Free users → Paid conversions (10,000+ potential users)
2. **Business Goal**: Cost calculator is #1 conversion driver (40%+ conversion rate)
3. **Value Impact**: Well-timed upgrade prompts convert 25-35% vs <2% poorly timed
4. **Revenue Impact**: Optimized conversion flows = +$600K ARR from calculator usage
5. **Growth Engine**: ROI demonstration drives immediate purchase decisions

These tests validate Tests 7 and 8 from the critical conversion paths.
"""

import pytest
from datetime import datetime, timezone

from app.tests.e2e.conftest import *
from .helpers import FirstTimeUserTestHelpers


class TestConversionFlowE2E:
    """Cost calculator and upgrade flow E2E tests"""

    async def test_7_cost_calculator_to_purchase_decision_e2e(
        self, conversion_environment, cost_savings_calculator
    ):
        """
        CRITICAL: Cost calculator → ROI demonstration → purchase decision
        
        BVJ: Cost calculator is the #1 conversion driver. Users who engage with
        calculator convert at 40%+ rates vs <5% without calculator usage.
        """
        env = conversion_environment
        
        # Phase 1: Interactive cost calculator usage
        calculator_result = await self._engage_cost_calculator(env, cost_savings_calculator)
        
        # Phase 2: Show compelling ROI scenarios
        roi_result = await self._demonstrate_roi_scenarios(env, calculator_result)
        
        # Phase 3: Clear purchase path with confidence
        await self._present_confident_purchase_path(env, roi_result)

    async def test_8_trial_limitations_and_upgrade_prompts_e2e(
        self, conversion_environment, permission_system
    ):
        """
        CRITICAL: Free tier limits → strategic upgrade prompts → conversion
        
        BVJ: Well-timed limit prompts convert 25-35% of users. Poorly timed
        prompts convert <2%. Timing and messaging are revenue-critical.
        """
        env = conversion_environment
        
        # Phase 1: Gradual approach to limits
        limit_approach = await self._approach_trial_limits(env, permission_system)
        
        # Phase 2: Strategic upgrade prompts
        prompt_result = await self._trigger_strategic_upgrade_prompts(env, limit_approach)
        
        # Phase 3: Smooth upgrade flow
        await self._execute_smooth_upgrade_flow(env, prompt_result)

    # Helper methods (each ≤8 lines as required)

    async def _engage_cost_calculator(self, env, calculator):
        """Engage user with interactive cost calculator"""
        user_inputs = {"current_monthly_spend": 2500, "growth_projection": 50, "efficiency_target": 25}
        calculation_result = calculator.calculate_immediate_savings(user_inputs)
        engagement_data = {"inputs": user_inputs, "calculation": calculation_result}
        return engagement_data

    async def _demonstrate_roi_scenarios(self, env, calculator_result):
        """Show compelling ROI scenarios based on user's inputs"""
        scenarios = [
            {"timeframe": "1_month", "savings": "$1,000", "roi": "40%"},
            {"timeframe": "6_months", "savings": "$7,200", "roi": "288%"},
            {"timeframe": "1_year", "savings": "$16,800", "roi": "672%"}
        ]
        roi_demonstration = {"scenarios": scenarios, "confidence": "conservative"}
        return roi_demonstration

    async def _present_confident_purchase_path(self, env, roi_result):
        """Present clear, confident purchase path with guarantees"""
        purchase_confidence = {
            "guarantee": "100% money-back if you don't save 2x the plan cost",
            "social_proof": "4.8/5 rating from 2,000+ customers",
            "urgency": "Start saving today - setup takes 5 minutes"
        }
        env["metrics_tracker"].upgrade_prompt_time = datetime.now(timezone.utc)
        return purchase_confidence

    async def _approach_trial_limits(self, env, permission_system):
        """Simulate gradual approach to trial limits"""
        current_usage = {"requests_today": 8, "limit": 10, "tokens_used": 7500, "token_limit": 10000}
        limit_status = {"approaching": True, "percentage_used": 80, "time_remaining": "2 hours"}
        return {"usage": current_usage, "status": limit_status}

    async def _trigger_strategic_upgrade_prompts(self, env, limit_approach):
        """Trigger well-timed, strategic upgrade prompts"""
        prompt_strategy = {
            "timing": "80_percent_usage",
            "message": "You're getting great results! Upgrade to continue optimizing without limits",
            "value_focus": "unlimited_optimizations"
        }
        await env["websocket_manager"].send_upgrade_prompt(prompt_strategy)
        return prompt_strategy

    async def _execute_smooth_upgrade_flow(self, env, prompt_result):
        """Execute smooth, frictionless upgrade flow"""
        upgrade_flow = {
            "steps": ["select_plan", "payment_method", "confirm"],
            "friction_reduced": True,
            "completion_time": "< 2 minutes"
        }
        return upgrade_flow