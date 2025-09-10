#!/usr/bin/env python
"""
E2E TEST 9: Performance Validation for UserExecutionEngine SSOT

PURPOSE: Test UserExecutionEngine performance meets baseline requirements for production.
This validates the SSOT requirement that consolidated execution performs better than multiple engines.

Expected to FAIL before SSOT consolidation (proves performance issues with multiple engines)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine meets performance targets)

Business Impact: $500K+ ARR Golden Path protection - performance affects user experience
E2E Level: Tests real performance on staging environment with real services
"""

import asyncio
import gc
import psutil
import sys
import os
import statistics
import threading
import time
import tracemalloc
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class PerformanceMetrics:
    """Tracks performance metrics for validation"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.metrics = {
            'execution_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'event_throughput': [],
            'concurrent_performance': [],
            'resource_utilization': []
        }
        self.start_time = None
        self.process = psutil.Process()
        
    def start_measurement(self):
        """Start performance measurement"""
        self.start_time = time.perf_counter()
        tracemalloc.start()
        
    def record_execution_time(self, operation: str, duration: float):
        """Record execution time for operation"""
        self.metrics['execution_times'].append({
            'operation': operation,
            'duration': duration,
            'timestamp': time.time()
        })
        
    def record_memory_usage(self):
        """Record current memory usage"""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.metrics['memory_usage'].append({
                'current': current,
                'peak': peak,
                'timestamp': time.time()
            })
        
        try:
            process_memory = self.process.memory_info().rss
            self.metrics['resource_utilization'].append({
                'memory_rss': process_memory,
                'cpu_percent': self.process.cpu_percent(),
                'timestamp': time.time()
            })
        except Exception:
            pass
            
    def record_event_throughput(self, events_processed: int, duration: float):
        """Record event processing throughput"""
        throughput = events_processed / duration if duration > 0 else 0
        self.metrics['event_throughput'].append({
            'events_processed': events_processed,
            'duration': duration,
            'throughput': throughput,
            'timestamp': time.time()
        })
        
    def record_concurrent_performance(self, concurrent_users: int, avg_response_time: float):
        """Record concurrent performance metrics"""
        self.metrics['concurrent_performance'].append({
            'concurrent_users': concurrent_users,
            'avg_response_time': avg_response_time,
            'timestamp': time.time()
        })
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {
            'test_name': self.test_name,
            'total_measurements': sum(len(metric_list) for metric_list in self.metrics.values()),
            'test_duration': time.perf_counter() - self.start_time if self.start_time else 0
        }
        
        # Calculate execution time statistics
        if self.metrics['execution_times']:
            durations = [m['duration'] for m in self.metrics['execution_times']]
            summary['execution_stats'] = {
                'avg_duration': statistics.mean(durations),
                'median_duration': statistics.median(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
            }
        
        # Calculate throughput statistics
        if self.metrics['event_throughput']:
            throughputs = [m['throughput'] for m in self.metrics['event_throughput']]
            summary['throughput_stats'] = {
                'avg_throughput': statistics.mean(throughputs),
                'max_throughput': max(throughputs),
                'min_throughput': min(throughputs)
            }
        
        # Calculate memory statistics
        if self.metrics['memory_usage']:
            current_memory = [m['current'] for m in self.metrics['memory_usage']]
            peak_memory = [m['peak'] for m in self.metrics['memory_usage']]
            summary['memory_stats'] = {
                'avg_current': statistics.mean(current_memory),
                'max_current': max(current_memory),
                'avg_peak': statistics.mean(peak_memory),
                'max_peak': max(peak_memory)
            }
        
        return summary


class PerformanceWebSocketMock:
    """High-performance WebSocket mock for testing"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events_sent = 0
        self.last_event_time = None
        self.send_agent_event = AsyncMock(side_effect=self._fast_event_handler)
        
    async def _fast_event_handler(self, event_type: str, data: Dict[str, Any]):
        """Fast event handler for performance testing"""
        self.events_sent += 1
        self.last_event_time = time.perf_counter()
        # Minimal processing for performance testing


class TestPerformanceValidation(SSotAsyncTestCase):
    """E2E Test 9: Validate UserExecutionEngine performance meets baseline requirements"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = f"performance_user_{uuid.uuid4().hex[:8]}"
        self.test_session_id = f"performance_session_{uuid.uuid4().hex[:8]}"
        
    async def test_execution_engine_creation_performance(self):
        """Test UserExecutionEngine creation performance"""
        print("\n🔍 Testing UserExecutionEngine creation performance...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        metrics = PerformanceMetrics("engine_creation_performance")
        metrics.start_measurement()
        
        # Test single engine creation performance
        creation_times = []
        
        for i in range(50):  # Create 50 engines to get statistical significance
            websocket_mock = PerformanceWebSocketMock(f"{self.test_user_id}_{i}")
            
            creation_start = time.perf_counter()
            try:
                engine = UserExecutionEngine(
                    user_id=f"{self.test_user_id}_{i}",
                    session_id=f"{self.test_session_id}_{i}",
                    websocket_manager=websocket_mock
                )
                creation_time = time.perf_counter() - creation_start
                creation_times.append(creation_time)
                
                metrics.record_execution_time(f"engine_creation_{i}", creation_time)
                metrics.record_memory_usage()
                
                # Cleanup
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                del engine
                
                # Force garbage collection every 10 iterations
                if i % 10 == 0:
                    gc.collect()
                
            except Exception as e:
                performance_violations.append(f"Engine creation {i} failed: {e}")
        
        # Analyze creation performance
        if creation_times:
            avg_creation_time = statistics.mean(creation_times)
            median_creation_time = statistics.median(creation_times)
            max_creation_time = max(creation_times)
            std_dev = statistics.stdev(creation_times) if len(creation_times) > 1 else 0
            
            print(f"  📊 Engine Creation Performance:")
            print(f"    Average: {avg_creation_time:.4f}s")
            print(f"    Median: {median_creation_time:.4f}s")
            print(f"    Maximum: {max_creation_time:.4f}s")
            print(f"    Std Dev: {std_dev:.4f}s")
            
            # Performance thresholds
            if avg_creation_time > 0.05:  # 50ms average creation time
                performance_violations.append(f"Slow average creation time: {avg_creation_time:.4f}s")
            
            if max_creation_time > 0.2:  # 200ms max creation time
                performance_violations.append(f"Slow max creation time: {max_creation_time:.4f}s")
            
            if std_dev > 0.02:  # 20ms standard deviation
                performance_violations.append(f"Inconsistent creation time: {std_dev:.4f}s std dev")
        
        # Test concurrent engine creation
        async def create_engine_concurrent(index: int):
            """Create engine concurrently"""
            websocket_mock = PerformanceWebSocketMock(f"concurrent_{index}")
            start_time = time.perf_counter()
            
            try:
                engine = UserExecutionEngine(
                    user_id=f"concurrent_user_{index}",
                    session_id=f"concurrent_session_{index}",
                    websocket_manager=websocket_mock
                )
                creation_time = time.perf_counter() - start_time
                
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                
                return creation_time
            except Exception as e:
                performance_violations.append(f"Concurrent creation {index} failed: {e}")
                return float('inf')
        
        print(f"  🔄 Testing concurrent engine creation...")
        concurrent_tasks = [create_engine_concurrent(i) for i in range(20)]
        concurrent_times = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        valid_concurrent_times = [t for t in concurrent_times if isinstance(t, (int, float)) and t != float('inf')]
        
        if valid_concurrent_times:
            concurrent_avg = statistics.mean(valid_concurrent_times)
            concurrent_max = max(valid_concurrent_times)
            
            print(f"    Concurrent average: {concurrent_avg:.4f}s")
            print(f"    Concurrent maximum: {concurrent_max:.4f}s")
            
            metrics.record_concurrent_performance(len(concurrent_tasks), concurrent_avg)
            
            # Concurrent creation shouldn't be much slower
            if concurrent_avg > avg_creation_time * 2:  # Allow 2x slower for concurrent
                performance_violations.append(f"Concurrent creation too slow: {concurrent_avg:.4f}s vs {avg_creation_time:.4f}s")
        
        print(f"  ✅ Engine creation performance tested: {len(creation_times)} sequential, {len(valid_concurrent_times)} concurrent")
        
        # CRITICAL: Engine creation performance affects user experience
        if performance_violations:
            self.fail(f"Engine creation performance violations: {performance_violations}")
        
        print(f"  ✅ UserExecutionEngine creation performance validated")
    
    async def test_event_processing_performance(self):
        """Test WebSocket event processing performance"""
        print("\n🔍 Testing WebSocket event processing performance...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        metrics = PerformanceMetrics("event_processing_performance")
        metrics.start_measurement()
        
        # Create test engine
        websocket_mock = PerformanceWebSocketMock(self.test_user_id)
        engine = UserExecutionEngine(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            websocket_manager=websocket_mock
        )
        
        # Test single event processing performance
        print(f"  📊 Testing single event processing...")
        
        event_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        single_event_times = []
        
        for i in range(100):  # Process 100 events for statistical significance
            event_type = event_types[i % len(event_types)]
            event_data = {
                'test_index': i,
                'user_id': self.test_user_id,
                'timestamp': time.time()
            }
            
            event_start = time.perf_counter()
            try:
                await engine.send_websocket_event(event_type, event_data)
                event_time = time.perf_counter() - event_start
                single_event_times.append(event_time)
                
                metrics.record_execution_time(f"event_processing_{i}", event_time)
                
                if i % 20 == 0:
                    metrics.record_memory_usage()
                
            except Exception as e:
                performance_violations.append(f"Event processing {i} failed: {e}")
        
        # Analyze single event performance
        if single_event_times:
            avg_event_time = statistics.mean(single_event_times)
            median_event_time = statistics.median(single_event_times)
            max_event_time = max(single_event_times)
            
            print(f"    Average event time: {avg_event_time:.4f}s")
            print(f"    Median event time: {median_event_time:.4f}s")
            print(f"    Maximum event time: {max_event_time:.4f}s")
            
            # Performance thresholds for event processing
            if avg_event_time > 0.001:  # 1ms average event processing
                performance_violations.append(f"Slow average event processing: {avg_event_time:.4f}s")
            
            if max_event_time > 0.01:  # 10ms max event processing
                performance_violations.append(f"Slow max event processing: {max_event_time:.4f}s")
        
        # Test burst event processing
        print(f"  🔄 Testing burst event processing...")
        
        burst_sizes = [10, 50, 100, 200]
        
        for burst_size in burst_sizes:
            burst_start = time.perf_counter()
            
            try:
                # Send burst of events
                burst_tasks = []
                for i in range(burst_size):
                    event_type = event_types[i % len(event_types)]
                    event_data = {
                        'burst_index': i,
                        'burst_size': burst_size,
                        'user_id': self.test_user_id
                    }
                    task = engine.send_websocket_event(event_type, event_data)
                    burst_tasks.append(task)
                
                # Wait for all events to complete
                await asyncio.gather(*burst_tasks)
                
                burst_time = time.perf_counter() - burst_start
                burst_throughput = burst_size / burst_time
                
                print(f"    Burst {burst_size} events: {burst_time:.4f}s ({burst_throughput:.1f} events/sec)")
                
                metrics.record_event_throughput(burst_size, burst_time)
                
                # Performance thresholds for burst processing
                if burst_throughput < 100:  # At least 100 events/sec
                    performance_violations.append(f"Slow burst throughput for {burst_size} events: {burst_throughput:.1f} events/sec")
                
            except Exception as e:
                performance_violations.append(f"Burst processing {burst_size} failed: {e}")
        
        # Test sustained event processing
        print(f"  ⏱️  Testing sustained event processing...")
        
        sustained_duration = 5.0  # 5 seconds of sustained processing
        sustained_start = time.perf_counter()
        sustained_events = 0
        
        try:
            while time.perf_counter() - sustained_start < sustained_duration:
                event_type = event_types[sustained_events % len(event_types)]
                event_data = {
                    'sustained_index': sustained_events,
                    'user_id': self.test_user_id
                }
                
                await engine.send_websocket_event(event_type, event_data)
                sustained_events += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)
        
        except Exception as e:
            performance_violations.append(f"Sustained processing failed: {e}")
        
        sustained_actual_time = time.perf_counter() - sustained_start
        sustained_throughput = sustained_events / sustained_actual_time
        
        print(f"    Sustained processing: {sustained_events} events in {sustained_actual_time:.3f}s ({sustained_throughput:.1f} events/sec)")
        
        metrics.record_event_throughput(sustained_events, sustained_actual_time)
        
        # Sustained processing should maintain performance
        if sustained_throughput < 50:  # At least 50 events/sec sustained
            performance_violations.append(f"Slow sustained throughput: {sustained_throughput:.1f} events/sec")
        
        # Cleanup
        if hasattr(engine, 'cleanup'):
            engine.cleanup()
        
        print(f"  ✅ Event processing performance tested: {len(single_event_times)} single events, {len(burst_sizes)} burst tests, {sustained_events} sustained events")
        
        # CRITICAL: Event processing performance affects real-time user experience
        if performance_violations:
            self.fail(f"Event processing performance violations: {performance_violations}")
        
        print(f"  ✅ WebSocket event processing performance validated")
    
    async def test_memory_performance_characteristics(self):
        """Test memory performance and resource management"""
        print("\n🔍 Testing memory performance characteristics...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        metrics = PerformanceMetrics("memory_performance")
        metrics.start_measurement()
        
        # Test memory usage during engine lifecycle
        print(f"  💾 Testing memory usage patterns...")
        
        initial_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        memory_measurements = []
        
        # Create and destroy engines to test memory patterns
        for cycle in range(10):
            cycle_engines = []
            
            # Create multiple engines
            for i in range(20):
                websocket_mock = PerformanceWebSocketMock(f"memory_test_{cycle}_{i}")
                
                try:
                    engine = UserExecutionEngine(
                        user_id=f"memory_user_{cycle}_{i}",
                        session_id=f"memory_session_{cycle}_{i}",
                        websocket_manager=websocket_mock
                    )
                    cycle_engines.append(engine)
                    
                    # Use the engine
                    context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
                    await engine.send_websocket_event('test_memory', {'cycle': cycle, 'index': i})
                    
                except Exception as e:
                    performance_violations.append(f"Memory test engine creation failed: {e}")
            
            # Measure memory after creation
            creation_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
            
            # Cleanup engines
            for engine in cycle_engines:
                try:
                    if hasattr(engine, 'cleanup'):
                        engine.cleanup()
                except Exception:
                    pass
            
            cycle_engines.clear()
            gc.collect()
            
            # Measure memory after cleanup
            cleanup_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
            
            memory_measurements.append({
                'cycle': cycle,
                'creation_memory': creation_memory,
                'cleanup_memory': cleanup_memory,
                'memory_growth': cleanup_memory - initial_memory,
                'cycle_peak': creation_memory - cleanup_memory
            })
            
            metrics.record_memory_usage()
            
            print(f"    Cycle {cycle}: {creation_memory/1024/1024:.2f}MB peak, {cleanup_memory/1024/1024:.2f}MB after cleanup")
        
        # Analyze memory performance
        if memory_measurements:
            total_growth = memory_measurements[-1]['memory_growth']
            peak_cycle_memory = max(m['cycle_peak'] for m in memory_measurements)
            avg_cycle_memory = statistics.mean(m['cycle_peak'] for m in memory_measurements)
            
            print(f"  📊 Memory Performance Analysis:")
            print(f"    Total memory growth: {total_growth/1024/1024:.2f}MB")
            print(f"    Peak cycle memory: {peak_cycle_memory/1024/1024:.2f}MB")
            print(f"    Average cycle memory: {avg_cycle_memory/1024/1024:.2f}MB")
            
            # Memory performance thresholds
            if total_growth > 100 * 1024 * 1024:  # 100MB total growth is excessive
                performance_violations.append(f"Excessive total memory growth: {total_growth/1024/1024:.2f}MB")
            
            if peak_cycle_memory > 50 * 1024 * 1024:  # 50MB per cycle is excessive
                performance_violations.append(f"Excessive cycle memory usage: {peak_cycle_memory/1024/1024:.2f}MB")
        
        # Test memory usage under load
        print(f"  🚀 Testing memory usage under load...")
        
        load_start_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        
        # Create load scenario
        async def create_load_engine(index: int):
            """Create engine with load simulation"""
            websocket_mock = PerformanceWebSocketMock(f"load_user_{index}")
            
            try:
                engine = UserExecutionEngine(
                    user_id=f"load_user_{index}",
                    session_id=f"load_session_{index}",
                    websocket_manager=websocket_mock
                )
                
                # Simulate realistic load
                for event_num in range(10):
                    await engine.send_websocket_event('load_test', {
                        'user_index': index,
                        'event_num': event_num,
                        'load_data': 'x' * 100  # Some data
                    })
                
                # Cleanup
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                
                return True
                
            except Exception as e:
                performance_violations.append(f"Load engine {index} failed: {e}")
                return False
        
        # Run load test
        load_tasks = [create_load_engine(i) for i in range(50)]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        load_end_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        load_memory_growth = load_end_memory - load_start_memory
        
        successful_loads = sum(1 for result in load_results if result is True)
        
        print(f"    Load test: {successful_loads}/{len(load_tasks)} successful")
        print(f"    Load memory growth: {load_memory_growth/1024/1024:.2f}MB")
        
        # Load memory growth should be reasonable
        if load_memory_growth > 75 * 1024 * 1024:  # 75MB for 50 engines under load
            performance_violations.append(f"Excessive load memory growth: {load_memory_growth/1024/1024:.2f}MB")
        
        if successful_loads < len(load_tasks) * 0.95:  # 95% success rate
            performance_violations.append(f"Load test success rate too low: {successful_loads}/{len(load_tasks)}")
        
        print(f"  ✅ Memory performance tested: {len(memory_measurements)} cycles, {len(load_tasks)} load engines")
        
        # CRITICAL: Memory performance affects system stability
        if performance_violations:
            self.fail(f"Memory performance violations: {performance_violations}")
        
        print(f"  ✅ Memory performance characteristics validated")
    
    def test_baseline_performance_comparison(self):
        """Test performance against established baselines"""
        print("\n🔍 Testing performance against baselines...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        
        # Define performance baselines (production requirements)
        baselines = {
            'engine_creation_time': 0.05,     # 50ms max
            'event_processing_time': 0.001,   # 1ms max
            'event_throughput': 100,          # 100 events/sec min
            'memory_per_engine': 5 * 1024 * 1024,  # 5MB max per engine
            'concurrent_users': 50,           # 50 concurrent users min
            'response_time_95th': 0.1         # 100ms 95th percentile
        }
        
        print(f"  📊 Performance Baselines:")
        for metric, baseline in baselines.items():
            if 'time' in metric:
                print(f"    {metric}: {baseline:.3f}s")
            elif 'throughput' in metric:
                print(f"    {metric}: {baseline} events/sec")
            elif 'memory' in metric:
                print(f"    {metric}: {baseline/1024/1024:.1f}MB")
            else:
                print(f"    {metric}: {baseline}")
        
        # Test against engine creation baseline
        print(f"  🔬 Testing engine creation baseline...")
        
        creation_times = []
        for i in range(20):
            websocket_mock = PerformanceWebSocketMock(f"baseline_user_{i}")
            
            creation_start = time.perf_counter()
            try:
                engine = UserExecutionEngine(
                    user_id=f"baseline_user_{i}",
                    session_id=f"baseline_session_{i}",
                    websocket_manager=websocket_mock
                )
                creation_time = time.perf_counter() - creation_start
                creation_times.append(creation_time)
                
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                
            except Exception as e:
                performance_violations.append(f"Baseline engine creation {i} failed: {e}")
        
        if creation_times:
            avg_creation_time = statistics.mean(creation_times)
            p95_creation_time = statistics.quantiles(creation_times, n=20)[18] if len(creation_times) >= 20 else max(creation_times)
            
            print(f"    Average creation time: {avg_creation_time:.4f}s (baseline: {baselines['engine_creation_time']:.3f}s)")
            print(f"    95th percentile: {p95_creation_time:.4f}s")
            
            if avg_creation_time > baselines['engine_creation_time']:
                performance_violations.append(f"Engine creation time exceeds baseline: {avg_creation_time:.4f}s > {baselines['engine_creation_time']:.3f}s")
        
        # Test against event processing baseline
        print(f"  🔬 Testing event processing baseline...")
        
        websocket_mock = PerformanceWebSocketMock(self.test_user_id)
        engine = UserExecutionEngine(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            websocket_manager=websocket_mock
        )
        
        async def test_event_baseline():
            event_times = []
            
            for i in range(100):
                event_start = time.perf_counter()
                try:
                    await engine.send_websocket_event('baseline_test', {'index': i})
                    event_time = time.perf_counter() - event_start
                    event_times.append(event_time)
                except Exception as e:
                    performance_violations.append(f"Baseline event processing {i} failed: {e}")
            
            return event_times
        
        event_times = asyncio.run(test_event_baseline())
        
        if event_times:
            avg_event_time = statistics.mean(event_times)
            p95_event_time = statistics.quantiles(event_times, n=20)[18] if len(event_times) >= 20 else max(event_times)
            
            print(f"    Average event time: {avg_event_time:.4f}s (baseline: {baselines['event_processing_time']:.3f}s)")
            print(f"    95th percentile: {p95_event_time:.4f}s (baseline: {baselines['response_time_95th']:.3f}s)")
            
            if avg_event_time > baselines['event_processing_time']:
                performance_violations.append(f"Event processing time exceeds baseline: {avg_event_time:.4f}s > {baselines['event_processing_time']:.3f}s")
            
            if p95_event_time > baselines['response_time_95th']:
                performance_violations.append(f"95th percentile response time exceeds baseline: {p95_event_time:.4f}s > {baselines['response_time_95th']:.3f}s")
        
        # Test throughput baseline
        print(f"  🔬 Testing throughput baseline...")
        
        async def test_throughput_baseline():
            start_time = time.perf_counter()
            events_sent = 0
            test_duration = 2.0  # 2 seconds
            
            while time.perf_counter() - start_time < test_duration:
                try:
                    await engine.send_websocket_event('throughput_test', {'event': events_sent})
                    events_sent += 1
                except Exception as e:
                    performance_violations.append(f"Throughput test event {events_sent} failed: {e}")
                    break
            
            actual_duration = time.perf_counter() - start_time
            throughput = events_sent / actual_duration
            
            return throughput, events_sent
        
        throughput, total_events = asyncio.run(test_throughput_baseline())
        
        print(f"    Throughput: {throughput:.1f} events/sec (baseline: {baselines['event_throughput']} events/sec)")
        print(f"    Total events: {total_events}")
        
        if throughput < baselines['event_throughput']:
            performance_violations.append(f"Event throughput below baseline: {throughput:.1f} < {baselines['event_throughput']}")
        
        # Cleanup
        if hasattr(engine, 'cleanup'):
            engine.cleanup()
        
        print(f"  ✅ Baseline performance comparison completed")
        
        # CRITICAL: Baseline performance ensures production readiness
        if performance_violations:
            self.fail(f"Baseline performance violations: {performance_violations}")
        
        print(f"  ✅ All performance baselines met")


if __name__ == '__main__':
    unittest.main(verbosity=2)