"""
AI Supply Chain Failover Test Helpers

BVJ: Protects $75K+ MRR from LLM provider outages by ensuring robust failover mechanisms.
Architecture: Functions  <= 8 lines, modular provider simulation utilities.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional
from netra_backend.app.llm.fallback_config import FallbackConfig
from netra_backend.app.llm.fallback_handler import LLMFallbackHandler
from netra_backend.app.schemas.llm_base_types import LLMProvider
from netra_backend.app.llm.llm_provider_handlers import create_llm_for_provider
from netra_backend.app.schemas.config import LLMConfig


class ProviderStatus(Enum):
    """Provider availability status."""
    HEALTHY = "healthy"
    TIMEOUT = "timeout" 
    RATE_LIMITED = "rate_limited"
    COST_EXCEEDED = "cost_exceeded"
    QUALITY_DEGRADED = "quality_degraded"
    COMPLETELY_DOWN = "completely_down"


@dataclass
class ProviderConfig:
    """Provider configuration for simulation."""
    name: str
    cost_per_token: float
    quality_score: float
    timeout_ms: int
    rate_limit_rpm: int
    status: ProviderStatus = ProviderStatus.HEALTHY


@dataclass
class FailoverMetrics:
    """Metrics tracking for failover tests."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    total_cost: float = 0.0
    failover_count: int = 0


class RealLLMProvider:
    """Real LLM provider with configurable behavior for testing."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.request_count = 0
        self.last_request_time = 0
        self.llm_client = self._create_real_llm_client()

    def _create_real_llm_client(self) -> Optional[Any]:
        """Create real LLM client based on provider name."""
        provider_map = {
            "gemini": LLMProvider.GOOGLE,
            "gpt4": LLMProvider.OPENAI, 
            "claude": LLMProvider.ANTHROPIC
        }
        
        provider = provider_map.get(self.config.name)
        if not provider:
            return None
            
        # Use real API keys from environment or fail gracefully
        api_key = self._get_api_key_for_provider(provider)
        if not api_key:
            raise ValueError(f"API key required for {self.config.name} provider")
            
        model_name = self._get_model_for_provider(provider)
        generation_config = {"temperature": 0.7, "max_tokens": 1000}
        
        return create_llm_for_provider(provider, model_name, api_key, generation_config)
    
    def _get_api_key_for_provider(self, provider: LLMProvider) -> Optional[str]:
        """Get API key for provider from environment."""
        from shared.isolated_environment import get_env
        env = get_env()
        key_map = {
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY"
        }
        return env.get(key_map.get(provider, ""))
    
    def _get_model_for_provider(self, provider: LLMProvider) -> str:
        """Get default model name for provider."""
        model_map = {
            LLMProvider.GOOGLE: "gemini-2.5-flash",
            LLMProvider.OPENAI: "gpt-4",
            LLMProvider.ANTHROPIC: "claude-3.5-sonnet"
        }
        return model_map.get(provider, "gpt-4")

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using real LLM provider with configured behavior."""
        await self._simulate_provider_behavior()
        return await self._make_real_llm_request(prompt)
    
    async def _simulate_provider_behavior(self) -> None:
        """Simulate provider-specific behavior patterns."""
        self._check_rate_limits()
        await self._simulate_latency()
        self._check_provider_status()
        self.request_count += 1
        self.last_request_time = time.time()

    def _check_rate_limits(self) -> None:
        """Check if rate limits are exceeded."""
        if self.config.status == ProviderStatus.RATE_LIMITED:
            raise Exception(f"Rate limit exceeded for {self.config.name}")
        current_time = time.time()
        if self.last_request_time > 0 and current_time - self.last_request_time < 60 / self.config.rate_limit_rpm:
            raise Exception(f"Rate limit exceeded for {self.config.name}")

    async def _simulate_latency(self) -> None:
        """Simulate provider response latency."""
        if self.config.status == ProviderStatus.TIMEOUT:
            await asyncio.sleep(10)  # Long timeout to force failure
        else:
            await asyncio.sleep(0.01)  # Normal latency

    def _check_provider_status(self) -> None:
        """Check current provider status and raise appropriate errors."""
        if self.config.status == ProviderStatus.COMPLETELY_DOWN:
            raise Exception(f"Provider {self.config.name} is completely down")
        elif self.config.status == ProviderStatus.COST_EXCEEDED:
            raise Exception(f"Cost threshold exceeded for {self.config.name}")
        elif self.config.status == ProviderStatus.QUALITY_DEGRADED:
            # For degraded quality, we lower the quality score but don't fail
            self.config.quality_score = 0.5  # Below acceptable threshold

    async def _make_real_llm_request(self, prompt: str) -> Dict[str, Any]:
        """Make actual request to real LLM provider."""
        if not self.llm_client:
            raise Exception(f"No LLM client available for {self.config.name}")
        
        try:
            # Make real API call to LLM
            from langchain.schema import HumanMessage
            messages = [HumanMessage(content=prompt)]
            response = await self.llm_client.ainvoke(messages)
            
            # Extract response content and metadata
            content = response.content if hasattr(response, 'content') else str(response)
            tokens_used = len(prompt.split()) + len(content.split())
            cost = tokens_used * self.config.cost_per_token
            
            return {
                "content": content,
                "provider": self.config.name,
                "quality_score": self.config.quality_score,
                "cost": cost,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            # If real API fails, raise exception instead of returning mock data
            raise Exception(f"Real LLM request failed for {self.config.name}: {str(e)}")


class ProviderSimulator:
    """Simulates multiple LLM providers with different characteristics."""
    
    def __init__(self):
        self.providers = self._create_default_providers()
        self.metrics = FailoverMetrics()

    def _create_default_providers(self) -> Dict[str, RealLLMProvider]:
        """Create default provider configurations."""
        configs = {
            "gemini": ProviderConfig("gemini", 0.001, 0.95, 2000, 60),
            "gpt4": ProviderConfig("gpt4", 0.03, 0.98, 3000, 40),
            "claude": ProviderConfig("claude", 0.008, 0.97, 1500, 50)
        }
        return {name: RealLLMProvider(config) for name, config in configs.items()}

    def set_provider_status(self, provider: str, status: ProviderStatus) -> None:
        """Set provider status for testing scenarios."""
        if provider in self.providers:
            self.providers[provider].config.status = status

    async def execute_with_failover(self, prompt: str, primary_provider: str = "gemini") -> Dict[str, Any]:
        """Execute request with automatic failover logic."""
        provider_order = self._get_failover_order(primary_provider)
        result = await self._try_providers_in_order(prompt, provider_order)
        # Check if we need to upgrade due to quality issues
        return await self._check_quality_and_upgrade(result, prompt, provider_order)

    async def _check_quality_and_upgrade(self, result: Dict[str, Any], prompt: str, provider_order: List[str]) -> Dict[str, Any]:
        """Check quality and upgrade to premium provider if needed."""
        if result.get("quality_score", 1.0) < 0.85:  # Quality threshold
            premium_providers = ["gpt4", "claude"]
            for provider in premium_providers:
                if provider in provider_order and provider != result.get("provider"):
                    try:
                        return await self._attempt_provider_request(prompt, provider)
                    except Exception:
                        continue
        return result


    def _get_failover_order(self, primary: str) -> List[str]:
        """Get provider failover order based on cost and quality."""
        all_providers = list(self.providers.keys())
        if primary in all_providers:
            all_providers.remove(primary)
            all_providers.insert(0, primary)
        return all_providers

    async def _try_providers_in_order(self, prompt: str, provider_order: List[str]) -> Dict[str, Any]:
        """Try providers in specified order until success."""
        last_error = None
        for provider_name in provider_order:
            try:
                return await self._attempt_provider_request(prompt, provider_name)
            except Exception as e:
                last_error = e
                self.metrics.failover_count += 1
                self.metrics.failed_requests += 1
                continue  # Try next provider
        raise Exception(f"All providers failed. Last error: {last_error}")

    async def _attempt_provider_request(self, prompt: str, provider_name: str) -> Dict[str, Any]:
        """Attempt request with specific provider."""
        start_time = time.time()
        try:
            # Add timeout wrapper for provider requests
            result = await asyncio.wait_for(
                self.providers[provider_name].generate(prompt), 
                timeout=4.0  # 4 second timeout to stay under 5s SLA
            )
            self._update_metrics(start_time, result)
            return result
        except asyncio.TimeoutError:
            raise Exception(f"Provider {provider_name} timed out")


    def _update_metrics(self, start_time: float, result: Dict[str, Any]) -> None:
        """Update failover metrics with request results."""
        latency = (time.time() - start_time) * 1000
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.avg_latency_ms = self._calculate_avg_latency(latency)
        self.metrics.total_cost += result.get("cost", 0)

    def _calculate_avg_latency(self, current_latency: float) -> float:
        """Calculate running average latency."""
        if self.metrics.total_requests == 1:
            return current_latency
        return ((self.metrics.avg_latency_ms * (self.metrics.total_requests - 1)) + current_latency) / self.metrics.total_requests


class SLAValidator:
    """Validates SLA compliance during failover scenarios."""
    
    def __init__(self, max_latency_ms: float = 5000, min_success_rate: float = 0.99):
        self.max_latency_ms = max_latency_ms
        self.min_success_rate = min_success_rate

    def validate_sla_compliance(self, metrics: FailoverMetrics) -> bool:
        """Check if metrics meet SLA requirements."""
        success_rate = self._calculate_success_rate(metrics)
        return (metrics.avg_latency_ms <= self.max_latency_ms and 
                success_rate >= self.min_success_rate)

    def _calculate_success_rate(self, metrics: FailoverMetrics) -> float:
        """Calculate success rate from metrics."""
        if metrics.total_requests == 0:
            return 1.0
        return metrics.successful_requests / metrics.total_requests


class CostOptimizer:
    """Optimizes provider selection based on cost thresholds."""
    
    def __init__(self, cost_threshold: float = 100.0):
        self.cost_threshold = cost_threshold
        self.current_spend = 0.0

    def should_switch_provider(self, current_cost: float) -> bool:
        """Determine if provider switch needed based on cost."""
        projected_spend = self.current_spend + current_cost
        return projected_spend > self.cost_threshold

    def get_cheapest_provider(self, providers: Dict[str, RealLLMProvider]) -> str:
        """Find cheapest available provider."""
        return min(providers.keys(), 
                  key=lambda p: providers[p].config.cost_per_token)


class QualityMonitor:
    """Monitors response quality and triggers provider switches."""
    
    def __init__(self, min_quality_threshold: float = 0.85):
        self.min_quality_threshold = min_quality_threshold
        self.quality_history: List[float] = []

    def check_quality_degradation(self, response: Dict[str, Any]) -> bool:
        """Check if response quality is below threshold."""
        quality = response.get("quality_score", 1.0)
        self.quality_history.append(quality)
        return self._is_quality_degraded()

    def _is_quality_degraded(self) -> bool:
        """Check if recent quality is below threshold."""
        if len(self.quality_history) < 3:
            return False
        recent_avg = sum(self.quality_history[-3:]) / 3
        return recent_avg < self.min_quality_threshold