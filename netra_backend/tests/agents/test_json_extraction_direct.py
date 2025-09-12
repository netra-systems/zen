from unittest.mock import Mock, patch, MagicMock

"""Direct test for JSON extraction to debug the issue"""

import sys
from pathlib import Path
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead


import pytest

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.utils import extract_json_from_response

def test_extract_json_with_trailing_comma():
    """Test extract_json_from_response with trailing comma"""
    response = '{"category": "Test", "priority": "high",}'
    
    result = llm_parser.extract_json_from_response(response)
    
    assert result is not None, "extract_json_from_response should return a result"
    assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
    assert result.get("category") == "Test", f"Category should be 'Test', got {result.get('category')}"
    assert result.get("priority") == "high", f"Priority should be 'high', got {result.get('priority')}"

def test_triage_agent_extract_json():
    """Test TriageSubAgent's _extract_and_validate_json method"""
    # Create a triage agent instance
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_llm = mock_llm_instance  # Initialize appropriate service
    # Mock: Generic component isolation for controlled unit testing
    mock_tool = mock_tool_instance  # Initialize appropriate service
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
    print("[U+2713] extract_json_from_response test passed")
    
    test_triage_agent_extract_json()
    print("[U+2713] TriageSubAgent._extract_and_validate_json test passed")