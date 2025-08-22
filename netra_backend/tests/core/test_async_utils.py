"""
Consolidated test suite for async utilities
Imports all modular test files to maintain test discovery while enforcing architectural compliance
≤300 lines, ≤8 lines per function
"""

# Import all split test modules to ensure test discovery

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from tests.core.test_async_batch_processor import TestAsyncBatchProcessor
from tests.core.test_async_connection_pool import TestAsyncConnectionPool
from tests.core.test_async_globals_threadpool import (
    # Add project root to path
    TestGlobalInstances,
    TestRunInThreadpool,
    TestShutdownAsyncUtils,
)
from tests.core.test_async_integration_scenarios import (
    TestIntegrationScenarios,
)
from tests.core.test_async_lock_circuit_breaker import (
    TestAsyncCircuitBreaker,
    TestAsyncLock,
)
from tests.core.test_async_rate_limiter import TestAsyncRateLimiter
from tests.core.test_async_resource_manager import (
    TestAsyncResourceManager,
)
from tests.core.test_async_task_pool import TestAsyncTaskPool
from tests.core.test_async_timeout_retry import (
    TestAsyncTimeout,
    TestWithRetry,
)

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])