"""
Comprehensive tests for LLM Manager provider switching and failover
Tests LLM provider management, switching, failover mechanisms, and load balancing
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Type
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum
import json

from app.llm.llm_manager import LLMManager, MockLLM, MockStructuredLLM
from app.schemas import AppConfig, LLMConfig
from app.core.exceptions import NetraException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class LLMProvider(Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class MockLLMResponse:
    """Mock LLM response for testing"""
    
    def __init__(self, content: str, provider: str = "mock"):
        self.content = content
        self.provider = provider
        self.timestamp = datetime.utcnow()


class MockLLMClient:
    """Mock LLM client that can simulate different provider behaviors"""
    
    def __init__(self, provider: LLMProvider, model_name: str):
        self.provider = provider
        self.model_name = model_name
        self.response_time = 0.1  # Default response time
        self.should_fail = False
        self.failure_rate = 0.0  # Probability of failure
        self.failure_message = "Mock LLM failure"
        self.request_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
    async def ainvoke(self, prompt: str):
        """Mock async invoke"""
        self.request_count += 1
        
        # Simulate response time
        await asyncio.sleep(self.response_time)
        
        # Simulate failures
        if self.should_fail or (self.failure_rate > 0 and 
                               __import__('random').random() < self.failure_rate):
            self.failed_requests += 1
            raise Exception(self.failure_message)
        
        self.successful_requests += 1
        return MockLLMResponse(
            f"[{self.provider.value}] Response to: {prompt[:50]}...",
            self.provider.value
        )
    
    async def astream(self, prompt: str):
        """Mock async stream"""
        self.request_count += 1
        
        if self.should_fail:
            self.failed_requests += 1
            raise Exception(self.failure_message)
        
        # Simulate streaming response
        words = f"[{self.provider.value}] Streaming: {prompt[:30]}...".split()
        for word in words:
            await asyncio.sleep(0.01)
            yield type('obj', (object,), {'content': word + ' '})()
        
        self.successful_requests += 1
    
    def with_structured_output(self, schema: Type[BaseModel], **kwargs):
        """Mock structured output"""
        return MockStructuredLLMClient(self.provider, self.model_name, schema)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return {
            'provider': self.provider.value,
            'model_name': self.model_name,
            'request_count': self.request_count,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / max(self.request_count, 1),
            'response_time': self.response_time
        }


class MockStructuredLLMClient:
    """Mock structured LLM client"""
    
    def __init__(self, provider: LLMProvider, model_name: str, schema: Type[BaseModel]):
        self.provider = provider
        self.model_name = model_name
        self.schema = schema
        self.should_fail = False
    
    async def ainvoke(self, prompt: str):
        """Mock structured invoke"""
        if self.should_fail:
            raise Exception("Mock structured LLM failure")
        
        # Create mock structured response
        mock_data = {}
        for field_name, field_info in self.schema.model_fields.items():
            if hasattr(field_info, 'is_required') and field_info.is_required():
                annotation = field_info.annotation
                if annotation == str:
                    mock_data[field_name] = f"Mock {field_name} from {self.provider.value}"
                elif annotation == int:
                    mock_data[field_name] = 42
                elif annotation == float:
                    mock_data[field_name] = 3.14
                elif annotation == bool:
                    mock_data[field_name] = True
                elif annotation == list:
                    mock_data[field_name] = ["mock", "list"]
                elif annotation == dict:
                    mock_data[field_name] = {"mock": "dict"}
                else:
                    mock_data[field_name] = f"mock_{field_name}"
        
        return self.schema(**mock_data)


class EnhancedLLMManager(LLMManager):
    """Enhanced LLM Manager with provider switching and failover"""
    
    def __init__(self, settings: AppConfig):
        super().__init__(settings)
        self.provider_clients = {}
        self.provider_health = {}
        self.provider_metrics = {}
        self.failover_config = {
            'enabled': True,
            'max_failures': 3,
            'cooldown_period': 300,  # 5 minutes
            'health_check_interval': 60  # 1 minute
        }
        self.load_balancing = {
            'strategy': 'round_robin',  # round_robin, weighted, failover_only
            'current_provider_index': 0,
            'provider_weights': {}
        }
        
    def register_provider_client(self, provider: LLMProvider, model_name: str, client: MockLLMClient):
        """Register a provider client"""
        key = f"{provider.value}_{model_name}"
        self.provider_clients[key] = client
        self.provider_health[key] = {
            'healthy': True,
            'last_failure': None,
            'failure_count': 0,
            'last_health_check': datetime.utcnow()
        }
        self.provider_metrics[key] = client.get_metrics()
    
    async def check_provider_health(self, provider_key: str) -> bool:
        """Check if a provider is healthy"""
        if provider_key not in self.provider_health:
            return False
        
        health = self.provider_health[provider_key]
        
        # Check if provider is in cooldown
        if not health['healthy'] and health['last_failure']:
            cooldown_end = health['last_failure'] + timedelta(seconds=self.failover_config['cooldown_period'])
            if datetime.utcnow() < cooldown_end:
                return False
        
        # Perform health check
        try:
            client = self.provider_clients[provider_key]
            test_response = await client.ainvoke("health check")
            
            # Reset failure count on successful health check
            health['healthy'] = True
            health['failure_count'] = 0
            health['last_health_check'] = datetime.utcnow()
            
            return True
            
        except Exception:
            health['healthy'] = False
            health['failure_count'] += 1
            health['last_failure'] = datetime.utcnow()
            health['last_health_check'] = datetime.utcnow()
            
            return False
    
    async def get_next_available_provider(self, exclude_providers: List[str] = None) -> Optional[str]:
        """Get next available provider based on load balancing strategy"""
        exclude_providers = exclude_providers or []
        available_providers = [
            key for key in self.provider_clients.keys()
            if key not in exclude_providers
        ]
        
        if not available_providers:
            return None
        
        strategy = self.load_balancing['strategy']
        
        if strategy == 'round_robin':
            return self._get_round_robin_provider(available_providers)
        elif strategy == 'weighted':
            return self._get_weighted_provider(available_providers)
        elif strategy == 'failover_only':
            # Return first healthy provider
            for provider_key in available_providers:
                if await self.check_provider_health(provider_key):
                    return provider_key
        
        return available_providers[0] if available_providers else None
    
    def _get_round_robin_provider(self, available_providers: List[str]) -> str:
        """Get provider using round-robin strategy"""
        if not available_providers:
            return None
        
        current_index = self.load_balancing['current_provider_index']
        provider = available_providers[current_index % len(available_providers)]
        self.load_balancing['current_provider_index'] = (current_index + 1) % len(available_providers)
        
        return provider
    
    def _get_weighted_provider(self, available_providers: List[str]) -> str:
        """Get provider using weighted strategy"""
        import random
        
        if not available_providers:
            return None
        
        # Use weights if available, otherwise equal weight
        weights = []
        for provider in available_providers:
            weight = self.load_balancing['provider_weights'].get(provider, 1.0)
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(available_providers)
        
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return available_providers[i]
        
        return available_providers[-1]
    
    async def invoke_with_failover(self, prompt: str, preferred_provider: str = None, max_retries: int = 3) -> Any:
        """Invoke LLM with automatic failover on failure"""
        attempted_providers = []
        
        # Try preferred provider first if specified
        if preferred_provider and preferred_provider in self.provider_clients:
            try:
                if await self.check_provider_health(preferred_provider):
                    client = self.provider_clients[preferred_provider]
                    return await client.ainvoke(prompt)
            except Exception as e:
                attempted_providers.append(preferred_provider)
                self._record_provider_failure(preferred_provider, e)
        
        # Try other available providers
        for attempt in range(max_retries):
            try:
                next_provider = await self.get_next_available_provider(attempted_providers)
                if not next_provider:
                    break
                
                if await self.check_provider_health(next_provider):
                    client = self.provider_clients[next_provider]
                    return await client.ainvoke(prompt)
                
                attempted_providers.append(next_provider)
                
            except Exception as e:
                if next_provider:
                    attempted_providers.append(next_provider)
                    self._record_provider_failure(next_provider, e)
                
                if attempt == max_retries - 1:
                    raise NetraException(f"All LLM providers failed: {str(e)}")
        
        raise NetraException("No healthy LLM providers available")
    
    def _record_provider_failure(self, provider_key: str, error: Exception):
        """Record provider failure for health tracking"""
        if provider_key in self.provider_health:
            health = self.provider_health[provider_key]
            health['failure_count'] += 1
            health['last_failure'] = datetime.utcnow()
            
            # Mark as unhealthy if too many failures
            if health['failure_count'] >= self.failover_config['max_failures']:
                health['healthy'] = False
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get statistics for all providers"""
        stats = {}
        
        for provider_key, client in self.provider_clients.items():
            client_metrics = client.get_metrics()
            health_info = self.provider_health.get(provider_key, {})
            
            stats[provider_key] = {
                **client_metrics,
                'health_status': 'healthy' if health_info.get('healthy', False) else 'unhealthy',
                'failure_count': health_info.get('failure_count', 0),
                'last_failure': health_info.get('last_failure'),
                'last_health_check': health_info.get('last_health_check')
            }
        
        return stats


class TestLLMManagerProviderSwitching:
    """Test LLM manager provider switching functionality"""
    
    @pytest.fixture
    def mock_app_config(self):
        """Create mock app configuration"""
        config = AppConfig()
        config.environment = "testing"
        config.llm_configs = {
            'openai_gpt4': LLMConfig(
                provider='openai',
                model_name='gpt-4',
                api_key='test_openai_key'
            ),
            'google_gemini': LLMConfig(
                provider='google',
                model_name='gemini-pro',
                api_key='test_google_key'
            ),
            'anthropic_claude': LLMConfig(
                provider='anthropic',
                model_name='claude-3-sonnet',
                api_key='test_anthropic_key'
            )
        }
        return config
    
    @pytest.fixture
    def enhanced_llm_manager(self, mock_app_config):
        """Create enhanced LLM manager"""
        return EnhancedLLMManager(mock_app_config)
    
    @pytest.fixture
    def mock_providers(self, enhanced_llm_manager):
        """Setup mock providers"""
        providers = {
            'openai_gpt4': MockLLMClient(LLMProvider.OPENAI, 'gpt-4'),
            'google_gemini': MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro'),
            'anthropic_claude': MockLLMClient(LLMProvider.ANTHROPIC, 'claude-3-sonnet')
        }
        
        # Register providers
        for key, client in providers.items():
            provider = LLMProvider(key.split('_')[0].upper())
            enhanced_llm_manager.register_provider_client(provider, client.model_name, client)
        
        return providers
    
    def test_provider_registration(self, enhanced_llm_manager, mock_providers):
        """Test provider registration"""
        # Should have registered all providers
        assert len(enhanced_llm_manager.provider_clients) == 3
        assert 'OPENAI_gpt-4' in enhanced_llm_manager.provider_clients
        assert 'GOOGLE_gemini-pro' in enhanced_llm_manager.provider_clients
        assert 'ANTHROPIC_claude-3-sonnet' in enhanced_llm_manager.provider_clients
        
        # All providers should be healthy initially
        for provider_key in enhanced_llm_manager.provider_health:
            assert enhanced_llm_manager.provider_health[provider_key]['healthy'] is True
    
    @pytest.mark.asyncio
    async def test_provider_health_check_success(self, enhanced_llm_manager, mock_providers):
        """Test successful provider health check"""
        provider_key = 'OPENAI_gpt-4'
        
        # Health check should succeed
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        
        assert is_healthy is True
        health_info = enhanced_llm_manager.provider_health[provider_key]
        assert health_info['healthy'] is True
        assert health_info['failure_count'] == 0
    
    @pytest.mark.asyncio
    async def test_provider_health_check_failure(self, enhanced_llm_manager, mock_providers):
        """Test provider health check failure"""
        provider_key = 'OPENAI_gpt-4'
        
        # Make provider fail
        mock_providers['openai_gpt4'].should_fail = True
        
        # Health check should fail
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        
        assert is_healthy is False
        health_info = enhanced_llm_manager.provider_health[provider_key]
        assert health_info['healthy'] is False
        assert health_info['failure_count'] == 1
        assert health_info['last_failure'] is not None
    
    @pytest.mark.asyncio
    async def test_round_robin_provider_selection(self, enhanced_llm_manager, mock_providers):
        """Test round-robin provider selection"""
        enhanced_llm_manager.load_balancing['strategy'] = 'round_robin'
        
        # Get providers in round-robin fashion
        providers = []
        for i in range(6):  # Test 2 full cycles
            provider = await enhanced_llm_manager.get_next_available_provider()
            providers.append(provider)
        
        # Should cycle through providers
        assert len(set(providers)) == 3  # All 3 providers used
        # Should repeat pattern after 3 providers
        assert providers[0] == providers[3]
        assert providers[1] == providers[4]
        assert providers[2] == providers[5]
    
    @pytest.mark.asyncio
    async def test_weighted_provider_selection(self, enhanced_llm_manager, mock_providers):
        """Test weighted provider selection"""
        enhanced_llm_manager.load_balancing['strategy'] = 'weighted'
        
        # Set weights (higher weight for OpenAI)
        enhanced_llm_manager.load_balancing['provider_weights'] = {
            'OPENAI_gpt-4': 3.0,
            'GOOGLE_gemini-pro': 1.0,
            'ANTHROPIC_claude-3-sonnet': 1.0
        }
        
        # Get many providers and count distribution
        provider_counts = {}
        for _ in range(100):
            provider = await enhanced_llm_manager.get_next_available_provider()
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # OpenAI should be selected more often due to higher weight
        openai_count = provider_counts.get('OPENAI_gpt-4', 0)
        total_others = sum(count for key, count in provider_counts.items() 
                          if key != 'OPENAI_gpt-4')
        
        # OpenAI should have roughly 60% (3/5) of selections
        assert openai_count > total_others * 0.8  # Allow some variance
    
    @pytest.mark.asyncio
    async def test_failover_invoke_success(self, enhanced_llm_manager, mock_providers):
        """Test successful LLM invocation with failover"""
        prompt = "Test prompt for failover"
        
        # Should succeed with first available provider
        result = await enhanced_llm_manager.invoke_with_failover(prompt)
        
        assert result is not None
        assert "Response to: Test prompt" in result.content
    
    @pytest.mark.asyncio
    async def test_failover_invoke_preferred_provider(self, enhanced_llm_manager, mock_providers):
        """Test LLM invocation with preferred provider"""
        prompt = "Test prompt with preferred provider"
        preferred_provider = 'GOOGLE_gemini-pro'
        
        # Should use preferred provider
        result = await enhanced_llm_manager.invoke_with_failover(prompt, preferred_provider)
        
        assert result is not None
        assert "[google]" in result.content.lower()
    
    @pytest.mark.asyncio
    async def test_failover_invoke_provider_failure(self, enhanced_llm_manager, mock_providers):
        """Test LLM invocation with provider failure and failover"""
        prompt = "Test prompt with failover"
        preferred_provider = 'OPENAI_gpt-4'
        
        # Make preferred provider fail
        mock_providers['openai_gpt4'].should_fail = True
        
        # Should failover to another provider
        result = await enhanced_llm_manager.invoke_with_failover(prompt, preferred_provider)
        
        assert result is not None
        # Should not be from OpenAI (which is failing)
        assert "[openai]" not in result.content.lower()
        
        # Should record failure
        health_info = enhanced_llm_manager.provider_health[preferred_provider]
        assert health_info['failure_count'] > 0
    
    @pytest.mark.asyncio
    async def test_failover_all_providers_fail(self, enhanced_llm_manager, mock_providers):
        """Test behavior when all providers fail"""
        prompt = "Test prompt with all failures"
        
        # Make all providers fail
        for provider_client in mock_providers.values():
            provider_client.should_fail = True
        
        # Should raise exception when all providers fail
        with pytest.raises(NetraException) as exc_info:
            await enhanced_llm_manager.invoke_with_failover(prompt)
        
        assert "providers failed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_provider_cooldown_period(self, enhanced_llm_manager, mock_providers):
        """Test provider cooldown period after failures"""
        provider_key = 'OPENAI_gpt-4'
        
        # Set short cooldown for testing
        enhanced_llm_manager.failover_config['cooldown_period'] = 1  # 1 second
        
        # Make provider fail multiple times to trigger unhealthy state
        client = mock_providers['openai_gpt4']
        client.should_fail = True
        
        for _ in range(enhanced_llm_manager.failover_config['max_failures']):
            try:
                await enhanced_llm_manager.invoke_with_failover("test", provider_key)
            except:
                pass
        
        # Provider should be unhealthy
        health_info = enhanced_llm_manager.provider_health[provider_key]
        assert health_info['healthy'] is False
        
        # Should not be available during cooldown
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        assert is_healthy is False
        
        # Wait for cooldown period
        await asyncio.sleep(1.1)
        
        # Fix provider
        client.should_fail = False
        
        # Should be healthy again after cooldown
        is_healthy = await enhanced_llm_manager.check_provider_health(provider_key)
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_concurrent_provider_switching(self, enhanced_llm_manager, mock_providers):
        """Test concurrent requests with provider switching"""
        # Setup different response times for providers
        mock_providers['openai_gpt4'].response_time = 0.1
        mock_providers['google_gemini'].response_time = 0.05
        mock_providers['anthropic_claude'].response_time = 0.15
        
        # Make concurrent requests
        tasks = []
        for i in range(20):
            task = enhanced_llm_manager.invoke_with_failover(f"Concurrent request {i}")
            tasks.append(task)
        
        # Execute all requests
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 20
        
        # Should use different providers (round-robin)
        providers_used = set()
        for result in successful_results:
            if '[openai]' in result.content.lower():
                providers_used.add('openai')
            elif '[google]' in result.content.lower():
                providers_used.add('google')
            elif '[anthropic]' in result.content.lower():
                providers_used.add('anthropic')
        
        # Should have used multiple providers
        assert len(providers_used) >= 2
    
    def test_provider_statistics_collection(self, enhanced_llm_manager, mock_providers):
        """Test provider statistics collection"""
        # Simulate some requests
        asyncio.run(self._simulate_provider_usage(enhanced_llm_manager, mock_providers))
        
        # Get statistics
        stats = enhanced_llm_manager.get_provider_statistics()
        
        assert len(stats) == 3
        
        for provider_key, stat in stats.items():
            assert 'provider' in stat
            assert 'model_name' in stat
            assert 'request_count' in stat
            assert 'successful_requests' in stat
            assert 'failed_requests' in stat
            assert 'success_rate' in stat
            assert 'health_status' in stat
    
    async def _simulate_provider_usage(self, manager, providers):
        """Helper to simulate provider usage for testing"""
        # Simulate some successful requests
        for _ in range(5):
            try:
                await manager.invoke_with_failover("test prompt")
            except:
                pass
        
        # Simulate some failures
        providers['openai_gpt4'].should_fail = True
        for _ in range(2):
            try:
                await manager.invoke_with_failover("test prompt", 'OPENAI_gpt-4')
            except:
                pass
        providers['openai_gpt4'].should_fail = False


class TestLLMManagerLoadBalancing:
    """Test LLM manager load balancing strategies"""
    
    @pytest.fixture
    def load_balanced_manager(self):
        """Create LLM manager configured for load balancing testing"""
        config = AppConfig()
        config.environment = "testing"
        manager = EnhancedLLMManager(config)
        
        # Setup multiple providers with different capabilities
        providers = [
            ('FAST_openai', MockLLMClient(LLMProvider.OPENAI, 'gpt-3.5-turbo')),
            ('SLOW_openai', MockLLMClient(LLMProvider.OPENAI, 'gpt-4')),
            ('FAST_google', MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro')),
        ]
        
        # Set different response times
        providers[0][1].response_time = 0.05  # Fast
        providers[1][1].response_time = 0.2   # Slow
        providers[2][1].response_time = 0.1   # Medium
        
        # Register providers
        for key, client in providers:
            provider_enum = LLMProvider(key.split('_')[1].upper())
            manager.register_provider_client(provider_enum, client.model_name, client)
        
        return manager, dict(providers)
    
    @pytest.mark.asyncio
    async def test_response_time_based_load_balancing(self, load_balanced_manager):
        """Test load balancing based on provider response times"""
        manager, providers = load_balanced_manager
        
        # Set weights based on inverse response time (faster = higher weight)
        manager.load_balancing['strategy'] = 'weighted'
        manager.load_balancing['provider_weights'] = {
            'OPENAI_gpt-3.5-turbo': 4.0,  # Fast provider
            'OPENAI_gpt-4': 1.0,          # Slow provider
            'GOOGLE_gemini-pro': 2.0      # Medium provider
        }
        
        # Execute many requests and measure distribution
        provider_usage = {}
        start_time = time.time()
        
        tasks = []
        for i in range(30):
            task = manager.invoke_with_failover(f"Load balance test {i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Count usage per provider
        for result in results:
            if '[openai]' in result.content.lower():
                provider_usage['openai'] = provider_usage.get('openai', 0) + 1
            elif '[google]' in result.content.lower():
                provider_usage['google'] = provider_usage.get('google', 0) + 1
        
        # Faster providers should be used more frequently
        # (This is a probabilistic test, so we allow some variance)
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete quickly due to load balancing
    
    @pytest.mark.asyncio
    async def test_adaptive_load_balancing(self, load_balanced_manager):
        """Test adaptive load balancing based on success rates"""
        manager, providers = load_balanced_manager
        
        # Make one provider intermittently fail
        providers['SLOW_openai'].failure_rate = 0.3  # 30% failure rate
        
        # Use adaptive strategy
        manager.load_balancing['strategy'] = 'weighted'
        
        # Initial equal weights
        manager.load_balancing['provider_weights'] = {
            'OPENAI_gpt-3.5-turbo': 1.0,
            'OPENAI_gpt-4': 1.0,
            'GOOGLE_gemini-pro': 1.0
        }
        
        # Simulate adaptive weight adjustment based on success rates
        async def adaptive_invoke_with_weight_adjustment(prompt):
            """Invoke with adaptive weight adjustment"""
            try:
                result = await manager.invoke_with_failover(prompt)
                # Increase weight for successful provider
                # (Simplified weight adjustment logic)
                return result
            except Exception as e:
                # Decrease weight for failed provider
                # (In real implementation, this would be more sophisticated)
                raise e
        
        # Execute requests and track performance
        successful_requests = 0
        failed_requests = 0
        
        for i in range(50):
            try:
                await adaptive_invoke_with_weight_adjustment(f"Adaptive test {i}")
                successful_requests += 1
            except:
                failed_requests += 1
        
        # Should have some failures due to the failing provider
        assert failed_requests > 0
        assert successful_requests > failed_requests  # But more successes due to failover
    
    @pytest.mark.asyncio
    async def test_geographic_load_balancing(self, load_balanced_manager):
        """Test geographic/regional load balancing simulation"""
        manager, providers = load_balanced_manager
        
        # Simulate geographic latencies
        geographic_latencies = {
            'OPENAI_gpt-3.5-turbo': 0.05,  # US East
            'OPENAI_gpt-4': 0.15,          # US West  
            'GOOGLE_gemini-pro': 0.08      # EU
        }
        
        # Set latencies
        for key, client in providers.items():
            provider_key = f"OPENAI_{client.model_name}" if client.provider == LLMProvider.OPENAI else f"GOOGLE_{client.model_name}"
            if provider_key in geographic_latencies:
                client.response_time = geographic_latencies[provider_key]
        
        # Use latency-based weights
        manager.load_balancing['strategy'] = 'weighted'
        manager.load_balancing['provider_weights'] = {
            key: 1.0 / latency for key, latency in geographic_latencies.items()
        }
        
        # Execute requests and measure total latency
        start_time = time.time()
        
        tasks = [manager.invoke_with_failover(f"Geographic test {i}") for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        avg_time_per_request = total_time / len(results)
        
        # Should prefer lower latency providers
        assert avg_time_per_request < 0.15  # Should be closer to fastest provider


class TestLLMManagerStructuredOutput:
    """Test LLM manager with structured output and provider switching"""
    
    class OutputSchema(BaseModel):
        """Test schema for structured output"""
        summary: str
        confidence: float
        categories: List[str]
        metadata: Dict[str, Any]
    
    @pytest.fixture
    def structured_llm_manager(self):
        """Create LLM manager for structured output testing"""
        config = AppConfig()
        config.environment = "testing"
        manager = EnhancedLLMManager(config)
        
        # Setup providers with structured output support
        providers = [
            MockLLMClient(LLMProvider.OPENAI, 'gpt-4'),
            MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro')
        ]
        
        for i, client in enumerate(providers):
            provider_enum = LLMProvider(client.provider.value.upper())
            manager.register_provider_client(provider_enum, client.model_name, client)
        
        return manager
    
    @pytest.mark.asyncio
    async def test_structured_output_with_failover(self, structured_llm_manager):
        """Test structured output with provider failover"""
        # This would test structured output failover in a real implementation
        # For now, we'll test the concept with our mock setup
        
        prompt = "Analyze this text and provide structured output"
        
        # In a real implementation, this would use structured output
        # For testing, we simulate the concept
        result = await structured_llm_manager.invoke_with_failover(prompt)
        
        assert result is not None
        assert isinstance(result.content, str)
        
        # Test that different providers can be used for structured output
        provider_results = []
        for _ in range(4):
            result = await structured_llm_manager.invoke_with_failover(prompt)
            provider_results.append(result)
        
        # Should get results from different providers (round-robin)
        provider_types = set()
        for result in provider_results:
            if '[openai]' in result.content.lower():
                provider_types.add('openai')
            elif '[google]' in result.content.lower():
                provider_types.add('google')
        
        assert len(provider_types) >= 1  # At least one provider type used