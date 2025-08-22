"""Modular LLM Manager - Main orchestration layer.

Coordinates LLM operations using focused modules while maintaining backward compatibility.
Each function must be ≤8 lines as per CLAUDE.md requirements.
"""
from typing import Any, AsyncIterator, Optional, Type, TypeVar

from pydantic import BaseModel

from netra_backend.app.llm.llm_core_operations import LLMCoreOperations
from netra_backend.app.llm.llm_management_utilities import LLMManagementUtilities
from netra_backend.app.llm.llm_response_processing import parse_nested_json_recursive
from netra_backend.app.llm.llm_structured_operations import LLMStructuredOperations
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.schemas.llm_base_types import (
    LLMConfigInfo,
    LLMHealthCheck,
    LLMManagerStats,
)
from netra_backend.app.schemas.llm_config_types import LLMConfig as GenerationConfig
from netra_backend.app.schemas.llm_response_types import LLMResponse

logger = central_logger.get_logger(__name__)
T = TypeVar('T', bound=BaseModel)


class LLMManager:
    """Main LLM manager coordinating modular operations."""
    
    def __init__(self, settings: AppConfig) -> None:
        self.settings = settings
        self._core = LLMCoreOperations(settings)
        self._structured = LLMStructuredOperations(self._core)
        self._management = LLMManagementUtilities(self._core)
        self.enabled = self._core.enabled

    def get_llm(self, name: str, generation_config: Optional[GenerationConfig] = None) -> Any:
        """Get LLM instance with caching."""
        return self._core.get_llm(name, generation_config)

    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        """Ask LLM and return response content as string."""
        return await self._core.ask_llm(prompt, llm_config_name, use_cache)
    
    async def ask_llm_full(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> LLMResponse:
        """Ask LLM and return full LLMResponse object with metadata."""
        return await self._core.ask_llm_full(prompt, llm_config_name, use_cache)

    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response content."""
        async for chunk in self._core.stream_llm(prompt, llm_config_name):
            yield chunk
    
    def get_structured_llm(self, name: str, schema: Type[T], 
                          generation_config: Optional[GenerationConfig] = None,
                          **kwargs) -> Any:
        """Get an LLM configured for structured output."""
        return self._structured.get_structured_llm(name, schema, generation_config, **kwargs)
    
    async def ask_structured_llm(self, prompt: str, llm_config_name: str, 
                                 schema: Type[T], use_cache: bool = True,
                                 **kwargs) -> T:
        """Ask an LLM and get a structured response."""
        return await self._structured.ask_structured_llm(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )
    
    def get_config_info(self, name: str) -> Optional[LLMConfigInfo]:
        """Get information about an LLM configuration."""
        return self._management.get_config_info(name)
    
    def get_manager_stats(self) -> LLMManagerStats:
        """Get LLM manager statistics."""
        return self._management.get_manager_stats()
    
    async def health_check(self, config_name: str) -> LLMHealthCheck:
        """Perform health check on an LLM configuration."""
        return await self._management.health_check(config_name)
    
    def _parse_nested_json(self, data: Any) -> Any:
        """Parse nested JSON strings within data structure for test compatibility."""
        return parse_nested_json_recursive(data)