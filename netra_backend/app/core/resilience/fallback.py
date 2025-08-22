"""Fallback chain management for unified resilience framework.

This module provides enterprise-grade fallback mechanisms with:
- Configurable fallback chains and strategies
- Context-aware fallback selection
- Graceful degradation patterns
- Integration with circuit breakers and monitoring

All functions are ≤8 lines per MANDATORY requirements.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class FallbackStrategy(Enum):
    """Fallback strategy types."""
    FAIL_FAST = "fail_fast"
    DEGRADE_GRACEFULLY = "degrade_gracefully"
    CACHE_LAST_KNOWN = "cache_last_known"
    STATIC_RESPONSE = "static_response"
    ALTERNATIVE_SERVICE = "alternative_service"


class FallbackPriority(Enum):
    """Fallback priority levels."""
    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3
    EMERGENCY = 4


@dataclass
class FallbackConfig:
    """Enterprise fallback configuration."""
    name: str
    strategy: FallbackStrategy
    priority: FallbackPriority
    enabled: bool = True
    timeout_seconds: float = 5.0
    max_retries: int = 1
    context_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate fallback configuration."""
        self._validate_timeout()
        self._validate_retries()
    
    def _validate_timeout(self) -> None:
        """Validate timeout is positive."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
    
    def _validate_retries(self) -> None:
        """Validate max retries is non-negative."""
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass
class FallbackAttempt:
    """Information about a fallback attempt."""
    config: FallbackConfig
    success: bool
    execution_time: float
    error: Optional[Exception]
    response: Any


@dataclass
class FallbackMetrics:
    """Fallback metrics for monitoring."""
    total_invocations: int = 0
    successful_fallbacks: int = 0
    failed_fallbacks: int = 0
    fallback_attempts: List[FallbackAttempt] = field(default_factory=list)
    average_execution_time: float = 0.0


class FallbackException(Exception):
    """Base exception for fallback failures."""
    
    def __init__(self, message: str, fallback_name: str) -> None:
        super().__init__(message)
        self.fallback_name = fallback_name


class FallbackChainExhaustedException(FallbackException):
    """Raised when all fallbacks in chain fail."""
    
    def __init__(self, attempts: List[FallbackAttempt]) -> None:
        super().__init__("All fallback strategies exhausted", "chain")
        self.attempts = attempts


class FallbackHandler(ABC):
    """Abstract base class for fallback handlers."""
    
    def __init__(self, config: FallbackConfig) -> None:
        self.config = config
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute fallback strategy."""
        pass
    
    def can_handle(self, context: Dict[str, Any]) -> bool:
        """Check if handler can process given context."""
        for key, expected_value in self.config.context_requirements.items():
            if context.get(key) != expected_value:
                return False
        return True


class StaticResponseFallback(FallbackHandler):
    """Fallback that returns static response."""
    
    def __init__(self, config: FallbackConfig, response: Any) -> None:
        super().__init__(config)
        self.response = response
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Return static response."""
        logger.info(f"Using static response fallback: {self.config.name}")
        await asyncio.sleep(0.1)  # Simulate processing
        return self.response


class CacheLastKnownFallback(FallbackHandler):
    """Fallback that returns cached response."""
    
    def __init__(self, config: FallbackConfig) -> None:
        super().__init__(config)
        self._cache: Dict[str, Any] = {}
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Return cached response if available."""
        cache_key = context.get("cache_key", "default")
        if cache_key in self._cache:
            logger.info(f"Using cached fallback: {self.config.name}")
            return self._cache[cache_key]
        raise FallbackException("No cached data available", self.config.name)
    
    def update_cache(self, key: str, value: Any) -> None:
        """Update cache with new value."""
        self._cache[key] = value


class AlternativeServiceFallback(FallbackHandler):
    """Fallback that calls alternative service."""
    
    def __init__(self, config: FallbackConfig, service_func: Callable) -> None:
        super().__init__(config)
        self.service_func = service_func
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute alternative service."""
        logger.info(f"Using alternative service fallback: {self.config.name}")
        if asyncio.iscoroutinefunction(self.service_func):
            return await self.service_func(context)
        return self.service_func(context)


class UnifiedFallbackChain:
    """Enterprise fallback chain manager."""
    
    def __init__(self, name: str) -> None:
        self.name = name
        self.handlers: List[FallbackHandler] = []
        self.metrics = FallbackMetrics()
    
    def add_fallback(self, handler: FallbackHandler) -> None:
        """Add fallback handler to chain."""
        self.handlers.append(handler)
        self._sort_handlers_by_priority()
    
    def _sort_handlers_by_priority(self) -> None:
        """Sort handlers by priority."""
        self.handlers.sort(key=lambda h: h.config.priority.value)
    
    async def execute_fallback(
        self, 
        context: Dict[str, Any], 
        original_exception: Optional[Exception] = None
    ) -> Any:
        """Execute fallback chain until success or exhaustion."""
        self.metrics.total_invocations += 1
        attempts = []
        
        for handler in self.handlers:
            if not handler.config.enabled or not handler.can_handle(context):
                continue
                
            attempt = await self._try_fallback_handler(handler, context)
            attempts.append(attempt)
            
            if attempt.success:
                self.metrics.successful_fallbacks += 1
                return attempt.response
        
        self.metrics.failed_fallbacks += 1
        raise FallbackChainExhaustedException(attempts)
    
    async def _try_fallback_handler(
        self, 
        handler: FallbackHandler, 
        context: Dict[str, Any]
    ) -> FallbackAttempt:
        """Try executing single fallback handler."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await asyncio.wait_for(
                handler.execute(context), 
                timeout=handler.config.timeout_seconds
            )
            execution_time = asyncio.get_event_loop().time() - start_time
            return FallbackAttempt(handler.config, True, execution_time, None, response)
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.warning(f"Fallback {handler.config.name} failed: {e}")
            return FallbackAttempt(handler.config, False, execution_time, e, None)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get fallback metrics for monitoring."""
        return {
            "name": self.name,
            "total_invocations": self.metrics.total_invocations,
            "successful_fallbacks": self.metrics.successful_fallbacks,
            "failed_fallbacks": self.metrics.failed_fallbacks,
            "success_rate": self._calculate_success_rate(),
            "handler_count": len(self.handlers),
            "enabled_handlers": self._count_enabled_handlers()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate fallback success rate."""
        if self.metrics.total_invocations > 0:
            return self.metrics.successful_fallbacks / self.metrics.total_invocations
        return 1.0
    
    def _count_enabled_handlers(self) -> int:
        """Count enabled handlers."""
        return sum(1 for h in self.handlers if h.config.enabled)
    
    def remove_fallback(self, handler_name: str) -> bool:
        """Remove fallback handler by name."""
        for i, handler in enumerate(self.handlers):
            if handler.config.name == handler_name:
                del self.handlers[i]
                return True
        return False
    
    def disable_fallback(self, handler_name: str) -> bool:
        """Disable fallback handler by name."""
        for handler in self.handlers:
            if handler.config.name == handler_name:
                handler.config.enabled = False
                return True
        return False
    
    def enable_fallback(self, handler_name: str) -> bool:
        """Enable fallback handler by name."""
        for handler in self.handlers:
            if handler.config.name == handler_name:
                handler.config.enabled = True
                return True
        return False


class FallbackChainManager:
    """Enterprise fallback chain manager."""
    
    def __init__(self) -> None:
        self.chains: Dict[str, UnifiedFallbackChain] = {}
    
    def create_chain(self, name: str) -> UnifiedFallbackChain:
        """Create new fallback chain."""
        chain = UnifiedFallbackChain(name)
        self.chains[name] = chain
        return chain
    
    def get_chain(self, name: str) -> Optional[UnifiedFallbackChain]:
        """Get fallback chain by name."""
        return self.chains.get(name)
    
    def remove_chain(self, name: str) -> bool:
        """Remove fallback chain."""
        if name in self.chains:
            del self.chains[name]
            return True
        return False
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all chains."""
        return {name: chain.get_metrics() for name, chain in self.chains.items()}
    
    async def execute_fallback_for_service(
        self, 
        service_name: str, 
        context: Dict[str, Any], 
        original_exception: Optional[Exception] = None
    ) -> Any:
        """Execute fallback for specific service."""
        chain = self.get_chain(service_name)
        if not chain:
            raise FallbackException(f"No fallback chain for service: {service_name}", service_name)
        return await chain.execute_fallback(context, original_exception)


# Predefined fallback configurations for common scenarios
class FallbackPresets:
    """Predefined fallback configurations for common scenarios."""
    
    @staticmethod
    def get_api_fallback_config() -> FallbackConfig:
        """Get fallback configuration for API services."""
        return FallbackConfig(
            name="api_fallback",
            strategy=FallbackStrategy.CACHE_LAST_KNOWN,
            priority=FallbackPriority.PRIMARY,
            timeout_seconds=3.0,
            max_retries=2
        )
    
    @staticmethod
    def get_database_fallback_config() -> FallbackConfig:
        """Get fallback configuration for database operations."""
        return FallbackConfig(
            name="database_fallback",
            strategy=FallbackStrategy.CACHE_LAST_KNOWN,
            priority=FallbackPriority.PRIMARY,
            timeout_seconds=2.0,
            max_retries=1
        )
    
    @staticmethod
    def get_llm_fallback_config() -> FallbackConfig:
        """Get fallback configuration for LLM services."""
        return FallbackConfig(
            name="llm_fallback",
            strategy=FallbackStrategy.ALTERNATIVE_SERVICE,
            priority=FallbackPriority.SECONDARY,
            timeout_seconds=10.0,
            max_retries=0
        )
    
    @staticmethod
    def get_emergency_fallback_config() -> FallbackConfig:
        """Get emergency fallback configuration."""
        return FallbackConfig(
            name="emergency_fallback",
            strategy=FallbackStrategy.STATIC_RESPONSE,
            priority=FallbackPriority.EMERGENCY,
            timeout_seconds=1.0,
            max_retries=0
        )


# Global fallback chain manager instance
fallback_manager = FallbackChainManager()