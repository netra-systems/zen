from unittest.mock import Mock, patch, MagicMock, AsyncMock
"""Helper functions for conftest.py fixtures to maintain 25-line function limit."""

import os
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import get_env


env = get_env()
def _setup_basic_llm_mocks(mock_manager):
    """Setup basic LLM mock methods."""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_manager.get_response = AsyncMock(return_value = "Mock LLM response")
    # Mock: Async component isolation for testing without real async operations
    mock_manager.get_structured_response = AsyncMock(return_value = {"analysis": "mock analysis", "recommendations": []})
    # Mock: Async component isolation for testing without real async operations
    mock_manager.generate = AsyncMock(return_value = "Mock generated content")
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.stream_response = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    mock_manager.generate_response = AsyncMock(return_value = {
        "content": "This is a sample AI response for testing",
        "model": LLMModel.GEMINI_2_5_FLASH.value,
        "tokens_used": 45,
        "cost": 0.0012,
})

def _setup_performance_llm_mocks(mock_manager):
    """Setup performance-specific LLM mock methods."""
    # Mock: Async component isolation for testing without real async operations
    mock_manager.generate_structured = AsyncMock(return_value = {"optimizations": ["cache optimization", "parallel processing"], "confidence": 0.85})
    # Mock: Database isolation for unit testing without external database connections
    mock_manager.analyze_performance = AsyncMock(return_value = {"latency_ms": 250, "throughput": 1000, "bottlenecks": ["database", "api calls"]})

def _setup_websocket_interface_compatibility(manager):
    """Setup WebSocket interface compatibility."""
    if not hasattr(manager, 'send_message'):
        manager.send_message == manager.send_message_to_user

def _setup_websocket_test_mocks(manager):
    """Setup WebSocket test mocks to prevent actual operations."""
    # Mock: Async component isolation for testing without real async operations
    manager.send_message = AsyncMock(return_value = True)
    # Mock: Async component isolation for testing without real async operations
    manager.send_to_thread = AsyncMock(return_value = True)
    # Mock: Async component isolation for testing without real async operations
    manager.send_message_to_user = AsyncMock(return_value = True)

def _create_real_tool_dispatcher():
    """Create real tool dispatcher instance."""
    # Skip during collection mode
    if env.get("TEST_COLLECTION_MODE"):
        # Mock: Generic component isolation for controlled unit testing
        return MagicMock()
    try:
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        return ToolDispatcher()
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import ToolDispatcher: {e}. Using mock instead.")
        return _create_mock_tool_dispatcher()

def _create_mock_tool_dispatcher():
    """Create mock tool dispatcher."""
    # Mock: Generic component isolation for controlled unit testing
    mock_dispatcher == MagicMock()
    _setup_tool_dispatcher_mocks(mock_dispatcher)
    return mock_dispatcher

def _setup_tool_dispatcher_mocks(mock_dispatcher):
    """Setup tool dispatcher mock methods."""
    # Mock: Async component isolation for testing without real async operations
    mock_dispatcher.execute = AsyncMock(return_value = {"result": "mock tool execution", "success": True})
    # Mock: Async component isolation for testing without real async operations
    mock_dispatcher.dispatch_tool = AsyncMock(return_value = {"output": "mock output"})
    # Mock: Service component isolation for predictable testing behavior
    mock_dispatcher.get_available_tools = MagicMock(return_value = [])

def _import_agent_classes():
    """Import agent classes for instantiation."""
    base_imports = _import_base_agent_classes()
    additional_imports = _import_additional_agent_classes()
    return {**base_imports, **additional_imports}

def _import_base_agent_classes():
    """Import base agent classes."""
    # Skip during collection mode
    if env.get("TEST_COLLECTION_MODE"):
        return {}
    
    agents == {}
    try:
        from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
        agents['data'] = DataSubAgent
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import DataSubAgent: {e}")
    
    try:
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        agents['triage'] = TriageSubAgent
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import TriageSubAgent: {e}")
    
    return agents

def _import_additional_agent_classes():
    """Import additional agent classes."""
    # Skip during collection mode
    if env.get("TEST_COLLECTION_MODE"):
        return {}
    
    agents == {}
    try:
        from netra_backend.app.agents.optimizations_core_sub_agent import (
            OptimizationsCoreSubAgent,
        )
        agents['optimization'] = OptimizationsCoreSubAgent
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import OptimizationsCoreSubAgent: {e}")
    
    try:
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        agents['reporting'] = ReportingSubAgent
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import ReportingSubAgent: {e}")
    
    return agents

def _instantiate_agents(agent_classes, llm_manager, tool_dispatcher):
    """Instantiate agents with dependencies."""
    agents = {}
    for name, agent_class in agent_classes.items():
        try:
            agents[name] = agent_class(llm_manager, tool_dispatcher)
        except Exception as e:
            import warnings
            warnings.warn(f"Cannot instantiate agent {name}: {e}")
            # Create a mock agent as fallback
            from unittest.mock import MagicMock
            # Mock: Generic component isolation for controlled unit testing
            agents[name] = MagicMock()
    return agents