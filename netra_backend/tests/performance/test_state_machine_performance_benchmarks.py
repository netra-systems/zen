"""
State Machine Performance Benchmark Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Performance Infrastructure)
- Business Goal: Ensure state machine operations meet performance SLAs for real-time chat
- Value Impact: Fast state transitions = responsive UI, reduced user wait times, better UX
- Strategic Impact: Performance compliance prevents user abandonment during chat interactions

CRITICAL: These benchmarks validate that state machine operations meet performance
requirements for real-time chat applications where responsiveness directly impacts
user satisfaction and platform adoption.

Performance SLA Requirements:
- State transition: < 1ms (95th percentile)
- Registry operations: < 5ms (99th percentile)  
- Concurrent operations: < 10ms under high load
- Memory usage: < 1MB per 1000 connections

Test Difficulty: EXTREME (Performance tests are inherently flaky)
- Timing-dependent assertions on different hardware
- Concurrent load generation and measurement
- Memory profiling and leak detection
- Statistical analysis of performance distributions

@compliance TEST_CREATION_GUIDE.md - Performance tests with real services
@compliance CLAUDE.md - Business value focused, validates actual performance requirements
"""

import asyncio
import gc
import memory_profiler
import pytest
import psutil
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
import uuid

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine,
    ConnectionStateMachineRegistry,
    get_connection_state_registry
)
from shared.types.core_types import UserID, ConnectionID
from test_framework.base import BaseTestCase
from test_framework.performance_helpers import (
    PerformanceProfiler,
    MemoryTracker,
    ConcurrencyBenchmark,
    StatisticalAnalyzer
)


class StateTransitionPerformanceBenchmark(BaseTestCase):
    """
    Performance benchmark tests for state machine operations.
    
    These tests validate that state transitions meet business SLA requirements
    for responsive chat applications.
    """
    
    def setUp(self):
        """Set up performance testing environment."""
        super().setUp()
        
        # Performance SLA targets (business requirements)
        self.performance_slas = {
            'state_transition_p95_ms': 1.0,      # 95th percentile < 1ms
            'state_transition_p99_ms': 2.0,      # 99th percentile < 2ms
            'registry_operation_p95_ms': 5.0,    # Registry ops < 5ms
            'registry_operation_p99_ms': 10.0,   # Registry ops < 10ms
            'concurrent_operation_p95_ms': 10.0, # Concurrent ops < 10ms
            'memory_per_1000_connections_mb': 1.0, # Memory efficiency
            'cpu_usage_under_load_percent': 50.0  # CPU efficiency
        }
        
        # Test configuration
        self.sample_sizes = {
            'basic_performance': 1000,     # Basic transition tests
            'high_load': 10000,            # High load tests
            'stress_test': 50000,          # Stress testing
            'concurrent_users': 100        # Concurrent user simulation
        }
        
        # Performance tracking
        self.performance_results: Dict[str, List[float]] = {}
        self.memory_measurements: List[Dict[str, Any]] = []
        self.sla_violations: List[Dict[str, Any]] = []
        
        # Clean up for consistent performance measurement
        gc.collect()
    
    def record_performance_sample(self, test_name: str, duration_ms: float):
        """Record a performance sample for statistical analysis."""
        if test_name not in self.performance_results:
            self.performance_results[test_name] = []
        self.performance_results[test_name].append(duration_ms)
    
    def analyze_performance_distribution(self, test_name: str) -> Dict[str, float]:
        """Analyze performance distribution and calculate percentiles."""
        if test_name not in self.performance_results:
            return {}
        
        samples = self.performance_results[test_name]
        if not samples:
            return {}
        
        return {
            'count': len(samples),
            'min_ms': min(samples),
            'max_ms': max(samples),
            'mean_ms': statistics.mean(samples),
            'median_ms': statistics.median(samples),
            'p95_ms': statistics.quantiles(samples, n=20)[18],  # 95th percentile
            'p99_ms': statistics.quantiles(samples, n=100)[98], # 99th percentile
            'stdev_ms': statistics.stdev(samples) if len(samples) > 1 else 0
        }
    
    def check_sla_compliance(self, test_name: str, metrics: Dict[str, float]) -> bool:
        """Check if performance metrics meet SLA requirements."""
        violations = []
        
        # Check state transition SLAs
        if 'state_transition' in test_name:
            if metrics.get('p95_ms', 0) > self.performance_slas['state_transition_p95_ms']:
                violations.append({
                    'sla': 'state_transition_p95_ms',
                    'target': self.performance_slas['state_transition_p95_ms'],
                    'actual': metrics['p95_ms']
                })
            
            if metrics.get('p99_ms', 0) > self.performance_slas['state_transition_p99_ms']:
                violations.append({
                    'sla': 'state_transition_p99_ms',
                    'target': self.performance_slas['state_transition_p99_ms'],
                    'actual': metrics['p99_ms']
                })
        
        # Check registry operation SLAs
        if 'registry' in test_name:
            if metrics.get('p95_ms', 0) > self.performance_slas['registry_operation_p95_ms']:
                violations.append({
                    'sla': 'registry_operation_p95_ms',
                    'target': self.performance_slas['registry_operation_p95_ms'],
                    'actual': metrics['p95_ms']
                })
        
        # Record violations for analysis
        if violations:
            self.sla_violations.extend([{
                'test': test_name,
                'timestamp': time.time(),
                **violation
            } for violation in violations])
        
        return len(violations) == 0

    def test_basic_state_transition_performance(self):
        """
        Benchmark basic state transition performance.
        
        Business requirement: State transitions must complete within 1ms
        to maintain responsive UI during chat interactions.
        """
        test_name = 'basic_state_transition'
        sample_size = self.sample_sizes['basic_performance']
        
        # Create test state machine
        user_id = UserID("perf-test-user")
        connection_id = ConnectionID("perf-test-conn")
        machine = ConnectionStateMachine(connection_id, user_id)
        
        # Warm up JIT compilation and caches
        for _ in range(100):
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "warmup")
            machine.transition_to(ApplicationConnectionState.CONNECTING, "reset")
        
        # Benchmark state transitions
        test_transitions = [
            (ApplicationConnectionState.ACCEPTED, "transport_ready"),
            (ApplicationConnectionState.AUTHENTICATED, "auth_complete"),
            (ApplicationConnectionState.SERVICES_READY, "services_loaded"),
            (ApplicationConnectionState.PROCESSING_READY, "fully_operational"),
            (ApplicationConnectionState.PROCESSING, "message_received"),
            (ApplicationConnectionState.IDLE, "message_processed"),
        ]
        
        # Run performance benchmark
        for i in range(sample_size):
            # Reset to initial state
            machine = ConnectionStateMachine(connection_id, user_id)
            
            for target_state, reason in test_transitions:
                # Measure single transition
                start_time = time.perf_counter()
                success = machine.transition_to(target_state, reason)
                end_time = time.perf_counter()
                
                duration_ms = (end_time - start_time) * 1000
                self.record_performance_sample(test_name, duration_ms)
                
                self.assertTrue(success, f"Transition to {target_state} should succeed")
        
        # Analyze performance
        metrics = self.analyze_performance_distribution(test_name)
        sla_compliant = self.check_sla_compliance(test_name, metrics)
        
        # Business SLA assertions
        self.assertLessEqual(
            metrics['p95_ms'], self.performance_slas['state_transition_p95_ms'],
            f"95th percentile state transition time {metrics['p95_ms']:.3f}ms "
            f"exceeds SLA target of {self.performance_slas['state_transition_p95_ms']}ms"
        )
        
        self.assertLessEqual(
            metrics['p99_ms'], self.performance_slas['state_transition_p99_ms'],
            f"99th percentile state transition time {metrics['p99_ms']:.3f}ms "
            f"exceeds SLA target of {self.performance_slas['state_transition_p99_ms']}ms"
        )
        
        # Record business metrics
        self.record_metric("state_transition_p95_ms", metrics['p95_ms'])
        self.record_metric("state_transition_p99_ms", metrics['p99_ms'])
        self.record_metric("state_transition_mean_ms", metrics['mean_ms'])
        self.record_metric("sla_compliant", sla_compliant)
        self.record_metric("sample_size", metrics['count'])

    def test_registry_operation_performance(self):
        """
        Benchmark connection registry operation performance.
        
        Business requirement: Registry operations must complete within 5ms
        to support rapid connection establishment during user login spikes.
        """
        test_name = 'registry_operations'
        sample_size = self.sample_sizes['basic_performance']
        
        registry = get_connection_state_registry()
        
        # Test operations to benchmark
        operations_to_test = [
            'register_connection',
            'get_connection_state_machine', 
            'get_all_operational_connections',
            'get_registry_stats',
            'unregister_connection'
        ]
        
        for operation_name in operations_to_test:
            operation_samples = []
            
            for i in range(sample_size // len(operations_to_test)):
                user_id = UserID(f"perf-user-{i}")
                connection_id = ConnectionID(f"perf-conn-{i}")
                
                if operation_name == 'register_connection':
                    start_time = time.perf_counter()
                    machine = registry.register_connection(connection_id, user_id)
                    end_time = time.perf_counter()
                    
                elif operation_name == 'get_connection_state_machine':
                    # Pre-register connection
                    registry.register_connection(connection_id, user_id)
                    
                    start_time = time.perf_counter()
                    retrieved = registry.get_connection_state_machine(connection_id)
                    end_time = time.perf_counter()
                    
                    self.assertIsNotNone(retrieved)
                    
                elif operation_name == 'get_all_operational_connections':
                    # Pre-register and make operational
                    machine = registry.register_connection(connection_id, user_id)
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "test")
                    machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "test")
                    machine.transition_to(ApplicationConnectionState.SERVICES_READY, "test")
                    machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "test")
                    
                    start_time = time.perf_counter()
                    operational = registry.get_all_operational_connections()
                    end_time = time.perf_counter()
                    
                elif operation_name == 'get_registry_stats':
                    start_time = time.perf_counter()
                    stats = registry.get_registry_stats()
                    end_time = time.perf_counter()
                    
                    self.assertIsInstance(stats, dict)
                    
                elif operation_name == 'unregister_connection':
                    # Pre-register connection
                    registry.register_connection(connection_id, user_id)
                    
                    start_time = time.perf_counter()
                    success = registry.unregister_connection(connection_id)
                    end_time = time.perf_counter()
                    
                    self.assertTrue(success)
                
                duration_ms = (end_time - start_time) * 1000
                operation_samples.append(duration_ms)
                self.record_performance_sample(f"{test_name}_{operation_name}", duration_ms)
            
            # Clean up connections for this operation
            registry.cleanup_closed_connections()
        
        # Analyze overall registry performance
        all_samples = []
        for operation_name in operations_to_test:
            operation_key = f"{test_name}_{operation_name}"
            if operation_key in self.performance_results:
                all_samples.extend(self.performance_results[operation_key])
        
        if all_samples:
            overall_metrics = {
                'count': len(all_samples),
                'mean_ms': statistics.mean(all_samples),
                'p95_ms': statistics.quantiles(all_samples, n=20)[18] if len(all_samples) >= 20 else max(all_samples),
                'p99_ms': statistics.quantiles(all_samples, n=100)[98] if len(all_samples) >= 100 else max(all_samples),
            }
            
            # SLA compliance check
            sla_compliant = self.check_sla_compliance(test_name, overall_metrics)
            
            # Business assertions
            self.assertLessEqual(
                overall_metrics['p95_ms'], self.performance_slas['registry_operation_p95_ms'],
                f"95th percentile registry operation time {overall_metrics['p95_ms']:.3f}ms "
                f"exceeds SLA target of {self.performance_slas['registry_operation_p95_ms']}ms"
            )
            
            # Record metrics
            self.record_metric("registry_p95_ms", overall_metrics['p95_ms'])
            self.record_metric("registry_p99_ms", overall_metrics['p99_ms'])
            self.record_metric("registry_mean_ms", overall_metrics['mean_ms'])
            self.record_metric("registry_sla_compliant", sla_compliant)

    def test_concurrent_operation_performance(self):
        """
        Benchmark concurrent state machine operation performance.
        
        Business requirement: System must handle concurrent operations from
        multiple users without performance degradation beyond 10ms.
        """
        test_name = 'concurrent_operations'
        concurrent_users = self.sample_sizes['concurrent_users']
        operations_per_user = 20
        
        registry = get_connection_state_registry()
        
        def user_operation_sequence(user_index: int) -> List[float]:
            """Simulate a typical user's state machine operations."""
            user_id = UserID(f"concurrent-user-{user_index}")
            connection_id = ConnectionID(f"concurrent-conn-{user_index}")
            
            operation_times = []
            
            try:
                # Register connection
                start_time = time.perf_counter()
                machine = registry.register_connection(connection_id, user_id)
                operation_times.append((time.perf_counter() - start_time) * 1000)
                
                # Perform state transitions
                transitions = [
                    (ApplicationConnectionState.ACCEPTED, "concurrent_test"),
                    (ApplicationConnectionState.AUTHENTICATED, "concurrent_test"),
                    (ApplicationConnectionState.SERVICES_READY, "concurrent_test"),
                    (ApplicationConnectionState.PROCESSING_READY, "concurrent_test"),
                ]
                
                for target_state, reason in transitions:
                    start_time = time.perf_counter()
                    success = machine.transition_to(target_state, reason)
                    duration = (time.perf_counter() - start_time) * 1000
                    operation_times.append(duration)
                    
                    if not success:
                        operation_times.append(10.0)  # Penalty for failed operations
                
                # Simulate operational activity
                for _ in range(operations_per_user - len(transitions) - 2):
                    start_time = time.perf_counter()
                    _ = machine.can_process_messages()
                    _ = machine.get_metrics()
                    operation_times.append((time.perf_counter() - start_time) * 1000)
                
                # Cleanup
                start_time = time.perf_counter()
                registry.unregister_connection(connection_id)
                operation_times.append((time.perf_counter() - start_time) * 1000)
                
            except Exception as e:
                # Record error as performance penalty
                operation_times.append(100.0)  # 100ms penalty for errors
            
            return operation_times
        
        # Execute concurrent load test
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=min(concurrent_users, 50)) as executor:
            # Submit all user operation sequences
            futures = [
                executor.submit(user_operation_sequence, i) 
                for i in range(concurrent_users)
            ]
            
            # Collect results
            all_operation_times = []
            completed_users = 0
            
            for future in as_completed(futures):
                try:
                    user_times = future.result()
                    all_operation_times.extend(user_times)
                    completed_users += 1
                    
                    # Record samples for analysis
                    for duration in user_times:
                        self.record_performance_sample(test_name, duration)
                        
                except Exception as e:
                    # Handle user sequence failures
                    all_operation_times.extend([50.0] * operations_per_user)  # Penalty times
        
        total_duration = time.perf_counter() - start_time
        
        # Analyze concurrent performance
        metrics = self.analyze_performance_distribution(test_name)
        sla_compliant = self.check_sla_compliance(test_name, metrics)
        
        # Calculate throughput metrics
        total_operations = len(all_operation_times)
        operations_per_second = total_operations / total_duration if total_duration > 0 else 0
        
        # Business performance assertions
        self.assertLessEqual(
            metrics['p95_ms'], self.performance_slas['concurrent_operation_p95_ms'],
            f"95th percentile concurrent operation time {metrics['p95_ms']:.3f}ms "
            f"exceeds SLA target of {self.performance_slas['concurrent_operation_p95_ms']}ms"
        )
        
        self.assertGreaterEqual(
            completed_users / concurrent_users, 0.95,
            f"Concurrent operation success rate {completed_users/concurrent_users:.1%} below 95%"
        )
        
        # Verify throughput meets business requirements
        min_required_ops_per_second = 1000  # Business requirement
        self.assertGreaterEqual(
            operations_per_second, min_required_ops_per_second,
            f"Throughput {operations_per_second:.0f} ops/sec below requirement of {min_required_ops_per_second}"
        )
        
        # Record concurrency metrics
        self.record_metric("concurrent_users", concurrent_users)
        self.record_metric("concurrent_p95_ms", metrics['p95_ms'])
        self.record_metric("concurrent_p99_ms", metrics['p99_ms'])
        self.record_metric("operations_per_second", operations_per_second)
        self.record_metric("concurrent_success_rate", completed_users / concurrent_users)
        self.record_metric("concurrent_sla_compliant", sla_compliant)

    @memory_profiler.profile
    def test_memory_usage_performance(self):
        """
        Benchmark memory usage for state machines under load.
        
        Business requirement: Memory usage must stay under 1MB per 1000 connections
        to support cost-effective scaling and prevent OOM errors.
        """
        test_name = 'memory_usage'
        connection_count = 1000
        
        # Get baseline memory usage
        gc.collect()
        process = psutil.Process()
        baseline_memory_mb = process.memory_info().rss / (1024 * 1024)
        
        registry = get_connection_state_registry()
        state_machines = []
        
        # Create connections and measure memory growth
        memory_samples = [baseline_memory_mb]
        
        for i in range(0, connection_count, 100):  # Sample every 100 connections
            # Create batch of connections
            batch_start = i
            batch_end = min(i + 100, connection_count)
            
            for j in range(batch_start, batch_end):
                user_id = UserID(f"memory-test-user-{j}")
                connection_id = ConnectionID(f"memory-test-conn-{j}")
                
                machine = registry.register_connection(connection_id, user_id)
                
                # Advance to operational state to simulate real usage
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "memory_test")
                machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "memory_test")
                machine.transition_to(ApplicationConnectionState.SERVICES_READY, "memory_test")
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "memory_test")
                
                state_machines.append((connection_id, machine))
            
            # Measure memory after batch
            gc.collect()
            current_memory_mb = process.memory_info().rss / (1024 * 1024)
            memory_samples.append(current_memory_mb)
            
            connections_created = batch_end
            memory_used_mb = current_memory_mb - baseline_memory_mb
            
            self.memory_measurements.append({
                'connections': connections_created,
                'memory_mb': memory_used_mb,
                'memory_per_connection_kb': (memory_used_mb * 1024) / connections_created if connections_created > 0 else 0
            })
        
        # Calculate final memory metrics
        final_memory_mb = memory_samples[-1] - baseline_memory_mb
        memory_per_connection_kb = (final_memory_mb * 1024) / connection_count
        memory_per_1000_connections_mb = memory_per_connection_kb * 1000 / 1024
        
        # Test memory efficiency during operations
        operation_start_memory = process.memory_info().rss / (1024 * 1024)
        
        # Perform operations on all connections
        for connection_id, machine in state_machines[:100]:  # Test subset for performance
            machine.get_metrics()
            machine.can_process_messages()
            machine.transition_to(ApplicationConnectionState.PROCESSING, "memory_test_ops")
            machine.transition_to(ApplicationConnectionState.IDLE, "memory_test_ops")
        
        gc.collect()
        operation_end_memory = process.memory_info().rss / (1024 * 1024)
        operation_memory_growth = operation_end_memory - operation_start_memory
        
        # Cleanup and measure memory recovery
        cleanup_start_memory = process.memory_info().rss / (1024 * 1024)
        
        for connection_id, machine in state_machines:
            machine.transition_to(ApplicationConnectionState.CLOSED, "cleanup")
            registry.unregister_connection(connection_id)
        
        registry.cleanup_closed_connections()
        gc.collect()
        
        cleanup_end_memory = process.memory_info().rss / (1024 * 1024)
        memory_recovered_mb = cleanup_start_memory - cleanup_end_memory
        
        # Business memory efficiency assertions
        self.assertLessEqual(
            memory_per_1000_connections_mb, self.performance_slas['memory_per_1000_connections_mb'],
            f"Memory usage {memory_per_1000_connections_mb:.2f}MB per 1000 connections "
            f"exceeds SLA target of {self.performance_slas['memory_per_1000_connections_mb']}MB"
        )
        
        # Verify no significant memory leaks during operations
        self.assertLessEqual(
            operation_memory_growth, 10.0,  # 10MB max growth during operations
            f"Excessive memory growth {operation_memory_growth:.2f}MB during operations"
        )
        
        # Verify memory recovery after cleanup
        memory_recovery_rate = memory_recovered_mb / final_memory_mb if final_memory_mb > 0 else 0
        self.assertGreaterEqual(
            memory_recovery_rate, 0.8,
            f"Memory recovery rate {memory_recovery_rate:.1%} below 80%, possible memory leak"
        )
        
        # Record memory metrics
        self.record_metric("connections_tested", connection_count)
        self.record_metric("memory_per_1000_connections_mb", memory_per_1000_connections_mb)
        self.record_metric("memory_per_connection_kb", memory_per_connection_kb)
        self.record_metric("operation_memory_growth_mb", operation_memory_growth)
        self.record_metric("memory_recovery_rate", memory_recovery_rate)
        self.record_metric("memory_sla_compliant", memory_per_1000_connections_mb <= self.performance_slas['memory_per_1000_connections_mb'])

    def test_stress_test_performance_limits(self):
        """
        Stress test to find performance limits under extreme load.
        
        This test determines the breaking point where performance degrades
        significantly, helping establish capacity planning guidelines.
        """
        test_name = 'stress_test'
        max_connections = self.sample_sizes['stress_test']
        
        registry = get_connection_state_registry()
        performance_degradation_threshold = 5.0  # 5x slower than baseline
        
        # Establish baseline performance
        baseline_times = []
        for i in range(100):
            user_id = UserID(f"baseline-user-{i}")
            connection_id = ConnectionID(f"baseline-conn-{i}")
            
            start_time = time.perf_counter()
            machine = registry.register_connection(connection_id, user_id)
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "baseline")
            registry.unregister_connection(connection_id)
            end_time = time.perf_counter()
            
            baseline_times.append((end_time - start_time) * 1000)
        
        baseline_mean = statistics.mean(baseline_times)
        degradation_threshold_ms = baseline_mean * performance_degradation_threshold
        
        # Stress test with increasing load
        load_levels = [1000, 5000, 10000, 25000, 50000]
        stress_results = []
        
        for load_level in load_levels:
            if load_level > max_connections:
                break
                
            # Create load
            start_time = time.perf_counter()
            active_connections = []
            
            batch_size = min(1000, load_level)
            operation_times = []
            
            for i in range(0, load_level, batch_size):
                batch_start = time.perf_counter()
                
                batch_connections = []
                for j in range(i, min(i + batch_size, load_level)):
                    user_id = UserID(f"stress-user-{j}")
                    connection_id = ConnectionID(f"stress-conn-{j}")
                    
                    try:
                        machine = registry.register_connection(connection_id, user_id)
                        machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "stress")
                        batch_connections.append((connection_id, machine))
                    except Exception as e:
                        # Record failure time
                        operation_times.append(degradation_threshold_ms * 2)
                
                batch_end = time.perf_counter()
                batch_time_ms = (batch_end - batch_start) * 1000
                avg_operation_time = batch_time_ms / batch_size
                operation_times.append(avg_operation_time)
                
                active_connections.extend(batch_connections)
            
            load_creation_time = time.perf_counter() - start_time
            
            # Test operations under load
            operation_start = time.perf_counter()
            sample_size = min(100, len(active_connections))
            
            for i in range(sample_size):
                connection_id, machine = active_connections[i]
                op_start = time.perf_counter()
                try:
                    machine.can_process_messages()
                    machine.get_metrics()
                except Exception:
                    pass
                op_time = (time.perf_counter() - op_start) * 1000
                operation_times.append(op_time)
            
            operations_time = time.perf_counter() - operation_start
            
            # Cleanup
            cleanup_start = time.perf_counter()
            for connection_id, machine in active_connections:
                try:
                    registry.unregister_connection(connection_id)
                except Exception:
                    pass
            cleanup_time = time.perf_counter() - cleanup_start
            
            # Analyze load level performance
            if operation_times:
                load_mean = statistics.mean(operation_times)
                load_p95 = statistics.quantiles(operation_times, n=20)[18] if len(operation_times) >= 20 else max(operation_times)
                performance_degradation = load_mean / baseline_mean
                
                stress_result = {
                    'load_level': load_level,
                    'mean_operation_ms': load_mean,
                    'p95_operation_ms': load_p95,
                    'performance_degradation_ratio': performance_degradation,
                    'load_creation_time_s': load_creation_time,
                    'operations_time_s': operations_time,
                    'cleanup_time_s': cleanup_time,
                    'degraded_performance': performance_degradation > performance_degradation_threshold
                }
                
                stress_results.append(stress_result)
                
                # Record samples
                for duration in operation_times:
                    self.record_performance_sample(test_name, duration)
                
                # Stop if performance has degraded significantly
                if performance_degradation > performance_degradation_threshold:
                    break
        
        # Analyze stress test results
        if stress_results:
            max_sustainable_load = max(
                result['load_level'] for result in stress_results 
                if not result['degraded_performance']
            )
            
            peak_performance_result = next(
                (result for result in stress_results if result['degraded_performance']), 
                stress_results[-1]
            )
            
            # Business capacity assertions
            min_required_capacity = 10000  # Business requirement: support 10k concurrent connections
            
            self.assertGreaterEqual(
                max_sustainable_load, min_required_capacity,
                f"Maximum sustainable load {max_sustainable_load} below business requirement of {min_required_capacity}"
            )
            
            # Record stress test metrics
            self.record_metric("max_sustainable_load", max_sustainable_load)
            self.record_metric("baseline_performance_ms", baseline_mean)
            self.record_metric("degradation_threshold_ms", degradation_threshold_ms)
            self.record_metric("peak_load_tested", peak_performance_result['load_level'])
            self.record_metric("peak_performance_degradation", peak_performance_result['performance_degradation_ratio'])
            self.record_metric("capacity_requirement_met", max_sustainable_load >= min_required_capacity)
            self.record_metric("stress_results", stress_results)

    def test_performance_regression_detection(self):
        """
        Detect performance regressions by comparing against baseline metrics.
        
        This test helps catch performance regressions in CI/CD pipeline.
        """
        test_name = 'regression_detection'
        
        # Historical baseline (these would come from previous test runs in production)
        historical_baselines = {
            'state_transition_mean_ms': 0.1,
            'registry_operation_mean_ms': 0.5,
            'concurrent_operation_mean_ms': 2.0
        }
        
        # Acceptable regression tolerance (business requirement)
        regression_tolerance = 1.5  # 50% slower than baseline is acceptable
        
        # Run current performance tests
        current_metrics = {}
        
        # Quick state transition test
        user_id = UserID("regression-test-user")
        connection_id = ConnectionID("regression-test-conn")
        machine = ConnectionStateMachine(connection_id, user_id)
        
        transition_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "regression_test")
            machine.transition_to(ApplicationConnectionState.CONNECTING, "reset")  # Reset
            end_time = time.perf_counter()
            
            transition_times.append((end_time - start_time) * 1000)
        
        current_metrics['state_transition_mean_ms'] = statistics.mean(transition_times)
        
        # Quick registry test
        registry = get_connection_state_registry()
        registry_times = []
        
        for i in range(100):
            test_user_id = UserID(f"reg-test-{i}")
            test_conn_id = ConnectionID(f"reg-conn-{i}")
            
            start_time = time.perf_counter()
            registry.register_connection(test_conn_id, test_user_id)
            registry.get_connection_state_machine(test_conn_id)
            registry.unregister_connection(test_conn_id)
            end_time = time.perf_counter()
            
            registry_times.append((end_time - start_time) * 1000)
        
        current_metrics['registry_operation_mean_ms'] = statistics.mean(registry_times)
        
        # Quick concurrent test
        with ThreadPoolExecutor(max_workers=10) as executor:
            concurrent_times = []
            
            def quick_concurrent_test(index):
                start = time.perf_counter()
                user_id = UserID(f"concurrent-{index}")
                conn_id = ConnectionID(f"concurrent-{index}")
                machine = registry.register_connection(conn_id, user_id)
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "concurrent")
                registry.unregister_connection(conn_id)
                return (time.perf_counter() - start) * 1000
            
            futures = [executor.submit(quick_concurrent_test, i) for i in range(50)]
            concurrent_times = [future.result() for future in futures]
        
        current_metrics['concurrent_operation_mean_ms'] = statistics.mean(concurrent_times)
        
        # Check for regressions
        regressions_detected = []
        
        for metric_name, baseline_value in historical_baselines.items():
            current_value = current_metrics.get(metric_name, 0)
            regression_ratio = current_value / baseline_value if baseline_value > 0 else float('inf')
            
            if regression_ratio > regression_tolerance:
                regressions_detected.append({
                    'metric': metric_name,
                    'baseline': baseline_value,
                    'current': current_value,
                    'regression_ratio': regression_ratio,
                    'tolerance': regression_tolerance
                })
        
        # Business regression assertions
        self.assertEqual(
            len(regressions_detected), 0,
            f"Performance regressions detected: {regressions_detected}"
        )
        
        # Record regression metrics
        for metric_name, current_value in current_metrics.items():
            self.record_metric(f"current_{metric_name}", current_value)
            
            baseline_value = historical_baselines.get(metric_name, 0)
            if baseline_value > 0:
                regression_ratio = current_value / baseline_value
                self.record_metric(f"{metric_name}_regression_ratio", regression_ratio)
        
        self.record_metric("regressions_detected", len(regressions_detected))
        self.record_metric("performance_stable", len(regressions_detected) == 0)

    def tearDown(self):
        """Clean up performance test environment and generate summary report."""
        # Generate performance summary
        if self.performance_results:
            summary_report = {
                'test_timestamp': time.time(),
                'performance_slas': self.performance_slas,
                'sla_violations': self.sla_violations,
                'test_results': {}
            }
            
            for test_name, samples in self.performance_results.items():
                if samples:
                    metrics = self.analyze_performance_distribution(test_name)
                    summary_report['test_results'][test_name] = metrics
            
            # Save summary for CI/CD integration
            self.record_metric("performance_summary", summary_report)
            
            # Print summary for debugging
            print("\n" + "="*80)
            print("PERFORMANCE BENCHMARK SUMMARY")
            print("="*80)
            
            for test_name, metrics in summary_report['test_results'].items():
                print(f"\n{test_name.upper()}:")
                print(f"  Samples: {metrics.get('count', 0)}")
                print(f"  Mean: {metrics.get('mean_ms', 0):.3f}ms")
                print(f"  P95: {metrics.get('p95_ms', 0):.3f}ms")
                print(f"  P99: {metrics.get('p99_ms', 0):.3f}ms")
            
            if self.sla_violations:
                print(f"\n⚠️  SLA VIOLATIONS: {len(self.sla_violations)}")
                for violation in self.sla_violations:
                    print(f"  {violation['test']}: {violation['sla']} "
                          f"(target: {violation['target']}, actual: {violation['actual']})")
            else:
                print("\n✅ ALL PERFORMANCE SLAS MET")
        
        super().tearDown()


if __name__ == "__main__":
    # Run specific performance tests
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        pytest.main([
            "test_state_machine_performance_benchmarks.py::StateTransitionPerformanceBenchmark::test_basic_state_transition_performance",
            "-v", "--tb=short"
        ])
    elif len(sys.argv) > 1 and sys.argv[1] == "--stress":
        pytest.main([
            "test_state_machine_performance_benchmarks.py::StateTransitionPerformanceBenchmark::test_stress_test_performance_limits",
            "-v", "--tb=short"
        ])
    elif len(sys.argv) > 1 and sys.argv[1] == "--memory":
        pytest.main([
            "test_state_machine_performance_benchmarks.py::StateTransitionPerformanceBenchmark::test_memory_usage_performance",
            "-v", "--tb=short"
        ])
    else:
        pytest.main([
            "test_state_machine_performance_benchmarks.py",
            "-v", "--tb=short"
        ])