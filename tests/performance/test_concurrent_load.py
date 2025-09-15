"""
Concurrent Load Performance Test Suite - Issue #1200

MISSION CRITICAL: Comprehensive concurrent load testing for multi-user scenarios.
Tests system performance, resource utilization, and scalability under realistic
concurrent user load patterns with strict business SLA requirements.

PURPOSE:
- Tests 5+ concurrent user load testing with performance validation
- Validates resource sharing and system scalability under load
- Tests performance degradation detection with concurrent operations
- Validates system stability and reliability under sustained load
- Measures throughput, latency, and resource utilization patterns

BUSINESS VALUE:
- Protects $500K+ ARR system scalability expectations
- Ensures enterprise-grade multi-user performance under load
- Validates system can handle expected customer concurrent usage
- Tests load balancing and resource allocation effectiveness
- Demonstrates load performance gaps for capacity planning

TESTING APPROACH:
- Uses realistic concurrent user load patterns with staged ramp-up
- Tests sustained load performance over extended durations
- Validates resource utilization and memory management under load
- Monitors system throughput and latency degradation patterns
- Initially designed to FAIL to establish current load handling capabilities
- Uses SSOT testing patterns with real concurrent service validation

GitHub Issue: #1200 Performance Integration Test Creation
Related Issues: #1116 (Factory Performance), #420 (Infrastructure), #762 (WebSocket)
Test Category: performance, load_testing, concurrency, scalability_validation
Expected Runtime: 300-600 seconds for comprehensive load validation
SSOT Integration: Uses SSotAsyncTestCase with real concurrent load testing
"""

import asyncio
import json
import time
import pytest
import psutil
import statistics
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Concurrent Load Performance SLA Requirements
CONCURRENT_LOAD_SLA = {
    # Load Testing SLA
    "min_concurrent_users_supported": 5,           # Minimum 5 concurrent users
    "target_concurrent_users": 10,                 # Target 10 concurrent users
    "max_concurrent_users_tested": 20,             # Test up to 20 concurrent users
    "max_load_test_duration": 300.0,               # Load test within 5 minutes

    # Performance Under Load SLA
    "max_response_degradation_percent": 30.0,      # <30% response time degradation
    "max_throughput_degradation_percent": 25.0,    # <25% throughput degradation
    "max_concurrent_response_time": 90.0,          # Response time <90s under load
    "min_concurrent_success_rate": 92.0,           # 92% success rate under load

    # Resource Utilization SLA
    "max_memory_usage_under_load_mb": 2048,        # Memory usage <2GB under load
    "max_cpu_usage_under_load": 90.0,              # CPU usage <90% under load
    "max_memory_per_concurrent_user_mb": 150,      # Memory per user <150MB
    "max_resource_growth_rate_percent": 15.0,      # Resource growth <15% per additional user

    # Throughput and Latency SLA
    "min_requests_per_second": 2.0,                # Minimum 2 RPS under load
    "max_average_latency_ms": 5000.0,              # Average latency <5s
    "max_p95_latency_ms": 15000.0,                 # P95 latency <15s
    "max_p99_latency_ms": 30000.0,                 # P99 latency <30s

    # System Stability SLA
    "max_error_rate_under_load": 8.0,              # Error rate <8% under load
    "max_timeout_rate_under_load": 5.0,            # Timeout rate <5% under load
    "min_system_availability_percent": 95.0,       # System availability >95%
    "max_connection_failures_percent": 10.0,       # Connection failures <10%

    # Load Ramp-up SLA
    "max_ramp_up_time_per_user": 2.0,              # Ramp-up <2s per user
    "max_steady_state_stabilization": 30.0,        # Steady state within 30s
    "max_ramp_down_time": 15.0,                    # Ramp-down within 15s
}

# Load testing scenarios with progressive difficulty
LOAD_TEST_SCENARIOS = [
    {
        "name": "baseline_single_user_load",
        "description": "Single user baseline load performance",
        "concurrent_users": 1,
        "test_duration": 30,
        "ramp_up_time": 5,
        "operations_per_user": 3,
        "expected_success_rate": 100.0
    },
    {
        "name": "light_concurrent_load",
        "description": "Light concurrent load (5 users)",
        "concurrent_users": 5,
        "test_duration": 60,
        "ramp_up_time": 10,
        "operations_per_user": 2,
        "expected_success_rate": 95.0
    },
    {
        "name": "moderate_concurrent_load",
        "description": "Moderate concurrent load (10 users)",
        "concurrent_users": 10,
        "test_duration": 120,
        "ramp_up_time": 20,
        "operations_per_user": 2,
        "expected_success_rate": 92.0
    },
    {
        "name": "heavy_concurrent_load",
        "description": "Heavy concurrent load (15 users)",
        "concurrent_users": 15,
        "test_duration": 180,
        "ramp_up_time": 30,
        "operations_per_user": 1,
        "expected_success_rate": 88.0
    },
    {
        "name": "stress_concurrent_load",
        "description": "Stress concurrent load (20 users)",
        "concurrent_users": 20,
        "test_duration": 240,
        "ramp_up_time": 40,
        "operations_per_user": 1,
        "expected_success_rate": 80.0
    }
]


@dataclass
class LoadTestMetrics:
    """Container for load test performance metrics."""
    user_count: int
    duration: float
    successful_operations: int
    failed_operations: int
    total_operations: int
    success_rate: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_rps: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    timeout_rate: float
    timestamp: str


class TestConcurrentLoad(SSotAsyncTestCase):
    """
    Concurrent Load Performance Test Suite for Issue #1200

    This test suite validates system performance under various concurrent
    user load conditions with comprehensive metrics and SLA validation.

    CRITICAL: These tests are designed to initially FAIL to establish
    current load handling capabilities and identify performance bottlenecks.
    """

    def setup_method(self, method):
        """Set up load testing infrastructure for each test."""
        super().setup_method(method)
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.baseline_cpu = psutil.cpu_percent(interval=1)
        self.start_time = time.time()

        # Initialize load testing tracking
        self.test_session_id = str(uuid.uuid4())
        self.staging_config = StagingConfig()
        self.auth_client = StagingAuthClient(self.staging_config)

        # Load testing metrics
        self.load_test_results = []
        self.performance_metrics = defaultdict(list)
        self.resource_usage_timeline = deque(maxlen=1000)
        self.operation_latencies = deque(maxlen=10000)
        self.error_events = []

        # Performance tracking data
        self.load_test_data = {
            "test_session_id": self.test_session_id,
            "test_method": method.__name__,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "sla_requirements": CONCURRENT_LOAD_SLA.copy(),
            "load_scenarios": [],
            "metrics_timeline": [],
            "violations": [],
            "resource_monitoring": []
        }

    def teardown_method(self, method):
        """Collect final load testing metrics and validate performance SLAs."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - self.initial_memory

        # Collect comprehensive load test metrics
        self.load_test_data["end_time"] = datetime.now(timezone.utc).isoformat()
        self.load_test_data["total_test_duration"] = total_duration
        self.load_test_data["memory_increase_mb"] = memory_increase
        self.load_test_data["final_memory_mb"] = final_memory
        self.load_test_data["total_operations"] = sum(r.total_operations for r in self.load_test_results)
        self.load_test_data["average_success_rate"] = statistics.mean([r.success_rate for r in self.load_test_results]) if self.load_test_results else 0

        # Log comprehensive load test analysis
        self._log_load_test_analysis()
        super().teardown_method(method)

    def _log_load_test_analysis(self):
        """Log detailed load test analysis results."""
        print(f"\n=== LOAD TEST ANALYSIS: {self.load_test_data['test_method']} ===")
        print(f"Session ID: {self.test_session_id}")
        print(f"Total Duration: {self.load_test_data.get('total_test_duration', 0):.3f}s")

        print(f"\nLOAD TEST METRICS:")
        print(f"  - Total Operations: {self.load_test_data.get('total_operations', 0)}")
        print(f"  - Average Success Rate: {self.load_test_data.get('average_success_rate', 0):.1f}%")
        print(f"  - Memory Increase: {self.load_test_data.get('memory_increase_mb', 0):.1f}MB")

        if self.load_test_results:
            print(f"\nPERFORMANCE BY LOAD LEVEL:")
            for result in self.load_test_results:
                print(f"  - {result.user_count} users: {result.success_rate:.1f}% success, "
                      f"{result.average_response_time:.3f}s avg response, "
                      f"{result.throughput_rps:.2f} RPS")

        if self.load_test_data["violations"]:
            print(f"\nSLA VIOLATIONS:")
            for violation in self.load_test_data["violations"]:
                print(f"  - {violation['type']}: {violation['message']}")

        if self.error_events:
            print(f"\nERROR EVENTS: {len(self.error_events)} total")
            for error in self.error_events[-3:]:  # Show last 3 errors
                print(f"  - {error['type']}: {error['message']}")

    async def _execute_load_test_scenario(self, scenario: Dict[str, Any]) -> LoadTestMetrics:
        """
        Execute a complete load test scenario with ramp-up and monitoring.

        Args:
            scenario: Load test scenario configuration

        Returns:
            LoadTestMetrics with comprehensive performance data
        """
        print(f"\nExecuting load test: {scenario['name']} ({scenario['concurrent_users']} users)")
        scenario_start = time.perf_counter()

        # Initialize scenario tracking
        user_tasks = []
        operation_results = []
        resource_snapshots = []

        # Phase 1: Ramp-up users gradually
        print(f"Phase 1: Ramping up {scenario['concurrent_users']} users over {scenario['ramp_up_time']}s...")
        ramp_up_delay = scenario['ramp_up_time'] / scenario['concurrent_users'] if scenario['concurrent_users'] > 0 else 0

        for user_index in range(scenario['concurrent_users']):
            # Create unique user context
            user_context = {
                "user_id": f"load-test-user-{user_index+1}-{uuid.uuid4().hex[:8]}",
                "session_id": str(uuid.uuid4()),
                "user_index": user_index,
                "scenario": scenario['name'],
                "start_time": datetime.now(timezone.utc).isoformat()
            }

            # Create user load test task
            user_task = asyncio.create_task(
                self._execute_user_load_operations(user_context, scenario)
            )
            user_tasks.append(user_task)

            # Gradual ramp-up delay
            if user_index < scenario['concurrent_users'] - 1:  # No delay for last user
                await asyncio.sleep(ramp_up_delay)

            # Monitor resources during ramp-up
            if user_index % 5 == 0:  # Monitor every 5 users
                resource_snapshot = self._capture_resource_snapshot(f"ramp_up_user_{user_index+1}")
                resource_snapshots.append(resource_snapshot)

        ramp_up_duration = time.perf_counter() - scenario_start
        print(f"Ramp-up completed in {ramp_up_duration:.2f}s")

        # Phase 2: Steady state load execution
        print(f"Phase 2: Steady state execution for {scenario['test_duration']}s...")
        steady_state_start = time.perf_counter()

        # Monitor resources during steady state
        monitoring_task = asyncio.create_task(
            self._monitor_resources_during_load(scenario['test_duration'], resource_snapshots)
        )

        # Wait for all user operations to complete
        try:
            results = await asyncio.gather(*user_tasks, return_exceptions=True)
            steady_state_duration = time.perf_counter() - steady_state_start

            # Stop resource monitoring
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            print(f"❌ LOAD TEST SCENARIO FAILED: {scenario['name']} - {e}")
            monitoring_task.cancel()
            raise

        # Phase 3: Collect and analyze results
        print(f"Phase 3: Analyzing results from {len(results)} users...")
        total_scenario_duration = time.perf_counter() - scenario_start

        # Process user operation results
        successful_operations = 0
        failed_operations = 0
        operation_latencies = []
        error_count = 0
        timeout_count = 0

        for result in results:
            if isinstance(result, Exception):
                failed_operations += 1
                error_count += 1
                self.error_events.append({
                    "type": "user_operation_exception",
                    "message": str(result),
                    "scenario": scenario['name'],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            elif isinstance(result, dict):
                if result.get("success", False):
                    successful_operations += result.get("operations_completed", 1)
                    if "operation_latencies" in result:
                        operation_latencies.extend(result["operation_latencies"])
                else:
                    failed_operations += result.get("operations_failed", 1)
                    if result.get("timeout", False):
                        timeout_count += 1

        total_operations = successful_operations + failed_operations
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0

        # Calculate performance metrics
        avg_response_time = statistics.mean(operation_latencies) if operation_latencies else 0
        p95_response_time = statistics.quantiles(operation_latencies, n=20)[18] if len(operation_latencies) > 20 else avg_response_time
        p99_response_time = statistics.quantiles(operation_latencies, n=100)[98] if len(operation_latencies) > 100 else p95_response_time
        throughput_rps = successful_operations / total_scenario_duration if total_scenario_duration > 0 else 0

        # Resource utilization metrics
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        current_cpu = psutil.cpu_percent(interval=0.1)

        # Error and timeout rates
        error_rate = (error_count / total_operations * 100) if total_operations > 0 else 0
        timeout_rate = (timeout_count / total_operations * 100) if total_operations > 0 else 0

        # Create comprehensive metrics
        metrics = LoadTestMetrics(
            user_count=scenario['concurrent_users'],
            duration=total_scenario_duration,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            total_operations=total_operations,
            success_rate=success_rate,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput_rps=throughput_rps,
            memory_usage_mb=final_memory,
            cpu_usage_percent=current_cpu,
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Store results for analysis
        self.load_test_results.append(metrics)
        self.load_test_data["load_scenarios"].append({
            "scenario": scenario,
            "metrics": metrics.__dict__,
            "resource_snapshots": resource_snapshots[-10:] if resource_snapshots else []  # Last 10 snapshots
        })

        print(f"✅ LOAD TEST COMPLETED: {scenario['name']}")
        print(f"   - Success Rate: {success_rate:.1f}%")
        print(f"   - Avg Response: {avg_response_time:.3f}s")
        print(f"   - Throughput: {throughput_rps:.2f} RPS")
        print(f"   - Memory Usage: {final_memory:.1f}MB")

        return metrics

    async def _execute_user_load_operations(self, user_context: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute load operations for a single user."""
        user_start = time.perf_counter()
        operations_completed = 0
        operations_failed = 0
        operation_latencies = []

        try:
            # Authenticate user
            auth_start = time.perf_counter()
            auth_tokens = await self.auth_client.get_auth_token(
                email=f"{user_context['user_id']}@netrasystems.ai",
                name=f"Load Test User {user_context['user_index']+1}",
                permissions=["user", "chat"]
            )
            auth_duration = time.perf_counter() - auth_start
            operation_latencies.append(auth_duration)

            # Create user execution context using factory method
            user_id_from_auth = auth_tokens.get("user", {}).get("id", user_context["user_id"])
            execution_context = UserExecutionContext.from_request(
                user_id=user_id_from_auth,
                thread_id=f"thread-{user_context['user_index']}-{uuid.uuid4().hex[:8]}",
                run_id=f"run-{user_context['user_index']}-{uuid.uuid4().hex[:8]}",
                request_id=f"req-{user_context['user_index']}-{uuid.uuid4().hex[:8]}"
            )

            # Execute specified number of operations
            for operation_index in range(scenario['operations_per_user']):
                operation_start = time.perf_counter()

                try:
                    # Simulate user operation (WebSocket connection, agent execution, etc.)
                    await self._simulate_user_operation(user_context, operation_index)

                    operation_duration = time.perf_counter() - operation_start
                    operation_latencies.append(operation_duration)
                    operations_completed += 1

                except asyncio.TimeoutError:
                    operation_duration = time.perf_counter() - operation_start
                    operation_latencies.append(operation_duration)
                    operations_failed += 1

                except Exception as e:
                    operation_duration = time.perf_counter() - operation_start
                    operation_latencies.append(operation_duration)
                    operations_failed += 1

                # Brief delay between operations
                await asyncio.sleep(0.1)

            total_user_duration = time.perf_counter() - user_start

            return {
                "user_id": user_context["user_id"],
                "user_index": user_context["user_index"],
                "duration": total_user_duration,
                "operations_completed": operations_completed,
                "operations_failed": operations_failed,
                "operation_latencies": operation_latencies,
                "auth_tokens": {"user_id": auth_tokens.get("user", {}).get("id", f"test-user-{user_context['user_index']}")},
                "execution_context": execution_context,
                "success": operations_completed > 0,
                "timeout": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            total_user_duration = time.perf_counter() - user_start
            return {
                "user_id": user_context["user_id"],
                "user_index": user_context["user_index"],
                "duration": total_user_duration,
                "operations_completed": operations_completed,
                "operations_failed": operations_failed + 1,
                "operation_latencies": operation_latencies,
                "success": False,
                "timeout": isinstance(e, asyncio.TimeoutError),
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _simulate_user_operation(self, user_context: Dict[str, Any], operation_index: int):
        """Simulate a realistic user operation with potential for timeout or failure."""
        # Simulate WebSocket connection
        await asyncio.sleep(0.1)  # Connection time

        # Simulate message sending
        await asyncio.sleep(0.05)  # Message send time

        # Simulate agent processing
        processing_time = 0.5 + (operation_index * 0.1)  # Progressive load
        await asyncio.sleep(processing_time)

        # Simulate response delivery
        await asyncio.sleep(0.05)  # Response delivery time

    def _capture_resource_snapshot(self, context: str) -> Dict[str, Any]:
        """Capture current system resource snapshot."""
        return {
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "available_memory_mb": psutil.virtual_memory().available / 1024 / 1024
        }

    async def _monitor_resources_during_load(self, duration: float, snapshots: List[Dict[str, Any]]):
        """Monitor system resources during load test execution."""
        monitoring_start = time.perf_counter()
        monitoring_interval = min(5.0, duration / 10)  # Monitor at least 10 times during test

        while (time.perf_counter() - monitoring_start) < duration:
            try:
                snapshot = self._capture_resource_snapshot("steady_state_monitoring")
                snapshots.append(snapshot)

                # Add to timeline for analysis
                self.resource_usage_timeline.append(snapshot)

                await asyncio.sleep(monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                await asyncio.sleep(monitoring_interval)

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.load_testing
    async def test_progressive_concurrent_load_performance(self):
        """
        Test progressive concurrent load performance with multiple user levels.

        Executes load tests starting from single user baseline through moderate
        concurrent load levels, validating performance degradation patterns.

        DESIGNED TO FAIL INITIALLY: Establishes current load handling baselines.
        """
        print(f"\n=== TESTING PROGRESSIVE CONCURRENT LOAD PERFORMANCE ===")

        # Execute progressive load scenarios
        baseline_metrics = None
        for scenario in LOAD_TEST_SCENARIOS[:3]:  # First 3 scenarios: 1, 5, 10 users
            print(f"\nExecuting scenario: {scenario['name']}")

            metrics = await self._execute_load_test_scenario(scenario)

            # Validate individual scenario SLAs
            if scenario['concurrent_users'] == 1:
                baseline_metrics = metrics
                # Single user baseline should have high performance
                assert metrics.success_rate >= 95.0, (
                    f"BASELINE SLA VIOLATION: {metrics.success_rate:.1f}% < 95% success rate"
                )
                assert metrics.average_response_time < 30.0, (
                    f"BASELINE RESPONSE TIME VIOLATION: {metrics.average_response_time:.3f}s > 30s"
                )
            else:
                # Validate concurrent load against baseline
                if baseline_metrics:
                    response_degradation = ((metrics.average_response_time - baseline_metrics.average_response_time) / baseline_metrics.average_response_time) * 100

                    assert response_degradation <= CONCURRENT_LOAD_SLA["max_response_degradation_percent"], (
                        f"RESPONSE DEGRADATION SLA VIOLATION: {response_degradation:.1f}% > "
                        f"{CONCURRENT_LOAD_SLA['max_response_degradation_percent']}% for {scenario['concurrent_users']} users"
                    )

                # Validate concurrent performance SLAs
                assert metrics.success_rate >= scenario.get('expected_success_rate', 90.0), (
                    f"CONCURRENT SUCCESS RATE VIOLATION: {metrics.success_rate:.1f}% < "
                    f"{scenario.get('expected_success_rate', 90.0)}% for {scenario['concurrent_users']} users"
                )

                assert metrics.average_response_time < CONCURRENT_LOAD_SLA["max_concurrent_response_time"], (
                    f"CONCURRENT RESPONSE TIME VIOLATION: {metrics.average_response_time:.3f}s > "
                    f"{CONCURRENT_LOAD_SLA['max_concurrent_response_time']}s for {scenario['concurrent_users']} users"
                )

        print(f"✅ PROGRESSIVE LOAD TEST COMPLETED: {len(self.load_test_results)} scenarios executed")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.load_testing
    async def test_resource_utilization_under_concurrent_load(self):
        """
        Test system resource utilization under concurrent load conditions.

        Validates memory usage, CPU utilization, and resource growth patterns
        under progressive concurrent load with strict resource limits.

        DESIGNED TO FAIL INITIALLY: Establishes current resource utilization patterns.
        """
        print(f"\n=== TESTING RESOURCE UTILIZATION UNDER CONCURRENT LOAD ===")

        # Test moderate concurrent load with detailed resource monitoring
        scenario = LOAD_TEST_SCENARIOS[2]  # 10 concurrent users
        print(f"Testing resource utilization with {scenario['concurrent_users']} concurrent users...")

        # Capture baseline resources
        baseline_snapshot = self._capture_resource_snapshot("pre_load_baseline")
        baseline_memory = baseline_snapshot["memory_mb"]
        baseline_cpu = baseline_snapshot["cpu_percent"]

        # Execute load test with intensive resource monitoring
        metrics = await self._execute_load_test_scenario(scenario)

        # Analyze resource utilization
        peak_memory = max([s["memory_mb"] for s in self.resource_usage_timeline], default=baseline_memory)
        avg_memory = statistics.mean([s["memory_mb"] for s in self.resource_usage_timeline]) if self.resource_usage_timeline else baseline_memory
        avg_cpu = statistics.mean([s["cpu_percent"] for s in self.resource_usage_timeline]) if self.resource_usage_timeline else baseline_cpu

        memory_increase = peak_memory - baseline_memory
        memory_per_user = memory_increase / scenario['concurrent_users'] if scenario['concurrent_users'] > 0 else 0

        print(f"RESOURCE UTILIZATION ANALYSIS:")
        print(f"  - Baseline Memory: {baseline_memory:.1f}MB")
        print(f"  - Peak Memory: {peak_memory:.1f}MB")
        print(f"  - Memory Increase: {memory_increase:.1f}MB")
        print(f"  - Memory Per User: {memory_per_user:.1f}MB")
        print(f"  - Average CPU: {avg_cpu:.1f}%")

        # Validate resource utilization SLAs
        assert peak_memory < CONCURRENT_LOAD_SLA["max_memory_usage_under_load_mb"], (
            f"MEMORY USAGE SLA VIOLATION: {peak_memory:.1f}MB > "
            f"{CONCURRENT_LOAD_SLA['max_memory_usage_under_load_mb']}MB under {scenario['concurrent_users']} user load"
        )

        assert avg_cpu < CONCURRENT_LOAD_SLA["max_cpu_usage_under_load"], (
            f"CPU USAGE SLA VIOLATION: {avg_cpu:.1f}% > "
            f"{CONCURRENT_LOAD_SLA['max_cpu_usage_under_load']}% under {scenario['concurrent_users']} user load"
        )

        assert memory_per_user < CONCURRENT_LOAD_SLA["max_memory_per_concurrent_user_mb"], (
            f"MEMORY PER USER SLA VIOLATION: {memory_per_user:.1f}MB > "
            f"{CONCURRENT_LOAD_SLA['max_memory_per_concurrent_user_mb']}MB per concurrent user"
        )

        print(f"✅ RESOURCE UTILIZATION TEST COMPLETED: Memory and CPU within limits")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.load_testing
    async def test_throughput_and_latency_under_load(self):
        """
        Test system throughput and latency performance under concurrent load.

        Validates request throughput, response latency distribution, and
        performance consistency under sustained concurrent operations.

        DESIGNED TO FAIL INITIALLY: Establishes current throughput and latency baselines.
        """
        print(f"\n=== TESTING THROUGHPUT AND LATENCY UNDER LOAD ===")

        # Test with moderate concurrent load for throughput analysis
        scenario = LOAD_TEST_SCENARIOS[2]  # 10 concurrent users
        scenario_extended = scenario.copy()
        scenario_extended["test_duration"] = 90  # Extended duration for throughput analysis

        print(f"Testing throughput and latency with {scenario['concurrent_users']} concurrent users for {scenario_extended['test_duration']}s...")

        metrics = await self._execute_load_test_scenario(scenario_extended)

        print(f"THROUGHPUT AND LATENCY ANALYSIS:")
        print(f"  - Throughput: {metrics.throughput_rps:.2f} RPS")
        print(f"  - Average Latency: {metrics.average_response_time:.3f}s ({metrics.average_response_time * 1000:.1f}ms)")
        print(f"  - P95 Latency: {metrics.p95_response_time:.3f}s ({metrics.p95_response_time * 1000:.1f}ms)")
        print(f"  - P99 Latency: {metrics.p99_response_time:.3f}s ({metrics.p99_response_time * 1000:.1f}ms)")

        # Validate throughput SLAs
        assert metrics.throughput_rps >= CONCURRENT_LOAD_SLA["min_requests_per_second"], (
            f"THROUGHPUT SLA VIOLATION: {metrics.throughput_rps:.2f} RPS < "
            f"{CONCURRENT_LOAD_SLA['min_requests_per_second']} RPS minimum under {scenario['concurrent_users']} user load"
        )

        # Validate latency SLAs (convert to milliseconds)
        avg_latency_ms = metrics.average_response_time * 1000
        p95_latency_ms = metrics.p95_response_time * 1000
        p99_latency_ms = metrics.p99_response_time * 1000

        assert avg_latency_ms <= CONCURRENT_LOAD_SLA["max_average_latency_ms"], (
            f"AVERAGE LATENCY SLA VIOLATION: {avg_latency_ms:.1f}ms > "
            f"{CONCURRENT_LOAD_SLA['max_average_latency_ms']}ms under {scenario['concurrent_users']} user load"
        )

        assert p95_latency_ms <= CONCURRENT_LOAD_SLA["max_p95_latency_ms"], (
            f"P95 LATENCY SLA VIOLATION: {p95_latency_ms:.1f}ms > "
            f"{CONCURRENT_LOAD_SLA['max_p95_latency_ms']}ms under {scenario['concurrent_users']} user load"
        )

        assert p99_latency_ms <= CONCURRENT_LOAD_SLA["max_p99_latency_ms"], (
            f"P99 LATENCY SLA VIOLATION: {p99_latency_ms:.1f}ms > "
            f"{CONCURRENT_LOAD_SLA['max_p99_latency_ms']}ms under {scenario['concurrent_users']} user load"
        )

        print(f"✅ THROUGHPUT AND LATENCY TEST COMPLETED: Performance within SLA limits")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.load_testing
    async def test_high_concurrency_stress_load_limits(self):
        """
        Test system behavior under maximum expected concurrent load.

        Validates system stability, error handling, and graceful degradation
        under stress-level concurrent user loads.

        DESIGNED TO FAIL INITIALLY: Establishes system breaking points and limits.
        """
        print(f"\n=== TESTING HIGH CONCURRENCY STRESS LOAD LIMITS ===")

        # Execute stress-level concurrent load
        stress_scenario = LOAD_TEST_SCENARIOS[4]  # 20 concurrent users
        print(f"Testing stress load with {stress_scenario['concurrent_users']} concurrent users...")

        metrics = await self._execute_load_test_scenario(stress_scenario)

        print(f"STRESS LOAD ANALYSIS:")
        print(f"  - Concurrent Users: {stress_scenario['concurrent_users']}")
        print(f"  - Success Rate: {metrics.success_rate:.1f}%")
        print(f"  - Error Rate: {metrics.error_rate:.1f}%")
        print(f"  - Timeout Rate: {metrics.timeout_rate:.1f}%")
        print(f"  - Throughput: {metrics.throughput_rps:.2f} RPS")
        print(f"  - Average Response: {metrics.average_response_time:.3f}s")

        # Validate stress load tolerance SLAs
        assert metrics.success_rate >= stress_scenario.get('expected_success_rate', 80.0), (
            f"STRESS LOAD SUCCESS RATE VIOLATION: {metrics.success_rate:.1f}% < "
            f"{stress_scenario.get('expected_success_rate', 80.0)}% under {stress_scenario['concurrent_users']} user stress load"
        )

        assert metrics.error_rate <= CONCURRENT_LOAD_SLA["max_error_rate_under_load"], (
            f"STRESS LOAD ERROR RATE VIOLATION: {metrics.error_rate:.1f}% > "
            f"{CONCURRENT_LOAD_SLA['max_error_rate_under_load']}% under {stress_scenario['concurrent_users']} user stress load"
        )

        assert metrics.timeout_rate <= CONCURRENT_LOAD_SLA["max_timeout_rate_under_load"], (
            f"STRESS LOAD TIMEOUT RATE VIOLATION: {metrics.timeout_rate:.1f}% > "
            f"{CONCURRENT_LOAD_SLA['max_timeout_rate_under_load']}% under {stress_scenario['concurrent_users']} user stress load"
        )

        # Calculate system availability
        system_availability = 100.0 - (metrics.error_rate + metrics.timeout_rate)
        assert system_availability >= CONCURRENT_LOAD_SLA["min_system_availability_percent"], (
            f"SYSTEM AVAILABILITY SLA VIOLATION: {system_availability:.1f}% < "
            f"{CONCURRENT_LOAD_SLA['min_system_availability_percent']}% under {stress_scenario['concurrent_users']} user stress load"
        )

        print(f"✅ STRESS LOAD TEST COMPLETED: System stability maintained under {stress_scenario['concurrent_users']} user load")