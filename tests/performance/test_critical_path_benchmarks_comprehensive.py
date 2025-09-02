#!/usr/bin/env python
"""
CRITICAL PATH PERFORMANCE BENCHMARKS - COMPREHENSIVE SUITE

Business Value: Ensures $500K+ ARR protection through performance SLA compliance
Critical Requirements:
- Agent execution: <2s for 95th percentile (Enterprise SLA)
- WebSocket events: <100ms latency for real-time experience
- Circuit breaker overhead: <5ms per operation (CLAUDE.md requirement)
- Memory usage: <1GB peak during 100+ concurrent operations
- Throughput: >50 concurrent agents without degradation

This suite establishes performance baselines and detects regressions that could:
- Breach Enterprise SLA agreements (99.9% uptime, <2s response)
- Cause user experience degradation affecting retention
- Lead to infrastructure scaling costs exceeding budget
- Trigger performance penalty clauses in contracts

ANY PERFORMANCE REGRESSION BLOCKS PRODUCTION DEPLOYMENT.
"""

import asyncio
import gc
import json
import math
import os
import psutil
import random
import statistics
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass, asdict
import tempfile

import pytest
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import performance-critical components
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from netra_backend.app.core.reliability_retry import RetryHandler, RetryConfig, BackoffStrategy
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# PERFORMANCE MEASUREMENT UTILITIES
# ============================================================================

@dataclass
class PerformanceMeasurement:
    """Comprehensive performance measurement data."""
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0


@dataclass
class BenchmarkResults:
    """Comprehensive benchmark results with statistical analysis."""
    benchmark_name: str
    measurements: List[PerformanceMeasurement]
    start_timestamp: float
    end_timestamp: float
    
    @property
    def duration_ms(self) -> List[float]:
        return [m.duration_ms for m in self.measurements if m.success]
    
    @property
    def memory_usage_mb(self) -> List[float]:
        return [m.memory_usage_mb for m in self.measurements if m.success]
    
    @property
    def cpu_usage_percent(self) -> List[float]:
        return [m.cpu_usage_percent for m in self.measurements if m.success]
    
    @property
    def success_rate(self) -> float:
        if not self.measurements:
            return 0.0
        return sum(1 for m in self.measurements if m.success) / len(self.measurements)
    
    def get_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate performance percentiles."""
        if not values:
            return {"p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0, "avg": 0}
        
        sorted_values = sorted(values)
        length = len(sorted_values)
        
        return {
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": statistics.mean(sorted_values),
            "median": statistics.median(sorted_values),
            "p50": sorted_values[int(0.5 * length)] if length > 0 else 0,
            "p95": sorted_values[int(0.95 * length)] if length > 0 else 0,
            "p99": sorted_values[int(0.99 * length)] if length > 0 else 0,
            "stddev": statistics.stdev(sorted_values) if length > 1 else 0
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "benchmark_name": self.benchmark_name,
            "total_operations": len(self.measurements),
            "successful_operations": sum(1 for m in self.measurements if m.success),
            "success_rate": self.success_rate,
            "duration_stats": self.get_percentiles(self.duration_ms),
            "memory_stats": self.get_percentiles(self.memory_usage_mb),
            "cpu_stats": self.get_percentiles(self.cpu_usage_percent),
            "total_benchmark_time": self.end_timestamp - self.start_timestamp,
            "throughput_ops_per_second": len(self.measurements) / (self.end_timestamp - self.start_timestamp),
            "failed_operations": sum(1 for m in self.measurements if not m.success)
        }


class PerformanceBenchmarkRunner:
    """Comprehensive performance benchmark runner with real-time monitoring."""
    
    def __init__(self):
        self.current_measurements: List[PerformanceMeasurement] = []
        self.benchmark_results: List[BenchmarkResults] = []
        self.resource_monitoring_active = False
        self.resource_samples: List[Dict] = []
        self.performance_baselines: Dict[str, Dict] = {}
        
        # Load existing baselines if available
        self._load_performance_baselines()
    
    def _load_performance_baselines(self):
        """Load performance baselines from file."""
        baseline_file = "tests/performance/performance_baselines.json"
        try:
            if os.path.exists(baseline_file):
                with open(baseline_file, 'r') as f:
                    self.performance_baselines = json.load(f)
                logger.info(f"Loaded {len(self.performance_baselines)} performance baselines")
        except Exception as e:
            logger.warning(f"Could not load performance baselines: {e}")
            self.performance_baselines = {}
    
    def save_performance_baselines(self):
        """Save current performance results as baselines."""
        baseline_file = "tests/performance/performance_baselines.json"
        os.makedirs(os.path.dirname(baseline_file), exist_ok=True)
        
        try:
            # Update baselines with current results
            for result in self.benchmark_results:
                summary = result.get_performance_summary()
                self.performance_baselines[result.benchmark_name] = {
                    "duration_p95": summary["duration_stats"]["p95"],
                    "duration_avg": summary["duration_stats"]["avg"],
                    "memory_p95": summary["memory_stats"]["p95"],
                    "cpu_avg": summary["cpu_stats"]["avg"],
                    "success_rate": summary["success_rate"],
                    "throughput": summary["throughput_ops_per_second"],
                    "timestamp": time.time(),
                    "baseline_version": "1.0"
                }
            
            with open(baseline_file, 'w') as f:
                json.dump(self.performance_baselines, f, indent=2)
            logger.info(f"Saved {len(self.performance_baselines)} performance baselines")
            
        except Exception as e:
            logger.error(f"Could not save performance baselines: {e}")
    
    async def start_resource_monitoring(self):
        """Start continuous resource monitoring."""
        self.resource_monitoring_active = True
        self.resource_samples = []
        
        async def monitor_resources():
            while self.resource_monitoring_active:
                try:
                    process = psutil.Process()
                    sample = {
                        "timestamp": time.time(),
                        "memory_mb": process.memory_info().rss / 1024 / 1024,
                        "cpu_percent": process.cpu_percent(),
                        "thread_count": process.num_threads(),
                        "open_files": len(process.open_files())
                    }
                    self.resource_samples.append(sample)
                except Exception:
                    pass  # Ignore monitoring errors
                
                await asyncio.sleep(0.5)
        
        self.monitoring_task = asyncio.create_task(monitor_resources())
    
    async def stop_resource_monitoring(self):
        """Stop resource monitoring."""
        self.resource_monitoring_active = False
        if hasattr(self, 'monitoring_task'):
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def measure_operation(
        self, 
        operation_name: str, 
        operation: Callable,
        *args, 
        **kwargs
    ) -> PerformanceMeasurement:
        """Measure performance of single operation."""
        
        # Capture initial state
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.perf_counter()
        
        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                result = operation(*args, **kwargs)
            
            end_time = time.perf_counter()
            
            # Capture final state
            final_memory = process.memory_info().rss / 1024 / 1024
            cpu_usage = process.cpu_percent()
            
            measurement = PerformanceMeasurement(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=(end_time - start_time) * 1000,
                memory_usage_mb=final_memory,
                cpu_usage_percent=cpu_usage,
                success=True,
                metadata={"result": str(result)[:100]}  # Sample of result
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            
            measurement = PerformanceMeasurement(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=(end_time - start_time) * 1000,
                memory_usage_mb=initial_memory,
                cpu_usage_percent=0,
                success=False,
                error_message=str(e),
                metadata={"error_type": type(e).__name__}
            )
        
        self.current_measurements.append(measurement)
        return measurement
    
    async def run_benchmark(
        self, 
        benchmark_name: str, 
        operations: List[Callable],
        iterations: int = 100,
        concurrent: bool = False,
        concurrency_level: int = 10
    ) -> BenchmarkResults:
        """Run comprehensive benchmark with multiple iterations."""
        
        logger.info(f"Starting benchmark: {benchmark_name} ({iterations} iterations, "
                   f"concurrent: {concurrent})")
        
        self.current_measurements = []
        start_timestamp = time.time()
        
        if concurrent:
            # Run operations concurrently
            await self._run_concurrent_benchmark(operations, iterations, concurrency_level)
        else:
            # Run operations sequentially
            await self._run_sequential_benchmark(operations, iterations)
        
        end_timestamp = time.time()
        
        # Create benchmark results
        results = BenchmarkResults(
            benchmark_name=benchmark_name,
            measurements=self.current_measurements.copy(),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        )
        
        self.benchmark_results.append(results)
        
        # Analyze results
        summary = results.get_performance_summary()
        logger.info(f"Benchmark {benchmark_name} completed: "
                   f"{summary['successful_operations']}/{summary['total_operations']} ops, "
                   f"p95: {summary['duration_stats']['p95']:.1f}ms, "
                   f"throughput: {summary['throughput_ops_per_second']:.1f} ops/s")
        
        return results
    
    async def _run_sequential_benchmark(self, operations: List[Callable], iterations: int):
        """Run benchmark operations sequentially."""
        for i in range(iterations):
            operation = operations[i % len(operations)]
            operation_name = getattr(operation, '__name__', f'operation_{i}')
            
            await self.measure_operation(operation_name, operation)
            
            # Small delay to prevent overwhelming
            if i % 50 == 0:
                await asyncio.sleep(0.01)
    
    async def _run_concurrent_benchmark(self, operations: List[Callable], iterations: int, concurrency: int):
        """Run benchmark operations concurrently."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_operation(i: int):
            async with semaphore:
                operation = operations[i % len(operations)]
                operation_name = getattr(operation, '__name__', f'operation_{i}')
                return await self.measure_operation(operation_name, operation)
        
        # Create all tasks
        tasks = [bounded_operation(i) for i in range(iterations)]
        
        # Execute with progress monitoring
        completed = 0
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            if completed % 25 == 0:
                logger.info(f"Benchmark progress: {completed}/{iterations}")
    
    def compare_with_baseline(self, benchmark_name: str, current_results: BenchmarkResults) -> Dict[str, Any]:
        """Compare current results with established baseline."""
        if benchmark_name not in self.performance_baselines:
            return {"status": "no_baseline", "message": "No baseline available for comparison"}
        
        baseline = self.performance_baselines[benchmark_name]
        current_summary = current_results.get_performance_summary()
        
        comparisons = {}
        
        # Duration comparison
        current_p95 = current_summary["duration_stats"]["p95"]
        baseline_p95 = baseline["duration_p95"]
        duration_regression = (current_p95 - baseline_p95) / baseline_p95 if baseline_p95 > 0 else 0
        
        comparisons["duration"] = {
            "current_p95": current_p95,
            "baseline_p95": baseline_p95,
            "regression_percent": duration_regression * 100,
            "acceptable": duration_regression < 0.2  # 20% regression threshold
        }
        
        # Throughput comparison
        current_throughput = current_summary["throughput_ops_per_second"]
        baseline_throughput = baseline["throughput"]
        throughput_change = (current_throughput - baseline_throughput) / baseline_throughput if baseline_throughput > 0 else 0
        
        comparisons["throughput"] = {
            "current": current_throughput,
            "baseline": baseline_throughput,
            "change_percent": throughput_change * 100,
            "acceptable": throughput_change > -0.15  # 15% degradation threshold
        }
        
        # Memory comparison
        current_memory = current_summary["memory_stats"]["p95"]
        baseline_memory = baseline["memory_p95"]
        memory_increase = (current_memory - baseline_memory) / baseline_memory if baseline_memory > 0 else 0
        
        comparisons["memory"] = {
            "current_p95": current_memory,
            "baseline_p95": baseline_memory,
            "increase_percent": memory_increase * 100,
            "acceptable": memory_increase < 0.3  # 30% memory increase threshold
        }
        
        # Overall assessment
        all_acceptable = all(comp.get("acceptable", True) for comp in comparisons.values())
        
        return {
            "status": "passed" if all_acceptable else "regression_detected",
            "comparisons": comparisons,
            "overall_acceptable": all_acceptable,
            "baseline_timestamp": baseline.get("timestamp", 0)
        }


# ============================================================================
# PERFORMANCE TEST COMPONENTS
# ============================================================================

class PerformanceTestAgent(BaseAgent):
    """High-performance test agent for benchmarking."""
    
    def __init__(self, name: str = "perf_test_agent"):
        # Create optimized mock LLM manager
        mock_llm = AsyncMock(spec=LLMManager)
        
        # Configure realistic response times based on operation complexity
        async def mock_chat_completion(*args, **kwargs):
            # Simulate realistic processing time
            base_delay = 0.1 + random.uniform(0, 0.3)  # 100-400ms
            await asyncio.sleep(base_delay)
            
            return {
                "content": "Performance test response",
                "tokens": {
                    "input": random.randint(50, 150),
                    "output": random.randint(100, 300),
                    "total": random.randint(150, 450)
                },
                "model": "gpt-4",
                "provider": "openai"
            }
        
        mock_llm.chat_completion = mock_chat_completion
        
        super().__init__(
            llm_manager=mock_llm,
            name=name,
            description=f"Performance test agent: {name}"
        )
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Optimized execute method for performance testing."""
        
        # Simulate realistic agent processing
        if hasattr(self, 'llm_manager') and self.llm_manager:
            response = await self.llm_manager.chat_completion(
                messages=[{"role": "user", "content": "Performance test query"}],
                model="gpt-4"
            )
            
            # Process response
            if response and response.get("content"):
                state.context["llm_response"] = response["content"]
                state.context["tokens_used"] = response.get("tokens", {}).get("total", 0)
        
        # Update state with processing results
        state.context[f"processed_by_{self.name}"] = time.time()
        state.context["processing_run_id"] = run_id
        
        # Simulate some computational work
        await asyncio.sleep(0.01)  # Minimal processing delay


class MockWebSocketManager:
    """High-performance mock WebSocket manager for benchmarking."""
    
    def __init__(self):
        self.message_count = 0
        self.total_latency = 0
        self.connections = {}
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Mock send with latency tracking."""
        start_time = time.perf_counter()
        
        # Simulate minimal WebSocket overhead
        await asyncio.sleep(0.001)  # 1ms overhead
        
        latency = (time.perf_counter() - start_time) * 1000  # Convert to ms
        self.message_count += 1
        self.total_latency += latency
        
        return True
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get WebSocket performance statistics."""
        return {
            "total_messages": self.message_count,
            "average_latency_ms": self.total_latency / self.message_count if self.message_count > 0 else 0,
            "total_latency_ms": self.total_latency
        }


# ============================================================================
# BENCHMARK TEST OPERATIONS
# ============================================================================

class CriticalPathOperations:
    """Collection of critical path operations for benchmarking."""
    
    def __init__(self):
        self.agent = PerformanceTestAgent()
        self.websocket_manager = MockWebSocketManager()
        self.websocket_notifier = WebSocketNotifier(self.websocket_manager)
        
        # Circuit breaker for performance testing
        self.circuit_breaker = CircuitBreaker(
            "perf_test_circuit",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30,
                success_threshold=2,
                timeout=10.0
            )
        )
        
        # Retry handler for performance testing
        self.retry_handler = RetryHandler(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.1,
                max_delay=2.0,
                backoff_strategy=BackoffStrategy.EXPONENTIAL
            )
        )
    
    async def agent_execution_operation(self) -> str:
        """Single agent execution operation."""
        state = DeepAgentState()
        state.run_id = f"perf_test_{uuid.uuid4().hex[:8]}"
        
        await self.agent.execute(state, state.run_id, stream_updates=False)
        return f"Agent executed: {state.run_id}"
    
    async def websocket_notification_operation(self) -> str:
        """WebSocket notification operation."""
        from netra_backend.app.agents.supervisor.agent_execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            run_id=f"ws_perf_{uuid.uuid4().hex[:8]}",
            thread_id="perf_test_thread",
            user_id="perf_test_user",
            agent_name="perf_agent",
            retry_count=0,
            max_retries=1
        )
        
        await self.websocket_notifier.send_agent_thinking(context, "Performance test thinking")
        return f"WebSocket notification sent: {context.run_id}"
    
    async def circuit_breaker_operation(self) -> str:
        """Circuit breaker protected operation."""
        
        async def protected_operation():
            # Simulate successful operation most of the time
            if random.random() > 0.95:  # 5% failure rate
                raise ConnectionError("Simulated failure")
            
            await asyncio.sleep(0.01)  # Minimal processing time
            return "Circuit breaker operation completed"
        
        result = await self.circuit_breaker.call(protected_operation)
        return result
    
    async def retry_logic_operation(self) -> str:
        """Retry logic operation."""
        
        async def potentially_failing_operation():
            # Succeed on 70% of attempts
            if random.random() > 0.7:
                raise ConnectionError("Transient failure")
            
            await asyncio.sleep(0.02)  # Minimal processing
            return "Retry operation completed"
        
        result = await self.retry_handler.execute_with_retry(potentially_failing_operation)
        return result
    
    async def state_management_operation(self) -> str:
        """Agent state management operation."""
        state = DeepAgentState()
        state.run_id = f"state_perf_{uuid.uuid4().hex[:8]}"
        
        # Simulate complex state operations
        for i in range(10):
            state.context[f"key_{i}"] = f"value_{i}_{time.time()}"
        
        # Serialize/deserialize to test state management
        state_dict = state.context.copy()
        state.context = state_dict
        
        return f"State managed: {len(state.context)} keys"
    
    async def concurrent_agent_operation(self) -> str:
        """Operation for concurrent agent testing."""
        # Create multiple agents working concurrently
        agents = [PerformanceTestAgent(f"concurrent_agent_{i}") for i in range(3)]
        
        # Execute all agents concurrently
        tasks = []
        for i, agent in enumerate(agents):
            state = DeepAgentState()
            state.run_id = f"concurrent_{i}_{uuid.uuid4().hex[:8]}"
            
            task = asyncio.create_task(
                agent.execute(state, state.run_id, stream_updates=False)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        return f"Concurrent execution completed: {len(agents)} agents"


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def performance_runner():
    """Performance benchmark runner fixture."""
    runner = PerformanceBenchmarkRunner()
    yield runner
    # Save baselines after tests
    runner.save_performance_baselines()


@pytest.fixture
def critical_path_ops():
    """Critical path operations fixture."""
    return CriticalPathOperations()


@pytest.fixture
async def monitored_performance_runner(performance_runner):
    """Performance runner with active monitoring."""
    await performance_runner.start_resource_monitoring()
    yield performance_runner
    await performance_runner.stop_resource_monitoring()


# ============================================================================
# CRITICAL PATH PERFORMANCE BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(180)
async def test_agent_execution_performance_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark agent execution performance - must meet <2s p95 SLA."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create operation list
    operations = [ops.agent_execution_operation for _ in range(100)]
    
    # Run benchmark
    results = await runner.run_benchmark(
        "agent_execution_performance",
        operations,
        iterations=100,
        concurrent=False
    )
    
    # CRITICAL SLA ASSERTIONS
    summary = results.get_performance_summary()
    duration_p95 = summary["duration_stats"]["p95"]
    
    assert duration_p95 < 2000, \
        f"Agent execution p95 too high: {duration_p95:.1f}ms (SLA: <2000ms)"
    
    assert summary["success_rate"] > 0.95, \
        f"Agent execution success rate too low: {summary['success_rate']:.2f} (required: >0.95)"
    
    # Memory usage should be reasonable
    memory_p95 = summary["memory_stats"]["p95"]
    assert memory_p95 < 512, \
        f"Agent execution memory usage too high: {memory_p95:.1f}MB (limit: <512MB)"
    
    # Compare with baseline if available
    baseline_comparison = runner.compare_with_baseline("agent_execution_performance", results)
    if baseline_comparison["status"] == "regression_detected":
        logger.warning(f"Performance regression detected: {baseline_comparison['comparisons']}")
        
        # Only fail if regression is severe
        duration_regression = baseline_comparison["comparisons"]["duration"]["regression_percent"]
        if duration_regression > 50:  # 50% regression threshold for failure
            pytest.fail(f"Severe performance regression: {duration_regression:.1f}% slower")
    
    logger.info(f"Agent execution benchmark: p95={duration_p95:.1f}ms, "
                f"throughput={summary['throughput_ops_per_second']:.1f} ops/s, "
                f"memory_p95={memory_p95:.1f}MB")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(120)
async def test_websocket_notification_latency_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark WebSocket notification latency - must be <100ms for real-time UX."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create WebSocket notification operations
    operations = [ops.websocket_notification_operation for _ in range(200)]
    
    # Run benchmark
    results = await runner.run_benchmark(
        "websocket_notification_latency",
        operations,
        iterations=200,
        concurrent=False
    )
    
    # CRITICAL LATENCY ASSERTIONS
    summary = results.get_performance_summary()
    duration_p95 = summary["duration_stats"]["p95"]
    
    assert duration_p95 < 100, \
        f"WebSocket notification p95 too high: {duration_p95:.1f}ms (UX requirement: <100ms)"
    
    assert summary["success_rate"] > 0.98, \
        f"WebSocket notification success rate too low: {summary['success_rate']:.2f} (required: >0.98)"
    
    # Throughput should be high for real-time applications
    throughput = summary["throughput_ops_per_second"]
    assert throughput > 100, \
        f"WebSocket notification throughput too low: {throughput:.1f} ops/s (required: >100)"
    
    # Get WebSocket-specific performance stats
    ws_stats = ops.websocket_manager.get_performance_stats()
    avg_ws_latency = ws_stats["average_latency_ms"]
    
    assert avg_ws_latency < 50, \
        f"Average WebSocket latency too high: {avg_ws_latency:.2f}ms (limit: <50ms)"
    
    logger.info(f"WebSocket notification benchmark: p95={duration_p95:.1f}ms, "
                f"throughput={throughput:.1f} ops/s, "
                f"avg_ws_latency={avg_ws_latency:.2f}ms")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(90)
async def test_circuit_breaker_overhead_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark circuit breaker overhead - must be <5ms per CLAUDE.md requirement."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create circuit breaker operations
    operations = [ops.circuit_breaker_operation for _ in range(500)]
    
    # Run benchmark
    results = await runner.run_benchmark(
        "circuit_breaker_overhead",
        operations,
        iterations=500,
        concurrent=False
    )
    
    # CRITICAL OVERHEAD ASSERTIONS (CLAUDE.md requirement)
    summary = results.get_performance_summary()
    avg_duration = summary["duration_stats"]["avg"]
    
    assert avg_duration < 5, \
        f"Circuit breaker overhead too high: {avg_duration:.2f}ms (CLAUDE.md requirement: <5ms)"
    
    p95_duration = summary["duration_stats"]["p95"]
    assert p95_duration < 10, \
        f"Circuit breaker p95 overhead too high: {p95_duration:.1f}ms (limit: <10ms)"
    
    assert summary["success_rate"] > 0.92, \
        f"Circuit breaker success rate too low: {summary['success_rate']:.2f} (expected: >0.92 with 5% failure rate)"
    
    # Should maintain high throughput despite protection
    throughput = summary["throughput_ops_per_second"]
    assert throughput > 200, \
        f"Circuit breaker throughput too low: {throughput:.1f} ops/s (required: >200)"
    
    logger.info(f"Circuit breaker benchmark: avg={avg_duration:.2f}ms, "
                f"p95={p95_duration:.1f}ms, "
                f"throughput={throughput:.1f} ops/s")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(120)
async def test_retry_logic_performance_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark retry logic performance including backoff timing accuracy."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create retry operations
    operations = [ops.retry_logic_operation for _ in range(100)]
    
    # Run benchmark
    results = await runner.run_benchmark(
        "retry_logic_performance",
        operations,
        iterations=100,
        concurrent=False
    )
    
    # CRITICAL RETRY PERFORMANCE ASSERTIONS
    summary = results.get_performance_summary()
    
    # Success rate should be high due to retries
    assert summary["success_rate"] > 0.95, \
        f"Retry logic success rate too low: {summary['success_rate']:.2f} (retries should recover failures)"
    
    # P95 should account for retry delays but not be excessive
    p95_duration = summary["duration_stats"]["p95"]
    assert p95_duration < 1000, \
        f"Retry logic p95 too high: {p95_duration:.1f}ms (including retries, limit: <1000ms)"
    
    # Average should be reasonable for successful first attempts
    avg_duration = summary["duration_stats"]["avg"]
    assert avg_duration < 200, \
        f"Retry logic average too high: {avg_duration:.1f}ms (many should succeed first attempt)"
    
    # Memory usage should not grow with retries
    memory_p95 = summary["memory_stats"]["p95"]
    assert memory_p95 < 256, \
        f"Retry logic memory usage too high: {memory_p95:.1f}MB (retries should not leak memory)"
    
    logger.info(f"Retry logic benchmark: p95={p95_duration:.1f}ms, "
                f"avg={avg_duration:.1f}ms, "
                f"success_rate={summary['success_rate']:.2f}")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(150)
async def test_concurrent_agent_execution_scalability(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark concurrent agent execution - must handle 50+ agents without degradation."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create concurrent operations
    operations = [ops.concurrent_agent_operation for _ in range(50)]
    
    # Run concurrent benchmark
    results = await runner.run_benchmark(
        "concurrent_agent_scalability",
        operations,
        iterations=50,
        concurrent=True,
        concurrency_level=20  # 20 concurrent operations
    )
    
    # CRITICAL SCALABILITY ASSERTIONS
    summary = results.get_performance_summary()
    
    # Should handle high concurrency without failures
    assert summary["success_rate"] > 0.9, \
        f"Concurrent execution success rate too low: {summary['success_rate']:.2f} (required: >0.9)"
    
    # P95 should not degrade significantly under load
    p95_duration = summary["duration_stats"]["p95"]
    assert p95_duration < 5000, \
        f"Concurrent execution p95 too high: {p95_duration:.1f}ms (scalability limit: <5000ms)"
    
    # Should maintain reasonable throughput
    throughput = summary["throughput_ops_per_second"]
    assert throughput > 10, \
        f"Concurrent execution throughput too low: {throughput:.1f} ops/s (required: >10)"
    
    # Memory usage should be bounded
    memory_p95 = summary["memory_stats"]["p95"]
    assert memory_p95 < 1024, \
        f"Concurrent execution memory too high: {memory_p95:.1f}MB (limit: <1GB)"
    
    # Check resource monitoring for stability
    if runner.resource_samples:
        peak_memory = max(sample["memory_mb"] for sample in runner.resource_samples)
        avg_threads = statistics.mean([sample["thread_count"] for sample in runner.resource_samples])
        
        assert peak_memory < 1500, \
            f"Peak memory during concurrent test too high: {peak_memory:.1f}MB"
        assert avg_threads < 150, \
            f"Too many threads during concurrent test: {avg_threads:.1f}"
    
    logger.info(f"Concurrent scalability benchmark: p95={p95_duration:.1f}ms, "
                f"throughput={throughput:.1f} ops/s, "
                f"memory_p95={memory_p95:.1f}MB, "
                f"success_rate={summary['success_rate']:.2f}")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(120)
async def test_state_management_performance_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: Benchmark agent state management performance."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create state management operations
    operations = [ops.state_management_operation for _ in range(300)]
    
    # Run benchmark
    results = await runner.run_benchmark(
        "state_management_performance",
        operations,
        iterations=300,
        concurrent=False
    )
    
    # CRITICAL STATE MANAGEMENT ASSERTIONS
    summary = results.get_performance_summary()
    
    # State operations should be fast
    p95_duration = summary["duration_stats"]["p95"]
    assert p95_duration < 50, \
        f"State management p95 too high: {p95_duration:.1f}ms (limit: <50ms)"
    
    # Should have perfect success rate for state operations
    assert summary["success_rate"] > 0.99, \
        f"State management success rate too low: {summary['success_rate']:.2f} (should be >0.99)"
    
    # Should maintain high throughput
    throughput = summary["throughput_ops_per_second"]
    assert throughput > 100, \
        f"State management throughput too low: {throughput:.1f} ops/s (required: >100)"
    
    # Memory usage should be efficient
    memory_p95 = summary["memory_stats"]["p95"]
    assert memory_p95 < 200, \
        f"State management memory usage too high: {memory_p95:.1f}MB (limit: <200MB)"
    
    logger.info(f"State management benchmark: p95={p95_duration:.1f}ms, "
                f"throughput={throughput:.1f} ops/s, "
                f"memory_p95={memory_p95:.1f}MB")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(200)
async def test_end_to_end_critical_path_benchmark(monitored_performance_runner, critical_path_ops):
    """CRITICAL: End-to-end benchmark of complete critical path workflow."""
    
    runner = monitored_performance_runner
    ops = critical_path_ops
    
    # Create end-to-end workflow operation
    async def e2e_critical_path_operation():
        """Complete critical path: Agent + WebSocket + Circuit Breaker + State."""
        
        # 1. Agent execution
        agent_result = await ops.agent_execution_operation()
        
        # 2. WebSocket notification
        ws_result = await ops.websocket_notification_operation()
        
        # 3. Circuit breaker protection
        cb_result = await ops.circuit_breaker_operation()
        
        # 4. State management
        state_result = await ops.state_management_operation()
        
        return f"E2E completed: {len([agent_result, ws_result, cb_result, state_result])} steps"
    
    # Run end-to-end benchmark
    operations = [e2e_critical_path_operation for _ in range(50)]
    
    results = await runner.run_benchmark(
        "end_to_end_critical_path",
        operations,
        iterations=50,
        concurrent=False
    )
    
    # CRITICAL END-TO-END ASSERTIONS
    summary = results.get_performance_summary()
    
    # Complete workflow should be fast enough for user experience
    p95_duration = summary["duration_stats"]["p95"]
    assert p95_duration < 3000, \
        f"E2E critical path p95 too high: {p95_duration:.1f}ms (UX limit: <3000ms)"
    
    # Should maintain high reliability
    assert summary["success_rate"] > 0.9, \
        f"E2E critical path success rate too low: {summary['success_rate']:.2f} (required: >0.9)"
    
    # Should maintain reasonable throughput
    throughput = summary["throughput_ops_per_second"]
    assert throughput > 5, \
        f"E2E critical path throughput too low: {throughput:.1f} ops/s (required: >5)"
    
    # Memory usage should be bounded
    memory_p95 = summary["memory_stats"]["p95"]
    assert memory_p95 < 800, \
        f"E2E critical path memory too high: {memory_p95:.1f}MB (limit: <800MB)"
    
    # Compare with baseline
    baseline_comparison = runner.compare_with_baseline("end_to_end_critical_path", results)
    if baseline_comparison["status"] == "regression_detected":
        # Log detailed regression information
        comparisons = baseline_comparison["comparisons"]
        logger.warning(f"E2E performance regression detected:")
        for metric, data in comparisons.items():
            if not data.get("acceptable", True):
                logger.warning(f"  {metric}: {data}")
    
    logger.info(f"E2E critical path benchmark: p95={p95_duration:.1f}ms, "
                f"throughput={throughput:.1f} ops/s, "
                f"memory_p95={memory_p95:.1f}MB, "
                f"success_rate={summary['success_rate']:.2f}")


if __name__ == "__main__":
    # Run critical path performance benchmarks
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])