"""Error context management utilities for maintaining error context across async operations."""

import asyncio
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# Context variables for error tracking
_trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_error_context: ContextVar[Dict[str, Any]] = ContextVar('error_context', default={})


class ErrorContextModel(BaseModel):
    """Error context model for consistent error handling"""
    trace_id: str = Field(..., description="Unique trace identifier")
    operation: str = Field(..., description="Operation being performed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    correlation_id: Optional[str] = Field(default=None, description="Correlation identifier")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    agent_name: Optional[str] = Field(default=None, description="Agent name")
    operation_name: Optional[str] = Field(default=None, description="Operation name")
    run_id: Optional[str] = Field(default=None, description="Run identifier")
    retry_count: int = Field(default=0, description="Retry count")
    max_retries: int = Field(default=3, description="Maximum retries")
    details: Dict[str, Any] = Field(default_factory=dict, description="Error details")
    additional_data: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    component: Optional[str] = Field(default=None, description="Component name")
    severity: Optional[str] = Field(default=None, description="Error severity")
    error_code: Optional[str] = Field(default=None, description="Error code")


class AsyncErrorContext:
    """Manages error context for tracking errors across async operations using context variables."""
    
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
        base_context = AsyncErrorContext._get_base_context()
        base_context = AsyncErrorContext._filter_none_values(base_context)
        return AsyncErrorContext._merge_custom_context(base_context)
    
    @staticmethod
    def _get_base_context() -> Dict[str, Any]:
        """Get base context information."""
        return {
            'trace_id': _trace_id_context.get(),
            'request_id': _request_id_context.get(),
            'user_id': _user_id_context.get(),
        }
    
    @staticmethod
    def _filter_none_values(context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values from context."""
        return {k: v for k, v in context.items() if v is not None}
    
    @staticmethod
    def _merge_custom_context(base_context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge custom context with base context."""
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


class AsyncErrorContextManager:
    """Context manager for error context."""
    
    def __init__(
        self,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **context_kwargs
    ):
        self._init_context_values(trace_id, request_id, user_id, context_kwargs)
        self._init_previous_values()
    
    def _init_context_values(self, trace_id: Optional[str], request_id: Optional[str], user_id: Optional[str], context_kwargs: dict) -> None:
        """Initialize context values."""
        self.trace_id = trace_id or str(uuid4())
        self.request_id = request_id
        self.user_id = user_id
        self.context_kwargs = context_kwargs
    
    def _init_previous_values(self) -> None:
        """Initialize previous values for restoration."""
        self.previous_trace_id = None
        self.previous_request_id = None
        self.previous_user_id = None
        self.previous_context = None
    
    def __enter__(self):
        """Enter the context manager."""
        self._store_previous_values()
        self._set_new_context_values()
        return self
    
    def _store_previous_values(self) -> None:
        """Store previous context values for restoration."""
        self.previous_trace_id = AsyncErrorContext.get_trace_id()
        self.previous_request_id = AsyncErrorContext.get_request_id()
        self.previous_user_id = AsyncErrorContext.get_user_id()
        self.previous_context = _error_context.get().copy()
    
    def _set_new_context_values(self) -> None:
        """Set new context values."""
        ErrorContext.set_trace_id(self.trace_id)
        self._set_optional_context_ids()
        self._set_custom_context_kwargs()
    
    def _set_optional_context_ids(self) -> None:
        """Set optional request and user IDs."""
        if self.request_id:
            ErrorContext.set_request_id(self.request_id)
        if self.user_id:
            ErrorContext.set_user_id(self.user_id)
    
    def _set_custom_context_kwargs(self) -> None:
        """Set custom context keyword arguments."""
        for key, value in self.context_kwargs.items():
            ErrorContext.set_context(key, value)
    
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        """Exit the context manager."""
        self._restore_trace_id()
        self._restore_request_id()
        self._restore_user_id()
        _error_context.set(self.previous_context)
    
    def _restore_trace_id(self) -> None:
        """Restore previous trace ID."""
        if self.previous_trace_id:
            AsyncErrorContext.set_trace_id(self.previous_trace_id)
        else:
            _trace_id_context.set(None)
    
    def _restore_request_id(self) -> None:
        """Restore previous request ID."""
        if self.previous_request_id:
            AsyncErrorContext.set_request_id(self.previous_request_id)
        else:
            _request_id_context.set(None)
    
    def _restore_user_id(self) -> None:
        """Restore previous user ID."""
        if self.previous_user_id:
            AsyncErrorContext.set_user_id(self.previous_user_id)
        else:
            _user_id_context.set(None)


def with_error_context(
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **context_kwargs
):
    """Decorator to add error context to a function."""
    def decorator(func):
        return _create_context_wrapper(func, trace_id, request_id, user_id, **context_kwargs)
    return decorator


def _create_context_wrapper(func, trace_id, request_id, user_id, **context_kwargs):
    """Create appropriate wrapper based on function type."""
    if asyncio.iscoroutinefunction(func):
        return _create_async_wrapper(func, trace_id, request_id, user_id, **context_kwargs)
    return _create_sync_wrapper(func, trace_id, request_id, user_id, **context_kwargs)


def _create_async_wrapper(func, trace_id, request_id, user_id, **context_kwargs):
    """Create async wrapper with error context."""
    async def async_wrapper(*args, **kwargs):
        with AsyncErrorContextManager(trace_id, request_id, user_id, **context_kwargs):
            return await func(*args, **kwargs)
    return async_wrapper


def _create_sync_wrapper(func, trace_id, request_id, user_id, **context_kwargs):
    """Create sync wrapper with error context."""
    def sync_wrapper(*args, **kwargs):
        with AsyncErrorContextManager(trace_id, request_id, user_id, **context_kwargs):
            return func(*args, **kwargs)
    return sync_wrapper


def get_enriched_error_context(additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get enriched error context with additional information."""
    context = AsyncErrorContext.get_all_context()
    
    if additional_context:
        context.update(additional_context)
    
    return context


# Alias for backward compatibility with imports
ErrorContext = AsyncErrorContext