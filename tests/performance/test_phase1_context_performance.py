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

"""
Performance Validation Suite for UserExecutionContext Migration (Phase 1)

This module provides comprehensive performance testing for the UserExecutionContext
migration to ensure no performance regressions and validate system scalability.

Test Categories:
1. Context Creation Overhead
2. Memory Usage Comparison (Legacy vs New)
3. Database Connection Pool Efficiency
4. Concurrent Request Handling
5. Context Propagation Overhead
6. Session Cleanup & Garbage Collection
7. WebSocket Event Dispatch Performance
8. Load Test Scenarios
9. Memory Leak Detection

Business Value:
- Ensures migration doesn't degrade performance
- Validates system can handle production load
- Identifies bottlenecks before deployment
- Provides baseline metrics for monitoring
"""

import asyncio
import gc
import json
import os
import psutil
import pytest
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test imports
from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    get_execution_engine_factory,
    user_execution_engine
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance test metrics."""
    test_name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    cpu_percent: float
    success_count: int
    error_count: int
    operations_per_second: float
    additional_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            'test_name': self.test_name,
            'duration_ms': self.duration_ms,
            'memory_before_mb': self.memory_before_mb,
            'memory_after_mb': self.memory_after_mb,
            'memory_delta_mb': self.memory_delta_mb,
            'cpu_percent': self.cpu_percent,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'operations_per_second': self.operations_per_second,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **self.additional_metrics
        }


class PerformanceProfiler:
    """Utility class for performance profiling."""
    
    def __init__(self, test_name: str):
    pass
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.memory_before = None
        self.memory_after = None
        self.cpu_percent = None
        self.success_count = 0
        self.error_count = 0
        self.additional_metrics = {}
    
    def __enter__(self):
        """Start performance profiling."""
        gc.collect()  # Ensure clean start
        self.memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End performance profiling."""
    pass
        self.end_time = time.time()
        self.memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        self.cpu_percent = psutil.Process().cpu_percent()
    
    def record_success(self):
        """Record a successful operation."""
        self.success_count += 1
    
    def record_error(self):
        """Record a failed operation."""
    pass
        self.error_count += 1
    
    def add_metric(self, key: str, value: Any):
        """Add additional metric."""
        self.additional_metrics[key] = value
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics."""
    pass
        duration = (self.end_time - self.start_time) * 1000  # Convert to ms
        total_ops = self.success_count + self.error_count
        ops_per_sec = total_ops / ((self.end_time - self.start_time)) if total_ops > 0 else 0
        
        return PerformanceMetrics(
            test_name=self.test_name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=duration,
            memory_before_mb=self.memory_before,
            memory_after_mb=self.memory_after,
            memory_delta_mb=self.memory_after - self.memory_before,
            cpu_percent=self.cpu_percent,
            success_count=self.success_count,
            error_count=self.error_count,
            operations_per_second=ops_per_sec,
            additional_metrics=self.additional_metrics
        )


class MockAgentFactory:
    """Mock agent factory for performance testing."""
    
    def __init__(self):
    pass
        self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
    
    async def create_agent(self, agent_type: str, context: UserExecutionContext):
        """Create mock agent."""
        websocket = TestWebSocketConnection()
        mock_agent.execute = AsyncMock(return_value="test_result")
        await asyncio.sleep(0)
    return mock_agent


@pytest.fixture
async def mock_agent_factory():
    """Provide mock agent factory for tests."""
    pass
    await asyncio.sleep(0)
    return MockAgentFactory()


@pytest.fixture
async def performance_test_context():
    """Create test context for performance tests."""
    await asyncio.sleep(0)
    return UserExecutionContext(
        user_id=f"perf_test_user_{uuid.uuid4().hex[:8]}",
        thread_id=f"perf_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"perf_run_{uuid.uuid4().hex[:8]}",
        request_id=f"perf_req_{uuid.uuid4().hex[:8]}"
    )


@pytest.mark.asyncio
class TestContextCreationPerformance:
    """Test suite for UserExecutionContext creation performance."""
    
    async def test_single_context_creation_overhead(self, performance_test_context):
        """Test single context creation performance."""
        with PerformanceProfiler("single_context_creation") as profiler:
            for _ in range(100):  # Warm up
                try:
                    context = UserExecutionContext(
                        user_id=f"user_{uuid.uuid4().hex[:8]}",
                        thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                        run_id=f"run_{uuid.uuid4().hex[:8]}",
                        request_id=f"req_{uuid.uuid4().hex[:8]}"
                    )
                    profiler.record_success()
                except Exception:
                    profiler.record_error()
        
        metrics = profiler.get_metrics()
        assert metrics.error_count == 0, f"Context creation errors: {metrics.error_count}"
        assert metrics.duration_ms < 100, f"Single context creation too slow: {metrics.duration_ms}ms"
        assert metrics.operations_per_second > 1000, f"Context creation rate too low: {metrics.operations_per_second} ops/sec"
    
    async def test_bulk_context_creation_10k(self):
        """Test creating 10,000 contexts for overhead measurement."""
    pass
        contexts_created = []
        
        with PerformanceProfiler("bulk_10k_context_creation") as profiler:
            for i in range(10000):
                try:
                    context = UserExecutionContext(
                        user_id=f"bulk_user_{i}_{uuid.uuid4().hex[:8]}",
                        thread_id=f"bulk_thread_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"bulk_run_{i}_{uuid.uuid4().hex[:8]}",
                        request_id=f"bulk_req_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    contexts_created.append(context)
                    profiler.record_success()
                    
                    if i % 1000 == 0:  # Progress tracking
                        profiler.add_metric(f"memory_at_{i}", psutil.Process().memory_info().rss / 1024 / 1024)
                        
                except Exception as e:
                    logger.error(f"Error creating context {i}: {e}")
                    profiler.record_error()
        
        metrics = profiler.get_metrics()
        
        # Performance assertions
        assert metrics.success_count >= 9900, f"Too many creation failures: {metrics.error_count}"
        assert metrics.duration_ms < 5000, f"10k context creation too slow: {metrics.duration_ms}ms"  # 5 seconds max
        assert metrics.memory_delta_mb < 100, f"Memory growth too high: {metrics.memory_delta_mb}MB"
        assert metrics.operations_per_second > 2000, f"Context creation rate too low: {metrics.operations_per_second} ops/sec"
        
        profiler.add_metric("contexts_created_count", len(contexts_created))
        logger.info(f"Created {len(contexts_created)} contexts in {metrics.duration_ms}ms")


@pytest.mark.asyncio
class TestExecutionEnginePerformance:
    """Test suite for UserExecutionEngine performance."""
    
        async def test_engine_creation_performance(self, mock_get_factory, performance_test_context):
        """Test execution engine creation performance."""
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        
        with PerformanceProfiler("execution_engine_creation") as profiler:
            engines_created = []
            
            for i in range(100):
                try:
                    context = UserExecutionContext(
                        user_id=f"engine_user_{i}_{uuid.uuid4().hex[:8]}",
                        thread_id=f"engine_thread_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"engine_run_{i}_{uuid.uuid4().hex[:8]}",
                        request_id=f"engine_req_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    engine = await factory.create_for_user(context)
                    engines_created.append(engine)
                    profiler.record_success()
                    
                except Exception as e:
                    logger.error(f"Error creating engine {i}: {e}")
                    profiler.record_error()
            
            # Cleanup engines
            for engine in engines_created:
                try:
                    await factory.cleanup_engine(engine)
                except Exception as e:
                    logger.error(f"Error cleaning up engine: {e}")
        
        metrics = profiler.get_metrics()
        profiler.add_metric("engines_created", len(engines_created))
        
        # Performance assertions
        assert metrics.error_count == 0, f"Engine creation errors: {metrics.error_count}"
        assert metrics.duration_ms < 2000, f"Engine creation too slow: {metrics.duration_ms}ms"  # 2 seconds for 100 engines
        assert metrics.operations_per_second > 50, f"Engine creation rate too low: {metrics.operations_per_second} engines/sec"
        
        await factory.shutdown()
    
        async def test_concurrent_engine_creation(self, mock_get_factory):
        """Test concurrent execution engine creation."""
    pass
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        concurrent_count = 50
        
        async def create_engine(user_index: int) -> Tuple[bool, Optional[str]]:
            """Create single engine for concurrent test."""
            try:
                context = UserExecutionContext(
                    user_id=f"concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"concurrent_thread_{user_index}_{uuid.uuid4().hex[:8]}",
                    run_id=f"concurrent_run_{user_index}_{uuid.uuid4().hex[:8]}",
                    request_id=f"concurrent_req_{user_index}_{uuid.uuid4().hex[:8]}"
                )
                
                engine = await factory.create_for_user(context)
                await factory.cleanup_engine(engine)
                await asyncio.sleep(0)
    return True, None
                
            except Exception as e:
                return False, str(e)
        
        with PerformanceProfiler("concurrent_engine_creation") as profiler:
            # Create engines concurrently
            tasks = [create_engine(i) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, tuple):
                    success, error = result
                    if success:
                        profiler.record_success()
                    else:
                        profiler.record_error()
                        logger.error(f"Concurrent engine creation error: {error}")
                else:
                    profiler.record_error()
                    logger.error(f"Concurrent engine creation exception: {result}")
        
        metrics = profiler.get_metrics()
        
        # Performance assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Concurrent creation success rate too low: {success_rate:.2%}"
        assert metrics.duration_ms < 5000, f"Concurrent engine creation too slow: {metrics.duration_ms}ms"
        
        await factory.shutdown()


@pytest.mark.asyncio
class TestMemoryUsageComparison:
    """Test suite for memory usage comparison."""
    
    async def test_memory_baseline_measurement(self):
        """Establish memory baseline for new architecture."""
        gc.collect()
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        with PerformanceProfiler("memory_baseline") as profiler:
            # Simulate typical usage pattern
            contexts = []
            for i in range(1000):
                context = UserExecutionContext(
                    user_id=f"baseline_user_{i}",
                    thread_id=f"baseline_thread_{i}",
                    run_id=f"baseline_run_{i}",
                    request_id=f"baseline_req_{i}"
                )
                contexts.append(context)
                profiler.record_success()
            
            # Keep references to measure steady-state memory
            await asyncio.sleep(0.1)  # Allow garbage collection
        
        metrics = profiler.get_metrics()
        profiler.add_metric("baseline_memory_mb", baseline_memory)
        profiler.add_metric("contexts_in_memory", len(contexts))
        
        logger.info(f"Memory baseline: {baseline_memory:.2f}MB -> {metrics.memory_after_mb:.2f}MB "
                   f"({metrics.memory_delta_mb:.2f}MB delta for 1000 contexts)")
        
        # Memory efficiency assertions
        assert metrics.memory_delta_mb < 50, f"Memory usage too high: {metrics.memory_delta_mb}MB for 1000 contexts"
        
        # Cleanup and verify garbage collection
        del contexts
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_recovered = metrics.memory_after_mb - final_memory
        profiler.add_metric("memory_recovered_mb", memory_recovered)
        
        assert memory_recovered > metrics.memory_delta_mb * 0.8, f"Memory not properly released: {memory_recovered}MB recovered"
    
        async def test_engine_memory_lifecycle(self, mock_get_factory):
        """Test memory usage throughout engine lifecycle."""
    pass
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        with PerformanceProfiler("engine_memory_lifecycle") as profiler:
            engines = []
            
            # Create engines
            for i in range(100):
                try:
                    context = UserExecutionContext(
                        user_id=f"mem_user_{i}_{uuid.uuid4().hex[:8]}",
                        thread_id=f"mem_thread_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"mem_run_{i}_{uuid.uuid4().hex[:8]}",
                        request_id=f"mem_req_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    engine = await factory.create_for_user(context)
                    engines.append(engine)
                    profiler.record_success()
                    
                    if i % 20 == 0:  # Track memory growth
                        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        profiler.add_metric(f"memory_at_engine_{i}", current_memory)
                        
                except Exception as e:
                    logger.error(f"Error creating engine for memory test {i}: {e}")
                    profiler.record_error()
            
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            profiler.add_metric("peak_memory_mb", peak_memory)
            profiler.add_metric("engines_created", len(engines))
            
            # Cleanup engines
            for engine in engines:
                try:
                    await factory.cleanup_engine(engine)
                except Exception as e:
                    logger.error(f"Error cleaning up engine for memory test: {e}")
            
            # Force garbage collection
            del engines
            gc.collect()
            await asyncio.sleep(0.1)
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_leaked = final_memory - initial_memory
        
        metrics = profiler.get_metrics()
        profiler.add_metric("initial_memory_mb", initial_memory)
        profiler.add_metric("final_memory_mb", final_memory)
        profiler.add_metric("memory_leaked_mb", memory_leaked)
        
        logger.info(f"Memory lifecycle: {initial_memory:.2f}MB -> {peak_memory:.2f}MB -> {final_memory:.2f}MB")
        logger.info(f"Memory leaked: {memory_leaked:.2f}MB")
        
        # Memory leak assertions
        assert memory_leaked < 20, f"Potential memory leak detected: {memory_leaked}MB not released"
        assert metrics.success_count >= 95, f"Too many engine creation failures: {metrics.error_count}"
        
        await factory.shutdown()


@pytest.mark.asyncio
class TestConcurrentRequestHandling:
    """Test suite for concurrent request handling performance."""
    
        async def test_concurrent_request_simulation(self, mock_get_factory):
        """Simulate 1000+ concurrent requests."""
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        concurrent_requests = 1000
        
        async def simulate_request(request_id: int) -> Tuple[bool, float, Optional[str]]:
            """Simulate single request with timing."""
    pass
            start_time = time.time()
            
            try:
                context = UserExecutionContext(
                    user_id=f"concurrent_user_{request_id % 100}_{uuid.uuid4().hex[:8]}",  # 100 unique users
                    thread_id=f"concurrent_thread_{request_id}_{uuid.uuid4().hex[:8]}",
                    run_id=f"concurrent_run_{request_id}_{uuid.uuid4().hex[:8]}",
                    request_id=f"concurrent_req_{request_id}_{uuid.uuid4().hex[:8]}"
                )
                
                async with factory.user_execution_scope(context) as engine:
                    # Simulate some work
                    await asyncio.sleep(0.01)  # 10ms simulated work
                    duration = time.time() - start_time
                    await asyncio.sleep(0)
    return True, duration, None
                    
            except Exception as e:
                duration = time.time() - start_time
                return False, duration, str(e)
        
        with PerformanceProfiler("concurrent_1000_requests") as profiler:
            # Execute all requests concurrently
            tasks = [simulate_request(i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            request_durations = []
            
            for result in results:
                if isinstance(result, tuple):
                    success, duration, error = result
                    request_durations.append(duration)
                    
                    if success:
                        profiler.record_success()
                    else:
                        profiler.record_error()
                        logger.warning(f"Concurrent request failed: {error}")
                else:
                    profiler.record_error()
                    logger.error(f"Concurrent request exception: {result}")
            
            # Calculate percentile metrics
            if request_durations:
                request_durations.sort()
                profiler.add_metric("min_request_duration_ms", min(request_durations) * 1000)
                profiler.add_metric("max_request_duration_ms", max(request_durations) * 1000)
                profiler.add_metric("avg_request_duration_ms", sum(request_durations) / len(request_durations) * 1000)
                profiler.add_metric("p50_request_duration_ms", request_durations[len(request_durations) // 2] * 1000)
                profiler.add_metric("p95_request_duration_ms", request_durations[int(len(request_durations) * 0.95)] * 1000)
                profiler.add_metric("p99_request_duration_ms", request_durations[int(len(request_durations) * 0.99)] * 1000)
        
        metrics = profiler.get_metrics()
        
        # Performance assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Concurrent request success rate too low: {success_rate:.2%}"
        assert metrics.duration_ms < 30000, f"1000 concurrent requests took too long: {metrics.duration_ms}ms"  # 30 seconds max
        
        # Request duration assertions
        if 'p95_request_duration_ms' in profiler.additional_metrics:
            assert profiler.additional_metrics['p95_request_duration_ms'] < 5000, \
                f"P95 request duration too high: {profiler.additional_metrics['p95_request_duration_ms']}ms"
        
        logger.info(f"Concurrent requests completed: {metrics.success_count}/{concurrent_requests} "
                   f"({success_rate:.2%} success rate)")
        
        await factory.shutdown()


@pytest.mark.asyncio 
class TestWebSocketPerformance:
    """Test suite for WebSocket event dispatch performance."""
    
        async def test_websocket_event_dispatch_rate(self, mock_get_factory):
        """Test WebSocket event dispatch performance."""
        mock_factory = MockAgentFactory()
        mock_get_factory.return_value = mock_factory
        
        factory = ExecutionEngineFactory()
        
        with PerformanceProfiler("websocket_event_dispatch") as profiler:
            context = UserExecutionContext(
                user_id=f"ws_user_{uuid.uuid4().hex[:8]}",
                thread_id=f"ws_thread_{uuid.uuid4().hex[:8]}",
                run_id=f"ws_run_{uuid.uuid4().hex[:8]}",
                request_id=f"ws_req_{uuid.uuid4().hex[:8]}"
            )
            
            async with factory.user_execution_scope(context) as engine:
                websocket_emitter = engine.websocket_emitter
                
                # Dispatch many events rapidly
                for i in range(1000):
                    try:
                        await websocket_emitter.send_event({
                            "type": "test_event",
                            "data": f"Event {i}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        profiler.record_success()
                        
                    except Exception as e:
                        logger.error(f"WebSocket event dispatch error {i}: {e}")
                        profiler.record_error()
        
        metrics = profiler.get_metrics()
        
        # Performance assertions
        assert metrics.error_count == 0, f"WebSocket dispatch errors: {metrics.error_count}"
        assert metrics.operations_per_second > 1000, f"WebSocket dispatch rate too low: {metrics.operations_per_second} events/sec"
        assert metrics.duration_ms < 2000, f"WebSocket event dispatch too slow: {metrics.duration_ms}ms for 1000 events"
        
        # Verify mock was called expected number of times
        assert mock_factory._websocket_bridge.send_event.call_count == 1000, \
            f"Expected 1000 WebSocket calls, got {mock_factory._websocket_bridge.send_event.call_count}"
        
        await factory.shutdown()


@pytest.mark.asyncio
class TestLoadScenarios:
    """Test suite for various load scenarios."""
    
        async def test_sustained_load_simulation(self, mock_get_factory):
        """Simulate sustained load: 100 req/sec for 60 seconds (scaled down for testing)."""
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        
        # Scaled down: 10 req/sec for 6 seconds (60 total requests)
        requests_per_second = 10
        duration_seconds = 6
        total_requests = requests_per_second * duration_seconds
        
        async def sustained_load_worker():
            """Worker for sustained load generation."""
    pass
            request_count = 0
            
            with PerformanceProfiler("sustained_load") as profiler:
                start_time = time.time()
                
                while time.time() - start_time < duration_seconds:
                    batch_start = time.time()
                    
                    # Send batch of requests
                    batch_tasks = []
                    for _ in range(requests_per_second):
                        if request_count >= total_requests:
                            break
                        
                        context = UserExecutionContext(
                            user_id=f"sustained_user_{request_count % 20}_{uuid.uuid4().hex[:8]}",  # 20 unique users
                            thread_id=f"sustained_thread_{request_count}_{uuid.uuid4().hex[:8]}",
                            run_id=f"sustained_run_{request_count}_{uuid.uuid4().hex[:8]}",
                            request_id=f"sustained_req_{request_count}_{uuid.uuid4().hex[:8]}"
                        )
                        
                        batch_tasks.append(self._execute_sustained_request(factory, context, profiler))
                        request_count += 1
                    
                    # Execute batch
                    if batch_tasks:
                        await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Maintain rate
                    batch_duration = time.time() - batch_start
                    if batch_duration < 1.0:
                        await asyncio.sleep(1.0 - batch_duration)
                
                await asyncio.sleep(0)
    return profiler.get_metrics()
        
        metrics = await sustained_load_worker()
        
        # Performance assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.90, f"Sustained load success rate too low: {success_rate:.2%}"
        assert metrics.memory_delta_mb < 100, f"Memory growth too high during sustained load: {metrics.memory_delta_mb}MB"
        
        logger.info(f"Sustained load completed: {metrics.success_count} requests, "
                   f"{success_rate:.2%} success rate, {metrics.memory_delta_mb:.2f}MB memory delta")
        
        await factory.shutdown()
    
    async def _execute_sustained_request(self, factory, context, profiler):
        """Execute single sustained request."""
        try:
            async with factory.user_execution_scope(context) as engine:
                await asyncio.sleep(0.01)  # Simulate work
                profiler.record_success()
        except Exception as e:
            logger.warning(f"Sustained request failed: {e}")
            profiler.record_error()
    
        async def test_spike_load_simulation(self, mock_get_factory):
        """Simulate spike load: 0 to 1000 req/sec instantly."""
    pass
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        spike_requests = 500  # Scaled down from 1000
        
        with PerformanceProfiler("spike_load") as profiler:
            # Generate spike instantly
            spike_tasks = []
            
            for i in range(spike_requests):
                context = UserExecutionContext(
                    user_id=f"spike_user_{i % 50}_{uuid.uuid4().hex[:8]}",  # 50 unique users
                    thread_id=f"spike_thread_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"spike_run_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"spike_req_{i}_{uuid.uuid4().hex[:8]}"
                )
                
                spike_tasks.append(self._execute_spike_request(factory, context, profiler))
            
            # Execute all requests simultaneously (spike)
            results = await asyncio.gather(*spike_tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Spike request failed: {result}")
                    profiler.record_error()
        
        metrics = profiler.get_metrics()
        
        # Spike load assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.80, f"Spike load success rate too low: {success_rate:.2%}"  # Lower threshold for spike
        assert metrics.duration_ms < 10000, f"Spike load took too long: {metrics.duration_ms}ms"  # 10 seconds max
        
        logger.info(f"Spike load completed: {metrics.success_count}/{spike_requests} requests, "
                   f"{success_rate:.2%} success rate")
        
        await factory.shutdown()
    
    async def _execute_spike_request(self, factory, context, profiler):
        """Execute single spike request."""
        try:
            async with factory.user_execution_scope(context) as engine:
                await asyncio.sleep(0.005)  # 5ms work
                profiler.record_success()
                await asyncio.sleep(0)
    return True
        except Exception as e:
            profiler.record_error()
            raise


@pytest.mark.asyncio
class TestMemoryLeakDetection:
    """Test suite for memory leak detection."""
    
        async def test_extended_memory_monitoring(self, mock_get_factory):
        """Monitor memory usage over 1000+ request cycles."""
        mock_get_factory.return_value = MockAgentFactory()
        
        factory = ExecutionEngineFactory()
        cycles = 100  # Scaled down from 1000 for test duration
        requests_per_cycle = 10
        
        memory_samples = []
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples.append(('initial', initial_memory))
        
        with PerformanceProfiler("memory_leak_detection") as profiler:
            for cycle in range(cycles):
                cycle_start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                # Execute requests in this cycle
                cycle_tasks = []
                for req in range(requests_per_cycle):
                    context = UserExecutionContext(
                        user_id=f"leak_user_{cycle}_{req}_{uuid.uuid4().hex[:8]}",
                        thread_id=f"leak_thread_{cycle}_{req}_{uuid.uuid4().hex[:8]}",
                        run_id=f"leak_run_{cycle}_{req}_{uuid.uuid4().hex[:8]}",
                        request_id=f"leak_req_{cycle}_{req}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    cycle_tasks.append(self._execute_leak_test_request(factory, context, profiler))
                
                # Execute cycle requests
                await asyncio.gather(*cycle_tasks, return_exceptions=True)
                
                # Force garbage collection after each cycle
                gc.collect()
                await asyncio.sleep(0.01)  # Brief pause
                
                cycle_end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append((f'cycle_{cycle}', cycle_end_memory))
                
                # Track memory growth every 10 cycles
                if cycle % 10 == 0:
                    memory_growth = cycle_end_memory - initial_memory
                    profiler.add_metric(f"memory_growth_cycle_{cycle}", memory_growth)
                    
                    logger.debug(f"Cycle {cycle}: Memory {cycle_start_memory:.2f}MB -> {cycle_end_memory:.2f}MB "
                               f"(+{cycle_end_memory - cycle_start_memory:.2f}MB)")
        
        # Analyze memory trend
        final_memory = memory_samples[-1][1]
        total_memory_growth = final_memory - initial_memory
        
        profiler.add_metric("initial_memory_mb", initial_memory)
        profiler.add_metric("final_memory_mb", final_memory) 
        profiler.add_metric("total_memory_growth_mb", total_memory_growth)
        profiler.add_metric("memory_samples", len(memory_samples))
        profiler.add_metric("total_requests_processed", cycles * requests_per_cycle)
        
        # Calculate memory growth rate
        memory_growth_per_request = total_memory_growth / (cycles * requests_per_cycle) if cycles * requests_per_cycle > 0 else 0
        profiler.add_metric("memory_growth_per_request_kb", memory_growth_per_request * 1024)
        
        metrics = profiler.get_metrics()
        
        logger.info(f"Memory leak test: {initial_memory:.2f}MB -> {final_memory:.2f}MB "
                   f"(+{total_memory_growth:.2f}MB over {cycles * requests_per_cycle} requests)")
        logger.info(f"Memory growth per request: {memory_growth_per_request * 1024:.2f}KB")
        
        # Memory leak assertions
        assert total_memory_growth < 50, f"Potential memory leak: {total_memory_growth:.2f}MB growth over {cycles} cycles"
        assert memory_growth_per_request < 0.05, f"Memory growth per request too high: {memory_growth_per_request * 1024:.2f}KB"
        
        # Success rate assertion
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Too many failures during memory leak test: {success_rate:.2%}"
        
        await factory.shutdown()
    
    async def _execute_leak_test_request(self, factory, context, profiler):
        """Execute single request for memory leak testing."""
    pass
        try:
            async with factory.user_execution_scope(context) as engine:
                # Simulate typical usage
                await asyncio.sleep(0.001)  # 1ms work
                profiler.record_success()
        except Exception as e:
            logger.warning(f"Memory leak test request failed: {e}")
            profiler.record_error()


# Performance test utilities
class PerformanceReporter:
    """Utility for generating performance reports."""
    
    @staticmethod
    def save_metrics(metrics_list: List[PerformanceMetrics], filename: str):
    """Use real service instance."""
    # TODO: Initialize real service
        """Save metrics to JSON file."""
    pass
        report_data = {
            "test_suite": "Phase1_UserExecutionContext_Performance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_info": {
                "python_version": os.sys.version,
                "cpu_count": os.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024
            },
            "metrics": [metric.to_dict() for metric in metrics_list]
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Performance metrics saved to {filename}")
    
    @staticmethod 
    def print_summary(metrics_list: List[PerformanceMetrics]):
        """Print performance test summary."""
        print("
" + "="*80)
        print("PERFORMANCE TEST SUMMARY")
        print("="*80)
        
        total_tests = len(metrics_list)
        total_operations = sum(m.success_count + m.error_count for m in metrics_list)
        total_errors = sum(m.error_count for m in metrics_list)
        total_duration = sum(m.duration_ms for m in metrics_list)
        
        print(f"Total Tests: {total_tests}")
        print(f"Total Operations: {total_operations}")
        print(f"Total Errors: {total_errors}")
        print(f"Total Duration: {total_duration:.2f}ms")
        print(f"Overall Success Rate: {((total_operations - total_errors) / total_operations * 100):.2f}%")
        print()
        
        for metric in metrics_list:
            success_rate = metric.success_count / (metric.success_count + metric.error_count) * 100
            print(f"{metric.test_name}:")
            print(f"  Duration: {metric.duration_ms:.2f}ms")
            print(f"  Operations/sec: {metric.operations_per_second:.2f}")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Memory Delta: {metric.memory_delta_mb:.2f}MB")
            print()
        
        print("="*80)


if __name__ == "__main__":
    """Run performance tests directly."""
    pass
    pytest.main([__file__, "-v", "--tb=short"])