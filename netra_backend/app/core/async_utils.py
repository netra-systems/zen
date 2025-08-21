"""Async utilities for proper resource management and optimized async patterns.

This module provides backward compatibility by re-exporting all functionality from the focused modules.
"""

# Import all classes and functions from the focused modules
from netra_backend.app.async_connection_pool import AsyncConnectionPool
from netra_backend.app.async_rate_limiter import AsyncRateLimiter
from netra_backend.app.async_retry_logic import (
    async_timeout,
    with_timeout,
    with_retry,
    AsyncCircuitBreaker,
    AsyncLock
)
from netra_backend.app.async_batch_processor import AsyncBatchProcessor
from netra_backend.app.async_resource_manager import (
    AsyncResourceManager,
    AsyncTaskPool,
    get_global_resource_manager,
    get_global_task_pool,
    run_in_threadpool,
    shutdown_async_utils
)

# Re-export everything for backward compatibility
__all__ = [
    # Connection pooling
    'AsyncConnectionPool',
    
    # Rate limiting
    'AsyncRateLimiter',
    
    # Retry and timeout logic
    'async_timeout',
    'with_timeout', 
    'with_retry',
    'AsyncCircuitBreaker',
    'AsyncLock',
    
    # Resource management
    'AsyncResourceManager',
    'AsyncTaskPool',
    'AsyncBatchProcessor',
    'get_global_resource_manager',
    'get_global_task_pool',
    'run_in_threadpool',
    'shutdown_async_utils'
]