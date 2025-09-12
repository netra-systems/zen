"""
LLM Fallback Execution Strategies

This module implements the Strategy pattern for different LLM execution approaches.
Each strategy encapsulates a specific execution behavior with  <= 8 line functions.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional

from netra_backend.app.core.reliability import CircuitBreaker
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LLMExecutionStrategy(ABC):
    """Abstract strategy for LLM execution."""
    
    @abstractmethod
    async def execute(self) -> Any:
        """Execute the strategy."""
        pass


class CircuitFallbackStrategy(LLMExecutionStrategy):
    """Strategy for circuit breaker fallback."""
    
    def __init__(self, handler: 'LLMFallbackHandler', fallback_type: str):
        """Initialize circuit fallback strategy."""
        self.handler = handler
        self.fallback_type = fallback_type
    
    async def execute(self) -> Any:
        """Execute circuit fallback strategy."""
        return self.handler._create_fallback_response(self.fallback_type)


class RetryExecutionStrategy(LLMExecutionStrategy):
    """Strategy for retry execution with fallback."""
    
    def _set_strategy_properties(self, handler: 'LLMFallbackHandler', llm_operation,
                                operation_name: str, circuit_breaker: CircuitBreaker, 
                                provider: str, fallback_type: str) -> None:
        """Set all strategy properties."""
        self._set_core_properties(handler, llm_operation, operation_name)
        self._set_reliability_properties(circuit_breaker, provider, fallback_type)
    
    def _set_core_properties(self, handler: 'LLMFallbackHandler', 
                           llm_operation, operation_name: str) -> None:
        """Set core strategy properties."""
        self.handler = handler
        self.llm_operation = llm_operation
        self.operation_name = operation_name
    
    def _set_reliability_properties(self, circuit_breaker: CircuitBreaker, 
                                  provider: str, fallback_type: str) -> None:
        """Set reliability-related properties."""
        self.circuit_breaker = circuit_breaker
        self.provider = provider
        self.fallback_type = fallback_type
    
    def __init__(self, handler: 'LLMFallbackHandler', llm_operation, 
                 operation_name: str, circuit_breaker: CircuitBreaker, 
                 provider: str, fallback_type: str):
        """Initialize retry execution strategy."""
        self._set_strategy_properties(handler, llm_operation, operation_name, 
                                    circuit_breaker, provider, fallback_type)
    
    async def execute(self) -> Any:
        """Execute retry strategy with fallback."""
        return await self.handler._execute_with_retry(
            self.llm_operation, self.operation_name, self.circuit_breaker, 
            self.provider, self.fallback_type
        )


class RetryExecutor:
    """Handles retry execution logic with chain of responsibility."""
    
    def __init__(self, handler: 'LLMFallbackHandler'):
        """Initialize retry executor."""
        self.handler = handler
    
    async def execute_operation(self, llm_operation, circuit_breaker: CircuitBreaker, provider: str):
        """Execute operation with timeout and circuit breaker recording."""
        result = await asyncio.wait_for(llm_operation(), timeout=self.handler.config.timeout)
        self.handler._record_success(circuit_breaker, provider)
        return result
    
    async def handle_operation_failure(self, error: Exception, attempt: int, 
                                     operation_name: str, circuit_breaker: CircuitBreaker):
        """Handle operation failure with logging and circuit breaker recording."""
        failure_type = self.handler._classify_error(error)
        self.handler._record_retry_attempt(attempt, failure_type, str(error))
        if self.handler.config.use_circuit_breaker:
            circuit_breaker.record_failure(failure_type)
    
    def _log_retry_warning(self, operation_name: str, attempt: int, error: Exception, delay: float) -> None:
        """Log retry warning message."""
        logger.warning(
            f"LLM operation {operation_name} failed (attempt {attempt}/{self.handler.config.max_retries}): {error}. "
            f"Retrying in {delay:.2f}s"
        )
    
    async def wait_before_retry(self, attempt: int, error: Exception, operation_name: str):
        """Wait before retry with exponential backoff."""
        failure_type = self.handler._classify_error(error)
        delay = self.handler._calculate_delay(attempt, failure_type)
        self._log_retry_warning(operation_name, attempt, error, delay)
        await asyncio.sleep(delay)


class StructuredFallbackBuilder:
    """Builder pattern for creating structured fallbacks."""
    
    def __init__(self, schema):
        """Initialize builder with schema."""
        self.schema = schema
        self.field_defaults = {}
    
    def build_field_defaults(self):
        """Build default values for schema fields."""
        for field_name, field_info in self.schema.model_fields.items():
            self._set_field_default(field_name, field_info)
        return self
    
    def _set_field_default(self, field_name: str, field_info):
        """Set default value for a specific field."""
        if field_info.default is not None:
            self.field_defaults[field_name] = field_info.default
        else:
            self.field_defaults[field_name] = self._get_type_default(field_info.annotation)
    
    def _get_type_default(self, annotation):
        """Get default value based on type annotation."""
        from netra_backend.app.llm.fallback_responses import TypeDefaultProvider
        return TypeDefaultProvider.get_default(annotation)
    
    
    def build(self):
        """Build the structured fallback instance."""
        try:
            return self.schema(**self.field_defaults)
        except Exception as e:
            logger.error(f"Failed to create structured fallback for {self.schema.__name__}: {e}")
            return self._create_empty_fallback()
    
    def _create_empty_fallback(self):
        """Create empty fallback instance as last resort."""
        try:
            return self.schema()
        except Exception:
            raise ValueError(f"Cannot create fallback instance for {self.schema.__name__}")