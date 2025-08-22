
# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest
from langchain_core.tools import tool

# Add project root to path
from app.agents.tool_dispatcher import ToolDispatcher

# Add project root to path

@tool
def mock_tool(a: int, b: int) -> int:
    """A mock tool that adds two numbers."""
    return a + b
async def test_tool_dispatcher():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("mock_tool", a=1, b=2)
    assert result.status == "success"
    assert result.payload.result == 3  # Access as attribute of SimpleToolPayload
    assert result.tool_input.tool_name == "mock_tool"
async def test_tool_dispatcher_tool_not_found():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("non_existent_tool", a=1, b=2)
    assert "Tool non_existent_tool not found" in result.message
    assert result.tool_input.tool_name == "non_existent_tool"
async def test_tool_dispatcher_tool_error():
    dispatcher = ToolDispatcher(tools=[mock_tool])
    result = await dispatcher.dispatch("mock_tool", a=1, b="2")
    # Error message contains the actual exception
    assert result.message != None
    assert result.tool_input.tool_name == "mock_tool"
