"""Real API Integration Tests.

Tests direct integration with real LLM APIs (OpenAI, Anthropic, Google).
NO MOCKS - all tests use actual API calls.

Business Value Justification (BVJ):
1. Segment: Enterprise ($347K+ MRR protection)
2. Business Goal: Validate LLM provider integrations work correctly
3. Value Impact: Ensures multi-provider AI optimization capabilities
4. Revenue Impact: Prevents integration failures that could lose customers
"""

import asyncio
import time
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.config import get_config
from shared.isolated_environment import get_env
from netra_backend.app.llm.llm_manager import LLMManager


@pytest.mark.real_llm
@pytest.mark.api_integration
@pytest.mark.e2e
class RealAPIIntegrationTests:
    """Test real LLM API integration across providers."""
    
    @pytest.mark.asyncio
    async def test_google_ai_integration(self, llm_manager, real_llm_test_manager):
        """Test real Google AI API integration."""
        # Validate configuration
        analysis_config = llm_manager.settings.llm_configs.get('analysis', {})
        has_api_key = bool(analysis_config and getattr(analysis_config, 'api_key', None))
        
        if not has_api_key:
            pytest.skip("Google AI API key not configured for analysis config")
            
        # Execute real API call
        prompt = "Analyze cost optimization for AI infrastructure (brief response)"
        timeout = real_llm_test_manager.get_llm_timeout()
        
        start_time = time.time()
        response = await asyncio.wait_for(
            llm_manager.ask_llm_full(prompt, "analysis"),
            timeout=timeout
        )
        execution_time = time.time() - start_time
        
        # Validate response
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        self._validate_api_response(response_dict, provider="google")
        
        # Record usage for cost tracking
        if "usage" in response_dict and "total_tokens" in response_dict["usage"]:
            tokens_used = response_dict["usage"]["total_tokens"]
            real_llm_test_manager.record_usage(tokens_used)
            assert real_llm_test_manager.validate_cost_limits(tokens_used)
        
        # Validate performance
        assert execution_time < 60.0, f"API call took {execution_time:.2f}s, exceeding 60s limit"
    
    @pytest.mark.asyncio
    async def test_default_model_integration(self, llm_manager, real_llm_test_manager):
        """Test real default model API integration."""
        # Validate configuration
        default_config = llm_manager.settings.llm_configs.get('default', {})
        has_api_key = bool(default_config and getattr(default_config, 'api_key', None))
        
        if not has_api_key:
            pytest.skip("Default model API key not configured")
            
        # Execute real API call
        prompt = "Provide infrastructure optimization recommendations (concise)"
        timeout = real_llm_test_manager.get_llm_timeout()
        
        start_time = time.time()
        response = await asyncio.wait_for(
            llm_manager.ask_llm_full(prompt, "default"),
            timeout=timeout
        )
        execution_time = time.time() - start_time
        
        # Validate response
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        self._validate_api_response(response_dict, provider="default")
        
        # Record usage
        if "usage" in response_dict and "total_tokens" in response_dict["usage"]:
            tokens_used = response_dict["usage"]["total_tokens"]
            real_llm_test_manager.record_usage(tokens_used)
        
        # Validate performance
        assert execution_time < 60.0, f"API call took {execution_time:.2f}s, exceeding 60s limit"
    
    @pytest.mark.asyncio
    async def test_triage_model_integration(self, llm_manager, real_llm_test_manager):
        """Test real triage model API integration for fast responses."""
        # Validate configuration
        triage_config = llm_manager.settings.llm_configs.get('triage', {})
        has_api_key = bool(triage_config and getattr(triage_config, 'api_key', None))
        
        if not has_api_key:
            pytest.skip("Triage model API key not configured")
            
        # Execute real API call
        prompt = "Quick analysis of system status"
        
        start_time = time.time()
        response = await llm_manager.ask_llm_full(prompt, "triage")
        execution_time = time.time() - start_time
        
        # Validate response
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        self._validate_api_response(response_dict, provider="triage")
        
        # Triage should be fast - stricter timeout
        assert execution_time < 30.0, f"Triage call took {execution_time:.2f}s, exceeding 30s limit"
    
    @pytest.mark.asyncio
    async def test_reporting_model_integration(self, llm_manager, real_llm_test_manager):
        """Test real reporting model API integration."""
        # Validate configuration
        reporting_config = llm_manager.settings.llm_configs.get('reporting', {})
        has_api_key = bool(reporting_config and getattr(reporting_config, 'api_key', None))
        
        if not has_api_key:
            pytest.skip("Reporting model API key not configured")
            
        # Execute real API call
        prompt = "Generate brief cost analysis report"
        
        response = await llm_manager.ask_llm_full(prompt, "reporting")
        
        # Validate response
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        self._validate_api_response(response_dict, provider="reporting")
    
    @pytest.mark.asyncio
    async def test_data_model_integration(self, llm_manager, real_llm_test_manager):
        """Test real data model API integration."""
        # Validate configuration
        data_config = llm_manager.settings.llm_configs.get('data', {})
        has_api_key = bool(data_config and getattr(data_config, 'api_key', None))
        
        if not has_api_key:
            pytest.skip("Data model API key not configured")
            
        # Execute real API call
        prompt = "Analyze data patterns for optimization"
        
        response = await llm_manager.ask_llm_full(prompt, "data")
        
        # Validate response
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        self._validate_api_response(response_dict, provider="data")
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, llm_manager, real_llm_test_manager):
        """Test concurrent real API calls across different configurations."""
        # Check available configurations
        available_configs = []
        for config_name in ["analysis", "default", "triage", "reporting", "data"]:
            config = llm_manager.settings.llm_configs.get(config_name, {})
            if config and getattr(config, 'api_key', None):
                available_configs.append(config_name)
        
        if len(available_configs) < 2:
            pytest.skip("Need at least 2 configured LLM configs for concurrent testing")
        
        # Use first 3 available configs
        test_configs = available_configs[:3]
        
        # Create concurrent tasks
        tasks = [
            self._execute_concurrent_call(llm_manager, config_name, i)
            for i, config_name in enumerate(test_configs)
        ]
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate results
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful) >= 2, f"Too many concurrent failures: {failed}"
        assert total_time < 90.0, f"Concurrent calls took {total_time:.2f}s, too slow"
        
        # Validate each successful response
        for result in successful:
            self._validate_api_response(result, provider="concurrent")
    
    @pytest.mark.asyncio 
    async def test_api_error_handling(self, llm_manager, real_llm_test_manager):
        """Test API error handling with invalid requests."""
        # Test with empty prompt
        with pytest.raises((ValueError, AssertionError)):
            await llm_manager.ask_llm_full("", "analysis")
        
        # Test with excessively long prompt (should be handled gracefully)
        long_prompt = "x" * 10000  # Very long prompt
        try:
            response = await asyncio.wait_for(
                llm_manager.ask_llm_full(long_prompt, "triage"),
                timeout=30
            )
            # If it doesn't raise, validate the response
            response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
            assert response_dict is not None
        except (asyncio.TimeoutError, ValueError, Exception) as e:
            # Expected - API should handle this gracefully
            assert "too long" in str(e).lower() or "timeout" in str(e).lower()
    
    # Helper methods
    
    async def _execute_concurrent_call(self, llm_manager, config_name: str, task_id: int):
        """Execute concurrent API call."""
        prompt = f"Concurrent analysis task {task_id} - brief response please"
        response = await llm_manager.ask_llm_full(prompt, config_name)
        return response.model_dump() if hasattr(response, 'model_dump') else response
    
    def _validate_api_response(self, response: Dict[str, Any], provider: str):
        """Validate API response structure and content."""
        assert response is not None, f"{provider} response is None"
        
        # Check for content in various possible formats
        has_content = (
            "content" in response or 
            "choices" in response or
            "text" in response or
            "message" in response
        )
        assert has_content, f"{provider} response missing content: {response}"
        
        # Check usage information if present
        if "usage" in response:
            usage = response["usage"]
            if isinstance(usage, dict) and "total_tokens" in usage:
                assert usage["total_tokens"] >= 0, f"{provider} invalid token count"
        
        # Validate response is not empty
        content = (
            response.get("content", "") or
            response.get("text", "") or
            (response.get("choices", [{}])[0].get("message", {}).get("content", "") if response.get("choices") else "") or
            str(response.get("message", ""))
        )
        
        assert len(content.strip()) > 0, f"{provider} response content is empty"
        assert len(content.strip()) > 10, f"{provider} response too short: '{content[:50]}...'"


@pytest.mark.real_llm
@pytest.mark.api_integration
@pytest.mark.e2e
class APIProviderSpecificTests:
    """Test provider-specific API features."""
    
    @pytest.mark.asyncio
    async def test_google_ai_specific_features(self, llm_manager, real_llm_test_manager):
        """Test Google AI specific features and capabilities."""
        # Skip if Google AI not available
        env = get_env()
        if not env.get("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not available for Google AI testing")
        
        # Test structured prompt
        prompt = """
        Analyze the following for cost optimization:
        - Infrastructure costs
        - API usage patterns
        - Resource allocation
        
        Provide a brief structured response.
        """
        
        response = await llm_manager.ask_llm_full(prompt, "analysis")
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        
        # Validate structured response
        content = self._extract_content(response_dict)
        assert "cost" in content.lower(), "Response should mention cost"
        assert len(content.split('\n')) > 1, "Response should be structured"
    
    def _extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from response regardless of format."""
        return (
            response.get("content", "") or
            response.get("text", "") or
            (response.get("choices", [{}])[0].get("message", {}).get("content", "") if response.get("choices") else "") or
            str(response.get("message", ""))
        )
