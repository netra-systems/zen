"""Core LLM operations module.

Handles basic LLM operations including caching, configuration management,
and standard text generation. Each function must be ≤8 lines as per architecture requirements.
"""
from typing import Any, Dict, Optional, AsyncIterator
from app.schemas import AppConfig
from app.schemas.llm_base_types import LLMProvider
from app.schemas.llm_config_types import LLMConfig as GenerationConfig
from app.schemas.llm_response_types import LLMResponse
from app.llm.llm_mocks import MockLLM
from app.llm.llm_provider_handlers import create_llm_for_provider, validate_provider_key
from app.llm.llm_response_processing import create_cached_llm_response, create_llm_response, stream_llm_response
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger
import time

logger = central_logger.get_logger(__name__)


class LLMCoreOperations:
    """Core LLM operations handler."""
    
    def __init__(self, settings: AppConfig) -> None:
        self.settings = settings
        self._llm_cache: Dict[str, Any] = {}
        self.enabled = self._check_if_enabled()

    def _check_if_enabled(self) -> bool:
        """Check if LLMs should be enabled based on service mode configuration."""
        import os
        llm_mode = os.environ.get("LLM_MODE", "shared").lower()
        if llm_mode in ["disabled", "mock"]:
            logger.info(f"LLMs are disabled (mode: {llm_mode})")
            return False
        return self._check_environment_enabled()

    def _check_environment_enabled(self) -> bool:
        """Check environment-specific LLM enablement."""
        if self.settings.environment == "development":
            return self._check_dev_enabled()
        return True

    def _check_dev_enabled(self) -> bool:
        """Check if LLMs are enabled in development."""
        enabled = self.settings.dev_mode_llm_enabled
        if not enabled:
            logger.info("LLMs are disabled in development configuration")
        return enabled

    def get_llm(self, name: str, generation_config: Optional[GenerationConfig] = None) -> Any:
        """Get LLM instance with caching."""
        if not self.enabled:
            logger.debug(f"Returning mock LLM for '{name}' - LLMs disabled")
            return MockLLM(name)
        
        cache_key = self._create_cache_key(name, generation_config)
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        llm = self._create_new_llm(name, generation_config)
        if llm:
            self._llm_cache[cache_key] = llm
        return llm
    
    def _create_cache_key(self, name: str, generation_config: Optional[GenerationConfig]) -> str:
        """Create cache key for LLM configuration."""
        cache_key = name
        if generation_config:
            cache_key += str(sorted(generation_config.items()))
        return cache_key
    
    def _create_new_llm(self, name: str, generation_config: Optional[GenerationConfig]) -> Optional[Any]:
        """Create new LLM instance for given configuration."""
        config = self.settings.llm_configs.get(name)
        if not config:
            raise ValueError(f"LLM configuration for '{name}' not found.")
        
        if not validate_provider_key(LLMProvider(config.provider), config.api_key):
            if config.provider in ["google", "vertexai"]:
                raise ValueError(f"LLM '{name}': API key required for {config.provider}")
            return None
        
        final_config = self._merge_generation_config(config, generation_config)
        return create_llm_for_provider(
            LLMProvider(config.provider), 
            config.model_name, 
            config.api_key, 
            final_config
        )
    
    def _merge_generation_config(self, config: Any, override: Optional[GenerationConfig]) -> Dict[str, Any]:
        """Merge default and override generation configurations."""
        final_config = config.generation_config.copy()
        if override:
            if isinstance(override, GenerationConfig):
                final_config.update(override.model_dump(exclude_unset=True))
            else:
                final_config.update(override)
        return final_config

    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM and return response content as string for backward compatibility."""
        response = await self.ask_llm_full(prompt, llm_config_name, use_cache)
        return response.choices[0]["message"]["content"] if isinstance(response, LLMResponse) else response
    
    async def ask_llm_full(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> LLMResponse:
        """Ask LLM and return full LLMResponse object with metadata."""
        if use_cache:
            cached_response = await llm_cache_service.get_cached_response(prompt, llm_config_name)
            if cached_response:
                config = self.settings.llm_configs.get(llm_config_name)
                return await create_cached_llm_response(cached_response, config, llm_config_name)
        
        return await self._execute_llm_request(prompt, llm_config_name, use_cache)
    
    async def _execute_llm_request(self, prompt: str, llm_config_name: str, use_cache: bool) -> LLMResponse:
        """Execute the actual LLM request."""
        start_time = time.time()
        llm = self.get_llm(llm_config_name)
        response = await llm.ainvoke(prompt)
        execution_time_ms = (time.time() - start_time) * 1000
        
        config = self.settings.llm_configs.get(llm_config_name)
        llm_response = await create_llm_response(response, config, llm_config_name, execution_time_ms)
        
        await self._cache_response_if_needed(use_cache, prompt, response.content, llm_config_name)
        return llm_response
    
    async def _cache_response_if_needed(self, use_cache: bool, prompt: str, 
                                      content: str, llm_config_name: str) -> None:
        """Cache response if caching is enabled and appropriate."""
        if use_cache and llm_cache_service.should_cache_response(prompt, content):
            await llm_cache_service.cache_response(prompt, content, llm_config_name)

    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response content."""
        llm = self.get_llm(llm_config_name)
        async for chunk in stream_llm_response(llm, prompt):
            yield chunk