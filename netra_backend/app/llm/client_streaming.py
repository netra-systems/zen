"""LLM client streaming operations.

Handles streaming LLM responses with circuit breaker protection.
Provides real-time response streaming with error handling.
"""

from typing import AsyncIterator
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.client_circuit_breaker import LLMCircuitBreakerManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LLMStreamingClient:
    """Handles LLM streaming operations with circuit breaker protection."""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize streaming client."""
        self.llm_manager = llm_manager
        self.circuit_manager = LLMCircuitBreakerManager()
    
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
            async for chunk in self._stream_with_manager(prompt, config_name):
                yield chunk
            await circuit._record_success()
        except Exception as e:
            await self._handle_streaming_error(circuit, e)
    
    async def _stream_with_manager(self, prompt: str, config_name: str) -> AsyncIterator[str]:
        """Stream using LLM manager."""
        async for chunk in self.llm_manager.stream_llm(prompt, config_name):
            yield chunk
    
    async def _yield_unavailable_message(self) -> AsyncIterator[str]:
        """Yield circuit breaker unavailable message."""
        yield "[Circuit breaker open - streaming unavailable]"
    
    async def _handle_stream_execution(self, circuit: CircuitBreaker, prompt: str, config_name: str) -> AsyncIterator[str]:
        """Handle stream execution with availability check."""
        if not await self._check_streaming_availability(circuit, config_name):
            async for chunk in self._yield_unavailable_message():
                yield chunk
            return
        async for chunk in self._execute_streaming(circuit, prompt, config_name):
            yield chunk
    
    async def stream_llm(self, prompt: str, llm_config_name: str) -> AsyncIterator[str]:
        """Stream LLM response with circuit breaker protection."""
        circuit = await self.circuit_manager.get_circuit(llm_config_name)
        async for chunk in self._handle_stream_execution(circuit, prompt, llm_config_name):
            yield chunk