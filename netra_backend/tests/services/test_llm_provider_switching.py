"""
Tests for LLM Manager provider switching and failover functionality
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
import time
from typing import Any, Dict, List

import pytest

# Add project root to path
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.tests.enhanced_llm_manager import EnhancedLLMManager
from netra_backend.tests.llm_manager_helpers import (
    assert_failure_count,
    assert_health_status,
    count_provider_usage,
    # Add project root to path
    create_mock_app_config,
    create_mock_providers,
    execute_concurrent_requests,
    make_providers_fail,
    register_providers_with_manager,
    simulate_provider_usage_pattern,
)


class TestLLMManagerProviderSwitching:
    """Test LLM manager provider switching functionality"""
    
    @pytest.fixture
    def mock_app_config(self):
        """Create mock app configuration"""
        return create_mock_app_config()
    
    @pytest.fixture
    def enhanced_llm_manager(self, mock_app_config):
        """Create enhanced LLM manager"""
        return EnhancedLLMManager(mock_app_config)
    
    @pytest.fixture
    def mock_providers(self, enhanced_llm_manager):
        """Setup mock providers"""
        providers = create_mock_providers()
        register_providers_with_manager(enhanced_llm_manager, providers)
        return providers
    
    def test_provider_registration(self, enhanced_llm_manager, mock_providers):
        """Test provider registration"""
        assert len(enhanced_llm_manager.provider_clients) == 3
        self._assert_all_providers_registered(enhanced_llm_manager)
        self._assert_all_providers_healthy(enhanced_llm_manager)
    
    def _assert_all_providers_registered(self, manager):
        """Assert all expected providers are registered"""
        expected_keys = ['openai_gpt-4', 'google_gemini-pro', 'anthropic_claude-3-sonnet']
        for key in expected_keys:
            assert key in manager.provider_clients
    
    def _assert_all_providers_healthy(self, manager):
        """Assert all providers are initially healthy"""
        for provider_key in manager.provider_health:
            assert_health_status(manager, provider_key, True)
    async def test_provider_health_check_success(self, enhanced_llm_manager, mock_providers):
        """Test successful provider health check"""
        provider_key = 'openai_gpt-4'
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        
        assert is_healthy == True
        assert_health_status(enhanced_llm_manager, provider_key, True)
        assert_failure_count(enhanced_llm_manager, provider_key, 0)
    async def test_provider_health_check_failure(self, enhanced_llm_manager, mock_providers):
        """Test provider health check failure"""
        provider_key = 'openai_gpt-4'
        make_providers_fail(mock_providers, ['openai_gpt4'])
        
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        
        assert is_healthy == False
        assert_health_status(enhanced_llm_manager, provider_key, False)
        self._assert_has_failure_recorded(enhanced_llm_manager, provider_key)
    
    def _assert_has_failure_recorded(self, manager, provider_key):
        """Assert failure was recorded"""
        health_info = manager.provider_health[provider_key]
        assert health_info['failure_count'] >= 1
        assert health_info['last_failure'] != None
    async def test_round_robin_provider_selection(self, enhanced_llm_manager, mock_providers):
        """Test round-robin provider selection"""
        enhanced_llm_manager.load_balancing['strategy'] = 'round_robin'
        
        providers = await self._get_providers_in_cycles(enhanced_llm_manager, 6)
        
        assert len(set(providers)) == 3  # All 3 providers used
        self._assert_round_robin_pattern(providers)
    
    async def _get_providers_in_cycles(self, manager, count):
        """Get providers in round-robin cycles"""
        providers = []
        for _ in range(count):
            provider = await manager.get_next_available_provider()
            providers.append(provider)
        return providers
    
    def _assert_round_robin_pattern(self, providers):
        """Assert round-robin pattern is maintained"""
        assert providers[0] == providers[3]
        assert providers[1] == providers[4]
        assert providers[2] == providers[5]
    async def test_failover_invoke_success(self, enhanced_llm_manager, mock_providers):
        """Test successful LLM invocation with failover"""
        prompt = "Test prompt for failover"
        
        result = await enhanced_llm_manager.invoke_with_failover(prompt)
        
        assert result != None
        assert "Response to: Test prompt" in result.content
    async def test_failover_invoke_preferred_provider(self, enhanced_llm_manager, mock_providers):
        """Test LLM invocation with preferred provider"""
        prompt = "Test prompt with preferred provider"
        preferred_provider = 'google_gemini-pro'
        
        result = await enhanced_llm_manager.invoke_with_failover(prompt, preferred_provider)
        
        assert result != None
        assert "[google]" in result.content.lower()
    async def test_failover_invoke_provider_failure(self, enhanced_llm_manager, mock_providers):
        """Test LLM invocation with provider failure and failover"""
        prompt = "Test prompt with failover"
        preferred_provider = 'openai_gpt-4'
        
        make_providers_fail(mock_providers, ['openai_gpt4'])
        result = await enhanced_llm_manager.invoke_with_failover(prompt, preferred_provider)
        
        assert result != None
        assert "[openai]" not in result.content.lower()
        self._assert_failure_recorded(enhanced_llm_manager, preferred_provider)
    
    def _assert_failure_recorded(self, manager, provider_key):
        """Assert failure was recorded for provider"""
        health_info = manager.provider_health[provider_key]
        assert health_info['failure_count'] > 0
    async def test_failover_all_providers_fail(self, enhanced_llm_manager, mock_providers):
        """Test behavior when all providers fail"""
        prompt = "Test prompt with all failures"
        make_providers_fail(mock_providers, list(mock_providers.keys()))
        
        with pytest.raises(NetraException) as exc_info:
            await enhanced_llm_manager.invoke_with_failover(prompt)
        
        assert "all llm providers failed" in str(exc_info.value).lower()
    async def test_provider_cooldown_period(self, enhanced_llm_manager, mock_providers):
        """Test provider cooldown period after failures"""
        provider_key = 'openai_gpt-4'
        enhanced_llm_manager.failover_config['cooldown_period'] = 1  # 1 second
        
        await self._trigger_provider_unhealthy_state(enhanced_llm_manager, mock_providers, provider_key)
        await self._verify_cooldown_behavior(enhanced_llm_manager, mock_providers, provider_key)
    
    async def _trigger_provider_unhealthy_state(self, manager, providers, provider_key):
        """Trigger provider to become unhealthy"""
        client = providers['openai_gpt4']
        client.should_fail = True
        
        for _ in range(manager.failover_config['max_failures']):
            try:
                await manager.invoke_with_failover("test", provider_key)
            except:
                pass
        
        assert_health_status(manager, provider_key, False)
    
    async def _verify_cooldown_behavior(self, manager, providers, provider_key):
        """Verify cooldown period behavior"""
        is_healthy = await manager.check_provider_health(provider_key)
        assert is_healthy == False  # Should not be available during cooldown
        
        await asyncio.sleep(1.1)  # Wait for cooldown period
        providers['openai_gpt4'].should_fail = False  # Fix provider
        
        is_healthy = await manager.check_provider_health(provider_key)
        assert is_healthy == True  # Should be healthy after cooldown
    async def test_concurrent_provider_switching(self, enhanced_llm_manager, mock_providers):
        """Test concurrent requests with provider switching"""
        self._setup_provider_response_times(mock_providers)
        
        results = await execute_concurrent_requests(enhanced_llm_manager, 20, "Concurrent request")
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 20
        self._assert_multiple_providers_used(successful_results)
    
    def _setup_provider_response_times(self, providers):
        """Setup different response times for providers"""
        providers['openai_gpt4'].response_time = 0.1
        providers['google_gemini'].response_time = 0.05
        providers['anthropic_claude'].response_time = 0.15
    
    def _assert_multiple_providers_used(self, results):
        """Assert multiple providers were used"""
        provider_usage = count_provider_usage(results)
        assert len(provider_usage) >= 2
    
    def test_provider_statistics_collection(self, enhanced_llm_manager, mock_providers):
        """Test provider statistics collection"""
        asyncio.run(simulate_provider_usage_pattern(enhanced_llm_manager, mock_providers))
        
        stats = enhanced_llm_manager.get_provider_statistics()
        
        assert len(stats) == 3
        self._assert_statistics_format(stats)
    
    def _assert_statistics_format(self, stats):
        """Assert statistics have correct format"""
        for provider_key, stat in stats.items():
            required_keys = [
                'provider', 'model_name', 'request_count', 
                'successful_requests', 'failed_requests', 
                'success_rate', 'health_status'
            ]
            for key in required_keys:
                assert key in stat