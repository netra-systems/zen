"""
LLM Manager service implementation.

Provides centralized management of LLM operations, including model selection,
request routing, caching, and cost tracking.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass
class LLMRequest:
    """LLM request configuration."""
    model: str
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    provider: Optional[LLMProvider] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """LLM response with metadata."""
    content: str
    provider: str
    model: str
    tokens_used: int
    cost: float
    latency: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None


class LLMManager:
    """Manages LLM operations and provider selection."""
    
    def __init__(self):
        """Initialize LLM manager."""
        self.providers = {
            LLMProvider.OPENAI: "OpenAI",
            LLMProvider.ANTHROPIC: "Anthropic",
            LLMProvider.GOOGLE: "Google",
            LLMProvider.LOCAL: "Local"
        }
        
        self.model_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        }
        
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "provider_usage": {},
            "model_usage": {}
        }
        
        self.enabled = True
    
    async def process_request(self, request: LLMRequest) -> LLMResponse:
        """Process LLM request with provider routing and caching."""
        if not self.enabled:
            raise RuntimeError("LLM Manager is disabled")
        
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Check cache first
            cache_result = await self._check_cache(request)
            if cache_result:
                self.stats["cache_hits"] += 1
                return cache_result
            
            self.stats["cache_misses"] += 1
            
            # Route to appropriate provider
            response = await self._route_request(request)
            
            # Update statistics
            self._update_stats(response)
            
            # Cache response
            await self._cache_response(request, response)
            
            return response
            
        except Exception as e:
            self.stats["errors"] += 1
            raise RuntimeError(f"LLM request failed: {str(e)}")
    
    async def _check_cache(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Check if request is cached."""
        try:
            from app.services.llm_cache_service import llm_cache_service
            
            cache_key = self._generate_cache_key(request)
            cached_data = await llm_cache_service.get(cache_key)
            
            if cached_data:
                return LLMResponse(
                    content=cached_data.get("content", ""),
                    provider=cached_data.get("provider", "unknown"),
                    model=cached_data.get("model", "unknown"),
                    tokens_used=cached_data.get("tokens_used", 0),
                    cost=cached_data.get("cost", 0.0),
                    latency=cached_data.get("latency", 0.0),
                    cached=True,
                    metadata=cached_data.get("metadata")
                )
        except ImportError:
            pass
        except Exception:
            pass
        
        return None
    
    async def _cache_response(self, request: LLMRequest, response: LLMResponse) -> None:
        """Cache the response."""
        try:
            from app.services.llm_cache_service import llm_cache_service
            
            cache_key = self._generate_cache_key(request)
            cache_data = {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "latency": response.latency,
                "metadata": response.metadata
            }
            
            await llm_cache_service.set(cache_key, cache_data, ttl=3600)  # 1 hour
            
        except ImportError:
            pass
        except Exception:
            pass
    
    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        import hashlib
        
        key_data = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _route_request(self, request: LLMRequest) -> LLMResponse:
        """Route request to appropriate provider."""
        # Simulate LLM processing
        await asyncio.sleep(0.1)  # Simulate latency
        
        # Determine provider
        provider = request.provider or self._select_provider(request.model)
        
        # Simulate response
        content = f"Generated response for model {request.model}"
        tokens_used = len(content.split()) * 2  # Rough estimation
        cost = self._calculate_cost(request.model, tokens_used)
        latency = time.time() - time.time()  # Would be actual start time
        
        return LLMResponse(
            content=content,
            provider=provider.value if isinstance(provider, LLMProvider) else str(provider),
            model=request.model,
            tokens_used=tokens_used,
            cost=cost,
            latency=latency,
            cached=False,
            metadata=request.metadata
        )
    
    def _select_provider(self, model: str) -> LLMProvider:
        """Select provider based on model."""
        if "gpt" in model.lower():
            return LLMProvider.OPENAI
        elif "claude" in model.lower():
            return LLMProvider.ANTHROPIC
        elif "gemini" in model.lower() or "palm" in model.lower():
            return LLMProvider.GOOGLE
        else:
            return LLMProvider.LOCAL
    
    def _calculate_cost(self, model: str, tokens_used: int) -> float:
        """Calculate cost for request."""
        model_cost = self.model_costs.get(model, {"input": 0.001, "output": 0.002})
        
        # Assume 70% input, 30% output tokens
        input_tokens = int(tokens_used * 0.7)
        output_tokens = int(tokens_used * 0.3)
        
        cost = (input_tokens * model_cost["input"] / 1000) + (output_tokens * model_cost["output"] / 1000)
        return round(cost, 6)
    
    def _update_stats(self, response: LLMResponse) -> None:
        """Update usage statistics."""
        self.stats["total_tokens"] += response.tokens_used
        self.stats["total_cost"] += response.cost
        
        # Provider usage
        provider = response.provider
        if provider not in self.stats["provider_usage"]:
            self.stats["provider_usage"][provider] = {"requests": 0, "tokens": 0, "cost": 0.0}
        
        self.stats["provider_usage"][provider]["requests"] += 1
        self.stats["provider_usage"][provider]["tokens"] += response.tokens_used
        self.stats["provider_usage"][provider]["cost"] += response.cost
        
        # Model usage
        model = response.model
        if model not in self.stats["model_usage"]:
            self.stats["model_usage"][model] = {"requests": 0, "tokens": 0, "cost": 0.0}
        
        self.stats["model_usage"][model]["requests"] += 1
        self.stats["model_usage"][model]["tokens"] += response.tokens_used
        self.stats["model_usage"][model]["cost"] += response.cost
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        cache_total = self.stats["cache_hits"] + self.stats["cache_misses"]
        cache_hit_rate = self.stats["cache_hits"] / max(cache_total, 1)
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "average_cost_per_request": self.stats["total_cost"] / max(self.stats["total_requests"], 1),
            "average_tokens_per_request": self.stats["total_tokens"] / max(self.stats["total_requests"], 1),
            "enabled": self.enabled
        }
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models by provider."""
        return {
            "openai": ["gpt-4", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "google": ["gemini-pro", "palm-2"],
            "local": ["llama-2", "mistral-7b"]
        }
    
    def get_cost_estimates(self) -> Dict[str, Dict[str, float]]:
        """Get cost estimates for models."""
        return self.model_costs.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of LLM services."""
        return {
            "status": "healthy" if self.enabled else "disabled",
            "providers_available": len(self.providers),
            "models_available": sum(len(models) for models in self.get_available_models().values()),
            "total_requests_processed": self.stats["total_requests"],
            "error_rate": self.stats["errors"] / max(self.stats["total_requests"], 1)
        }
    
    def disable(self) -> None:
        """Disable LLM manager."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable LLM manager."""
        self.enabled = True
    
    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "provider_usage": {},
            "model_usage": {}
        }


# Global instance
llm_manager = LLMManager()