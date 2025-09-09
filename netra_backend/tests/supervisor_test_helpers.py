"""
Helper functions for supervisor agent tests.
Extracts common setup, mock creation, and assertion logic to keep test functions ≤8 lines.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.execution_context import (
    AgentExecutionContext as BaseAgentExecutionContext,
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.core.interfaces_execution import ExecutionStrategy
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

def create_supervisor_mocks():
    """Create standard mocks for supervisor tests."""
    return {
        # Mock: Session isolation for controlled testing without external state
        'db_session': AsyncMock(),
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': AsyncMock(spec=LLMManager),
        # Mock: WebSocket connection isolation for testing without network overhead
        'websocket_manager': AsyncMock(),
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        'tool_dispatcher': AsyncMock(spec=ToolDispatcher)
    }

def create_supervisor_agent(mocks: Dict[str, Any]) -> SupervisorAgent:
    """Create supervisor agent with mocks."""
    return SupervisorAgent(
        mocks['db_session'],
        mocks['llm_manager'],
        mocks['websocket_manager'],
        mocks['tool_dispatcher']
    )

def create_execution_context(run_id: str, **kwargs) -> AgentExecutionContext:
    """Create execution context with defaults."""
    context_params = _build_execution_context_params(run_id, kwargs)
    return AgentExecutionContext(**context_params)

def _build_execution_context_params(run_id: str, kwargs: dict) -> dict:
    """Build execution context parameters with defaults."""
    return {
        'context_id': run_id,
        'agent_id': kwargs.get('agent_name', 'Supervisor'),
        'operation': kwargs.get('operation', 'test_operation'),
        'metadata': None,
        'timeout': kwargs.get('timeout', 30.0)
    }

def create_agent_state(user_request: str, **kwargs) -> DeepAgentState:
    """Create agent state with optional results."""
    state = DeepAgentState(user_request=user_request)
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state

def setup_triage_agent_mock(supervisor: SupervisorAgent, return_data: Dict[str, Any]):
    """Setup triage agent mock with return data."""
    triage_agent = supervisor.agents.get("triage")
    triage_result = _create_triage_result(return_data)
    mock_execute = _create_triage_execute_func(triage_result)
    triage_agent.execute = mock_execute

def setup_optimization_agent_mock(supervisor: SupervisorAgent, return_data: Dict[str, Any]):
    """Setup optimization agent mock with return data."""
    opt_agent = supervisor.agents.get("optimization")
    optimizations_result = _create_optimizations_result(return_data)
    mock_execute = _create_optimization_execute_func(optimizations_result)
    opt_agent.execute = mock_execute

def setup_data_agent_mock(supervisor: SupervisorAgent, return_data: Dict[str, Any]):
    """Setup data agent mock with return data."""
    data_agent = supervisor.agents.get("data")
    data_result = _create_data_result(return_data)
    mock_execute = _create_data_execute_func(data_result)
    data_agent.execute = mock_execute

def setup_failing_agent_mock(supervisor: SupervisorAgent, agent_name: str, error_msg: str):
    """Setup agent mock to fail with specific error."""
    agent = supervisor.agents.get(agent_name)
    # Mock: Async component isolation for testing without real async operations
    agent.execute = AsyncMock(side_effect=Exception(error_msg))

def setup_retry_agent_mock(supervisor: SupervisorAgent, agent_name: str, failures: List[str], success_data: Dict[str, Any]):
    """Setup agent mock with retry behavior."""
    agent = supervisor.agents.get(agent_name)
    side_effects = _create_retry_side_effects(failures, agent_name, success_data)
    # Mock: Async component isolation for testing without real async operations
    agent.execute = AsyncMock(side_effect=side_effects)

def assert_agent_called(supervisor: SupervisorAgent, agent_name: str):
    """Assert that specific agent was called."""
    agent = supervisor.agents.get(agent_name)
    assert agent.execute.called, f"Agent {agent_name} was not called"

def assert_agent_not_called(supervisor: SupervisorAgent, agent_name: str):
    """Assert that specific agent was not called."""
    agent = supervisor.agents.get(agent_name)
    assert not agent.execute.called, f"Agent {agent_name} should not have been called"

def assert_routing_result(result: AgentExecutionResult, expected_success: bool, **kwargs):
    """Assert routing result properties."""
    assert result.success == expected_success
    _assert_optional_error(result, kwargs)
    _assert_optional_state_attr(result, kwargs)

def setup_circuit_breaker(supervisor: SupervisorAgent, threshold: int = 3):
    """Setup circuit breaker on supervisor."""
    supervisor.circuit_breaker_enabled = True
    supervisor.circuit_breaker_threshold = threshold
    supervisor.circuit_breaker_failures = {}
    supervisor.circuit_breaker_open_time = {}
    supervisor.circuit_breaker_cooldown = 0.1  # 100ms cooldown for testing

def create_pipeline_config(agents: List[str], strategies: List[ExecutionStrategy]) -> List[tuple]:
    """Create pipeline configuration."""
    return list(zip(agents, strategies))

async def execute_pipeline(supervisor: SupervisorAgent, state: DeepAgentState, context: AgentExecutionContext, pipeline: List[tuple]):
    """Execute agent pipeline with conditional logic."""
    for agent_name, strategy in pipeline:
        should_execute = _should_execute_agent(strategy, state)
        if should_execute:
            await supervisor._route_to_agent(state, context, agent_name)

# Quality testing helpers
def create_quality_supervisor_mocks():
    """Create mocks for quality supervisor tests."""
    return {
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': AsyncMock(spec=LLMManager),
        # Mock: WebSocket connection isolation for testing without network overhead
        'websocket_manager': AsyncMock()
    }

def setup_quality_response_mock(llm_manager: AsyncMock, response_data: Dict[str, Any]):
    """Setup LLM manager mock for quality responses."""
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.ask_llm = AsyncMock()
    llm_manager.ask_llm.return_value = json.dumps(response_data)

def create_quality_response_data(quality_score: float, approved: bool, issues: List[str] = None) -> Dict[str, Any]:
    """Create quality response data structure."""
    return {
        "quality_score": quality_score,
        "approved": approved,
        "issues": issues or []
    }

# Admin tool testing helpers
def create_admin_dispatcher_mocks():
    """Create mocks for admin tool dispatcher tests."""
    return {
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': AsyncMock(spec=LLMManager),
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        'tool_dispatcher': AsyncMock(spec=ToolDispatcher)
    }

def create_admin_operation(op_type: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Create admin operation structure."""
    operation = {
        "type": op_type,
        "params": params
    }
    operation.update(kwargs)
    return operation

def setup_tool_dispatcher_mock(tool_dispatcher: AsyncMock, return_data: Dict[str, Any]):
    """Setup tool dispatcher mock with return data."""
    # Mock: Tool execution isolation for predictable agent testing
    tool_dispatcher.execute_tool = AsyncMock()
    tool_dispatcher.execute_tool.return_value = return_data

# Corpus admin testing helpers
def create_corpus_admin_mocks():
    """Create mocks for corpus admin tests."""
    return {
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': AsyncMock(spec=LLMManager),
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        'tool_dispatcher': AsyncMock(spec=ToolDispatcher),
        # Mock: Generic component isolation for controlled unit testing
        'vector_store': AsyncMock()
    }

def create_test_documents(count: int = 5) -> List[Dict[str, str]]:
    """Create test documents for indexing."""
    return [
        {"id": f"doc{i}", "content": f"Document {i} content"}
        for i in range(1, count + 1)
    ]

def setup_vector_store_mock(vector_store: AsyncMock, operation: str, return_data: Any):
    """Setup vector store mock for specific operation."""
    if operation == "add_documents":
        _setup_add_documents_mock(vector_store, return_data)
    elif operation == "similarity_search":
        _setup_similarity_search_mock(vector_store, return_data)
    elif operation == "update_document":
        _setup_update_document_mock(vector_store, return_data)

# Supply researcher testing helpers
def create_supply_researcher_mocks():
    """Create mocks for supply researcher tests."""
    return {
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': AsyncMock(spec=LLMManager),
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        'tool_dispatcher': AsyncMock(spec=ToolDispatcher),
        # Mock: Generic component isolation for controlled unit testing
        'data_sources': AsyncMock(),
        # Mock: Generic component isolation for controlled unit testing
        'enrichment_service': AsyncMock()
    }

def create_supply_data(suppliers: List[Dict[str, Any]], inventory: Dict[str, int]) -> Dict[str, Any]:
    """Create supply data structure."""
    return {
        "suppliers": suppliers,
        "inventory": inventory
    }

def create_supplier_data(supplier_id: str, name: str, reliability: float) -> Dict[str, Any]:
    """Create supplier data structure."""
    return {
        "id": supplier_id,
        "name": name,
        "reliability": reliability
    }

# Utility testing helpers
async def run_concurrent_tasks(tasks: List, max_concurrent: int = 5) -> List[Any]:
    """Run tasks concurrently with limit."""
    semaphore = asyncio.Semaphore(max_concurrent)
    run_with_semaphore = _create_semaphore_task_runner(semaphore)
    wrapped_tasks = [run_with_semaphore(task) for task in tasks]
    return await asyncio.gather(*wrapped_tasks)

def assert_call_count(mock_obj: AsyncMock, expected_count: int):
    """Assert mock was called expected number of times."""
    assert mock_obj.call_count == expected_count

def assert_contains_error(error_message: str, expected_substring: str):
    """Assert error message contains expected substring."""
    assert expected_substring in error_message

def _create_triage_result(return_data: Dict[str, Any]):
    """Create triage result from return data."""
    from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
    triage_dict = return_data.get('triage_result', {'message_type': 'query'})
    if isinstance(triage_dict, dict):
        return _build_triage_result_from_dict(TriageResult, triage_dict)
    return triage_dict

def _build_triage_result_from_dict(result_class, triage_dict: Dict[str, Any]):
    """Build TriageResult from dictionary."""
    # Import here to avoid circular imports
    from netra_backend.app.agents.triage.unified_triage_agent import SuggestedWorkflow
    
    # Determine next agent based on requirements
    next_agent = "DataSubAgent" if triage_dict.get('requires_data', False) else "OptimizationAgent"
    required_data_sources = ["metrics", "logs"] if triage_dict.get('requires_data', False) else []
    
    return result_class(
        category=triage_dict.get('message_type', 'query'),
        confidence_score=triage_dict.get('confidence', 0.8),
        suggested_workflow=SuggestedWorkflow(
            next_agent=next_agent,
            required_data_sources=required_data_sources
        )
    )

def _create_triage_execute_func(triage_result):
    """Create triage execute function."""
    async def mock_execute(state, run_id, stream_updates=True):
        state.triage_result = triage_result
        return state
    
    # Create AsyncMock with the same behavior but trackable calls
    mock = AsyncMock(side_effect=mock_execute)
    return mock

def _create_optimizations_result(return_data: Dict[str, Any]):
    """Create optimizations result from return data."""
    from netra_backend.app.agents.state import OptimizationsResult
    opt_dict = _prepare_optimizations_dict(return_data)
    return OptimizationsResult(**opt_dict)

def _prepare_optimizations_dict(return_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare optimizations dictionary with defaults."""
    opt_dict = return_data.get('optimizations_result', {
        'optimization_type': 'performance', 'recommendations': []
    })
    if 'optimization_type' not in opt_dict:
        opt_dict['optimization_type'] = 'performance'
    return opt_dict

def _create_optimization_execute_func(optimizations_result):
    """Create optimization execute function."""
    async def mock_execute(state, run_id, stream_updates=True):
        state.optimizations_result = optimizations_result
        return state
    
    # Create AsyncMock with the same behavior but trackable calls
    mock = AsyncMock(side_effect=mock_execute)
    return mock

def _create_data_result(return_data: Dict[str, Any]):
    """Create data result from return data."""
    from netra_backend.app.schemas.shared_types import AnomalyDetectionResponse
    data_dict = return_data.get('data_result', {'processed': True})
    if isinstance(data_dict, dict):
        confidence_score = _get_data_confidence_score(data_dict)
        return _create_anomaly_detection_response(data_dict, confidence_score)
    return data_dict

def _get_data_confidence_score(data_dict: Dict[str, Any]) -> float:
    """Get confidence score from data dict."""
    if 'analysis' in data_dict:
        return data_dict.get('analysis', {}).get('metrics', {}).get('accuracy', 0.95)
    elif data_dict.get('processed') is True:
        return 0.95
    return 0.8

def _create_anomaly_detection_response(data_dict: Dict[str, Any], confidence_score: float):
    """Create anomaly detection response."""
    from netra_backend.app.schemas.shared_types import AnomalyDetectionResponse
    summary = f"Analysis complete: {data_dict.get('analysis', {}).get('trends', 'processed')}"
    return AnomalyDetectionResponse(
        summary=summary,
        anomalies=[],
        confidence_score=confidence_score,
        processing_time_ms=100
    )

def _create_data_execute_func(data_result):
    """Create data execute function."""
    async def mock_execute(state, run_id, stream_updates=True):
        state.data_result = data_result
        return state
    
    # Create AsyncMock with the same behavior but trackable calls
    mock = AsyncMock(side_effect=mock_execute)
    return mock

def _create_retry_side_effects(failures: List[str], agent_name: str, success_data: Dict[str, Any]):
    """Create side effects for retry behavior."""
    side_effects = [Exception(err) for err in failures]
    success_state = _create_success_state(agent_name, success_data)
    side_effects.append(success_state)
    return side_effects

def _create_success_state(agent_name: str, success_data: Dict[str, Any]):
    """Create success state for retry mock."""
    if agent_name == "triage" and 'triage_result' in success_data:
        success_data = _process_triage_success_data(success_data)
    return DeepAgentState(**success_data)

def _process_triage_success_data(success_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process triage success data."""
    from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
    triage_dict = success_data['triage_result']
    if isinstance(triage_dict, dict):
        category = "success" if triage_dict.get('success') else triage_dict.get('message_type', 'query')
        triage_result = TriageResult(category=category)
        success_data = success_data.copy()
        success_data['triage_result'] = triage_result
    return success_data

def _assert_optional_error(result, kwargs):
    """Assert optional error in result."""
    if 'error' in kwargs:
        assert result.error == kwargs['error']

def _assert_optional_state_attr(result, kwargs):
    """Assert optional state attribute in result."""
    if 'state_attr' in kwargs and 'state_value' in kwargs:
        attr_value = getattr(result.state, kwargs['state_attr'], None)
        assert attr_value == kwargs['state_value']

def _should_execute_agent(strategy, state) -> bool:
    """Check if agent should be executed based on strategy."""
    if strategy == ExecutionStrategy.CONDITIONAL:
        return state.triage_result and state.triage_result.get("requires_data")
    return True

def _setup_add_documents_mock(vector_store: AsyncMock, return_data: Any):
    """Setup add documents mock."""
    # Mock: Generic component isolation for controlled unit testing
    vector_store.add_documents = AsyncMock()
    vector_store.add_documents.return_value = return_data

def _setup_similarity_search_mock(vector_store: AsyncMock, return_data: Any):
    """Setup similarity search mock."""
    # Mock: Generic component isolation for controlled unit testing
    vector_store.similarity_search = AsyncMock()
    vector_store.similarity_search.return_value = return_data

def _setup_update_document_mock(vector_store: AsyncMock, return_data: Any):
    """Setup update document mock."""
    # Mock: Generic component isolation for controlled unit testing
    vector_store.update_document = AsyncMock()
    vector_store.update_document.return_value = return_data

def _create_semaphore_task_runner(semaphore):
    """Create task runner with semaphore."""
    async def run_with_semaphore(task):
        async with semaphore:
            return await task
    return run_with_semaphore

def create_timestamp_data() -> Dict[str, Any]:
    """Create data with timestamp."""
    return {
        "timestamp": time.time(),
        "value": 0.5
    }