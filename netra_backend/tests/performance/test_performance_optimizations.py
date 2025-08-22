"""
Performance Tests - Index
Central index for all performance optimization tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all performance test modules

import sys
from pathlib import Path

from test_framework import setup_test_path

from netra_backend.tests.test_performance_batching import (
    TestBatchProcessor,
    TestMessageBatcher,
)
from netra_backend.tests.test_performance_cache import (
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