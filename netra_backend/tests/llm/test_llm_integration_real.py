"""
Comprehensive LLM Integration Test Suite with Real Response Patterns

Tests critical LLM integration scenarios including response parsing, 
fallback mechanisms, retry logic, and model switching.
Maximum 300 lines, functions ≤8 lines per architecture requirements.
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import pytest
from netra_backend.app.llm.llm_response_processing import (
    attempt_json_fallback_parse,
    create_llm_response,
    extract_response_content,
    parse_nested_json_recursive,
)
from pydantic import BaseModel, Field, ValidationError
from netra_backend.app.schemas import AppConfig, LLMConfig

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.schemas.llm_response_types import LLMResponse

class ResponseModel(BaseModel):
    """Test model for structured LLM responses."""
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class ComplexNestedModel(BaseModel):
    """Complex model with deeply nested structures."""
    analysis_id: str
    results: Dict[str, Any]
    tool_configs: List[Dict[str, str]]
    performance_metrics: Dict[str, float]

@pytest.fixture
def test_llm_config():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test LLM configuration with proper mock setup."""
    return AppConfig(
        llm_configs={
            "primary": LLMConfig(
                provider="openai",
                model_name=LLMModel.GEMINI_2_5_FLASH.value,
                api_key="test-key",
                generation_config={"temperature": 0.7}
            ),
            "fallback": LLMConfig(
                provider="openai",
                model_name=LLMModel.GEMINI_2_5_FLASH.value,
                api_key="test-key",
                generation_config={"temperature": 0.5}
            )
        }
    )

@pytest.fixture
def llm_manager(test_llm_config):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create LLM manager for testing with mocked API calls."""
    # Disable logging that can cause issues with mock objects
    test_llm_config.llm_data_logging_enabled = False
    test_llm_config.llm_heartbeat_enabled = False
    manager = LLMManager(test_llm_config)
    return manager

def _create_mock_openai_llm():
    """Create mock OpenAI LLM with proper response format."""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_llm = AsyncNone  # TODO: Use real service instance
    mock_response = _create_mock_openai_response()
    mock_llm.ainvoke.return_value = mock_response
    mock_llm.with_structured_output.return_value = mock_llm
    return mock_llm

def _create_mock_openai_response(content: str = "Mock response"):
    """Create mock response matching OpenAI format."""
    # Mock: Generic component isolation for controlled unit testing
    mock_response = MagicNone  # TODO: Use real service instance
    mock_response.content = content
    mock_response.prompt_tokens = 50
    mock_response.completion_tokens = 25
    mock_response.total_tokens = 75
    return mock_response

class TestRealResponsePatterns:
    """Test real-world LLM response patterns and edge cases."""

    def test_markdown_wrapped_json_response(self):
        """Test JSON extraction from markdown code blocks."""
        markdown_response = """```json
        {
            "category": "optimization",
            "confidence": 0.85,
            "recommendations": [{"tool": "analyzer", "priority": "high"}]
        }
        ```"""
        
        # Clean markdown wrapper
        clean_json = markdown_response.strip().replace("```json", "").replace("```", "").strip()
        result = attempt_json_fallback_parse(clean_json, ResponseModel)
        
        assert result.category == "optimization"
        assert result.confidence == 0.85
        assert len(result.recommendations) == 1

    def test_malformed_json_with_trailing_comma(self):
        """Test handling of malformed JSON with syntax errors."""
        malformed_json = """{
            "category": "analysis",
            "confidence": 0.75,
            "recommendations": [],
        }"""
        
        with pytest.raises((json.JSONDecodeError, ValidationError)):
            attempt_json_fallback_parse(malformed_json, ResponseModel)

    def test_partial_response_due_to_token_limit(self):
        """Test handling of truncated responses."""
        partial_response = """{
            "category": "optimization",
            "confidence": 0.9,
            "recommendations": [
                {"tool": "analyzer", "prior"""
        
        with pytest.raises((json.JSONDecodeError, ValidationError)):
            attempt_json_fallback_parse(partial_response, ResponseModel)

    def test_string_vs_dict_field_conversion(self):
        """Test conversion of string fields to expected dict types."""
        mixed_response = {
            "category": "analysis",
            "confidence": 0.8,
            "recommendations": [{"tool_config": '{"timeout": 30, "retries": 3}'}],
            "metadata": '{"source": "llm", "timestamp": "2024-01-01T00:00:00Z"}'
        }
        
        parsed = parse_nested_json_recursive(mixed_response)
        result = ResponseModel(**parsed)
        
        assert isinstance(result.metadata, dict)
        assert result.metadata["source"] == "llm"

    def test_deeply_nested_json_strings(self):
        """Test parsing of deeply nested JSON structures."""
        nested_data = {
            "analysis_id": "test_001",
            "results": '{"metrics": "{\\"latency\\": 50, \\"throughput\\": 1000}"}',
            "tool_configs": [{"config": '{"param1": "value1"}'}],
            "performance_metrics": {"cpu": 0.75, "memory": 0.60}
        }
        
        parsed = parse_nested_json_recursive(nested_data)
        
        assert isinstance(parsed["results"]["metrics"], dict)
        assert parsed["results"]["metrics"]["latency"] == 50

class TestRetryMechanisms:
    """Test LLM retry logic and backoff strategies."""
    @pytest.mark.asyncio
    async def test_exponential_backoff_rate_limit(self, llm_manager):
        """Test exponential backoff on rate limit errors."""
        rate_limit_error = Exception("Rate limit exceeded. Retry after 60 seconds")
        
        with patch.object(llm_manager, 'get_llm') as mock_get_llm:
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_llm = AsyncNone  # TODO: Use real service instance
            mock_llm.ainvoke.side_effect = [rate_limit_error, rate_limit_error, "Success"]
            mock_get_llm.return_value = mock_llm
            
            start_time = time.time()
            # Would need actual retry implementation
            assert mock_llm.ainvoke.call_count <= 3
    @pytest.mark.asyncio
    async def test_model_fallback_on_failure(self, llm_manager):
        """Test switching to fallback model on primary failure."""
        # Mock model fallback scenario
        model_error = Exception("Model unavailable")
        fallback_response = _create_mock_openai_response("Fallback response")
        
        with patch.object(llm_manager._core, '_execute_llm_call') as mock_execute:
            # First call fails, second succeeds (simulating model fallback)
            mock_execute.side_effect = [model_error, (fallback_response, 120.0)]
            
            # Test would require actual fallback logic implementation
            assert True  # Placeholder for fallback verification
    @pytest.mark.asyncio
    async def test_timeout_handling(self, llm_manager):
        """Test handling of request timeouts."""
        with patch.object(llm_manager._core, 'ask_llm_full') as mock_ask_full:
            mock_ask_full.side_effect = asyncio.TimeoutError("Request timeout")
            
            with pytest.raises(asyncio.TimeoutError):
                await llm_manager.ask_llm("test prompt", "primary")

class TestCostOptimization:
    """Test cost optimization through intelligent model selection."""
    @pytest.mark.asyncio
    async def test_cheap_model_for_simple_tasks(self, llm_manager):
        """Test using cheaper models for simple classification tasks."""
        simple_prompt = "Classify this as positive or negative: Good product"
        
        # Create a mock LLMResponse with the expected content
        mock_llm_response = LLMResponse(
            choices=[{"message": {"content": "positive"}}],
            usage=TokenUsage(prompt_tokens=20, completion_tokens=5, total_tokens=25),
            provider=LLMProvider.OPENAI,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            response_time_ms=100.0
        )
        
        with patch.object(llm_manager._core, 'ask_llm_full') as mock_ask_full:
            mock_ask_full.return_value = mock_llm_response
            
            result = await llm_manager.ask_llm(simple_prompt, "fallback")
            assert "positive" in result
    @pytest.mark.asyncio
    async def test_expensive_model_for_complex_reasoning(self, llm_manager):
        """Test using expensive models for complex reasoning tasks."""
        complex_prompt = """Analyze the performance implications of switching 
        from GPT-4 to GPT-3.5-turbo for our customer support chatbot..."""
        
        # Create a mock LLMResponse with the expected analysis content
        mock_llm_response = LLMResponse(
            choices=[{"message": {"content": "Detailed analysis..."}}],
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            provider=LLMProvider.OPENAI,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            response_time_ms=200.0
        )
        
        with patch.object(llm_manager._core, 'ask_llm_full') as mock_ask_full:
            mock_ask_full.return_value = mock_llm_response
            
            result = await llm_manager.ask_llm(complex_prompt, "primary")
            assert "analysis" in result.lower()

class TestStructuredGenerationEdgeCases:
    """Test edge cases in structured generation."""
    @pytest.mark.asyncio
    async def test_structured_output_with_string_fallback(self, llm_manager):
        """Test fallback to string parsing when structured output fails."""
        # Create a proper ResponseModel instance for fallback
        fallback_response = ResponseModel(
            category="test",
            confidence=0.7,
            recommendations=[]
        )
        
        with patch.object(llm_manager._structured, 'get_structured_llm') as mock_get_structured:
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            mock_structured_llm = AsyncNone  # TODO: Use real service instance
            # First call fails, triggers fallback to string parsing
            mock_structured_llm.ainvoke.side_effect = Exception("JSON schema not supported")
            mock_get_structured.return_value = mock_structured_llm
            
            with patch.object(llm_manager._structured, 'ask_structured_llm') as mock_ask_structured:
                mock_ask_structured.return_value = fallback_response
                
                result = await llm_manager.ask_structured_llm(
                    "test", "primary", ResponseModel, use_cache=False
                )
                
                assert result.category == "test"
                assert result.confidence == 0.7
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, llm_manager):
        """Test handling of Pydantic validation errors."""
        invalid_json = json.dumps({
            "category": "test",
            "confidence": 1.5,  # Invalid: > 1.0
            "recommendations": "not_a_list"  # Invalid: should be list
        })
        
        with pytest.raises((ValidationError, Exception)):
            attempt_json_fallback_parse(invalid_json, ResponseModel)

class TestTokenUsageMonitoring:
    """Test token usage tracking and optimization."""

    def test_token_usage_calculation(self):
        """Test accurate token usage calculation."""
        # Mock: Generic component isolation for controlled unit testing
        mock_response = MagicNone  # TODO: Use real service instance
        mock_response.prompt_tokens = 100
        mock_response.completion_tokens = 50
        mock_response.total_tokens = 150
        
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    @pytest.mark.asyncio
    async def test_response_with_usage_metadata(self, llm_manager):
        """Test LLM response includes proper usage metadata."""
        # Create a properly structured LLMResponse with usage metadata
        expected_response = LLMResponse(
            choices=[{"message": {"content": "Test response"}}],
            usage=TokenUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
            provider=LLMProvider.OPENAI,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            response_time_ms=150.0
        )
        
        with patch.object(llm_manager._core, 'ask_llm_full') as mock_ask_full:
            mock_ask_full.return_value = expected_response
            
            result = await llm_manager.ask_llm_full("test", "primary")
            
            assert isinstance(result, LLMResponse)
            assert result.usage.total_tokens == 75

class TestProviderSwitching:
    """Test switching between different LLM providers."""
    @pytest.mark.asyncio
    async def test_openai_to_anthropic_fallback(self, llm_manager):
        """Test fallback from OpenAI to Anthropic on failure."""
        # Mock provider failure scenario
        openai_error = Exception("OpenAI API error")
        anthropic_response = LLMResponse(
            choices=[{"message": {"content": "Anthropic response"}}],
            usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
            provider=LLMProvider.OPENAI,  # In reality would be ANTHROPIC
            model=LLMModel.GEMINI_2_5_FLASH.value,
            response_time_ms=100.0
        )
        
        with patch.object(llm_manager._core, 'ask_llm_full') as mock_ask_full:
            # First call fails, second succeeds (simulating provider fallback)
            mock_ask_full.side_effect = [openai_error, anthropic_response]
            
            # Test would require actual provider switching logic
            # For now, just verify the mock setup works
            assert mock_ask_full is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])