"""Core LLM operations module.

Handles basic LLM operations including caching, configuration management,
and standard text generation. Each function must be ≤8 lines as per architecture requirements.
"""
from typing import Any, Dict, Optional, AsyncIterator
from app.schemas import AppConfig
from app.schemas.llm_base_types import LLMProvider
from app.schemas.llm_config_types import LLMConfig as GenerationConfig
from app.schemas.llm_response_types import LLMResponse
# Only import MockLLM for development mode to avoid test dependencies in production
try:
    from app.tests.helpers.llm_mocks import MockLLM
except ImportError:
    MockLLM = None
from app.core.exceptions_service import ServiceUnavailableError
from app.llm.llm_provider_handlers import create_llm_for_provider, validate_provider_key
from app.llm.llm_response_processing import create_cached_llm_response, create_llm_response, stream_llm_response
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger
from app.llm.observability import generate_llm_correlation_id, start_llm_heartbeat, stop_llm_heartbeat, get_heartbeat_logger, get_data_logger, log_llm_input, log_llm_output
import time

logger = central_logger.get_logger(__name__)


class LLMCoreOperations:
    """Core LLM operations handler."""
    
    def __init__(self, settings: AppConfig) -> None:
        self.settings = settings
        self._llm_cache: Dict[str, Any] = {}
        self.enabled = self._check_if_enabled()
        self._configure_heartbeat_logger()

    def _configure_heartbeat_logger(self) -> None:
        """Configure the heartbeat logger with settings."""
        heartbeat_logger = get_heartbeat_logger()
        heartbeat_logger.interval_seconds = self.settings.llm_heartbeat_interval_seconds
        heartbeat_logger.log_as_json = self.settings.llm_heartbeat_log_json
        self._configure_data_logger()

    def _configure_data_logger(self) -> None:
        """Configure the data logger with settings."""
        data_logger = get_data_logger()
        data_logger.truncate_length = self.settings.llm_data_truncate_length
        data_logger.json_depth = self.settings.llm_data_json_depth
        data_logger.log_format = self.settings.llm_data_log_format

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

    def _handle_disabled_llm(self, name: str) -> Any:
        """Handle disabled LLM based on environment - dev gets mock, production gets error."""
        if self.settings.environment == "development" and MockLLM is not None:
            logger.debug(f"Returning mock LLM for '{name}' - LLMs disabled in dev mode")
            return MockLLM(name)
        
        error_msg = f"LLM '{name}' is not available - LLM service is disabled"
        logger.error(error_msg)
        raise ServiceUnavailableError(error_msg)

    def get_llm(self, name: str, generation_config: Optional[GenerationConfig] = None) -> Any:
        """Get LLM instance with caching."""
        if not self.enabled:
            return self._handle_disabled_llm(name)
        
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
        """Execute the actual LLM request with heartbeat and data logging."""
        correlation_id = generate_llm_correlation_id()
        if self.settings.llm_heartbeat_enabled:
            start_llm_heartbeat(correlation_id, llm_config_name)
        
        try:
            start_time = time.time()
            llm = self.get_llm(llm_config_name)
            
            # Log input data if enabled
            if self.settings.llm_data_logging_enabled:
                self._log_llm_input(llm_config_name, correlation_id, prompt, llm)
            
            response = await llm.ainvoke(prompt)
            execution_time_ms = (time.time() - start_time) * 1000
            
            config = self.settings.llm_configs.get(llm_config_name)
            llm_response = await create_llm_response(response, config, llm_config_name, execution_time_ms)
            
            # Log output data if enabled
            if self.settings.llm_data_logging_enabled:
                self._log_llm_output(llm_config_name, correlation_id, response, llm_response)
            
            await self._cache_response_if_needed(use_cache, prompt, response.content, llm_config_name)
            return llm_response
        finally:
            if self.settings.llm_heartbeat_enabled:
                stop_llm_heartbeat(correlation_id)
    
    def _log_llm_input(self, agent_name: str, correlation_id: str, prompt: str, llm: Any) -> None:
        """Log LLM input data for debugging."""
        params = self._extract_llm_params(llm)
        log_llm_input(agent_name, correlation_id, prompt, params)

    def _log_llm_output(self, agent_name: str, correlation_id: str, response: Any, llm_response: Any) -> None:
        """Log LLM output data for debugging."""
        response_content = self._extract_response_content(response)
        token_count = self._extract_token_count_from_response(response, llm_response)
        log_llm_output(agent_name, correlation_id, response_content, token_count)

    def _extract_llm_params(self, llm: Any) -> Dict[str, Any]:
        """Extract parameters from LLM instance."""
        params = {}
        if hasattr(llm, 'model_name'):
            params['model'] = llm.model_name
        if hasattr(llm, 'temperature'):
            params['temperature'] = llm.temperature
        return params

    def _extract_response_content(self, response: Any) -> str:
        """Extract content from LLM response."""
        if hasattr(response, 'content'):
            return response.content
        if isinstance(response, str):
            return response
        return str(response)

    def _extract_token_count_from_response(self, response: Any, llm_response: Any) -> Optional[int]:
        """Extract token count from response objects."""
        data_logger = get_data_logger()
        token_count = data_logger._extract_token_count(response)
        if token_count is None and hasattr(llm_response, 'usage'):
            token_count = getattr(llm_response.usage, 'total_tokens', None)
        return token_count

    async def _cache_response_if_needed(self, use_cache: bool, prompt: str, 
                                      content: str, llm_config_name: str) -> None:
        """Cache response if caching is enabled and appropriate."""
        if use_cache and llm_cache_service.should_cache_response(prompt, content):
            await llm_cache_service.cache_response(prompt, content, llm_config_name)

    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response content with heartbeat and data logging."""
        correlation_id = generate_llm_correlation_id()
        if self.settings.llm_heartbeat_enabled:
            start_llm_heartbeat(correlation_id, llm_config_name)
        
        try:
            llm = self.get_llm(llm_config_name)
            
            # Log input data if enabled
            if self.settings.llm_data_logging_enabled:
                self._log_llm_input(llm_config_name, correlation_id, prompt, llm)
            
            response_chunks = []
            async for chunk in stream_llm_response(llm, prompt):
                response_chunks.append(chunk)
                yield chunk
            
            # Log output data if enabled
            if self.settings.llm_data_logging_enabled:
                full_response = "".join(response_chunks)
                log_llm_output(llm_config_name, correlation_id, full_response, None)
                
        finally:
            if self.settings.llm_heartbeat_enabled:
                stop_llm_heartbeat(correlation_id)