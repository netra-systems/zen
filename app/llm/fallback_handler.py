"""
LLM Fallback Handler with exponential backoff and graceful degradation.

This module provides robust fallback mechanisms for LLM failures including:
- Exponential backoff retry logic
- Provider failover 
- Default response generation
- Circuit breaker integration
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, TypeVar, Type
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel

from app.logging_config import central_logger
from app.core.reliability import CircuitBreaker, CircuitBreakerConfig

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class FailureType(Enum):
    """Types of LLM failures"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit" 
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    UNKNOWN = "unknown"


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    timeout: float = 60.0
    use_circuit_breaker: bool = True
    log_circuit_breaker_warnings: bool = False


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    failure_type: FailureType
    error_message: str
    timestamp: float


class LLMFallbackHandler:
    """Handles LLM failures with retry logic and graceful degradation"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_history: List[RetryAttempt] = []
        self._init_default_responses()
    
    def _init_default_responses(self) -> None:
        """Initialize default response templates"""
        self.default_responses = {
            "triage": self._create_triage_response(),
            "data_analysis": self._create_data_analysis_response(),
            "general": "I apologize, but I'm experiencing technical difficulties. Please try again in a few moments."
        }
    
    def _create_triage_response(self) -> Dict[str, Any]:
        """Create default triage response template."""
        return {
            "category": "General Inquiry",
            "confidence_score": 0.5,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {"fallback_used": True}
        }
    
    def _create_data_analysis_response(self) -> Dict[str, Any]:
        """Create default data analysis response template."""
        return {
            "insights": ["Analysis unavailable due to system limitations"],
            "recommendations": ["Please try again later"],
            "confidence": 0.3,
            "metadata": {"fallback_used": True}
        }
    
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
        circuit_breaker = self._get_circuit_breaker(provider)
        if self._should_use_circuit_fallback(circuit_breaker, provider, fallback_type):
            return self._create_fallback_response(fallback_type)
        return await self._execute_with_retry(llm_operation, operation_name, 
                                             circuit_breaker, provider, fallback_type)
    
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
        """Execute operation with retry logic."""
        attempt = 0
        last_error = None
        
        while attempt < self.config.max_retries:
            try:
                result = await self._try_operation(llm_operation, circuit_breaker, provider)
                return result
            except Exception as e:
                attempt += 1
                last_error = e
                await self._handle_operation_failure(e, attempt, operation_name, circuit_breaker)
                
                if attempt < self.config.max_retries:
                    await self._wait_before_retry(attempt, e, operation_name)
                else:
                    logger.error(f"LLM operation {operation_name} failed after {attempt} attempts: {e}")
        
        return self._create_fallback_response(fallback_type, last_error)
    
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
        
        if self.config.use_circuit_breaker:
            circuit_breaker.record_failure(failure_type)
    
    async def _wait_before_retry(self, attempt: int, error: Exception, operation_name: str) -> None:
        """Wait before retry with exponential backoff."""
        failure_type = self._classify_error(error)
        delay = self._calculate_delay(attempt, failure_type)
        logger.warning(
            f"LLM operation {operation_name} failed (attempt {attempt}/{self.config.max_retries}): {error}. "
            f"Retrying in {delay:.2f}s"
        )
        await asyncio.sleep(delay)
    
    async def execute_structured_with_fallback(
        self,
        llm_operation,
        schema: Type[T],
        operation_name: str,
        provider: str = "default"
    ) -> T:
        """Execute structured LLM operation with typed fallback"""
        async def _operation():
            return await llm_operation()
        
        result = await self.execute_with_fallback(
            _operation,
            operation_name,
            provider,
            "structured"
        )
        
        if isinstance(result, schema):
            return result
        
        # Create fallback instance with default values
        return self._create_structured_fallback(schema)
    
    def _classify_error(self, error: Exception) -> FailureType:
        """Classify error type for appropriate handling"""
        if isinstance(error, asyncio.TimeoutError) or "timeout" in str(error).lower():
            return FailureType.TIMEOUT
        
        error_str = str(error).lower()
        return self._classify_by_error_string(error_str)
    
    def _classify_by_error_string(self, error_str: str) -> FailureType:
        """Classify error by string content."""
        if "rate limit" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        elif self._is_auth_error(error_str):
            return FailureType.AUTHENTICATION_ERROR
        elif self._is_network_error(error_str):
            return FailureType.NETWORK_ERROR
        elif "validation" in error_str:
            return FailureType.VALIDATION_ERROR
        elif self._is_api_error(error_str):
            return FailureType.API_ERROR
        return FailureType.UNKNOWN
    
    def _is_auth_error(self, error_str: str) -> bool:
        """Check if error is authentication-related."""
        return "auth" in error_str or "401" in error_str or "403" in error_str
    
    def _is_network_error(self, error_str: str) -> bool:
        """Check if error is network-related."""
        return "network" in error_str or "connection" in error_str
    
    def _is_api_error(self, error_str: str) -> bool:
        """Check if error is API-related."""
        return "api" in error_str or "500" in error_str
    
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
        retry_attempt = RetryAttempt(
            attempt_number=attempt,
            failure_type=failure_type,
            error_message=error_msg,
            timestamp=time.time()
        )
        self.retry_history.append(retry_attempt)
        
        # Keep only recent history to prevent memory leaks
        if len(self.retry_history) > 100:
            self.retry_history = self.retry_history[-50:]
    
    def _create_fallback_response(self, fallback_type: str, error: Optional[Exception] = None) -> Any:
        """Create appropriate fallback response"""
        if fallback_type in self.default_responses:
            response = self.default_responses[fallback_type].copy()
            if isinstance(response, dict) and "metadata" in response:
                response["metadata"]["error"] = str(error) if error else "Unknown error"
                response["metadata"]["timestamp"] = time.time()
            return response
        
        return self.default_responses["general"]
    
    def _create_structured_fallback(self, schema: Type[T]) -> T:
        """Create fallback instance of Pydantic model with safe defaults"""
        try:
            # Get model fields and create minimal valid instance
            field_defaults = {}
            
            for field_name, field_info in schema.model_fields.items():
                if field_info.default is not None:
                    field_defaults[field_name] = field_info.default
                elif field_info.annotation == str:
                    field_defaults[field_name] = "Unavailable due to system error"
                elif field_info.annotation == int:
                    field_defaults[field_name] = 0
                elif field_info.annotation == float:
                    field_defaults[field_name] = 0.0
                elif field_info.annotation == bool:
                    field_defaults[field_name] = False
                elif hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ == list:
                    field_defaults[field_name] = []
                elif hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ == dict:
                    field_defaults[field_name] = {}
            
            return schema(**field_defaults)
            
        except Exception as e:
            logger.error(f"Failed to create structured fallback for {schema.__name__}: {e}")
            # Last resort: try to create empty instance
            try:
                return schema()
            except Exception:
                raise ValueError(f"Cannot create fallback instance for {schema.__name__}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get fallback handler health status"""
        recent_failures = [
            attempt for attempt in self.retry_history
            if time.time() - attempt.timestamp < 300  # Last 5 minutes
        ]
        
        return {
            "total_retries": len(self.retry_history),
            "recent_failures": len(recent_failures),
            "circuit_breakers": {
                provider: cb.get_status()
                for provider, cb in self.circuit_breakers.items()
            },
            "failure_types": {
                failure_type.value: len([
                    a for a in recent_failures 
                    if a.failure_type == failure_type
                ])
                for failure_type in FailureType
            }
        }
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")