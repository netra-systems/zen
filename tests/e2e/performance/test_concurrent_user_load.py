"""
Concurrent User Load Test Suite - Modular Index
Imports all concurrent load tests from focused modules.
Maximum 300 lines, functions ≤8 lines.
"""

# Import all test modules to ensure they're discovered by pytest

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from tests.e2e.test_concurrent_load_core import TestConcurrentLoadCore
from tests.e2e.test_fair_queuing import TestFairQueuing
from tests.e2e.test_resource_exhaustion import TestResourceExhaustion
from tests.e2e.test_websocket_limits import TestWebSocketLimits

# Add project root to path

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