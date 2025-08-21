"""Error Decorators Module.

Provides decorators and utilities for error handling.
Manages retry logic and error context creation.
"""

import asyncio
from uuid import uuid4
from typing import Any, Optional

from app.schemas.shared_types import ErrorContext
from netra_backend.app.agent_error_handler import AgentErrorHandler
from netra_backend.app.error_recovery_strategy import ErrorRecoveryStrategy


# Global error handler instance
global_error_handler = AgentErrorHandler()


def handle_agent_error(operation_name: str):
    """Decorator to handle agent errors with recovery."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            context = _create_error_context(operation_name, self, kwargs)
            return await _execute_with_retry(
                func, self, args, kwargs, context, operation_name
            )
        return wrapper
    return decorator


def _create_error_context(
    operation_name: str, 
    agent_instance, 
    kwargs: dict
) -> ErrorContext:
    """Create error context for operation."""
    return ErrorContext(
        trace_id=str(uuid4()),
        operation=operation_name,
        agent_name=getattr(agent_instance, 'name', 'Unknown'),
        operation_name=operation_name,
        run_id=kwargs.get('run_id', 'unknown')
    )


async def _execute_with_retry(
    func, 
    agent_instance, 
    args, 
    kwargs, 
    context: ErrorContext, 
    operation_name: str
) -> Any:
    """Execute function with retry logic."""
    max_attempts = 3
    for attempt in range(max_attempts):
        context.retry_count = attempt
        result = await _attempt_execution(
            func, agent_instance, args, kwargs, 
            context, operation_name, attempt, max_attempts
        )
        if result is not None:
            return result


async def _attempt_execution(
    func, 
    agent_instance, 
    args, 
    kwargs, 
    context: ErrorContext, 
    operation_name: str, 
    attempt: int, 
    max_attempts: int
) -> Any:
    """Attempt single execution with error handling."""
    try:
        return await func(agent_instance, *args, **kwargs)
    except Exception as e:
        return await _handle_execution_error(
            e, context, operation_name, agent_instance, attempt, max_attempts
        )


async def _handle_execution_error(
    error: Exception, 
    context: ErrorContext, 
    operation_name: str, 
    agent_instance, 
    attempt: int, 
    max_attempts: int
) -> Any:
    """Handle execution error with retry or fallback logic."""
    if attempt == max_attempts - 1:
        return await _handle_final_attempt_error(
            error, context, operation_name, agent_instance
        )
    return await _handle_retry_attempt_error(
        error, context, operation_name, agent_instance, attempt
    )


async def _handle_final_attempt_error(
    error: Exception, 
    context: ErrorContext, 
    operation_name: str, 
    agent_instance
) -> Any:
    """Handle error on final attempt."""
    fallback = getattr(agent_instance, f'_fallback_{operation_name}', None)
    return await global_error_handler.handle_error(error, context, fallback)


async def _handle_retry_attempt_error(
    error: Exception, 
    context: ErrorContext, 
    operation_name: str, 
    agent_instance, 
    attempt: int
) -> Optional[Any]:
    """Handle error on retry attempt."""
    agent_error = global_error_handler._convert_to_agent_error(error, context)
    if not global_error_handler.recovery_strategy.should_retry(agent_error):
        fallback = getattr(agent_instance, f'_fallback_{operation_name}', None)
        return await global_error_handler.handle_error(error, context, fallback)
    
    delay = ErrorRecoveryStrategy.get_recovery_delay(agent_error, attempt)
    await asyncio.sleep(delay)
    return None