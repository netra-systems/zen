"""Structured LLM operations module.

Handles structured output generation, schema validation, and fallback parsing.
Each function must be  <= 8 lines as per architecture requirements.
"""
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from netra_backend.app.core.serialization.unified_json_handler import llm_parser
from netra_backend.app.llm.llm_response_processing import (
    attempt_json_fallback_parse,
    cache_structured_response,
    create_structured_cache_key,
    get_cached_structured_response,
    parse_nested_json_recursive,
    should_cache_structured_response,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.config import LLMConfig as GenerationConfig

logger = central_logger.get_logger(__name__)
T = TypeVar('T', bound=BaseModel)


class LLMStructuredOperations:
    """Structured LLM operations handler."""
    
    def __init__(self, core_operations) -> None:
        self.core = core_operations

    def get_structured_llm(self, name: str, schema: Type[T], 
                          generation_config: Optional[GenerationConfig] = None,
                          **kwargs) -> Any:
        """Get an LLM configured for structured output with a Pydantic schema."""
        llm = self.core.get_llm(name, generation_config)
        
        # All LLMs (including mocks) support with_structured_output
        return llm.with_structured_output(schema, **kwargs)
    
    async def ask_structured_llm(self, prompt: str, llm_config_name: str, 
                                 schema: Type[T], use_cache: bool = True,
                                 **kwargs) -> T:
        """Ask an LLM and get a structured response as a Pydantic model instance."""
        cache_key = create_structured_cache_key(prompt, llm_config_name, schema.__name__)
        
        cached_result = await self._try_get_cached_result(cache_key, llm_config_name, schema, use_cache)
        if cached_result:
            return cached_result
        
        return await self._generate_or_fallback(prompt, llm_config_name, schema, cache_key, use_cache, **kwargs)
    
    async def _try_get_cached_result(self, cache_key: str, llm_config_name: str, 
                                   schema: Type[T], use_cache: bool) -> Optional[T]:
        """Try to get cached result if caching is enabled."""
        if use_cache:
            return await get_cached_structured_response(cache_key, llm_config_name, schema)
        return None
    
    async def _generate_or_fallback(self, prompt: str, llm_config_name: str, schema: Type[T], 
                                  cache_key: str, use_cache: bool, **kwargs) -> T:
        """Generate structured response or use fallback parsing."""
        try:
            return await self._generate_structured_response(prompt, llm_config_name, schema, 
                                                          cache_key, use_cache, **kwargs)
        except Exception as e:
            return await self._handle_generation_failure(prompt, llm_config_name, schema, use_cache, e)
    
    async def _handle_generation_failure(self, prompt: str, llm_config_name: str, 
                                       schema: Type[T], use_cache: bool, 
                                       original_error: Exception) -> T:
        """Handle structured generation failure."""
        return await self._fallback_structured_parse(prompt, llm_config_name, schema, 
                                                   use_cache, original_error)
    
    async def _generate_structured_response(self, prompt: str, llm_config_name: str, 
                                          schema: Type[T], cache_key: str, 
                                          use_cache: bool, **kwargs) -> T:
        """Generate structured response using LLM."""
        structured_llm = self.get_structured_llm(llm_config_name, schema, **kwargs)
        response = await structured_llm.ainvoke(prompt)
        final_response = self._process_llm_response(response, schema)
        await self._handle_response_caching(use_cache, prompt, final_response, cache_key, llm_config_name)
        return final_response
    
    async def _handle_response_caching(self, use_cache: bool, prompt: str, 
                                     response: T, cache_key: str, 
                                     llm_config_name: str) -> None:
        """Handle response caching if needed."""
        await self._cache_structured_if_needed(use_cache, prompt, response, 
                                             cache_key, llm_config_name)
    
    def _process_llm_response(self, response: Any, schema: Type[T]) -> T:
        """Process LLM response and convert to structured format."""
        response_data = response.model_dump()
        parsed_data = parse_nested_json_recursive(response_data)
        return schema(**parsed_data)
    
    async def _fallback_structured_parse(self, prompt: str, llm_config_name: str, 
                                       schema: Type[T], use_cache: bool, 
                                       original_error: Exception) -> T:
        """Fallback to text generation and JSON parsing."""
        logger.error(f"Structured generation failed: {original_error}")
        try:
            return await self._try_text_fallback(prompt, llm_config_name, schema, use_cache)
        except Exception as parse_error:
            return self._handle_fallback_failure(parse_error, original_error)
    
    async def _try_text_fallback(self, prompt: str, llm_config_name: str, 
                               schema: Type[T], use_cache: bool) -> T:
        """Try text generation fallback."""
        text_response = await self.core.ask_llm(prompt, llm_config_name, use_cache)
        json_response = llm_parser.ensure_agent_response_is_json(text_response)
        return schema(**json_response)
    
    def _handle_fallback_failure(self, parse_error: Exception, 
                               original_error: Exception) -> None:
        """Handle fallback parsing failure."""
        logger.error(f"Fallback parsing also failed: {parse_error}")
        raise original_error
    
    async def _cache_structured_if_needed(self, use_cache: bool, prompt: str, 
                                        response: T, cache_key: str, 
                                        llm_config_name: str) -> None:
        """Cache structured response if appropriate."""
        response_json = response.model_dump_json()
        if use_cache and should_cache_structured_response(prompt, response_json):
            await cache_structured_response(cache_key, response_json, llm_config_name)