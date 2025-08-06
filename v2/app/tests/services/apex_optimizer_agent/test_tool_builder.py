import pytest
from functools import partial
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.llm.llm_manager import LLMManager
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_llm_manager():
    return MagicMock(spec=LLMManager)

def test_all_tools_have_name_and_dunder_name_attributes(mock_db_session, mock_llm_manager):
    all_tools, _ = ToolBuilder.build_all(mock_db_session, mock_llm_manager)
    for name, tool in all_tools.items():
        assert hasattr(tool, 'name'), f"Tool {name} is missing name attribute"
        assert hasattr(tool, '__name__'), f"Tool {name} is missing __name__ attribute"

def test_tool_name_attributes_match_key(mock_db_session, mock_llm_manager):
    all_tools, _ = ToolBuilder.build_all(mock_db_session, mock_llm_manager)
    for name, tool in all_tools.items():
        assert tool.name == name, f"Tool {name} has mismatched name: {tool.name}"
        assert tool.__name__ == name, f"Tool {name} has mismatched __name__: {tool.__name__}"