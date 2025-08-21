"""LLM client retry functionality.

Provides retry logic with exponential backoff and jitter
for improved reliability in LLM operations.
"""

import asyncio
import random
from typing import Type, TypeVar
from netra_backend.app.core.async_retry_logic import with_retry
from netra_backend.app.llm.client_core import LLMCoreClient
from netra_backend.app.llm.llm_manager import LLMManager
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class RetryableLLMClient(LLMCoreClient):
    """LLM client with both circuit breakers and retry logic."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        """Initialize retryable LLM client."""
        super().__init__(llm_manager)
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def ask_llm_with_retry(self, 
                                prompt: str, 
                                llm_config_name: str, 
                                use_cache: bool = True) -> str:
        """Ask LLM with retry logic, jitter, and circuit breaker."""
        # Add jitter to prevent thundering herd
        await asyncio.sleep(random.uniform(0, 0.5))
        return await self.ask_llm(prompt, llm_config_name, use_cache)
    
    async def _call_structured_llm(self, prompt: str, config_name: str, 
                                  schema: Type[T], use_cache: bool, **kwargs) -> T:
        """Internal call to structured LLM."""
        return await self.ask_structured_llm(
            prompt, config_name, schema, use_cache, **kwargs
        )
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def ask_structured_llm_with_retry(self, prompt: str, llm_config_name: str, 
                                           schema: Type[T], use_cache: bool = True, **kwargs) -> T:
        """Ask structured LLM with retry logic and jitter."""
        # Add jitter to prevent thundering herd
        await asyncio.sleep(random.uniform(0, 0.5))
        return await self._call_structured_llm(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )