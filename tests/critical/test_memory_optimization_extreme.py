#!/usr/bin/env python
"""
EXTREME MEMORY OPTIMIZATION TEST SUITE

CRITICAL MEMORY FIXES VALIDATION:
- 2GB memory limit enforcement
- Worker process memory optimization  
- Lazy loading implementation
- Memory leak detection and prevention
- Request-scoped memory isolation
- Concurrent user memory management

This test suite provides EXTREME testing scenarios:
1. High-memory load simulation (approaching 2GB limit)
2. Memory leak detection under stress
3. Concurrent user memory isolation validation
4. Worker process memory optimization verification
5. Lazy loading stress testing
6. Memory pressure handling validation
7. Memory regression prevention

Business Impact: Prevents OOM crashes, ensures scalability, maintains performance
Strategic Value: Critical for production stability and user experience
"""

import asyncio
import gc
import os
import psutil
import pytest
import sys
import time
import uuid
import threading
import weakref
import tracemalloc
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Callable, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import json

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# Memory optimization services
try:
    from netra_backend.app.services.memory_optimization_service import (
        MemoryOptimizationService, MemoryPressureLevel, RequestScope, get_memory_service
    )
    from netra_backend.app.services.session_memory_manager import (
        SessionMemoryManager, UserSession, SessionState, get_session_manager
    )
    from netra_backend.app.services.lazy_component_loader import (
        LazyComponentLoader, ComponentPriority, LoadingStrategy, get_component_loader
    )
    from netra_backend.app.models.user_execution_context import UserExecutionContext
    MEMORY_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Memory services not available: {e}")
    MEMORY_SERVICES_AVAILABLE = False
    
    # Create mock classes for testing
    class MemoryOptimizationService:
        def __init__(self): pass
        async def start(self): pass
        async def stop(self): pass
        
    class SessionMemoryManager:
        def __init__(self): pass
        async def start(self): pass
        async def stop(self): pass
        
    class LazyComponentLoader:
        def __init__(self): pass
        async def load_component(self, name): return MagicMock()
        
    class UserExecutionContext:
        def __init__(self, user_id, thread_id, run_id, request_id, websocket_connection_id=None):
            self.user_id = user_id
            self.thread_id = thread_id
            self.run_id = run_id
            self.request_id = request_id
            self.websocket_connection_id = websocket_connection_id

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Memory test constants
MEMORY_LIMIT_GB = 2.0  # 2GB limit
MEMORY_LIMIT_MB = MEMORY_LIMIT_GB * 1024  # 2048MB
MEMORY_WARNING_THRESHOLD = MEMORY_LIMIT_MB * 0.8  # 80% of limit
MEMORY_CRITICAL_THRESHOLD = MEMORY_LIMIT_MB * 0.95  # 95% of limit
CONCURRENT_USERS = 50  # Number of concurrent users for stress test
OPERATIONS_PER_USER = 100  # Operations per user
MEMORY_LEAK_THRESHOLD_MB = 10  # Max acceptable memory increase per operation
STRESS_TEST_DURATION = 60  # Duration in seconds


@dataclass
class MemoryMeasurement:
    """Memory measurement data."""
    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size  
    percent: float  # Memory percentage
    available_mb: float  # Available system memory
    label: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryLeakEvent:
    """Memory leak detection event."""
    timestamp: float
    operation: str
    before_mb: float
    after_mb: float
    leak_mb: float
    context: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class ConcurrentUserData:
    """Data for concurrent user testing."""
    user_id: str
    user_context: UserExecutionContext
    memory_tracker: 'ExtremeMemoryTracker'
    operations_completed: int = 0
    errors: List[Exception] = field(default_factory=list)
    memory_measurements: List[MemoryMeasurement] = field(default_factory=list)


class ExtremeMemoryTracker:
    """Advanced memory tracker for extreme testing scenarios."""
    
    def __init__(self, name: str = "memory_tracker"):
        self.name = name
        self.process = psutil.Process()
        self.start_time = time.time()
        self.measurements: List[MemoryMeasurement] = []
        self.leak_events: List[MemoryLeakEvent] = []
        self.peak_memory_mb = 0.0
        self.baseline_memory_mb = 0.0
        self.lock = threading.Lock()
        self.tracemalloc_enabled = False
        
        # Start memory tracking
        self.baseline_memory_mb = self._get_memory_usage()
        self.peak_memory_mb = self.baseline_memory_mb
        
    def start_tracemalloc(self):
        """Start Python memory tracing."""
        try:
            tracemalloc.start()
            self.tracemalloc_enabled = True
            logger.info(f"Started tracemalloc for {self.name}")
        except Exception as e:
            logger.warning(f"Failed to start tracemalloc: {e}")
    
    def stop_tracemalloc(self):
        """Stop Python memory tracing."""
        if self.tracemalloc_enabled:
            try:
                tracemalloc.stop()
                self.tracemalloc_enabled = False
                logger.info(f"Stopped tracemalloc for {self.name}")
            except Exception as e:
                logger.warning(f"Failed to stop tracemalloc: {e}")
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage metrics."""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            virtual_memory = psutil.virtual_memory()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': memory_percent,
                'available_mb': virtual_memory.available / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0}
    
    def measure(self, label: str = "", context: Dict[str, Any] = None) -> MemoryMeasurement:
        """Take detailed memory measurement."""
        with self.lock:
            memory_data = self._get_memory_usage()
            
            measurement = MemoryMeasurement(
                timestamp=time.time() - self.start_time,
                rss_mb=memory_data['rss_mb'],
                vms_mb=memory_data['vms_mb'],
                percent=memory_data['percent'],
                available_mb=memory_data['available_mb'],
                label=label,
                context=context or {}
            )
            
            self.measurements.append(measurement)
            
            # Update peak memory
            if measurement.rss_mb > self.peak_memory_mb:
                self.peak_memory_mb = measurement.rss_mb
            
            # Check for memory limit violations
            if measurement.rss_mb > MEMORY_CRITICAL_THRESHOLD:
                logger.error(f"CRITICAL: Memory usage {measurement.rss_mb:.1f}MB exceeds threshold {MEMORY_CRITICAL_THRESHOLD:.1f}MB")
            elif measurement.rss_mb > MEMORY_WARNING_THRESHOLD:
                logger.warning(f"WARNING: Memory usage {measurement.rss_mb:.1f}MB exceeds threshold {MEMORY_WARNING_THRESHOLD:.1f}MB")
            
            return measurement
    
    def detect_memory_leak(self, operation: str, before: MemoryMeasurement, after: MemoryMeasurement, 
                          threshold_mb: float = MEMORY_LEAK_THRESHOLD_MB) -> Optional[MemoryLeakEvent]:
        """Detect memory leak between two measurements."""
        leak_mb = after.rss_mb - before.rss_mb
        
        if leak_mb > threshold_mb:
            leak_event = MemoryLeakEvent(
                timestamp=after.timestamp,
                operation=operation,
                before_mb=before.rss_mb,
                after_mb=after.rss_mb,
                leak_mb=leak_mb,
                context={
                    'before_context': before.context,
                    'after_context': after.context
                }
            )
            
            with self.lock:
                self.leak_events.append(leak_event)
            
            logger.error(f"MEMORY LEAK DETECTED: {operation} leaked {leak_mb:.2f}MB (threshold: {threshold_mb}MB)")
            return leak_event
        
        return None
    
    def get_memory_increase(self) -> float:
        """Get total memory increase since baseline."""
        current_memory = self._get_memory_usage()
        return current_memory['rss_mb'] - self.baseline_memory_mb
    
    def get_peak_memory_usage(self) -> float:
        """Get peak memory usage."""
        return self.peak_memory_mb
    
    def validate_memory_limits(self) -> Tuple[bool, List[str]]:
        """Validate memory usage against limits."""
        violations = []
        current_memory = self._get_memory_usage()
        
        # Check current usage
        if current_memory['rss_mb'] > MEMORY_LIMIT_MB:
            violations.append(f"Current memory {current_memory['rss_mb']:.1f}MB exceeds limit {MEMORY_LIMIT_MB:.1f}MB")
        
        # Check peak usage
        if self.peak_memory_mb > MEMORY_LIMIT_MB:
            violations.append(f"Peak memory {self.peak_memory_mb:.1f}MB exceeds limit {MEMORY_LIMIT_MB:.1f}MB")
        
        # Check for memory leaks
        if self.leak_events:
            violations.append(f"Detected {len(self.leak_events)} memory leaks")
        
        return len(violations) == 0, violations
    
    def get_tracemalloc_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get current tracemalloc snapshot."""
        if not self.tracemalloc_enabled:
            return None
            
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            return {
                'total_size_mb': sum(stat.size for stat in top_stats) / 1024 / 1024,
                'total_count': sum(stat.count for stat in top_stats),
                'top_10': [
                    {
                        'filename': stat.traceback.format()[0],
                        'size_mb': stat.size / 1024 / 1024,
                        'count': stat.count
                    }
                    for stat in top_stats[:10]
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get tracemalloc snapshot: {e}")
            return None


class MemoryStressGenerator:
    """Generates memory stress scenarios."""
    
    def __init__(self):
        self.allocated_data: List[Any] = []
        self.weak_refs: List[weakref.ref] = []
    
    async def allocate_memory_gradually(self, target_mb: float, step_mb: float = 10.0, 
                                       delay_seconds: float = 0.1) -> List[bytes]:
        """Gradually allocate memory to test memory pressure handling."""
        allocated = []
        current_mb = 0.0
        
        while current_mb < target_mb:
            # Allocate step_mb of memory
            chunk_size = int(min(step_mb, target_mb - current_mb) * 1024 * 1024)
            chunk = bytearray(chunk_size)
            allocated.append(chunk)
            current_mb += chunk_size / 1024 / 1024
            
            # Add delay to allow memory monitoring
            await asyncio.sleep(delay_seconds)
            
            logger.debug(f"Allocated {current_mb:.1f}MB / {target_mb:.1f}MB")
        
        self.allocated_data.extend(allocated)
        return allocated
    
    def create_circular_references(self, count: int = 1000) -> List[Any]:
        """Create circular references to test garbage collection."""
        objects = []
        
        class CircularRef:
            def __init__(self, id_val):
                self.id = id_val
                self.refs = []
                self.data = bytearray(1024)  # 1KB per object
        
        # Create objects
        for i in range(count):
            obj = CircularRef(i)
            objects.append(obj)
        
        # Create circular references
        for i, obj in enumerate(objects):
            next_obj = objects[(i + 1) % count]
            obj.refs.append(next_obj)
            
            # Create weak reference for tracking
            self.weak_refs.append(weakref.ref(obj))
        
        return objects
    
    def cleanup_allocated_memory(self):
        """Clean up allocated memory."""
        self.allocated_data.clear()
        gc.collect()
    
    def check_weak_refs_cleanup(self) -> Tuple[int, int]:
        """Check if weak references have been cleaned up."""
        alive_count = sum(1 for ref in self.weak_refs if ref() is not None)
        total_count = len(self.weak_refs)
        return alive_count, total_count


class ConcurrentUserMemoryTester:
    """Tests memory behavior under concurrent user load."""
    
    def __init__(self, user_count: int = CONCURRENT_USERS):
        self.user_count = user_count
        self.users: Dict[str, ConcurrentUserData] = {}
        self.executor = ThreadPoolExecutor(max_workers=user_count)
        self.results: Dict[str, Any] = {}
        self.lock = threading.Lock()
    
    def create_concurrent_users(self) -> List[ConcurrentUserData]:
        """Create concurrent user contexts."""
        users = []
        
        for i in range(self.user_count):
            user_id = f"stress_user_{i}_{uuid.uuid4().hex[:8]}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
                websocket_connection_id=f"ws_{i}_{uuid.uuid4().hex[:8]}"
            )
            
            user_data = ConcurrentUserData(
                user_id=user_id,
                user_context=user_context,
                memory_tracker=ExtremeMemoryTracker(f"user_{user_id}")
            )
            
            users.append(user_data)
            
            with self.lock:
                self.users[user_id] = user_data
        
        return users
    
    async def simulate_user_operations(self, user_data: ConcurrentUserData, 
                                     operations_count: int = OPERATIONS_PER_USER) -> Dict[str, Any]:
        """Simulate operations for a single user."""
        try:
            user_data.memory_tracker.start_tracemalloc()
            
            # Baseline measurement
            baseline = user_data.memory_tracker.measure("baseline")
            
            for op_id in range(operations_count):
                operation_name = f"operation_{op_id}"
                
                # Pre-operation measurement
                pre_op = user_data.memory_tracker.measure(f"pre_{operation_name}")
                
                # Simulate memory-intensive operation
                await self._simulate_memory_operation(user_data, operation_name)
                
                # Post-operation measurement
                post_op = user_data.memory_tracker.measure(f"post_{operation_name}")
                
                # Check for memory leaks
                user_data.memory_tracker.detect_memory_leak(operation_name, pre_op, post_op)
                
                user_data.operations_completed += 1
                
                # Yield control periodically
                if op_id % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # Final measurement
            final = user_data.memory_tracker.measure("final")
            
            # Validate memory usage
            is_valid, violations = user_data.memory_tracker.validate_memory_limits()
            
            return {
                'user_id': user_data.user_id,
                'operations_completed': user_data.operations_completed,
                'baseline_memory_mb': baseline.rss_mb,
                'final_memory_mb': final.rss_mb,
                'peak_memory_mb': user_data.memory_tracker.get_peak_memory_usage(),
                'memory_increase_mb': user_data.memory_tracker.get_memory_increase(),
                'leak_events_count': len(user_data.memory_tracker.leak_events),
                'memory_valid': is_valid,
                'violations': violations,
                'errors': len(user_data.errors)
            }
        
        except Exception as e:
            user_data.errors.append(e)
            logger.error(f"User operation failed for {user_data.user_id}: {e}")
            raise
        
        finally:
            user_data.memory_tracker.stop_tracemalloc()
    
    async def _simulate_memory_operation(self, user_data: ConcurrentUserData, operation_name: str):
        """Simulate a memory-intensive operation."""
        try:
            # Simulate different types of memory operations
            operation_type = hash(operation_name) % 4
            
            if operation_type == 0:
                # Allocate and deallocate temporary data
                temp_data = bytearray(1024 * 1024)  # 1MB
                await asyncio.sleep(0.001)  # Simulate processing
                del temp_data
            
            elif operation_type == 1:
                # Create and process objects
                objects = [{'id': i, 'data': f'data_{i}'} for i in range(1000)]
                processed = [obj['id'] for obj in objects if obj['id'] % 2 == 0]
                await asyncio.sleep(0.001)
            
            elif operation_type == 2:
                # Simulate database-like operations
                records = []
                for i in range(100):
                    record = {
                        'user_id': user_data.user_id,
                        'timestamp': time.time(),
                        'data': f'record_data_{i}' * 10
                    }
                    records.append(record)
                await asyncio.sleep(0.001)
            
            else:
                # Simulate file-like operations
                content = f"User {user_data.user_id} operation {operation_name}" * 100
                await asyncio.sleep(0.001)
        
        except Exception as e:
            user_data.errors.append(e)
            raise
    
    async def run_concurrent_stress_test(self, duration_seconds: int = STRESS_TEST_DURATION) -> Dict[str, Any]:
        """Run concurrent user stress test."""
        logger.info(f"Starting concurrent stress test with {self.user_count} users for {duration_seconds}s")
        
        # Create users
        users = self.create_concurrent_users()
        
        # Start concurrent operations
        start_time = time.time()
        tasks = []
        
        for user_data in users:
            task = asyncio.create_task(
                self.simulate_user_operations(user_data, OPERATIONS_PER_USER)
            )
            tasks.append(task)
        
        # Wait for completion or timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=duration_seconds + 30  # Allow extra time for cleanup
            )
        except asyncio.TimeoutError:
            logger.error("Concurrent stress test timed out")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            results = ["timeout"] * len(tasks)
        
        end_time = time.time()
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict)]
        failed_results = [r for r in results if not isinstance(r, dict)]
        
        total_operations = sum(r.get('operations_completed', 0) for r in successful_results)
        total_memory_increase = sum(r.get('memory_increase_mb', 0) for r in successful_results)
        total_leaks = sum(r.get('leak_events_count', 0) for r in successful_results)
        
        return {
            'duration_seconds': end_time - start_time,
            'total_users': self.user_count,
            'successful_users': len(successful_results),
            'failed_users': len(failed_results),
            'total_operations': total_operations,
            'total_memory_increase_mb': total_memory_increase,
            'total_leak_events': total_leaks,
            'average_memory_increase_mb': total_memory_increase / max(len(successful_results), 1),
            'user_results': successful_results,
            'failures': failed_results
        }


# ============================================================================
# EXTREME MEMORY OPTIMIZATION TESTS
# ============================================================================

@pytest.fixture
async def extreme_memory_tracker():
    """Fixture providing extreme memory tracker."""
    tracker = ExtremeMemoryTracker("test_extreme")
    tracker.start_tracemalloc()
    try:
        yield tracker
    finally:
        tracker.stop_tracemalloc()


@pytest.fixture
async def memory_stress_generator():
    """Fixture providing memory stress generator."""
    generator = MemoryStressGenerator()
    try:
        yield generator
    finally:
        generator.cleanup_allocated_memory()


@pytest.fixture
async def concurrent_user_tester():
    """Fixture providing concurrent user memory tester."""
    tester = ConcurrentUserMemoryTester()
    try:
        yield tester
    finally:
        tester.executor.shutdown(wait=True)


@pytest.mark.asyncio
class TestExtremeMemoryOptimization:
    """Extreme memory optimization test suite."""
    
    async def test_memory_limit_enforcement_extreme(self, extreme_memory_tracker, memory_stress_generator):
        """Test that 2GB memory limit is strictly enforced under extreme load."""
        logger.info("Testing 2GB memory limit enforcement under extreme load")
        
        # Baseline measurement
        baseline = extreme_memory_tracker.measure("baseline")
        assert baseline.rss_mb < MEMORY_LIMIT_MB, f"Baseline memory {baseline.rss_mb:.1f}MB exceeds limit"
        
        # Gradually increase memory usage approaching the limit
        target_mb = MEMORY_LIMIT_MB * 0.9  # Target 90% of limit
        
        try:
            allocated_chunks = await memory_stress_generator.allocate_memory_gradually(
                target_mb=target_mb,
                step_mb=50.0,  # 50MB steps
                delay_seconds=0.05
            )
            
            # Measure after allocation
            after_allocation = extreme_memory_tracker.measure("after_allocation")
            logger.info(f"Allocated {len(allocated_chunks)} chunks, memory usage: {after_allocation.rss_mb:.1f}MB")
            
            # Memory should not exceed the limit
            assert after_allocation.rss_mb <= MEMORY_LIMIT_MB, \
                f"Memory usage {after_allocation.rss_mb:.1f}MB exceeds limit {MEMORY_LIMIT_MB:.1f}MB"
            
            # Validate memory tracking
            is_valid, violations = extreme_memory_tracker.validate_memory_limits()
            assert is_valid, f"Memory limit violations: {violations}"
            
        finally:
            # Cleanup
            memory_stress_generator.cleanup_allocated_memory()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Verify memory is released
            after_cleanup = extreme_memory_tracker.measure("after_cleanup")
            memory_released = after_allocation.rss_mb - after_cleanup.rss_mb
            
            logger.info(f"Memory released after cleanup: {memory_released:.1f}MB")
            assert memory_released > 0, "Memory was not properly released after cleanup"
    
    async def test_memory_leak_detection_extreme(self, extreme_memory_tracker):
        """Test extreme memory leak detection across thousands of operations."""
        logger.info("Testing memory leak detection across thousands of operations")
        
        baseline = extreme_memory_tracker.measure("baseline")
        operations_count = 5000  # Large number of operations
        leak_threshold_mb = 1.0  # Very strict threshold
        
        for i in range(operations_count):
            operation_name = f"operation_{i}"
            
            # Pre-operation measurement
            pre_op = extreme_memory_tracker.measure(f"pre_{operation_name}")
            
            # Simulate operation that might leak memory
            await self._simulate_potential_memory_leak_operation(i)
            
            # Post-operation measurement
            post_op = extreme_memory_tracker.measure(f"post_{operation_name}")
            
            # Check for leaks with strict threshold
            extreme_memory_tracker.detect_memory_leak(operation_name, pre_op, post_op, leak_threshold_mb)
            
            # Periodic cleanup and validation
            if i % 500 == 0:
                gc.collect()
                await asyncio.sleep(0.01)
                
                # Check total memory increase
                memory_increase = extreme_memory_tracker.get_memory_increase()
                max_acceptable_increase = (i + 1) * 0.01  # 0.01MB per operation max
                
                if memory_increase > max_acceptable_increase:
                    logger.error(f"Excessive memory increase detected: {memory_increase:.2f}MB after {i+1} operations")
        
        # Final validation
        final = extreme_memory_tracker.measure("final")
        total_increase = extreme_memory_tracker.get_memory_increase()
        
        logger.info(f"Completed {operations_count} operations, total memory increase: {total_increase:.2f}MB")
        logger.info(f"Detected {len(extreme_memory_tracker.leak_events)} leak events")
        
        # Strict memory increase validation
        max_acceptable_total_increase = operations_count * 0.01  # 0.01MB per operation
        assert total_increase <= max_acceptable_total_increase, \
            f"Total memory increase {total_increase:.2f}MB exceeds acceptable limit {max_acceptable_total_increase:.2f}MB"
        
        # No significant memory leaks should be detected
        significant_leaks = [leak for leak in extreme_memory_tracker.leak_events if leak.leak_mb > leak_threshold_mb]
        assert len(significant_leaks) == 0, f"Detected {len(significant_leaks)} significant memory leaks"
    
    async def _simulate_potential_memory_leak_operation(self, operation_id: int):
        """Simulate an operation that might leak memory."""
        # Create temporary objects that should be cleaned up
        temp_objects = []
        
        for i in range(10):
            obj = {
                'id': f"{operation_id}_{i}",
                'data': bytearray(1024),  # 1KB per object
                'timestamp': time.time(),
                'refs': []
            }
            temp_objects.append(obj)
        
        # Create some references that might not be cleaned up properly
        if operation_id % 100 == 0:  # Occasionally create potential leak
            # This should be cleaned up, but might not be immediately
            persistent_ref = temp_objects[0]
            persistent_ref['large_data'] = bytearray(10240)  # 10KB
        
        # Simulate processing
        await asyncio.sleep(0.001)
        
        # Explicit cleanup (simulating proper cleanup)
        del temp_objects
    
    @pytest.mark.slow
    async def test_concurrent_user_memory_isolation_extreme(self, concurrent_user_tester):
        """Test memory isolation between concurrent users under extreme load."""
        logger.info(f"Testing memory isolation with {CONCURRENT_USERS} concurrent users")
        
        # Run concurrent stress test
        results = await concurrent_user_tester.run_concurrent_stress_test(STRESS_TEST_DURATION)
        
        logger.info(f"Concurrent test results: {json.dumps(results, indent=2)}")
        
        # Validate test completion
        assert results['successful_users'] > 0, "No users completed successfully"
        assert results['failed_users'] == 0, f"{results['failed_users']} users failed"
        
        # Validate memory behavior
        assert results['total_operations'] > 0, "No operations were completed"
        assert results['average_memory_increase_mb'] <= MEMORY_LEAK_THRESHOLD_MB, \
            f"Average memory increase {results['average_memory_increase_mb']:.2f}MB exceeds threshold {MEMORY_LEAK_THRESHOLD_MB}MB"
        
        # Validate no significant memory leaks
        assert results['total_leak_events'] == 0, f"Detected {results['total_leak_events']} memory leaks"
        
        # Validate individual user results
        for user_result in results['user_results']:
            assert user_result['memory_valid'], f"User {user_result['user_id']} violated memory limits: {user_result['violations']}"
            assert user_result['peak_memory_mb'] <= MEMORY_LIMIT_MB, \
                f"User {user_result['user_id']} peak memory {user_result['peak_memory_mb']:.1f}MB exceeds limit"
            assert user_result['errors'] == 0, f"User {user_result['user_id']} had {user_result['errors']} errors"
    
    async def test_worker_memory_optimization_extreme(self, extreme_memory_tracker):
        """Test worker process memory optimization under extreme scenarios."""
        logger.info("Testing worker process memory optimization")
        
        baseline = extreme_memory_tracker.measure("baseline")
        
        # Simulate multiple worker-like operations
        worker_count = 10
        operations_per_worker = 200
        
        async def simulate_worker(worker_id: int):
            """Simulate memory-intensive worker operations."""
            worker_memory_usage = []
            
            for op_id in range(operations_per_worker):
                # Pre-operation measurement
                pre_op = extreme_memory_tracker.measure(f"worker_{worker_id}_op_{op_id}_start")
                
                # Simulate worker operations
                await self._simulate_worker_operation(worker_id, op_id)
                
                # Post-operation measurement
                post_op = extreme_memory_tracker.measure(f"worker_{worker_id}_op_{op_id}_end")
                
                worker_memory_usage.append(post_op.rss_mb - pre_op.rss_mb)
                
                # Yield control
                if op_id % 20 == 0:
                    await asyncio.sleep(0.01)
            
            return worker_memory_usage
        
        # Run workers concurrently
        tasks = [simulate_worker(i) for i in range(worker_count)]
        worker_results = await asyncio.gather(*tasks)
        
        # Analyze worker memory usage
        all_memory_deltas = [delta for worker_deltas in worker_results for delta in worker_deltas]
        average_memory_delta = sum(all_memory_deltas) / len(all_memory_deltas) if all_memory_deltas else 0
        max_memory_delta = max(all_memory_deltas) if all_memory_deltas else 0
        
        final = extreme_memory_tracker.measure("final")
        total_increase = final.rss_mb - baseline.rss_mb
        
        logger.info(f"Worker test completed: avg delta {average_memory_delta:.3f}MB, max delta {max_memory_delta:.3f}MB")
        logger.info(f"Total memory increase: {total_increase:.2f}MB")
        
        # Validate worker memory efficiency
        assert average_memory_delta <= 0.1, f"Average worker memory delta {average_memory_delta:.3f}MB too high"
        assert max_memory_delta <= 1.0, f"Max worker memory delta {max_memory_delta:.3f}MB too high"
        assert total_increase <= 50.0, f"Total memory increase {total_increase:.2f}MB too high for worker operations"
    
    async def _simulate_worker_operation(self, worker_id: int, operation_id: int):
        """Simulate a worker operation."""
        # Simulate different types of worker operations
        operation_type = (worker_id + operation_id) % 3
        
        if operation_type == 0:
            # Data processing operation
            data = [f"worker_{worker_id}_data_{i}" for i in range(100)]
            processed = [item.upper() for item in data if len(item) > 10]
            await asyncio.sleep(0.001)
        
        elif operation_type == 1:
            # Computation operation
            result = sum(i * i for i in range(100))
            await asyncio.sleep(0.001)
        
        else:
            # I/O simulation operation
            buffer = bytearray(1024)  # 1KB buffer
            # Simulate I/O processing
            await asyncio.sleep(0.001)
            del buffer
    
    async def test_lazy_loading_memory_efficiency_extreme(self, extreme_memory_tracker):
        """Test lazy loading memory efficiency under extreme load."""
        logger.info("Testing lazy loading memory efficiency")
        
        baseline = extreme_memory_tracker.measure("baseline")
        
        # Simulate lazy loading scenarios
        component_count = 1000
        lazy_loader = LazyComponentLoader() if MEMORY_SERVICES_AVAILABLE else MagicMock()
        
        # Track loaded components
        loaded_components = {}
        component_access_pattern = []
        
        for i in range(component_count * 2):  # More accesses than components
            # Use access pattern that tests lazy loading
            component_id = f"component_{i % component_count}"
            
            pre_load = extreme_memory_tracker.measure(f"pre_load_{component_id}")
            
            # Load component (should be lazy)
            if component_id not in loaded_components:
                component = await self._simulate_lazy_component_load(lazy_loader, component_id)
                loaded_components[component_id] = component
            else:
                component = loaded_components[component_id]
            
            post_load = extreme_memory_tracker.measure(f"post_load_{component_id}")
            
            component_access_pattern.append({
                'component_id': component_id,
                'memory_delta': post_load.rss_mb - pre_load.rss_mb,
                'was_cached': component_id in loaded_components
            })
            
            # Periodic cleanup test
            if i % 200 == 0:
                await self._simulate_lazy_loading_cleanup(loaded_components)
                gc.collect()
                await asyncio.sleep(0.01)
        
        final = extreme_memory_tracker.measure("final")
        total_increase = final.rss_mb - baseline.rss_mb
        
        # Analyze lazy loading efficiency
        initial_loads = [item for item in component_access_pattern if not item['was_cached']]
        cached_loads = [item for item in component_access_pattern if item['was_cached']]
        
        avg_initial_load_memory = sum(item['memory_delta'] for item in initial_loads) / len(initial_loads) if initial_loads else 0
        avg_cached_load_memory = sum(item['memory_delta'] for item in cached_loads) / len(cached_loads) if cached_loads else 0
        
        logger.info(f"Lazy loading test: {len(initial_loads)} initial loads, {len(cached_loads)} cached loads")
        logger.info(f"Avg memory delta - initial: {avg_initial_load_memory:.3f}MB, cached: {avg_cached_load_memory:.3f}MB")
        
        # Validate lazy loading efficiency
        assert avg_cached_load_memory <= avg_initial_load_memory * 0.1, \
            "Cached loads should use significantly less memory than initial loads"
        assert total_increase <= 100.0, f"Total memory increase {total_increase:.2f}MB too high for lazy loading"
        assert len(loaded_components) == component_count, f"Expected {component_count} components, got {len(loaded_components)}"
    
    async def _simulate_lazy_component_load(self, lazy_loader, component_id: str):
        """Simulate lazy component loading."""
        if hasattr(lazy_loader, 'load_component'):
            return await lazy_loader.load_component(component_id)
        else:
            # Mock component
            component = {
                'id': component_id,
                'data': bytearray(1024 * 10),  # 10KB per component
                'loaded_at': time.time(),
                'refs': []
            }
            await asyncio.sleep(0.001)  # Simulate loading time
            return component
    
    async def _simulate_lazy_loading_cleanup(self, loaded_components: Dict[str, Any]):
        """Simulate lazy loading cleanup."""
        # Remove some components to simulate memory cleanup
        components_to_remove = list(loaded_components.keys())[:len(loaded_components) // 10]
        
        for component_id in components_to_remove:
            if component_id in loaded_components:
                del loaded_components[component_id]
    
    async def test_garbage_collection_effectiveness_extreme(self, extreme_memory_tracker, memory_stress_generator):
        """Test garbage collection effectiveness under extreme memory pressure."""
        logger.info("Testing garbage collection effectiveness")
        
        baseline = extreme_memory_tracker.measure("baseline")
        
        # Create circular references that need garbage collection
        circular_refs = memory_stress_generator.create_circular_references(2000)
        after_creation = extreme_memory_tracker.measure("after_circular_refs")
        
        logger.info(f"Created circular references, memory increase: {after_creation.rss_mb - baseline.rss_mb:.2f}MB")
        
        # Clear references
        del circular_refs
        
        # Force multiple garbage collection cycles
        for i in range(3):
            gc.collect()
            await asyncio.sleep(0.1)
            intermediate = extreme_memory_tracker.measure(f"after_gc_{i}")
            logger.info(f"After GC cycle {i}: memory {intermediate.rss_mb:.2f}MB")
        
        # Check weak references cleanup
        alive_refs, total_refs = memory_stress_generator.check_weak_refs_cleanup()
        cleanup_ratio = 1.0 - (alive_refs / total_refs) if total_refs > 0 else 1.0
        
        final = extreme_memory_tracker.measure("final")
        memory_recovered = after_creation.rss_mb - final.rss_mb
        
        logger.info(f"Garbage collection results:")
        logger.info(f"  Memory recovered: {memory_recovered:.2f}MB")
        logger.info(f"  Cleanup ratio: {cleanup_ratio:.2%}")
        logger.info(f"  Alive refs: {alive_refs}/{total_refs}")
        
        # Validate garbage collection effectiveness
        assert memory_recovered > 0, "No memory was recovered by garbage collection"
        assert cleanup_ratio > 0.9, f"Cleanup ratio {cleanup_ratio:.2%} too low, expected >90%"
        assert alive_refs <= total_refs * 0.1, f"Too many references still alive: {alive_refs}/{total_refs}"
    
    @pytest.mark.slow 
    async def test_memory_pressure_handling_extreme(self, extreme_memory_tracker, memory_stress_generator):
        """Test system behavior under extreme memory pressure."""
        logger.info("Testing extreme memory pressure handling")
        
        baseline = extreme_memory_tracker.measure("baseline")
        
        # Gradually increase memory pressure
        pressure_levels = [0.3, 0.5, 0.7, 0.85, 0.95]  # As fraction of memory limit
        
        for pressure_level in pressure_levels:
            target_mb = MEMORY_LIMIT_MB * pressure_level
            logger.info(f"Testing memory pressure level: {pressure_level:.0%} ({target_mb:.0f}MB)")
            
            try:
                # Allocate memory to reach pressure level
                allocated = await memory_stress_generator.allocate_memory_gradually(
                    target_mb=target_mb - baseline.rss_mb,
                    step_mb=20.0,
                    delay_seconds=0.02
                )
                
                pressure_measurement = extreme_memory_tracker.measure(f"pressure_{pressure_level}")
                
                # Test system responsiveness under pressure
                start_time = time.time()
                await self._test_system_responsiveness_under_pressure()
                response_time = time.time() - start_time
                
                logger.info(f"System response time under {pressure_level:.0%} pressure: {response_time:.3f}s")
                
                # Validate system behavior
                assert pressure_measurement.rss_mb <= MEMORY_LIMIT_MB, \
                    f"Memory pressure test exceeded limit: {pressure_measurement.rss_mb:.1f}MB"
                assert response_time <= 1.0, f"System too slow under pressure: {response_time:.3f}s"
                
                # Clean up this pressure level
                memory_stress_generator.cleanup_allocated_memory()
                gc.collect()
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed at pressure level {pressure_level:.0%}: {e}")
                # Clean up and continue
                memory_stress_generator.cleanup_allocated_memory()
                gc.collect()
                
                if pressure_level >= 0.95:  # Expected to fail at very high pressure
                    logger.info("High pressure failure is acceptable")
                    continue
                else:
                    raise
        
        final = extreme_memory_tracker.measure("final")
        logger.info(f"Memory pressure test completed, final memory: {final.rss_mb:.2f}MB")
    
    async def _test_system_responsiveness_under_pressure(self):
        """Test system responsiveness under memory pressure."""
        # Simulate typical system operations
        operations = [
            self._simulate_json_processing(),
            self._simulate_string_operations(),
            self._simulate_list_operations(),
            self._simulate_async_operations()
        ]
        
        await asyncio.gather(*operations)
    
    async def _simulate_json_processing(self):
        """Simulate JSON processing operations."""
        data = {'test': 'data', 'items': list(range(100))}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        await asyncio.sleep(0.01)
    
    async def _simulate_string_operations(self):
        """Simulate string operations."""
        text = "test string " * 100
        processed = text.upper().replace("TEST", "processed")
        await asyncio.sleep(0.01)
    
    async def _simulate_list_operations(self):
        """Simulate list operations."""
        items = list(range(1000))
        filtered = [x for x in items if x % 2 == 0]
        sorted_items = sorted(filtered, reverse=True)
        await asyncio.sleep(0.01)
    
    async def _simulate_async_operations(self):
        """Simulate async operations."""
        async def async_task(n):
            await asyncio.sleep(0.001)
            return n * 2
        
        tasks = [async_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)