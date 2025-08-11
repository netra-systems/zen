
import pytest
from app.agents.tool_dispatcher import ToolDispatcher
from langchain_core.tools import tool

@tool
def mock_tool(a: int, b: int) -> int:
    """A mock tool that adds two numbers."""
    return a + b

@pytest.mark.asyncio
async def test_tool_dispatcher():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("mock_tool", a=1, b=2)
    assert result.payload == 3
    assert result.tool_input.tool_name == "mock_tool"

@pytest.mark.asyncio
async def test_tool_dispatcher_tool_not_found():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("non_existent_tool", a=1, b=2)
    assert "Tool non_existent_tool not found" in result.message
    assert result.tool_input.tool_name == "non_existent_tool"

@pytest.mark.asyncio
async def test_tool_dispatcher_tool_error():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("mock_tool", a=1, b="2")
    # Error message contains the actual exception
    assert result.message is not None
    assert result.tool_input.tool_name == "mock_tool"
