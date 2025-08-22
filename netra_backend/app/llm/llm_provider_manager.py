"""LLM provider management module.

Handles LLM instance creation, caching, and provider configuration.
Each function must be ≤8 lines as per architecture requirements.
"""

from typing import Any, Dict, Optional

from netra_backend.app.llm.llm_config_manager import LLMConfigManager
from netra_backend.app.llm.llm_provider_handlers import (
    create_llm_for_provider,
    validate_provider_key,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.schemas.llm_base_types import LLMProvider
from netra_backend.app.schemas.llm_config_types import LLMConfig as GenerationConfig

logger = central_logger.get_logger(__name__)


class LLMProviderManager:
    """Manages LLM provider instances and caching."""
    
    def __init__(self, settings: AppConfig):
        """Initialize provider manager with settings."""
        self.settings = settings
        self._llm_cache: Dict[str, Any] = {}
        self.config_manager = LLMConfigManager(settings)
    
    def get_llm(self, name: str, generation_config: Optional[GenerationConfig] = None) -> Any:
        """Get LLM instance with caching."""
        if not self.config_manager.enabled:
            return self.config_manager._handle_disabled_llm(name)
        return self._get_cached_or_create_llm(name, generation_config)
    
    def _get_cached_or_create_llm(self, name: str, generation_config: Optional[GenerationConfig]) -> Any:
        """Get cached LLM or create new one."""
        cache_key = self._create_cache_key(name, generation_config)
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        return self._create_and_cache_llm(name, generation_config, cache_key)
    
    def _create_and_cache_llm(self, name: str, generation_config: Optional[GenerationConfig], cache_key: str) -> Any:
        """Create new LLM and cache if successful."""
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
        config = self._get_and_validate_config(name)
        self._validate_provider_requirements(config, name)
        final_config = self._merge_generation_config(config, generation_config)
        return self._build_llm_instance(config, final_config)
    
    def _build_llm_instance(self, config: Any, final_config: Dict[str, Any]) -> Optional[Any]:
        """Build LLM instance using provider and configuration."""
        return create_llm_for_provider(
            LLMProvider(config.provider), 
            config.model_name, 
            config.api_key, 
            final_config
        )
    
    def _get_and_validate_config(self, name: str) -> Any:
        """Get and validate LLM configuration."""
        config = self.settings.llm_configs.get(name)
        if not config:
            raise ValueError(f"LLM configuration for '{name}' not found.")
        return config
    
    def _validate_provider_requirements(self, config: Any, name: str) -> None:
        """Validate provider API key requirements."""
        if not validate_provider_key(LLMProvider(config.provider), config.api_key):
            if config.provider in ["google", "vertexai"]:
                raise ValueError(f"LLM '{name}': API key required for {config.provider}")
    
    def _apply_config_override(self, final_config: Dict[str, Any], override: GenerationConfig) -> None:
        """Apply generation config override to final config."""
        if isinstance(override, GenerationConfig):
            final_config.update(override.model_dump(exclude_unset=True))
        else:
            final_config.update(override)
    
    def _merge_generation_config(self, config: Any, override: Optional[GenerationConfig]) -> Dict[str, Any]:
        """Merge default and override generation configurations."""
        final_config = config.generation_config.copy()
        if override:
            self._apply_config_override(final_config, override)
        return final_config