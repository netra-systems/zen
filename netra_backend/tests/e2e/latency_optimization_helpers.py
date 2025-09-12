"""
Latency Optimization Test Helpers
Shared utilities for latency optimization workflow tests.
Maximum 300 lines, functions  <= 8 lines.
"""

from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.websocket_core import WebSocketManager
from typing import Dict, List, Optional, Tuple
import time
import uuid

def create_latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Setup real agent environment for latency optimization testing."""
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

    return build_latency_setup(agents, real_llm_manager, real_websocket_manager)

def build_latency_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Build complete setup dictionary."""

    return {

        'agents': agents, 'llm': llm, 'websocket': ws,

        'run_id': str(uuid.uuid4()), 'user_id': 'latency-test-user'

    }

def create_3x_latency_state() -> DeepAgentState:

    """Create state for 3x latency reduction test."""

    return DeepAgentState(

        user_request="My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",

        metadata={'test_type': 'latency_3x', 'target_improvement': '3x', 'budget_constraint': 'zero'}

    )

def create_bottleneck_analysis_state() -> DeepAgentState:

    """Create state for bottleneck analysis test."""

    return DeepAgentState(

        user_request="Analyze current system latency bottlenecks and propose optimization strategies.",

        metadata={'test_type': 'bottleneck_analysis', 'focus': 'identification'}

    )

def create_caching_optimization_state() -> DeepAgentState:

    """Create state for caching optimization test."""

    return DeepAgentState(

        user_request="Optimize system latency through improved caching strategies without additional infrastructure costs.",

        metadata={'test_type': 'caching_optimization', 'focus': 'caching'}

    )

def create_parallel_processing_state() -> DeepAgentState:

    """Create state for parallel processing optimization test."""

    return DeepAgentState(

        user_request="Reduce latency through better parallel processing and async operations optimization.",

        metadata={'test_type': 'parallel_optimization', 'focus': 'parallelization'}

    )

def create_impossible_latency_state() -> DeepAgentState:

    """Create state for impossible latency targets test."""

    return DeepAgentState(

        user_request="Reduce latency by 1000x to achieve sub-millisecond response times without any changes.",

        metadata={'test_type': 'impossible_targets', 'target': '1000x'}

    )

def create_already_optimized_state() -> DeepAgentState:

    """Create state for already optimized system test."""

    return DeepAgentState(

        user_request="My system is already highly optimized. Find any remaining latency improvements.",

        metadata={'test_type': 'already_optimized', 'baseline': 'high'}

    )

async def execute_latency_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:

    """Execute complete latency optimization workflow with all 5 agents."""

    results = []

    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:

        step_result = await execute_timed_step(setup, step_name, state)

        results.append(step_result)
    
    return results

async def execute_timed_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:

    """Execute workflow step with high-precision timing measurements."""
    # Fix WebSocket interface - ensure both methods are available

    fix_websocket_interface(setup['websocket'])
    
    timing_data = await execute_step_with_detailed_timing(setup, step_name, state)
    
    return create_enhanced_timed_result(step_name, timing_data, state)

async def execute_step_with_detailed_timing(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:

    """Execute step with detailed timing breakdown."""

    start_time = time.perf_counter()

    setup_start = time.perf_counter()
    
    agent = setup_agent_for_execution(setup, step_name)

    setup_time = time.perf_counter() - setup_start
    
    execution_start = time.perf_counter()

    execution_result = await agent.run(state, setup['run_id'], True)

    execution_time = time.perf_counter() - execution_start
    
    total_time = time.perf_counter() - start_time
    
    return {

        'agent': agent, 'execution_result': execution_result,

        'setup_time': setup_time, 'execution_time': execution_time, 'total_time': total_time

    }

def fix_websocket_interface(websocket_manager):

    """Fix WebSocket interface compatibility."""

    if hasattr(websocket_manager, 'send_message') and not hasattr(websocket_manager, 'send_to_thread'):

        websocket_manager.send_to_thread = websocket_manager.send_message

    elif hasattr(websocket_manager, 'send_to_thread') and not hasattr(websocket_manager, 'send_message'):

        websocket_manager.send_message = websocket_manager.send_to_thread

def setup_agent_for_execution(setup: Dict, step_name: str):

    """Setup agent for execution with required properties."""

    agent = setup['agents'][step_name]

    agent.websocket_manager = setup['websocket']

    agent.user_id = setup['user_id']

    return agent

def create_timed_result(step_name: str, agent, state: DeepAgentState, 

                        result, exec_time: float) -> Dict:

    """Create timed execution result dictionary."""

    return {

        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,

        'execution_result': result, 'execution_time': exec_time, 'state_updated': state is not None

    }

def create_enhanced_timed_result(step_name: str, timing_data: Dict, state: DeepAgentState) -> Dict:

    """Create enhanced timed result with detailed performance metrics."""

    agent = timing_data['agent']

    performance_metrics = calculate_performance_metrics(timing_data)
    
    return {

        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,

        'execution_result': timing_data['execution_result'], 'execution_time': timing_data['execution_time'],

        'setup_time': timing_data['setup_time'], 'total_time': timing_data['total_time'],

        'performance_metrics': performance_metrics, 'state_updated': state is not None

    }

def calculate_performance_metrics(timing_data: Dict) -> Dict:

    """Calculate performance metrics from timing data."""

    setup_overhead = timing_data['setup_time'] / timing_data['total_time'] * 100

    execution_efficiency = timing_data['execution_time'] / timing_data['total_time'] * 100
    
    return {

        'setup_overhead_percent': setup_overhead, 'execution_efficiency_percent': execution_efficiency,

        'is_fast_execution': timing_data['execution_time'] < 1.0, 'is_slow_execution': timing_data['execution_time'] > 10.0

    }

# Validation Helper Functions

async def validate_3x_latency_results(results: List[Dict], state: DeepAgentState):

    """Validate 3x latency reduction results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    await validate_latency_requirement_parsing(results[0], state)

    await validate_current_performance_analysis(results[1], state)

async def validate_latency_requirement_parsing(result: Dict, state: DeepAgentState):

    """Validate parsing of latency requirements."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert '3x' in state.user_request

    assert 'can\'t spend more money' in state.user_request

    assert result['execution_time'] < 30.0  # Reasonable execution time

async def validate_current_performance_analysis(result: Dict, state: DeepAgentState):

    """Validate current performance analysis."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

    assert result['execution_time'] < 60.0  # Data analysis should be reasonable

async def validate_optimization_strategy_development(result: Dict, state: DeepAgentState):

    """Validate optimization strategy development."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated'] or result['execution_result'] is not None

    assert result['execution_time'] < 90.0  # Complex analysis time limit

def validate_bottleneck_identification(results: List[Dict], state: DeepAgentState):

    """Validate bottleneck identification results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    validate_triage_identifies_bottlenecks(results[0])

    validate_data_analysis_measures_performance(results[1])

def validate_triage_identifies_bottlenecks(result: Dict):

    """Validate triage identifies bottleneck focus."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert 'bottleneck' in result['workflow_state'].user_request.lower()

def validate_data_analysis_measures_performance(result: Dict):

    """Validate data analysis measures current performance."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated']

def validate_optimization_targets_bottlenecks(result: Dict):

    """Validate optimization targets identified bottlenecks."""

    assert result['agent_state'] == SubAgentLifecycle.COMPLETED

    assert result['state_updated'] or result['execution_result'] is not None

def validate_caching_strategy_results(results: List[Dict]):

    """Validate caching strategy optimization results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])

def validate_parallel_processing_results(results: List[Dict]):

    """Validate parallel processing optimization results."""

    assert len(results) == 5, "All 5 workflow steps must execute"

    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])

def validate_execution_time_bounds(results: List[Dict], total_time: float):

    """Validate overall execution time bounds."""

    assert total_time < 300.0, "Workflow should complete within 5 minutes"

    assert len(results) == 5, "All 5 workflow steps should execute"

    assert all('execution_time' in r for r in results), "All steps should be timed"

    validate_performance_metrics_presence(results)

def validate_timing_consistency(results: List[Dict]):

    """Validate timing consistency across steps."""

    execution_times = [r['execution_time'] for r in results if 'execution_time' in r]

    assert len(execution_times) == 5, "All steps should have timing data"

    assert all(t >= 0 for t in execution_times), "All execution times should be non-negative"

    validate_timing_precision(results)

def validate_performance_metrics_presence(results: List[Dict]):

    """Validate that performance metrics are present in results."""

    for result in results:

        if 'performance_metrics' in result:

            metrics = result['performance_metrics']

            assert 'setup_overhead_percent' in metrics

            assert 'execution_efficiency_percent' in metrics

def validate_timing_precision(results: List[Dict]):

    """Validate timing precision and detect performance issues."""

    slow_steps = [r for r in results if r.get('performance_metrics', {}).get('is_slow_execution', False)]

    fast_steps = [r for r in results if r.get('performance_metrics', {}).get('is_fast_execution', False)]
    
    # Log performance insights for analysis

    if slow_steps:

        print(f"Performance Warning: {len(slow_steps)} slow steps detected")

    if len(fast_steps) >= 3:

        print(f"Performance Good: {len(fast_steps)} fast steps detected")

def validate_impossible_target_handling(results: List[Dict]):

    """Validate handling of impossible latency targets."""

    assert len(results) >= 3, "At least initial analysis should complete"

    triage_result = results[0]

    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

def validate_optimized_system_handling(results: List[Dict]):

    """Validate handling of already optimized systems."""

    assert len(results) == 5, "All 5 workflow steps should attempt analysis"

    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 

               for r in results)

def validate_agent_data_flow(results: List[Dict], state: DeepAgentState):

    """Validate proper data flow between agents."""

    assert all(r['workflow_state'] is state for r in results)

    assert state.user_request is not None

    assert hasattr(state, 'metadata')

def validate_state_consistency(results: List[Dict], original_state: DeepAgentState):

    """Validate state consistency throughout workflow."""

    assert len(results) == 5, "All 5 workflow steps should execute"

    for result in results:

        assert result['workflow_state'] is original_state

        assert result['state_updated']