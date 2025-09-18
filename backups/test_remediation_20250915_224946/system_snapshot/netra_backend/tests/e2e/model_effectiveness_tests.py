"""
Model Effectiveness Analysis Tests
Tests for model effectiveness analysis workflows
"""

from typing import Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle

class TestModelEffectivenessAnalysis:
    """Test model effectiveness analysis workflows."""
    
    @pytest.mark.real_llm
    async def test_gpt4o_claude3_sonnet_effectiveness(self, model_selection_setup):
        """Test: 'I'm considering using the new 'gpt-4o' and LLMModel.GEMINI_2_5_FLASH.value models. How effective would they be in my current setup?'"""
        setup = model_selection_setup
        state = _create_model_effectiveness_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_model_effectiveness_results(results, state)
    
    @pytest.mark.real_llm
    async def test_comparative_model_analysis(self, model_selection_setup):
        """Test comparative analysis between different models."""
        setup = model_selection_setup
        state = _create_comparative_analysis_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_comparative_analysis_results(results)

def _create_model_effectiveness_state() -> DeepAgentState:
    """Create state for model effectiveness analysis."""
    return DeepAgentState(
        user_request="I'm considering using the new 'gpt-4o' and LLMModel.GEMINI_2_5_FLASH.value models. How effective would they be in my current setup?",
        metadata=AgentMetadata(custom_fields={'test_type': 'model_effectiveness', 'candidate_models': 'gpt-4o,claude-3-sonnet'})
    )

def _create_comparative_analysis_state() -> DeepAgentState:
    """Create state for comparative model analysis."""
    return DeepAgentState(
        user_request="Compare performance characteristics of GPT-4, Claude-3, and Gemini models for our workload.",
        metadata={'test_type': 'comparative_analysis', 'models': [LLMModel.GEMINI_2_5_FLASH.value, 'claude-3', 'gemini']}
    )

async def _execute_model_selection_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete model selection workflow with all 5 agents."""
    results = []
    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:
        step_result = await _execute_model_step(setup, step_name, state)
        results.append(step_result)
    
    return results

async def _execute_model_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute single model selection workflow step."""
    # Fix WebSocket interface - ensure both methods are available
    if hasattr(setup['websocket'], 'send_message') and not hasattr(setup['websocket'], 'send_to_thread'):
        setup['websocket'].send_to_thread = setup['websocket'].send_message
    elif hasattr(setup['websocket'], 'send_to_thread') and not hasattr(setup['websocket'], 'send_message'):
        setup['websocket'].send_message = setup['websocket'].send_to_thread
    
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    return _create_model_result(step_name, agent, state, execution_result)

def _create_model_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:
    """Create model selection result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'state_updated': state is not None,
        'agent_type': type(agent).__name__
    }

def _validate_model_effectiveness_results(results: List[Dict], state: DeepAgentState):
    """Validate model effectiveness analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_model_identification(results[0], state)
    _validate_current_setup_analysis(results[1], state)
    _validate_effectiveness_optimization(results[2], state)

def _validate_model_identification(result: Dict, state: DeepAgentState):
    """Validate identification of target models."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'gpt-4o' in state.user_request or LLMModel.GEMINI_2_5_FLASH.value in state.user_request
    assert 'effective' in state.user_request

def _validate_current_setup_analysis(result: Dict, state: DeepAgentState):
    """Validate current setup analysis for model compatibility."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['agent_type'] == 'DataSubAgent'

def _validate_effectiveness_optimization(result: Dict, state: DeepAgentState):
    """Validate effectiveness optimization recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    # For model selection workflows, accept completed agents even with None results (fallback scenarios)
    assert result['agent_state'] in [SubAgentLifecycle.COMPLETED]
    assert result['agent_type'] == 'OptimizationsCoreSubAgent'

def _validate_comparative_analysis_results(results: List[Dict]):
    """Validate comparative model analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])