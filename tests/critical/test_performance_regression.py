#!/usr/bin/env python
"""
PERFORMANCE REGRESSION TEST SUITE

CRITICAL PERFORMANCE BENCHMARKING AND VALIDATION:
- Baseline performance establishment and monitoring
- Regression detection across all critical fixes
- Performance impact analysis for each system component
- Load testing and scalability validation
- Memory performance optimization verification
- Real-time performance monitoring and alerting
- Historical performance trend analysis

This test suite provides COMPREHENSIVE performance testing:
1. Baseline performance measurement and storage
2. Component-specific performance benchmarking
3. Integration performance validation
4. Memory usage optimization verification
5. WebSocket throughput and latency testing
6. Database query performance analysis
7. Startup time performance validation
8. Concurrent user performance scaling
9. Resource utilization efficiency testing
10. Performance regression alerts and reporting

Business Impact: Ensures optimal system performance and user experience
Strategic Value: Critical for maintaining competitive performance standards
"""

import asyncio
import json
import os
import random
import sys
import time
import uuid
import threading
import statistics
import tracemalloc
import psutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set, Callable, Tuple, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# Import system components for performance testing
try:
    # Memory optimization
    from netra_backend.app.services.memory_optimization_service import MemoryOptimizationService
    from netra_backend.app.services.session_memory_manager import SessionMemoryManager
    
    # WebSocket systems
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Database systems
    from netra_backend.app.database.clickhouse_client import ClickHouseClient
    
    # Startup systems
    from netra_backend.app.smd import StartupOrchestrator
    
    PERFORMANCE_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Performance test services not available: {e}")
    PERFORMANCE_SERVICES_AVAILABLE = False
    
    # Mock services for performance testing
    class MemoryOptimizationService:
        async def start(self): await asyncio.sleep(0.1)
        async def stop(self): await asyncio.sleep(0.1)
        
    class SessionMemoryManager:
        async def start(self): await asyncio.sleep(0.1)
        async def stop(self): await asyncio.sleep(0.1)
        
    class WebSocketManager:
        def __init__(self): self.active_connections = {}
        async def connect(self, ws, user_id): await asyncio.sleep(0.01)
        async def send_message(self, user_id, msg): await asyncio.sleep(0.01)
        
    class AgentWebSocketBridge:
        async def send_notification(self, user_id, data): await asyncio.sleep(0.01)
        
    class ClickHouseClient:
        async def connect(self): await asyncio.sleep(0.1)
        async def execute(self, query): 
            await asyncio.sleep(0.05)
            return []
            
    class StartupOrchestrator:
        def __init__(self, app): self.app = app
        async def initialize_system(self): await asyncio.sleep(1.0)

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Performance test constants
PERFORMANCE_BASELINE_FILE = os.path.join(project_root, "tests", "performance_baseline.json")
REGRESSION_THRESHOLD = 1.5  # 50% performance degradation threshold
MEMORY_LIMIT_MB = 2048  # 2GB memory limit
CONCURRENT_USER_COUNTS = [1, 5, 10, 25, 50]  # Different load levels
STRESS_TEST_DURATION = 120  # 2 minutes for stress tests
BENCHMARK_ITERATIONS = 10  # Iterations for reliable benchmarks
WARMUP_ITERATIONS = 3  # Warmup iterations to exclude JIT effects


@dataclass
class PerformanceBenchmark:
    """Performance benchmark result."""
    test_name: str
    timestamp: float
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    throughput: float  # Operations per second
    latency_ms: float
    concurrent_users: int
    operations_completed: int
    errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBaseline:
    """Performance baseline for regression detection."""
    test_name: str
    baseline_duration_ms: float
    baseline_memory_mb: float
    baseline_throughput: float
    baseline_latency_ms: float
    established_date: float
    version: str = "1.0"
    confidence_interval: float = 0.95


@dataclass
class RegressionDetectionResult:
    """Performance regression detection result."""
    test_name: str
    regression_detected: bool
    severity: str  # "none", "minor", "moderate", "critical"
    current_performance: PerformanceBenchmark
    baseline_performance: PerformanceBaseline
    performance_delta_percent: float
    details: Dict[str, Any] = field(default_factory=dict)


class SystemPerformanceProfiler:
    """Profiles system performance across all components."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = 0.0
        self.profiling_active = False
        self.measurement_interval = 0.1  # 100ms intervals
        self.measurements: List[Dict[str, Any]] = []
        
    def start_profiling(self):
        """Start continuous performance profiling."""
        self.profiling_active = True
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        self.measurements.clear()
        tracemalloc.start()
        
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return summary metrics."""
        self.profiling_active = False
        
        if not self.measurements:
            return {"error": "No measurements collected"}
        
        # Calculate summary statistics
        cpu_values = [m["cpu_percent"] for m in self.measurements]
        memory_values = [m["memory_mb"] for m in self.measurements]
        
        # Get tracemalloc statistics
        tracemalloc_stats = {}
        try:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc_stats = {
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024
            }
            tracemalloc.stop()
        except Exception:
            pass
        
        return {
            "duration_ms": len(self.measurements) * self.measurement_interval * 1000,
            "avg_cpu_percent": statistics.mean(cpu_values) if cpu_values else 0,
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "avg_memory_mb": statistics.mean(memory_values) if memory_values else 0,
            "max_memory_mb": max(memory_values) if memory_values else 0,
            "memory_growth_mb": max(memory_values) - self.baseline_memory if memory_values else 0,
            "measurement_count": len(self.measurements),
            "tracemalloc": tracemalloc_stats
        }
    
    async def measure_performance_during(self, async_operation: Callable, context: str = ""):
        """Measure performance during an async operation."""
        self.start_profiling()
        
        # Start background monitoring
        monitoring_task = asyncio.create_task(self._continuous_monitoring())
        
        try:
            start_time = time.time()
            result = await async_operation()
            end_time = time.time()
            
            # Stop monitoring
            monitoring_task.cancel()
            
            # Get performance summary
            perf_summary = self.stop_profiling()
            perf_summary["operation_duration_ms"] = (end_time - start_time) * 1000
            perf_summary["context"] = context
            
            return result, perf_summary
            
        except Exception as e:
            monitoring_task.cancel()
            self.stop_profiling()
            raise
    
    async def _continuous_monitoring(self):
        """Continuously monitor system performance."""
        try:
            while self.profiling_active:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()
                
                measurement = {
                    "timestamp": time.time(),
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": cpu_percent,
                    "threads": self.process.num_threads()
                }
                
                self.measurements.append(measurement)
                await asyncio.sleep(self.measurement_interval)
                
        except asyncio.CancelledError:
            pass


class PerformanceBenchmarkRunner:
    """Runs comprehensive performance benchmarks."""
    
    def __init__(self):
        self.profiler = SystemPerformanceProfiler()
        self.benchmarks: List[PerformanceBenchmark] = []
        
    async def benchmark_memory_optimization_performance(self) -> PerformanceBenchmark:
        """Benchmark memory optimization service performance."""
        logger.info("Benchmarking memory optimization performance")
        
        async def memory_operation():
            service = MemoryOptimizationService()
            await service.start()
            
            # Simulate memory-intensive operations
            operations_completed = 0
            for i in range(1000):
                # Simulate memory allocation and cleanup
                temp_data = [f"data_{i}_{j}" for j in range(100)]
                await asyncio.sleep(0.001)  # Simulate processing
                del temp_data
                operations_completed += 1
            
            await service.stop()
            return {"operations_completed": operations_completed}
        
        result, perf_data = await self.profiler.measure_performance_during(
            memory_operation, "memory_optimization"
        )
        
        benchmark = PerformanceBenchmark(
            test_name="memory_optimization",
            timestamp=time.time(),
            duration_ms=perf_data["operation_duration_ms"],
            memory_mb=perf_data["max_memory_mb"],
            cpu_percent=perf_data["max_cpu_percent"],
            throughput=result["operations_completed"] / (perf_data["operation_duration_ms"] / 1000),
            latency_ms=perf_data["operation_duration_ms"] / result["operations_completed"],
            concurrent_users=1,
            operations_completed=result["operations_completed"],
            metadata={"memory_growth_mb": perf_data["memory_growth_mb"]}
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def benchmark_websocket_performance(self, concurrent_users: int = 10) -> PerformanceBenchmark:
        """Benchmark WebSocket manager performance."""
        logger.info(f"Benchmarking WebSocket performance with {concurrent_users} users")
        
        async def websocket_operation():
            manager = WebSocketManager()
            bridge = AgentWebSocketBridge()
            
            # Create concurrent connections
            connections = []
            messages_sent = 0
            
            # Connect users
            for i in range(concurrent_users):
                mock_ws = Mock()
                user_id = f"perf_user_{i}"
                await manager.connect(mock_ws, user_id)
                connections.append((mock_ws, user_id))
            
            # Send messages
            for i in range(100):  # 100 messages per user
                for mock_ws, user_id in connections:
                    message = {
                        "type": "performance_test",
                        "user_id": user_id,
                        "message_id": i,
                        "data": "x" * 100  # 100 bytes per message
                    }
                    await manager.send_message(user_id, message)
                    await bridge.send_notification(user_id, message)
                    messages_sent += 1
            
            # Disconnect users
            for mock_ws, user_id in connections:
                await manager.disconnect(mock_ws)
            
            return {"messages_sent": messages_sent, "connections": len(connections)}
        
        result, perf_data = await self.profiler.measure_performance_during(
            websocket_operation, f"websocket_{concurrent_users}_users"
        )
        
        benchmark = PerformanceBenchmark(
            test_name="websocket_performance",
            timestamp=time.time(),
            duration_ms=perf_data["operation_duration_ms"],
            memory_mb=perf_data["max_memory_mb"],
            cpu_percent=perf_data["max_cpu_percent"],
            throughput=result["messages_sent"] / (perf_data["operation_duration_ms"] / 1000),
            latency_ms=perf_data["operation_duration_ms"] / result["messages_sent"],
            concurrent_users=concurrent_users,
            operations_completed=result["messages_sent"],
            metadata={
                "connections": result["connections"],
                "memory_growth_mb": perf_data["memory_growth_mb"]
            }
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def benchmark_database_performance(self) -> PerformanceBenchmark:
        """Benchmark database operations performance."""
        logger.info("Benchmarking database performance")
        
        async def database_operation():
            client = ClickHouseClient()
            await client.connect()
            
            queries_executed = 0
            
            # Test different query types
            test_queries = [
                "SELECT 1",
                "SELECT version()",
                "SELECT count(*) FROM system.tables",
                "SELECT name FROM system.databases LIMIT 5",
                "SELECT name, engine FROM system.tables LIMIT 10"
            ]
            
            # Execute queries multiple times
            for _ in range(200):  # 200 iterations
                query = random.choice(test_queries)
                await client.execute(query)
                queries_executed += 1
            
            return {"queries_executed": queries_executed}
        
        result, perf_data = await self.profiler.measure_performance_during(
            database_operation, "database_performance"
        )
        
        benchmark = PerformanceBenchmark(
            test_name="database_performance",
            timestamp=time.time(),
            duration_ms=perf_data["operation_duration_ms"],
            memory_mb=perf_data["max_memory_mb"],
            cpu_percent=perf_data["max_cpu_percent"],
            throughput=result["queries_executed"] / (perf_data["operation_duration_ms"] / 1000),
            latency_ms=perf_data["operation_duration_ms"] / result["queries_executed"],
            concurrent_users=1,
            operations_completed=result["queries_executed"],
            metadata={"memory_growth_mb": perf_data["memory_growth_mb"]}
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def benchmark_startup_performance(self) -> PerformanceBenchmark:
        """Benchmark system startup performance."""
        logger.info("Benchmarking startup performance")
        
        async def startup_operation():
            from fastapi import FastAPI
            app = FastAPI() if PERFORMANCE_SERVICES_AVAILABLE else Mock()
            orchestrator = StartupOrchestrator(app)
            
            await orchestrator.initialize_system()
            return {"startup_completed": True}
        
        result, perf_data = await self.profiler.measure_performance_during(
            startup_operation, "startup_performance"
        )
        
        benchmark = PerformanceBenchmark(
            test_name="startup_performance",
            timestamp=time.time(),
            duration_ms=perf_data["operation_duration_ms"],
            memory_mb=perf_data["max_memory_mb"],
            cpu_percent=perf_data["max_cpu_percent"],
            throughput=1 / (perf_data["operation_duration_ms"] / 1000),  # Startups per second
            latency_ms=perf_data["operation_duration_ms"],
            concurrent_users=1,
            operations_completed=1,
            metadata={"memory_growth_mb": perf_data["memory_growth_mb"]}
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def benchmark_integrated_system_performance(self, concurrent_users: int = 25) -> PerformanceBenchmark:
        """Benchmark integrated system performance under load."""
        logger.info(f"Benchmarking integrated system with {concurrent_users} users")
        
        async def integrated_operation():
            # Initialize all services
            memory_service = MemoryOptimizationService()
            session_manager = SessionMemoryManager()
            websocket_manager = WebSocketManager()
            bridge = AgentWebSocketBridge()
            clickhouse_client = ClickHouseClient()
            
            await memory_service.start()
            await session_manager.start()
            await clickhouse_client.connect()
            
            total_operations = 0
            
            # Simulate integrated user operations
            for user_id in range(concurrent_users):
                # WebSocket connection
                mock_ws = Mock()
                await websocket_manager.connect(mock_ws, f"user_{user_id}")
                
                # User operations
                for op in range(20):  # 20 operations per user
                    # Send WebSocket message
                    message = {
                        "user_id": f"user_{user_id}",
                        "operation": op,
                        "data": "test_data"
                    }
                    await websocket_manager.send_message(f"user_{user_id}", message)
                    
                    # Database operation
                    await clickhouse_client.execute(f"SELECT '{user_id}', {op}")
                    
                    # Bridge notification
                    await bridge.send_notification(f"user_{user_id}", message)
                    
                    total_operations += 3  # WebSocket + DB + Bridge
                
                # Disconnect
                await websocket_manager.disconnect(mock_ws)
            
            # Cleanup
            await memory_service.stop()
            await session_manager.stop()
            
            return {"total_operations": total_operations, "users": concurrent_users}
        
        result, perf_data = await self.profiler.measure_performance_during(
            integrated_operation, f"integrated_system_{concurrent_users}_users"
        )
        
        benchmark = PerformanceBenchmark(
            test_name="integrated_system",
            timestamp=time.time(),
            duration_ms=perf_data["operation_duration_ms"],
            memory_mb=perf_data["max_memory_mb"],
            cpu_percent=perf_data["max_cpu_percent"],
            throughput=result["total_operations"] / (perf_data["operation_duration_ms"] / 1000),
            latency_ms=perf_data["operation_duration_ms"] / result["total_operations"],
            concurrent_users=concurrent_users,
            operations_completed=result["total_operations"],
            metadata={
                "users": result["users"],
                "memory_growth_mb": perf_data["memory_growth_mb"]
            }
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmarks."""
        if not self.benchmarks:
            return {"error": "No benchmarks completed"}
        
        summary = {
            "total_benchmarks": len(self.benchmarks),
            "benchmarks": []
        }
        
        for benchmark in self.benchmarks:
            summary["benchmarks"].append({
                "test_name": benchmark.test_name,
                "duration_ms": benchmark.duration_ms,
                "throughput": benchmark.throughput,
                "memory_mb": benchmark.memory_mb,
                "concurrent_users": benchmark.concurrent_users,
                "timestamp": benchmark.timestamp
            })
        
        return summary


class PerformanceRegressionDetector:
    """Detects performance regressions by comparing against baselines."""
    
    def __init__(self, baseline_file: str = PERFORMANCE_BASELINE_FILE):
        self.baseline_file = baseline_file
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.load_baselines()
    
    def load_baselines(self):
        """Load performance baselines from file."""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    
                for baseline_data in data.get("baselines", []):
                    baseline = PerformanceBaseline(**baseline_data)
                    self.baselines[baseline.test_name] = baseline
                
                logger.info(f"Loaded {len(self.baselines)} performance baselines")
            else:
                logger.info("No existing baseline file found")
        except Exception as e:
            logger.error(f"Failed to load baselines: {e}")
    
    def save_baselines(self):
        """Save performance baselines to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            
            data = {
                "created": time.time(),
                "baselines": [asdict(baseline) for baseline in self.baselines.values()]
            }
            
            with open(self.baseline_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.baselines)} performance baselines")
        except Exception as e:
            logger.error(f"Failed to save baselines: {e}")
    
    def establish_baseline(self, benchmark: PerformanceBenchmark):
        """Establish a new performance baseline."""
        baseline = PerformanceBaseline(
            test_name=benchmark.test_name,
            baseline_duration_ms=benchmark.duration_ms,
            baseline_memory_mb=benchmark.memory_mb,
            baseline_throughput=benchmark.throughput,
            baseline_latency_ms=benchmark.latency_ms,
            established_date=time.time()
        )
        
        self.baselines[benchmark.test_name] = baseline
        logger.info(f"Established baseline for {benchmark.test_name}")
    
    def detect_regression(self, benchmark: PerformanceBenchmark) -> RegressionDetectionResult:
        """Detect performance regression by comparing to baseline."""
        baseline = self.baselines.get(benchmark.test_name)
        
        if not baseline:
            # No baseline exists, establish one
            self.establish_baseline(benchmark)
            return RegressionDetectionResult(
                test_name=benchmark.test_name,
                regression_detected=False,
                severity="none",
                current_performance=benchmark,
                baseline_performance=baseline,
                performance_delta_percent=0.0,
                details={"message": "Baseline established"}
            )
        
        # Calculate performance deltas
        duration_delta = ((benchmark.duration_ms - baseline.baseline_duration_ms) / 
                         baseline.baseline_duration_ms * 100)
        memory_delta = ((benchmark.memory_mb - baseline.baseline_memory_mb) / 
                       max(baseline.baseline_memory_mb, 1) * 100)
        throughput_delta = ((baseline.baseline_throughput - benchmark.throughput) / 
                           baseline.baseline_throughput * 100)
        latency_delta = ((benchmark.latency_ms - baseline.baseline_latency_ms) / 
                        baseline.baseline_latency_ms * 100)
        
        # Determine worst regression
        max_regression = max(duration_delta, memory_delta, throughput_delta, latency_delta)
        
        # Classify severity
        if max_regression < 10:
            severity = "none"
            regression_detected = False
        elif max_regression < 25:
            severity = "minor"
            regression_detected = True
        elif max_regression < 50:
            severity = "moderate"
            regression_detected = True
        else:
            severity = "critical"
            regression_detected = True
        
        return RegressionDetectionResult(
            test_name=benchmark.test_name,
            regression_detected=regression_detected,
            severity=severity,
            current_performance=benchmark,
            baseline_performance=baseline,
            performance_delta_percent=max_regression,
            details={
                "duration_delta_percent": duration_delta,
                "memory_delta_percent": memory_delta,
                "throughput_delta_percent": throughput_delta,
                "latency_delta_percent": latency_delta,
                "analysis": f"Worst regression: {max_regression:.2f}%"
            }
        )
    
    def update_baseline_if_improved(self, benchmark: PerformanceBenchmark):
        """Update baseline if current performance is significantly better."""
        baseline = self.baselines.get(benchmark.test_name)
        if not baseline:
            return
        
        # Check if performance improved significantly (>15% better)
        throughput_improvement = ((benchmark.throughput - baseline.baseline_throughput) / 
                                baseline.baseline_throughput * 100)
        
        if throughput_improvement > 15:
            logger.info(f"Performance improved by {throughput_improvement:.2f}%, updating baseline for {benchmark.test_name}")
            self.establish_baseline(benchmark)


class ConcurrentLoadTester:
    """Tests performance under varying concurrent load."""
    
    def __init__(self, benchmark_runner: PerformanceBenchmarkRunner):
        self.benchmark_runner = benchmark_runner
        self.load_test_results: List[PerformanceBenchmark] = []
    
    async def run_scaling_performance_test(self) -> List[PerformanceBenchmark]:
        """Run performance tests with increasing concurrent load."""
        logger.info("Running scaling performance test")
        
        results = []
        
        for user_count in CONCURRENT_USER_COUNTS:
            logger.info(f"Testing with {user_count} concurrent users")
            
            # Run WebSocket performance test
            websocket_benchmark = await self.benchmark_runner.benchmark_websocket_performance(user_count)
            results.append(websocket_benchmark)
            
            # Run integrated system test for higher user counts
            if user_count >= 5:
                integrated_benchmark = await self.benchmark_runner.benchmark_integrated_system_performance(user_count)
                results.append(integrated_benchmark)
            
            # Allow system to cool down between tests
            await asyncio.sleep(2.0)
        
        self.load_test_results = results
        return results
    
    def analyze_scaling_performance(self) -> Dict[str, Any]:
        """Analyze how performance scales with load."""
        if not self.load_test_results:
            return {"error": "No load test results"}
        
        # Group by test type
        websocket_results = [r for r in self.load_test_results if r.test_name == "websocket_performance"]
        integrated_results = [r for r in self.load_test_results if r.test_name == "integrated_system"]
        
        def analyze_test_group(results: List[PerformanceBenchmark], test_type: str):
            if not results:
                return {}
            
            # Calculate scaling metrics
            throughput_per_user = []
            memory_per_user = []
            latency_growth = []
            
            for result in results:
                throughput_per_user.append(result.throughput / result.concurrent_users)
                memory_per_user.append(result.memory_mb / result.concurrent_users)
                latency_growth.append(result.latency_ms)
            
            # Detect scaling issues
            throughput_degradation = ((throughput_per_user[0] - throughput_per_user[-1]) / 
                                    throughput_per_user[0] * 100) if len(throughput_per_user) > 1 else 0
            
            memory_growth_rate = ((memory_per_user[-1] - memory_per_user[0]) / 
                                memory_per_user[0] * 100) if len(memory_per_user) > 1 else 0
            
            latency_increase = ((latency_growth[-1] - latency_growth[0]) / 
                              latency_growth[0] * 100) if len(latency_growth) > 1 else 0
            
            return {
                "test_type": test_type,
                "user_counts": [r.concurrent_users for r in results],
                "throughput_per_user": throughput_per_user,
                "memory_per_user": memory_per_user,
                "latency_values": latency_growth,
                "throughput_degradation_percent": throughput_degradation,
                "memory_growth_rate_percent": memory_growth_rate,
                "latency_increase_percent": latency_increase,
                "scaling_efficiency": max(0, 100 - throughput_degradation)
            }
        
        websocket_analysis = analyze_test_group(websocket_results, "websocket")
        integrated_analysis = analyze_test_group(integrated_results, "integrated")
        
        return {
            "websocket_scaling": websocket_analysis,
            "integrated_scaling": integrated_analysis,
            "overall_scaling_health": {
                "websocket_efficient": websocket_analysis.get("scaling_efficiency", 0) > 70,
                "integrated_efficient": integrated_analysis.get("scaling_efficiency", 0) > 60,
                "memory_growth_acceptable": (
                    websocket_analysis.get("memory_growth_rate_percent", 0) < 200 and
                    integrated_analysis.get("memory_growth_rate_percent", 0) < 300
                )
            }
        }


# ============================================================================
# PERFORMANCE REGRESSION TEST SUITE
# ============================================================================

@pytest.fixture
async def performance_profiler():
    """Fixture providing system performance profiler."""
    profiler = SystemPerformanceProfiler()
    try:
        yield profiler
    finally:
        if profiler.profiling_active:
            profiler.stop_profiling()


@pytest.fixture
async def benchmark_runner():
    """Fixture providing performance benchmark runner."""
    runner = PerformanceBenchmarkRunner()
    try:
        yield runner
    finally:
        pass


@pytest.fixture
async def regression_detector():
    """Fixture providing performance regression detector."""
    detector = PerformanceRegressionDetector()
    try:
        yield detector
    finally:
        detector.save_baselines()


@pytest.fixture
async def concurrent_load_tester(benchmark_runner):
    """Fixture providing concurrent load tester."""
    tester = ConcurrentLoadTester(benchmark_runner)
    try:
        yield tester
    finally:
        pass


@pytest.mark.asyncio
class TestPerformanceRegression:
    """Performance regression test suite."""
    
    async def test_memory_optimization_performance_benchmark(self, benchmark_runner, regression_detector):
        """Test memory optimization performance and detect regressions."""
        logger.info("Running memory optimization performance benchmark")
        
        # Run benchmark
        benchmark = await benchmark_runner.benchmark_memory_optimization_performance()
        
        # Detect regressions
        regression_result = regression_detector.detect_regression(benchmark)
        
        logger.info(f"Memory optimization benchmark results:")
        logger.info(f"  Duration: {benchmark.duration_ms:.2f}ms")
        logger.info(f"  Memory usage: {benchmark.memory_mb:.2f}MB")
        logger.info(f"  Throughput: {benchmark.throughput:.2f} ops/s")
        logger.info(f"  Regression: {regression_result.severity}")
        
        # Validate performance requirements
        assert benchmark.duration_ms <= 30000, f"Memory optimization too slow: {benchmark.duration_ms:.2f}ms"
        assert benchmark.memory_mb <= 500, f"Memory optimization uses too much memory: {benchmark.memory_mb:.2f}MB"
        assert benchmark.throughput >= 20, f"Memory optimization throughput too low: {benchmark.throughput:.2f} ops/s"
        
        # Validate no critical regressions
        assert regression_result.severity != "critical", \
            f"CRITICAL performance regression detected in memory optimization: {regression_result.performance_delta_percent:.2f}%"
        
        # Update baseline if performance improved
        regression_detector.update_baseline_if_improved(benchmark)
    
    async def test_websocket_performance_benchmark(self, benchmark_runner, regression_detector):
        """Test WebSocket performance and detect regressions."""
        logger.info("Running WebSocket performance benchmark")
        
        # Test with moderate load
        benchmark = await benchmark_runner.benchmark_websocket_performance(concurrent_users=10)
        
        # Detect regressions
        regression_result = regression_detector.detect_regression(benchmark)
        
        logger.info(f"WebSocket benchmark results:")
        logger.info(f"  Duration: {benchmark.duration_ms:.2f}ms")
        logger.info(f"  Memory usage: {benchmark.memory_mb:.2f}MB")
        logger.info(f"  Throughput: {benchmark.throughput:.2f} msg/s")
        logger.info(f"  Latency: {benchmark.latency_ms:.2f}ms")
        logger.info(f"  Regression: {regression_result.severity}")
        
        # Validate performance requirements
        assert benchmark.throughput >= 100, f"WebSocket throughput too low: {benchmark.throughput:.2f} msg/s"
        assert benchmark.latency_ms <= 100, f"WebSocket latency too high: {benchmark.latency_ms:.2f}ms"
        assert benchmark.memory_mb <= 200, f"WebSocket memory usage too high: {benchmark.memory_mb:.2f}MB"
        
        # Validate no critical regressions
        assert regression_result.severity != "critical", \
            f"CRITICAL WebSocket performance regression: {regression_result.performance_delta_percent:.2f}%"
        
        regression_detector.update_baseline_if_improved(benchmark)
    
    async def test_database_performance_benchmark(self, benchmark_runner, regression_detector):
        """Test database performance and detect regressions."""
        logger.info("Running database performance benchmark")
        
        # Run database benchmark
        benchmark = await benchmark_runner.benchmark_database_performance()
        
        # Detect regressions
        regression_result = regression_detector.detect_regression(benchmark)
        
        logger.info(f"Database benchmark results:")
        logger.info(f"  Duration: {benchmark.duration_ms:.2f}ms")
        logger.info(f"  Throughput: {benchmark.throughput:.2f} queries/s")
        logger.info(f"  Average latency: {benchmark.latency_ms:.2f}ms")
        logger.info(f"  Regression: {regression_result.severity}")
        
        # Validate performance requirements
        assert benchmark.throughput >= 50, f"Database throughput too low: {benchmark.throughput:.2f} queries/s"
        assert benchmark.latency_ms <= 50, f"Database latency too high: {benchmark.latency_ms:.2f}ms"
        
        # Validate no critical regressions
        assert regression_result.severity != "critical", \
            f"CRITICAL database performance regression: {regression_result.performance_delta_percent:.2f}%"
        
        regression_detector.update_baseline_if_improved(benchmark)
    
    async def test_startup_performance_benchmark(self, benchmark_runner, regression_detector):
        """Test startup performance and detect regressions."""
        logger.info("Running startup performance benchmark")
        
        # Run startup benchmark
        benchmark = await benchmark_runner.benchmark_startup_performance()
        
        # Detect regressions
        regression_result = regression_detector.detect_regression(benchmark)
        
        logger.info(f"Startup benchmark results:")
        logger.info(f"  Duration: {benchmark.duration_ms:.2f}ms")
        logger.info(f"  Memory usage: {benchmark.memory_mb:.2f}MB")
        logger.info(f"  Regression: {regression_result.severity}")
        
        # Validate performance requirements
        assert benchmark.duration_ms <= 10000, f"Startup too slow: {benchmark.duration_ms:.2f}ms"
        assert benchmark.memory_mb <= 300, f"Startup memory usage too high: {benchmark.memory_mb:.2f}MB"
        
        # Validate no critical regressions
        assert regression_result.severity != "critical", \
            f"CRITICAL startup performance regression: {regression_result.performance_delta_percent:.2f}%"
        
        regression_detector.update_baseline_if_improved(benchmark)
    
    @pytest.mark.slow
    async def test_integrated_system_performance_benchmark(self, benchmark_runner, regression_detector):
        """Test integrated system performance under realistic load."""
        logger.info("Running integrated system performance benchmark")
        
        # Test with realistic concurrent load
        benchmark = await benchmark_runner.benchmark_integrated_system_performance(concurrent_users=25)
        
        # Detect regressions
        regression_result = regression_detector.detect_regression(benchmark)
        
        logger.info(f"Integrated system benchmark results:")
        logger.info(f"  Duration: {benchmark.duration_ms:.2f}ms")
        logger.info(f"  Memory usage: {benchmark.memory_mb:.2f}MB")
        logger.info(f"  Throughput: {benchmark.throughput:.2f} ops/s")
        logger.info(f"  Operations completed: {benchmark.operations_completed}")
        logger.info(f"  Regression: {regression_result.severity}")
        
        # Validate performance requirements
        assert benchmark.throughput >= 10, f"Integrated system throughput too low: {benchmark.throughput:.2f} ops/s"
        assert benchmark.memory_mb <= MEMORY_LIMIT_MB * 0.8, \
            f"Integrated system memory usage too high: {benchmark.memory_mb:.2f}MB"
        assert benchmark.operations_completed >= 25 * 20 * 3 * 0.8, \
            f"Too few operations completed: {benchmark.operations_completed}"
        
        # Validate no critical regressions
        assert regression_result.severity != "critical", \
            f"CRITICAL integrated system performance regression: {regression_result.performance_delta_percent:.2f}%"
        
        regression_detector.update_baseline_if_improved(benchmark)
    
    @pytest.mark.slow
    async def test_concurrent_scaling_performance(self, concurrent_load_tester, regression_detector):
        """Test performance scaling under increasing concurrent load."""
        logger.info("Running concurrent scaling performance test")
        
        # Run scaling test
        scaling_results = await concurrent_load_tester.run_scaling_performance_test()
        
        # Analyze scaling performance
        scaling_analysis = concurrent_load_tester.analyze_scaling_performance()
        
        logger.info(f"Scaling performance analysis:")
        logger.info(f"  WebSocket scaling efficiency: {scaling_analysis['websocket_scaling'].get('scaling_efficiency', 0):.2f}%")
        logger.info(f"  Integrated scaling efficiency: {scaling_analysis['integrated_scaling'].get('scaling_efficiency', 0):.2f}%")
        
        # Check each scaling result for regressions
        scaling_regressions = []
        for result in scaling_results:
            regression = regression_detector.detect_regression(result)
            if regression.severity in ["moderate", "critical"]:
                scaling_regressions.append(regression)
        
        # Validate scaling performance
        scaling_health = scaling_analysis.get("overall_scaling_health", {})
        
        assert scaling_health.get("websocket_efficient", False), \
            "WebSocket scaling efficiency below 70%"
        
        assert scaling_health.get("integrated_efficient", False), \
            "Integrated system scaling efficiency below 60%"
        
        assert scaling_health.get("memory_growth_acceptable", False), \
            "Memory growth rate unacceptable during scaling"
        
        # No critical scaling regressions
        critical_regressions = [r for r in scaling_regressions if r.severity == "critical"]
        assert len(critical_regressions) == 0, \
            f"Critical performance regressions during scaling: {[r.test_name for r in critical_regressions]}"
        
        # Update baselines for improved performance
        for result in scaling_results:
            regression_detector.update_baseline_if_improved(result)
    
    async def test_memory_leak_performance_validation(self, performance_profiler):
        """Test that critical fixes don't introduce memory leaks affecting performance."""
        logger.info("Running memory leak performance validation")
        
        async def memory_intensive_operations():
            # Simulate operations that could cause memory leaks
            services = []
            
            # Memory optimization service
            memory_service = MemoryOptimizationService()
            await memory_service.start()
            services.append(memory_service)
            
            # WebSocket manager
            websocket_manager = WebSocketManager()
            services.append(websocket_manager)
            
            # Simulate multiple operation cycles
            for cycle in range(10):
                # Create and destroy objects
                for i in range(100):
                    mock_ws = Mock()
                    user_id = f"leak_test_user_{cycle}_{i}"
                    
                    await websocket_manager.connect(mock_ws, user_id)
                    await websocket_manager.send_message(user_id, {"test": f"cycle_{cycle}"})
                    await websocket_manager.disconnect(mock_ws)
                
                # Force garbage collection
                import gc
                gc.collect()
            
            # Cleanup
            await memory_service.stop()
            
            return {"cycles_completed": 10, "operations_per_cycle": 100}
        
        result, perf_data = await performance_profiler.measure_performance_during(
            memory_intensive_operations, "memory_leak_test"
        )
        
        logger.info(f"Memory leak test results:")
        logger.info(f"  Memory growth: {perf_data['memory_growth_mb']:.2f}MB")
        logger.info(f"  Peak memory: {perf_data['max_memory_mb']:.2f}MB")
        logger.info(f"  Duration: {perf_data['operation_duration_ms']:.2f}ms")
        
        # Validate no significant memory leaks
        assert perf_data["memory_growth_mb"] <= 50, \
            f"Excessive memory growth detected: {perf_data['memory_growth_mb']:.2f}MB"
        
        assert perf_data["max_memory_mb"] <= 500, \
            f"Peak memory usage too high: {perf_data['max_memory_mb']:.2f}MB"
        
        # Performance should not degrade significantly due to memory pressure
        operations_per_ms = (result["cycles_completed"] * result["operations_per_cycle"]) / perf_data["operation_duration_ms"]
        assert operations_per_ms >= 0.5, f"Performance degraded due to memory issues: {operations_per_ms:.4f} ops/ms"
    
    async def test_performance_monitoring_alerts(self, benchmark_runner, regression_detector):
        """Test performance monitoring and alerting for critical regressions."""
        logger.info("Testing performance monitoring and alerts")
        
        # Run comprehensive benchmarks
        benchmarks = []
        
        benchmarks.append(await benchmark_runner.benchmark_memory_optimization_performance())
        benchmarks.append(await benchmark_runner.benchmark_websocket_performance(5))
        benchmarks.append(await benchmark_runner.benchmark_database_performance())
        benchmarks.append(await benchmark_runner.benchmark_startup_performance())
        
        # Analyze all benchmarks for regressions
        regression_alerts = []
        
        for benchmark in benchmarks:
            regression = regression_detector.detect_regression(benchmark)
            
            if regression.severity in ["moderate", "critical"]:
                regression_alerts.append({
                    "test_name": regression.test_name,
                    "severity": regression.severity,
                    "performance_delta": regression.performance_delta_percent,
                    "details": regression.details
                })
        
        # Generate performance report
        performance_report = {
            "timestamp": time.time(),
            "total_benchmarks": len(benchmarks),
            "regressions_detected": len(regression_alerts),
            "critical_regressions": len([a for a in regression_alerts if a["severity"] == "critical"]),
            "moderate_regressions": len([a for a in regression_alerts if a["severity"] == "moderate"]),
            "performance_summary": {
                benchmark.test_name: {
                    "duration_ms": benchmark.duration_ms,
                    "throughput": benchmark.throughput,
                    "memory_mb": benchmark.memory_mb
                }
                for benchmark in benchmarks
            },
            "regression_alerts": regression_alerts
        }
        
        logger.info(f"Performance monitoring report:")
        logger.info(f"  Total benchmarks: {performance_report['total_benchmarks']}")
        logger.info(f"  Regressions detected: {performance_report['regressions_detected']}")
        logger.info(f"  Critical regressions: {performance_report['critical_regressions']}")
        
        # Validate monitoring effectiveness
        assert performance_report["total_benchmarks"] >= 4, "Not enough benchmarks for comprehensive monitoring"
        
        # Critical regressions should trigger alerts
        critical_regressions = performance_report["critical_regressions"]
        if critical_regressions > 0:
            logger.error(f"CRITICAL PERFORMANCE ALERT: {critical_regressions} critical regressions detected!")
            for alert in regression_alerts:
                if alert["severity"] == "critical":
                    logger.error(f"  {alert['test_name']}: {alert['performance_delta']:.2f}% regression")
        
        # No critical regressions should be present in production-ready code
        assert critical_regressions == 0, \
            f"CRITICAL performance regressions detected: {critical_regressions}. System not production-ready!"
        
        # Moderate regressions should be limited
        moderate_regressions = performance_report["moderate_regressions"]
        assert moderate_regressions <= 1, \
            f"Too many moderate performance regressions: {moderate_regressions}. Performance optimization needed."