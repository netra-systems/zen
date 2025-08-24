"""
Tests for structured generation functionality in LLM Manager.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import json
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, Field
from netra_backend.app.schemas import AppConfig, LLMConfig

from netra_backend.app.llm.llm_manager import LLMManager

from netra_backend.tests.llm_mocks import MockLLM, MockStructuredLLM

class SampleResponseModel(BaseModel):
    """Sample model for structured generation testing."""
    message: str
    confidence: float = Field(ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[dict] = None

class SampleComplexModel(BaseModel):
    """Complex model with nested structures for testing."""
    id: int
    name: str
    details: dict
    items: List[dict]
    score: float = Field(ge=0.0, le=100.0)

@pytest.fixture
def test_config():
    """Create test configuration."""
    import os
    
    # Use real API key if available, otherwise use test key
    api_key = os.environ.get("OPENAI_API_KEY", "test-openai-key")
    
    # If we have a Gemini API key but testing with OpenAI, skip real testing
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true" and api_key == "test-openai-key":
        # Try using Gemini instead if available
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            return AppConfig(
                llm_configs={
                    "test": LLMConfig(
                        provider="google",
                        model_name="gemini-1.5-flash",
                        api_key=gemini_key,
                        generation_config={"temperature": 0.7}
                    )
                }
            )
    
    return AppConfig(
        llm_configs={
            "test": LLMConfig(
                provider="openai",
                model_name="gpt-3.5-turbo",
                api_key=api_key,
                generation_config={"temperature": 0.7}
            )
        }
    )

@pytest.fixture
def llm_manager(test_config):
    """Create LLM manager instance."""
    return LLMManager(test_config)

class TestMockStructuredLLM:
    """Test MockStructuredLLM functionality."""
    
    def test_mock_structured_llm_creation(self):
        """Test creating a mock structured LLM."""
        mock_llm = MockLLM("test-model")
        structured_llm = mock_llm.with_structured_output(SampleResponseModel)
        
        assert isinstance(structured_llm, MockStructuredLLM)
        assert structured_llm.model_name == "test-model"
        assert structured_llm.schema == SampleResponseModel
    @pytest.mark.asyncio
    async def test_mock_structured_llm_invoke(self):
        """Test invoking mock structured LLM returns valid schema instance."""
        mock_llm = MockLLM("test-model")
        structured_llm = mock_llm.with_structured_output(SampleResponseModel)
        
        result = await structured_llm.ainvoke("test prompt")
        
        assert isinstance(result, SampleResponseModel)
        assert isinstance(result.message, str)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.tags, list)
    @pytest.mark.asyncio
    async def test_mock_structured_llm_complex_model(self):
        """Test mock structured LLM with complex model."""
        mock_llm = MockLLM("test-model")
        structured_llm = mock_llm.with_structured_output(SampleComplexModel)
        
        result = await structured_llm.ainvoke("test prompt")
        
        assert isinstance(result, SampleComplexModel)
        assert isinstance(result.id, int)
        assert isinstance(result.name, str)
        assert isinstance(result.details, dict)
        assert isinstance(result.items, list)

class TestLLMManagerStructuredGeneration:
    """Test LLMManager structured generation methods."""
    
    def test_get_structured_llm_with_mock(self, llm_manager):
        """Test getting structured LLM in dev mode (mock)."""
        llm_manager.enabled = False  # Force mock mode
        llm_manager._core.enabled = False  # Also set core enabled to False
        llm_manager._core.provider_manager.config_manager.enabled = False  # Disable at config level
        
        structured_llm = llm_manager.get_structured_llm(
            "test",
            SampleResponseModel
        )
        
        assert isinstance(structured_llm, MockStructuredLLM)
    
    # Mock: Component isolation for testing without external dependencies
    @patch('langchain_openai.ChatOpenAI')
    def test_get_structured_llm_with_real(self, mock_openai, llm_manager):
        """Test getting structured LLM with real provider."""
        llm_manager.enabled = True
        llm_manager._core.enabled = True
        
        # Mock the get_llm method to return our mock LLM
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_instance = MagicMock()
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_instance.with_structured_output = MagicMock(return_value="structured_llm")
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager._core.get_llm = MagicMock(return_value=mock_llm_instance)
        
        structured_llm = llm_manager.get_structured_llm(
            "test",
            SampleResponseModel
        )
        
        mock_llm_instance.with_structured_output.assert_called_once()
        assert structured_llm == "structured_llm"
    @pytest.mark.asyncio
    async def test_ask_structured_llm_success(self, llm_manager):
        """Test successful structured LLM call."""
        # Create a mock structured LLM that returns a valid response
        mock_response = SampleResponseModel(
            message="Test response",
            confidence=0.95,
            tags=["test", "success"]
        )
        
        # Mock at the structured operations level
        with patch.object(llm_manager._structured, 'get_structured_llm') as mock_get:
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm = AsyncMock()
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_structured_llm
            
            result = await llm_manager.ask_structured_llm(
                "test prompt",
                "test",
                SampleResponseModel,
                use_cache=False
            )
            
            assert isinstance(result, SampleResponseModel)
            assert result.message == "Test response"
            assert result.confidence == 0.95
            assert result.tags == ["test", "success"]
    @pytest.mark.asyncio
    async def test_ask_structured_llm_with_cache(self, llm_manager):
        """Test structured LLM with caching."""
        cached_data = SampleResponseModel(
            message="Cached response",
            confidence=0.85,
            tags=["cached"]
        )
        
        # Mock the structured operations to return cached data directly
        with patch.object(llm_manager._structured, 'ask_structured_llm') as mock_ask:
            mock_ask.return_value = cached_data
            
            result = await llm_manager.ask_structured_llm(
                "test prompt",
                "test",
                SampleResponseModel,
                use_cache=True
            )
            
            assert isinstance(result, SampleResponseModel)
            assert result.message == "Cached response"
            assert result.confidence == 0.85
            assert result.tags == ["cached"]
    @pytest.mark.asyncio
    async def test_ask_structured_llm_fallback_to_json(self, llm_manager):
        """Test fallback to JSON parsing when structured generation fails."""
        json_response = json.dumps({
            "message": "JSON fallback",
            "confidence": 0.75,
            "tags": ["fallback"]
        })
        
        # Mock the structured operations to trigger fallback behavior
        with patch.object(llm_manager._structured, 'get_structured_llm') as mock_get:
            # Make structured call fail
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm = AsyncMock()
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm.ainvoke = AsyncMock(
                side_effect=Exception("Structured generation failed")
            )
            mock_get.return_value = mock_structured_llm
            
            # Mock the core ask_llm for fallback
            with patch.object(llm_manager._structured.core, 'ask_llm') as mock_ask:
                mock_ask.return_value = json_response
                
                result = await llm_manager.ask_structured_llm(
                    "test prompt",
                    "test",
                    SampleResponseModel,
                    use_cache=False
                )
                
                assert isinstance(result, SampleResponseModel)
                assert result.message == "JSON fallback"
                assert result.confidence == 0.75
    @pytest.mark.asyncio
    async def test_ask_structured_llm_complete_failure(self, llm_manager):
        """Test complete failure of structured generation."""
        with patch.object(llm_manager._structured, 'get_structured_llm') as mock_get:
            # Make structured call fail
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm = AsyncMock()
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm.ainvoke = AsyncMock(
                side_effect=Exception("Structured generation failed")
            )
            mock_get.return_value = mock_structured_llm
            
            # Make fallback also fail
            with patch.object(llm_manager._structured.core, 'ask_llm') as mock_ask:
                mock_ask.return_value = "Not JSON"
                
                with pytest.raises(Exception) as exc_info:
                    await llm_manager.ask_structured_llm(
                        "test prompt",
                        "test",
                        SampleResponseModel,
                        use_cache=False
                    )
                
                assert "Structured generation failed" in str(exc_info.value)

class TestNestedJSONParsing:
    """Test nested JSON parsing functionality."""
    @pytest.mark.asyncio
    async def test_parse_nested_json_with_tool_recommendations(self, llm_manager):
        """Test parsing nested JSON strings in tool_recommendations parameters."""
        # This is the exact structure that was failing
        raw_data = {
            "category": "optimization",
            "confidence_score": 0.85,
            "tool_recommendations": [
                {
                    "tool_name": "latency_analyzer",
                    "relevance_score": 0.9,
                    "parameters": '{"feature_X_latency": "50ms", "feature_Y_latency": "200ms"}'
                },
                {
                    "tool_name": "performance_monitor",
                    "relevance_score": 0.8,
                    "parameters": '{"threshold": 100, "interval": "5m"}'
                }
            ]
        }
        
        parsed = llm_manager._parse_nested_json(raw_data)
        
        # Verify parameters are now dictionaries, not strings
        assert isinstance(parsed["tool_recommendations"][0]["parameters"], dict)
        assert isinstance(parsed["tool_recommendations"][1]["parameters"], dict)
        
        # Verify the actual values
        assert parsed["tool_recommendations"][0]["parameters"]["feature_X_latency"] == "50ms"
        assert parsed["tool_recommendations"][1]["parameters"]["threshold"] == 100
    @pytest.mark.asyncio
    async def test_parse_deeply_nested_json(self, llm_manager):
        """Test parsing deeply nested JSON strings."""
        raw_data = {
            "outer": {
                "middle": '{"inner": "{\\"value\\": 42}"}'
            }
        }
        
        parsed = llm_manager._parse_nested_json(raw_data)
        
        # Should parse all levels
        assert isinstance(parsed["outer"]["middle"], dict)
        assert isinstance(parsed["outer"]["middle"]["inner"], dict)
        assert parsed["outer"]["middle"]["inner"]["value"] == 42

class TestIntegrationWithAgents:
    """Test integration of structured generation with agents."""
    @pytest.mark.asyncio
    async def test_triage_agent_structured_response(self):
        """Test that triage agent can use structured responses."""
        from netra_backend.app.agents.triage_sub_agent import TriageResult
        from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
        
        # This is more of an integration test placeholder
        # Real test would require full agent setup
        
        # Verify the model is properly defined
        result = TriageResult(
            category="Test Category",
            confidence_score=0.9
        )
        
        assert result.category == "Test Category"
        assert result.confidence_score == 0.9
        assert result.priority.value == "medium"  # Default value
    @pytest.mark.asyncio
    async def test_triage_result_with_nested_json_parameters(self, llm_manager):
        """Test TriageResult validation with nested JSON in tool_recommendations."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        
        # Simulate the exact error case: parameters as JSON string
        raw_response = {
            "category": "optimization",
            "confidence_score": 0.85,
            "tool_recommendations": [
                {
                    "tool_name": "latency_analyzer",
                    "relevance_score": 0.9,
                    "parameters": '{"feature_X_latency": "50ms", "feature_Y_latency": "200ms"}'
                }
            ]
        }
        
        # Parse nested JSON
        parsed = llm_manager._parse_nested_json(raw_response)
        
        # Should now validate successfully
        result = TriageResult(**parsed)
        
        assert result.category == "optimization"
        assert result.confidence_score == 0.85
        assert len(result.tool_recommendations) == 1
        assert isinstance(result.tool_recommendations[0].parameters, dict)
        assert result.tool_recommendations[0].parameters["feature_X_latency"] == "50ms"
    @pytest.mark.asyncio
    async def test_data_agent_structured_response(self):
        """Test that data agent can use structured responses."""
        from netra_backend.app.agents.data_sub_agent.models import DataAnalysisResponse
        
        # Verify the model is properly defined
        response = DataAnalysisResponse(
            query="SELECT * FROM test",
            results=[{"id": 1, "value": "test"}],
            execution_time_ms=125.5
        )
        
        assert response.query == "SELECT * FROM test"
        assert len(response.results) == 1
        assert response.execution_time_ms == 125.5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])