"""
E2E Test Helpers - Modular Support Functions
All helper functions broken into ≤8 line functions for architectural compliance
"""

import uuid
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from llm.llm_manager import LLMManager


def create_mock_infrastructure():
    """Create mock infrastructure for e2e testing"""
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    return db_session, llm_manager, ws_manager


def _create_optimization_responses():
    """Create responses for optimization flow"""
    return [
        {"category": "optimization", "requires_analysis": True},
        {"bottleneck": "memory", "utilization": 0.95},
        {"recommendations": ["Use gradient checkpointing", "Reduce batch size"]}
    ]


def _setup_structured_llm_responses(llm_manager, responses):
    """Setup structured LLM responses with cycling"""
    response_index = 0
    async def mock_structured_llm(*args, **kwargs):
        nonlocal response_index
        result = responses[response_index]
        response_index += 1
        return result
    llm_manager.ask_structured_llm = AsyncMock(side_effect=mock_structured_llm)


def setup_llm_responses(llm_manager):
    """Setup LLM responses for full optimization flow"""
    responses = _create_optimization_responses()
    _setup_structured_llm_responses(llm_manager, responses)
    llm_manager.call_llm = AsyncMock(return_value={"content": "Optimization complete"})


def setup_websocket_manager(ws_manager):
    """Setup websocket manager for testing"""
    ws_manager.send_message = AsyncMock()


def create_mock_persistence():
    """Create mock persistence service"""
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(side_effect=_mock_save_agent_state)
    _setup_persistence_methods(mock_persistence)
    return mock_persistence


async def _mock_save_agent_state(*args, **kwargs):
    """Handle different save_agent_state signatures"""
    if len(args) == 2:
        return (True, "test_id")
    elif len(args) == 5:
        return True
    else:
        return (True, "test_id")


def _setup_persistence_methods(mock_persistence):
    """Setup persistence service methods"""
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))


def _create_tool_dispatcher():
    """Create mock tool dispatcher"""
    from app.agents.tool_dispatcher import ToolDispatcher
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
    return dispatcher


def _setup_supervisor_ids(supervisor):
    """Setup supervisor agent IDs"""
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())


def _setup_supervisor_mocks(supervisor, mock_persistence):
    """Setup supervisor agent mocks"""
    supervisor.state_persistence = mock_persistence
    from app.agents.supervisor.execution_context import AgentExecutionResult
    supervisor.engine.execute_pipeline = AsyncMock(return_value=[
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None)
    ])


def create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence):
    """Create supervisor with all mocked dependencies"""
    dispatcher = _create_tool_dispatcher()
    supervisor = SupervisorAgent(db_session, llm_manager, ws_manager, dispatcher)
    _setup_supervisor_ids(supervisor)
    _setup_supervisor_mocks(supervisor, mock_persistence)
    return supervisor


async def execute_optimization_flow(supervisor):
    """Execute the optimization flow and return result"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )


def verify_optimization_flow(state, supervisor):
    """Verify the optimization flow completed successfully"""
    assert state is not None
    assert supervisor.engine.execute_pipeline.called


def create_multiple_supervisors(db_session, llm_manager, ws_manager, mock_persistence, count):
    """Create multiple supervisor agents for concurrent testing"""
    supervisors = []
    for i in range(count):
        supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
        supervisors.append(supervisor)
    return supervisors


def create_concurrent_tasks(supervisors):
    """Create concurrent tasks for multiple supervisors"""
    tasks = [
        supervisor.run(
            f"Request {i}",
            supervisor.thread_id,
            supervisor.user_id,
            str(uuid.uuid4())
        )
        for i, supervisor in enumerate(supervisors)
    ]
    return tasks


def verify_concurrent_results(results, expected_count):
    """Verify concurrent execution results"""
    from app.agents.state import DeepAgentState
    assert len(results) == expected_count
    for result in results:
        if not isinstance(result, Exception):
            assert isinstance(result, DeepAgentState)


def setup_mock_llm_with_retry():
    """Setup mock LLM with retry behavior"""
    llm_manager = Mock(spec=LLMManager)
    call_counter = {"count": 0}
    async def mock_llm_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            raise Exception("LLM call timed out")
        return {"content": "Successful response after retry", "tool_calls": []}
    llm_manager.call_llm = AsyncMock(side_effect=mock_llm_call)
    return llm_manager, call_counter


def create_tool_execution_mocks():
    """Create mocks for tool execution testing"""
    from app.agents.tool_dispatcher import ToolDispatcher
    dispatcher = Mock(spec=ToolDispatcher)
    tool_results = []
    
    async def mock_dispatch(tool_name, params):
        result = {
            "tool": tool_name, "params": params,
            "result": f"Executed {tool_name}", "status": "success"
        }
        tool_results.append(result)
        return result
    
    dispatcher.dispatch_tool = AsyncMock(side_effect=mock_dispatch)
    return dispatcher, tool_results


def create_llm_response_with_tools():
    """Create LLM response with tool calls"""
    return {
        "content": "I'll analyze your workload",
        "tool_calls": [
            {"name": "analyze_workload", "parameters": {"metric": "gpu_util"}},
            {"name": "optimize_batch_size", "parameters": {"current": 32}}
        ]
    }


async def execute_tool_calls(dispatcher, tool_calls):
    """Execute all tool calls from LLM response"""
    for tool_call in tool_calls:
        await dispatcher.dispatch_tool(tool_call["name"], tool_call["parameters"])


def verify_tool_execution(tool_results, expected_tools):
    """Verify tool execution results"""
    assert len(tool_results) == len(expected_tools)
    for i, expected_tool in enumerate(expected_tools):
        assert tool_results[i]["tool"] == expected_tool