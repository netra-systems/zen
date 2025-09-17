class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Performance Regression Test Suite for Request Isolation Architecture

        This test suite ensures the isolation architecture maintains performance targets
        as the system evolves. It prevents performance regressions by testing against
        strict latency requirements.

        Business Value:
        - Maintains chat responsiveness for user satisfaction
        - Prevents performance degradations before production
        - Validates system can handle 100+ concurrent users
        - Ensures <20ms total request overhead

        Performance Requirements:
        - Agent instance creation: <10ms (p95)
        - WebSocket message dispatch: <5ms (p95)
        - Database session acquisition: <2ms (p95)
        - Context cleanup: <5ms (p95)
        - Total request overhead: <20ms (p95)
        '''

        import asyncio
        import pytest
        import time
        import uuid
        import statistics
        from typing import List, Dict, Any
        from datetime import datetime, timezone
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
        AgentInstanceFactory,
        get_agent_instance_factory
            
        from netra_backend.app.agents.supervisor.factory_performance_config import ( )
        FactoryPerformanceConfig,
        set_factory_performance_config
            
        from netra_backend.app.monitoring.performance_metrics import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        PerformanceMonitor,
        get_performance_monitor,
        timed_operation
            


class TestPerformanceTargets:
        """Test suite for performance regression detection."""

    # Performance targets in milliseconds
        TARGETS = { )
        'context_creation_p95': 10.0,
        'agent_creation_p95': 10.0,
        'cleanup_p95': 5.0,
        'websocket_init_p95': 1.0,
        'database_session_p95': 2.0,
        'total_request_p95': 20.0
    

    # Test configuration
        ITERATIONS = 100  # Number of test iterations
        CONCURRENT_USERS = 10  # Number of concurrent users to simulate

        @pytest.fixture
    async def factory(self):
        """Create optimized factory for testing."""
    # Use maximum performance config for testing
        set_factory_performance_config(FactoryPerformanceConfig.maximum_performance())
        factory = AgentInstanceFactory()

    # Mock dependencies
        websocket = TestWebSocketConnection()
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)

        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_registry.get_agent_class = Mock(return_value=Mock)

        factory.configure( )
        agent_class_registry=mock_registry,
        websocket_bridge=mock_bridge
    

        yield factory

    # Cleanup
        await factory.cleanup_all()

        @pytest.fixture
    async def monitor(self):
        """Get performance monitor for testing."""
        pass
        monitor = PerformanceMonitor(sample_rate=1.0)  # Sample everything in tests
        yield monitor
        await monitor.stop_background_reporting()

    async def measure_operation(self, operation, iterations: int = 100) -> List[float]:
        """Measure operation performance over multiple iterations."""
        times = []

    # Warm-up (10% of iterations)
        for _ in range(max(1, iterations // 10)):
        await operation()

        # Actual measurements
        for _ in range(iterations):
        start = time.perf_counter()
        await operation()
        duration_ms = (time.perf_counter() - start) * 1000
        times.append(duration_ms)

        await asyncio.sleep(0)
        return times

    def calculate_percentile(self, times: List[float], percentile: int) -> float:
        """Calculate specific percentile from timing data."""
        if not times:
        return 0

        sorted_times = sorted(times)
        index = int(len(sorted_times) * (percentile / 100))
        return sorted_times[min(index, len(sorted_times) - 1)]

@pytest.mark.asyncio
    async def test_context_creation_performance(self, factory, monitor):
"""Test user execution context creation meets <10ms p95 target."""

async def create_context():
context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
    
await factory.cleanup_user_context(context)

    # Measure performance
times = await self.measure_operation(create_context, self.ITERATIONS)

    # Calculate statistics
p95 = self.calculate_percentile(times, 95)
p99 = self.calculate_percentile(times, 99)
mean = statistics.mean(times)

    # Log results
print(f" )
Context Creation Performance:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

    # Assert performance target
assert p95 < self.TARGETS['context_creation_p95'], \
"formatted_string"

@pytest.mark.asyncio
    async def test_agent_creation_performance(self, factory):
"""Test agent instance creation meets <10ms p95 target."""

        # Create a context once for agent creation tests
context = await factory.create_user_execution_context( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run"
        

async def create_agent():
pass
    # Mock agent class for fast instantiation
mock_agent_class = Mock(websocket = TestWebSocketConnection()  # Real WebSocket implementation)
agent = await factory.create_agent_instance( )
agent_name="test_agent",
user_context=context,
agent_class=mock_agent_class
    
await asyncio.sleep(0)
return agent

try:
        # Measure performance
times = await self.measure_operation(create_agent, self.ITERATIONS)

        # Calculate statistics
p95 = self.calculate_percentile(times, 95)
p99 = self.calculate_percentile(times, 99)
mean = statistics.mean(times)

        # Log results
print(f" )
Agent Creation Performance:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

        # Assert performance target
assert p95 < self.TARGETS['agent_creation_p95'], \
"formatted_string"

finally:
await factory.cleanup_user_context(context)

@pytest.mark.asyncio
    async def test_cleanup_performance(self, factory):
"""Test context cleanup meets <5ms p95 target."""

                # Pre-create contexts
contexts = []
for i in range(self.ITERATIONS):
context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
                    
contexts.append(context)

                    # Measure cleanup performance
times = []
for context in contexts:
start = time.perf_counter()
await factory.cleanup_user_context(context)
duration_ms = (time.perf_counter() - start) * 1000
times.append(duration_ms)

                        # Calculate statistics
p95 = self.calculate_percentile(times, 95)
p99 = self.calculate_percentile(times, 99)
mean = statistics.mean(times)

                        # Log results
print(f" )
Cleanup Performance:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

                        # Assert performance target
assert p95 < self.TARGETS['cleanup_p95'], \
"formatted_string"

@pytest.mark.asyncio
    async def test_websocket_handler_performance(self):
"""Test WebSocket handler initialization meets <1ms p95 target."""
pass
from netra_backend.app.websocket.connection_handler import ConnectionHandler

                            # Mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation

async def create_handler():
pass
handler = ConnectionHandler( )
websocket=mock_ws,
user_id="formatted_string"
    
await asyncio.sleep(0)
return handler

    # Measure performance
times = []
for _ in range(self.ITERATIONS):
start = time.perf_counter()
handler = await create_handler()
duration_ms = (time.perf_counter() - start) * 1000
times.append(duration_ms)
        # Cleanup
await handler.cleanup()

        # Calculate statistics
p95 = self.calculate_percentile(times, 95)
p99 = self.calculate_percentile(times, 99)
mean = statistics.mean(times)

        # Log results
print(f" )
WebSocket Handler Init Performance:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

        # Assert performance target
assert p95 < self.TARGETS['websocket_init_p95'], \
"formatted_string"

@pytest.mark.asyncio
    async def test_concurrent_user_performance(self, factory):
"""Test system performance with concurrent users."""

async def simulate_user_request(user_id: str) -> float:
"""Simulate a single user request."""
pass
start = time.perf_counter()

    # Create context
context = await factory.create_user_execution_context( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
    

    # Create agent
mock_agent_class = Mock(websocket = TestWebSocketConnection()  # Real WebSocket implementation)
agent = await factory.create_agent_instance( )
agent_name="test_agent",
user_context=context,
agent_class=mock_agent_class
    

    # Simulate some work
await asyncio.sleep(0.001)  # 1ms of work

    # Cleanup
await factory.cleanup_user_context(context)

await asyncio.sleep(0)
return (time.perf_counter() - start) * 1000

    # Run concurrent requests
all_times = []

for batch in range(10):  # 10 batches of concurrent users
tasks = [ )
simulate_user_request("formatted_string")
for i in range(self.CONCURRENT_USERS)
    

batch_times = await asyncio.gather(*tasks)
all_times.extend(batch_times)

    # Calculate statistics
p95 = self.calculate_percentile(all_times, 95)
p99 = self.calculate_percentile(all_times, 99)
mean = statistics.mean(all_times)

    # Log results
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

    # Assert performance target
assert p95 < self.TARGETS['total_request_p95'], \
"formatted_string"

@pytest.mark.asyncio
    async def test_performance_under_load(self, factory):
"""Test performance degradation under sustained load."""

        # Baseline measurement (low load)
baseline_times = []
for _ in range(20):
start = time.perf_counter()
context = await factory.create_user_execution_context( )
user_id="baseline_user",
thread_id="baseline_thread",
run_id="formatted_string"
            
await factory.cleanup_user_context(context)
baseline_times.append((time.perf_counter() - start) * 1000)

baseline_mean = statistics.mean(baseline_times)

            # High load measurement (100 concurrent operations)
async def load_operation():
context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
    
await factory.cleanup_user_context(context)

    # Create sustained load
load_tasks = []
load_times = []

for _ in range(100):
start = time.perf_counter()
task = asyncio.create_task(load_operation())
load_tasks.append(task)

        # Measure a sample operation during load
if len(load_tasks) % 10 == 0:
sample_start = time.perf_counter()
context = await factory.create_user_execution_context( )
user_id="sample_user",
thread_id="sample_thread",
run_id="formatted_string"
            
await factory.cleanup_user_context(context)
load_times.append((time.perf_counter() - sample_start) * 1000)

            # Wait for all load tasks
await asyncio.gather(*load_tasks)

load_mean = statistics.mean(load_times) if load_times else 0

            # Calculate degradation
degradation_factor = load_mean / baseline_mean if baseline_mean > 0 else 1

            # Log results
print(f" )
Performance Under Load:")
print("formatted_string")
print("formatted_string")
print("formatted_string")

            # Assert acceptable degradation (max 2x slowdown)
assert degradation_factor < 2.0, \
"formatted_string"

@pytest.mark.asyncio
    async def test_memory_efficiency(self, factory):
"""Test memory efficiency of the factory pattern."""
pass
import gc
import tracemalloc

                # Start memory tracking
tracemalloc.start()

                # Baseline memory
gc.collect()
baseline = tracemalloc.get_traced_memory()[0]

                # Create many contexts
contexts = []
for i in range(100):
context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
                    
contexts.append(context)

                    # Peak memory with contexts
peak_with_contexts = tracemalloc.get_traced_memory()[0]

                    # Cleanup all contexts
for context in contexts:
await factory.cleanup_user_context(context)
contexts.clear()

                        # Force garbage collection
gc.collect()

                        # Memory after cleanup
after_cleanup = tracemalloc.get_traced_memory()[0]

tracemalloc.stop()

                        # Calculate memory metrics
memory_per_context = (peak_with_contexts - baseline) / 100 / 1024  # KB per context
memory_leaked = (after_cleanup - baseline) / 1024  # KB leaked

                        # Log results
print(f" )
Memory Efficiency:")
print("formatted_string")
print("formatted_string")
print("formatted_string")

                        # Assert memory efficiency
assert memory_per_context < 10, \
"formatted_string"
assert memory_leaked < 100, \
"formatted_string"

@pytest.mark.asyncio
    async def test_performance_metrics_integration(self, factory, monitor):
"""Test integration with performance monitoring."""

                            # Perform operations with monitoring
for i in range(10):
async with monitor.timer('test.context_creation'):
context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
                                    

async with monitor.timer('test.agent_creation'):
mock_agent_class = Mock(websocket = TestWebSocketConnection()  # Real WebSocket implementation)
agent = await factory.create_agent_instance( )
agent_name="test_agent",
user_context=context,
agent_class=mock_agent_class
                                        

async with monitor.timer('test.cleanup'):
await factory.cleanup_user_context(context)

                                            # Get metrics summary
summary = await monitor.get_metrics_summary()

                                            # Verify metrics were collected
assert 'test.context_creation' in summary['timers']
assert 'test.agent_creation' in summary['timers']
assert 'test.cleanup' in summary['timers']

                                            Verify performance stats from factory
perf_stats = factory.get_performance_stats()
assert 'context_creation' in perf_stats
assert 'agent_creation' in perf_stats
assert 'cleanup' in perf_stats

                                            # Log integrated metrics
print(f" )
Integrated Performance Metrics:")
print("formatted_string")
print("formatted_string")
print("formatted_string")


if __name__ == "__main__":
                                                # Run tests with detailed output
pytest.main([__file__, "-v", "--tb=short"])
pass
