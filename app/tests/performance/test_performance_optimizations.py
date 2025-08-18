"""
Performance Tests - Index
Central index for all performance optimization tests split across modules.
Compliance: <300 lines, 8-line max functions, modular design.
"""

# Import all performance test modules
from app.tests.performance.test_performance_cache import (
    TestMemoryCache,
    TestQueryOptimizer
)
from app.tests.performance.test_performance_batching import (
    TestBatchProcessor,
    TestMessageBatcher
)
from app.tests.performance.test_performance_monitoring import (
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