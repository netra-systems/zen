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
            "triage": {
                "category": "General Inquiry",
                "confidence_score": 0.5,
                "priority": "medium",
                "extracted_entities": {},
                "tool_recommendations": [],
                "metadata": {"fallback_used": True}
            },
            "data_analysis": {
                "insights": ["Analysis unavailable due to system limitations"],
                "recommendations": ["Please try again later"],
                "confidence": 0.3,
                "metadata": {"fallback_used": True}
            },
            "general": "I apologize, but I'm experiencing technical difficulties. Please try again in a few moments."
        }
    
    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider not in self.circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                name=f"llm_fallback_{provider}"
            )
            self.circuit_breakers[provider] = CircuitBreaker(config)
        return self.circuit_breakers[provider]
    
    async def execute_with_fallback(
        self,
        llm_operation,
        operation_name: str,
        provider: str = "default",
        fallback_type: str = "general"
    ) -> Any:
        """Execute LLM operation with fallback handling"""
        circuit_breaker = self._get_circuit_breaker(provider)
        
        # Handle case where circuit_breaker might not be properly initialized
        is_circuit_open = False
        if self.config.use_circuit_breaker and hasattr(circuit_breaker, 'is_open'):
            try:
                is_circuit_open = circuit_breaker.is_open()
            except (TypeError, AttributeError):
                logger.warning(f"Circuit breaker for {provider} not properly initialized")
                is_circuit_open = False
        
        if is_circuit_open:
            logger.warning(f"Circuit breaker open for {provider}, using fallback")
            return self._create_fallback_response(fallback_type)
        
        attempt = 0
        last_error = None
        
        while attempt < self.config.max_retries:
            try:
                result = await asyncio.wait_for(
                    llm_operation(),
                    timeout=self.config.timeout
                )
                
                if self.config.use_circuit_breaker and hasattr(circuit_breaker, 'record_success'):
                    try:
                        circuit_breaker.record_success()
                    except (TypeError, AttributeError):
                        logger.debug(f"Could not record success for circuit breaker {provider}")
                
                return result
                
            except Exception as e:
                attempt += 1
                last_error = e
                failure_type = self._classify_error(e)
                
                self._record_retry_attempt(attempt, failure_type, str(e))
                
                if self.config.use_circuit_breaker:
                    circuit_breaker.record_failure()
                
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt, failure_type)
                    logger.warning(
                        f"LLM operation {operation_name} failed (attempt {attempt}/{self.config.max_retries}): {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM operation {operation_name} failed after {attempt} attempts: {e}")
        
        return self._create_fallback_response(fallback_type, last_error)
    
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
        error_str = str(error).lower()
        
        if "timeout" in error_str or isinstance(error, asyncio.TimeoutError):
            return FailureType.TIMEOUT
        elif "rate limit" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        elif "auth" in error_str or "401" in error_str or "403" in error_str:
            return FailureType.AUTHENTICATION_ERROR
        elif "network" in error_str or "connection" in error_str:
            return FailureType.NETWORK_ERROR
        elif "validation" in error_str:
            return FailureType.VALIDATION_ERROR
        elif "api" in error_str or "500" in error_str:
            return FailureType.API_ERROR
        else:
            return FailureType.UNKNOWN
    
    def _calculate_delay(self, attempt: int, failure_type: FailureType) -> float:
        """Calculate exponential backoff delay with jitter"""
        base_delay = self.config.base_delay
        
        # Adjust base delay for different failure types
        if failure_type == FailureType.RATE_LIMIT:
            base_delay = max(base_delay * 2, 5.0)
        elif failure_type == FailureType.TIMEOUT:
            base_delay = max(base_delay * 1.5, 2.0)
        
        delay = base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
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