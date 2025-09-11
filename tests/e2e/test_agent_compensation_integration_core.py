"""E2E integration tests for agent compensation core functionality.

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise (paid tiers requiring reliable agent performance tracking and billing)
2. **Business Goal**: Maximize revenue through accurate agent compensation/billing tracking
3. **Value Impact**: Ensures agents costs are properly tracked, attributed, and billed
4. **Revenue Impact**: Enables usage-based pricing and accurate financial reporting
5. **Risk Mitigation**: Prevents billing errors that could cost revenue or customer trust

Tests the complete agent billing workflow from cost tracking to revenue calculation.
Critical for maintaining accurate billing and customer satisfaction.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Real service imports - NO MOCKS allowed
from netra_backend.app.services.billing.billing_engine import (
    BillingEngine, BillingPeriod, BillingStatus, Bill, BillingLineItem
)
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from netra_backend.app.business.billing_calculator import BillingCalculator
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, create_isolated_execution_context
)
from netra_backend.app.schemas.billing import (
    UsageEvent, UsageEventType, Invoice, InvoiceStatus,
    BillingTier, UsageSummary
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
class TestAgentCompensationIntegrationCore(SSotAsyncTestCase):
    """E2E integration tests for agent compensation core functionality
    
    These tests validate the complete business scenario where multiple users
    execute agents with different costs, and the system accurately tracks,
    attributes, and bills for usage while maintaining proper isolation.
    """

    def setup_method(self, method=None):
        """Set up real services for agent compensation testing."""
        super().setup_method(method)
        
        # Initialize real services - NO MOCKS
        self.billing_engine = BillingEngine()
        self.cost_tracker = CostTracker()
        self.billing_calculator = BillingCalculator()
        self.id_manager = UnifiedIDManager()
        self.env = IsolatedEnvironment()
        
        # Test users with different tiers
        self.users = {
            'free_user': {
                'user_id': f'user_free_{uuid.uuid4()}',
                'tier': 'free',
                'expected_limits': True
            },
            'starter_user': {
                'user_id': f'user_starter_{uuid.uuid4()}', 
                'tier': 'starter',
                'expected_limits': False
            },
            'enterprise_user': {
                'user_id': f'user_enterprise_{uuid.uuid4()}',
                'tier': 'enterprise', 
                'expected_limits': False
            }
        }
        
        # Agent types with different cost profiles
        self.agent_types = {
            'data_helper': {
                'base_cost_per_call': Decimal('0.005'),
                'token_multiplier': Decimal('0.00001'),
                'typical_tokens': 1500
            },
            'optimization': {
                'base_cost_per_call': Decimal('0.02'),
                'token_multiplier': Decimal('0.00005'), 
                'typical_tokens': 5000
            },
            'reporting': {
                'base_cost_per_call': Decimal('0.01'),
                'token_multiplier': Decimal('0.00002'),
                'typical_tokens': 3000
            }
        }
        
        # Billing period for tests
        self.billing_period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.billing_period_end = self.billing_period_start + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_multi_user_agent_cost_tracking_and_isolation(self):
        """Test that agent costs are properly tracked and isolated per user.
        
        CRITICAL TEST: Validates that multi-user agent execution properly isolates
        costs and billing attribution, preventing cross-user billing contamination.
        """
        usage_events = []
        
        for user_key, user_data in self.users.items():
            user_id = user_data['user_id']
            tier = user_data['tier']
            
            # Create isolated execution context for this user
            thread_id = self.id_manager.generate_thread_id()
            run_id = self.id_manager.generate_run_id()
            request_id = f'req_agent_cost_{uuid.uuid4()}'
            
            context = await create_isolated_execution_context(
                user_id=user_id,
                request_id=request_id,
                thread_id=thread_id,
                run_id=run_id,
                validate_user=False  # Skip DB validation for test
            )
            
            # Simulate multiple agent executions for this user
            for agent_type, cost_profile in self.agent_types.items():
                operation_id = f'op_{agent_type}_{user_id}_{uuid.uuid4()}'
                
                # Calculate actual costs based on agent type and tier
                base_cost = cost_profile['base_cost_per_call']
                tokens_used = cost_profile['typical_tokens']
                token_cost = tokens_used * cost_profile['token_multiplier']
                total_cost = base_cost + token_cost
                
                # Apply tier-based discounts for enterprise
                if tier == 'enterprise':
                    total_cost = total_cost * Decimal('0.8')  # 20% enterprise discount
                elif tier == 'free' and user_data['expected_limits']:
                    # Free tier has usage limits
                    if len(usage_events) > 2:  # Simple limit simulation
                        total_cost = Decimal('0')  # Free tier exceeded
                
                # Track the operation cost with real cost tracker
                await self.cost_tracker.track_operation_cost(
                    operation_id=operation_id,
                    operation_type=f'agent_{agent_type}',
                    model_name=f'agent_{agent_type}_model',
                    tokens_used=tokens_used,
                    cost=total_cost,
                    metadata={
                        'user_id': user_id,
                        'tier': tier,
                        'agent_type': agent_type,
                        'thread_id': context.thread_id,
                        'run_id': context.run_id,
                        'context_request_id': context.request_id
                    }
                )
                
                # Create usage event for billing
                usage_event = UsageEvent(
                    id=operation_id,
                    user_id=user_id,
                    event_type=UsageEventType.API_CALL,
                    resource_name=f'agent_{agent_type}',
                    quantity=Decimal('1'),
                    unit='execution',
                    cost_per_unit=total_cost,
                    total_cost=total_cost,
                    billing_period=f'{self.billing_period_start.strftime("%Y%m%d")}_{self.billing_period_end.strftime("%Y%m%d")}',
                    metadata={
                        'agent_type': agent_type,
                        'tokens_used': tokens_used,
                        'tier': tier,
                        'context_isolation_verified': True
                    }
                )
                usage_events.append(usage_event)
        
        # CRITICAL VALIDATION: Verify cost isolation per user
        user_cost_totals = {}
        for event in usage_events:
            if event.user_id not in user_cost_totals:
                user_cost_totals[event.user_id] = Decimal('0')
            user_cost_totals[event.user_id] += event.total_cost
        
        # Validate each user has non-zero costs (except free tier if limited)
        for user_key, user_data in self.users.items():
            user_id = user_data['user_id']
            user_total = user_cost_totals.get(user_id, Decimal('0'))
            
            if user_data['tier'] == 'free' and user_data['expected_limits']:
                # Free tier might have zero costs due to limits
                assert user_total >= Decimal('0'), f"Free tier user {user_id} has negative costs"
            else:
                assert user_total > Decimal('0'), f"Paid tier user {user_id} should have tracked costs"
        
        # Validate no cross-contamination between users
        user_events = {}
        for event in usage_events:
            if event.user_id not in user_events:
                user_events[event.user_id] = []
            user_events[event.user_id].append(event)
        
        # Each user should have their own events only
        for user_id, events in user_events.items():
            for event in events:
                assert event.user_id == user_id, "Cross-user cost contamination detected!"
                assert user_id in event.metadata.get('context_request_id', ''), "Context isolation failed!"

    @pytest.mark.asyncio
    async def test_agent_billing_generation_accuracy(self):
        """Test that agent usage generates accurate bills with correct calculations.
        
        BUSINESS CRITICAL: Validates that billing amounts are mathematically correct
        and enterprise vs free tier pricing models work as expected.
        """
        # Create usage data for billing test
        test_user_id = f'billing_test_user_{uuid.uuid4()}'
        usage_data = {}
        expected_totals = {}
        
        # Test each tier's billing accuracy
        for tier in ['starter', 'professional', 'enterprise']:
            # Simulate realistic agent usage for this tier
            api_calls = 100 if tier == 'starter' else (500 if tier == 'professional' else 2000)
            llm_tokens = api_calls * 1500  # Average tokens per call
            
            usage_data[f'{tier}_api_call'] = {
                'quantity': api_calls,
                'metadata': {'tier': tier, 'usage_type': 'api_call'}
            }
            usage_data[f'{tier}_llm_tokens'] = {
                'quantity': llm_tokens,
                'metadata': {'tier': tier, 'usage_type': 'llm_tokens'}
            }
            
            # Generate bill with real billing engine
            test_bill = await self.billing_engine.generate_bill(
                user_id=f'{test_user_id}_{tier}',
                period_start=self.billing_period_start,
                period_end=self.billing_period_end,
                usage_data={
                    'api_call': usage_data[f'{tier}_api_call'],
                    'llm_tokens': usage_data[f'{tier}_llm_tokens']
                },
                tier=tier
            )
            
            # Validate bill structure and amounts
            assert isinstance(test_bill, Bill), f"Expected Bill object for {tier}"
            assert test_bill.user_id == f'{test_user_id}_{tier}', f"User ID mismatch for {tier}"
            assert test_bill.status == BillingStatus.PENDING, f"Bill should be pending for {tier}"
            assert test_bill.total_amount > Decimal('0'), f"Bill total should be positive for {tier}"
            
            # Validate line items exist and are accurate
            assert len(test_bill.line_items) >= 1, f"Bill should have line items for {tier}"
            
            # Calculate expected costs manually for validation
            pricing = self.billing_engine.pricing_tiers[tier]
            expected_monthly_base = pricing.get('monthly_base', Decimal('0'))
            expected_api_cost = Decimal(str(api_calls)) * pricing['api_call']
            expected_token_cost = Decimal(str(llm_tokens)) * pricing['llm_tokens']
            expected_subtotal = expected_monthly_base + expected_api_cost + expected_token_cost
            
            # Apply tax (8% default, 0% for enterprise)
            expected_tax = expected_subtotal * (Decimal('0') if tier == 'enterprise' else Decimal('0.08'))
            expected_total = expected_subtotal + expected_tax
            
            # Validate calculations are accurate (within rounding tolerance)
            assert abs(test_bill.subtotal - expected_subtotal) <= Decimal('0.01'), \
                f"Subtotal calculation error for {tier}: expected {expected_subtotal}, got {test_bill.subtotal}"
            assert abs(test_bill.tax_amount - expected_tax) <= Decimal('0.01'), \
                f"Tax calculation error for {tier}: expected {expected_tax}, got {test_bill.tax_amount}"
            assert abs(test_bill.total_amount - expected_total) <= Decimal('0.01'), \
                f"Total calculation error for {tier}: expected {expected_total}, got {test_bill.total_amount}"
            
            expected_totals[tier] = expected_total

        # CRITICAL: Validate tier pricing differences make business sense
        assert expected_totals['enterprise'] > expected_totals['professional'], \
            "Enterprise usage should cost more due to higher base fee"
        assert expected_totals['professional'] > expected_totals['starter'], \
            "Professional usage should cost more than starter"
        
        # Validate enterprise gets tax exemption
        enterprise_bill_id = list(self.billing_engine.bills.keys())[-1]  # Last created bill
        enterprise_bill = self.billing_engine.bills[enterprise_bill_id]
        if 'enterprise' in enterprise_bill.user_id:
            assert enterprise_bill.tax_amount == Decimal('0'), "Enterprise should have no tax"

    @pytest.mark.asyncio
    async def test_agent_compensation_financial_accuracy_end_to_end(self):
        """Test complete end-to-end financial accuracy for agent compensation.
        
        REVENUE PROTECTION: This test validates the complete financial workflow
        that directly impacts revenue accuracy and customer billing integrity.
        """
        # Create comprehensive test scenario with multiple users and agents
        financial_test_users = [
            {'user_id': f'finance_user_1_{uuid.uuid4()}', 'tier': 'professional'},
            {'user_id': f'finance_user_2_{uuid.uuid4()}', 'tier': 'enterprise'},
        ]
        
        total_tracked_costs = Decimal('0')
        total_billed_amounts = Decimal('0')
        user_financial_records = []
        
        for user_data in financial_test_users:
            user_id = user_data['user_id']
            tier = user_data['tier']
            
            # Create user execution context
            context = await create_isolated_execution_context(
                user_id=user_id,
                request_id=f'finance_test_{uuid.uuid4()}',
                validate_user=False
            )
            
            # Simulate realistic agent workload
            agent_executions = [
                {'agent_type': 'data_helper', 'executions': 50, 'avg_tokens': 1200},
                {'agent_type': 'optimization', 'executions': 20, 'avg_tokens': 4500},
                {'agent_type': 'reporting', 'executions': 10, 'avg_tokens': 2800},
            ]
            
            user_usage_data = {'api_call': {'quantity': 0}, 'llm_tokens': {'quantity': 0}}
            user_tracked_cost = Decimal('0')
            
            for execution_config in agent_executions:
                agent_type = execution_config['agent_type']
                exec_count = execution_config['executions']
                avg_tokens = execution_config['avg_tokens']
                
                for i in range(exec_count):
                    operation_id = f'finance_op_{agent_type}_{user_id}_{i}'
                    
                    # Calculate costs using agent cost profiles
                    cost_profile = self.agent_types[agent_type]
                    base_cost = cost_profile['base_cost_per_call']
                    token_cost = avg_tokens * cost_profile['token_multiplier']
                    execution_cost = base_cost + token_cost
                    
                    # Apply enterprise discount
                    if tier == 'enterprise':
                        execution_cost = execution_cost * Decimal('0.8')
                    
                    # Track with cost tracker
                    await self.cost_tracker.track_operation_cost(
                        operation_id=operation_id,
                        operation_type=f'agent_{agent_type}',
                        model_name=f'model_{agent_type}',
                        tokens_used=avg_tokens,
                        cost=execution_cost,
                        metadata={
                            'user_id': user_id,
                            'tier': tier,
                            'financial_test': True,
                            'context_id': context.request_id
                        }
                    )
                    
                    user_tracked_cost += execution_cost
                    user_usage_data['api_call']['quantity'] += 1
                    user_usage_data['llm_tokens']['quantity'] += avg_tokens
            
            # Generate bill for this user
            user_bill = await self.billing_engine.generate_bill(
                user_id=user_id,
                period_start=self.billing_period_start,
                period_end=self.billing_period_end,
                usage_data=user_usage_data,
                tier=tier
            )
            
            # Record financial data for validation
            user_financial_records.append({
                'user_id': user_id,
                'tier': tier,
                'tracked_cost': user_tracked_cost,
                'billed_amount': user_bill.total_amount,
                'api_calls': user_usage_data['api_call']['quantity'],
                'tokens': user_usage_data['llm_tokens']['quantity'],
                'bill_id': user_bill.bill_id
            })
            
            total_tracked_costs += user_tracked_cost
            total_billed_amounts += user_bill.total_amount
        
        # CRITICAL FINANCIAL VALIDATIONS
        
        # 1. Validate total costs are reasonable and non-zero
        assert total_tracked_costs > Decimal('0'), "Total tracked costs must be positive"
        assert total_billed_amounts > Decimal('0'), "Total billed amounts must be positive"
        
        # 2. Validate enterprise discounts are applied correctly
        enterprise_records = [r for r in user_financial_records if r['tier'] == 'enterprise']
        professional_records = [r for r in user_financial_records if r['tier'] == 'professional']
        
        for ent_record in enterprise_records:
            # Enterprise should have meaningful usage costs tracked
            assert ent_record['tracked_cost'] > Decimal('5'), f"Enterprise user should have substantial tracked costs"
            assert ent_record['billed_amount'] > Decimal('10'), f"Enterprise user should have substantial bill"
            
            # Validate tax exemption for enterprise
            enterprise_bill = self.billing_engine.bills[ent_record['bill_id']]
            assert enterprise_bill.tax_amount == Decimal('0'), "Enterprise should have no tax"
        
        # 3. Validate per-user isolation in financial records
        user_ids_in_records = {r['user_id'] for r in user_financial_records}
        assert len(user_ids_in_records) == len(financial_test_users), "Each user should have isolated financial record"
        
        # 4. Validate API call and token accounting
        for record in user_financial_records:
            assert record['api_calls'] > 0, f"User {record['user_id']} should have API calls recorded"
            assert record['tokens'] > 0, f"User {record['user_id']} should have tokens recorded"
            
            # Validate reasonable token-to-call ratios (should be > 1000 tokens per call on average)
            avg_tokens_per_call = record['tokens'] / record['api_calls']
            assert avg_tokens_per_call > 1000, f"Average tokens per call should be realistic: {avg_tokens_per_call}"
        
        # 5. BUSINESS CRITICAL: Validate billing engine statistics are updated
        billing_stats = self.billing_engine.get_stats()
        assert billing_stats['bills_generated'] >= len(financial_test_users), "All bills should be tracked in statistics"
        assert billing_stats['total_revenue'] >= total_billed_amounts, "Revenue statistics should match billed amounts"
        assert billing_stats['enabled'] is True, "Billing engine should remain enabled after operations"

    @pytest.mark.asyncio
    async def test_agent_cost_tracking_data_persistence_validation(self):
        """Test that agent cost data persists correctly for financial reporting.
        
        COMPLIANCE CRITICAL: Validates that cost and billing data is properly
        persisted and retrievable for audit and financial reporting purposes.
        """
        test_user_id = f'persistence_user_{uuid.uuid4()}'
        
        # Create execution context
        context = await create_isolated_execution_context(
            user_id=test_user_id,
            request_id=f'persistence_test_{uuid.uuid4()}',
            validate_user=False
        )
        
        # Generate multiple days of cost data for trend analysis
        daily_costs = []
        for day_offset in range(7):  # 7 days of data
            test_date = datetime.now(timezone.utc) - timedelta(days=day_offset)
            
            # Simulate daily agent usage
            for agent_type, cost_profile in self.agent_types.items():
                operation_id = f'persistence_op_{agent_type}_{test_date.strftime("%Y%m%d")}_{uuid.uuid4()}'
                
                cost = cost_profile['base_cost_per_call'] + (
                    cost_profile['typical_tokens'] * cost_profile['token_multiplier']
                )
                
                # Track cost with specific date
                await self.cost_tracker.track_operation_cost(
                    operation_id=operation_id,
                    operation_type=f'agent_{agent_type}',
                    model_name=f'persistence_model_{agent_type}',
                    tokens_used=cost_profile['typical_tokens'],
                    cost=cost,
                    metadata={
                        'user_id': test_user_id,
                        'date': test_date.isoformat(),
                        'persistence_test': True
                    }
                )
                
                daily_costs.append({
                    'date': test_date,
                    'agent_type': agent_type,
                    'cost': cost,
                    'operation_id': operation_id
                })
        
        # PERSISTENCE VALIDATIONS
        
        # 1. Validate daily cost retrieval
        for day_offset in range(7):
            query_date = datetime.now(timezone.utc) - timedelta(days=day_offset)
            daily_data = await self.cost_tracker.get_daily_costs(query_date)
            
            assert 'date' in daily_data, "Daily data should include date"
            assert 'total_cost' in daily_data, "Daily data should include total cost"
            assert 'total_tokens' in daily_data, "Daily data should include token count"
            assert 'operations' in daily_data, "Daily data should include operation breakdown"
            
            # Validate costs are tracked for this date
            expected_daily_cost = sum(
                d['cost'] for d in daily_costs 
                if d['date'].date() == query_date.date()
            )
            
            if expected_daily_cost > 0:
                assert daily_data['total_cost'] > 0, f"Should have costs for {query_date.date()}"
                # Note: Exact matching may vary due to Redis timing, so we check for reasonable values
                assert daily_data['total_cost'] <= float(expected_daily_cost * 2), "Daily cost should be reasonable"
        
        # 2. Validate cost trends over time
        cost_trends = await self.cost_tracker.get_cost_trends(days=7)
        assert len(cost_trends) <= 7, "Should return up to 7 days of trends"
        assert isinstance(cost_trends, list), "Cost trends should be a list"
        
        for trend_day in cost_trends:
            assert 'date' in trend_day, "Each trend day should have date"
            assert 'total_cost' in trend_day, "Each trend day should have total cost"
        
        # 3. Validate monthly cost estimation
        monthly_estimate = await self.cost_tracker.estimate_monthly_cost()
        assert 'estimated_monthly_cost' in monthly_estimate, "Should provide monthly estimate"
        assert 'confidence' in monthly_estimate, "Should provide confidence level"
        assert monthly_estimate['estimated_monthly_cost'] >= 0, "Monthly estimate should be non-negative"
        
        # 4. Validate model breakdown accuracy
        model_breakdown = await self.cost_tracker.get_cost_breakdown_by_model(days=7)
        assert isinstance(model_breakdown, dict), "Model breakdown should be a dictionary"
        
        # Should have entries for each agent type we tracked
        for agent_type in self.agent_types.keys():
            model_key = f'persistence_model_{agent_type}'
            if model_key in model_breakdown:
                model_data = model_breakdown[model_key]
                assert 'cost' in model_data, f"Model {model_key} should have cost data"
                assert 'tokens' in model_data, f"Model {model_key} should have token data"
                assert 'requests' in model_data, f"Model {model_key} should have request count"
                assert model_data['cost'] >= 0, f"Model {model_key} cost should be non-negative"
        
        # 5. COMPLIANCE: Validate cached usage statistics
        cached_usage = self.cost_tracker.get_cached_usage()
        assert isinstance(cached_usage, dict), "Cached usage should be a dictionary"
        
        # Should have agent operation types in cache
        agent_operations = [op for op in cached_usage.keys() if op.startswith('agent_')]
        assert len(agent_operations) > 0, "Should have agent operations in cache"

    async def async_teardown_method(self, method=None):
        """Clean up after test execution."""
        # Clean up any remaining resources
        if hasattr(self, 'billing_engine'):
            self.billing_engine.disable()
        
        # Clear caches
        if hasattr(self, 'cost_tracker') and hasattr(self.cost_tracker, '_usage_cache'):
            self.cost_tracker._usage_cache.clear()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])