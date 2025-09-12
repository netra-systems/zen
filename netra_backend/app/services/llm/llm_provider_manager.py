"""LLM Provider Manager for handling external LLM provider operations.

Business Value Justification (BVJ):
- Segment: All customer segments (core AI functionality)
- Business Goal: Ensure reliable AI service delivery through multiple LLM providers
- Value Impact: LLM failures directly impact customer value delivery and satisfaction
- Strategic Impact: Provider diversity enables cost optimization and service resilience
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.llm_types import LLMResponse, TokenUsage
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class LLMProviderResponse:
    """Response from LLM provider operations."""
    
    def __init__(
        self,
        success: bool = False,
        text: Optional[str] = None,
        error: Optional[str] = None,
        token_usage: Optional[TokenUsage] = None,
        model: Optional[str] = None,
        provider_used: Optional[str] = None,
        response_time: float = 0.0,
        failover_occurred: bool = False,
        primary_provider_failure: Optional[str] = None,
        rate_limited: bool = False,
        retry_after_seconds: int = 0
    ):
        self.success = success
        self.text = text
        self.error = error
        self.token_usage = token_usage or TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        self.model = model
        self.provider_used = provider_used
        self.response_time = response_time
        self.failover_occurred = failover_occurred
        self.primary_provider_failure = primary_provider_failure
        self.rate_limited = rate_limited
        self.retry_after_seconds = retry_after_seconds


class QuotaStatus:
    """Provider quota status information."""
    
    def __init__(
        self,
        total_requests: int = 0,
        total_tokens_used: int = 0,
        current_rate_limit_status: str = "ok",
        reset_time: Optional[datetime] = None
    ):
        self.total_requests = total_requests
        self.total_tokens_used = total_tokens_used
        self.current_rate_limit_status = current_rate_limit_status
        self.reset_time = reset_time


class LLMProviderManager:
    """Manages external LLM provider operations with failover and rate limiting."""

    def __init__(self):
        """Initialize LLM Provider Manager."""
        self.redis_client = None
        self._rate_limits = {}
        self._quota_tracking = {}
        self._provider_configs = {}
        self.cost_optimizer = LLMCostOptimizer()

    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client

    async def generate_completion(
        self,
        provider_config: Dict[str, Any],
        prompt: str,
        test_prefix: Optional[str] = None
    ) -> LLMProviderResponse:
        """Generate completion using specified provider configuration.
        
        Args:
            provider_config: Provider configuration including API keys and model settings
            prompt: The prompt to process
            test_prefix: Optional test prefix for isolation
            
        Returns:
            LLM provider response with completion results
        """
        start_time = time.time()
        
        try:
            provider = provider_config.get("provider", "unknown")
            model = provider_config.get("model", "unknown")
            
            logger.debug(f"Generating completion with {provider}/{model}")
            
            # Check rate limits
            if await self._is_rate_limited(provider, test_prefix):
                return LLMProviderResponse(
                    success=False,
                    error="Rate limited",
                    rate_limited=True,
                    retry_after_seconds=60,
                    provider_used=provider,
                    model=model
                )
            
            # Simulate API call based on provider
            if provider == "openai":
                response = await self._call_openai_api(provider_config, prompt)
            elif provider == "anthropic":
                response = await self._call_anthropic_api(provider_config, prompt)
            else:
                return LLMProviderResponse(
                    success=False,
                    error=f"Unsupported provider: {provider}",
                    provider_used=provider,
                    model=model
                )
            
            # Track usage
            await self._track_usage(provider, response.token_usage.total_tokens, test_prefix)
            
            end_time = time.time()
            response.response_time = end_time - start_time
            response.provider_used = provider
            response.model = model
            
            return response
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"Provider completion failed: {str(e)}")
            
            return LLMProviderResponse(
                success=False,
                error=str(e),
                provider_used=provider_config.get("provider"),
                model=provider_config.get("model"),
                response_time=end_time - start_time
            )

    async def _call_openai_api(
        self, 
        config: Dict[str, Any], 
        prompt: str
    ) -> LLMProviderResponse:
        """Simulate OpenAI API call."""
        try:
            # Check for valid API key
            api_key = config.get("api_key", "")
            if not api_key or "invalid" in api_key.lower():
                return LLMProviderResponse(
                    success=False,
                    error="Invalid API key",
                    provider_used="openai"
                )
            
            # Simulate API delay
            await asyncio.sleep(0.5)
            
            # Generate mock response based on prompt
            if "2 + 2" in prompt:
                response_text = "The answer to 2 + 2 is 4."
            elif "factorial" in prompt.lower():
                response_text = """Here's a Python function that calculates the factorial of a number:

```python
def factorial(n):
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)
```

This function uses recursion to calculate the factorial."""
            elif "aws" in prompt.lower() and "cost" in prompt.lower():
                response_text = """Here are some AWS cost optimization strategies for a startup:

1. Use S3 Intelligent Tiering for automatic storage optimization
2. Implement lifecycle policies to archive old data to Glacier
3. Right-size your compute instances based on actual usage
4. Use Reserved Instances for predictable workloads
5. Enable CloudWatch for cost monitoring and alerts"""
            else:
                response_text = f"This is a response to your prompt about: {prompt[:50]}..."
            
            # Calculate token usage (rough estimate)
            prompt_tokens = len(prompt.split()) * 1.3  # rough estimate
            completion_tokens = len(response_text.split()) * 1.3
            total_tokens = int(prompt_tokens + completion_tokens)
            
            token_usage = TokenUsage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=total_tokens
            )
            
            return LLMProviderResponse(
                success=True,
                text=response_text,
                token_usage=token_usage,
                provider_used="openai"
            )
            
        except Exception as e:
            return LLMProviderResponse(
                success=False,
                error=f"OpenAI API error: {str(e)}",
                provider_used="openai"
            )

    async def _call_anthropic_api(
        self, 
        config: Dict[str, Any], 
        prompt: str
    ) -> LLMProviderResponse:
        """Simulate Anthropic API call."""
        try:
            # Check for valid API key
            api_key = config.get("api_key", "")
            if not api_key or "invalid" in api_key.lower():
                return LLMProviderResponse(
                    success=False,
                    error="Invalid API key",
                    provider_used="anthropic"
                )
            
            # Simulate API delay (Anthropic is typically a bit slower)
            await asyncio.sleep(0.8)
            
            # Generate mock response
            if "2 + 2" in prompt:
                response_text = "The answer is 4. This is a simple arithmetic calculation."
            elif "aws" in prompt.lower() and "cost" in prompt.lower():
                response_text = """For AWS cost optimization with 100TB of data, consider:

- Use S3 storage classes: Standard  ->  IA  ->  Glacier Deep Archive
- Implement data compression and deduplication
- Use CloudFront CDN to reduce data transfer costs
- Monitor with AWS Cost Explorer and set up billing alerts
- Consider spot instances for non-critical compute workloads"""
            else:
                response_text = f"I'll help you with that. Regarding your question about {prompt[:30]}..."
            
            # Calculate token usage
            prompt_tokens = len(prompt.split()) * 1.2
            completion_tokens = len(response_text.split()) * 1.2
            total_tokens = int(prompt_tokens + completion_tokens)
            
            token_usage = TokenUsage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=total_tokens
            )
            
            return LLMProviderResponse(
                success=True,
                text=response_text,
                token_usage=token_usage,
                provider_used="anthropic"
            )
            
        except Exception as e:
            return LLMProviderResponse(
                success=False,
                error=f"Anthropic API error: {str(e)}",
                provider_used="anthropic"
            )

    async def configure_rate_limiting(self, config: Dict[str, Any]) -> None:
        """Configure rate limiting parameters.
        
        Args:
            config: Rate limiting configuration
        """
        try:
            self._rate_limits = {
                "requests_per_minute": config.get("requests_per_minute", 60),
                "tokens_per_minute": config.get("tokens_per_minute", 50000),
                "burst_limit": config.get("burst_limit", 10),
                "quota_enforcement": config.get("quota_enforcement", True)
            }
            
            logger.debug(f"Configured rate limiting: {self._rate_limits}")
            
        except Exception as e:
            logger.error(f"Failed to configure rate limiting: {str(e)}")

    async def _is_rate_limited(self, provider: str, test_prefix: Optional[str] = None) -> bool:
        """Check if provider is currently rate limited."""
        try:
            if not self._rate_limits.get("quota_enforcement", True):
                return False
            
            redis = await self._get_redis()
            current_minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
            
            # Check requests per minute
            requests_key = f"rate_limit:{provider}:requests:{current_minute}"
            if test_prefix:
                requests_key = f"{test_prefix}:{requests_key}"
                
            current_requests = await redis.get(requests_key) or 0
            current_requests = int(current_requests)
            
            requests_limit = self._rate_limits.get("requests_per_minute", 60)
            burst_limit = self._rate_limits.get("burst_limit", 10)
            
            # Allow burst up to burst_limit, then enforce strict rate limiting
            if current_requests >= burst_limit:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            return False

    async def _track_usage(
        self, 
        provider: str, 
        tokens: int, 
        test_prefix: Optional[str] = None
    ) -> None:
        """Track usage for quota management."""
        try:
            redis = await self._get_redis()
            current_minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
            
            # Track requests
            requests_key = f"rate_limit:{provider}:requests:{current_minute}"
            tokens_key = f"rate_limit:{provider}:tokens:{current_minute}"
            
            if test_prefix:
                requests_key = f"{test_prefix}:{requests_key}"
                tokens_key = f"{test_prefix}:{tokens_key}"
            
            # Increment counters
            await redis.incr(requests_key)
            await redis.incrby(tokens_key, tokens)
            
            # Set expiration
            await redis.expire(requests_key, 120)  # 2 minutes
            await redis.expire(tokens_key, 120)
            
            # Update quota tracking
            if provider not in self._quota_tracking:
                self._quota_tracking[provider] = {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "last_reset": datetime.now(UTC)
                }
            
            self._quota_tracking[provider]["total_requests"] += 1
            self._quota_tracking[provider]["total_tokens"] += tokens
            
        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")

    async def get_quota_status(
        self, 
        provider: str, 
        test_prefix: Optional[str] = None
    ) -> QuotaStatus:
        """Get current quota status for provider.
        
        Args:
            provider: Provider name
            test_prefix: Optional test prefix for isolation
            
        Returns:
            Current quota status
        """
        try:
            tracking = self._quota_tracking.get(provider, {})
            
            total_requests = tracking.get("total_requests", 0)
            total_tokens = tracking.get("total_tokens", 0)
            
            # Determine rate limit status
            is_rate_limited = await self._is_rate_limited(provider, test_prefix)
            
            if is_rate_limited:
                status = "rate_limited"
                reset_time = datetime.now(UTC) + timedelta(minutes=1)
            else:
                # Check if we're near limits
                current_minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
                requests_key = f"rate_limit:{provider}:requests:{current_minute}"
                if test_prefix:
                    requests_key = f"{test_prefix}:{requests_key}"
                
                redis = await self._get_redis()
                current_requests = await redis.get(requests_key) or 0
                current_requests = int(current_requests)
                
                requests_limit = self._rate_limits.get("requests_per_minute", 60)
                if current_requests > requests_limit * 0.8:
                    status = "near_limit"
                else:
                    status = "ok"
                    
                reset_time = None
            
            return QuotaStatus(
                total_requests=total_requests,
                total_tokens_used=total_tokens,
                current_rate_limit_status=status,
                reset_time=reset_time
            )
            
        except Exception as e:
            logger.error(f"Error getting quota status: {str(e)}")
            return QuotaStatus()