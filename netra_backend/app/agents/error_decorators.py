"""Error Decorators Module.

Provides decorators and utilities for error handling.
Manages retry logic and error context creation.
"""

import asyncio
from typing import Any, Optional
from uuid import uuid4

from netra_backend.app.agents.error_recovery_strategy import ErrorRecoveryStrategy
from netra_backend.app.core.error_handlers.agents.agent_error_handler import AgentErrorHandler
from netra_backend.app.schemas.shared_types import ErrorContext

# Global error handler instance
global_error_handler = AgentErrorHandler()


def handle_agent_error(
    operation_name: Optional[str] = None,
    agent_name: Optional[str] = None, 
    max_retries: int = 3,
    retry_delay: float = 1.0,
    error_handler: Optional[AgentErrorHandler] = None,
    context_data: Optional[dict] = None
):
    """Decorator to handle agent errors with recovery."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Handle both bound methods and standalone functions
            if args and hasattr(args[0], '__class__'):
                self = args[0]
                func_args = args[1:]
            else:
                self = None
                func_args = args
            
            # Create context
            context = _create_error_context(
                operation_name or func.__name__, 
                self, 
                agent_name, 
                kwargs, 
                context_data
            )
            
            # Use custom handler or global
            handler = error_handler or global_error_handler
            
            # Execute with retry
            return await _execute_with_retry(
                func, self, func_args, kwargs, context, 
                operation_name or func.__name__, max_retries, retry_delay, handler
            )
        return wrapper
    return decorator


def _create_error_context(
    operation_name: str, 
    agent_instance, 
    agent_name: Optional[str],
    kwargs: dict,
    context_data: Optional[dict]
) -> ErrorContext:
    """Create error context for operation."""
    # Determine agent name
    if agent_name:
        resolved_agent_name = agent_name
    elif agent_instance:
        resolved_agent_name = getattr(agent_instance, 'name', agent_instance.__class__.__name__)
    else:
        resolved_agent_name = 'Unknown'
    
    # Create context
    context = ErrorContext(
        trace_id=str(uuid4()),
        operation=operation_name,
        agent_name=resolved_agent_name,
        operation_name=operation_name,
        run_id=kwargs.get('run_id', 'unknown')
    )
    
    # Add any additional context data
    if context_data:
        for key, value in context_data.items():
            setattr(context, key, value)
    
    return context


async def _execute_with_retry(
    func, 
    agent_instance, 
    args, 
    kwargs, 
    context: ErrorContext, 
    operation_name: str,
    max_retries: int,
    retry_delay: float,
    handler: AgentErrorHandler
) -> Any:
    """Execute function with retry logic."""
    max_attempts = max_retries + 1
    for attempt in range(max_attempts):
        context.retry_count = attempt
        context.max_retries = max_retries
        
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(func):
                if agent_instance is not None:
                    result = await func(agent_instance, *args, **kwargs)
                else:
                    result = await func(*args, **kwargs)
            else:
                if agent_instance is not None:
                    result = func(agent_instance, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt == max_attempts - 1:
                # Final attempt, handle error and potentially raise
                return await _handle_final_attempt_error(
                    e, context, operation_name, agent_instance, handler
                )
            else:
                # Retry attempt, check if should retry
                should_continue = await _handle_retry_attempt_error(
                    e, context, operation_name, agent_instance, attempt, handler, retry_delay
                )
                if not should_continue:
                    raise e


async def _handle_final_attempt_error(
    error: Exception, 
    context: ErrorContext, 
    operation_name: str, 
    agent_instance,
    handler: AgentErrorHandler
) -> Any:
    """Handle error on final attempt."""
    fallback = getattr(agent_instance, f'_fallback_{operation_name}', None) if agent_instance else None
    try:
        result = await handler.handle_error(error, context, fallback)
        # If the handler returns something other than None or an actual result,
        # but we're at max retries, we should still raise the original error
        # unless the result is explicitly a successful recovery (not an error object)
        from netra_backend.app.core.exceptions_agent import AgentError
        if isinstance(result, AgentError) and context.retry_count >= context.max_retries:
            # Handler returned an error object at max retries, re-raise original
            raise error
        return result
    except Exception:
        # If handler doesn't resolve it, re-raise the original error
        raise error


async def _handle_retry_attempt_error(
    error: Exception, 
    context: ErrorContext, 
    operation_name: str, 
    agent_instance, 
    attempt: int,
    handler: AgentErrorHandler,
    retry_delay: float
) -> bool:
    """Handle error on retry attempt. Returns True to continue retry, False to stop."""
    agent_error = handler._convert_to_agent_error(error, context)
    
    # Check if should retry based on error type and retry count
    if not handler.recovery_coordinator.strategy.should_retry(agent_error):
        return False
    
    # Apply retry delay
    await asyncio.sleep(retry_delay)
    return True