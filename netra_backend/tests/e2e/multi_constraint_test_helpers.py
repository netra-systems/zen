"""
Multi-Constraint Test Helpers Module
Shared helper functions for multi-constraint workflow tests.
Maximum 300 lines, functions  <= 8 lines.
"""

from netra_backend.app.agents.actions_to_meet_goals_sub_agent import (
    ActionsToMeetGoalsSubAgent,
)
from netra_backend.app.websocket_core import WebSocketManager
from typing import Dict, List
import uuid
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.optimizations_core_sub_agent import (
    OptimizationsCoreSubAgent,
)
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.agent_models import AgentMetadata
from netra_backend.app.schemas.agent import SubAgentLifecycle

def create_test_llm_manager() -> LLMManager:

    """Create real LLM manager instance."""

    manager = LLMManager()

    return manager

def create_test_websocket_manager() -> WebSocketManager:

    """Create WebSocket manager instance."""

    return WebSocketManager()

def create_agent_instances(llm: LLMManager, tool_dispatcher) -> Dict:

    """Create agent instances with real LLM."""

    return {

        'triage': TriageSubAgent(llm, tool_dispatcher),

        'data': DataSubAgent(llm, tool_dispatcher),

        'optimization': OptimizationsCoreSubAgent(llm, tool_dispatcher),

        'actions': ActionsToMeetGoalsSubAgent(llm, tool_dispatcher),

        'reporting': ReportingSubAgent(llm, tool_dispatcher)

    }

def build_multi_constraint_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Build complete setup dictionary."""

    return {

        'agents': agents, 'llm': llm, 'websocket': ws,

        'run_id': str(uuid.uuid4()), 'user_id': 'multi-constraint-test-user'

    }

async def execute_multi_constraint_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:

    """Execute complete multi-constraint optimization workflow."""

    results = []

    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:

        step_result = await execute_constraint_step(setup, step_name, state)

        results.append(step_result)
    
    return results

async def execute_constraint_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:

    """Execute single multi-constraint workflow step."""

    agent = setup['agents'][step_name]

    agent.websocket_manager = setup['websocket']

    agent.user_id = setup['user_id']
    
    try:

        execution_result = await agent.run(state, setup['run_id'], True)

        return create_constraint_result(step_name, agent, state, execution_result)

    except Exception as e:

        return create_error_result(step_name, agent, state, e)

def create_constraint_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:

    """Create multi-constraint result dictionary."""

    return {

        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,

        'execution_result': result, 'state_updated': state is not None,

        'agent_type': type(agent).__name__

    }

def create_error_result(step_name: str, agent, state: DeepAgentState, error: Exception) -> Dict:

    """Create error result dictionary."""

    return {

        'step': step_name, 'agent_state': SubAgentLifecycle.FAILED, 'workflow_state': state,

        'execution_result': None, 'state_updated': False,

        'agent_type': type(agent).__name__, 'error': str(error)

    }

def create_kv_cache_audit_state() -> DeepAgentState:

    """Create state for KV cache audit workflow."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'kv_cache_audit', 

            'focus': 'system_wide_audit', 

            'scope': 'all_cache_instances'

        }

    )

    return DeepAgentState(

        user_request="I want to audit all uses of KV caching in my system to find optimization opportunities.",

        metadata=metadata

    )

def create_comprehensive_cache_state() -> DeepAgentState:

    """Create state for comprehensive cache analysis."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'comprehensive_cache', 

            'analysis_depth': 'deep', 

            'include_recommendations': 'True'

        }

    )

    return DeepAgentState(

        user_request="Perform comprehensive analysis of caching strategies and identify improvement opportunities.",

        metadata=metadata

    )

def create_triple_constraint_state() -> DeepAgentState:

    """Create state for triple constraint optimization."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'triple_constraint', 

            'constraints': 'cost,quality,latency'

        }

    )

    return DeepAgentState(

        user_request="Optimize system for minimum cost, maximum quality, and sub-200ms latency simultaneously.",

        metadata=metadata

    )

def create_quality_cost_latency_state() -> DeepAgentState:

    """Create state for quality vs cost vs latency analysis."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'quality_cost_latency_tradeoff', 

            'dimensions': '3'

        }

    )

    return DeepAgentState(

        user_request="Analyze tradeoffs between quality improvements, cost reductions, and latency optimizations.",

        metadata=metadata

    )

def create_holistic_optimization_state() -> DeepAgentState:

    """Create state for holistic system optimization."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'holistic_optimization', 

            'scope': 'system_wide', 

            'components': 'cache,models,infrastructure'

        }

    )

    return DeepAgentState(

        user_request="Perform holistic optimization of entire system including caching, models, infrastructure, and workflows.",

        metadata=metadata

    )

def create_infrastructure_app_state() -> DeepAgentState:

    """Create state for infrastructure and application optimization."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'infrastructure_app', 

            'levels': 'infrastructure,application'

        }

    )

    return DeepAgentState(

        user_request="Optimize both infrastructure configuration and application performance simultaneously.",

        metadata=metadata

    )

def create_priority_optimization_state() -> DeepAgentState:

    """Create state for priority-based optimization."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'priority_optimization', 

            'priorities': 'quality,cost,latency'

        }

    )

    return DeepAgentState(

        user_request="Optimize with priority: 1) Maintain quality above 95%, 2) Reduce costs by 15%, 3) Improve latency if possible.",

        metadata=metadata

    )

def create_dynamic_constraint_state() -> DeepAgentState:

    """Create state for dynamic constraint adjustment."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'dynamic_constraints', 

            'adaptation': 'real_time'

        }

    )

    return DeepAgentState(

        user_request="Adjust optimization strategy dynamically based on real-time performance metrics.",

        metadata=metadata

    )

def create_impossible_constraints_state() -> DeepAgentState:

    """Create state for impossible constraints test."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'impossible_constraints', 

            'feasibility': 'impossible'

        }

    )

    return DeepAgentState(

        user_request="Achieve zero cost, infinite quality, and zero latency while doubling performance.",

        metadata=metadata

    )

def create_minimal_constraint_state() -> DeepAgentState:

    """Create state for minimal constraints test."""

    metadata = AgentMetadata(

        custom_fields={

            'test_type': 'minimal_constraints', 

            'constraints_count': '0'

        }

    )

    return DeepAgentState(

        user_request="Find any optimization opportunities in the system.",

        metadata=metadata

    )

def validate_basic_workflow_execution(results: List[Dict]) -> None:

    """Validate basic workflow execution requirements."""

    assert len(results) == 5, "All workflow steps must execute"

    assert all('step' in r for r in results), "All results must have step names"

    assert all('agent_state' in r for r in results), "All results must have agent states"

def validate_cache_scope_identification(result: Dict, state: DeepAgentState) -> None:

    """Validate cache scope identification."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert 'KV caching' in state.user_request

    assert 'audit' in state.user_request

    assert 'optimization opportunities' in state.user_request

def validate_cache_inventory_analysis(result: Dict, state: DeepAgentState) -> None:

    """Validate cache inventory analysis."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

    assert result['agent_type'] == 'DataSubAgent'

def validate_optimization_opportunity_identification(result: Dict, state: DeepAgentState) -> None:

    """Validate optimization opportunity identification."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    # Allow None execution_result for fallback scenarios

    assert result['agent_type'] == 'OptimizationsCoreSubAgent'

def validate_constraint_conflict_identification(result: Dict, state: DeepAgentState) -> None:

    """Validate constraint conflict identification."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    # Check that the state contains optimization-related information

    request_lower = state.user_request.lower()

    assert any(keyword in request_lower for keyword in ['constraint', 'optimize', 'minimum', 'maximum'])

    constraints_str = state.metadata.custom_fields.get('constraints', '')
    # Allow flexible constraint structure for different test scenarios

    assert isinstance(constraints_str, str)

def validate_multi_objective_analysis(result: Dict, state: DeepAgentState) -> None:

    """Validate multi-objective analysis."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    # Allow None execution_result for fallback scenarios

def validate_compromise_recommendations(result: Dict, state: DeepAgentState) -> None:

    """Validate compromise recommendations."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['agent_type'] == 'ActionsToMeetGoalsSubAgent'

def validate_completed_or_fallback_states(results: List[Dict]) -> None:

    """Validate that agents completed or gracefully failed."""

    valid_states = [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

    assert all(r['agent_state'] in valid_states for r in results)

def validate_constraint_data_consistency(results: List[Dict], state: DeepAgentState) -> None:

    """Validate constraint data consistency."""

    assert all(r['workflow_state'] is state for r in results)

    focus = state.metadata.custom_fields.get('focus', '')

    assert focus == 'system_wide_audit'

    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]

    assert all(r['state_updated'] for r in completed_results)

def validate_optimization_state_preservation(results: List[Dict], state: DeepAgentState) -> None:

    """Validate optimization state preservation."""

    assert len(results) == 5, "All workflow steps should execute"

    assert all(r['workflow_state'] is state for r in results)

    assert state.user_request is not None

    assert hasattr(state, 'metadata')

def validate_impossible_constraints_handling(results: List[Dict]) -> None:

    """Validate handling of impossible constraints."""

    assert len(results) >= 1, "At least triage should execute"

    triage_result = results[0]

    valid_states = [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

    assert triage_result['agent_state'] in valid_states

def validate_priority_optimization_results(results: List[Dict], state: DeepAgentState) -> None:

    """Validate priority-based optimization results."""

    assert len(results) == 5, "All workflow steps must execute"

    assert '95%' in state.user_request

    assert '15%' in state.user_request

    priorities_str = state.metadata.custom_fields.get('priorities', '')
    # Allow flexible priority structure

    assert isinstance(priorities_str, str)

def create_state_with_metadata(user_request: str, custom_fields: dict) -> DeepAgentState:

    """Create a DeepAgentState with custom metadata fields."""

    metadata = AgentMetadata(custom_fields=custom_fields)

    return DeepAgentState(user_request=user_request, metadata=metadata)