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

# CRITICAL REMEDIATION: Import timeout management for LLM circuit breaker protection
from netra_backend.app.agents.execution_timeout_manager import (
    get_timeout_manager,
    CircuitBreakerOpenError
)

T = TypeVar('T', bound=BaseModel)


class LLMManager:
    """Main LLM Manager for handling LLM operations with user isolation.
    
    This class provides the primary interface for LLM operations throughout
    the application. It manages configurations, handles requests, and provides
    user-scoped caching and error handling to prevent conversation mixing.
    
    SECURITY: Each LLM Manager instance maintains its own cache to prevent
    conversation data from leaking between users. Use create_llm_manager()
    factory function for proper isolation.
    """
    
    # Class-level logger for test mocking compatibility - will be overridden per instance
    _logger = logger
    
    def __init__(self, user_context: Optional['UserExecutionContext'] = None):
        """
        Initialize LLM Manager with optional user context.
        
        Args:
            user_context: Optional UserExecutionContext for user-scoped operations
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create isolated logger instance for this manager to prevent context mixing
        # Each manager gets its own logger instance for proper factory pattern isolation
        from netra_backend.app.core.unified_logging import UnifiedLogger
        self._logger = UnifiedLogger()  # Create separate logger instance for true isolation
        self._config = None
        self._cache: Dict[str, Any] = {}  # User-scoped cache
        self._initialized = False
        self._ever_initialized = False  # Track if manager has ever been successfully initialized
        self._user_context = user_context
        
        # CRITICAL REMEDIATION: Initialize timeout manager for LLM circuit breaker protection
        self._timeout_manager = get_timeout_manager()
        
        # Log the initialization with security context
        if user_context:
            self._logger.info(f"LLM Manager initialized for user {user_context.user_id[:8]}... with timeout protection")
        else:
            self._logger.warning(
                "LLM Manager initialized without user context. "
                "This may lead to cache mixing between users."
            )
    
    async def initialize(self) -> None:
        """Initialize the LLM manager with configuration."""
        if self._initialized:
            return
        
        try:
            self._config = get_unified_config()
            self._logger.info("LLM Manager initialized successfully")
            self._initialized = True
            self._ever_initialized = True  # Mark as having been successfully initialized
        except Exception as e:
            self._logger.error(f"Failed to initialize LLM Manager: {e}")
            # Continue with minimal functionality
            self._initialized = True
            self._ever_initialized = True  # Even failed initialization counts as "attempted"
    
    async def _ensure_initialized(self) -> None:
        """Ensure the manager is initialized."""
        if not self._initialized:
            await self.initialize()
    
    def _is_cached(self, prompt: str, llm_config_name: str) -> bool:
        """Check if a prompt is cached for this user context."""
        user_prefix = ""
        if self._user_context:
            user_prefix = f"{self._user_context.user_id}:"
        cache_key = f"{user_prefix}{llm_config_name}:{hash(prompt)}"
        return cache_key in self._cache
    
    def _get_cache_key(self, prompt: str, llm_config_name: str) -> str:
        """Generate user-scoped cache key for a prompt."""
        user_prefix = ""
        if self._user_context:
            user_prefix = f"{self._user_context.user_id}:"
        return f"{user_prefix}{llm_config_name}:{hash(prompt)}"
    
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
        
        # Check cache first (user-scoped for security)
        if use_cache and self._is_cached(prompt, llm_config_name):
            cache_key = self._get_cache_key(prompt, llm_config_name)
            self._logger.debug(
                f"Cache hit for user {self._user_context.user_id[:8] if self._user_context else 'unknown'}... "
                f"prompt hash: {hash(prompt)}"
            )
            return self._cache[cache_key]
        
        try:
            # CRITICAL REMEDIATION: Make LLM request with circuit breaker protection
            async def llm_request_wrapper():
                # For now, return a placeholder response
                # In a real implementation, this would call the actual LLM
                return await self._make_llm_request(prompt, llm_config_name)
            
            response = await self._timeout_manager.execute_llm_with_circuit_breaker(
                llm_request_wrapper,
                f"llm_request_{llm_config_name}"
            )
            
            # Cache the response (user-scoped)
            if use_cache:
                cache_key = self._get_cache_key(prompt, llm_config_name)
                self._cache[cache_key] = response
            
            return response
            
        except CircuitBreakerOpenError as e:
            self._logger.error(f"🚫 LLM circuit breaker open: {e}")
            return (
                "I apologize, but our AI service is temporarily unavailable due to high demand. "
                "Please try again in a moment. If the issue persists, please contact support."
            )
        except TimeoutError as e:
            self._logger.error(f"⏰ LLM request timed out: {e}")
            return (
                "I apologize, but your request is taking longer than expected to process. "
                "Please try again with a simpler request or contact support if the issue persists."
            )
        except Exception as e:
            self._logger.error(f"❌ LLM request failed: {e}")
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
            content=text_response,
            model=self._get_model_name(llm_config_name),
            provider=self._get_provider(llm_config_name),
            usage=TokenUsage(
                prompt_tokens=len(prompt.split()),  # Rough estimate
                completion_tokens=len(text_response.split()),  # Rough estimate
                total_tokens=len(prompt.split()) + len(text_response.split())
            ),
            cached=use_cache and self._is_cached(prompt, llm_config_name)
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

    async def agenerate(
        self, 
        prompts: List[str], 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        **kwargs
    ):
        """Legacy compatibility method for agenerate interface.
        
        This method provides backward compatibility with existing code that expects
        the agenerate interface. It maps to the modern ask_llm_full interface.
        
        Args:
            prompts: List of prompts (only first prompt is used)
            temperature: Temperature parameter (ignored in current implementation)
            max_tokens: Max tokens parameter (ignored in current implementation)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Mock response object with generations structure for compatibility
        """
        if not prompts:
            raise ValueError("At least one prompt must be provided")
            
        # Use the first prompt
        prompt = prompts[0]
        
        # Get the actual response using the modern interface
        response = await self.ask_llm_full(prompt, "default", use_cache=True)
        
        # Create a mock response object that matches the expected interface
        # This maintains compatibility with existing parsing code
        class MockGeneration:
            def __init__(self, text: str):
                self.text = text
        
        class MockResponse:
            def __init__(self, content: str):
                self.generations = [[MockGeneration(content)]]
                
        return MockResponse(response.content)
    
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
    
    async def get_llm_config(self, config_name: str = "default") -> Optional[LLMConfig]:
        """Get LLM configuration by name (alias for get_config).
        
        This method exists for backward compatibility with health checks
        and other components that expect this method name.
        """
        return await self.get_config(config_name)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on LLM services.
        
        This method reports current state without side effects.
        It does not trigger initialization - use initialize() or _ensure_initialized() explicitly.
        """        
        # Get available configs without triggering initialization
        available_configs = []
        if self._initialized:
            available_configs = await self.get_available_models()
        elif self._config and hasattr(self._config, 'llm_configs'):
            # If we have config but aren't initialized, list the available configs
            available_configs = list(self._config.llm_configs.keys())
            
        return {
            "status": "healthy" if self._initialized else "unhealthy", 
            "initialized": self._initialized,
            "cache_size": len(self._cache),
            "available_configs": available_configs
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


# SECURITY FIX: Replace singleton with factory pattern
# Global instance removed to prevent multi-user conversation mixing
# Use create_llm_manager(user_context) instead


def create_llm_manager(user_context: 'UserExecutionContext' = None) -> LLMManager:
    """
    Create a new LLM Manager instance with user context isolation.
    
    This factory function replaces the singleton pattern to prevent conversation
    mixing between users. Each manager instance maintains its own cache scoped
    to the specific user context.
    
    Args:
        user_context: Optional UserExecutionContext for user-scoped operations
        
    Returns:
        LLMManager: New isolated manager instance
        
    Example:
        # Create user-scoped LLM manager
        manager = create_llm_manager(user_context)
        response = await manager.ask_llm("Hello", use_cache=True)
    """
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.logging_config import central_logger
    factory_logger = central_logger.get_logger(f"{__name__}.factory")
    
    if user_context:
        factory_logger.info(f"Creating LLM Manager for user {user_context.user_id[:8]}...")
    else:
        factory_logger.warning("Creating LLM Manager without user context - cache isolation may be compromised")
    
    manager = LLMManager(user_context)
    return manager


async def get_llm_manager() -> LLMManager:
    """
    DEPRECATED: Get the global LLM manager instance.
    
    WARNING: This function creates a non-isolated manager instance that can cause
    CRITICAL SECURITY VULNERABILITIES in multi-user environments. It should only
    be used for backward compatibility in legacy code that cannot be immediately
    migrated to the factory pattern.
    
    For new code, use:
    - create_llm_manager(user_context) for isolated managers with user-scoped cache
    
    Returns:
        LLMManager: A NEW instance (not singleton) for basic compatibility
    """
    import warnings
    
    warnings.warn(
        "get_llm_manager() creates instances that can mix conversations "
        "between users. Use create_llm_manager(user_context) "
        "for safe per-user LLM operations.",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.warning(
        "SECURITY WARNING: Using deprecated get_llm_manager() function. "
        "This creates a non-isolated manager that can mix conversations between users. "
        "Migrate to create_llm_manager(user_context) for proper isolation."
    )
    
    # Return a NEW instance each time to prevent shared state
    # This is still not ideal but safer than a true singleton
    manager = LLMManager()
    await manager.initialize()
    return manager


# Export the main classes and functions
__all__ = [
    "LLMManager",
    "create_llm_manager",  # New factory function
    "get_llm_manager",     # Deprecated singleton function
]