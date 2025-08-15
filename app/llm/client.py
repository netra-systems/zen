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
from app.core.async_retry_logic import with_retry
from app.llm.llm_manager import LLMManager
from app.schemas.llm_config_types import LLMConfig as GenerationConfig
from app.schemas.llm_response_types import LLMResponse
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
    
    async def _create_simple_request(self, prompt: str, config_name: str, use_cache: bool) -> callable:
        """Create simple LLM request function."""
        async def _make_request() -> str:
            return await self.llm_manager.ask_llm(prompt, config_name, use_cache)
        return _make_request
    
    async def _handle_circuit_open_simple(self, prompt: str, config_name: str) -> str:
        """Handle circuit breaker open for simple requests."""
        logger.warning(f"LLM request blocked - circuit open: {config_name}")
        return await self._get_fallback_response(prompt, config_name)
    
    async def _execute_simple_request(self, circuit: CircuitBreaker, request_fn: callable, 
                                      prompt: str, config_name: str) -> str:
        """Execute simple request with circuit breaker."""
        try:
            return await circuit.call(request_fn)
        except CircuitBreakerOpenError:
            return await self._handle_circuit_open_simple(prompt, config_name)
    
    async def ask_llm(self, 
                     prompt: str, 
                     llm_config_name: str, 
                     use_cache: bool = True) -> str:
        """Ask LLM with circuit breaker protection."""
        circuit = await self._get_circuit(llm_config_name)
        request_fn = await self._create_simple_request(prompt, llm_config_name, use_cache)
        return await self._execute_simple_request(circuit, request_fn, prompt, llm_config_name)
    
    async def _create_full_request(self, prompt: str, config_name: str, use_cache: bool) -> callable:
        """Create full LLM request function."""
        async def _make_request() -> LLMResponse:
            return await self.llm_manager.ask_llm_full(prompt, config_name, use_cache)
        return _make_request
    
    async def _handle_circuit_open_full(self, config_name: str) -> None:
        """Handle circuit breaker open for full requests."""
        logger.warning(f"LLM full request blocked - circuit open: {config_name}")
        raise CircuitBreakerOpenError(f"Circuit open: {config_name}")
    
    async def _execute_full_request(self, circuit: CircuitBreaker, request_fn: callable, config_name: str) -> LLMResponse:
        """Execute full request with circuit breaker."""
        try:
            return await circuit.call(request_fn)
        except CircuitBreakerOpenError:
            await self._handle_circuit_open_full(config_name)
            raise
    
    async def ask_llm_full(self, 
                          prompt: str, 
                          llm_config_name: str, 
                          use_cache: bool = True) -> LLMResponse:
        """Ask LLM for full response with circuit breaker."""
        circuit = await self._get_circuit(llm_config_name)
        request_fn = await self._create_full_request(prompt, llm_config_name, use_cache)
        return await self._execute_full_request(circuit, request_fn, llm_config_name)
    
    async def _get_structured_circuit(self, config_name: str) -> CircuitBreaker:
        """Get circuit breaker for structured LLM requests."""
        circuit_name = f"{config_name}_structured"
        return await circuit_registry.get_circuit(
            circuit_name, LLMClientConfig.STRUCTURED_LLM_CONFIG
        )
    
    async def _create_structured_request(self, prompt: str, config_name: str, 
                                        schema: Type[T], use_cache: bool, **kwargs) -> callable:
        """Create structured LLM request function."""
        async def _make_request() -> T:
            return await self.llm_manager.ask_structured_llm(
                prompt, config_name, schema, use_cache, **kwargs
            )
        return _make_request
    
    async def _handle_circuit_open_structured(self, config_name: str) -> None:
        """Handle circuit breaker open for structured requests."""
        logger.warning(f"Structured LLM blocked - circuit open: {config_name}")
        raise CircuitBreakerOpenError(f"Structured circuit open: {config_name}")
    
    async def _execute_structured_request(self, circuit: CircuitBreaker, request_fn: callable, config_name: str) -> T:
        """Execute structured request with circuit breaker."""
        try:
            return await circuit.call(request_fn)
        except CircuitBreakerOpenError:
            await self._handle_circuit_open_structured(config_name)
            raise
    
    async def _prepare_structured_components(self, prompt: str, config_name: str, 
                                            schema: Type[T], use_cache: bool, **kwargs) -> tuple:
        """Prepare circuit and request for structured LLM."""
        circuit = await self._get_structured_circuit(config_name)
        request_fn = await self._create_structured_request(
            prompt, config_name, schema, use_cache, **kwargs
        )
        return circuit, request_fn
    
    async def ask_structured_llm(self, prompt: str, llm_config_name: str, 
                                schema: Type[T], use_cache: bool = True, **kwargs) -> T:
        """Ask LLM for structured output with circuit breaker."""
        circuit, request_fn = await self._prepare_structured_components(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )
        return await self._execute_structured_request(circuit, request_fn, llm_config_name)
    
    async def _check_streaming_availability(self, circuit: CircuitBreaker, config_name: str) -> bool:
        """Check if streaming is available through circuit breaker."""
        if not await circuit._can_execute():
            logger.warning(f"LLM streaming blocked - circuit open: {config_name}")
            return False
        return True
    
    async def _handle_streaming_error(self, circuit: CircuitBreaker, error: Exception) -> None:
        """Handle streaming error and record circuit failure."""
        await circuit._record_failure(type(error).__name__)
        logger.error(f"LLM streaming failed: {error}")
        raise error
    
    async def _execute_streaming(self, circuit: CircuitBreaker, prompt: str, config_name: str) -> AsyncIterator[str]:
        """Execute streaming with circuit breaker recording."""
        try:
            async for chunk in self.llm_manager.stream_llm(prompt, config_name):
                yield chunk
            await circuit._record_success()
        except Exception as e:
            await self._handle_streaming_error(circuit, e)
    
    async def _yield_unavailable_message(self) -> AsyncIterator[str]:
        """Yield circuit breaker unavailable message."""
        yield "[Circuit breaker open - streaming unavailable]"
    
    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response with circuit breaker protection."""
        circuit = await self._get_circuit(llm_config_name)
        if not await self._check_streaming_availability(circuit, llm_config_name):
            async for chunk in self._yield_unavailable_message():
                yield chunk
            return
        async for chunk in self._execute_streaming(circuit, prompt, llm_config_name):
            yield chunk
    
    async def _get_fallback_response(self, prompt: str, config_name: str) -> str:
        """Provide fallback response when circuit is open."""
        fallback_msg = (
            f"[Service temporarily unavailable - {config_name}] "
            f"Request: {prompt[:50]}..."
        )
        logger.info(f"Providing fallback response for {config_name}")
        return fallback_msg
    
    async def _get_health_components(self, config_name: str) -> tuple:
        """Get health check components for LLM and circuit."""
        llm_health = await self.llm_manager.health_check(config_name)
        circuit = await self._get_circuit(config_name)
        circuit_status = circuit.get_status()
        return llm_health, circuit_status
    
    def _build_health_response(self, llm_health: Any, circuit_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build health check response from components."""
        return {
            "llm_health": llm_health,
            "circuit_status": circuit_status,
            "overall_health": self._assess_overall_health(llm_health, circuit_status)
        }
    
    def _build_error_response(self, config_name: str, error: Exception) -> Dict[str, Any]:
        """Build error response for health check failure."""
        logger.error(f"Health check failed for {config_name}: {error}")
        return {
            "error": str(error),
            "overall_health": "unhealthy"
        }
    
    async def health_check(self, config_name: str) -> Dict[str, Any]:
        """Comprehensive health check for LLM configuration."""
        try:
            llm_health, circuit_status = await self._get_health_components(config_name)
            return self._build_health_response(llm_health, circuit_status)
        except Exception as e:
            return self._build_error_response(config_name, e)
    
    def _check_llm_health_status(self, llm_health: Any) -> Optional[str]:
        """Check LLM health status and return override if unhealthy."""
        if not llm_health.healthy:
            return "unhealthy"
        return None
    
    def _check_circuit_health_status(self, circuit_status: Dict[str, Any]) -> str:
        """Check circuit health status and return appropriate state."""
        circuit_health = circuit_status["health"]
        if circuit_health == "unhealthy":
            return "degraded"
        elif circuit_health == "recovering":
            return "recovering"
        return "healthy"
    
    def _assess_overall_health(self, llm_health: Any, circuit_status: Dict[str, Any]) -> str:
        """Assess overall health from LLM and circuit status."""
        llm_override = self._check_llm_health_status(llm_health)
        if llm_override:
            return llm_override
        return self._check_circuit_health_status(circuit_status)
    
    async def get_all_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all LLM circuits."""
        return {name: circuit.get_status() 
                for name, circuit in self._circuits.items()}


class RetryableLLMClient(ResilientLLMClient):
    """LLM client with both circuit breakers and retry logic."""
    
    def __init__(self, llm_manager: LLMManager) -> None:
        super().__init__(llm_manager)
        pass  # Use decorators for retry logic
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def ask_llm_with_retry(self, 
                                prompt: str, 
                                llm_config_name: str, 
                                use_cache: bool = True) -> str:
        """Ask LLM with retry logic and circuit breaker."""
        return await self.ask_llm(prompt, llm_config_name, use_cache)
    
    async def _call_structured_llm(self, prompt: str, config_name: str, 
                                  schema: Type[T], use_cache: bool, **kwargs) -> T:
        """Internal call to structured LLM."""
        return await self.ask_structured_llm(
            prompt, config_name, schema, use_cache, **kwargs
        )
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def ask_structured_llm_with_retry(self, prompt: str, llm_config_name: str, 
                                           schema: Type[T], use_cache: bool = True, **kwargs) -> T:
        """Ask structured LLM with retry logic."""
        return await self._call_structured_llm(
            prompt, llm_config_name, schema, use_cache, **kwargs
        )


def _create_client_instance(llm_manager: LLMManager, with_retry: bool) -> ResilientLLMClient:
    """Create appropriate LLM client instance."""
    if with_retry:
        return RetryableLLMClient(llm_manager)
    return ResilientLLMClient(llm_manager)

def _perform_client_cleanup(client: ResilientLLMClient) -> None:
    """Perform client cleanup operations."""
    # Cleanup if needed
    pass

@asynccontextmanager
async def get_llm_client(llm_manager: LLMManager, with_retry: bool = False):
    """Context manager for getting LLM client with cleanup."""
    client = _create_client_instance(llm_manager, with_retry)
    
    try:
        yield client
    finally:
        _perform_client_cleanup(client)