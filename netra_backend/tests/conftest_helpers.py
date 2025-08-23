"""Helper functions for conftest.py fixtures to maintain 25-line function limit."""

from unittest.mock import AsyncMock, MagicMock

def _setup_basic_llm_mocks(mock_manager):
    """Setup basic LLM mock methods."""
    mock_manager.get_response = AsyncMock(return_value="Mock LLM response")
    mock_manager.get_structured_response = AsyncMock(return_value={"analysis": "mock analysis", "recommendations": []})
    mock_manager.generate = AsyncMock(return_value="Mock generated content")
    mock_manager.stream_response = AsyncMock()
    mock_manager.generate_response = AsyncMock(return_value={
        "content": "This is a sample AI response for testing",
        "model": "gpt-3.5-turbo",
        "tokens_used": 45,
        "cost": 0.0012
    })

def _setup_performance_llm_mocks(mock_manager):
    """Setup performance-specific LLM mock methods."""
    mock_manager.generate_structured = AsyncMock(return_value={"optimizations": ["cache optimization", "parallel processing"], "confidence": 0.85})
    mock_manager.analyze_performance = AsyncMock(return_value={"latency_ms": 250, "throughput": 1000, "bottlenecks": ["database", "api calls"]})

def _setup_websocket_interface_compatibility(manager):
    """Setup WebSocket interface compatibility."""
    if not hasattr(manager, 'send_message'):
        manager.send_message = manager.send_message_to_user

def _setup_websocket_test_mocks(manager):
    """Setup WebSocket test mocks to prevent actual operations."""
    manager.send_message = AsyncMock(return_value=True)
    manager.send_to_thread = AsyncMock(return_value=True)
    manager.send_message_to_user = AsyncMock(return_value=True)

def _create_real_tool_dispatcher():
    """Create real tool dispatcher instance."""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    return ToolDispatcher()

def _create_mock_tool_dispatcher():
    """Create mock tool dispatcher."""
    mock_dispatcher = MagicMock()
    _setup_tool_dispatcher_mocks(mock_dispatcher)
    return mock_dispatcher

def _setup_tool_dispatcher_mocks(mock_dispatcher):
    """Setup tool dispatcher mock methods."""
    mock_dispatcher.execute = AsyncMock(return_value={"result": "mock tool execution", "success": True})
    mock_dispatcher.dispatch_tool = AsyncMock(return_value={"output": "mock output"})
    mock_dispatcher.get_available_tools = MagicMock(return_value=[])

def _import_agent_classes():
    """Import agent classes for instantiation."""
    base_imports = _import_base_agent_classes()
    additional_imports = _import_additional_agent_classes()
    return {**base_imports, **additional_imports}

def _import_base_agent_classes():
    """Import base agent classes."""
    from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
    from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
    return {'triage': TriageSubAgent, 'data': DataSubAgent}

def _import_additional_agent_classes():
    """Import additional agent classes."""
    from netra_backend.app.agents.optimizations_core_sub_agent import (
        OptimizationsCoreSubAgent,
    )
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    return {'optimization': OptimizationsCoreSubAgent, 'reporting': ReportingSubAgent}

def _instantiate_agents(agent_classes, llm_manager, tool_dispatcher):
    """Instantiate agents with dependencies."""
    return {
        name: agent_class(llm_manager, tool_dispatcher)
        for name, agent_class in agent_classes.items()
    }