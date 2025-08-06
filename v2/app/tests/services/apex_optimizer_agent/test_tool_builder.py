import pytest
from functools import partial
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.llm.llm_manager import LLMManager
from unittest.mock import MagicMock
from app.services.context import ToolContext
from app.services.deepagents.state import DeepAgentState
from app.services.supply_catalog_service import SupplyCatalogService

@pytest.fixture
def mock_tool_context():
    return ToolContext(
        db_session=MagicMock(),
        llm_manager=MagicMock(spec=LLMManager),
        cost_estimator=MagicMock(),
        state=MagicMock(spec=DeepAgentState),
        supply_catalog=MagicMock(spec=SupplyCatalogService),
        logs=[]
    )

def test_all_tools_have_name_and_dunder_name_attributes(mock_tool_context):
    all_tools, _ = ToolBuilder.build_all(mock_tool_context)
    for name, tool in all_tools.items():
        assert hasattr(tool, 'name'), f"Tool {name} is missing name attribute"
        assert hasattr(tool, '__name__'), f"Tool {name} is missing __name__ attribute"

def test_tool_name_attributes_match_key(mock_tool_context):
    all_tools, _ = ToolBuilder.build_all(mock_tool_context)
    for name, tool in all_tools.items():
        assert tool.name == name, f"Tool {name} has mismatched name: {tool.name}"
        assert tool.__name__ == name, f"Tool {name} has mismatched __name__: {tool.__name__}"