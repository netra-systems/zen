"""Circuit breaker-enabled LLM client for reliable AI operations.

This module provides a robust LLM client with circuit breaker protection,
retry logic, and comprehensive error handling for production environments.
"""

import asyncio
from typing import Any, Dict, Optional, Type, TypeVar, AsyncIterator
from contextlib import asynccontextmanager

from app.core.circuit_breaker import (
    CircuitBreaker, CircuitConfig, CircuitBreakerOpenError, circuit_registry
)
from app.core.async_retry_logic import RetryConfig, retry_async
from app.llm.llm_manager import LLMManager
from app.schemas.llm_types import GenerationConfig, LLMResponse
from app.logging_config import central_logger
from pydantic import BaseModel

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMClientConfig:
    """Configuration for LLM client circuit breakers."""
    
    # Circuit breaker configurations for different LLM types
    FAST_LLM_CONFIG = CircuitConfig(
        name="fast_llm",
        failure_threshold=3,
        recovery_timeout=15.0,
        timeout_seconds=5.0
    )
    
    STANDARD_LLM_CONFIG = CircuitConfig(
        name="standard_llm", 
        failure_threshold=5,
        recovery_timeout=30.0,
        timeout_seconds=15.0
    )
    
    SLOW_LLM_CONFIG = CircuitConfig(
        name="slow_llm",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout_seconds=30.0
    )
    
    STRUCTURED_LLM_CONFIG = CircuitConfig(
        name="structured_llm",
        failure_threshold=3,
        recovery_timeout=20.0,
        timeout_seconds=10.0
    )


class ResilientLLMClient:
    """Production LLM client with circuit breaker protection."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager
        self._circuits: Dict[str, CircuitBreaker] = {}
    
    async def _get_circuit(self, config_name: str) -> CircuitBreaker:
        """Get circuit breaker for LLM configuration."""
        if config_name not in self._circuits:
            circuit_config = self._select_circuit_config(config_name)
            self._circuits[config_name] = await circuit_registry.get_circuit(
                f"llm_{config_name}", circuit_config
            )
        return self._circuits[config_name]
    
    def _select_circuit_config(self, config_name: str) -> CircuitConfig:
        """Select appropriate circuit config based on LLM type."""
        if "fast" in config_name.lower() or "gpt-3.5" in config_name.lower():
            return LLMClientConfig.FAST_LLM_CONFIG
        elif "gpt-4" in config_name.lower() or "claude" in config_name.lower():
            return LLMClientConfig.SLOW_LLM_CONFIG
        else:
            return LLMClientConfig.STANDARD_LLM_CONFIG
    
    async def ask_llm(self, 
                     prompt: str, 
                     llm_config_name: str, 
                     use_cache: bool = True) -> str:
        """Ask LLM with circuit breaker protection."""
        circuit = await self._get_circuit(llm_config_name)
        
        async def _make_request() -> str:
            return await self.llm_manager.ask_llm(prompt, llm_config_name, use_cache)
        
        try:
            return await circuit.call(_make_request)
        except CircuitBreakerOpenError:
            logger.warning(f"LLM request blocked - circuit open: {llm_config_name}")
            return await self._get_fallback_response(prompt, llm_config_name)
    
    async def ask_llm_full(self, 
                          prompt: str, 
                          llm_config_name: str, 
                          use_cache: bool = True) -> LLMResponse:
        """Ask LLM for full response with circuit breaker."""
        circuit = await self._get_circuit(llm_config_name)
        
        async def _make_request() -> LLMResponse:
            return await self.llm_manager.ask_llm_full(prompt, llm_config_name, use_cache)
        
        try:
            return await circuit.call(_make_request)
        except CircuitBreakerOpenError:
            logger.warning(f"LLM full request blocked - circuit open: {llm_config_name}")
            raise
    
    async def ask_structured_llm(self, 
                                prompt: str, 
                                llm_config_name: str, 
                                schema: Type[T], 
                                use_cache: bool = True,
                                **kwargs) -> T:
        """Ask LLM for structured output with circuit breaker."""
        circuit_name = f"{llm_config_name}_structured"
        circuit = await circuit_registry.get_circuit(
            circuit_name, LLMClientConfig.STRUCTURED_LLM_CONFIG
        )
        
        async def _make_request() -> T:
            return await self.llm_manager.ask_structured_llm(
                prompt, llm_config_name, schema, use_cache, **kwargs
            )
        
        try:
            return await circuit.call(_make_request)
        except CircuitBreakerOpenError:
            logger.warning(f"Structured LLM blocked - circuit open: {llm_config_name}")
            raise
    
    async def stream_llm(self, 
                        prompt: str, 
                        llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response with circuit breaker protection."""
        circuit = await self._get_circuit(llm_config_name)
        
        if not await circuit._can_execute():
            logger.warning(f"LLM streaming blocked - circuit open: {llm_config_name}")
            yield "[Circuit breaker open - streaming unavailable]"
            return
        
        try:
            async for chunk in self.llm_manager.stream_llm(prompt, llm_config_name):
                yield chunk
            await circuit._record_success()
        except Exception as e:
            await circuit._record_failure(type(e).__name__)
            logger.error(f"LLM streaming failed: {e}")
            raise
    
    async def _get_fallback_response(self, prompt: str, config_name: str) -> str:
        """Provide fallback response when circuit is open."""
        fallback_msg = (
            f"[Service temporarily unavailable - {config_name}] "
            f"Request: {prompt[:50]}..."
        )
        logger.info(f"Providing fallback response for {config_name}")
        return fallback_msg
    
    async def health_check(self, config_name: str) -> Dict[str, Any]:
        """Comprehensive health check for LLM configuration."""
        try:
            # Check LLM manager health
            llm_health = await self.llm_manager.health_check(config_name)
            
            # Check circuit breaker status
            circuit = await self._get_circuit(config_name)
            circuit_status = circuit.get_status()
            
            return {
                "llm_health": llm_health,
                "circuit_status": circuit_status,
                "overall_health": self._assess_overall_health(llm_health, circuit_status)
            }
        except Exception as e:
            logger.error(f"Health check failed for {config_name}: {e}")
            return {
                "error": str(e),
                "overall_health": "unhealthy"
            }
    
    def _assess_overall_health(self, llm_health: Any, circuit_status: Dict[str, Any]) -> str:
        """Assess overall health from LLM and circuit status."""
        if not llm_health.healthy:
            return "unhealthy"
        elif circuit_status["health"] == "unhealthy":
            return "degraded"
        elif circuit_status["health"] == "recovering":
            return "recovering"
        else:
            return "healthy"
    
    async def get_all_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all LLM circuits."""
        return {name: circuit.get_status() 
                for name, circuit in self._circuits.items()}


class RetryableLLMClient(ResilientLLMClient):
    """LLM client with both circuit breakers and retry logic."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        super().__init__(llm_manager)
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0
        )
    
    async def ask_llm_with_retry(self, 
                                prompt: str, 
                                llm_config_name: str, 
                                use_cache: bool = True) -> str:
        """Ask LLM with retry logic and circuit breaker."""
        @retry_async(self.retry_config)
        async def _request_with_retry() -> str:
            return await self.ask_llm(prompt, llm_config_name, use_cache)
        
        return await _request_with_retry()
    
    async def ask_structured_llm_with_retry(self, 
                                           prompt: str, 
                                           llm_config_name: str, 
                                           schema: Type[T], 
                                           use_cache: bool = True,
                                           **kwargs) -> T:
        """Ask structured LLM with retry logic."""
        @retry_async(self.retry_config)
        async def _request_with_retry() -> T:
            return await self.ask_structured_llm(
                prompt, llm_config_name, schema, use_cache, **kwargs
            )
        
        return await _request_with_retry()


@asynccontextmanager
async def get_llm_client(llm_manager: LLMManager, with_retry: bool = False):
    """Context manager for getting LLM client with cleanup."""
    if with_retry:
        client = RetryableLLMClient(llm_manager)
    else:
        client = ResilientLLMClient(llm_manager)
    
    try:
        yield client
    finally:
        # Cleanup if needed
        pass