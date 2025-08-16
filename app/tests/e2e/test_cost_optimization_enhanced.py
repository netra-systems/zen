"""
Enhanced Cost Optimization Workflows Test Suite
Tests real cost calculations, budget constraints, and model optimization.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.schemas import SubAgentLifecycle
from app.schemas.llm_base_types import LLMProvider, TokenUsage
from app.services.cost_calculator import (
    CostCalculatorService, BudgetManager, CostTier,
    create_cost_calculator, create_budget_manager
)
from app.core.exceptions import NetraException


@pytest.fixture
def cost_calculator():
    """Create cost calculator service"""
    return create_cost_calculator()


@pytest.fixture
def budget_manager():
    """Create budget manager with test budget"""
    return create_budget_manager(Decimal("5.00"))  # $5 test budget for stricter testing


@pytest.fixture
def enhanced_cost_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup enhanced cost optimization testing environment"""
    agents = _create_cost_aware_agents(real_llm_manager, real_tool_dispatcher)
    return _build_enhanced_setup(agents, real_llm_manager, real_websocket_manager)


def _create_cost_aware_agents(llm: LLMManager, dispatcher) -> Dict:
    """Create agents with cost awareness"""
    return {
        'triage': TriageSubAgent(llm, dispatcher),
        'data': DataSubAgent(llm, dispatcher)
    }


def _build_enhanced_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Build enhanced setup with cost tracking"""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'cost-enhanced-test',
        'cost_calculator': create_cost_calculator(),
        'budget_manager': create_budget_manager(Decimal("25.00"))
    }


@pytest.mark.real_llm
class TestCostCalculationAccuracy:
    """Test accurate cost calculation for different providers and models"""
    
    async def test_token_usage_cost_estimation(self, cost_calculator):
        """Test accurate token usage cost calculation"""
        usage = _create_test_token_usage()
        costs = _calculate_costs_all_providers(usage, cost_calculator)
        _validate_cost_accuracy(costs, usage)
    
    async def test_cost_comparison_across_providers(self, cost_calculator):
        """Test cost comparison across different providers"""
        usage = _create_large_token_usage()
        comparison = _compare_provider_costs(usage, cost_calculator)
        _validate_cost_comparison(comparison)
    
    async def test_budget_impact_estimation(self, budget_manager, cost_calculator):
        """Test budget impact estimation for projected usage"""
        projected_tokens = 50000
        impacts = _calculate_budget_impacts(projected_tokens, cost_calculator)
        _validate_budget_impacts(impacts, budget_manager)


def _create_test_token_usage() -> TokenUsage:
    """Create test token usage for validation"""
    return TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)


def _create_large_token_usage() -> TokenUsage:
    """Create large token usage for stress testing"""
    return TokenUsage(prompt_tokens=10000, completion_tokens=5000, total_tokens=15000)


def _calculate_costs_all_providers(usage: TokenUsage, calculator: CostCalculatorService) -> Dict:
    """Calculate costs for all providers"""
    return {
        'openai_gpt4': calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-4"),
        'openai_gpt35': calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo"),
        'anthropic_opus': calculator.calculate_cost(usage, LLMProvider.ANTHROPIC, "claude-3-opus"),
        'anthropic_haiku': calculator.calculate_cost(usage, LLMProvider.ANTHROPIC, "claude-3-haiku"),
        'google_pro': calculator.calculate_cost(usage, LLMProvider.GOOGLE, "gemini-2.5-pro")
    }


def _validate_cost_accuracy(costs: Dict, usage: TokenUsage):
    """Validate cost calculation accuracy"""
    assert all(cost >= Decimal("0") for cost in costs.values()), "All costs must be non-negative"
    assert costs['openai_gpt4'] > costs['openai_gpt35'], "GPT-4 should cost more than GPT-3.5"
    assert costs['anthropic_opus'] > costs['anthropic_haiku'], "Opus should cost more than Haiku"
    # Verify token usage cost estimation now works
    estimated_cost = usage.cost_estimate
    assert estimated_cost is not None, "Cost estimation should work with enhanced TokenUsage"
    assert estimated_cost > 0, "Estimated cost should be positive"


@pytest.mark.real_llm
class TestBudgetConstraintEnforcement:
    """Test budget constraint enforcement and violation handling"""
    
    async def test_budget_check_prevents_overspend(self, budget_manager):
        """Test budget check prevents operations that would exceed budget"""
        large_usage = _create_budget_busting_usage()
        within_budget = _check_budget_compliance(large_usage, budget_manager)
        _validate_budget_enforcement(within_budget, budget_manager)
    
    async def test_cost_tier_recommendation(self, budget_manager):
        """Test cost tier recommendation based on remaining budget"""
        recommendations = _test_tier_recommendations(budget_manager)
        _validate_tier_recommendations(recommendations, budget_manager)
    
    async def test_real_workflow_budget_tracking(self, enhanced_cost_setup):
        """Test budget tracking during real agent workflow"""
        setup = enhanced_cost_setup
        state = _create_budget_conscious_state()
        budget_tracking = await _execute_with_budget_tracking(setup, state)
        _validate_workflow_budget_tracking(budget_tracking)


def _create_budget_busting_usage() -> TokenUsage:
    """Create usage that would exceed typical budget"""
    return TokenUsage(prompt_tokens=100000, completion_tokens=50000, total_tokens=150000)


def _check_budget_compliance(usage: TokenUsage, manager: BudgetManager) -> Dict:
    """Check budget compliance for different models"""
    return {
        'gpt4_within_budget': manager.check_budget_impact(usage, LLMProvider.OPENAI, "gpt-4"),
        'gpt35_within_budget': manager.check_budget_impact(usage, LLMProvider.OPENAI, "gpt-3.5-turbo"),
        'haiku_within_budget': manager.check_budget_impact(usage, LLMProvider.ANTHROPIC, "claude-3-haiku")
    }


def _validate_budget_enforcement(compliance: Dict, manager: BudgetManager):
    """Validate budget enforcement logic"""
    # Large usage should violate budget for expensive models
    assert not compliance['gpt4_within_budget'], "GPT-4 should exceed budget with large usage"
    # But may be acceptable for economy models
    remaining_budget = manager.get_remaining_budget()
    assert remaining_budget >= Decimal("0"), "Remaining budget should never be negative"


@pytest.mark.real_llm
class TestModelSelectionOptimization:
    """Test model selection optimization based on cost-performance ratios"""
    
    async def test_cost_tier_optimization(self, cost_calculator):
        """Test model selection optimization by cost tier"""
        optimizations = _test_cost_tier_selections(cost_calculator)
        _validate_cost_optimizations(optimizations)
    
    async def test_cost_savings_calculation(self, cost_calculator):
        """Test cost savings calculation from optimization"""
        savings = _calculate_optimization_savings(cost_calculator)
        _validate_cost_savings(savings)
    
    async def test_real_agent_cost_optimization(self, enhanced_cost_setup):
        """Test cost optimization in real agent execution"""
        setup = enhanced_cost_setup
        state = _create_cost_optimization_state()
        optimization_result = await _execute_cost_optimized_workflow(setup, state)
        _validate_agent_cost_optimization(optimization_result)


def _test_cost_tier_selections(calculator: CostCalculatorService) -> Dict:
    """Test cost tier model selections"""
    return {
        'openai_economy': calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.ECONOMY),
        'openai_balanced': calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.BALANCED),
        'anthropic_economy': calculator.get_cost_optimal_model(LLMProvider.ANTHROPIC, CostTier.ECONOMY),
        'google_economy': calculator.get_cost_optimal_model(LLMProvider.GOOGLE, CostTier.ECONOMY)
    }


def _validate_cost_optimizations(optimizations: Dict):
    """Validate cost optimization selections"""
    assert optimizations['openai_economy'] == "gpt-3.5-turbo", "Should select economy model"
    assert optimizations['anthropic_economy'] == "claude-3-haiku", "Should select economy model"
    assert all(model is not None for model in optimizations.values()), "All selections should be valid"


# Workflow execution functions (≤8 lines each)
async def _execute_with_budget_tracking(setup: Dict, state: DeepAgentState) -> Dict:
    """Execute workflow with budget tracking"""
    budget_manager = setup['budget_manager']
    initial_budget = budget_manager.get_remaining_budget()
    # Execute simplified workflow for budget testing
    triage_result = await setup['agents']['triage'].run(state, setup['run_id'], True)
    final_budget = budget_manager.get_remaining_budget()
    return {'initial_budget': initial_budget, 'final_budget': final_budget, 'result': triage_result}


async def _execute_cost_optimized_workflow(setup: Dict, state: DeepAgentState) -> Dict:
    """Execute workflow with cost optimization"""
    cost_calculator = setup['cost_calculator']
    # Test with economy tier for cost optimization
    optimal_model = cost_calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.ECONOMY)
    triage_result = await setup['agents']['triage'].run(state, setup['run_id'], True)
    return {'optimal_model': optimal_model, 'result': triage_result}


# State creation functions (≤8 lines each)
def _create_budget_conscious_state() -> DeepAgentState:
    """Create state for budget-conscious testing"""
    return DeepAgentState(
        user_request="I need to optimize costs while maintaining quality. Budget is tight.",
        metadata={'test_type': 'budget_conscious', 'cost_priority': 'high'}
    )


def _create_cost_optimization_state() -> DeepAgentState:
    """Create state for cost optimization testing"""
    return DeepAgentState(
        user_request="Help me reduce LLM costs by 30% while keeping performance acceptable.",
        metadata={'test_type': 'cost_optimization', 'target_reduction': '30%'}
    )


# Additional helper functions
def _compare_provider_costs(usage: TokenUsage, calculator: CostCalculatorService) -> Dict:
    """Compare costs across providers"""
    costs = _calculate_costs_all_providers(usage, calculator)
    sorted_costs = sorted(costs.items(), key=lambda x: x[1])
    return {'cheapest': sorted_costs[0], 'most_expensive': sorted_costs[-1], 'all_costs': costs}


def _validate_cost_comparison(comparison: Dict):
    """Validate cost comparison results"""
    cheapest = comparison['cheapest']
    most_expensive = comparison['most_expensive']
    assert cheapest[1] < most_expensive[1], "Cheapest should cost less than most expensive"
    assert len(comparison['all_costs']) >= 3, "Should compare multiple providers"


def _calculate_budget_impacts(token_count: int, calculator: CostCalculatorService) -> Dict:
    """Calculate budget impacts for projected usage"""
    return {
        'gpt4_impact': calculator.estimate_budget_impact(token_count, LLMProvider.OPENAI, "gpt-4"),
        'gpt35_impact': calculator.estimate_budget_impact(token_count, LLMProvider.OPENAI, "gpt-3.5-turbo"),
        'haiku_impact': calculator.estimate_budget_impact(token_count, LLMProvider.ANTHROPIC, "claude-3-haiku")
    }


def _validate_budget_impacts(impacts: Dict, manager: BudgetManager):
    """Validate budget impact calculations"""
    daily_budget = manager.daily_budget
    assert all(impact >= Decimal("0") for impact in impacts.values()), "All impacts should be non-negative"
    assert impacts['gpt4_impact'] > impacts['gpt35_impact'], "GPT-4 should have higher budget impact"


def _test_tier_recommendations(manager: BudgetManager) -> Dict:
    """Test cost tier recommendations based on budget"""
    # Simulate different budget scenarios
    original_spending = manager.current_spending
    recommendations = {}
    
    # Test with different spending levels
    manager.current_spending = manager.daily_budget * Decimal("0.2")  # 20% used
    recommendations['low_usage'] = manager.recommend_cost_tier()
    
    manager.current_spending = manager.daily_budget * Decimal("0.6")  # 60% used
    recommendations['medium_usage'] = manager.recommend_cost_tier()
    
    manager.current_spending = manager.daily_budget * Decimal("0.9")  # 90% used
    recommendations['high_usage'] = manager.recommend_cost_tier()
    
    # Restore original spending
    manager.current_spending = original_spending
    return recommendations


def _validate_tier_recommendations(recommendations: Dict, manager: BudgetManager):
    """Validate tier recommendation logic"""
    # High usage should recommend economy tier
    assert recommendations['high_usage'] == CostTier.ECONOMY, "High usage should recommend economy tier"
    # Low usage can recommend balanced tier
    assert recommendations['low_usage'] in [CostTier.BALANCED, CostTier.ECONOMY], "Low usage should allow better tiers"


def _calculate_optimization_savings(calculator: CostCalculatorService) -> Dict:
    """Calculate cost savings from model optimization"""
    usage = _create_test_token_usage()
    
    # Original: expensive model
    original_cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-4")
    
    # Optimized: economy model
    optimized_cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
    
    savings = original_cost - optimized_cost
    return {
        'original_cost': original_cost,
        'optimized_cost': optimized_cost,
        'savings': savings,
        'savings_percentage': (savings / original_cost) * 100 if original_cost > 0 else 0
    }


def _validate_cost_savings(savings: Dict):
    """Validate cost savings calculations"""
    assert savings['savings'] > Decimal("0"), "Should have positive savings"
    assert savings['original_cost'] > savings['optimized_cost'], "Optimized cost should be lower"
    assert savings['savings_percentage'] > 0, "Should have positive savings percentage"


def _validate_workflow_budget_tracking(tracking: Dict):
    """Validate workflow budget tracking"""
    assert 'initial_budget' in tracking, "Should track initial budget"
    assert 'final_budget' in tracking, "Should track final budget"
    assert tracking['final_budget'] <= tracking['initial_budget'], "Budget should not increase"


def _validate_agent_cost_optimization(result: Dict):
    """Validate agent cost optimization results"""
    assert 'optimal_model' in result, "Should identify optimal model"
    assert result['optimal_model'] is not None, "Optimal model should be selected"
    assert 'result' in result, "Should have execution result"