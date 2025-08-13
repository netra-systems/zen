"""Error context management utilities for maintaining error context across async operations."""

import asyncio
from contextvars import ContextVar
from typing import Dict, Any, Optional
from uuid import uuid4


# Context variables for error tracking
_trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_error_context: ContextVar[Dict[str, Any]] = ContextVar('error_context', default={})


class ErrorContext:
    """Manages error context for tracking errors across async operations."""
    
    @staticmethod
    def set_trace_id(trace_id: str) -> str:
        """Set the trace ID for the current context."""
        _trace_id_context.set(trace_id)
        return trace_id
    
    @staticmethod
    def get_trace_id() -> Optional[str]:
        """Get the current trace ID."""
        return _trace_id_context.get()
    
    @staticmethod
    def generate_trace_id() -> str:
        """Generate and set a new trace ID."""
        trace_id = str(uuid4())
        _trace_id_context.set(trace_id)
        return trace_id
    
    @staticmethod
    def set_request_id(request_id: str) -> str:
        """Set the request ID for the current context."""
        _request_id_context.set(request_id)
        return request_id
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        """Get the current request ID."""
        return _request_id_context.get()
    
    @staticmethod
    def set_user_id(user_id: str) -> str:
        """Set the user ID for the current context."""
        _user_id_context.set(user_id)
        return user_id
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get the current user ID."""
        return _user_id_context.get()
    
    @staticmethod
    def set_context(key: str, value: Any) -> None:
        """Set a context value."""
        context = _error_context.get().copy()
        context[key] = value
        _error_context.set(context)
    
    @staticmethod
    def get_context(key: str, default: Any = None) -> Any:
        """Get a context value."""
        return _error_context.get().get(key, default)
    
    @staticmethod
    def get_all_context() -> Dict[str, Any]:
        """Get all context information."""
        base_context = {
            'trace_id': _trace_id_context.get(),
            'request_id': _request_id_context.get(),
            'user_id': _user_id_context.get(),
        }
        
        # Remove None values
        base_context = {k: v for k, v in base_context.items() if v is not None}
        
        # Add custom context
        custom_context = _error_context.get()
        if custom_context:
            base_context.update(custom_context)
        
        return base_context
    
    @staticmethod
    def clear_context() -> None:
        """Clear all context variables."""
        _trace_id_context.set(None)
        _request_id_context.set(None)
        _user_id_context.set(None)
        _error_context.set({})


class ErrorContextManager:
    """Context manager for error context."""
    
    def __init__(
        self,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **context_kwargs
    ):
        self.trace_id = trace_id or str(uuid4())
        self.request_id = request_id
        self.user_id = user_id
        self.context_kwargs = context_kwargs
        
        # Store previous values for restoration
        self.previous_trace_id = None
        self.previous_request_id = None
        self.previous_user_id = None
        self.previous_context = None
    
    def __enter__(self):
        """Enter the context manager."""
        # Store previous values
        self.previous_trace_id = ErrorContext.get_trace_id()
        self.previous_request_id = ErrorContext.get_request_id()
        self.previous_user_id = ErrorContext.get_user_id()
        self.previous_context = _error_context.get().copy()
        
        # Set new values
        ErrorContext.set_trace_id(self.trace_id)
        if self.request_id:
            ErrorContext.set_request_id(self.request_id)
        if self.user_id:
            ErrorContext.set_user_id(self.user_id)
        
        for key, value in self.context_kwargs.items():
            ErrorContext.set_context(key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # Restore previous values
        if self.previous_trace_id:
            ErrorContext.set_trace_id(self.previous_trace_id)
        else:
            _trace_id_context.set(None)
            
        if self.previous_request_id:
            ErrorContext.set_request_id(self.previous_request_id)
        else:
            _request_id_context.set(None)
            
        if self.previous_user_id:
            ErrorContext.set_user_id(self.previous_user_id)
        else:
            _user_id_context.set(None)
        
        _error_context.set(self.previous_context)


def with_error_context(
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **context_kwargs
):
    """Decorator to add error context to a function."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with ErrorContextManager(trace_id, request_id, user_id, **context_kwargs):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with ErrorContextManager(trace_id, request_id, user_id, **context_kwargs):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def get_enriched_error_context(additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get enriched error context with additional information."""
    context = ErrorContext.get_all_context()
    
    if additional_context:
        context.update(additional_context)
    
    return context