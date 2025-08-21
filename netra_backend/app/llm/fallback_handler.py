"""
LLM Fallback Handler with exponential backoff and graceful degradation.

This module provides robust fallback mechanisms for LLM failures including:
- Exponential backoff retry logic
- Provider failover 
- Default response generation
- Circuit breaker integration
"""

import asyncio
from typing import Optional, Dict, Any, TypeVar, Type
from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.reliability import CircuitBreaker, CircuitBreakerConfig
from netra_backend.app.llm.fallback_strategies import CircuitFallbackStrategy, RetryExecutionStrategy, RetryExecutor
from netra_backend.app.llm.error_classification import ErrorClassificationChain, FailureType
from netra_backend.app.llm.fallback_config import FallbackConfig, RetryHistoryManager
from netra_backend.app.llm.fallback_responses import FallbackResponseFactory, StructuredFallbackBuilder
from netra_backend.app.llm.retry_helpers import (
    execute_retry_template, create_health_status_base, 
    add_circuit_breaker_status, add_failure_type_breakdown
)

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)




class LLMFallbackHandler:
    """Handles LLM failures with retry logic and graceful degradation"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_manager = RetryHistoryManager()
        self.error_classifier = ErrorClassificationChain()
        self.response_factory = FallbackResponseFactory()
    
    
    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = self._create_circuit_breaker(provider)
        return self.circuit_breakers[provider]
    
    def _create_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Create new circuit breaker for provider."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            name=f"llm_fallback_{provider}"
        )
        return CircuitBreaker(config)
    
    async def execute_with_fallback(
        self,
        llm_operation,
        operation_name: str,
        provider: str = "default",
        fallback_type: str = "general"
    ) -> Any:
        """Execute LLM operation with fallback handling"""
        execution_strategy = self._create_execution_strategy(llm_operation, operation_name, provider, fallback_type)
        return await execution_strategy.execute()
    
    def _create_execution_strategy(self, llm_operation, operation_name: str, provider: str, fallback_type: str):
        """Create execution strategy based on circuit breaker status."""
        circuit_breaker = self._get_circuit_breaker(provider)
        if self._should_use_circuit_fallback(circuit_breaker, provider, fallback_type):
            return CircuitFallbackStrategy(self, fallback_type)
        return RetryExecutionStrategy(self, llm_operation, operation_name, circuit_breaker, provider, fallback_type)
    
    def _should_use_circuit_fallback(self, circuit_breaker: CircuitBreaker, provider: str, fallback_type: str) -> bool:
        """Check if should use circuit fallback with logging."""
        if self._is_circuit_open(circuit_breaker, provider):
            logger.warning(f"Circuit breaker open for {provider}, using fallback")
            return True
        return False
    
    def _is_circuit_open(self, circuit_breaker: CircuitBreaker, provider: str) -> bool:
        """Check if circuit breaker is open with error handling."""
        if not self._should_check_circuit_breaker(circuit_breaker):
            return False
        return self._check_circuit_breaker_status(circuit_breaker, provider)
    
    def _should_check_circuit_breaker(self, circuit_breaker: CircuitBreaker) -> bool:
        """Check if circuit breaker should be checked."""
        return self.config.use_circuit_breaker and hasattr(circuit_breaker, 'is_open')
    
    def _check_circuit_breaker_status(self, circuit_breaker: CircuitBreaker, provider: str) -> bool:
        """Check actual circuit breaker status with error handling."""
        try:
            return circuit_breaker.is_open()
        except (TypeError, AttributeError):
            self._log_circuit_breaker_warning(provider)
            return False
    
    def _log_circuit_breaker_warning(self, provider: str) -> None:
        """Log circuit breaker warning if enabled."""
        if self.config.log_circuit_breaker_warnings:
            logger.warning(f"Circuit breaker for {provider} not properly initialized")
    
    async def _execute_with_retry(self, llm_operation, operation_name: str,
                                 circuit_breaker: CircuitBreaker, provider: str, 
                                 fallback_type: str) -> Any:
        """Execute operation with retry logic using Template Method pattern."""
        retry_executor = RetryExecutor(self)
        return await self._execute_retry_template(retry_executor, llm_operation, 
                                                 operation_name, circuit_breaker, provider, fallback_type)
    
    async def _execute_retry_template(self, retry_executor: RetryExecutor, llm_operation, 
                                     operation_name: str, circuit_breaker: CircuitBreaker, 
                                     provider: str, fallback_type: str) -> Any:
        """Execute retry template with all parameters."""
        return await execute_retry_template(
            self, retry_executor, llm_operation, operation_name, 
            circuit_breaker, provider, fallback_type
        )
    
    async def _try_operation(self, llm_operation, circuit_breaker: CircuitBreaker, provider: str) -> Any:
        """Try executing the LLM operation with timeout."""
        result = await asyncio.wait_for(llm_operation(), timeout=self.config.timeout)
        self._record_success(circuit_breaker, provider)
        return result
    
    def _record_success(self, circuit_breaker: CircuitBreaker, provider: str) -> None:
        """Record successful operation in circuit breaker."""
        if self.config.use_circuit_breaker and hasattr(circuit_breaker, 'record_success'):
            try:
                circuit_breaker.record_success()
            except (TypeError, AttributeError):
                logger.debug(f"Could not record success for circuit breaker {provider}")
    
    async def _handle_operation_failure(self, error: Exception, attempt: int, 
                                       operation_name: str, circuit_breaker: CircuitBreaker) -> None:
        """Handle operation failure with logging and circuit breaker recording."""
        failure_type = self._classify_error(error)
        self._record_retry_attempt(attempt, failure_type, str(error))
        self._record_circuit_failure_if_enabled(circuit_breaker, failure_type)
    
    def _record_circuit_failure_if_enabled(self, circuit_breaker: CircuitBreaker, failure_type: Any) -> None:
        """Record circuit breaker failure if circuit breaker is enabled."""
        if self.config.use_circuit_breaker:
            circuit_breaker.record_failure(failure_type)
    
    async def _wait_before_retry(self, attempt: int, error: Exception, operation_name: str) -> None:
        """Wait before retry with exponential backoff."""
        failure_type = self._classify_error(error)
        delay = self._calculate_delay(attempt, failure_type)
        self._log_retry_warning(operation_name, attempt, error, delay)
        await asyncio.sleep(delay)
    
    def _log_retry_warning(self, operation_name: str, attempt: int, error: Exception, delay: float) -> None:
        """Log retry warning message with details."""
        logger.warning(
            f"LLM operation {operation_name} failed (attempt {attempt}/{self.config.max_retries}): {error}. "
            f"Retrying in {delay:.2f}s"
        )
    
    async def execute_structured_with_fallback(
        self,
        llm_operation,
        schema: Type[T],
        operation_name: str,
        provider: str = "default"
    ) -> T:
        """Execute structured LLM operation with typed fallback"""
        result = await self._execute_operation_wrapper(llm_operation, operation_name, provider)
        return self._validate_or_create_fallback(result, schema)
    
    def _classify_error(self, error: Exception) -> FailureType:
        """Classify error type using Chain of Responsibility pattern."""
        return self.error_classifier.classify_error(error)
    
    # Error classification methods removed - now handled by ErrorClassificationChain
    
    def _calculate_delay(self, attempt: int, failure_type: FailureType) -> float:
        """Calculate exponential backoff delay with jitter"""
        base_delay = self._get_adjusted_base_delay(failure_type)
        delay = self._calculate_exponential_delay(base_delay, attempt)
        return self._add_jitter_to_delay(delay)
    
    def _get_adjusted_base_delay(self, failure_type: FailureType) -> float:
        """Get base delay adjusted for failure type."""
        base_delay = self.config.base_delay
        if failure_type == FailureType.RATE_LIMIT:
            return max(base_delay * 2, 5.0)
        elif failure_type == FailureType.TIMEOUT:
            return max(base_delay * 1.5, 2.0)
        return base_delay
    
    def _calculate_exponential_delay(self, base_delay: float, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = base_delay * (self.config.exponential_base ** (attempt - 1))
        return min(delay, self.config.max_delay)
    
    def _add_jitter_to_delay(self, delay: float) -> float:
        """Add jitter to delay to prevent thundering herd."""
        import random
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter
    
    def _record_retry_attempt(self, attempt: int, failure_type: FailureType, error_msg: str) -> None:
        """Record retry attempt for monitoring"""
        self.retry_manager.add_attempt(attempt, failure_type, error_msg)
    
    def _create_fallback_response(self, fallback_type: str, error: Optional[Exception] = None) -> Any:
        """Create appropriate fallback response"""
        return self.response_factory.create_response(fallback_type, error)
    
    def _create_structured_fallback(self, schema: Type[T]) -> T:
        """Create fallback instance using Builder pattern."""
        builder = StructuredFallbackBuilder(schema)
        return builder.build_field_defaults().build()
    
    async def _execute_operation_wrapper(self, llm_operation, operation_name: str, provider: str) -> Any:
        """Execute operation wrapper for structured fallback."""
        async def _operation():
            return await llm_operation()
        
        return await self.execute_with_fallback(
            _operation, operation_name, provider, "structured"
        )
    
    def _validate_or_create_fallback(self, result: Any, schema: Type[T]) -> T:
        """Validate result or create structured fallback."""
        if isinstance(result, schema):
            return result
        return self._create_structured_fallback(schema)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get fallback handler health status using composite pattern."""
        health_status = create_health_status_base(self.retry_manager.retry_history)
        health_status = add_circuit_breaker_status(health_status, self.circuit_breakers)
        return add_failure_type_breakdown(health_status, health_status["recent_failure_list"])
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")