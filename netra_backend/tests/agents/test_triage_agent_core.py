"""
Triage agent core functionality tests
Tests agent initialization, request validation, entity extraction, and intent determination
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, Mock

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
        
        assert "gpt-4" in entities.models_mentioned
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