"""
Enhanced LLM Manager - Test implementation with provider switching and failover
Extracted from test_llm_manager_provider_switching.py for 25-line function compliance
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.Config import AppConfig
from .llm_manager_helpers import LLMProvider
from .llm_mock_clients import MockLLMClient


class EnhancedLLMManager(LLMManager):
    """Enhanced LLM Manager with provider switching and failover"""
    
    def __init__(self, settings: AppConfig):
        super().__init__(settings)
        self._init_provider_tracking()
        self._init_failover_config()
        self._init_load_balancing()
        
    def _init_provider_tracking(self):
        """Initialize provider tracking structures"""
        self.provider_clients = {}
        self.provider_health = {}
        self.provider_metrics = {}
        
    def _init_failover_config(self):
        """Initialize failover configuration"""
        self.failover_config = {
            'enabled': True, 'max_failures': 3,
            'cooldown_period': 300, 'health_check_interval': 60
        }
        
    def _init_load_balancing(self):
        """Initialize load balancing configuration"""
        self.load_balancing = {
            'strategy': 'round_robin', 'current_provider_index': 0,
            'provider_weights': {}
        }
        
    def register_provider_client(self, provider: LLMProvider, model_name: str, client: MockLLMClient):
        """Register a provider client"""
        key = f"{provider.value}_{model_name}"
        self.provider_clients[key] = client
        self._init_provider_health(key)
        self.provider_metrics[key] = client.get_metrics()
        
    def _init_provider_health(self, key: str):
        """Initialize provider health tracking"""
        self.provider_health[key] = {
            'healthy': True, 'last_failure': None,
            'failure_count': 0, 'last_health_check': datetime.now(UTC)
        }
        
    async def check_provider_health(self, provider_key: str) -> bool:
        """Check if a provider is healthy"""
        if provider_key not in self.provider_health:
            return False
        
        if not self._is_out_of_cooldown(provider_key):
            return False
        
        return await self._perform_health_check(provider_key)
        
    def _is_out_of_cooldown(self, provider_key: str) -> bool:
        """Check if provider is out of cooldown period"""
        health = self.provider_health[provider_key]
        if health['healthy'] or not health['last_failure']:
            return True
            
        cooldown_end = health['last_failure'] + timedelta(seconds=self.failover_config['cooldown_period'])
        return datetime.now(UTC) >= cooldown_end
        
    async def _perform_health_check(self, provider_key: str) -> bool:
        """Perform actual health check"""
        try:
            client = self.provider_clients[provider_key]
            await client.ainvoke("health check")
            self._mark_provider_healthy(provider_key)
            return True
        except Exception:
            self._mark_provider_unhealthy(provider_key)
            return False
            
    def _mark_provider_healthy(self, provider_key: str):
        """Mark provider as healthy"""
        health = self.provider_health[provider_key]
        health['healthy'] = True
        health['failure_count'] = 0
        health['last_health_check'] = datetime.now(UTC)
        
    def _mark_provider_unhealthy(self, provider_key: str):
        """Mark provider as unhealthy"""
        health = self.provider_health[provider_key]
        health['healthy'] = False
        health['failure_count'] += 1
        health['last_failure'] = datetime.now(UTC)
        health['last_health_check'] = datetime.now(UTC)
        
    async def get_next_available_provider(self, exclude_providers: List[str] = None) -> Optional[str]:
        """Get next available provider based on load balancing strategy"""
        exclude_providers = exclude_providers or []
        available_providers = self._get_available_providers(exclude_providers)
        
        if not available_providers:
            return None
        
        return await self._select_provider_by_strategy(available_providers)
        
    def _get_available_providers(self, exclude_providers: List[str]) -> List[str]:
        """Get list of available providers"""
        return [
            key for key in self.provider_clients.keys()
            if key not in exclude_providers
        ]
        
    async def _select_provider_by_strategy(self, available_providers: List[str]) -> Optional[str]:
        """Select provider based on configured strategy"""
        strategy = self.load_balancing['strategy']
        
        if strategy == 'round_robin':
            return self._get_round_robin_provider(available_providers)
        elif strategy == 'weighted':
            return self._get_weighted_provider(available_providers)
        elif strategy == 'failover_only':
            return await self._get_failover_provider(available_providers)
        
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
        
        weights = self._calculate_provider_weights(available_providers)
        return self._select_weighted_provider(available_providers, weights)
        
    def _calculate_provider_weights(self, available_providers: List[str]) -> List[float]:
        """Calculate weights for providers"""
        weights = []
        for provider in available_providers:
            weight = self.load_balancing['provider_weights'].get(provider, 1.0)
            weights.append(weight)
        return weights
        
    def _select_weighted_provider(self, available_providers: List[str], weights: List[float]) -> str:
        """Select provider based on weights"""
        import random
        
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(available_providers)
        
        return self._weighted_random_selection(available_providers, weights, total_weight)
        
    def _weighted_random_selection(self, providers: List[str], weights: List[float], total_weight: float) -> str:
        """Perform weighted random selection"""
        import random
        
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return providers[i]
        
        return providers[-1]
        
    async def _get_failover_provider(self, available_providers: List[str]) -> Optional[str]:
        """Get first healthy provider for failover strategy"""
        for provider_key in available_providers:
            if await self.check_provider_health(provider_key):
                return provider_key
        return None
        
    async def invoke_with_failover(self, prompt: str, preferred_provider: str = None, max_retries: int = 3) -> Any:
        """Invoke LLM with automatic failover on failure"""
        attempted_providers = []
        
        result = await self._try_preferred_provider(prompt, preferred_provider, attempted_providers)
        if result:
            return result
        
        return await self._try_available_providers(prompt, attempted_providers, max_retries)
        
    async def _try_preferred_provider(self, prompt: str, preferred_provider: str, attempted_providers: List[str]) -> Any:
        """Try preferred provider first"""
        if not preferred_provider or preferred_provider not in self.provider_clients:
            return None
        
        try:
            if await self.check_provider_health(preferred_provider):
                client = self.provider_clients[preferred_provider]
                return await client.ainvoke(prompt)
        except Exception as e:
            attempted_providers.append(preferred_provider)
            self._record_provider_failure(preferred_provider, e)
        
        return None
        
    async def _try_available_providers(self, prompt: str, attempted_providers: List[str], max_retries: int) -> Any:
        """Try available providers with retries"""
        for attempt in range(max_retries):
            next_provider = await self.get_next_available_provider(attempted_providers)
            if not next_provider:
                break
            
            result = await self._attempt_provider_invoke(prompt, next_provider, attempted_providers)
            if result:
                return result
            
            if attempt == max_retries - 1:
                raise NetraException(f"All LLM providers failed")
        
        raise NetraException("No healthy LLM providers available")
        
    async def _attempt_provider_invoke(self, prompt: str, provider_key: str, attempted_providers: List[str]) -> Any:
        """Attempt to invoke with specific provider"""
        try:
            if await self.check_provider_health(provider_key):
                client = self.provider_clients[provider_key]
                return await client.ainvoke(prompt)
            
            attempted_providers.append(provider_key)
        except Exception as e:
            attempted_providers.append(provider_key)
            self._record_provider_failure(provider_key, e)
        
        return None
        
    def _record_provider_failure(self, provider_key: str, error: Exception):
        """Record provider failure for health tracking"""
        if provider_key not in self.provider_health:
            return
        
        health = self.provider_health[provider_key]
        health['failure_count'] += 1
        health['last_failure'] = datetime.now(UTC)
        
        if health['failure_count'] >= self.failover_config['max_failures']:
            health['healthy'] = False
            
    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get statistics for all providers"""
        stats = {}
        
        for provider_key, client in self.provider_clients.items():
            client_metrics = client.get_metrics()
            health_info = self.provider_health.get(provider_key, {})
            
            stats[provider_key] = self._build_provider_stats(client_metrics, health_info)
        
        return stats
        
    def _build_provider_stats(self, client_metrics: Dict[str, Any], health_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build provider statistics dictionary"""
        return {
            **client_metrics,
            'health_status': 'healthy' if health_info.get('healthy', False) else 'unhealthy',
            'failure_count': health_info.get('failure_count', 0),
            'last_failure': health_info.get('last_failure'),
            'last_health_check': health_info.get('last_health_check')
        }