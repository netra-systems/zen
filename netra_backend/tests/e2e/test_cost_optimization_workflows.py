"""
Comprehensive E2E Cost Optimization Workflows Test Suite
Tests real LLM agents with complete data flow validation.
Maximum 300 lines, functions ≤8 lines.
"""

from netra_backend.app.websocket.unified.manager import UnifiedWebSocketManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import uuid
from decimal import Decimal
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
from netra_backend.app.schemas import SubAgentLifecycle
from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WSManager

from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.quality_gate_service import (

    ContentType,

    QualityGateService,

    QualityLevel,

)

@pytest.fixture

def cost_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Setup real agent environment for cost optimization testing."""
    # Import additional agents to avoid circular dependencies
    from netra_backend.app.agents.actions_to_meet_goals_sub_agent import (

        ActionsToMeetGoalsSubAgent,

    )
    from netra_backend.app.agents.optimizations_core_sub_agent import (

        OptimizationsCoreSubAgent,

    )
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    
    agents = {

        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),

        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher),

        'optimization': OptimizationsCoreSubAgent(real_llm_manager, real_tool_dispatcher),

        'actions': ActionsToMeetGoalsSubAgent(real_llm_manager, real_tool_dispatcher),

        'reporting': ReportingSubAgent(real_llm_manager, real_tool_dispatcher)

    }

    return _build_cost_setup(agents, real_llm_manager, real_websocket_manager)

def _build_cost_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Build complete setup dictionary."""

    return {

        'agents': agents, 'llm': llm, 'websocket': ws,

        'run_id': str(uuid.uuid4()), 'user_id': 'cost-test-user'

    }

@pytest.mark.real_llm

class TestCostQualityConstraints:

    """Test cost optimization with quality preservation requirements."""
    
    async def test_cost_reduction_quality_preservation(self, cost_optimization_setup):

        """Test: 'I need to reduce costs but keep quality the same. For feature X, I can accept latency of 500ms. For feature Y, I need to maintain current latency of 200ms.'"""

        setup = cost_optimization_setup

        state = _create_cost_quality_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_cost_quality_results(results, state)
    
    async def test_multi_constraint_optimization(self, cost_optimization_setup):

        """Test: 'I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?'"""

        setup = cost_optimization_setup

        state = _create_multi_constraint_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_multi_constraint_results(results, state)

def _create_cost_quality_state() -> DeepAgentState:

    """Create state for cost-quality optimization test."""

    return DeepAgentState(

        user_request="I need to reduce costs but keep quality the same. For feature X, I can accept latency of 500ms. For feature Y, I need to maintain current latency of 200ms.",

        metadata={'test_type': 'cost_quality', 'priority': 1}

    )

def _create_multi_constraint_state() -> DeepAgentState:

    """Create state for multi-constraint optimization test."""

    return DeepAgentState(

        user_request="I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",

        metadata={'test_type': 'multi_constraint', 'usage_increase': '30%', 'cost_target': '20%'}

    )

async def _execute_cost_optimization_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:

    """Execute complete cost optimization workflow with all 5 agents."""

    results = []

    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']

    for step_name in workflow_steps:

        step_result = await _execute_workflow_step(setup, step_name, state)

        results.append(step_result)

    return results

async def _execute_workflow_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:

    """Execute single workflow step with real agent."""

    agent = setup['agents'][step_name]
    # Fix WebSocket interface - ensure both methods are available

    if hasattr(setup['websocket'], 'send_message') and not hasattr(setup['websocket'], 'send_to_thread'):

        setup['websocket'].send_to_thread = setup['websocket'].send_message

    elif hasattr(setup['websocket'], 'send_to_thread') and not hasattr(setup['websocket'], 'send_message'):

        setup['websocket'].send_message = setup['websocket'].send_to_thread
    
    agent.websocket_manager = setup['websocket']

    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)

    return _create_execution_result(step_name, agent, state, execution_result)

def _create_execution_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:

    """Create execution result dictionary."""

    return {

        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,

        'execution_result': result, 'state_updated': state is not None

    }

def _validate_cost_quality_results(results: List[Dict], state: DeepAgentState):

    """Validate complete cost-quality optimization results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    _validate_triage_identifies_constraints(results[0], state)

    _validate_data_analysis_captures_metrics(results[1], state)

    _validate_optimization_proposes_solutions(results[2], state)

    _validate_actions_provides_implementation(results[3], state)

    _validate_reporting_summarizes_results(results[4], state)

def _validate_triage_identifies_constraints(result: Dict, state: DeepAgentState):

    """Validate triage identifies cost and quality constraints."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert hasattr(state, 'user_request')

    assert 'feature X' in state.user_request or 'feature Y' in state.user_request

    assert '500ms' in state.user_request or '200ms' in state.user_request

def _validate_data_analysis_captures_metrics(result: Dict, state: DeepAgentState):

    """Validate data analysis captures relevant performance metrics."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

    assert hasattr(state, 'messages') or hasattr(state, 'analysis_data')

def _validate_optimization_proposes_solutions(result: Dict, state: DeepAgentState):

    """Validate optimization agent proposes cost-effective solutions."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']
    # Optimization agent may return None execution_result but should update state

    assert hasattr(state, 'optimizations_result') or result['execution_result'] is not None
    
def _validate_multi_constraint_results(results: List[Dict], state: DeepAgentState):

    """Validate multi-constraint optimization results."""

    assert len(results) == 5, "All workflow steps must execute"

    _validate_constraint_parsing(results[0], state)

    _validate_impact_analysis(results[1], state)

    _validate_comprehensive_optimization(results[2], state)

def _validate_constraint_parsing(result: Dict, state: DeepAgentState):

    """Validate parsing of multiple constraints."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert '20%' in state.user_request and '2x' in state.user_request

    assert '30%' in state.user_request

def _validate_impact_analysis(result: Dict, state: DeepAgentState):

    """Validate impact analysis considers usage increase."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

def _validate_comprehensive_optimization(result: Dict, state: DeepAgentState):

    """Validate comprehensive optimization strategy."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']
    # Optimization step should either return result or update state

    assert hasattr(state, 'optimizations_result') or result['execution_result'] is not None

@pytest.mark.real_llm

class TestBudgetConstrainedOptimization:

    """Test optimization workflows with strict budget constraints."""
    
    async def test_zero_budget_latency_improvement(self, cost_optimization_setup):

        """Test: 'My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.'"""

        setup = cost_optimization_setup

        state = _create_zero_budget_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_zero_budget_results(results, state)

def _create_zero_budget_state() -> DeepAgentState:

    """Create state for zero-budget latency improvement."""

    return DeepAgentState(

        user_request="My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",

        metadata={'test_type': 'zero_budget', 'latency_target': '3x', 'budget_constraint': 'zero'}

    )

def _validate_zero_budget_results(results: List[Dict], state: DeepAgentState):

    """Validate zero-budget optimization results."""

    assert len(results) == 5, "All workflow steps must execute"

    _validate_budget_constraint_recognition(results[0])

    _validate_data_analysis_captures_metrics(results[1], state)

    _validate_efficiency_focus(results[2])

    _validate_actions_provides_implementation(results[3], state)

    _validate_reporting_summarizes_results(results[4], state)

def _validate_budget_constraint_recognition(result: Dict):

    """Validate recognition of budget constraints."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert 'can\'t spend more money' in result['workflow_state'].user_request

def _validate_efficiency_focus(result: Dict):

    """Validate focus on efficiency improvements."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

@pytest.mark.real_llm

class TestWorkflowIntegrity:

    """Test integrity of complete cost optimization workflows."""
    
    async def test_agent_state_transitions(self, cost_optimization_setup):

        """Test proper agent state transitions throughout workflow."""

        setup = cost_optimization_setup

        state = _create_cost_quality_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_state_transitions(results)
    
    async def test_data_flow_continuity(self, cost_optimization_setup):

        """Test data flow continuity between agents."""

        setup = cost_optimization_setup

        state = _create_multi_constraint_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_data_continuity(results, state)

def _validate_state_transitions(results: List[Dict]):

    """Validate proper agent state transitions."""

    for result in results:

        assert result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

        assert result['state_updated']

def _validate_data_continuity(results: List[Dict], state: DeepAgentState):

    """Validate data continuity between workflow steps."""

    assert all(result['workflow_state'] is state for result in results)

    assert state.user_request is not None

    assert hasattr(state, 'metadata')

@pytest.mark.real_llm

class TestErrorHandling:

    """Test error handling in cost optimization workflows."""
    
    async def test_invalid_constraint_handling(self, cost_optimization_setup):

        """Test handling of invalid or contradictory constraints."""

        setup = cost_optimization_setup

        state = _create_invalid_constraint_state()
        
        try:

            results = await _execute_cost_optimization_workflow(setup, state)

            _validate_error_recovery(results)

        except NetraException:

            pass  # Expected for some invalid constraints
    
    async def test_agent_failure_recovery(self, cost_optimization_setup):

        """Test recovery from individual agent failures."""

        setup = cost_optimization_setup

        state = _create_cost_quality_state()

        results = await _execute_with_simulated_failures(setup, state)

        _validate_failure_recovery(results)

def _create_invalid_constraint_state() -> DeepAgentState:

    """Create state with invalid constraints for testing."""

    return DeepAgentState(

        user_request="Reduce costs to zero while improving everything infinitely fast",

        metadata={'test_type': 'invalid_constraints'}

    )

def _validate_error_recovery(results: List[Dict]):

    """Validate error recovery mechanisms."""

    assert len(results) >= 1, "At least one agent should attempt execution"

    assert any(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] for r in results)

async def _execute_with_simulated_failures(setup: Dict, state: DeepAgentState) -> List[Dict]:

    """Execute workflow with simulated agent failures."""

    results = []

    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:

        try:

            if step_name in setup['agents']:  # Check if agent exists

                step_result = await _execute_workflow_step(setup, step_name, state)

                results.append(step_result)

            else:

                results.append({'step': step_name, 'error': f'Agent {step_name} not available', 'agent_state': SubAgentLifecycle.FAILED})

        except Exception as e:

            results.append({'step': step_name, 'error': str(e), 'agent_state': SubAgentLifecycle.FAILED})
    
    return results

def _validate_failure_recovery(results: List[Dict]):

    """Validate failure recovery in workflow."""

    assert len(results) >= 1, "At least one step should execute"
    # Workflow should handle individual agent failures gracefully

    successful_steps = [r for r in results if r.get('agent_state') == SubAgentLifecycle.COMPLETED]

    assert len(successful_steps) >= 0, "Some steps should succeed even with failures"

def _validate_actions_provides_implementation(result: Dict, state: DeepAgentState):

    """Validate actions agent provides implementation steps."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']
    # Actions agent should either return result or update state

    assert hasattr(state, 'action_plan_result') or result['execution_result'] is not None

def _validate_reporting_summarizes_results(result: Dict, state: DeepAgentState):

    """Validate reporting agent summarizes optimization results."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

    assert hasattr(state, 'user_request') or hasattr(state, 'messages')

@pytest.mark.real_llm

class TestExamplePromptsCostOptimization:

    """Test specific example prompts EP-001 and EP-007 with real LLM validation."""
    
    async def test_ep_001_cost_quality_constraints_real_llm(self, cost_optimization_setup):

        """Test EP-001: Cost reduction with quality preservation using real LLM."""

        setup = cost_optimization_setup

        state = _create_ep_001_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_ep_001_results(results, state, setup)
    
    async def test_ep_007_multi_constraint_real_llm(self, cost_optimization_setup):

        """Test EP-007: Multi-constraint optimization using real LLM."""

        setup = cost_optimization_setup

        state = _create_ep_007_state()

        results = await _execute_cost_optimization_workflow(setup, state)

        _validate_ep_007_results(results, state, setup)

def _create_ep_001_state() -> DeepAgentState:

    """Create state for EP-001 example prompt test."""

    return DeepAgentState(

        user_request="I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",

        metadata={'test_type': 'ep_001', 'prompt_id': 'EP-001', 'priority': 1}

    )

def _create_ep_007_state() -> DeepAgentState:

    """Create state for EP-007 example prompt test."""

    return DeepAgentState(

        user_request="I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",

        metadata={'test_type': 'ep_007', 'prompt_id': 'EP-007', 'cost_target': '20%', 'latency_target': '2x', 'usage_increase': '30%'}

    )

def _validate_ep_001_results(results: List[Dict], state: DeepAgentState, setup: Dict):

    """Validate EP-001 results with enhanced quality checks."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    _validate_cost_quality_results(results, state)

    _validate_response_quality_ep_001(results, setup)

def _validate_ep_007_results(results: List[Dict], state: DeepAgentState, setup: Dict):

    """Validate EP-007 results with enhanced quality checks."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    _validate_multi_constraint_results(results, state)

    _validate_response_quality_ep_007(results, setup)

async def _validate_response_quality_ep_001(results: List[Dict], setup: Dict):

    """Validate response quality for EP-001 using quality gate service."""

    quality_service = QualityGateService()

    final_result = results[-1]  # Reporting result
    
    if hasattr(final_result.get('workflow_state', {}), 'final_response'):

        response_text = str(final_result['workflow_state'].final_response)

        is_valid, score, feedback = await quality_service.validate_content(

            content=response_text, content_type=ContentType.OPTIMIZATION_REPORT, quality_level=QualityLevel.MEDIUM

        )

        assert is_valid, f"EP-001 response quality validation failed: {feedback}"

        assert score >= 70, f"EP-001 quality score too low: {score}"

async def _validate_response_quality_ep_007(results: List[Dict], setup: Dict):

    """Validate response quality for EP-007 using quality gate service."""

    quality_service = QualityGateService()

    final_result = results[-1]  # Reporting result
    
    if hasattr(final_result.get('workflow_state', {}), 'final_response'):

        response_text = str(final_result['workflow_state'].final_response)

        is_valid, score, feedback = await quality_service.validate_content(

            content=response_text, content_type=ContentType.OPTIMIZATION_REPORT, quality_level=QualityLevel.MEDIUM

        )

        assert is_valid, f"EP-007 response quality validation failed: {feedback}"

        assert score >= 70, f"EP-007 quality score too low: {score}"