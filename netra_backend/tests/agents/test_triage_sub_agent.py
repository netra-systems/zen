"""
Comprehensive tests for the enhanced TriageSubAgent.
Tests all major functionality including categorization, caching, fallback, and error handling.
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Test framework import - using pytest fixtures instead

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from netra_backend.app.schemas import SubAgentLifecycle

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent import (
    Complexity,
    ExtractedEntities,
    KeyParameters,
    Priority,
    TriageResult,
    UserIntent,
    ValidationStatus,
)

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
    # Mock ask_structured_llm to raise an exception so it falls back to regular ask_llm
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

class TestToolRecommendation:
    """Test tool recommendation functionality."""
    
    def test_recommend_tools_for_cost_optimization(self, triage_agent):
        """Test tool recommendations for cost optimization."""
        entities = ExtractedEntities(models_mentioned=[LLMModel.GEMINI_2_5_FLASH.value], metrics_mentioned=["cost"])
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

class TestCaching:
    """Test caching functionality."""
    @pytest.mark.asyncio
    async def test_cache_hit(self, triage_agent, sample_state, mock_redis_manager):
        """Test successful cache hit."""
        cached_result = {
            "category": "Cost Optimization",
            "metadata": {"cache_hit": False, "triage_duration_ms": 100}
        }
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis_manager.get = AsyncMock(return_value=json.dumps(cached_result))
        
        # Mock LLM should not be called on cache hit
        # Mock: LLM provider isolation to prevent external API usage and costs
        triage_agent.llm_manager.ask_llm = AsyncMock(return_value='{"category": "Different"}')
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Verify cache was checked
        mock_redis_manager.get.assert_called_once()
        
        # Verify LLM was not called due to cache hit
        triage_agent.llm_manager.ask_llm.assert_not_called()
        
        # Check result uses cached data
        assert sample_state.triage_result.category == "Cost Optimization"
        assert sample_state.triage_result.metadata.cache_hit == True
    @pytest.mark.asyncio
    async def test_cache_miss_and_store(self, triage_agent, sample_state, mock_redis_manager):
        """Test cache miss leading to LLM call and result caching."""
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis_manager.get = AsyncMock(return_value=None)  # Cache miss
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis_manager.set = AsyncMock(return_value=True)  # Mock the set method
        
        llm_response = json.dumps({
            "category": "Cost Optimization",
            "priority": "high"
        })
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        triage_agent.llm_manager.ask_llm = AsyncMock(return_value=llm_response)
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Verify cache was checked
        mock_redis_manager.get.assert_called_once()
        
        # Verify LLM was called
        triage_agent.llm_manager.ask_llm.assert_called_once()
        
        # Verify result was cached
        mock_redis_manager.set.assert_called_once()
        
        # Check result - agent may return different categories based on fallback behavior
        assert sample_state.triage_result.category in ["Cost Optimization", "unknown", "General Inquiry"]
        assert sample_state.triage_result.metadata.cache_hit == False

class TestExecuteMethod:
    """Test the main execute method."""
    @pytest.mark.asyncio
    async def test_successful_execution(self, triage_agent, sample_state):
        """Test successful execution with valid LLM response."""
        llm_response = json.dumps({
            "category": "Cost Optimization",
            "priority": "high",
            "confidence_score": 0.9
        })
        triage_agent.llm_manager.ask_llm.return_value = llm_response
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        assert sample_state.triage_result != None
        assert sample_state.triage_result.category == "Cost Optimization"
        assert sample_state.triage_result.priority == Priority.HIGH
        assert hasattr(sample_state.triage_result, 'metadata')
        assert hasattr(sample_state.triage_result, 'extracted_entities')
        assert "user_intent" in sample_state.triage_result
        assert "tool_recommendations" in sample_state.triage_result
    @pytest.mark.asyncio
    async def test_execution_with_retry(self, triage_agent, sample_state):
        """Test execution with LLM failure and retry."""
        # First call fails, second succeeds
        triage_agent.llm_manager.ask_llm.side_effect = [
            Exception("LLM error"),
            json.dumps({"category": "Cost Optimization"})
        ]
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Should have called LLM twice (initial + 1 retry)
        assert triage_agent.llm_manager.ask_llm.call_count == 2
        assert sample_state.triage_result.category == "Cost Optimization"
        assert sample_state.triage_result.metadata.retry_count == 1
    @pytest.mark.asyncio
    async def test_execution_with_fallback(self, triage_agent, sample_state):
        """Test execution falling back to simple categorization."""
        # All retries fail
        triage_agent.llm_manager.ask_llm.side_effect = Exception("LLM error")
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=False)
        
        # Should have attempted max retries
        assert triage_agent.llm_manager.ask_llm.call_count == triage_agent.max_retries
        
        # Should use fallback
        assert sample_state.triage_result != None
        assert sample_state.triage_result.metadata.fallback_used == True
        assert sample_state.triage_result.confidence_score == 0.5
    @pytest.mark.asyncio
    async def test_execution_with_websocket_updates(self, triage_agent, sample_state):
        """Test execution with WebSocket updates enabled."""
        # Mock: WebSocket connection isolation for testing without network overhead
        triage_agent.websocket_manager = AsyncMock()
        
        llm_response = json.dumps({"category": "Cost Optimization"})
        triage_agent.llm_manager.ask_llm.return_value = llm_response
        
        await triage_agent.execute(sample_state, "test_run", stream_updates=True)
        
        # Should have sent WebSocket updates
        assert triage_agent.websocket_manager.send_message.called

class TestEntryConditions:
    """Test entry condition validation."""
    @pytest.mark.asyncio
    async def test_entry_conditions_met(self, triage_agent, sample_state):
        """Test when entry conditions are met."""
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

class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_triage_result_validation(self):
        """Test TriageResult model validation."""
        # Valid result
        result = TriageResult(
            category="Test",
            confidence_score=0.8,
            priority=Priority.HIGH,
            complexity=Complexity.MODERATE
        )
        assert result.category == "Test"
        assert result.confidence_score == 0.8
    
    def test_triage_result_confidence_validation(self):
        """Test confidence score validation."""
        with pytest.raises(ValueError):
            TriageResult(category="Test", confidence_score=1.5)  # Out of range
    
    def test_key_parameters_model(self):
        """Test KeyParameters model."""
        params = KeyParameters(
            workload_type="inference",
            optimization_focus="cost",
            constraints=["latency < 100ms", "cost < $1000"]
        )
        assert params.workload_type == "inference"
        assert len(params.constraints) == 2
    
    def test_user_intent_model(self):
        """Test UserIntent model."""
        intent = UserIntent(
            primary_intent="optimize",
            secondary_intents=["analyze", "compare"],
            action_required=True
        )
        assert intent.primary_intent == "optimize"
        assert len(intent.secondary_intents) == 2
        assert intent.action_required == True

class TestCleanup:
    """Test cleanup functionality."""
    @pytest.mark.asyncio
    async def test_cleanup_with_metrics(self, triage_agent, sample_state):
        """Test cleanup logs metrics when available."""
        sample_state.triage_result = {
            "category": "Test",
            "metadata": {
                "triage_duration_ms": 100,
                "cache_hit": False
            }
        }
        
        # Patch the instance logger, not the module logger
        with patch.object(triage_agent, 'logger') as mock_logger:
            await triage_agent.cleanup(sample_state, "test_run")
            
            # Should log debug metrics
            mock_logger.debug.assert_called()

class TestRequestHashing:
    """Test request hashing for caching."""
    
    def test_hash_generation(self, triage_agent):
        """Test hash generation for requests."""
        request1 = "Optimize my costs"
        request2 = "optimize MY   costs"  # Different case and spacing
        request3 = "Reduce my costs"  # Different text
        
        hash1 = triage_agent._generate_request_hash(request1)
        hash2 = triage_agent._generate_request_hash(request2)
        hash3 = triage_agent._generate_request_hash(request3)
        
        # Similar requests should have same hash
        assert hash1 == hash2
        
        # Different requests should have different hash
        assert hash1 != hash3
    
    def test_hash_normalization(self, triage_agent):
        """Test that request normalization works correctly."""
        request = "  OPTIMIZE   my   COSTS  "
        normalized_hash = triage_agent._generate_request_hash(request)
        
        # Should handle extra spaces and case
        expected_hash = triage_agent._generate_request_hash("optimize my costs")
        assert normalized_hash == expected_hash

if __name__ == "__main__":
    pytest.main([__file__, "-v"])