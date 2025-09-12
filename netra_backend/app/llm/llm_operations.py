"""LLM core operations module.

Provides main LLM operation functions: ask_llm, ask_llm_full, and stream_llm.
Each function must be  <= 8 lines as per architecture requirements.
"""

import time
from typing import Any, AsyncIterator, Optional, Tuple

from netra_backend.app.llm.llm_provider_manager import LLMProviderManager
from netra_backend.app.llm.llm_response_processing import (
    create_cached_llm_response,
    create_llm_response,
    stream_llm_response,
)
from netra_backend.app.llm.llm_utils import LLMUtils
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.schemas.config import AppConfig
from netra_backend.app.schemas.llm_response_types import LLMResponse
from netra_backend.app.services.llm_cache_service import llm_cache_service


class LLMOperations:
    """Core LLM operations handler."""
    
    def __init__(self, settings: AppConfig) -> None:
        """Initialize LLM operations with settings."""
        self.settings = settings
        self.provider_manager = LLMProviderManager(settings)
        self._last_response_chunks = []
        self.enabled = True  # Default to enabled for testing
    
    def get_llm(self, name: str, generation_config=None):
        """Get LLM instance - delegates to provider manager."""
        return self.provider_manager.get_llm(name, generation_config)
    
    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM and return response content as string for backward compatibility."""
        response = await self.ask_llm_full(prompt, llm_config_name, use_cache)
        return response.choices[0]["message"]["content"] if isinstance(response, LLMResponse) else response
    
    async def _try_get_cached_response(self, prompt: str, llm_config_name: str) -> Optional[LLMResponse]:
        """Try to get cached response if available."""
        cached_response = await llm_cache_service.get_cached_response(prompt, llm_config_name)
        if cached_response:
            config = self.settings.llm_configs.get(llm_config_name)
            return await create_cached_llm_response(cached_response, config, llm_config_name)
        return None
    
    async def ask_llm_full(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> LLMResponse:
        """Ask LLM and return full LLMResponse object with metadata."""
        if use_cache:
            cached_result = await self._try_get_cached_response(prompt, llm_config_name)
            if cached_result:
                return cached_result
        return await self._execute_llm_request(prompt, llm_config_name, use_cache)
    
    async def _process_llm_execution(self, prompt: str, llm_config_name: str, 
                                   correlation_id: str, use_cache: bool) -> LLMResponse:
        """Process LLM execution with timing and response creation."""
        start_time, llm = await self._prepare_llm_execution(llm_config_name, correlation_id, prompt)
        response, execution_time_ms = await self._execute_llm_call(llm, prompt, start_time)
        llm_response = await self._create_response_object(response, llm_config_name, execution_time_ms)
        await self._log_output_and_cache(llm_config_name, correlation_id, response, llm_response, use_cache, prompt)
        return llm_response
    
    async def _execute_llm_request(self, prompt: str, llm_config_name: str, use_cache: bool) -> LLMResponse:
        """Execute the actual LLM request with heartbeat and data logging."""
        correlation_id = generate_llm_correlation_id()
        self._start_heartbeat_if_enabled(correlation_id, llm_config_name)
        try:
            return await self._process_llm_execution(prompt, llm_config_name, correlation_id, use_cache)
        finally:
            self._stop_heartbeat_if_enabled(correlation_id)
    
    def _start_heartbeat_if_enabled(self, correlation_id: str, llm_config_name: str) -> None:
        """Start heartbeat logging if enabled."""
        if self.settings.llm_heartbeat_enabled:
            start_llm_heartbeat(correlation_id, llm_config_name)
    
    def _stop_heartbeat_if_enabled(self, correlation_id: str) -> None:
        """Stop heartbeat logging if enabled."""
        if self.settings.llm_heartbeat_enabled:
            stop_llm_heartbeat(correlation_id)
    
    async def _prepare_llm_execution(self, llm_config_name: str, correlation_id: str, prompt: str) -> Tuple[float, Any]:
        """Prepare LLM execution by getting LLM instance and logging input."""
        start_time = time.time()
        llm = self.provider_manager.get_llm(llm_config_name)
        if self.settings.llm_data_logging_enabled:
            LLMUtils.log_llm_input_data(llm_config_name, correlation_id, prompt, llm)
        return start_time, llm
    
    async def _execute_llm_call(self, llm: Any, prompt: str, start_time: float) -> Tuple[Any, float]:
        """Execute the actual LLM call and calculate execution time."""
        response = await llm.ainvoke(prompt)
        execution_time_ms = (time.time() - start_time) * 1000
        return response, execution_time_ms
    
    async def _create_response_object(self, response: Any, llm_config_name: str, execution_time_ms: float) -> Any:
        """Create LLM response object from raw response."""
        config = self.settings.llm_configs.get(llm_config_name)
        return await create_llm_response(response, config, llm_config_name, execution_time_ms)
    
    async def _log_output_and_cache(self, llm_config_name: str, correlation_id: str, response: Any, 
                                  llm_response: Any, use_cache: bool, prompt: str) -> None:
        """Log output data and cache response if needed."""
        if self.settings.llm_data_logging_enabled:
            LLMUtils.log_llm_output_data(llm_config_name, correlation_id, response, llm_response)
        await LLMUtils.cache_response_if_needed(use_cache, prompt, response.content, llm_config_name)
    
    async def _stream_and_collect_chunks(self, llm: Any, prompt: str) -> AsyncIterator[str]:
        """Stream LLM response and collect chunks for logging."""
        response_chunks = []
        async for chunk in stream_llm_response(llm, prompt):
            response_chunks.append(chunk)
            yield chunk
        # Store chunks for later logging access
        self._last_response_chunks = response_chunks
    
    async def _execute_streaming_process(self, prompt: str, llm_config_name: str, correlation_id: str) -> AsyncIterator[str]:
        """Execute the streaming process with LLM preparation and chunk collection."""
        llm = await self._prepare_streaming_llm(llm_config_name, correlation_id, prompt)
        async for chunk in self._stream_and_collect_chunks(llm, prompt):
            yield chunk
        await self._log_streaming_output_if_enabled(llm_config_name, correlation_id, self._last_response_chunks)
    
    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response content with heartbeat and data logging."""
        correlation_id = generate_llm_correlation_id()
        self._start_heartbeat_if_enabled(correlation_id, llm_config_name)
        async for chunk in self._stream_with_heartbeat_cleanup(prompt, llm_config_name, correlation_id):
            yield chunk
    
    async def _stream_with_heartbeat_cleanup(self, prompt: str, llm_config_name: str, 
                                           correlation_id: str) -> AsyncIterator[str]:
        """Stream with automatic heartbeat cleanup."""
        try:
            async for chunk in self._execute_streaming_process(prompt, llm_config_name, correlation_id):
                yield chunk
        finally:
            self._stop_heartbeat_if_enabled(correlation_id)
    
    async def _prepare_streaming_llm(self, llm_config_name: str, correlation_id: str, prompt: str) -> Any:
        """Prepare LLM for streaming by getting instance and logging input."""
        llm = self.provider_manager.get_llm(llm_config_name)
        if self.settings.llm_data_logging_enabled:
            LLMUtils.log_llm_input_data(llm_config_name, correlation_id, prompt, llm)
        return llm
    
    async def _log_streaming_output_if_enabled(self, llm_config_name: str, correlation_id: str, response_chunks: list) -> None:
        """Log streaming output data if logging is enabled."""
        if self.settings.llm_data_logging_enabled:
            full_response = "".join(response_chunks)
            LLMUtils.log_llm_output_data(llm_config_name, correlation_id, full_response, None)