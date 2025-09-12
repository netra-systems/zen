
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Golden Path Tests for ReportingSubAgent UserExecutionContext Migration - Issue #354

CRITICAL BUSINESS VALUE PROTECTION: Golden Path represents the core revenue-generating
workflow that protects $500K+ ARR. ReportingSubAgent is the final step in the Golden Path
that delivers customer value through comprehensive AI-generated reports.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - All customers depend on reporting functionality
- Business Goal: Ensure core revenue workflow continues working after security migration
- Value Impact: Protects the primary value delivery mechanism (AI-powered reports)
- Revenue Impact: Prevents $500K+ ARR loss from broken Golden Path after migration

GOLDEN PATH WORKFLOW:
1. User submits analysis request
2. System processes through multiple agents (Triage  ->  Data  ->  Optimizations  ->  Action Plan)
3. ReportingSubAgent generates final comprehensive report  <-  CRITICAL POINT
4. Report delivered to user with actionable insights

MIGRATION VALIDATION:
These tests ensure that migration from DeepAgentState to UserExecutionContext maintains
100% Golden Path functionality while fixing security vulnerabilities.

EXPECTED BEHAVIOR:
- BEFORE Migration: Tests may FAIL due to parameter type issues during transition
- AFTER Migration: Tests must PASS - Golden Path works with UserExecutionContext
- CRITICAL: No loss of business functionality during security fix
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass
class GoldenPathScenario:
    """Represents a Golden Path user scenario."""
    scenario_name: str
    user_profile: Dict[str, Any]
    analysis_results: Dict[str, Any]
    expected_outcomes: List[str]
    business_value: str
    revenue_segment: str


@dataclass
class GoldenPathResult:
    """Results from Golden Path execution."""
    scenario_name: str
    execution_success: bool
    report_generated: bool
    business_value_delivered: bool
    user_satisfaction_score: float
    execution_time_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TestReportingAgentUserContextGoldenPath(SSotAsyncTestCase):
    """
    Golden Path tests ensuring ReportingSubAgent works with UserExecutionContext.
    
    These tests validate that the core revenue-generating workflow continues to work
    after security migration, maintaining 100% business value delivery.
    """

    def setup_method(self, method=None):
        """Set up Golden Path test environment with realistic business scenarios."""
        super().setup_method(method)
        
        # Define Golden Path scenarios representing real customer use cases
        self.golden_path_scenarios = [
            GoldenPathScenario(
                scenario_name="enterprise_cost_optimization",
                user_profile={
                    "segment": "Enterprise",
                    "company": "TechCorp Industries",
                    "role": "AI Operations Director",
                    "goal": "Reduce AI infrastructure costs by 30%"
                },
                analysis_results={
                    "triage_result": {
                        "priority": "high",
                        "focus_areas": ["cost optimization", "performance tuning"],
                        "estimated_savings": "$50K annually"
                    },
                    "data_result": {
                        "current_spend": "$15K monthly",
                        "usage_patterns": "Heavy batch processing during business hours",
                        "inefficiencies": ["Unused GPU time", "Oversized instances"]
                    },
                    "optimizations_result": {
                        "recommendations": [
                            "Switch to spot instances for batch jobs",
                            "Implement auto-scaling",
                            "Optimize model inference"
                        ],
                        "potential_savings": "35% cost reduction"
                    },
                    "action_plan_result": {
                        "timeline": "3 months implementation",
                        "phases": ["Infrastructure audit", "Optimization implementation", "Monitoring setup"],
                        "success_metrics": "30% cost reduction, maintained performance"
                    }
                },
                expected_outcomes=[
                    "comprehensive_cost_analysis",
                    "specific_optimization_recommendations", 
                    "implementation_roadmap",
                    "roi_projections"
                ],
                business_value="High-value enterprise customer retention",
                revenue_segment="Enterprise ($50K+ ARR)"
            ),
            
            GoldenPathScenario(
                scenario_name="startup_growth_optimization",
                user_profile={
                    "segment": "Early Stage",
                    "company": "AI Startup Inc",
                    "role": "CTO",
                    "goal": "Scale AI infrastructure efficiently"
                },
                analysis_results={
                    "triage_result": {
                        "priority": "medium",
                        "focus_areas": ["scalability", "cost management"],
                        "growth_stage": "Series A"
                    },
                    "data_result": {
                        "current_usage": "Growing 50% month over month",
                        "challenges": "Unpredictable costs, performance bottlenecks",
                        "budget_constraints": "Limited runway"
                    },
                    "optimizations_result": {
                        "recommendations": [
                            "Implement usage monitoring",
                            "Set up cost alerts", 
                            "Optimize for growth patterns"
                        ],
                        "growth_enablers": "Predictable scaling, cost visibility"
                    },
                    "action_plan_result": {
                        "immediate_actions": ["Cost tracking setup", "Performance baselines"],
                        "growth_preparation": ["Auto-scaling rules", "Budget forecasting"],
                        "success_metrics": "Predictable costs, 2x scale capacity"
                    }
                },
                expected_outcomes=[
                    "growth_readiness_assessment",
                    "cost_predictability_plan",
                    "scaling_strategy",
                    "funding_runway_extension"
                ],
                business_value="Startup success and expansion potential",
                revenue_segment="Early Stage ($5K-15K ARR)"
            ),
            
            GoldenPathScenario(
                scenario_name="mid_market_efficiency_optimization",
                user_profile={
                    "segment": "Mid-Market",
                    "company": "GrowthCorp Solutions",
                    "role": "VP Engineering",
                    "goal": "Improve AI system efficiency and reliability"
                },
                analysis_results={
                    "triage_result": {
                        "priority": "high",
                        "focus_areas": ["reliability", "performance optimization"],
                        "current_pain_points": "Inconsistent performance, manual processes"
                    },
                    "data_result": {
                        "performance_metrics": "80% uptime, variable response times",
                        "bottlenecks": "Database queries, model loading times",
                        "user_impact": "Customer complaints about slow responses"
                    },
                    "optimizations_result": {
                        "recommendations": [
                            "Implement caching layers",
                            "Optimize database queries",
                            "Add performance monitoring"
                        ],
                        "reliability_improvements": "99.5% uptime target"
                    },
                    "action_plan_result": {
                        "quick_wins": ["Query optimization", "Basic monitoring"],
                        "strategic_improvements": ["Architecture redesign", "SLA implementation"],
                        "success_metrics": "99.5% uptime, <200ms response time"
                    }
                },
                expected_outcomes=[
                    "reliability_improvement_plan",
                    "performance_optimization_strategy",
                    "monitoring_and_alerting_setup", 
                    "customer_satisfaction_recovery"
                ],
                business_value="Mid-market customer satisfaction and retention",
                revenue_segment="Mid-Market ($15K-50K ARR)"
            )
        ]
        
        # Track Golden Path execution results
        self.golden_path_results = []
        self.business_value_score = 0.0

    async def test_golden_path_enterprise_cost_optimization_complete_workflow(self):
        """
        Test complete Golden Path workflow for Enterprise cost optimization scenario.
        
        BUSINESS CRITICAL: This scenario represents $50K+ ARR enterprise customers
        EXPECTED: Must work after migration - no loss of business value
        """
        scenario = self.golden_path_scenarios[0]  # Enterprise scenario
        golden_path_result = await self._execute_golden_path_scenario(scenario)
        
        # CRITICAL: Golden Path must succeed after migration
        if not golden_path_result.execution_success:
            assert False, (
                f" ALERT:  GOLDEN PATH FAILURE: Enterprise cost optimization workflow failed after migration. "
                f"Errors: {golden_path_result.errors}. This represents $50K+ ARR customer impact. "
                f"ReportingSubAgent UserExecutionContext migration broke core business workflow."
            )
        
        # Validate business value delivery
        if not golden_path_result.business_value_delivered:
            assert False, (
                f" ALERT:  BUSINESS VALUE LOSS: Enterprise scenario executed but failed to deliver business value. "
                f"Report generated: {golden_path_result.report_generated}. "
                f"User satisfaction: {golden_path_result.user_satisfaction_score}. "
                f"Migration must maintain 100% business functionality."
            )

    async def test_golden_path_startup_growth_optimization_complete_workflow(self):
        """
        Test complete Golden Path workflow for Startup growth optimization scenario.
        
        BUSINESS CRITICAL: This scenario represents high-growth potential customers
        EXPECTED: Must work after migration - critical for business expansion
        """
        scenario = self.golden_path_scenarios[1]  # Startup scenario
        golden_path_result = await self._execute_golden_path_scenario(scenario)
        
        # CRITICAL: Startup workflow must succeed (growth segment is strategic)
        if not golden_path_result.execution_success:
            assert False, (
                f" ALERT:  GOLDEN PATH FAILURE: Startup growth optimization workflow failed after migration. "
                f"Errors: {golden_path_result.errors}. This impacts business growth strategy. "
                f"Startup customers are critical for market expansion and future revenue growth."
            )
        
        # Validate growth enablement
        if golden_path_result.user_satisfaction_score < 8.0:  # 8/10 minimum for growth scenarios
            assert False, (
                f" ALERT:  GROWTH ENABLEMENT FAILURE: Startup scenario satisfaction score "
                f"{golden_path_result.user_satisfaction_score} below minimum 8.0. "
                f"Growth customers require exceptional experience for retention and expansion."
            )

    async def test_golden_path_mid_market_efficiency_optimization_complete_workflow(self):
        """
        Test complete Golden Path workflow for Mid-Market efficiency optimization.
        
        BUSINESS CRITICAL: Mid-market represents stable revenue base
        EXPECTED: Must work after migration - revenue stability depends on this
        """
        scenario = self.golden_path_scenarios[2]  # Mid-market scenario
        golden_path_result = await self._execute_golden_path_scenario(scenario)
        
        # CRITICAL: Mid-market workflow must succeed (revenue stability)
        if not golden_path_result.execution_success:
            assert False, (
                f" ALERT:  GOLDEN PATH FAILURE: Mid-market efficiency optimization workflow failed. "
                f"Errors: {golden_path_result.errors}. This represents stable revenue base impact. "
                f"Mid-market customers are core revenue contributors requiring consistent service."
            )

    async def _execute_golden_path_scenario(self, scenario: GoldenPathScenario) -> GoldenPathResult:
        """Execute a complete Golden Path scenario and measure business value delivery."""
        start_time = time.time()
        result = GoldenPathResult(
            scenario_name=scenario.scenario_name,
            execution_success=False,
            report_generated=False, 
            business_value_delivered=False,
            user_satisfaction_score=0.0,
            execution_time_ms=0.0
        )
        
        try:
            # Create ReportingSubAgent instance
            reporting_agent = ReportingSubAgent()
            
            # Create UserExecutionContext with complete Golden Path data
            user_context = self._create_golden_path_user_context(scenario)
            
            # Execute reporting with full Golden Path context
            with patch.object(reporting_agent, 'emit_agent_started') as mock_started, \
                 patch.object(reporting_agent, 'emit_agent_completed') as mock_completed, \
                 patch.object(reporting_agent, 'emit_thinking') as mock_thinking:
                
                # Configure mocks to track Golden Path events
                mock_started.return_value = None
                mock_completed.return_value = None
                mock_thinking.return_value = None
                
                # Execute with UserExecutionContext (post-migration pattern)
                execution_result = await reporting_agent.execute_modern(
                    context=user_context,
                    stream_updates=True  # Enable WebSocket events for complete Golden Path
                )
                
                # Measure execution time
                execution_time = (time.time() - start_time) * 1000
                result.execution_time_ms = execution_time
                
                # Validate execution success
                if isinstance(execution_result, ExecutionResult):
                    result.execution_success = (execution_result.status == ExecutionStatus.COMPLETED)
                    
                    if execution_result.data:
                        result.report_generated = True
                        
                        # Analyze business value delivery
                        business_value_analysis = self._analyze_business_value_delivery(
                            scenario, execution_result.data
                        )
                        result.business_value_delivered = business_value_analysis['value_delivered']
                        result.user_satisfaction_score = business_value_analysis['satisfaction_score']
                        
                else:
                    # Handle dictionary result (legacy format)
                    if execution_result and isinstance(execution_result, dict):
                        result.execution_success = True
                        result.report_generated = True
                        
                        business_value_analysis = self._analyze_business_value_delivery(
                            scenario, execution_result
                        )
                        result.business_value_delivered = business_value_analysis['value_delivered']
                        result.user_satisfaction_score = business_value_analysis['satisfaction_score']
                
                # Validate WebSocket events were emitted (Golden Path requirement)
                if not (mock_started.called and mock_completed.called):
                    result.warnings.append("WebSocket events not properly emitted")
                
        except Exception as e:
            result.errors.append(f"Golden Path execution failed: {str(e)}")
            result.execution_time_ms = (time.time() - start_time) * 1000
        
        self.golden_path_results.append(result)
        return result

    def _create_golden_path_user_context(self, scenario: GoldenPathScenario) -> UserExecutionContext:
        """Create UserExecutionContext with complete Golden Path analysis results."""
        return UserExecutionContext(
            user_id=UserID(f"{scenario.scenario_name}_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"{scenario.scenario_name}_thread_{uuid.uuid4().hex[:8]}"),
            run_id=RunID(f"{scenario.scenario_name}_run_{uuid.uuid4().hex[:8]}"),
            agent_context={
                "user_request": f"Generate comprehensive optimization report for {scenario.user_profile['company']}",
                "user_profile": scenario.user_profile,
                "golden_path_scenario": scenario.scenario_name,
                "business_segment": scenario.revenue_segment
            },
            audit_metadata={
                "golden_path_test": True,
                "scenario": scenario.scenario_name,
                "business_value": scenario.business_value,
                "revenue_segment": scenario.revenue_segment,
                
                # Complete Golden Path analysis results
                "triage_result": scenario.analysis_results.get("triage_result"),
                "data_result": scenario.analysis_results.get("data_result"),
                "optimizations_result": scenario.analysis_results.get("optimizations_result"), 
                "action_plan_result": scenario.analysis_results.get("action_plan_result")
            },
            metadata={
                # Legacy compatibility - merge all analysis results for ReportingSubAgent
                **scenario.analysis_results,
                "user_request": f"Generate comprehensive optimization report for {scenario.user_profile['company']}"
            }
        )

    def _analyze_business_value_delivery(self, scenario: GoldenPathScenario, 
                                       report_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze whether the generated report delivers expected business value."""
        analysis = {
            "value_delivered": False,
            "satisfaction_score": 0.0,
            "outcome_coverage": 0.0,
            "actionability_score": 0.0,
            "details": {}
        }
        
        if not report_result:
            return analysis
        
        report_str = str(report_result).lower()
        
        # Check coverage of expected outcomes
        outcomes_covered = 0
        for expected_outcome in scenario.expected_outcomes:
            # Convert outcome to searchable terms
            outcome_terms = expected_outcome.replace("_", " ").split()
            
            # Check if outcome terms appear in report
            terms_found = sum(1 for term in outcome_terms if term in report_str)
            if terms_found >= len(outcome_terms) * 0.6:  # 60% term match threshold
                outcomes_covered += 1
        
        analysis["outcome_coverage"] = outcomes_covered / len(scenario.expected_outcomes)
        
        # Check for actionable content
        actionable_indicators = [
            "recommend", "suggest", "should", "implement", "step", "action",
            "next", "timeline", "phase", "priority", "quick win"
        ]
        
        actionable_terms_found = sum(1 for term in actionable_indicators if term in report_str)
        analysis["actionability_score"] = min(1.0, actionable_terms_found / 5.0)  # Max score with 5+ terms
        
        # Check for scenario-specific business value indicators
        business_value_indicators = self._get_scenario_business_indicators(scenario)
        business_terms_found = sum(1 for term in business_value_indicators if term in report_str)
        business_value_score = min(1.0, business_terms_found / len(business_value_indicators))
        
        # Calculate overall satisfaction score (0-10 scale)
        analysis["satisfaction_score"] = (
            analysis["outcome_coverage"] * 4.0 +      # 40% weight on outcome coverage
            analysis["actionability_score"] * 3.0 +   # 30% weight on actionability
            business_value_score * 3.0                # 30% weight on business value
        )
        
        # Determine if business value is delivered (threshold: 7.0/10)
        analysis["value_delivered"] = analysis["satisfaction_score"] >= 7.0
        
        analysis["details"] = {
            "outcomes_covered": f"{outcomes_covered}/{len(scenario.expected_outcomes)}",
            "actionable_terms": actionable_terms_found,
            "business_terms": business_terms_found,
            "report_length": len(report_str)
        }
        
        return analysis

    def _get_scenario_business_indicators(self, scenario: GoldenPathScenario) -> List[str]:
        """Get business value indicators specific to each scenario."""
        indicators = {
            "enterprise_cost_optimization": [
                "cost", "savings", "reduce", "optimize", "efficiency", "roi", "budget"
            ],
            "startup_growth_optimization": [
                "growth", "scale", "runway", "funding", "expand", "sustainable", "monitoring"
            ],
            "mid_market_efficiency_optimization": [
                "reliability", "performance", "uptime", "response time", "customer satisfaction", "sla"
            ]
        }
        
        return indicators.get(scenario.scenario_name, ["optimization", "improvement", "value"])

    async def test_golden_path_performance_requirements(self):
        """
        Test that Golden Path performance meets business requirements after migration.
        
        BUSINESS REQUIREMENT: Reports must generate within acceptable time limits
        EXPECTED: Performance maintained or improved after migration
        """
        # Test all scenarios for performance
        performance_results = []
        
        for scenario in self.golden_path_scenarios:
            result = await self._execute_golden_path_scenario(scenario)
            performance_results.append({
                "scenario": scenario.scenario_name,
                "execution_time": result.execution_time_ms,
                "success": result.execution_success
            })
        
        # Analyze performance requirements
        performance_failures = []
        
        for perf_result in performance_results:
            # Business requirement: Reports must generate within 30 seconds
            max_execution_time_ms = 30000  # 30 seconds
            
            if perf_result["execution_time"] > max_execution_time_ms:
                performance_failures.append(
                    f"{perf_result['scenario']}: {perf_result['execution_time']:.0f}ms "
                    f"(exceeds {max_execution_time_ms}ms limit)"
                )
        
        if performance_failures:
            assert False, (
                f" ALERT:  GOLDEN PATH PERFORMANCE FAILURE: Migration degraded performance beyond "
                f"business requirements. Failures: {performance_failures}. "
                f"UserExecutionContext migration must not impact customer experience."
            )

    async def test_golden_path_business_value_preservation(self):
        """
        Test that business value is preserved across all Golden Path scenarios.
        
        BUSINESS CRITICAL: Migration must not reduce business value delivery
        EXPECTED: 100% business value preservation after migration
        """
        # Execute all scenarios and measure business value
        total_scenarios = len(self.golden_path_scenarios)
        successful_scenarios = 0
        high_value_scenarios = 0
        
        for scenario in self.golden_path_scenarios:
            result = await self._execute_golden_path_scenario(scenario)
            
            if result.execution_success:
                successful_scenarios += 1
                
            if result.business_value_delivered and result.user_satisfaction_score >= 8.0:
                high_value_scenarios += 1
        
        # Calculate business value preservation metrics
        success_rate = successful_scenarios / total_scenarios
        high_value_rate = high_value_scenarios / total_scenarios
        
        # Business requirements
        minimum_success_rate = 1.0      # 100% scenarios must execute successfully
        minimum_high_value_rate = 0.8   # 80% must deliver high business value
        
        if success_rate < minimum_success_rate:
            assert False, (
                f" ALERT:  BUSINESS VALUE DEGRADATION: Success rate {success_rate*100:.1f}% below "
                f"required {minimum_success_rate*100:.1f}%. {total_scenarios - successful_scenarios} "
                f"Golden Path scenarios failed after migration. This represents direct revenue impact."
            )
        
        if high_value_rate < minimum_high_value_rate:
            assert False, (
                f" ALERT:  CUSTOMER SATISFACTION DEGRADATION: High-value delivery rate {high_value_rate*100:.1f}% "
                f"below required {minimum_high_value_rate*100:.1f}%. Migration reduced customer value "
                f"delivery quality. This impacts customer retention and expansion."
            )

    def test_golden_path_userexecutioncontext_integration_completeness(self):
        """
        Test that UserExecutionContext integration is complete and properly structured.
        
        INTEGRATION REQUIREMENT: All Golden Path data must be properly accessible
        EXPECTED: Complete integration with no data loss
        """
        # Test UserExecutionContext structure for Golden Path compatibility
        test_scenario = self.golden_path_scenarios[0]
        user_context = self._create_golden_path_user_context(test_scenario)
        
        # Validate required data structures
        integration_issues = []
        
        # Check that all analysis results are accessible
        required_results = ["triage_result", "data_result", "optimizations_result", "action_plan_result"]
        
        for result_type in required_results:
            # Check in audit_metadata
            if result_type not in user_context.audit_metadata:
                integration_issues.append(f"Missing {result_type} in audit_metadata")
            
            # Check in legacy metadata (compatibility)
            if hasattr(user_context, 'metadata') and result_type not in user_context.metadata:
                integration_issues.append(f"Missing {result_type} in legacy metadata")
        
        # Check user profile accessibility
        if "user_profile" not in user_context.agent_context:
            integration_issues.append("User profile not accessible in agent_context")
        
        # Check Golden Path scenario identification
        if "golden_path_scenario" not in user_context.agent_context:
            integration_issues.append("Golden Path scenario identification missing")
        
        if integration_issues:
            assert False, (
                f" ALERT:  INTEGRATION INCOMPLETENESS: UserExecutionContext integration issues detected: "
                f"{integration_issues}. Golden Path data must be fully accessible after migration."
            )

    def teardown_method(self, method=None):
        """Clean up Golden Path test resources and generate business impact summary."""
        # Calculate overall business impact
        if self.golden_path_results:
            total_results = len(self.golden_path_results)
            successful_results = sum(1 for r in self.golden_path_results if r.execution_success)
            avg_satisfaction = sum(r.user_satisfaction_score for r in self.golden_path_results) / total_results
            
            self.business_value_score = (successful_results / total_results) * (avg_satisfaction / 10.0) * 100.0
        
        # Clear results
        self.golden_path_results.clear()
        
        super().teardown_method(method)