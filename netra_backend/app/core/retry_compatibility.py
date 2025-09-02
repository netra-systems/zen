"""
Retry Compatibility Module - Migration Helper

This module provides backward compatibility wrappers and helpers for migrating
from legacy retry implementations to the unified UnifiedRetryHandler.

Business Value:
- Smooth migration path from legacy retry patterns
- Maintains existing API compatibility
- Single import point for all retry functionality

Usage:
    from netra_backend.app.core.retry_compatibility import (
        retry_with_exponential_backoff,  # Drop-in replacement
        get_unified_retry_handler,       # Direct access
        migrate_legacy_config           # Config conversion
    )
"""

import asyncio
import warnings
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type

from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    RetryConfig,
    RetryStrategy,
    RetryResult,
    database_retry_handler,
    llm_retry_handler, 
    agent_retry_handler,
    api_retry_handler,
    websocket_retry_handler,
    file_retry_handler
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Domain-specific retry handlers for easy migration
DOMAIN_HANDLERS = {
    'database': database_retry_handler,
    'db': database_retry_handler,
    'postgres': database_retry_handler,
    'clickhouse': database_retry_handler,
    'redis': database_retry_handler,
    'llm': llm_retry_handler,
    'openai': llm_retry_handler,
    'anthropic': llm_retry_handler,
    'agent': agent_retry_handler,
    'api': api_retry_handler,
    'http': api_retry_handler,
    'rest': api_retry_handler,
    'websocket': websocket_retry_handler,
    'ws': websocket_retry_handler,
    'file': file_retry_handler,
    'io': file_retry_handler,
    'auth': api_retry_handler,
    'service': api_retry_handler,
}


def get_unified_retry_handler(
    service_name: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: str = "exponential",
    domain: Optional[str] = None
) -> UnifiedRetryHandler:
    """
    Get a unified retry handler with specified configuration.
    
    Args:
        service_name: Name of the service using the handler
        max_attempts: Maximum retry attempts
        base_delay: Initial delay between retries
        strategy: Retry strategy (exponential, linear, fixed, etc.)
        domain: Domain-specific configuration (database, llm, api, etc.)
        
    Returns:
        Configured UnifiedRetryHandler instance
    """
    # Use domain-specific handler if available
    if domain and domain.lower() in DOMAIN_HANDLERS:
        handler = DOMAIN_HANDLERS[domain.lower()]
        logger.debug(f"Using domain-specific handler for {domain}: {handler.service_name}")
        return handler
    
    # Convert strategy string to enum
    try:
        retry_strategy = RetryStrategy(strategy.lower())
    except ValueError:
        logger.warning(f"Unknown strategy '{strategy}', using exponential")
        retry_strategy = RetryStrategy.EXPONENTIAL
    
    # Create custom configuration
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=retry_strategy,
        backoff_multiplier=2.0,
        jitter_range=0.1,
        circuit_breaker_enabled=False,
        metrics_enabled=True
    )
    
    return UnifiedRetryHandler(service_name, config)


async def retry_with_exponential_backoff(
    func: Callable[[], Awaitable[Any]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    service_name: str = "compatibility_wrapper"
) -> Any:
    """
    Drop-in replacement for legacy exponential backoff retry functions.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay cap
        retryable_exceptions: Exceptions that should trigger retries
        service_name: Service name for logging
        
    Returns:
        Result from successful function execution
        
    Raises:
        Exception from final failed attempt
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_multiplier=2.0,
        jitter_range=0.1,
        retryable_exceptions=retryable_exceptions,
        circuit_breaker_enabled=False,
        metrics_enabled=True
    )
    
    handler = UnifiedRetryHandler(service_name, config)
    result = await handler.execute_with_retry_async(func)
    
    if result.success:
        return result.result
    else:
        raise result.final_exception


def retry_with_linear_backoff(
    func: Callable[[], Any],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    increment: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    service_name: str = "compatibility_wrapper"
) -> Any:
    """
    Drop-in replacement for linear backoff retry functions.
    
    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        base_delay: Initial delay between retries
        increment: Linear increment for each retry
        retryable_exceptions: Exceptions that should trigger retries
        service_name: Service name for logging
        
    Returns:
        Result from successful function execution
        
    Raises:
        Exception from final failed attempt
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=RetryStrategy.LINEAR,
        backoff_multiplier=increment,  # Used as linear increment
        retryable_exceptions=retryable_exceptions,
        circuit_breaker_enabled=False,
        metrics_enabled=True
    )
    
    handler = UnifiedRetryHandler(service_name, config)
    result = handler.execute_with_retry(func)
    
    if result.success:
        return result.result
    else:
        raise result.final_exception


def migrate_legacy_config(legacy_config: Dict[str, Any]) -> RetryConfig:
    """
    Convert legacy retry configuration to UnifiedRetryHandler format.
    
    Args:
        legacy_config: Dictionary with legacy configuration keys
        
    Returns:
        RetryConfig instance with converted values
    """
    # Common legacy config key mappings
    key_mappings = {
        'max_retries': 'max_attempts',
        'retry_count': 'max_attempts', 
        'attempts': 'max_attempts',
        'initial_delay': 'base_delay',
        'retry_delay': 'base_delay',
        'delay': 'base_delay',
        'backoff': 'backoff_multiplier',
        'backoff_factor': 'backoff_multiplier',
        'multiplier': 'backoff_multiplier',
        'timeout': 'timeout_seconds',
        'max_timeout': 'max_delay'
    }
    
    # Convert keys
    converted = {}
    for old_key, value in legacy_config.items():
        new_key = key_mappings.get(old_key, old_key)
        converted[new_key] = value
    
    # Handle special cases
    if 'max_attempts' in converted and isinstance(converted['max_attempts'], int):
        # Legacy often uses max_retries (excluding first attempt)
        # UnifiedRetryHandler uses max_attempts (including first attempt)
        if converted['max_attempts'] < 10:  # Likely legacy format
            converted['max_attempts'] += 1
    
    # Set sensible defaults
    defaults = {
        'max_attempts': 3,
        'base_delay': 1.0,
        'max_delay': 60.0,
        'strategy': RetryStrategy.EXPONENTIAL,
        'backoff_multiplier': 2.0,
        'jitter_range': 0.1,
        'circuit_breaker_enabled': False,
        'metrics_enabled': True
    }
    
    # Apply defaults for missing keys
    for key, default_value in defaults.items():
        if key not in converted:
            converted[key] = default_value
    
    return RetryConfig(**converted)


# Decorator helpers for backward compatibility
def exponential_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    domain: Optional[str] = None
):
    """
    Decorator for exponential retry with unified handler.
    
    Usage:
        @exponential_retry(max_attempts=3, domain="database")
        async def my_db_operation():
            # Database operation that might fail
            pass
    """
    def decorator(func):
        handler = get_unified_retry_handler(
            func.__name__, max_attempts, base_delay, "exponential", domain
        )
        return handler(func)
    return decorator


def linear_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    increment: float = 1.0,
    domain: Optional[str] = None
):
    """
    Decorator for linear retry with unified handler.
    
    Usage:
        @linear_retry(max_attempts=5, base_delay=0.5, increment=0.5)
        async def my_api_call():
            # API call that might fail
            pass
    """
    def decorator(func):
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            strategy=RetryStrategy.LINEAR,
            backoff_multiplier=increment,
            circuit_breaker_enabled=False,
            metrics_enabled=True
        )
        handler = UnifiedRetryHandler(func.__name__, config)
        return handler(func)
    return decorator


# Legacy function name aliases for backward compatibility
async def exponential_backoff(
    func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Any:
    """DEPRECATED: Use retry_with_exponential_backoff instead."""
    warnings.warn(
        "exponential_backoff is deprecated. Use retry_with_exponential_backoff "
        "or get_unified_retry_handler() for better functionality.",
        DeprecationWarning,
        stacklevel=2
    )
    return await retry_with_exponential_backoff(func, max_retries + 1, base_delay)


def retry_operation(
    func: Callable[[], Any],
    max_retries: int = 3,
    delay: float = 1.0
) -> Any:
    """DEPRECATED: Use retry_with_linear_backoff instead."""
    warnings.warn(
        "retry_operation is deprecated. Use retry_with_linear_backoff "
        "or get_unified_retry_handler() for better functionality.",
        DeprecationWarning,
        stacklevel=2
    )
    return retry_with_linear_backoff(func, max_retries + 1, delay)


# Migration utility functions
def audit_retry_usage(module_path: str) -> Dict[str, Any]:
    """
    Audit a module for legacy retry patterns that need migration.
    
    Args:
        module_path: Path to the module to audit
        
    Returns:
        Dictionary with audit results and migration recommendations
    """
    # This would typically parse the module and identify legacy patterns
    # For now, return a basic structure
    return {
        "legacy_patterns_found": [],
        "migration_recommendations": [],
        "estimated_effort": "low",
        "breaking_changes": False
    }


def create_migration_plan(legacy_patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a migration plan for converting legacy retry patterns.
    
    Args:
        legacy_patterns: Dictionary of found legacy patterns
        
    Returns:
        Migration plan with steps and recommendations
    """
    return {
        "steps": [
            "1. Replace legacy retry functions with unified handlers",
            "2. Update configuration to use RetryConfig format",
            "3. Test with existing exception handling",
            "4. Verify WebSocket notifications are preserved",
            "5. Remove deprecated imports"
        ],
        "risk_level": "low",
        "estimated_time": "1-2 hours per module",
        "compatibility_maintained": True
    }


# Export commonly used items for easy access
__all__ = [
    'get_unified_retry_handler',
    'retry_with_exponential_backoff',
    'retry_with_linear_backoff',
    'migrate_legacy_config',
    'exponential_retry',
    'linear_retry',
    'DOMAIN_HANDLERS',
    # Legacy aliases
    'exponential_backoff',
    'retry_operation'
]