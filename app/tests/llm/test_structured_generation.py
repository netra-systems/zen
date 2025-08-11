"""
Tests for structured generation functionality in LLM Manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel, Field
from typing import List, Optional
import json

from app.llm.llm_manager import LLMManager, MockLLM, MockStructuredLLM
from app.schemas import AppConfig, LLMConfig


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
    return AppConfig(
        llm_configs={
            "test": LLMConfig(
                provider="openai",
                model_name="gpt-3.5-turbo",
                api_key="test-key",
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
        
        structured_llm = llm_manager.get_structured_llm(
            "test",
            SampleResponseModel
        )
        
        assert isinstance(structured_llm, MockStructuredLLM)
    
    @patch('app.llm.llm_manager.ChatOpenAI')
    def test_get_structured_llm_with_real(self, mock_openai, llm_manager):
        """Test getting structured LLM with real provider."""
        llm_manager.enabled = True
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output = MagicMock(return_value="structured_llm")
        mock_openai.return_value = mock_llm_instance
        
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
        
        with patch.object(llm_manager, 'get_structured_llm') as mock_get:
            mock_structured_llm = AsyncMock()
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
        
        with patch('app.services.llm_cache_service.llm_cache_service') as mock_cache:
            mock_cache.get_cached_response = AsyncMock(
                return_value=cached_data.model_dump_json()
            )
            
            result = await llm_manager.ask_structured_llm(
                "test prompt",
                "test",
                SampleResponseModel,
                use_cache=True
            )
            
            assert isinstance(result, SampleResponseModel)
            assert result.message == "Cached response"
            assert result.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_ask_structured_llm_fallback_to_json(self, llm_manager):
        """Test fallback to JSON parsing when structured generation fails."""
        json_response = json.dumps({
            "message": "JSON fallback",
            "confidence": 0.75,
            "tags": ["fallback"]
        })
        
        with patch.object(llm_manager, 'get_structured_llm') as mock_get:
            # Make structured call fail
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                side_effect=Exception("Structured generation failed")
            )
            mock_get.return_value = mock_structured_llm
            
            # Mock regular LLM to return JSON
            with patch.object(llm_manager, 'ask_llm') as mock_ask:
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
        with patch.object(llm_manager, 'get_structured_llm') as mock_get:
            # Make structured call fail
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                side_effect=Exception("Structured generation failed")
            )
            mock_get.return_value = mock_structured_llm
            
            # Make fallback also fail
            with patch.object(llm_manager, 'ask_llm') as mock_ask:
                mock_ask.return_value = "Not JSON"
                
                with pytest.raises(Exception) as exc_info:
                    await llm_manager.ask_structured_llm(
                        "test prompt",
                        "test",
                        SampleResponseModel,
                        use_cache=False
                    )
                
                assert "Structured generation failed" in str(exc_info.value)


class TestIntegrationWithAgents:
    """Test integration of structured generation with agents."""
    
    @pytest.mark.asyncio
    async def test_triage_agent_structured_response(self):
        """Test that triage agent can use structured responses."""
        from app.agents.triage_sub_agent import TriageResult, TriageSubAgent
        
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
    async def test_data_agent_structured_response(self):
        """Test that data agent can use structured responses."""
        from app.agents.data_sub_agent import DataAnalysisResponse
        
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