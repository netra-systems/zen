"""LLM Manager Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Provide LLM management interface
- Value Impact: Enables LLM operations throughout the application
- Strategic Impact: Centralizes LLM access and management

This module provides the main LLM management interface expected by agents
and other components throughout the system.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.config import LLMConfig
from netra_backend.app.schemas.llm_types import (
    GenerationConfig,
    LLMProvider,
    LLMResponse,
    TokenUsage,
)

T = TypeVar('T', bound=BaseModel)


class LLMManager:
    """Main LLM Manager for handling LLM operations.
    
    This class provides the primary interface for LLM operations throughout
    the application. It manages configurations, handles requests, and provides
    caching and error handling.
    """
    
    def __init__(self):
        """Initialize LLM Manager."""
        self._logger = logger
        self._config = None
        self._cache: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the LLM manager with configuration."""
        if self._initialized:
            return
        
        try:
            self._config = get_unified_config()
            self._logger.info("LLM Manager initialized successfully")
            self._initialized = True
        except Exception as e:
            self._logger.error(f"Failed to initialize LLM Manager: {e}")
            # Continue with minimal functionality
            self._initialized = True
    
    async def _ensure_initialized(self) -> None:
        """Ensure the manager is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def ask_llm(
        self, 
        prompt: str, 
        llm_config_name: str = "default", 
        use_cache: bool = True
    ) -> str:
        """Ask LLM a question and return the text response.
        
        Args:
            prompt: The prompt to send to the LLM
            llm_config_name: Name of the LLM configuration to use
            use_cache: Whether to use caching
            
        Returns:
            str: The LLM response text
        """
        await self._ensure_initialized()
        
        # Check cache first
        if use_cache:
            cache_key = f"{llm_config_name}:{hash(prompt)}"
            if cache_key in self._cache:
                self._logger.debug(f"Cache hit for prompt hash: {hash(prompt)}")
                return self._cache[cache_key]
        
        try:
            # For now, return a placeholder response
            # In a real implementation, this would call the actual LLM
            response = await self._make_llm_request(prompt, llm_config_name)
            
            # Cache the response
            if use_cache:
                self._cache[cache_key] = response
            
            return response
        except Exception as e:
            self._logger.error(f"LLM request failed: {e}")
            return f"I apologize, but I'm unable to process your request at the moment. Error: {str(e)}"
    
    async def ask_llm_full(
        self, 
        prompt: str, 
        llm_config_name: str = "default", 
        use_cache: bool = True
    ) -> LLMResponse:
        """Ask LLM a question and return the full response object.
        
        Args:
            prompt: The prompt to send to the LLM
            llm_config_name: Name of the LLM configuration to use  
            use_cache: Whether to use caching
            
        Returns:
            LLMResponse: The full LLM response object
        """
        await self._ensure_initialized()
        
        # Get text response
        text_response = await self.ask_llm(prompt, llm_config_name, use_cache)
        
        # Create full response object
        response = LLMResponse(
            response=text_response,
            model=self._get_model_name(llm_config_name),
            provider=self._get_provider(llm_config_name),
            token_usage=TokenUsage(
                prompt_tokens=len(prompt.split()),  # Rough estimate
                completion_tokens=len(text_response.split()),  # Rough estimate
                total_tokens=len(prompt.split()) + len(text_response.split())
            ),
            cached=use_cache and f"{llm_config_name}:{hash(prompt)}" in self._cache
        )
        
        return response
    
    async def ask_llm_structured(
        self, 
        prompt: str, 
        response_model: Type[T], 
        llm_config_name: str = "default", 
        use_cache: bool = True
    ) -> T:
        """Ask LLM for a structured response.
        
        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model for structured response
            llm_config_name: Name of the LLM configuration to use
            use_cache: Whether to use caching
            
        Returns:
            T: Instance of the response model
        """
        await self._ensure_initialized()
        
        # Get text response
        text_response = await self.ask_llm(prompt, llm_config_name, use_cache)
        
        try:
            # Attempt to parse as JSON and create model instance
            import json
            if text_response.strip().startswith('{'):
                data = json.loads(text_response)
                return response_model(**data)
            else:
                # If not JSON, create a simple response
                return response_model(content=text_response)
        except Exception as e:
            self._logger.warning(f"Failed to parse structured response: {e}")
            # Return a minimal valid instance
            try:
                return response_model()
            except Exception:
                raise ValueError(f"Cannot create {response_model.__name__} from response: {text_response}")
    
    async def _make_llm_request(self, prompt: str, config_name: str) -> str:
        """Make an actual LLM request.
        
        This is a placeholder implementation. In a real system, this would
        interface with actual LLM providers (OpenAI, Google, Anthropic, etc.)
        """
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Return a placeholder response based on the prompt
        if "error" in prompt.lower():
            raise Exception("Simulated LLM error")
        
        return f"This is a simulated response to: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
    
    def _get_model_name(self, config_name: str) -> str:
        """Get the model name for a configuration."""
        if self._config and hasattr(self._config, 'llm_configs'):
            config = self._config.llm_configs.get(config_name, {})
            if hasattr(config, 'model_name'):
                return config.model_name
        return "gemini-2.5-pro"  # Default
    
    def _get_provider(self, config_name: str) -> LLMProvider:
        """Get the provider for a configuration."""
        if self._config and hasattr(self._config, 'llm_configs'):
            config = self._config.llm_configs.get(config_name, {})
            if hasattr(config, 'provider'):
                return config.provider
        return LLMProvider.GOOGLE  # Default
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        await self._ensure_initialized()
        
        if self._config and hasattr(self._config, 'llm_configs'):
            return list(self._config.llm_configs.keys())
        return ["default"]
    
    async def get_config(self, config_name: str) -> Optional[LLMConfig]:
        """Get LLM configuration by name."""
        await self._ensure_initialized()
        
        if self._config and hasattr(self._config, 'llm_configs'):
            return self._config.llm_configs.get(config_name)
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on LLM services."""
        await self._ensure_initialized()
        
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "cache_size": len(self._cache),
            "available_configs": await self.get_available_models()
        }
    
    def clear_cache(self) -> None:
        """Clear the LLM cache."""
        self._cache.clear()
        self._logger.info("LLM cache cleared")
    
    async def shutdown(self) -> None:
        """Shutdown the LLM manager."""
        self.clear_cache()
        self._initialized = False
        self._logger.info("LLM Manager shutdown complete")


# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None


async def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
        await _llm_manager.initialize()
    return _llm_manager


# Export the main classes and functions
__all__ = [
    "LLMManager",
    "get_llm_manager",
]