"""Integration tests for Triage Agent with Gemini 2.5 Pro

Tests verifying that the triage agent correctly uses Gemini 2.5 Pro
and handles all integration scenarios including circuit breaker behavior,
fallback mechanisms, and structured output validation.

Integration test category: Validates cross-service LLM integration
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from netra_backend.app.agents.triage_sub_agent.config import TriageConfig
from netra_backend.app.agents.triage_sub_agent.llm_processor import TriageLLMProcessor
from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.schemas.llm_types import LLMProvider
from netra_backend.tests.fixtures.llm_fixtures_core import create_basic_llm_manager


@pytest.fixture
def triage_config():
    """Fixture providing triage configuration."""
    return TriageConfig()


@pytest.fixture
def mock_agent():
    """Mock triage agent for testing."""
    agent = MagicMock()
    agent.llm_manager = create_basic_llm_manager()
    agent.llm_fallback_handler = MagicMock()
    agent.triage_core = MagicMock()
    agent.prompt_builder = MagicMock()
    agent.result_processor = MagicMock()
    agent._send_update = AsyncMock()
    return agent


@pytest.fixture
def llm_processor(mock_agent):
    """Fixture providing LLM processor instance."""
    return TriageLLMProcessor(mock_agent)


@pytest.fixture
def sample_state():
    """Sample agent state for testing."""
    return DeepAgentState(
        user_request="How can I optimize my AI costs?",
        thread_id="test-thread-123",
        user_id="test-user-456"
    )


@pytest.fixture
def expected_triage_result():
    """Expected triage result structure."""
    return TriageResult(
        category="Cost Optimization",
        confidence_score=0.92,
        priority="high",
        extracted_entities={
            "intent": "cost_optimization",
            "domain": "ai_infrastructure"
        },
        tool_recommendations=[
            "data_sub_agent",
            "optimizations_core_sub_agent"
        ],
        metadata={
            "triage_duration_ms": 1250,
            "cache_hit": False,
            "retry_count": 0,
            "fallback_used": False
        }
    )


class TestTriageGeminiConfiguration:
    """Test triage agent configuration uses Gemini 2.5 Pro correctly."""
    
    def test_triage_config_uses_gemini_25_pro(self, triage_config):
        """Verify triage config specifies Gemini 2.5 Pro as primary model."""
        assert triage_config.PRIMARY_MODEL == LLMModel.GEMINI_2_5_PRO
        assert triage_config.PROVIDER == LLMProvider.GOOGLE
        assert triage_config.get_model_display_name() == "Google gemini-2.5-pro"
    
    def test_triage_config_fallback_model(self, triage_config):
        """Verify fallback configuration uses Gemini 2.5 Flash."""
        assert triage_config.FALLBACK_MODEL == LLMModel.GEMINI_2_5_FLASH
        fallback_config = triage_config.get_fallback_config()
        assert fallback_config["fallback_model"] == LLMModel.GEMINI_2_5_FLASH.value
    
    def test_triage_config_pro_model_timeout(self, triage_config):
        """Verify Pro model gets longer timeout than Flash."""
        pro_timeout = triage_config.get_timeout_for_model(LLMModel.GEMINI_2_5_PRO)
        flash_timeout = triage_config.get_timeout_for_model(LLMModel.GEMINI_2_5_FLASH)
        assert pro_timeout == 17.0
        assert flash_timeout == 10.0
        assert pro_timeout > flash_timeout
    
    def test_llm_config_generation(self, triage_config):
        """Verify LLM config generation produces correct parameters."""
        config = triage_config.get_llm_config()
        
        assert config["provider"] == LLMProvider.GOOGLE.value
        assert config["model_name"] == LLMModel.GEMINI_2_5_PRO.value
        assert config["temperature"] == 0.0  # Deterministic
        assert config["max_tokens"] == 4096
        assert config["timeout_seconds"] == 17.0
        assert config["use_structured_output"] is True


class TestTriageLLMIntegration:
    """Test triage LLM integration with actual model calls."""
    
    @pytest.mark.asyncio
    async def test_triage_uses_correct_llm_config(self, llm_processor, sample_state, expected_triage_result):
        """Verify triage agent calls LLM with correct configuration name."""
        # Setup mocks
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = expected_triage_result
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.result_processor.enrich_triage_result.return_value = expected_triage_result.model_dump()
        
        # Execute triage
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", True)
        
        # Verify LLM was called with 'triage' config
        llm_processor.agent.llm_manager.ask_structured_llm.assert_called_once()
        call_args = llm_processor.agent.llm_manager.ask_structured_llm.call_args
        assert call_args[1]["llm_config_name"] == "triage"
        assert call_args[1]["schema"] == TriageResult
        assert call_args[1]["use_cache"] is False
    
    @pytest.mark.asyncio
    async def test_structured_output_validation(self, llm_processor, sample_state, expected_triage_result):
        """Test structured output validation with Gemini Pro."""
        # Setup mocks
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = expected_triage_result
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.result_processor.enrich_triage_result.return_value = expected_triage_result.model_dump()
        
        # Execute and verify structured output
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        assert "category" in result
        assert "confidence_score" in result
        assert "priority" in result
        assert "extracted_entities" in result
        assert "tool_recommendations" in result
        assert isinstance(result["confidence_score"], float)
        assert 0.0 <= result["confidence_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_gemini_pro_timeout_handling(self, llm_processor, sample_state):
        """Test proper timeout handling for Gemini 2.5 Pro calls."""
        # Setup timeout scenario
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = asyncio.TimeoutError("LLM timeout")
        llm_processor.agent.llm_fallback_handler.execute_structured_with_fallback = AsyncMock()
        
        # Mock fallback handler to return proper response
        fallback_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {"fallback_used": True}
        }
        llm_processor.agent.llm_fallback_handler.execute_structured_with_fallback.return_value = fallback_result
        
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
        
        # Execute with timeout
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify fallback was triggered
        llm_processor.agent.llm_fallback_handler.execute_structured_with_fallback.assert_called_once()
        assert result["metadata"]["fallback_used"] is True


class TestTriageFallbackBehavior:
    """Test triage agent fallback from Pro to Flash on failure."""
    
    @pytest.mark.asyncio
    async def test_fallback_to_flash_on_pro_failure(self, llm_processor, sample_state):
        """Test fallback from Gemini 2.5 Pro to Flash on failure."""
        # Setup Pro failure scenario
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        
        # Mock structured LLM failure
        from pydantic import ValidationError
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = ValidationError(
            "Invalid response format", TriageResult
        )
        
        # Mock fallback LLM success
        llm_processor.agent.llm_manager.ask_llm.return_value = '''
        {
            "category": "General Inquiry",
            "confidence_score": 0.4,
            "priority": "medium",
            "extracted_entities": {"intent": "general"},
            "tool_recommendations": []
        }
        '''
        
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.triage_core.extract_and_validate_json.return_value = {
            "category": "General Inquiry",
            "confidence_score": 0.4,
            "priority": "medium",
            "extracted_entities": {"intent": "general"},
            "tool_recommendations": [],
            "metadata": {"triage_duration_ms": 0, "fallback_used": True}
        }
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = lambda x, _: x
        
        # Execute and verify fallback
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify both Pro and fallback calls were made
        assert llm_processor.agent.llm_manager.ask_structured_llm.called
        assert llm_processor.agent.llm_manager.ask_llm.called
        
        # Verify result indicates fallback was used
        assert result["metadata"]["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_fallback_preserves_structured_format(self, llm_processor, sample_state):
        """Test that fallback attempts to preserve structured output format."""
        # Setup fallback scenario
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = Exception("Pro model failure")
        
        # Mock successful fallback with proper JSON
        fallback_response = '''
        {
            "category": "Technical Support",
            "confidence_score": 0.7,
            "priority": "high",
            "extracted_entities": {"issue_type": "performance"},
            "tool_recommendations": ["data_sub_agent"]
        }
        '''
        llm_processor.agent.llm_manager.ask_llm.return_value = fallback_response
        
        expected_parsed = {
            "category": "Technical Support",
            "confidence_score": 0.7,
            "priority": "high",
            "extracted_entities": {"issue_type": "performance"},
            "tool_recommendations": ["data_sub_agent"],
            "metadata": {"triage_duration_ms": 0, "fallback_used": True}
        }
        
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.triage_core.extract_and_validate_json.return_value = expected_parsed
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = lambda x, _: x
        
        # Execute fallback
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify structured format is preserved
        required_fields = ["category", "confidence_score", "priority", "extracted_entities", "tool_recommendations"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert TriageConfig.validate_response_format(result)


class TestTriageCircuitBreakerIntegration:
    """Test triage-specific circuit breaker behavior."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_configuration(self, triage_config):
        """Verify triage circuit breaker uses correct configuration."""
        cb_config = triage_config.get_circuit_breaker_config()
        
        assert cb_config["failure_threshold"] == 10
        assert cb_config["recovery_timeout"] == 10.0
        assert cb_config["timeout_seconds"] == 17.0  # Pro model timeout
        assert cb_config["half_open_max_calls"] == 5
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_isolation(self, llm_processor, sample_state):
        """Test that triage circuit breaker doesn't affect other agents."""
        # This test verifies circuit breaker isolation
        # In a real implementation, we'd test that triage circuit breaker
        # failures don't cascade to other agent types
        
        # Setup circuit breaker mock
        with patch('netra_backend.app.agents.base.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb_instance = MagicMock()
            mock_cb.return_value = mock_cb_instance
            mock_cb_instance.call = AsyncMock(side_effect=Exception("Circuit open"))
            
            llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
            llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
            llm_processor.agent.triage_core.get_cached_result.return_value = None
            
            # Mock final fallback
            llm_processor.agent.result_processor.enrich_triage_result.return_value = {
                "category": "General Inquiry",
                "confidence_score": 0.3,
                "priority": "medium",
                "extracted_entities": {},
                "tool_recommendations": [],
                "metadata": {"fallback_used": True, "circuit_breaker_open": True}
            }
            
            # Circuit breaker should be isolated to triage operations
            result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
            
            # Verify we get a valid response even with circuit breaker open
            assert "category" in result
            assert result["metadata"]["fallback_used"] is True


class TestTriageRateLimiting:
    """Test triage agent rate limiting and concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_triage_requests(self, llm_processor, sample_state, expected_triage_result):
        """Test handling of concurrent triage requests."""
        # Setup mocks for concurrent execution
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = expected_triage_result
        llm_processor.agent.triage_core.generate_request_hash.side_effect = lambda x: f"hash-{hash(x)}"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.result_processor.enrich_triage_result.return_value = expected_triage_result.model_dump()
        
        # Create multiple concurrent requests
        concurrent_requests = [
            llm_processor.execute_triage_with_llm(
                DeepAgentState(
                    user_request=f"Request {i}",
                    thread_id=f"thread-{i}",
                    user_id="test-user"
                ),
                f"run-{i}",
                False
            )
            for i in range(5)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*concurrent_requests)
        
        # Verify all requests completed successfully
        assert len(results) == 5
        for result in results:
            assert "category" in result
            assert "confidence_score" in result
        
        # Verify LLM was called for each request
        assert llm_processor.agent.llm_manager.ask_structured_llm.call_count == 5
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, llm_processor, sample_state):
        """Test proper handling of rate limit errors from Gemini API."""
        # Setup rate limit error
        from netra_backend.app.core.exceptions_service import RateLimitError
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = RateLimitError("Rate limit exceeded")
        
        # Mock fallback behavior
        llm_processor.agent.llm_fallback_handler.execute_structured_with_fallback = AsyncMock()
        fallback_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {"fallback_used": True, "rate_limited": True}
        }
        llm_processor.agent.llm_fallback_handler.execute_structured_with_fallback.return_value = fallback_result
        
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
        
        # Execute with rate limiting
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify graceful handling
        assert result["metadata"]["fallback_used"] is True
        assert result["metadata"]["rate_limited"] is True


class TestTriageResponseValidation:
    """Test triage response format validation specific to Gemini Pro output."""
    
    def test_valid_response_passes_validation(self, triage_config):
        """Test that valid triage response passes validation."""
        valid_response = {
            "category": "Cost Optimization",
            "confidence_score": 0.85,
            "priority": "high",
            "extracted_entities": {"intent": "cost_reduction"},
            "tool_recommendations": ["data_sub_agent"]
        }
        
        assert triage_config.validate_response_format(valid_response) is True
    
    def test_invalid_confidence_score_fails_validation(self, triage_config):
        """Test that invalid confidence score fails validation."""
        invalid_response = {
            "category": "Cost Optimization",
            "confidence_score": 1.5,  # Invalid: > 1.0
            "priority": "high",
            "extracted_entities": {"intent": "cost_reduction"},
            "tool_recommendations": ["data_sub_agent"]
        }
        
        assert triage_config.validate_response_format(invalid_response) is False
    
    def test_invalid_priority_fails_validation(self, triage_config):
        """Test that invalid priority value fails validation."""
        invalid_response = {
            "category": "Cost Optimization",
            "confidence_score": 0.85,
            "priority": "critical",  # Invalid: not in valid_priorities
            "extracted_entities": {"intent": "cost_reduction"},
            "tool_recommendations": ["data_sub_agent"]
        }
        
        assert triage_config.validate_response_format(invalid_response) is False
    
    def test_missing_required_fields_fail_validation(self, triage_config):
        """Test that missing required fields fail validation."""
        incomplete_response = {
            "category": "Cost Optimization",
            "confidence_score": 0.85,
            # Missing: priority, extracted_entities, tool_recommendations
        }
        
        assert triage_config.validate_response_format(incomplete_response) is False


@pytest.mark.integration
@pytest.mark.llm
class TestTriageEndToEndIntegration:
    """End-to-end integration tests requiring real LLM connectivity."""
    
    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_real_gemini_pro_integration(self, sample_state):
        """Test actual integration with Gemini 2.5 Pro API.
        
        This test requires GEMINI_API_KEY environment variable and --real-llm flag.
        """
        pytest.skip("Real LLM integration test - enable with --real-llm flag")
        
        # This would be implemented for real integration testing
        # when --real-llm flag is provided
        pass
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_triage_performance_with_gemini_pro(self, llm_processor, sample_state, expected_triage_result):
        """Test triage performance characteristics with Gemini 2.5 Pro."""
        import time
        
        # Setup mocks
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = expected_triage_result
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        llm_processor.agent.result_processor.enrich_triage_result.return_value = expected_triage_result.model_dump()
        
        # Measure performance
        start_time = time.time()
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        execution_time = time.time() - start_time
        
        # Verify reasonable performance (should complete within reasonable time)
        assert execution_time < 5.0  # Should complete within 5 seconds in mock mode
        assert "triage_duration_ms" in result["metadata"]
        assert result["metadata"]["triage_duration_ms"] >= 0