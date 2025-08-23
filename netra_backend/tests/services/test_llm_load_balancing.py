"""
Tests for LLM Manager load balancing strategies
Refactored to comply with 25-line function limit and 450-line file limit
"""

import asyncio
import os
import time
from typing import Any, Dict, List

import pytest

from netra_backend.app.schemas.Config import AppConfig
from netra_backend.tests.helpers.enhanced_llm_manager import EnhancedLLMManager
from netra_backend.tests.helpers.llm_manager_helpers import (
    LLMProvider,
    count_provider_usage,
    execute_concurrent_requests,
    setup_weighted_load_balancing,
)
from netra_backend.tests.helpers.llm_mock_clients import MockLLMClient

class TestLLMManagerLoadBalancing:
    """Test LLM manager load balancing strategies"""
    
    @pytest.fixture
    def load_balanced_manager(self):
        """Create LLM manager configured for load balancing testing"""
        config = self._create_load_balancing_config()
        manager = EnhancedLLMManager(config)
        
        providers = self._create_load_balancing_providers()
        self._register_load_balancing_providers(manager, providers)
        
        return manager, dict(providers)
    
    def _create_load_balancing_config(self) -> AppConfig:
        """Create configuration for load balancing tests"""
        config = AppConfig()
        config.environment = "testing"
        
        # Detect real LLM environment
        config.dev_mode_llm_enabled = self._detect_real_llm_environment()
        
        return config
    
    def _detect_real_llm_environment(self) -> bool:
        """Detect if real LLM environment is available"""
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        return any(os.getenv(key) for key in api_keys)
    
    def _create_load_balancing_providers(self) -> List[tuple]:
        """Create providers with different capabilities"""
        return [
            ('FAST_openai', MockLLMClient(LLMProvider.OPENAI, 'gpt-3.5-turbo')),
            ('SLOW_openai', MockLLMClient(LLMProvider.OPENAI, 'gpt-4')),
            ('FAST_google', MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro')),
        ]
    
    def _register_load_balancing_providers(self, manager, providers):
        """Register providers and set response times"""
        self._set_provider_response_times(providers)
        
        for key, client in providers:
            provider_enum = LLMProvider(key.split('_')[1])
            manager.register_provider_client(provider_enum, client.model_name, client)
    
    def _set_provider_response_times(self, providers):
        """Set different response times for providers"""
        response_times = [0.05, 0.2, 0.1]  # Fast, Slow, Medium
        for (key, client), time_val in zip(providers, response_times):
            client.response_time = time_val
    async def test_weighted_provider_selection(self, load_balanced_manager):
        """Test weighted provider selection"""
        manager, providers = load_balanced_manager
        
        weights = self._create_weighted_config()
        setup_weighted_load_balancing(manager, weights)
        
        provider_usage = await self._test_weighted_distribution(manager, 100)
        self._assert_weighted_distribution(provider_usage)
    
    def _create_weighted_config(self) -> Dict[str, float]:
        """Create weighted configuration"""
        return {
            'OPENAI_gpt-3.5-turbo': 4.0,  # Fast provider
            'openai_gpt-4': 1.0,          # Slow provider  
            'google_gemini-pro': 2.0      # Medium provider
        }
    
    async def _test_weighted_distribution(self, manager, count: int) -> Dict[str, int]:
        """Test provider distribution with weights"""
        results = await execute_concurrent_requests(manager, count, "Weighted test")
        return count_provider_usage(results)
    
    def _assert_weighted_distribution(self, usage: Dict[str, int]):
        """Assert providers used according to weights"""
        openai_count = usage.get('openai', 0)
        total_others = sum(count for key, count in usage.items() if key != 'openai')
        
        # OpenAI should have roughly 60% (4/7) of selections
        assert openai_count > total_others * 0.4  # Allow variance
    async def test_response_time_based_load_balancing(self, load_balanced_manager):
        """Test load balancing based on provider response times"""
        manager, providers = load_balanced_manager
        
        self._configure_response_time_weights(manager)
        
        start_time = time.time()
        results = await execute_concurrent_requests(manager, 30, "Load balance test")
        total_time = time.time() - start_time
        
        self._assert_load_balanced_performance(results, total_time)
    
    def _configure_response_time_weights(self, manager):
        """Configure weights based on inverse response time"""
        setup_weighted_load_balancing(manager, {
            'OPENAI_gpt-3.5-turbo': 4.0,  # Fast provider
            'openai_gpt-4': 1.0,          # Slow provider
            'google_gemini-pro': 2.0      # Medium provider
        })
    
    def _assert_load_balanced_performance(self, results, total_time):
        """Assert load balancing improves performance"""
        provider_usage = count_provider_usage(results)
        assert len(results) == 30
        assert total_time < 2.0  # Should complete quickly due to load balancing
    async def test_adaptive_load_balancing(self, load_balanced_manager):
        """Test adaptive load balancing based on success rates"""
        manager, providers = load_balanced_manager
        
        self._setup_failing_provider(providers)
        self._configure_initial_equal_weights(manager)
        
        successes = await self._test_adaptive_behavior(manager, 30)
        self._assert_adaptive_behavior(providers, successes)
    
    def _setup_failing_provider(self, providers):
        """Make one provider intermittently fail"""
        providers['SLOW_openai'].failure_rate = 0.3  # 30% failure rate
    
    def _configure_initial_equal_weights(self, manager):
        """Configure initial equal weights"""
        setup_weighted_load_balancing(manager, {
            'openai_gpt-3.5-turbo': 1.0,
            'openai_gpt-4': 1.0,
            'google_gemini-pro': 1.0
        })
    
    async def _test_adaptive_behavior(self, manager, count: int) -> int:
        """Test adaptive behavior with failing provider"""
        successes = 0
        for i in range(count):
            try:
                await manager.invoke_with_failover(f"Adaptive test {i}")
                successes += 1
            except:
                pass  # Some failures expected
        return successes
    
    def _assert_adaptive_behavior(self, providers, successes):
        """Assert adaptive behavior works correctly"""
        # Most requests should succeed despite one provider having failures
        assert successes >= 20  # At least 2/3 should succeed with failover
        
        # Check that the failing provider has recorded failures
        slow_provider_client = providers['SLOW_openai']
        assert slow_provider_client.failed_requests > 0
    async def test_geographic_load_balancing(self, load_balanced_manager):
        """Test geographic/regional load balancing simulation"""
        manager, providers = load_balanced_manager
        
        geographic_latencies = self._setup_geographic_latencies(providers)
        self._configure_latency_based_weights(manager, geographic_latencies)
        
        avg_time = await self._test_geographic_performance(manager, 20)
        self._assert_geographic_performance(avg_time)
    
    def _setup_geographic_latencies(self, providers) -> Dict[str, float]:
        """Setup geographic latencies simulation"""
        latencies = {
            'OPENAI_gpt-3.5-turbo': 0.05,  # US East
            'openai_gpt-4': 0.15,          # US West  
            'google_gemini-pro': 0.08      # EU
        }
        
        for key, client in providers.items():
            provider_key = self._build_provider_key(client)
            if provider_key in latencies:
                client.response_time = latencies[provider_key]
        
        return latencies
    
    def _build_provider_key(self, client) -> str:
        """Build provider key for latency mapping"""
        if client.provider == LLMProvider.OPENAI:
            return f"OPENAI_{client.model_name}"
        return f"GOOGLE_{client.model_name}"
    
    def _configure_latency_based_weights(self, manager, latencies: Dict[str, float]):
        """Configure weights based on latency"""
        weights = {key: 1.0 / latency for key, latency in latencies.items()}
        setup_weighted_load_balancing(manager, weights)
    
    async def _test_geographic_performance(self, manager, count: int) -> float:
        """Test geographic performance optimization"""
        start_time = time.time()
        
        results = await execute_concurrent_requests(manager, count, "Geographic test")
        
        total_time = time.time() - start_time
        return total_time / len(results)
    
    def _assert_geographic_performance(self, avg_time_per_request: float):
        """Assert geographic optimization works"""
        # Should prefer lower latency providers
        assert avg_time_per_request < 0.15  # Should be closer to fastest provider