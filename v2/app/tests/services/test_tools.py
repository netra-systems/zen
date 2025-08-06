import pytest
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from langchain_core.tools import tool

@tool
def mock_tool(a: int, b: int) -> int:
    """A mock tool that adds two numbers."""
    return a + b

@pytest.mark.asyncio
async def test_tool_dispatcher():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("mock_tool", a=1, b=2)
    assert result == 3

@pytest.mark.asyncio
async def test_tool_dispatcher_tool_not_found():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("non_existent_tool", a=1, b=2)
    assert result == "Tool 'non_existent_tool' not found."
