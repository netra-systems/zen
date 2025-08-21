"""Unified LLM client interface.

Combines all LLM client components into a single unified interface
that provides core operations, streaming, health monitoring, and retry functionality.
"""

from typing import Any, AsyncIterator, Dict, Type, TypeVar

from pydantic import BaseModel

from netra_backend.app.llm.client_core import LLMCoreClient
from netra_backend.app.llm.client_health import LLMHealthMonitor
from netra_backend.app.llm.client_retry import RetryableLLMClient
from netra_backend.app.llm.client_streaming import LLMStreamingClient
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.llm_response_types import LLMResponse

T = TypeVar('T', bound=BaseModel)


class ResilientLLMClient:
    """Production LLM client with circuit breaker protection."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        """Initialize unified resilient LLM client."""
        self.core_client = LLMCoreClient(llm_manager)
        self.streaming_client = LLMStreamingClient(llm_manager)
        self.health_monitor = LLMHealthMonitor(llm_manager)
    
    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM with circuit breaker protection."""
        return await self.core_client.ask_llm(prompt, llm_config_name, use_cache)
    
    async def ask_llm_full(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> LLMResponse:
        """Ask LLM for full response with circuit breaker."""
        return await self.core_client.ask_llm_full(prompt, llm_config_name, use_cache)
    
    async def ask_structured_llm(self, prompt: str, llm_config_name: str, 
                                schema: Type[T], use_cache: bool = True, **kwargs) -> T:
        """Ask LLM for structured output with circuit breaker."""
        return await self.core_client.ask_structured_llm(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )
    
    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response with circuit breaker protection."""
        async for chunk in self.streaming_client.stream_llm(prompt, llm_config_name):
            yield chunk
    
    async def health_check(self, config_name: str) -> Dict[str, Any]:
        """Comprehensive health check for LLM configuration."""
        return await self.health_monitor.health_check(config_name)
    
    async def get_all_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all LLM circuits."""
        return await self.health_monitor.get_all_circuit_status()


class RetryableUnifiedClient(ResilientLLMClient):
    """LLM client with both circuit breakers and retry logic."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        """Initialize retryable unified LLM client."""
        super().__init__(llm_manager)
        self.retry_client = RetryableLLMClient(llm_manager)
    
    async def ask_llm_with_retry(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM with retry logic, jitter, and circuit breaker."""
        return await self.retry_client.ask_llm_with_retry(prompt, llm_config_name, use_cache)
    
    async def ask_structured_llm_with_retry(self, prompt: str, llm_config_name: str, 
                                           schema: Type[T], use_cache: bool = True, **kwargs) -> T:
        """Ask structured LLM with retry logic and jitter."""
        return await self.retry_client.ask_structured_llm_with_retry(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )