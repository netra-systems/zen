from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from unittest.mock import MagicMock

def test_tool_builder_builds_all_tools():
    mock_db_session = MagicMock()
    mock_llm_manager = MagicMock()
    
    all_tools, super_tools = ToolBuilder.build_all(mock_db_session, mock_llm_manager)
    
    assert isinstance(all_tools, dict)
    assert len(all_tools) > 0