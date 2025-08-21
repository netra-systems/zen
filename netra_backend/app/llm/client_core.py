"""Core LLM client operations.

Provides basic LLM request handling with circuit breaker protection.
Handles simple, full, and structured LLM requests.
"""

from typing import Type, TypeVar

from pydantic import BaseModel

from netra_backend.app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from netra_backend.app.llm.client_circuit_breaker import LLMCircuitBreakerManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.resource_manager import resource_monitor
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.llm_response_types import LLMResponse

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMCoreClient:
    """Core LLM client with circuit breaker protection."""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize core LLM client."""
        self.llm_manager = llm_manager
        self.resource_monitor = resource_monitor
        self.circuit_manager = LLMCircuitBreakerManager()
    
    async def _create_simple_request(self, prompt: str, config_name: str, use_cache: bool) -> callable:
        """Create simple LLM request function with resource pooling."""
        async def _make_request() -> str:
            pool = self.resource_monitor.get_request_pool(config_name)
            async with pool:
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
        components = await self._prepare_simple_request(prompt, llm_config_name, use_cache)
        return await self._execute_simple_request(*components, prompt, llm_config_name)
    
    async def _prepare_simple_request(self, prompt: str, config_name: str, use_cache: bool) -> tuple:
        """Prepare circuit and request function for simple LLM call."""
        circuit = await self.circuit_manager.get_circuit(config_name)
        request_fn = await self._create_simple_request(prompt, config_name, use_cache)
        return circuit, request_fn
    
    async def _create_full_request(self, prompt: str, config_name: str, use_cache: bool) -> callable:
        """Create full LLM request function with resource pooling."""
        async def _make_request() -> LLMResponse:
            pool = self.resource_monitor.get_request_pool(config_name)
            async with pool:
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
        components = await self._prepare_full_request(prompt, llm_config_name, use_cache)
        return await self._execute_full_request(*components, llm_config_name)
    
    async def _prepare_full_request(self, prompt: str, config_name: str, use_cache: bool) -> tuple:
        """Prepare circuit and request function for full LLM call."""
        circuit = await self.circuit_manager.get_circuit(config_name)
        request_fn = await self._create_full_request(prompt, config_name, use_cache)
        return circuit, request_fn
    
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
        circuit = await self.circuit_manager.get_structured_circuit(config_name)
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
    
    async def _get_fallback_response(self, prompt: str, config_name: str) -> str:
        """Provide fallback response when circuit is open."""
        fallback_msg = self._build_fallback_message(prompt, config_name)
        logger.info(f"Providing fallback response for {config_name}")
        return fallback_msg
    
    def _build_fallback_message(self, prompt: str, config_name: str) -> str:
        """Build fallback message from prompt and config."""
        return (
            f"[Service temporarily unavailable - {config_name}] "
            f"Request: {prompt[:50]}..."
        )