"""
Performance Tests - Index
Central index for all performance optimization tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all performance test modules

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from netra_backend.tests.performance.test_performance_batching import (
    TestBatchProcessor,
    TestMessageBatcher,
)
from netra_backend.tests.performance.test_performance_cache import (
    TestMemoryCache,
    TestQueryOptimizer,
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestMemoryCache",
    "TestQueryOptimizer",
    "TestBatchProcessor", 
    "TestMessageBatcher",
]