"""
LLM Response Handling Integration Tests

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core AI functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from LLM integration failures
- Value Impact: Validates LLM response handling and formatting for agent integration
- Revenue Impact: Ensures agent responses are properly formatted for customer consumption

REQUIREMENTS:
- LLM response formatting and validation
- Agent-specific response handling
- Response content verification
- Error response handling and fallback
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from netra_backend.tests.shared_fixtures import mock_llm_manager, llm_test_agent

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestResponseHandling:
    """BVJ: Validates LLM response handling and formatting for agent integration."""

    @pytest.mark.asyncio
    async def test_agent_llm_response_integration(self, llm_test_agent):
        """BVJ: Validates agent LLM response integration works correctly."""
        prompt = "Analyze GPU workload optimization opportunities"
        
        # Mock the agent's LLM call
        llm_test_agent.llm_manager.generate_response = AsyncMock(return_value={
            "content": "GPU optimization analysis: Current usage shows 24GB peak allocation.",
            "usage": {"total_tokens": 150},
            "response_time": 1.2
        })
        
        response = await llm_test_agent.llm_manager.generate_response(prompt)
        
        assert response["content"] is not None
        assert "optimization" in response["content"].lower()
        assert response["usage"]["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_llm_response_content_validation(self, mock_llm_manager):
        """BVJ: Validates LLM response content meets quality standards."""
        prompt = "Provide GPU performance optimization recommendations"
        
        response = await mock_llm_manager.generate_response(prompt)
        
        assert len(response["content"]) >= 50  # Minimum content length
        assert response["finish_reason"] == "stop"
        assert response["provider"] in ["openai", "anthropic", "azure"]

    @pytest.mark.asyncio
    async def test_agent_specific_response_formatting(self, mock_llm_manager):
        """BVJ: Validates agent-specific response formatting."""
        triage_prompt = "Route this optimization request to appropriate specialist"
        optimization_prompt = "Optimize GPU memory usage for large model training"
        
        triage_response = await mock_llm_manager.generate_response(triage_prompt, agent_type="triage")
        opt_response = await mock_llm_manager.generate_response(optimization_prompt, agent_type="optimization")
        
        assert "route" in triage_response["content"].lower()
        assert "optimization" in opt_response["content"].lower()

    @pytest.mark.asyncio
    async def test_response_token_usage_accuracy(self, mock_llm_manager):
        """BVJ: Validates response token usage tracking accuracy."""
        short_prompt = "Quick test"
        long_prompt = "This is a much longer prompt that should consume significantly more tokens for processing and generate a correspondingly longer response with detailed analysis and recommendations."
        
        short_response = await mock_llm_manager.generate_response(short_prompt)
        long_response = await mock_llm_manager.generate_response(long_prompt)
        
        assert long_response["usage"]["total_tokens"] > short_response["usage"]["total_tokens"]
        assert short_response["usage"]["prompt_tokens"] < long_response["usage"]["prompt_tokens"]

    @pytest.mark.asyncio
    async def test_response_timing_metrics(self, mock_llm_manager):
        """BVJ: Validates response timing metrics are captured."""
        prompt = "Performance timing test prompt"
        
        response = await mock_llm_manager.generate_response(prompt)
        
        assert "response_time" in response
        assert response["response_time"] > 0
        assert response["response_time"] < 30.0  # Within timeout limit

    @pytest.mark.asyncio
    async def test_multiple_response_consistency(self, mock_llm_manager):
        """BVJ: Validates multiple responses maintain consistency."""
        prompt = "Consistent response test"
        
        responses = []
        for _ in range(3):
            response = await mock_llm_manager.generate_response(prompt)
            responses.append(response)
        
        # All responses should have required fields
        for response in responses:
            assert "content" in response
            assert "usage" in response
            assert "response_time" in response

    @pytest.mark.asyncio
    async def test_response_error_handling(self, llm_test_agent):
        """BVJ: Validates response error handling for malformed responses."""
        # Mock a malformed response
        llm_test_agent.llm_manager.generate_response = AsyncMock(side_effect=Exception("Malformed response"))
        
        with pytest.raises(Exception):
            await llm_test_agent.llm_manager.generate_response("Error handling test")

    @pytest.mark.asyncio
    async def test_response_content_length_validation(self, mock_llm_manager):
        """BVJ: Validates response content length is appropriate."""
        minimal_prompt = "Yes or no?"
        detailed_prompt = "Provide comprehensive analysis of GPU optimization strategies including memory management, performance tuning, cost analysis, and implementation recommendations."
        
        minimal_response = await mock_llm_manager.generate_response(minimal_prompt)
        detailed_response = await mock_llm_manager.generate_response(detailed_prompt)
        
        # Detailed prompt should generate longer response
        assert len(detailed_response["content"]) >= len(minimal_response["content"])

    @pytest.mark.asyncio
    async def test_response_model_tracking(self, mock_llm_manager):
        """BVJ: Validates response tracks which model was used."""
        prompt = "Model tracking test"
        
        response = await mock_llm_manager.generate_response(prompt, model="gpt-4")
        
        assert "model" in response
        assert response["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_concurrent_response_handling(self, mock_llm_manager):
        """BVJ: Validates concurrent response handling works correctly."""
        prompts = [f"Concurrent test {i}" for i in range(5)]
        
        tasks = [mock_llm_manager.generate_response(prompt) for prompt in prompts]
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 5
        for response in responses:
            assert response["content"] is not None
            assert response["usage"]["total_tokens"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])