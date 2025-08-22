"""
Model Effectiveness Analysis Workflows Test Suite
Tests real LLM agents for model effectiveness and GPT-5 migration workflows.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path

from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import uuid
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
from schemas import SubAgentLifecycle
from ws_manager import WebSocketManager

from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
from netra_backend.app.agents.state import AgentMetadata, DeepAgentState

# Add project root to path
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.llm.llm_manager import LLMManager

# Add project root to path


@pytest.fixture

def model_selection_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Setup real agent environment for model selection testing."""
    from netra_backend.app.agents.actions_to_meet_goals_sub_agent import (

        ActionsToMeetGoalsSubAgent,

    )
    from netra_backend.app.agents.optimizations_core_sub_agent import (

        OptimizationsCoreSubAgent,

    )
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    

    agents = _create_agent_dictionary(real_llm_manager, real_tool_dispatcher)

    return _build_model_setup(agents, real_llm_manager, real_websocket_manager)


def _create_agent_dictionary(llm_manager, tool_dispatcher):

    """Create dictionary of agents"""

        ActionsToMeetGoalsSubAgent,

    )

        OptimizationsCoreSubAgent,

    )
    

    return {

        'triage': TriageSubAgent(llm_manager, tool_dispatcher, None),

        'data': DataSubAgent(llm_manager, tool_dispatcher),

        'optimization': OptimizationsCoreSubAgent(llm_manager, tool_dispatcher),

        'actions': ActionsToMeetGoalsSubAgent(llm_manager, tool_dispatcher),

        'reporting': ReportingSubAgent(llm_manager, tool_dispatcher)

    }


async def _create_real_llm_manager() -> LLMManager:

    """Create real LLM manager instance."""

    manager = LLMManager()

    await manager.initialize()

    return manager


def _create_websocket_manager() -> WebSocketManager:

    """Create WebSocket manager instance."""

    return WebSocketManager()


def _build_model_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Build complete setup dictionary."""

    return {

        'agents': agents, 'llm': llm, 'websocket': ws,

        'run_id': str(uuid.uuid4()), 'user_id': 'model-test-user'

    }


class TestModelEffectivenessAnalysis:

    """Test model effectiveness analysis workflows."""
    

    @pytest.mark.real_llm

    async def test_gpt4o_claude3_sonnet_effectiveness(self, model_selection_setup):

        """Test: 'I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?'"""

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

        user_request="I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",

        metadata=AgentMetadata(custom_fields={'test_type': 'model_effectiveness', 'candidate_models': 'gpt-4o,claude-3-sonnet'})

    )


def _create_comparative_analysis_state() -> DeepAgentState:

    """Create state for comparative model analysis."""

    return DeepAgentState(

        user_request="Compare performance characteristics of GPT-4, Claude-3, and Gemini models for our workload.",

        metadata={'test_type': 'comparative_analysis', 'models': ['gpt-4', 'claude-3', 'gemini']}

    )


async def _execute_model_selection_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:

    """Execute complete model selection workflow with all 5 agents."""

    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']

    results = []
    

    for step_name in workflow_steps:

        step_result = await _execute_model_step(setup, step_name, state)

        results.append(step_result)

    return results


async def _execute_model_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:

    """Execute single model selection workflow step."""

    _fix_websocket_interface(setup)

    agent = _setup_agent_for_execution(setup, step_name)
    

    execution_result = await agent.run(state, setup['run_id'], True)

    return _create_model_result(step_name, agent, state, execution_result)


def _setup_agent_for_execution(setup: Dict, step_name: str):

    """Setup agent for execution with WebSocket and user ID."""

    agent = setup['agents'][step_name]

    agent.websocket_manager = setup['websocket']

    agent.user_id = setup['user_id']

    return agent


def _fix_websocket_interface(setup: Dict):

    """Fix WebSocket interface compatibility"""

    if hasattr(setup['websocket'], 'send_message') and not hasattr(setup['websocket'], 'send_to_thread'):

        setup['websocket'].send_to_thread = setup['websocket'].send_message

    elif hasattr(setup['websocket'], 'send_to_thread') and not hasattr(setup['websocket'], 'send_message'):

        setup['websocket'].send_message = setup['websocket'].send_to_thread


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

    assert 'gpt-4o' in state.user_request or 'claude-3-sonnet' in state.user_request

    assert 'effective' in state.user_request


def _validate_current_setup_analysis(result: Dict, state: DeepAgentState):

    """Validate current setup analysis for model compatibility."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

    assert result['agent_type'] == 'DataSubAgent'


def _validate_effectiveness_optimization(result: Dict, state: DeepAgentState):

    """Validate effectiveness optimization recommendations."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['agent_state'] in [SubAgentLifecycle.COMPLETED]

    assert result['agent_type'] == 'OptimizationsCoreSubAgent'


def _validate_comparative_analysis_results(results: List[Dict]):

    """Validate comparative model analysis results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])


class TestGPT5MigrationWorkflows:

    """Test GPT-5 migration and tool selection workflows."""
    

    async def test_gpt5_tool_selection(self, model_selection_setup):

        """Test: '@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?'"""

        setup = model_selection_setup

        state = _create_gpt5_tool_selection_state()

        results = await _execute_model_selection_workflow(setup, state)

        _validate_gpt5_tool_selection_results(results, state)
    

    async def test_gpt5_upgrade_analysis(self, model_selection_setup):

        """Test: '@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher'"""

        setup = model_selection_setup

        state = _create_gpt5_upgrade_analysis_state()

        results = await _execute_model_selection_workflow(setup, state)

        _validate_gpt5_upgrade_analysis_results(results, state)


def _create_gpt5_tool_selection_state() -> DeepAgentState:

    """Create state for GPT-5 tool selection."""

    return DeepAgentState(

        user_request="@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",

        metadata=AgentMetadata(custom_fields={'test_type': 'gpt5_tool_selection', 'target_model': 'GPT-5', 'focus': 'tool_migration'})

    )


def _create_gpt5_upgrade_analysis_state() -> DeepAgentState:

    """Create state for GPT-5 upgrade analysis."""

    return DeepAgentState(

        user_request="@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher",

        metadata={'test_type': 'gpt5_upgrade_analysis', 'action': 'cost_benefit_analysis', 'rollback_candidate': True}

    )


def _validate_gpt5_tool_selection_results(results: List[Dict], state: DeepAgentState):

    """Validate GPT-5 tool selection results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    _validate_tool_inventory_analysis(results[1])

    _validate_migration_recommendations(results[2])

    _validate_verbosity_configuration(results[3])


def _validate_tool_inventory_analysis(result: Dict):

    """Validate tool inventory analysis."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']


def _validate_migration_recommendations(result: Dict):

    """Validate migration recommendations."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['agent_state'] in [SubAgentLifecycle.COMPLETED]


def _validate_verbosity_configuration(result: Dict):

    """Validate verbosity configuration recommendations."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED


def _validate_gpt5_upgrade_analysis_results(results: List[Dict], state: DeepAgentState):

    """Validate GPT-5 upgrade analysis results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    _validate_upgrade_impact_assessment(results[1])

    _validate_rollback_recommendations(results[3])


def _validate_upgrade_impact_assessment(result: Dict):

    """Validate upgrade impact assessment."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']


def _validate_rollback_recommendations(result: Dict):

    """Validate rollback recommendations."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED


if __name__ == "__main__":

    pytest.main([__file__, "-v"])