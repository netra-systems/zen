"""Timing Decorators for Agent Performance Tracking

Provides easy-to-use decorators for automatic timing collection:
- Method-level timing with @time_operation
- Class-level timing with @timed_agent
- Async and sync support
- Automatic category detection

Business Value: Reduces implementation effort for performance tracking by 90%.
BVJ: Platform | Development Velocity | Simplified integration accelerates adoption
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Optional, Type, TypeVar, Union

from netra_backend.app.agents.base.timing_collector import (
    ExecutionTimingCollector,
    TimingCategory
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


def detect_category(operation_name: str) -> TimingCategory:
    """Auto-detect timing category based on operation name.
    
    Args:
        operation_name: Name of the operation
        
    Returns:
        Detected timing category
    """
    operation_lower = operation_name.lower()
    
    # LLM operations
    if any(keyword in operation_lower for keyword in ['llm', 'gpt', 'claude', 'openai', 'prompt', 'completion']):
        return TimingCategory.LLM
        
    # Database operations
    if any(keyword in operation_lower for keyword in ['query', 'database', 'db', 'sql', 'clickhouse', 'postgres']):
        return TimingCategory.DATABASE
        
    # Cache operations
    if any(keyword in operation_lower for keyword in ['cache', 'redis', 'memcache']):
        return TimingCategory.CACHE
        
    # Processing operations
    if any(keyword in operation_lower for keyword in ['process', 'analyze', 'compute', 'calculate', 'transform']):
        return TimingCategory.PROCESSING
        
    # Network operations
    if any(keyword in operation_lower for keyword in ['api', 'http', 'request', 'fetch', 'webhook']):
        return TimingCategory.NETWORK
        
    # Validation operations
    if any(keyword in operation_lower for keyword in ['validate', 'verify', 'check', 'assert']):
        return TimingCategory.VALIDATION
        
    # Orchestration operations
    if any(keyword in operation_lower for keyword in ['orchestrate', 'coordinate', 'pipeline', 'workflow']):
        return TimingCategory.ORCHESTRATION
        
    return TimingCategory.UNKNOWN


def time_operation(
    operation: Optional[str] = None,
    category: Optional[TimingCategory] = None,
    include_args: bool = False
) -> Callable:
    """Decorator for timing individual operations.
    
    Args:
        operation: Operation name (defaults to function name)
        category: Timing category (auto-detected if not provided)
        include_args: Whether to include function arguments in metadata
        
    Example:
        @time_operation("fetch_user_data", TimingCategory.DATABASE)
        async def get_user(self, user_id: int):
            return await self.db.fetch_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        # Get operation name
        op_name = operation or f"{func.__module__}.{func.__qualname__}"
        
        # Auto-detect category if not provided
        op_category = category or detect_category(op_name)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get timing collector from self if available
                collector = _get_collector_from_args(args)
                if not collector:
                    # Execute without timing if no collector available
                    return await func(*args, **kwargs)
                    
                # Build metadata
                metadata = _build_metadata(func, args, kwargs, include_args)
                
                # Time the operation
                with collector.time_operation(op_name, op_category, metadata):
                    return await func(*args, **kwargs)
                    
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Get timing collector from self if available
                collector = _get_collector_from_args(args)
                if not collector:
                    # Execute without timing if no collector available
                    return func(*args, **kwargs)
                    
                # Build metadata
                metadata = _build_metadata(func, args, kwargs, include_args)
                
                # Time the operation
                with collector.time_operation(op_name, op_category, metadata):
                    return func(*args, **kwargs)
                    
            return sync_wrapper
            
    return decorator


def timed_agent(cls: Type[T]) -> Type[T]:
    """Class decorator to add timing to all agent methods.
    
    Automatically adds ExecutionTimingCollector to the agent and
    times all public methods.
    
    Example:
        @timed_agent
        class MyAgent(BaseAgent):
            async def process(self):
                # Automatically timed
                pass
    """
    # Add timing collector to __init__
    original_init = cls.__init__
    
    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Add timing collector if not present
        if not hasattr(self, 'timing_collector'):
            agent_name = getattr(self, 'name', cls.__name__)
            self.timing_collector = ExecutionTimingCollector(agent_name)
            logger.debug(f"Added timing collector to {agent_name}")
            
    cls.__init__ = new_init
    
    # Time all public methods
    for name, method in inspect.getmembers(cls):
        # Skip private methods and properties
        if name.startswith('_'):
            continue
            
        # Skip non-callable members
        if not callable(method):
            continue
            
        # Skip already decorated methods
        if hasattr(method, '_timing_decorated'):
            continue
            
        # Get the actual function (unwrap if needed)
        func = method
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__
            
        # Only decorate methods defined in this class
        if not hasattr(func, '__qualname__') or cls.__name__ not in func.__qualname__:
            continue
            
        # Apply timing decorator
        operation_name = f"{cls.__name__}.{name}"
        timed_method = time_operation(operation_name)(method)
        timed_method._timing_decorated = True
        setattr(cls, name, timed_method)
        
    logger.info(f"Applied timing to {cls.__name__} agent")
    return cls


def time_step(
    step_name: str,
    category: Optional[TimingCategory] = None
) -> Callable:
    """Decorator for timing pipeline steps.
    
    Specifically designed for supervisor pipeline steps.
    
    Args:
        step_name: Name of the pipeline step
        category: Timing category (defaults to ORCHESTRATION)
        
    Example:
        @time_step("data_validation")
        async def validate_data(self, data):
            # Step execution
            pass
    """
    return time_operation(
        operation=f"pipeline_step.{step_name}",
        category=category or TimingCategory.ORCHESTRATION,
        include_args=False
    )


class TimingContext:
    """Context manager for timing with explicit collector.
    
    Useful when you need to time a block of code without decorators.
    
    Example:
        async with TimingContext(collector, "complex_operation", TimingCategory.PROCESSING):
            # Complex multi-step operation
            result1 = await step1()
            result2 = await step2(result1)
            return result2
    """
    
    def __init__(
        self,
        collector: ExecutionTimingCollector,
        operation: str,
        category: TimingCategory = TimingCategory.UNKNOWN,
        metadata: Optional[dict] = None
    ):
        self.collector = collector
        self.operation = operation
        self.category = category
        self.metadata = metadata or {}
        self.entry = None
        
    def __enter__(self):
        """Start timing on context entry."""
        self.entry = self.collector.start_timing(
            self.operation,
            self.category,
            self.metadata
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing on context exit."""
        error = str(exc_val) if exc_val else None
        if self.entry:
            self.collector.end_timing(self.entry, error)
            
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)


def _get_collector_from_args(args: tuple) -> Optional[ExecutionTimingCollector]:
    """Extract timing collector from function arguments.
    
    Args:
        args: Function arguments
        
    Returns:
        Timing collector if found in self argument
    """
    if not args:
        return None
        
    # First argument is typically self for methods
    self_arg = args[0]
    
    # Look for timing_collector attribute
    if hasattr(self_arg, 'timing_collector'):
        return self_arg.timing_collector
        
    # Look for collector in execution context
    if hasattr(self_arg, 'execution_context'):
        context = self_arg.execution_context
        if hasattr(context, 'timing_collector'):
            return context.timing_collector
            
    return None


def _build_metadata(
    func: Callable,
    args: tuple,
    kwargs: dict,
    include_args: bool
) -> dict:
    """Build metadata for timing entry.
    
    Args:
        func: Function being timed
        args: Function arguments
        kwargs: Function keyword arguments
        include_args: Whether to include arguments in metadata
        
    Returns:
        Metadata dictionary
    """
    metadata = {
        "function": func.__name__,
        "module": func.__module__
    }
    
    # Add agent name if available
    if args and hasattr(args[0], 'name'):
        metadata["agent_name"] = args[0].name
        
    # Include arguments if requested
    if include_args:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Add non-self arguments
        for param_name, param_value in bound_args.arguments.items():
            if param_name != 'self':
                # Convert to string for simple types
                if isinstance(param_value, (str, int, float, bool)):
                    metadata[f"arg_{param_name}"] = param_value
                else:
                    metadata[f"arg_{param_name}"] = type(param_value).__name__
                    
    return metadata


# Export convenience function for manual timing
def get_global_timing_collector() -> ExecutionTimingCollector:
    """Get or create a global timing collector.
    
    Returns:
        Global timing collector instance
    """
    if not hasattr(get_global_timing_collector, '_collector'):
        get_global_timing_collector._collector = ExecutionTimingCollector("global")
    return get_global_timing_collector._collector