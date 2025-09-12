"""
Retry Helper Functions

This module contains helper functions for the retry logic to keep each function  <= 8 lines.
Implements Template Method pattern components for retry operations.
"""

import asyncio
from typing import Any, Optional, Tuple

from netra_backend.app.llm.fallback_strategies import RetryExecutor
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def try_retry_attempt(retry_executor: RetryExecutor, llm_operation, 
                           circuit_breaker, provider: str) -> Optional[Any]:
    """Try a single retry attempt and return result or None on failure."""
    try:
        return await retry_executor.execute_operation(llm_operation, circuit_breaker, provider)
    except Exception:
        return None


async def handle_retry_failure(retry_executor: RetryExecutor, attempt: int, operation_name: str,
                             circuit_breaker, last_error: Exception, config) -> Tuple[int, Exception]:
    """Handle retry failure and return updated attempt count and error."""
    updated_attempt = await _process_failure_attempt(retry_executor, attempt, operation_name, circuit_breaker, last_error)
    await _handle_retry_delay_or_log(retry_executor, updated_attempt, operation_name, last_error, config)
    return updated_attempt, last_error

async def _process_failure_attempt(retry_executor: RetryExecutor, attempt: int, operation_name: str,
                                 circuit_breaker, error: Exception) -> int:
    """Process failure attempt and return incremented count."""
    attempt += 1
    await retry_executor.handle_operation_failure(error, attempt, operation_name, circuit_breaker)
    return attempt

async def _handle_retry_delay_or_log(retry_executor: RetryExecutor, attempt: int, operation_name: str,
                                   error: Exception, config) -> None:
    """Handle retry delay or final failure logging."""
    if attempt < config.max_retries:
        await retry_executor.wait_before_retry(attempt, error, operation_name)
    else:
        log_final_failure(operation_name, attempt, error)


def log_final_failure(operation_name: str, attempt: int, error: Exception) -> None:
    """Log final failure after all retry attempts."""
    logger.error(f"LLM operation {operation_name} failed after {attempt} attempts: {error}")


async def execute_retry_template(handler, retry_executor: RetryExecutor, llm_operation,
                               operation_name: str, circuit_breaker, provider: str, 
                               fallback_type: str) -> Any:
    """Template method for retry execution logic."""
    result = await _execute_retry_loop(handler, retry_executor, llm_operation, operation_name, circuit_breaker, provider)
    return result if result is not None else handler._create_fallback_response(fallback_type, None)

async def _attempt_retry_operation(retry_executor: RetryExecutor, llm_operation, 
                                  circuit_breaker, provider: str) -> Optional[Any]:
    """Attempt a single retry operation."""
    result = await try_retry_attempt(retry_executor, llm_operation, circuit_breaker, provider)
    return result if result is not None else None

async def _process_retry_attempt(handler, retry_executor: RetryExecutor, llm_operation,
                                operation_name: str, circuit_breaker, provider: str, 
                                attempt: int, last_error) -> tuple:
    """Process a single retry attempt."""
    result = await _attempt_retry_operation(retry_executor, llm_operation, circuit_breaker, provider)
    if result is not None:
        return result, None, None
    return None, *await handle_retry_failure(
        retry_executor, attempt, operation_name, circuit_breaker, last_error, handler.config
    )

async def _execute_retry_loop(handler, retry_executor: RetryExecutor, llm_operation,
                            operation_name: str, circuit_breaker, provider: str) -> Optional[Any]:
    """Execute retry loop and return successful result or None."""
    attempt, last_error = 0, None
    while attempt < handler.config.max_retries:
        result, attempt, last_error = await _process_retry_attempt(
            handler, retry_executor, llm_operation, operation_name, circuit_breaker, provider, attempt, last_error
        )
        if result is not None:
            return result
    return None


def create_health_status_base(retry_history: list) -> dict:
    """Create base health status with recent failures."""
    recent_failures = _get_recent_failures(retry_history)
    return _build_health_status_dict(retry_history, recent_failures)

def _get_recent_failures(retry_history: list, time_window: int = 300) -> list:
    """Get failures within the specified time window (default 5 minutes)."""
    import time
    cutoff_time = time.time() - time_window
    return [
        attempt for attempt in retry_history
        if attempt.timestamp >= cutoff_time
    ]

def _build_health_status_dict(retry_history: list, recent_failures: list) -> dict:
    """Build health status dictionary with failure counts."""
    return {
        "total_retries": len(retry_history),
        "recent_failures": len(recent_failures),
        "recent_failure_list": recent_failures
    }


def add_circuit_breaker_status(health_status: dict, circuit_breakers: dict) -> dict:
    """Add circuit breaker status to health status."""
    health_status["circuit_breakers"] = {
        provider: cb.get_status()
        for provider, cb in circuit_breakers.items()
    }
    return health_status


def _count_failures_by_type(recent_failures: list, failure_type) -> int:
    """Count failures of a specific type."""
    return len([a for a in recent_failures if a.failure_type == failure_type])

def add_failure_type_breakdown(health_status: dict, recent_failures: list) -> dict:
    """Add failure type breakdown to health status."""
    from netra_backend.app.core.interfaces_validation import FailureType
    health_status["failure_types"] = {
        failure_type.value: _count_failures_by_type(recent_failures, failure_type)
        for failure_type in FailureType
    }
    return health_status