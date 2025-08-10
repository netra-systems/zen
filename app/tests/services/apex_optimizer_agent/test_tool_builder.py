import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.agents.tool_dispatcher import ToolDispatcher
from app.services.context import ToolContext
from langchain_core.tools import StructuredTool
from app.services.apex_optimizer_agent.models import ToolStatus

@pytest.mark.asyncio
async def test_tool_builder_and_dispatcher():
    # Create a mock context
    mock_context = MagicMock(spec=ToolContext)
    mock_context.db_session = AsyncMock()
    mock_context.llm_manager = MagicMock()
    mock_context.cost_estimator = MagicMock()
    mock_context.state = MagicMock()
    mock_context.supply_catalog = MagicMock()

    # Build the tools
    bound_tools, _ = ToolBuilder.build_all(mock_context)

    # Check that all tools are StructuredTool instances
    for tool_name, tool in bound_tools.items():
        assert isinstance(tool, StructuredTool), f"Tool {tool_name} is not a StructuredTool"

    # Create a ToolDispatcher with the built tools
    tool_dispatcher = ToolDispatcher(tools=list(bound_tools.values()))

    # Get the cost_analyzer tool
    cost_analyzer_tool = bound_tools.get("cost_analyzer")
    assert cost_analyzer_tool is not None, "cost_analyzer tool not found"

    # Mock the tool's _arun method
    cost_analyzer_tool._arun = AsyncMock(return_value="Success")

    # Dispatch the tool
    result = await tool_dispatcher.dispatch("cost_analyzer", **{})

    # Assert the result
    assert result.status == ToolStatus.SUCCESS
    assert result.payload == "Success"

    # Verify that the _arun method was called
    cost_analyzer_tool._arun.assert_called_once()
