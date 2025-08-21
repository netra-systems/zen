"""
Consolidated test suite for async utilities
Imports all modular test files to maintain test discovery while enforcing architectural compliance
≤300 lines, ≤8 lines per function
"""

# Import all split test modules to ensure test discovery
from netra_backend.tests.core.test_async_resource_manager import TestAsyncResourceManager
from netra_backend.tests.core.test_async_task_pool import TestAsyncTaskPool
from netra_backend.tests.core.test_async_rate_limiter import TestAsyncRateLimiter
from netra_backend.tests.core.test_async_timeout_retry import TestAsyncTimeout, TestWithRetry
from netra_backend.tests.core.test_async_batch_processor import TestAsyncBatchProcessor
from netra_backend.tests.core.test_async_lock_circuit_breaker import TestAsyncLock, TestAsyncCircuitBreaker
from netra_backend.tests.core.test_async_connection_pool import TestAsyncConnectionPool
from netra_backend.tests.core.test_async_globals_threadpool import (
    TestGlobalInstances,
    TestRunInThreadpool,
    TestShutdownAsyncUtils,
)
from netra_backend.tests.core.test_async_integration_scenarios import TestIntegrationScenarios

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])