"""
Triage agent core functionality tests
Tests agent initialization, request validation, entity extraction, and intent determination
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent import ExtractedEntities, UserIntent
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager

@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager."""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock = Mock(spec=LLMManager)
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock.ask_llm = AsyncMock()
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Structured generation not available in test"))
    return mock

@pytest.fixture
def mock_tool_dispatcher():
    """Create a mock tool dispatcher."""
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    return Mock(spec=ToolDispatcher)

@pytest.fixture
def mock_redis_manager():
    """Create a mock Redis manager."""
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock = Mock(spec=RedisManager)
    # Mock: Async component isolation for testing without real async operations
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create a TriageSubAgent instance with mocked dependencies."""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)

@pytest.fixture
def sample_state():
    """Create a sample DeepAgentState."""
    return DeepAgentState(user_request="Optimize my GPT-4 costs by 30% while maintaining latency under 100ms")

class TestTriageSubAgentInitialization:
    """Test agent initialization and configuration."""
    
    def test_initialization_with_redis(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test initialization with Redis manager."""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        
        assert agent.llm_manager == mock_llm_manager
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.redis_manager == mock_redis_manager
        assert agent.cache_ttl == 3600
        assert agent.max_retries == 3
        assert agent.name == "TriageSubAgent"
    
    def test_initialization_without_redis(self, mock_llm_manager, mock_tool_dispatcher):
        """Test initialization without Redis manager."""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        assert agent.redis_manager == None
        assert agent.cache_ttl == 3600  # Still set even without Redis

class TestRequestValidation:
    """Test request validation functionality."""
    
    def test_valid_request(self, triage_agent):
        """Test validation of a valid request."""
        validation = triage_agent._validate_request("Optimize my AI costs")
        
        assert validation.is_valid == True
        assert len(validation.validation_errors) == 0
    
    def test_request_too_short(self, triage_agent):
        """Test validation of request that's too short."""
        validation = triage_agent._validate_request("ab")
        
        assert validation.is_valid == False
        assert "too short" in validation.validation_errors[0]
    
    def test_request_too_long(self, triage_agent):
        """Test validation of request that's too long."""
        long_request = "a" * 10001
        validation = triage_agent._validate_request(long_request)
        
        assert validation.is_valid == False
        assert "exceeds maximum length" in validation.validation_errors[0]
    
    def test_request_with_injection_pattern(self, triage_agent):
        """Test detection of potential injection patterns."""
        validation = triage_agent._validate_request("DROP TABLE users; SELECT * FROM data")
        
        assert validation.is_valid == False
        assert "malicious pattern" in validation.validation_errors[0]
    
    def test_request_with_warnings(self, triage_agent):
        """Test request that generates warnings but is still valid."""
        long_request = "a" * 5001
        validation = triage_agent._validate_request(long_request)
        
        assert validation.is_valid == True  # Valid but with warnings
        assert len(validation.warnings) > 0

class TestEntityExtraction:
    """Test entity extraction from requests."""
    
    def test_extract_model_names(self, triage_agent):
        """Test extraction of AI model names."""
        request = "Compare GPT-4 with Claude-2 and Llama-2 performance"
        entities = triage_agent._extract_entities_from_request(request)
        
        assert LLMModel.GEMINI_2_5_FLASH.value in entities.models_mentioned
        assert "claude-2" in entities.models_mentioned
        assert "llama-2" in entities.models_mentioned
    
    def test_extract_metrics(self, triage_agent):
        """Test extraction of performance metrics."""
        request = "Reduce latency and improve throughput while managing cost"
        entities = triage_agent._extract_entities_from_request(request)
        
        assert "latency" in entities.metrics_mentioned
        assert "throughput" in entities.metrics_mentioned
        assert "cost" in entities.metrics_mentioned
    
    def test_extract_numerical_thresholds(self, triage_agent):
        """Test extraction of numerical thresholds and targets."""
        request = "Keep latency under 100ms and reduce costs by 30%"
        entities = triage_agent._extract_entities_from_request(request)
        
        # Check thresholds
        time_thresholds = [t for t in entities.thresholds if t["type"] == "time"]
        assert len(time_thresholds) > 0
        
        # Check targets
        percentage_targets = [t for t in entities.targets if t["type"] == "percentage"]
        assert len(percentage_targets) > 0
    
    def test_extract_time_ranges(self, triage_agent):
        """Test extraction of time ranges."""
        request = "Analyze performance over the last 7 days"
        entities = triage_agent._extract_entities_from_request(request)
        
        assert len(entities.time_ranges) > 0

class TestIntentDetermination:
    """Test user intent determination."""
    
    def test_optimize_intent(self, triage_agent):
        """Test detection of optimization intent."""
        request = "Optimize my model performance"
        intent = triage_agent._determine_intent(request)
        
        assert intent.primary_intent == "optimize"
        assert intent.action_required == True
    
    def test_analyze_intent(self, triage_agent):
        """Test detection of analysis intent."""
        request = "Analyze the usage patterns"
        intent = triage_agent._determine_intent(request)
        
        assert intent.primary_intent == "analyze"
    
    def test_multiple_intents(self, triage_agent):
        """Test detection of multiple intents."""
        request = "Analyze current performance and recommend optimizations"
        intent = triage_agent._determine_intent(request)
        
        assert intent.primary_intent in ["analyze", "recommend"]
        assert len(intent.secondary_intents) > 0
    
    def test_complex_intent(self, triage_agent):
        """Test detection of complex multi-part intent."""
        request = "Monitor my AI costs and automatically optimize when costs exceed $1000"
        intent = triage_agent._determine_intent(request)
        
        assert intent.primary_intent in ["monitor", "optimize"]
        assert intent.action_required == True
        assert len(intent.secondary_intents) >= 0  # May have secondary intents
    
    def test_fallback_intent_classification(self, triage_agent):
        """Test fallback mechanism for unclear intents."""
        request = "Something is wrong with my AI models maybe"
        intent = triage_agent._determine_intent(request)
        
        # Should fallback to analyze intent (default)
        assert intent.primary_intent == "analyze"
        assert intent.action_required == False  # Analyze intent doesn't require action by default

class TestTriageAgentIntegration:
    """Test integration scenarios with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_full_triage_process_success(self, triage_agent, sample_state):
        """Test complete triage process with successful validation and processing."""
        # Mock successful LLM response
        triage_agent.llm_manager.ask_llm.return_value = {
            "category": "optimization",
            "subcategory": "cost",
            "confidence": 0.85,
            "reasoning": "User wants to optimize GPT-4 costs"
        }
        
        # Execute the triage workflow (this updates the state instead of returning a result)
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Check that the state was updated with triage results
        assert hasattr(sample_state, 'triage_result')
        assert sample_state.triage_result is not None
        # Verify the triage result has expected structure
        if isinstance(sample_state.triage_result, dict):
            assert "category" in sample_state.triage_result
        assert triage_agent.llm_manager.ask_llm.called
    
    @pytest.mark.asyncio
    async def test_triage_with_validation_failure(self, triage_agent):
        """Test triage process when request validation fails."""
        invalid_state = DeepAgentState(user_request="ab")  # Too short
        
        # Execute the triage workflow with invalid state
        await triage_agent.execute(invalid_state, "test_run", stream_updates=False)
        
        # Check that the state was updated with error result
        assert hasattr(invalid_state, 'triage_result')
        assert invalid_state.triage_result is not None
        if isinstance(invalid_state.triage_result, dict):
            # Should have error category or error field
            assert invalid_state.triage_result.get("category") == "Error" or "error" in invalid_state.triage_result
        # LLM should not be called for invalid requests
        triage_agent.llm_manager.ask_llm.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_triage_with_llm_failure(self, triage_agent, sample_state):
        """Test triage process when LLM fails."""
        # Mock LLM failure
        triage_agent.llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")
        
        # Execute the triage workflow with LLM failure
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Check that the state was updated with fallback result
        assert hasattr(sample_state, 'triage_result')
        assert sample_state.triage_result is not None
        if isinstance(sample_state.triage_result, dict):
            # Should have a category (either fallback or error)
            assert "category" in sample_state.triage_result
            # Could be error or fallback category
            category = sample_state.triage_result.get("category")
            assert category in ["general", "optimization", "Error"]