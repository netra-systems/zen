"""
Performance Tests - Index
Central index for all performance optimization tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all performance test modules
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.performance.test_performance_cache import (

# Add project root to path
    TestMemoryCache,
    TestQueryOptimizer
)
from netra_backend.tests.performance.test_performance_batching import (
    TestBatchProcessor,
    TestMessageBatcher
)
from netra_backend.tests.performance.test_performance_monitoring import (
    TestPerformanceMonitoring,
    TestDatabaseIndexOptimization,
    TestPerformanceOptimizationIntegration
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