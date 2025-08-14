from typing import Any, Dict, Optional, Type, TypeVar, List, AsyncIterator
from app.schemas import AppConfig
from app.schemas.llm_types import (
    GenerationConfig, LLMResponse, LLMStreamChunk, LLMCacheEntry,
    StructuredLLMResponse, LLMConfigInfo, LLMManagerStats, 
    MockLLMResponse, LLMValidationError, LLMHealthCheck,
    BatchLLMRequest, BatchLLMResponse, LLMProvider
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger
from pydantic import BaseModel
import json
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
        for word in f"[Dev Mode - LLM Disabled] Mock streaming response for: {prompt[:50]}...".split():
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
        # Create a mock instance with minimal required fields
        mock_data = {}
        for field_name, field_info in self.schema.model_fields.items():
            if field_info.is_required():
                # Provide mock values based on field type
                annotation = field_info.annotation
                
                # Handle basic types
                if annotation == str:
                    mock_data[field_name] = f"[Mock {field_name}]"
                elif annotation == float:
                    mock_data[field_name] = 0.5
                elif annotation == int:
                    mock_data[field_name] = 1
                elif annotation == bool:
                    mock_data[field_name] = False
                elif annotation == dict:
                    mock_data[field_name] = {}
                elif annotation == list:
                    mock_data[field_name] = []
                elif hasattr(annotation, '__origin__'):
                    # Handle generic types like List, Dict, Optional
                    origin = annotation.__origin__
                    if origin == list:
                        mock_data[field_name] = []
                    elif origin == dict:
                        mock_data[field_name] = {}
                    else:
                        # For Optional and other types, try to get first arg
                        mock_data[field_name] = None
                else:
                    # For other types, provide empty dict for dict-like types
                    mock_data[field_name] = {}
        
        return self.schema(**mock_data)

class LLMManager:
    def __init__(self, settings: AppConfig) -> None:
        self.settings = settings
        self._llm_cache: Dict[str, Any] = {}
        self.enabled = self._check_if_enabled()

    def _check_if_enabled(self) -> None:
        """Check if LLMs should be enabled based on service mode configuration."""
        import os
        
        # Check service mode from environment (set by dev launcher)
        llm_mode = os.environ.get("LLM_MODE", "shared").lower()
        
        if llm_mode == "disabled":
            logger.info("LLMs are disabled (mode: disabled)")
            return False
        elif llm_mode == "mock":
            logger.info("LLMs are running in mock mode")
            return False  # Use mock implementation
        
        if self.settings.environment == "development":
            enabled = self.settings.dev_mode_llm_enabled
            if not enabled:
                logger.info("LLMs are disabled in development configuration")
            return enabled
        # LLMs are always enabled in production and testing
        return True

    def get_llm(self, name: str, generation_config: Optional[GenerationConfig] = None) -> Any:
        # Return mock LLM if disabled in dev mode
        if not self.enabled:
            logger.debug(f"Returning mock LLM for '{name}' - LLMs disabled in dev mode")
            return MockLLM(name)
        
        cache_key = name
        if generation_config:
            # Create a unique cache key for this combination of name and generation_config
            cache_key += str(sorted(generation_config.items()))

        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        config = self.settings.llm_configs.get(name)
        if not config:
            raise ValueError(f"LLM configuration for '{name}' not found.")

        # Check if API key is available for branded LLMs
        # Skip initialization if no key provided for optional providers
        if not config.api_key:
            if config.provider in [LLMProvider.GOOGLE, LLMProvider.VERTEXAI]:
                # Gemini/Google/VertexAI is required
                raise ValueError(f"LLM '{name}': Gemini API key is required for {config.provider.value} provider")
            else:
                # Other providers are optional - skip if no key
                logger.info(f"Skipping LLM '{name}' initialization - no API key provided for {config.provider.value}")
                return None

        # Merge the default generation config with the override
        final_generation_config = config.generation_config.copy()
        if generation_config:
            if isinstance(generation_config, GenerationConfig):
                final_generation_config.update(generation_config.model_dump(exclude_unset=True))
            else:
                final_generation_config.update(generation_config)

        if config.provider == LLMProvider.GOOGLE:
            # Defer genai.configure until a Google model is actually used
            llm = ChatGoogleGenerativeAI(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        elif config.provider == LLMProvider.OPENAI:
            llm = ChatOpenAI(
                model_name=config.model_name,
                api_key=config.api_key,
                **final_generation_config,
            )
        elif config.provider == LLMProvider.ANTHROPIC:
            # Import only if needed
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        elif config.provider == LLMProvider.COHERE:
            # Import only if needed
            from langchain_cohere import ChatCohere
            llm = ChatCohere(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        elif config.provider == "mistral":
            # Import only if needed
            from langchain_mistralai import ChatMistralAI
            llm = ChatMistralAI(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        elif config.provider == LLMProvider.VERTEXAI:
            # Use same implementation as google for now
            # Both use Gemini models but via different endpoints
            logger.info(f"Using Google Gemini for VertexAI provider")
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        else:
            logger.warning(f"Unsupported LLM provider: {config.provider} - skipping initialization")
            return None

        self._llm_cache[cache_key] = llm
        return llm

    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM and return response content as string for backward compatibility."""
        response = await self.ask_llm_full(prompt, llm_config_name, use_cache)
        return response.choices[0]["message"]["content"] if isinstance(response, LLMResponse) else response
    
    async def ask_llm_full(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> LLMResponse:
        """Ask LLM and return full LLMResponse object with metadata."""
        # Check cache first if enabled
        if use_cache:
            cached_response = await llm_cache_service.get_cached_response(prompt, llm_config_name)
            if cached_response:
                # Return cached response as simple string-based response
                config = self.settings.llm_configs.get(llm_config_name)
                provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
                from app.schemas.llm_types import TokenUsage
                return LLMResponse(
                    provider=provider,
                    model=config.model_name if config else llm_config_name,
                    choices=[{
                        "message": {"content": cached_response},
                        "finish_reason": "stop",
                        "index": 0
                    }],
                    usage=TokenUsage(),
                    response_time_ms=0,
                    cached=True
                )
        
        # Make LLM call
        start_time = time.time()
        llm = self.get_llm(llm_config_name)
        response = await llm.ainvoke(prompt)
        execution_time_ms = (time.time() - start_time) * 1000
        
        response_content = response.content
        
        # Get provider from config
        config = self.settings.llm_configs.get(llm_config_name)
        provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
        
        # Create typed response with required fields
        from app.schemas.llm_types import TokenUsage
        llm_response = LLMResponse(
            provider=provider,
            model=getattr(response, 'model', config.model_name if config else llm_config_name),
            choices=[{
                "message": {"content": response_content},
                "finish_reason": getattr(response, 'finish_reason', 'stop'),
                "index": 0
            }],
            usage=TokenUsage(
                prompt_tokens=getattr(response, 'prompt_tokens', 0),
                completion_tokens=getattr(response, 'completion_tokens', 0),
                total_tokens=getattr(response, 'total_tokens', 0)
            ),
            response_time_ms=execution_time_ms
        )
        
        # Cache the response if appropriate
        if use_cache and llm_cache_service.should_cache_response(prompt, response_content):
            await llm_cache_service.cache_response(prompt, response_content, llm_config_name)
        
        return llm_response

    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        llm = self.get_llm(llm_config_name)
        async for chunk in llm.astream(prompt):
            yield chunk.content
    
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
        """Ask an LLM and get a structured response as a Pydantic model instance.
        
        Args:
            prompt: The prompt to send to the LLM
            llm_config_name: The LLM configuration to use
            schema: The Pydantic model class for the response
            use_cache: Whether to use response caching
            **kwargs: Additional parameters for with_structured_output
            
        Returns:
            An instance of the schema with the LLM's response
        """
        # Check cache first if enabled
        cache_key = f"{prompt}_{llm_config_name}_{schema.__name__}"
        if use_cache:
            cached_response = await llm_cache_service.get_cached_response(cache_key, llm_config_name)
            if cached_response:
                try:
                    # Parse cached JSON back to Pydantic model
                    return schema.model_validate_json(cached_response)
                except Exception as e:
                    logger.warning(f"Failed to parse cached structured response: {e}")
        
        # Get structured LLM and make the call
        structured_llm = self.get_structured_llm(llm_config_name, schema, **kwargs)
        
        try:
            response = await structured_llm.ainvoke(prompt)
            
            # Parse any nested JSON strings in the response
            response_data = response.model_dump()
            parsed_data = self._parse_nested_json(response_data)
            response = schema(**parsed_data)
            
            # Cache the response if appropriate
            if use_cache and llm_cache_service.should_cache_response(prompt, response.model_dump_json()):
                await llm_cache_service.cache_response(
                    cache_key, 
                    response.model_dump_json(), 
                    llm_config_name
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            # Try fallback to regular text generation and parse
            try:
                text_response = await self.ask_llm(prompt, llm_config_name, use_cache)
                # Attempt to parse as JSON
                if text_response.strip().startswith('{'):
                    data = json.loads(text_response)
                    # Parse nested JSON strings
                    data = self._parse_nested_json(data)
                    return schema(**data)
                else:
                    # If not JSON, raise the original error
                    raise e
            except Exception as parse_error:
                logger.error(f"Fallback parsing also failed: {parse_error}")
                raise e
    
    def _parse_nested_json(self, data: Any) -> Any:
        """Recursively parse JSON strings within a data structure."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Try to parse as JSON
                    try:
                        if value.strip().startswith(('{', '[')):
                            parsed = json.loads(value)
                            # Recursively parse in case of nested JSON strings
                            result[key] = self._parse_nested_json(parsed)
                        else:
                            result[key] = value
                    except (json.JSONDecodeError, ValueError):
                        result[key] = value
                else:
                    result[key] = self._parse_nested_json(value)
            return result
        elif isinstance(data, list):
            return [self._parse_nested_json(item) for item in data]
        else:
            return data
    
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