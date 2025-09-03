"""
Stress Testing and Resource Limit Validation for UserExecutionContext Migration

This module provides advanced stress testing to validate system behavior under
extreme conditions and verify resource limit enforcement.

Test Categories:
1. Resource Exhaustion Testing
2. User Limit Enforcement
3. System Breaking Point Detection
4. Recovery and Resilience Testing
5. Edge Case Performance
6. Graceful Degradation Validation

Business Value:
- Validates system stability under stress
- Ensures resource limits prevent system failure
- Tests graceful degradation mechanisms
- Validates recovery capabilities
"""

import asyncio
import gc
import os
import psutil
import pytest
import signal
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StressTestProfiler:
    """Advanced profiler for stress testing scenarios."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.memory_samples = []
        self.cpu_samples = []
        self.resource_samples = []
        self.error_events = []
        self.success_events = []
        
    def start_monitoring(self):
        """Start system monitoring."""
        self.start_time = time.time()
        self._take_system_snapshot("start")
        
    def stop_monitoring(self):
        """Stop system monitoring."""
        self.end_time = time.time()
        self._take_system_snapshot("end")
        
    def _take_system_snapshot(self, label: str):
        """Take snapshot of system resources."""
        process = psutil.Process()
        
        snapshot = {
            'timestamp': time.time(),
            'label': label,
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'threads': process.num_threads(),
            'open_files': len(process.open_files()),
            'connections': len(process.connections()),
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent(interval=0.1)
        }
        
        self.resource_samples.append(snapshot)
        
    def record_success(self, operation: str, duration_ms: float = None, metadata: Dict = None):
        """Record successful operation."""
        event = {
            'timestamp': time.time(),
            'operation': operation,
            'duration_ms': duration_ms,
            'metadata': metadata or {}
        }
        self.success_events.append(event)
        
    def record_error(self, operation: str, error: str, metadata: Dict = None):
        """Record error event."""
        event = {
            'timestamp': time.time(),
            'operation': operation,
            'error': error,
            'metadata': metadata or {}
        }
        self.error_events.append(event)
        
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report."""
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        # Calculate success/error rates
        total_operations = len(self.success_events) + len(self.error_events)
        success_rate = len(self.success_events) / total_operations if total_operations > 0 else 0
        
        # Memory analysis
        memory_start = self.resource_samples[0]['memory_mb'] if self.resource_samples else 0
        memory_end = self.resource_samples[-1]['memory_mb'] if self.resource_samples else 0
        memory_peak = max(sample['memory_mb'] for sample in self.resource_samples) if self.resource_samples else 0
        
        return {
            'test_name': self.test_name,
            'duration_seconds': duration,
            'total_operations': total_operations,
            'success_count': len(self.success_events),
            'error_count': len(self.error_events),
            'success_rate': success_rate,
            'memory_analysis': {
                'start_mb': memory_start,
                'end_mb': memory_end,
                'peak_mb': memory_peak,
                'growth_mb': memory_end - memory_start,
                'max_growth_mb': memory_peak - memory_start
            },
            'resource_samples': self.resource_samples,
            'error_summary': self._summarize_errors(),
            'performance_summary': self._summarize_performance()
        }
    
    def _summarize_errors(self) -> Dict[str, Any]:
        """Summarize error patterns."""
        error_types = {}
        for error_event in self.error_events:
            error_type = error_event.get('operation', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
        return {
            'total_errors': len(self.error_events),
            'error_types': error_types,
            'first_error_time': self.error_events[0]['timestamp'] - self.start_time if self.error_events else None,
            'last_error_time': self.error_events[-1]['timestamp'] - self.start_time if self.error_events else None
        }
    
    def _summarize_performance(self) -> Dict[str, Any]:
        """Summarize performance characteristics."""
        durations = [event['duration_ms'] for event in self.success_events if event.get('duration_ms')]
        
        if durations:
            durations.sort()
            return {
                'min_duration_ms': min(durations),
                'max_duration_ms': max(durations),
                'avg_duration_ms': sum(durations) / len(durations),
                'p50_duration_ms': durations[len(durations) // 2],
                'p95_duration_ms': durations[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                'p99_duration_ms': durations[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations),
                'total_operations_with_timing': len(durations)
            }
        else:
            return {'total_operations_with_timing': 0}


class MockAgentFactoryForStress:
    """Enhanced mock agent factory for stress testing."""
    
    def __init__(self):
        self._websocket_bridge = Mock()
        self._websocket_bridge.send_event = AsyncMock()
        self._agent_registry = Mock()
        self.creation_count = 0
        self.failure_rate = 0  # Configurable failure rate for testing
        
    async def create_agent(self, agent_type: str, context: UserExecutionContext):
        """Create mock agent with configurable failure."""
        self.creation_count += 1
        
        # Simulate occasional failures under stress
        if self.failure_rate > 0 and (self.creation_count % int(1/self.failure_rate)) == 0:
            raise Exception(f"Simulated agent creation failure #{self.creation_count}")
        
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=f"stress_test_result_{self.creation_count}")
        
        # Simulate varying execution times under stress
        execution_time = 0.01 + (self.creation_count % 10) * 0.001  # 10-20ms range
        
        async def stress_execute(*args, **kwargs):
            await asyncio.sleep(execution_time)
            return f"stress_result_{self.creation_count}"
        
        mock_agent.execute = stress_execute
        return mock_agent


@pytest.fixture
async def stress_test_factory():
    """Provide mock factory configured for stress testing."""
    return MockAgentFactoryForStress()


@pytest.mark.asyncio
class TestResourceExhaustion:
    """Test suite for resource exhaustion scenarios."""
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_user_engine_limit_enforcement(self, mock_get_factory, stress_test_factory):
        """Test per-user engine limit enforcement under stress."""
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        # Factory limits: max 2 engines per user
        
        profiler = StressTestProfiler("user_engine_limit_enforcement")
        profiler.start_monitoring()
        
        test_user_id = f"limit_test_user_{uuid.uuid4().hex[:8]}"
        engines_created = []
        
        # Try to create more engines than allowed
        for attempt in range(5):  # Attempt to create 5 engines (limit is 2)
            try:
                context = UserExecutionContext(
                    user_id=test_user_id,  # Same user for all attempts
                    thread_id=f"limit_thread_{attempt}_{uuid.uuid4().hex[:8]}",
                    run_id=f"limit_run_{attempt}_{uuid.uuid4().hex[:8]}",
                    request_id=f"limit_req_{attempt}_{uuid.uuid4().hex[:8]}"
                )
                
                engine = await factory.create_for_user(context)
                engines_created.append(engine)
                profiler.record_success("engine_creation", metadata={'attempt': attempt})
                
            except Exception as e:
                profiler.record_error("engine_creation", str(e), metadata={'attempt': attempt})
                logger.info(f"Expected limit enforcement triggered: {e}")
        
        profiler.stop_monitoring()
        report = profiler.get_comprehensive_report()
        
        # Cleanup created engines
        for engine in engines_created:
            try:
                await factory.cleanup_engine(engine)
            except Exception as e:
                logger.warning(f"Error cleaning up engine: {e}")
        
        await factory.shutdown()
        
        # Limit enforcement assertions
        assert len(engines_created) <= 2, f"User limit not enforced: {len(engines_created)} engines created"
        assert report['error_count'] >= 3, f"Expected limit enforcement errors, got {report['error_count']}"
        assert report['success_count'] <= 2, f"Too many engines allowed: {report['success_count']}"
        
        logger.info(f"User limit test: {len(engines_created)} engines created, "
                   f"{report['error_count']} limit enforcements triggered")
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_system_resource_exhaustion(self, mock_get_factory, stress_test_factory):
        """Test system behavior under resource exhaustion."""
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        
        profiler = StressTestProfiler("system_resource_exhaustion")
        profiler.start_monitoring()
        
        # Gradually increase load until system shows stress
        max_concurrent_users = 200
        engines_by_user = {}
        
        try:
            for user_num in range(max_concurrent_users):
                user_id = f"stress_user_{user_num}_{uuid.uuid4().hex[:8]}"
                
                try:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=f"stress_thread_{user_num}_{uuid.uuid4().hex[:8]}",
                        run_id=f"stress_run_{user_num}_{uuid.uuid4().hex[:8]}",
                        request_id=f"stress_req_{user_num}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    engine = await factory.create_for_user(context)
                    engines_by_user[user_id] = engine
                    
                    profiler.record_success("engine_creation", metadata={
                        'user_num': user_num,
                        'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
                    })
                    
                    # Check system resource usage
                    memory_percent = psutil.virtual_memory().percent
                    if memory_percent > 90:  # System memory stress
                        logger.warning(f"High system memory usage: {memory_percent}%")
                        break
                        
                except Exception as e:
                    profiler.record_error("engine_creation", str(e), metadata={'user_num': user_num})
                    logger.warning(f"Engine creation failed for user {user_num}: {e}")
                    
                    # Stop if we're getting consistent failures
                    recent_errors = [event for event in profiler.error_events[-10:] if event['operation'] == 'engine_creation']
                    if len(recent_errors) >= 5:  # 5 recent failures
                        logger.info("Stopping stress test due to consistent failures")
                        break
                
                # Brief pause to avoid overwhelming system
                if user_num % 20 == 0:
                    await asyncio.sleep(0.1)
                    profiler._take_system_snapshot(f"user_{user_num}")
        
        finally:
            profiler.stop_monitoring()
            
            # Cleanup all created engines
            cleanup_start = time.time()
            for user_id, engine in engines_by_user.items():
                try:
                    await factory.cleanup_engine(engine)
                except Exception as e:
                    logger.warning(f"Error cleaning up engine for {user_id}: {e}")
            
            cleanup_duration = time.time() - cleanup_start
            await factory.shutdown()
            
            logger.info(f"Stress test cleanup completed in {cleanup_duration:.2f}s")
        
        report = profiler.get_comprehensive_report()
        
        # Stress test analysis
        engines_created = len([e for e in profiler.success_events if e['operation'] == 'engine_creation'])
        peak_memory = max(sample['memory_mb'] for sample in profiler.resource_samples)
        
        logger.info(f"Stress test results: {engines_created} engines created, "
                   f"peak memory: {peak_memory:.2f}MB, {report['error_count']} errors")
        
        # Stress test assertions
        assert engines_created >= 50, f"System should handle at least 50 concurrent engines, got {engines_created}"
        assert report['success_rate'] >= 0.7, f"Success rate under stress too low: {report['success_rate']:.2%}"
        assert peak_memory < 1000, f"Memory usage too high under stress: {peak_memory}MB"
        
        # System should not crash (if we reach here, it didn't crash)
        assert True, "System remained stable under stress"


@pytest.mark.asyncio
class TestGracefulDegradation:
    """Test suite for graceful degradation under extreme load."""
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_graceful_degradation_under_load(self, mock_get_factory, stress_test_factory):
        """Test system graceful degradation under extreme load."""
        # Configure factory to occasionally fail under stress
        stress_test_factory.failure_rate = 0.1  # 10% failure rate
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        
        profiler = StressTestProfiler("graceful_degradation")
        profiler.start_monitoring()
        
        # Gradually increase load and monitor degradation
        load_levels = [10, 25, 50, 100, 200, 300]  # Requests per level
        degradation_metrics = {}
        
        for load_level in load_levels:
            level_start = time.time()
            logger.info(f"Testing load level: {load_level} concurrent requests")
            
            # Execute requests at this load level
            async def execute_load_request(req_id: int) -> Tuple[bool, float, str]:
                """Execute single request for load testing."""
                start = time.time()
                
                try:
                    context = UserExecutionContext(
                        user_id=f"load_user_{req_id % 50}_{uuid.uuid4().hex[:8]}",  # 50 users
                        thread_id=f"load_thread_{req_id}_{uuid.uuid4().hex[:8]}",
                        run_id=f"load_run_{req_id}_{uuid.uuid4().hex[:8]}",
                        request_id=f"load_req_{req_id}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    async with factory.user_execution_scope(context) as engine:
                        await asyncio.sleep(0.01)  # 10ms work
                        
                    duration = time.time() - start
                    return True, duration, ""
                    
                except Exception as e:
                    duration = time.time() - start
                    return False, duration, str(e)
            
            # Execute load level
            tasks = [execute_load_request(i) for i in range(load_level)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for this load level
            successful_requests = 0
            failed_requests = 0
            response_times = []
            
            for result in results:
                if isinstance(result, tuple):
                    success, duration, error = result
                    response_times.append(duration)
                    
                    if success:
                        successful_requests += 1
                        profiler.record_success("load_request", duration * 1000, {'load_level': load_level})
                    else:
                        failed_requests += 1
                        profiler.record_error("load_request", error, {'load_level': load_level})
                else:
                    failed_requests += 1
                    profiler.record_error("load_request", str(result), {'load_level': load_level})
            
            # Calculate metrics for this load level
            success_rate = successful_requests / (successful_requests + failed_requests)
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            level_duration = time.time() - level_start
            
            degradation_metrics[load_level] = {
                'success_rate': success_rate,
                'avg_response_time_ms': avg_response_time * 1000,
                'total_requests': load_level,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'level_duration_seconds': level_duration,
                'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
            }
            
            logger.info(f"Load level {load_level}: {success_rate:.2%} success rate, "
                       f"{avg_response_time * 1000:.1f}ms avg response time")
            
            # Stop if success rate drops too low (graceful degradation detected)
            if success_rate < 0.5:  # 50% threshold
                logger.info(f"Graceful degradation detected at load level {load_level}")
                break
            
            # Brief pause between load levels
            await asyncio.sleep(1)
        
        profiler.stop_monitoring()
        report = profiler.get_comprehensive_report()
        report['degradation_metrics'] = degradation_metrics
        
        await factory.shutdown()
        
        # Analyze degradation pattern
        load_levels_tested = list(degradation_metrics.keys())
        success_rates = [degradation_metrics[level]['success_rate'] for level in load_levels_tested]
        
        # Graceful degradation assertions
        assert len(load_levels_tested) >= 3, f"Should test at least 3 load levels, tested {len(load_levels_tested)}"
        assert max(success_rates) >= 0.9, f"Should achieve >90% success rate at low load, max was {max(success_rates):.2%}"
        
        # Verify degradation is gradual, not sudden
        if len(success_rates) >= 3:
            rate_changes = [abs(success_rates[i] - success_rates[i-1]) for i in range(1, len(success_rates))]
            max_rate_change = max(rate_changes) if rate_changes else 0
            assert max_rate_change < 0.5, f"Degradation too sudden: {max_rate_change:.2%} max change between levels"
        
        logger.info(f"Graceful degradation test completed: {len(load_levels_tested)} levels tested")


@pytest.mark.asyncio
class TestRecoveryAndResilience:
    """Test suite for system recovery and resilience."""
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_recovery_after_resource_exhaustion(self, mock_get_factory, stress_test_factory):
        """Test system recovery after resource exhaustion."""
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        
        profiler = StressTestProfiler("recovery_after_exhaustion")
        profiler.start_monitoring()
        
        # Phase 1: Create resource exhaustion
        logger.info("Phase 1: Creating resource exhaustion...")
        engines_created = []
        
        try:
            # Create many engines to approach limits
            for i in range(100):
                try:
                    context = UserExecutionContext(
                        user_id=f"recovery_user_{i % 30}_{uuid.uuid4().hex[:8]}",  # 30 users
                        thread_id=f"recovery_thread_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"recovery_run_{i}_{uuid.uuid4().hex[:8]}",
                        request_id=f"recovery_req_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    engine = await factory.create_for_user(context)
                    engines_created.append(engine)
                    profiler.record_success("exhaustion_creation", metadata={'phase': 1, 'engine_num': i})
                    
                except Exception as e:
                    profiler.record_error("exhaustion_creation", str(e), metadata={'phase': 1, 'engine_num': i})
                    
                    # Stop creating if we hit consistent failures
                    recent_errors = len([event for event in profiler.error_events[-5:] 
                                       if event['operation'] == 'exhaustion_creation'])
                    if recent_errors >= 3:
                        logger.info("Resource exhaustion detected, stopping creation")
                        break
        finally:
            pass  # Resources will be cleaned up in Phase 2
        
        exhaustion_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(f"Resource exhaustion phase: {len(engines_created)} engines created, "
                   f"memory: {exhaustion_memory:.2f}MB")
        
        # Phase 2: Cleanup to trigger recovery
        logger.info("Phase 2: Cleanup and recovery...")
        cleanup_start = time.time()
        
        for engine in engines_created:
            try:
                await factory.cleanup_engine(engine)
                profiler.record_success("recovery_cleanup", metadata={'phase': 2})
            except Exception as e:
                profiler.record_error("recovery_cleanup", str(e), metadata={'phase': 2})
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(1)  # Allow cleanup to complete
        
        cleanup_duration = time.time() - cleanup_start
        recovery_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Phase 3: Verify system can handle new requests
        logger.info("Phase 3: Testing post-recovery functionality...")
        
        post_recovery_engines = []
        for i in range(20):  # Test 20 new requests
            try:
                context = UserExecutionContext(
                    user_id=f"post_recovery_user_{i}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"post_recovery_thread_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"post_recovery_run_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"post_recovery_req_{i}_{uuid.uuid4().hex[:8]}"
                )
                
                async with factory.user_execution_scope(context) as engine:
                    await asyncio.sleep(0.01)  # Brief work
                
                profiler.record_success("post_recovery_request", metadata={'phase': 3, 'request_num': i})
                
            except Exception as e:
                profiler.record_error("post_recovery_request", str(e), metadata={'phase': 3, 'request_num': i})
        
        profiler.stop_monitoring()
        report = profiler.get_comprehensive_report()
        
        await factory.shutdown()
        
        # Recovery analysis
        memory_recovered = exhaustion_memory - recovery_memory
        recovery_success_rate = len([e for e in profiler.success_events if e['metadata'].get('phase') == 3]) / 20
        
        logger.info(f"Recovery test: {exhaustion_memory:.2f}MB -> {recovery_memory:.2f}MB "
                   f"({memory_recovered:.2f}MB recovered in {cleanup_duration:.2f}s)")
        logger.info(f"Post-recovery success rate: {recovery_success_rate:.2%}")
        
        # Recovery assertions
        assert memory_recovered > 0, f"No memory recovered: {memory_recovered}MB"
        assert recovery_success_rate >= 0.9, f"Poor post-recovery performance: {recovery_success_rate:.2%}"
        assert recovery_memory < exhaustion_memory * 1.2, f"Memory not properly recovered: {recovery_memory}MB"


@pytest.mark.asyncio
class TestEdgeCasePerformance:
    """Test suite for edge case performance scenarios."""
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_rapid_create_destroy_cycles(self, mock_get_factory, stress_test_factory):
        """Test rapid create/destroy cycles for performance impact."""
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        
        profiler = StressTestProfiler("rapid_create_destroy_cycles")
        profiler.start_monitoring()
        
        cycles = 200  # 200 rapid cycles
        
        for cycle in range(cycles):
            cycle_start = time.time()
            
            try:
                context = UserExecutionContext(
                    user_id=f"rapid_user_{cycle}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"rapid_thread_{cycle}_{uuid.uuid4().hex[:8]}",
                    run_id=f"rapid_run_{cycle}_{uuid.uuid4().hex[:8]}",
                    request_id=f"rapid_req_{cycle}_{uuid.uuid4().hex[:8]}"
                )
                
                # Create engine
                engine = await factory.create_for_user(context)
                
                # Immediately cleanup (rapid cycle)
                await factory.cleanup_engine(engine)
                
                cycle_duration = (time.time() - cycle_start) * 1000
                profiler.record_success("rapid_cycle", cycle_duration, metadata={'cycle': cycle})
                
                # Occasional system snapshot
                if cycle % 50 == 0:
                    profiler._take_system_snapshot(f"cycle_{cycle}")
                
            except Exception as e:
                cycle_duration = (time.time() - cycle_start) * 1000
                profiler.record_error("rapid_cycle", str(e), metadata={'cycle': cycle})
        
        profiler.stop_monitoring()
        report = profiler.get_comprehensive_report()
        
        await factory.shutdown()
        
        # Calculate cycle performance
        successful_cycles = len([e for e in profiler.success_events if e['operation'] == 'rapid_cycle'])
        cycle_durations = [e['duration_ms'] for e in profiler.success_events if e.get('duration_ms')]
        
        avg_cycle_time = sum(cycle_durations) / len(cycle_durations) if cycle_durations else 0
        cycles_per_second = successful_cycles / report['duration_seconds'] if report['duration_seconds'] > 0 else 0
        
        logger.info(f"Rapid cycles: {successful_cycles}/{cycles} successful, "
                   f"avg cycle time: {avg_cycle_time:.2f}ms, "
                   f"rate: {cycles_per_second:.2f} cycles/sec")
        
        # Rapid cycle assertions
        assert successful_cycles >= cycles * 0.95, f"Too many rapid cycle failures: {cycles - successful_cycles}"
        assert avg_cycle_time < 50, f"Rapid cycles too slow: {avg_cycle_time:.2f}ms average"
        assert cycles_per_second > 20, f"Rapid cycle rate too low: {cycles_per_second:.2f} cycles/sec"
        assert report['memory_analysis']['growth_mb'] < 20, f"Memory growth during rapid cycles: {report['memory_analysis']['growth_mb']:.2f}MB"
    
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
    async def test_mixed_workload_performance(self, mock_get_factory, stress_test_factory):
        """Test performance under mixed workload (short and long operations)."""
        mock_get_factory.return_value = stress_test_factory
        
        factory = ExecutionEngineFactory()
        
        profiler = StressTestProfiler("mixed_workload")
        profiler.start_monitoring()
        
        # Mixed workload: 70% short operations, 30% long operations
        total_operations = 100
        short_operations = int(total_operations * 0.7)
        long_operations = total_operations - short_operations
        
        async def short_operation(op_id: int) -> Tuple[bool, float, str]:
            """Short operation (10ms)."""
            start = time.time()
            
            try:
                context = UserExecutionContext(
                    user_id=f"short_user_{op_id}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"short_thread_{op_id}_{uuid.uuid4().hex[:8]}",
                    run_id=f"short_run_{op_id}_{uuid.uuid4().hex[:8]}",
                    request_id=f"short_req_{op_id}_{uuid.uuid4().hex[:8]}"
                )
                
                async with factory.user_execution_scope(context) as engine:
                    await asyncio.sleep(0.01)  # 10ms work
                
                duration = time.time() - start
                return True, duration, "short"
                
            except Exception as e:
                duration = time.time() - start
                return False, duration, str(e)
        
        async def long_operation(op_id: int) -> Tuple[bool, float, str]:
            """Long operation (100ms)."""
            start = time.time()
            
            try:
                context = UserExecutionContext(
                    user_id=f"long_user_{op_id}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"long_thread_{op_id}_{uuid.uuid4().hex[:8]}",
                    run_id=f"long_run_{op_id}_{uuid.uuid4().hex[:8]}",
                    request_id=f"long_req_{op_id}_{uuid.uuid4().hex[:8]}"
                )
                
                async with factory.user_execution_scope(context) as engine:
                    await asyncio.sleep(0.1)  # 100ms work
                
                duration = time.time() - start
                return True, duration, "long"
                
            except Exception as e:
                duration = time.time() - start
                return False, duration, str(e)
        
        # Create mixed task list
        tasks = []
        
        # Add short operations
        tasks.extend([short_operation(i) for i in range(short_operations)])
        
        # Add long operations
        tasks.extend([long_operation(i) for i in range(long_operations)])
        
        # Shuffle for realistic mixed load
        import random
        random.shuffle(tasks)
        
        # Execute mixed workload
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze mixed workload results
        short_durations = []
        long_durations = []
        
        for result in results:
            if isinstance(result, tuple):
                success, duration, operation_type = result
                
                if success:
                    if operation_type == "short":
                        short_durations.append(duration)
                        profiler.record_success("short_operation", duration * 1000)
                    elif operation_type == "long":
                        long_durations.append(duration)
                        profiler.record_success("long_operation", duration * 1000)
                else:
                    profiler.record_error("mixed_operation", operation_type)
            else:
                profiler.record_error("mixed_operation", str(result))
        
        profiler.stop_monitoring()
        report = profiler.get_comprehensive_report()
        
        await factory.shutdown()
        
        # Performance analysis
        short_avg = sum(short_durations) / len(short_durations) * 1000 if short_durations else 0
        long_avg = sum(long_durations) / len(long_durations) * 1000 if long_durations else 0
        
        logger.info(f"Mixed workload: {len(short_durations)} short ops (avg {short_avg:.1f}ms), "
                   f"{len(long_durations)} long ops (avg {long_avg:.1f}ms)")
        
        # Mixed workload assertions
        assert len(short_durations) >= short_operations * 0.95, f"Too many short operation failures"
        assert len(long_durations) >= long_operations * 0.95, f"Too many long operation failures"
        assert short_avg < 50, f"Short operations too slow: {short_avg:.1f}ms (expected ~10ms)"
        assert long_avg < 150, f"Long operations too slow: {long_avg:.1f}ms (expected ~100ms)"
        
        # Verify short operations weren't blocked by long ones
        if short_durations:
            short_durations.sort()
            p95_short = short_durations[int(len(short_durations) * 0.95)]
            assert p95_short < 0.05, f"Short operations blocked by long ones: P95 = {p95_short * 1000:.1f}ms"


if __name__ == "__main__":
    """Run stress tests directly."""
    print("🚀 Starting UserExecutionContext Stress Testing Suite")
    print("="*60)
    
    # Run pytest on this module
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    if exit_code == 0:
        print("\n✅ All stress tests passed!")
    else:
        print(f"\n❌ Some stress tests failed (exit code: {exit_code})")
    
    sys.exit(exit_code)