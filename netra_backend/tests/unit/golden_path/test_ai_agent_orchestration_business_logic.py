"""
Test AI Agent Orchestration Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core AI functionality
- Business Goal: Ensure AI agents deliver consistent, high-quality insights
- Value Impact: Agent orchestration is 90% of our $500K+ ARR value delivery
- Strategic Impact: Proper agent sequencing prevents customer-facing failures

This test validates core agent orchestration algorithms that power:
1. Agent execution order (Triage  ->  Data Helper  ->  UVS Optimizer  ->  Reporter)  
2. Agent dependency resolution and execution planning
3. Context passing between agents for coherent results
4. Error recovery and graceful degradation patterns
5. Agent selection based on user query and tier

CRITICAL BUSINESS RULES:
- Triage agent MUST run first to classify the problem
- Data Helper agent provides context for optimization
- Optimization agents (UVS, Cost, etc.) require data context
- Reporter agent synthesizes results into user-friendly format
- Enterprise customers get all agents, Free tier limited to 2-agent chains
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import uuid

from shared.types.core_types import UserID, AgentID, RunID
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Business Logic Classes (SSOT for agent orchestration)

class AgentType(Enum):
    TRIAGE = "triage_agent"
    DATA_HELPER = "data_helper_agent"
    UVS_OPTIMIZER = "uvs_optimizer_agent"
    COST_OPTIMIZER = "cost_optimizer_agent"
    SECURITY_ANALYZER = "security_analyzer_agent"
    REPORTER = "reporter_agent"

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class SubscriptionTier(Enum):
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"

@dataclass
class AgentCapabilities:
    """Agent capabilities and requirements."""
    agent_type: AgentType
    required_context_types: List[str]
    output_context_types: List[str]
    execution_time_limit_seconds: int
    tier_restrictions: Optional[List[SubscriptionTier]]
    dependencies: List[AgentType]

@dataclass
class AgentExecutionContext:
    """Context passed between agents."""
    user_query: str
    user_tier: SubscriptionTier
    execution_history: Dict[AgentType, Any]
    available_data_sources: List[str]
    session_metadata: Dict[str, Any]

@dataclass
class AgentExecutionResult:
    """Result from agent execution."""
    agent_type: AgentType
    status: ExecutionStatus
    output_data: Dict[str, Any]
    execution_time_seconds: float
    tokens_used: int
    confidence_score: float
    error_message: Optional[str]
    next_recommended_agents: List[AgentType]

@dataclass
class ExecutionPlan:
    """Complete execution plan for agent chain."""
    execution_sequence: List[AgentType]
    estimated_total_time: int
    estimated_total_cost: Decimal
    tier_compliance: bool
    context_flow: Dict[AgentType, List[str]]

class AgentOrchestrator:
    """
    SSOT Agent Orchestration Business Logic
    
    This class implements the core business rules for AI agent coordination
    that delivers the platform's primary value proposition.
    """
    
    # AGENT CAPABILITY DEFINITIONS
    AGENT_REGISTRY = {
        AgentType.TRIAGE: AgentCapabilities(
            agent_type=AgentType.TRIAGE,
            required_context_types=["user_query"],
            output_context_types=["problem_category", "urgency_level", "recommended_agents"],
            execution_time_limit_seconds=10,
            tier_restrictions=None,  # Available to all tiers
            dependencies=[]
        ),
        AgentType.DATA_HELPER: AgentCapabilities(
            agent_type=AgentType.DATA_HELPER,
            required_context_types=["user_query", "problem_category"],
            output_context_types=["relevant_data", "data_quality_score", "data_sources"],
            execution_time_limit_seconds=30,
            tier_restrictions=None,  # Available to all tiers
            dependencies=[AgentType.TRIAGE]
        ),
        AgentType.UVS_OPTIMIZER: AgentCapabilities(
            agent_type=AgentType.UVS_OPTIMIZER,
            required_context_types=["problem_category", "relevant_data"],
            output_context_types=["optimization_recommendations", "impact_analysis"],
            execution_time_limit_seconds=60,
            tier_restrictions=[SubscriptionTier.EARLY, SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
            dependencies=[AgentType.TRIAGE, AgentType.DATA_HELPER]
        ),
        AgentType.COST_OPTIMIZER: AgentCapabilities(
            agent_type=AgentType.COST_OPTIMIZER,
            required_context_types=["problem_category", "relevant_data"],
            output_context_types=["cost_savings", "implementation_plan"],
            execution_time_limit_seconds=45,
            tier_restrictions=[SubscriptionTier.EARLY, SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
            dependencies=[AgentType.TRIAGE, AgentType.DATA_HELPER]
        ),
        AgentType.SECURITY_ANALYZER: AgentCapabilities(
            agent_type=AgentType.SECURITY_ANALYZER,
            required_context_types=["problem_category", "relevant_data"],
            output_context_types=["security_analysis", "risk_assessment"],
            execution_time_limit_seconds=40,
            tier_restrictions=[SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
            dependencies=[AgentType.TRIAGE, AgentType.DATA_HELPER]
        ),
        AgentType.REPORTER: AgentCapabilities(
            agent_type=AgentType.REPORTER,
            required_context_types=["optimization_recommendations", "cost_savings", "security_analysis"],
            output_context_types=["final_report", "executive_summary"],
            execution_time_limit_seconds=20,
            tier_restrictions=None,  # Available to all tiers
            dependencies=[]  # Can depend on any completion agents
        )
    }
    
    # TIER-BASED EXECUTION LIMITS
    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            'max_agents_per_execution': 2,
            'max_execution_time': 60,
            'allowed_agent_types': [AgentType.TRIAGE, AgentType.DATA_HELPER, AgentType.REPORTER]
        },
        SubscriptionTier.EARLY: {
            'max_agents_per_execution': 4,
            'max_execution_time': 120,
            'allowed_agent_types': list(AgentType)  # All agents
        },
        SubscriptionTier.MID: {
            'max_agents_per_execution': 6,
            'max_execution_time': 300,
            'allowed_agent_types': list(AgentType)  # All agents
        },
        SubscriptionTier.ENTERPRISE: {
            'max_agents_per_execution': 10,
            'max_execution_time': 600,
            'allowed_agent_types': list(AgentType)  # All agents
        }
    }

    def create_execution_plan(self, user_query: str, user_tier: SubscriptionTier, 
                            preferred_agents: Optional[List[AgentType]] = None) -> ExecutionPlan:
        """
        Create optimal execution plan for user query.
        
        Critical business logic that determines value delivery.
        """
        # Start with triage agent (always required)
        execution_sequence = [AgentType.TRIAGE]
        
        # Get tier limits
        tier_config = self.TIER_LIMITS[user_tier]
        max_agents = tier_config['max_agents_per_execution']
        allowed_agents = set(tier_config['allowed_agent_types'])
        
        # Classify query to determine needed agents (simplified heuristic)
        if "cost" in user_query.lower() or "savings" in user_query.lower():
            if AgentType.DATA_HELPER in allowed_agents and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.DATA_HELPER)
            if AgentType.COST_OPTIMIZER in allowed_agents and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.COST_OPTIMIZER)
                
        if "security" in user_query.lower() or "compliance" in user_query.lower():
            if AgentType.DATA_HELPER in allowed_agents and AgentType.DATA_HELPER not in execution_sequence and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.DATA_HELPER)
            if AgentType.SECURITY_ANALYZER in allowed_agents and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.SECURITY_ANALYZER)
                
        if "optimize" in user_query.lower() or "performance" in user_query.lower():
            if AgentType.DATA_HELPER in allowed_agents and AgentType.DATA_HELPER not in execution_sequence and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.DATA_HELPER)
            if AgentType.UVS_OPTIMIZER in allowed_agents and len(execution_sequence) < max_agents:
                execution_sequence.append(AgentType.UVS_OPTIMIZER)
        
        # Add preferred agents if specified and allowed
        if preferred_agents:
            for agent in preferred_agents:
                if (agent in allowed_agents and 
                    agent not in execution_sequence and 
                    len(execution_sequence) < max_agents):
                    execution_sequence.append(agent)
        
        # Add reporter if there's room and we have analysis agents
        analysis_agents = {AgentType.UVS_OPTIMIZER, AgentType.COST_OPTIMIZER, AgentType.SECURITY_ANALYZER}
        if (any(agent in execution_sequence for agent in analysis_agents) and
            AgentType.REPORTER in allowed_agents and
            AgentType.REPORTER not in execution_sequence and
            len(execution_sequence) < max_agents):
            execution_sequence.append(AgentType.REPORTER)
        
        # Validate dependencies and reorder if needed
        execution_sequence = self._resolve_dependencies(execution_sequence)
        
        # Calculate estimates
        estimated_time = sum(
            self.AGENT_REGISTRY[agent].execution_time_limit_seconds 
            for agent in execution_sequence
        )
        estimated_cost = Decimal(str(len(execution_sequence) * 0.05))  # $0.05 per agent
        
        # Check tier compliance
        tier_compliant = (
            len(execution_sequence) <= max_agents and
            estimated_time <= tier_config['max_execution_time'] and
            all(agent in allowed_agents for agent in execution_sequence)
        )
        
        # Build context flow map
        context_flow = {}
        for agent in execution_sequence:
            capabilities = self.AGENT_REGISTRY[agent]
            context_flow[agent] = capabilities.required_context_types
        
        return ExecutionPlan(
            execution_sequence=execution_sequence,
            estimated_total_time=estimated_time,
            estimated_total_cost=estimated_cost,
            tier_compliance=tier_compliant,
            context_flow=context_flow
        )

    def validate_execution_context(self, context: AgentExecutionContext, 
                                 agent_type: AgentType) -> Dict[str, bool]:
        """
        Validate that execution context meets agent requirements.
        
        Critical for preventing agent failures.
        """
        capabilities = self.AGENT_REGISTRY[agent_type]
        validation_results = {
            'has_required_context': True,
            'tier_compliant': True,
            'dependencies_met': True,
            'data_sources_available': True
        }
        
        # Check required context
        for required_context in capabilities.required_context_types:
            if required_context not in context.session_metadata and required_context != "user_query":
                # Check if context is available from previous agents
                context_available = False
                for prev_agent, prev_result in context.execution_history.items():
                    if isinstance(prev_result, dict) and required_context in prev_result:
                        context_available = True
                        break
                
                if not context_available:
                    validation_results['has_required_context'] = False
        
        # Check tier compliance
        if capabilities.tier_restrictions and context.user_tier not in capabilities.tier_restrictions:
            validation_results['tier_compliant'] = False
            
        # Check dependencies
        for dependency in capabilities.dependencies:
            if dependency not in context.execution_history:
                validation_results['dependencies_met'] = False
                break
                
        # Check data sources (simplified)
        if "data" in capabilities.required_context_types and not context.available_data_sources:
            validation_results['data_sources_available'] = False
            
        return validation_results

    def calculate_execution_priority(self, agent_type: AgentType, context: AgentExecutionContext) -> float:
        """
        Calculate execution priority for agent scheduling.
        
        Higher priority agents run first in parallel scenarios.
        """
        base_priority = {
            AgentType.TRIAGE: 1.0,  # Always highest priority
            AgentType.DATA_HELPER: 0.9,
            AgentType.UVS_OPTIMIZER: 0.8,
            AgentType.COST_OPTIMIZER: 0.8,
            AgentType.SECURITY_ANALYZER: 0.7,
            AgentType.REPORTER: 0.6  # Always last
        }.get(agent_type, 0.5)
        
        # Adjust based on context
        if "urgent" in context.user_query.lower():
            base_priority += 0.1
            
        if context.user_tier == SubscriptionTier.ENTERPRISE:
            base_priority += 0.05
            
        return min(1.0, base_priority)

    def determine_error_recovery_strategy(self, failed_agent: AgentType, 
                                        context: AgentExecutionContext) -> Dict[str, Any]:
        """
        Determine recovery strategy when agent fails.
        
        Critical for maintaining service continuity.
        """
        capabilities = self.AGENT_REGISTRY[failed_agent]
        
        # Find alternative agents that could provide similar output
        alternative_agents = []
        for agent_type, agent_caps in self.AGENT_REGISTRY.items():
            if (agent_type != failed_agent and
                any(output_type in capabilities.output_context_types 
                    for output_type in agent_caps.output_context_types)):
                alternative_agents.append(agent_type)
        
        # Determine if execution can continue without this agent
        can_continue = failed_agent != AgentType.TRIAGE  # Triage failure is critical
        
        # Calculate impact on final result quality
        impact_score = 0.5  # Base impact
        if failed_agent == AgentType.TRIAGE:
            impact_score = 1.0  # Critical failure
        elif failed_agent == AgentType.DATA_HELPER:
            impact_score = 0.8  # High impact on data-driven agents
        elif failed_agent == AgentType.REPORTER:
            impact_score = 0.3  # Can provide raw results
            
        return {
            'can_continue': can_continue,
            'alternative_agents': alternative_agents,
            'impact_on_quality': impact_score,
            'recommended_action': 'retry' if impact_score > 0.7 else 'continue_with_alternatives',
            'user_notification_required': impact_score > 0.6
        }

    def optimize_agent_sequence_for_tier(self, base_sequence: List[AgentType], 
                                       user_tier: SubscriptionTier) -> List[AgentType]:
        """
        Optimize agent sequence for specific tier constraints.
        
        Maximizes value delivery within tier limits.
        """
        tier_config = self.TIER_LIMITS[user_tier]
        max_agents = tier_config['max_agents_per_execution']
        allowed_agents = set(tier_config['allowed_agent_types'])
        
        # Filter by allowed agents
        filtered_sequence = [agent for agent in base_sequence if agent in allowed_agents]
        
        # If within limits, return as-is
        if len(filtered_sequence) <= max_agents:
            return filtered_sequence
            
        # Need to trim sequence - prioritize based on business value
        agent_value_scores = {
            AgentType.TRIAGE: 1.0,  # Always keep
            AgentType.DATA_HELPER: 0.9,  # High value
            AgentType.COST_OPTIMIZER: 0.8,  # Direct ROI value
            AgentType.UVS_OPTIMIZER: 0.7,  # Performance value
            AgentType.SECURITY_ANALYZER: 0.6,  # Compliance value
            AgentType.REPORTER: 0.5  # Nice to have
        }
        
        # Sort by value score and take top N
        sorted_agents = sorted(filtered_sequence, 
                             key=lambda agent: agent_value_scores.get(agent, 0.0), 
                             reverse=True)
        
        optimized_sequence = sorted_agents[:max_agents]
        
        # Ensure dependencies are maintained
        return self._resolve_dependencies(optimized_sequence)

    def calculate_business_impact_score(self, execution_results: List[AgentExecutionResult]) -> Dict[str, float]:
        """
        Calculate business impact score for completed execution.
        
        Used for optimization and customer success metrics.
        """
        if not execution_results:
            return {'overall_impact': 0.0, 'component_scores': {}}
            
        component_scores = {}
        
        # Score each agent's contribution
        for result in execution_results:
            if result.status == ExecutionStatus.COMPLETED:
                base_score = result.confidence_score
                
                # Adjust based on agent type business value
                business_multipliers = {
                    AgentType.TRIAGE: 0.2,  # Enables everything else
                    AgentType.DATA_HELPER: 0.25,  # Foundation for insights
                    AgentType.COST_OPTIMIZER: 0.3,  # Direct ROI
                    AgentType.UVS_OPTIMIZER: 0.25,  # Performance improvements
                    AgentType.SECURITY_ANALYZER: 0.2,  # Risk mitigation
                    AgentType.REPORTER: 0.15  # Presentation value
                }
                
                multiplier = business_multipliers.get(result.agent_type, 0.1)
                component_scores[result.agent_type.value] = base_score * multiplier
            else:
                component_scores[result.agent_type.value] = 0.0
        
        # Calculate overall impact
        overall_impact = sum(component_scores.values())
        
        # Bonus for successful multi-agent coordination
        successful_agents = sum(1 for result in execution_results if result.status == ExecutionStatus.COMPLETED)
        if successful_agents >= 3:
            coordination_bonus = 0.1 * (successful_agents - 2)
            overall_impact += coordination_bonus
            component_scores['coordination_bonus'] = coordination_bonus
            
        return {
            'overall_impact': min(1.0, overall_impact),
            'component_scores': component_scores,
            'successful_agents': successful_agents,
            'total_execution_time': sum(result.execution_time_seconds for result in execution_results)
        }

    # PRIVATE HELPER METHODS

    def _resolve_dependencies(self, agent_sequence: List[AgentType]) -> List[AgentType]:
        """Resolve and reorder agents based on dependencies."""
        resolved_sequence = []
        remaining_agents = set(agent_sequence)
        
        # Keep resolving until all agents are ordered
        while remaining_agents:
            # Find agents with no unmet dependencies
            ready_agents = []
            for agent in remaining_agents:
                dependencies = set(self.AGENT_REGISTRY[agent].dependencies)
                if dependencies.issubset(set(resolved_sequence)):
                    ready_agents.append(agent)
            
            if not ready_agents:
                # Circular dependency or missing dependency - add remaining in original order
                ready_agents = list(remaining_agents)
                
            # Add first ready agent to sequence
            next_agent = ready_agents[0]
            resolved_sequence.append(next_agent)
            remaining_agents.remove(next_agent)
            
        return resolved_sequence


@pytest.mark.golden_path
@pytest.mark.unit
class TestAIAgentOrchestrationBusinessLogic:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Test AI agent orchestration business logic that drives value delivery."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.orchestrator = AgentOrchestrator()
        
    def _create_test_context(self, user_tier: SubscriptionTier = SubscriptionTier.MID, 
                           execution_history: Optional[Dict] = None) -> AgentExecutionContext:
        """Helper to create test execution contexts."""
        return AgentExecutionContext(
            user_query="Optimize my cloud costs and improve performance",
            user_tier=user_tier,
            execution_history=execution_history or {},
            available_data_sources=["aws_billing", "cloudwatch_metrics"],
            session_metadata={"user_id": str(uuid.uuid4())}
        )
        
    def _create_test_result(self, agent_type: AgentType, 
                          status: ExecutionStatus = ExecutionStatus.COMPLETED,
                          confidence: float = 0.85) -> AgentExecutionResult:
        """Helper to create test execution results."""
        return AgentExecutionResult(
            agent_type=agent_type,
            status=status,
            output_data={"test": "result"},
            execution_time_seconds=30.0,
            tokens_used=1000,
            confidence_score=confidence,
            error_message=None if status == ExecutionStatus.COMPLETED else "Test error",
            next_recommended_agents=[]
        )

    # EXECUTION PLAN CREATION TESTS

    def test_basic_execution_plan_creation(self):
        """Test basic execution plan creation for mid-tier customer."""
        plan = self.orchestrator.create_execution_plan(
            "Optimize my AWS costs", 
            SubscriptionTier.MID
        )
        
        assert AgentType.TRIAGE in plan.execution_sequence  # Always included
        assert AgentType.DATA_HELPER in plan.execution_sequence  # Needed for cost analysis
        assert AgentType.COST_OPTIMIZER in plan.execution_sequence  # Matches query
        assert plan.tier_compliance is True
        assert plan.estimated_total_time > 0
        assert plan.estimated_total_cost > 0

    def test_free_tier_execution_plan_limits(self):
        """Test that Free tier gets limited execution plan."""
        plan = self.orchestrator.create_execution_plan(
            "Optimize everything - cost, security, performance",
            SubscriptionTier.FREE
        )
        
        # Free tier limited to 2 agents
        assert len(plan.execution_sequence) <= 2
        assert plan.tier_compliance is True
        
        # Should prioritize basic agents over premium ones
        assert AgentType.TRIAGE in plan.execution_sequence
        allowed_free_agents = {AgentType.TRIAGE, AgentType.DATA_HELPER, AgentType.REPORTER}
        for agent in plan.execution_sequence:
            assert agent in allowed_free_agents

    def test_enterprise_tier_execution_plan_full_features(self):
        """Test Enterprise tier gets full feature execution plan."""
        plan = self.orchestrator.create_execution_plan(
            "Comprehensive analysis of costs, security, and performance optimization",
            SubscriptionTier.ENTERPRISE
        )
        
        # Enterprise should get comprehensive analysis
        assert len(plan.execution_sequence) >= 4
        assert plan.tier_compliance is True
        
        # Should include all relevant agents
        assert AgentType.TRIAGE in plan.execution_sequence
        assert AgentType.DATA_HELPER in plan.execution_sequence
        assert AgentType.COST_OPTIMIZER in plan.execution_sequence
        assert AgentType.SECURITY_ANALYZER in plan.execution_sequence

    def test_execution_plan_dependency_resolution(self):
        """Test that execution plan properly orders agents by dependencies."""
        plan = self.orchestrator.create_execution_plan(
            "Security and cost analysis",
            SubscriptionTier.ENTERPRISE
        )
        
        # Triage should come before agents that depend on it
        triage_index = plan.execution_sequence.index(AgentType.TRIAGE)
        
        if AgentType.DATA_HELPER in plan.execution_sequence:
            data_helper_index = plan.execution_sequence.index(AgentType.DATA_HELPER)
            assert triage_index < data_helper_index
            
        if AgentType.SECURITY_ANALYZER in plan.execution_sequence:
            security_index = plan.execution_sequence.index(AgentType.SECURITY_ANALYZER)
            assert triage_index < security_index

    def test_preferred_agents_consideration(self):
        """Test that preferred agents are included when possible."""
        preferred = [AgentType.UVS_OPTIMIZER, AgentType.REPORTER]
        
        plan = self.orchestrator.create_execution_plan(
            "General optimization query",
            SubscriptionTier.MID,
            preferred_agents=preferred
        )
        
        # Should include preferred agents if tier allows
        assert AgentType.UVS_OPTIMIZER in plan.execution_sequence
        # Reporter might not be included if no analysis agents present
        
        assert plan.tier_compliance is True

    # EXECUTION CONTEXT VALIDATION TESTS

    def test_valid_execution_context(self):
        """Test validation of valid execution context."""
        context = self._create_test_context()
        context.execution_history[AgentType.TRIAGE] = {"problem_category": "cost_optimization"}
        
        result = self.orchestrator.validate_execution_context(context, AgentType.DATA_HELPER)
        
        assert result['has_required_context'] is True
        assert result['tier_compliant'] is True
        assert result['dependencies_met'] is True

    def test_missing_required_context(self):
        """Test validation with missing required context."""
        context = self._create_test_context()
        # No execution history provided
        
        result = self.orchestrator.validate_execution_context(context, AgentType.DATA_HELPER)
        
        assert result['has_required_context'] is False
        assert result['dependencies_met'] is False

    def test_tier_restriction_validation(self):
        """Test tier restriction validation."""
        context = self._create_test_context(user_tier=SubscriptionTier.FREE)
        
        result = self.orchestrator.validate_execution_context(context, AgentType.SECURITY_ANALYZER)
        
        # Security analyzer not available to Free tier
        assert result['tier_compliant'] is False

    def test_dependency_validation(self):
        """Test dependency validation logic."""
        context = self._create_test_context()
        # UVS Optimizer requires Triage and Data Helper
        
        result = self.orchestrator.validate_execution_context(context, AgentType.UVS_OPTIMIZER)
        
        assert result['dependencies_met'] is False
        
        # Add required dependencies
        context.execution_history[AgentType.TRIAGE] = {"problem_category": "performance"}
        context.execution_history[AgentType.DATA_HELPER] = {"relevant_data": "metrics"}
        
        result = self.orchestrator.validate_execution_context(context, AgentType.UVS_OPTIMIZER)
        
        assert result['dependencies_met'] is True

    # EXECUTION PRIORITY CALCULATION TESTS

    def test_agent_priority_calculation(self):
        """Test agent priority calculation logic."""
        context = self._create_test_context()
        
        triage_priority = self.orchestrator.calculate_execution_priority(AgentType.TRIAGE, context)
        data_priority = self.orchestrator.calculate_execution_priority(AgentType.DATA_HELPER, context)
        reporter_priority = self.orchestrator.calculate_execution_priority(AgentType.REPORTER, context)
        
        # Triage should have highest priority
        assert triage_priority > data_priority > reporter_priority

    def test_priority_adjustments_for_urgency(self):
        """Test priority adjustments for urgent queries."""
        urgent_context = self._create_test_context()
        urgent_context.user_query = "URGENT: Fix critical security issue"
        
        normal_context = self._create_test_context()
        normal_context.user_query = "Routine security review"
        
        urgent_priority = self.orchestrator.calculate_execution_priority(AgentType.SECURITY_ANALYZER, urgent_context)
        normal_priority = self.orchestrator.calculate_execution_priority(AgentType.SECURITY_ANALYZER, normal_context)
        
        assert urgent_priority > normal_priority

    def test_priority_adjustments_for_enterprise(self):
        """Test priority adjustments for Enterprise tier."""
        enterprise_context = self._create_test_context(user_tier=SubscriptionTier.ENTERPRISE)
        mid_context = self._create_test_context(user_tier=SubscriptionTier.MID)
        
        enterprise_priority = self.orchestrator.calculate_execution_priority(AgentType.COST_OPTIMIZER, enterprise_context)
        mid_priority = self.orchestrator.calculate_execution_priority(AgentType.COST_OPTIMIZER, mid_context)
        
        assert enterprise_priority > mid_priority

    # ERROR RECOVERY STRATEGY TESTS

    def test_triage_agent_failure_recovery(self):
        """Test recovery strategy for critical Triage agent failure."""
        context = self._create_test_context()
        
        recovery = self.orchestrator.determine_error_recovery_strategy(AgentType.TRIAGE, context)
        
        assert recovery['can_continue'] is False  # Triage failure is critical
        assert recovery['impact_on_quality'] == 1.0  # Maximum impact
        assert recovery['recommended_action'] == 'retry'
        assert recovery['user_notification_required'] is True

    def test_reporter_agent_failure_recovery(self):
        """Test recovery strategy for Reporter agent failure."""
        context = self._create_test_context()
        
        recovery = self.orchestrator.determine_error_recovery_strategy(AgentType.REPORTER, context)
        
        assert recovery['can_continue'] is True  # Can provide raw results
        assert recovery['impact_on_quality'] == 0.3  # Low impact
        assert recovery['recommended_action'] == 'continue_with_alternatives'

    def test_data_helper_failure_recovery(self):
        """Test recovery strategy for Data Helper failure."""
        context = self._create_test_context()
        
        recovery = self.orchestrator.determine_error_recovery_strategy(AgentType.DATA_HELPER, context)
        
        assert recovery['can_continue'] is True
        assert recovery['impact_on_quality'] == 0.8  # High impact on downstream agents
        assert recovery['recommended_action'] == 'retry'  # Should retry due to high impact
        assert recovery['user_notification_required'] is True

    # TIER OPTIMIZATION TESTS

    def test_sequence_optimization_for_free_tier(self):
        """Test agent sequence optimization for Free tier."""
        full_sequence = [AgentType.TRIAGE, AgentType.DATA_HELPER, AgentType.UVS_OPTIMIZER, 
                        AgentType.COST_OPTIMIZER, AgentType.SECURITY_ANALYZER, AgentType.REPORTER]
        
        optimized = self.orchestrator.optimize_agent_sequence_for_tier(full_sequence, SubscriptionTier.FREE)
        
        assert len(optimized) <= 2  # Free tier limit
        assert AgentType.TRIAGE in optimized  # Always keep highest priority
        # Should not include tier-restricted agents
        assert AgentType.SECURITY_ANALYZER not in optimized

    def test_sequence_optimization_for_early_tier(self):
        """Test agent sequence optimization for Early tier."""
        full_sequence = [AgentType.TRIAGE, AgentType.DATA_HELPER, AgentType.UVS_OPTIMIZER, 
                        AgentType.COST_OPTIMIZER, AgentType.SECURITY_ANALYZER, AgentType.REPORTER]
        
        optimized = self.orchestrator.optimize_agent_sequence_for_tier(full_sequence, SubscriptionTier.EARLY)
        
        assert len(optimized) <= 4  # Early tier limit
        assert AgentType.TRIAGE in optimized
        # Should prioritize high-value agents
        assert AgentType.COST_OPTIMIZER in optimized  # High business value

    def test_dependency_preservation_in_optimization(self):
        """Test that optimization preserves agent dependencies."""
        sequence = [AgentType.UVS_OPTIMIZER, AgentType.TRIAGE, AgentType.DATA_HELPER]  # Wrong order
        
        optimized = self.orchestrator.optimize_agent_sequence_for_tier(sequence, SubscriptionTier.MID)
        
        # Should reorder to respect dependencies
        triage_index = optimized.index(AgentType.TRIAGE)
        data_helper_index = optimized.index(AgentType.DATA_HELPER)
        uvs_index = optimized.index(AgentType.UVS_OPTIMIZER)
        
        assert triage_index < data_helper_index < uvs_index

    # BUSINESS IMPACT SCORING TESTS

    def test_business_impact_calculation_successful_execution(self):
        """Test business impact calculation for successful execution."""
        results = [
            self._create_test_result(AgentType.TRIAGE, ExecutionStatus.COMPLETED, 0.9),
            self._create_test_result(AgentType.DATA_HELPER, ExecutionStatus.COMPLETED, 0.8),
            self._create_test_result(AgentType.COST_OPTIMIZER, ExecutionStatus.COMPLETED, 0.85),
        ]
        
        impact = self.orchestrator.calculate_business_impact_score(results)
        
        assert impact['overall_impact'] > 0.5  # Should have meaningful impact
        assert impact['successful_agents'] == 3
        assert 'cost_optimizer' in impact['component_scores']
        # Should include coordination bonus for 3+ agents
        assert 'coordination_bonus' in impact['component_scores']

    def test_business_impact_with_failures(self):
        """Test business impact calculation with some agent failures."""
        results = [
            self._create_test_result(AgentType.TRIAGE, ExecutionStatus.COMPLETED, 0.9),
            self._create_test_result(AgentType.DATA_HELPER, ExecutionStatus.FAILED, 0.0),
            self._create_test_result(AgentType.COST_OPTIMIZER, ExecutionStatus.COMPLETED, 0.8),
        ]
        
        impact = self.orchestrator.calculate_business_impact_score(results)
        
        assert impact['successful_agents'] == 2
        assert impact['component_scores']['data_helper'] == 0.0  # Failed agent contributes nothing
        assert impact['component_scores']['cost_optimizer'] > 0  # Successful agent contributes
        assert 'coordination_bonus' not in impact['component_scores']  # No bonus with <3 successful

    def test_empty_execution_results_impact(self):
        """Test business impact calculation with no execution results."""
        impact = self.orchestrator.calculate_business_impact_score([])
        
        assert impact['overall_impact'] == 0.0
        assert impact['component_scores'] == {}

    # CONFIGURATION AND CONSTANTS TESTS

    def test_agent_registry_completeness(self):
        """Test that agent registry is complete and well-formed."""
        for agent_type in AgentType:
            assert agent_type in self.orchestrator.AGENT_REGISTRY
            
            capabilities = self.orchestrator.AGENT_REGISTRY[agent_type]
            assert capabilities.agent_type == agent_type
            assert isinstance(capabilities.required_context_types, list)
            assert isinstance(capabilities.output_context_types, list)
            assert capabilities.execution_time_limit_seconds > 0

    def test_tier_limits_configuration(self):
        """Test tier limits configuration is logical."""
        for tier in SubscriptionTier:
            assert tier in self.orchestrator.TIER_LIMITS
            
            config = self.orchestrator.TIER_LIMITS[tier]
            assert config['max_agents_per_execution'] > 0
            assert config['max_execution_time'] > 0
            assert isinstance(config['allowed_agent_types'], list)
        
        # Verify tier progression (higher tiers get more resources)
        assert (self.orchestrator.TIER_LIMITS[SubscriptionTier.FREE]['max_agents_per_execution'] <
                self.orchestrator.TIER_LIMITS[SubscriptionTier.ENTERPRISE]['max_agents_per_execution'])

    def test_agent_dependencies_are_valid(self):
        """Test that all agent dependencies reference valid agents."""
        for agent_type, capabilities in self.orchestrator.AGENT_REGISTRY.items():
            for dependency in capabilities.dependencies:
                assert dependency in AgentType  # Dependency must be a valid agent type
                assert dependency in self.orchestrator.AGENT_REGISTRY  # Must be in registry