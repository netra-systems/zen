"""
Test Agent Execution Business Logic Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Core product functionality and value delivery
- Value Impact: Ensures agents deliver consistent business value to users
- Strategic Impact: Foundation of competitive advantage and user satisfaction

CRITICAL REQUIREMENTS:
- Tests real agent execution with business logic validation
- Validates agent output quality and consistency
- Ensures proper resource allocation and limits
- No mocks - uses real agent execution system
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.business.agent_quality_validator import AgentQualityValidator
from netra_backend.app.business.usage_tracker import UsageTracker


class TestAgentExecutionBusinessLogicComprehensive(SSotBaseTestCase):
    """
    Comprehensive agent execution business logic tests.
    
    Tests critical business logic that determines product value:
    - Agent execution quality and consistency
    - Business rule enforcement and validation
    - Resource allocation and usage tracking
    - Cross-tier functionality and limits
    - Output quality and user value delivery
    """
    
    def __init__(self):
        """Initialize agent execution business logic test suite."""
        super().__init__()
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"agent_business_{uuid.uuid4().hex[:8]}"
        
    async def setup_agent_system(self) -> tuple:
        """Set up agent execution system with business logic components."""
        agent_registry = get_agent_registry()
        execution_engine = ExecutionEngine()
        quality_validator = AgentQualityValidator()
        usage_tracker = UsageTracker()
        
        await execution_engine.initialize()
        await quality_validator.initialize()
        await usage_tracker.initialize()
        
        return agent_registry, execution_engine, quality_validator, usage_tracker
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_quality_and_business_value_validation(self):
        """
        Test agent execution delivers consistent quality and business value.
        
        BUSINESS CRITICAL: Agent quality directly impacts customer satisfaction.
        Poor agent responses reduce customer retention and expansion.
        """
        agent_registry, execution_engine, quality_validator, usage_tracker = await self.setup_agent_system()
        
        try:
            # Test different agent types for quality consistency
            agent_test_scenarios = [
                {
                    "agent_type": "triage_agent",
                    "user_query": "Help me optimize my cloud spending and reduce costs",
                    "expected_capabilities": ["cost_analysis", "optimization_recommendations"],
                    "quality_metrics": {
                        "min_response_length": 100,
                        "should_contain_keywords": ["cost", "optimize", "savings"],
                        "should_provide_actionable_advice": True,
                        "response_time_sla_ms": 10000
                    }
                },
                {
                    "agent_type": "data_analyzer", 
                    "user_query": "Analyze my sales performance data and identify trends",
                    "expected_capabilities": ["data_processing", "trend_analysis", "insights_generation"],
                    "quality_metrics": {
                        "min_response_length": 200,
                        "should_contain_keywords": ["analysis", "trends", "data", "insights"],
                        "should_provide_actionable_advice": True,
                        "response_time_sla_ms": 15000
                    }
                },
                {
                    "agent_type": "optimization_agent",
                    "user_query": "How can I improve my system performance and efficiency?",
                    "expected_capabilities": ["performance_analysis", "optimization_strategies"],
                    "quality_metrics": {
                        "min_response_length": 150,
                        "should_contain_keywords": ["performance", "efficiency", "optimization"],
                        "should_provide_actionable_advice": True, 
                        "response_time_sla_ms": 20000
                    }
                }
            ]
            
            execution_results = []
            
            for scenario in agent_test_scenarios:
                # Create test execution context
                execution_context = {
                    "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
                    "agent_type": scenario["agent_type"],
                    "query": scenario["user_query"],
                    "test_id": f"{self.test_prefix}_{scenario['agent_type']}",
                    "subscription_tier": "mid",  # Standard tier for baseline testing
                    "execution_timeout": scenario["quality_metrics"]["response_time_sla_ms"] / 1000
                }
                
                # Execute agent with timing
                start_time = datetime.now()
                
                execution_result = await execution_engine.execute_agent(
                    agent_type=scenario["agent_type"],
                    user_query=scenario["user_query"],
                    context=execution_context
                )
                
                end_time = datetime.now()
                execution_duration = (end_time - start_time).total_seconds() * 1000  # Convert to ms
                
                # Validate execution success
                assert execution_result.success, \
                    f"Agent execution failed for {scenario['agent_type']}: {execution_result.error}"
                
                # Validate response time SLA
                assert execution_duration < scenario["quality_metrics"]["response_time_sla_ms"], \
                    f"Agent {scenario['agent_type']} exceeded SLA: {execution_duration:.0f}ms > {scenario['quality_metrics']['response_time_sla_ms']}ms"
                
                # Validate response quality
                response_text = execution_result.response
                assert len(response_text) >= scenario["quality_metrics"]["min_response_length"], \
                    f"Response too short for {scenario['agent_type']}: {len(response_text)} < {scenario['quality_metrics']['min_response_length']}"
                
                # Validate keyword presence (business domain relevance)
                response_lower = response_text.lower()
                missing_keywords = []
                
                for keyword in scenario["quality_metrics"]["should_contain_keywords"]:
                    if keyword.lower() not in response_lower:
                        missing_keywords.append(keyword)
                
                assert len(missing_keywords) == 0, \
                    f"Response lacks domain keywords for {scenario['agent_type']}: missing {missing_keywords}"
                
                # Validate actionable advice (business value)
                if scenario["quality_metrics"]["should_provide_actionable_advice"]:
                    actionable_indicators = [
                        "recommend", "suggest", "should", "can", "try", "consider",
                        "step", "action", "implement", "optimize", "improve"
                    ]
                    
                    has_actionable_content = any(
                        indicator in response_lower for indicator in actionable_indicators
                    )
                    
                    assert has_actionable_content, \
                        f"Response lacks actionable advice for {scenario['agent_type']}: {response_text[:200]}..."
                
                # Quality score validation
                quality_score = await quality_validator.calculate_response_quality(
                    agent_type=scenario["agent_type"],
                    user_query=scenario["user_query"],
                    agent_response=response_text,
                    expected_capabilities=scenario["expected_capabilities"]
                )
                
                assert quality_score.overall_score >= 0.7, \
                    f"Quality score too low for {scenario['agent_type']}: {quality_score.overall_score:.2f} < 0.7"
                
                execution_results.append({
                    "scenario": scenario,
                    "result": execution_result,
                    "duration_ms": execution_duration,
                    "quality_score": quality_score
                })
            
            # Validate consistency across agent types
            quality_scores = [r["quality_score"].overall_score for r in execution_results]
            quality_variance = max(quality_scores) - min(quality_scores)
            
            # Quality should be consistent across agent types (variance < 0.3)
            assert quality_variance < 0.3, \
                f"Quality inconsistency across agents: variance {quality_variance:.2f} > 0.3"
            
            # Validate business value metrics
            total_business_value = sum(
                r["quality_score"].business_value_score for r in execution_results
            )
            avg_business_value = total_business_value / len(execution_results)
            
            assert avg_business_value >= 0.75, \
                f"Average business value too low: {avg_business_value:.2f} < 0.75"
                
        finally:
            await usage_tracker.cleanup_test_data(test_prefix=self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_subscription_tier_business_rule_enforcement(self):
        """
        Test business rule enforcement across subscription tiers.
        
        BUSINESS CRITICAL: Tier enforcement protects revenue and prevents abuse.
        Incorrect limits can lead to revenue leakage or customer dissatisfaction.
        """
        agent_registry, execution_engine, quality_validator, usage_tracker = await self.setup_agent_system()
        
        try:
            # Define tier-specific business rules
            tier_rules = {
                "free": {
                    "max_monthly_executions": 10,
                    "max_execution_time_seconds": 30,
                    "allowed_agents": ["triage_agent"],
                    "advanced_features": False,
                    "concurrent_executions": 1,
                    "expected_restrictions": ["advanced_agents", "concurrent_limit", "time_limit"]
                },
                "early": {
                    "max_monthly_executions": 100,
                    "max_execution_time_seconds": 120,
                    "allowed_agents": ["triage_agent", "data_analyzer"],
                    "advanced_features": True,
                    "concurrent_executions": 2,
                    "expected_restrictions": ["execution_limit"]
                },
                "mid": {
                    "max_monthly_executions": 500,
                    "max_execution_time_seconds": 300,
                    "allowed_agents": ["triage_agent", "data_analyzer", "optimization_agent"],
                    "advanced_features": True,
                    "concurrent_executions": 5,
                    "expected_restrictions": []
                },
                "enterprise": {
                    "max_monthly_executions": float('inf'),  # Unlimited
                    "max_execution_time_seconds": 600,
                    "allowed_agents": ["triage_agent", "data_analyzer", "optimization_agent", "research_agent"],
                    "advanced_features": True,
                    "concurrent_executions": 10,
                    "expected_restrictions": []
                }
            }
            
            tier_test_results = []
            
            for tier, rules in tier_rules.items():
                test_user_id = f"tier_test_{tier}_{uuid.uuid4().hex[:8]}"
                
                # Test agent access restrictions
                for agent_type in ["triage_agent", "data_analyzer", "optimization_agent", "research_agent"]:
                    access_check = await execution_engine.check_agent_access(
                        user_id=test_user_id,
                        subscription_tier=tier,
                        agent_type=agent_type
                    )
                    
                    if agent_type in rules["allowed_agents"]:
                        assert access_check.allowed, \
                            f"Tier {tier} should allow access to {agent_type}"
                    else:
                        assert not access_check.allowed, \
                            f"Tier {tier} should NOT allow access to {agent_type}"
                        assert "upgrade" in access_check.restriction_reason.lower(), \
                            f"Restriction reason should mention upgrade for {tier}/{agent_type}"
                
                # Test execution time limits
                if rules["max_execution_time_seconds"] < float('inf'):
                    long_running_context = {
                        "user_id": test_user_id,
                        "subscription_tier": tier,
                        "estimated_duration": rules["max_execution_time_seconds"] + 10,
                        "test_id": f"{self.test_prefix}_timeout_test"
                    }
                    
                    timeout_check = await execution_engine.validate_execution_limits(
                        context=long_running_context
                    )
                    
                    if rules["max_execution_time_seconds"] <= 120:  # Free/Early tiers
                        assert not timeout_check.within_limits, \
                            f"Tier {tier} should reject long executions"
                    else:  # Mid/Enterprise tiers
                        assert timeout_check.within_limits, \
                            f"Tier {tier} should allow longer executions"
                
                # Test concurrent execution limits
                concurrent_contexts = [
                    {
                        "user_id": test_user_id,
                        "subscription_tier": tier,
                        "execution_id": f"concurrent_{i}",
                        "test_id": self.test_prefix
                    }
                    for i in range(rules["concurrent_executions"] + 2)  # Try to exceed limit
                ]
                
                concurrent_results = []
                
                for context in concurrent_contexts:
                    concurrent_check = await execution_engine.check_concurrent_limit(
                        user_id=test_user_id,
                        subscription_tier=tier,
                        context=context
                    )
                    concurrent_results.append(concurrent_check.allowed)
                
                allowed_concurrent = sum(concurrent_results)
                
                assert allowed_concurrent <= rules["concurrent_executions"], \
                    f"Tier {tier} allowed too many concurrent executions: {allowed_concurrent} > {rules['concurrent_executions']}"
                
                # Test monthly usage limits
                if rules["max_monthly_executions"] < float('inf'):
                    # Simulate near-limit usage
                    current_usage = rules["max_monthly_executions"] - 2
                    
                    usage_context = {
                        "user_id": test_user_id,
                        "subscription_tier": tier,
                        "current_monthly_usage": current_usage,
                        "test_id": self.test_prefix
                    }
                    
                    # Should allow execution within limit
                    within_limit_check = await execution_engine.validate_monthly_usage(
                        context=usage_context
                    )
                    assert within_limit_check.within_limits, \
                        f"Tier {tier} should allow execution within monthly limit"
                    
                    # Should reject execution at limit
                    usage_context["current_monthly_usage"] = rules["max_monthly_executions"]
                    at_limit_check = await execution_engine.validate_monthly_usage(
                        context=usage_context
                    )
                    assert not at_limit_check.within_limits, \
                        f"Tier {tier} should reject execution at monthly limit"
                
                tier_test_results.append({
                    "tier": tier,
                    "rules": rules,
                    "test_results": {
                        "agent_access": "validated",
                        "time_limits": "validated",
                        "concurrent_limits": "validated", 
                        "monthly_limits": "validated"
                    }
                })
            
            # Test tier upgrade scenarios
            upgrade_scenarios = [
                {"from": "free", "to": "early"},
                {"from": "early", "to": "mid"},
                {"from": "mid", "to": "enterprise"}
            ]
            
            for scenario in upgrade_scenarios:
                from_tier = scenario["from"]
                to_tier = scenario["to"]
                
                upgrade_user_id = f"upgrade_{from_tier}_to_{to_tier}_{uuid.uuid4().hex[:8]}"
                
                # Test access before upgrade
                before_upgrade = await execution_engine.get_user_capabilities(
                    user_id=upgrade_user_id,
                    subscription_tier=from_tier
                )
                
                # Test access after upgrade  
                after_upgrade = await execution_engine.get_user_capabilities(
                    user_id=upgrade_user_id,
                    subscription_tier=to_tier
                )
                
                # Should have more capabilities after upgrade
                assert len(after_upgrade.allowed_agents) >= len(before_upgrade.allowed_agents), \
                    f"Upgrade {from_tier} to {to_tier} should increase agent access"
                
                assert after_upgrade.max_execution_time >= before_upgrade.max_execution_time, \
                    f"Upgrade {from_tier} to {to_tier} should increase time limits"
                
                assert after_upgrade.concurrent_limit >= before_upgrade.concurrent_limit, \
                    f"Upgrade {from_tier} to {to_tier} should increase concurrent limits"
                
        finally:
            await usage_tracker.cleanup_test_data(test_prefix=self.test_prefix)


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])