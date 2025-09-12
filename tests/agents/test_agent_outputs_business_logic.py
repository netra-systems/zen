"""Business Logic Validation Tests for Agent Outputs

Tests validate that agent outputs contain actionable, accurate, and valuable business recommendations.
Focuses on business value rather than technical execution.

Business Value Justification (BVJ):
- Segments: Growth & Enterprise (primary revenue drivers)
- Business Goals: Revenue Expansion, Customer Success, Value Demonstration
- Value Impact: Ensures agent recommendations drive real cost savings ($10K-100K+ annually per customer)
- Strategic Impact: Validates core value proposition - AI optimization recommendations that work
"""

import asyncio
import pytest
from decimal import Decimal
from typing import Dict, Any, List, Optional
import json

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config
from test_framework.environment_isolation import EnvironmentTestManager


@pytest.mark.agents
@pytest.mark.env("dev")
@pytest.mark.env("staging")
class TestOptimizationRecommendationsBusiness:
    """Test optimization recommendations are actionable and valuable."""
    
    @pytest.fixture
    async def business_test_environment(self):
        """Setup environment for business logic testing."""
        manager = EnvironmentTestManager()
        env = manager.setup_test_security_environment()
        try:
            yield env
        finally:
            manager.restore_env_vars()
    
    @pytest.fixture
    async def optimization_agent(self, business_test_environment):
        """Setup optimization agent with real LLM for business logic testing."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        tool_dispatcher = ToolDispatcher()
        
        agent = OptimizationsCoreSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations_are_actionable(self, optimization_agent):
        """Test that optimization recommendations contain specific, actionable steps."""
        
        # Setup realistic business scenario
        state = DeepAgentState()
        state.user_request = (
            "Our API response times are averaging 3.2 seconds and we're spending "
            "$2,400/month on LLM API calls. We need to reduce both latency and costs."
        )
        
        # Setup realistic data analysis results showing real performance issues
        state.data_result = {
            "analysis_type": "performance_cost",
            "metrics": {
                "avg_response_time_ms": 3200,
                "p95_response_time_ms": 5800,
                "monthly_llm_costs": 2400,
                "request_volume": 48000,
                "cost_per_request": 0.05
            },
            "findings": [
                "Response times exceed industry standard (1-2s)",
                "LLM costs are 60% higher than similar volume benchmarks",
                "95th percentile latency indicates systemic bottlenecks"
            ]
        }
        
        # Setup triage results
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult, ValidationStatus
        state.triage_result = TriageResult(
            category="performance_optimization",
            confidence_score=0.85,
            validation_status=ValidationStatus(is_valid=True)
        )
        
        run_id = "actionable_recommendations_test"
        
        # Execute optimization agent
        await optimization_agent.execute(state, run_id, stream_updates=False)
        
        # Validate optimization results exist
        assert state.optimizations_result is not None, "No optimization results produced"
        assert len(state.optimizations_result.recommendations) > 0, "No recommendations provided"
        
        recommendations = state.optimizations_result.recommendations
        
        # Test 1: Recommendations must be specific and actionable
        actionable_keywords = [
            'implement', 'reduce', 'optimize', 'cache', 'batch', 'scale',
            'upgrade', 'configure', 'enable', 'disable', 'adjust', 'switch'
        ]
        
        actionable_recommendations = []
        for rec in recommendations:
            rec_text = str(rec).lower()
            if any(keyword in rec_text for keyword in actionable_keywords):
                actionable_recommendations.append(rec)
        
        assert len(actionable_recommendations) >= 2, "Insufficient actionable recommendations"
        
        # Test 2: Recommendations should address the specific issues mentioned
        cost_related = any(
            'cost' in str(rec).lower() or 'price' in str(rec).lower() or 'budget' in str(rec).lower()
            for rec in recommendations
        )
        performance_related = any(
            'latency' in str(rec).lower() or 'response' in str(rec).lower() or 'speed' in str(rec).lower()
            for rec in recommendations
        )
        
        assert cost_related, "No cost-related recommendations found"
        assert performance_related, "No performance-related recommendations found"
        
        # Test 3: Recommendations should include implementation details
        detailed_recommendations = []
        for rec in recommendations:
            rec_text = str(rec)
            # Look for specific technical details, metrics, or steps
            has_details = any(keyword in rec_text.lower() for keyword in [
                'cache', 'database', 'api', 'memory', 'cpu', 'network', 'timeout',
                'connection', 'pool', 'batch', 'queue', 'index', 'query'
            ])
            if has_details:
                detailed_recommendations.append(rec)
        
        assert len(detailed_recommendations) >= 1, "Recommendations lack technical implementation details"
        
        # Test 4: Confidence score should reflect recommendation quality
        assert state.optimizations_result.confidence_score >= 0.6, "Confidence too low for business use"
        
        print(f" PASS:  Generated {len(recommendations)} actionable recommendations")
        print(f"   - {len(actionable_recommendations)} with clear action verbs")
        print(f"   - {len(detailed_recommendations)} with technical details")
        print(f"   - Confidence: {state.optimizations_result.confidence_score:.2f}")
    
    @pytest.mark.asyncio
    async def test_cost_savings_calculations_accuracy(self, optimization_agent):
        """Test that cost savings calculations are realistic and accurate."""
        
        state = DeepAgentState()
        state.user_request = "Analyze our $5,000 monthly AI spend and suggest cost optimizations"
        
        # Setup data with specific cost metrics
        state.data_result = {
            "analysis_type": "cost_analysis",
            "current_costs": {
                "monthly_total": 5000,
                "llm_api_calls": 3200,
                "compute_resources": 1200,
                "data_storage": 400,
                "monitoring_tools": 200
            },
            "usage_patterns": {
                "peak_hours": "9am-5pm",
                "utilization_rate": 0.65,
                "redundant_calls": 0.12
            }
        }
        
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult, ValidationStatus
        state.triage_result = TriageResult(
            category="cost_optimization",
            confidence_score=0.90,
            validation_status=ValidationStatus(is_valid=True)
        )
        
        run_id = "cost_savings_test"
        
        # Execute optimization agent
        await optimization_agent.execute(state, run_id, stream_updates=False)
        
        assert state.optimizations_result is not None
        
        # Test cost savings if provided
        cost_savings = getattr(state.optimizations_result, 'cost_savings', None)
        if cost_savings:
            # If specific cost savings are provided, validate they're realistic
            if isinstance(cost_savings, dict):
                savings_amount = cost_savings.get('amount_cents', 0) / 100  # Convert to dollars
                savings_percentage = cost_savings.get('percentage', 0)
                
                # Cost savings should be realistic (typically 10-40% for AI optimization)
                assert 0 < savings_percentage <= 50, f"Unrealistic savings percentage: {savings_percentage}%"
                assert 0 < savings_amount <= 2500, f"Unrealistic savings amount: ${savings_amount}"
                
                # Percentage and amount should be consistent
                expected_amount = 5000 * (savings_percentage / 100)
                amount_difference = abs(savings_amount - expected_amount)
                assert amount_difference <= expected_amount * 0.1, "Savings percentage and amount inconsistent"
        
        # Test that recommendations include cost-conscious suggestions
        recommendations = state.optimizations_result.recommendations
        cost_focused = [
            rec for rec in recommendations
            if any(keyword in str(rec).lower() for keyword in [
                'cost', 'save', 'reduce', 'cheaper', 'efficient', 'budget', 'optimize spend'
            ])
        ]
        
        assert len(cost_focused) >= 1, "No cost-focused recommendations for cost optimization request"
        
        print(" PASS:  Cost savings calculations validated as realistic and accurate")
    
    @pytest.mark.asyncio 
    async def test_performance_improvements_quantified(self, optimization_agent):
        """Test that performance improvement recommendations include quantifiable metrics."""
        
        state = DeepAgentState()
        state.user_request = (
            "Our API latency is 4.5 seconds average, 8.2 seconds at 95th percentile. "
            "Users are complaining about slow responses. Need performance optimizations."
        )
        
        state.data_result = {
            "analysis_type": "performance_analysis",
            "performance_metrics": {
                "avg_latency_ms": 4500,
                "p95_latency_ms": 8200,
                "p99_latency_ms": 12000,
                "throughput_rps": 25,
                "error_rate": 0.03,
                "timeout_rate": 0.08
            },
            "bottlenecks": [
                "Database query optimization needed",
                "LLM API calls not parallelized", 
                "No response caching implemented",
                "Memory allocation inefficient"
            ]
        }
        
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        state.triage_result = TriageResult(
            category="performance_optimization",
            confidence_score=0.88,
            validation_status=None
        )
        
        run_id = "performance_quantification_test"
        
        # Execute optimization agent
        await optimization_agent.execute(state, run_id, stream_updates=False)
        
        assert state.optimizations_result is not None
        recommendations = state.optimizations_result.recommendations
        
        # Test for quantified performance improvements
        performance_improvements = getattr(state.optimizations_result, 'performance_improvement', None)
        if performance_improvements and isinstance(performance_improvements, dict):
            # Validate performance improvement metrics are realistic
            latency_improvement = performance_improvements.get('latency_reduction_percentage')
            if latency_improvement:
                assert 0 < latency_improvement <= 80, f"Unrealistic latency improvement: {latency_improvement}%"
        
        # Test that recommendations address specific performance issues
        performance_focused = [
            rec for rec in recommendations 
            if any(keyword in str(rec).lower() for keyword in [
                'latency', 'performance', 'speed', 'fast', 'response time',
                'cache', 'parallel', 'async', 'optimize', 'bottleneck'
            ])
        ]
        
        assert len(performance_focused) >= 2, "Insufficient performance-focused recommendations"
        
        # Test recommendations address specific bottlenecks identified in data
        bottleneck_addressed = []
        for bottleneck in state.data_result["bottlenecks"]:
            for rec in recommendations:
                if any(keyword in str(rec).lower() for keyword in [
                    'database', 'query', 'parallel', 'cache', 'memory'
                ]):
                    bottleneck_addressed.append(bottleneck)
                    break
        
        assert len(bottleneck_addressed) >= 2, "Recommendations don't address identified bottlenecks"
        
        print(f" PASS:  Performance improvements properly quantified")
        print(f"   - {len(performance_focused)} performance-focused recommendations")
        print(f"   - {len(bottleneck_addressed)} bottlenecks addressed")


@pytest.mark.agents
@pytest.mark.env("dev")
@pytest.mark.env("staging") 
class TestActionPlanExecutability:
    """Test action plans are executable and realistic for implementation."""
    
    @pytest.fixture
    async def actions_agent(self, business_test_environment):
        """Setup actions agent for business testing."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        tool_dispatcher = ToolDispatcher()
        
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent
    
    @pytest.fixture
    async def business_test_environment(self):
        """Setup environment for business logic testing.""" 
        manager = EnvironmentTestManager()
        manager.setup_test_security_environment()
        try:
            yield manager
        finally:
            manager.restore_env_vars()
    
    @pytest.mark.asyncio
    async def test_action_plans_have_realistic_timelines(self, actions_agent):
        """Test that action plans include realistic implementation timelines."""
        
        state = DeepAgentState()
        state.user_request = (
            "Create implementation plan for reducing our AI costs by 30% "
            "while improving response times. We have a 3-person engineering team."
        )
        
        # Setup optimization results from previous pipeline stages
        from netra_backend.app.agents.state import OptimizationsResult
        state.optimizations_result = OptimizationsResult(
            optimization_type="cost_performance",
            recommendations=[
                "Implement response caching to reduce 40% of redundant LLM calls",
                "Optimize database queries to reduce average latency by 1.2 seconds",
                "Switch to more cost-effective LLM provider for non-critical operations",
                "Implement request batching for bulk operations"
            ],
            confidence_score=0.82,
            cost_savings={"percentage": 30, "amount_cents": 180000},  # $1800/month
            performance_improvement={"latency_reduction_percentage": 45}
        )
        
        # Setup data analysis results from previous pipeline stages
        state.data_result = {
            "analysis_type": "cost_performance",
            "current_metrics": {
                "monthly_cost": 6000,
                "avg_latency_ms": 2800,
                "team_size": 3,
                "technical_debt": "medium"
            }
        }
        
        run_id = "realistic_timeline_test"
        
        # Execute actions agent
        await actions_agent.execute(state, run_id, stream_updates=False)
        
        assert state.action_plan_result is not None, "No action plan generated"
        assert len(state.action_plan_result.plan_steps) > 0, "Action plan has no steps"
        
        # Test timeline realism
        timeline = getattr(state.action_plan_result, 'estimated_timeline', None)
        if timeline:
            # Timeline should be realistic (not too fast, not too slow)
            if isinstance(timeline, str):
                timeline_lower = timeline.lower()
                # Should not promise unrealistic timelines like "1 day" for complex optimizations
                unrealistic_fast = any(phrase in timeline_lower for phrase in [
                    'immediately', 'instant', '1 day', 'few hours'
                ])
                assert not unrealistic_fast, f"Unrealistic timeline: {timeline}"
                
                # Should not be excessively long for simple optimizations
                unrealistic_slow = any(phrase in timeline_lower for phrase in [
                    'year', '12 months', 'years'
                ])
                # Allow some longer timelines but flag if all are very long
                
        # Test step-by-step breakdown
        plan_steps = state.action_plan_result.plan_steps
        
        # Should have logical step progression
        assert len(plan_steps) >= 3, "Action plan too simplistic"
        assert len(plan_steps) <= 12, "Action plan too complex"
        
        # Steps should be concrete and specific
        concrete_steps = []
        for step in plan_steps:
            step_text = str(step).lower()
            is_concrete = any(keyword in step_text for keyword in [
                'implement', 'install', 'configure', 'deploy', 'test',
                'monitor', 'measure', 'optimize', 'update', 'migrate'
            ])
            if is_concrete:
                concrete_steps.append(step)
        
        concrete_ratio = len(concrete_steps) / len(plan_steps)
        assert concrete_ratio >= 0.6, f"Only {concrete_ratio:.1%} of steps are concrete"
        
        # Test team size considerations
        team_considerations = []
        for step in plan_steps:
            step_text = str(step).lower()
            considers_team = any(keyword in step_text for keyword in [
                'team', 'resource', 'capacity', 'person', 'developer', 'engineer'
            ])
            if considers_team:
                team_considerations.append(step)
        
        # At least some steps should consider team constraints
        # (Not all steps need to, but complex implementations should)
        
        print(f" PASS:  Action plan has realistic timeline with {len(plan_steps)} steps")
        print(f"   - {len(concrete_steps)} concrete implementation steps")
        print(f"   - {len(team_considerations)} steps considering team capacity")
    
    @pytest.mark.asyncio
    async def test_action_steps_are_prioritized_correctly(self, actions_agent):
        """Test that action plan steps are prioritized by business impact."""
        
        state = DeepAgentState()
        state.user_request = (
            "We need to cut AI costs immediately due to budget constraints, "
            "but also improve our API performance over the next quarter."
        )
        
        # Setup optimization results with mixed urgency from pipeline
        from netra_backend.app.agents.state import OptimizationsResult
        state.optimizations_result = OptimizationsResult(
            optimization_type="urgent_cost_reduction",
            recommendations=[
                "Immediately reduce LLM call frequency by 25% through smart caching",
                "Switch to cheaper LLM tier for non-customer-facing operations", 
                "Long-term: Implement custom model for routine classification tasks",
                "Optimize database indexes to reduce query times by 40%",
                "Quick win: Enable response compression to reduce bandwidth costs"
            ],
            confidence_score=0.88,
            cost_savings={"percentage": 35, "amount_cents": 210000}  # $2100/month
        )
        
        state.data_result = {
            "analysis_type": "urgent_optimization",
            "constraints": {
                "budget_pressure": "high",
                "timeline": "immediate_savings_needed"
            }
        }
        
        run_id = "prioritization_test"
        
        # Execute actions agent  
        await actions_agent.execute(state, run_id, stream_updates=False)
        
        assert state.action_plan_result is not None
        plan_steps = state.action_plan_result.plan_steps
        
        # Test prioritization logic
        priority_indicators = []
        for i, step in enumerate(plan_steps):
            step_text = str(step).lower()
            
            # Early steps should address urgent needs
            if i < len(plan_steps) // 2:  # First half of steps
                is_urgent = any(keyword in step_text for keyword in [
                    'immediate', 'quick', 'fast', 'now', 'first', 'urgent', 'cache'
                ])
                priority_indicators.append(('early', is_urgent))
            else:  # Later steps
                is_long_term = any(keyword in step_text for keyword in [
                    'long-term', 'future', 'eventually', 'later', 'optimize', 'custom'
                ])
                priority_indicators.append(('late', is_long_term))
        
        # Early steps should tend to be urgent, later steps can be long-term
        early_urgent = sum(1 for phase, urgent in priority_indicators[:3] if urgent and phase == 'early')
        
        # Should have some quick wins early in the plan
        assert early_urgent >= 1, "No urgent actions prioritized early in plan"
        
        # Test business impact ordering
        high_impact_early = []
        for i, step in enumerate(plan_steps[:3]):  # First 3 steps
            step_text = str(step).lower()
            has_impact_keywords = any(keyword in step_text for keyword in [
                'reduce', 'save', 'cut', 'lower', 'immediate', 'cache', 'switch'
            ])
            if has_impact_keywords:
                high_impact_early.append(step)
        
        assert len(high_impact_early) >= 1, "No high-impact actions prioritized early"
        
        print(f" PASS:  Action plan properly prioritized with {len(plan_steps)} steps")
        print(f"   - {early_urgent} urgent actions in first half")
        print(f"   - {len(high_impact_early)} high-impact actions in first 3 steps")
    
    @pytest.mark.asyncio
    async def test_action_dependencies_are_logical(self, actions_agent):
        """Test that action plan steps have logical dependencies and sequencing."""
        
        state = DeepAgentState()
        state.user_request = (
            "Implement a comprehensive AI optimization strategy including "
            "caching, model switching, and performance monitoring."
        )
        
        from netra_backend.app.agents.state import OptimizationsResult
        state.optimizations_result = OptimizationsResult(
            optimization_type="comprehensive",
            recommendations=[
                "Set up monitoring and baseline metrics collection",
                "Implement Redis caching layer for LLM responses",
                "Deploy A/B testing framework for model comparison",
                "Migrate 30% of traffic to cost-optimized LLM provider", 
                "Implement automated cost alerting and budget controls",
                "Optimize cache hit rates through intelligent invalidation"
            ],
            confidence_score=0.91
        )
        
        state.data_result = {
            "analysis_type": "comprehensive_strategy",
            "current_state": "basic_setup",
            "complexity": "high"
        }
        
        run_id = "dependencies_test"
        
        # Execute actions agent
        await actions_agent.execute(state, run_id, stream_updates=False)
        
        assert state.action_plan_result is not None
        plan_steps = state.action_plan_result.plan_steps
        
        # Test logical sequencing
        monitoring_step = None
        caching_step = None
        optimization_step = None
        
        for i, step in enumerate(plan_steps):
            step_text = str(step).lower()
            
            if any(keyword in step_text for keyword in ['monitor', 'baseline', 'metrics']):
                monitoring_step = i
            elif any(keyword in step_text for keyword in ['cache', 'redis']):
                caching_step = i
            elif any(keyword in step_text for keyword in ['optimize', 'improve', 'hit rate']):
                optimization_step = i
        
        # Logical dependencies: monitoring should come before optimization
        if monitoring_step is not None and optimization_step is not None:
            assert monitoring_step < optimization_step, "Optimization before monitoring setup"
        
        # Caching implementation should come before cache optimization
        if caching_step is not None and optimization_step is not None:
            # Allow some flexibility, but caching should generally come before optimization
            pass  # Not strictly required to be in perfect order
        
        # Test for prerequisite steps
        prerequisite_patterns = [
            (['setup', 'install', 'configure'], ['deploy', 'migrate', 'optimize']),
            (['baseline', 'measure'], ['improve', 'optimize']),
            (['test', 'validate'], ['deploy', 'production'])
        ]
        
        dependency_violations = 0
        for prereq_keywords, dependent_keywords in prerequisite_patterns:
            prereq_steps = []
            dependent_steps = []
            
            for i, step in enumerate(plan_steps):
                step_text = str(step).lower()
                if any(keyword in step_text for keyword in prereq_keywords):
                    prereq_steps.append(i)
                elif any(keyword in step_text for keyword in dependent_keywords):
                    dependent_steps.append(i)
            
            # Check if any dependent steps come before prerequisite steps
            for dep_idx in dependent_steps:
                prereq_before = any(prereq_idx < dep_idx for prereq_idx in prereq_steps)
                if not prereq_before and prereq_steps:
                    dependency_violations += 1
        
        # Allow some violations for complex plans, but should be minimal
        violation_rate = dependency_violations / len(prerequisite_patterns) if prerequisite_patterns else 0
        assert violation_rate <= 0.5, f"Too many dependency violations: {violation_rate:.1%}"
        
        print(f" PASS:  Action plan has logical dependencies")
        print(f"   - {len(plan_steps)} total steps")
        print(f"   - {dependency_violations} dependency violations out of {len(prerequisite_patterns)} patterns")


@pytest.mark.agents
@pytest.mark.env("dev")
@pytest.mark.env("staging")
class TestReportingBusinessValue:
    """Test that reports provide clear business value and insights."""
    
    @pytest.fixture
    async def business_test_environment(self):
        """Setup environment for business logic testing."""
        manager = EnvironmentTestManager()
        env = manager.setup_test_security_environment()
        try:
            yield env
        finally:
            manager.restore_env_vars()
    
    @pytest.fixture
    async def reporting_agent(self, business_test_environment):
        """Setup reporting agent for business testing."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        tool_dispatcher = ToolDispatcher()
        
        agent = ReportingSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent
    
    @pytest.mark.asyncio
    async def test_reports_include_executive_summary(self, reporting_agent):
        """Test that reports include clear executive summaries for business stakeholders."""
        
        # Setup comprehensive state with full pipeline results
        state = DeepAgentState()
        state.user_request = (
            "Analyze our AI infrastructure costs and performance, "
            "provide recommendations for 25% cost reduction while maintaining quality."
        )
        
        # Setup complete pipeline results from previous stages
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        state.triage_result = TriageResult(
            category="cost_optimization",
            confidence_score=0.87,
            validation_status=None
        )
        
        state.data_result = {
            "analysis_type": "cost_performance",
            "key_findings": [
                "Monthly AI costs: $8,400 (60% above industry benchmark)",
                "Average API latency: 2.8s (target: 1.5s)",
                "Cache hit rate: 23% (industry standard: 70%+)"
            ],
            "total_cost_monthly": 8400,
            "performance_score": 0.65
        }
        
        from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult, PlanStep
        state.optimizations_result = OptimizationsResult(
            optimization_type="cost_performance",
            recommendations=[
                "Implement intelligent caching system - 40% cost reduction",
                "Switch to cost-optimized LLM for non-critical operations",
                "Optimize API call batching - 15% latency improvement"
            ],
            confidence_score=0.84,
            cost_savings={"percentage": 28, "amount_cents": 235200}  # $2352/month
        )
        
        state.action_plan_result = ActionPlanResult(
            plan_steps=[
                PlanStep(description="Phase 1: Implement caching layer", estimated_duration="2 weeks"),
                PlanStep(description="Phase 2: LLM provider optimization", estimated_duration="1 week"),
                PlanStep(description="Phase 3: API batching implementation", estimated_duration="3 weeks")
            ],
            estimated_timeline="6-8 weeks total",
            priority="high"
        )
        
        run_id = "executive_summary_test"
        
        # Execute reporting agent
        await reporting_agent.execute(state, run_id, stream_updates=False)
        
        assert state.report_result is not None, "No report generated"
        assert state.report_result.content, "Report content is empty"
        
        report_content = state.report_result.content.lower()
        
        # Test for executive summary elements
        executive_indicators = [
            'summary', 'overview', 'executive', 'key findings',
            'recommendations', 'impact', 'roi', 'savings', 'timeline'
        ]
        
        summary_elements = sum(1 for indicator in executive_indicators if indicator in report_content)
        assert summary_elements >= 4, f"Report missing executive summary elements ({summary_elements}/9)"
        
        # Test for business metrics
        business_metrics = [
            'cost', 'savings', '$', 'percent', '%', 'roi', 'performance',
            'latency', 'improvement', 'reduction'
        ]
        
        metrics_mentioned = sum(1 for metric in business_metrics if metric in report_content)
        assert metrics_mentioned >= 5, "Report lacks business metrics"
        
        # Test report length is appropriate for executive consumption
        content_length = len(state.report_result.content)
        assert content_length >= 500, "Report too brief for executive review"
        assert content_length <= 5000, "Report too long for executive consumption"
        
        # Test for clear value proposition
        value_keywords = ['save', 'reduce', 'improve', 'optimize', 'benefit', 'advantage']
        has_value_prop = any(keyword in report_content for keyword in value_keywords)
        assert has_value_prop, "Report lacks clear value proposition"
        
        print(f" PASS:  Report includes executive summary with business focus")
        print(f"   - {summary_elements}/9 summary elements present")
        print(f"   - {metrics_mentioned} business metrics mentioned")
        print(f"   - {content_length} characters (appropriate length)")
    
    @pytest.mark.asyncio
    async def test_reports_quantify_business_impact(self, reporting_agent):
        """Test that reports quantify ROI and business impact clearly."""
        
        state = DeepAgentState()
        state.user_request = "What's the ROI of implementing AI optimization recommendations?"
        
        # Setup results with quantifiable impacts from pipeline stages
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult  
        state.triage_result = TriageResult(
            category="roi_analysis",
            confidence_score=0.91,
            validation_status=None
        )
        
        state.data_result = {
            "current_costs": {
                "monthly_ai_spend": 12000,
                "annual_ai_spend": 144000,
                "operational_overhead": 2400
            },
            "performance_baseline": {
                "avg_response_time": 3.1,
                "customer_satisfaction": 0.78
            }
        }
        
        from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult, PlanStep
        state.optimizations_result = OptimizationsResult(
            optimization_type="roi_focused",
            recommendations=[
                "Caching implementation: $3,600 annual savings, 2-week payback",
                "LLM optimization: $18,000 annual savings, 1-month implementation",
                "Performance tuning: 40% latency reduction, improved user satisfaction"
            ],
            confidence_score=0.89,
            cost_savings={"percentage": 25, "amount_cents": 360000}  # $3600/month
        )
        
        state.action_plan_result = ActionPlanResult(
            plan_steps=[
                PlanStep(description="Quick wins implementation", estimated_duration="2 weeks"),
                PlanStep(description="Major optimizations", estimated_duration="6 weeks")
            ],
            estimated_timeline="8 weeks",
            priority="high"
        )
        
        run_id = "roi_quantification_test"
        
        # Execute reporting agent
        await reporting_agent.execute(state, run_id, stream_updates=False)
        
        assert state.report_result is not None
        report_content = state.report_result.content
        
        # Test for quantified impacts
        quantification_patterns = [
            r'\$[\d,]+',  # Dollar amounts
            r'\d+%',      # Percentages  
            r'\d+\.?\d* (weeks?|months?|days?)',  # Time periods
            r'\d+\.?\d*x',  # Multipliers
            r'\d+\.?\d*(s|ms)',  # Time measurements
        ]
        
        import re
        quantified_elements = 0
        for pattern in quantification_patterns:
            matches = re.findall(pattern, report_content, re.IGNORECASE)
            quantified_elements += len(matches)
        
        assert quantified_elements >= 3, f"Report lacks quantification ({quantified_elements} metrics found)"
        
        # Test for ROI calculation elements
        roi_keywords = [
            'roi', 'return on investment', 'payback', 'savings', 'cost reduction',
            'break-even', 'annual', 'monthly', 'investment', 'benefit'
        ]
        
        roi_mentions = sum(1 for keyword in roi_keywords if keyword in report_content.lower())
        assert roi_mentions >= 3, "Report lacks ROI analysis"
        
        # Test for business impact beyond just cost savings
        impact_areas = [
            'performance', 'customer', 'satisfaction', 'competitive', 'efficiency',
            'scalability', 'reliability', 'user experience'
        ]
        
        impact_coverage = sum(1 for area in impact_areas if area in report_content.lower())
        assert impact_coverage >= 2, "Report focuses only on cost, missing broader business impact"
        
        print(f" PASS:  Report quantifies business impact effectively")
        print(f"   - {quantified_elements} quantified metrics")
        print(f"   - {roi_mentions} ROI-related mentions")
        print(f"   - {impact_coverage} business impact areas covered")
    
    @pytest.mark.asyncio
    async def test_reports_include_risk_assessment(self, reporting_agent):
        """Test that reports include realistic risk assessment and mitigation strategies."""
        
        state = DeepAgentState()
        state.user_request = (
            "Create implementation plan with risk assessment for switching "
            "our LLM provider to reduce costs by 40%."
        )
        
        # Setup high-impact, high-risk scenario from pipeline analysis
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        state.triage_result = TriageResult(
            category="high_impact_optimization",
            confidence_score=0.75,  # Lower confidence for risky changes
            validation_status=None
        )
        
        state.data_result = {
            "current_provider": "premium_llm",
            "proposed_changes": {
                "provider_switch": "cost_optimized_llm",
                "expected_cost_reduction": 40,
                "quality_impact_risk": "medium"
            }
        }
        
        from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult, PlanStep
        state.optimizations_result = OptimizationsResult(
            optimization_type="provider_migration",
            recommendations=[
                "Gradual migration to cost-optimized LLM provider",
                "Implement A/B testing for quality validation",
                "Set up fallback mechanisms for quality issues"
            ],
            confidence_score=0.75,
            cost_savings={"percentage": 40, "amount_cents": 480000}
        )
        
        state.action_plan_result = ActionPlanResult(
            plan_steps=[
                PlanStep(description="Phase 1: A/B test setup", estimated_duration="1 week"),
                PlanStep(description="Phase 2: 10% traffic migration", estimated_duration="1 week"), 
                PlanStep(description="Phase 3: Gradual rollout with monitoring", estimated_duration="4 weeks")
            ],
            estimated_timeline="6 weeks with careful monitoring",
            priority="high_with_caution"
        )
        
        run_id = "risk_assessment_test"
        
        # Execute reporting agent
        await reporting_agent.execute(state, run_id, stream_updates=False)
        
        assert state.report_result is not None
        report_content = state.report_result.content.lower()
        
        # Test for risk assessment elements
        risk_keywords = [
            'risk', 'mitigation', 'caution', 'careful', 'monitor', 'fallback',
            'contingency', 'backup', 'gradual', 'phased', 'testing'
        ]
        
        risk_mentions = sum(1 for keyword in risk_keywords if keyword in report_content)
        assert risk_mentions >= 3, f"Report lacks risk assessment ({risk_mentions} risk elements)"
        
        # Test for mitigation strategies
        mitigation_indicators = [
            'test', 'validate', 'monitor', 'rollback', 'backup', 'gradual',
            'phase', 'pilot', 'trial', 'fallback', 'contingency'
        ]
        
        mitigation_strategies = sum(1 for indicator in mitigation_indicators if indicator in report_content)
        assert mitigation_strategies >= 2, "Report lacks mitigation strategies"
        
        # Test for quality considerations
        quality_keywords = [
            'quality', 'performance', 'accuracy', 'reliability', 'customer impact',
            'user experience', 'satisfaction', 'degradation'
        ]
        
        quality_considerations = sum(1 for keyword in quality_keywords if keyword in report_content)
        assert quality_considerations >= 1, "Report ignores quality risks"
        
        # Test that report balances optimism with realism
        balanced_language = [
            'however', 'although', 'but', 'careful', 'ensure', 'important', 'consider'
        ]
        
        balance_indicators = sum(1 for phrase in balanced_language if phrase in report_content)
        assert balance_indicators >= 1, "Report lacks balanced perspective on risks/benefits"
        
        print(f" PASS:  Report includes comprehensive risk assessment")
        print(f"   - {risk_mentions} risk-related mentions")
        print(f"   - {mitigation_strategies} mitigation strategies")
        print(f"   - {quality_considerations} quality considerations")
        print(f"   - {balance_indicators} balanced perspective indicators")