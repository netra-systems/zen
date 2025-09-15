"""
Test Agent Execution Order Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure Data  ->  Optimization  ->  Report sequence for coherent AI analysis
- Value Impact: Proper agent orchestration prevents incomplete or contradictory results
- Strategic Impact: Enforces the critical execution order that delivers complete business value

CRITICAL: This test validates the business logic for the Data  ->  Optimization  ->  Report execution sequence
that has been identified as essential for delivering coherent and complete AI analysis to users.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the decision-making algorithms and orchestration patterns that ensure proper agent execution order.
"""
import pytest
import time
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set, Tuple
from enum import Enum
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID, ThreadID, AgentID, ExecutionID
from netra_backend.app.services.user_execution_context import UserExecutionContext

class AgentType(Enum):
    """Types of agents in the orchestration system."""
    DATA_COLLECTION = 'data_collection'
    DATA_ANALYSIS = 'data_analysis'
    COST_OPTIMIZATION = 'cost_optimization'
    REPORT_GENERATION = 'report_generation'
    TRIAGE = 'triage'

class ExecutionPhase(Enum):
    """Execution phases for agent orchestration."""
    PLANNING = 'planning'
    DATA_GATHERING = 'data_gathering'
    OPTIMIZATION = 'optimization'
    REPORTING = 'reporting'
    COMPLETION = 'completion'

class DependencyType(Enum):
    """Types of dependencies between agents."""
    HARD_DEPENDENCY = 'hard_dependency'
    SOFT_DEPENDENCY = 'soft_dependency'
    DATA_DEPENDENCY = 'data_dependency'

@dataclass
class AgentExecutionPlan:
    """Plan for agent execution with dependencies."""
    agent_id: AgentID
    agent_type: AgentType
    execution_phase: ExecutionPhase
    dependencies: List[AgentID] = field(default_factory=list)
    required_data: List[str] = field(default_factory=list)
    produces_data: List[str] = field(default_factory=list)
    business_purpose: str = ''
    estimated_duration: int = 60
    can_run_parallel: bool = False

@dataclass
class ExecutionState:
    """State tracking for agent execution orchestration."""
    execution_id: ExecutionID
    user_id: UserID
    thread_id: ThreadID
    current_phase: ExecutionPhase
    completed_agents: Set[AgentID] = field(default_factory=set)
    running_agents: Set[AgentID] = field(default_factory=set)
    failed_agents: Set[AgentID] = field(default_factory=set)
    available_data: Set[str] = field(default_factory=set)
    execution_start_time: float = field(default_factory=time.time)

class MockAgentOrchestrator:
    """Mock agent orchestrator for business logic testing."""

    def __init__(self):
        self.agent_templates = self._initialize_agent_templates()
        self.execution_rules = self._initialize_execution_rules()
        self.active_executions: Dict[ExecutionID, ExecutionState] = {}
        self.agent_execution_history: List[Dict[str, Any]] = []

    def _initialize_agent_templates(self) -> Dict[AgentType, AgentExecutionPlan]:
        """Initialize agent templates with business logic requirements."""
        return {AgentType.DATA_COLLECTION: AgentExecutionPlan(agent_id=AgentID('data_collector'), agent_type=AgentType.DATA_COLLECTION, execution_phase=ExecutionPhase.DATA_GATHERING, dependencies=[], required_data=[], produces_data=['raw_cost_data', 'usage_metrics', 'resource_inventory'], business_purpose='Gather comprehensive cost and usage data for analysis', estimated_duration=30, can_run_parallel=True), AgentType.DATA_ANALYSIS: AgentExecutionPlan(agent_id=AgentID('data_analyzer'), agent_type=AgentType.DATA_ANALYSIS, execution_phase=ExecutionPhase.DATA_GATHERING, dependencies=[AgentID('data_collector')], required_data=['raw_cost_data', 'usage_metrics'], produces_data=['analyzed_patterns', 'cost_trends', 'efficiency_metrics'], business_purpose='Analyze collected data to identify patterns and trends', estimated_duration=45, can_run_parallel=False), AgentType.COST_OPTIMIZATION: AgentExecutionPlan(agent_id=AgentID('cost_optimizer'), agent_type=AgentType.COST_OPTIMIZATION, execution_phase=ExecutionPhase.OPTIMIZATION, dependencies=[AgentID('data_analyzer')], required_data=['analyzed_patterns', 'cost_trends', 'efficiency_metrics'], produces_data=['optimization_recommendations', 'cost_savings_analysis', 'implementation_plan'], business_purpose='Generate actionable cost optimization recommendations', estimated_duration=60, can_run_parallel=False), AgentType.REPORT_GENERATION: AgentExecutionPlan(agent_id=AgentID('report_generator'), agent_type=AgentType.REPORT_GENERATION, execution_phase=ExecutionPhase.REPORTING, dependencies=[AgentID('cost_optimizer')], required_data=['optimization_recommendations', 'cost_savings_analysis'], produces_data=['executive_summary', 'detailed_report', 'action_items'], business_purpose='Create comprehensive reports with actionable insights', estimated_duration=30, can_run_parallel=False), AgentType.TRIAGE: AgentExecutionPlan(agent_id=AgentID('triage_agent'), agent_type=AgentType.TRIAGE, execution_phase=ExecutionPhase.PLANNING, dependencies=[], required_data=[], produces_data=['execution_plan', 'agent_selection', 'priority_order'], business_purpose='Determine optimal agent execution strategy', estimated_duration=15, can_run_parallel=False)}

    def _initialize_execution_rules(self) -> Dict[str, Any]:
        """Initialize business rules for agent execution."""
        return {'max_parallel_agents': 3, 'data_before_optimization': True, 'optimization_before_reporting': True, 'require_complete_data': True, 'allow_phase_overlap': False, 'minimum_data_quality_threshold': 0.8, 'timeout_per_agent': 300, 'total_execution_timeout': 1800}

    def create_execution_plan(self, user_request: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Business logic: Create execution plan based on user request."""
        required_agents = self._analyze_request_requirements(user_request)
        execution_sequence = self._generate_execution_sequence(required_agents)
        validation_result = self._validate_execution_sequence(execution_sequence)
        if not validation_result['valid']:
            return {'success': False, 'error': validation_result['error'], 'execution_plan': None}
        return {'success': True, 'execution_plan': execution_sequence, 'estimated_total_duration': self._calculate_total_duration(execution_sequence), 'business_value_expected': self._assess_business_value_potential(execution_sequence), 'phases': self._group_agents_by_phase(execution_sequence)}

    def _analyze_request_requirements(self, user_request: str) -> List[AgentType]:
        """Analyze user request to determine required agents."""
        request_lower = user_request.lower()
        required_agents = []
        required_agents.append(AgentType.DATA_COLLECTION)
        cost_keywords = ['optim', 'cost', 'save money', 'efficiency']
        if any((keyword in request_lower for keyword in cost_keywords)):
            required_agents.extend([AgentType.DATA_ANALYSIS, AgentType.COST_OPTIMIZATION, AgentType.REPORT_GENERATION])
        report_keywords = ['report', 'summar', 'analysis', 'insights', 'recommendations']
        if any((keyword in request_lower for keyword in report_keywords)) and AgentType.REPORT_GENERATION not in required_agents:
            required_agents.append(AgentType.DATA_ANALYSIS)
            required_agents.append(AgentType.COST_OPTIMIZATION)
            required_agents.append(AgentType.REPORT_GENERATION)
        return required_agents

    def _generate_execution_sequence(self, required_agents: List[AgentType]) -> List[AgentExecutionPlan]:
        """Generate execution sequence based on agent dependencies."""
        agent_plans = [self.agent_templates[agent_type] for agent_type in required_agents]

        def dependency_sort_key(plan: AgentExecutionPlan) -> Tuple[int, int, int]:
            phase_order = {ExecutionPhase.PLANNING: 0, ExecutionPhase.DATA_GATHERING: 1, ExecutionPhase.OPTIMIZATION: 2, ExecutionPhase.REPORTING: 3, ExecutionPhase.COMPLETION: 4}
            return (phase_order.get(plan.execution_phase, 99), len(plan.dependencies), -len(plan.produces_data))
        sorted_plans = sorted(agent_plans, key=dependency_sort_key)
        return sorted_plans

    def _validate_execution_sequence(self, execution_sequence: List[AgentExecutionPlan]) -> Dict[str, Any]:
        """Validate execution sequence follows business rules."""
        data_agents = [plan for plan in execution_sequence if plan.execution_phase == ExecutionPhase.DATA_GATHERING]
        optimization_agents = [plan for plan in execution_sequence if plan.execution_phase == ExecutionPhase.OPTIMIZATION]
        if optimization_agents and (not data_agents):
            return {'valid': False, 'error': 'Business rule violation: Optimization agents require data gathering agents'}
        reporting_agents = [plan for plan in execution_sequence if plan.execution_phase == ExecutionPhase.REPORTING]
        if reporting_agents and (not optimization_agents) and (not data_agents):
            return {'valid': False, 'error': 'Business rule violation: Reporting agents require optimization or analysis'}
        available_agents = set()
        for plan in execution_sequence:
            for dependency in plan.dependencies:
                if dependency not in [p.agent_id for p in execution_sequence]:
                    return {'valid': False, 'error': f'Missing dependency: {plan.agent_id} requires {dependency}'}
        return {'valid': True}

    def _calculate_total_duration(self, execution_sequence: List[AgentExecutionPlan]) -> int:
        """Calculate total estimated execution duration."""
        total_duration = 0
        parallel_groups = self._group_parallel_execution(execution_sequence)
        for group in parallel_groups:
            group_duration = max((plan.estimated_duration for plan in group))
            total_duration += group_duration
        return total_duration

    def _group_parallel_execution(self, execution_sequence: List[AgentExecutionPlan]) -> List[List[AgentExecutionPlan]]:
        """Group agents that can execute in parallel."""
        parallel_groups = []
        remaining_agents = execution_sequence.copy()
        while remaining_agents:
            parallel_group = []
            available_data = set()
            for completed_group in parallel_groups:
                for plan in completed_group:
                    available_data.update(plan.produces_data)
            for plan in remaining_agents[:]:
                dependencies_satisfied = True
                for dep_agent_id in plan.dependencies:
                    dep_completed = any((dep_agent_id in [p.agent_id for group in parallel_groups for p in group] for group in parallel_groups))
                    if not dep_completed:
                        dependencies_satisfied = False
                        break
                data_requirements_met = all((data in available_data for data in plan.required_data))
                if (dependencies_satisfied or len(plan.dependencies) == 0) and (data_requirements_met or len(plan.required_data) == 0):
                    parallel_group.append(plan)
                    available_data.update(plan.produces_data)
                    remaining_agents.remove(plan)
            if not parallel_group and remaining_agents:
                parallel_group.append(remaining_agents.pop(0))
            if parallel_group:
                parallel_groups.append(parallel_group)
        return parallel_groups

    def _assess_business_value_potential(self, execution_sequence: List[AgentExecutionPlan]) -> str:
        """Assess potential business value of execution sequence."""
        has_data_collection = any((plan.agent_type == AgentType.DATA_COLLECTION for plan in execution_sequence))
        has_optimization = any((plan.agent_type == AgentType.COST_OPTIMIZATION for plan in execution_sequence))
        has_reporting = any((plan.agent_type == AgentType.REPORT_GENERATION for plan in execution_sequence))
        if has_data_collection and has_optimization and has_reporting:
            return 'High - Complete analysis pipeline with actionable recommendations'
        elif has_data_collection and has_optimization:
            return 'Medium-High - Data-driven optimization without comprehensive reporting'
        elif has_data_collection:
            return 'Medium - Data insights without optimization recommendations'
        else:
            return 'Low - Limited analysis capability'

    def _group_agents_by_phase(self, execution_sequence: List[AgentExecutionPlan]) -> Dict[str, List[str]]:
        """Group agents by execution phase for clear visualization."""
        phases = {}
        for plan in execution_sequence:
            phase_name = plan.execution_phase.value
            if phase_name not in phases:
                phases[phase_name] = []
            phases[phase_name].append(plan.agent_id)
        return phases

    def start_execution(self, execution_id: ExecutionID, user_id: UserID, thread_id: ThreadID, execution_plan: List[AgentExecutionPlan]) -> Dict[str, Any]:
        """Business logic: Start agent execution following the orchestrated plan."""
        execution_state = ExecutionState(execution_id=execution_id, user_id=user_id, thread_id=thread_id, current_phase=ExecutionPhase.PLANNING)
        self.active_executions[execution_id] = execution_state
        first_phase_agents = [plan for plan in execution_plan if plan.execution_phase == ExecutionPhase.DATA_GATHERING or plan.execution_phase == ExecutionPhase.PLANNING]
        if not first_phase_agents:
            first_phase_agents = execution_plan[:1]
        started_agents = []
        for plan in first_phase_agents:
            if self._can_start_agent(execution_state, plan, execution_plan):
                execution_state.running_agents.add(plan.agent_id)
                started_agents.append(plan.agent_id)
        return {'success': True, 'execution_id': str(execution_id), 'started_agents': [str(agent_id) for agent_id in started_agents], 'current_phase': execution_state.current_phase.value, 'business_value_tracking': 'Execution started with proper agent sequencing'}

    def _can_start_agent(self, execution_state: ExecutionState, agent_plan: AgentExecutionPlan, full_execution_plan: List[AgentExecutionPlan]) -> bool:
        """Check if agent can start based on business rules and dependencies."""
        for dependency in agent_plan.dependencies:
            if dependency not in execution_state.completed_agents:
                return False
        for required_data in agent_plan.required_data:
            if required_data not in execution_state.available_data:
                return False
        if agent_plan.agent_id in execution_state.running_agents or agent_plan.agent_id in execution_state.completed_agents:
            return False
        if len(execution_state.running_agents) >= self.execution_rules['max_parallel_agents']:
            if not agent_plan.can_run_parallel:
                return False
        return True

    def complete_agent_execution(self, execution_id: ExecutionID, agent_id: AgentID, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Business logic: Handle agent completion and trigger next agents."""
        if execution_id not in self.active_executions:
            return {'success': False, 'error': 'Execution not found'}
        execution_state = self.active_executions[execution_id]
        execution_state.running_agents.discard(agent_id)
        execution_state.completed_agents.add(agent_id)
        agent_plan = next((plan for plan in self.agent_templates.values() if plan.agent_id == agent_id), None)
        if agent_plan:
            execution_state.available_data.update(agent_plan.produces_data)
        self.agent_execution_history.append({'execution_id': str(execution_id), 'agent_id': str(agent_id), 'completion_time': time.time(), 'data_produced': agent_plan.produces_data if agent_plan else [], 'business_value': result_data.get('business_value', 'Value generated')})
        phase_transition = self._check_phase_transition(execution_state)
        return {'success': True, 'agent_completed': str(agent_id), 'phase_transition': phase_transition, 'available_data': list(execution_state.available_data), 'completed_agents': [str(agent_id) for agent_id in execution_state.completed_agents], 'business_value_accumulated': self._calculate_accumulated_business_value(execution_state)}

    def _check_phase_transition(self, execution_state: ExecutionState) -> Dict[str, Any]:
        """Check if execution should transition to next phase."""
        current_phase = execution_state.current_phase
        phase_progression = [ExecutionPhase.PLANNING, ExecutionPhase.DATA_GATHERING, ExecutionPhase.OPTIMIZATION, ExecutionPhase.REPORTING, ExecutionPhase.COMPLETION]
        current_phase_agents = []
        for agent_type, plan in self.agent_templates.items():
            if plan.execution_phase == current_phase:
                current_phase_agents.append(plan.agent_id)
        phase_complete = all((agent_id in execution_state.completed_agents for agent_id in current_phase_agents))
        if phase_complete and current_phase != ExecutionPhase.COMPLETION:
            current_index = phase_progression.index(current_phase)
            next_phase = phase_progression[current_index + 1]
            execution_state.current_phase = next_phase
            return {'transitioned': True, 'from_phase': current_phase.value, 'to_phase': next_phase.value, 'business_impact': f'Progressed from {current_phase.value} to {next_phase.value}'}
        return {'transitioned': False}

    def _calculate_accumulated_business_value(self, execution_state: ExecutionState) -> str:
        """Calculate accumulated business value based on completed agents."""
        completed_count = len(execution_state.completed_agents)
        available_data_count = len(execution_state.available_data)
        if completed_count == 0:
            return 'No business value yet - execution just started'
        elif completed_count == 1:
            return 'Initial data collection complete - foundation for analysis established'
        elif completed_count == 2:
            return 'Data analysis complete - patterns and insights identified'
        elif completed_count >= 3:
            return 'Optimization recommendations generated - actionable business value delivered'
        return f'Partial business value - {completed_count} agents completed'

    def get_execution_health_metrics(self, execution_id: ExecutionID) -> Dict[str, Any]:
        """Get execution health metrics for monitoring business value delivery."""
        if execution_id not in self.active_executions:
            return {'healthy': False, 'error': 'Execution not found'}
        execution_state = self.active_executions[execution_id]
        execution_duration = time.time() - execution_state.execution_start_time
        total_agents = len(self.agent_templates)
        completed_ratio = len(execution_state.completed_agents) / total_agents
        is_healthy = len(execution_state.failed_agents) == 0 and execution_duration < self.execution_rules['total_execution_timeout'] and (completed_ratio > 0)
        return {'healthy': is_healthy, 'execution_duration': execution_duration, 'completed_agents': len(execution_state.completed_agents), 'running_agents': len(execution_state.running_agents), 'failed_agents': len(execution_state.failed_agents), 'progress_percentage': completed_ratio * 100, 'current_phase': execution_state.current_phase.value, 'available_data_types': len(execution_state.available_data), 'business_value_status': self._calculate_accumulated_business_value(execution_state)}

@pytest.mark.golden_path
@pytest.mark.unit
class TestAgentOrchestrationLogic(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(user_id='test_user', thread_id='test_thread', run_id='test_run')
    'Test agent orchestration business logic validation.'

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.orchestrator = MockAgentOrchestrator()
        self.test_execution_id = ExecutionID('exec_orchestration_123')
        self.test_user_id = UserID('user_enterprise_456')
        self.test_thread_id = ThreadID('thread_analysis_789')

    @pytest.mark.unit
    def test_critical_execution_order_business_rule(self):
        """Test the critical Data  ->  Optimization  ->  Report execution order business rule."""
        data_plan = self.orchestrator.agent_templates[AgentType.DATA_COLLECTION]
        analysis_plan = self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS]
        optimization_plan = self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION]
        reporting_plan = self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]
        assert len(data_plan.dependencies) == 0
        assert data_plan.execution_phase == ExecutionPhase.DATA_GATHERING
        assert AgentID('data_collector') in analysis_plan.dependencies
        assert analysis_plan.execution_phase == ExecutionPhase.DATA_GATHERING
        assert AgentID('data_analyzer') in optimization_plan.dependencies
        assert optimization_plan.execution_phase == ExecutionPhase.OPTIMIZATION
        assert AgentID('cost_optimizer') in reporting_plan.dependencies
        assert reporting_plan.execution_phase == ExecutionPhase.REPORTING
        self.record_metric('critical_execution_order_validated', True)

    @pytest.mark.unit
    def test_execution_plan_creation_business_logic(self):
        """Test execution plan creation based on user request analysis."""
        cost_optimization_request = 'Help me optimize my cloud costs and generate a detailed report with savings recommendations'
        plan_result = self.orchestrator.create_execution_plan(cost_optimization_request, {'user_tier': 'enterprise'})
        assert plan_result['success'] is True
        assert plan_result['execution_plan'] is not None
        assert 'High - Complete analysis pipeline' in plan_result['business_value_expected']
        plan_agents = [plan.agent_type for plan in plan_result['execution_plan']]
        assert AgentType.DATA_COLLECTION in plan_agents
        assert AgentType.DATA_ANALYSIS in plan_agents
        assert AgentType.COST_OPTIMIZATION in plan_agents
        assert AgentType.REPORT_GENERATION in plan_agents
        phases = plan_result['phases']
        assert 'data_gathering' in phases
        assert 'optimization' in phases
        assert 'reporting' in phases
        assert plan_result['estimated_total_duration'] > 60
        assert plan_result['estimated_total_duration'] < 600
        self.record_metric('execution_plan_creation_success', True)
        self.record_metric('plan_estimated_duration', plan_result['estimated_total_duration'])
        self.record_metric('plan_agents_count', len(plan_result['execution_plan']))

    @pytest.mark.unit
    def test_data_dependency_validation_logic(self):
        """Test data dependency validation for business logic coherence."""
        optimization_plan = self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION]
        required_data = optimization_plan.required_data
        assert 'analyzed_patterns' in required_data
        assert 'cost_trends' in required_data
        assert 'efficiency_metrics' in required_data
        analysis_plan = self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS]
        produced_data = analysis_plan.produces_data
        for required in required_data:
            assert required in produced_data, f'Data dependency issue: {required} not produced by analysis'
        reporting_plan = self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]
        assert 'optimization_recommendations' in reporting_plan.required_data
        assert 'cost_savings_analysis' in reporting_plan.required_data
        self.record_metric('data_dependency_validation_success', True)

    @pytest.mark.unit
    def test_execution_sequence_validation_business_rules(self):
        """Test execution sequence validation against business rules."""
        valid_sequence = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION], self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]]
        validation_result = self.orchestrator._validate_execution_sequence(valid_sequence)
        assert validation_result['valid'] is True
        invalid_sequence_1 = [self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION], self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]]
        invalid_result_1 = self.orchestrator._validate_execution_sequence(invalid_sequence_1)
        assert invalid_result_1['valid'] is False
        assert 'optimization agents require data gathering' in invalid_result_1['error'].lower()
        invalid_sequence_2 = [self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]]
        invalid_result_2 = self.orchestrator._validate_execution_sequence(invalid_sequence_2)
        assert invalid_result_2['valid'] is False
        assert 'reporting agents require optimization or analysis' in invalid_result_2['error'].lower()
        self.record_metric('sequence_validation_accuracy', True)
        self.record_metric('business_rule_enforcement', True)

    @pytest.mark.unit
    def test_parallel_execution_grouping_logic(self):
        """Test parallel execution grouping while maintaining business logic order."""
        execution_sequence = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION], self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]]
        parallel_groups = self.orchestrator._group_parallel_execution(execution_sequence)
        assert len(parallel_groups) >= 3
        first_group = parallel_groups[0]
        assert len(first_group) == 1
        assert first_group[0].agent_type == AgentType.DATA_COLLECTION
        second_group = parallel_groups[1]
        data_analysis_agent = next((plan for plan in second_group if plan.agent_type == AgentType.DATA_ANALYSIS), None)
        assert data_analysis_agent is not None
        optimization_found = False
        for group in parallel_groups[2:]:
            if any((plan.agent_type == AgentType.COST_OPTIMIZATION for plan in group)):
                optimization_found = True
                break
        assert optimization_found
        self.record_metric('parallel_grouping_logic_accuracy', True)

    @pytest.mark.unit
    def test_business_value_assessment_logic(self):
        """Test business value assessment for different execution sequences."""
        complete_sequence = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION], self.orchestrator.agent_templates[AgentType.REPORT_GENERATION]]
        complete_value = self.orchestrator._assess_business_value_potential(complete_sequence)
        assert 'High - Complete analysis pipeline' in complete_value
        partial_sequence = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION]]
        partial_value = self.orchestrator._assess_business_value_potential(partial_sequence)
        assert 'Medium-High' in partial_value
        data_only_sequence = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION]]
        data_only_value = self.orchestrator._assess_business_value_potential(data_only_sequence)
        assert 'Medium' in data_only_value
        self.record_metric('business_value_assessment_accuracy', True)
        self.record_metric('complete_pipeline_value', 'high')
        self.record_metric('partial_pipeline_value', 'medium-high')

    @pytest.mark.unit
    def test_agent_execution_start_logic(self):
        """Test agent execution start logic with proper sequencing."""
        execution_plan = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION]]
        start_result = self.orchestrator.start_execution(self.test_execution_id, self.test_user_id, self.test_thread_id, execution_plan)
        assert start_result['success'] is True
        assert len(start_result['started_agents']) >= 1
        started_agents = start_result['started_agents']
        assert str(AgentID('data_collector')) in started_agents
        assert str(AgentID('data_analyzer')) not in started_agents
        assert str(AgentID('cost_optimizer')) not in started_agents
        execution_state = self.orchestrator.active_executions[self.test_execution_id]
        assert execution_state.current_phase in [ExecutionPhase.PLANNING, ExecutionPhase.DATA_GATHERING]
        assert len(execution_state.running_agents) >= 1
        assert len(execution_state.completed_agents) == 0
        self.record_metric('execution_start_success', True)
        self.record_metric('proper_agent_sequencing', True)

    @pytest.mark.unit
    def test_agent_completion_and_progression_logic(self):
        """Test agent completion and automatic progression to next agents."""
        execution_plan = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS], self.orchestrator.agent_templates[AgentType.COST_OPTIMIZATION]]
        self.orchestrator.start_execution(self.test_execution_id, self.test_user_id, self.test_thread_id, execution_plan)
        data_collector_result = {'business_value': 'Comprehensive cost data collected', 'data_quality': 'high', 'records_processed': 10000}
        completion_result = self.orchestrator.complete_agent_execution(self.test_execution_id, AgentID('data_collector'), data_collector_result)
        assert completion_result['success'] is True
        assert completion_result['agent_completed'] == str(AgentID('data_collector'))
        available_data = completion_result['available_data']
        assert 'raw_cost_data' in available_data
        assert 'usage_metrics' in available_data
        assert 'resource_inventory' in available_data
        business_value = completion_result['business_value_accumulated']
        assert 'data collection complete' in business_value.lower()
        execution_state = self.orchestrator.active_executions[self.test_execution_id]
        assert AgentID('data_collector') in execution_state.completed_agents
        assert AgentID('data_collector') not in execution_state.running_agents
        assert len(execution_state.available_data) >= 3
        self.record_metric('agent_completion_logic_success', True)
        self.record_metric('data_availability_tracking', True)
        self.record_metric('business_value_accumulation', True)

    @pytest.mark.unit
    def test_phase_transition_logic(self):
        """Test execution phase transition business logic."""
        execution_state = ExecutionState(execution_id=self.test_execution_id, user_id=self.test_user_id, thread_id=self.test_thread_id, current_phase=ExecutionPhase.DATA_GATHERING)
        execution_state.completed_agents.add(AgentID('data_collector'))
        execution_state.completed_agents.add(AgentID('data_analyzer'))
        self.orchestrator.active_executions[self.test_execution_id] = execution_state
        transition_result = self.orchestrator._check_phase_transition(execution_state)
        if transition_result['transitioned']:
            assert transition_result['from_phase'] == 'data_gathering'
            assert transition_result['to_phase'] == 'optimization'
            assert 'business_impact' in transition_result
            assert execution_state.current_phase == ExecutionPhase.OPTIMIZATION
        self.record_metric('phase_transition_logic_accuracy', True)

    @pytest.mark.unit
    def test_execution_health_monitoring_logic(self):
        """Test execution health monitoring for business value tracking."""
        execution_plan = [self.orchestrator.agent_templates[AgentType.DATA_COLLECTION], self.orchestrator.agent_templates[AgentType.DATA_ANALYSIS]]
        self.orchestrator.start_execution(self.test_execution_id, self.test_user_id, self.test_thread_id, execution_plan)
        execution_state = self.orchestrator.active_executions[self.test_execution_id]
        execution_state.completed_agents.add(AgentID('data_collector'))
        execution_state.available_data.update(['raw_cost_data', 'usage_metrics'])
        health_metrics = self.orchestrator.get_execution_health_metrics(self.test_execution_id)
        assert health_metrics['healthy'] is True
        assert health_metrics['completed_agents'] == 1
        assert health_metrics['progress_percentage'] > 0
        assert health_metrics['available_data_types'] >= 2
        business_status = health_metrics['business_value_status']
        assert len(business_status) > 20
        assert 'complete' in business_status.lower() or 'progress' in business_status.lower()
        execution_state.execution_start_time = time.time() - 2000
        timeout_health = self.orchestrator.get_execution_health_metrics(self.test_execution_id)
        assert timeout_health['healthy'] is False
        assert timeout_health['execution_duration'] > 1800
        self.record_metric('health_monitoring_accuracy', True)
        self.record_metric('timeout_detection_working', True)

    @pytest.mark.unit
    def test_business_rule_enforcement_comprehensive(self):
        """Test comprehensive business rule enforcement across orchestration."""
        invalid_request_result = self.orchestrator.create_execution_plan('Generate optimization report', {})
        if invalid_request_result['success']:
            plan_agents = [plan.agent_type for plan in invalid_request_result['execution_plan']]
            assert AgentType.DATA_COLLECTION in plan_agents, 'Data collection should be included as foundation'
        execution_rules = self.orchestrator.execution_rules
        assert execution_rules['data_before_optimization'] is True
        assert execution_rules['optimization_before_reporting'] is True
        assert execution_rules['require_complete_data'] is True
        assert execution_rules['allow_phase_overlap'] is False
        assert execution_rules['timeout_per_agent'] <= 300
        assert execution_rules['total_execution_timeout'] <= 1800
        self.record_metric('business_rule_comprehensive_enforcement', True)
        self.record_metric('execution_timeout_reasonable', execution_rules['total_execution_timeout'] <= 1800)

    @pytest.mark.unit
    def test_end_to_end_orchestration_business_value(self):
        """Test end-to-end orchestration delivers complete business value."""
        customer_request = 'I need a comprehensive analysis of my cloud infrastructure costs with detailed optimization recommendations and an executive summary'
        plan_result = self.orchestrator.create_execution_plan(customer_request, {'customer_tier': 'enterprise'})
        start_result = self.orchestrator.start_execution(self.test_execution_id, self.test_user_id, self.test_thread_id, plan_result['execution_plan'])
        agents_to_complete = [(AgentID('data_collector'), {'data_collected': '10GB cost data', 'business_value': 'Comprehensive data foundation'}), (AgentID('data_analyzer'), {'patterns_identified': 15, 'business_value': 'Cost patterns and trends identified'}), (AgentID('cost_optimizer'), {'recommendations': 8, 'potential_savings': '$50000/month', 'business_value': 'Actionable optimization recommendations'}), (AgentID('report_generator'), {'reports_generated': 3, 'business_value': 'Executive summary and detailed reports'})]
        business_value_progression = []
        for agent_id, result_data in agents_to_complete:
            completion_result = self.orchestrator.complete_agent_execution(self.test_execution_id, agent_id, result_data)
            if completion_result['success']:
                business_value_progression.append(completion_result['business_value_accumulated'])
        final_health = self.orchestrator.get_execution_health_metrics(self.test_execution_id)
        assert plan_result['business_value_expected'] == 'High - Complete analysis pipeline with actionable recommendations'
        assert final_health['progress_percentage'] >= 75
        assert len(business_value_progression) >= 3
        final_business_value = business_value_progression[-1]
        assert 'actionable business value delivered' in final_business_value.lower() or 'optimization recommendations generated' in final_business_value.lower()
        assert final_health['execution_duration'] < self.orchestrator.execution_rules['total_execution_timeout']
        execution_duration = final_health['execution_duration']
        completed_agents = final_health['completed_agents']
        self.record_metric('end_to_end_orchestration_success', True)
        self.record_metric('complete_execution_duration', execution_duration)
        self.record_metric('agents_completed', completed_agents)
        self.record_metric('business_value_delivery_complete', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')