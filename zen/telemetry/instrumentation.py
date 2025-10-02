"""
Telemetry Instrumentation Framework

Provides decorators and utilities for instrumenting functions and classes
with telemetry collection. Includes automatic data sanitization and PII filtering.
"""

import functools
import inspect
import logging
from typing import Optional, Dict, Any, Callable, Union, TypeVar, Type
import time
import asyncio

# OpenTelemetry imports with fallback
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from .manager import telemetry_manager
from .sanitization import DataSanitizer

logger = logging.getLogger(__name__)

# Type variables for generic decorators
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    capture_args: bool = False,
    capture_result: bool = False,
    sanitize_data: bool = True
) -> Callable[[F], F]:
    """
    Decorator to add distributed tracing to functions

    Args:
        name: Custom span name (defaults to function name)
        attributes: Additional span attributes
        capture_args: Whether to capture function arguments
        capture_result: Whether to capture function result
        sanitize_data: Whether to sanitize captured data for PII

    Example:
        @traced("user_operation", {"operation.type": "authentication"})
        def authenticate_user(username: str) -> bool:
            return True

        @traced(capture_args=True, capture_result=True)
        async def process_data(data: dict) -> dict:
            return {"status": "processed"}
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not telemetry_manager.is_enabled():
                return await func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__qualname__}"
            span_attributes = dict(attributes) if attributes else {}

            # Add function metadata
            span_attributes.update({
                "function.name": func.__name__,
                "function.module": func.__module__,
                "function.type": "async" if asyncio.iscoroutinefunction(func) else "sync"
            })

            # Capture arguments if requested
            if capture_args:
                sanitized_args = _capture_function_args(func, args, kwargs, sanitize_data)
                span_attributes.update(sanitized_args)

            start_time = time.time()

            with telemetry_manager.create_span(span_name, span_attributes) as span:
                try:
                    result = await func(*args, **kwargs)

                    # Capture result if requested
                    if capture_result and result is not None:
                        sanitized_result = DataSanitizer.sanitize_value(result) if sanitize_data else result
                        span.set_attribute("function.result", str(sanitized_result)[:1000])  # Limit size

                    # Record performance metrics
                    duration = time.time() - start_time
                    span.set_attribute("function.duration_ms", int(duration * 1000))

                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record exception
                    if hasattr(span, 'record_exception'):
                        span.record_exception(e)
                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.ERROR, str(e)))

                    # Add error attributes
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))

                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not telemetry_manager.is_enabled():
                return func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__qualname__}"
            span_attributes = dict(attributes) if attributes else {}

            # Add function metadata
            span_attributes.update({
                "function.name": func.__name__,
                "function.module": func.__module__,
                "function.type": "sync"
            })

            # Add community analytics metadata if enabled
            config = telemetry_manager.get_config()
            if config.use_community_analytics:
                span_attributes.update({
                    "zen.analytics.type": "community",
                    "zen.analytics.anonymous": True,
                    "zen.differentiator": "open_source_analytics",
                    "zen.contribution": "public_insights"
                })

            # Capture arguments if requested
            if capture_args:
                sanitized_args = _capture_function_args(func, args, kwargs, sanitize_data)
                span_attributes.update(sanitized_args)

            start_time = time.time()

            with telemetry_manager.create_span(span_name, span_attributes) as span:
                try:
                    result = func(*args, **kwargs)

                    # Capture result if requested
                    if capture_result and result is not None:
                        sanitized_result = DataSanitizer.sanitize_value(result) if sanitize_data else result
                        span.set_attribute("function.result", str(sanitized_result)[:1000])  # Limit size

                    # Record performance metrics
                    duration = time.time() - start_time
                    span.set_attribute("function.duration_ms", int(duration * 1000))

                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record exception
                    if hasattr(span, 'record_exception'):
                        span.record_exception(e)
                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.ERROR, str(e)))

                    # Add error attributes
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))

                    raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def instrument_class(
    methods: Optional[list] = None,
    exclude: Optional[list] = None,
    prefix: Optional[str] = None
) -> Callable[[Type[T]], Type[T]]:
    """
    Class decorator to instrument multiple methods

    Args:
        methods: List of method names to instrument (None = all public methods)
        exclude: List of method names to exclude
        prefix: Prefix for span names

    Example:
        @instrument_class(methods=["process", "validate"], prefix="orchestrator")
        class DataProcessor:
            def process(self, data): pass
            def validate(self, data): pass
    """
    def decorator(cls: Type[T]) -> Type[T]:
        if not telemetry_manager.is_enabled():
            return cls

        exclude_set = set(exclude or [])
        exclude_set.update({'__init__', '__new__', '__del__'})

        # Get methods to instrument
        if methods:
            methods_to_instrument = [m for m in methods if m not in exclude_set]
        else:
            methods_to_instrument = [
                name for name, method in inspect.getmembers(cls, predicate=inspect.ismethod)
                if not name.startswith('_') and name not in exclude_set
            ]

        # Instrument each method
        for method_name in methods_to_instrument:
            if hasattr(cls, method_name):
                original_method = getattr(cls, method_name)
                span_name = f"{prefix}.{method_name}" if prefix else f"{cls.__name__}.{method_name}"

                instrumented_method = traced(
                    name=span_name,
                    attributes={"class.name": cls.__name__, "method.name": method_name}
                )(original_method)

                setattr(cls, method_name, instrumented_method)

        return cls

    return decorator


def _capture_function_args(
    func: Callable,
    args: tuple,
    kwargs: dict,
    sanitize: bool = True
) -> Dict[str, str]:
    """
    Capture function arguments safely

    Args:
        func: The function being called
        args: Positional arguments
        kwargs: Keyword arguments
        sanitize: Whether to sanitize the data

    Returns:
        Dictionary of sanitized argument data
    """
    try:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        captured = {}
        for param_name, value in bound_args.arguments.items():
            # Skip 'self' and 'cls' parameters
            if param_name in ('self', 'cls'):
                continue

            # Convert to string and sanitize if needed
            value_str = str(value)
            if sanitize:
                value_str = DataSanitizer.sanitize_value(value_str)

            # Limit size to prevent large spans
            captured[f"function.arg.{param_name}"] = value_str[:500]

        return captured

    except Exception as e:
        logger.debug(f"Failed to capture function arguments: {e}")
        return {"function.args.error": str(e)}


def trace_performance(operation: str, **attributes) -> "PerformanceTracer":
    """
    Context manager for performance tracing

    Args:
        operation: Name of the operation being traced
        **attributes: Additional attributes to add to the span

    Example:
        with trace_performance("database_query", table="users"):
            result = db.query("SELECT * FROM users")
    """
    return PerformanceTracer(operation, attributes)


class PerformanceTracer:
    """Context manager for performance tracing"""

    def __init__(self, operation: str, attributes: Dict[str, Any]):
        self.operation = operation
        self.attributes = attributes
        self.span = None
        self.start_time = None

    def set_attribute(self, key: str, value: Any):
        """Set attribute on the span (no-op if telemetry disabled)"""
        if self.span and hasattr(self.span, 'set_attribute'):
            self.span.set_attribute(key, value)

    def __enter__(self):
        if not telemetry_manager.is_enabled():
            return self

        self.start_time = time.time()
        self.span = telemetry_manager.create_span(
            f"performance.{self.operation}",
            {
                "operation.type": "performance",
                "operation.name": self.operation,
                **self.attributes
            }
        )
        span_context = self.span.__enter__()
        # Return self so set_attribute works on PerformanceTracer
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span and self.start_time:
            duration = time.time() - self.start_time
            self.span.set_attribute("performance.duration_ms", int(duration * 1000))

            if exc_type:
                self.span.set_attribute("performance.error", True)
                self.span.set_attribute("performance.error_type", exc_type.__name__)

            self.span.__exit__(exc_type, exc_val, exc_tb)


def instrument_async_generator(name: Optional[str] = None):
    """
    Decorator for async generators

    Example:
        @instrument_async_generator("data_stream")
        async def process_data_stream():
            for i in range(10):
                yield f"data_{i}"
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not telemetry_manager.is_enabled():
                async for item in func(*args, **kwargs):
                    yield item
                return

            span_name = name or f"{func.__module__}.{func.__qualname__}"

            with telemetry_manager.create_span(span_name) as span:
                try:
                    count = 0
                    async for item in func(*args, **kwargs):
                        count += 1
                        yield item

                    span.set_attribute("generator.items_yielded", count)
                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.OK))

                except Exception as e:
                    if hasattr(span, 'record_exception'):
                        span.record_exception(e)
                    if hasattr(span, 'set_status'):
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper
    return decorator