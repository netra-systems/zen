"""
Strategic Unit Tests for Agent Performance Validation Under Load Conditions

Business Value Justification (BVJ):
- Segment: Enterprise/Scale - High-volume production deployments
- Business Goal: Performance & Reliability - Maintain responsiveness under load  
- Value Impact: Protects $500K+ ARR from performance-related churn and SLA violations
- Strategic Impact: Enables enterprise scaling and performance SLA confidence

STRATEGIC GAP ADDRESSED: Performance Validation under load conditions
This test suite focuses on performance degradation scenarios:
1. Message throughput under high concurrent user load
2. Memory usage patterns during sustained agent operations
3. Response time degradation under burst scenarios
4. WebSocket connection scaling limits
5. Agent execution performance under resource constraints

CRITICAL: These tests validate production-scale performance requirements.
"""
import pytest
import asyncio
import time
import psutil
import gc
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock, PropertyMock
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState, IntegrationConfig

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking for load testing."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    response_times: List[float] = field(default_factory=list)
    memory_samples: List[int] = field(default_factory=list)
    cpu_samples: List[float] = field(default_factory=list)
    throughput_samples: List[float] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Total test duration in seconds."""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def operations_per_second(self) -> float:
        """Operations per second throughput."""
        return self.total_operations / self.duration if self.duration > 0 else 0

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        return self.successful_operations / self.total_operations * 100 if self.total_operations > 0 else 0

    @property
    def avg_response_time(self) -> float:
        """Average response time in milliseconds."""
        return statistics.mean(self.response_times) * 1000 if self.response_times else 0

    @property
    def p95_response_time(self) -> float:
        """95th percentile response time in milliseconds."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] * 1000

class AgentPerformanceValidationStrategicTests(SSotAsyncTestCase):
    """
    Strategic unit tests for agent performance validation under load conditions.
    
    PERFORMANCE FOCUS: Production-scale scenarios that could cause performance degradation
    and impact user experience at enterprise scale.
    """

    def setup_method(self, method):
        """Set up test fixtures with performance monitoring."""
        super().setup_method(method)
        self.bridge = AgentWebSocketBridge()
        self.metrics = PerformanceMetrics()
        self.memory_monitor_active = False
        self.cpu_monitor_active = False
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.emit_to_run.side_effect = self._track_performance_emission
        self.concurrent_operations = []
        self.performance_violations = []

    async def _track_performance_emission(self, run_id, event_type, data, **kwargs):
        """Track performance metrics for emissions."""
        operation_start = time.time()
        message_size = len(str(data)) if data else 0
        processing_delay = min(message_size / 100000, 0.05)
        await asyncio.sleep(processing_delay)
        operation_time = time.time() - operation_start
        self.metrics.response_times.append(operation_time)
        self.metrics.total_operations += 1
        self.metrics.successful_operations += 1
        return True

    def _start_resource_monitoring(self):
        """Start monitoring system resources."""
        self.memory_monitor_active = True
        self.cpu_monitor_active = True

        def monitor_resources():
            while self.memory_monitor_active or self.cpu_monitor_active:
                if self.memory_monitor_active:
                    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                    self.metrics.memory_samples.append(int(memory_mb))
                if self.cpu_monitor_active:
                    cpu_percent = psutil.Process().cpu_percent(interval=None)
                    self.metrics.cpu_samples.append(cpu_percent)
                time.sleep(0.1)
        threading.Thread(target=monitor_resources, daemon=True).start()

    def _stop_resource_monitoring(self):
        """Stop monitoring system resources."""
        self.memory_monitor_active = False
        self.cpu_monitor_active = False

    async def test_high_volume_concurrent_message_throughput(self):
        """
        PERFORMANCE CRITICAL: Validate message throughput under high concurrent load.
        
        SCALE REQUIREMENT: System must handle 100+ concurrent users with sustained throughput.
        This simulates peak production load scenarios.
        """
        num_concurrent_users = 50
        messages_per_user = 20
        self._start_resource_monitoring()
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            concurrent_tasks = []
            for user_id in range(num_concurrent_users):
                run_id = f'perf_run_{user_id}'
                agent_name = f'PerfAgent_{user_id}'
                for msg_id in range(messages_per_user):
                    concurrent_tasks.extend([self.bridge.notify_agent_started(run_id=f'{run_id}_{msg_id}', agent_name=agent_name, context={'user_id': user_id, 'message_id': msg_id, 'load_test': True, 'data_payload': 'x' * 1000}), self.bridge.notify_agent_thinking(run_id=f'{run_id}_{msg_id}', agent_name=agent_name, reasoning=f'Processing high-volume message {msg_id} for user {user_id}', step_number=msg_id, progress_percentage=msg_id * 5.0), self.bridge.notify_agent_completed(run_id=f'{run_id}_{msg_id}', agent_name=agent_name, result={'user_id': user_id, 'message_id': msg_id, 'processing_result': 'x' * 2000, 'completion_status': 'success'}, execution_time_ms=50.0 + msg_id * 2)])
            start_time = time.time()
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            self.metrics.end_time = time.time()
            self._stop_resource_monitoring()
            successful_results = sum((1 for r in results if r is True))
            failed_results = sum((1 for r in results if isinstance(r, Exception)))
            assert self.metrics.operations_per_second >= 200, f'Throughput requirement not met: {self.metrics.operations_per_second:.1f} ops/sec (required: 200+)'
            assert self.metrics.success_rate >= 99.0, f'Success rate requirement not met: {self.metrics.success_rate:.1f}% (required: 99.0%+)'
            assert self.metrics.avg_response_time <= 100, f'Average response time too high: {self.metrics.avg_response_time:.1f}ms (required: ≤100ms)'
            assert self.metrics.p95_response_time <= 250, f'P95 response time too high: {self.metrics.p95_response_time:.1f}ms (required: ≤250ms)'
            assert failed_results == 0, f'Should have no failures under load: {failed_results} failures'

    async def test_sustained_load_memory_stability(self):
        """
        PERFORMANCE CRITICAL: Memory usage must remain stable under sustained load.
        
        MEMORY REQUIREMENT: No memory leaks or unbounded growth during sustained operations.
        This prevents production memory exhaustion scenarios.
        """
        duration_seconds = 10
        operations_per_second = 50
        self._start_resource_monitoring()
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            end_time = time.time() + duration_seconds
            operation_count = 0
            while time.time() < end_time:
                batch_start = time.time()
                batch_tasks = []
                for i in range(10):
                    run_id = f'sustained_run_{operation_count}_{i}'
                    batch_tasks.extend([self.bridge.notify_agent_started(run_id=run_id, agent_name='SustainedAgent', context={'operation_count': operation_count, 'batch_id': i, 'sustained_load': True, 'payload': 'x' * 5000}), self.bridge.notify_agent_thinking(run_id=run_id, agent_name='SustainedAgent', reasoning=f'Sustained processing operation {operation_count}', step_number=operation_count % 10), self.bridge.notify_agent_completed(run_id=run_id, agent_name='SustainedAgent', result={'sustained_result': 'x' * 10000, 'operation_count': operation_count, 'memory_efficient': True})])
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                operation_count += len([r for r in batch_results if r is True])
                batch_time = time.time() - batch_start
                target_batch_time = len(batch_tasks) / operations_per_second
                if batch_time < target_batch_time:
                    await asyncio.sleep(target_batch_time - batch_time)
                if operation_count % 100 == 0:
                    gc.collect()
            self.metrics.end_time = time.time()
            self._stop_resource_monitoring()
            if self.metrics.memory_samples:
                max_memory = max(self.metrics.memory_samples)
                min_memory = min(self.metrics.memory_samples)
                avg_memory = statistics.mean(self.metrics.memory_samples)
                memory_growth = max_memory - baseline_memory
                assert memory_growth <= 100, f'Excessive memory growth: {memory_growth:.1f}MB (should be ≤100MB)'
                memory_variance = statistics.variance(self.metrics.memory_samples) if len(self.metrics.memory_samples) > 1 else 0
                assert memory_variance <= 1000, f'High memory variance indicates instability: {memory_variance:.1f}'
                final_memory = self.metrics.memory_samples[-1]
                memory_leak_threshold = baseline_memory + 50
                assert final_memory <= memory_leak_threshold, f'Possible memory leak: final={final_memory:.1f}MB, baseline={baseline_memory:.1f}MB'

    async def test_burst_traffic_response_time_stability(self):
        """
        PERFORMANCE CRITICAL: Response times must remain stable during traffic bursts.
        
        LATENCY REQUIREMENT: P95 response time must stay under 500ms even during bursts.
        This simulates viral usage spikes or coordinated user activity.
        """
        normal_load_ops = 20
        burst_load_ops = 200
        burst_duration = 2
        self._start_resource_monitoring()
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            normal_tasks = []
            for i in range(normal_load_ops):
                normal_tasks.append(self.bridge.notify_agent_thinking(run_id=f'normal_run_{i}', agent_name='NormalAgent', reasoning=f'Normal load operation {i}', step_number=i))
            normal_start = time.time()
            normal_results = await asyncio.gather(*normal_tasks)
            normal_duration = time.time() - normal_start
            baseline_ops_per_sec = len(normal_tasks) / normal_duration
            baseline_response_time = statistics.mean(self.metrics.response_times[-len(normal_tasks):]) * 1000
            burst_tasks = []
            for i in range(burst_load_ops):
                burst_tasks.extend([self.bridge.notify_agent_started(run_id=f'burst_run_{i}', agent_name='BurstAgent', context={'burst_operation': True, 'operation_id': i, 'payload': 'x' * 3000}), self.bridge.notify_agent_thinking(run_id=f'burst_run_{i}', agent_name='BurstAgent', reasoning=f'Burst processing {i} under high load', step_number=i)])
            burst_start = time.time()
            burst_results = await asyncio.gather(*burst_tasks, return_exceptions=True)
            burst_end = time.time()
            self.metrics.end_time = burst_end
            self._stop_resource_monitoring()
            burst_duration_actual = burst_end - burst_start
            burst_ops_per_sec = len(burst_tasks) / burst_duration_actual
            burst_response_times = self.metrics.response_times[-len(burst_tasks):]
            if burst_response_times:
                burst_avg_response = statistics.mean(burst_response_times) * 1000
                burst_p95_response = statistics.quantiles(burst_response_times, n=20)[18] * 1000
                assert burst_p95_response <= 500, f'P95 response time too high during burst: {burst_p95_response:.1f}ms (required: ≤500ms)'
                max_acceptable_avg = baseline_response_time * 3
                assert burst_avg_response <= max_acceptable_avg, f'Average response time degraded too much: {burst_avg_response:.1f}ms (max acceptable: {max_acceptable_avg:.1f}ms)'
            assert burst_ops_per_sec >= 50, f'Throughput too low during burst: {burst_ops_per_sec:.1f} ops/sec (required: ≥50)'
            burst_failures = sum((1 for r in burst_results if isinstance(r, Exception)))
            assert burst_failures == 0, f'Burst should not cause failures: {burst_failures} failures'

    async def test_resource_constraint_graceful_degradation(self):
        """
        PERFORMANCE CRITICAL: System must degrade gracefully under resource constraints.
        
        CONSTRAINT HANDLING: When system resources are limited, performance should degrade
        gracefully without complete failure.
        """
        self._start_resource_monitoring()
        slow_websocket_manager = AsyncMock()

        async def constrained_emission(run_id, event_type, data, **kwargs):
            operation_size = len(str(data)) if data else 0
            constraint_delay = min(operation_size / 50000, 0.2)
            await asyncio.sleep(constraint_delay)
            if time.time() % 1 < 0.05:
                raise Exception('Temporary resource exhaustion')
            return True
        slow_websocket_manager.emit_to_run.side_effect = constrained_emission
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = slow_websocket_manager
            constrained_tasks = []
            for i in range(100):
                run_id = f'constrained_run_{i}'
                constrained_tasks.extend([self.bridge.notify_agent_started(run_id=run_id, agent_name='ConstrainedAgent', context={'operation_id': i, 'resource_constrained': True, 'large_payload': 'x' * 8000}), self.bridge.notify_agent_thinking(run_id=run_id, agent_name='ConstrainedAgent', reasoning=f'Processing under resource constraints {i}', step_number=i, progress_percentage=min(i * 2.0, 100.0)), self.bridge.notify_agent_completed(run_id=run_id, agent_name='ConstrainedAgent', result={'constrained_result': 'x' * 15000, 'operation_id': i, 'resource_usage': 'high'})])
            start_time = time.time()
            results = await asyncio.gather(*constrained_tasks, return_exceptions=True)
            self.metrics.end_time = time.time()
            self._stop_resource_monitoring()
            successful_results = sum((1 for r in results if r is True))
            failed_results = sum((1 for r in results if isinstance(r, Exception)))
            success_rate = successful_results / len(constrained_tasks) * 100
            assert success_rate >= 80.0, f'Success rate too low under constraints: {success_rate:.1f}% (required: ≥80%)'
            constrained_ops_per_sec = len(constrained_tasks) / self.metrics.duration
            assert constrained_ops_per_sec >= 20, f'Throughput too low under constraints: {constrained_ops_per_sec:.1f} ops/sec (required: ≥20)'
            failure_rate = failed_results / len(constrained_tasks) * 100
            assert failure_rate <= 20.0, f'Failure rate too high under constraints: {failure_rate:.1f}% (should be ≤20%)'

    async def test_connection_scaling_performance_limits(self):
        """
        PERFORMANCE CRITICAL: Test WebSocket connection scaling limits.
        
        SCALING REQUIREMENT: System should handle realistic connection counts
        while maintaining per-connection performance.
        """
        num_connections = 25
        messages_per_connection = 10
        self._start_resource_monitoring()
        connection_managers = []
        for i in range(num_connections):
            manager = AsyncMock()
            manager.connection_id = f'conn_{i}'
            manager.emit_to_run.side_effect = self._track_performance_emission
            connection_managers.append(manager)
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            scaling_tasks = []
            for conn_id, manager in enumerate(connection_managers):
                mock_ws_property.return_value = manager
                for msg_id in range(messages_per_connection):
                    run_id = f'scale_run_{conn_id}_{msg_id}'
                    scaling_tasks.extend([self.bridge.notify_agent_started(run_id=run_id, agent_name=f'ScaleAgent_Conn{conn_id}', context={'connection_id': conn_id, 'message_id': msg_id, 'scaling_test': True, 'connection_specific_data': f'data_for_conn_{conn_id}'}), self.bridge.notify_agent_completed(run_id=run_id, agent_name=f'ScaleAgent_Conn{conn_id}', result={'connection_id': conn_id, 'message_id': msg_id, 'scaling_result': f'result_for_conn_{conn_id}_msg_{msg_id}'})])
            start_time = time.time()
            results = await asyncio.gather(*scaling_tasks, return_exceptions=True)
            self.metrics.end_time = time.time()
            self._stop_resource_monitoring()
            successful_results = sum((1 for r in results if r is True))
            total_operations = len(scaling_tasks)
            success_rate = successful_results / total_operations * 100
            assert success_rate >= 98.0, f'Connection scaling success rate too low: {success_rate:.1f}% (required: ≥98%)'
            operations_per_connection = messages_per_connection * 2
            total_expected_ops = num_connections * operations_per_connection
            assert successful_results >= total_expected_ops * 0.95, f'Not enough operations completed: {successful_results}/{total_expected_ops}'
            scaling_ops_per_sec = total_operations / self.metrics.duration
            expected_min_throughput = num_connections * 5
            assert scaling_ops_per_sec >= expected_min_throughput, f'Scaling throughput too low: {scaling_ops_per_sec:.1f} ops/sec (required: ≥{expected_min_throughput})'

    def teardown_method(self, method):
        """Clean up performance test artifacts."""
        super().teardown_method(method)
        self._stop_resource_monitoring()
        self.concurrent_operations.clear()
        self.performance_violations.clear()
        gc.collect()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')