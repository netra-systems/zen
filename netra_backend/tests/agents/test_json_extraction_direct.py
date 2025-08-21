"""Direct test for JSON extraction to debug the issue"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import Mock

# Add project root to path

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.utils import extract_json_from_response

# Add project root to path


def test_extract_json_with_trailing_comma():
    """Test extract_json_from_response with trailing comma"""
    response = '{"category": "Test", "priority": "high",}'
    
    result = extract_json_from_response(response)
    
    assert result is not None, "extract_json_from_response should return a result"
    assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
    assert result.get("category") == "Test", f"Category should be 'Test', got {result.get('category')}"
    assert result.get("priority") == "high", f"Priority should be 'high', got {result.get('priority')}"


def test_triage_agent_extract_json():
    """Test TriageSubAgent's _extract_and_validate_json method"""
    # Create a triage agent instance
    mock_llm = Mock()
    mock_tool = Mock()
    agent = TriageSubAgent(mock_llm, mock_tool, None)
    
    response = '{"category": "Test", "priority": "high",}'
    
    result = agent._extract_and_validate_json(response)
    
    assert result is not None, "_extract_and_validate_json should return a result"
    assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
    assert result.get("category") == "Test", f"Category should be 'Test', got {result.get('category')}"
    assert result.get("priority") == "high", f"Priority should be 'high', got {result.get('priority')}"


if __name__ == "__main__":
    # Run the tests directly
    test_extract_json_with_trailing_comma()
    print("✓ extract_json_from_response test passed")
    
    test_triage_agent_extract_json()
    print("✓ TriageSubAgent._extract_and_validate_json test passed")