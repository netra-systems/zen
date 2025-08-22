"""
Triage agent validation and tools tests
Tests tool recommendation, fallback categorization, JSON extraction, and entry conditions
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, Mock

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent import ExtractedEntities

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager

@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager."""
    mock = Mock(spec=LLMManager)
    mock.ask_llm = AsyncMock()
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Structured generation not available in test"))
    return mock

@pytest.fixture
def mock_tool_dispatcher():
    """Create a mock tool dispatcher."""
    return Mock(spec=ToolDispatcher)

@pytest.fixture
def mock_redis_manager():
    """Create a mock Redis manager."""
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create a TriageSubAgent instance with mocked dependencies."""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)

class TestToolRecommendation:
    """Test tool recommendation functionality."""
    
    def test_recommend_tools_for_cost_optimization(self, triage_agent):
        """Test tool recommendations for cost optimization."""
        entities = ExtractedEntities(models_mentioned=["gpt-4"], metrics_mentioned=["cost"])
        tools = triage_agent._recommend_tools("Cost Optimization", entities)
        
        assert len(tools) > 0
        assert any("cost" in t.tool_name.lower() for t in tools)
        assert all(0 <= t.relevance_score <= 1 for t in tools)
    
    def test_recommend_tools_for_performance(self, triage_agent):
        """Test tool recommendations for performance optimization."""
        entities = ExtractedEntities(metrics_mentioned=["latency", "throughput"])
        tools = triage_agent._recommend_tools("Performance Optimization", entities)
        
        assert len(tools) > 0
        assert any("latency" in t.tool_name or "performance" in t.tool_name for t in tools)

class TestFallbackCategorization:
    """Test fallback categorization when LLM fails."""
    
    def test_fallback_with_optimize_keyword(self, triage_agent):
        """Test fallback categorization with optimize keyword."""
        result = triage_agent._fallback_categorization("optimize my costs")
        
        assert result.category == "Cost Optimization"
        assert result.confidence_score == 0.5  # Lower confidence for fallback
        assert result.metadata.fallback_used == True
    
    def test_fallback_with_unknown_request(self, triage_agent):
        """Test fallback with request that doesn't match any keywords."""
        result = triage_agent._fallback_categorization("random text without keywords")
        
        assert result.category == "General Inquiry"
        assert result.confidence_score == 0.5

class TestJSONExtraction:
    """Test enhanced JSON extraction and validation."""
    
    def test_extract_valid_json(self, triage_agent):
        """Test extraction of valid JSON."""
        response = '{"category": "Test", "priority": "high"}'
        result = triage_agent._extract_and_validate_json(response)
        
        assert result != None
        assert result["category"] == "Test"
        assert result["priority"] == "high"
    
    def test_extract_json_with_text(self, triage_agent):
        """Test extraction of JSON embedded in text."""
        response = 'Here is the result: {"category": "Test"} and some more text'
        result = triage_agent._extract_and_validate_json(response)
        
        assert result != None
        assert result["category"] == "Test"
    
    def test_repair_json_with_trailing_comma(self, triage_agent):
        """Test repair of JSON with trailing commas."""
        response = '{"category": "Test", "priority": "high",}'
        result = triage_agent._extract_and_validate_json(response)
        
        assert result != None
        assert result["category"] == "Test"
        assert result["priority"] == "high"
    
    def test_extract_json_with_single_quotes(self, triage_agent):
        """Test extraction of JSON-like structure with single quotes."""
        response = "{'category': 'Test', 'priority': 'high'}"
        result = triage_agent._extract_and_validate_json(response)
        
        assert result != None
        assert result["category"] == "Test"

class TestEntryConditions:
    """Test entry condition validation."""
    
    @pytest.mark.asyncio
    
    async def test_entry_conditions_met(self, triage_agent):
        """Test when entry conditions are met."""
        sample_state = DeepAgentState(user_request="Optimize my GPT-4 costs by 30%")
        result = await triage_agent.check_entry_conditions(sample_state, "test_run")
        assert result == True

    @pytest.mark.asyncio

    async def test_entry_conditions_no_request(self, triage_agent):
        """Test when no user request is provided."""
        empty_state = DeepAgentState(user_request="")
        result = await triage_agent.check_entry_conditions(empty_state, "test_run")
        assert result == False

    @pytest.mark.asyncio

    async def test_entry_conditions_invalid_request(self, triage_agent):
        """Test when request is invalid."""
        state = DeepAgentState(user_request="a")  # Too short
        result = await triage_agent.check_entry_conditions(state, "test_run")
        assert result == False
        # Check validation status instead of error field
        assert hasattr(state.triage_result, 'validation_status')
        assert not state.triage_result.validation_status.is_valid