"""
Test User Credit System Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Revenue protection and credit system integrity
- Value Impact: Prevents revenue leakage and ensures accurate billing
- Strategic Impact: Foundation for monetization and subscription management

CRITICAL REQUIREMENTS:
- Tests real credit deduction and management logic
- Validates billing accuracy and subscription enforcement
- Ensures no credit overselling or revenue leakage
- No mocks - uses real business logic with database
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.db.transaction_manager import TransactionManager
from netra_backend.app.db.models_postgres import User, CreditTransaction, Subscription
from netra_backend.app.business.credit_manager import CreditManager
from netra_backend.app.business.subscription_manager import SubscriptionManager
from netra_backend.app.business.billing_calculator import BillingCalculator


class TestUserCreditSystemComprehensive(SSotBaseTestCase):
    """
    Comprehensive user credit system tests.
    
    Tests critical business logic that directly impacts revenue:
    - Credit allocation and deduction accuracy
    - Subscription tier enforcement
    - Usage tracking and billing
    - Overage handling and limits
    - Revenue protection mechanisms
    """
    
        
    async def setup_credit_system(self) -> Tuple[CreditManager, SubscriptionManager, BillingCalculator]:
        """Set up credit system with real business logic."""
        # Get transaction manager
        from netra_backend.app.db.database_manager import get_database_manager
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        tx_manager = TransactionManager(db_manager.get_session_factory())
        
        # Initialize business logic managers
        credit_manager = CreditManager(tx_manager)
        subscription_manager = SubscriptionManager(tx_manager) 
        billing_calculator = BillingCalculator()
        
        return credit_manager, subscription_manager, billing_calculator
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_credit_allocation_by_subscription_tier(self):
        """
        Test credit allocation based on subscription tiers.
        
        BUSINESS CRITICAL: Credit allocation determines revenue per user.
        Must ensure each tier gets correct credit limits and allocations.
        """
        test_user_prefix = f"credit_test_{uuid.uuid4().hex[:8]}"
        credit_manager, subscription_manager, billing_calculator = await self.setup_credit_system()
        
        try:
            # Test Free tier credit allocation
            free_user_email = f"{test_user_prefix}_free@example.com"
            free_user = await self._create_test_user(
                credit_manager, 
                free_user_email,
                subscription_tier="free"
            )
            
            # Free tier: 100 credits monthly
            free_allocation = await credit_manager.allocate_monthly_credits(
                user_id=free_user.id,
                tier="free"
            )
            
            assert free_allocation.success, f"Free tier allocation failed: {free_allocation.error}"
            assert free_allocation.credits_allocated == 100, \
                f"Free tier should get 100 credits, got {free_allocation.credits_allocated}"
            
            # Verify user credits updated
            updated_free_user = await credit_manager.get_user_credits(free_user.id)
            assert updated_free_user.credits_remaining == 100, \
                f"Free user credits incorrect: {updated_free_user.credits_remaining}"
            
            # Test Early tier credit allocation (paid tier)
            early_user_email = f"{test_user_prefix}_early@example.com"
            early_user = await self._create_test_user(
                credit_manager,
                early_user_email,
                subscription_tier="early"
            )
            
            # Early tier: 1000 credits monthly
            early_allocation = await credit_manager.allocate_monthly_credits(
                user_id=early_user.id,
                tier="early"
            )
            
            assert early_allocation.success, f"Early tier allocation failed: {early_allocation.error}"
            assert early_allocation.credits_allocated == 1000, \
                f"Early tier should get 1000 credits, got {early_allocation.credits_allocated}"
            
            # Test Mid tier (higher tier)
            mid_user_email = f"{test_user_prefix}_mid@example.com"
            mid_user = await self._create_test_user(
                credit_manager,
                mid_user_email, 
                subscription_tier="mid"
            )
            
            # Mid tier: 5000 credits monthly
            mid_allocation = await credit_manager.allocate_monthly_credits(
                user_id=mid_user.id,
                tier="mid"
            )
            
            assert mid_allocation.success, f"Mid tier allocation failed: {mid_allocation.error}"
            assert mid_allocation.credits_allocated == 5000, \
                f"Mid tier should get 5000 credits, got {mid_allocation.credits_allocated}"
            
            # Test Enterprise tier (highest tier)
            enterprise_user_email = f"{test_user_prefix}_enterprise@example.com"
            enterprise_user = await self._create_test_user(
                credit_manager,
                enterprise_user_email,
                subscription_tier="enterprise"
            )
            
            # Enterprise tier: 25000 credits monthly  
            enterprise_allocation = await credit_manager.allocate_monthly_credits(
                user_id=enterprise_user.id,
                tier="enterprise"
            )
            
            assert enterprise_allocation.success, f"Enterprise tier allocation failed: {enterprise_allocation.error}"
            assert enterprise_allocation.credits_allocated == 25000, \
                f"Enterprise tier should get 25000 credits, got {enterprise_allocation.credits_allocated}"
            
            # Verify tier progression makes sense (higher tiers get more credits)
            allocations = [
                ("free", 100),
                ("early", 1000), 
                ("mid", 5000),
                ("enterprise", 25000)
            ]
            
            for i in range(1, len(allocations)):
                current_tier, current_credits = allocations[i]
                previous_tier, previous_credits = allocations[i-1]
                
                assert current_credits > previous_credits, \
                    f"Tier progression error: {current_tier} ({current_credits}) should have more credits than {previous_tier} ({previous_credits})"
            
            # Test subscription upgrade credit handling
            upgrade_result = await subscription_manager.upgrade_subscription(
                user_id=free_user.id,
                from_tier="free",
                to_tier="early"
            )
            
            assert upgrade_result.success, f"Subscription upgrade failed: {upgrade_result.error}"
            
            # Verify credits adjusted for upgrade (pro-rated)
            post_upgrade_user = await credit_manager.get_user_credits(free_user.id)
            assert post_upgrade_user.credits_remaining > 100, \
                f"Upgrade should increase credits beyond free tier: {post_upgrade_user.credits_remaining}"
            
        finally:
            await self._cleanup_test_users(credit_manager)
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_credit_deduction_accuracy_and_tracking(self):
        """
        Test credit deduction accuracy and usage tracking.
        
        BUSINESS CRITICAL: Inaccurate deductions cause revenue leakage.
        Must track all credit usage with perfect accuracy.
        """
        credit_manager, subscription_manager, billing_calculator = await self.setup_credit_system()
        
        try:
            # Create test user with known credit balance
            test_user_email = f"{test_user_prefix}_deduction@example.com"
            test_user = await self._create_test_user(
                credit_manager,
                test_user_email,
                subscription_tier="mid",
                initial_credits=1000
            )
            
            # Test various agent execution costs
            agent_costs = [
                {"agent_type": "triage_agent", "complexity": "low", "expected_cost": 10},
                {"agent_type": "data_analyzer", "complexity": "medium", "expected_cost": 50},
                {"agent_type": "optimization_agent", "complexity": "high", "expected_cost": 150},
                {"agent_type": "research_agent", "complexity": "very_high", "expected_cost": 300}
            ]
            
            remaining_credits = 1000
            transaction_history = []
            
            for i, agent_cost in enumerate(agent_costs):
                # Calculate expected cost
                cost_calculation = billing_calculator.calculate_agent_cost(
                    agent_type=agent_cost["agent_type"],
                    complexity=agent_cost["complexity"],
                    estimated_tokens=1000,
                    user_tier="mid"
                )
                
                actual_cost = cost_calculation.total_cost
                assert abs(actual_cost - agent_cost["expected_cost"]) < 5, \
                    f"Cost calculation incorrect for {agent_cost['agent_type']}: expected ~{agent_cost['expected_cost']}, got {actual_cost}"
                
                # Perform credit deduction
                deduction_result = await credit_manager.deduct_credits(
                    user_id=test_user.id,
                    amount=actual_cost,
                    reason=f"Agent execution: {agent_cost['agent_type']}",
                    transaction_metadata={
                        "agent_type": agent_cost["agent_type"],
                        "complexity": agent_cost["complexity"],
                        "execution_id": f"exec_{i}_{uuid.uuid4().hex[:8]}"
                    }
                )
                
                assert deduction_result.success, f"Credit deduction failed: {deduction_result.error}"
                assert deduction_result.credits_deducted == actual_cost, \
                    f"Deduction amount mismatch: expected {actual_cost}, deducted {deduction_result.credits_deducted}"
                
                # Update expected remaining credits
                remaining_credits -= actual_cost
                
                # Verify user balance is accurate
                current_balance = await credit_manager.get_user_credits(test_user.id)
                assert current_balance.credits_remaining == remaining_credits, \
                    f"Credit balance incorrect after deduction {i}: expected {remaining_credits}, got {current_balance.credits_remaining}"
                
                # Track transaction
                transaction_history.append({
                    "amount": actual_cost,
                    "remaining": remaining_credits,
                    "agent_type": agent_cost["agent_type"]
                })
            
            # Verify complete transaction history
            user_transactions = await credit_manager.get_credit_transaction_history(
                user_id=test_user.id,
                limit=10
            )
            
            assert len(user_transactions) == len(agent_costs), \
                f"Transaction history incomplete: expected {len(agent_costs)}, got {len(user_transactions)}"
            
            # Validate transaction accuracy
            total_deducted = sum(t["amount"] for t in transaction_history)
            assert 1000 - remaining_credits == total_deducted, \
                f"Total deduction mismatch: expected {total_deducted}, actual {1000 - remaining_credits}"
            
            # Test insufficient credit handling
            large_deduction_result = await credit_manager.deduct_credits(
                user_id=test_user.id,
                amount=remaining_credits + 100,  # More than available
                reason="Test oversized deduction"
            )
            
            assert not large_deduction_result.success, "Oversized deduction should fail"
            assert "insufficient" in large_deduction_result.error.lower()
            
            # Verify no partial deduction occurred
            final_balance = await credit_manager.get_user_credits(test_user.id)
            assert final_balance.credits_remaining == remaining_credits, \
                f"Partial deduction occurred: expected {remaining_credits}, got {final_balance.credits_remaining}"
                
        finally:
            await self._cleanup_test_users(credit_manager)
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_subscription_enforcement_and_limits(self):
        """
        Test subscription tier enforcement and usage limits.
        
        BUSINESS CRITICAL: Tier enforcement prevents revenue leakage.
        Free users must not access paid features without upgrading.
        """
        credit_manager, subscription_manager, billing_calculator = await self.setup_credit_system()
        
        try:
            # Create users in different tiers
            free_user_email = f"{test_user_prefix}_enforcement_free@example.com"
            free_user = await self._create_test_user(
                credit_manager,
                free_user_email,
                subscription_tier="free",
                initial_credits=100
            )
            
            paid_user_email = f"{test_user_prefix}_enforcement_paid@example.com"
            paid_user = await self._create_test_user(
                credit_manager,
                paid_user_email,
                subscription_tier="mid",
                initial_credits=1000
            )
            
            # Test free tier limitations
            free_limits = await subscription_manager.get_tier_limits("free")
            
            # Free tier should have restrictions
            assert free_limits.max_monthly_credits == 100
            assert free_limits.max_concurrent_agents == 1
            assert not free_limits.advanced_features_enabled
            assert not free_limits.priority_support
            
            # Test advanced agent access restriction for free tier
            advanced_agent_result = await credit_manager.check_agent_access(
                user_id=free_user.id,
                agent_type="advanced_research_agent",
                user_tier="free"
            )
            
            assert not advanced_agent_result.access_allowed, \
                "Free tier should not access advanced agents"
            assert "upgrade" in advanced_agent_result.restriction_reason.lower()
            
            # Test paid tier has advanced access
            paid_agent_result = await credit_manager.check_agent_access(
                user_id=paid_user.id,
                agent_type="advanced_research_agent",
                user_tier="mid"
            )
            
            assert paid_agent_result.access_allowed, \
                f"Paid tier should access advanced agents: {paid_agent_result.restriction_reason}"
            
            # Test concurrent agent limits
            # Free tier: 1 concurrent agent max
            concurrent_result_1 = await credit_manager.start_agent_execution(
                user_id=free_user.id,
                agent_type="triage_agent",
                execution_id="exec_1"
            )
            
            assert concurrent_result_1.success, "First agent execution should succeed"
            
            # Try second concurrent agent (should fail for free tier)
            concurrent_result_2 = await credit_manager.start_agent_execution(
                user_id=free_user.id,
                agent_type="triage_agent", 
                execution_id="exec_2"
            )
            
            assert not concurrent_result_2.success, "Free tier should not allow concurrent agents"
            assert "concurrent" in concurrent_result_2.error.lower()
            
            # Paid tier should allow multiple concurrent agents
            paid_concurrent_1 = await credit_manager.start_agent_execution(
                user_id=paid_user.id,
                agent_type="data_analyzer",
                execution_id="paid_exec_1"
            )
            
            paid_concurrent_2 = await credit_manager.start_agent_execution(
                user_id=paid_user.id,
                agent_type="optimization_agent",
                execution_id="paid_exec_2"
            )
            
            assert paid_concurrent_1.success and paid_concurrent_2.success, \
                "Paid tier should allow multiple concurrent agents"
            
            # Test monthly usage limits
            # Exhaust free tier monthly credits
            free_monthly_usage = await credit_manager.get_monthly_usage(free_user.id)
            credits_to_use = 100 - free_monthly_usage.credits_used
            
            if credits_to_use > 0:
                exhaust_result = await credit_manager.deduct_credits(
                    user_id=free_user.id,
                    amount=credits_to_use,
                    reason="Monthly limit test"
                )
                assert exhaust_result.success, "Credit deduction should succeed"
            
            # Try to use more credits (should fail)
            over_limit_result = await credit_manager.deduct_credits(
                user_id=free_user.id,
                amount=10,
                reason="Over limit test"
            )
            
            assert not over_limit_result.success, "Should not allow usage over monthly limit"
            
            # Test upgrade enforcement
            upgrade_prompt = await subscription_manager.check_upgrade_needed(
                user_id=free_user.id,
                requested_feature="advanced_analytics"
            )
            
            assert upgrade_prompt.upgrade_required, "Advanced features should require upgrade"
            assert "mid" in upgrade_prompt.recommended_tier or "early" in upgrade_prompt.recommended_tier
            
            # Test feature access after upgrade
            upgrade_result = await subscription_manager.upgrade_subscription(
                user_id=free_user.id,
                from_tier="free",
                to_tier="early"
            )
            
            assert upgrade_result.success, f"Upgrade should succeed: {upgrade_result.error}"
            
            # Verify upgraded user gets advanced access
            post_upgrade_access = await credit_manager.check_agent_access(
                user_id=free_user.id,
                agent_type="advanced_research_agent",
                user_tier="early"
            )
            
            assert post_upgrade_access.access_allowed, \
                "Upgraded user should get advanced access"
                
        finally:
            await self._cleanup_test_users(credit_manager)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_billing_calculation_accuracy(self):
        """
        Test billing calculation accuracy for revenue protection.
        
        BUSINESS CRITICAL: Billing errors directly impact revenue.
        Must calculate charges with perfect accuracy.
        """
        credit_manager, subscription_manager, billing_calculator = await self.setup_credit_system()
        
        try:
            # Test users in different tiers for billing comparison
            tiers_to_test = [
                {"tier": "early", "monthly_rate": 29.99, "credits": 1000},
                {"tier": "mid", "monthly_rate": 99.99, "credits": 5000},
                {"tier": "enterprise", "monthly_rate": 299.99, "credits": 25000}
            ]
            
            billing_test_results = []
            
            for tier_info in tiers_to_test:
                user_email = f"{test_user_prefix}_billing_{tier_info['tier']}@example.com"
                user = await self._create_test_user(
                    credit_manager,
                    user_email,
                    subscription_tier=tier_info["tier"],
                    initial_credits=tier_info["credits"]
                )
                
                # Simulate month of usage
                monthly_usage = [
                    {"agent": "triage_agent", "executions": 50, "avg_tokens": 500},
                    {"agent": "data_analyzer", "executions": 20, "avg_tokens": 2000},
                    {"agent": "optimization_agent", "executions": 10, "avg_tokens": 5000},
                    {"agent": "research_agent", "executions": 5, "avg_tokens": 10000}
                ]
                
                total_credits_used = 0
                usage_details = []
                
                for usage in monthly_usage:
                    for _ in range(usage["executions"]):
                        cost_calc = billing_calculator.calculate_agent_cost(
                            agent_type=usage["agent"],
                            complexity="medium",
                            estimated_tokens=usage["avg_tokens"],
                            user_tier=tier_info["tier"]
                        )
                        
                        deduction_result = await credit_manager.deduct_credits(
                            user_id=user.id,
                            amount=cost_calc.total_cost,
                            reason=f"Billing test: {usage['agent']}"
                        )
                        
                        if deduction_result.success:
                            total_credits_used += cost_calc.total_cost
                            usage_details.append({
                                "agent": usage["agent"],
                                "cost": cost_calc.total_cost,
                                "tokens": usage["avg_tokens"]
                            })
                
                # Calculate monthly bill
                monthly_bill = billing_calculator.calculate_monthly_bill(
                    user_id=user.id,
                    subscription_tier=tier_info["tier"],
                    credits_used=total_credits_used,
                    base_monthly_rate=tier_info["monthly_rate"]
                )
                
                # Validate billing accuracy
                expected_base_charge = tier_info["monthly_rate"]
                assert abs(monthly_bill.base_subscription - expected_base_charge) < 0.01, \
                    f"Base subscription charge incorrect for {tier_info['tier']}: expected {expected_base_charge}, got {monthly_bill.base_subscription}"
                
                # Check overage charges if credits exceeded
                credits_included = tier_info["credits"]
                if total_credits_used > credits_included:
                    overage_credits = total_credits_used - credits_included
                    expected_overage = overage_credits * billing_calculator.overage_rate_per_credit
                    
                    assert abs(monthly_bill.overage_charges - expected_overage) < 0.01, \
                        f"Overage charges incorrect: expected {expected_overage}, got {monthly_bill.overage_charges}"
                else:
                    assert monthly_bill.overage_charges == 0.0, \
                        f"No overage expected but charged: {monthly_bill.overage_charges}"
                
                # Validate total bill
                expected_total = monthly_bill.base_subscription + monthly_bill.overage_charges + monthly_bill.tax_amount
                assert abs(monthly_bill.total_amount - expected_total) < 0.01, \
                    f"Total bill calculation error: expected {expected_total}, got {monthly_bill.total_amount}"
                
                billing_test_results.append({
                    "tier": tier_info["tier"],
                    "credits_used": total_credits_used,
                    "bill": monthly_bill,
                    "usage_details": usage_details
                })
            
            # Validate tier-based billing differences
            early_bill = next(r for r in billing_test_results if r["tier"] == "early")["bill"]
            mid_bill = next(r for r in billing_test_results if r["tier"] == "mid")["bill"]
            enterprise_bill = next(r for r in billing_test_results if r["tier"] == "enterprise")["bill"]
            
            # Higher tiers should have higher base rates
            assert early_bill.base_subscription < mid_bill.base_subscription < enterprise_bill.base_subscription, \
                "Tier pricing progression incorrect"
            
            # Test billing edge cases
            # Zero usage billing
            zero_usage_bill = billing_calculator.calculate_monthly_bill(
                user_id=user.id,
                subscription_tier="mid",
                credits_used=0,
                base_monthly_rate=99.99
            )
            
            assert zero_usage_bill.base_subscription == 99.99
            assert zero_usage_bill.overage_charges == 0.0
            assert zero_usage_bill.usage_charges == 0.0
            
            # Maximum overage billing
            max_overage_bill = billing_calculator.calculate_monthly_bill(
                user_id=user.id,
                subscription_tier="early",
                credits_used=10000,  # Way over 1000 included
                base_monthly_rate=29.99
            )
            
            expected_overage = (10000 - 1000) * billing_calculator.overage_rate_per_credit
            assert abs(max_overage_bill.overage_charges - expected_overage) < 0.01
            
        finally:
            await self._cleanup_test_users(credit_manager)
    
    async def _create_test_user(
        self, 
        credit_manager: CreditManager, 
        email: str, 
        subscription_tier: str,
        initial_credits: int = 0
    ) -> User:
        """Helper to create test user with credits."""
        user_data = {
            "email": email,
            "name": f"Test User {email.split('@')[0]}",
            "subscription_tier": subscription_tier,
            "credits_remaining": initial_credits,
            "created_at": datetime.now(timezone.utc)
        }
        
        user = await credit_manager.create_user_with_credits(user_data)
        return user
    
    async def _cleanup_test_users(self, credit_manager: CreditManager):
        """Helper to cleanup test users."""
        await credit_manager.cleanup_test_users_by_prefix(test_user_prefix)


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])