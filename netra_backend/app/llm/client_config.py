"""LLM client configuration module.

Provides circuit breaker configurations for different LLM types.
Each configuration is optimized for specific performance characteristics.
"""

from app.schemas.core_models import CircuitBreakerConfig


class LLMClientConfig:
    """Configuration for LLM client circuit breakers."""
    
    # Circuit breaker configurations for different LLM types
    FAST_LLM_CONFIG = CircuitBreakerConfig(
        name="fast_llm",
        failure_threshold=5,  # Increased from 3
        recovery_timeout=20.0,  # Increased from 15
        timeout_seconds=10,  # Increased from 5
        slow_call_threshold=3.0  # Increased from 2
    )
    
    STANDARD_LLM_CONFIG = CircuitBreakerConfig(
        name="standard_llm", 
        failure_threshold=7,  # Increased from 5
        recovery_timeout=45.0,  # Increased from 30
        timeout_seconds=20,  # Increased from 15
        slow_call_threshold=15.0  # Increased from 10
    )
    
    SLOW_LLM_CONFIG = CircuitBreakerConfig(
        name="slow_llm",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout_seconds=30,
        slow_call_threshold=20.0
    )
    
    STRUCTURED_LLM_CONFIG = CircuitBreakerConfig(
        name="structured_llm",
        failure_threshold=3,
        recovery_timeout=20.0,
        timeout_seconds=10,
        slow_call_threshold=5.0
    )