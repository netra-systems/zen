"""
Golden Path Unit Tests: Agent Execution Sequence Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Ensure correct Data→Optimization→Report sequence delivers maximum AI value
- Value Impact: Proper execution order maximizes analysis quality and user satisfaction
- Strategic/Revenue Impact: Critical for $500K+ ARR - correct sequence enables upselling and retention

CRITICAL: This test validates the business logic for the agent execution sequence that delivers
the core AI value proposition. The Data→Optimization→Report sequence is fundamental to
providing actionable insights that justify customer spend and enable business growth.

Key Sequence Areas Tested:
1. Data Agent Execution - Must run first to gather and validate user data
2. Optimization Agent Execution - Must run after data to provide cost/performance insights
3. Report Agent Execution - Must run last to synthesize findings into business value
4. Agent Handoff Logic - Business rules for passing context between agents
5. Execution State Management - Business state tracking throughout the sequence
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
from enum import Enum

# Import business logic components for testing
from test_framework.base import BaseTestCase
from shared.types.core_types import (
    UserID, ThreadID, ExecutionID, AgentID,
    ensure_user_id, ensure_thread_id
)
from shared.types.execution_types import StronglyTypedUserExecutionContext


class AgentType(Enum):
    """Types of agents in the business execution sequence."""
    DATA_AGENT = "data_agent"
    OPTIMIZATION_AGENT = "optimization_agent" 
    REPORT_AGENT = "report_agent"
    SUPERVISOR_AGENT = "supervisor_agent"


class ExecutionPhase(Enum):
    """Business execution phases in the Golden Path sequence."""
    INITIALIZATION = "initialization"
    DATA_COLLECTION = "data_collection"
    DATA_ANALYSIS = "data_analysis"
    OPTIMIZATION_ANALYSIS = "optimization_analysis"
    OPTIMIZATION_RECOMMENDATIONS = "optimization_recommendations"
    REPORT_GENERATION = "report_generation"
    REPORT_FINALIZATION = "report_finalization"
    COMPLETION = "completion"


class BusinessValueMetric(Enum):
    """Business value metrics tracked during execution."""
    DATA_QUALITY_SCORE = "data_quality_score"
    OPTIMIZATION_POTENTIAL = "optimization_potential"
    COST_SAVINGS_IDENTIFIED = "cost_savings_identified"
    ACTIONABILITY_SCORE = "actionability_score"
    USER_SATISFACTION_PREDICTION = "user_satisfaction_prediction"


@dataclass
class AgentExecutionResult:
    """Result of individual agent execution with business context."""
    agent_type: AgentType
    agent_id: AgentID
    execution_id: ExecutionID
    success: bool
    execution_time_ms: int
    business_value: Dict[BusinessValueMetric, float]
    outputs: Dict[str, Any]
    handoff_context: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SequenceExecutionState:
    """State tracking for the complete agent execution sequence."""
    execution_id: ExecutionID
    user_context: StronglyTypedUserExecutionContext
    current_phase: ExecutionPhase
    completed_agents: List[AgentType] = field(default_factory=list)
    agent_results: Dict[AgentType, AgentExecutionResult] = field(default_factory=dict)
    sequence_start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cumulative_business_value: Dict[BusinessValueMetric, float] = field(default_factory=dict)
    sequence_errors: List[str] = field(default_factory=list)


class AgentExecutionOrchestrator:
    """Business logic orchestrator for the Golden Path agent execution sequence."""
    
    def __init__(self):
        self.business_sequence_rules = self._initialize_sequence_rules()
        self.active_executions: Dict[ExecutionID, SequenceExecutionState] = {}
        self.sequence_performance_metrics = []
        
    def _initialize_sequence_rules(self) -> Dict[str, Any]:
        """Initialize business rules for agent execution sequence."""
        return {
            "required_sequence": [AgentType.DATA_AGENT, AgentType.OPTIMIZATION_AGENT, AgentType.REPORT_AGENT],
            "phase_transitions": {
                ExecutionPhase.INITIALIZATION: ExecutionPhase.DATA_COLLECTION,
                ExecutionPhase.DATA_COLLECTION: ExecutionPhase.DATA_ANALYSIS,
                ExecutionPhase.DATA_ANALYSIS: ExecutionPhase.OPTIMIZATION_ANALYSIS,
                ExecutionPhase.OPTIMIZATION_ANALYSIS: ExecutionPhase.OPTIMIZATION_RECOMMENDATIONS,
                ExecutionPhase.OPTIMIZATION_RECOMMENDATIONS: ExecutionPhase.REPORT_GENERATION,
                ExecutionPhase.REPORT_GENERATION: ExecutionPhase.REPORT_FINALIZATION,
                ExecutionPhase.REPORT_FINALIZATION: ExecutionPhase.COMPLETION
            },
            "agent_phase_mapping": {
                AgentType.DATA_AGENT: [ExecutionPhase.DATA_COLLECTION, ExecutionPhase.DATA_ANALYSIS],
                AgentType.OPTIMIZATION_AGENT: [ExecutionPhase.OPTIMIZATION_ANALYSIS, ExecutionPhase.OPTIMIZATION_RECOMMENDATIONS],
                AgentType.REPORT_AGENT: [ExecutionPhase.REPORT_GENERATION, ExecutionPhase.REPORT_FINALIZATION]
            },
            "handoff_requirements": {
                AgentType.DATA_AGENT: {
                    "required_outputs": ["analyzed_data", "data_quality_metrics", "usage_patterns"],
                    "business_value_minimum": {BusinessValueMetric.DATA_QUALITY_SCORE: 0.7}
                },
                AgentType.OPTIMIZATION_AGENT: {
                    "required_inputs": ["analyzed_data", "usage_patterns"],
                    "required_outputs": ["optimization_recommendations", "cost_analysis", "performance_insights"],
                    "business_value_minimum": {BusinessValueMetric.OPTIMIZATION_POTENTIAL: 0.1}
                },
                AgentType.REPORT_AGENT: {
                    "required_inputs": ["analyzed_data", "optimization_recommendations", "cost_analysis"],
                    "required_outputs": ["final_report", "executive_summary", "action_items"],
                    "business_value_minimum": {BusinessValueMetric.ACTIONABILITY_SCORE: 0.8}
                }
            },
            "business_quality_gates": {
                "data_quality_threshold": 0.7,
                "optimization_value_threshold": 0.1,
                "report_actionability_threshold": 0.8,
                "maximum_execution_time_minutes": 15
            }
        }
    
    def start_execution_sequence(self, user_context: StronglyTypedUserExecutionContext) -> ExecutionID:
        """Start the Golden Path agent execution sequence."""
        execution_id = ExecutionID(f"seq-{uuid.uuid4()}")
        
        # Business Rule: Initialize execution state with business tracking
        execution_state = SequenceExecutionState(
            execution_id=execution_id,
            user_context=user_context,
            current_phase=ExecutionPhase.INITIALIZATION,
            cumulative_business_value={metric: 0.0 for metric in BusinessValueMetric}
        )
        
        self.active_executions[execution_id] = execution_state
        
        # Business Rule: Transition to first business phase
        self._transition_phase(execution_id, ExecutionPhase.DATA_COLLECTION)
        
        return execution_id
    
    def execute_agent(self, execution_id: ExecutionID, agent_type: AgentType) -> AgentExecutionResult:
        """Execute individual agent with business validation."""
        execution_state = self.active_executions.get(execution_id)
        if not execution_state:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Business Rule: Validate agent can execute in current phase
        allowed_phases = self.business_sequence_rules["agent_phase_mapping"][agent_type]
        if execution_state.current_phase not in allowed_phases:
            raise ValueError(f"Agent {agent_type} cannot execute in phase {execution_state.current_phase}")
        
        # Business Rule: Validate sequence order
        required_sequence = self.business_sequence_rules["required_sequence"]
        agent_index = required_sequence.index(agent_type)
        
        for i in range(agent_index):
            required_predecessor = required_sequence[i]
            if required_predecessor not in execution_state.completed_agents:
                raise ValueError(f"Agent {agent_type} requires {required_predecessor} to complete first")
        
        # Simulate agent execution with business logic
        start_time = datetime.now(timezone.utc)
        agent_result = self._simulate_agent_execution(agent_type, execution_state)
        end_time = datetime.now(timezone.utc)
        
        # Business Rule: Record execution time for performance tracking
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        agent_result.execution_time_ms = execution_time_ms
        
        # Business Rule: Validate business quality gates
        self._validate_business_quality_gates(agent_result, agent_type)
        
        # Business Rule: Update execution state
        execution_state.agent_results[agent_type] = agent_result
        execution_state.completed_agents.append(agent_type)
        
        # Business Rule: Update cumulative business value
        for metric, value in agent_result.business_value.items():
            execution_state.cumulative_business_value[metric] += value
        
        # Business Rule: Advance to next phase if appropriate
        self._advance_execution_phase(execution_id, agent_type)
        
        return agent_result
    
    def _simulate_agent_execution(self, agent_type: AgentType, execution_state: SequenceExecutionState) -> AgentExecutionResult:
        """Simulate agent execution with realistic business outputs."""
        agent_id = AgentID(f"{agent_type.value}-{uuid.uuid4()}")
        
        if agent_type == AgentType.DATA_AGENT:
            return AgentExecutionResult(
                agent_type=agent_type,
                agent_id=agent_id,
                execution_id=execution_state.execution_id,
                success=True,
                execution_time_ms=0,  # Will be set by caller
                business_value={
                    BusinessValueMetric.DATA_QUALITY_SCORE: 0.85,
                    BusinessValueMetric.ACTIONABILITY_SCORE: 0.3
                },
                outputs={
                    "analyzed_data": {
                        "monthly_ai_spend": 15000,
                        "token_usage": {"gpt-4": 500000, "claude": 300000},
                        "cost_breakdown": {"openai": 12000, "anthropic": 3000}
                    },
                    "data_quality_metrics": {
                        "completeness": 0.9, "accuracy": 0.85, "consistency": 0.88
                    },
                    "usage_patterns": {
                        "peak_hours": [9, 10, 11, 14, 15], 
                        "heavy_usage_features": ["code_generation", "analysis"]
                    }
                },
                handoff_context={
                    "data_validated": True,
                    "optimization_opportunities_identified": True,
                    "business_context": "enterprise_customer_high_usage"
                }
            )
            
        elif agent_type == AgentType.OPTIMIZATION_AGENT:
            # Business Rule: Use data from previous agent
            data_result = execution_state.agent_results.get(AgentType.DATA_AGENT)
            if not data_result:
                raise ValueError("Optimization agent requires data agent results")
                
            analyzed_data = data_result.outputs["analyzed_data"]
            monthly_spend = analyzed_data["monthly_ai_spend"]
            
            return AgentExecutionResult(
                agent_type=agent_type,
                agent_id=agent_id,
                execution_id=execution_state.execution_id,
                success=True,
                execution_time_ms=0,
                business_value={
                    BusinessValueMetric.OPTIMIZATION_POTENTIAL: 0.25,  # 25% potential savings
                    BusinessValueMetric.COST_SAVINGS_IDENTIFIED: monthly_spend * 0.25
                },
                outputs={
                    "optimization_recommendations": [
                        {"action": "reduce_gpt4_usage", "impact": "30% cost reduction", "effort": "low"},
                        {"action": "optimize_prompt_caching", "impact": "15% performance gain", "effort": "medium"},
                        {"action": "implement_model_routing", "impact": "20% cost optimization", "effort": "high"}
                    ],
                    "cost_analysis": {
                        "current_monthly_cost": monthly_spend,
                        "potential_monthly_savings": monthly_spend * 0.25,
                        "roi_timeline": "3_months"
                    },
                    "performance_insights": {
                        "bottlenecks": ["token_inefficiency", "model_over_provisioning"],
                        "optimization_priorities": ["cost", "performance", "reliability"]
                    }
                },
                handoff_context={
                    "optimization_validated": True,
                    "high_value_recommendations": True,
                    "implementation_feasible": True
                }
            )
            
        elif agent_type == AgentType.REPORT_AGENT:
            # Business Rule: Use results from both previous agents
            data_result = execution_state.agent_results.get(AgentType.DATA_AGENT)
            optimization_result = execution_state.agent_results.get(AgentType.OPTIMIZATION_AGENT)
            
            if not data_result or not optimization_result:
                raise ValueError("Report agent requires data and optimization results")
                
            cost_savings = optimization_result.business_value[BusinessValueMetric.COST_SAVINGS_IDENTIFIED]
            
            return AgentExecutionResult(
                agent_type=agent_type,
                agent_id=agent_id,
                execution_id=execution_state.execution_id,
                success=True,
                execution_time_ms=0,
                business_value={
                    BusinessValueMetric.ACTIONABILITY_SCORE: 0.9,
                    BusinessValueMetric.USER_SATISFACTION_PREDICTION: 0.85
                },
                outputs={
                    "final_report": {
                        "executive_summary": f"AI cost optimization analysis reveals ${cost_savings:,.0f} monthly savings potential",
                        "key_findings": [
                            f"Current AI spend: ${data_result.outputs['analyzed_data']['monthly_ai_spend']:,}/month",
                            f"Optimization potential: ${cost_savings:,.0f}/month (25% savings)",
                            "3-month ROI timeline with high-impact, low-effort implementations"
                        ],
                        "recommendations_prioritized": optimization_result.outputs["optimization_recommendations"]
                    },
                    "executive_summary": f"Optimize AI costs: Save ${cost_savings:,.0f}/month with strategic model usage changes",
                    "action_items": [
                        {"priority": "high", "action": "Implement GPT-4 usage reduction", "timeline": "1_week"},
                        {"priority": "medium", "action": "Deploy prompt caching", "timeline": "2_weeks"},
                        {"priority": "low", "action": "Evaluate model routing", "timeline": "1_month"}
                    ]
                },
                handoff_context={
                    "report_complete": True,
                    "business_value_delivered": True,
                    "user_actionable_insights": True
                }
            )
        
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    def _validate_business_quality_gates(self, agent_result: AgentExecutionResult, agent_type: AgentType) -> None:
        """Validate agent results meet business quality requirements."""
        quality_gates = self.business_sequence_rules["business_quality_gates"]
        handoff_requirements = self.business_sequence_rules["handoff_requirements"][agent_type]
        
        # Business Rule 1: Validate minimum business value thresholds
        min_business_values = handoff_requirements.get("business_value_minimum", {})
        for metric, min_value in min_business_values.items():
            actual_value = agent_result.business_value.get(metric, 0.0)
            if actual_value < min_value:
                agent_result.warnings.append(f"Business value {metric} ({actual_value:.2f}) below threshold ({min_value:.2f})")
        
        # Business Rule 2: Validate required outputs are present
        required_outputs = handoff_requirements.get("required_outputs", [])
        for output_key in required_outputs:
            if output_key not in agent_result.outputs:
                agent_result.errors.append(f"Required output missing: {output_key}")
                agent_result.success = False
    
    def _advance_execution_phase(self, execution_id: ExecutionID, completed_agent_type: AgentType) -> None:
        """Advance execution phase based on business rules."""
        execution_state = self.active_executions[execution_id]
        phase_transitions = self.business_sequence_rules["phase_transitions"]
        
        # Business Rule: Determine next phase based on completed agent
        if completed_agent_type == AgentType.DATA_AGENT:
            if execution_state.current_phase == ExecutionPhase.DATA_COLLECTION:
                self._transition_phase(execution_id, ExecutionPhase.DATA_ANALYSIS)
            elif execution_state.current_phase == ExecutionPhase.DATA_ANALYSIS:
                self._transition_phase(execution_id, ExecutionPhase.OPTIMIZATION_ANALYSIS)
                
        elif completed_agent_type == AgentType.OPTIMIZATION_AGENT:
            if execution_state.current_phase == ExecutionPhase.OPTIMIZATION_ANALYSIS:
                self._transition_phase(execution_id, ExecutionPhase.OPTIMIZATION_RECOMMENDATIONS)
            elif execution_state.current_phase == ExecutionPhase.OPTIMIZATION_RECOMMENDATIONS:
                self._transition_phase(execution_id, ExecutionPhase.REPORT_GENERATION)
                
        elif completed_agent_type == AgentType.REPORT_AGENT:
            if execution_state.current_phase == ExecutionPhase.REPORT_GENERATION:
                self._transition_phase(execution_id, ExecutionPhase.REPORT_FINALIZATION)
            elif execution_state.current_phase == ExecutionPhase.REPORT_FINALIZATION:
                self._transition_phase(execution_id, ExecutionPhase.COMPLETION)
    
    def _transition_phase(self, execution_id: ExecutionID, new_phase: ExecutionPhase) -> None:
        """Transition execution to new business phase."""
        execution_state = self.active_executions[execution_id]
        execution_state.current_phase = new_phase
    
    def get_sequence_business_summary(self, execution_id: ExecutionID) -> Dict[str, Any]:
        """Get business summary of execution sequence."""
        execution_state = self.active_executions.get(execution_id)
        if not execution_state:
            return {"error": "Execution not found"}
        
        sequence_duration = datetime.now(timezone.utc) - execution_state.sequence_start_time
        
        return {
            "execution_complete": execution_state.current_phase == ExecutionPhase.COMPLETION,
            "completed_agents": len(execution_state.completed_agents),
            "total_agents_required": len(self.business_sequence_rules["required_sequence"]),
            "sequence_duration_seconds": sequence_duration.total_seconds(),
            "cumulative_business_value": execution_state.cumulative_business_value,
            "current_phase": execution_state.current_phase.value,
            "business_outcomes": self._calculate_business_outcomes(execution_state)
        }
    
    def _calculate_business_outcomes(self, execution_state: SequenceExecutionState) -> Dict[str, Any]:
        """Calculate final business outcomes from execution sequence."""
        outcomes = {
            "data_insights_delivered": False,
            "optimization_opportunities_identified": False,
            "actionable_report_generated": False,
            "estimated_monthly_savings": 0.0,
            "user_satisfaction_prediction": 0.0,
            "business_value_score": 0.0
        }
        
        # Calculate outcomes based on completed agents
        if AgentType.DATA_AGENT in execution_state.completed_agents:
            outcomes["data_insights_delivered"] = True
        
        if AgentType.OPTIMIZATION_AGENT in execution_state.completed_agents:
            outcomes["optimization_opportunities_identified"] = True
            optimization_result = execution_state.agent_results.get(AgentType.OPTIMIZATION_AGENT)
            if optimization_result:
                outcomes["estimated_monthly_savings"] = optimization_result.business_value.get(BusinessValueMetric.COST_SAVINGS_IDENTIFIED, 0.0)
        
        if AgentType.REPORT_AGENT in execution_state.completed_agents:
            outcomes["actionable_report_generated"] = True
            report_result = execution_state.agent_results.get(AgentType.REPORT_AGENT)
            if report_result:
                outcomes["user_satisfaction_prediction"] = report_result.business_value.get(BusinessValueMetric.USER_SATISFACTION_PREDICTION, 0.0)
        
        # Calculate overall business value score
        total_possible_value = len(BusinessValueMetric) * 1.0
        actual_total_value = sum(execution_state.cumulative_business_value.values())
        outcomes["business_value_score"] = min(actual_total_value / total_possible_value, 1.0)
        
        return outcomes


@pytest.mark.unit
@pytest.mark.golden_path
class TestAgentExecutionSequenceBusinessLogic(BaseTestCase):
    """Test agent execution sequence business logic for Golden Path delivery."""

    def setup_method(self):
        """Setup test environment for each test."""
        super().setup_method()
        self.orchestrator = AgentExecutionOrchestrator()
        self.test_user_context = StronglyTypedUserExecutionContext(
            user_id=ensure_user_id("test-user-123"),
            thread_id=ensure_thread_id("thread-456"),
            execution_id=ExecutionID("exec-789"),
            session_id="session-abc",
            websocket_client_id="ws-def"
        )

    def test_data_agent_first_execution_business_requirement(self):
        """Test Data Agent must execute first in the business sequence."""
        # Business Value: Data collection and analysis must happen before optimization
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Business Rule 1: Execution should start in data collection phase
        execution_state = self.orchestrator.active_executions[execution_id]
        assert execution_state.current_phase == ExecutionPhase.DATA_COLLECTION, "Execution must start with data collection"
        
        # Business Rule 2: Data agent must be able to execute first
        data_result = self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        assert data_result.success is True, "Data agent must execute successfully"
        assert data_result.agent_type == AgentType.DATA_AGENT, "Result must be from data agent"
        
        # Business Rule 3: Data agent must produce required business outputs
        required_outputs = ["analyzed_data", "data_quality_metrics", "usage_patterns"]
        for output in required_outputs:
            assert output in data_result.outputs, f"Data agent must produce {output}"
        
        # Business Rule 4: Data agent must meet business quality thresholds
        data_quality_score = data_result.business_value[BusinessValueMetric.DATA_QUALITY_SCORE]
        assert data_quality_score >= 0.7, "Data quality must meet business threshold"
        
        # Business Rule 5: Data must contain business-relevant insights
        analyzed_data = data_result.outputs["analyzed_data"]
        assert "monthly_ai_spend" in analyzed_data, "Data must include cost analysis"
        assert "token_usage" in analyzed_data, "Data must include usage metrics"
        assert analyzed_data["monthly_ai_spend"] > 0, "Cost data must be meaningful"

    def test_optimization_agent_requires_data_agent_business_rule(self):
        """Test Optimization Agent requires Data Agent completion for business logic."""
        # Business Value: Optimization recommendations must be based on actual data analysis
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Business Rule 1: Optimization agent cannot execute without data agent
        with pytest.raises(ValueError, match="requires data_agent to complete first"):
            self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        
        # Business Rule 2: After data agent completes, optimization agent can execute
        self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        optimization_result = self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        
        assert optimization_result.success is True, "Optimization agent must execute after data agent"
        
        # Business Rule 3: Optimization must use data from previous agent
        optimization_outputs = optimization_result.outputs
        assert "optimization_recommendations" in optimization_outputs, "Must provide optimization recommendations"
        assert "cost_analysis" in optimization_outputs, "Must provide cost analysis"
        
        # Business Rule 4: Optimization must identify business value
        optimization_potential = optimization_result.business_value[BusinessValueMetric.OPTIMIZATION_POTENTIAL]
        assert optimization_potential > 0, "Optimization must identify potential value"
        
        cost_savings = optimization_result.business_value[BusinessValueMetric.COST_SAVINGS_IDENTIFIED]
        assert cost_savings > 0, "Optimization must identify cost savings"
        
        # Business Rule 5: Recommendations must be actionable
        recommendations = optimization_outputs["optimization_recommendations"]
        assert len(recommendations) > 0, "Must provide actionable recommendations"
        for rec in recommendations:
            assert "action" in rec, "Each recommendation must have an action"
            assert "impact" in rec, "Each recommendation must specify impact"
            assert "effort" in rec, "Each recommendation must specify effort level"

    def test_report_agent_requires_complete_sequence_business_rule(self):
        """Test Report Agent requires complete sequence for business report generation."""
        # Business Value: Final report must synthesize all analysis for maximum user value
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Business Rule 1: Report agent cannot execute without predecessors
        with pytest.raises(ValueError, match="requires data_agent to complete first"):
            self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        # Execute data agent only
        self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        
        # Business Rule 2: Report agent still cannot execute without optimization agent
        with pytest.raises(ValueError, match="requires optimization_agent to complete first"):
            self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        # Execute optimization agent
        self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        
        # Business Rule 3: Now report agent can execute
        report_result = self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        assert report_result.success is True, "Report agent must execute after complete sequence"
        
        # Business Rule 4: Report must synthesize all previous results
        report_outputs = report_result.outputs
        assert "final_report" in report_outputs, "Must generate final business report"
        assert "executive_summary" in report_outputs, "Must provide executive summary"
        assert "action_items" in report_outputs, "Must provide actionable next steps"
        
        # Business Rule 5: Report must have high actionability for business value
        actionability_score = report_result.business_value[BusinessValueMetric.ACTIONABILITY_SCORE]
        assert actionability_score >= 0.8, "Report must have high actionability score"
        
        # Business Rule 6: Report must include specific business metrics
        final_report = report_outputs["final_report"]
        assert "key_findings" in final_report, "Report must include key business findings"
        assert "recommendations_prioritized" in final_report, "Report must prioritize recommendations"
        
        # Verify executive summary contains business value
        exec_summary = report_outputs["executive_summary"]
        assert "Save" in exec_summary and "$" in exec_summary, "Executive summary must highlight savings"

    def test_complete_golden_path_sequence_business_outcomes(self):
        """Test complete Golden Path sequence delivers expected business outcomes."""
        # Business Value: Full sequence must deliver complete AI optimization value proposition
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Execute complete sequence
        data_result = self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        optimization_result = self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        report_result = self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        # Business Rule 1: All agents must succeed
        assert data_result.success is True, "Data agent must succeed"
        assert optimization_result.success is True, "Optimization agent must succeed"
        assert report_result.success is True, "Report agent must succeed"
        
        # Business Rule 2: Get comprehensive business summary
        business_summary = self.orchestrator.get_sequence_business_summary(execution_id)
        assert business_summary["execution_complete"] is True, "Execution must be complete"
        assert business_summary["completed_agents"] == 3, "All 3 agents must complete"
        
        # Business Rule 3: Validate business outcomes achieved
        business_outcomes = business_summary["business_outcomes"]
        assert business_outcomes["data_insights_delivered"] is True, "Must deliver data insights"
        assert business_outcomes["optimization_opportunities_identified"] is True, "Must identify optimizations"
        assert business_outcomes["actionable_report_generated"] is True, "Must generate actionable report"
        
        # Business Rule 4: Validate financial business value
        assert business_outcomes["estimated_monthly_savings"] > 0, "Must identify cost savings"
        assert business_outcomes["user_satisfaction_prediction"] >= 0.8, "Must predict high user satisfaction"
        assert business_outcomes["business_value_score"] > 0.5, "Must achieve meaningful business value"
        
        # Business Rule 5: Validate cumulative business value
        cumulative_value = business_summary["cumulative_business_value"]
        assert cumulative_value[BusinessValueMetric.DATA_QUALITY_SCORE] > 0, "Must have data quality value"
        assert cumulative_value[BusinessValueMetric.OPTIMIZATION_POTENTIAL] > 0, "Must have optimization value"
        assert cumulative_value[BusinessValueMetric.COST_SAVINGS_IDENTIFIED] > 0, "Must identify cost savings"
        assert cumulative_value[BusinessValueMetric.ACTIONABILITY_SCORE] > 0, "Must have actionability value"

    def test_agent_handoff_context_business_continuity(self):
        """Test agent handoff context maintains business continuity between agents."""
        # Business Value: Context passing ensures insights build upon each other for maximum value
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Execute data agent and examine handoff context
        data_result = self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        data_handoff = data_result.handoff_context
        
        # Business Rule 1: Data agent must provide business context for optimization
        assert data_handoff.get("data_validated") is True, "Data validation must be confirmed"
        assert data_handoff.get("optimization_opportunities_identified") is True, "Optimization opportunities must be flagged"
        assert "business_context" in data_handoff, "Business context must be provided"
        
        # Execute optimization agent and verify it uses data context
        optimization_result = self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        
        # Business Rule 2: Optimization must reference data agent's findings
        # (This is validated through the business logic requiring data inputs)
        assert "analyzed_data" in data_result.outputs, "Data must be available for optimization"
        
        optimization_handoff = optimization_result.handoff_context
        assert optimization_handoff.get("optimization_validated") is True, "Optimization must be validated"
        assert optimization_handoff.get("high_value_recommendations") is True, "High-value recommendations must be flagged"
        
        # Execute report agent and verify it synthesizes all context
        report_result = self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        # Business Rule 3: Report must synthesize insights from both previous agents
        final_report = report_result.outputs["final_report"]
        key_findings = final_report["key_findings"]
        
        # Verify data insights are incorporated
        data_spend = data_result.outputs["analyzed_data"]["monthly_ai_spend"]
        assert any(str(data_spend) in finding for finding in key_findings), "Data insights must be in report"
        
        # Verify optimization insights are incorporated
        cost_savings = optimization_result.business_value[BusinessValueMetric.COST_SAVINGS_IDENTIFIED]
        assert any(str(int(cost_savings)) in finding for finding in key_findings), "Optimization insights must be in report"

    def test_execution_phase_transitions_business_logic(self):
        """Test execution phases transition correctly according to business rules."""
        # Business Value: Proper phase transitions ensure business process integrity
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        execution_state = self.orchestrator.active_executions[execution_id]
        
        # Business Rule 1: Start in data collection phase
        assert execution_state.current_phase == ExecutionPhase.DATA_COLLECTION, "Must start in data collection"
        
        # Execute data agent - should advance through data phases
        self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        # Phase transitions happen internally, verify we're in optimization phase
        assert execution_state.current_phase == ExecutionPhase.OPTIMIZATION_ANALYSIS, "Must advance to optimization analysis"
        
        # Execute optimization agent - should advance through optimization phases
        self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        assert execution_state.current_phase == ExecutionPhase.REPORT_GENERATION, "Must advance to report generation"
        
        # Execute report agent - should complete sequence
        self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        assert execution_state.current_phase == ExecutionPhase.COMPLETION, "Must complete execution"
        
        # Business Rule 2: Verify business summary reflects completion
        business_summary = self.orchestrator.get_sequence_business_summary(execution_id)
        assert business_summary["execution_complete"] is True, "Business summary must show completion"
        assert business_summary["current_phase"] == "completion", "Current phase must be completion"

    def test_business_quality_gates_validation(self):
        """Test business quality gates ensure minimum value delivery standards."""
        # Business Value: Quality gates prevent low-value outputs that damage user experience
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Execute agents and verify quality gates are applied
        data_result = self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        
        # Business Rule 1: Data quality must meet minimum threshold
        data_quality = data_result.business_value[BusinessValueMetric.DATA_QUALITY_SCORE]
        quality_threshold = self.orchestrator.business_sequence_rules["business_quality_gates"]["data_quality_threshold"]
        assert data_quality >= quality_threshold, f"Data quality ({data_quality}) must meet threshold ({quality_threshold})"
        
        optimization_result = self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        
        # Business Rule 2: Optimization potential must exceed minimum threshold
        optimization_potential = optimization_result.business_value[BusinessValueMetric.OPTIMIZATION_POTENTIAL]
        optimization_threshold = self.orchestrator.business_sequence_rules["business_quality_gates"]["optimization_value_threshold"]
        assert optimization_potential >= optimization_threshold, f"Optimization potential ({optimization_potential}) must meet threshold ({optimization_threshold})"
        
        report_result = self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        # Business Rule 3: Report actionability must meet minimum threshold
        actionability_score = report_result.business_value[BusinessValueMetric.ACTIONABILITY_SCORE]
        actionability_threshold = self.orchestrator.business_sequence_rules["business_quality_gates"]["report_actionability_threshold"]
        assert actionability_score >= actionability_threshold, f"Actionability ({actionability_score}) must meet threshold ({actionability_threshold})"
        
        # Business Rule 4: Overall business value must be meaningful
        business_summary = self.orchestrator.get_sequence_business_summary(execution_id)
        business_value_score = business_summary["business_outcomes"]["business_value_score"]
        assert business_value_score > 0.5, "Overall business value must be meaningful"

    def test_execution_sequence_performance_business_requirements(self):
        """Test execution sequence completes within business time requirements."""
        # Business Value: Fast execution prevents user abandonment and enables real-time insights
        
        start_time = datetime.now(timezone.utc)
        
        execution_id = self.orchestrator.start_execution_sequence(self.test_user_context)
        
        # Execute complete sequence
        self.orchestrator.execute_agent(execution_id, AgentType.DATA_AGENT)
        self.orchestrator.execute_agent(execution_id, AgentType.OPTIMIZATION_AGENT)
        self.orchestrator.execute_agent(execution_id, AgentType.REPORT_AGENT)
        
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()
        
        # Business Rule 1: Complete sequence must finish within business time limit
        max_duration = self.orchestrator.business_sequence_rules["business_quality_gates"]["maximum_execution_time_minutes"] * 60
        assert total_duration < max_duration, f"Sequence duration ({total_duration}s) must be under {max_duration}s"
        
        # Business Rule 2: Business summary must track performance metrics
        business_summary = self.orchestrator.get_sequence_business_summary(execution_id)
        sequence_duration = business_summary["sequence_duration_seconds"]
        assert sequence_duration > 0, "Sequence duration must be tracked"
        assert sequence_duration < max_duration, "Business summary duration must meet requirements"
        
        # Business Rule 3: Individual agent performance must be reasonable
        execution_state = self.orchestrator.active_executions[execution_id]
        for agent_type, result in execution_state.agent_results.items():
            # Each agent should complete in reasonable time (< 5 seconds for unit tests)
            assert result.execution_time_ms < 5000, f"{agent_type} must complete in reasonable time"