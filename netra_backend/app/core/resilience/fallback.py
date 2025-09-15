"""Fallback Management for Unified Resilience Framework

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Provide graceful degradation
- Value Impact: Prevents complete service failures by providing fallback responses
- Strategic Impact: Enables system resilience and availability guarantees

This module provides fallback strategy management for graceful degradation
when primary services fail.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class FallbackStrategy(str, Enum):
    """Fallback strategy types."""
    STATIC_RESPONSE = "static_response"
    CACHE_LAST_KNOWN = "cache_last_known"  
    ALTERNATIVE_SERVICE = "alternative_service"
    CIRCUIT_BREAKER = "circuit_breaker"


class FallbackPriority(str, Enum):
    """Fallback priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FallbackConfig(BaseModel):
    """Configuration for fallback behavior."""
    strategy: FallbackStrategy
    priority: FallbackPriority = FallbackPriority.MEDIUM
    timeout_seconds: float = 5.0
    max_retries: int = 3
    enabled: bool = True
    static_response: Optional[Dict[str, Any]] = None
    cache_ttl_seconds: Optional[int] = 300
    alternative_endpoint: Optional[str] = None


class FallbackHandler(ABC):
    """Abstract base class for fallback handlers."""
    
    def __init__(self, config: FallbackConfig):
        """Initialize fallback handler."""
        self.config = config
        self._logger = logger
    
    @abstractmethod
    async def handle_fallback(self, original_error: Exception, context: Dict[str, Any]) -> Any:
        """Handle fallback when primary operation fails.
        
        Args:
            original_error: The exception that triggered the fallback
            context: Additional context for fallback handling
            
        Returns:
            Fallback response
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if fallback is enabled."""
        return self.config.enabled


class StaticResponseFallback(FallbackHandler):
    """Fallback that returns a static response."""
    
    async def handle_fallback(self, original_error: Exception, context: Dict[str, Any]) -> Any:
        """Return configured static response."""
        self._logger.warning(f"Using static fallback for error: {original_error}")
        return self.config.static_response or {"status": "fallback", "message": "Service temporarily unavailable"}


class CacheLastKnownFallback(FallbackHandler):
    """Fallback that returns cached last known good response."""
    
    def __init__(self, config: FallbackConfig):
        """Initialize cache-based fallback."""
        super().__init__(config)
        self._cache: Dict[str, Any] = {}
    
    async def handle_fallback(self, original_error: Exception, context: Dict[str, Any]) -> Any:
        """Return cached last known response."""
        cache_key = context.get("cache_key", "default")
        cached_response = self._cache.get(cache_key)
        
        if cached_response:
            self._logger.info(f"Using cached fallback response for key: {cache_key}")
            return cached_response
        
        self._logger.warning(f"No cached response available for key: {cache_key}, using empty response")
        return {"status": "fallback", "message": "No cached data available"}
    
    def cache_response(self, key: str, response: Any) -> None:
        """Cache a successful response for future fallback use."""
        self._cache[key] = response


class AlternativeServiceFallback(FallbackHandler):
    """Fallback that redirects to an alternative service."""
    
    async def handle_fallback(self, original_error: Exception, context: Dict[str, Any]) -> Any:
        """Redirect to alternative service endpoint."""
        alternative_endpoint = self.config.alternative_endpoint
        if not alternative_endpoint:
            self._logger.error("No alternative endpoint configured")
            return {"status": "error", "message": "Alternative service not available"}
        
        self._logger.info(f"Using alternative service: {alternative_endpoint}")
        # In a real implementation, this would make an HTTP call to the alternative service
        return {"status": "fallback", "alternative_service": alternative_endpoint, "message": "Using alternative service"}


class UnifiedFallbackChain:
    """Manages a chain of fallback handlers."""
    
    def __init__(self):
        """Initialize fallback chain."""
        self._logger = logger
        self._handlers: List[FallbackHandler] = []
    
    def add_handler(self, handler: FallbackHandler) -> None:
        """Add a fallback handler to the chain."""
        if handler.is_enabled():
            self._handlers.append(handler)
            self._logger.info(f"Added fallback handler: {handler.__class__.__name__}")
    
    def remove_handler(self, handler_class: type) -> None:
        """Remove a fallback handler from the chain."""
        self._handlers = [h for h in self._handlers if not isinstance(h, handler_class)]
    
    async def execute_fallback(self, original_error: Exception, context: Dict[str, Any]) -> Any:
        """Execute fallback chain until one succeeds."""
        for handler in self._handlers:
            try:
                result = await handler.handle_fallback(original_error, context)
                self._logger.info(f"Fallback successful with handler: {handler.__class__.__name__}")
                return result
            except Exception as fallback_error:
                self._logger.warning(f"Fallback handler {handler.__class__.__name__} failed: {fallback_error}")
                continue
        
        # If all fallbacks fail, return a generic error response
        self._logger.error("All fallback handlers failed")
        return {"status": "error", "message": "Service unavailable - all fallbacks exhausted"}
    
    def get_handler_count(self) -> int:
        """Get the number of active fallback handlers."""
        return len(self._handlers)


class FallbackPresets:
    """Predefined fallback configurations for common scenarios."""
    
    @staticmethod
    def create_static_fallback(response: Dict[str, Any], priority: FallbackPriority = FallbackPriority.MEDIUM) -> FallbackConfig:
        """Create a static response fallback configuration."""
        return FallbackConfig(
            strategy=FallbackStrategy.STATIC_RESPONSE,
            priority=priority,
            static_response=response
        )
    
    @staticmethod
    def create_cache_fallback(cache_ttl: int = 300, priority: FallbackPriority = FallbackPriority.HIGH) -> FallbackConfig:
        """Create a cache-based fallback configuration."""
        return FallbackConfig(
            strategy=FallbackStrategy.CACHE_LAST_KNOWN,
            priority=priority,
            cache_ttl_seconds=cache_ttl
        )
    
    @staticmethod
    def create_alternative_service_fallback(endpoint: str, priority: FallbackPriority = FallbackPriority.LOW) -> FallbackConfig:
        """Create an alternative service fallback configuration."""
        return FallbackConfig(
            strategy=FallbackStrategy.ALTERNATIVE_SERVICE,
            priority=priority,
            alternative_endpoint=endpoint
        )


class FallbackManager:
    """Global fallback manager for the application."""
    
    def __init__(self):
        """Initialize fallback manager."""
        self._logger = logger
        self._service_chains: Dict[str, UnifiedFallbackChain] = {}
    
    def register_service_fallback(self, service_name: str, config: FallbackConfig) -> None:
        """Register a fallback configuration for a service."""
        if service_name not in self._service_chains:
            self._service_chains[service_name] = UnifiedFallbackChain()
        
        # Create the appropriate handler based on strategy
        handler = self._create_handler(config)
        self._service_chains[service_name].add_handler(handler)
        self._logger.info(f"Registered fallback for service: {service_name}")
    
    def _create_handler(self, config: FallbackConfig) -> FallbackHandler:
        """Create a fallback handler based on configuration."""
        handlers = {
            FallbackStrategy.STATIC_RESPONSE: StaticResponseFallback,
            FallbackStrategy.CACHE_LAST_KNOWN: CacheLastKnownFallback,
            FallbackStrategy.ALTERNATIVE_SERVICE: AlternativeServiceFallback,
        }
        
        handler_class = handlers.get(config.strategy, StaticResponseFallback)
        return handler_class(config)
    
    async def execute_fallback(self, service_name: str, original_error: Exception, context: Dict[str, Any] = None) -> Any:
        """Execute fallback for a specific service."""
        if context is None:
            context = {}
        
        chain = self._service_chains.get(service_name)
        if not chain:
            self._logger.warning(f"No fallback configured for service: {service_name}")
            return {"status": "error", "message": f"Service {service_name} unavailable"}
        
        return await chain.execute_fallback(original_error, context)
    
    def has_fallback(self, service_name: str) -> bool:
        """Check if a service has fallback configured."""
        return service_name in self._service_chains and self._service_chains[service_name].get_handler_count() > 0


# Global fallback manager instance
fallback_manager = FallbackManager()


# Export all classes and instances
__all__ = [
    "FallbackStrategy",
    "FallbackPriority", 
    "FallbackConfig",
    "FallbackHandler",
    "StaticResponseFallback",
    "CacheLastKnownFallback",
    "AlternativeServiceFallback",
    "UnifiedFallbackChain",
    "FallbackPresets",
    "FallbackManager",
    "fallback_manager",
]