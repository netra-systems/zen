"""Helper functions and fixtures for ToolDispatcher tests."""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import (
    ProductionTool,
    ToolDispatcher,
    ToolDispatchResponse,
)
from netra_backend.app.schemas import ToolInput, ToolResult, ToolStatus

class MockBaseTool:
    """Mock tool for testing."""
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
    
    async def arun(self, kwargs: Dict[str, Any]) -> Any:
        if self.should_fail:
            raise Exception(f"Tool {self.name} failed")
        return {"result": f"Tool {self.name} executed with {kwargs}"}

def create_mock_tool(name: str, should_fail: bool = False) -> MockBaseTool:
    """Create a mock tool with specified behavior."""
    return MockBaseTool(name, should_fail)

def create_dispatcher_with_tools(tool_names: list[str]) -> ToolDispatcher:
    """Create dispatcher with mock tools."""
    tools = [create_mock_tool(name) for name in tool_names]
    return ToolDispatcher(tools)

def create_test_state(user_request: str = "test") -> DeepAgentState:
    """Create a test agent state."""
    return DeepAgentState(user_request=user_request)

def create_tool_input(tool_name: str, **kwargs) -> ToolInput:
    """Create a ToolInput for testing."""
    return ToolInput(tool_name=tool_name, kwargs=kwargs)

def verify_tool_result_success(result: ToolResult, tool_name: str) -> None:
    """Verify a ToolResult indicates success."""
    assert isinstance(result, ToolResult)
    assert result.status == ToolStatus.SUCCESS
    assert result.tool_input.tool_name == tool_name

def verify_tool_result_error(result: ToolResult, expected_error: str) -> None:
    """Verify a ToolResult indicates error with expected message."""
    assert isinstance(result, ToolResult)
    assert result.status == ToolStatus.ERROR
    assert expected_error in result.message

def verify_dispatch_response_success(response: ToolDispatchResponse) -> None:
    """Verify a ToolDispatchResponse indicates success."""
    assert isinstance(response, ToolDispatchResponse)
    assert response.success is True
    assert response.result is not None
    assert response.error is None

def verify_dispatch_response_error(response: ToolDispatchResponse, expected_error: str) -> None:
    """Verify a ToolDispatchResponse indicates error."""
    assert isinstance(response, ToolDispatchResponse)
    assert response.success is False
    assert response.result is None
    assert expected_error in response.error

def create_production_tool_mock(name: str, return_value: Any = None) -> ProductionTool:
    """Create a mocked ProductionTool."""
    tool = ProductionTool(name)
    tool.execute = AsyncMock(return_value=return_value or {"success": True})
    return tool

def setup_service_mock(service_path: str, method_name: str, return_value: Any = None):
    """Setup a service mock with return value."""
    return patch(service_path).return_value.__getattr__(method_name)

def assert_synthetic_tools_registered(dispatcher: ToolDispatcher) -> None:
    """Assert synthetic tools are registered in dispatcher."""
    synthetic_tools = _get_synthetic_tool_names()
    _assert_tools_registered(dispatcher, synthetic_tools)

def assert_corpus_tools_registered(dispatcher: ToolDispatcher) -> None:
    """Assert corpus tools are registered in dispatcher."""
    corpus_tools = _get_corpus_tool_names()
    _assert_tools_registered(dispatcher, corpus_tools)

def _get_synthetic_tool_names() -> list[str]:
    """Get list of synthetic tool names."""
    return [
        "generate_synthetic_data_batch",
        "validate_synthetic_data", 
        "store_synthetic_data"
    ]

def _get_corpus_tool_names() -> list[str]:
    """Get list of corpus tool names."""
    return [
        "create_corpus", "search_corpus", "update_corpus", "delete_corpus",
        "analyze_corpus", "export_corpus", "import_corpus", "validate_corpus"
    ]

def _assert_tools_registered(dispatcher: ToolDispatcher, tool_names: list[str]) -> None:
    """Assert all tools in list are registered."""
    for tool_name in tool_names:
        assert tool_name in dispatcher.tools
        assert isinstance(dispatcher.tools[tool_name], ProductionTool)

def verify_metadata(response: ToolDispatchResponse, tool_name: str, run_id: str) -> None:
    """Verify response metadata contains expected values."""
    assert response.metadata["tool_name"] == tool_name
    assert response.metadata["run_id"] == run_id