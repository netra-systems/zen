"""
Concurrent User Load Test Suite - Modular Index
Imports all concurrent load tests from focused modules.
Maximum 300 lines, functions ≤8 lines.
"""

# Import all test modules to ensure they're discovered by pytest
from tests.e2e.test_concurrent_load_core import TestConcurrentLoadCore
from tests.e2e.test_resource_exhaustion import TestResourceExhaustion
from tests.e2e.test_fair_queuing import TestFairQueuing
from tests.e2e.test_websocket_limits import TestWebSocketLimits

# Legacy alias for backward compatibility
TestConcurrentUserLoad = TestConcurrentLoadCore

# Re-export test classes for backward compatibility
__all__ = [
    'TestConcurrentLoadCore',
    'TestResourceExhaustion',
    'TestFairQueuing', 
    'TestWebSocketLimits',
    'TestConcurrentUserLoad'  # Legacy alias
]