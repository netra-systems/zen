"""
Performance Tests - Index
Central index for all performance optimization tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all performance test modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.test_performance_batching import (
    TestBatchProcessor,
    TestMessageBatcher,
)
from netra_backend.tests.test_performance_cache import (
    # Add project root to path
    TestMemoryCache,
    TestQueryOptimizer,
)
from netra_backend.tests.test_performance_monitoring import (
    TestDatabaseIndexOptimization,
    TestPerformanceMonitoring,
    TestPerformanceOptimizationIntegration,
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestMemoryCache",
    "TestQueryOptimizer",
    "TestBatchProcessor", 
    "TestMessageBatcher",
    "TestPerformanceMonitoring",
    "TestDatabaseIndexOptimization",
    "TestPerformanceOptimizationIntegration"
]