"""WebSocket Load Testing and Performance Validation - Main Index Module

Re-exports all test classes from focused modules for backwards compatibility.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest

# Import all test classes from focused modules
from .test_websocket_load_metrics import LoadTestMetrics, WebSocketLoadTester
from .test_websocket_performance_components import (
    TestWebSocketMemoryManagerPerformance,
    TestWebSocketMessageBatcherPerformance,
    TestWebSocketCompressionPerformance,
    TestWebSocketPerformanceMonitorAlerting,
    TestWebSocketStateSynchronizerResilience
)
from .test_websocket_load_scenarios import (
    TestWebSocketLoadScenarios,
    TestWebSocketLoadEdgeCases
)

# Re-export all classes and functions for backwards compatibility
__all__ = [
    'LoadTestMetrics',
    'WebSocketLoadTester', 
    'TestWebSocketMemoryManagerPerformance',
    'TestWebSocketMessageBatcherPerformance',
    'TestWebSocketCompressionPerformance',
    'TestWebSocketPerformanceMonitorAlerting',
    'TestWebSocketStateSynchronizerResilience',
    'TestWebSocketLoadScenarios',
    'TestWebSocketLoadEdgeCases'
]


if __name__ == "__main__":
    # Run performance tests
    import asyncio
    asyncio.run(test_integrated_performance_improvements())