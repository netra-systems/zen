from typing import Any, Dict, Optional, Type, TypeVar, AsyncIterator
from app.schemas import AppConfig
from app.schemas.llm_types import (
    GenerationConfig, LLMResponse, LLMConfigInfo, LLMManagerStats,
    LLMHealthCheck, LLMProvider
)
from app.llm.llm_provider_handlers import (
    create_llm_for_provider, validate_provider_key
)
from app.llm.llm_response_processing import (
    stream_llm_response, create_mock_structured_response,
    parse_nested_json_recursive, create_cached_llm_response,
    create_llm_response, attempt_json_fallback_parse,
    create_structured_cache_key, get_cached_structured_response,
    cache_structured_response, should_cache_structured_response
)
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger
from pydantic import BaseModel
import time
from datetime import datetime

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)

class MockLLM:
    """Mock LLM for when LLMs are disabled in dev mode."""
    
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
    
    async def ainvoke(self, prompt: str) -> Any:
        class MockResponse:
            content = f"[Dev Mode - LLM Disabled] Mock response for: {prompt[:100]}..."
        return MockResponse()
    
    async def astream(self, prompt: str) -> AsyncIterator[Any]:
        words = f"[Dev Mode - LLM Disabled] Mock streaming response for: {prompt[:50]}...".split()
        for word in words:
            yield type('obj', (object,), {'content': word + ' '})()
    
    def with_structured_output(self, schema: Type[T], **kwargs) -> 'MockStructuredLLM':
        """Return a mock structured LLM for dev mode."""
        return MockStructuredLLM(self.model_name, schema)


class MockStructuredLLM:
    """Mock structured LLM for when LLMs are disabled in dev mode."""
    
    def __init__(self, model_name: str, schema: Type[T]) -> None:
        self.model_name = model_name
        self.schema = schema
    
    async def ainvoke(self, prompt: str) -> T:
        """Return a mock instance of the schema with default values."""
        return create_mock_structured_response(self.schema)

class LLMManager:
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
    
    def get_structured_llm(self, name: str, schema: Type[T], 
                          generation_config: Optional[GenerationConfig] = None,
                          **kwargs) -> Any:
        """Get an LLM configured for structured output with a Pydantic schema.
        
        Args:
            name: The LLM configuration name
            schema: The Pydantic model class for structured output
            generation_config: Optional generation config overrides
            **kwargs: Additional parameters for with_structured_output
            
        Returns:
            An LLM instance configured for structured output
        """
        llm = self.get_llm(name, generation_config)
        
        # Mock LLMs already have with_structured_output
        if isinstance(llm, MockLLM):
            return llm.with_structured_output(schema, **kwargs)
        
        # For LangChain models, use with_structured_output
        return llm.with_structured_output(schema, **kwargs)
    
    async def ask_structured_llm(self, prompt: str, llm_config_name: str, 
                                 schema: Type[T], use_cache: bool = True,
                                 **kwargs) -> T:
        """Ask an LLM and get a structured response as a Pydantic model instance."""
        cache_key = create_structured_cache_key(prompt, llm_config_name, schema.__name__)
        
        if use_cache:
            cached_result = await get_cached_structured_response(cache_key, llm_config_name, schema)
            if cached_result:
                return cached_result
        
        try:
            return await self._generate_structured_response(prompt, llm_config_name, schema, 
                                                          cache_key, use_cache, **kwargs)
        except Exception as e:
            return await self._fallback_structured_parse(prompt, llm_config_name, schema, 
                                                       use_cache, e)
    
    async def _generate_structured_response(self, prompt: str, llm_config_name: str, 
                                          schema: Type[T], cache_key: str, 
                                          use_cache: bool, **kwargs) -> T:
        """Generate structured response using LLM."""
        structured_llm = self.get_structured_llm(llm_config_name, schema, **kwargs)
        response = await structured_llm.ainvoke(prompt)
        
        response_data = response.model_dump()
        parsed_data = parse_nested_json_recursive(response_data)
        final_response = schema(**parsed_data)
        
        await self._cache_structured_if_needed(use_cache, prompt, final_response, 
                                             cache_key, llm_config_name)
        return final_response
    
    async def _fallback_structured_parse(self, prompt: str, llm_config_name: str, 
                                       schema: Type[T], use_cache: bool, 
                                       original_error: Exception) -> T:
        """Fallback to text generation and JSON parsing."""
        logger.error(f"Structured generation failed: {original_error}")
        try:
            text_response = await self.ask_llm(prompt, llm_config_name, use_cache)
            return attempt_json_fallback_parse(text_response, schema)
        except Exception as parse_error:
            logger.error(f"Fallback parsing also failed: {parse_error}")
            raise original_error
    
    async def _cache_structured_if_needed(self, use_cache: bool, prompt: str, 
                                        response: T, cache_key: str, 
                                        llm_config_name: str) -> None:
        """Cache structured response if appropriate."""
        response_json = response.model_dump_json()
        if use_cache and should_cache_structured_response(prompt, response_json):
            await cache_structured_response(cache_key, response_json, llm_config_name)
    
    
    def get_config_info(self, name: str) -> Optional[LLMConfigInfo]:
        """Get information about an LLM configuration."""
        config = self.settings.llm_configs.get(name)
        if not config:
            return None
        
        return LLMConfigInfo(
            name=name,
            provider=LLMProvider(config.provider),
            model_name=config.model_name,
            api_key_configured=bool(config.api_key),
            generation_config=GenerationConfig(**config.generation_config),
            enabled=bool(config.api_key) if config.provider == "google" else True
        )
    
    def get_manager_stats(self) -> LLMManagerStats:
        """Get LLM manager statistics."""
        active_configs = [name for name, config in self.settings.llm_configs.items() 
                         if config.api_key or config.provider != "google"]
        
        return LLMManagerStats(
            total_requests=0,  # Would need to implement request tracking
            cached_responses=0,  # Would need to implement cache tracking
            cache_hit_rate=0.0,
            average_response_time_ms=0.0,
            active_configs=active_configs,
            enabled=self.enabled
        )
    
    async def health_check(self, config_name: str) -> LLMHealthCheck:
        """Perform health check on an LLM configuration."""
        start_time = time.time()
        try:
            # Simple test prompt
            test_response = await self.ask_llm("Hello", config_name, use_cache=False)
            response_time_ms = (time.time() - start_time) * 1000
            
            return LLMHealthCheck(
                config_name=config_name,
                healthy=bool(test_response),
                response_time_ms=response_time_ms,
                last_checked=datetime.utcnow()
            )
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return LLMHealthCheck(
                config_name=config_name,
                healthy=False,
                response_time_ms=response_time_ms,
                error=str(e),
                last_checked=datetime.utcnow()
            )
    
    def _parse_nested_json(self, data: Any) -> Any:
        """Parse nested JSON strings within data structure."""
        return parse_nested_json_recursive(data)