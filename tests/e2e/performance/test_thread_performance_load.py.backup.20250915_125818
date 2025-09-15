"""Thread Performance Load Tests
Focused tests for thread operations under heavy load conditions.
Split from test_thread_performance_core.py to meet size requirements.

BVJ: Load performance ensures platform stability under enterprise usage patterns.
Segment: Enterprise primarily. Business Goal: Platform reliability and scalability.
Value Impact: Load handling prevents performance degradation during peak usage.
Strategic Impact: Performance under load directly impacts enterprise customer satisfaction.
"""

import asyncio
import statistics
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.schemas.core_enums import WebSocketMessageType
from tests.e2e.config import TEST_USERS
from tests.e2e.fixtures.core.thread_test_fixtures_core import (
    ThreadContextManager,
    ThreadPerformanceUtils,
    ThreadWebSocketFixtures,
    performance_utils,
    thread_context_manager,
    unified_harness,
    ws_thread_fixtures,
)


class TestThreadLoader:
    """Specialized load testing for thread operations."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures, perf_utils: ThreadPerformanceUtils):
        self.ws_fixtures = ws_fixtures
        self.perf_utils = perf_utils
        self.load_metrics: List[Dict[str, Any]] = []
    
    async def simulate_user_load(self, user_count: int, operations_per_user: int) -> Dict[str, Any]:
        """Simulate realistic user load patterns."""
        user_tasks = []
        
        for i in range(user_count):
            user_id = f"load_user_{i}"
            task = self._simulate_single_user_workload(user_id, operations_per_user, i)
            user_tasks.append(task)
        
        # Execute concurrent user operations
        start_time = time.perf_counter()
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze load test results
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_users = len(results) - len(successful_users)
        
        total_operations = sum(r.get("completed_operations", 0) for r in successful_users)
        
        load_metrics = {
            "total_time": total_time,
            "user_count": user_count,
            "successful_users": len(successful_users),
            "failed_users": failed_users,
            "total_operations": total_operations,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0,
            "avg_operations_per_user": total_operations / len(successful_users) if successful_users else 0,
            "success_rate": len(successful_users) / user_count if user_count > 0 else 0
        }
        
        self.load_metrics.append({
            "test_type": "user_load",
            "metrics": load_metrics,
            "timestamp": time.time()
        })
        
        return load_metrics
    
    async def _simulate_single_user_workload(self, user_id: str, operation_count: int, 
                                             user_index: int) -> Dict[str, Any]:
        """Simulate realistic single user workload."""
        try:
            # Create connection
            await self.ws_fixtures.create_authenticated_connection(user_id)
            
            completed_operations = 0
            created_threads = []
            
            # Phase 1: Create threads (typical user starts with 1-3 threads)
            thread_creation_count = min(3, max(1, operation_count // 3))
            for i in range(thread_creation_count):
                thread_id = f"load_user_{user_index}_thread_{i}_{int(time.time())}"
                thread_name = f"Load User {user_index} Thread {i+1}"
                
                # Create thread
                message = self.ws_fixtures.build_websocket_message(
                    WebSocketMessageType.CREATE_THREAD,
                    thread_id=thread_id,
                    thread_name=thread_name
                )
                await self.ws_fixtures.send_websocket_message(user_id, message)
                
                # Initialize context
                context_key = f"{user_id}:{thread_id}"
                self.ws_fixtures.thread_contexts[context_key] = {
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "created_at": time.time(),
                    "messages": [],
                    "load_test": True
                }
                
                created_threads.append(thread_id)
                completed_operations += 1
            
            # Phase 2: Perform thread switches (users typically switch between threads)
            switch_count = min(operation_count - completed_operations, len(created_threads) * 3)
            for i in range(switch_count):
                if created_threads:
                    thread_id = created_threads[i % len(created_threads)]
                    
                    switch_message = self.ws_fixtures.build_websocket_message(
                        WebSocketMessageType.SWITCH_THREAD,
                        thread_id=thread_id
                    )
                    await self.ws_fixtures.send_websocket_message(user_id, switch_message)
                    
                    # Update context access
                    context_key = f"{user_id}:{thread_id}"
                    if context_key in self.ws_fixtures.thread_contexts:
                        self.ws_fixtures.thread_contexts[context_key]["last_accessed"] = time.time()
                    
                    completed_operations += 1
            
            return {
                "success": True,
                "user_id": user_id,
                "user_index": user_index,
                "completed_operations": completed_operations,
                "created_threads": len(created_threads)
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "user_index": user_index,
                "error": str(e),
                "completed_operations": 0
            }
    
    async def measure_sustained_load(self, duration_seconds: int, 
                                     operations_per_second: int) -> Dict[str, Any]:
        """Measure performance under sustained load."""
        total_operations = duration_seconds * operations_per_second
        operations_executed = 0
        errors = []
        
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        operation_times = []
        
        while time.perf_counter() < end_time:
            batch_start = time.perf_counter()
            
            # Execute batch of operations
            batch_size = min(10, operations_per_second)  # Process in batches
            batch_tasks = []
            
            for i in range(batch_size):
                user_id = f"sustained_user_{operations_executed + i}"
                task = self._execute_single_load_operation(user_id, operations_executed + i)
                batch_tasks.append(task)
            
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        errors.append(str(result))
                    else:
                        operations_executed += 1
                        operation_times.append(time.perf_counter() - batch_start)
                
            except Exception as e:
                errors.append(str(e))
            
            # Control rate
            batch_duration = time.perf_counter() - batch_start
            target_batch_time = batch_size / operations_per_second
            if batch_duration < target_batch_time:
                await asyncio.sleep(target_batch_time - batch_duration)
        
        actual_duration = time.perf_counter() - start_time
        
        sustained_metrics = {
            "duration": actual_duration,
            "target_operations": total_operations,
            "completed_operations": operations_executed,
            "errors": len(errors),
            "actual_ops_per_second": operations_executed / actual_duration,
            "target_ops_per_second": operations_per_second,
            "success_rate": operations_executed / total_operations if total_operations > 0 else 0,
            "avg_operation_time": statistics.mean(operation_times) if operation_times else 0,
            "error_details": errors[:5]  # Sample of errors
        }
        
        self.load_metrics.append({
            "test_type": "sustained_load",
            "metrics": sustained_metrics,
            "timestamp": time.time()
        })
        
        return sustained_metrics
    
    async def _execute_single_load_operation(self, user_id: str, operation_index: int) -> Dict[str, Any]:
        """Execute single operation for sustained load test."""
        # Create connection if not exists
        if user_id not in self.ws_fixtures.active_connections:
            await self.ws_fixtures.create_authenticated_connection(user_id)
        
        # Alternate between thread creation and switching
        if operation_index % 2 == 0:
            # Create thread
            thread_id = f"sustained_thread_{operation_index}_{int(time.time())}"
            message = self.ws_fixtures.build_websocket_message(
                WebSocketMessageType.CREATE_THREAD,
                thread_id=thread_id,
                thread_name=f"Sustained Thread {operation_index}"
            )
            await self.ws_fixtures.send_websocket_message(user_id, message)
            
            # Initialize context
            context_key = f"{user_id}:{thread_id}"
            self.ws_fixtures.thread_contexts[context_key] = {
                "thread_id": thread_id,
                "created_at": time.time(),
                "messages": [],
                "sustained_load": True
            }
            
            return {"operation": "create", "thread_id": thread_id}
        else:
            # Switch to existing thread (if any)
            user_contexts = [
                key for key in self.ws_fixtures.thread_contexts.keys()
                if key.startswith(f"{user_id}:")
            ]
            
            if user_contexts:
                context_key = user_contexts[0]  # Switch to first available thread
                thread_id = context_key.split(":", 1)[1]
                
                switch_message = self.ws_fixtures.build_websocket_message(
                    WebSocketMessageType.SWITCH_THREAD,
                    thread_id=thread_id
                )
                await self.ws_fixtures.send_websocket_message(user_id, switch_message)
                
                return {"operation": "switch", "thread_id": thread_id}
            else:
                # No threads to switch to, create one
                thread_id = f"fallback_thread_{operation_index}_{int(time.time())}"
                message = self.ws_fixtures.build_websocket_message(
                    WebSocketMessageType.CREATE_THREAD,
                    thread_id=thread_id,
                    thread_name=f"Fallback Thread {operation_index}"
                )
                await self.ws_fixtures.send_websocket_message(user_id, message)
                
                return {"operation": "create_fallback", "thread_id": thread_id}


@pytest.fixture
def thread_load_tester(ws_thread_fixtures, performance_utils):
    """Thread load tester fixture."""
    return ThreadLoadTester(ws_thread_fixtures, performance_utils)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_user_load_performance(thread_load_tester):
    """Test performance with realistic concurrent user load."""
    user_count = 8
    operations_per_user = 6
    
    # Execute load test
    load_metrics = await thread_load_tester.simulate_user_load(user_count, operations_per_user)
    
    # Verify load performance requirements
    assert load_metrics["successful_users"] >= user_count * 0.85, \
           f"At least 85% of users must succeed, got {load_metrics['successful_users']}/{user_count}"
    
    assert load_metrics["operations_per_second"] >= 15.0, \
           f"Load throughput must be >= 15 ops/sec, got {load_metrics['operations_per_second']:.2f}"
    
    assert load_metrics["total_time"] < 8.0, \
           f"Load test must complete within 8 seconds, took {load_metrics['total_time']:.2f}s"
    
    assert load_metrics["success_rate"] >= 0.85, \
           f"Overall success rate must be >= 85%, got {load_metrics['success_rate']:.2%}"
    
    # Verify reasonable operation distribution
    expected_total_operations = user_count * operations_per_user
    actual_operations = load_metrics["total_operations"]
    
    assert actual_operations >= expected_total_operations * 0.8, \
           f"Should complete at least 80% of operations, got {actual_operations}/{expected_total_operations}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_sustained_load_performance(thread_load_tester):
    """Test performance under sustained load over time."""
    duration_seconds = 5
    target_ops_per_second = 12
    
    # Execute sustained load test
    sustained_metrics = await thread_load_tester.measure_sustained_load(
        duration_seconds, target_ops_per_second
    )
    
    # Verify sustained performance requirements
    assert sustained_metrics["success_rate"] >= 0.8, \
           f"Sustained success rate must be >= 80%, got {sustained_metrics['success_rate']:.2%}"
    
    assert sustained_metrics["actual_ops_per_second"] >= target_ops_per_second * 0.8, \
           f"Must achieve 80% of target throughput, got {sustained_metrics['actual_ops_per_second']:.2f}"
    
    assert sustained_metrics["errors"] <= sustained_metrics["completed_operations"] * 0.1, \
           f"Error count must be <= 10% of operations, got {sustained_metrics['errors']}"
    
    assert sustained_metrics["avg_operation_time"] < 1.0, \
           f"Average operation time must be < 1s, got {sustained_metrics['avg_operation_time']:.3f}s"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_peak_load_burst_handling(ws_thread_fixtures, thread_load_tester):
    """Test handling of peak load bursts."""
    # Simulate burst load pattern
    burst_user_count = 15
    burst_operations = 4
    
    # Execute burst load
    start_time = time.perf_counter()
    burst_metrics = await thread_load_tester.simulate_user_load(
        burst_user_count, burst_operations
    )
    burst_duration = time.perf_counter() - start_time
    
    # Verify burst handling
    assert burst_duration < 6.0, \
           f"Burst load must be handled within 6 seconds, took {burst_duration:.2f}s"
    
    assert burst_metrics["successful_users"] >= burst_user_count * 0.75, \
           f"At least 75% of burst users must succeed, got {burst_metrics['successful_users']}/{burst_user_count}"
    
    assert burst_metrics["operations_per_second"] >= 8.0, \
           f"Burst throughput must be >= 8 ops/sec, got {burst_metrics['operations_per_second']:.2f}"
    
    # Verify system stability after burst
    assert len(ws_thread_fixtures.active_connections) >= burst_user_count * 0.8, \
           "Most connections should remain active after burst"
    
    # Verify thread contexts integrity
    total_contexts = len(ws_thread_fixtures.thread_contexts)
    expected_min_contexts = burst_user_count * burst_operations * 0.3  # Minimum expected threads
    
    assert total_contexts >= expected_min_contexts, \
           f"Should have created minimum threads, got {total_contexts}, expected >= {expected_min_contexts}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_load_performance_degradation_limits(thread_load_tester):
    """Test that performance degradation stays within acceptable limits under load."""
    # Baseline performance test
    baseline_metrics = await thread_load_tester.simulate_user_load(2, 4)
    baseline_ops_per_sec = baseline_metrics["operations_per_second"]
    
    # Load performance test
    load_metrics = await thread_load_tester.simulate_user_load(10, 4)
    load_ops_per_sec = load_metrics["operations_per_second"]
    
    # Calculate performance degradation
    if baseline_ops_per_sec > 0:
        degradation_ratio = load_ops_per_sec / baseline_ops_per_sec
        degradation_percent = (1 - degradation_ratio) * 100
        
        # Performance should not degrade more than 50% under 5x load
        assert degradation_percent <= 50.0, \
               f"Performance degradation must be <= 50%, got {degradation_percent:.1f}%"
        
        assert degradation_ratio >= 0.5, \
               f"Load performance must be >= 50% of baseline, ratio: {degradation_ratio:.2f}"
    
    # Verify both tests had acceptable performance
    assert baseline_metrics["success_rate"] >= 0.9, "Baseline test should have high success rate"
    assert load_metrics["success_rate"] >= 0.8, "Load test should maintain reasonable success rate"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_memory_efficiency_under_load(ws_thread_fixtures, thread_load_tester):
    """Test memory efficiency and cleanup under load conditions."""
    # Capture initial state
    initial_connections = len(ws_thread_fixtures.active_connections)
    initial_contexts = len(ws_thread_fixtures.thread_contexts)
    initial_events = len(ws_thread_fixtures.thread_events)
    
    # Execute load test
    load_metrics = await thread_load_tester.simulate_user_load(6, 5)
    
    # Capture peak state
    peak_connections = len(ws_thread_fixtures.active_connections)
    peak_contexts = len(ws_thread_fixtures.thread_contexts)
    peak_events = len(ws_thread_fixtures.thread_events)
    
    # Verify reasonable resource usage
    connection_growth = peak_connections - initial_connections
    context_growth = peak_contexts - initial_contexts
    event_growth = peak_events - initial_events
    
    # Connections should grow linearly with users
    expected_connection_growth = load_metrics["successful_users"]
    assert connection_growth <= expected_connection_growth * 1.2, \
           f"Connection growth should be reasonable, got {connection_growth}, expected ~{expected_connection_growth}"
    
    # Contexts should grow with thread creation
    expected_min_contexts = load_metrics["total_operations"] * 0.3  # Assume ~30% are thread creations
    assert context_growth >= expected_min_contexts, \
           f"Should have created minimum contexts, got {context_growth}, expected >= {expected_min_contexts}"
    
    # Events should be proportional to operations
    assert event_growth >= load_metrics["total_operations"] * 0.5, \
           f"Should have generated reasonable events, got {event_growth} for {load_metrics['total_operations']} ops"
    
    # Verify no memory leaks (basic check)
    contexts_per_user = context_growth / max(1, load_metrics["successful_users"])
    assert contexts_per_user <= 10, \
           f"Contexts per user should be reasonable, got {contexts_per_user:.1f}"
