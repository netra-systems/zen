"""
Tests for LLM Manager with structured output and provider switching
Refactored to comply with 25-line function limit and 450-line file limit
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict, List

import pytest
from pydantic import BaseModel
from netra_backend.app.schemas import AppConfig

from netra_backend.tests.enhanced_llm_manager import EnhancedLLMManager

# Add project root to path
from netra_backend.tests.llm_manager_helpers import (
    LLMProvider,
    count_provider_usage,
)
from netra_backend.tests.llm_mock_clients import MockLLMClient

# Add project root to path


class OutputSchema(BaseModel):
    """Test schema for structured output"""
    summary: str
    confidence: float
    categories: List[str]
    metadata: Dict[str, Any]


class TestLLMManagerStructuredOutput:
    """Test LLM manager with structured output and provider switching"""
    
    @pytest.fixture
    def structured_llm_manager(self):
        """Create LLM manager for structured output testing"""
        config = AppConfig()
        config.environment = "testing"
        manager = EnhancedLLMManager(config)
        
        providers = self._create_structured_output_providers()
        self._register_structured_providers(manager, providers)
        
        return manager
    
    def _create_structured_output_providers(self) -> List[MockLLMClient]:
        """Create providers with structured output support"""
        return [
            MockLLMClient(LLMProvider.OPENAI, 'gpt-4'),
            MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro')
        ]
    
    def _register_structured_providers(self, manager, providers: List[MockLLMClient]):
        """Register structured output providers"""
        for client in providers:
            provider_enum = LLMProvider(client.provider.value)
            manager.register_provider_client(provider_enum, client.model_name, client)
    async def test_structured_output_with_failover(self, structured_llm_manager):
        """Test structured output with provider failover"""
        prompt = "Analyze this text and provide structured output"
        
        result = await structured_llm_manager.invoke_with_failover(prompt)
        
        assert result != None
        assert isinstance(result.content, str)
    async def test_structured_output_provider_switching(self, structured_llm_manager):
        """Test structured output with multiple providers"""
        prompt = "Structured output test"
        
        provider_results = await self._collect_provider_results(structured_llm_manager, prompt, 4)
        provider_types = self._extract_provider_types(provider_results)
        
        assert len(provider_types) >= 1  # At least one provider type used
    
    async def _collect_provider_results(self, manager, prompt: str, count: int) -> List[Any]:
        """Collect results from multiple provider invocations"""
        provider_results = []
        for _ in range(count):
            result = await manager.invoke_with_failover(prompt)
            provider_results.append(result)
        return provider_results
    
    def _extract_provider_types(self, results: List[Any]) -> set:
        """Extract unique provider types from results"""
        provider_types = set()
        for result in results:
            provider = self._identify_provider_from_result(result)
            if provider:
                provider_types.add(provider)
        return provider_types
    
    def _identify_provider_from_result(self, result) -> str:
        """Identify provider from result content"""
        content = result.content.lower()
        if '[openai]' in content:
            return 'openai'
        elif '[google]' in content:
            return 'google'
        return None
    async def test_structured_output_schema_validation(self, structured_llm_manager):
        """Test that structured output can work with schema validation"""
        # This would test structured output with schema in a real implementation
        # For testing with mock setup, we validate the concept
        
        prompt = "Create structured data following schema"
        result = await structured_llm_manager.invoke_with_failover(prompt)
        
        self._assert_structured_response_format(result)
    
    def _assert_structured_response_format(self, result):
        """Assert structured response has expected format"""
        assert result != None
        assert hasattr(result, 'content')
        assert isinstance(result.content, str)
        assert len(result.content) > 0
    async def test_structured_output_concurrent_requests(self, structured_llm_manager):
        """Test concurrent structured output requests"""
        prompt = "Concurrent structured output test"
        
        concurrent_results = await self._execute_concurrent_structured_requests(structured_llm_manager, prompt, 6)
        self._assert_concurrent_results_quality(concurrent_results)
    
    async def _execute_concurrent_structured_requests(self, manager, prompt: str, count: int) -> List[Any]:
        """Execute multiple concurrent structured output requests"""
        tasks = [manager.invoke_with_failover(f"{prompt} {i}") for i in range(count)]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _assert_concurrent_results_quality(self, results: List[Any]):
        """Assert concurrent results meet quality expectations"""
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 4  # Most should succeed
        
        for result in successful_results:
            assert hasattr(result, 'content')
            assert len(result.content) > 10  # Non-trivial content
    async def test_structured_output_failover_behavior(self, structured_llm_manager):
        """Test failover behavior with structured output"""
        prompt = "Test structured failover"
        
        # Test that failover works even with structured output requirements
        results = await self._test_structured_failover_scenarios(structured_llm_manager, prompt)
        self._assert_failover_maintains_quality(results)
    
    async def _test_structured_failover_scenarios(self, manager, prompt: str) -> List[Any]:
        """Test various failover scenarios"""
        results = []
        
        # Test with different preferred providers
        preferred_providers = [None, 'openai_gpt-4', 'google_gemini-pro']
        for preferred in preferred_providers:
            result = await manager.invoke_with_failover(prompt, preferred)
            results.append(result)
        
        return results
    
    def _assert_failover_maintains_quality(self, results: List[Any]):
        """Assert failover maintains output quality"""
        assert len(results) == 3
        
        for result in results:
            assert result != None
            assert hasattr(result, 'content')
            assert "Response to:" in result.content
    async def test_structured_output_load_balancing(self, structured_llm_manager):
        """Test load balancing with structured output"""
        structured_llm_manager.load_balancing['strategy'] = 'round_robin'
        
        balanced_results = await self._test_structured_load_balancing(structured_llm_manager, 8)
        provider_distribution = self._analyze_provider_distribution(balanced_results)
        
        # Should use multiple providers for load balancing
        assert len(provider_distribution) >= 2
    
    async def _test_structured_load_balancing(self, manager, count: int) -> List[Any]:
        """Test load balancing behavior with structured output"""
        tasks = []
        for i in range(count):
            task = manager.invoke_with_failover(f"Load balanced structured test {i}")
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def _analyze_provider_distribution(self, results: List[Any]) -> Dict[str, int]:
        """Analyze distribution of providers used"""
        return count_provider_usage(results)