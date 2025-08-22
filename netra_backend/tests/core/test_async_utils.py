"""
Consolidated test suite for async utilities
Imports all modular test files to maintain test discovery while enforcing architectural compliance
≤300 lines, ≤8 lines per function
"""

# Import all split test modules to ensure test discovery

import sys
from pathlib import Path

from test_framework import setup_test_path

from core.test_async_batch_processor import TestAsyncBatchProcessor
from core.test_async_connection_pool import TestAsyncConnectionPool
from core.test_async_globals_threadpool import (
    TestGlobalInstances,
    TestRunInThreadpool,
    TestShutdownAsyncUtils,
)
from core.test_async_integration_scenarios import (
    TestIntegrationScenarios,
)
from core.test_async_lock_circuit_breaker import (
    TestAsyncCircuitBreaker,
    TestAsyncLock,
)
from core.test_async_rate_limiter import TestAsyncRateLimiter
from core.test_async_resource_manager import (
    TestAsyncResourceManager,
)
from core.test_async_task_pool import TestAsyncTaskPool
from core.test_async_timeout_retry import (
    TestAsyncTimeout,
    TestWithRetry,
)

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])